from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path

import torch


def load_calibration_module():
    path=Path(__file__).with_name("64_calibrate_diffusiongemma_hf_native.py")
    spec=importlib.util.spec_from_file_location("dg_calibration_for_bilingual_gate",path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load DiffusionGemma calibration helpers.")
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
                    "note":contrast[state][language],
                })
    return cases


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--config",required=True)
    ap.add_argument("--model-dir",required=True)
    ap.add_argument("--output",required=True)
    ap.add_argument("--seed",type=int,default=20260924)
    ap.add_argument("--max-new-tokens",type=int,default=256)
    ap.add_argument("--parse-retries",type=int,default=2)
    args=ap.parse_args()

    os.environ["HF_HUB_OFFLINE"]="1"
    os.environ["TRANSFORMERS_OFFLINE"]="1"
    os.environ["HF_DATASETS_OFFLINE"]="1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"]="1"

    from transformers import AutoProcessor, DiffusionGemmaForBlockDiffusion

    helper=load_calibration_module()
    cases=load_cases(Path(args.config).resolve())
    model_dir=Path(args.model_dir).resolve()
    processor=AutoProcessor.from_pretrained(str(model_dir),local_files_only=True)
    model=DiffusionGemmaForBlockDiffusion.from_pretrained(
        str(model_dir),
        dtype=torch.bfloat16,
        device_map="auto",
        low_cpu_mem_usage=True,
        local_files_only=True,
        attn_implementation="sdpa",
    )
    model.eval()
    first_device=next(model.parameters()).device

    scores={}
    retries_used=0
    for idx,case in enumerate(cases):
        prompt=helper.build_prompt(case["note"])
        parsed=None
        last_error=None
        for attempt in range(args.parse_retries+1):
            torch.manual_seed(args.seed+idx+attempt*10000)
            torch.cuda.manual_seed_all(args.seed+idx+attempt*10000)
            inputs=processor.apply_chat_template(
                [{"role":"user","content":prompt}],
                tokenize=True,
                add_generation_prompt=True,
                return_dict=True,
                return_tensors="pt",
                enable_thinking=False,
            )
            inputs={k:v.to(first_device) if hasattr(v,"to") else v for k,v in inputs.items()}
            input_len=inputs["input_ids"].shape[-1]
            with torch.inference_mode():
                generated=model.generate(**inputs,max_new_tokens=args.max_new_tokens)
            sequences=getattr(generated,"sequences",generated)
            completion_ids=sequences[0,input_len:].detach().cpu().tolist()
            decoded=processor.tokenizer.decode(completion_ids,skip_special_tokens=True)
            try:
                parsed=helper.extract_scores(decoded)
                retries_used += attempt
                break
            except Exception as exc:
                last_error=exc
        if parsed is None:
            raise RuntimeError(f"DiffusionGemma parse failed for {case['case_id']}: {last_error}")
        scores[case["case_id"]]=parsed

    report={
        "analysis":"Synthetic bilingual semantic gate raw scores for DiffusionGemma",
        "synthetic_only":True,
        "labels_read_or_used":False,
        "patient_data_read":False,
        "model":"google/diffusiongemma-26B-A4B-it",
        "backend":"transformers_native_bf16",
        "score_definition":"Prompted zero-shot 0-1 support scores; not Jev noul probabilities.",
        "parse_retries_used":int(retries_used),
        "scores":scores,
    }
    out=Path(args.output).resolve()
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({
        "analysis":report["analysis"],
        "synthetic_notes":len(scores),
        "parse_retries_used":retries_used,
    },indent=2))


if __name__=="__main__":
    main()
