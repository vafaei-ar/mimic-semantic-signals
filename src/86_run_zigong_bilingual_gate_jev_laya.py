from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path

import torch

from semantic_schema import SEMANTIC_CONSTRUCTS


def load_module(filename: str, name: str):
    path=Path(__file__).with_name(filename)
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {filename}")
    mod=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=mod
    spec.loader.exec_module(mod)
    return mod


def load_cases(path: Path):
    cfg=json.loads(path.read_text(encoding="utf-8"))
    cases=[]
    for contrast in cfg["contrasts"]:
        construct=contrast["construct"]
        for state in ("negative","positive"):
            for language in ("en","zh"):
                cases.append({
                    "case_id":f"{construct}__{state}__{language}",
                    "construct":construct,
                    "state":state,
                    "language":language,
                    "note":contrast[state][language],
                })
    return cases


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--config",required=True)
    ap.add_argument("--laya-dir",required=True)
    ap.add_argument("--output",required=True)
    args=ap.parse_args()

    os.environ["HF_HUB_OFFLINE"]="1"
    os.environ["TRANSFORMERS_OFFLINE"]="1"
    os.environ["HF_DATASETS_OFFLINE"]="1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"]="1"
    os.environ["USE_TF"]="0"

    cases=load_cases(Path(args.config).resolve())
    oj_mod=load_module("22_run_open_jev_real_local.py","openjev_real_runner_for_bilingual_gate")
    laya_mod=load_module("37_run_laya_real_local.py","laya_real_runner_for_bilingual_gate")
    synthetic_case={"questions":SEMANTIC_CONSTRUCTS}

    report={
        "analysis":"Synthetic bilingual semantic gate raw scores for Open-Jev and Laya",
        "synthetic_only":True,
        "labels_read_or_used":False,
        "patient_data_read":False,
        "models":{},
    }

    from typed_decisions.open_jev import OpenJev
    oj=OpenJev.from_pretrained("com-kotobalabs/open-jev-deberta-v3-large",device="cuda")
    oj_names,oj_questions=oj_mod.make_questions(synthetic_case)
    oj_scores={}
    for case in cases:
        ids=oj.tok(case["note"],add_special_tokens=False)["input_ids"]
        chunks=oj_mod.chunk_token_ids(ids,size=220,overlap=40,max_chunks=8)
        chunk_texts=[oj.tok.decode(x,skip_special_tokens=True) for x in chunks]
        per={name:[] for name in oj_names}
        for text in chunk_texts:
            packs=oj_mod.context_safe_question_packs(
                oj,text,oj_names,oj_questions,max_questions_per_pack=4
            )
            for n_pack,q_pack in packs:
                answers=oj.decide(text,q_pack)
                for name,answer in zip(n_pack,answers):
                    p=answer.get("noul")
                    if isinstance(p,(int,float)):
                        per[name].append(float(p))
        scores={name:oj_mod.aggregate_probabilities(name,vals) for name,vals in per.items()}
        if len(scores)!=8 or any(not isinstance(v,float) for v in scores.values()):
            raise RuntimeError(f"Open-Jev invalid score row: {case['case_id']}")
        oj_scores[case["case_id"]]=scores
    report["models"]["open_jev"]={"score_definition":"noul probability","scores":oj_scores}
    del oj
    torch.cuda.empty_cache()

    import laya
    agent=laya.load(str(Path(args.laya_dir).expanduser().resolve()),device="cuda")
    lq=laya_mod.make_questions(synthetic_case)
    laya_scores={}
    for case in cases:
        ids=agent.tok(case["note"],add_special_tokens=False)["input_ids"]
        chunks=laya_mod.chunk_token_ids(ids,size=600,overlap=100,max_chunks=8)
        chunk_texts=[agent.tok.decode(x,skip_special_tokens=True) for x in chunks]
        per={name:[] for name in lq}
        for text in chunk_texts:
            result=agent.predict(text,lq)
            answers=result.get("answers",{})
            for name in lq:
                p=answers.get(name,{}).get("noul")
                if isinstance(p,(int,float)):
                    per[name].append(float(p))
        scores={name:laya_mod.aggregate_probability(name,vals) for name,vals in per.items()}
        if len(scores)!=8 or any(not isinstance(v,float) for v in scores.values()):
            raise RuntimeError(f"Laya invalid score row: {case['case_id']}")
        laya_scores[case["case_id"]]=scores
    report["models"]["laya"]={"score_definition":"noul probability","scores":laya_scores}
    del agent
    torch.cuda.empty_cache()

    out=Path(args.output).resolve()
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({
        "analysis":report["analysis"],
        "synthetic_notes":len(cases),
        "models":{k:len(v["scores"]) for k,v in report["models"].items()},
    },indent=2))


if __name__=="__main__":
    main()
