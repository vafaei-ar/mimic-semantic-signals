from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from collections import Counter, defaultdict
from pathlib import Path
import subprocess

import numpy as np
import pandas as pd


OUTCOMES = [
    "invasive_ventilation",
    "renal_replacement_therapy",
    "icu_death",
]
SPLITS = ["train", "validation", "test"]
RATIOS = {"train": 0.70, "validation": 0.15, "test": 0.15}


class UnionFind:
    def __init__(self, n: int) -> None:
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if self.rank[ra] < self.rank[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        if self.rank[ra] == self.rank[rb]:
            self.rank[ra] += 1


def package_version(name: str) -> dict:
    available = importlib.util.find_spec(name) is not None
    version = None
    if available:
        for candidate in [name, name.replace("_", "-")]:
            try:
                version = importlib.metadata.version(candidate)
                break
            except importlib.metadata.PackageNotFoundError:
                pass
    return {"available": bool(available), "version": version}


def safe_config_summary(path: Path) -> dict:
    if not path.exists():
        return {"present": False}
    try:
        cfg = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"present": True, "config_read_error": type(exc).__name__}
    keys = [
        "model_type",
        "architectures",
        "hidden_size",
        "num_hidden_layers",
        "num_attention_heads",
        "vocab_size",
        "torch_dtype",
    ]
    return {"present": True, **{k: cfg.get(k) for k in keys if k in cfg}}


def dir_size_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    total = 0
    for p in path.rglob("*"):
        try:
            if p.is_file():
                total += p.stat().st_size
        except OSError:
            pass
    return int(total)


def model_cache_audit(repo_root: Path) -> dict:
    home = Path.home()
    openjev_root = home / ".cache" / "huggingface" / "hub" / "models--com-kotobalabs--open-jev-deberta-v3-large"
    openjev_configs = sorted(openjev_root.glob("snapshots/*/config.json"))
    openjev_cfg = safe_config_summary(openjev_configs[-1]) if openjev_configs else {"present": False}

    laya_root = home / ".cache" / "mimic-semantic-signals" / "laya-typed-decisions-f9ab0b2"
    laya_cfg = safe_config_summary(laya_root / "config.json")
    if not laya_cfg.get("present") and (laya_root / "model.safetensors").exists():
        laya_cfg["present"] = True

    dg_root = repo_root / "data" / "local_models" / "diffusiongemma-26B-A4B-it-hf"
    dg_cfg = safe_config_summary(dg_root / "config.json")

    return {
        "openjev": {
            "checkpoint_cached": bool(openjev_configs),
            "config": openjev_cfg,
            "cache_size_gb": round(dir_size_bytes(openjev_root) / (1024 ** 3), 3),
        },
        "laya": {
            "checkpoint_cached": bool((laya_root / "model.safetensors").exists()),
            "config": laya_cfg,
            "cache_size_gb": round(dir_size_bytes(laya_root) / (1024 ** 3), 3),
        },
        "diffusiongemma_hf": {
            "checkpoint_cached": bool((dg_root / "model.safetensors.index.json").exists()),
            "config": dg_cfg,
            "cache_size_gb": round(dir_size_bytes(dg_root) / (1024 ** 3), 3),
        },
    }


def gpu_audit() -> dict:
    try:
        out = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,memory.free",
                "--format=csv,noheader,nounits",
            ],
            text=True,
            stderr=subprocess.STDOUT,
            timeout=20,
        )
        rows = []
        for line in out.strip().splitlines():
            parts = [x.strip() for x in line.split(",")]
            if len(parts) >= 3:
                rows.append(
                    {
                        "name": parts[0],
                        "memory_total_mb": int(float(parts[1])),
                        "memory_free_mb": int(float(parts[2])),
                    }
                )
        return {"available": bool(rows), "gpus": rows}
    except Exception as exc:
        return {"available": False, "error": type(exc).__name__}


def diffusiongemma_env_audit(repo_root: Path) -> dict:
    py = repo_root / "data" / "local_envs" / "diffusiongemma_hf_cu124" / "bin" / "python"
    if not py.exists():
        return {"present": False}
    code = (
        "import json, importlib.util, torch, transformers; "
        "print(json.dumps({"
        "'torch':torch.__version__,"
        "'torch_cuda':torch.version.cuda,"
        "'transformers':transformers.__version__,"
        "'peft':importlib.util.find_spec('peft') is not None,"
        "'accelerate':importlib.util.find_spec('accelerate') is not None,"
        "'bitsandbytes':importlib.util.find_spec('bitsandbytes') is not None"
        "}))"
    )
    env = dict(os.environ)
    env.update(
        {
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "HF_DATASETS_OFFLINE": "1",
            "HF_HUB_DISABLE_TELEMETRY": "1",
        }
    )
    try:
        out = subprocess.check_output(
            [str(py), "-c", code],
            text=True,
            stderr=subprocess.STDOUT,
            timeout=60,
            env=env,
        )
        return {"present": True, **json.loads(out.strip().splitlines()[-1])}
    except Exception as exc:
        return {"present": True, "query_error": type(exc).__name__}


def build_component_split(base: Path, seed: int) -> dict:
    frames = {}
    node_keys = []
    node_rows = {}
    node_patients = {}

    for outcome in OUTCOMES:
        p = base / outcome / "snapshot_index_local.csv"
        if not p.exists():
            raise FileNotFoundError(p)
        df = pd.read_csv(p)
        required = {"subject_id", "match_set", "label", "case_id"}
        missing = required - set(df.columns)
        if missing:
            raise RuntimeError(f"{outcome}: snapshot index missing {sorted(missing)}")
        df["subject_id"] = pd.to_numeric(df["subject_id"], errors="raise").astype(int)
        df["match_set"] = pd.to_numeric(df["match_set"], errors="raise").astype(int)
        df["label"] = pd.to_numeric(df["label"], errors="raise").astype(int)
        frames[outcome] = df

        for ms, g in df.groupby("match_set", sort=True):
            key = (outcome, int(ms))
            node_keys.append(key)
            node_rows[key] = g.copy()
            node_patients[key] = set(g["subject_id"].astype(int).tolist())

    node_index = {k: i for i, k in enumerate(node_keys)}
    uf = UnionFind(len(node_keys))
    by_patient = defaultdict(list)
    for key in node_keys:
        for sid in node_patients[key]:
            by_patient[sid].append(key)
    for keys in by_patient.values():
        first = keys[0]
        for other in keys[1:]:
            uf.union(node_index[first], node_index[other])

    components = defaultdict(list)
    for key in node_keys:
        components[uf.find(node_index[key])].append(key)

    comp_records = []
    for root, keys in components.items():
        patients = set()
        outcome_counts = Counter()
        rows = 0
        for key in keys:
            patients.update(node_patients[key])
            outcome_counts[key[0]] += 1
            rows += len(node_rows[key])
        comp_records.append(
            {
                "root": root,
                "keys": keys,
                "patients": patients,
                "outcome_match_sets": dict(outcome_counts),
                "match_sets": len(keys),
                "rows": rows,
            }
        )

    totals = Counter(k[0] for k in node_keys)
    targets = {
        split: {o: RATIOS[split] * totals[o] for o in OUTCOMES}
        for split in SPLITS
    }
    assigned_counts = {split: Counter() for split in SPLITS}
    assignment = {}

    rng = np.random.default_rng(seed)
    jitter = {id(rec): float(rng.random()) for rec in comp_records}
    comp_records = sorted(
        comp_records,
        key=lambda x: (-x["match_sets"], -x["rows"], jitter[id(x)]),
    )

    for rec in comp_records:
        best_split = None
        best_score = None
        for split in SPLITS:
            score = 0.0
            for outcome in OUTCOMES:
                new_count = assigned_counts[split][outcome] + rec["outcome_match_sets"].get(outcome, 0)
                target = targets[split][outcome]
                score += ((new_count - target) ** 2) / max(target, 1.0)
            total_new = sum(assigned_counts[split].values()) + rec["match_sets"]
            total_target = RATIOS[split] * sum(totals.values())
            score += 0.25 * ((total_new - total_target) ** 2) / max(total_target, 1.0)
            if best_score is None or score < best_score:
                best_score = score
                best_split = split
        assignment[rec["root"]] = best_split
        for outcome, n in rec["outcome_match_sets"].items():
            assigned_counts[best_split][outcome] += n

    split_patients = {s: set() for s in SPLITS}
    split_summary = {s: {} for s in SPLITS}
    for split in SPLITS:
        for outcome in OUTCOMES:
            selected_keys = []
            for rec in comp_records:
                if assignment[rec["root"]] == split:
                    selected_keys.extend([k for k in rec["keys"] if k[0] == outcome])
                    split_patients[split].update(rec["patients"])
            parts = [node_rows[k] for k in selected_keys]
            d = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=frames[outcome].columns)
            split_summary[split][outcome] = {
                "rows": int(len(d)),
                "cases": int(d["label"].sum()) if len(d) else 0,
                "controls": int((1 - d["label"]).sum()) if len(d) else 0,
                "match_sets": int(len(selected_keys)),
                "unique_patients": int(d["subject_id"].nunique()) if len(d) else 0,
            }

    overlaps = {}
    for i, a in enumerate(SPLITS):
        for b in SPLITS[i + 1:]:
            overlaps[f"{a}_vs_{b}"] = int(len(split_patients[a] & split_patients[b]))

    component_sizes_sets = [r["match_sets"] for r in comp_records]
    component_sizes_patients = [len(r["patients"]) for r in comp_records]
    cross_outcome_components = sum(
        1 for r in comp_records if len(r["outcome_match_sets"]) > 1
    )

    return {
        "split_method": (
            "Connected components of matched sets linked by any shared subject_id across all three outcomes, "
            "followed by deterministic seeded greedy allocation toward 70/15/15 outcome-balanced train/validation/test."
        ),
        "seed": seed,
        "ratios": RATIOS,
        "total_unique_patients": int(len(by_patient)),
        "total_match_sets_by_outcome": {o: int(totals[o]) for o in OUTCOMES},
        "connected_components": int(len(comp_records)),
        "cross_outcome_components": int(cross_outcome_components),
        "largest_component_match_sets": int(max(component_sizes_sets) if component_sizes_sets else 0),
        "largest_component_patients": int(max(component_sizes_patients) if component_sizes_patients else 0),
        "patient_overlap_across_splits": overlaps,
        "split_summary": split_summary,
        "identifiers_shared_in_report": False,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Read-only local audit for leakage-safe post-freeze tuning feasibility.")
    ap.add_argument("--base", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--seed", type=int, default=20260924)
    args = ap.parse_args()

    repo_root = Path.cwd().resolve()
    base = Path(args.base).expanduser().resolve()
    report = {
        "analysis": "Post-freeze tuning feasibility audit",
        "local_only": True,
        "read_only": True,
        "network_required": False,
        "contains_note_text": False,
        "contains_source_patient_identifiers": False,
        "cohort_split_feasibility": build_component_split(base, args.seed),
        "runtime_packages": {
            name: package_version(name)
            for name in [
                "torch",
                "transformers",
                "typed_decisions",
                "laya",
                "peft",
                "accelerate",
                "bitsandbytes",
                "datasets",
            ]
        },
        "model_caches": model_cache_audit(repo_root),
        "gpu_state": gpu_audit(),
        "diffusiongemma_env": diffusiongemma_env_audit(repo_root),
        "guardrail": (
            "This audit does not train, modify, or delete any model or clinical data. "
            "Its purpose is to determine whether a patient-disjoint post-freeze tuning phase can be "
            "specified before any supervised adaptation begins."
        ),
    }
    out = Path(args.output).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
