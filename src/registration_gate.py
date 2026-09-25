from __future__ import annotations

import json
import re
from pathlib import Path


DEFAULT_RECORD = Path("docs/registration/osf_registration.json")
_OSF_ID = re.compile(r"^[A-Za-z0-9]{4,12}$")


def require_osf_registration(project_root: Path | str = ".", record: Path | str = DEFAULT_RECORD) -> dict:
    root = Path(project_root).resolve()
    path = Path(record)
    if not path.is_absolute():
        path = root / path
    if not path.exists():
        raise RuntimeError(
            "CONFIRMATORY ANALYSIS LOCKED: OSF registration record is absent. "
            "Complete and submit the preregistration before running real-label predictive evaluation."
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    reg_id = str(data.get("registration_id") or "").strip()
    registered_at = str(data.get("registered_at") or "").strip()
    status = str(data.get("status") or "").strip().lower()
    if status != "registered" or not registered_at or not _OSF_ID.fullmatch(reg_id):
        raise RuntimeError(
            "CONFIRMATORY ANALYSIS LOCKED: invalid OSF registration record. "
            "Expected status=registered, a registration_id, and registered_at."
        )
    return data
