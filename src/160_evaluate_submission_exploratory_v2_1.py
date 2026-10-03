from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

from registration_gate import require_osf_registration
from runrelay_progress import update_progress


ANALYSIS_KEYS = ("ventilation", "rrt", "death_metavision")


def load_numbered_module(filename: str, name: str):
    path = Path(__file__).with_name(filename)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {filename}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


h7 = load_numbered_module(
    "155_evaluate_h7_patient_shuffled_openjev_v2_1.py", "h7_submission"
)
h1 = h7.h1
rich = h7.rich


def semantic_only_crossfit(
    sem_matrix: pd.DataFrame,
    y: np.ndarray,
    folds: np.ndarray,
    has_note: np.ndarray,
) -> dict:
    note_mask = np.asarray(has_note, dtype=int) == 1
    pred = np.full(len(y), np.nan, dtype=float)
    for fold in range(1, h1.FOLDS + 1):
        tr = np.flatnonzero(note_mask & (folds != fold))
        te = np.flatnonzero(note_mask & (folds == fold))
        if len(tr) == 0 or len(te) == 0:
            raise RuntimeError(f"Empty note-available train/test set for fold {fold}")
        if y[tr].sum() == 0 or y[tr].sum() == len(tr):
            raise RuntimeError(f"Degenerate note-available training labels in fold {fold}")
        model = rich.build_hgb(20260924)
        model.fit(sem_matrix.iloc[tr], y[tr])
        pred[te] = model.predict_proba(sem_matrix.iloc[te])[:, 1]
    if np.isnan(pred[note_mask]).any():
        raise RuntimeError("Incomplete semantic-only note-available OOF predictions")
    metrics = rich.legacy_metrics.basic_metrics(y[note_mask], pred[note_mask])
    return {
        "n": int(note_mask.sum()),
        "cases": int(y[note_mask].sum()),
        "controls": int(note_mask.sum() - y[note_mask].sum()),
        **metrics,
    }


def comparator_levels(
    x_base: pd.DataFrame,
    outcome: str,
    context_freeze: dict,
) -> dict[str, list[str]]:
    cols = list(x_base.columns)
    if len(cols) < 34:
        raise RuntimeError("Rich comparator has fewer than 34 encoded structured features")
    level_a = cols[:34]

    treatment = [
        "treat_fio2_last_6h",
        "treat_oxygen_flow_last_6h",
        "treat_high_flow_any_6h",
        "treat_niv_any_6h",
        "treat_vasoactive_any",
        "treat_vasoactive_agent_count",
        "treat_sedative_any",
        "treat_sedative_agent_count",
    ]
    if outcome == "icu_death":
        treatment += [
            "code_status_available",
            "code_status_limitation",
            "code_status_comfort_or_no_cpr",
            "code_status_other",
        ]

    doc = list(context_freeze["documentation_behavior"]["features"])
    note_context = [
        "has_note",
        "note_age_at_landmark_hours",
        *[c for c in cols if c.startswith("note_category_")],
    ]

    for name in treatment + doc + note_context:
        if name not in cols:
            raise RuntimeError(f"Expected comparator feature missing: {name}")

    levels = {
        "A_structured_34": level_a,
        "B_plus_treatment_support": level_a + treatment,
        "C_plus_documentation_behavior": level_a + treatment + doc,
        "D_registered_rich_comparator": level_a + treatment + doc + note_context,
    }

    if set(levels["D_registered_rich_comparator"]) != set(cols):
        missing = sorted(set(cols) - set(levels["D_registered_rich_comparator"]))
        extra = sorted(set(levels["D_registered_rich_comparator"]) - set(cols))
        raise RuntimeError(
            f"Comparator decomposition does not reconstruct rich comparator: "
            f"missing={missing}, extra={extra}"
        )
    return levels


def self_test() -> None:
    cols = [f"s{i}" for i in range(34)] + [
        "treat_fio2_last_6h",
        "treat_oxygen_flow_last_6h",
        "treat_high_flow_any_6h",
        "treat_niv_any_6h",
        "treat_vasoactive_any",
        "treat_vasoactive_agent_count",
        "treat_sedative_any",
        "treat_sedative_agent_count",
        "doc_note_count_12h",
        "doc_note_chars_total_12h",
        "doc_note_chars_latest_12h",
        "doc_note_category_groups_12h",
        "doc_nursing_note_count_12h",
        "doc_physician_note_count_12h",
        "doc_respiratory_note_count_12h",
        "doc_other_note_count_12h",
        "has_note",
        "note_age_at_landmark_hours",
        "note_category_nursing",
        "note_category_physician",
        "note_category_respiratory",
        "note_category_other",
        "note_category_no_note",
    ]
    x = pd.DataFrame(columns=cols)
    freeze = {
        "documentation_behavior": {
            "features": [
                "doc_note_count_12h",
                "doc_note_chars_total_12h",
                "doc_note_chars_latest_12h",
                "doc_note_category_groups_12h",
                "doc_nursing_note_count_12h",
                "doc_physician_note_count_12h",
                "doc_respiratory_note_count_12h",
                "doc_other_note_count_12h",
            ]
        }
    }
    levels = comparator_levels(x, "invasive_ventilation", freeze)
    if len(levels["A_structured_34"]) != 34:
        raise RuntimeError("self-test failed: level A")
    if set(levels["D_registered_rich_comparator"]) != set(cols):
        raise RuntimeError("self-test failed: level D")
    print(json.dumps({"self_test": "passed"}))


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Post-registration Paper 1 exploratory semantic-only discrimination and "
            "four-level HGB comparator decomposition."
        )
    )
    ap.add_argument("--base")
    ap.add_argument("--split-manifest")
    ap.add_argument("--context-freeze")
    ap.add_argument("--analysis-populations")
    ap.add_argument("--preanalysis-clarifications")
    ap.add_argument("--output")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        self_test()
        return

    required = [
        args.base,
        args.split_manifest,
        args.context_freeze,
        args.analysis_populations,
        args.preanalysis_clarifications,
        args.output,
    ]
    if any(x is None for x in required):
        ap.error("all input paths and --output are required")

    require_osf_registration()

    context_freeze_path = Path(args.context_freeze).expanduser().resolve()
    context_freeze = json.loads(context_freeze_path.read_text(encoding="utf-8"))

    results = {}
    total_units = len(ANALYSIS_KEYS) * (5 + 4 * 5)
    unit = 0

    for analysis_key in ANALYSIS_KEYS:
        spec = h7.ANALYSES[analysis_key]
        local_args = SimpleNamespace(
            analysis=analysis_key,
            base=args.base,
            split_manifest=args.split_manifest,
            context_freeze=args.context_freeze,
            analysis_populations=args.analysis_populations,
            preanalysis_clarifications=args.preanalysis_clarifications,
        )
        d = h7.load_analysis_inputs(local_args, spec)
        levels = comparator_levels(d["x_base"], d["outcome"], context_freeze)

        semantic_repeats = []
        for ri, seed in enumerate(h1.REPEAT_SEEDS, start=1):
            folds = pd.to_numeric(
                d["frozen_splits"][f"repeat_{ri}_fold"], errors="raise"
            ).astype(int).to_numpy()
            metrics = semantic_only_crossfit(
                d["sem_matrix"], d["y"], folds, d["has_note"]
            )
            semantic_repeats.append(
                {"repeat": int(ri), "seed": int(seed), **metrics}
            )
            unit += 1
            update_progress(
                current=unit,
                total=total_units,
                phase="submission_semantic_only_and_decomposition",
                message=f"{analysis_key}: semantic-only repeat {ri}/5",
                unit="repeat",
            )

        decomposition = {}
        for level_name, level_cols in levels.items():
            level_repeats = []
            x_level = d["x_base"].loc[:, level_cols].copy()
            x_aug = pd.concat(
                [x_level.reset_index(drop=True), d["sem_matrix"].reset_index(drop=True)],
                axis=1,
            )
            for ri, seed in enumerate(h1.REPEAT_SEEDS, start=1):
                folds = pd.to_numeric(
                    d["frozen_splits"][f"repeat_{ri}_fold"], errors="raise"
                ).astype(int).to_numpy()
                pb, pa = h1.crossfit_pair(x_level, x_aug, d["y"], folds)
                mb, ma, delta = h1.metric_pair(d["y"], pb, pa)
                level_repeats.append(
                    {
                        "repeat": int(ri),
                        "seed": int(seed),
                        "comparator": mb,
                        "comparator_plus_openjev": ma,
                        "delta": delta,
                    }
                )
                unit += 1
                update_progress(
                    current=unit,
                    total=total_units,
                    phase="submission_semantic_only_and_decomposition",
                    message=f"{analysis_key}: {level_name}, repeat {ri}/5",
                    unit="repeat",
                )
            decomposition[level_name] = {
                "feature_count": int(len(level_cols)),
                "feature_names": level_cols,
                "primary_repeat": level_repeats[0],
                "repeats": level_repeats,
                "delta_auroc_range": [
                    float(min(r["delta"]["auroc"] for r in level_repeats)),
                    float(max(r["delta"]["auroc"] for r in level_repeats)),
                ],
            }

        results[analysis_key] = {
            "outcome": d["outcome"],
            "source": d["source"],
            "n": int(len(d["y"])),
            "cases": int(d["y"].sum()),
            "note_available_rows": int(np.sum(d["has_note"] == 1)),
            "frozen_split_sha256": d["split_hash"],
            "semantic_only_note_available": {
                "primary_repeat": semantic_repeats[0],
                "repeats": semantic_repeats,
                "auroc_range": [
                    float(min(r["auroc"] for r in semantic_repeats)),
                    float(max(r["auroc"] for r in semantic_repeats)),
                ],
            },
            "comparator_decomposition": decomposition,
        }

    report = {
        "analysis": (
            "Post-registration Paper 1 exploratory semantic-only discrimination "
            "and HGB comparator decomposition"
        ),
        "status": "completed",
        "registration_id": "ahxn9",
        "registered_primary_results_modified": False,
        "uncertainty": (
            "Five pre-frozen patient-grouped partitions only; no new bootstrap "
            "intervals or confirmatory p-values."
        ),
        "semantic_only_population": "note-available rows only",
        "comparator_levels": {
            "A": "34 registered structured physiology/laboratory/urine features only",
            "B": "A plus treatment/support context and death-only code status",
            "C": "B plus documentation-behavior features",
            "D": "C plus ordinary note context; registered rich comparator",
        },
        "interpretation_guardrails": [
            "This entire predictive extension is post-registration exploratory.",
            "Do not present five frozen partitions as independent inferential replicates.",
            "Do not compare TF-IDF numerically across learner families using this table; use H5 for the common-logistic representation comparison.",
            "At level A, semantic missingness on no-note rows can reveal note availability; interpret attenuation across levels descriptively.",
            "No new 500-replicate bootstrap is performed.",
        ],
        "results": results,
    }

    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"status": "completed", "output": str(output)}))


if __name__ == "__main__":
    main()
