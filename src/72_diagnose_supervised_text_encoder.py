from __future__ import annotations

import importlib.util
import json
import os
import time
from pathlib import Path

import torch


def load_training_module():
    path = Path(__file__).with_name("71_train_supervised_text_encoder.py")
    spec = importlib.util.spec_from_file_location("supervised_text_encoder_v1", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load supervised encoder module.")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> None:
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_DATASETS_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"

    from transformers import AutoModel, AutoTokenizer

    out = Path("outputs/multitask_benchmark/supervised_text_encoder_diagnostic_v1.json").resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "analysis": "PHI-safe supervised text encoder smoke failure diagnostic",
        "local_only": True,
        "test_split_read": False,
        "contains_note_text": False,
        "contains_source_patient_identifiers": False,
        "stages": [],
        "status": "started",
    }
    stage = "start"
    started = time.perf_counter()

    try:
        mod = load_training_module()
        report["stages"].append("training_module_loaded")

        stage = "checkpoint_discovery"
        checkpoint = mod.discover_checkpoint()
        report["checkpoint_found"] = True
        report["stages"].append(stage)

        stage = "tokenizer_load"
        tokenizer = AutoTokenizer.from_pretrained(str(checkpoint), local_files_only=True)
        report["tokenizer_class"] = type(tokenizer).__name__
        report["stages"].append(stage)

        stage = "train_data_load"
        base = Path("data/real_mimic_local/multitask_tuning_v1").resolve()
        train_rows = mod.load_split(
            base,
            "train",
            tokenizer,
            chunk_tokens=384,
            chunk_overlap=64,
            max_chunks=5,
            limit_per_outcome=8,
            seed=20260924,
        )
        mod.assign_outcome_weights(train_rows)
        report["train_notes_loaded"] = len(train_rows)
        report["train_truncated_notes"] = sum(int(x.truncated) for x in train_rows)
        report["stages"].append(stage)

        stage = "validation_data_load"
        val_rows = mod.load_split(
            base,
            "validation",
            tokenizer,
            chunk_tokens=384,
            chunk_overlap=64,
            max_chunks=5,
            limit_per_outcome=8,
            seed=20260924,
        )
        report["validation_notes_loaded"] = len(val_rows)
        report["validation_truncated_notes"] = sum(int(x.truncated) for x in val_rows)
        report["stages"].append(stage)

        stage = "collate"
        collate = mod.make_collate(tokenizer)
        batch = collate(train_rows[:2])
        report["batch_notes"] = 2
        report["batch_chunks"] = int(batch["input_ids"].shape[0])
        report["batch_sequence_length"] = int(batch["input_ids"].shape[1])
        report["stages"].append(stage)

        stage = "model_load"
        encoder = AutoModel.from_pretrained(str(checkpoint), local_files_only=True)
        if hasattr(encoder, "gradient_checkpointing_enable"):
            encoder.gradient_checkpointing_enable()
        model = mod.MultiTaskDeberta(encoder, int(encoder.config.hidden_size), 3)
        device = torch.device("cuda:0")
        model.to(device)
        report["model_class"] = type(encoder).__name__
        report["stages"].append(stage)

        stage = "forward"
        input_ids = batch["input_ids"].to(device)
        attention_mask = batch["attention_mask"].to(device)
        chunk_note_index = batch["chunk_note_index"].to(device)
        outcome_index = batch["outcome_index"].to(device)
        labels = batch["labels"].to(device)
        with torch.autocast(device_type="cuda", dtype=torch.bfloat16):
            chunk_logits = model(input_ids, attention_mask)
            note_logits = mod.aggregate_note_logits(
                chunk_logits,
                chunk_note_index,
                outcome_index,
                len(batch["case_ids"]),
            )
            loss = torch.nn.functional.binary_cross_entropy_with_logits(note_logits, labels)
        report["forward_loss"] = float(loss.detach().cpu())
        report["stages"].append(stage)

        stage = "backward"
        loss.backward()
        report["stages"].append(stage)

        report["cuda_peak_allocated_gb"] = round(torch.cuda.max_memory_allocated() / (1024 ** 3), 3)
        report["cuda_peak_reserved_gb"] = round(torch.cuda.max_memory_reserved() / (1024 ** 3), 3)
        report["status"] = "completed"
    except Exception as exc:
        report["status"] = "failed"
        report["failed_stage"] = stage
        report["error_type"] = type(exc).__name__
        report["error_message"] = str(exc)[:2000]
    finally:
        report["runtime_seconds"] = time.perf_counter() - started
        out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))

    if report["status"] != "completed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
