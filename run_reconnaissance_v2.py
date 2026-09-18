from __future__ import annotations

import argparse
import json
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS = [
    "08_semantic_substrate_profile.py",
    "09_event_definition_audit.py",
]

EXPORT_FILES = [
    "semantic_substrate_coverage.csv",
    "semantic_substrate_by_dbsource.csv",
    "event_definition_item_audit.csv",
    "canonical_vasopressor_itemids.csv",
    "event_definition_audit_summary.csv",
    "run_manifest_v2.json",
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--output", default="outputs/recon_v2")
    args = ap.parse_args()

    repo = Path(__file__).resolve().parent
    src = repo / "src"
    out = Path(args.output).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)

    runs = []
    for name in SCRIPTS:
        cmd = [
            sys.executable, str(src / name),
            "--root", str(Path(args.root).expanduser().resolve()),
            "--output", str(out),
        ]
        proc = subprocess.run(cmd, text=True, capture_output=True)
        runs.append({
            "script": name,
            "returncode": proc.returncode,
            "status": "ok" if proc.returncode == 0 else "failed",
            "stderr_tail": proc.stderr[-3000:] if proc.stderr else "",
        })
        print(f"[{'OK' if proc.returncode == 0 else 'FAILED'}] {name}")
        if proc.returncode != 0 and proc.stderr:
            print(proc.stderr[-1200:], file=sys.stderr)

    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": sys.version,
        "root_path": str(Path(args.root).expanduser().resolve()),
        "output_path": str(out),
        "scripts": runs,
        "privacy_note": "Aggregate-only second-pass outputs. No raw note text or patient-level identifiers are exported.",
    }
    (out / "run_manifest_v2.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    zip_path = out / "mimic_feasibility_results_v2.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name in EXPORT_FILES:
            p = out / name
            if p.exists() and p.is_file():
                zf.write(p, arcname=name)

    print(f"\nExport: {zip_path}")


if __name__ == "__main__":
    main()
