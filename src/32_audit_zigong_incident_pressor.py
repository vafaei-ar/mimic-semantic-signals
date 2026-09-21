from __future__ import annotations

import argparse
import json
import re
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd


CSV_ENCODINGS = ["utf-8-sig", "utf-8", "gb18030"]

PRESSOR_PATTERNS = {
    "norepinephrine": [
        r"norepinephrine",
        r"noradrenaline",
        r"levophed",
        r"去甲肾上腺素",
    ],
    "epinephrine": [
        r"(?<!nor)(?<!deoxy)epinephrine",
        r"(?<!nor)adrenaline",
        r"(?<!去甲)(?<!去氧)肾上腺素",
    ],
    "dopamine": [
        r"dopamine",
        r"多巴胺",
    ],
    "vasopressin": [
        r"vasopressin",
        r"血管加压素",
    ],
    "phenylephrine": [
        r"phenylephrine",
        r"deoxyepinephrine",
        r"去氧肾上腺素",
        r"苯肾上腺素",
    ],
}

# High-specificity administration evidence only. Deliberately excludes generic
# Chinese verbs such as "use", "continue", and "maintain".
STRICT_ADMIN_CUES = [
    r"泵入",
    r"微泵",
    r"静脉泵",
    r"静滴",
    r"静脉滴注",
    r"输注",
    r"滴速",
    r"ml\s*/\s*h",
    r"ml\s*/\s*小时",
    r"(?:ug|μg|mcg)\s*/\s*kg\s*/\s*min",
    r"(?:ug|μg|mcg)\s*/\s*min",
]

NEGATION_OR_PLAN_CUES = [
    r"未用",
    r"未使用",
    r"未予",
    r"停用",
    r"拟",
    r"计划",
    r"考虑",
]


def compile_rx(patterns: list[str]) -> re.Pattern:
    return re.compile("|".join(f"(?:{p})" for p in patterns), re.IGNORECASE)


PRESSOR_RX = {k: compile_rx(v) for k, v in PRESSOR_PATTERNS.items()}
ANY_PRESSOR_RX = compile_rx([p for v in PRESSOR_PATTERNS.values() for p in v])
STRICT_ADMIN_RX = compile_rx(STRICT_ADMIN_CUES)
NEG_PLAN_RX = compile_rx(NEGATION_OR_PLAN_CUES)


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


def discover_csvs(root: Path) -> dict[str, Path]:
    csvs = [p for p in root.rglob("*.csv") if not p.name.startswith("._")]
    if not csvs:
        archives = sorted(root.rglob("DataTables.zip"))
        if len(archives) != 1:
            raise RuntimeError("Expected one DataTables.zip under --root.")
        archive = archives[0]
        extract_dir = archive.parent / "_inventory_extracted"
        extract_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive, "r") as zf:
            base = extract_dir.resolve()
            for member in zf.infolist():
                target = (extract_dir / member.filename).resolve()
                try:
                    target.relative_to(base)
                except ValueError as exc:
                    raise RuntimeError(f"Unsafe archive path: {member.filename}") from exc
            zf.extractall(extract_dir)
        csvs = [p for p in extract_dir.rglob("*.csv") if not p.name.startswith("._")]
    return {p.name.lower(): p for p in csvs}


def classify_agents(series: pd.Series) -> dict[str, pd.Series]:
    text = series.astype(str)
    return {
        agent: text.str.contains(rx, regex=True, na=False)
        for agent, rx in PRESSOR_RX.items()
    }


def qstats(x: pd.Series) -> dict:
    x = pd.to_numeric(x, errors="coerce").dropna()
    if x.empty:
        return {"n": 0, "median": None, "p25": None, "p75": None, "p05": None, "p95": None}
    return {
        "n": int(len(x)),
        "median": float(x.median()),
        "p25": float(x.quantile(0.25)),
        "p75": float(x.quantile(0.75)),
        "p05": float(x.quantile(0.05)),
        "p95": float(x.quantile(0.95)),
    }


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Audit incident vasopressor starts in Zigong using strict nursing-note "
            "administration evidence and nearest same-agent physician orders."
        )
    )
    ap.add_argument("--root", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--washout-hours", type=float, default=12.0)
    args = ap.parse_args()

    root = Path(args.root).expanduser().resolve()
    out = Path(args.output).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    files = discover_csvs(root)
    for name in ["dtbaseline.csv", "dtdrugs.csv", "dtnursingchart.csv"]:
        if name not in files:
            raise RuntimeError(f"Missing {name}")

    baseline = read_csv_robust(
        files["dtbaseline.csv"],
        usecols=lambda c: c in {"PATIENT_ID", "INP_NO"},
        low_memory=False,
    )
    baseline["PATIENT_ID"] = pd.to_numeric(baseline["PATIENT_ID"], errors="coerce")
    baseline["INP_NO"] = pd.to_numeric(baseline["INP_NO"], errors="coerce")
    baseline = baseline.dropna(subset=["PATIENT_ID", "INP_NO"]).copy()
    baseline["PATIENT_ID"] = baseline["PATIENT_ID"].astype("int64")
    baseline["INP_NO"] = baseline["INP_NO"].astype("int64")
    inp_to_patient = dict(zip(baseline["INP_NO"], baseline["PATIENT_ID"]))

    # All pressor orders, classified without substring overwrite.
    order_parts = []
    for chunk in iter_csv_robust(
        files["dtdrugs.csv"],
        chunksize=200_000,
        usecols=lambda c: c in {"PATIENT_ID", "DrugName", "Drug_time"},
        low_memory=False,
    ):
        chunk["PATIENT_ID"] = pd.to_numeric(chunk["PATIENT_ID"], errors="coerce")
        chunk["Drug_time"] = pd.to_numeric(chunk["Drug_time"], errors="coerce")
        chunk = chunk.dropna(subset=["PATIENT_ID", "DrugName", "Drug_time"]).copy()
        if chunk.empty:
            continue
        chunk["PATIENT_ID"] = chunk["PATIENT_ID"].astype("int64")
        agent_masks = classify_agents(chunk["DrugName"])
        used = pd.Series(False, index=chunk.index)
        for agent in ["norepinephrine", "phenylephrine", "dopamine", "epinephrine", "vasopressin"]:
            mask = agent_masks[agent] & ~used
            if not mask.any():
                continue
            part = chunk.loc[mask, ["PATIENT_ID", "Drug_time"]].copy()
            part["agent"] = agent
            part = part.rename(columns={"PATIENT_ID": "patient_id", "Drug_time": "order_time"})
            order_parts.append(part)
            used = used | mask

    orders = pd.concat(order_parts, ignore_index=True) if order_parts else pd.DataFrame(
        columns=["patient_id", "order_time", "agent"]
    )

    # Nursing events. Persist only patient/time/agent flags in memory; never text.
    any_first: dict[int, float] = {}
    strict_events = []

    for chunk in iter_csv_robust(
        files["dtnursingchart.csv"],
        chunksize=100_000,
        usecols=lambda c: c in {"INP_NO", "NURSING_DESC", "ChartTime"},
        low_memory=False,
    ):
        chunk["INP_NO"] = pd.to_numeric(chunk["INP_NO"], errors="coerce")
        chunk["ChartTime"] = pd.to_numeric(chunk["ChartTime"], errors="coerce")
        chunk = chunk.dropna(subset=["INP_NO", "NURSING_DESC", "ChartTime"]).copy()
        if chunk.empty:
            continue
        chunk["INP_NO"] = chunk["INP_NO"].astype("int64")
        desc = chunk["NURSING_DESC"].astype(str)

        any_mask = desc.str.contains(ANY_PRESSOR_RX, regex=True, na=False)
        if not any_mask.any():
            continue

        sub = chunk.loc[any_mask, ["INP_NO", "NURSING_DESC", "ChartTime"]].copy()
        sdesc = sub["NURSING_DESC"].astype(str)

        for row in sub[["INP_NO", "ChartTime"]].itertuples(index=False):
            patient = inp_to_patient.get(int(row.INP_NO))
            if patient is None:
                continue
            t = float(row.ChartTime)
            old = any_first.get(patient)
            if old is None or t < old:
                any_first[patient] = t

        strict = (
            sdesc.str.contains(STRICT_ADMIN_RX, regex=True, na=False)
            & ~sdesc.str.contains(NEG_PLAN_RX, regex=True, na=False)
        )
        if not strict.any():
            continue

        ss = sub.loc[strict].copy()
        masks = classify_agents(ss["NURSING_DESC"])
        used = pd.Series(False, index=ss.index)
        for agent in ["norepinephrine", "phenylephrine", "dopamine", "epinephrine", "vasopressin"]:
            mask = masks[agent] & ~used
            if not mask.any():
                continue
            for row in ss.loc[mask, ["INP_NO", "ChartTime"]].itertuples(index=False):
                patient = inp_to_patient.get(int(row.INP_NO))
                if patient is not None:
                    strict_events.append(
                        {
                            "patient_id": int(patient),
                            "admin_time": float(row.ChartTime),
                            "agent": agent,
                        }
                    )
            used = used | mask

    strict_df = pd.DataFrame(strict_events)
    if strict_df.empty:
        raise RuntimeError("No strict administration-like nursing events found.")

    first_strict = (
        strict_df.sort_values("admin_time")
        .groupby("patient_id", as_index=False)
        .first()
    )
    first_strict["first_any_pressor_mention_time"] = first_strict["patient_id"].map(any_first)
    first_strict["prior_any_gap_hours"] = (
        first_strict["admin_time"] - first_strict["first_any_pressor_mention_time"]
    )

    # Incident-like: event occurs after a meaningful observation window and the
    # strict event is also the patient's first pressor mention (within 0.25 h,
    # allowing charting granularity).
    incident = first_strict[
        (first_strict["admin_time"] >= float(args.washout_hours))
        & (first_strict["prior_any_gap_hours"].abs() <= 0.25)
    ].copy()

    # Match each first strict administration mention to nearest same-agent order.
    order_groups = {
        (int(pid), str(agent)): np.sort(g["order_time"].astype(float).to_numpy())
        for (pid, agent), g in orders.groupby(["patient_id", "agent"])
    }

    nearest_deltas = []
    previous_deltas = []
    next_deltas = []

    def add_order_alignment(df: pd.DataFrame) -> pd.DataFrame:
        out_df = df.copy()
        nearest = []
        previous = []
        following = []
        for row in out_df.itertuples(index=False):
            arr = order_groups.get((int(row.patient_id), str(row.agent)), np.array([]))
            t = float(row.admin_time)
            if len(arr) == 0:
                nearest.append(np.nan)
                previous.append(np.nan)
                following.append(np.nan)
                continue
            d = t - arr
            nearest.append(float(d[np.argmin(np.abs(d))]))
            prev = arr[arr <= t]
            nxt = arr[arr >= t]
            previous.append(float(t - prev[-1]) if len(prev) else np.nan)
            following.append(float(nxt[0] - t) if len(nxt) else np.nan)
        out_df["admin_minus_nearest_same_agent_order_h"] = nearest
        out_df["hours_since_previous_same_agent_order"] = previous
        out_df["hours_until_next_same_agent_order"] = following
        return out_df

    aligned_all = add_order_alignment(first_strict)
    aligned_incident = add_order_alignment(incident)

    def alignment_windows(df: pd.DataFrame) -> dict:
        d = df["admin_minus_nearest_same_agent_order_h"].dropna()
        return {
            "n_with_same_agent_order": int(len(d)),
            "within_1h_absolute": int((d.abs() <= 1).sum()),
            "within_6h_absolute": int((d.abs() <= 6).sum()),
            "within_12h_absolute": int((d.abs() <= 12).sum()),
            "within_24h_absolute": int((d.abs() <= 24).sum()),
        }

    report = {
        "dataset": "Zigong Fourth People's Hospital critical care infection database v1.1",
        "local_only": True,
        "contains_note_text": False,
        "contains_patient_identifiers": False,
        "washout_hours_from_hospital_admission": float(args.washout_hours),
        "strict_admin_definition": (
            "pressor term plus high-specificity infusion/pump/rate language, excluding "
            "negation and planning cues"
        ),
        "patients_with_any_pressor_order": int(orders["patient_id"].nunique()),
        "pressor_order_patients_by_agent": (
            orders.groupby("agent")["patient_id"].nunique().astype(int).to_dict()
        ),
        "patients_with_strict_admin_like_nursing_event": int(first_strict["patient_id"].nunique()),
        "strict_admin_patients_by_agent": (
            first_strict.groupby("agent")["patient_id"].nunique().astype(int).to_dict()
        ),
        "first_strict_admin_time_hours": qstats(first_strict["admin_time"]),
        "incident_like_patients": int(len(incident)),
        "incident_like_by_agent": (
            incident.groupby("agent")["patient_id"].nunique().astype(int).to_dict()
            if not incident.empty else {}
        ),
        "incident_first_admin_time_hours": qstats(
            incident["admin_time"] if not incident.empty else pd.Series(dtype=float)
        ),
        "all_first_admin_nearest_same_agent_order_delta_hours": qstats(
            aligned_all["admin_minus_nearest_same_agent_order_h"]
        ),
        "all_first_admin_order_alignment": alignment_windows(aligned_all),
        "incident_nearest_same_agent_order_delta_hours": qstats(
            aligned_incident["admin_minus_nearest_same_agent_order_h"]
            if not aligned_incident.empty else pd.Series(dtype=float)
        ),
        "incident_order_alignment": (
            alignment_windows(aligned_incident)
            if not aligned_incident.empty
            else {}
        ),
        "candidate_external_endpoint": (
            "first strict nursing administration-like pressor event after the washout "
            "window, provided it is also the first pressor mention; physician orders are "
            "used as supporting timing evidence rather than the endpoint itself"
        ),
        "next_decision": (
            "If incident_like_patients is adequate and the majority have plausible "
            "same-agent order alignment, proceed to build the frozen 6-hour risk-set "
            "external validation cohort. Otherwise reconsider the endpoint."
        ),
    }

    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
