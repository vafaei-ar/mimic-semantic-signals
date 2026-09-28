from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import subprocess
from pathlib import Path


REGISTERED_MODEL = "com-kotobalabs/open-jev-deberta-v3-large"
REGISTERED_REVISION = "19bf9a64815add579fbf6c907bef584d9277a8e4"
REGISTERED_TYPED = "10d7834d3b99041f890db4615fb38ef95ced50cc"
REGISTERED_SCHEMA = "72763082c314a4542817ccfcd42d2b10d9446fc8e84c3391a2140790b2483623"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def inspect_typed_decisions() -> dict:
    out = {
        "import_ok": False,
        "module_parent_name": None,
        "git_repo_found": False,
        "git_commit": None,
        "distribution_found": False,
        "distribution_name": None,
        "distribution_version": None,
        "direct_url_present": False,
        "direct_url_vcs_commit": None,
        "registered_commit_match": False,
        "error": None,
    }
    try:
        import typed_decisions
        out["import_ok"] = True
        module_path = Path(typed_decisions.__file__).resolve()
        out["module_parent_name"] = module_path.parent.name

        for parent in [module_path.parent, *module_path.parents]:
            if (parent / ".git").exists():
                out["git_repo_found"] = True
                proc = subprocess.run(
                    ["git", "-C", str(parent), "rev-parse", "HEAD"],
                    capture_output=True,
                    text=True,
                )
                if proc.returncode == 0:
                    out["git_commit"] = proc.stdout.strip() or None
                break

        for dist_name in ("typed-decisions", "typed_decisions"):
            try:
                dist = importlib.metadata.distribution(dist_name)
            except importlib.metadata.PackageNotFoundError:
                continue
            out["distribution_found"] = True
            out["distribution_name"] = dist.metadata.get("Name") or dist_name
            out["distribution_version"] = dist.version
            direct = dist.read_text("direct_url.json")
            if direct:
                out["direct_url_present"] = True
                try:
                    data = json.loads(direct)
                    out["direct_url_vcs_commit"] = (
                        (data.get("vcs_info") or {}).get("commit_id")
                    )
                except json.JSONDecodeError:
                    pass
            break

        # direct_url.json is authoritative for the installed VCS package.
        # A parent .git directory can belong to the Medical JEV project itself.
        observed = out["direct_url_vcs_commit"]
        out["registered_commit_match"] = observed == REGISTERED_TYPED
    except Exception as exc:
        out["error"] = f"{type(exc).__name__}: {exc}"
    return out


def inspect_openjev_cache() -> dict:
    out = {
        "huggingface_hub_import_ok": False,
        "snapshot_resolved": False,
        "snapshot_leaf": None,
        "registered_revision_match": False,
        "error": None,
    }
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    try:
        from huggingface_hub import snapshot_download
        out["huggingface_hub_import_ok"] = True
        snap = snapshot_download(
            repo_id=REGISTERED_MODEL,
            revision=REGISTERED_REVISION,
            local_files_only=True,
        )
        p = Path(snap).resolve()
        out["snapshot_resolved"] = True
        out["snapshot_leaf"] = p.name
        out["registered_revision_match"] = p.name == REGISTERED_REVISION
    except Exception as exc:
        out["error"] = f"{type(exc).__name__}: {exc}"
    return out


def inspect_openjev_import() -> dict:
    out = {"openjev_import_ok": False, "error": None}
    try:
        from typed_decisions.open_jev import OpenJev  # noqa: F401
        out["openjev_import_ok"] = True
    except Exception as exc:
        out["error"] = f"{type(exc).__name__}: {exc}"
    return out


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    schema_hash = sha256_file(root / "src" / "semantic_schema.py")

    report = {
        "analysis": "Registered Open-Jev v2.1 environment preflight",
        "clinical_data_read": False,
        "outcome_labels_read": False,
        "semantic_inference_run": False,
        "registered": {
            "model_id": REGISTERED_MODEL,
            "model_revision": REGISTERED_REVISION,
            "typed_decisions_commit": REGISTERED_TYPED,
            "semantic_schema_sha256": REGISTERED_SCHEMA,
        },
        "semantic_schema": {
            "observed_sha256": schema_hash,
            "registered_match": schema_hash == REGISTERED_SCHEMA,
        },
        "typed_decisions": inspect_typed_decisions(),
        "openjev_cache": inspect_openjev_cache(),
        "openjev_import": inspect_openjev_import(),
    }

    checks = [
        report["semantic_schema"]["registered_match"],
        report["typed_decisions"]["import_ok"],
        report["typed_decisions"]["registered_commit_match"],
        report["openjev_cache"]["snapshot_resolved"],
        report["openjev_cache"]["registered_revision_match"],
        report["openjev_import"]["openjev_import_ok"],
    ]
    report["ready_for_registered_inference"] = bool(all(checks))

    out = root / "outputs" / "integrity" / "v2_1_registered_openjev_environment_preflight.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))

    if not report["ready_for_registered_inference"]:
        raise RuntimeError("Registered Open-Jev environment preflight failed; see safe aggregate artifact.")


if __name__ == "__main__":
    main()
