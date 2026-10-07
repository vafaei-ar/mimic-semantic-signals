from __future__ import annotations

import json
import os
import signal
import time
from pathlib import Path


TARGET_JOB_ID = "C8M4R7K2"


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


def matching_processes() -> list[dict]:
    rows = []
    for path in Path("/proc").iterdir():
        if not path.name.isdigit():
            continue
        pid = int(path.name)
        if env_job_id(pid) != TARGET_JOB_ID:
            continue
        try:
            pgid = os.getpgid(pid)
            sid = os.getsid(pid)
        except ProcessLookupError:
            continue
        rows.append(
            {
                "pid": pid,
                "pgid": pgid,
                "sid": sid,
                "comm": comm(pid),
            }
        )
    rows.sort(key=lambda x: x["pid"])
    return rows


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    before = matching_processes()
    if not before:
        result = {
            "status": "no_matching_orphan",
            "target_job_id": TARGET_JOB_ID,
            "before": [],
            "after": [],
            "signals_sent": [],
        }
    else:
        pgids = sorted({int(row["pgid"]) for row in before})
        sids = sorted({int(row["sid"]) for row in before})
        if len(pgids) != 1 or len(sids) != 1 or pgids[0] != sids[0]:
            raise RuntimeError(
                f"Refusing cleanup: target job spans unexpected groups/sessions "
                f"pgids={pgids} sids={sids}"
            )
        pgid = pgids[0]
        if pgid == os.getpgrp() or pgid == os.getsid(0):
            raise RuntimeError("Refusing cleanup: target group matches cleanup process")

        signals = []
        os.killpg(pgid, signal.SIGTERM)
        signals.append("SIGTERM")
        deadline = time.time() + 15.0
        while time.time() < deadline:
            if not matching_processes():
                break
            time.sleep(0.5)

        after_term = matching_processes()
        if after_term:
            os.killpg(pgid, signal.SIGKILL)
            signals.append("SIGKILL")
            deadline = time.time() + 5.0
            while time.time() < deadline:
                if not matching_processes():
                    break
                time.sleep(0.25)

        after = matching_processes()
        if after:
            raise RuntimeError(
                f"Target RunRelay orphan still present after cleanup: {after}"
            )

        result = {
            "status": "terminated",
            "target_job_id": TARGET_JOB_ID,
            "process_group": pgid,
            "session_id": sids[0],
            "before": before,
            "after": after,
            "signals_sent": signals,
        }

    result["guardrails"] = [
        "Only processes whose environment contains RUNRELAY_JOB_ID=C8M4R7K2 are eligible.",
        "Cleanup aborts unless all matching processes belong to one process group and session.",
        "The cleanup process refuses to signal its own group/session.",
        "No unrelated process command lines, working directories, environments, clinical data, or research rows are inspected.",
    ]

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
