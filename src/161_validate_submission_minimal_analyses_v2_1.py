from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path


def load_numbered_module(filename: str, name: str):
    path = Path(__file__).with_name(filename)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {filename}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    alignment = load_numbered_module(
        "159_audit_semantic_alignment_v2_1.py", "alignment_submission_validation"
    )
    exploratory = load_numbered_module(
        "160_evaluate_submission_exploratory_v2_1.py",
        "exploratory_submission_validation",
    )

    alignment.self_test()
    exploratory.self_test()

    report = {
        "analysis": "Validation of minimal-submission analysis code",
        "status": "passed",
        "real_clinical_data_read": False,
        "real_outcome_performance_computed": False,
        "validated_modules": [
            "src/159_audit_semantic_alignment_v2_1.py",
            "src/160_evaluate_submission_exploratory_v2_1.py",
        ],
        "checks": [
            "between-patient semantic permutation self-test",
            "association summary self-test",
            "comparator-level reconstruction self-test",
        ],
    }
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
