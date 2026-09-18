from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from common import MODULE_DIRS, csv_files, module_path, read_header, resolve_root, safe_write_csv, write_json


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    root = resolve_root(args.root)
    out = Path(args.output)
    rows = []

    for key in MODULE_DIRS:
        base = module_path(root, key)
        files = csv_files(base)
        if not base.exists():
            rows.append({
                "module": key, "available": False, "relative_path": "",
                "size_mb": 0.0, "n_columns": 0, "columns": "",
            })
            continue
        if not files:
            rows.append({
                "module": key, "available": True, "relative_path": "",
                "size_mb": 0.0, "n_columns": 0, "columns": "",
            })
        for f in files:
            cols = read_header(f)
            rows.append({
                "module": key,
                "available": True,
                "relative_path": str(f.relative_to(root)),
                "size_mb": round(f.stat().st_size / 1024**2, 3),
                "n_columns": len(cols),
                "columns": "|".join(cols),
            })

    df = pd.DataFrame(rows)
    safe_write_csv(df, out / "inventory.csv")

    summary = {
        "root_exists": True,
        "module_availability": {
            key: bool(module_path(root, key).exists()) for key in MODULE_DIRS
        },
        "csv_file_counts": {
            key: len(csv_files(module_path(root, key))) for key in MODULE_DIRS
        },
        "total_csv_files": int(sum(len(csv_files(module_path(root, k))) for k in MODULE_DIRS)),
    }
    write_json(summary, out / "inventory_summary.json")


if __name__ == "__main__":
    main()
