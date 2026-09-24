from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from scipy import sparse
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from torch.utils.data import DataLoader, Dataset

from runrelay_progress import update_progress


OUTCOMES = [
    "invasive_ventilation",
    "renal_replacement_therapy",
    "icu_death",
]
OUTCOME_TO_INDEX = {o: i for i, o in enumerate(OUTCOMES)}
EXPECTED_CHECKPOINT_SHA256 = "563b21c8a53cf5c61c46677f1ee634592bd06a711e3da52616a10b2b6f9826a6"
BOOTSTRAP_REPLICATES = 2000
BOOTSTRAP_SEED = 20260924


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_training_module():
    path = Path(__file__).with_name("71_train_supervised_text_encoder.py")
    spec = importlib.util.spec_from_file_location("supervised_text_encoder_final_test", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load supervised encoder utilities.")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def read_cases(base: Path, split: str, outcome: str) -> pd.DataFrame:
    path = base / split / outcome / "cases.jsonl"
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            meta = rec.get("metadata", {})
            note = rec.get("model_state", {}).get("clinical_note")
            if meta.get("tuning_split") != split:
                raise RuntimeError(f"{path}: tuning split metadata mismatch")
            if meta.get("outcome") != outcome:
                raise RuntimeError(f"{path}: outcome metadata mismatch")
            if not isinstance(note, str) or not note.strip():
                raise RuntimeError(f"{path}: blank note")
            rows.append(
                {
                    "case_id": str(rec.get("case_id")),
                    "label": int(meta["label"]),
                    "match_set": int(meta["match_set"]),
                    "note_text": note,
                    "category": str(meta["note_category"]),
                    "dbsource": str(meta["dbsource"]),
                    "hours_since_icu": float(meta["hours_since_icu"]),
                }
            )
    out = pd.DataFrame(rows)
    if out.empty or out["case_id"].duplicated().any():
        raise RuntimeError(f"{path}: empty or duplicated cases")
    return out


def load_structured(base: Path, split: str, outcome: str) -> pd.DataFrame:
    path = base / split / outcome / "structured_features.csv"
    df = pd.read_csv(path)
    df["case_id"] = df["case_id"].astype(str)
    if df.empty or df["case_id"].duplicated().any():
        raise RuntimeError(f"{path}: empty or duplicated structured rows")
    return df


class TestNote:
    def __init__(self, case_id, outcome, outcome_index, label, chunks):
        self.case_id = case_id
        self.outcome = outcome
        self.outcome_index = outcome_index
        self.label = label
        self.chunks = chunks
        self.weight = 1.0


class TestDataset(Dataset):
    def __init__(self, rows):
        self.rows = rows

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, i):
        return self.rows[i]


def make_test_examples(v1, tokenizer, df: pd.DataFrame, outcome: str):
    rows = []
    for rec in df.itertuples(index=False):
        ids = tokenizer(rec.note_text, add_special_tokens=False)["input_ids"]
        chunks, _ = v1.chunk_ids(ids, 384, 64, 5)
        rows.append(
            TestNote(
                rec.case_id,
                outcome,
                OUTCOME_TO_INDEX[outcome],
                int(rec.label),
                chunks,
            )
        )
    return rows


def make_collate(tokenizer):
    def collate(notes):
        flat_ids = []
        chunk_note_index = []
        for note_i, ex in enumerate(notes):
            for ids in ex.chunks:
                flat_ids.append(tokenizer.build_inputs_with_special_tokens(ids))
                chunk_note_index.append(note_i)
        padded = tokenizer.pad({"input_ids": flat_ids}, padding=True, return_tensors="pt")
        return {
            "input_ids": padded["input_ids"],
            "attention_mask": padded["attention_mask"],
            "chunk_note_index": torch.tensor(chunk_note_index, dtype=torch.long),
            "outcome_index": torch.tensor([x.outcome_index for x in notes], dtype=torch.long),
            "case_ids": [x.case_id for x in notes],
        }
    return collate


@torch.no_grad()
def predict_encoder(v1, model, tokenizer, df: pd.DataFrame, outcome: str, device) -> np.ndarray:
    examples = make_test_examples(v1, tokenizer, df, outcome)
    loader = DataLoader(
        TestDataset(examples),
        batch_size=2,
        shuffle=False,
        num_workers=0,
        collate_fn=make_collate(tokenizer),
        pin_memory=True,
    )
    probs = []
    model.eval()
    for batch in loader:
        input_ids = batch["input_ids"].to(device, non_blocking=True)
        attention_mask = batch["attention_mask"].to(device, non_blocking=True)
        cni = batch["chunk_note_index"].to(device)
        oi = batch["outcome_index"].to(device)
        with torch.autocast(device_type="cuda", dtype=torch.bfloat16):
            chunk_logits = model(input_ids, attention_mask)
            note_logits = v1.aggregate_note_logits(chunk_logits, cni, oi, len(batch["case_ids"]))
        probs.extend(torch.sigmoid(note_logits).float().cpu().numpy().tolist())
    return np.asarray(probs, dtype=float)


def make_structured_preprocessor(train_df: pd.DataFrame, feature_cols: list[str]):
    categorical = [c for c in ["category", "dbsource"] if c in feature_cols]
    numeric = [c for c in feature_cols if c not in categorical]
    transformers = []
    if numeric:
        transformers.append(
            (
                "num",
                Pipeline(
                    [
                        ("impute", SimpleImputer(strategy="median", add_indicator=True)),
                        ("scale", StandardScaler()),
                    ]
                ),
                numeric,
            )
        )
    if categorical:
        transformers.append(("cat", OneHotEncoder(handle_unknown="ignore"), categorical))
    return ColumnTransformer(transformers, remainder="drop")


def fit_baselines(train: pd.DataFrame, test: pd.DataFrame) -> dict[str, np.ndarray]:
    reserved = {"case_id", "label", "match_set", "patient_group", "note_text"}
    categorical = [c for c in ["category", "dbsource"] if c in train.columns]
    baseline_cols = [c for c in ["hours_since_icu", *categorical] if c in train.columns]
    excluded = reserved | set(categorical) | {"hours_since_icu", "tuning_split"}
    physiology = [
        c for c in train.columns
        if c not in excluded and pd.api.types.is_numeric_dtype(train[c])
    ]
    structured_cols = ["hours_since_icu", *categorical, *physiology]

    structured_pre = make_structured_preprocessor(train, structured_cols)
    xs_train = sparse.csr_matrix(structured_pre.fit_transform(train[structured_cols]))
    xs_test = sparse.csr_matrix(structured_pre.transform(test[structured_cols]))

    context_pre = make_structured_preprocessor(train, baseline_cols)
    xc_train = sparse.csr_matrix(context_pre.fit_transform(train[baseline_cols]))
    xc_test = sparse.csr_matrix(context_pre.transform(test[baseline_cols]))

    tfidf = TfidfVectorizer(
        lowercase=True,
        strip_accents="unicode",
        ngram_range=(1, 2),
        min_df=5,
        max_df=0.98,
        max_features=10000,
        sublinear_tf=True,
        dtype=np.float64,
    )
    xt_train = tfidf.fit_transform(train["note_text"].astype(str))
    xt_test = tfidf.transform(test["note_text"].astype(str))

    y = train["label"].astype(int).to_numpy()
    matrices = {
        "structured_only": (xs_train, xs_test),
        "context_plus_tfidf": (
            sparse.hstack([xc_train, xt_train], format="csr"),
            sparse.hstack([xc_test, xt_test], format="csr"),
        ),
        "structured_plus_tfidf": (
            sparse.hstack([xs_train, xt_train], format="csr"),
            sparse.hstack([xs_test, xt_test], format="csr"),
        ),
    }
    out = {}
    for name, (a, b) in matrices.items():
        model = LogisticRegression(max_iter=3000, solver="liblinear", C=1.0)
        model.fit(a, y)
        out[name] = model.predict_proba(b)[:, 1]
    return out


def metric_summary(y: np.ndarray, p: np.ndarray) -> dict:
    return {
        "auroc": float(roc_auc_score(y, p)),
        "auprc": float(average_precision_score(y, p)),
        "brier": float(brier_score_loss(y, p)),
    }


def cluster_bootstrap(df: pd.DataFrame, pred_cols: list[str], outcome_seed: int) -> tuple[dict, dict]:
    by_set = {k: g.copy() for k, g in df.groupby("match_set", sort=False)}
    sets = np.asarray(list(by_set.keys()))
    rng = np.random.default_rng(outcome_seed)
    model_auroc = {m: [] for m in pred_cols}
    model_auprc = {m: [] for m in pred_cols}
    diff_keys = [
        ("supervised_encoder_v2", "context_plus_tfidf"),
        ("supervised_encoder_v2", "structured_only"),
        ("structured_plus_tfidf", "structured_only"),
    ]
    diffs = {f"{a}_minus_{b}": [] for a, b in diff_keys}

    for _ in range(BOOTSTRAP_REPLICATES):
        sampled = rng.choice(sets, size=len(sets), replace=True)
        boot = pd.concat([by_set[k] for k in sampled], ignore_index=True)
        y = boot["label"].to_numpy(dtype=int)
        aucs = {}
        for m in pred_cols:
            p = boot[m].to_numpy(dtype=float)
            aucs[m] = roc_auc_score(y, p)
            model_auroc[m].append(float(aucs[m]))
            model_auprc[m].append(float(average_precision_score(y, p)))
        for a, b in diff_keys:
            diffs[f"{a}_minus_{b}"].append(float(aucs[a] - aucs[b]))

    intervals = {}
    for m in pred_cols:
        a = np.asarray(model_auroc[m])
        p = np.asarray(model_auprc[m])
        intervals[m] = {
            "auroc_ci95": [float(np.quantile(a, 0.025)), float(np.quantile(a, 0.975))],
            "auprc_ci95": [float(np.quantile(p, 0.025)), float(np.quantile(p, 0.975))],
        }

    diff_out = {}
    for key, vals in diffs.items():
        arr = np.asarray(vals)
        a, b = key.split("_minus_")
        observed = roc_auc_score(df["label"], df[a]) - roc_auc_score(df["label"], df[b])
        diff_out[key] = {
            "difference": float(observed),
            "ci95": [float(np.quantile(arr, 0.025)), float(np.quantile(arr, 0.975))],
            "bootstrap_replicates": BOOTSTRAP_REPLICATES,
            "cluster": "match_set",
        }
    return intervals, diff_out


def main() -> None:
    ap = argparse.ArgumentParser(description="One-time locked-test evaluation of frozen supervised encoder v2.")
    ap.add_argument("--base", required=True)
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for final supervised encoder evaluation.")

    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_DATASETS_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"

    checkpoint_path = Path(args.checkpoint).expanduser().resolve()
    actual_sha = sha256_file(checkpoint_path)
    if actual_sha != EXPECTED_CHECKPOINT_SHA256:
        raise RuntimeError(
            f"Checkpoint SHA-256 mismatch before test unlock: {actual_sha}"
        )

    # Test access begins only after the frozen checkpoint hash is verified.
    from transformers import AutoModel, AutoTokenizer

    v1 = load_training_module()
    base = Path(args.base).expanduser().resolve()
    out_path = Path(args.output).expanduser().resolve()
    model_path = v1.discover_checkpoint()
    tokenizer = AutoTokenizer.from_pretrained(str(model_path), local_files_only=True)

    obj = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    if int(obj.get("epoch", -1)) != 4:
        raise RuntimeError("Frozen checkpoint is not selected epoch 4.")
    encoder = AutoModel.from_pretrained(str(model_path), local_files_only=True)
    model = v1.MultiTaskDeberta(encoder, int(encoder.config.hidden_size), len(OUTCOMES))
    model.load_state_dict(obj["model_state_dict"])
    device = torch.device("cuda:0")
    model.to(device)

    report = {
        "analysis": "One-time locked-test evaluation of supervised Open-Jev DeBERTa multitask upper-bound v2",
        "protocol": "docs/multitask_supervised_text_encoder_v2_final_test_protocol.md",
        "checkpoint_sha256": actual_sha,
        "selected_epoch": 4,
        "local_only": True,
        "network_enabled": False,
        "test_split_opened": True,
        "contains_note_text": False,
        "contains_source_patient_identifiers": False,
        "patient_level_predictions_shared": False,
        "semantic_preservation_claimed": False,
        "matched_case_control_prevalence": 0.25,
        "bootstrap_replicates": BOOTSTRAP_REPLICATES,
        "bootstrap_cluster": "match_set",
        "outcomes": {},
    }

    for i, outcome in enumerate(OUTCOMES):
        update_progress(
            current=i,
            total=len(OUTCOMES),
            phase="supervised_encoder_v2_final_test",
            message=f"Evaluating locked test outcome {i + 1}/{len(OUTCOMES)}: {outcome}",
            unit="outcome",
        )
        train_cases = read_cases(base, "train", outcome)
        test_cases = read_cases(base, "test", outcome)
        train_struct = load_structured(base, "train", outcome)
        test_struct = load_structured(base, "test", outcome)

        train = train_cases.merge(
            train_struct.drop(columns=[c for c in ["label", "match_set", "patient_group", "category", "dbsource", "hours_since_icu", "tuning_split"] if c in train_struct.columns]),
            on="case_id",
            how="inner",
        )
        test = test_cases.merge(
            test_struct.drop(columns=[c for c in ["label", "match_set", "patient_group", "category", "dbsource", "hours_since_icu", "tuning_split"] if c in test_struct.columns]),
            on="case_id",
            how="inner",
        )
        if len(train) != len(train_cases) or len(test) != len(test_cases):
            raise RuntimeError(f"{outcome}: structured merge lost rows")

        neural_p = predict_encoder(v1, model, tokenizer, test_cases, outcome, device)
        baseline_p = fit_baselines(train, test)
        eval_df = test_cases[["case_id", "label", "match_set"]].copy()
        eval_df["supervised_encoder_v2"] = neural_p
        for name, p in baseline_p.items():
            eval_df[name] = p

        pred_cols = [
            "supervised_encoder_v2",
            "structured_only",
            "context_plus_tfidf",
            "structured_plus_tfidf",
        ]
        metrics = {
            m: metric_summary(
                eval_df["label"].to_numpy(dtype=int),
                eval_df[m].to_numpy(dtype=float),
            )
            for m in pred_cols
        }
        intervals, differences = cluster_bootstrap(
            eval_df,
            pred_cols,
            BOOTSTRAP_SEED + i * 100,
        )
        for m in pred_cols:
            metrics[m].update(intervals[m])

        report["outcomes"][outcome] = {
            "n": int(len(eval_df)),
            "cases": int(eval_df["label"].sum()),
            "controls": int((1 - eval_df["label"]).sum()),
            "models": metrics,
            "paired_auroc_differences": differences,
        }
        update_progress(
            current=i + 1,
            total=len(OUTCOMES),
            phase="supervised_encoder_v2_final_test",
            message=f"Completed locked test outcome {i + 1}/{len(OUTCOMES)}: {outcome}",
            unit="outcome",
        )

    report["interpretation_guardrail"] = (
        "This is a one-time evaluation on frozen 1:3 matched test cohorts. "
        "Brier scores are descriptive under artificial 25% prevalence. "
        "The supervised encoder is an outcome-supervised predictive upper bound/comparator, "
        "not a semantic-preserving JEV model."
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
