from __future__ import annotations

import json
import os
import time
from pathlib import Path


def update_progress(*, current=None, total=None, phase: str, message: str, unit: str) -> None:
    target = os.environ.get("RUNRELAY_PROGRESS_FILE")
    if not target:
        return
    payload = {
        "schema_version": 1,
        "phase": str(phase),
        "message": str(message),
        "unit": str(unit),
        "updated_at_epoch": time.time(),
    }
    if current is not None:
        payload["current"] = int(current)
    if total is not None:
        payload["total"] = int(total)
    if current is not None and total:
        payload["fraction"] = max(0.0, min(1.0, float(current) / float(total)))
    path = Path(target)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    os.replace(tmp, path)
