from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

candidates = [
    ".venv/bin/python",
    "/usr/bin/python3",
    str(Path.home() / "miniconda3/bin/python"),
]

rows = []
for candidate in candidates:
    p = Path(candidate).expanduser()
    item = {"python": str(p), "exists": p.exists(), "matplotlib_ok": False}
    if p.exists():
        proc = subprocess.run(
            [str(p), "-c", "import sys, matplotlib; print(sys.executable); print(matplotlib.__version__)"],
            text=True,
            capture_output=True,
        )
        item["returncode"] = int(proc.returncode)
        item["stdout"] = proc.stdout.strip()
        item["stderr"] = proc.stderr.strip()
        item["matplotlib_ok"] = proc.returncode == 0
    rows.append(item)

out = Path("outputs/integrity/paper1_figure_python_environment.json")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps({"candidates": rows}, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"candidates": rows}, indent=2))
