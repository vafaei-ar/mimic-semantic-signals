from __future__ import annotations

import json
import math
import os
import platform
import re
import resource
import statistics
import subprocess
import sys
import time
from pathlib import Path


def read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except Exception:
        return None


def read_meminfo() -> dict[str, int]:
    out = {}
    path = Path("/proc/meminfo")
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        parts = value.strip().split()
        if not parts:
            continue
        try:
            number = int(parts[0])
        except ValueError:
            continue
        if len(parts) > 1 and parts[1].lower() == "kb":
            number *= 1024
        out[key] = number
    return out


def read_pressure() -> dict[str, str]:
    out = {}
    for name in ("cpu", "memory", "io"):
        text = read_text(Path("/proc/pressure") / name)
        if text is not None:
            out[name] = text
    return out


def read_cpu_scaling() -> dict:
    rows = []
    for cpu_dir in sorted(Path("/sys/devices/system/cpu").glob("cpu[0-9]*")):
        cpufreq = cpu_dir / "cpufreq"
        if not cpufreq.is_dir():
            continue
        row = {"cpu": cpu_dir.name}
        for name in (
            "scaling_governor",
            "scaling_cur_freq",
            "cpuinfo_cur_freq",
            "scaling_min_freq",
            "scaling_max_freq",
            "cpuinfo_min_freq",
            "cpuinfo_max_freq",
        ):
            value = read_text(cpufreq / name)
            if value is not None:
                if name.endswith("_freq"):
                    try:
                        row[name + "_khz"] = int(value)
                    except ValueError:
                        row[name] = value
                else:
                    row[name] = value
        rows.append(row)
    return {"cpus": rows}


def read_thermal() -> list[dict]:
    rows = []
    for zone in sorted(Path("/sys/class/thermal").glob("thermal_zone*")):
        typ = read_text(zone / "type")
        temp = read_text(zone / "temp")
        if temp is None:
            continue
        try:
            value = float(temp)
            if abs(value) > 1000:
                value /= 1000.0
        except ValueError:
            continue
        rows.append({"zone": zone.name, "type": typ, "temp_c": value})
    return rows


def read_power() -> list[dict]:
    rows = []
    for item in sorted(Path("/sys/class/power_supply").glob("*")):
        row = {"name": item.name}
        for key in ("type", "online", "status", "capacity"):
            value = read_text(item / key)
            if value is not None:
                row[key] = value
        if len(row) > 1:
            rows.append(row)
    return rows


def run_capture(cmd: list[str], timeout: int = 15) -> dict:
    try:
        p = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return {
            "returncode": int(p.returncode),
            "stdout": (p.stdout or "").strip(),
            "stderr": (p.stderr or "").strip(),
        }
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}


def top_processes() -> list[dict]:
    r = run_capture(
        ["ps", "-eo", "pid=,comm=,pcpu=,pmem=,rss=,ni=", "--sort=-pcpu"],
        timeout=10,
    )
    text = r.get("stdout") or ""
    rows = []
    for raw in text.splitlines()[:25]:
        parts = raw.split(None, 5)
        if len(parts) != 6:
            continue
        pid, comm, pcpu, pmem, rss, nice = parts
        try:
            rows.append(
                {
                    "pid": int(pid),
                    "comm": comm,
                    "cpu_percent": float(pcpu),
                    "mem_percent": float(pmem),
                    "rss_bytes": int(rss) * 1024,
                    "nice": int(nice),
                }
            )
        except ValueError:
            continue
    return rows


def suspend_events() -> dict:
    r = run_capture(
        [
            "journalctl",
            "-b",
            "-k",
            "--since",
            "36 hours ago",
            "--no-pager",
            "-o",
            "short-iso",
        ],
        timeout=20,
    )
    if "stdout" not in r:
        return r
    rx = re.compile(
        r"(suspend|resume|sleep|PM: suspend|PM: resume|Freezing user space|Restarting tasks)",
        re.IGNORECASE,
    )
    lines = [line for line in r["stdout"].splitlines() if rx.search(line)]
    return {
        "returncode": r.get("returncode"),
        "matching_lines": lines[-100:],
        "stderr": r.get("stderr"),
    }


def benchmark() -> dict:
    out = {}
    try:
        import numpy as np

        out["numpy_version"] = np.__version__
        rng = np.random.default_rng(20261007)

        a = rng.normal(size=(1400, 1400)).astype(np.float64)
        b = rng.normal(size=(1400, 1400)).astype(np.float64)
        matmul = []
        checksum = None
        for _ in range(3):
            t0 = time.perf_counter()
            c = a @ b
            matmul.append(time.perf_counter() - t0)
            checksum = float(c[0, 0])
        out["numpy_matmul_1400x1400_seconds"] = matmul
        out["numpy_matmul_median_seconds"] = statistics.median(matmul)
        out["numpy_matmul_checksum"] = checksum
    except Exception as exc:
        out["numpy_error"] = f"{type(exc).__name__}: {exc}"

    try:
        from threadpoolctl import threadpool_info

        out["threadpools"] = threadpool_info()
    except Exception as exc:
        out["threadpool_error"] = f"{type(exc).__name__}: {exc}"

    try:
        import numpy as np
        import sklearn
        from sklearn.ensemble import HistGradientBoostingClassifier
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression

        out["sklearn_version"] = sklearn.__version__
        rng = np.random.default_rng(20261007)

        x = rng.normal(size=(18000, 48)).astype(np.float64)
        logit = 0.7 * x[:, 0] - 0.4 * x[:, 1] + 0.25 * x[:, 2]
        y = (logit + rng.normal(size=len(x)) > 0).astype(int)
        hgb_times = []
        for _ in range(2):
            model = HistGradientBoostingClassifier(
                learning_rate=0.05,
                max_iter=100,
                max_leaf_nodes=31,
                min_samples_leaf=20,
                l2_regularization=0.0,
                random_state=20260924,
            )
            t0 = time.perf_counter()
            model.fit(x, y)
            hgb_times.append(time.perf_counter() - t0)
        out["synthetic_hgb_fit_seconds"] = hgb_times
        out["synthetic_hgb_median_seconds"] = statistics.median(hgb_times)

        vocab = [f"tok{i}" for i in range(400)]
        docs = []
        labels = []
        for i in range(6000):
            toks = rng.choice(vocab, size=90, replace=True).tolist()
            label = int(i % 5 == 0)
            if label:
                toks.extend(["riskword", "worsening", "support"])
            docs.append(" ".join(toks))
            labels.append(label)
        vec = TfidfVectorizer(
            lowercase=True,
            strip_accents="unicode",
            ngram_range=(1, 2),
            min_df=5,
            max_df=0.98,
            max_features=10000,
            sublinear_tf=True,
            dtype=np.float64,
        )
        t0 = time.perf_counter()
        xx = vec.fit_transform(docs)
        vectorize_seconds = time.perf_counter() - t0
        model = LogisticRegression(
            penalty="l2",
            C=1.0,
            solver="liblinear",
            max_iter=5000,
            tol=0.0001,
            fit_intercept=True,
            class_weight=None,
        )
        t0 = time.perf_counter()
        model.fit(xx, np.asarray(labels, dtype=int))
        logistic_seconds = time.perf_counter() - t0
        out["synthetic_tfidf_shape"] = [int(xx.shape[0]), int(xx.shape[1])]
        out["synthetic_tfidf_vectorize_seconds"] = vectorize_seconds
        out["synthetic_logistic_fit_seconds"] = logistic_seconds
    except Exception as exc:
        out["sklearn_error"] = f"{type(exc).__name__}: {exc}"

    t0 = time.perf_counter()
    acc = 0
    for i in range(8_000_000):
        acc = (acc + (i * i) % 1000003) % 1000000007
    out["pure_python_8m_loop_seconds"] = time.perf_counter() - t0
    out["pure_python_checksum"] = int(acc)
    return out


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    mem = read_meminfo()
    load1, load5, load15 = os.getloadavg()
    report = {
        "analysis": "extension runtime workstation diagnostic",
        "timestamp_epoch": time.time(),
        "hostname": platform.node(),
        "platform": platform.platform(),
        "python": sys.version,
        "cpu_count_logical": os.cpu_count(),
        "load_average": {"1m": load1, "5m": load5, "15m": load15},
        "memory": {
            "MemTotal": mem.get("MemTotal"),
            "MemAvailable": mem.get("MemAvailable"),
            "SwapTotal": mem.get("SwapTotal"),
            "SwapFree": mem.get("SwapFree"),
        },
        "pressure": read_pressure(),
        "cpu_scaling": read_cpu_scaling(),
        "thermal": read_thermal(),
        "power_supply": read_power(),
        "top_processes_by_cpu": top_processes(),
        "kernel_suspend_resume_events_last_36h": suspend_events(),
        "environment_thread_vars": {
            name: os.environ.get(name)
            for name in (
                "OMP_NUM_THREADS",
                "OPENBLAS_NUM_THREADS",
                "MKL_NUM_THREADS",
                "NUMEXPR_NUM_THREADS",
                "VECLIB_MAXIMUM_THREADS",
                "BLIS_NUM_THREADS",
            )
        },
        "resource_limits": {
            "as": list(resource.getrlimit(resource.RLIMIT_AS)),
            "data": list(resource.getrlimit(resource.RLIMIT_DATA)),
            "nofile": list(resource.getrlimit(resource.RLIMIT_NOFILE)),
            "nproc": list(resource.getrlimit(resource.RLIMIT_NPROC)),
        },
        "synthetic_benchmark": benchmark(),
        "guardrails": [
            "No MIMIC data, clinical notes, outcome labels, or row-level research data are read.",
            "Process reporting includes pid, executable name, CPU, memory, RSS, and nice value only; no command lines or environment values are exposed.",
            "The artifact is machine/runtime telemetry only.",
        ],
    }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "completed", "output": str(out)}, indent=2))


if __name__ == "__main__":
    main()
