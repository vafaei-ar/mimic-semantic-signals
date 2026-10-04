from __future__ import annotations

import json
import subprocess
from pathlib import Path

root = Path(".").resolve()

def run(*args):
    p = subprocess.run(args, cwd=root, text=True, capture_output=True)
    return {"returncode": p.returncode, "stdout": p.stdout.strip(), "stderr": p.stderr.strip()}

status = run("git", "status", "--porcelain", "--untracked-files=all")
head = run("git", "rev-parse", "HEAD")
branch = run("git", "branch", "--show-current")
diffcheck = run("git", "diff", "--check")

checks = {}
checks["tracked_worktree_clean"] = status["returncode"] == 0 and status["stdout"] == ""
checks["git_diff_check_clean"] = diffcheck["returncode"] == 0 and diffcheck["stdout"] == ""

required = [
    "manuscript/make_paper1_figures.py",
    "manuscript/figure1_nature_style_data.json",
    "manuscript/figure2_nature_style_data.json",
    "manuscript/JAMIA_WORKING_DRAFT_2026-10-03.md",
    "manuscript/SUPPLEMENT_2026-10-03.md",
    "manuscript/JAMIA_COVER_LETTER_2026-10-03.md",
    "manuscript/JAMIA_SUBMISSION_CHECKLIST_2026-10-03.md",
    "docs/results/PAPER1_PROVENANCE_INDEX_2026-10-03.md",
]
checks["required_submission_sources_present"] = all((root / p).is_file() for p in required)

manifest = (root / ".runrelay/project.yaml").read_text(encoding="utf-8")
checks["final_figure_task_present"] = "build_paper1_final_matplotlib_figures:" in manifest
checks["temporary_figure_tasks_absent"] = (
    "check_paper1_figure_python:" not in manifest
    and "qa_paper1_final_matplotlib_figures:" not in manifest
)
checks["temporary_figure_helpers_absent"] = (
    not (root / "scripts/check_paper1_figure_python.py").exists()
    and not (root / "scripts/make_paper1_figure_previews.py").exists()
)

key_docs = {
    "README.md": (root / "README.md").read_text(encoding="utf-8"),
    "docs/01_READ_FIRST.md": (root / "docs/01_READ_FIRST.md").read_text(encoding="utf-8"),
    "docs/02_CURRENT_SCIENTIFIC_STATUS.md": (root / "docs/02_CURRENT_SCIENTIFIC_STATUS.md").read_text(encoding="utf-8"),
    "docs/12_MINIMAL_SUBMISSION_PLAN_2026-10-03.md": (root / "docs/12_MINIMAL_SUBMISSION_PLAN_2026-10-03.md").read_text(encoding="utf-8"),
    "manuscript/JAMIA_WORKING_DRAFT_2026-10-03.md": (root / "manuscript/JAMIA_WORKING_DRAFT_2026-10-03.md").read_text(encoding="utf-8"),
    "docs/results/PAPER1_PROVENANCE_INDEX_2026-10-03.md": (root / "docs/results/PAPER1_PROVENANCE_INDEX_2026-10-03.md").read_text(encoding="utf-8"),
}

stale = [
    "The remaining registered critical path is H8",
    "Do not lock the manuscript claim until H8 human construct validation is complete",
    "docs/12_PUBLICATION_SPRINT_AND_MISSINGNESS_RESILIENCE_PLAN_2026-10-03.md",
]
checks["no_stale_current_plan_phrases"] = not any(
    phrase in key_docs["README.md"] + key_docs["docs/01_READ_FIRST.md"] + key_docs["docs/02_CURRENT_SCIENTIFIC_STATUS.md"]
    for phrase in stale
)
checks["final_figure_generator_referenced"] = "manuscript/make_paper1_figures.py" in (
    key_docs["README.md"]
    + key_docs["docs/02_CURRENT_SCIENTIFIC_STATUS.md"]
    + key_docs["docs/results/PAPER1_PROVENANCE_INDEX_2026-10-03.md"]
)
checks["figure1_legend_matches_rendering"] = "outcome-specific pale band" in key_docs["manuscript/JAMIA_WORKING_DRAFT_2026-10-03.md"]
checks["research_phase_closed"] = (
    "research phase is closed" in key_docs["README.md"].lower()
    and "research phase is closed" in key_docs["docs/02_CURRENT_SCIENTIFIC_STATUS.md"].lower()
)

report = {
    "head": head["stdout"],
    "branch": branch["stdout"],
    "git_status_porcelain": status["stdout"],
    "checks": checks,
    "pass": all(checks.values()),
}
out = root / "outputs/integrity/paper1_submission_repo_audit.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, indent=2))
raise SystemExit(0 if report["pass"] else 1)
