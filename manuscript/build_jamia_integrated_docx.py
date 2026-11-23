"""Build the JAMIA Word working manuscript from the repository's exact Markdown.

All numbered references and narrative remain as supplied. Native Word
tables replace the three Markdown tables; Table 3 uses a landscape page.
Zotero field linking and final figure visual QA are separate milestones.
Only aggregate public manuscript content is read. No outcomes are modeled.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import zipfile
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENTATION, WD_SECTION_START
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "manuscript/JAMIA_WORKING_DRAFT_2026-10-03.md"
OUT = ROOT / "outputs/manuscript/jamia_integrated_v1"
TARGET = OUT / "JAMIA_Working_Manuscript_Integrated_v1.docx"
AUDIT = OUT / "JAMIA_Working_Manuscript_Integrated_v1_QA.json"
PRIMARY = [
    ["Invasive ventilation", "0.72468", "0.72463", "-0.00005", "-0.02173 to +0.01910", "+0.00387"],
    ["Renal replacement therapy", "0.97394", "0.97315", "-0.00079", "-0.00323 to +0.00275", "-0.00048"],
    ["ICU death, MetaVision", "0.93338", "0.93126", "-0.00212", "-0.00802 to +0.00531", "+0.00087"],
]

def blob_sha(content):
    return hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()

def inline(paragraph, text):
    for part in re.split(r"(\*\*[^*]+\*\*|\*[^*]+\*)", text):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            r = paragraph.add_run(part[2:-2])
            r.bold = True
        elif part.startswith("*") and part.endswith("*"):
            r = paragraph.add_run(part[1:-1])
            r.italic = True
        else:
            paragraph.add_run(part)

def size_section(section, landscape=False):
    section.orientation = WD_ORIENTATION.LANDSCAPE if landscape else WD_ORIENTATION.PORTRAIT
    section.page_width = Inches(11 if landscape else 8.5)
    section.page_height = Inches(8.5 if landscape else 11)
    section.top_margin = Inches(.76)
    section.bottom_margin = Inches(.76)
    section.left_margin = Inches(.72 if landscape else .83)
    section.right_margin = Inches(.72 if landscape else .83)

def styles(doc):
    n = doc.styles["Normal"]
    n.font.name = "Cambria"
    n.font.size = Pt(10.5)
    n.font.color.rgb = RGBColor(35, 43, 50)
    n.paragraph_format.line_spacing = 1.16
    n.paragraph_format.space_after = Pt(6)
    for name, pt in [("Heading 1", 12.2), ("Heading 2", 11.2)]:
        s = doc.styles[name]
        s.font.name = "Cambria"
        s.font.size = Pt(pt)
        s.font.bold = True
        s.paragraph_format.space_before = Pt(12)
        s.paragraph_format.space_after = Pt(6)
        s.paragraph_format.keep_with_next = True

def head_style(row):
    tr_pr = row._tr.get_or_add_trPr()
    tag = OxmlElement("w:tblHeader")
    tag.set(qn("w:val"), "true")
    tr_pr.append(tag)
    for cell in row.cells:
        pr = cell._tc.get_or_add_tcPr()
        sh = OxmlElement("w:shd")
        sh.set(qn("w:fill"), "E8EDF2")
        pr.append(sh)

def add_table(doc, rows, idx):
    if not rows or not all(len(x) == len(rows[0]) for x in rows):
        raise ValueError("Irregular Markdown table " + str(idx))
    table = doc.add_table(rows=len(rows), cols=len(rows[0]))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"
    table.autofit = False
    widths = {
        1: [2.15, 1.57, 1.57, 1.57],
        2: [1.36, .97, .97, .91, 1.52, 1.10],
        3: [1.63, .95, .95, .88, 1.25, 1.15, 1.17, 1.16],
    }[idx]
    for i, values in enumerate(rows):
        for j, value in enumerate(values):
            cell = table.cell(i, j)
            cell.width = Inches(widths[j])
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            cell.text = ""
            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.line_spacing = 1.02
            if j:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            inline(p, value)
            for run in p.runs:
                run.font.size = Pt(7.5 if idx == 3 else 8.1)
                if i == 0:
                    run.bold = True
    head_style(table.rows[0])
    return table

def table_row(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]

def main():
    raw = SOURCE.read_bytes()
    text = raw.decode("utf-8")
    lines = text.splitlines()
    first = lines.index("## Title page")
    lines = lines[first:]
    doc = Document()
    size_section(doc.sections[0])
    styles(doc)
    table_data = []
    ref_count = 0
    figure_legends = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if line.startswith("|"):
            block = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                block.append(table_row(lines[i]))
                i += 1
            block = [row for row in block if not all(re.fullmatch(r":?-{3,}:?", c) for c in row)]
            idx = len(table_data) + 1
            add_table(doc, block, idx)
            table_data.append(block)
            if idx == 3:
                section = doc.add_section(WD_SECTION_START.NEW_PAGE)
                size_section(section, landscape=False)
            continue
        if line.startswith("**Table "):
            if line.startswith("**Table 3."):
                section = doc.add_section(WD_SECTION_START.NEW_PAGE)
                size_section(section, landscape=True)
            p = doc.add_paragraph(style="Caption")
            p.paragraph_format.keep_with_next = True
            inline(p, line)
        elif line == "## Title page":
            pass
        elif line.startswith("## "):
            h = line[3:]
            if h in ("Abstract", "Figure legends"):
                doc.add_page_break()
            doc.add_heading(h, level=1)
        elif line.startswith("### "):
            h = line[4:]
            doc.add_heading(h, level=2)
            if h.startswith("Figure "):
                figure_legends.append(h)
        elif line.startswith("**Title:**"):
            p = doc.add_paragraph(style="Title")
            inline(p, line[len("**Title:**"):].strip())
        elif re.match(r"^\d+\.\s", line):
            ref_count += 1
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Inches(.20)
            p.paragraph_format.first_line_indent = Inches(-.20)
            p.paragraph_format.space_after = Pt(4)
            inline(p, line)
        elif line.startswith("- "):
            p = doc.add_paragraph(style="List Bullet")
            inline(p, line[2:])
        else:
            p = doc.add_paragraph()
            inline(p, line)
        i += 1

    if len(table_data) != 3 or [len(x) for x in table_data] != [11, 4, 4]:
        raise ValueError("Unexpected Word table inventory")
    if table_data[1][1:] != PRIMARY:
        raise ValueError("Registered Table 2 diverges from its frozen five-decimal values")
    if ref_count != 17 or len(figure_legends) != 2:
        raise ValueError(f"References or figure legends missing: refs={ref_count}, figs={figure_legends}")
    OUT.mkdir(parents=True, exist_ok=True)
    doc.save(TARGET)
    with zipfile.ZipFile(TARGET) as archive:
        if archive.testzip() is not None:
            raise ValueError("Corrupted DOCX archive")
    reread = Document(TARGET)
    if len(reread.tables) != 3 or len(reread.sections) != 3:
        raise ValueError("Roundtrip tables or orientation sections did not survive")
    if reread.sections[1].orientation != WD_ORIENTATION.LANDSCAPE:
        raise ValueError("Table 3 landscape orientation missing")
    if [[cell.text for cell in row.cells] for row in reread.tables[1].rows[1:]] != PRIMARY:
        raise ValueError("DOCX data cells diverge from source")

    report = {
        "status": "passed",
        "source_path": str(SOURCE.relative_to(ROOT)),
        "source_git_blob_sha1": blob_sha(raw),
        "docx_path": str(TARGET.relative_to(ROOT)),
        "docx_sha256": hashlib.sha256(TARGET.read_bytes()).hexdigest(),
        "table_rows_including_header": [len(t.rows) for t in reread.tables],
        "table_columns": [len(t.columns) for t in reread.tables],
        "word_sections": len(reread.sections),
        "wide_table_landscape": True,
        "references_preserved": ref_count,
        "figure_legends": figure_legends,
        "Zotero_fields_embedded": False,
        "figure_images_embedded": False,
        "patient_level_data": False,
        "new_scientific_analysis": False,
        "manual_visual_QA": None,
    }
    office = shutil.which("libreoffice") or shutil.which("soffice")
    if office:
        try:
            profile = OUT / ".lo_profile"
            cp = subprocess.run(
                [office, "-env:UserInstallation=" + profile.as_uri(),
                 "--headless", "--convert-to", "pdf", "--outdir", str(OUT), str(TARGET)],
                timeout=150, capture_output=True, text=True,
            )
            pdf = TARGET.with_suffix(".pdf")
            if cp.returncode == 0 and pdf.exists() and pdf.stat().st_size > 3000:
                report["pdf_rendered"] = True
                try:
                    import fitz
                    handle = fitz.open(pdf)
                    report["pdf_pages"] = len(handle)
                    report["all_pages_nonempty"] = all(len(p.get_text().strip()) > 20 for p in handle)
                except ImportError:
                    report["pdf_pages"] = None
            else:
                report["pdf_rendered"] = False
                report["render_error"] = (cp.stderr or cp.stdout)[-300:]
        except Exception as exc:
            report["pdf_rendered"] = False
            report["render_error"] = str(exc)[:300]
    else:
        report["pdf_rendered"] = False
        report["render_error"] = "LibreOffice not available in workstation environment"
    AUDIT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"docx": report["docx_path"], "docx_sha256": report["docx_sha256"],
                      "tables": report["table_rows_including_header"],
                      "refs": report["references_preserved"],
                      "pdf_rendered": report["pdf_rendered"]}))

if __name__ == "__main__":
    main()
