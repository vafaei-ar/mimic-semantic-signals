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
