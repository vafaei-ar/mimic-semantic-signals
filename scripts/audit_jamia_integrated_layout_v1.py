"""Bounded layout preflight for already-produced JAMIA working DOCX/PDF.

Uses standard Python library and optional existing Poppler text extraction.
Does not alter the manuscript, scientific results, rendered binaries, models,
raw clinical records, or package state. One safe aggregate JSON report.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "outputs/manuscript/jamia_integrated_v1"
DOCX = BASE / "JAMIA_Working_Manuscript_Integrated_v1.docx"
PDF = BASE / "JAMIA_Working_Manuscript_Integrated_v1.pdf"
OUT = ROOT / "outputs/integrity/jamia_integrated_layout_preflight.json"
EXPECTED_DOCX = "ea5730e0f6fe323a39e428043bbedfbfde56a49136aad629d307184c007b023d"
EXPECTED_PDF = "9d2585b4aba9678c1c514e8767877a7d3ed16d991bd4bd500857712f98a8946a"
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
XHTML = {"h": "http://www.w3.org/1999/xhtml"}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def pdf_page_layout(pdf):
    executable = shutil.which("pdftotext")
    if not executable:
        return {"available": False, "reason": "pdftotext executable not available"}
    cmd = [executable, "-bbox", "-enc", "UTF-8", str(pdf), "-"]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=75)
    if proc.returncode:
        return {"available": False, "reason": "pdftotext -bbox failed", "stderr": proc.stderr[-400:]}
    root = ET.fromstring(proc.stdout)
    pages = [node for node in root.iter() if node.tag.rsplit("}", 1)[-1] == "page"]
    results = []
    outside = []
    for index, page in enumerate(pages, 1):
        width = float(page.get("width"))
        height = float(page.get("height"))
        word_nodes = [x for x in page.iter() if x.tag.rsplit("}", 1)[-1] == "word"]
        words = [(w.text or "") for w in word_nodes]
        string = " ".join(words)
        for node in word_nodes:
            x1, y1, x2, y2 = [float(node.get(k)) for k in ("xMin", "yMin", "xMax", "yMax")]
            if x1 < -1.5 or y1 < -1.5 or x2 > width + 1.5 or y2 > height + 1.5:
                outside.append({"page": index, "text": (node.text or "")[:50],
                                "bounds": [round(x1, 1), round(y1, 1), round(x2, 1), round(y2, 1)]})
        results.append({
            "page": index,
            "size_pt": [round(width, 1), round(height, 1)],
            "orientation": "landscape" if width > height else "portrait",
            "word_count": len(words),
            "estimated_text_characters": len(string),
            "has_table_1": "Table 1." in string,
            "has_table_2": "Table 2." in string,
            "has_table_3": "Table 3." in string,
            "has_figure_legend": "Figure 1." in string or "Figure 2." in string,
        })
    return {"available": True, "pages": results, "out_of_page_words": outside[:25],
            "out_of_page_word_count": len(outside)}

def read_docx(docx):
    with zipfile.ZipFile(docx) as z:
        if z.testzip():
            raise RuntimeError("DOCX archive check failed")
        document = ET.fromstring(z.read("word/document.xml"))
    sections = []
    for section in document.findall(".//w:sectPr", NS):
        page = section.find("w:pgSz", NS)
        if page is None:
            continue
        a = {key.rsplit("}", 1)[-1]: value for key, value in page.attrib.items()}
        w = float(a.get("w", "0"))
        h = float(a.get("h", "0"))
        sections.append({"page_width_in": round(w / 1440, 3),
                         "page_height_in": round(h / 1440, 3),
                         "orientation": "landscape" if w > h else "portrait",
                         "explicit_orient": a.get("orient")})
    tables = []
    for tbl in document.findall(".//w:tbl", NS):
        rows = tbl.findall("./w:tr", NS)
        num_cols = max((len(row.findall("./w:tc", NS)) for row in rows), default=0)
        grid = tbl.find("w:tblGrid", NS)
        widths = []
        if grid is not None:
            widths = [
                round(int(n.get(W + "w", "0")) / 1440, 3)
                for n in grid.findall("./w:gridCol", NS)
            ]
        tables.append({"rows": len(rows), "columns": num_cols, "grid_col_widths_in": widths})
    return {"page_sections": sections, "native_tables": tables}

def main():
    if not DOCX.exists() or not PDF.exists():
        raise FileNotFoundError("Expected existing manuscript assets missing")
    doc_hash, pdf_hash = sha(DOCX), sha(PDF)
    if doc_hash != EXPECTED_DOCX or pdf_hash != EXPECTED_PDF:
        raise ValueError("Existing artifacts differ from canonical N58C387J hashes")
    document = read_docx(DOCX)
    pdf = pdf_page_layout(PDF)
    checks = {
        "docx_sha256_matches_runrelay": doc_hash == EXPECTED_DOCX,
        "pdf_sha256_matches_runrelay": pdf_hash == EXPECTED_PDF,
        "three_native_tables": len(document["native_tables"]) == 3,
        "registered_table_shape": [(v["rows"], v["columns"]) for v in document["native_tables"]]
            == [(11, 4), (4, 6), (4, 8)],
    }
    if pdf["available"]:
        checks["all_pdf_pages_have_text"] = all(p["word_count"] > 20 for p in pdf["pages"])
        checks["no_off_page_words"] = pdf["out_of_page_word_count"] == 0
        checks["all_three_table_captions_in_pdf"] = all(
            any(p[f"has_table_{i}"] for p in pdf["pages"]) for i in (1, 2, 3)
        )
    # A multi-column wide table on portrait pages is a specific readability
    # risk, not by itself proof of clipped or illegible printed content.
    has_landscape_section = any(s["orientation"] == "landscape"
                                for s in document["page_sections"])
    eight_cols = document["native_tables"][-1]["columns"] == 8
    cautions = []
    if eight_cols and not has_landscape_section:
        cautions.append("Table 3 has 8 columns, but Word has no landscape page section. Inspect its final-size readability and wrapping.")
    if not pdf["available"]:
        cautions.append("Poppler bbox extraction unavailable. Word/pdf boundaries were not automatically inspected.")
    if pdf["available"] and not any(p["orientation"] == "landscape" for p in pdf["pages"]):
        cautions.append("Rendered PDF contains no landscape pages. The wide comparison table may be compressed.")
    if pdf["available"]:
        for p in pdf["pages"]:
            if p["word_count"] < 80:
                cautions.append(f"Page {p['page']} contains only {p['word_count']} detected words, inspect whitespace/page break.")
    result = {
        "schema_version": 1,
        "scope": "layout preflight of existing confirmed Word and PDF only",
        "project": "mimic-semantic-signals",
        "production_job_id": "N58C387J",
        "sha256": {"docx": doc_hash, "pdf": pdf_hash},
        "document": document,
        "pdf_layout": pdf,
        "checks": checks,
        "warnings": cautions,
        "structural_preflight_pass": all(checks.values()),
        "manual_visual_review": None,
        "no_model_fitting": True,
        "no_patient_level_data": True,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUT.relative_to(ROOT)),
                      "structural_preflight_pass": result["structural_preflight_pass"],
                      "pages": len(pdf.get("pages", [])),
                      "warnings": cautions}, ensure_ascii=False))
    if not result["structural_preflight_pass"]:
        raise SystemExit(2)

if __name__ == "__main__":
    main()
