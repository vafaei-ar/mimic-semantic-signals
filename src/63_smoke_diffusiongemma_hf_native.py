from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from semantic_schema import SEMANTIC_CONSTRUCTS


EXPECTED = [q["name"] for q in SEMANTIC_CONSTRUCTS]


def build_prompt(note: str) -> str:
    parts = [
        "You are a clinical semantic scoring system.",
        "Score ONLY the information explicitly supported by the clinical note below.",
        "For each construct, return a number from 0.0 to 1.0 representing how strongly the TRUE criterion is supported.",
        "0.0 means the TRUE criterion is not supported; 1.0 means it is strongly supported.",
        "Return exactly one JSON object with the eight keys shown below and numeric values only.",
        "Do not add markdown, explanations, units, or extra keys.",
        "",
        "Clinical note:",
        note,
        "",
        "Constructs:",
    ]
    for q in SEMANTIC_CONSTRUCTS:
        parts.extend(
            [
                f"- {q['name']}: {q['question']}",
                f"  TRUE: {q['criteria']['true']}",
                f"  FALSE: {q['criteria']['false']}",
            ]
        )
    parts.extend(
        [
            "",
            "Required JSON keys in this exact order:",
            ", ".join(EXPECTED),
        ]
    )
    return "\n".join(parts)


def extract_scores(text: str) -> dict[str, float]:
    candidates = re.findall(r"\{[^{}]*\}", text, flags=re.DOTALL)
    errors: list[str] = []
    for raw in reversed(candidates):
        try:
            obj = json.loads(raw)
        except Exception as exc:
            errors.append(type(exc).__name__)
            continue
        if not isinstance(obj, dict):
            continue
        if not all(name in obj for name in EXPECTED):
            continue
        scores: dict[str, float] = {}
        try:
            for name in EXPECTED:
                value = float(obj[name])
                if not 0.0 <= value <= 1.0:
                    raise ValueError(f"{name} out of range: {value}")
                scores[name] = value
        except Exception as exc:
            errors.append(str(exc))
            continue
        return scores
    raise ValueError(f"No valid eight-score JSON object found. parse_errors={errors[-3:]}")


def directory_size_gb(path: Path) -> float:
    total = 0
    for p in path.rglob("*"):
        if p.is_file():
            try:
                total += p.stat().st_size
            except OSError:
                pass
    return round(total / (1024 ** 3), 3)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-dir", required=True)
    ap.add_argument("--report", required=True)
    ap.add_argument("--seed", type=int, default=20260923)
    ap.add_argument("--max-new-tokens", type=int, default=256)
    args = ap.parse_args()

    import torch
    import transformers
    from transformers import AutoProcessor, DiffusionGemmaForBlockDiffusion

    model_dir = Path(args.model_dir).expanduser().resolve()
    report_path = Path(args.report).expanduser().resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is not available in the isolated Hugging Face environment.")
    if torch.cuda.device_count() < 2:
        raise RuntimeError("Native BF16 DiffusionGemma smoke test requires at least two visible GPUs.")

    gpus = []
    for idx in range(torch.cuda.device_count()):
        props = torch.cuda.get_device_properties(idx)
        gpus.append(
            {
                "index": idx,
                "name": props.name,
                "capability": list(torch.cuda.get_device_capability(idx)),
                "total_memory_gb": round(props.total_memory / (1024 ** 3), 2),
            }
        )

    torch.manual_seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)

    processor = AutoProcessor.from_pretrained(str(model_dir), local_files_only=True)
    model = DiffusionGemmaForBlockDiffusion.from_pretrained(
        str(model_dir),
        dtype=torch.bfloat16,
        device_map="auto",
        low_cpu_mem_usage=True,
        local_files_only=True,
        attn_implementation="sdpa",
    )
    model.eval()

    hf_map = getattr(model, "hf_device_map", {}) or {}
    device_counts: dict[str, int] = {}
    for device in hf_map.values():
        key = str(device)
        device_counts[key] = device_counts.get(key, 0) + 1

    synthetic_cases = [
        {
            "name": "stable",
            "note": "Synthetic note: patient remains comfortable and clinically stable with no new acute concerns. Oxygen requirement is unchanged and blood pressure is stable.",
        },
        {
            "name": "respiratory_worsening",
            "note": "Synthetic note: patient has increasing work of breathing, rising oxygen requirement, and worsening respiratory fatigue. The team is concerned that additional respiratory support may be needed.",
        },
        {
            "name": "hemodynamic_worsening",
            "note": "Synthetic note: patient is becoming hypotensive with cool extremities and worsening perfusion. The team is concerned about circulatory deterioration and is considering escalation of support.",
        },
    ]

    outputs = []
    for case in synthetic_cases:
        prompt = build_prompt(case["note"])
        messages = [{"role": "user", "content": prompt}]
        inputs = processor.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_dict=True,
            return_tensors="pt",
            enable_thinking=False,
        )
        first_device = next(model.parameters()).device
        inputs = {k: v.to(first_device) if hasattr(v, "to") else v for k, v in inputs.items()}
        input_len = inputs["input_ids"].shape[-1]
        with torch.inference_mode():
            generated = model.generate(
                **inputs,
                max_new_tokens=args.max_new_tokens,
            )
        sequences = getattr(generated, "sequences", generated)
        if sequences.ndim != 2 or sequences.shape[0] != 1:
            raise RuntimeError(
                f"Unexpected generated sequence shape: {tuple(sequences.shape)}"
            )
        completion_ids = sequences[0, input_len:].detach().cpu().tolist()
        decoded = processor.tokenizer.decode(
            completion_ids,
            skip_special_tokens=True,
        )
        if not isinstance(decoded, str):
            raise TypeError(f"Decoded completion is not text: {type(decoded).__name__}")
        scores = extract_scores(decoded)
        outputs.append(
            {
                "case": case["name"],
                "scores": scores,
                "decoded_tail": decoded[-4000:],
            }
        )

    by_case = {x["case"]: x["scores"] for x in outputs}
    directional_checks = {
        "stable_reassurance_exceeds_concern": (
            by_case["stable"]["reassuring_stability"]
            > by_case["stable"]["overall_clinician_concern"]
        ),
        "respiratory_note_has_more_respiratory_concern_than_stable": (
            by_case["respiratory_worsening"]["respiratory_concern"]
            > by_case["stable"]["respiratory_concern"]
        ),
        "hemodynamic_note_has_more_hemodynamic_concern_than_stable": (
            by_case["hemodynamic_worsening"]["hemodynamic_concern"]
            > by_case["stable"]["hemodynamic_concern"]
        ),
    }

    report = {
        "analysis": "Native Hugging Face DiffusionGemma synthetic semantic-score smoke test",
        "status": "completed",
        "synthetic_only": True,
        "clinical_note_inference_performed": False,
        "model": "google/diffusiongemma-26B-A4B-it",
        "backend": "transformers_native_bf16",
        "score_definition": (
            "Prompted zero-shot 0-1 support scores for the frozen eight semantic constructs; "
            "these are not Jev noul probabilities and must be labeled separately."
        ),
        "torch_version": torch.__version__,
        "torch_cuda_version": torch.version.cuda,
        "transformers_version": transformers.__version__,
        "visible_gpus": gpus,
        "device_map_module_counts": device_counts,
        "model_directory_size_gb": directory_size_gb(model_dir),
        "seed": args.seed,
        "outputs": outputs,
        "directional_sanity_checks_non_gating": directional_checks,
        "all_directional_sanity_checks_passed": all(directional_checks.values()),
        "next_gate": (
            "Do not run MIMIC notes until this native-HF synthetic result and score semantics are reviewed."
        ),
    }
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
