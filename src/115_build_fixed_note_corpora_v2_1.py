from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from pathlib import Path

import pandas as pd

from runrelay_progress import update_progress


ANALYSES = (
    "invasive_ventilation",
    "renal_replacement_therapy",
    "icu_death",
    "icu_death_carevue",
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def note_identity_hash(index: pd.DataFrame) -> str:
    """Reproduce the frozen G8/R8 note-identity serialization across pandas versions."""
    cols = ["case_id", "icustay_id", "has_note", "note_time", "category"]
    x = index[cols].copy()
    for col in cols:
        s = x[col]
        if pd.api.types.is_datetime64_any_dtype(s):
            # The frozen G8 hash used pandas datetime stringification, where missing
            # datetimes serialize as "NaT" rather than an empty string.
            x[col] = s.map(lambda v: "NaT" if pd.isna(v) else str(v))
        else:
            x[col] = s.map(lambda v: "" if pd.isna(v) else str(v))
    payload = "\n".join(
        "|".join(row)
        for row in x.sort_values("case_id").itertuples(index=False, name=None)
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def prepare_index_for_frozen_context_hash(idx: pd.DataFrame) -> pd.DataFrame:
    out = idx.copy()
    for col in ["subject_id", "hadm_id", "icustay_id", "label"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="raise").astype("int64")
    if "landmark_time" in out.columns:
        out["landmark_time"] = pd.to_datetime(out["landmark_time"], errors="raise")
    out["note_time"] = pd.to_datetime(out["note_time"], errors="coerce")
    return out


def verify_note_identity_and_normalize_has_note(
    idx: pd.DataFrame,
    expected_hash: str,
    analysis_name: str,
) -> tuple[pd.DataFrame, str]:
    observed_hash = note_identity_hash(idx)
    if observed_hash != expected_hash:
        raise RuntimeError(
            f"{analysis_name}: frozen note-identity contract violation: "
            f"observed {observed_hash}, expected {expected_hash}"
        )
    out = idx.copy()
    out["has_note"] = (
        pd.to_numeric(out["has_note"], errors="coerce").fillna(0).ne(0)
    )
    return out, observed_hash


def compile_outcome_regex(patterns: list[str]) -> re.Pattern:
    return re.compile("|".join(f"(?:{p})" for p in patterns), flags=re.IGNORECASE)


def strip_text(text: str, rx: re.Pattern, replacement: str) -> tuple[str, int]:
    matches = list(rx.finditer(text))
    return rx.sub(replacement, text), len(matches)


def analysis_specs(local_root: Path, contract: dict) -> dict[str, dict]:
    primary = contract["confirmatory_outcomes"]
    rep = contract["prespecified_replications"]["icu_death_carevue"]
    return {
        "invasive_ventilation": {
            "outcome": "invasive_ventilation",
            "source": "metavision",
            "expected": primary["invasive_ventilation"],
            "suffix": "",
        },
        "renal_replacement_therapy": {
            "outcome": "renal_replacement_therapy",
            "source": "metavision",
            "expected": primary["renal_replacement_therapy"],
            "suffix": "",
        },
        "icu_death": {
            "outcome": "icu_death",
            "source": "metavision",
            "expected": primary["icu_death"],
            "suffix": "",
        },
        "icu_death_carevue": {
            "outcome": "icu_death",
            "source": "carevue",
            "expected": rep,
            "suffix": "_carevue",
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Materialize fixed-note full and language-stripped v2.1 corpora without semantic or predictive inference."
    )
    ap.add_argument("--local-root", required=True)
    ap.add_argument("--analysis-populations", required=True)
    ap.add_argument("--context-feature-results", required=True)
    ap.add_argument("--strip-freeze", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    local_root = Path(args.local_root).expanduser().resolve()
    contract = json.loads(
        Path(args.analysis_populations).expanduser().resolve().read_text(encoding="utf-8")
    )
    context_results = json.loads(
        Path(args.context_feature_results).expanduser().resolve().read_text(encoding="utf-8")
    )
    freeze = json.loads(
        Path(args.strip_freeze).expanduser().resolve().read_text(encoding="utf-8")
    )
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    replacement = str(freeze["replacement"])
    specs = analysis_specs(local_root, contract)

    report = {
        "analysis": "v2.1 fixed-note full/stripped corpus materialization",
        "outcome_performance_computed": False,
        "semantic_or_lexical_inference_run": False,
        "primary_corpus": freeze["primary_corpus"],
        "secondary_corpus": freeze["secondary_corpus"],
        "strip_freeze": "config/v2_1_language_stripping_freeze.json",
        "analysis_population_contract": "config/v2_1_analysis_population_contract.json",
        "context_feature_result_contract": "config/v2_1_context_feature_result_contract.json",
        "transformation": {
            "flags": freeze["flags"],
            "replacement": replacement,
            "post_replacement_normalization": freeze["post_replacement_normalization"],
        },
        "analyses": {},
    }

    for ai, name in enumerate(ANALYSES, start=1):
        spec = specs[name]
        outcome = spec["outcome"]
        source = spec["source"]
        expected = spec["expected"]
        suffix = spec["suffix"]

        update_progress(
            current=ai,
            total=len(ANALYSES),
            phase="fixed_note_corpus",
            message=f"{name}: materializing full and stripped fixed-note corpora",
            unit="analysis",
        )

        index_path = local_root / outcome / "population_index_local.csv"
        idx = pd.read_csv(index_path, low_memory=False)
        idx["dbsource"] = idx["dbsource"].fillna("unknown").astype(str).str.strip().str.lower()
        idx = idx[idx["dbsource"].eq(source)].copy()
        idx = prepare_index_for_frozen_context_hash(idx)

        # Hash the frozen population-index representation exactly as materialized
        # by the G8 context builder. Converting 0/1 to False/True before hashing
        # changes the string representation without changing note identity.
        expected_note_identity = context_results["analyses"][name]["note_identity_sha256"]
        idx, current_note_identity = verify_note_identity_and_normalize_has_note(
            idx,
            expected_note_identity,
            name,
        )

        observed = {
            "rows": int(len(idx)),
            "unique_patients": int(idx["subject_id"].nunique()),
            "cases": int(pd.to_numeric(idx["label"], errors="raise").sum()),
            "controls": int(len(idx) - pd.to_numeric(idx["label"], errors="raise").sum()),
            "note_available_rows": int(idx["has_note"].sum()),
        }
        for key, value in observed.items():
            if int(expected[key]) != int(value):
                raise RuntimeError(
                    f"{name}: analysis-population contract violation for {key}: "
                    f"observed {value}, expected {expected[key]}"
                )

        selected = idx[idx["has_note"]].copy()
        selected_ids = set(selected["case_id"].astype(str))
        direct_expected = int(
            pd.to_numeric(
                selected["direct_outcome_language_present"],
                errors="coerce",
            ).fillna(0).ne(0).sum()
        )

        source_cases = local_root / outcome / "cases.jsonl"
        records = {}
        with source_cases.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                rec = json.loads(line)
                cid = str(rec["case_id"])
                if cid in selected_ids:
                    if cid in records:
                        raise RuntimeError(f"{name}: duplicate case_id in source cases: {cid}")
                    records[cid] = rec

        missing = sorted(selected_ids - set(records))
        extra = sorted(set(records) - selected_ids)
        if missing or extra:
            raise RuntimeError(
                f"{name}: selected-note record mismatch: missing={len(missing)} extra={len(extra)}"
            )

        patterns = freeze["patterns"][outcome]
        rx = compile_outcome_regex(patterns)

        full_path = local_root / outcome / f"fixed_notes_full_v2_1{suffix}_local.jsonl"
        stripped_path = local_root / outcome / f"fixed_notes_stripped_v2_1{suffix}_local.jsonl"

        notes_changed = 0
        total_matches = 0
        chars_before = 0
        chars_after = 0

        with full_path.open("w", encoding="utf-8") as full_handle, stripped_path.open(
            "w", encoding="utf-8"
        ) as strip_handle:
            for cid in sorted(selected_ids):
                rec = records[cid]
                text = str(rec["model_state"]["clinical_note"])
                stripped, match_count = strip_text(text, rx, replacement)

                full_rec = copy.deepcopy(rec)
                full_rec.setdefault("metadata", {})["corpus_variant"] = "full_unstripped"
                full_rec["metadata"]["source_system_analysis"] = source

                stripped_rec = copy.deepcopy(rec)
                stripped_rec["model_state"]["clinical_note"] = stripped
                stripped_rec.setdefault("metadata", {})["corpus_variant"] = "language_stripped"
                stripped_rec["metadata"]["source_system_analysis"] = source
                stripped_rec["metadata"]["outcome_language_match_count"] = int(match_count)

                full_handle.write(json.dumps(full_rec, ensure_ascii=False) + "\n")
                strip_handle.write(json.dumps(stripped_rec, ensure_ascii=False) + "\n")

                notes_changed += int(match_count > 0)
                total_matches += int(match_count)
                chars_before += len(text)
                chars_after += len(stripped)

        report["analyses"][name] = {
            "outcome": outcome,
            "source": source,
            "eligible_rows": int(len(idx)),
            "note_available_rows": int(len(selected)),
            "note_identity_sha256": current_note_identity,
            "pre_review_direct_language_flagged_notes": direct_expected,
            "notes_changed_by_corrected_stripping": int(notes_changed),
            "additional_notes_changed_vs_pre_review_flag": int(notes_changed - direct_expected),
            "total_regex_matches": int(total_matches),
            "characters_before": int(chars_before),
            "characters_after": int(chars_after),
            "full_local_file": str(full_path),
            "full_local_file_sha256": sha256_file(full_path),
            "stripped_local_file": str(stripped_path),
            "stripped_local_file_sha256": sha256_file(stripped_path),
            "pattern_count": int(len(patterns)),
        }

    report["guardrails"] = [
        "Note identity and eligibility were frozen before text transformation and matched the G8 context-feature result contract.",
        "The stripped corpus changes text only; note timing/category/has_note are unchanged.",
        "The corrected stripping count is frozen independently of the pre-review direct-language flag because the preregistration review deliberately broadened the vocabulary.",
        "No semantic model, TF-IDF model, or clinical prediction model was run.",
        "Row-level note text remains local; the declared artifact contains only aggregate hashes and counts.",
    ]

    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
