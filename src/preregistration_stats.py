from __future__ import annotations

import numpy as np


def one_sided_centered_bootstrap_pvalue(delta_observed: float, bootstrap_deltas) -> float:
    """One-sided bootstrap p-value for H0: delta <= 0 versus H1: delta > 0.

    The bootstrap distribution is centered at the observed statistic to
    approximate the null distribution.
    """
    d = np.asarray(bootstrap_deltas, dtype=float)
    if d.ndim != 1 or len(d) == 0 or not np.isfinite(d).all():
        raise ValueError("bootstrap_deltas must be a non-empty finite vector")
    centered = d - float(delta_observed)
    return float((1 + np.sum(centered >= float(delta_observed))) / (len(d) + 1))


def patient_cluster_refit_indices(subject_ids, fold_assignment, rng: np.random.Generator):
    """Generate explicit duplicated-row bootstrap train/test indices by fixed fold.

    Patients are resampled with replacement. Every ICU row for a sampled
    patient is duplicated according to that patient's multiplicity. Fold
    membership never changes, so a duplicated patient cannot enter both train
    and test within a bootstrap fold.
    """
    subjects = np.asarray(subject_ids)
    folds = np.asarray(fold_assignment, dtype=int)
    if len(subjects) != len(folds):
        raise ValueError("subject_ids and fold_assignment lengths differ")
    if len(subjects) == 0:
        raise ValueError("empty input")

    unique_subjects, inverse = np.unique(subjects, return_inverse=True)
    n_patients = len(unique_subjects)
    sampled_patient_positions = rng.integers(0, n_patients, size=n_patients)
    patient_mult = np.bincount(sampled_patient_positions, minlength=n_patients)
    row_mult = patient_mult[inverse]
    duplicated_rows = np.repeat(np.arange(len(subjects), dtype=int), row_mult)

    out = {}
    for fold in sorted(np.unique(folds)):
        test_mask = folds[duplicated_rows] == fold
        test_idx = duplicated_rows[test_mask]
        train_idx = duplicated_rows[~test_mask]
        out[int(fold)] = (train_idx, test_idx)

    return out

def patient_cluster_bootstrap_row_indices(subject_ids, rng: np.random.Generator):
    """Resample source patients with replacement and return duplicated row indices.

    Every ICU row belonging to a sampled patient is retained according to that
    patient's bootstrap multiplicity. This is the fixed-prediction analogue of
    the patient-cluster resampling used in the superseded exact-refit plan.
    """
    subjects = np.asarray(subject_ids)
    if subjects.ndim != 1 or len(subjects) == 0:
        raise ValueError("subject_ids must be a non-empty one-dimensional vector")

    unique_subjects, inverse = np.unique(subjects, return_inverse=True)
    n_patients = len(unique_subjects)
    sampled_patient_positions = rng.integers(0, n_patients, size=n_patients)
    patient_mult = np.bincount(sampled_patient_positions, minlength=n_patients)
    row_mult = patient_mult[inverse]
    return np.repeat(np.arange(len(subjects), dtype=int), row_mult)


def paired_prediction_cluster_bootstrap_delta_auc(
    y_true,
    base_prediction,
    augmented_prediction,
    subject_ids,
    *,
    n_boot: int = 5000,
    seed: int = 20260924,
):
    """Bootstrap paired delta-AUROC from frozen out-of-fold predictions.

    The models are not refit. The returned distribution therefore quantifies
    patient-sampling variability conditional on the supplied fitted prediction
    functions.
    """
    from sklearn.metrics import roc_auc_score

    y = np.asarray(y_true, dtype=int)
    p0 = np.asarray(base_prediction, dtype=float)
    p1 = np.asarray(augmented_prediction, dtype=float)
    subjects = np.asarray(subject_ids)

    if not (len(y) == len(p0) == len(p1) == len(subjects)):
        raise ValueError("input lengths differ")
    if len(y) == 0:
        raise ValueError("empty input")
    if not np.isfinite(p0).all() or not np.isfinite(p1).all():
        raise ValueError("predictions must be finite")
    if not set(np.unique(y)).issubset({0, 1}) or len(np.unique(y)) != 2:
        raise ValueError("y_true must contain both binary classes")
    if int(n_boot) <= 0:
        raise ValueError("n_boot must be positive")

    observed = float(roc_auc_score(y, p1) - roc_auc_score(y, p0))
    children = np.random.SeedSequence(int(seed)).spawn(int(n_boot))
    deltas = np.empty(int(n_boot), dtype=float)

    for i, child in enumerate(children):
        idx = patient_cluster_bootstrap_row_indices(
            subjects,
            np.random.default_rng(child),
        )
        yy = y[idx]
        if yy.sum() == 0 or yy.sum() == len(yy):
            raise RuntimeError(
                "patient-cluster bootstrap replicate contained only one class"
            )
        deltas[i] = float(
            roc_auc_score(yy, p1[idx]) - roc_auc_score(yy, p0[idx])
        )

    lo, hi = np.quantile(deltas, [0.025, 0.975])
    return {
        "observed_delta_auroc": observed,
        "bootstrap_replicates": int(n_boot),
        "seed": int(seed),
        "interval_type": "two-sided 95% percentile",
        "ci95": [float(lo), float(hi)],
        "bootstrap_delta_auroc": deltas,
        "conditional_on_fitted_predictions": True,
    }

