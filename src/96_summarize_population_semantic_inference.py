from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import numpy as np

SEMANTIC_NAMES=[
    "overall_clinician_concern","worsening_trajectory","respiratory_concern",
    "hemodynamic_concern","poor_treatment_response","escalation_considered",
    "diagnostic_uncertainty","reassuring_stability",
]


def qstats(values):
    x=np.asarray(list(values),dtype=float)
    if x.size==0:
        return {"n":0}
    return {
        "n":int(x.size),
        "p05":float(np.quantile(x,.05)),
        "median":float(np.quantile(x,.50)),
        "p95":float(np.quantile(x,.95)),
        "max":float(np.max(x)),
    }


def main():
    ap=argparse.ArgumentParser(description="Aggregate safe report for population semantic inference.")
    ap.add_argument("--raw",required=True)
    ap.add_argument("--expected",type=int,required=True)
    ap.add_argument("--model",required=True)
    ap.add_argument("--output",required=True)
    args=ap.parse_args()

    raw=Path(args.raw).expanduser().resolve()
    out=Path(args.output).expanduser().resolve()
    out.parent.mkdir(parents=True,exist_ok=True)

    completed=0
    failed=0
    error_types=Counter()
    note_tokens=[]
    chunks=[]
    scores={k:[] for k in SEMANTIC_NAMES}
    seen=set()

    with raw.open("r",encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec=json.loads(line)
            cid=str(rec.get("case_id"))
            if not cid or cid=="None" or cid in seen:
                raise RuntimeError("Missing or duplicate semantic inference case_id")
            seen.add(cid)
            if rec.get("status")!="ok":
                failed+=1
                error_types[str(rec.get("error","unknown")).split(":",1)[0]]+=1
                continue
            completed+=1
            meta=rec.get("metadata",{})
            if isinstance(meta.get("note_tokens"),(int,float)):
                note_tokens.append(float(meta["note_tokens"]))
            if isinstance(meta.get("chunks_evaluated"),(int,float)):
                chunks.append(float(meta["chunks_evaluated"]))
            ans=rec.get("response",{}).get("answers",{})
            for name in SEMANTIC_NAMES:
                item=ans.get(name,{})
                p=item.get("noul") if isinstance(item,dict) else None
                if not isinstance(p,(int,float)):
                    raise RuntimeError(f"Missing semantic score for {name}")
                scores[name].append(float(p))

    report={
        "analysis":"Population landmark semantic inference aggregate report v1",
        "model":args.model,
        "local_only":True,
        "labels_read_or_used":False,
        "contains_note_text":False,
        "contains_case_ids":False,
        "contains_patient_level_scores":False,
        "expected_unique_notes":int(args.expected),
        "completed":int(completed),
        "failed":int(failed),
        "error_type_counts":dict(error_types),
        "note_token_count":qstats(note_tokens),
        "chunks_evaluated":qstats(chunks),
        "per_construct_score_summary":{
            k:{
                **qstats(v),
                "mean":float(np.mean(v)) if v else None,
                "std":float(np.std(v)) if v else None,
                "intermediate_fraction":float(np.mean((np.asarray(v)>0)&(np.asarray(v)<1))) if v else None,
            }
            for k,v in scores.items()
        },
        "guardrail":"Aggregate completion and score-resolution diagnostics only. No outcome labels were read or used during semantic inference."
    }
    out.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))

    if completed!=args.expected or failed!=0 or len(seen)!=args.expected:
        raise RuntimeError(
            f"Inference completeness failure: expected={args.expected}, completed={completed}, failed={failed}, seen={len(seen)}"
        )


if __name__=="__main__":
    main()
