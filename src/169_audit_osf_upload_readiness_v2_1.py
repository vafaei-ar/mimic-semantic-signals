from __future__ import annotations

import importlib.util
import json
import os
import shutil
from pathlib import Path

OUT=Path("outputs/integrity/extension_osf_upload_readiness_v2_1.json")
OUT.parent.mkdir(parents=True,exist_ok=True)
home=Path.home()

candidate_paths=[
    home/".osfclient",
    home/".osfcli.config",
    home/".config"/"osfclient",
    home/".config"/"osf",
    home/".config"/"osfcli",
]
present=[str(p) for p in candidate_paths if p.exists()]

report={
    "analysis":"OSF upload readiness audit",
    "status":"completed",
    "reads_outcome_labels":False,
    "reads_clinical_notes":False,
    "credential_contents_read":False,
    "commands":{
        "osf":shutil.which("osf"),
        "osfclient":shutil.which("osfclient"),
        "curl":shutil.which("curl"),
    },
    "python_modules":{
        "osfclient":bool(importlib.util.find_spec("osfclient")),
        "requests":bool(importlib.util.find_spec("requests")),
    },
    "possible_config_paths_present":present,
    "osf_token_env_name_present":bool(os.environ.get("OSF_TOKEN")),
    "note":"No credential values or config contents were read or emitted.",
}
OUT.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
print(json.dumps(report,indent=2))
