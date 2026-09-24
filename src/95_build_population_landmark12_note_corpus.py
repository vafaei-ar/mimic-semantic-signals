from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

OUTCOMES=("invasive_ventilation","renal_replacement_therapy","icu_death")


def qstats(values):
    x=np.asarray(list(values),dtype=float)
    if x.size==0:
        return {"n":0}
    return {
        "n":int(x.size),
        "p05":float(np.quantile(x,.05)),
        "p25":float(np.quantile(x,.25)),
        "median":float(np.quantile(x,.50)),
        "p75":float(np.quantile(x,.75)),
        "p95":float(np.quantile(x,.95)),
        "max":float(np.max(x)),
    }


def note_id(text: str) -> str:
    return "plnote_"+hashlib.sha256(text.encode("utf-8")).hexdigest()[:24]


def main():
    ap=argparse.ArgumentParser(description="Build deduplicated population landmark note corpus without reading labels.")
    ap.add_argument("--base",required=True)
    ap.add_argument("--local-output",required=True)
    ap.add_argument("--manifest",required=True)
    args=ap.parse_args()

    base=Path(args.base).expanduser().resolve()
    local=Path(args.local_output).expanduser().resolve()
    manifest=Path(args.manifest).expanduser().resolve()
    local.mkdir(parents=True,exist_ok=True)
    manifest.parent.mkdir(parents=True,exist_ok=True)

    unique={}
    mapping=[]
    per_outcome={}
    memberships=defaultdict(set)
    chars=[]
    row_count=0

    for outcome in OUTCOMES:
        path=base/outcome/"cases.jsonl"
        n=0
        with path.open("r",encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                rec=json.loads(line)
                text=rec.get("model_state",{}).get("clinical_note")
                if not isinstance(text,str) or not text.strip():
                    raise RuntimeError(f"{outcome}: blank note in frozen note-available corpus")
                cid=str(rec.get("case_id"))
                if not cid or cid=="None":
                    raise RuntimeError(f"{outcome}: missing case_id")
                nid=note_id(text)
                if nid in unique and unique[nid]!=text:
                    raise RuntimeError("Unexpected note hash collision")
                unique[nid]=text
                memberships[nid].add(outcome)
                mapping.append({"outcome":outcome,"case_id":cid,"note_case_id":nid})
                chars.append(len(text))
                n+=1
                row_count+=1
        per_outcome[outcome]=n

    corpus_path=local/"cases.jsonl"
    map_path=local/"case_to_note_mapping.jsonl"

    with corpus_path.open("w",encoding="utf-8") as f:
        for nid,text in sorted(unique.items()):
            rec={
                "case_id":nid,
                "synthetic_only":False,
                "local_only":True,
                "model_state":{"clinical_note":text},
                "metadata":{
                    "analysis":"population_landmark12_unique_note_corpus_v1",
                    "source_outcomes":sorted(memberships[nid]),
                    "note_characters":len(text),
                },
                "questions":[
                    "overall_clinician_concern",
                    "worsening_trajectory",
                    "respiratory_concern",
                    "hemodynamic_concern",
                    "poor_treatment_response",
                    "escalation_considered",
                    "diagnostic_uncertainty",
                    "reassuring_stability",
                ],
                "gold":None,
            }
            f.write(json.dumps(rec,ensure_ascii=False)+"\n")

    with map_path.open("w",encoding="utf-8") as f:
        for rec in mapping:
            f.write(json.dumps(rec)+"\n")

    overlap=Counter(len(v) for v in memberships.values())
    combo=Counter("+".join(sorted(v)) for v in memberships.values())
    report={
        "analysis":"Population landmark 12h deduplicated narrative workload audit v1",
        "local_only":True,
        "labels_read_or_used":False,
        "contains_note_text":False,
        "contains_source_patient_identifiers":False,
        "total_outcome_note_rows":int(row_count),
        "unique_exact_note_texts":int(len(unique)),
        "deduplication_fraction":float(1-len(unique)/row_count) if row_count else None,
        "note_rows_by_outcome":per_outcome,
        "unique_notes_by_number_of_outcomes":{
            str(k):int(v) for k,v in sorted(overlap.items())
        },
        "unique_note_outcome_membership_combinations":dict(sorted(combo.items())),
        "note_character_count_across_outcome_rows":qstats(chars),
        "local_unique_corpus":str(corpus_path),
        "local_mapping":str(map_path),
        "guardrail":"Exact-text deduplication only. No outcome labels are read or used. Note text and case mappings remain local."
    }
    manifest.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))


if __name__=="__main__":
    main()
