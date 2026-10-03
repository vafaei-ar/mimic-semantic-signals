from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from registration_gate import require_osf_registration
from runrelay_progress import update_progress


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

OUTCOMES = (
    ("invasive_ventilation", 20261031),
    ("renal_replacement_therapy", 20261032),
    ("icu_death", 20261033),
)

SUPPORT_FIELDS = (
    "treat_vasoactive_any",
    "treat_niv_any_6h",
    "treat_high_flow_any_6h",
    "treat_fio2_last_6h",
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def finite_spearman(x, y) -> dict:
    x = pd.to_numeric(pd.Series(x), errors="coerce").to_numpy(dtype=float)
    y = pd.to_numeric(pd.Series(y), errors="coerce").to_numpy(dtype=float)
    ok = np.isfinite(x) & np.isfinite(y)
    if int(ok.sum()) < 3:
        return {"n": int(ok.sum()), "spearman_rho": None}
    xv = x[ok]
    yv = y[ok]
    if np.unique(xv).size < 2 or np.unique(yv).size < 2:
        return {"n": int(ok.sum()), "spearman_rho": None}
    rho = float(spearmanr(xv, yv).statistic)
    return {"n": int(ok.sum()), "spearman_rho": rho}


def association_summary(score, field, *, binary: bool) -> dict:
    out = finite_spearman(score, field)
    s = pd.to_numeric(pd.Series(score), errors="coerce").to_numpy(dtype=float)
    f = pd.to_numeric(pd.Series(field), errors="coerce").to_numpy(dtype=float)
    ok = np.isfinite(s) & np.isfinite(f)
    if binary and int(ok.sum()) > 0:
        pos = ok & (f > 0.5)
        neg = ok & (f <= 0.5)
        out.update(
            {
                "n_positive": int(pos.sum()),
                "n_nonpositive": int(neg.sum()),
                "score_mean_positive": float(s[pos].mean()) if pos.any() else None,
                "score_mean_nonpositive": float(s[neg].mean()) if neg.any() else None,
                "mean_difference_positive_minus_nonpositive": (
                    float(s[pos].mean() - s[neg].mean())
                    if pos.any() and neg.any()
                    else None
                ),
            }
        )
    return out


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
                raise RuntimeError(f"Non-ok semantic inference row for case_id={cid}")
            answers = (rec.get("response") or {}).get("answers") or {}
            row = {"case_id": cid}
            for name in SEMANTIC_NAMES:
                item = answers.get(name)
                value = item.get("noul") if isinstance(item, dict) else None
                if not isinstance(value, (int, float)) or not np.isfinite(float(value)):
                    raise RuntimeError(f"Missing/non-finite semantic score {name} for case_id={cid}")
                row[name] = float(value)
            meta = rec.get("metadata") or {}
            row["note_tokens"] = float(meta.get("note_tokens"))
            row["chunks_evaluated"] = float(meta.get("chunks_evaluated"))
            rows.append(row)
    return pd.DataFrame(rows)


def load_note_lengths(path: Path) -> pd.DataFrame:
    rows = []
    seen = set()
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            rec = json.loads(line)
            cid = str(rec.get("case_id"))
            if not cid or cid == "None" or cid in seen:
                raise RuntimeError("Missing or duplicate case_id in frozen note corpus")
            seen.add(cid)
            note = (rec.get("model_state") or {}).get("clinical_note")
            if not isinstance(note, str) or not note.strip():
                raise RuntimeError(f"Missing note text for case_id={cid}")
            rows.append({"case_id": cid, "note_characters": int(len(note))})
    return pd.DataFrame(rows)


def between_patient_permutation(subject_ids: np.ndarray, seed: int) -> np.ndarray:
    subjects = pd.to_numeric(pd.Series(subject_ids), errors="raise").astype("int64").to_numpy()
    rng = np.random.default_rng(seed)
    idx = np.arange(len(subjects), dtype=int)
    for _ in range(5000):
        donor = rng.permutation(idx)
        if np.all(subjects[donor] != subjects):
            return donor
    raise RuntimeError("Could not construct a between-patient semantic permutation")


def self_test() -> None:
    subjects = np.arange(100, dtype=int)
    donor = between_patient_permutation(subjects, 12345)
    if np.any(subjects[donor] == subjects):
        raise RuntimeError("self-test failed: same-subject donor")
    a = association_summary(np.arange(10), np.arange(10), binary=False)
    if a["spearman_rho"] < 0.99:
        raise RuntimeError("self-test failed: Spearman")
    print(json.dumps({"self_test": "passed"}))


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Post-registration label-free semantic alignment audit for Paper 1."
    )
    ap.add_argument("--base")
    ap.add_argument("--analysis-populations")
    ap.add_argument("--output")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        self_test()
        return

    if not args.base or not args.analysis_populations or not args.output:
        ap.error("--base, --analysis-populations, and --output are required")

    require_osf_registration()

    base = Path(args.base).expanduser().resolve()
    population_path = Path(args.analysis_populations).expanduser().resolve()
    population = json.loads(population_path.read_text(encoding="utf-8"))

    results = {}
    for oi, (outcome, seed) in enumerate(OUTCOMES, start=1):
        expected = population["confirmatory_outcomes"][outcome]
        context_path = base / outcome / "preregistration_context_features_v2_1_local.csv"
        semantic_path = base / outcome / "openjev_registered_v2_1_raw_local.jsonl"
        notes_path = base / outcome / "fixed_notes_stripped_v2_1_local.jsonl"

        wanted = {"case_id", "subject_id", *SUPPORT_FIELDS}
        context = pd.read_csv(
            context_path,
            usecols=lambda c: c in wanted,
            low_memory=False,
        )
        missing = wanted - set(context.columns)
        if missing:
            raise RuntimeError(f"{outcome}: missing context columns {sorted(missing)}")
        context["case_id"] = context["case_id"].astype(str)
        if context["case_id"].duplicated().any():
            raise RuntimeError(f"{outcome}: duplicate case_id in context input")

        sem = load_semantics(semantic_path)
        notes = load_note_lengths(notes_path)
        if len(sem) != int(expected["note_available_rows"]):
            raise RuntimeError(
                f"{outcome}: semantic rows {len(sem)} != frozen note rows "
                f"{expected['note_available_rows']}"
            )
        if set(sem["case_id"]) != set(notes["case_id"]):
            raise RuntimeError(f"{outcome}: semantic/note corpus case_id mismatch")

        frame = (
            sem.merge(notes, on="case_id", how="inner", validate="one_to_one")
            .merge(context, on="case_id", how="left", validate="one_to_one")
        )
        if len(frame) != len(sem):
            raise RuntimeError(f"{outcome}: alignment merge changed row count")
        if frame["subject_id"].isna().any():
            raise RuntimeError(f"{outcome}: missing subject_id after alignment")

        donor = between_patient_permutation(
            frame["subject_id"].to_numpy(), seed=seed
        )
        shuffled = frame.loc[:, SEMANTIC_NAMES].iloc[donor].reset_index(drop=True)

        construct_fields = {
            "hemodynamic_concern": (
                ("treat_vasoactive_any", True),
            ),
            "respiratory_concern": (
                ("treat_niv_any_6h", True),
                ("treat_high_flow_any_6h", True),
                ("treat_fio2_last_6h", False),
            ),
            "reassuring_stability": (
                ("treat_vasoactive_any", True),
                ("treat_niv_any_6h", True),
                ("treat_high_flow_any_6h", True),
                ("treat_fio2_last_6h", False),
            ),
        }

        assoc = {}
        for construct, fields in construct_fields.items():
            assoc[construct] = {}
            for field, is_binary in fields:
                assoc[construct][field] = {
                    "real": association_summary(
                        frame[construct], frame[field], binary=is_binary
                    ),
                    "between_patient_shuffled": association_summary(
                        shuffled[construct], frame[field], binary=is_binary
                    ),
                }

        chunk_length = {
            "chunks_vs_note_tokens": finite_spearman(
                frame["chunks_evaluated"], frame["note_tokens"]
            ),
            "chunks_vs_note_characters": finite_spearman(
                frame["chunks_evaluated"], frame["note_characters"]
            ),
            "note_tokens_vs_note_characters": finite_spearman(
                frame["note_tokens"], frame["note_characters"]
            ),
        }

        results[outcome] = {
            "source": str(expected["source"]),
            "note_available_rows": int(len(frame)),
            "note_available_patients": int(frame["subject_id"].nunique()),
            "outcome_labels_read": False,
            "semantic_note_case_ids_match_exactly": True,
            "between_patient_shuffle_seed": int(seed),
            "same_patient_donor_assignments": int(
                np.sum(
                    frame["subject_id"].to_numpy(dtype=int)
                    == frame["subject_id"].to_numpy(dtype=int)[donor]
                )
            ),
            "construct_state_associations": assoc,
            "chunk_note_length_correlations": chunk_length,
            "input_hashes": {
                "context_sha256": sha256_file(context_path),
                "semantics_sha256": sha256_file(semantic_path),
                "notes_sha256": sha256_file(notes_path),
            },
        }
        update_progress(
            current=oi,
            total=len(OUTCOMES),
            phase="submission_semantic_alignment_audit",
            message=f"Completed label-free alignment audit for {outcome}",
            unit="outcome",
        )

    report = {
        "analysis": "Post-registration Paper 1 label-free semantic alignment audit",
        "status": "completed",
        "registration_id": "ahxn9",
        "registered_analysis_modified": False,
        "outcome_labels_read": False,
        "purpose": (
            "Exclude gross note/stay semantic misalignment as an explanation for the "
            "registered near-null incremental results before manuscript interpretation."
        ),
        "interpretation_rule": (
            "Clinical review should confirm expected-direction real construct-state "
            "associations materially exceed between-patient shuffled references. If not, "
            "stop null-result interpretation and investigate alignment/inference provenance."
        ),
        "analysis_population_contract_sha256": sha256_file(population_path),
        "outcomes": results,
        "guardrails": [
            "No outcome labels are read.",
            "Only aggregate associations leave the workstation.",
            "Raw notes and row-level semantic scores remain local.",
            "The shuffle permutes complete semantic vectors between different patients.",
            "This audit does not alter registered H1-H7 estimates.",
        ],
    }
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"status": "completed", "output": str(output)}))


if __name__ == "__main__":
    main()
