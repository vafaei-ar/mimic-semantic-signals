from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import sys
from pathlib import Path

import torch


def load_v1_module():
    path=Path(__file__).with_name("83_audit_zigong_tokenizers.py")
    spec=importlib.util.spec_from_file_location("zigong_tokenizer_audit_v1",path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load tokenizer audit helpers.")
    mod=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=mod
    spec.loader.exec_module(mod)
    return mod


def chunking_summary(tokenizer, notes, *, chunk_tokens:int, overlap:int, max_chunks:int):
    counts=[]
    needed=[]
    truncated=0
    capacity=chunk_tokens + max(0,max_chunks-1)*(chunk_tokens-overlap)
    for note in notes:
        ids=tokenizer(note,add_special_tokens=False)["input_ids"]
        if ids and isinstance(ids[0],list):
            ids=ids[0]
        n=len(ids)
        counts.append(n)
        if n <= chunk_tokens:
            k=1
        else:
            k=1+math.ceil((n-chunk_tokens)/(chunk_tokens-overlap))
        needed.append(k)
        if k>max_chunks:
            truncated += 1
    def qs(vals):
        vals=sorted(float(x) for x in vals)
        if not vals:
            return {"n":0}
        def q(p):
            if len(vals)==1: return vals[0]
            pos=(len(vals)-1)*p
            lo=int(math.floor(pos)); hi=int(math.ceil(pos))
            if lo==hi: return vals[lo]
            return vals[lo]*(hi-pos)+vals[hi]*(pos-lo)
        return {
            "n":len(vals),"p05":q(.05),"p25":q(.25),"median":q(.5),
            "p75":q(.75),"p95":q(.95),"max":vals[-1]
        }
    return {
        "chunk_tokens":chunk_tokens,
        "chunk_overlap":overlap,
        "max_chunks":max_chunks,
        "maximum_representable_tokens_under_policy":capacity,
        "note_token_count":qs(counts),
        "chunks_needed":qs(needed),
        "notes_exceeding_max_chunks":int(truncated),
        "fraction_notes_exceeding_max_chunks":float(truncated/len(notes)) if notes else None,
    }


def main():
    ap=argparse.ArgumentParser(description="Exact-pipeline tokenizer applicability audit for frozen Zigong cohort.")
    ap.add_argument("--cases",required=True)
    ap.add_argument("--laya-dir",required=True)
    ap.add_argument("--diffusiongemma-dir",required=True)
    ap.add_argument("--output",required=True)
    args=ap.parse_args()

    os.environ["HF_HUB_OFFLINE"]="1"
    os.environ["TRANSFORMERS_OFFLINE"]="1"
    os.environ["HF_DATASETS_OFFLINE"]="1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"]="1"
    os.environ["USE_TF"]="0"

    v1=load_v1_module()
    notes=v1.load_notes(Path(args.cases).expanduser().resolve())

    char_counts=[len(x) for x in notes]
    cjk_counts=[sum(v1.is_cjk(ch) for ch in x) for x in notes]
    nonspace_counts=[sum(not ch.isspace() for ch in x) for x in notes]

    report={
        "analysis":"Frozen Zigong exact-pipeline tokenizer/language applicability audit v2",
        "local_only":True,
        "labels_read_or_used":False,
        "model_inference_performed":False,
        "contains_note_text":False,
        "contains_patient_identifiers":False,
        "notes":len(notes),
        "language_profile":{
            "character_count":v1.quantiles(char_counts),
            "cjk_character_count":v1.quantiles(cjk_counts),
            "overall_cjk_fraction_of_nonspace_characters":float(sum(cjk_counts)/sum(nonspace_counts)) if sum(nonspace_counts) else 0.0,
            "notes_with_any_cjk":int(sum(c>0 for c in cjk_counts)),
        },
        "tokenizers":{},
        "load_errors":{},
        "pipeline_loading":{
            "open_jev":"typed_decisions.open_jev.OpenJev.from_pretrained(...).tok",
            "laya":"laya.load(...).tok",
            "diffusiongemma":"transformers.AutoProcessor.from_pretrained(...).tokenizer",
        }
    }

    # Open-Jev: use exact working inference loader, no decide/predict call.
    try:
        from typed_decisions.open_jev import OpenJev
        model=OpenJev.from_pretrained("com-kotobalabs/open-jev-deberta-v3-large",device="cuda")
        tok=model.tok
        rep=v1.audit_tokenizer("open_jev",tok,notes,context_hint=None)
        rep["frozen_chunking_policy"]=chunking_summary(tok,notes,chunk_tokens=220,overlap=40,max_chunks=8)
        report["tokenizers"]["open_jev"]=rep
        del model
        torch.cuda.empty_cache()
    except Exception as exc:
        report["load_errors"]["open_jev"]={"error_type":type(exc).__name__,"error_message":str(exc)[:1200]}
        torch.cuda.empty_cache()

    # Laya: use exact working inference loader, no agent.predict call.
    try:
        import laya
        agent=laya.load(str(Path(args.laya_dir).expanduser().resolve()),device="cuda")
        tok=agent.tok
        rep=v1.audit_tokenizer("laya",tok,notes,context_hint=None)
        rep["frozen_chunking_policy"]=chunking_summary(tok,notes,chunk_tokens=600,overlap=100,max_chunks=8)
        report["tokenizers"]["laya"]=rep
        del agent
        torch.cuda.empty_cache()
    except Exception as exc:
        report["load_errors"]["laya"]={"error_type":type(exc).__name__,"error_message":str(exc)[:1200]}
        torch.cuda.empty_cache()

    # DiffusionGemma: exact native-HF processor path; processor/tokenizer only, no model load.
    try:
        from transformers import AutoProcessor
        processor=AutoProcessor.from_pretrained(
            str(Path(args.diffusiongemma_dir).expanduser().resolve()),
            local_files_only=True,
        )
        tok=processor.tokenizer
        rep=v1.audit_tokenizer("diffusiongemma",tok,notes,context_hint=2048)
        rep["frozen_chunking_policy"]=chunking_summary(tok,notes,chunk_tokens=977,overlap=97,max_chunks=8)
        report["tokenizers"]["diffusiongemma"]=rep
        del processor
    except Exception as exc:
        report["load_errors"]["diffusiongemma"]={"error_type":type(exc).__name__,"error_message":str(exc)[:1200]}

    report["guardrail"]=(
        "No outcome labels are read and no semantic predictions are generated. "
        "Tokenizer and chunking coverage are necessary but not sufficient for semantic validity. "
        "A label-free bilingual semantic-consistency gate must be frozen and passed before any Zigong outcome performance is inspected."
    )

    out=Path(args.output).expanduser().resolve()
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2,ensure_ascii=False))


if __name__=="__main__":
    main()
