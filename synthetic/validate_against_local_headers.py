from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


FILES = [
    "ADMISSIONS.csv.gz",
    "ICUSTAYS.csv.gz",
    "NOTEEVENTS.csv.gz",
    "D_ITEMS.csv.gz",
    "D_LABITEMS.csv.gz",
    "CHARTEVENTS.csv.gz",
    "LABEVENTS.csv.gz",
    "INPUTEVENTS_MV.csv.gz",
    "INPUTEVENTS_CV.csv.gz",
    "PROCEDUREEVENTS_MV.csv.gz",
]


def find_real_file(root: Path, filename: str) -> Path | None:
    hits = sorted(root.rglob(filename))
    return hits[0] if hits else None


def header(path: Path) -> list[str]:
    return list(pd.read_csv(path, nrows=0).columns)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--real-root", required=True)
    ap.add_argument("--synthetic-root", required=True)
    ap.add_argument("--output", default="")
    args = ap.parse_args()

    real_root = Path(args.real_root).expanduser().resolve()
    syn_root = Path(args.synthetic_root).expanduser().resolve() / "mimiciii" / "1.4"

    rows = []
    for filename in FILES:
        real = find_real_file(real_root / "mimiciii", filename)
        synthetic = syn_root / filename

        if real is None:
            rows.append(
                {
                    "file": filename,
                    "real_found": False,
                    "synthetic_found": synthetic.exists(),
                    "same_column_names": False,
                    "same_column_order": False,
                    "real_n_columns": 0,
                    "synthetic_n_columns": len(header(synthetic))
                    if synthetic.exists()
                    else 0,
                    "missing_from_synthetic": "",
                    "extra_in_synthetic": "",
                }
            )
            continue

        real_cols = header(real)
        syn_cols = header(synthetic) if synthetic.exists() else []

        rows.append(
            {
                "file": filename,
                "real_found": True,
                "synthetic_found": synthetic.exists(),
                "same_column_names": set(real_cols) == set(syn_cols),
                "same_column_order": real_cols == syn_cols,
                "real_n_columns": len(real_cols),
                "synthetic_n_columns": len(syn_cols),
                "missing_from_synthetic": "|".join(
                    c for c in real_cols if c not in syn_cols
                ),
                "extra_in_synthetic": "|".join(
                    c for c in syn_cols if c not in real_cols
                ),
            }
        )

    result = pd.DataFrame(rows)
    print(result.to_string(index=False))

    if args.output:
        out = Path(args.output).expanduser().resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        result.to_csv(out, index=False)

    failures = result[
        result["real_found"]
        & (
            ~result["synthetic_found"]
            | ~result["same_column_names"]
            | ~result["same_column_order"]
        )
    ]
    if len(failures):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
