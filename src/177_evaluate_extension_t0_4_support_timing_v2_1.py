from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from common import find_file, lower_columns, module_path, parse_datetime, read_columns, resolve_root
from registration_gate import require_osf_registration
from runrelay_progress import update_progress


BASE = Path("data/real_mimic_local/population_landmark12_v2_1")
POPULATION_CONTRACT = Path("config/v2_1_analysis_population_contract.json")
CONTEXT_FREEZE = Path("config/v2_1_context_feature_freeze.json")
ATTESTATION = Path("docs/registration/exploratory_extension_osf_upload_attestation_2026-10-05.md")
T0_4_CLARIFICATION = Path(
    "docs/registration/exploratory_extension_t0_4_support_timing_clarification_2026-10-06.md"
)
FIO2_DEVIATION = Path(
    "docs/registration/exploratory_extension_t0_4_fio2_definition_deviation_2026-10-06.md"
)

OUTCOMES = (
    ("invasive_ventilation", 20261031),
    ("renal_replacement_therapy", 20261032),
    ("icu_death", 20261033),
)
PAIR_SPECS = {
    "vasoactive_start": "hemodynamic_concern",
    "high_flow_start": "respiratory_concern",
    "niv_start": "respiratory_concern",
}
WASHOUT_H = 6.0
WINDOW_H = 12.0
BOOTSTRAP_TARGET = 2000
BOOTSTRAP_SEED = 20261006
MAX_REPLACEMENT_FRACTION = 0.05


def load_numbered_module(filename: str, name: str):
    path = Path(__file__).with_name(filename)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {filename}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


align = load_numbered_module(
    "159_audit_semantic_alignment_v2_1.py",
    "extension_t0_4_alignment",
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_note_frame(outcome: str, shuffle_seed: int, population: dict) -> tuple[pd.DataFrame, dict]:
    expected = population["confirmatory_outcomes"][outcome]
    if str(expected["source"]).strip().lower() != "metavision":
        raise RuntimeError(f"{outcome}: T0.4 primary population must be MetaVision")

    index_path = BASE / outcome / "population_index_local.csv"
    semantic_path = BASE / outcome / "openjev_registered_v2_1_raw_local.jsonl"
    wanted = {
        "case_id",
        "subject_id",
        "icustay_id",
        "dbsource",
        "landmark_time",
        "has_note",
        "note_time",
    }
    idx = pd.read_csv(index_path, usecols=lambda c: c in wanted, low_memory=False)
    missing = wanted - set(idx.columns)
    if missing:
        raise RuntimeError(f"{outcome}: population index missing {sorted(missing)}")
    idx["case_id"] = idx["case_id"].astype(str)
    idx["subject_id"] = pd.to_numeric(idx["subject_id"], errors="raise").astype("int64")
    idx["icustay_id"] = pd.to_numeric(idx["icustay_id"], errors="raise").astype("int64")
    idx["dbsource"] = idx["dbsource"].fillna("unknown").astype(str).str.strip().str.lower()
    idx["landmark_time"] = pd.to_datetime(idx["landmark_time"], errors="raise")
    idx["note_time"] = pd.to_datetime(idx["note_time"], errors="coerce")
    idx["has_note"] = pd.to_numeric(idx["has_note"], errors="raise").astype(int)
    idx = idx[idx["dbsource"].eq("metavision") & idx["has_note"].eq(1)].copy()
    if idx["note_time"].isna().any():
        raise RuntimeError(f"{outcome}: note-available row missing prospective note_time")
    if len(idx) != int(expected["note_available_rows"]):
        raise RuntimeError(
            f"{outcome}: note rows {len(idx)} != frozen {expected['note_available_rows']}"
        )
    if idx["case_id"].duplicated().any():
        raise RuntimeError(f"{outcome}: duplicate case_id in note frame")

    sem = align.load_semantics(semantic_path)
    if set(sem["case_id"]) != set(idx["case_id"]):
        raise RuntimeError(f"{outcome}: semantic/index case_id mismatch")
    frame = idx.merge(
        sem[["case_id", *align.SEMANTIC_NAMES]],
        on="case_id",
        how="inner",
        validate="one_to_one",
    )
    frame["icu_intime"] = frame["landmark_time"] - pd.to_timedelta(12.0, unit="h")
    if (frame["note_time"] < frame["icu_intime"]).any():
        raise RuntimeError(f"{outcome}: selected note precedes inferred ICU intime")

    donor = align.between_patient_permutation(
        frame["subject_id"].to_numpy(),
        seed=int(shuffle_seed),
    )
    for construct in set(PAIR_SPECS.values()):
        frame[f"{construct}_shuffled"] = (
            frame[construct].to_numpy(dtype=float)[donor]
        )

    hashes = {
        "population_index_sha256": sha256_file(index_path),
        "semantics_sha256": sha256_file(semantic_path),
    }
    return frame, hashes


def load_vasoactive_intervals(root: Path, wanted_icu: set[int], freeze: dict) -> pd.DataFrame:
    ids = set()
    for agent_ids in freeze["treatment"]["vasoactive"]["metavision"].values():
        ids |= {int(x) for x in agent_ids}

    f = find_file(
        module_path(root, "mimiciii"),
        ["INPUTEVENTS_MV.csv.gz", "INPUTEVENTS_MV.csv"],
    )
    if f is None:
        raise FileNotFoundError("INPUTEVENTS_MV not found")

    parts = []
    for chunk in read_columns(
        f,
        ["icustay_id", "itemid", "starttime", "endtime", "rate", "statusdescription"],
        chunksize=250_000,
    ):
        c = lower_columns(chunk)
        c["icustay_id"] = pd.to_numeric(c["icustay_id"], errors="coerce")
        c["itemid"] = pd.to_numeric(c["itemid"], errors="coerce")
        c = c[c["icustay_id"].isin(wanted_icu) & c["itemid"].isin(ids)].copy()
        if c.empty:
            continue
        bad = c["statusdescription"].fillna("").astype(str).str.lower().str.contains(
            "rewritten|cancelled", regex=True, na=False
        )
        c = c[~bad].copy()
        c["starttime"] = parse_datetime(c["starttime"])
        c["endtime"] = parse_datetime(c["endtime"])
        c["rate"] = pd.to_numeric(c["rate"], errors="coerce")
        c = c.dropna(subset=["icustay_id", "starttime", "endtime"])
        c = c[c["rate"].isna() | c["rate"].gt(0)].copy()
        c["icustay_id"] = c["icustay_id"].astype("int64")
        parts.append(c[["icustay_id", "starttime", "endtime"]])
    if not parts:
        return pd.DataFrame(columns=["icustay_id", "starttime", "endtime"])
    return pd.concat(parts, ignore_index=True)


def load_respiratory_positive_events(
    root: Path,
    wanted_icu: set[int],
    freeze: dict,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    resp = freeze["treatment"]["respiratory"]
    device_ids = {int(x) for x in resp["oxygen_device"]["metavision"]}
    niv_ids = {int(x) for x in resp["niv_items"]["metavision"]}
    all_ids = device_ids | niv_ids
    high_rx = str(resp["high_flow_regex"])
    niv_rx = str(resp["niv_device_regex"])

    f = find_file(
        module_path(root, "mimiciii"),
        ["CHARTEVENTS.csv.gz", "CHARTEVENTS.csv"],
    )
    if f is None:
        raise FileNotFoundError("CHARTEVENTS not found")

    high_parts = []
    niv_parts = []
    for chunk in read_columns(
        f,
        ["icustay_id", "itemid", "charttime", "value", "error"],
        chunksize=500_000,
    ):
        c = lower_columns(chunk)
        c["icustay_id"] = pd.to_numeric(c["icustay_id"], errors="coerce")
        c["itemid"] = pd.to_numeric(c["itemid"], errors="coerce")
        c = c[c["icustay_id"].isin(wanted_icu) & c["itemid"].isin(all_ids)].copy()
        if c.empty:
            continue
        bad = pd.to_numeric(
            c.get("error", pd.Series(0, index=c.index)),
            errors="coerce",
        ).fillna(0).ne(0)
        c = c[~bad].copy()
        c["charttime"] = parse_datetime(c["charttime"])
        c = c.dropna(subset=["icustay_id", "itemid", "charttime"])
        c["icustay_id"] = c["icustay_id"].astype("int64")
        c["itemid"] = c["itemid"].astype(int)

        dq = c[c["itemid"].isin(device_ids)].copy()
        if not dq.empty:
            vals = dq["value"].fillna("").astype(str).str.strip().str.lower()
            h = dq[vals.str.contains(high_rx, regex=True, na=False)]
            n = dq[vals.str.contains(niv_rx, regex=True, na=False)]
            if not h.empty:
                high_parts.append(h[["icustay_id", "charttime"]])
            if not n.empty:
                niv_parts.append(n[["icustay_id", "charttime"]])

        nq = c[c["itemid"].isin(niv_ids)]
        if not nq.empty:
            niv_parts.append(nq[["icustay_id", "charttime"]])

    high = (
        pd.concat(high_parts, ignore_index=True).drop_duplicates()
        if high_parts
        else pd.DataFrame(columns=["icustay_id", "charttime"])
    )
    niv = (
        pd.concat(niv_parts, ignore_index=True).drop_duplicates()
        if niv_parts
        else pd.DataFrame(columns=["icustay_id", "charttime"])
    )
    return high, niv


def vaso_episode_map(
    intervals: pd.DataFrame,
    icu_intime: dict[int, pd.Timestamp],
) -> tuple[dict[int, list[pd.Timestamp]], dict[int, list[tuple[pd.Timestamp, pd.Timestamp]]]]:
    transitions: dict[int, list[pd.Timestamp]] = {}
    merged_intervals: dict[int, list[tuple[pd.Timestamp, pd.Timestamp]]] = {}
    washout = pd.to_timedelta(WASHOUT_H, unit="h")

    for icu, q in intervals.groupby("icustay_id"):
        rows = q.sort_values(["starttime", "endtime"])[["starttime", "endtime"]].itertuples(index=False)
        episodes: list[list[pd.Timestamp]] = []
        for start, end in rows:
            start = pd.Timestamp(start)
            end = pd.Timestamp(end)
            if end <= start:
                continue
            if not episodes:
                episodes.append([start, end])
            else:
                prev = episodes[-1]
                if start - prev[1] < washout:
                    if end > prev[1]:
                        prev[1] = end
                else:
                    episodes.append([start, end])
        eps = [(x[0], x[1]) for x in episodes]
        merged_intervals[int(icu)] = eps
        intime = icu_intime.get(int(icu))
        t = []
        if intime is not None:
            for start, _end in eps:
                if start - intime >= washout:
                    t.append(start)
        transitions[int(icu)] = t
    return transitions, merged_intervals


def evidence_transition_map(
    events: pd.DataFrame,
    icu_intime: dict[int, pd.Timestamp],
) -> tuple[dict[int, list[pd.Timestamp]], dict[int, list[pd.Timestamp]]]:
    transitions: dict[int, list[pd.Timestamp]] = {}
    positives: dict[int, list[pd.Timestamp]] = {}
    washout = pd.to_timedelta(WASHOUT_H, unit="h")

    for icu, q in events.groupby("icustay_id"):
        ts = sorted(pd.Timestamp(x) for x in q["charttime"].dropna().unique())
        positives[int(icu)] = ts
        intime = icu_intime.get(int(icu))
        out = []
        prev = None
        for t in ts:
            if intime is None or t - intime < washout:
                prev = t
                continue
            if prev is None or t - prev >= washout:
                out.append(t)
            prev = t
        transitions[int(icu)] = out
    return transitions, positives


def transition_category(note_time: pd.Timestamp, transitions: list[pd.Timestamp]) -> str:
    if not transitions:
        return "neither"
    note = pd.Timestamp(note_time)
    lower = note - pd.to_timedelta(WINDOW_H, unit="h")
    upper = note + pd.to_timedelta(WINDOW_H, unit="h")
    prior = any(lower <= t <= note for t in transitions)
    subsequent = any(note < t <= upper for t in transitions)
    if prior and subsequent:
        return "both"
    if prior:
        return "prior_only"
    if subsequent:
        return "subsequent_only"
    return "neither"


def ongoing_vaso(note_time: pd.Timestamp, intervals: list[tuple[pd.Timestamp, pd.Timestamp]]) -> bool:
    note = pd.Timestamp(note_time)
    return any(start <= note < end for start, end in intervals)


def ongoing_evidence(note_time: pd.Timestamp, positives: list[pd.Timestamp]) -> bool:
    note = pd.Timestamp(note_time)
    lower = note - pd.to_timedelta(WASHOUT_H, unit="h")
    return any(lower <= t <= note for t in positives)


def distribution(categories: pd.Series) -> dict:
    order = ("prior_only", "subsequent_only", "both", "neither")
    n = int(len(categories))
    counts = {k: int((categories == k).sum()) for k in order}
    return {
        "n": n,
        "counts": counts,
        "percentages": {
            k: (float(v / n) if n else None) for k, v in counts.items()
        },
    }


def primary_bootstrap(
    frame: pd.DataFrame,
    high_mask: np.ndarray,
    categories: np.ndarray,
) -> dict:
    high = np.asarray(high_mask, dtype=bool)
    cats = np.asarray(categories, dtype=object)
    any_transition = cats != "neither"
    subsequent_only = cats == "subsequent_only"

    work = pd.DataFrame(
        {
            "subject_id": frame["subject_id"].to_numpy(dtype=np.int64),
            "den": (high & any_transition).astype(int),
            "num": (high & subsequent_only).astype(int),
        }
    )
    agg = work.groupby("subject_id", as_index=False)[["den", "num"]].sum()
    if int(agg["den"].sum()) == 0:
        raise RuntimeError("No high-score notes with any qualifying transition")

    subjects = agg["subject_id"].to_numpy(dtype=np.int64)
    den = agg["den"].to_numpy(dtype=int)
    num = agg["num"].to_numpy(dtype=int)
    n_subjects = len(subjects)
    children = np.random.SeedSequence(BOOTSTRAP_SEED).spawn(
        BOOTSTRAP_TARGET + int(math.floor(BOOTSTRAP_TARGET * MAX_REPLACEMENT_FRACTION)) + 20
    )
    values = []
    replacements = 0
    child_index = 0
    while len(values) < BOOTSTRAP_TARGET:
        child = children[child_index]
        child_index += 1
        rng = np.random.default_rng(child)
        draw = rng.integers(0, n_subjects, size=n_subjects)
        d = int(den[draw].sum())
        if d == 0:
            replacements += 1
            if replacements > int(math.floor(BOOTSTRAP_TARGET * MAX_REPLACEMENT_FRACTION)):
                raise RuntimeError("T0.4 bootstrap replacement cap exceeded")
            continue
        values.append(float(num[draw].sum() / d))

    arr = np.asarray(values, dtype=float)
    lo, hi = np.quantile(arr, [0.025, 0.975])
    observed = float(num.sum() / den.sum())
    return {
        "observed_subsequent_only_proportion": observed,
        "high_score_notes_with_any_transition": int(den.sum()),
        "subsequent_only_high_score_notes": int(num.sum()),
        "bootstrap_valid_replicates": int(len(values)),
        "bootstrap_replacements_zero_denominator": int(replacements),
        "bootstrap_unit": "source_patient",
        "bootstrap_seed": BOOTSTRAP_SEED,
        "ci95_percentile": [float(lo), float(hi)],
    }


def summarize_pair(
    frame: pd.DataFrame,
    construct: str,
    transition_map: dict[int, list[pd.Timestamp]],
    ongoing_map,
    *,
    shuffled_col: str,
) -> dict:
    categories = np.asarray(
        [
            transition_category(nt, transition_map.get(int(icu), []))
            for icu, nt in zip(frame["icustay_id"], frame["note_time"])
        ],
        dtype=object,
    )
    ongoing = np.asarray(
        [
            bool(ongoing_map(int(icu), pd.Timestamp(nt)))
            for icu, nt in zip(frame["icustay_id"], frame["note_time"])
        ],
        dtype=bool,
    )

    score = pd.to_numeric(frame[construct], errors="raise").to_numpy(dtype=float)
    shuffled = pd.to_numeric(frame[shuffled_col], errors="raise").to_numpy(dtype=float)
    q1, q3 = np.quantile(score, [0.25, 0.75])
    groups = {
        "real_high": score >= q3,
        "real_low": score <= q1,
        "shuffled_high": shuffled >= q3,
        "shuffled_low": shuffled <= q1,
    }

    out_groups = {}
    for name, mask in groups.items():
        c = pd.Series(categories[mask], dtype="object")
        n = int(mask.sum())
        out_groups[name] = {
            "score_group_n": n,
            "transition_distribution": distribution(c),
            "ongoing_support": {
                "n": n,
                "count": int(ongoing[mask].sum()),
                "prevalence": float(ongoing[mask].mean()) if n else None,
            },
        }

    return {
        "construct": construct,
        "quartile_cutoffs": {"q25": float(q1), "q75": float(q3)},
        "groups": out_groups,
        "primary_high_score_summary": primary_bootstrap(
            frame, groups["real_high"], categories
        ),
    }


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Paper 1 extension T0.4 label-free note timing relative to frozen "
            "MetaVision vasoactive, high-flow, and NIV support transitions."
        )
    )
    ap.add_argument("--root", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    require_osf_registration()
    for gate in (ATTESTATION, T0_4_CLARIFICATION, FIO2_DEVIATION):
        if not gate.exists():
            raise RuntimeError(f"Required T0.4 gate missing: {gate}")

    root = resolve_root(args.root)
    population = json.loads(POPULATION_CONTRACT.read_text(encoding="utf-8"))
    freeze = json.loads(CONTEXT_FREEZE.read_text(encoding="utf-8"))

    frames = {}
    hashes = {}
    all_icu = set()
    icu_intime: dict[int, pd.Timestamp] = {}
    for outcome, seed in OUTCOMES:
        frame, h = load_note_frame(outcome, seed, population)
        frames[outcome] = frame
        hashes[outcome] = h
        all_icu |= set(frame["icustay_id"].astype(int))
        for row in frame[["icustay_id", "icu_intime"]].drop_duplicates().itertuples(index=False):
            icu = int(row.icustay_id)
            t = pd.Timestamp(row.icu_intime)
            if icu in icu_intime and icu_intime[icu] != t:
                raise RuntimeError("Conflicting inferred ICU intime across outcome frames")
            icu_intime[icu] = t

    update_progress(
        current=1, total=4, phase="extension_t0_4_support_timing",
        message="Loaded frozen note/semantic populations without outcome labels", unit="stage"
    )
    vaso = load_vasoactive_intervals(root, all_icu, freeze)
    vaso_trans, vaso_intervals = vaso_episode_map(vaso, icu_intime)

    update_progress(
        current=2, total=4, phase="extension_t0_4_support_timing",
        message="Built MetaVision vasoactive support episodes", unit="stage"
    )
    high, niv = load_respiratory_positive_events(root, all_icu, freeze)
    high_trans, high_positive = evidence_transition_map(high, icu_intime)
    niv_trans, niv_positive = evidence_transition_map(niv, icu_intime)

    update_progress(
        current=3, total=4, phase="extension_t0_4_support_timing",
        message="Built frozen high-flow and NIV chart-evidence transitions", unit="stage"
    )

    results = {}
    for outcome, seed in OUTCOMES:
        frame = frames[outcome]
        vaso_ongoing = lambda icu, nt: ongoing_vaso(nt, vaso_intervals.get(icu, []))
        high_ongoing = lambda icu, nt: ongoing_evidence(nt, high_positive.get(icu, []))
        niv_ongoing = lambda icu, nt: ongoing_evidence(nt, niv_positive.get(icu, []))

        results[outcome] = {
            "source": "metavision",
            "note_available_rows": int(len(frame)),
            "note_available_patients": int(frame["subject_id"].nunique()),
            "outcome_labels_read": False,
            "between_patient_shuffle_seed": int(seed),
            "pairs": {
                "vasoactive_start": summarize_pair(
                    frame,
                    "hemodynamic_concern",
                    vaso_trans,
                    vaso_ongoing,
                    shuffled_col="hemodynamic_concern_shuffled",
                ),
                "high_flow_start": summarize_pair(
                    frame,
                    "respiratory_concern",
                    high_trans,
                    high_ongoing,
                    shuffled_col="respiratory_concern_shuffled",
                ),
                "niv_start": summarize_pair(
                    frame,
                    "respiratory_concern",
                    niv_trans,
                    niv_ongoing,
                    shuffled_col="respiratory_concern_shuffled",
                ),
            },
            "input_hashes": hashes[outcome],
        }

    report = {
        "analysis": "Paper 1 exploratory extension T0.4 support-transition timing",
        "status": "completed",
        "extension_status": "post-registration exploratory",
        "parent_registration": "ahxn9",
        "extension_osf_project": "wmyb2",
        "outcome_labels_read": False,
        "window_hours_each_side": WINDOW_H,
        "support_free_washout_hours": WASHOUT_H,
        "bootstrap_replicates": BOOTSTRAP_TARGET,
        "fio2_transition_arm": {
            "status": "not_performed",
            "reason": (
                "Parent protocol referenced a nonexistent frozen FiO2 step-up definition; "
                "no post-hoc threshold was invented."
            ),
            "deviation_file": str(FIO2_DEVIATION),
        },
        "results": results,
        "source_event_counts": {
            "vasoactive_interval_rows": int(len(vaso)),
            "high_flow_positive_event_rows": int(len(high)),
            "niv_positive_event_rows": int(len(niv)),
        },
        "input_hashes": {
            "population_contract_sha256": sha256_file(POPULATION_CONTRACT),
            "context_freeze_sha256": sha256_file(CONTEXT_FREEZE),
            "t0_4_clarification_sha256": sha256_file(T0_4_CLARIFICATION),
            "fio2_deviation_sha256": sha256_file(FIO2_DEVIATION),
            "osf_upload_attestation_sha256": sha256_file(ATTESTATION),
        },
        "guardrails": [
            "No outcome label or outcome event time is read.",
            "Support definitions reuse the frozen MetaVision comparator mappings.",
            "High-flow/NIV timing is explicitly chart-evidence timing, not continuously observed device state.",
            "The FiO2 arm is omitted rather than assigned a post-hoc threshold.",
            "This analysis is descriptive and does not support a causal or predictive claim.",
            "Only aggregate timing summaries leave the workstation.",
        ],
    }

    update_progress(
        current=4, total=4, phase="extension_t0_4_support_timing",
        message="Completed aggregate label-free T0.4 timing analysis", unit="stage"
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "completed", "output": str(output)}, indent=2))


if __name__ == "__main__":
    main()
