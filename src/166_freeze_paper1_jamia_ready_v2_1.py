from __future__ import annotations

import json
import subprocess
from pathlib import Path

BASE = "f57ddfbdc5ac6c700431a96b281b40cdd1505382"
TAG = "paper1-jamia-ready-2026-10-04"
OUT = Path("outputs/integrity/paper1_extension_freeze.json")
OUT.parent.mkdir(parents=True, exist_ok=True)

def run(*args: str):
    p = subprocess.run(args, text=True, capture_output=True)
    return p.returncode, p.stdout.strip(), p.stderr.strip()

rc, objtype, err = run("git", "cat-file", "-t", BASE)
if rc != 0 or objtype != "commit":
    raise SystemExit(f"Base commit unavailable: {err or objtype}")

rc, current, _ = run("git", "rev-list", "-n", "1", TAG)
if rc == 0 and current:
    if current != BASE:
        raise SystemExit(f"Existing tag {TAG} points to {current}, expected {BASE}")
    state = "already_present"
else:
    rc, _, err = run("git", "tag", TAG, BASE)
    if rc != 0:
        raise SystemExit(f"Could not create local tag: {err}")
    rc, stdout, err = run("git", "push", "origin", f"refs/tags/{TAG}")
    if rc != 0:
        run("git", "tag", "-d", TAG)
        raise SystemExit(f"Could not push tag: {err or stdout}")
    state = "created_and_pushed"

report = {
    "status": "completed",
    "tag": TAG,
    "tagged_commit": BASE,
    "state": state,
    "preservation_branch": "archive/paper1-jamia-ready-2026-10-04",
}
OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, indent=2))
