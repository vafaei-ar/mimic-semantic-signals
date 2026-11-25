"""Render editable supplementary Word/PDF from the frozen candidate Markdown."""
from __future__ import annotations
import hashlib, html, json, re, shutil, subprocess, zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from word_core_properties import set_title_creator

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"manuscript/JAMIA_SUPPLEMENT_CANDIDATE_2026-11-23.md"
OUT=ROOT/"outputs/manuscript/jamia_submission_candidate_20261123"
TARGET=OUT/"JAMIA_Supplement_Candidate_2026-11-23.docx"
QA=OUT/"JAMIA_Supplement_Candidate_2026-11-23_QA.json"
SOURCE_SHA="b85bcd934495a9f6f2660770124fae3fa09cee3c"
W="{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

def git_blob(data):
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def rich(s):
    t=html.escape(s)
    t=re.sub(r"\x60([^\x60]+)\x60",r"<code>\1</code>",t)
    t=re.sub(r"\*\*([^*]+)\*\*",r"<strong>\1</strong>",t)
    t=re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)",r"<em>\1</em>",t)
    t=re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)",r'<a href="\2">\1</a>',t)
    return t

def cells(row):
    return [c.strip() for c in row.strip().strip("|").split("|")]

def make_html(source):
    lines=source.splitlines()
    blocks=[]
    count=0
    i=0
    in_code=False
    while i<len(lines):
        s=lines[i].strip()
        if s.startswith(chr(96)*3):
            in_code=not in_code
            blocks.append("<pre>" if in_code else "</pre>")
            i+=1
            continue
        if in_code:
            blocks.append(html.escape(lines[i]))
            i+=1
            continue
        if not s:
            i+=1
            continue
        if s.startswith("|"):
            rows=[]
            while i<len(lines) and lines[i].strip().startswith("|"):
                rows.append(cells(lines[i]))
                i+=1
            rows=[r for r in rows if not all(re.fullmatch(r":?-{2,}:?",x) for x in r)]
            if not rows or any(len(r)!=len(rows[0]) for r in rows):
                raise ValueError("Bad supplementary table")
            count+=1
            cols=len(rows[0])
            blocks.append('<table class="data cols'+str(cols)+'">')
            for j,row in enumerate(rows):
                tag="th" if j==0 else "td"
                blocks.append("<tr>"+"".join("<"+tag+">"+rich(x)+"</"+tag+">" for x in row)+"</tr>")
            blocks.append("</table>")
            continue
        m=re.match(r"^(#{1,4})\s+(.*)$",s)
        if m:
            n=len(m.group(1))
            blocks.append("<h"+str(n)+">"+rich(m.group(2))+"</h"+str(n)+">")
        elif s.startswith("- "):
            blocks.append('<p class="bullet">• '+rich(s[2:])+"</p>")
        elif s.startswith("> "):
            blocks.append('<p class="quoted">'+rich(s[2:])+"</p>")
        else:
            blocks.append("<p>"+rich(s)+"</p>")
        i+=1
    css="""
    @page { size:11in 8.5in; margin:.68in .72in; }
    body {font-family:Cambria,'Times New Roman',serif;color:#242b33;font-size:9.5pt;line-height:1.35;}
    p {margin:0 0 7pt 0;}
    h1 {font-size:15pt;margin:0 0 13pt 0;}
    h2 {font-size:12pt;margin:15pt 0 7pt 0;page-break-after:avoid;}
    h3 {font-size:10.5pt;margin:11pt 0 6pt 0;page-break-after:avoid;}
    h4 {font-size:9.8pt;margin:10pt 0 5pt 0;page-break-after:avoid;}
    table.data {border-collapse:collapse;width:100%;margin:7pt 0 13pt 0;
                font-size:7.9pt;line-height:1.18;}
    table.data th,table.data td {border:.45pt solid #aeb8bf;padding:3pt 4pt;vertical-align:middle;}
    table.data th {font-weight:bold;background:#e9edf0;}
    table.data td:not(:first-child) {text-align:center;}
    .cols8,.cols9,.cols10,.cols11,.cols12 {font-size:6.7pt;}
    .quoted {margin-left:.15in;color:#45515c;}
    pre,code {font-family:Consolas,monospace;}
    """
    return '<!doctype html><html><head><meta charset="utf-8"><style>'+css+'</style></head><body>'+"\n".join(blocks)+"</body></html>",count

def main():
    data=SOURCE.read_bytes()
    source_sha=git_blob(data)
    if source_sha!=SOURCE_SHA:
        raise ValueError("Frozen supplement source changed")
    content=data.decode("utf-8")
    for marker in ("Table S1.","Table S10.","Table S11.","Table S12.","Supplementary Note 5.","Supplementary Note 6."):
        if marker not in content:
            raise ValueError("Supplement marker absent: "+marker)
    document,num_tables=make_html(content)
    if num_tables<12:
        raise ValueError("Expected >=12 supplementary tables, got "+str(num_tables))
    OUT.mkdir(parents=True,exist_ok=True)
    hp=OUT/"JAMIA_Supplement_Candidate_2026-11-23.html"
    hp.write_text(document,encoding="utf-8")
    office=shutil.which("libreoffice") or shutil.which("soffice")
    if not office:
        raise RuntimeError("LibreOffice missing")
    run=subprocess.run([office,"-env:UserInstallation="+(OUT/".supp_profile").as_uri(),
                       "--headless","--infilter=HTML (StarWriter)","--convert-to",
                       "docx:Office Open XML Text","--outdir",str(OUT),str(hp)],
                       capture_output=True,text=True,timeout=120)
    if run.returncode or not TARGET.exists():
        raise RuntimeError("DOCX conversion failed: "+(run.stderr or run.stdout)[-500:])
    metadata=set_title_creator(TARGET,"Supplementary Material","Alireza Vafaei Sadr")
    with zipfile.ZipFile(TARGET) as z:
        if z.testzip():
            raise ValueError("Corrupted DOCX")
        tree=ET.fromstring(z.read("word/document.xml"))
    tables=tree.findall(".//"+W+"tbl")
    if len(tables)!=num_tables:
        raise ValueError("Table count changed after Word conversion")
    pdf=TARGET.with_suffix(".pdf")
    p=subprocess.run([office,"-env:UserInstallation="+(OUT/".supp_profile_pdf").as_uri(),
       "--headless","--convert-to","pdf","--outdir",str(OUT),str(TARGET)],
       capture_output=True,text=True,timeout=120)
    if p.returncode or not pdf.exists() or pdf.stat().st_size<5000:
        raise RuntimeError("Supplement PDF failed")
    report={"status":"passed","source_sha":source_sha,"table_count":num_tables,
      "native_word_table_count":len(tables),"docx_sha256":hashlib.sha256(TARGET.read_bytes()).hexdigest(),
      "pdf_sha256":hashlib.sha256(pdf.read_bytes()).hexdigest(),"manual_visual_qa":None,
      "source_patient_data_used":False,"new_model_fitting":False,
      "verified_core_properties":metadata}
    QA.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"status":"passed","tables":num_tables,"docx":str(TARGET.relative_to(ROOT))}))
if __name__=="__main__":
    main()
