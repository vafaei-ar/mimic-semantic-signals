from __future__ import annotations

import json
import os
from pathlib import Path


TARGET_JOB_IDS = {"C8M4R7K2", "F7M2R9K4"}


def env_job_id(pid: int) -> str | None:
    try:
        raw = (Path("/proc") / str(pid) / "environ").read_bytes()
    except Exception:
        return None
    for item in raw.split(b"\0"):
        if item.startswith(b"RUNRELAY_JOB_ID="):
            return item.split(b"=", 1)[1].decode("utf-8", errors="replace")
    return None


def comm(pid: int) -> str | None:
    try:
        return (Path("/proc") / str(pid) / "comm").read_text(
            encoding="utf-8", errors="replace"
        ).strip()
    except Exception:
        return None


def ppid(pid: int) -> int | None:
    try:
        text = (Path("/proc") / str(pid) / "status").read_text(
            encoding="utf-8", errors="replace"
        )
    except Exception:
        return None
    for line in text.splitlines():
        if line.startswith("PPid:"):
            try:
                return int(line.split(":", 1)[1].strip())
            except ValueError:
                return None
    return None


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    rows = []
    for path in Path("/proc").iterdir():
        if not path.name.isdigit():
            continue
        pid = int(path.name)
        job_id = env_job_id(pid)
        if job_id not in TARGET_JOB_IDS:
            continue
        try:
            pgid = os.getpgid(pid)
        except Exception:
            pgid = None
        try:
            sid = os.getsid(pid)
        except Exception:
            sid = None
        rows.append(
            {
                "job_id": job_id,
                "pid": pid,
                "ppid": ppid(pid),
                "pgid": pgid,
                "sid": sid,
                "comm": comm(pid),
            }
        )

    rows.sort(key=lambda x: (x["job_id"], x["pid"]))
    report = {
        "analysis": "RunRelay orphan audit for terminal T1.1 jobs",
        "target_job_ids": sorted(TARGET_JOB_IDS),
        "matching_processes": rows,
        "matching_counts": {
            job: sum(1 for row in rows if row["job_id"] == job)
            for job in sorted(TARGET_JOB_IDS)
        },
        "guardrails": [
            "Only RUNRELAY_JOB_ID is extracted from process environments.",
            "Only the two named terminal jobs are reported.",
            "No process command lines, working directories, unrelated environment values, clinical data, or research rows are inspected.",
            "This task is read-only and does not signal or terminate any process.",
        ],
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
