from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


EVENT_PATTERNS = {
    "vasopressor_initiation": {
        "vasopressor_term": [
            r"\bvasopressor(?:s)?\b",
            r"\bpressor(?:s)?\b",
            r"\bnorepinephrine\b",
            r"\blevophed\b",
            r"\bphenylephrine\b",
            r"\bneo[- ]?synephrine\b",
            r"\bvasopressin\b",
            r"\bdopamine\b",
            r"\bepinephrine\b",
            r"\badrenaline\b",
            r"\bvasoactive\b",
        ],
    },
    "intubation_mv_procedure": {
        "airway_event_term": [
            r"\bintubat(?:e|ed|ing|ion)\b",
            r"\bendotracheal\b",
            r"\bETT\b",
            r"\bmechanical ventilation\b",
            r"\bventilator\b",
        ],
    },
    "in_hospital_death": {
        "end_of_life_term": [
            r"\bcomfort measures?\b",
            r"\bcomfort care\b",
            r"\bCMO\b",
            r"\bhospice\b",
            r"\bterminal\b",
            r"\bdying\b",
            r"\bdeath\b",
            r"\bdeceased\b",
            r"\bDNR\b",
            r"\bDNI\b",
            r"\bdo not resuscitate\b",
            r"\bdo not intubate\b",
        ],
    },
}


def compile_patterns() -> dict[str, dict[str, list[re.Pattern[str]]]]:
    out = {}
    for event_type, groups in EVENT_PATTERNS.items():
        out[event_type] = {}
        for group, pats in groups.items():
            out[event_type][group] = [
                re.compile(p, flags=re.IGNORECASE)
                for p in pats
            ]
    return out


def match_groups(text: str, event_type: str, compiled) -> list[str]:
    groups = []
    for group, patterns in compiled.get(event_type, {}).items():
        if any(p.search(text) for p in patterns):
            groups.append(group)
    return groups


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Conservative local-only sensitivity filter for explicit event/treatment "
            "mentions in real MIMIC notes. Raw note text is never written to the manifest."
        )
    )
    ap.add_argument("--cases", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--manifest", required=True)
    args = ap.parse_args()

    src = Path(args.cases).expanduser().resolve()
    out = Path(args.output).expanduser().resolve()
    manifest_path = Path(args.manifest).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    compiled = compile_patterns()
    kept = []
    total = Counter()
    excluded = Counter()
    excluded_by_bin = Counter()
    excluded_by_group = Counter()
    kept_by_bin = Counter()
    excluded_pairs = set()

    with src.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec.get("synthetic_only") is True or rec.get("local_only") is not True:
                raise RuntimeError(
                    "Leakage filter only accepts real cases explicitly marked local_only=true."
                )

            meta = rec.get("metadata", {})
            event_type = str(meta.get("event_type", ""))
            time_bin = str(meta.get("time_bin", ""))
            admission_group = str(meta.get("admission_group", ""))
            note = rec.get("model_state", {}).get("clinical_note")
            if not isinstance(note, str):
                continue

            total[event_type] += 1
            groups = match_groups(note, event_type, compiled)
            if groups:
                excluded[event_type] += 1
                excluded_by_bin[(event_type, time_bin)] += 1
                excluded_pairs.add((event_type, admission_group))
                for group in groups:
                    excluded_by_group[(event_type, group)] += 1
                continue

            kept.append(rec)
            kept_by_bin[(event_type, time_bin)] += 1

    # For a longitudinal analysis, retain only event-admission pairs for which
    # all three original time bins remain after filtering.
    bins_by_pair = defaultdict(set)
    for rec in kept:
        meta = rec["metadata"]
        bins_by_pair[(str(meta["event_type"]), str(meta["admission_group"]))].add(
            str(meta["time_bin"])
        )
    complete_pairs = {
        pair
        for pair, bins in bins_by_pair.items()
        if bins == {"12_24h", "6_12h", "0_6h"}
    }
    kept_complete = [
        rec
        for rec in kept
        if (
            str(rec["metadata"]["event_type"]),
            str(rec["metadata"]["admission_group"]),
        ) in complete_pairs
    ]

    with out.open("w", encoding="utf-8") as f:
        for rec in kept_complete:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    complete_by_event = Counter(pair[0] for pair in complete_pairs)
    records_by_event = Counter(
        str(rec["metadata"]["event_type"]) for rec in kept_complete
    )

    manifest = {
        "local_only": True,
        "contains_credentialed_note_text_in_filtered_cases": True,
        "contains_note_text_in_manifest": False,
        "filter": "conservative explicit event/treatment term exclusion",
        "input_records_by_event": dict(total),
        "excluded_records_by_event": dict(excluded),
        "excluded_records_by_event_time_bin": [
            {"event_type": k[0], "time_bin": k[1], "n": v}
            for k, v in sorted(excluded_by_bin.items())
        ],
        "excluded_records_by_pattern_group": [
            {"event_type": k[0], "pattern_group": k[1], "n": v}
            for k, v in sorted(excluded_by_group.items())
        ],
        "complete_event_admission_pairs_after_filter": dict(complete_by_event),
        "output_records_by_event": dict(records_by_event),
        "output_records": len(kept_complete),
        "note": (
            "The sensitivity set drops any note containing an event-specific explicit "
            "term, then requires all three longitudinal time bins to remain for the "
            "event-admission pair. This is intentionally conservative and may remove "
            "legitimate early clinical concern along with treatment-plan leakage."
        ),
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
