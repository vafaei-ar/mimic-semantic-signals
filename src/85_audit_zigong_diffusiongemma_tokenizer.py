from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def is_cjk(ch:str)->bool:
    x=ord(ch)
    return (
        0x3400<=x<=0x4DBF or 0x4E00<=x<=0x9FFF or
        0xF900<=x<=0xFAFF or 0x20000<=x<=0x2FA1F
    )


def quantiles(values):
    vals=sorted(float(x) for x in values)
    if not vals: return {"n":0}
    def q(p):
        if len(vals)==1: return vals[0]
        pos=(len(vals)-1)*p
        lo=int(math.floor(pos)); hi=int(math.ceil(pos))
        if lo==hi: return vals[lo]
        return vals[lo]*(hi-pos)+vals[hi]*(pos-lo)
    return {"n":len(vals),"p05":q(.05),"p25":q(.25),"median":q(.5),"p75":q(.75),"p95":q(.95),"max":vals[-1]}


def load_notes(path:Path):
    out=[]
    with path.open("r",encoding="utf-8") as f:
        for line in f:
            if not line.strip(): continue
            rec=json.loads(line)
            note=rec.get("model_state",{}).get("clinical_note")
            if not isinstance(note,str) or not note.strip():
                raise RuntimeError("Blank/missing note in frozen Zigong cohort.")
            out.append(note)
    return out


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--cases",required=True)
    ap.add_argument("--model-dir",required=True)
    ap.add_argument("--output",required=True)
    args=ap.parse_args()

    from transformers import AutoProcessor

    notes=load_notes(Path(args.cases).expanduser().resolve())
    processor=AutoProcessor.from_pretrained(str(Path(args.model_dir).expanduser().resolve()),local_files_only=True)
    tok=processor.tokenizer
    unk_id=getattr(tok,"unk_token_id",None)

    token_counts=[]; unk_counts=[]; cjk_ratios=[]; chunks_needed=[]; truncated=0
    total_tokens=0; total_unk=0
    size=977; overlap=97; max_chunks=8
    for note in notes:
        ids=tok(note,add_special_tokens=False)["input_ids"]
        if ids and isinstance(ids[0],list): ids=ids[0]
        ids=list(ids)
        n=len(ids); token_counts.append(n); total_tokens+=n
        u=sum(int(x)==int(unk_id) for x in ids) if unk_id is not None else 0
        unk_counts.append(u); total_unk+=u
        dec=tok.decode(ids,skip_special_tokens=True)
        oc=sum(is_cjk(ch) for ch in note); dc=sum(is_cjk(ch) for ch in dec)
        cjk_ratios.append(dc/oc if oc else 1.0)
        k=1 if n<=size else 1+math.ceil((n-size)/(size-overlap))
        chunks_needed.append(k)
        if k>max_chunks: truncated+=1

    report={
        "analysis":"Frozen Zigong DiffusionGemma exact-environment tokenizer audit",
        "local_only":True,
        "labels_read_or_used":False,
        "model_inference_performed":False,
        "contains_note_text":False,
        "contains_patient_identifiers":False,
        "notes":len(notes),
        "tokenizer_class":type(tok).__name__,
        "vocab_size":int(getattr(tok,"vocab_size",0) or 0),
        "unk_token":str(getattr(tok,"unk_token",None)),
        "unk_token_id":int(unk_id) if unk_id is not None else None,
        "note_token_count":quantiles(token_counts),
        "overall_unknown_token_fraction":float(total_unk/total_tokens) if total_tokens else None,
        "notes_with_any_unknown_token":int(sum(u>0 for u in unk_counts)),
        "unknown_tokens_per_note":quantiles(unk_counts),
        "decoded_to_original_cjk_count_ratio":quantiles(cjk_ratios),
        "frozen_chunking_policy":{
            "chunk_tokens":size,
            "chunk_overlap":overlap,
            "max_chunks":max_chunks,
            "maximum_representable_tokens_under_policy":size+(max_chunks-1)*(size-overlap),
            "chunks_needed":quantiles(chunks_needed),
            "notes_exceeding_max_chunks":int(truncated),
            "fraction_notes_exceeding_max_chunks":float(truncated/len(notes)) if notes else None,
        },
        "guardrail":"Tokenizer coverage only. No semantic predictions or outcome labels are used."
    }
    out=Path(args.output).expanduser().resolve()
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2,ensure_ascii=False))


if __name__=="__main__":
    main()
