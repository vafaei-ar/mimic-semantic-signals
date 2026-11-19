"""Read-only integrity and accessible-vector audit of generated JAMIA main figures.

Audits the exact six files produced by RunRelay T0EK5K79. Uses only Python
standard-library APIs and the frozen public aggregate source. No model fitting,
patient data, or figure rewriting. Output is a safe derived JSON report.
"""
from __future__ import annotations

import hashlib
import json
import struct
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "outputs/manuscript/jamia_v1"
OUT = ROOT / "outputs/integrity/jamia_main_figures_v1_audit.json"

EXPECTED = {
    "JAMIA_Figure_1_Study_design.pdf": "e09ac9812f5b87ff0e8994ab7427d8186b4cdd129d98c322ea9076fc7ac7e69e",
    "JAMIA_Figure_1_Study_design.png": "b1efd8ea22dfd115ee0f13c966c9233dbe567d13164538754acebdbeae7934a9",
    "JAMIA_Figure_1_Study_design.svg": "f5198092d1536373ad96f57f6a2a682e99f5779558dd2f53c35f8207a9a7d8ba",
    "JAMIA_Figure_2_Primary_delta_AUROC.pdf": "dbe823ec948e28815cd142ddf06f3eb25d522792c34d657089882f7f41bcc0c1",
    "JAMIA_Figure_2_Primary_delta_AUROC.png": "bd89345a43bc3ae6ca0e35177dfd008486c6f5e9b32e6cd3adf145cf3853d3e0",
    "JAMIA_Figure_2_Primary_delta_AUROC.svg": "be58ab3be817c697044e3cccb4e1df4ddfa6227f1aa42b9b5d7d2aa80a5840ad",
}
TEXT_EXPECTATIONS = {
    "JAMIA_Figure_1_Study_design.svg": [
        "ICU admission", "12-h landmark", "Ventilation", "RRT", "ICU death",
        "Model comparison", "Eight predefined scores"
    ],
    "JAMIA_Figure_2_Primary_delta_AUROC.svg": [
        "Invasive ventilation", "Renal replacement therapy", "ICU death",
        "ΔAUROC", "500-valid-refit",
    ],
}
EXPECTED_PRIMARY = [
    ("Invasive ventilation", -0.00005, -0.02173, 0.01910),
    ("Renal replacement therapy", -0.00079, -0.00323, 0.00275),
    ("ICU death", -0.00212, -0.00802, 0.00531),
]


def main():
    source = ROOT / "manuscript/figure1_nature_style_data.json"
    aggregate = json.loads(source.read_text(encoding="utf-8"))
    primary = [r for r in aggregate["forest"] if r["kind"] == "primary"]
    source_checks = {
        "n_primary": len(primary) == 3,
        "cohort_counts": [(x["n"], x["cases"]) for x in aggregate["design"]["cohorts"][:3]]
            == [(11116, 279), (19395, 314), (19811, 214)],
        "landmark": aggregate["design"]["landmark_hours"] == 12,
        "horizon": aggregate["design"]["horizon_hours"] == 12,
    }
    for row, (name, est, lo, hi) in zip(primary, EXPECTED_PRIMARY):
        source_checks[name] = (
            row["group"] == name and
            abs(float(row["estimate"]) - est) < 1e-7 and
            abs(float(row["lo"]) - lo) < 1e-7 and
            abs(float(row["hi"]) - hi) < 1e-7
        )
    records = []
    errors = []
    for filename, expected_hash in EXPECTED.items():
        path = ARTIFACTS / filename
        if not path.is_file():
            errors.append(f"missing: {filename}")
            continue
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        item = {"name": filename, "size_bytes": len(data), "sha256": digest,
                "matches_t0ek5k79_artifact": digest == expected_hash}
        if digest != expected_hash:
            errors.append(f"sha256 mismatch: {filename}")
        if filename.endswith(".png"):
            if not data.startswith(bytes.fromhex("89504e470d0a1a0a")):
                errors.append(f"invalid PNG signature: {filename}")
            else:
                width, height = struct.unpack(">II", data[16:24])
                item["width_px"] = width
                item["height_px"] = height
                if min(width, height) < 700:
                    errors.append(f"unexpectedly small PNG: {filename}")
        elif filename.endswith(".pdf"):
            item["pdf_header_valid"] = data.startswith(b"%PDF-")
            item["pdf_eof_present"] = b"%%EOF" in data[-300:]
            if not item["pdf_header_valid"] or not item["pdf_eof_present"]:
                errors.append(f"PDF structure signature failed: {filename}")
        elif filename.endswith(".svg"):
            root = ET.fromstring(data)
            ns_tag = root.tag.rsplit("}", 1)[-1]
            texts = [e for e in root.iter() if e.tag.rsplit("}", 1)[-1] == "text"]
            rendered_text = " ".join("".join(e.itertext()) for e in texts)
            item["editable_text_elements"] = len(texts)
            item["view_box"] = root.get("viewBox")
            item["text_checks"] = {
                token: token in rendered_text
                for token in TEXT_EXPECTATIONS[filename]
            }
            if ns_tag != "svg" or len(texts) < 4:
                errors.append(f"SVG editability or structure failed: {filename}")
            for token, passed in item["text_checks"].items():
                if not passed:
                    errors.append(f"SVG label missing: {filename} / {token}")
        records.append(item)

    for name, passed in source_checks.items():
        if not passed:
            errors.append(f"frozen source mismatch: {name}")
    report = {
        "schema_version": 1,
        "job_id_inspected": "T0EK5K79",
        "project": "mimic-semantic-signals",
        "scientific_model_execution": False,
        "figure_render_execution": False,
        "audit_scope": "binary structure, SHA-256, raster dimensions, editable SVG text, frozen source values",
        "files_expected": 6,
        "files_verified": len(records),
        "source_checks": source_checks,
        "files": records,
        "errors": errors,
        "integrity_pass": not errors and len(records) == len(EXPECTED),
        "manual_visual_inspection_pass": None,
        "manual_visual_inspection_note": "Not assessed by this automated audit. Inspect final-size figures for layout, clipping, collisions and legibility before journal submission.",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "completed" if report["integrity_pass"] else "failed",
                      "output": str(OUT.relative_to(ROOT)),
                      "files_verified": len(records), "errors": errors}))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
