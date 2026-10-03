from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from common import find_file, lower_columns, module_path, parse_datetime, read_columns
from registration_gate import require_osf_registration
from runrelay_progress import update_progress
from semantic_schema import SEMANTIC_CONSTRUCTS


OUTCOMES = ("invasive_ventilation", "renal_replacement_therapy", "icu_death")
SENSITIVITIES = ("storetime_only", "fallback_delay")
LOOKBACK_HOURS = 12.0
FALLBACK_QUANTILE = 0.90


def load_numbered_module(filename: str, name: str):
    path = Path(__file__).with_name(filename)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {filename}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cohort = load_numbered_module("104_build_corrected_landmark12_v2_1_cohorts.py", "cohort_v2_1")
corpus = load_numbered_module("115_build_fixed_note_corpora_v2_1.py", "corpus_v2_1")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def norm_source(s: pd.Series) -> pd.Series:
    return s.fillna("unknown").astype(str).str.strip().str.lower()


def load_registered_populations(local_root: Path, contract: dict) -> dict[str, pd.DataFrame]:
    out = {}
    for outcome in OUTCOMES:
        expected = contract["confirmatory_outcomes"][outcome]
        path = local_root / outcome / "population_index_local.csv"
        use = [
            "case_id", "subject_id", "hadm_id", "icustay_id", "landmark_time",
            "outtime", "dbsource", "has_note", "note_time", "category",
            "storetime_available", "documentation_delay_hours",
        ]
        d = pd.read_csv(path, usecols=use, low_memory=False)
        d["case_id"] = d["case_id"].astype(str)
        d["dbsource"] = norm_source(d["dbsource"])
        d = d[d["dbsource"].eq(str(expected["source"]).strip().lower())].copy()
        for col in ["subject_id", "hadm_id", "icustay_id"]:
            d[col] = pd.to_numeric(d[col], errors="raise").astype("int64")
        d["landmark_time"] = pd.to_datetime(d["landmark_time"], errors="raise")
        d["outtime"] = pd.to_datetime(d["outtime"], errors="raise")
        d["intime"] = d["landmark_time"] - pd.to_timedelta(12, unit="h")
        d["note_time"] = pd.to_datetime(d["note_time"], errors="coerce")
        d["has_note"] = pd.to_numeric(d["has_note"], errors="coerce").fillna(0).ne(0)
        d["storetime_available"] = (
            pd.to_numeric(d["storetime_available"], errors="coerce").fillna(0).ne(0)
        )
        if int(len(d)) != int(expected["rows"]):
            raise RuntimeError(
                f"{outcome}: registered row mismatch {len(d)} != {expected['rows']}"
            )
        if int(d["has_note"].sum()) != int(expected["note_available_rows"]):
            raise RuntimeError(
                f"{outcome}: registered note-count mismatch "
                f"{int(d['has_note'].sum())} != {expected['note_available_rows']}"
            )
        out[outcome] = d
    return out


def scan_notes(root: Path, hadms: set[int]) -> tuple[pd.DataFrame, dict]:
    f = find_file(module_path(root, "mimiciii"), ["NOTEEVENTS.csv.gz", "NOTEEVENTS.csv"])
    if f is None:
        raise FileNotFoundError("NOTEEVENTS not found")

    parts = []
    scanned = 0
    relevant = 0
    errors_excluded = 0
    category_excluded = 0
    blank_excluded = 0
    source_order = 0

    for chunk in read_columns(
        f,
        ["hadm_id", "charttime", "storetime", "category", "iserror", "text"],
        chunksize=100_000,
    ):
        scanned += int(len(chunk))
        c = lower_columns(chunk)
        c["hadm_id"] = pd.to_numeric(c["hadm_id"], errors="coerce")
        c = c[c["hadm_id"].isin(hadms)].copy()
        if c.empty:
            continue
        relevant += int(len(c))

        if "iserror" in c.columns:
            ok = cohort.numeric_zero_mask(c["iserror"])
            errors_excluded += int((~ok).sum())
            c = c[ok].copy()

        c["category"] = c["category"].fillna("UNKNOWN").astype(str).str.strip()
        cat_ok = c["category"].isin(cohort.BEDSIDE_CATEGORIES)
        category_excluded += int((~cat_ok).sum())
        c = c[cat_ok].copy()
        if c.empty:
            continue

        c["chart_time"] = parse_datetime(c["charttime"])
        c["store_time"] = parse_datetime(c["storetime"])
        c = c.dropna(subset=["hadm_id", "chart_time", "text"]).copy()
        nonblank = c["text"].astype(str).str.strip().ne("")
        blank_excluded += int((~nonblank).sum())
        c = c[nonblank].copy()
        if c.empty:
            continue

        c["hadm_id"] = c["hadm_id"].astype("int64")
        c["storetime_available"] = c["store_time"].notna()
        c["primary_time"] = c["chart_time"]
        has_store = c["storetime_available"]
        c.loc[has_store, "primary_time"] = c.loc[
            has_store, ["chart_time", "store_time"]
        ].max(axis=1)
        c["documentation_delay_hours"] = (
            c["primary_time"] - c["chart_time"]
        ).dt.total_seconds() / 3600.0
        c["source_order"] = np.arange(source_order, source_order + len(c), dtype=np.int64)
        source_order += len(c)
        parts.append(
            c[
                [
                    "hadm_id", "chart_time", "store_time", "storetime_available",
                    "primary_time", "documentation_delay_hours", "category",
                    "text", "source_order",
                ]
            ]
        )

    if not parts:
        raise RuntimeError("No normalized bedside notes found for registered populations")

    notes = pd.concat(parts, ignore_index=True)
    report = {
        "raw_rows_scanned": int(scanned),
        "rows_in_registered_hadm_ids_before_hygiene": int(relevant),
        "error_rows_excluded": int(errors_excluded),
        "nonbedside_category_rows_excluded": int(category_excluded),
        "blank_text_rows_excluded": int(blank_excluded),
        "normalized_bedside_rows": int(len(notes)),
        "storetime_missing_rows": int((~notes["storetime_available"]).sum()),
        "storetime_missing_fraction": float((~notes["storetime_available"]).mean()),
    }
    return notes, report


def eligible_candidates(
    notes: pd.DataFrame,
    pop: pd.DataFrame,
    sensitivity: str,
    fallback_delay_hours: int,
) -> pd.DataFrame:
    m = notes.merge(
        pop[
            [
                "case_id", "subject_id", "hadm_id", "icustay_id",
                "intime", "landmark_time",
            ]
        ],
        on="hadm_id",
        how="inner",
    )
    if sensitivity == "storetime_only":
        m = m[m["storetime_available"]].copy()
        m["effective_time"] = m[["chart_time", "store_time"]].max(axis=1)
        m["availability_basis"] = "max(charttime,storetime);storetime_required"
    elif sensitivity == "fallback_delay":
        m["effective_time"] = m["chart_time"]
        has_store = m["storetime_available"]
        m.loc[has_store, "effective_time"] = m.loc[
            has_store, ["chart_time", "store_time"]
        ].max(axis=1)
        missing_store = ~has_store
        m.loc[missing_store, "effective_time"] = (
            m.loc[missing_store, "chart_time"]
            + pd.to_timedelta(fallback_delay_hours, unit="h")
        )
        m["availability_basis"] = np.where(
            has_store,
            "max(charttime,storetime)",
            f"charttime+{fallback_delay_hours}h_fallback",
        )
    else:
        raise ValueError(f"Unknown sensitivity: {sensitivity}")

    m = m[
        (m["effective_time"] >= m["intime"])
        & (m["effective_time"] <= m["landmark_time"])
    ].copy()
    m["hours_since_icu"] = (
        m["effective_time"] - m["intime"]
    ).dt.total_seconds() / 3600.0
    m["note_age_at_landmark_hours"] = (
        m["landmark_time"] - m["effective_time"]
    ).dt.total_seconds() / 3600.0
    return m


def select_latest(candidates: pd.DataFrame) -> pd.DataFrame:
    if candidates.empty:
        return candidates.copy()
    q = candidates.sort_values(
        ["icustay_id", "effective_time", "source_order"],
        kind="mergesort",
    ).copy()
    q = q.groupby("icustay_id", as_index=False, sort=False).tail(1).copy()
    return q.sort_values("case_id").reset_index(drop=True)


def primary_signature(row) -> tuple:
    if not bool(row.has_note):
        return ("no_note",)
    note_time = pd.Timestamp(row.note_time)
    category = "" if pd.isna(row.category) else str(row.category)
    if bool(row.storetime_available):
        return ("store", note_time.isoformat(), category)
    return ("fallback", note_time.isoformat(), category)


def sensitivity_signature(row) -> tuple:
    category = "" if pd.isna(row.category) else str(row.category)
    if bool(row.storetime_available):
        return ("store", pd.Timestamp(row.effective_time).isoformat(), category)
    return ("fallback", pd.Timestamp(row.chart_time).isoformat(), category)


def write_local_outputs(
    local_root: Path,
    outcome: str,
    sensitivity: str,
    selected: pd.DataFrame,
    pop: pd.DataFrame,
    strip_freeze: dict,
    fallback_delay_hours: int,
) -> dict:
    outdir = local_root / outcome
    index_path = outdir / f"h6_note_availability_{sensitivity}_index_v2_1_local.csv"
    full_path = outdir / f"h6_note_availability_{sensitivity}_full_v2_1_local.jsonl"
    stripped_path = outdir / f"h6_note_availability_{sensitivity}_stripped_v2_1_local.jsonl"

    cols = [
        "case_id", "subject_id", "hadm_id", "icustay_id", "dbsource",
        "landmark_time",
    ]
    idx = pop[cols].copy()
    keep = selected[
        [
            "case_id", "effective_time", "hours_since_icu",
            "note_age_at_landmark_hours", "category", "storetime_available",
            "documentation_delay_hours", "availability_basis",
        ]
    ].copy()
    keep = keep.rename(columns={"effective_time": "note_time"})
    idx = idx.merge(keep, on="case_id", how="left", validate="one_to_one")
    idx["has_note"] = idx["note_time"].notna()
    idx.to_csv(index_path, index=False)

    replacement = str(strip_freeze["replacement"])
    rx = corpus.compile_outcome_regex(strip_freeze["patterns"][outcome])
    notes_changed = 0
    total_matches = 0

    with full_path.open("w", encoding="utf-8") as fh_full, stripped_path.open(
        "w", encoding="utf-8"
    ) as fh_strip:
        for row in selected.sort_values("case_id").itertuples(index=False):
            text = str(row.text)
            stripped, nmatch = corpus.strip_text(text, rx, replacement)
            base = {
                "case_id": str(row.case_id),
                "synthetic_only": False,
                "local_only": True,
                "model_state": {"clinical_note": text},
                "metadata": {
                    "analysis": "h6_note_availability_v2_1",
                    "outcome": outcome,
                    "sensitivity": sensitivity,
                    "note_available": True,
                    "note_category": str(row.category),
                    "hours_since_icu_at_note": round(float(row.hours_since_icu), 3),
                    "note_age_at_landmark_hours": round(
                        float(row.note_age_at_landmark_hours), 3
                    ),
                    "note_availability_basis": str(row.availability_basis),
                    "storetime_available": bool(row.storetime_available),
                    "fallback_delay_hours": (
                        int(fallback_delay_hours)
                        if sensitivity == "fallback_delay"
                        else None
                    ),
                    "documentation_delay_hours": (
                        round(float(row.documentation_delay_hours), 3)
                        if pd.notna(row.documentation_delay_hours)
                        else None
                    ),
                    "note_characters": int(len(text)),
                },
                "questions": SEMANTIC_CONSTRUCTS,
                "gold": None,
            }
            full_rec = copy.deepcopy(base)
            full_rec["metadata"]["corpus_variant"] = "full_unstripped"
            strip_rec = copy.deepcopy(base)
            strip_rec["model_state"]["clinical_note"] = stripped
            strip_rec["metadata"]["corpus_variant"] = "language_stripped"
            strip_rec["metadata"]["outcome_language_match_count"] = int(nmatch)
            fh_full.write(json.dumps(full_rec, ensure_ascii=False) + "\n")
            fh_strip.write(json.dumps(strip_rec, ensure_ascii=False) + "\n")
            notes_changed += int(nmatch > 0)
            total_matches += int(nmatch)

    return {
        "index_local_file": str(index_path),
        "index_sha256": sha256_file(index_path),
        "full_local_file": str(full_path),
        "full_sha256": sha256_file(full_path),
        "stripped_local_file": str(stripped_path),
        "stripped_sha256": sha256_file(stripped_path),
        "notes_changed_by_frozen_stripping": int(notes_changed),
        "total_stripping_matches": int(total_matches),
    }


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Audit registered H6 note-availability timing, deterministically freeze "
            "a conservative missing-storetime fallback delay, and materialize local "
            "alternative note corpora without semantic or predictive inference."
        )
    )
    ap.add_argument("--root", required=True)
    ap.add_argument("--local-root", required=True)
    ap.add_argument("--analysis-populations", required=True)
    ap.add_argument("--strip-freeze", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    require_osf_registration()
    root = cohort.resolve_root(args.root)
    local_root = Path(args.local_root).expanduser().resolve()
    contract_path = Path(args.analysis_populations).expanduser().resolve()
    strip_path = Path(args.strip_freeze).expanduser().resolve()
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    strip_freeze = json.loads(strip_path.read_text(encoding="utf-8"))
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    update_progress(
        current=1, total=5, phase="h6_note_availability_audit",
        message="Loading frozen registered MetaVision populations", unit="stage"
    )
    populations = load_registered_populations(local_root, contract)
    hadms = set()
    icu_frames = []
    for d in populations.values():
        hadms.update(d["hadm_id"].tolist())
        icu_frames.append(
            d[["hadm_id", "icustay_id", "intime", "landmark_time"]]
        )
    icu_union = (
        pd.concat(icu_frames, ignore_index=True)
        .drop_duplicates("icustay_id")
        .reset_index(drop=True)
    )

    update_progress(
        current=2, total=5, phase="h6_note_availability_audit",
        message="Scanning normalized bedside NOTEEVENTS timing", unit="stage"
    )
    notes, scan_report = scan_notes(root, hadms)

    # Derive the conservative fallback delay without labels or performance.
    # Use only storetime-present bedside notes that are eligible under the
    # registered primary availability rule in at least one registered
    # MetaVision ICU stay, de-duplicated at the raw-note level.
    audit = notes[notes["storetime_available"]].merge(
        icu_union, on="hadm_id", how="inner"
    )
    audit = audit[
        (audit["primary_time"] >= audit["intime"])
        & (audit["primary_time"] <= audit["landmark_time"])
    ].copy()
    audit = audit.drop_duplicates(
        ["hadm_id", "chart_time", "store_time", "category", "source_order"]
    )
    delays = audit["documentation_delay_hours"].astype(float).to_numpy()
    if len(delays) == 0:
        raise RuntimeError("No eligible storetime-present notes for fallback-delay freeze")
    quantiles = {
        str(q): float(np.quantile(delays, q, method="linear"))
        for q in (0.50, 0.75, 0.90, 0.95, 0.99)
    }
    q90 = quantiles["0.9"]
    fallback_delay_hours = max(1, int(math.ceil(q90)))

    update_progress(
        current=3, total=5, phase="h6_note_availability_audit",
        message=(
            f"Frozen missing-storetime fallback delay at {fallback_delay_hours}h "
            "from label-free 90th-percentile rule"
        ),
        unit="stage"
    )

    outcome_reports = {}
    for oi, outcome in enumerate(OUTCOMES, start=1):
        pop = populations[outcome]
        primary_note_ids = set(pop.loc[pop["has_note"], "case_id"].astype(str))
        primary_sigs = {
            str(row.case_id): primary_signature(row)
            for row in pop.itertuples(index=False)
            if bool(row.has_note)
        }

        outcome_reports[outcome] = {
            "population_rows": int(len(pop)),
            "primary_note_available_rows": int(len(primary_note_ids)),
            "sensitivities": {},
        }

        for sensitivity in SENSITIVITIES:
            cand = eligible_candidates(
                notes, pop, sensitivity, fallback_delay_hours
            )
            selected = select_latest(cand)
            selected_ids = set(selected["case_id"].astype(str))
            sens_sigs = {
                str(row.case_id): sensitivity_signature(row)
                for row in selected.itertuples(index=False)
            }
            common = primary_note_ids & selected_ids
            same_sig = sum(
                int(primary_sigs[cid] == sens_sigs[cid]) for cid in common
            )
            changed_sig = len(common) - same_sig
            missing_store_selected = int((~selected["storetime_available"]).sum())

            files = write_local_outputs(
                local_root, outcome, sensitivity, selected, pop,
                strip_freeze, fallback_delay_hours
            )

            outcome_reports[outcome]["sensitivities"][sensitivity] = {
                "note_available_rows": int(len(selected)),
                "note_coverage": float(len(selected) / len(pop)),
                "lost_note_rows_vs_primary": int(len(primary_note_ids - selected_ids)),
                "gained_note_rows_vs_primary": int(len(selected_ids - primary_note_ids)),
                "common_note_rows_vs_primary": int(len(common)),
                "same_selected_note_signature_vs_primary": int(same_sig),
                "changed_selected_note_signature_vs_primary": int(changed_sig),
                "selected_missing_storetime_rows": missing_store_selected,
                "selected_storetime_present_rows": int(
                    len(selected) - missing_store_selected
                ),
                **files,
            }

    update_progress(
        current=5, total=5, phase="done",
        message="Completed label-free H6 note-availability timing audit and corpus materialization",
        unit="stage"
    )

    report = {
        "analysis": "Registered v2.1 H6 note-availability timing audit",
        "status": "completed",
        "registration_id": "ahxn9",
        "doi": "10.17605/OSF.IO/AHXN9",
        "outcome_performance_computed": False,
        "semantic_inference_run": False,
        "outcome_labels_used_for_fallback_delay_selection": False,
        "fallback_delay_freeze_rule": {
            "population": (
                "storetime-present normalized bedside notes eligible under the "
                "registered primary availability rule in the union of registered "
                "MetaVision populations"
            ),
            "statistic": "90th percentile of nonnegative max(charttime,storetime)-charttime delay",
            "rounding": "ceil to next whole hour; minimum 1 hour",
            "quantile": FALLBACK_QUANTILE,
            "observed_delay_quantiles_hours": quantiles,
            "eligible_storetime_present_notes_for_delay_distribution": int(len(delays)),
            "frozen_fallback_delay_hours": int(fallback_delay_hours),
        },
        "sensitivity_definitions": {
            "storetime_only": (
                "Require nonmissing storetime; effective availability is "
                "max(charttime,storetime)."
            ),
            "fallback_delay": (
                "Use max(charttime,storetime) when storetime is present; otherwise "
                f"use charttime + {fallback_delay_hours} hours."
            ),
        },
        "note_scan": scan_report,
        "outcomes": outcome_reports,
        "hashes": {
            "analysis_population_contract_sha256": sha256_file(contract_path),
            "language_stripping_freeze_sha256": sha256_file(strip_path),
        },
        "contains_patient_identifiers": False,
        "contains_row_level_data": False,
        "guardrails": [
            "The fallback-delay rule is deterministic and label-free and is fixed before any note-availability outcome-performance inspection.",
            "Cohort membership, outcome labels, structured physiology, treatment context, and frozen patient-grouped split assignments are not changed by this audit.",
            "Both registered note-availability sensitivities are materialized locally before semantic inference.",
            "The same frozen language-stripping vocabulary and replacement are applied to alternative selected notes.",
            "No semantic model, TF-IDF model, or clinical prediction model is run.",
            "Row-level note timing and text remain local; the declared artifact contains only aggregate counts, hashes, and the frozen fallback-delay value.",
        ],
    }
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
