from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from registration_gate import require_osf_registration
from runrelay_progress import update_progress


OUTCOME = "invasive_ventilation"
SEMANTIC_NAMES = (
    "overall_clinician_concern",
    "worsening_trajectory",
    "respiratory_concern",
    "hemodynamic_concern",
    "poor_treatment_response",
    "escalation_considered",
    "diagnostic_uncertainty",
    "reassuring_stability",
)


def load_numbered_module(filename: str, name: str):
    path = Path(__file__).with_name(filename)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {filename}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


dg = load_numbered_module(
    "136_evaluate_h6_diffusiongemma_ventilation_v2_1.py",
    "dg_v2_1",
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_zigong_labels(path: Path) -> pd.DataFrame:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            rec = json.loads(line)
            meta = rec.get("metadata") or {}
            rows.append(
                {
                    "case_id": str(rec["case_id"]),
                    "label": int(meta["label"]),
                    "match_set": int(meta["match_set"]),
                }
            )
    out = pd.DataFrame(rows)
    if len(out) != 340 or out["case_id"].duplicated().any():
        raise RuntimeError("Frozen Zigong cohort labels are incomplete or duplicated")
    if int(out["label"].sum()) != 85:
        raise RuntimeError("Frozen Zigong cohort case count mismatch")
    if int(out["match_set"].nunique()) != 85:
        raise RuntimeError("Frozen Zigong matched-set count mismatch")
    counts = out.groupby("match_set")["label"].agg(["size", "sum"])
    if not ((counts["size"] == 4) & (counts["sum"] == 1)).all():
        raise RuntimeError("Frozen Zigong matched sets are not complete 1:3 sets")
    return out


def metric_summary(y: np.ndarray, p: np.ndarray) -> dict:
    return {
        "auroc": float(roc_auc_score(y, p)),
        "auprc": float(average_precision_score(y, p)),
        "brier": float(brier_score_loss(y, p)),
    }


def matched_bootstrap(
    df: pd.DataFrame,
    probability_col: str,
    *,
    seed: int,
    n_boot: int,
) -> dict:
    sets = df["match_set"].drop_duplicates().to_numpy()
    by = {k: g.copy() for k, g in df.groupby("match_set", sort=False)}
    rng = np.random.default_rng(seed)
    aucs, aps, briers = [], [], []
    for bi in range(n_boot):
        sampled = rng.choice(sets, size=len(sets), replace=True)
        boot = pd.concat([by[x] for x in sampled], ignore_index=True)
        y = boot["label"].to_numpy(dtype=int)
        p = boot[probability_col].to_numpy(dtype=float)
        aucs.append(float(roc_auc_score(y, p)))
        aps.append(float(average_precision_score(y, p)))
        briers.append(float(brier_score_loss(y, p)))
        if (bi + 1) % 100 == 0 or bi + 1 == n_boot:
            update_progress(
                current=bi + 1,
                total=n_boot,
                phase="h9_zigong_matched_bootstrap",
                message=f"H9 matched-set bootstrap {bi+1}/{n_boot}",
                unit="replicate",
            )
    return {
        "auroc_ci95": [float(x) for x in np.quantile(aucs, [0.025, 0.975])],
        "auprc_ci95": [float(x) for x in np.quantile(aps, [0.025, 0.975])],
        "brier_ci95": [float(x) for x in np.quantile(briers, [0.025, 0.975])],
        "bootstrap_replicates": int(n_boot),
        "cluster": "zigong_match_set",
        "seed": int(seed),
    }


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Corrected registered v2.1 H9 MIMIC-to-Zigong DiffusionGemma "
            "semantic external transport evaluation."
        )
    )
    ap.add_argument("--mimic-base", required=True)
    ap.add_argument("--analysis-populations", required=True)
    ap.add_argument("--mimic-dg", required=True)
    ap.add_argument("--zigong-cases", required=True)
    ap.add_argument("--zigong-dg", required=True)
    ap.add_argument("--zigong-inference-report", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--bootstrap-replicates", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=20260924)
    args = ap.parse_args()

    require_osf_registration()

    mimic_base = Path(args.mimic_base).expanduser().resolve()
    population_path = Path(args.analysis_populations).expanduser().resolve()
    mimic_dg_path = Path(args.mimic_dg).expanduser().resolve()
    zigong_cases_path = Path(args.zigong_cases).expanduser().resolve()
    zigong_dg_path = Path(args.zigong_dg).expanduser().resolve()
    zigong_report_path = Path(args.zigong_inference_report).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()

    population = json.loads(population_path.read_text(encoding="utf-8"))
    expected = population["confirmatory_outcomes"][OUTCOME]
    if str(expected["source"]).strip().lower() != "metavision":
        raise RuntimeError("Registered H9 MIMIC training source must be MetaVision")

    zigong_report = json.loads(zigong_report_path.read_text(encoding="utf-8"))
    if zigong_report.get("status") != "completed":
        raise RuntimeError("Frozen Zigong DiffusionGemma inference report is not completed")
    if int(zigong_report.get("successful_rows_available", -1)) != 340:
        raise RuntimeError("Frozen Zigong DiffusionGemma inference is not complete for 340 notes")
    if bool(zigong_report.get("zigong_outcome_labels_read_or_used", True)):
        raise RuntimeError("Zigong semantic inference report indicates outcome-label access")
    policy = zigong_report.get("context_policy") or {}
    if (
        int(policy.get("note_chunk_tokens", -1)) != 977
        or int(policy.get("chunk_overlap_tokens", -1)) != 97
        or int(policy.get("max_chunks", -1)) != 8
        or int(policy.get("max_new_tokens", -1)) != 256
    ):
        raise RuntimeError("Frozen Zigong DiffusionGemma context policy changed")

    update_progress(
        current=1,
        total=4,
        phase="h9_zigong_transport",
        message="Loading full frozen v2.1 MIMIC ventilation cohort and semantic scores",
        unit="stage",
    )

    index_path = mimic_base / OUTCOME / "population_index_local.csv"
    index = pd.read_csv(
        index_path,
        usecols=["case_id", "subject_id", "dbsource", "label", "has_note"],
        low_memory=False,
    )
    index["case_id"] = index["case_id"].astype(str)
    index["dbsource"] = (
        index["dbsource"].fillna("unknown").astype(str).str.strip().str.lower()
    )
    index = index[index["dbsource"].eq("metavision")].copy()
    index["label"] = pd.to_numeric(index["label"], errors="raise").astype(int)
    index["subject_id"] = pd.to_numeric(
        index["subject_id"], errors="raise"
    ).astype("int64")
    index["has_note"] = (
        pd.to_numeric(index["has_note"], errors="coerce").fillna(0).ne(0)
    )

    observed = {
        "rows": int(len(index)),
        "unique_patients": int(index["subject_id"].nunique()),
        "cases": int(index["label"].sum()),
        "controls": int(len(index) - index["label"].sum()),
        "note_available_rows": int(index["has_note"].sum()),
    }
    for key, value in observed.items():
        if int(expected[key]) != int(value):
            raise RuntimeError(
                f"Registered MIMIC ventilation mismatch {key}: {value} != {expected[key]}"
            )
    if index["case_id"].duplicated().any():
        raise RuntimeError("Duplicate case_id in registered MIMIC ventilation cohort")

    mimic_sem = dg.load_semantics(mimic_dg_path)
    note_ids = set(index.loc[index["has_note"], "case_id"])
    sem_ids = set(mimic_sem["case_id"])
    if sem_ids != note_ids:
        raise RuntimeError(
            f"MIMIC DiffusionGemma/note mismatch: missing={len(note_ids-sem_ids)}, "
            f"extra={len(sem_ids-note_ids)}"
        )
    mimic_sem = mimic_sem.set_index("case_id").reindex(index["case_id"])
    mimic_x = mimic_sem.loc[:, SEMANTIC_NAMES].astype(float).reset_index(drop=True)
    if mimic_x.loc[index["has_note"].to_numpy()].isna().any().any():
        raise RuntimeError("MIMIC note-available row has incomplete DiffusionGemma scores")
    if mimic_x.loc[~index["has_note"].to_numpy()].notna().any().any():
        raise RuntimeError("MIMIC no-note row unexpectedly has DiffusionGemma scores")

    update_progress(
        current=2,
        total=4,
        phase="h9_zigong_transport",
        message="Loading frozen Zigong labels/matched sets and completed DiffusionGemma scores",
        unit="stage",
    )

    zig = load_zigong_labels(zigong_cases_path)
    zig_sem = dg.load_semantics(zigong_dg_path)
    if len(zig_sem) != 340:
        raise RuntimeError(f"Expected 340 Zigong semantic rows, found {len(zig_sem)}")
    zig = zig.merge(zig_sem, on="case_id", how="inner", validate="one_to_one")
    if len(zig) != 340:
        raise RuntimeError("Zigong labels/semantic score merge is incomplete")
    zig_x = zig.loc[:, SEMANTIC_NAMES].astype(float)
    if zig_x.isna().any().any():
        raise RuntimeError("Zigong semantic matrix contains missing values")

    pre = ColumnTransformer(
        [
            (
                "num",
                Pipeline(
                    [
                        ("impute", SimpleImputer(strategy="median", add_indicator=True)),
                        ("scale", StandardScaler()),
                    ]
                ),
                list(SEMANTIC_NAMES),
            )
        ],
        remainder="drop",
    )
    model = Pipeline(
        [
            ("pre", pre),
            (
                "model",
                LogisticRegression(
                    max_iter=3000,
                    solver="liblinear",
                    C=1.0,
                ),
            ),
        ]
    )

    update_progress(
        current=3,
        total=4,
        phase="h9_zigong_transport",
        message="Fitting semantic-only logistic pipeline on full frozen MIMIC cohort and applying unchanged to Zigong",
        unit="stage",
    )

    y_mimic = index["label"].to_numpy(dtype=int)
    model.fit(mimic_x, y_mimic)
    zig["transport_probability"] = model.predict_proba(zig_x)[:, 1]

    y = zig["label"].to_numpy(dtype=int)
    p = zig["transport_probability"].to_numpy(dtype=float)
    primary = metric_summary(y, p)
    primary.update(
        matched_bootstrap(
            zig[["label", "match_set", "transport_probability"]],
            "transport_probability",
            seed=args.seed,
            n_boot=args.bootstrap_replicates,
        )
    )

    constructs = {}
    for name in SEMANTIC_NAMES:
        raw = zig[name].to_numpy(dtype=float)
        oriented = 1.0 - raw if name == "reassuring_stability" else raw
        constructs[name] = {
            "orientation": "1-score" if name == "reassuring_stability" else "score",
            "auroc": float(roc_auc_score(y, oriented)),
            "case_mean": float(oriented[y == 1].mean()),
            "control_mean": float(oriented[y == 0].mean()),
        }

    local_pred_path = (
        Path("data/real_zigong_local/ventilation24_v1")
        / "h9_diffusiongemma_transport_predictions_v2_1_local.csv"
    ).resolve()
    pd.DataFrame(
        {
            "case_id": zig["case_id"].astype(str),
            "match_set": zig["match_set"].astype(int),
            "label": y,
            "transport_probability": p,
        }
    ).to_csv(local_pred_path, index=False)

    report = {
        "analysis": "Registered corrected v2.1 H9 MIMIC-to-Zigong DiffusionGemma semantic transport",
        "status": "completed",
        "registration_id": "ahxn9",
        "doi": "10.17605/OSF.IO/AHXN9",
        "protocol": "docs/zigong_diffusiongemma_external_transport_protocol_v1.md",
        "eligibility_freeze": "docs/zigong_direct_chinese_model_eligibility_freeze.md",
        "historical_v1_result_status": (
            "superseded for manuscript-facing H9 because its implementation trained "
            "on the obsolete 1,460-row v1 MIMIC benchmark rather than the protocol-required "
            "full frozen v2.1 ventilation cohort"
        ),
        "local_only": True,
        "contains_note_text": False,
        "contains_source_patient_identifiers": False,
        "patient_level_predictions_shared": False,
        "zigong_model_fitting_performed": False,
        "recalibration_performed": False,
        "threshold_selection_performed": False,
        "model": "google/diffusiongemma-26B-A4B-it",
        "score_definition": (
            "Prompted zero-shot 0-1 support scores for the frozen eight semantic constructs; "
            "not Jev noul probabilities."
        ),
        "training_dataset": {
            "name": "Frozen corrected v2.1 MIMIC-III invasive ventilation 12h cohort",
            **observed,
        },
        "external_dataset": {
            "name": "Frozen Zigong invasive ventilation 24h narrative risk-set cohort",
            "n": int(len(zig)),
            "cases": int(zig["label"].sum()),
            "controls": int(len(zig) - zig["label"].sum()),
            "matched_sets": int(zig["match_set"].nunique()),
            "sampled_prevalence": float(zig["label"].mean()),
        },
        "transport_model": {
            "features": list(SEMANTIC_NAMES),
            "preprocessing": (
                "median imputation with missing indicators, then standard scaling"
            ),
            "classifier": "LogisticRegression(liblinear, C=1.0, max_iter=3000)",
            "fit_on": "full frozen corrected v2.1 MIMIC ventilation cohort only",
            "applied_to": (
                "Zigong without refitting, recalibration, threshold selection, "
                "coefficient modification, prompt adaptation, or translation"
            ),
        },
        "primary_transport_metrics": primary,
        "construct_level_exploratory": constructs,
        "hashes": {
            "mimic_population_index_sha256": sha256_file(index_path),
            "mimic_diffusiongemma_sha256": sha256_file(mimic_dg_path),
            "analysis_population_contract_sha256": sha256_file(population_path),
            "zigong_cases_sha256": sha256_file(zigong_cases_path),
            "zigong_diffusiongemma_sha256": sha256_file(zigong_dg_path),
            "zigong_inference_report_sha256": sha256_file(zigong_report_path),
        },
        "local_prediction_file": str(local_pred_path),
        "guardrails": [
            "MIMIC training uses the full registered corrected v2.1 ventilation cohort, not the obsolete v1 matched benchmark.",
            "Only DiffusionGemma is scored on direct Chinese Zigong notes under the frozen bilingual eligibility gate.",
            "No model is fitted on Zigong labels.",
            "No Zigong recalibration, threshold selection, coefficient modification, prompt adaptation, or post-hoc translation is allowed.",
            "Primary uncertainty uses 2,000 matched-set bootstrap replicates with the frozen seed.",
            "AUPRC is conditional on the sampled 25% Zigong prevalence and Brier score is descriptive rather than population calibration.",
            "Row-level Zigong predictions and all patient-level data remain local; shared output is aggregate only.",
        ],
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    update_progress(
        current=4,
        total=4,
        phase="done",
        message="Completed corrected registered H9 Zigong DiffusionGemma transport",
        unit="stage",
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
