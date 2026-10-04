from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd


BASE = Path("data/real_mimic_local/population_landmark12_v2_1")
OUTCOME_SPECS = {
    "ventilation": {
        "outcome_dir": "invasive_ventilation",
        "report": "outputs/multitask_benchmark/h1_openjev_v2_1_ventilation.json",
        "pred": "h1_openjev_predictions_v2_1_local.csv",
    },
    "rrt": {
        "outcome_dir": "renal_replacement_therapy",
        "report": "outputs/multitask_benchmark/h2_openjev_v2_1_rrt.json",
        "pred": "h2_openjev_predictions_v2_1_local.csv",
    },
    "death_metavision": {
        "outcome_dir": "icu_death",
        "report": "outputs/multitask_benchmark/h3_openjev_v2_1_death.json",
        "pred": "h3_openjev_predictions_v2_1_local.csv",
    },
}
METRIC_KEYS = (
    "auroc",
    "auprc",
    "brier",
    "log_loss",
    "calibration_in_the_large",
    "joint_recalibration_intercept",
    "calibration_slope",
    "ece_10_equal_width_bins",
    "ece_10_quantile_bins",
)


def load_numbered_module(filename: str, name: str):
    path = Path(__file__).with_name(filename)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {filename}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


rich = load_numbered_module("117_evaluate_rich_comparator_v2_1.py", "rich_submission_review")
basic_metrics = rich.legacy_metrics.basic_metrics


def subset_metrics(y: np.ndarray, pb: np.ndarray, pa: np.ndarray) -> dict:
    mb = basic_metrics(y, pb)
    ma = basic_metrics(y, pa)
    return {
        "comparator": {k: float(mb[k]) for k in METRIC_KEYS},
        "augmented": {k: float(ma[k]) for k in METRIC_KEYS},
        "delta": {k: float(ma[k]) - float(mb[k]) for k in METRIC_KEYS},
    }


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Create an aggregate Paper 1 review-response summary from already-completed "
            "registered H1-H3 outputs and frozen local OOF predictions. No model fitting."
        )
    )
    ap.add_argument(
        "--output",
        default="outputs/multitask_benchmark/submission_review_metrics_v2_1.json",
    )
    args = ap.parse_args()

    root = Path(".").resolve()
    out = {
        "analysis": "Paper 1 registered secondary metrics plus note-available exploratory subgroup",
        "status": "completed",
        "registration_id": "ahxn9",
        "registered_secondary_metrics_source": (
            "Already-completed H1-H3 aggregate reports. No refitting or new bootstrap."
        ),
        "note_available_subgroup_status": "post-registration exploratory",
        "note_available_subgroup_method": (
            "Restrict the already-frozen full-cohort out-of-fold predictions to rows with "
            "has_note=1. Models are not refit within the subgroup. Five frozen partitions are reported."
        ),
        "outcomes": {},
        "guardrails": [
            "No raw note text or row-level predictions are shared.",
            "No model is fit by this task.",
            "Registered secondary metrics are copied from the canonical H1-H3 aggregate reports.",
            "The note-available subgroup uses the original full-cohort OOF predictions and is explicitly exploratory.",
            "Positive outcome orientation is unchanged (label=1 is the registered event); no AUROC is post-hoc inverted.",
        ],
    }

    for key, spec in OUTCOME_SPECS.items():
        report_path = root / spec["report"]
        outcome_dir = root / BASE / spec["outcome_dir"]
        pred_path = outcome_dir / spec["pred"]
        context_path = outcome_dir / "preregistration_context_features_v2_1_local.csv"

        if not report_path.exists():
            raise RuntimeError(f"Missing canonical aggregate report: {report_path}")
        if not pred_path.exists():
            raise RuntimeError(f"Missing frozen local OOF predictions: {pred_path}")
        if not context_path.exists():
            raise RuntimeError(f"Missing context file: {context_path}")

        report = json.loads(report_path.read_text(encoding="utf-8"))
        pred = pd.read_csv(pred_path, low_memory=False)
        ctx = pd.read_csv(context_path, usecols=["case_id", "has_note"], low_memory=False)

        pred["case_id"] = pred["case_id"].astype(str)
        ctx["case_id"] = ctx["case_id"].astype(str)
        if ctx["case_id"].duplicated().any():
            raise RuntimeError(f"Duplicate case_id in context for {key}")
        merged = pred.merge(ctx, on="case_id", how="left", validate="one_to_one")
        if merged["has_note"].isna().any():
            raise RuntimeError(f"Missing has_note after merge for {key}")

        note = merged[pd.to_numeric(merged["has_note"], errors="raise").astype(int).eq(1)].copy()
        expected_note_n = int(report["note_available_rows_with_complete_openjev"])
        if len(note) != expected_note_n:
            raise RuntimeError(f"Note-available row mismatch for {key}: {len(note)} != {expected_note_n}")

        y = pd.to_numeric(note["label"], errors="raise").astype(int).to_numpy()
        if y.sum() == 0 or y.sum() == len(y):
            raise RuntimeError(f"Degenerate note-available outcome for {key}")

        primary = report["primary_repeat"]
        secondary = {
            "primary_repeat": {
                "comparator": {k: float(primary["comparator"][k]) for k in METRIC_KEYS},
                "augmented": {k: float(primary["augmented"][k]) for k in METRIC_KEYS},
                "delta": {k: float(primary["delta"][k]) for k in METRIC_KEYS},
            },
            "refit_bootstrap_delta": {
                "brier": report["primary_refit_bootstrap"]["secondary_delta_summaries"]["delta_brier"],
                "log_loss": report["primary_refit_bootstrap"]["secondary_delta_summaries"]["delta_log_loss"],
                "auprc": report["primary_refit_bootstrap"]["secondary_delta_summaries"]["delta_auprc"],
            },
            "decision_curve": report["decision_curve"],
        }

        note_repeats = []
        for ri in range(1, 6):
            bcol = f"comparator_repeat_{ri}"
            acol = f"augmented_openjev_repeat_{ri}"
            for col in (bcol, acol):
                if col not in note.columns:
                    raise RuntimeError(f"Missing prediction column {col} for {key}")
            pb = pd.to_numeric(note[bcol], errors="raise").to_numpy(dtype=float)
            pa = pd.to_numeric(note[acol], errors="raise").to_numpy(dtype=float)
            if not np.isfinite(pb).all() or not np.isfinite(pa).all():
                raise RuntimeError(f"Non-finite note-available predictions for {key}, repeat {ri}")
            note_repeats.append({
                "repeat": ri,
                **subset_metrics(y, pb, pa),
            })

        out["outcomes"][key] = {
            "n_full": int(report["n"]),
            "cases_full": int(report["cases"]),
            "n_note_available": int(len(note)),
            "cases_note_available": int(y.sum()),
            "registered_secondary_metrics": secondary,
            "note_available_frozen_prediction_subgroup": {
                "primary_repeat": note_repeats[0],
                "all_five_repeats": note_repeats,
                "delta_auroc_all_five": [float(x["delta"]["auroc"]) for x in note_repeats],
            },
        }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
