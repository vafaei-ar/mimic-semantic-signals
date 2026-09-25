from __future__ import annotations

import json
import re
from pathlib import Path


DEFAULT_RECORD = Path("docs/registration/osf_registration.json")
_OSF_ID = re.compile(r"^[A-Za-z0-9]{4,12}$")


def require_osf_registration(
    project_root: Path | str = ".",
    record: Path | str = DEFAULT_RECORD,
) -> dict:
    root = Path(project_root).resolve()
    path = Path(record)
    if not path.is_absolute():
        path = root / path
    if not path.exists():
        raise RuntimeError(
            "CONFIRMATORY ANALYSIS LOCKED: OSF registration record is absent. "
            "Complete and approve the preregistration before running real-label predictive evaluation."
        )

    data = json.loads(path.read_text(encoding="utf-8"))
    reg_id = str(data.get("registration_id") or "").strip()
    registered_at = str(data.get("registered_at") or "").strip()
    status = str(data.get("status") or "").strip().lower()
    doi = str(data.get("doi") or "").strip()
    verification = data.get("verification")
    if not isinstance(verification, dict):
        verification = {}

    problems: list[str] = []
    if not _OSF_ID.fullmatch(reg_id):
        problems.append("registration_id")
    if not registered_at:
        problems.append("registered_at")
    if status != "approved":
        problems.append("status=approved")
    if not doi:
        problems.append("doi")
    if verification.get("osf_hosted_files_download_verified") is not True:
        problems.append("OSF-hosted file hash verification")
    if verification.get("registered_form_text_retrieved") is not True:
        problems.append("registered OSF form text retrieval")
    if verification.get("osf_form_addendum_verbatim_verified") is not True:
        problems.append("verbatim OSF form addendum verification")

    if problems:
        raise RuntimeError(
            "CONFIRMATORY ANALYSIS LOCKED: OSF registration is not fully approved "
            "and verified. Missing gate(s): " + ", ".join(problems) + "."
        )
    return data
