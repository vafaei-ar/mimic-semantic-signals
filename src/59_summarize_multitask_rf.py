from __future__ import annotations
import argparse, json
from pathlib import Path
OUTCOMES=["invasive_ventilation","renal_replacement_therapy","icu_death"]
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--input-root",required=True); ap.add_argument("--output",required=True); a=ap.parse_args()
    root=Path(a.input_root).expanduser().resolve(); res={}
    for o in OUTCOMES:
        r=json.loads((root/o/"report.json").read_text())
        res[o]={"n":r["n"],"cases":r["cases"],"controls":r["controls"],"model_specification":r["model_specification"],"models":r["models"],"matched_set_bootstrap_auroc_differences":r["matched_set_bootstrap_auroc_differences"]}
    out={"analysis":"Cross-outcome random-forest nonlinear structured sensitivity","local_only":True,"contains_patient_identifiers":False,"outcomes":res}
    p=Path(a.output).expanduser().resolve(); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(out,indent=2)+"\n"); print(json.dumps(out,indent=2))
if __name__=="__main__": main()
