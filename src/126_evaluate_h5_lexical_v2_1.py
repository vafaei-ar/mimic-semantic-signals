from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from registration_gate import require_osf_registration
from runrelay_progress import update_progress


OUTCOMES = ("invasive_ventilation", "renal_replacement_therapy", "icu_death")
REPEAT_SEEDS = (20260924, 20260925, 20260926, 20260927, 20260928)
FOLDS = 5
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


rich = load_numbered_module("117_evaluate_rich_comparator_v2_1.py", "rich_v2_1")
metrics_mod = rich.legacy_metrics


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_note_text(path: Path) -> pd.DataFrame:
    rows = []
    seen = set()
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            rec = json.loads(line)
            cid = str(rec.get("case_id"))
            if not cid or cid == "None" or cid in seen:
                raise RuntimeError("Missing or duplicate case_id in stripped-note corpus")
            seen.add(cid)
            note = (rec.get("model_state") or {}).get("clinical_note")
            if not isinstance(note, str) or not note.strip():
                raise RuntimeError(f"Missing note text for note-available case {cid}")
            rows.append({"case_id": cid, "note_text": note})
    if not rows:
        raise RuntimeError("Empty stripped-note corpus")
    return pd.DataFrame(rows)


def load_semantics(path: Path) -> pd.DataFrame:
    rows = []
    seen = set()
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            rec = json.loads(line)
            cid = str(rec.get("case_id"))
            if not cid or cid == "None" or cid in seen:
                raise RuntimeError("Missing or duplicate case_id in semantic inference")
            seen.add(cid)
            if rec.get("status") != "ok":
                raise RuntimeError(f"Semantic inference status not ok for case {cid}")
            ans = (rec.get("response") or {}).get("answers") or {}
            row = {"case_id": cid}
            for name in SEMANTIC_NAMES:
                item = ans.get(name)
                value = item.get("noul") if isinstance(item, dict) else None
                if not isinstance(value, (int, float)) or not np.isfinite(float(value)):
                    raise RuntimeError(f"Missing semantic score {name} for case {cid}")
                row[name] = float(value)
            rows.append(row)
    if not rows:
        raise RuntimeError("Empty semantic inference file")
    return pd.DataFrame(rows)


def build_logistic(spec: dict) -> LogisticRegression:
    return LogisticRegression(
        penalty=str(spec["penalty"]),
        C=float(spec["C"]),
        solver=str(spec["solver"]),
        max_iter=int(spec["max_iter"]),
        tol=float(spec["tol"]),
        fit_intercept=bool(spec["fit_intercept"]),
        class_weight=spec["class_weight"],
    )


def prepare_population(base: Path, outcome: str, population_contract: dict):
    outcome_contract = population_contract["confirmatory_outcomes"][outcome]
    source = str(outcome_contract["source"]).strip().lower()

    structured_path = base / outcome / "enhanced_structured_features_v2_1_local.csv"
    context_path = base / outcome / "preregistration_context_features_v2_1_local.csv"
    index_path = base / outcome / "population_index_local.csv"

    structured = pd.read_csv(structured_path, low_memory=False)
    context = pd.read_csv(context_path, low_memory=False)
    idx = pd.read_csv(index_path, usecols=["case_id", "dbsource"], low_memory=False)

    structured["case_id"] = structured["case_id"].astype(str)
    idx["case_id"] = idx["case_id"].astype(str)
    idx["dbsource"] = idx["dbsource"].fillna("unknown").astype(str).str.strip().str.lower()
    structured = structured.merge(idx, on="case_id", how="left", validate="one_to_one")
    structured = structured[structured["dbsource"].eq(source)].drop(columns=["dbsource"]).reset_index(drop=True)

    observed = {
        "rows": int(len(structured)),
        "unique_patients": int(structured["subject_id"].nunique()),
        "cases": int(structured["label"].astype(int).sum()),
        "controls": int(len(structured) - structured["label"].astype(int).sum()),
    }
    for key, value in observed.items():
        if int(outcome_contract[key]) != int(value):
            raise RuntimeError(f"{outcome}: {key}={value} != frozen {outcome_contract[key]}")

    return structured, context, source, structured_path, context_path


def split_dense_feature_roles(x: pd.DataFrame):
    binary = []
    for col in x.columns:
        if (
            col == "sex_male"
            or col == "has_note"
            or col.startswith("note_category_")
            or col in {
                "treat_high_flow_any_6h",
                "treat_niv_any_6h",
                "treat_vasoactive_any",
                "treat_sedative_any",
                "code_status_available",
                "code_status_limitation",
                "code_status_comfort_or_no_cpr",
                "code_status_other",
            }
        ):
            binary.append(col)
    continuous = [c for c in x.columns if c not in binary and not c.startswith("note_category_")]
    note_category = [c for c in x.columns if c.startswith("note_category_")]
    return continuous, binary, note_category


def fit_dense(train: pd.DataFrame, test: pd.DataFrame, continuous, binary):
    mats_train = []
    mats_test = []

    if continuous:
        pipe_impute = SimpleImputer(strategy="median")
        scaler = StandardScaler()
        tr = pipe_impute.fit_transform(train[continuous])
        te = pipe_impute.transform(test[continuous])
        tr = scaler.fit_transform(tr)
        te = scaler.transform(te)
        mats_train.append(sparse.csr_matrix(tr))
        mats_test.append(sparse.csr_matrix(te))

    if binary:
        tr = train[binary].astype(float).to_numpy()
        te = test[binary].astype(float).to_numpy()
        if not np.isfinite(tr).all() or not np.isfinite(te).all():
            raise RuntimeError("Binary comparator block contains non-finite values")
        mats_train.append(sparse.csr_matrix(tr))
        mats_test.append(sparse.csr_matrix(te))

    if not mats_train:
        raise RuntimeError("No dense comparator features")
    return sparse.hstack(mats_train, format="csr"), sparse.hstack(mats_test, format="csr")


def fit_semantic(train: pd.DataFrame, test: pd.DataFrame):
    imputer = SimpleImputer(strategy="median")
    scaler = StandardScaler()
    tr = imputer.fit_transform(train[list(SEMANTIC_NAMES)])
    te = imputer.transform(test[list(SEMANTIC_NAMES)])
    tr = scaler.fit_transform(tr)
    te = scaler.transform(te)
    return sparse.csr_matrix(tr), sparse.csr_matrix(te)


def main() -> None:
    ap = argparse.ArgumentParser(description="Registered v2.1 H5 TF-IDF versus Open-Jev common logistic-family analysis.")
    ap.add_argument("--base", required=True)
    ap.add_argument("--outcome", choices=OUTCOMES, required=True)
    ap.add_argument("--split-manifest", required=True)
    ap.add_argument("--context-freeze", required=True)
    ap.add_argument("--analysis-populations", required=True)
    ap.add_argument("--preanalysis-clarifications", required=True)
    ap.add_argument("--notes", required=True)
    ap.add_argument("--semantics", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    require_osf_registration()

    base = Path(args.base).expanduser().resolve()
    outcome = args.outcome
    split_manifest_path = Path(args.split_manifest).expanduser().resolve()
    split_manifest = json.loads(split_manifest_path.read_text(encoding="utf-8"))
    context_freeze_path = Path(args.context_freeze).expanduser().resolve()
    context_freeze = json.loads(context_freeze_path.read_text(encoding="utf-8"))
    population_path = Path(args.analysis_populations).expanduser().resolve()
    population = json.loads(population_path.read_text(encoding="utf-8"))
    clar_path = Path(args.preanalysis_clarifications).expanduser().resolve()
    clar = json.loads(clar_path.read_text(encoding="utf-8"))
    note_path = Path(args.notes).expanduser().resolve()
    semantic_path = Path(args.semantics).expanduser().resolve()

    structured, context, source, structured_path, context_path = prepare_population(base, outcome, population)
    merged, x_base, feature_names = rich.prepare_rich_features(structured, context, outcome, context_freeze)
    y = merged["label"].astype(int).to_numpy()
    groups = merged["subject_id"].to_numpy()
    frozen_splits, split_hash = rich.load_frozen_splits(merged, outcome, base, split_manifest)

    notes = load_note_text(note_path)
    sem = load_semantics(semantic_path)

    note_ids = set(notes["case_id"])
    sem_ids = set(sem["case_id"])
    if note_ids != sem_ids:
        raise RuntimeError(f"Note/semantic case-id mismatch: notes={len(note_ids)}, semantics={len(sem_ids)}")

    has_note = pd.to_numeric(merged["has_note"], errors="raise").astype(int).reset_index(drop=True)
    expected_note_ids = set(merged.loc[has_note.eq(1), "case_id"].astype(str))
    if note_ids != expected_note_ids:
        raise RuntimeError(f"Frozen note corpus does not match note-available cohort: corpus={len(note_ids)}, expected={len(expected_note_ids)}")

    note_map = notes.set_index("case_id")["note_text"].to_dict()
    text = merged["case_id"].astype(str).map(note_map).fillna("").astype(str).reset_index(drop=True)

    sem_aligned = sem.set_index("case_id").reindex(merged["case_id"].astype(str))
    sem_matrix = sem_aligned[list(SEMANTIC_NAMES)].astype(float).reset_index(drop=True)
    if sem_matrix.loc[has_note.eq(1)].isna().any().any():
        raise RuntimeError("Note-available row has incomplete semantic scores")
    if sem_matrix.loc[has_note.eq(0)].notna().any().any():
        raise RuntimeError("No-note row unexpectedly has semantic scores")

    x_base = x_base.reset_index(drop=True)
    continuous, binary, note_category = split_dense_feature_roles(x_base)
    binary_all = binary + note_category

    frame = x_base.copy()
    for name in SEMANTIC_NAMES:
        frame[name] = sem_matrix[name]
    frame["note_text"] = text

    spec = clar["h5_sparse_logistic"]
    model_names = (
        "comparator",
        "comparator_plus_openjev",
        "comparator_plus_tfidf",
        "comparator_plus_tfidf_plus_openjev",
    )

    repeats = []
    local_predictions = merged[["case_id", "subject_id", "icustay_id", "label"]].copy()
    vocab_rows = []
    total = len(REPEAT_SEEDS) * FOLDS
    current = 0

    for ri, seed in enumerate(REPEAT_SEEDS, start=1):
        folds = pd.to_numeric(frozen_splits[f"repeat_{ri}_fold"], errors="raise").astype(int).to_numpy()
        check = pd.DataFrame({"subject_id": groups, "fold": folds})
        if (check.groupby("subject_id")["fold"].nunique() > 1).any():
            raise RuntimeError(f"{outcome}: patient crosses folds in repeat {ri}")

        preds = {name: np.full(len(y), np.nan, dtype=float) for name in model_names}

        for fold in range(1, FOLDS + 1):
            te = np.flatnonzero(folds == fold)
            tr = np.flatnonzero(folds != fold)
            train = frame.iloc[tr]
            test = frame.iloc[te]

            xd_tr, xd_te = fit_dense(train, test, continuous, binary_all)
            xs_tr, xs_te = fit_semantic(train, test)

            vec = TfidfVectorizer(
                lowercase=True,
                strip_accents="unicode",
                ngram_range=(1, 2),
                min_df=5,
                max_df=0.98,
                max_features=10000,
                sublinear_tf=True,
                dtype=np.float64,
            )
            xt_tr = vec.fit_transform(train["note_text"])
            xt_te = vec.transform(test["note_text"])
            vocab_rows.append({"repeat": ri, "fold": fold, "vocabulary_size": int(len(vec.vocabulary_))})

            matrices = {
                "comparator": (xd_tr, xd_te),
                "comparator_plus_openjev": (
                    sparse.hstack([xd_tr, xs_tr], format="csr"),
                    sparse.hstack([xd_te, xs_te], format="csr"),
                ),
                "comparator_plus_tfidf": (
                    sparse.hstack([xd_tr, xt_tr], format="csr"),
                    sparse.hstack([xd_te, xt_te], format="csr"),
                ),
                "comparator_plus_tfidf_plus_openjev": (
                    sparse.hstack([xd_tr, xt_tr, xs_tr], format="csr"),
                    sparse.hstack([xd_te, xt_te, xs_te], format="csr"),
                ),
            }

            for name, (xtr, xte) in matrices.items():
                model = build_logistic(spec)
                model.fit(xtr, y[tr])
                preds[name][te] = model.predict_proba(xte)[:, 1]

            current += 1
            update_progress(
                current=current,
                total=total,
                phase="v2_1_h5_logistic_crossfit",
                message=f"{outcome}: repeat {ri}/5 fold {fold}/5",
                unit="fold",
            )

        row = {"repeat": ri, "seed": int(seed), "models": {}, "contrasts": {}}
        for name in model_names:
            if np.isnan(preds[name]).any():
                raise RuntimeError(f"{outcome}: incomplete predictions for {name}, repeat {ri}")
            row["models"][name] = metrics_mod.basic_metrics(y, preds[name])
            local_predictions[f"h5_{name}_repeat_{ri}"] = preds[name]

        auc = {name: float(row["models"][name]["auroc"]) for name in model_names}
        row["contrasts"] = {
            "openjev_minus_comparator": auc["comparator_plus_openjev"] - auc["comparator"],
            "tfidf_minus_comparator": auc["comparator_plus_tfidf"] - auc["comparator"],
            "openjev_after_tfidf": auc["comparator_plus_tfidf_plus_openjev"] - auc["comparator_plus_tfidf"],
            "tfidf_minus_openjev_increment": (
                (auc["comparator_plus_tfidf"] - auc["comparator"])
                - (auc["comparator_plus_openjev"] - auc["comparator"])
            ),
        }
        repeats.append(row)

    pred_path = base / outcome / "h5_logistic_predictions_v2_1_local.csv"
    local_predictions.to_csv(pred_path, index=False)

    primary = repeats[0]
    report = {
        "analysis": "Registered v2.1 H5 TF-IDF versus Open-Jev common logistic-family analysis",
        "status": "completed",
        "registration_id": "ahxn9",
        "doi": "10.17605/OSF.IO/AHXN9",
        "outcome": outcome,
        "source": source,
        "n": int(len(y)),
        "cases": int(y.sum()),
        "controls": int(len(y) - y.sum()),
        "note_available_rows": int(has_note.sum()),
        "model_family": "L2-penalized logistic regression",
        "logistic_specification": spec,
        "tfidf": {
            "text": "same frozen stripped note as primary Open-Jev analysis",
            "ngram_range": [1, 2],
            "min_df": 5,
            "max_df": 0.98,
            "max_features": 10000,
            "sublinear_tf": True,
            "fit_scope": "training fold only",
            "no_note_rule": "all-zero sparse TF-IDF vector",
            "vocabulary_size_mean": float(pd.DataFrame(vocab_rows)["vocabulary_size"].mean()),
            "vocabulary_size_min": int(pd.DataFrame(vocab_rows)["vocabulary_size"].min()),
            "vocabulary_size_max": int(pd.DataFrame(vocab_rows)["vocabulary_size"].max()),
        },
        "semantic_missingness": "training-fold median imputation then StandardScaler; has_note retained",
        "primary_repeat": primary,
        "repeat_results": repeats,
        "repeat_contrast_ranges": {
            key: [
                float(min(r["contrasts"][key] for r in repeats)),
                float(max(r["contrasts"][key] for r in repeats)),
            ]
            for key in primary["contrasts"]
        },
        "inference_role": (
            "Registered secondary H5 estimation. The registration specifies comparison within a common "
            "logistic family across frozen partitions but does not prescribe a new refit-bootstrap interval "
            "for H5; therefore this analysis reports the primary partition and all five frozen-partition estimates."
        ),
        "hashes": {
            "structured_input_sha256": sha256_file(structured_path),
            "context_input_sha256": sha256_file(context_path),
            "note_corpus_sha256": sha256_file(note_path),
            "semantic_input_sha256": sha256_file(semantic_path),
            "split_sha256": split_hash,
            "split_manifest_sha256": sha256_file(split_manifest_path),
            "context_freeze_sha256": sha256_file(context_freeze_path),
            "analysis_population_contract_sha256": sha256_file(population_path),
            "preanalysis_clarifications_sha256": sha256_file(clar_path),
        },
        "local_prediction_file": str(pred_path),
        "guardrails": [
            "All four H5 models use the same L2-logistic family and frozen folds.",
            "TF-IDF vocabulary and all learned preprocessing are fitted within training folds only.",
            "No-note rows receive all-zero TF-IDF vectors and retain has_note in the comparator.",
            "Semantic missingness is imputed from training-fold medians only.",
            "No p-values or binary significance rule are produced.",
            "Row-level predictions remain local; shared artifact is aggregate only.",
        ],
    }

    out = Path(args.output).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
