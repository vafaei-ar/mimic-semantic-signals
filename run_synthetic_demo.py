from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-root", default="data/synthetic_mimic")
    ap.add_argument("--n-admissions", type=int, default=500)
    ap.add_argument("--seed", type=int, default=20260919)
    args = ap.parse_args()

    repo = Path(__file__).resolve().parent
    root = Path(args.output_root).expanduser().resolve()

    # Fail fast on syntax errors before spending time generating the sandbox.
    subprocess.run(
        [
            sys.executable,
            "-m",
            "py_compile",
            str(repo / "synthetic" / "generate_mimiciii_semantic_sandbox.py"),
            str(repo / "src" / "semantic_schema.py"),
            str(repo / "src" / "10_build_semantic_windows.py"),
        ],
        check=True,
    )

    # Runtime smoke test on a tiny temporary sandbox before generating the full cohort.
    with tempfile.TemporaryDirectory(prefix="mimic_semantic_smoke_") as tmp:
        smoke_root = Path(tmp) / "synthetic_mimic"
        subprocess.run(
            [
                sys.executable,
                str(repo / "synthetic" / "generate_mimiciii_semantic_sandbox.py"),
                "--output",
                str(smoke_root),
                "--n-admissions",
                "3",
                "--seed",
                str(args.seed),
            ],
            check=True,
        )
        subprocess.run(
            [
                sys.executable,
                str(repo / "src" / "10_build_semantic_windows.py"),
                "--synthetic-root",
                str(smoke_root),
                "--output",
                str(smoke_root / "semantic_eval_cases_24h.jsonl"),
                "--window-hours",
                "24",
            ],
            check=True,
        )

    subprocess.run(
        [
            sys.executable,
            str(repo / "synthetic" / "generate_mimiciii_semantic_sandbox.py"),
            "--output",
            str(root),
            "--n-admissions",
            str(args.n_admissions),
            "--seed",
            str(args.seed),
        ],
        check=True,
    )

    cases = root / "semantic_eval_cases_24h.jsonl"
    subprocess.run(
        [
            sys.executable,
            str(repo / "src" / "10_build_semantic_windows.py"),
            "--synthetic-root",
            str(root),
            "--output",
            str(cases),
            "--window-hours",
            "24",
        ],
        check=True,
    )

    print(f"\nSynthetic MIMIC root: {root}")
    print(f"Provider-neutral semantic cases: {cases}")


if __name__ == "__main__":
    main()
