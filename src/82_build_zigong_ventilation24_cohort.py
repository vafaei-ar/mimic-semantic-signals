from __future__ import annotations

import argparse
import json
import random
import re
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

from runrelay_progress import update_progress


CSV_ENCODINGS = ["utf-8-sig", "utf-8", "gb18030"]
LEAK_RX = re.compile(
    r"插管|气管|气切|呼吸机|机械通气|拔管|拔除|"
    r"intubat|endotracheal|tracheost|ventilat|extubat|\\bETT\\b",
    re.IGNORECASE,
)


def read_csv_robust(path: Path, **kwargs) -> pd.DataFrame:
    last = None
    for enc in CSV_ENCODINGS:
        try:
            return pd.read_csv(path, encoding=enc, **kwargs)
        except UnicodeDecodeError as exc:
            last = exc
    if last is not None:
        raise last
    return pd.read_csv(path, **kwargs)


def iter_csv_robust(path: Path, chunksize: int, **kwargs):
    last = None
    for enc in CSV_ENCODINGS:
        first = True
        try:
            reader = pd.read_csv(path, encoding=enc, chunksize=chunksize, **kwargs)
            for chunk in reader:
                first = False
                yield chunk
            return
        except UnicodeDecodeError as exc:
            if not first:
                raise
            last = exc
    if last is not None:
        raise last


def find_one(root: Path, name: str) -> Path:
    hits = [p for p in root.rglob(name) if not p.name.startswith("._")]
    if len(hits) != 1:
        raise RuntimeError(f"Expected exactly one {name} under {root}; found {len(hits)}")
    return hits[0]


def clean_note(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return None
    if LEAK_RX.search(text):
        return None
    return text


def is_true(value: object) -> bool:
    if value is None or pd.isna(value):
        return False
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def numeric(value: object) -> float | None:
    try:
        x = float(value)
    except (TypeError, ValueError):
        return None
    return x if np.isfinite(x) else None


def qualifies_event(row: dict) -> bool:
    a = numeric(row.get("Endotracheal_intubation"))
    b = numeric(row.get("Endotracheal_intubation_Depth"))
    depth = a if a is not None else b
    vt = numeric(row.get("Vt_setting"))
    return (
        depth is not None
        and 10.0 <= depth <= 40.0
        and vt is not None
        and 100.0 <= vt <= 1000.0
    )


def qstats(values) -> dict:
    x = pd.to_numeric(pd.Series(list(values), dtype="float64"), errors="coerce").dropna()
    if x.empty:
        return {"n": 0}
    return {
        "n": int(len(x)),
        "p05": float(x.quantile(0.05)),
        "p25": float(x.quantile(0.25)),
        "median": float(x.median()),
        "p75": float(x.quantile(0.75)),
        "p95": float(x.quantile(0.95)),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Build frozen local Zigong 24h ventilation narrative risk set.")
    ap.add_argument("--root", required=True)
    ap.add_argument("--local-output-dir", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--washout-hours", type=float, default=6.0)
    ap.add_argument("--horizon-hours", type=float, default=24.0)
    ap.add_argument("--controls-per-case", type=int, default=3)
    ap.add_argument("--matching-seed", type=int, default=20260924)
    ap.add_argument("--preferred-match-hours", type=float, default=6.0)
    ap.add_argument("--max-match-hours", type=float, default=12.0)
    args = ap.parse_args()

    root = Path(args.root).expanduser().resolve()
    local_out = Path(args.local_output_dir).expanduser().resolve()
    manifest_path = Path(args.manifest).expanduser().resolve()
    local_out.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    nursing_path = find_one(root, "dtNursingChart.csv")
    baseline_path = find_one(root, "dtBaseline.csv")

    baseline = read_csv_robust(
        baseline_path,
        usecols=lambda c: c in {"PATIENT_ID", "INP_NO"},
        low_memory=False,
    )
    baseline["PATIENT_ID"] = pd.to_numeric(baseline["PATIENT_ID"], errors="coerce")
    baseline["INP_NO"] = pd.to_numeric(baseline["INP_NO"], errors="coerce")
    baseline = baseline.dropna(subset=["PATIENT_ID", "INP_NO"]).copy()
    baseline["PATIENT_ID"] = baseline["PATIENT_ID"].astype("int64")
    baseline["INP_NO"] = baseline["INP_NO"].astype("int64")
    inp_to_patient = dict(zip(baseline["INP_NO"], baseline["PATIENT_ID"]))
    valid_inp = set(inp_to_patient)

    update_progress(current=1, total=5, phase="event_scan", message="Scanning frozen within-nursing ventilation events", unit="stage")
    t0: dict[int, float] = {}
    tmax: dict[int, float] = {}
    first_event: dict[int, float] = {}
    first_extubation: dict[int, float] = {}

    event_cols = {
        "INP_NO",
        "ChartTime",
        "Endotracheal_intubation",
        "Endotracheal_intubation_Depth",
        "Vt_setting",
        "Extubation",
    }
    for chunk in iter_csv_robust(
        nursing_path,
        100_000,
        usecols=lambda c: c in event_cols,
        low_memory=False,
    ):
        chunk["INP_NO"] = pd.to_numeric(chunk["INP_NO"], errors="coerce")
        chunk["ChartTime"] = pd.to_numeric(chunk["ChartTime"], errors="coerce")
        chunk = chunk.dropna(subset=["INP_NO", "ChartTime"]).copy()
        if chunk.empty:
            continue
        chunk["INP_NO"] = chunk["INP_NO"].astype("int64")
        chunk = chunk[chunk["INP_NO"].isin(valid_inp)]
        for row in chunk.itertuples(index=False):
            rec = row._asdict()
            inp = int(rec["INP_NO"])
            tm = float(rec["ChartTime"])
            old0 = t0.get(inp)
            if old0 is None or tm < old0:
                t0[inp] = tm
            oldmax = tmax.get(inp)
            if oldmax is None or tm > oldmax:
                tmax[inp] = tm
            if qualifies_event(rec):
                old = first_event.get(inp)
                if old is None or tm < old:
                    first_event[inp] = tm
            if is_true(rec.get("Extubation")):
                old = first_extubation.get(inp)
                if old is None or tm < old:
                    first_extubation[inp] = tm

    event_after_washout = {
        inp: ev
        for inp, ev in first_event.items()
        if inp in t0 and (ev - t0[inp]) >= args.washout_hours
    }
    event_after_extubation_rule = {
        inp: ev
        for inp, ev in event_after_washout.items()
        if first_extubation.get(inp) is None or first_extubation[inp] >= ev
    }

    update_progress(current=2, total=5, phase="note_scan", message="Selecting leakage-clean case notes and control note candidates", unit="stage")
    case_best: dict[int, tuple[float, str]] = {}
    control_note_times: dict[int, list[float]] = defaultdict(list)

    note_cols = {"INP_NO", "ChartTime", "NURSING_DESC"}
    for chunk in iter_csv_robust(
        nursing_path,
        100_000,
        usecols=lambda c: c in note_cols,
        low_memory=False,
    ):
        chunk["INP_NO"] = pd.to_numeric(chunk["INP_NO"], errors="coerce")
        chunk["ChartTime"] = pd.to_numeric(chunk["ChartTime"], errors="coerce")
        chunk = chunk.dropna(subset=["INP_NO", "ChartTime", "NURSING_DESC"]).copy()
        if chunk.empty:
            continue
        chunk["INP_NO"] = chunk["INP_NO"].astype("int64")
        chunk = chunk[chunk["INP_NO"].isin(valid_inp)]
        for row in chunk.itertuples(index=False):
            inp = int(row.INP_NO)
            tm = float(row.ChartTime)
            text = clean_note(row.NURSING_DESC)
            if text is None:
                continue

            ev = event_after_extubation_rule.get(inp)
            if ev is not None and (ev - args.horizon_hours) <= tm < ev:
                old = case_best.get(inp)
                if old is None or tm > old[0] or (tm == old[0] and len(text) > len(old[1])):
                    case_best[inp] = (tm, text)

            # Controls can later develop the event, but not during the 24h horizon.
            if inp not in t0 or inp not in tmax:
                continue
            if tmax[inp] < tm + args.horizon_hours:
                continue
            first_ev = first_event.get(inp)
            if first_ev is not None and first_ev <= tm + args.horizon_hours:
                continue
            control_note_times[inp].append(tm)

    case_inp = sorted(case_best)
    case_patients = {inp_to_patient[inp] for inp in case_inp}

    # Remove all case patients from control candidates and deduplicate note times.
    control_by_patient: dict[int, list[tuple[float, int, float]]] = defaultdict(list)
    for inp, times in control_note_times.items():
        patient = inp_to_patient[inp]
        if patient in case_patients or inp not in t0:
            continue
        seen = set()
        for tm in times:
            key = round(float(tm), 6)
            if key in seen:
                continue
            seen.add(key)
            rel = float(tm - t0[inp])
            if rel < 0:
                continue
            control_by_patient[patient].append((rel, inp, float(tm)))

    rng = random.Random(args.matching_seed)
    update_progress(current=3, total=5, phase="matching", message="Matching 1:3 patient-unique control risk sets", unit="stage")
    used_control_patients: set[int] = set()
    matched_sets = []
    match_distances = []

    case_rows = []
    for inp in case_inp:
        patient = inp_to_patient[inp]
        ev = event_after_extubation_rule[inp]
        note_tm, text = case_best[inp]
        note_rel = float(note_tm - t0[inp])
        event_rel = float(ev - t0[inp])
        lead = float(ev - note_tm)
        case_rows.append({
            "inp": inp,
            "patient": patient,
            "event_abs": ev,
            "event_rel": event_rel,
            "note_abs": note_tm,
            "note_rel": note_rel,
            "lead": lead,
            "text": text,
        })

    # Match harder/later cases first to reduce greedy loss.
    case_rows.sort(key=lambda x: (-x["note_rel"], x["patient"], x["inp"]))

    for case in case_rows:
        candidates = []
        for patient, notes in control_by_patient.items():
            if patient in used_control_patients:
                continue
            best = None
            for rel, inp, tm in notes:
                diff = abs(rel - case["note_rel"])
                if diff > args.max_match_hours:
                    continue
                item = (0 if diff <= args.preferred_match_hours else 1, diff, rel, inp, tm)
                if best is None or item < best:
                    best = item
            if best is not None:
                candidates.append((best[0], best[1], rng.random(), patient, best[2], best[3], best[4]))

        candidates.sort()
        take = candidates[: args.controls_per_case]
        if len(take) < args.controls_per_case:
            continue
        set_id = len(matched_sets) + 1
        controls = []
        for bucket, diff, jitter, patient, rel, inp, tm in take:
            controls.append({
                "patient": int(patient),
                "inp": int(inp),
                "note_rel": float(rel),
                "note_abs": float(tm),
                "match_distance": float(diff),
            })
            used_control_patients.add(int(patient))
            match_distances.append(float(diff))
        matched_sets.append({"match_set": set_id, "case": case, "controls": controls})

    if not matched_sets:
        raise RuntimeError("No fully matched Zigong ventilation risk sets were found.")

    update_progress(current=4, total=5, phase="control_text", message="Retrieving selected leakage-clean control narratives", unit="stage")
    selected_control_keys = {
        (c["inp"], round(c["note_abs"], 6))
        for ms in matched_sets
        for c in ms["controls"]
    }
    control_texts: dict[tuple[int, float], str] = {}
    for chunk in iter_csv_robust(
        nursing_path,
        100_000,
        usecols=lambda c: c in note_cols,
        low_memory=False,
    ):
        chunk["INP_NO"] = pd.to_numeric(chunk["INP_NO"], errors="coerce")
        chunk["ChartTime"] = pd.to_numeric(chunk["ChartTime"], errors="coerce")
        chunk = chunk.dropna(subset=["INP_NO", "ChartTime", "NURSING_DESC"]).copy()
        if chunk.empty:
            continue
        chunk["INP_NO"] = chunk["INP_NO"].astype("int64")
        for row in chunk.itertuples(index=False):
            key = (int(row.INP_NO), round(float(row.ChartTime), 6))
            if key not in selected_control_keys:
                continue
            text = clean_note(row.NURSING_DESC)
            if text is None:
                continue
            old = control_texts.get(key)
            if old is None or len(text) > len(old):
                control_texts[key] = text

    missing_control_text = selected_control_keys - set(control_texts)
    if missing_control_text:
        raise RuntimeError(f"Failed to recover {len(missing_control_text)} selected control notes.")

    selected_patients = sorted(
        {ms["case"]["patient"] for ms in matched_sets}
        | {c["patient"] for ms in matched_sets for c in ms["controls"]}
    )
    patient_map = {p: f"zp{i:05d}" for i, p in enumerate(selected_patients, 1)}

    local_rows = []
    json_rows = []
    for ms in matched_sets:
        set_id = int(ms["match_set"])
        case = ms["case"]
        case_id = f"zv24_{set_id:04d}_case"
        local_rows.append({
            "case_id": case_id,
            "label": 1,
            "match_set": set_id,
            "patient_group": patient_map[case["patient"]],
            "PATIENT_ID": case["patient"],
            "INP_NO": case["inp"],
            "note_time": case["note_abs"],
            "note_elapsed_hours": case["note_rel"],
            "event_time": case["event_abs"],
            "event_elapsed_hours": case["event_rel"],
            "hours_before_event": case["lead"],
        })
        json_rows.append({
            "case_id": case_id,
            "synthetic_only": False,
            "local_only": True,
            "model_state": {"clinical_note": case["text"]},
            "metadata": {
                "analysis": "zigong_external_ventilation24_v1",
                "outcome": "invasive_ventilation_24h",
                "label": 1,
                "match_set": set_id,
                "patient_group": patient_map[case["patient"]],
                "note_category": "zigong_nursing_desc",
                "language": "zh",
                "note_elapsed_hours": round(case["note_rel"], 3),
                "hours_before_event": round(case["lead"], 3),
                "prediction_horizon_hours": float(args.horizon_hours),
                "time_basis": "within_dtNursingChart_relative_to_first_timed_row",
                "leakage_screened": True,
                "note_characters": len(case["text"]),
            },
            "gold": None,
        })

        for j, ctrl in enumerate(ms["controls"], 1):
            key = (ctrl["inp"], round(ctrl["note_abs"], 6))
            text = control_texts[key]
            cid = f"zv24_{set_id:04d}_ctrl{j}"
            local_rows.append({
                "case_id": cid,
                "label": 0,
                "match_set": set_id,
                "patient_group": patient_map[ctrl["patient"]],
                "PATIENT_ID": ctrl["patient"],
                "INP_NO": ctrl["inp"],
                "note_time": ctrl["note_abs"],
                "note_elapsed_hours": ctrl["note_rel"],
                "event_time": np.nan,
                "event_elapsed_hours": np.nan,
                "hours_before_event": np.nan,
            })
            json_rows.append({
                "case_id": cid,
                "synthetic_only": False,
                "local_only": True,
                "model_state": {"clinical_note": text},
                "metadata": {
                    "analysis": "zigong_external_ventilation24_v1",
                    "outcome": "invasive_ventilation_24h",
                    "label": 0,
                    "match_set": set_id,
                    "patient_group": patient_map[ctrl["patient"]],
                    "note_category": "zigong_nursing_desc",
                    "language": "zh",
                    "note_elapsed_hours": round(ctrl["note_rel"], 3),
                    "prediction_horizon_hours": float(args.horizon_hours),
                    "time_basis": "within_dtNursingChart_relative_to_first_timed_row",
                    "leakage_screened": True,
                    "note_characters": len(text),
                },
                "gold": None,
            })

    local_df = pd.DataFrame(local_rows)
    local_df.to_csv(local_out / "snapshot_index_local.csv", index=False)
    with (local_out / "cases.jsonl").open("w", encoding="utf-8") as f:
        for rec in json_rows:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    labels = np.asarray([r["metadata"]["label"] for r in json_rows], dtype=int)
    texts = [r["model_state"]["clinical_note"] for r in json_rows]
    groups_case = {r["metadata"]["patient_group"] for r in json_rows if r["metadata"]["label"] == 1}
    groups_ctrl = {r["metadata"]["patient_group"] for r in json_rows if r["metadata"]["label"] == 0}
    overlap = groups_case & groups_ctrl
    leakage_hits = sum(bool(LEAK_RX.search(t)) for t in texts)

    if overlap:
        raise RuntimeError(f"Case/control patient overlap after matching: {len(overlap)}")
    if any(not t.strip() for t in texts):
        raise RuntimeError("Blank note in frozen Zigong cohort.")
    if leakage_hits:
        raise RuntimeError(f"Leakage screen failure in {leakage_hits} notes.")
    if int(labels.sum()) * args.controls_per_case != int((labels == 0).sum()):
        raise RuntimeError("Matched cohort is not exact 1:3.")

    report = {
        "analysis": "Frozen Zigong external narrative ventilation 24h cohort v1",
        "protocol": "docs/zigong_ventilation_external_protocol_v1.md",
        "local_only": True,
        "model_inference_performed": False,
        "contains_note_text_in_declared_artifact": False,
        "contains_source_patient_identifiers_in_declared_artifact": False,
        "source_table": "dtNursingChart.csv",
        "time_basis": "within-table relative time from first valid timed nursing row",
        "fixed_clock_correction_applied": False,
        "outcome": (
            "first post-washout row with ETT depth 10-40 cm and same-row Vt_setting 100-1000 mL"
        ),
        "washout_hours": float(args.washout_hours),
        "prediction_horizon_hours": float(args.horizon_hours),
        "controls_per_case": int(args.controls_per_case),
        "matching_seed": int(args.matching_seed),
        "preferred_elapsed_time_match_hours": float(args.preferred_match_hours),
        "maximum_elapsed_time_match_hours": float(args.max_match_hours),
        "event_counts": {
            "all_encounters_with_qualifying_event": int(len(first_event)),
            "events_after_6h_washout": int(len(event_after_washout)),
            "after_prior_extubation_exclusion": int(len(event_after_extubation_rule)),
            "with_leakage_clean_pre_event_note_within_24h": int(len(case_best)),
        },
        "matched_cohort": {
            "cases": int(labels.sum()),
            "controls": int((labels == 0).sum()),
            "total_notes": int(len(labels)),
            "unique_patient_groups": int(len({r["metadata"]["patient_group"] for r in json_rows})),
            "case_control_patient_overlap": int(len(overlap)),
            "blank_notes": int(sum(not t.strip() for t in texts)),
            "leakage_term_hits_after_screen": int(leakage_hits),
            "case_note_lead_time_hours": qstats(
                ms["case"]["lead"] for ms in matched_sets
            ),
            "case_note_elapsed_time_hours": qstats(
                ms["case"]["note_rel"] for ms in matched_sets
            ),
            "control_elapsed_time_match_distance_hours": qstats(match_distances),
        },
        "local_outputs": {
            "cases_jsonl": str(local_out / "cases.jsonl"),
            "snapshot_index_local": str(local_out / "snapshot_index_local.csv"),
        },
        "next_gate": (
            "Audit language/tokenizer applicability for frozen local models before any Zigong outcome performance is inspected."
        ),
    }
    manifest_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    update_progress(current=5, total=5, phase="done", message="Completed frozen Zigong ventilation 24h cohort build", unit="stage")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
