"""Reproducibly assemble JAMIA working manuscript as an editable Word file.

Uses only Python standard library and the workstation's existing LibreOffice,
avoiding any dependency installation. It reads the tracked Markdown manuscript
and generates three native Word tables, 18 numbered references and two figure
legends. No patient-level data, notes, predictions or model fitting are used.
The references remain numbered plaintext, not Zotero-linked Word fields.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import shutil
import subprocess
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from word_core_properties import set_title_creator

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "manuscript/JAMIA_SUBMISSION_CANDIDATE_2026-11-23.md"
OUT = ROOT / "outputs/manuscript/jamia_submission_candidate_20261123"
TARGET = OUT / "JAMIA_Submission_Candidate_2026-11-23.docx"
QA = OUT / "JAMIA_Submission_Candidate_2026-11-23_QA.json"
EXPECTED_SOURCE_BLOB = "18a002a77e472b3247fe17171b00ebaa245f21fd"
EXPECTED_PRIMARY = [
    ["Invasive ventilation", "0.72468", "0.72463", "-0.00005", "-0.02173 to +0.01910", "+0.00387"],
    ["Renal replacement therapy", "0.97394", "0.97315", "-0.00079", "-0.00323 to +0.00275", "-0.00048"],
    ["ICU death, MetaVision", "0.93338", "0.93126", "-0.00212", "-0.00802 to +0.00531", "+0.00087"],
]
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

def git_blob(data: bytes):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def rich(content):
    # Preserve all original prose, link text, citation numbering and symbols.
    parts = re.split(r"(\*\*[^*]+\*\*|\*[^*]+\*)", content)
    out = []
    for part in parts:
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            out.append("<strong>" + html.escape(part[2:-2]) + "</strong>")
        elif part.startswith("*") and part.endswith("*"):
            out.append("<em>" + html.escape(part[1:-1]) + "</em>")
        else:
            out.append(html.escape(part))
    return "".join(out)

def cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]

def doc_html(source):
    lines = source.splitlines()
    start = lines.index("## Title page")
    lines = lines[start:]
    out = []
    tables = []
    refcount = 0
    figures = []
    i = 0
    while i < len(lines):
        s = lines[i].strip()
        if not s:
            i += 1
            continue
        if s.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(cells(lines[i]))
                i += 1
            rows = [row for row in rows if not all(re.fullmatch(r":?-{3,}:?", v) for v in row)]
            idx = len(tables) + 1
            if not all(len(r) == len(rows[0]) for r in rows):
                raise ValueError("Unequal source table width in table " + str(idx))
            tables.append(rows)
            out.append('<table class="data table' + str(idx) + '">')
            for ri, row in enumerate(rows):
                out.append("<tr>" + "".join(
                    "<" + ("th" if ri == 0 else "td") + ">" + rich(c) +
                    "</" + ("th" if ri == 0 else "td") + ">"
                    for c in row) + "</tr>")
            out.append("</table>")
            continue
        if s == "## Title page":
            i += 1
            continue
        if s.startswith("## "):
            title = s[3:]
            marker = " page-break" if title in ("Abstract", "Figure legends") else ""
            out.append('<h2 class="chapter' + marker + '">' + rich(title) + "</h2>")
        elif s.startswith("### "):
            title = s[4:]
            out.append("<h3>" + rich(title) + "</h3>")
            if title.startswith("Figure "):
                figures.append(title)
        elif s.startswith("**Table "):
            out.append('<p class="caption">' + rich(s) + "</p>")
        elif s.startswith("**Title:**"):
            out.append('<h1 class="paper-title">' + rich(s[len("**Title:**"):].strip()) + "</h1>")
        elif re.match(r"^\d+\.\s", s):
            refcount += 1
            out.append('<p class="reference">' + rich(s) + "</p>")
        elif s.startswith("- "):
            out.append('<p class="bullet">' + rich(s[2:]) + "</p>")
        else:
            out.append("<p>" + rich(s) + "</p>")
        i += 1
    if len(tables) != 3 or [len(t) for t in tables] != [11, 4, 4]:
        raise ValueError("Expected three registered tables with 11, 4, and 4 rows")
    if tables[1][1:] != EXPECTED_PRIMARY:
        raise ValueError("Frozen primary Table 2 values mismatch")
    if refcount != 18 or len(figures) != 2:
        raise ValueError(f"Source lost references or figures: {refcount} references and {len(figures)} legends")
    css = """
    @page { size: 8.5in 11in; margin: .78in .77in; }
    body { font-family: Cambria, 'Times New Roman', serif; font-size: 11pt;
           color: #2a3138; line-height: 2.0; }
    p { margin: 0 0 6pt 0; }
    h1.paper-title { font-size: 16pt; color: #243341; font-weight: bold;
                     margin: 0 0 16pt 0; line-height:1.1; }
    h2.chapter { font-size: 12.2pt; color: #263d52; font-weight: bold;
                 margin: 13pt 0 7pt 0; page-break-after: avoid; }
    h3 { font-size: 11pt; color: #263d52; font-weight:bold;
         margin:11pt 0 5pt 0; page-break-after:avoid; }
    .caption {font-size:9pt;font-weight:bold;margin:12pt 0 5pt 0;
              page-break-after:avoid;}
    table.data { border-collapse:collapse; width:100%; margin: 4pt 0 12pt 0;
                 font-size: 8.1pt; line-height:1.15; table-layout:fixed; }
    table.data th { background:#e8edf2; font-weight:bold; }
    table.data th, table.data td { border: .5pt solid #cbd3d9;
                 padding: 4pt 4pt; vertical-align:middle; }
    table.data td:not(:first-child) { text-align:center; }
    table.table1 th:first-child,table.table1 td:first-child { width:32%; }
    table.table2 th:first-child,table.table2 td:first-child { width:21%; }
    table.table3 {font-size:7.5pt;}
    table.table3 th:first-child,table.table3 td:first-child {width:18%;}
    .reference {margin:0 0 4pt .2in; text-indent:-.2in; font-size:9pt;}
    .bullet {margin:0 0 5pt .25in;}
    .page-break {page-break-before:always;}
    """
    result = ('<!DOCTYPE html><html><head><meta charset="utf-8"><title>JAMIA Submission Candidate</title>'
              '<style>' + css + '</style></head><body>' + "\n".join(out) + '</body></html>\n')
    return result, tables, refcount, figures



def enforce_double_spaced_paragraphs(docx_path):
    """Set explicit double spacing for all body paragraphs outside tables.

    Preserve the original Word package, original text, metadata, and the
    existing landscape section. Table cells keep their compact spacing.
    """
    with zipfile.ZipFile(docx_path, "r") as src:
        items = [(item, src.read(item.filename)) for item in src.infolist()]
    xml = next(data for item, data in items if item.filename == "word/document.xml").decode("utf-8")
    table_spans = []
    for table in re.finditer(r"<w:tbl(?=[\s>]).*?</w:tbl>", xml, flags=re.S):
        table_spans.append((table.start(), table.end()))
    paragraphs = list(re.finditer(r"<w:p(?=[\s>])[^>]*>.*?</w:p>", xml, flags=re.S))
    edits = []
    for p in paragraphs:
        if any(a <= p.start() < b for a, b in table_spans):
            continue
        body = p.group()
        if "<w:sectPr" in body:
            continue
        spacing = '<w:spacing w:line="480" w:lineRule="auto"/>'
        if re.search(r"<w:pPr(?:\s[^>]*)?>", body):
            body = re.sub(r"<w:spacing\b[^>]*/>", "", body)
            body = body.replace("</w:pPr>", spacing + "</w:pPr>", 1)
        else:
            body = re.sub(r"^(<w:p(?:\s[^>]*)?>)", r"\1<w:pPr>" + spacing + "</w:pPr>", body, count=1)
        edits.append((p.start(), p.end(), body))
    if len(edits) < 35:
        raise ValueError("Too few paragraphs for double-spacing verification")
    fixed = xml
    for begin, end, body in reversed(edits):
        fixed = fixed[:begin] + body + fixed[end:]
    ET.fromstring(fixed.encode("utf-8"))
    temp = docx_path.with_suffix(".spacing.tmp")
    with zipfile.ZipFile(temp, "w") as dst:
        for item, data in items:
            dst.writestr(item, fixed.encode("utf-8") if item.filename == "word/document.xml" else data)
    temp.replace(docx_path)
    check = fixed.count('w:line="480"')
    if check < len(edits):
        raise ValueError("Did not persist explicit double spacing")
    return {"double_spaced_body_paragraphs": len(edits), "line_twips": 480,
            "tables_keep_compact_spacing": True}


def orient_table3_landscape(docx_path):
    """Isolate the eight-column Table 3 in a landscape Word section.

    Keep all manuscript text, registered values, and other tables untouched.
    Change only document.xml, using standard library to avoid workstation
    dependency changes. The original final section remains portrait.
    """
    with zipfile.ZipFile(docx_path, "r") as src:
        files = [(item, src.read(item.filename)) for item in src.infolist()]
    document = next(payload for item, payload in files if item.filename == "word/document.xml")
    xml = document.decode("utf-8")
    starts = [m.start() for m in re.finditer(r"<w:tbl(?=[\s>])", xml)]
    if len(starts) != 3:
        raise ValueError("Expected exactly three tables before orientation repair")
    table_start = starts[2]
    table_end_at = xml.find("</w:tbl>", table_start)
    if table_end_at < 0:
        raise ValueError("Could not locate complete Table 3")
    table_end = table_end_at + len("</w:tbl>")
    cap_match = list(re.finditer(r"<w:p(?=[\s>])", xml[:table_start]))
    if not cap_match:
        raise ValueError("Table 3 caption is missing")
    caption_start = cap_match[-1].start()
    caption_end = xml.find("</w:p>", caption_start) + len("</w:p>")
    caption_xml = xml[caption_start:caption_end]
    caption_text = html.unescape("".join(re.findall(
        r"<w:t(?:\s[^>]*)?>(.*?)</w:t>", caption_xml, flags=re.S)))
    if "Table 3" not in caption_text:
        raise ValueError("Cannot safely locate Table 3 caption")
    sections = list(re.finditer(r"<w:sectPr(?:\s[^>]*)?>.*?</w:sectPr>", xml, flags=re.S))
    if len(sections) != 1 or sections[0].start() < table_end:
        raise ValueError("Expected one final portrait section after Table 3")
    portrait = sections[0].group()
    if not re.search(r"<w:pgSz\b[^>]*/>", portrait):
        raise ValueError("Cannot identify original page size")
    if 'w:orient="landscape"' in portrait:
        raise ValueError("Original final section is not portrait")
    # A section's properties apply to the content preceding its break.
    # The caption and Table 3 therefore live between a portrait break
    # and a landscape break; all following content resumes portrait.
    portrait_break = re.sub(
        r"(<w:sectPr(?:\s[^>]*)?>)", r'\1<w:type w:val="nextPage"/>',
        portrait, count=1)
    landscape_break = re.sub(
        r"(<w:sectPr(?:\s[^>]*)?>)", r'\1<w:type w:val="nextPage"/>',
        portrait, count=1)
    landscape_break = re.sub(
        r"<w:pgSz\b[^>]*/>",
        '<w:pgSz w:w="15840" w:h="12240" w:orient="landscape"/>',
        landscape_break, count=1)
    # Increase the grid and cell widths from the original portrait
    # geometry (7.32in) to the available landscape text width (~8.9in).
    table_xml = xml[table_start:table_end]
    def widened(match):
        return match.group(1) + str(round(int(match.group(2)) * 1.20)) + match.group(3)
    for tag in ("gridCol", "tcW"):
        table_xml = re.sub(
            r'(<w:' + tag + r'\b[^>]*\bw:w=")(\d+)(")',
            widened, table_xml)
    # Only scale fixed-width tblW. Percent and automatic widths remain unchanged.
    table_xml = re.sub(
        r'(<w:tblW\b(?=[^>]*w:type="dxa")[^>]*\bw:w=")(\d+)(")',
        widened, table_xml)
    before = "<w:p><w:pPr>" + portrait_break + "</w:pPr></w:p>"
    after = "<w:p><w:pPr>" + landscape_break + "</w:pPr></w:p>"
    fixed = xml[:caption_start] + before + xml[caption_start:table_start]
    fixed += table_xml + after + xml[table_end:]
    ET.fromstring(fixed.encode("utf-8"))  # Fail before replacing the original.
    temp = docx_path.with_suffix(".layout.tmp")
    with zipfile.ZipFile(temp, "w") as dst:
        for item, payload in files:
            dst.writestr(item, fixed.encode("utf-8") if item.filename == "word/document.xml" else payload)
    temp.replace(docx_path)
    return {"table3_landscape_section": True, "other_sections_portrait": True,
            "table3_grid_width_scale": 1.20}

def extract_word_tables(docx_path):
    with zipfile.ZipFile(docx_path) as package:
        if package.testzip() is not None:
            raise ValueError("DOCX package failed ZIP validation")
        xml = package.read("word/document.xml")
    root = ET.fromstring(xml)
    result = []
    for table in root.findall(".//w:tbl", NS):
        rows = []
        for tr in table.findall("./w:tr", NS):
            row = []
            for cell in tr.findall("./w:tc", NS):
                row.append("".join(t.text or "" for t in cell.findall(".//w:t", NS)).strip())
            rows.append(row)
        result.append(rows)
    return result, xml

def main():
    data = SRC.read_bytes()
    source_sha = git_blob(data)
    if source_sha != EXPECTED_SOURCE_BLOB:
        raise ValueError("Manuscript source moved from frozen text. Refuse to assemble.")
    source = data.decode("utf-8")
    # Remove repository preface: the journal Word file starts with its title page.
    if "## Title page" not in source:
        raise ValueError("Missing manuscript title page")
    source = source[source.index("## Title page"):]
    markup, original_tables, references, figures = doc_html(source)
    OUT.mkdir(parents=True, exist_ok=True)
    html_file = OUT / "JAMIA_Submission_Candidate_2026-11-23.html"
    html_file.write_text(markup, encoding="utf-8")
    office = shutil.which("libreoffice") or shutil.which("soffice")
    if not office:
        raise RuntimeError("LibreOffice is not installed in the bound environment")
    profile = OUT / ".lo_profile_docx"
    cmd = [
        office, "-env:UserInstallation=" + profile.as_uri(), "--headless",
        "--infilter=HTML (StarWriter)", "--convert-to", "docx:Office Open XML Text",
        "--outdir", str(OUT), str(html_file)
    ]
    cp = subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=False)
    if cp.returncode != 0 or not TARGET.is_file():
        raise RuntimeError("DOCX conversion failed: " + (cp.stderr or cp.stdout)[-900:])
    layout_changes = orient_table3_landscape(TARGET)
    paragraph_spacing = enforce_double_spaced_paragraphs(TARGET)
    title = next((line.split("**Title:**", 1)[1].strip()
                  for line in source.splitlines() if line.startswith("**Title:**")), "")
    author = next((line.split("**Author:**", 1)[1].strip()
                   for line in source.splitlines() if line.startswith("**Author:**")), "")
    if not title or not author:
        raise ValueError("Cannot verify author/title from manuscript title page")
    metadata = set_title_creator(TARGET, title, author.split(",")[0])
    word_tables, xml = extract_word_tables(TARGET)
    if len(word_tables) != 3:
        raise ValueError(f"Word native table count {len(word_tables)} != 3")
    if word_tables[1][1:] != EXPECTED_PRIMARY:
        raise ValueError("DOCX roundtrip altered registered Table 2 cells: " + str(word_tables[1][1:]))
    for ti in range(3):
        if len(word_tables[ti]) != len(original_tables[ti]):
            raise ValueError("Word table lost rows: " + str(ti + 1))
    doc_text = "".join((t.text or "") for t in ET.fromstring(xml).findall(".//w:t", NS))
    for phrase in ("Background and Significance", "Materials and Methods", "Discussion",
                   "Conclusion", "Figure 1.", "Figure 2.", "Competing interests"):
        if phrase not in doc_text:
            raise ValueError("Missing manuscript section " + phrase)
    pdf_file = TARGET.with_suffix(".pdf")
    pdf_proc = subprocess.run([
        office, "-env:UserInstallation=" + (OUT / ".lo_profile_pdf").as_uri(),
        "--headless", "--convert-to", "pdf", "--outdir", str(OUT), str(TARGET)
    ], capture_output=True, text=True, timeout=120, check=False)
    render_ok = pdf_proc.returncode == 0 and pdf_file.is_file() and pdf_file.stat().st_size > 3500
    report = {
        "status": "passed" if render_ok else "docx_passed_pdf_render_failed",
        "source": str(SRC.relative_to(ROOT)),
        "source_git_blob_sha1": source_sha,
        "word_file": str(TARGET.relative_to(ROOT)),
        "word_sha256": hashlib.sha256(TARGET.read_bytes()).hexdigest(),
        "native_table_rows": [len(t) for t in word_tables],
        "native_table_columns": [len(t[0]) for t in word_tables],
        "exact_registered_primary_table": word_tables[1][1:] == EXPECTED_PRIMARY,
        "numbered_references_from_source": references,
        "figure_legend_headings": figures,
        "editable_word_tables": True,
        "layout_correction": layout_changes,
        "double_spacing_verification": paragraph_spacing,
        "verified_core_properties": metadata,
        "pdf_rendered": render_ok,
        "zotero_field_linking": "pending (portable RIS included separately)",
        "figure_image_embedding": "not included, separate journal figures",
        "manual_visual_qa": None,
        "output_scope": "new submission candidate, no source-data changes",
        "new_model_fitting": False,
        "patient_level_data_used": False,
    }
    if not render_ok:
        report["render_diagnostic"] = (pdf_proc.stderr or pdf_proc.stdout)[-450:]
    QA.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"result": report["status"], "docx": report["word_file"],
                      "tables": report["native_table_rows"], "pdf": render_ok,
                      "qa": str(QA.relative_to(ROOT))}))

if __name__ == "__main__":
    main()
