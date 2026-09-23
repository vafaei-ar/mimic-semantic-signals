from __future__ import annotations

import argparse
import json
from pathlib import Path

OUTCOMES = [
    "invasive_ventilation",
    "renal_replacement_therapy",
    "icu_death",
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-root", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    root = Path(args.input_root).expanduser().resolve()
    results = {}
    for outcome in OUTCOMES:
        p = root / outcome / "report.json"
        report = json.loads(p.read_text(encoding="utf-8"))
        models = {x["model"]: x for x in report["models"]}
        boot = report["matched_set_bootstrap_auroc_differences"]
        results[outcome] = {
            "n": report["n"],
            "cases": report["cases"],
            "controls": report["controls"],
            "tfidf": report["tfidf"],
            "models": {
                k: models[k]
                for k in [
                    "physiology_only",
                    "lexical_only",
                    "physiology_plus_lexical",
                    "physiology_plus_openjev",
                    "physiology_plus_laya",
                    "physiology_plus_lexical_plus_openjev",
                    "physiology_plus_lexical_plus_laya",
                ]
            },
            "matched_set_bootstrap_auroc_differences": {
                k: boot[k]
                for k in [
                    "physiology_plus_lexical_minus_physiology_only",
                    "physiology_plus_openjev_minus_physiology_only",
                    "physiology_plus_laya_minus_physiology_only",
                    "physiology_plus_lexical_plus_openjev_minus_physiology_plus_lexical",
                    "physiology_plus_lexical_plus_laya_minus_physiology_plus_lexical",
                ]
            },
        }

    out = {
        "analysis": "Cross-outcome fold-fitted TF-IDF lexical robustness on frozen multitask benchmark v1",
        "protocol": "docs/multitask_benchmark_protocol_v1.md",
        "fit_scope": "TF-IDF vocabulary fitted within each training fold only",
        "local_only": True,
        "contains_note_text": False,
        "contains_source_patient_identifiers": False,
        "patient_level_predictions_shared": False,
        "outcomes": results,
        "interpretation_guardrail": (
            "This tests whether the compact zero-shot semantic scores retain AUROC increment after "
            "a simple fold-fitted bag-of-words/bigram representation of the same note is included. "
            "It does not establish clinical utility or causal meaning."
        ),
    }
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
