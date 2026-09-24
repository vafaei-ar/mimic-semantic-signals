from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from runrelay_progress import update_progress


OUTCOMES = ("invasive_ventilation", "renal_replacement_therapy", "icu_death")
REPEAT_SEEDS = (20260924, 20260925, 20260926, 20260927, 20260928)
FOLDS = 5


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def expected_split_frame(df: pd.DataFrame, outcome: str) -> pd.DataFrame:
    from sklearn.model_selection import StratifiedGroupKFold

    y = df["label"].astype(int).to_numpy()
    groups = df["subject_id"].to_numpy()
    out = df[["case_id", "subject_id"]].copy()

    for ri, seed in enumerate(REPEAT_SEEDS, start=1):
        assignment = pd.Series(-1, index=df.index, dtype="int64")
        cv = StratifiedGroupKFold(
            n_splits=FOLDS,
            shuffle=True,
            random_state=int(seed),
        )
        for fold, (_, te) in enumerate(cv.split(df, y, groups=groups), start=1):
            assignment.iloc[te] = fold

        if (assignment < 1).any():
            raise RuntimeError(f"{outcome}: incomplete fold assignment in repeat {ri}")

        check = pd.DataFrame(
            {
                "subject_id": df["subject_id"].to_numpy(),
                "fold": assignment.to_numpy(),
            }
        )
        if (check.groupby("subject_id")["fold"].nunique() > 1).any():
            raise RuntimeError(
                f"{outcome}: patient appears in multiple folds within repeat {ri}"
            )

        out[f"repeat_{ri}_fold"] = assignment.to_numpy()

    return out


def validate_existing(existing: pd.DataFrame, expected: pd.DataFrame, outcome: str) -> None:
    if list(existing.columns) != list(expected.columns):
        raise RuntimeError(
            f"{outcome}: existing split columns differ from deterministic freeze"
        )
    if len(existing) != len(expected):
        raise RuntimeError(
            f"{outcome}: existing split row count {len(existing)} != expected {len(expected)}"
        )

    left = existing.sort_values("case_id").reset_index(drop=True)
    right = expected.sort_values("case_id").reset_index(drop=True)

    if not left.equals(right):
        raise RuntimeError(
            f"{outcome}: existing split file differs from deterministic v2.1 assignment; refusing overwrite"
        )


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Freeze exact repeated patient-grouped CV assignments for corrected adult v2.1 cohorts."
    )
    ap.add_argument("--base", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    base = Path(args.base).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    report = {
        "analysis": "Corrected adult v2.1 patient-grouped CV split freeze",
        "protocol": "docs/enhanced_structured_baseline_evaluation_addendum_v2_1.md",
        "local_only": True,
        "contains_patient_identifiers": False,
        "contains_row_level_data": False,
        "predictive_model_fitted": False,
        "repeat_seeds": [int(x) for x in REPEAT_SEEDS],
        "folds_per_repeat": FOLDS,
        "group": "source_patient",
        "outcomes": {},
    }

    for oi, outcome in enumerate(OUTCOMES, start=1):
        update_progress(
            current=oi,
            total=len(OUTCOMES),
            phase="freeze_v2_1_cv_splits",
            message=f"{outcome}: generating deterministic patient-grouped split assignment",
            unit="outcome",
        )

        feature_path = base / outcome / "enhanced_structured_features_v2_1_local.csv"
        df = pd.read_csv(feature_path, low_memory=False)

        required = {"case_id", "subject_id", "label"}
        missing = required - set(df.columns)
        if missing:
            raise RuntimeError(
                f"{outcome}: missing required feature columns {sorted(missing)}"
            )
        if df["case_id"].duplicated().any():
            raise RuntimeError(f"{outcome}: duplicate case_id in feature file")

        expected = expected_split_frame(df, outcome)
        split_path = base / outcome / "enhanced_structured_cv_splits_v2_1_local.csv"

        if split_path.exists():
            existing = pd.read_csv(split_path, low_memory=False)
            validate_existing(existing, expected, outcome)
            status = "reused_identical_existing"
        else:
            expected.to_csv(split_path, index=False)
            status = "created"

        file_hash = sha256_file(split_path)

        fold_counts = {}
        case_counts = {}
        for ri in range(1, len(REPEAT_SEEDS) + 1):
            col = f"repeat_{ri}_fold"
            fold_counts[col] = {
                str(int(k)): int(v)
                for k, v in expected[col].value_counts().sort_index().to_dict().items()
            }
            case_counts[col] = {
                str(fold): int(
                    df.loc[expected[col].eq(fold).to_numpy(), "label"].astype(int).sum()
                )
                for fold in range(1, FOLDS + 1)
            }

        report["outcomes"][outcome] = {
            "rows": int(len(df)),
            "cases": int(df["label"].astype(int).sum()),
            "controls": int(len(df) - df["label"].astype(int).sum()),
            "unique_patients": int(df["subject_id"].nunique()),
            "split_status": status,
            "split_sha256": file_hash,
            "fold_row_counts": fold_counts,
            "fold_case_counts": case_counts,
            "local_split_file": str(split_path),
        }

    report["guardrails"] = [
        "No predictive model was fit or scored.",
        "Split files are local protected row-level analysis files.",
        "Existing split files are never overwritten unless the deterministic assignment is identical.",
        "The aggregate artifact contains hashes/counts only.",
    ]

    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
