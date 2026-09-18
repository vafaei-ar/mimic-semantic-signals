from __future__ import annotations

import argparse
import json
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path


SCRIPTS = [
    "00_inventory.py",
    "01_dataset_linkage.py",
    "02_note_timing_profile.py",
    "03_candidate_outcomes.py",
    "04_pre_event_coverage.py",
    "05_discharge_followup_profile.py",
    "06_cardiac_multimodal_profile.py",
    "07_feasibility_report.py",
]

EXPORT_FILES = [
    "inventory.csv",
    "inventory_summary.json",
    "linkage_matrix.csv",
    "linkage_details.csv",
    "note_categories.csv",
    "note_timing_summary.csv",
    "candidate_outcomes.csv",
    "outcome_event_counts.csv",
    "outcome_itemid_discovery.json",
    "pre_event_coverage.csv",
    "pre_event_coverage_by_category.csv",
    "discharge_followup.csv",
    "cardiac_linkage.csv",
    "candidate_feasibility.csv",
    "feasibility_report.md",
    "run_manifest.json",
]


def main() -> None:
    ap = argparse.ArgumentParser(description="Run aggregate-only MIMIC feasibility reconnaissance.")
    ap.add_argument("--root", required=True, help="Root containing mimiciii, mimiciv, mimic-iv-note, etc.")
    ap.add_argument("--output", default="outputs/recon_v1")
    args = ap.parse_args()

    repo = Path(__file__).resolve().parent
    src = repo / "src"
    out = Path(args.output).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)

    runs = []
    for name in SCRIPTS:
        script = src / name
        cmd = [sys.executable, str(script), "--output", str(out)]
        if name != "07_feasibility_report.py":
            cmd += ["--root", str(Path(args.root).expanduser().resolve())]
        proc = subprocess.run(cmd, text=True, capture_output=True)
        runs.append({
            "script": name,
            "returncode": proc.returncode,
            "status": "ok" if proc.returncode == 0 else "failed",
            "stderr_tail": proc.stderr[-3000:] if proc.stderr else "",
        })
        label = "OK" if proc.returncode == 0 else "FAILED"
        print(f"[{label}] {name}")
        if proc.returncode != 0 and proc.stderr:
            print(proc.stderr[-1200:], file=sys.stderr)

    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": sys.version,
        "root_path": str(Path(args.root).expanduser().resolve()),
        "output_path": str(out),
        "scripts": runs,
        "privacy_note": "Export bundle contains aggregate reconnaissance outputs only. Raw note text and patient-level identifiers are not intentionally exported.",
    }
    (out / "run_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    zip_path = out / "mimic_feasibility_results.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name in EXPORT_FILES:
            p = out / name
            if p.exists() and p.is_file():
                zf.write(p, arcname=name)

    failures = [x["script"] for x in runs if x["returncode"] != 0]
    print(f"\nExport: {zip_path}")
    if failures:
        print("Some modules failed: " + ", ".join(failures))
        print("The ZIP still contains all successful aggregate outputs and the run manifest.")


if __name__ == "__main__":
    main()
