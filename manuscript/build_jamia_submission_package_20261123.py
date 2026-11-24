"""Build a reviewer-ready JAMIA submission package from frozen manuscript sources.

Runs local document conversion and code-only figure generation. No restricted
clinical records, patient predictions, model training, or outcome-label access.
"""
from __future__ import annotations
import hashlib, html, json, re, shutil, subprocess, sys, zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"outputs/manuscript/jamia_submission_candidate_20261123"
FIG=OUT/"figures"
ZIP=OUT/"JAMIA_Submission_Candidate_2026-11-23.zip"
QA=OUT/"JAMIA_Submission_Candidate_2026-11-23_Package_QA.json"
MAIN_MD=ROOT/"manuscript/JAMIA_SUBMISSION_CANDIDATE_2026-11-23.md"
SUPP_MD=ROOT/"manuscript/JAMIA_SUPPLEMENT_CANDIDATE_2026-11-23.md"
LETTER_MD=ROOT/"manuscript/JAMIA_COVER_LETTER_CANDIDATE_2026-11-23.md"

def run(script):
    cp=subprocess.run([sys.executable,str(ROOT/script)],cwd=ROOT,
                     capture_output=True,text=True,timeout=180)
    if cp.returncode:
        raise RuntimeError(str(script)+" failed: "+(cp.stderr or cp.stdout)[-2000:])
    return cp.stdout

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def rich(s):
    return re.sub(r"\*\*([^*]+)\*\*",r"<strong>\1</strong>",html.escape(s))

def cover_letter():
    text=LETTER_MD.read_text(encoding="utf-8")
    body=[]
    for line in text.splitlines():
        s=line.strip()
        if not s:
            body.append("<p>&nbsp;</p>")
        elif s.startswith("# "):
            body.append("<h1>"+rich(s[2:])+"</h1>")
        else:
            body.append("<p>"+rich(s)+"</p>")
    markup="""<!doctype html><html><head><meta charset="utf-8"><style>
    @page {size:8.5in 11in;margin:.85in .9in;}
    body {font-family:Cambria,'Times New Roman',serif;font-size:10.5pt;line-height:1.24;}
    p {margin:0 0 6pt 0;}
    h1 {font-size:14pt;margin:0 0 12pt 0;}
    </style></head><body>"""+ "\n".join(body)+"</body></html>"
    hp=OUT/"Cover_Letter_2026-11-23.html"
    hp.write_text(markup,encoding="utf-8")
    office=shutil.which("libreoffice") or shutil.which("soffice")
    if not office:
        raise RuntimeError("LibreOffice not installed")
    commands=[
      [office,"-env:UserInstallation="+(OUT/".lo_cover").as_uri(),"--headless",
       "--infilter=HTML (StarWriter)","--convert-to","docx:Office Open XML Text",
       "--outdir",str(OUT),str(hp)]
    ]
    for cmd in commands:
        cp=subprocess.run(cmd,capture_output=True,text=True,timeout=120)
        if cp.returncode:
            raise RuntimeError("Letter DOCX failed: "+cp.stderr[-450:])
    docx=hp.with_suffix(".docx")
    if not docx.exists():
        raise RuntimeError("Cover letter DOCX missing")
    cp=subprocess.run([office,"-env:UserInstallation="+(OUT/".lo_cover_pdf").as_uri(),
       "--headless","--convert-to","pdf","--outdir",str(OUT),str(docx)],
       capture_output=True,text=True,timeout=120)
    pdf=hp.with_suffix(".pdf")
    if cp.returncode or not pdf.exists():
        raise RuntimeError("Cover letter PDF missing")
    return docx,pdf

def refs_ris():
    """Export citation metadata checked against PubMed or source model cards."""
    source=MAIN_MD.read_text(encoding="utf-8")
    lines=[x.strip() for x in source.split("## References")[1].split("## Figure legends")[0].splitlines()
           if re.match(r"^\d+\.\s",x.strip())]
    registry=json.loads((ROOT/"manuscript/JAMIA_REFERENCES_PUBMED_VERIFIED_2026-11-23.json").read_text(encoding="utf-8"))
    items=registry["items"]
    if len(lines)!=18 or len(items)!=18:
        raise ValueError("Expected exactly 18 manuscript references and registry items")
    output=[]
    for i,(line,item) in enumerate(zip(lines,items),1):
        if int(item["number"])!=i:
            raise ValueError("PubMed metadata order does not match manuscript")
        doi=item.get("doi")
        if doi and doi.lower() not in line.lower():
            raise ValueError("Manuscript DOI conflicts with registry at citation "+str(i))
        if item.get("type")=="ELEC" and item.get("url") not in line:
            raise ValueError("Model card URL mismatch for citation "+str(i))
        p=["TY  - "+item["type"],
           "ID  - JEV-REF-"+str(i),
           "TI  - "+item["title"]]
        for author in item["authors"]:
            p.append("AU  - "+author)
        if item.get("journal"):
            p.extend(["JO  - "+item["journal"],"JF  - "+item["journal"]])
        if item.get("publisher"):
            p.append("PB  - "+item["publisher"])
        if item.get("year"):
            p.append("PY  - "+str(item["year"]))
        for field,key in (("VL","volume"),("IS","issue"),("SP","pages"),("DO","doi")):
            if item.get(key):
                p.append(field+"  - "+str(item[key]))
        if item.get("pmid"):
            p.append("AN  - PMID:"+item["pmid"])
        url=item.get("source_url") or item.get("url")
        if url:
            p.append("UR  - "+url)
        if item.get("accessed"):
            p.append("Y2  - "+item["accessed"])
        p.extend(["N1  - Original manuscript reference: "+line,"ER  - ",""])
        output.append("\n".join(p))
    dest=OUT/"JAMIA_References_Zotero_Import_2026-11-23.ris"
    dest.write_text("\n".join(output)+"\n",encoding="utf-8")
    saved=dest.read_text(encoding="utf-8")
    if saved.count("\nER  - ")!=18 or saved.count("\nAU  - ")<18 or saved.count("\nJO  - ")!=15:
        raise ValueError("Incomplete RIS authors/journals after write")
    return dest,len(items)


def pdf_geometry(pdf):
    exe=shutil.which("pdftotext")
    if not exe:
        return {"available":False}
    r=subprocess.run([exe,"-bbox","-enc","UTF-8",str(pdf),"-"],
      capture_output=True,text=True,timeout=90)
    if r.returncode:
        return {"available":False,"error":r.stderr[-300:]}
    root=ET.fromstring(r.stdout)
    pages=[el for el in root.iter() if el.tag.rsplit("}",1)[-1]=="page"]
    outside=0
    results=[]
    for i,page in enumerate(pages,1):
        w,h=float(page.get("width")),float(page.get("height"))
        words=[x for x in page.iter() if x.tag.rsplit("}",1)[-1]=="word"]
        for x in words:
            x0,y0,x1,y1=[float(x.get(k)) for k in ("xMin","yMin","xMax","yMax")]
            if x0 < -1.5 or y0 < -1.5 or x1 > w+1.5 or y1 > h+1.5:
                outside+=1
        string=" ".join((x.text or "") for x in words)
        results.append({"page":i,"orientation":"landscape" if w>h else "portrait",
                        "words":len(words),
                        "table3":("Table 3." in string),
                        "s11":("Table S11." in string)})
    return {"available":True,"pages":results,"off_page_words":outside}

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    FIG.mkdir(parents=True,exist_ok=True)
    main_log=run(Path("manuscript/build_jamia_submission_candidate.py"))
    supplement_log=run(Path("manuscript/build_jamia_supplement_candidate.py"))
    letter,pdf_letter=cover_letter()
    figure=subprocess.run([sys.executable,str(ROOT/"manuscript/make_jamia_main_figures.py"),
      "--root",str(ROOT),"--out",str(FIG.relative_to(ROOT))],
      capture_output=True,text=True,cwd=ROOT,timeout=120)
    if figure.returncode:
        raise RuntimeError("Frozen figure render failed "+figure.stderr[-800:])
    ris,refcount=refs_ris()
    manuscript=OUT/"JAMIA_Submission_Candidate_2026-11-23.docx"
    manuscript_pdf=manuscript.with_suffix(".pdf")
    supplement=OUT/"JAMIA_Supplement_Candidate_2026-11-23.docx"
    supplement_pdf=supplement.with_suffix(".pdf")
    for x in (manuscript,manuscript_pdf,supplement,supplement_pdf,letter,pdf_letter):
        if not x.exists() or x.stat().st_size<2000:
            raise ValueError("Expected output missing/empty: "+str(x))
    geom_main=pdf_geometry(manuscript_pdf)
    geom_supp=pdf_geometry(supplement_pdf)
    checks={
       "source_main_exists":MAIN_MD.exists(),
       "source_supplement_exists":SUPP_MD.exists(),
       "all_reference_records":refcount==18,
       "verified_reference_metadata_in_ris":ris.exists() and ris.read_text(encoding="utf-8").count("\nJO  - ")==15,
       "main_pdf_has_landscape_table3":geom_main["available"] and any(
            p["orientation"]=="landscape" and p["table3"] for p in geom_main["pages"]),
       "supplement_pdf_readable":geom_supp["available"] and len(geom_supp["pages"])>4,
       "main_no_off_page_words":geom_main.get("off_page_words")==0,
       "supplement_no_off_page_words":geom_supp.get("off_page_words")==0,
       "all_six_figure_assets":all((FIG/(name+"."+ext)).exists()
           for name in ("JAMIA_Figure_1_Study_design","JAMIA_Figure_2_Primary_delta_AUROC")
           for ext in ("pdf","svg","png"))
    }
    if not all(checks.values()):
        raise ValueError("QA checks failed: "+json.dumps(checks))
    readme=OUT/"READ_FIRST_Submission_Review.txt"
    readme.write_text(
      "JAMIA RESEARCH AND APPLICATIONS | 2026-11-23 AUTHOR REVIEW PACKAGE\n"
      "This is a submission-candidate package, not an approved journal submission.\n\n"
      "MAIN: editable manuscript Word + PDF proof, three native tables, 18 references.\n"
      "SUPPLEMENT: editable Word + PDF with registered S1-S10 and exploratory S11-S14.\n"
      "FIGURES: two registered figures in PDF/SVG/PNG, generated from frozen aggregate values.\n"
      "COVER: separate editable Word/PDF letter.\n"
      "REFERENCES: PubMed-verified RIS with 15 article and 3 model-card records. Zotero library import still needs manual checking; Word citations are not linked fields.\n\n"
      "AUTHOR REQUIREMENTS BEFORE SUBMISSION:\n"
      "1. Verify conflicting interests and add accurate declaration; confirm funding.\n"
      "2. Confirm any applicable local institutional ethics determination.\n"
      "3. Final human visual inspection of all PDF pages and figure size/readability.\n"
      "4. Verify 18 reference records in Zotero and link manuscript Word citations.\n"
      "5. Obtain statistical interpretation sign-off on T1.5 ventilation A bootstrap shift.\n"
      "6. Review updated 2026 competitor paper and full text; approve final claims.\n"
      "7. Verify title page/affiliation/contact, final word count and journal portal forms.\n"
      "8. Keep main preregistered results separate from exploratory extensions.\n\n"
      "No protected patient-level MIMIC content is included.\n",encoding="utf-8")
    files=[
      manuscript,manuscript_pdf,supplement,supplement_pdf,letter,pdf_letter,ris,readme,
      MAIN_MD,SUPP_MD,LETTER_MD,
      OUT/"JAMIA_Submission_Candidate_2026-11-23_QA.json",
      OUT/"JAMIA_Supplement_Candidate_2026-11-23_QA.json"
    ]
    files.extend(sorted(FIG.glob("JAMIA_Figure_*")))
    manifest={
      "scope":"JAMIA author-review submission candidate",
      "original_preregistration_unchanged":True,
      "new_patient_level_analysis":False,
      "refcount":refcount,
      "files":{},
      "checks":checks,
      "manuscript_pdf":geom_main,
      "supplement_pdf":geom_supp,
      "visual_review": "pending",
      "zotero_word_field_linkage": "pending",
      "author_disclosures": "pending"
    }
    for file in files:
        if not file.exists():
            raise ValueError("Missing packaged file "+str(file))
        key=("sources/"+file.name) if file.parent==ROOT/"manuscript" else (
          "figures/"+file.name if file.parent==FIG else file.name)
        manifest["files"][key]={"sha256":sha(file),"bytes":file.stat().st_size}
    QA.write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    files.append(QA)
    with zipfile.ZipFile(ZIP,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=7) as z:
        for file in files:
            name=("sources/"+file.name) if file.parent==ROOT/"manuscript" else (
               "figures/"+file.name if file.parent==FIG else file.name)
            z.write(file,arcname=name)
    print(json.dumps({"status":"passed","zip":str(ZIP.relative_to(ROOT)),
      "package_sha256":sha(ZIP),"files":len(files),"checks":checks,
      "pages":{"main":len(geom_main["pages"]),"supplement":len(geom_supp["pages"])}}))
if __name__=="__main__":
    main()
