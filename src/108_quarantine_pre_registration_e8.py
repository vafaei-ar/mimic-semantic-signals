from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


CANDIDATES = (
    "data/real_mimic_local/population_landmark12_v2/invasive_ventilation/enhanced_structured_predictions_v2_local.csv",
    "data/real_mimic_local/population_landmark12_v2/invasive_ventilation/enhanced_structured_cv_splits_v2_local.csv",
    "data/real_mimic_local/population_landmark12_v2/renal_replacement_therapy/enhanced_structured_predictions_v2_local.csv",
    "data/real_mimic_local/population_landmark12_v2/renal_replacement_therapy/enhanced_structured_cv_splits_v2_local.csv",
    "data/real_mimic_local/population_landmark12_v2/icu_death/enhanced_structured_predictions_v2_local.csv",
    "data/real_mimic_local/population_landmark12_v2/icu_death/enhanced_structured_cv_splits_v2_local.csv",
    "outputs/multitask_benchmark/enhanced_structured_baseline_evaluation_v2.json",
)


def main() -> None:
    ap = argparse.ArgumentParser(description="Quarantine any partial pre-registration E8 outputs without deleting them.")
    ap.add_argument("--report", required=True)
    ap.add_argument("--quarantine-root", default="data/real_mimic_local/quarantine/pre_registration_e8")
    args = ap.parse_args()

    root = Path.cwd().resolve()
    qroot = (root / args.quarantine_root).resolve()
    qroot.mkdir(parents=True, exist_ok=True)

    moved = []
    absent = []
    for rel in CANDIDATES:
        src = root / rel
        if not src.exists():
            absent.append(rel)
            continue
        dest = qroot / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            raise RuntimeError(f"Quarantine destination already exists: {dest}")
        shutil.move(str(src), str(dest))
        moved.append({"source": rel, "quarantined_to": str(dest.relative_to(root))})

    report = {
        "analysis": "Pre-registration quarantine of E8R7Q5M3 partial local outputs",
        "source_job": "E8R7Q5M3",
        "source_job_status": "failed_timeout_no_declared_artifact",
        "moved": moved,
        "already_absent": absent,
        "deleted": False,
        "contains_performance_metrics": False,
        "guardrail": "Quarantined files are not manuscript-facing and must not be opened for scientific interpretation.",
    }
    out = Path(args.report)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
