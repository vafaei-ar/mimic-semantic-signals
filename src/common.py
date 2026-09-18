from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable

import pandas as pd

MODULE_DIRS = {
    "mimiciii": "mimiciii",
    "mimiciv": "mimiciv",
    "mimic_iv_note": "mimic-iv-note",
    "mimic_iv_ed": "mimic-iv-ed",
    "mimic_iv_ecg": "mimic-iv-ecg",
    "mimic_iv_echo": "mimic-iv-echo",
    "mimic_cxr": "mimic-cxr",
}

SENSITIVE_OUTPUT_COLUMNS = {
    "subject_id", "hadm_id", "stay_id", "icustay_id", "text", "note_text",
    "charttime", "storetime", "deathtime", "admittime", "dischtime",
}


def resolve_root(root: str | Path) -> Path:
    p = Path(root).expanduser().resolve()
    if not p.exists():
        raise FileNotFoundError(f"MIMIC root does not exist: {p}")
    return p


def module_path(root: Path, key: str) -> Path:
    return root / MODULE_DIRS[key]


def csv_files(path: Path) -> list[Path]:
    if not path.exists():
        return []
    out = []
    for p in path.rglob("*"):
        if p.is_file() and (p.name.lower().endswith(".csv") or p.name.lower().endswith(".csv.gz")):
            out.append(p)
    return sorted(out)


def find_file(path: Path, basenames: Iterable[str]) -> Path | None:
    wanted = [x.lower() for x in basenames]
    files = csv_files(path)
    by_name = {}
    for f in files:
        by_name.setdefault(f.name.lower(), []).append(f)
    for name in wanted:
        if name in by_name:
            return sorted(by_name[name], key=lambda x: (len(x.parts), len(str(x))))[0]
    for f in files:
        low = f.name.lower()
        if any(name in low for name in wanted):
            return f
    return None


def read_header(path: Path) -> list[str]:
    try:
        return list(pd.read_csv(path, nrows=0).columns)
    except Exception:
        return []


def normalize_columns(cols: Iterable[str]) -> dict[str, str]:
    return {str(c).strip().lower(): str(c) for c in cols}


def choose_anchor_with_column(path: Path, required: str = "subject_id") -> Path | None:
    candidates = []
    for f in csv_files(path):
        cols = normalize_columns(read_header(f))
        if required.lower() in cols:
            candidates.append((f.stat().st_size, f))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0])
    return candidates[0][1]


def read_columns(path: Path, wanted: Iterable[str], chunksize: int | None = None):
    header = read_header(path)
    cmap = normalize_columns(header)
    actual = [cmap[w.lower()] for w in wanted if w.lower() in cmap]
    if not actual:
        raise ValueError(f"None of requested columns found in {path}: {list(wanted)}")
    return pd.read_csv(path, usecols=actual, chunksize=chunksize, low_memory=False)


def lower_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).lower() for c in df.columns]
    return df


def parse_datetime(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, errors="coerce")


def aggregate_subject_ids(path: Path, chunksize: int = 250_000) -> set[int]:
    ids: set[int] = set()
    reader = read_columns(path, ["subject_id"], chunksize=chunksize)
    for chunk in reader:
        chunk = lower_columns(chunk)
        vals = pd.to_numeric(chunk["subject_id"], errors="coerce").dropna().astype("int64")
        ids.update(vals.tolist())
    return ids


def safe_write_csv(df: pd.DataFrame, path: Path) -> None:
    bad = [c for c in df.columns if str(c).lower() in SENSITIVE_OUTPUT_COLUMNS]
    if bad:
        raise ValueError(f"Refusing to export potentially patient-level/sensitive columns: {bad}")
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def write_json(obj: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str) + "\n", encoding="utf-8")


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
