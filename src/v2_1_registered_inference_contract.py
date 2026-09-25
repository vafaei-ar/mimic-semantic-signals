from __future__ import annotations

import hashlib
import json
from pathlib import Path


DEFAULT_FREEZE = Path("config/v2_1_osf_registered_instrument_freeze.json")
DEFAULT_SCHEMA = Path("src/semantic_schema.py")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_freeze(project_root: Path | str = ".") -> dict:
    root = Path(project_root).resolve()
    path = root / DEFAULT_FREEZE
    if not path.exists():
        raise RuntimeError("Missing v2.1 OSF registered instrument freeze.")
    data = json.loads(path.read_text(encoding="utf-8"))

    pending = data.get("submitted_form_text_pending_verbatim_import", {})
    if pending.get("require_verbatim_import_before_real_label_inference") is True:
        hypotheses = pending.get("directional_hypotheses", {})
        if any(hypotheses.get(k) is None for k in ("H4", "H5", "H9")):
            raise RuntimeError(
                "V2.1 INFERENCE LOCKED: verbatim registered H4/H5/H9 text has not been imported."
            )
        if pending.get("exploratory_analysis_list") is None:
            raise RuntimeError(
                "V2.1 INFERENCE LOCKED: verbatim registered exploratory analysis list has not been imported."
            )

    schema = data["semantic_schema"]
    expected = str(schema.get("sha256_exact") or "")
    observed = sha256_file(root / DEFAULT_SCHEMA)
    if not expected or observed != expected:
        raise RuntimeError(
            f"V2.1 INFERENCE LOCKED: semantic schema SHA-256 mismatch: {observed} != {expected}"
        )
    return data


def assert_registered_instrument(
    instrument: str,
    *,
    model_id: str | None = None,
    revision: str | None = None,
    chunk_tokens: int | None = None,
    chunk_overlap_tokens: int | None = None,
    max_chunks: int | None = None,
    package_version: str | None = None,
    typed_decisions_commit: str | None = None,
    project_root: Path | str = ".",
) -> dict:
    data = load_freeze(project_root)
    key = instrument.strip().lower()
    if key not in data["instruments"]:
        raise RuntimeError(f"Unknown registered v2.1 instrument: {instrument}")
    expected = data["instruments"][key]

    candidate_text = " ".join(
        str(x or "") for x in (model_id, revision)
    ).lower()
    if "nvfp4" in candidate_text:
        raise RuntimeError(
            "V2.1 INFERENCE LOCKED: NVFP4 DiffusionGemma is explicitly forbidden by the registered contract."
        )
    for forbidden in expected.get("forbidden_model_ids", []):
        if model_id == forbidden:
            raise RuntimeError(
                f"V2.1 INFERENCE LOCKED: forbidden registered model substitution: {model_id}"
            )

    checks = {
        "model_id": model_id,
        "chunk_tokens": chunk_tokens,
        "chunk_overlap_tokens": chunk_overlap_tokens,
        "max_chunks": max_chunks,
    }
    for field, observed in checks.items():
        if observed is not None and field in expected and observed != expected[field]:
            raise RuntimeError(
                f"V2.1 INFERENCE LOCKED: {key} {field}={observed!r}; registered value={expected[field]!r}"
            )

    expected_revision = expected.get("model_revision") or expected.get("model_revision_exact")
    if revision is not None and expected_revision and revision != expected_revision:
        raise RuntimeError(
            f"V2.1 INFERENCE LOCKED: {key} revision mismatch."
        )
    if package_version is not None and expected.get("package_version") and package_version != expected["package_version"]:
        raise RuntimeError(
            f"V2.1 INFERENCE LOCKED: {key} package version mismatch."
        )
    if typed_decisions_commit is not None and expected.get("typed_decisions_commit") and typed_decisions_commit != expected["typed_decisions_commit"]:
        raise RuntimeError(
            "V2.1 INFERENCE LOCKED: typed-decisions commit mismatch."
        )
    return expected
