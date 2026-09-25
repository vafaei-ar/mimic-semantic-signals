from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

from common import find_file, lower_columns, module_path, parse_datetime, read_columns, resolve_root
from runrelay_progress import update_progress


OUTCOMES = ("invasive_ventilation", "renal_replacement_therapy", "icu_death")
BEDSIDE_CATEGORIES = {"Physician", "Consult", "Nursing", "Nursing/other", "Respiratory", "General"}
SOURCE_PROXY_THRESHOLD = 0.80

TREATMENT_CANDIDATE_PATTERNS = {
    "fio2_or_oxygen_fraction": [
        r"\bfio2\b", r"inspired oxygen", r"oxygen fraction", r"fraction.*inspired",
    ],
    "oxygen_delivery_device": [
        r"oxygen.*device", r"delivery.*device", r"o2.*device", r"nasal cannula",
        r"high flow", r"high-flow", r"bipap", r"cpap",
    ],
    "oxygen_flow": [
        r"oxygen.*flow", r"o2.*flow", r"flow.*oxygen",
    ],
    "vasoactive": [
        r"norepinephrine", r"levophed", r"epinephrine", r"adrenaline",
        r"phenylephrine", r"neo-synephrine", r"dopamine", r"vasopressin",
    ],
    "sedative_analgesic": [
        r"propofol", r"midazolam", r"versed", r"dexmedetomidine",
        r"precedex", r"fentanyl",
    ],
    "arterial_line_or_invasive_monitoring": [
        r"arterial line", r"a-line", r"arterial catheter",
    ],
}
CODE_STATUS_IDS = {128, 223758}
VENT_ENDPOINT_RELATED_IDS = {
    224385, 223849, 224684, 224688, 225306, 225585, 225588, 225590,
    225592, 226431, 228069,
}


def collapse_note_category(value: object) -> str:
    x = str(value or "").strip().lower()
    if x in {"nursing", "nursing/other"}:
        return "nursing"
    if x in {"physician", "consult"}:
        return "physician"
    if x == "respiratory":
        return "respiratory"
    return "other"


def numeric_zero_mask(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce").fillna(0).eq(0)


def note_identity_hash(index: pd.DataFrame) -> str:
    cols = ["case_id", "icustay_id", "has_note", "note_time", "category"]
    x = index[cols].copy()
    for c in cols:
        x[c] = x[c].fillna("").astype(str)
    payload = "\n".join("|".join(row) for row in x.sort_values("case_id").itertuples(index=False, name=None))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_indices(local_root: Path) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    by_outcome = {}
    frames = []
    for outcome in OUTCOMES:
        p = local_root / outcome / "population_index_local.csv"
        d = pd.read_csv(p, low_memory=False)
        required = {
            "case_id", "subject_id", "hadm_id", "icustay_id", "landmark_time",
            "dbsource", "has_note", "note_time", "note_age_at_landmark_hours", "category",
        }
        missing = required - set(d.columns)
        if missing:
            raise RuntimeError(f"{p}: missing {sorted(missing)}")
        for c in ["subject_id", "hadm_id", "icustay_id"]:
            d[c] = pd.to_numeric(d[c], errors="raise").astype("int64")
        d["landmark_time"] = pd.to_datetime(d["landmark_time"], errors="raise")
        d["note_time"] = pd.to_datetime(d["note_time"], errors="coerce")
        d["dbsource"] = d["dbsource"].fillna("unknown").astype(str).str.strip().str.lower()
        d["category_group"] = d["category"].map(collapse_note_category)
        by_outcome[outcome] = d
        frames.append(
            d[["subject_id", "hadm_id", "icustay_id", "landmark_time", "dbsource"]]
        )

    unique = pd.concat(frames, ignore_index=True).drop_duplicates("icustay_id")
    return by_outcome, unique


def build_note_behavior(root: Path, unique: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    f = find_file(module_path(root, "mimiciii"), ["NOTEEVENTS.csv.gz", "NOTEEVENTS.csv"])
    if f is None:
        raise FileNotFoundError("NOTEEVENTS not found")

    hadms = set(unique["hadm_id"].astype(int))
    lookup = unique[
        ["subject_id", "hadm_id", "icustay_id", "landmark_time"]
    ].copy()

    rows = []
    raw_rows = 0
    selected_rows = 0
    for chunk in read_columns(
        f,
        ["subject_id", "hadm_id", "charttime", "storetime", "category", "iserror", "text"],
        chunksize=250_000,
    ):
        c = lower_columns(chunk)
        c["hadm_id"] = pd.to_numeric(c["hadm_id"], errors="coerce")
        c["subject_id"] = pd.to_numeric(c["subject_id"], errors="coerce")
        c = c[c["hadm_id"].isin(hadms)].copy()
        if c.empty:
            continue
        raw_rows += len(c)

        c = c[numeric_zero_mask(c.get("iserror", pd.Series(0, index=c.index)))].copy()
        c["category"] = c["category"].fillna("UNKNOWN").astype(str).str.strip()
        c = c[c["category"].isin(BEDSIDE_CATEGORIES)].copy()
        if c.empty:
            continue

        c["charttime"] = parse_datetime(c["charttime"])
        c["storetime"] = parse_datetime(c["storetime"])
        c["note_time"] = c["charttime"]
        has_store = c["storetime"].notna()
        c.loc[has_store, "note_time"] = c.loc[has_store, ["charttime", "storetime"]].max(axis=1)
        c["category_group"] = c["category"].map(collapse_note_category)
        c["note_chars"] = c["text"].fillna("").astype(str).str.len().astype("int64")

        m = c[
            ["subject_id", "hadm_id", "note_time", "category_group", "note_chars"]
        ].merge(lookup, on=["subject_id", "hadm_id"], how="inner")
        lower = m["landmark_time"] - pd.to_timedelta(12, unit="h")
        m = m[(m["note_time"] >= lower) & (m["note_time"] <= m["landmark_time"])].copy()
        if m.empty:
            continue
        selected_rows += len(m)
        rows.append(m[["icustay_id", "note_time", "category_group", "note_chars", "landmark_time"]])

    if rows:
        notes = pd.concat(rows, ignore_index=True)
        notes = notes.sort_values(["icustay_id", "note_time"])
        g = notes.groupby("icustay_id", sort=False)

        out = pd.DataFrame(index=pd.Index(unique["icustay_id"].unique(), name="icustay_id"))
        out["doc_note_count_12h"] = g.size()
        out["doc_note_chars_total_12h"] = g["note_chars"].sum()
        out["doc_note_chars_latest_12h"] = g["note_chars"].last()
        out["doc_note_category_groups_12h"] = g["category_group"].nunique()
        latest = g["note_time"].last()
        second_latest = g["note_time"].agg(
            lambda s: s.iloc[-2] if len(s) >= 2 else pd.NaT
        )
        lm = unique.drop_duplicates("icustay_id").set_index("icustay_id")["landmark_time"]
        out["doc_hours_since_last_note"] = (lm - latest).dt.total_seconds() / 3600.0
        out["doc_last_note_gap_hours"] = (latest - second_latest).dt.total_seconds() / 3600.0

        for cat in ("nursing", "physician", "respiratory", "other"):
            counts = notes.loc[notes["category_group"].eq(cat)].groupby("icustay_id").size()
            out[f"doc_{cat}_note_count_12h"] = counts

        out = out.reset_index()
    else:
        out = pd.DataFrame({"icustay_id": unique["icustay_id"].unique()})

    count_cols = [
        "doc_note_count_12h", "doc_note_chars_total_12h", "doc_note_chars_latest_12h",
        "doc_note_category_groups_12h", "doc_nursing_note_count_12h",
        "doc_physician_note_count_12h", "doc_respiratory_note_count_12h",
        "doc_other_note_count_12h",
    ]
    for col in count_cols:
        if col not in out:
            out[col] = 0.0
        out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0.0)

    for col in ["doc_hours_since_last_note", "doc_last_note_gap_hours"]:
        if col not in out:
            out[col] = np.nan

    return out, {
        "raw_hadm_matched_note_rows": int(raw_rows),
        "eligible_prelandmark_bedside_note_rows": int(selected_rows),
        "behavior_features": [c for c in out.columns if c != "icustay_id"],
    }


def audit_dictionary(root: Path) -> dict:
    f = find_file(module_path(root, "mimiciii"), ["D_ITEMS.csv.gz", "D_ITEMS.csv"])
    if f is None:
        raise FileNotFoundError("D_ITEMS not found")
    d = lower_columns(pd.read_csv(f, low_memory=False))
    d["itemid"] = pd.to_numeric(d["itemid"], errors="coerce")
    d = d.dropna(subset=["itemid"]).copy()
    d["itemid"] = d["itemid"].astype(int)
    for col in ["label", "dbsource", "linksto", "category", "unitname"]:
        if col not in d:
            d[col] = ""
        d[col] = d[col].fillna("").astype(str)

    out = {}
    for concept, patterns in TREATMENT_CANDIDATE_PATTERNS.items():
        rx = re.compile("|".join(f"(?:{p})" for p in patterns), re.IGNORECASE)
        q = d[d["label"].str.contains(rx, na=False)].copy()
        q["endpoint_overlap"] = q["itemid"].isin(VENT_ENDPOINT_RELATED_IDS)
        cols = ["itemid", "label", "dbsource", "linksto", "category", "unitname", "endpoint_overlap"]
        out[concept] = q[cols].sort_values(["dbsource", "itemid"]).to_dict(orient="records")

    code = d[d["itemid"].isin(CODE_STATUS_IDS)].copy()
    found = set(code["itemid"].tolist())
    return {
        "candidate_concepts": out,
        "code_status": {
            "expected_itemids": sorted(CODE_STATUS_IDS),
            "missing_itemids": sorted(CODE_STATUS_IDS - found),
            "items": code[
                ["itemid", "label", "dbsource", "linksto", "category", "unitname"]
            ].sort_values("itemid").to_dict(orient="records"),
        },
    }


def source_proxy_auc(df: pd.DataFrame, numeric_cols: list[str], cat_cols: list[str]) -> float:
    from sklearn.compose import ColumnTransformer
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.impute import SimpleImputer
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import StratifiedGroupKFold
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder

    x = df[numeric_cols + cat_cols].copy()
    y = df["source_target"].astype(int).to_numpy()
    groups = df["subject_id"].to_numpy()

    pred = np.full(len(df), np.nan, dtype=float)
    cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=20260924)
    for tr, te in cv.split(x, y, groups=groups):
        pre = ColumnTransformer(
            [
                ("num", SimpleImputer(strategy="median", add_indicator=True), numeric_cols),
                (
                    "cat",
                    Pipeline(
                        [
                            ("impute", SimpleImputer(strategy="most_frequent")),
                            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
                        ]
                    ),
                    cat_cols,
                ),
            ],
            remainder="drop",
        )
        xtr = pre.fit_transform(x.iloc[tr])
        xte = pre.transform(x.iloc[te])
        model = HistGradientBoostingClassifier(
            learning_rate=0.05,
            max_iter=200,
            max_leaf_nodes=15,
            min_samples_leaf=50,
            l2_regularization=1.0,
            early_stopping=False,
            random_state=20260924,
        )
        model.fit(xtr, y[tr])
        pred[te] = model.predict_proba(xte)[:, 1]

    if np.isnan(pred).any():
        raise RuntimeError("source-proxy audit produced missing predictions")
    return float(roc_auc_score(y, pred))


def main() -> None:
    ap = argparse.ArgumentParser(description="Model-free v2.1 treatment/documentation context audit and source-proxy diagnostic.")
    ap.add_argument("--root", required=True)
    ap.add_argument("--local-root", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    root = resolve_root(args.root)
    local_root = Path(args.local_root).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    update_progress(current=1, total=5, phase="context_audit", message="Loading corrected v2.1 cohort indices", unit="stage")
    by_outcome, unique = load_indices(local_root)

    update_progress(current=2, total=5, phase="context_audit", message="Building label-free pre-landmark note-behavior metadata", unit="stage")
    doc, doc_report = build_note_behavior(root, unique)

    for outcome, idx in by_outcome.items():
        local = idx[["case_id", "icustay_id"]].merge(doc, on="icustay_id", how="left")
        local.to_csv(local_root / outcome / "documentation_behavior_v2_1_local.csv", index=False)

    update_progress(current=3, total=5, phase="context_audit", message="Auditing treatment, support, device, and code-status dictionary candidates", unit="stage")
    dictionary = audit_dictionary(root)

    update_progress(current=4, total=5, phase="context_audit", message="Running label-free CareVue/MetaVision source-proxy diagnostic for ICU death", unit="stage")
    death_idx = by_outcome["icu_death"].copy()
    struct = pd.read_csv(
        local_root / "icu_death" / "enhanced_structured_features_v2_1_local.csv",
        low_memory=False,
    )
    struct = struct.drop(columns=["label"], errors="ignore")
    death = death_idx[
        [
            "case_id", "subject_id", "icustay_id", "dbsource", "has_note",
            "note_age_at_landmark_hours", "category_group",
        ]
    ].merge(struct, on=["case_id", "subject_id", "icustay_id", "has_note"], how="left", validate="one_to_one")
    death = death.merge(doc, on="icustay_id", how="left", validate="many_to_one")
    death = death[death["dbsource"].isin(["carevue", "metavision"])].copy()
    death["source_target"] = death["dbsource"].eq("metavision").astype(int)

    id_like = {
        "case_id", "subject_id", "icustay_id", "dbsource", "source_target",
        "sex", "category_group",
    }
    numeric = [
        c for c in death.columns
        if c not in id_like and pd.api.types.is_numeric_dtype(death[c])
    ]
    # Exclude has_note from numeric discovery only to re-add explicitly in a stable order.
    numeric = [c for c in numeric if c != "has_note"]
    numeric.append("has_note")
    numeric = list(dict.fromkeys(numeric))

    full_auc = source_proxy_auc(death, numeric, ["category_group"])
    doc_cols = [c for c in numeric if c.startswith("doc_")] + ["has_note", "note_age_at_landmark_hours"]
    doc_cols = list(dict.fromkeys([c for c in doc_cols if c in death.columns]))
    doc_auc = source_proxy_auc(death, doc_cols, ["category_group"])

    source_counts = death.groupby(["dbsource", "category_group"]).size().unstack(fill_value=0)

    update_progress(current=5, total=5, phase="context_audit", message="Writing aggregate preregistration context audit", unit="stage")
    report = {
        "analysis": "v2.1 preregistration treatment/documentation context audit",
        "outcome_labels_read_for_modeling": False,
        "outcome_performance_computed": False,
        "documentation_behavior": doc_report,
        "note_identity_hashes": {
            outcome: note_identity_hash(idx) for outcome, idx in by_outcome.items()
        },
        "collapsed_note_category_rule": {
            "Nursing,Nursing/other": "nursing",
            "Physician,Consult": "physician",
            "Respiratory": "respiratory",
            "General/other": "other",
        },
        "death_source_by_collapsed_note_category": {
            str(source): {str(k): int(v) for k, v in row.items()}
            for source, row in source_counts.to_dict(orient="index").items()
        },
        "treatment_context_dictionary_audit": dictionary,
        "death_source_proxy": {
            "threshold_auroc": SOURCE_PROXY_THRESHOLD,
            "documentation_only_auroc": doc_auc,
            "current_full_comparator_without_unfrozen_treatment_auroc": full_auc,
            "registration_blocked_if_current_full_auc_exceeds_threshold": bool(full_auc > SOURCE_PROXY_THRESHOLD),
            "interpretation": (
                "This is a label-free diagnostic of residual CareVue/MetaVision recoverability. "
                "It must be repeated after treatment-context mappings are frozen."
            ),
        },
        "local_files_written": {
            outcome: str(local_root / outcome / "documentation_behavior_v2_1_local.csv")
            for outcome in OUTCOMES
        },
        "guardrails": [
            "No clinical outcome performance was computed.",
            "No raw note text or patient identifiers are present in this aggregate artifact.",
            "Dictionary candidates are discovery output and are not automatically frozen predictors.",
            "Device-driven streams are treated as treatment/device context, not documentation behavior.",
        ],
    }
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
