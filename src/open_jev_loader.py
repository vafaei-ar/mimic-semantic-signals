from __future__ import annotations

import json
import os

import torch


def load_open_jev_corrected(
    repo_or_dir: str,
    device: str | None = None,
    revision: str | None = None,
):
    """Load Open-Jev with Transformers' corrected tokenizer regex behavior."""
    from huggingface_hub import snapshot_download
    from safetensors.torch import load_file
    from transformers import AutoModel, AutoTokenizer

    from typed_decisions.encoder import Collator, DecisionEncoder
    from typed_decisions.open_jev import OpenJev

    d = (
        repo_or_dir
        if os.path.isdir(repo_or_dir)
        else snapshot_download(repo_or_dir, revision=revision)
    )

    with open(os.path.join(d, "open_jev_config.json"), "r", encoding="utf-8") as f:
        cfg = json.load(f)

    tok = AutoTokenizer.from_pretrained(
        d,
        fix_mistral_regex=True,
    )
    bb = AutoModel.from_pretrained(
        d,
        attn_implementation=cfg.get("attn_implementation", "eager"),
    )

    m = DecisionEncoder(bb, cfg["hidden"], cfg["pool"])
    m.head.load_state_dict(load_file(os.path.join(d, "head.safetensors")))
    m.temperature = float(cfg.get("temperature", 1.0))

    dev = torch.device(
        device
        or (
            "cuda"
            if torch.cuda.is_available()
            else (
                "mps"
                if torch.backends.mps.is_available()
                else "cpu"
            )
        )
    )
    m.to(dev).eval()

    return OpenJev(
        m,
        tok,
        Collator(
            tok,
            max_state_tokens=cfg.get("max_state_tokens", 256),
            max_len=cfg.get("max_len", 512),
        ),
        cfg,
        dev,
    )
