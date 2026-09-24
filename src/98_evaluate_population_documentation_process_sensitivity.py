from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from runrelay_progress import update_progress

OUTCOMES = ("invasive_ventilation", "renal_replacement_therapy", "icu_death")
SEED = 20260924


def load_primary_module():
    path = Path(__file__).with_name("97_evaluate_population_landmark12_semantic_extension.py")
    spec = importlib.util.spec_from_file_location("population_semantic_primary", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load frozen population semantic evaluator.")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def selected_metrics(helper, y, p):
    m = helper.basic_metrics(y, p)
    return {
        "auroc": float(m["auroc"]),
        "auprc": float(m["auprc"]),
        "brier": float(m["brier"]),
        "log_loss": float(m["log_loss"]),
        "calibration_intercept": float(m["calibration_intercept"]),
        "calibration_slope": float(m["calibration_slope"]),
        "ece_10_quantile_bins": float(m["ece_10_quantile_bins"]),
    }


def paired_cluster_bootstrap(df, preds, comparisons, helper, n_boot):
    y = df["label"].astype(int).to_numpy()
    patient_codes, patients = pd.factorize(df["subject_id"], sort=False)
    n_patients = len(patients)
    rng = np.random.default_rng(SEED)

    needed = sorted(set(x for pair in comparisons.values() for x in pair))
    prepared = {m: helper._prepare_weighted_rank_metrics(y, preds[m]) for m in needed}
    sqerr = {m: (np.asarray(preds[m], dtype=float) - y.astype(float)) ** 2 for m in needed}

    out = {
        key: {"delta_auroc": [], "delta_auprc": [], "delta_brier": []}
        for key in comparisons
    }

    for b in range(n_boot):
        sampled = rng.integers(0, n_patients, size=n_patients)
        mult = np.bincount(sampled, minlength=n_patients).astype(float)
        w = mult[patient_codes]
        n = float(w.sum())
        if float(np.dot(w, y)) <= 0 or float(np.dot(w, 1 - y)) <= 0:
            continue

        vals = {}
        for m in needed:
            auc, ap = helper._weighted_auc_ap(prepared[m], w)
            if auc is None or ap is None:
                raise RuntimeError("Unexpected degenerate weighted bootstrap replicate")
            vals[m] = {
                "auroc": float(auc),
                "auprc": float(ap),
                "brier": float(np.dot(w, sqerr[m]) / n),
            }

        for key, (base, aug) in comparisons.items():
            out[key]["delta_auroc"].append(vals[aug]["auroc"] - vals[base]["auroc"])
            out[key]["delta_auprc"].append(vals[aug]["auprc"] - vals[base]["auprc"])
            out[key]["delta_brier"].append(vals[aug]["brier"] - vals[base]["brier"])

        if (b + 1) % 100 == 0 or b + 1 == n_boot:
            update_progress(
                current=b + 1,
                total=n_boot,
                phase="population_documentation_sensitivity_bootstrap",
                message=f"paired patient bootstrap {b + 1}/{n_boot}",
                unit="bootstrap",
            )

    def ci(x):
        a = np.asarray(x, dtype=float)
        return [float(np.quantile(a, 0.025)), float(np.quantile(a, 0.975))]

    return {
        key: {
            "replicates": int(len(v["delta_auroc"])),
            "delta_auroc_ci95": ci(v["delta_auroc"]),
            "delta_auprc_ci95": ci(v["delta_auprc"]),
            "delta_brier_ci95": ci(v["delta_brier"]),
        }
        for key, v in out.items()
    }


def main():
    ap = argparse.ArgumentParser(
        description="Post-result population documentation-process and note-available sensitivity."
    )
    ap.add_argument("--base", required=True)
    ap.add_argument("--semantic-base", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--bootstrap-replicates", type=int, default=1000)
    ap.add_argument("--max-features", type=int, default=10000)
    args = ap.parse_args()

    from scipy import sparse
    from sklearn.compose import ColumnTransformer
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import StratifiedGroupKFold
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler

    primary = load_primary_module()
    helper = primary.load_helper()

    base = Path(args.base).expanduser().resolve()
    semantic_base = Path(args.semantic_base).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    mapping_path = semantic_base / "case_to_note_mapping.jsonl"
    oj = primary.load_semantic_raw(semantic_base / "open_jev_raw.jsonl", "oj")
    laya = primary.load_semantic_raw(semantic_base / "laya_raw.jsonl", "laya")

    full_model_names = [
        "structured",
        "structured_has_note",
        "structured_has_note_category_source",
        "structured_full_context",
    ]
    full_comparisons = {
        "has_note_vs_structured": ("structured", "structured_has_note"),
        "category_source_after_has_note": (
            "structured_has_note",
            "structured_has_note_category_source",
        ),
        "note_age_after_category_source": (
            "structured_has_note_category_source",
            "structured_full_context",
        ),
        "full_context_vs_structured": ("structured", "structured_full_context"),
    }

    note_model_names = [
        "note_structured",
        "note_context",
        "note_context_openjev",
        "note_context_laya",
        "note_context_tfidf",
        "note_context_tfidf_openjev",
        "note_context_tfidf_laya",
    ]
    note_comparisons = {
        "openjev_vs_context": ("note_context", "note_context_openjev"),
        "laya_vs_context": ("note_context", "note_context_laya"),
        "openjev_after_tfidf": ("note_context_tfidf", "note_context_tfidf_openjev"),
        "laya_after_tfidf": ("note_context_tfidf", "note_context_tfidf_laya"),
    }

    report = {
        "analysis": "Population documentation-process sensitivity v1",
        "protocol": "docs/population_documentation_process_sensitivity_protocol_v1.md",
        "post_result_sensitivity": True,
        "local_only": True,
        "contains_note_text": False,
        "contains_source_patient_identifiers": False,
        "contains_row_level_predictions": False,
        "folds": int(args.folds),
        "bootstrap_replicates": int(args.bootstrap_replicates),
        "outcomes": {},
    }

    total_folds = len(OUTCOMES) * args.folds * 2
    fold_done = 0

    for oi, outcome in enumerate(OUTCOMES):
        df = primary.load_outcome_frame(base, outcome, mapping_path, oj, laya)
        y = df["label"].astype(int).to_numpy()
        groups = df["subject_id"].to_numpy()

        structured_cols = [
            c
            for c in df.columns
            if c
            not in {
                "case_id",
                "subject_id",
                "icustay_id",
                "label",
                "has_note",
                "category",
                "dbsource",
                "hours_since_icu",
                "note_age_hours",
                "note_text",
                "note_case_id",
                *[f"oj_{x}" for x in primary.SEMANTIC_NAMES],
                *[f"laya_{x}" for x in primary.SEMANTIC_NAMES],
            }
            and pd.api.types.is_numeric_dtype(df[c])
        ]
        if len(structured_cols) != 11:
            raise RuntimeError(
                f"{outcome}: expected 11 structured features, found {len(structured_cols)}"
            )

        def num_pipe():
            return Pipeline(
                [
                    ("impute", SimpleImputer(strategy="median", add_indicator=True)),
                    ("scale", StandardScaler()),
                ]
            )

        def context_preprocessor(num_cols, cat_cols):
            return ColumnTransformer(
                [
                    ("num", num_pipe(), num_cols),
                    ("cat", OneHotEncoder(handle_unknown="ignore"), cat_cols),
                ],
                remainder="drop",
            )

        # A. Full-population documentation-process decomposition.
        full_preds = {
            m: np.full(len(df), np.nan, dtype=float) for m in full_model_names
        }
        cv = StratifiedGroupKFold(
            n_splits=args.folds, shuffle=True, random_state=SEED + oi * 100
        )
        for fold, (tr, te) in enumerate(cv.split(df, y, groups=groups), start=1):
            train = df.iloc[tr]
            test = df.iloc[te]

            p_struct = num_pipe()
            x_struct_tr = sparse.csr_matrix(
                p_struct.fit_transform(train[structured_cols])
            )
            x_struct_te = sparse.csr_matrix(p_struct.transform(test[structured_cols]))

            p_has = num_pipe()
            has_cols = structured_cols + ["has_note"]
            x_has_tr = sparse.csr_matrix(p_has.fit_transform(train[has_cols]))
            x_has_te = sparse.csr_matrix(p_has.transform(test[has_cols]))

            p_cat = context_preprocessor(
                structured_cols + ["has_note"], ["category", "dbsource"]
            )
            cat_cols = structured_cols + ["has_note", "category", "dbsource"]
            x_cat_tr = sparse.csr_matrix(p_cat.fit_transform(train[cat_cols]))
            x_cat_te = sparse.csr_matrix(p_cat.transform(test[cat_cols]))

            p_full = context_preprocessor(
                structured_cols + ["has_note", "note_age_hours"],
                ["category", "dbsource"],
            )
            full_cols = structured_cols + [
                "has_note",
                "note_age_hours",
                "category",
                "dbsource",
            ]
            x_full_tr = sparse.csr_matrix(p_full.fit_transform(train[full_cols]))
            x_full_te = sparse.csr_matrix(p_full.transform(test[full_cols]))

            matrices = {
                "structured": (x_struct_tr, x_struct_te),
                "structured_has_note": (x_has_tr, x_has_te),
                "structured_has_note_category_source": (x_cat_tr, x_cat_te),
                "structured_full_context": (x_full_tr, x_full_te),
            }
            for name, (xtr, xte) in matrices.items():
                model = LogisticRegression(
                    max_iter=3000, solver="liblinear", C=1.0, class_weight=None
                )
                model.fit(xtr, y[tr])
                full_preds[name][te] = model.predict_proba(xte)[:, 1]

            fold_done += 1
            update_progress(
                current=fold_done,
                total=total_folds,
                phase="population_documentation_context_crossfit",
                message=f"{outcome}: full-population context fold {fold}/{args.folds}",
                unit="fold",
            )

        for name, p in full_preds.items():
            if np.isnan(p).any():
                raise RuntimeError(f"{outcome}: missing full-population predictions for {name}")

        full_metrics = {
            name: selected_metrics(helper, y, p) for name, p in full_preds.items()
        }
        full_point = {}
        for key, (base_name, aug_name) in full_comparisons.items():
            full_point[key] = {
                "delta_auroc": float(
                    full_metrics[aug_name]["auroc"] - full_metrics[base_name]["auroc"]
                ),
                "delta_auprc": float(
                    full_metrics[aug_name]["auprc"] - full_metrics[base_name]["auprc"]
                ),
                "delta_brier": float(
                    full_metrics[aug_name]["brier"] - full_metrics[base_name]["brier"]
                ),
            }
        full_boot = paired_cluster_bootstrap(
            df[["subject_id", "label"]],
            full_preds,
            full_comparisons,
            helper,
            args.bootstrap_replicates,
        )

        # B. Note-available-only conditional sensitivity.
        note_df = df.loc[df["has_note"].eq(1)].copy().reset_index(drop=True)
        note_y = note_df["label"].astype(int).to_numpy()
        note_groups = note_df["subject_id"].to_numpy()
        if note_y.sum() < args.folds:
            raise RuntimeError(f"{outcome}: too few note-available cases for {args.folds} folds")

        oj_cols = [f"oj_{x}" for x in primary.SEMANTIC_NAMES]
        laya_cols = [f"laya_{x}" for x in primary.SEMANTIC_NAMES]
        note_context_num = structured_cols + ["note_age_hours"]
        note_cats = ["category", "dbsource"]

        note_preds = {
            m: np.full(len(note_df), np.nan, dtype=float) for m in note_model_names
        }
        vocab_sizes = []
        note_cv = StratifiedGroupKFold(
            n_splits=args.folds, shuffle=True, random_state=SEED + oi * 100
        )
        for fold, (tr, te) in enumerate(
            note_cv.split(note_df, note_y, groups=note_groups), start=1
        ):
            train = note_df.iloc[tr]
            test = note_df.iloc[te]

            p_struct = num_pipe()
            xs_tr = sparse.csr_matrix(p_struct.fit_transform(train[structured_cols]))
            xs_te = sparse.csr_matrix(p_struct.transform(test[structured_cols]))

            p_ctx = context_preprocessor(note_context_num, note_cats)
            ctx_cols = note_context_num + note_cats
            xc_tr = sparse.csr_matrix(p_ctx.fit_transform(train[ctx_cols]))
            xc_te = sparse.csr_matrix(p_ctx.transform(test[ctx_cols]))

            p_oj = context_preprocessor(note_context_num + oj_cols, note_cats)
            oj_input = note_context_num + oj_cols + note_cats
            xoj_tr = sparse.csr_matrix(p_oj.fit_transform(train[oj_input]))
            xoj_te = sparse.csr_matrix(p_oj.transform(test[oj_input]))

            p_laya = context_preprocessor(note_context_num + laya_cols, note_cats)
            laya_input = note_context_num + laya_cols + note_cats
            xla_tr = sparse.csr_matrix(p_laya.fit_transform(train[laya_input]))
            xla_te = sparse.csr_matrix(p_laya.transform(test[laya_input]))

            vec = TfidfVectorizer(
                lowercase=True,
                strip_accents="unicode",
                ngram_range=(1, 2),
                min_df=5,
                max_df=0.98,
                max_features=args.max_features,
                sublinear_tf=True,
                dtype=np.float64,
            )
            xt_tr = vec.fit_transform(train["note_text"].astype(str))
            xt_te = vec.transform(test["note_text"].astype(str))
            vocab_sizes.append(int(len(vec.vocabulary_)))

            matrices = {
                "note_structured": (xs_tr, xs_te),
                "note_context": (xc_tr, xc_te),
                "note_context_openjev": (xoj_tr, xoj_te),
                "note_context_laya": (xla_tr, xla_te),
                "note_context_tfidf": (
                    sparse.hstack([xc_tr, xt_tr], format="csr"),
                    sparse.hstack([xc_te, xt_te], format="csr"),
                ),
                "note_context_tfidf_openjev": (
                    sparse.hstack([xoj_tr, xt_tr], format="csr"),
                    sparse.hstack([xoj_te, xt_te], format="csr"),
                ),
                "note_context_tfidf_laya": (
                    sparse.hstack([xla_tr, xt_tr], format="csr"),
                    sparse.hstack([xla_te, xt_te], format="csr"),
                ),
            }
            for name, (xtr, xte) in matrices.items():
                model = LogisticRegression(
                    max_iter=3000, solver="liblinear", C=1.0, class_weight=None
                )
                model.fit(xtr, note_y[tr])
                note_preds[name][te] = model.predict_proba(xte)[:, 1]

            fold_done += 1
            update_progress(
                current=fold_done,
                total=total_folds,
                phase="population_note_available_crossfit",
                message=f"{outcome}: note-available fold {fold}/{args.folds}",
                unit="fold",
            )

        for name, p in note_preds.items():
            if np.isnan(p).any():
                raise RuntimeError(f"{outcome}: missing note-available predictions for {name}")

        note_metrics = {
            name: selected_metrics(helper, note_y, p) for name, p in note_preds.items()
        }
        note_point = {}
        for key, (base_name, aug_name) in note_comparisons.items():
            note_point[key] = {
                "delta_auroc": float(
                    note_metrics[aug_name]["auroc"] - note_metrics[base_name]["auroc"]
                ),
                "delta_auprc": float(
                    note_metrics[aug_name]["auprc"] - note_metrics[base_name]["auprc"]
                ),
                "delta_brier": float(
                    note_metrics[aug_name]["brier"] - note_metrics[base_name]["brier"]
                ),
            }
        note_boot = paired_cluster_bootstrap(
            note_df[["subject_id", "label"]],
            note_preds,
            note_comparisons,
            helper,
            args.bootstrap_replicates,
        )

        case_mask = df["label"].eq(1)
        control_mask = ~case_mask
        report["outcomes"][outcome] = {
            "population": {
                "n": int(len(df)),
                "cases": int(y.sum()),
                "prevalence": float(y.mean()),
                "note_coverage": float(df["has_note"].mean()),
                "case_note_coverage": float(df.loc[case_mask, "has_note"].mean()),
                "control_note_coverage": float(df.loc[control_mask, "has_note"].mean()),
                "context_decomposition_metrics": full_metrics,
                "context_decomposition_point_differences": full_point,
                "context_decomposition_bootstrap_ci95": full_boot,
            },
            "note_available_conditional": {
                "n": int(len(note_df)),
                "cases": int(note_y.sum()),
                "prevalence": float(note_y.mean()),
                "tfidf_vocabulary_size_by_fold": vocab_sizes,
                "metrics": note_metrics,
                "paired_semantic_comparisons": note_point,
                "paired_patient_bootstrap_ci95": note_boot,
            },
        }

    report["guardrail"] = (
        "Post-result sensitivity only. Full-population context decomposition quantifies "
        "documentation-process signal. Note-available-only results condition on having an "
        "eligible prospective note and must not replace the frozen prevalence-preserving "
        "population analysis or be interpreted as population calibration/utility."
    )
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
