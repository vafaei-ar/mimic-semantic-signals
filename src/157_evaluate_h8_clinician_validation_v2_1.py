from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from registration_gate import require_osf_registration
from runrelay_progress import update_progress


def load_numbered_module(filename: str, name: str):
    path = Path(__file__).with_name(filename)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {filename}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


h1 = load_numbered_module("120_evaluate_h1_ventilation_openjev_v2_1.py", "h1_v2_1")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_spearman(x: np.ndarray, y: np.ndarray) -> float:
    mask = np.isfinite(x) & np.isfinite(y)
    if int(mask.sum()) < 3:
        return float("nan")
    xx = x[mask]
    yy = y[mask]
    if np.unique(xx).size < 2 or np.unique(yy).size < 2:
        return float("nan")
    return float(spearmanr(xx, yy).statistic)


def icc2_absolute(matrix: np.ndarray) -> tuple[float, float]:
    x = np.asarray(matrix, dtype=float)
    if x.ndim != 2 or x.shape[1] < 2:
        return float("nan"), float("nan")
    if not np.isfinite(x).all():
        return float("nan"), float("nan")
    n, k = x.shape
    if n < 3:
        return float("nan"), float("nan")

    grand = float(x.mean())
    row_mean = x.mean(axis=1)
    col_mean = x.mean(axis=0)

    ss_rows = float(k * np.sum((row_mean - grand) ** 2))
    ss_cols = float(n * np.sum((col_mean - grand) ** 2))
    residual = x - row_mean[:, None] - col_mean[None, :] + grand
    ss_error = float(np.sum(residual ** 2))

    ms_rows = ss_rows / (n - 1)
    ms_cols = ss_cols / (k - 1)
    ms_error = ss_error / ((n - 1) * (k - 1))

    denom_single = ms_rows + (k - 1) * ms_error + k * (ms_cols - ms_error) / n
    denom_mean = ms_rows + (ms_cols - ms_error) / n
    icc_single = (
        float((ms_rows - ms_error) / denom_single)
        if denom_single != 0
        else float("nan")
    )
    icc_mean = (
        float((ms_rows - ms_error) / denom_mean)
        if denom_mean != 0
        else float("nan")
    )
    return icc_single, icc_mean


def percentile_ci(values: list[float]) -> list[float] | None:
    vals = np.asarray([v for v in values if np.isfinite(v)], dtype=float)
    if len(vals) == 0:
        return None
    return [float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))]


def load_rater_file(
    path: Path,
    linkage: pd.DataFrame,
    constructs: list[str],
) -> pd.DataFrame:
    d = pd.read_csv(path, low_memory=False)
    required = {"sample_id", *constructs, "deterioration_probability_12h"}
    missing = required - set(d.columns)
    if missing:
        raise RuntimeError(f"{path.name}: missing rating columns {sorted(missing)}")
    d["sample_id"] = d["sample_id"].astype(str)
    if d["sample_id"].duplicated().any():
        raise RuntimeError(f"{path.name}: duplicate sample_id")

    expected_ids = set(linkage["sample_id"].astype(str))
    if set(d["sample_id"]) != expected_ids:
        raise RuntimeError(f"{path.name}: sample-id set differs from frozen H8 sample")

    d = d.set_index("sample_id").reindex(linkage["sample_id"].astype(str)).reset_index()

    if "clinical_note" in d.columns:
        observed_hash = d["clinical_note"].fillna("").astype(str).map(
            lambda s: hashlib.sha256(s.encode("utf-8")).hexdigest()
        )
        expected_hash = linkage["clinical_note_sha256"].astype(str).reset_index(drop=True)
        if not np.array_equal(observed_hash.to_numpy(), expected_hash.to_numpy()):
            raise RuntimeError(f"{path.name}: note text differs from frozen H8 packet")

    for col in [*constructs, "deterioration_probability_12h"]:
        raw = d[col]
        val = pd.to_numeric(raw, errors="coerce")
        nonmissing_raw = raw.notna() & raw.astype(str).str.strip().ne("")
        bad_parse = nonmissing_raw & val.isna()
        if bad_parse.any():
            raise RuntimeError(f"{path.name}: nonnumeric rating in {col}")
        observed = val.dropna()
        if ((observed < 0) | (observed > 100)).any():
            raise RuntimeError(f"{path.name}: {col} outside frozen 0-100 scale")
        if not np.allclose(observed.to_numpy(), np.round(observed.to_numpy()), atol=0, rtol=0):
            raise RuntimeError(f"{path.name}: {col} must use integer 0-100 ratings")
        d[col] = val.astype(float)
    return d


def human_aggregates(
    raters: list[pd.DataFrame],
    constructs: list[str],
    minimum_raters: int,
) -> tuple[dict[str, np.ndarray], np.ndarray, dict[str, np.ndarray]]:
    aggregate: dict[str, np.ndarray] = {}
    matrices: dict[str, np.ndarray] = {}
    for col in constructs:
        mat = np.column_stack([r[col].to_numpy(dtype=float) for r in raters])
        matrices[col] = mat
        count = np.isfinite(mat).sum(axis=1)
        mean = np.nanmean(mat, axis=1)
        mean[count < minimum_raters] = np.nan
        aggregate[col] = mean

    pmat = np.column_stack(
        [r["deterioration_probability_12h"].to_numpy(dtype=float) for r in raters]
    )
    pcount = np.isfinite(pmat).sum(axis=1)
    pmean = np.nanmean(pmat, axis=1)
    pmean[pcount < minimum_raters] = np.nan
    matrices["deterioration_probability_12h"] = pmat
    return aggregate, pmean, matrices


def cross_construct_summary(
    model: np.ndarray,
    human: np.ndarray,
    constructs: list[str],
) -> dict:
    m = len(constructs)
    corr = np.full((m, m), np.nan, dtype=float)
    for i in range(m):
        for j in range(m):
            corr[i, j] = safe_spearman(model[:, i], human[:, j])

    rows = []
    for i, name in enumerate(constructs):
        diagonal = corr[i, i]
        off = np.delete(corr[i, :], i)
        finite_off = off[np.isfinite(off)]
        mean_off = float(np.mean(finite_off)) if len(finite_off) else float("nan")
        max_off = float(np.max(finite_off)) if len(finite_off) else float("nan")
        finite_row = corr[i, np.isfinite(corr[i, :])]
        if np.isfinite(diagonal) and len(finite_row):
            rank = 1 + int(np.sum(finite_row > diagonal))
        else:
            rank = None
        rows.append(
            {
                "construct": name,
                "matched_rho": float(diagonal),
                "mean_off_diagonal_rho": mean_off,
                "maximum_off_diagonal_rho": max_off,
                "matched_minus_mean_off_diagonal": (
                    float(diagonal - mean_off)
                    if np.isfinite(diagonal) and np.isfinite(mean_off)
                    else float("nan")
                ),
                "matched_rank_among_human_constructs": rank,
            }
        )

    diag = np.diag(corr)
    off_all = corr[~np.eye(m, dtype=bool)]
    return {
        "matrix": {
            constructs[i]: {
                constructs[j]: float(corr[i, j]) for j in range(m)
            }
            for i in range(m)
        },
        "per_model_construct": rows,
        "mean_diagonal_rho": float(np.nanmean(diag)),
        "mean_off_diagonal_rho": float(np.nanmean(off_all)),
        "mean_diagonal_minus_mean_off_diagonal": float(
            np.nanmean(diag) - np.nanmean(off_all)
        ),
    }


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Evaluate registered v2.1 H8 blinded clinician construct validation."
    )
    ap.add_argument("--base", required=True)
    ap.add_argument("--freeze", required=True)
    ap.add_argument("--governance-gate", required=True)
    ap.add_argument("--preparation-artifact", required=True)
    ap.add_argument("--linkage", required=True)
    ap.add_argument("--rater-1", required=True)
    ap.add_argument("--rater-2", required=True)
    ap.add_argument("--rater-3", required=True)
    ap.add_argument("--semantics", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    require_osf_registration()
    base = Path(args.base).expanduser().resolve()
    freeze_path = Path(args.freeze).expanduser().resolve()
    gate_path = Path(args.governance_gate).expanduser().resolve()
    prep_path = Path(args.preparation_artifact).expanduser().resolve()
    linkage_path = Path(args.linkage).expanduser().resolve()
    semantic_path = Path(args.semantics).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()

    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    prep = json.loads(prep_path.read_text(encoding="utf-8"))

    if not bool(gate.get("irb_determination_documented")):
        raise RuntimeError("H8 governance gate closed: IRB determination not documented")
    if not bool(gate.get("all_primary_raters_authorized_for_mimic")):
        raise RuntimeError("H8 governance gate closed: not all primary raters are authorized")
    if int(gate.get("primary_rater_count", 0)) != int(
        freeze["raters"]["primary_rater_count"]
    ):
        raise RuntimeError("H8 governance gate rater count differs from frozen contract")

    constructs = [x["name"] for x in freeze["constructs"]]
    if constructs != list(h1.SEMANTIC_NAMES):
        raise RuntimeError("H8 construct order differs from registered Open-Jev schema")

    linkage = pd.read_csv(linkage_path, low_memory=False)
    required_link = {
        "sample_id",
        "case_id",
        "subject_id",
        "clinical_note_sha256",
    }
    if required_link - set(linkage.columns):
        raise RuntimeError("H8 linkage file missing required columns")
    linkage["sample_id"] = linkage["sample_id"].astype(str)
    linkage["case_id"] = linkage["case_id"].astype(str)
    linkage["subject_id"] = pd.to_numeric(
        linkage["subject_id"], errors="raise"
    ).astype("int64")
    if len(linkage) != int(freeze["sampling_frame"]["sample_size"]):
        raise RuntimeError("H8 linkage row count differs from frozen sample size")

    update_progress(
        current=1,
        total=4,
        phase="h8_clinician_validation",
        message="Validating three blinded clinician rating files and governance gate",
        unit="stage",
    )

    rater_paths = [
        Path(args.rater_1).expanduser().resolve(),
        Path(args.rater_2).expanduser().resolve(),
        Path(args.rater_3).expanduser().resolve(),
    ]
    raters = [load_rater_file(p, linkage, constructs) for p in rater_paths]

    minimum_raters = int(
        freeze["missing_and_adjudication"]["clinician_aggregate_minimum_raters"]
    )
    human, deterioration, matrices = human_aggregates(
        raters, constructs, minimum_raters
    )
    human_matrix = np.column_stack([human[c] for c in constructs])

    update_progress(
        current=2,
        total=4,
        phase="h8_clinician_validation",
        message="Joining frozen Open-Jev scores only after ratings are validated",
        unit="stage",
    )

    sem = h1.load_semantics(semantic_path)
    sem = sem.set_index("case_id").reindex(linkage["case_id"].astype(str))
    if sem.loc[:, constructs].isna().any().any():
        raise RuntimeError("H8 sampled note missing registered Open-Jev score")
    model = sem.loc[:, constructs].to_numpy(dtype=float)

    inter_rater = {}
    for c in [*constructs, "deterioration_probability_12h"]:
        mat = matrices[c]
        complete = np.isfinite(mat).all(axis=1)
        icc21, icc23 = icc2_absolute(mat[complete])
        pairwise = {}
        for i in range(3):
            for j in range(i + 1, 3):
                pairwise[f"rater_{i+1}_vs_{j+1}"] = safe_spearman(
                    mat[:, i], mat[:, j]
                )
        inter_rater[c] = {
            "complete_three_rater_notes": int(complete.sum()),
            "icc_2_1_absolute_agreement": icc21,
            "icc_2_3_absolute_agreement": icc23,
            "pairwise_spearman": pairwise,
        }

    same_construct = {
        c: {
            "n_with_at_least_two_raters": int(np.isfinite(human[c]).sum()),
            "rho": safe_spearman(model[:, i], human[c]),
        }
        for i, c in enumerate(constructs)
    }
    cross = cross_construct_summary(model, human_matrix, constructs)
    deterioration_assoc = {
        c: safe_spearman(model[:, i], deterioration)
        for i, c in enumerate(constructs)
    }

    update_progress(
        current=3,
        total=4,
        phase="h8_clinician_validation",
        message="Running frozen 2,000-replicate patient-cluster bootstrap",
        unit="stage",
    )

    target = int(freeze["uncertainty"]["valid_replicates_target"])
    seed = int(freeze["uncertainty"]["seed"])
    rng = np.random.default_rng(seed)
    patients = linkage["subject_id"].to_numpy(dtype=np.int64)
    unique_patients = np.unique(patients)
    patient_rows = {p: np.flatnonzero(patients == p) for p in unique_patients}

    boot_same = {c: [] for c in constructs}
    boot_diagdiff = {c: [] for c in constructs}
    boot_deterioration = {c: [] for c in constructs}
    boot_icc21 = {c: [] for c in [*constructs, "deterioration_probability_12h"]}
    boot_icc23 = {c: [] for c in [*constructs, "deterioration_probability_12h"]}
    boot_global_diag = []
    boot_global_off = []
    boot_global_diff = []

    for bi in range(target):
        draw = rng.choice(unique_patients, size=len(unique_patients), replace=True)
        rows = np.concatenate([patient_rows[p] for p in draw])

        bmodel = model[rows]
        bhuman = human_matrix[rows]
        bdet = deterioration[rows]
        bcross = cross_construct_summary(bmodel, bhuman, constructs)

        if np.isfinite(bcross["mean_diagonal_rho"]):
            boot_global_diag.append(bcross["mean_diagonal_rho"])
        if np.isfinite(bcross["mean_off_diagonal_rho"]):
            boot_global_off.append(bcross["mean_off_diagonal_rho"])
        if np.isfinite(bcross["mean_diagonal_minus_mean_off_diagonal"]):
            boot_global_diff.append(
                bcross["mean_diagonal_minus_mean_off_diagonal"]
            )

        for ci, c in enumerate(constructs):
            rho = safe_spearman(bmodel[:, ci], bhuman[:, ci])
            if np.isfinite(rho):
                boot_same[c].append(rho)
            dd = bcross["per_model_construct"][ci][
                "matched_minus_mean_off_diagonal"
            ]
            if np.isfinite(dd):
                boot_diagdiff[c].append(float(dd))
            dr = safe_spearman(bmodel[:, ci], bdet)
            if np.isfinite(dr):
                boot_deterioration[c].append(dr)

        for c in [*constructs, "deterioration_probability_12h"]:
            bmat = matrices[c][rows]
            complete = np.isfinite(bmat).all(axis=1)
            i21, i23 = icc2_absolute(bmat[complete])
            if np.isfinite(i21):
                boot_icc21[c].append(i21)
            if np.isfinite(i23):
                boot_icc23[c].append(i23)

        if (bi + 1) % 50 == 0 or bi + 1 == target:
            update_progress(
                current=bi + 1,
                total=target,
                phase="h8_clinician_validation_bootstrap",
                message=f"H8 patient-cluster bootstrap {bi+1}/{target}",
                unit="replicate",
            )

    for c in inter_rater:
        inter_rater[c]["icc_2_1_ci95_percentile"] = percentile_ci(boot_icc21[c])
        inter_rater[c]["icc_2_1_valid_bootstrap_replicates"] = len(boot_icc21[c])
        inter_rater[c]["icc_2_3_ci95_percentile"] = percentile_ci(boot_icc23[c])
        inter_rater[c]["icc_2_3_valid_bootstrap_replicates"] = len(boot_icc23[c])

    for c in constructs:
        same_construct[c]["rho_ci95_percentile"] = percentile_ci(boot_same[c])
        same_construct[c]["valid_bootstrap_replicates"] = len(boot_same[c])

    for i, c in enumerate(constructs):
        cross["per_model_construct"][i][
            "matched_minus_mean_off_diagonal_ci95_percentile"
        ] = percentile_ci(boot_diagdiff[c])
        cross["per_model_construct"][i][
            "valid_bootstrap_replicates"
        ] = len(boot_diagdiff[c])

    cross["mean_diagonal_rho_ci95_percentile"] = percentile_ci(boot_global_diag)
    cross["mean_off_diagonal_rho_ci95_percentile"] = percentile_ci(boot_global_off)
    cross[
        "mean_diagonal_minus_mean_off_diagonal_ci95_percentile"
    ] = percentile_ci(boot_global_diff)
    cross["global_valid_bootstrap_replicates"] = {
        "mean_diagonal": len(boot_global_diag),
        "mean_off_diagonal": len(boot_global_off),
        "difference": len(boot_global_diff),
    }

    deterioration_output = {
        c: {
            "rho": deterioration_assoc[c],
            "rho_ci95_percentile": percentile_ci(boot_deterioration[c]),
            "valid_bootstrap_replicates": len(boot_deterioration[c]),
        }
        for c in constructs
    }

    report = {
        "analysis": "Registered v2.1 H8 blinded clinician construct validation",
        "status": "completed",
        "registration_id": "ahxn9",
        "doi": "10.17605/OSF.IO/AHXN9",
        "sample_size": int(len(linkage)),
        "unique_patients": int(linkage["subject_id"].nunique()),
        "primary_rater_count": 3,
        "instrument": "Open-Jev",
        "corpus": "frozen stripped-note MetaVision ICU-death corpus",
        "inter_rater_reliability": inter_rater,
        "same_construct_model_human_association": same_construct,
        "cross_construct_discrimination": cross,
        "clinician_deterioration_probability_association": deterioration_output,
        "uncertainty": {
            "bootstrap_unit": "source_patient",
            "target_replicates": target,
            "seed": seed,
            "interval": "two-sided 95% percentile",
            "degenerate_rule": freeze["uncertainty"]["degenerate_rule"],
        },
        "hashes": {
            "h8_freeze_sha256": sha256_file(freeze_path),
            "preparation_artifact_sha256": sha256_file(prep_path),
            "linkage_sha256": sha256_file(linkage_path),
            "semantic_input_sha256": sha256_file(semantic_path),
            "governance_gate_sha256": sha256_file(gate_path),
            "rater_file_sha256": [sha256_file(p) for p in rater_paths],
        },
        "contains_patient_identifiers": False,
        "contains_note_text": False,
        "contains_row_level_ratings": False,
        "guardrails": [
            "Raters were blinded to model scores, outcomes, comparator risk, prior study results, and each other.",
            "Primary clinician aggregates require at least two numeric raters; no missing rating is imputed.",
            "Primary analysis uses no consensus adjudication.",
            "Only the registered stripped-note Open-Jev scores are used for the confirmatory H8 model-human comparison.",
            "No p-values, multiplicity tests, or binary success criterion are produced.",
            "Raw ratings, note text, sample linkage, and row-level model-human joins remain local.",
        ],
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    update_progress(
        current=4,
        total=4,
        phase="done",
        message="Completed registered H8 clinician construct-validation analysis",
        unit="stage",
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
