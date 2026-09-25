from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from statistics import NormalDist


V1_BASELINE_AUROC = {
    "invasive_ventilation": 0.707,
    "renal_replacement_therapy": 0.948,
    "icu_death": 0.793,
}
CORRELATIONS = (0.80, 0.90, 0.95)
ALPHAS = {
    "unadjusted_0_05": 0.05,
    "holm_first_0_05_over_3": 0.05 / 3.0,
}
POWERS = (0.80, 0.90)


def auc_variance(auc: float, n_pos: int, n_neg: int) -> float:
    if n_pos <= 1 or n_neg <= 1:
        return float("nan")
    a = min(max(float(auc), 1e-6), 1 - 1e-6)
    q1 = a / (2 - a)
    q2 = 2 * a * a / (1 + a)
    return (
        a * (1 - a)
        + (n_pos - 1) * (q1 - a * a)
        + (n_neg - 1) * (q2 - a * a)
    ) / (n_pos * n_neg)


def diff_se(a0: float, delta: float, n_pos: int, n_neg: int, rho: float) -> float:
    a1 = min(max(a0 + delta, 1e-5), 0.99999)
    v0 = auc_variance(a0, n_pos, n_neg)
    v1 = auc_variance(a1, n_pos, n_neg)
    cov = rho * math.sqrt(max(v0 * v1, 0.0))
    return math.sqrt(max(v0 + v1 - 2 * cov, 1e-16))


def approximate_power(a0: float, delta: float, n_pos: int, n_neg: int, rho: float, alpha: float) -> float:
    se = diff_se(a0, delta, n_pos, n_neg, rho)
    zcrit = NormalDist().inv_cdf(1 - alpha)
    z = delta / se
    return float(NormalDist().cdf(z - zcrit))


def find_mde(a0: float, n_pos: int, n_neg: int, rho: float, alpha: float, target_power: float) -> float | None:
    lo, hi = 0.0001, min(0.20, 0.999 - a0)
    if approximate_power(a0, hi, n_pos, n_neg, rho, alpha) < target_power:
        return None
    for _ in range(70):
        mid = (lo + hi) / 2
        if approximate_power(a0, mid, n_pos, n_neg, rho, alpha) >= target_power:
            hi = mid
        else:
            lo = mid
    return float(hi)


def counts_from_manifest(info: dict) -> dict:
    n_pos = int(info["cases"])
    n_neg = int(info["controls"])
    case_cov = float(info.get("case_note_coverage") or 0.0)
    control_cov = float(info.get("control_note_coverage") or 0.0)
    return {
        "full_cohort": {"cases": n_pos, "controls": n_neg},
        "note_available_conditional": {
            "cases": int(round(n_pos * case_cov)),
            "controls": int(round(n_neg * control_cov)),
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Planning MDE grid for v2.1 paired delta-AUROC analyses using frozen cohort counts only.")
    ap.add_argument("--cohort-manifest", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    manifest_path = Path(args.cohort_manifest).expanduser().resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    outcomes = manifest["outcomes"]

    report = {
        "analysis": "v2.1 preregistration detectable-effect planning grid",
        "real_outcome_predictions_used": False,
        "real_outcome_labels_read": False,
        "inputs_used": "aggregate frozen cohort counts, prevalence, and note coverage only",
        "baseline_auroc_assumptions": {
            "source": "known v1 population structured AUROCs; used only as planning anchors, not v2.1 estimates",
            **V1_BASELINE_AUROC,
        },
        "paired_prediction_correlation_scenarios": list(CORRELATIONS),
        "alpha_scenarios": ALPHAS,
        "target_power": list(POWERS),
        "method": (
            "Hanley-McNeil AUC variance approximation with assumed paired-AUC correlation; "
            "one-sided normal approximation. This is a planning calculation, not the primary inferential method."
        ),
        "outcomes": {},
    }

    for outcome, base_auc in V1_BASELINE_AUROC.items():
        info = outcomes[outcome]
        count_sets = counts_from_manifest(info)
        outcome_report = {"planning_baseline_auroc": base_auc, "samples": {}}
        for sample_name, counts in count_sets.items():
            n_pos = counts["cases"]
            n_neg = counts["controls"]
            sample = {
                "cases": n_pos,
                "controls": n_neg,
                "mde_delta_auroc": {},
                "power_for_candidate_deltas": {},
            }
            for rho in CORRELATIONS:
                rkey = f"rho_{rho:.2f}"
                sample["mde_delta_auroc"][rkey] = {}
                sample["power_for_candidate_deltas"][rkey] = {}
                for alpha_name, alpha in ALPHAS.items():
                    sample["mde_delta_auroc"][rkey][alpha_name] = {
                        f"power_{int(p*100)}": find_mde(
                            base_auc, n_pos, n_neg, rho, alpha, p
                        )
                        for p in POWERS
                    }
                    sample["power_for_candidate_deltas"][rkey][alpha_name] = {
                        f"{d:.3f}": approximate_power(
                            base_auc, d, n_pos, n_neg, rho, alpha
                        )
                        for d in (0.005, 0.010, 0.013, 0.015, 0.020, 0.030)
                    }
            outcome_report["samples"][sample_name] = sample
        report["outcomes"][outcome] = outcome_report

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
