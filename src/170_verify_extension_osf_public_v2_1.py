from __future__ import annotations

import hashlib
import json
from pathlib import Path

import requests

NODE = "wmyb2"
TARGET = "exploratory_extension_addendum_2026-10.md"
LOCAL = Path("docs/registration") / TARGET
OUT = Path("outputs/integrity/extension_osf_public_verification_v2_1.json")
API = f"https://api.osf.io/v2/nodes/{NODE}/files/osfstorage/"

OUT.parent.mkdir(parents=True, exist_ok=True)

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

local_sha = sha256_file(LOCAL)

resp = requests.get(
    API,
    params={"filter[name]": TARGET, "page[size]": 100},
    headers={"Accept": "application/vnd.api+json", "User-Agent": "mimic-semantic-signals-extension-verifier/1.0"},
    timeout=30,
)
resp.raise_for_status()
payload = resp.json()
items = payload.get("data") if isinstance(payload, dict) else None
if not isinstance(items, list):
    raise RuntimeError("Unexpected OSF file-list response")
matches = []
for item in items:
    if not isinstance(item, dict):
        continue
    attrs = item.get("attributes") or {}
    if attrs.get("name") == TARGET:
        matches.append(item)

if len(matches) != 1:
    raise RuntimeError(f"Expected exactly one public OSF file named {TARGET}; found {len(matches)}")

item = matches[0]
attrs = item.get("attributes") or {}
links = item.get("links") or {}
download_url = links.get("download")
if not download_url:
    raise RuntimeError("OSF file metadata did not include a public download URL")

download = requests.get(
    download_url,
    headers={"User-Agent": "mimic-semantic-signals-extension-verifier/1.0"},
    timeout=30,
)
download.raise_for_status()
public_sha = sha256_bytes(download.content)
sha_match = public_sha == local_sha
if not sha_match:
    raise RuntimeError(f"Public OSF file SHA256 {public_sha} does not match frozen repo file {local_sha}")

report = {
    "analysis": "public OSF exploratory extension addendum verification",
    "status": "completed",
    "reads_outcome_labels": False,
    "reads_clinical_notes": False,
    "node": NODE,
    "target_file": TARGET,
    "publicly_listed": True,
    "public_file_id": item.get("id"),
    "date_created": attrs.get("date_created"),
    "date_modified": attrs.get("date_modified"),
    "size_bytes": attrs.get("size"),
    "materialized_path": attrs.get("materialized_path"),
    "local_sha256": local_sha,
    "public_sha256": public_sha,
    "sha256_match": sha_match,
    "api_url": API,
}
OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, indent=2))
