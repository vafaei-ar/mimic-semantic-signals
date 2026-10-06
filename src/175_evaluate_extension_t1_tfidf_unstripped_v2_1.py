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


base = load_numbered_module(
    "172_evaluate_extension_t1_tfidf_v2_1.py",
    "extension_t1_tfidf_unstripped_base",
)

ATTESTATION = Path(
    "docs/registration/exploratory_extension_osf_upload_attestation_2026-10-05.md"
)
T1_IMPLEMENTATION = Path(
    "docs/registration/exploratory_extension_t1_implementation_clarification_2026-10-05.md"
)

OUTCOME_SUFFIX = {
    "invasive_ventilation": "ventilation",
    "renal_replacement_therapy": "rrt",
    "icu_death": "death",
}


def configure_unstripped() -> None:
    for outcome in base.OUTCOME_SPECS:
        base.OUTCOME_SPECS[outcome]["notes"] = "fixed_notes_full_v2_1_local.jsonl"


def self_test() -> None:
    import numpy as np

    configure_unstripped()
    for outcome, spec in base.OUTCOME_SPECS.items():
        if spec["notes"] != "fixed_notes_full_v2_1_local.jsonl":
            raise RuntimeError(f"{outcome}: unstripped note override failed")

    text = np.asarray(
        [
            "stable oxygen requirement",
            "worsening respiratory failure intubation planned",
            "stable hemodynamics",
            "norepinephrine started for shock",
        ] * 10,
        dtype=object,
    )
    y = np.asarray([0, 1, 0, 1] * 10, dtype=int)
    groups = np.repeat(np.arange(20, dtype=int), 2)
    score = base.inner_crossfit_text(text, y, groups, seed=20261005)
    if score.shape != (40,) or not np.isfinite(score).all():
        raise RuntimeError("T1.4 self-test failed: text cross-fitting")
    vec, model = base.fit_text_model(text, y)
    pred = model.decision_function(vec.transform(text.tolist()))
    if pred.shape != (40,) or not np.isfinite(pred).all():
        raise RuntimeError("T1.4 self-test failed: full text fit")

    print(json.dumps({"t1_4_self_test": "passed"}))


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Paper 1 exploratory extension T1.4 endpoint/treatment-language "
            "sensitivity: repeat T1.1 on frozen unstripped notes."
        )
    )
    ap.add_argument("--outcome", choices=tuple(base.OUTCOME_SPECS), required=True)
    ap.add_argument("--mode", choices=("timing", "full"), required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--timing-input")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        self_test()
        return

    base.require_osf_registration()
    for gate in (ATTESTATION, T1_IMPLEMENTATION):
        if not gate.exists():
            raise RuntimeError(f"Required extension gate missing: {gate}")

    configure_unstripped()
    outcome = args.outcome
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    point = base.point_estimates(outcome, write_local_predictions=True)
    point["representation"] = (
        "TF-IDF supervised text log-odds late fusion on frozen full unstripped notes"
    )
    point["corpus_variant"] = "full_unstripped"
    point["interpretation_label"] = "endpoint/treatment-language sensitivity"

    report = {
        "analysis": (
            "Paper 1 exploratory extension T1.4 endpoint/treatment-language "
            "sensitivity using unstripped notes"
        ),
        "status": "completed",
        "extension_status": "post-registration exploratory",
        "parent_registration": "ahxn9",
        "extension_osf_project": "wmyb2",
        "outcome": outcome,
        "mode": args.mode,
        "corpus_variant": "full_unstripped",
        "point_estimates": point,
        "guardrails": [
            "This is T1.4 endpoint/treatment-language sensitivity, not a pure leakage estimate.",
            "The only intended scientific change from T1.1 is stripped versus frozen full unstripped note text.",
            "TF-IDF, L2-logistic, patient-grouped cross-fitting, HGB settings, and bootstrap rules are unchanged from T1.1.",
            "Every result is reported regardless of direction.",
            "Row-level text scores and predictions remain local and are not declared as artifacts.",
        ],
    }

    if args.mode == "timing":
        timing = base.timing_gate(outcome)
        report["bootstrap_runtime_gate"] = timing
        report["bootstrap_status"] = (
            "timing gate complete; performance estimates from timing replicates discarded"
        )
    else:
        if not args.timing_input:
            raise RuntimeError("--timing-input is required in full mode")
        timing_path = Path(args.timing_input)
        timing_report = json.loads(timing_path.read_text(encoding="utf-8"))
        if (
            timing_report.get("outcome") != outcome
            or timing_report.get("mode") != "timing"
            or timing_report.get("corpus_variant") != "full_unstripped"
        ):
            raise RuntimeError("Timing input does not match requested T1.4 outcome/mode")
        timing = timing_report["bootstrap_runtime_gate"]
        report["bootstrap_runtime_gate"] = timing
        report["primary_refit_bootstrap"] = base.run_full_bootstrap(outcome, timing)
        report["bootstrap_status"] = "completed"

    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "completed",
                "analysis": "T1.4",
                "outcome": outcome,
                "mode": args.mode,
                "primary_delta_auroc": point["primary_repeat"]["delta"]["auroc"],
                "standalone_text_auroc": point["primary_repeat"][
                    "standalone_text_note_available"
                ]["auroc"],
                "selected_bootstrap_replicates": int(
                    report["bootstrap_runtime_gate"][
                        "selected_final_valid_replicates"
                    ]
                ),
                "output": str(output),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
