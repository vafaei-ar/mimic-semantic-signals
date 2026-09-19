from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-root", default="data/synthetic_mimic")
    ap.add_argument("--n-admissions", type=int, default=500)
    ap.add_argument("--seed", type=int, default=20260919)
    args = ap.parse_args()

    repo = Path(__file__).resolve().parent
    root = Path(args.output_root).expanduser().resolve()

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
