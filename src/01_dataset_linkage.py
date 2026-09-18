from __future__ import annotations

import argparse
from itertools import combinations
from pathlib import Path

import pandas as pd

from common import (
    MODULE_DIRS, aggregate_subject_ids, choose_anchor_with_column, find_file,
    module_path, resolve_root, safe_write_csv,
)

ANCHORS = {
    "mimiciii": ["PATIENTS.csv.gz", "PATIENTS.csv", "patients.csv.gz", "patients.csv"],
    "mimiciv": ["patients.csv.gz", "patients.csv"],
    "mimic_iv_note": ["discharge.csv.gz", "discharge.csv"],
    "mimic_iv_ed": ["edstays.csv.gz", "edstays.csv"],
    "mimic_iv_ecg": ["record_list.csv.gz", "record_list.csv"],
    "mimic_iv_echo": ["echo_measurements.csv.gz", "echo_measurements.csv", "record_list.csv.gz", "record_list.csv"],
    "mimic_cxr": ["mimic-cxr-2.0.0-metadata.csv.gz", "mimic-cxr-2.0.0-metadata.csv", "metadata.csv.gz", "metadata.csv"],
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    root = resolve_root(args.root)
    out = Path(args.output)
    sets: dict[str, set[int]] = {}
    detail = []

    for key in MODULE_DIRS:
        base = module_path(root, key)
        anchor = find_file(base, ANCHORS.get(key, []))
        if anchor is None:
            anchor = choose_anchor_with_column(base, "subject_id")
        if anchor is None:
            detail.append({"module": key, "anchor_found": False, "anchor_file": "", "unique_subjects": 0})
            continue
        ids = aggregate_subject_ids(anchor)
        sets[key] = ids
        detail.append({
            "module": key,
            "anchor_found": True,
            "anchor_file": str(anchor.relative_to(root)),
            "unique_subjects": len(ids),
        })

    safe_write_csv(pd.DataFrame(detail), out / "linkage_details.csv")

    matrix = []
    for a, b in combinations(sorted(sets), 2):
        inter = len(sets[a] & sets[b])
        union = len(sets[a] | sets[b])
        matrix.append({
            "module_a": a,
            "module_b": b,
            "subjects_a": len(sets[a]),
            "subjects_b": len(sets[b]),
            "intersection_subjects": inter,
            "pct_a_linked_to_b": round(100 * inter / len(sets[a]), 3) if sets[a] else 0.0,
            "pct_b_linked_to_a": round(100 * inter / len(sets[b]), 3) if sets[b] else 0.0,
            "jaccard": round(inter / union, 6) if union else 0.0,
        })

    safe_write_csv(pd.DataFrame(matrix), out / "linkage_matrix.csv")


if __name__ == "__main__":
    main()
