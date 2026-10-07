from __future__ import annotations

import json
import os
import re
import subprocess
import time
from pathlib import Path


MAX_LOAD_1M = 28.0
MAX_LOAD_5M = 28.0
MAX_CPU_PSI_AVG60 = 10.0
MAX_PACKAGE_TEMP_C = 90.0


def read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except Exception:
        return None


def cpu_psi_avg60() -> float | None:
    text = read_text(Path("/proc/pressure/cpu"))
    if not text:
        return None
    m = re.search(r"some\s+avg10=[0-9.]+\s+avg60=([0-9.]+)", text)
    return float(m.group(1)) if m else None


def package_temp_c() -> float | None:
    vals = []
    for zone in Path("/sys/class/thermal").glob("thermal_zone*"):
        typ = read_text(zone / "type") or ""
        if "pkg" not in typ.lower() and "cpu" not in typ.lower():
            continue
        raw = read_text(zone / "temp")
        if raw is None:
            continue
        try:
            val = float(raw)
        except ValueError:
            continue
        if abs(val) > 1000:
            val /= 1000.0
        vals.append(val)
    return max(vals) if vals else None


def top_processes() -> list[dict]:
    p = subprocess.run(
        ["ps", "-eo", "pid=,ppid=,comm=,pcpu=,pmem=,rss=,etimes=,ni=", "--sort=-pcpu"],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    rows = []
    for raw in (p.stdout or "").splitlines()[:20]:
        parts = raw.split(None, 7)
        if len(parts) != 8:
            continue
        pid, ppid, comm, pcpu, pmem, rss, etimes, nice = parts
        try:
            rows.append(
                {
                    "pid": int(pid),
                    "ppid": int(ppid),
                    "comm": comm,
                    "cpu_percent": float(pcpu),
                    "mem_percent": float(pmem),
                    "rss_bytes": int(rss) * 1024,
                    "elapsed_seconds": int(etimes),
                    "nice": int(nice),
                }
            )
        except ValueError:
            continue
    return rows


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    load1, load5, load15 = os.getloadavg()
    psi = cpu_psi_avg60()
    temp = package_temp_c()
    checks = {
        "load_1m": {
            "value": load1,
            "maximum": MAX_LOAD_1M,
            "pass": load1 <= MAX_LOAD_1M,
        },
        "load_5m": {
            "value": load5,
            "maximum": MAX_LOAD_5M,
            "pass": load5 <= MAX_LOAD_5M,
        },
        "cpu_psi_avg60": {
            "value": psi,
            "maximum": MAX_CPU_PSI_AVG60,
            "pass": psi is None or psi <= MAX_CPU_PSI_AVG60,
        },
        "package_temp_c": {
            "value": temp,
            "maximum": MAX_PACKAGE_TEMP_C,
            "pass": temp is None or temp <= MAX_PACKAGE_TEMP_C,
        },
    }
    ready = all(bool(item["pass"]) for item in checks.values())
    report = {
        "analysis": "extension runtime readiness gate",
        "timestamp_epoch": time.time(),
        "cpu_count_logical": os.cpu_count(),
        "load_average": {"1m": load1, "5m": load5, "15m": load15},
        "checks": checks,
        "ready_for_long_t1_compute": ready,
        "top_processes_by_cpu": top_processes(),
        "guardrails": [
            "Operational readiness only; this does not alter the scientific estimand, model, bootstrap target, or frozen analysis plan.",
            "No MIMIC data, clinical notes, outcome labels, or row-level research data are read.",
            "No unrelated process command lines, working directories, or environment contents are inspected.",
            "A long Tier-1 retry should not be launched unless this gate passes.",
        ],
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ready": ready, "output": str(out)}, indent=2))


if __name__ == "__main__":
    main()
