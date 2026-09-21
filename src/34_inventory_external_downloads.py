from __future__ import annotations

import argparse
import json
from pathlib import Path


DATASETS = {
    "zigong": {
        "patterns": ["DataTables.zip", "dtNursingChart.csv"],
    },
    "eicu": {
        "patterns": ["patient.csv.gz", "patient.csv", "medication.csv.gz", "infusionDrug.csv.gz"],
    },
    "nwicu": {
        "patterns": ["admissions.csv.gz", "icustays.csv.gz", "chartevents.csv.gz", "emar.csv.gz"],
    },
    "mimic_br": {
        "patterns": ["person.csv", "visit_occurrence.csv", "drug_exposure.csv", "measurement.csv"],
    },
    "hirid": {
        "patterns": ["general_table.csv", "observation_tables", "pharma_records"],
    },
    "sicdb": {
        "patterns": ["cases.csv", "medication.csv", "data_float_h.csv"],
    },
    "amsterdamumcdb": {
        "patterns": ["person", "visit_occurrence", "measurement", "drug_exposure"],
    },
}


def summarize_tree(root: Path) -> dict:
    files = [p for p in root.rglob("*") if p.is_file()]
    total = sum(p.stat().st_size for p in files)
    largest = sorted(files, key=lambda p: p.stat().st_size, reverse=True)[:20]
    return {
        "exists": root.exists(),
        "files": len(files),
        "bytes": int(total),
        "gb": round(total / (1024 ** 3), 3),
        "largest_files": [
            {
                "path": str(p.relative_to(root)),
                "bytes": int(p.stat().st_size),
            }
            for p in largest
        ],
    }


def find_patterns(root: Path, patterns: list[str]) -> dict:
    out = {}
    for pattern in patterns:
        if "." in pattern:
            matches = list(root.rglob(pattern))
        else:
            matches = [p for p in root.rglob("*") if pattern.lower() in p.name.lower()]
        out[pattern] = len(matches)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Inventory locally downloaded external ICU datasets without reading patient data."
    )
    ap.add_argument(
        "--base",
        default="~/datasets/external_icu",
        help="Base directory containing external ICU datasets.",
    )
    ap.add_argument(
        "--zigong-root",
        default="~/datasets/zigong",
        help="Zigong root, which may be outside --base.",
    )
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    base = Path(args.base).expanduser().resolve()
    zigong = Path(args.zigong_root).expanduser().resolve()
    out = Path(args.output).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    roots = {
        "zigong": zigong,
        "eicu": base / "eicu",
        "nwicu": base / "nwicu",
        "mimic_br": base / "mimic_br",
        "hirid": base / "hirid",
        "sicdb": base / "sicdb",
        "amsterdamumcdb": base / "amsterdamumcdb",
    }

    report = {
        "contains_patient_data": False,
        "reads_file_contents": False,
        "datasets": {},
    }

    for name, root in roots.items():
        if not root.exists():
            report["datasets"][name] = {
                "root": str(root),
                "exists": False,
                "files": 0,
                "bytes": 0,
                "gb": 0.0,
                "expected_pattern_counts": {},
            }
            continue
        s = summarize_tree(root)
        s["root"] = str(root)
        s["expected_pattern_counts"] = find_patterns(
            root, DATASETS[name]["patterns"]
        )
        report["datasets"][name] = s

    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
