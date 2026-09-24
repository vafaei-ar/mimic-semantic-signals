from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path


def load_notes(path: Path) -> list[str]:
    notes=[]
    with path.open("r",encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec=json.loads(line)
            note=rec.get("model_state",{}).get("clinical_note")
            if not isinstance(note,str) or not note.strip():
                raise RuntimeError("Blank or missing clinical_note in frozen Zigong cohort.")
            notes.append(note)
    if not notes:
        raise RuntimeError("No notes found.")
    return notes


def is_cjk(ch: str) -> bool:
    x=ord(ch)
    return (
        0x3400 <= x <= 0x4DBF
        or 0x4E00 <= x <= 0x9FFF
        or 0xF900 <= x <= 0xFAFF
        or 0x20000 <= x <= 0x2FA1F
    )


def quantiles(values):
    vals=sorted(float(x) for x in values)
    if not vals:
        return {"n":0}
    def q(p):
        if len(vals)==1:
            return vals[0]
        pos=(len(vals)-1)*p
        lo=int(math.floor(pos)); hi=int(math.ceil(pos))
        if lo==hi:
            return vals[lo]
        return vals[lo]*(hi-pos)+vals[hi]*(pos-lo)
    return {
        "n":len(vals),
        "p05":q(0.05),
        "p25":q(0.25),
        "median":q(0.5),
        "p75":q(0.75),
        "p95":q(0.95),
        "max":vals[-1],
    }


def audit_tokenizer(name, tokenizer, notes, context_hint=None):
    note_token_counts=[]
    unk_counts=[]
    note_has_unk=0
    decoded_cjk_ratios=[]
    total_tokens=0
    total_unk=0
    unk_id=getattr(tokenizer,"unk_token_id",None)

    for note in notes:
        enc=tokenizer(note,add_special_tokens=False)
        ids=enc["input_ids"]
        if ids and isinstance(ids[0],list):
            ids=ids[0]
        ids=list(ids)
        n=len(ids)
        note_token_counts.append(n)
        total_tokens += n

        if unk_id is not None:
            u=sum(int(x)==int(unk_id) for x in ids)
        else:
            u=0
        unk_counts.append(u)
        total_unk += u
        if u:
            note_has_unk += 1

        try:
            dec=tokenizer.decode(ids,skip_special_tokens=True)
            orig_cjk=sum(is_cjk(ch) for ch in note)
            dec_cjk=sum(is_cjk(ch) for ch in dec)
            decoded_cjk_ratios.append(dec_cjk/orig_cjk if orig_cjk else 1.0)
        except Exception:
            pass

    model_max=getattr(tokenizer,"model_max_length",None)
    if isinstance(model_max,(int,float)) and model_max < 10**8:
        tokenizer_limit=int(model_max)
    else:
        tokenizer_limit=None

    limit=context_hint or tokenizer_limit
    report={
        "tokenizer_class":type(tokenizer).__name__,
        "vocab_size":int(getattr(tokenizer,"vocab_size",0) or 0),
        "unk_token":str(getattr(tokenizer,"unk_token",None)),
        "unk_token_id":int(unk_id) if unk_id is not None else None,
        "tokenizer_model_max_length":tokenizer_limit,
        "context_limit_used_for_pressure":int(limit) if limit else None,
        "note_token_count":quantiles(note_token_counts),
        "overall_unknown_token_fraction":float(total_unk/total_tokens) if total_tokens else None,
        "notes_with_any_unknown_token":int(note_has_unk),
        "fraction_notes_with_any_unknown_token":float(note_has_unk/len(notes)),
        "unknown_tokens_per_note":quantiles(unk_counts),
        "decoded_to_original_cjk_count_ratio":quantiles(decoded_cjk_ratios),
    }
    if limit:
        report["notes_exceeding_context_limit"]=int(sum(n>limit for n in note_token_counts))
        report["fraction_notes_exceeding_context_limit"]=float(sum(n>limit for n in note_token_counts)/len(note_token_counts))
    return report


def main():
    ap=argparse.ArgumentParser(description="Aggregate language/tokenizer applicability audit for frozen Zigong notes.")
    ap.add_argument("--cases",required=True)
    ap.add_argument("--laya-dir",required=True)
    ap.add_argument("--diffusiongemma-dir",required=True)
    ap.add_argument("--output",required=True)
    args=ap.parse_args()

    from transformers import AutoTokenizer

    cases=Path(args.cases).expanduser().resolve()
    notes=load_notes(cases)
    char_counts=[len(x) for x in notes]
    cjk_counts=[sum(is_cjk(ch) for ch in x) for x in notes]
    nonspace_counts=[sum(not ch.isspace() for ch in x) for x in notes]

    report={
        "analysis":"Frozen Zigong cohort language/tokenizer applicability audit v1",
        "local_only":True,
        "labels_read_or_used":False,
        "model_inference_performed":False,
        "contains_note_text":False,
        "contains_patient_identifiers":False,
        "notes":len(notes),
        "language_profile":{
            "character_count":quantiles(char_counts),
            "cjk_character_count":quantiles(cjk_counts),
            "overall_cjk_fraction_of_nonspace_characters":float(sum(cjk_counts)/sum(nonspace_counts)) if sum(nonspace_counts) else 0.0,
            "notes_with_any_cjk":int(sum(c>0 for c in cjk_counts)),
        },
        "tokenizers":{},
        "load_errors":{},
    }

    specs=[
        ("open_jev","com-kotobalabs/open-jev-deberta-v3-large",None),
        ("laya",str(Path(args.laya_dir).expanduser().resolve()),None),
        ("diffusiongemma",str(Path(args.diffusiongemma_dir).expanduser().resolve()),2048),
    ]
    for name,path,hint in specs:
        try:
            tok=AutoTokenizer.from_pretrained(path,local_files_only=True)
            report["tokenizers"][name]=audit_tokenizer(name,tok,notes,context_hint=hint)
        except Exception as exc:
            report["load_errors"][name]={
                "error_type":type(exc).__name__,
                "error_message":str(exc)[:1000],
            }

    report["guardrail"]=(
        "This audit ignores outcome labels and performs no model inference. "
        "Tokenizer coverage does not establish semantic validity. Any translation or preprocessing rule must be frozen before Zigong performance is inspected."
    )
    out=Path(args.output).expanduser().resolve()
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2,ensure_ascii=False))


if __name__=="__main__":
    main()
