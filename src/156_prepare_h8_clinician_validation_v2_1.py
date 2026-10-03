from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from registration_gate import require_osf_registration
from runrelay_progress import update_progress
from semantic_schema import SEMANTIC_CONSTRUCTS


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_lines(values: list[str]) -> str:
    payload = "\n".join(values).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def read_corpus(path: Path) -> dict[str, str]:
    records: dict[str, str] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            rec = json.loads(line)
            cid = str(rec["case_id"])
            if cid in records:
                raise RuntimeError(f"duplicate case_id in H8 corpus: {cid}")
            records[cid] = str(rec["model_state"]["clinical_note"])
    return records


def construct_names() -> list[str]:
    return [str(x["name"]) for x in SEMANTIC_CONSTRUCTS]


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Freeze the registered H8 random clinician-validation sample and "
            "materialize local blinded rater packets without reading labels or model scores."
        )
    )
    ap.add_argument("--base", required=True)
    ap.add_argument("--freeze", required=True)
    ap.add_argument("--corpus-contract", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    require_osf_registration()
    base = Path(args.base).expanduser().resolve()
    freeze_path = Path(args.freeze).expanduser().resolve()
    contract_path = Path(args.corpus_contract).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()

    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    contract = json.loads(contract_path.read_text(encoding="utf-8"))

    sf = freeze["sampling_frame"]
    if sf["analysis"] != "icu_death" or sf["source"] != "metavision":
        raise RuntimeError("H8 sampling frame changed from frozen MetaVision ICU-death frame")
    if sf["corpus_variant"] != "language_stripped":
        raise RuntimeError("H8 corpus must remain the frozen stripped-note corpus")

    frozen_constructs = freeze["constructs"]
    if frozen_constructs != SEMANTIC_CONSTRUCTS:
        raise RuntimeError("H8 frozen construct wording differs from semantic_schema.py")

    outcome_dir = base / "icu_death"
    corpus_path = outcome_dir / "fixed_notes_stripped_v2_1_local.jsonl"
    index_path = outcome_dir / "population_index_local.csv"

    expected = contract["analyses"]["icu_death"]
    expected_corpus_hash = str(expected["stripped_sha256"])
    observed_corpus_hash = sha256_file(corpus_path)
    if observed_corpus_hash != expected_corpus_hash:
        raise RuntimeError(
            f"H8 frozen corpus hash mismatch: {observed_corpus_hash} != {expected_corpus_hash}"
        )
    if observed_corpus_hash != str(sf["corpus_sha256"]):
        raise RuntimeError("H8 freeze corpus hash differs from fixed-note contract")

    update_progress(
        current=1,
        total=4,
        phase="h8_clinician_validation_prepare",
        message="Loading frozen MetaVision ICU-death stripped-note frame",
        unit="stage",
    )

    idx = pd.read_csv(
        index_path,
        usecols=[
            "case_id",
            "subject_id",
            "icustay_id",
            "dbsource",
            "has_note",
            "note_time",
            "category",
        ],
        low_memory=False,
    )
    idx["case_id"] = idx["case_id"].astype(str)
    idx["dbsource"] = idx["dbsource"].fillna("unknown").astype(str).str.strip().str.lower()
    idx["has_note"] = (
        pd.to_numeric(idx["has_note"], errors="coerce").fillna(0).ne(0)
    )
    idx = idx[idx["dbsource"].eq("metavision") & idx["has_note"]].copy()
    idx["subject_id"] = pd.to_numeric(idx["subject_id"], errors="raise").astype("int64")
    idx["icustay_id"] = pd.to_numeric(idx["icustay_id"], errors="raise").astype("int64")
    idx["note_time"] = pd.to_datetime(idx["note_time"], errors="raise")
    idx["category"] = idx["category"].fillna("UNKNOWN").astype(str)

    expected_n = int(sf["note_available_rows"])
    if len(idx) != expected_n or len(idx) != int(expected["note_available_rows"]):
        raise RuntimeError(
            f"H8 note frame size mismatch: observed {len(idx)}, expected {expected_n}"
        )
    if idx["case_id"].duplicated().any():
        raise RuntimeError("H8 frame contains duplicate case_id")

    records = read_corpus(corpus_path)
    frame_ids = sorted(idx["case_id"].tolist())
    if set(records) != set(frame_ids):
        raise RuntimeError(
            f"H8 corpus/index mismatch: corpus={len(records)} index={len(frame_ids)}"
        )

    update_progress(
        current=2,
        total=4,
        phase="h8_clinician_validation_prepare",
        message="Drawing frozen uniform random note sample without labels or model scores",
        unit="stage",
    )

    sample_size = int(sf["sample_size"])
    seed = int(sf["seed"])
    if sample_size <= 0 or sample_size > len(frame_ids):
        raise RuntimeError("Invalid H8 sample size")

    rng = np.random.default_rng(seed)
    sampled_positions = rng.choice(len(frame_ids), size=sample_size, replace=False)
    sampled_case_ids = [frame_ids[int(i)] for i in sampled_positions]

    idx_map = idx.set_index("case_id", drop=False)
    sample_rows = []
    for j, cid in enumerate(sampled_case_ids, start=1):
        row = idx_map.loc[cid]
        text = records[cid]
        sample_rows.append(
            {
                "sample_id": f"H8-{j:03d}",
                "case_id": cid,
                "subject_id": int(row["subject_id"]),
                "icustay_id": int(row["icustay_id"]),
                "note_time": row["note_time"].isoformat(),
                "category": str(row["category"]),
                "clinical_note": text,
                "clinical_note_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "note_characters": int(len(text)),
            }
        )

    sample = pd.DataFrame(sample_rows)
    if sample["case_id"].duplicated().any() or len(sample) != sample_size:
        raise RuntimeError("H8 sample uniqueness failure")

    update_progress(
        current=3,
        total=4,
        phase="h8_clinician_validation_prepare",
        message="Materializing local blinded linkage and three rater packets",
        unit="stage",
    )

    local_dir = base.parent / "h8_clinician_validation"
    local_dir.mkdir(parents=True, exist_ok=True)

    linkage_path = local_dir / "h8_sample_linkage_v2_1_local.csv"
    sample[
        [
            "sample_id",
            "case_id",
            "subject_id",
            "icustay_id",
            "note_time",
            "category",
            "clinical_note_sha256",
            "note_characters",
        ]
    ].to_csv(linkage_path, index=False)

    canonical_packet = sample[["sample_id", "clinical_note"]].copy()
    for name in construct_names():
        canonical_packet[name] = pd.Series([pd.NA] * len(canonical_packet), dtype="Float64")
    canonical_packet["deterioration_probability_12h"] = pd.Series(
        [pd.NA] * len(canonical_packet), dtype="Float64"
    )
    canonical_packet["rater_comment_optional"] = ""

    packet_paths = []
    packet_hashes = []
    order_hashes = []
    rater_order_seeds = [20261011, 20261012, 20261013]
    if int(freeze["raters"]["primary_rater_count"]) != len(rater_order_seeds):
        raise RuntimeError("H8 primary rater count differs from frozen three-rater packet plan")

    for rater_i, order_seed in enumerate(rater_order_seeds, start=1):
        order_rng = np.random.default_rng(order_seed)
        order = order_rng.permutation(len(canonical_packet))
        packet = canonical_packet.iloc[order].reset_index(drop=True)
        packet_path = local_dir / f"h8_rater_{rater_i}_packet_v2_1_local.csv"
        packet.to_csv(packet_path, index=False)
        packet_paths.append(str(packet_path))
        packet_hashes.append(sha256_file(packet_path))
        order_hashes.append(sha256_lines(packet["sample_id"].astype(str).tolist()))

    sample_case_ids_sorted = sorted(sample["case_id"].astype(str).tolist())
    sample_note_hashes_sorted = sorted(sample["clinical_note_sha256"].astype(str).tolist())
    category_counts = {
        str(k): int(v)
        for k, v in sample["category"].value_counts(dropna=False).sort_index().items()
    }

    report = {
        "analysis": "Registered v2.1 H8 clinician construct-validation sample preparation",
        "status": "completed",
        "registration_id": "ahxn9",
        "doi": "10.17605/OSF.IO/AHXN9",
        "human_ratings_collected": False,
        "outcome_labels_read": False,
        "model_scores_read": False,
        "predictive_performance_computed": False,
        "sampling_frame": {
            "analysis": "icu_death",
            "source": "metavision",
            "corpus_variant": "language_stripped",
            "rows": int(len(frame_ids)),
            "sample_size": int(sample_size),
            "seed": int(seed),
            "method": sf["sampling_method"],
            "frame_case_id_sha256": sha256_lines(frame_ids),
            "sample_case_id_sha256": sha256_lines(sample_case_ids_sorted),
            "sample_note_text_sha256": sha256_lines(sample_note_hashes_sorted),
            "category_counts": category_counts,
            "note_characters": {
                "min": int(sample["note_characters"].min()),
                "median": float(sample["note_characters"].median()),
                "mean": float(sample["note_characters"].mean()),
                "max": int(sample["note_characters"].max()),
            },
        },
        "rater_packets": {
            "primary_rater_count": 3,
            "all_raters_rate_all_notes": True,
            "independent_order_seeds": rater_order_seeds,
            "packet_sha256": packet_hashes,
            "sample_order_sha256": order_hashes,
            "local_packet_paths": packet_paths,
            "local_linkage_path": str(linkage_path),
            "local_linkage_sha256": sha256_file(linkage_path),
        },
        "construct_names": construct_names(),
        "hashes": {
            "frozen_corpus_sha256": observed_corpus_hash,
            "fixed_note_corpus_contract_sha256": sha256_file(contract_path),
            "h8_freeze_sha256": sha256_file(freeze_path),
        },
        "governance_gate": {
            "human_note_access_requires_irb_determination": True,
            "all_raters_require_applicable_physionet_mimic_access": True,
            "packets_may_not_be_distributed_until_gate_documented": True,
        },
        "contains_patient_identifiers": False,
        "contains_note_text": False,
        "contains_row_level_data": False,
        "guardrails": [
            "Sampling uses only frozen note identity and text availability; outcome labels and model scores are not read.",
            "The selected sample is uniform random without replacement from the frozen MetaVision ICU-death stripped-note frame.",
            "Rater packets contain restricted note text and remain local; they are not declared RunRelay artifacts.",
            "Raters remain blinded to identifiers, outcomes, model scores, comparator risk, prior results, and each other.",
            "Human rating may begin only after the institutional/DUA governance gate is documented.",
        ],
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    update_progress(
        current=4,
        total=4,
        phase="done",
        message="Frozen H8 random sample and local blinded rater packets",
        unit="stage",
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
