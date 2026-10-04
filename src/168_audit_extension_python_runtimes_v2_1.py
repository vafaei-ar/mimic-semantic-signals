from __future__ import annotations

import json
import subprocess
from pathlib import Path

OUT=Path("outputs/integrity/extension_python_runtimes_v2_1.json")
OUT.parent.mkdir(parents=True,exist_ok=True)
home=Path.home()
root=Path(".").resolve()

candidates=[]
for p in [
    root/".venv"/"bin"/"python",
    home/"miniconda3"/"bin"/"python",
    Path("/usr/bin/python3"),
]:
    if p.exists():
        candidates.append(p)

for base in [home/"miniconda3"/"envs", home/".venvs", root]:
    if not base.exists():
        continue
    pats=["*/bin/python"] if base != root else [".venv*/bin/python"]
    for pat in pats:
        for p in sorted(base.glob(pat)):
            if p.exists():
                candidates.append(p)

seen=set()
rows=[]
probe = r'''
import json,sys
out={"executable":sys.executable}
for name in ["torch","transformers","sentence_transformers","sklearn"]:
    try:
        m=__import__(name)
        out[name]={"ok":True,"version":getattr(m,"__version__",None)}
    except Exception as e:
        out[name]={"ok":False,"error":type(e).__name__+": "+str(e)[:300]}
print(json.dumps(out))
'''
for p in candidates:
    key=str(p.resolve())
    if key in seen:
        continue
    seen.add(key)
    proc=subprocess.run([str(p),"-c",probe],text=True,capture_output=True,timeout=60)
    row={"python":str(p),"returncode":proc.returncode,"stderr":proc.stderr.strip()[:1000]}
    if proc.returncode==0:
        try: row["probe"]=json.loads(proc.stdout.strip().splitlines()[-1])
        except Exception: row["stdout"]=proc.stdout.strip()[:1500]
    else:
        row["stdout"]=proc.stdout.strip()[:1500]
    rows.append(row)

report={
 "analysis":"label-free Python runtime inventory for extension embedding",
 "status":"completed",
 "reads_outcome_labels":False,
 "reads_clinical_notes":False,
 "network_used":False,
 "runtimes":rows,
}
OUT.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
print(json.dumps(report,indent=2))
