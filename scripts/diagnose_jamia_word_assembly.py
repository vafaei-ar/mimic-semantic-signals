"""Read-only diagnostic for integrated JAMIA Word-assembly task.

Captures module availability, process status and traceback to a safe aggregate
JSON artifact. It does not read patient data, alter models, or install modules.
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
out = root / "outputs/integrity/jamia_word_assembly_diagnostic.json"
out.parent.mkdir(parents=True, exist_ok=True)

def has_module(name):
    try:
        return importlib.util.find_spec(name) is not None
    except Exception:
        return False

report = {
    "status": "diagnostic_completed",
    "interpreter": sys.executable,
    "python_version": sys.version.split()[0],
    "python_docx_installed": has_module("docx"),
    "libreoffice_path": shutil.which("libreoffice") or shutil.which("soffice"),
    "pymupdf_installed": has_module("fitz"),
    "source_md_exists": (root / "manuscript/JAMIA_WORKING_DRAFT_2026-10-03.md").is_file(),
    "script_exists": (root / "manuscript/build_jamia_integrated_docx.py").is_file(),
}
try:
    proc = subprocess.run(
        [sys.executable, "manuscript/build_jamia_integrated_docx.py"],
        cwd=str(root), capture_output=True, text=True, timeout=110,
    )
    report["assembly_exit_code"] = proc.returncode
    report["stdout_tail"] = proc.stdout[-3000:]
    report["stderr_tail"] = proc.stderr[-5000:]
except Exception as exc:
    report["invocation_error"] = type(exc).__name__ + ": " + str(exc)[:1200]
out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"path":str(out.relative_to(root)), "assembly_exit_code":report.get("assembly_exit_code"), "docx_module":report["python_docx_installed"]}))
