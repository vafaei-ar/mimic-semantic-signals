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
    for raw in reversed(candidates):
        try:
            obj = json.loads(raw)
        except Exception:
            continue
        if not isinstance(obj, dict) or not all(name in obj for name in EXPECTED):
            continue
        scores: dict[str, float] = {}
        try:
            for name in EXPECTED:
                value = float(obj[name])
                if not 0.0 <= value <= 1.0:
                    raise ValueError
                scores[name] = value
        except Exception:
            continue
        return scores
    raise ValueError("No valid eight-score JSON object found.")


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

    model_dir = Path(args.model_dir).resolve()
    report_path = Path(args.report).resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)

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

    cases = [
        {
            "name": "stable",
            "note": "Synthetic note: patient remains comfortable and clinically stable with no new acute concerns. Oxygen requirement is unchanged and blood pressure is stable.",
        },
        {
            "name": "respiratory_mild",
            "note": "Synthetic note: patient has a small increase in oxygen requirement from baseline but is comfortable, speaking normally, and has no obvious respiratory distress. Team plans closer monitoring.",
        },
        {
            "name": "respiratory_moderate",
            "note": "Synthetic note: patient has increased work of breathing and needs more supplemental oxygen than earlier. Respiratory status is concerning, although the patient is not yet in severe distress and no immediate intubation is planned.",
        },
        {
            "name": "respiratory_severe",
            "note": "Synthetic note: patient has rapidly worsening hypoxemia, marked work of breathing, and respiratory fatigue despite escalating oxygen. The team is preparing for possible intubation.",
        },
        {
            "name": "hemodynamic_mild",
            "note": "Synthetic note: blood pressure is borderline lower than earlier, but the patient remains warm, alert, and well perfused. No vasopressor or urgent escalation is planned; team will monitor.",
        },
        {
            "name": "hemodynamic_moderate",
            "note": "Synthetic note: blood pressure continues to drift down with cool extremities and concern for worsening perfusion. Response to fluids is incomplete, and the team is discussing whether additional circulatory support may be needed.",
        },
        {
            "name": "hemodynamic_severe",
            "note": "Synthetic note: patient has persistent severe hypotension with poor peripheral perfusion and worsening mental status despite initial treatment. The team is preparing to escalate hemodynamic support urgently.",
        },
        {
            "name": "diagnostic_uncertainty",
            "note": "Synthetic note: patient has mild tachycardia and fatigue, but the cause is unclear. The team is considering infection, pain, medication effect, and dehydration and is uncertain which explanation is most likely.",
        },
        {
            "name": "poor_treatment_response",
            "note": "Synthetic note: symptoms and abnormal vital signs remain largely unchanged despite the initial treatment. The team notes limited improvement and is considering a different management approach.",
        },
        {
            "name": "improving_after_treatment",
            "note": "Synthetic note: after treatment, breathing is easier, oxygen requirement has fallen, blood pressure is stable, and the patient appears comfortable. The team documents clear clinical improvement.",
        },
    ]

    outputs = []
    for case in cases:
        prompt = build_prompt(case["note"])
        inputs = processor.apply_chat_template(
            [{"role": "user", "content": prompt}],
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
            generated = model.generate(**inputs, max_new_tokens=args.max_new_tokens)
        sequences = getattr(generated, "sequences", generated)
        if sequences.ndim != 2 or sequences.shape[0] != 1:
            raise RuntimeError(f"Unexpected generated sequence shape: {tuple(sequences.shape)}")
        completion_ids = sequences[0, input_len:].detach().cpu().tolist()
        decoded = processor.tokenizer.decode(completion_ids, skip_special_tokens=True)
        scores = extract_scores(decoded)
        outputs.append({"case": case["name"], "scores": scores, "decoded_tail": decoded[-3000:]})

    by_case = {x["case"]: x["scores"] for x in outputs}
    all_values = [v for row in outputs for v in row["scores"].values()]
    unique_values = sorted(set(all_values))
    intermediate_values = [v for v in all_values if 0.0 < v < 1.0]

    respiratory_sequence = [
        by_case["respiratory_mild"]["respiratory_concern"],
        by_case["respiratory_moderate"]["respiratory_concern"],
        by_case["respiratory_severe"]["respiratory_concern"],
    ]
    hemodynamic_sequence = [
        by_case["hemodynamic_mild"]["hemodynamic_concern"],
        by_case["hemodynamic_moderate"]["hemodynamic_concern"],
        by_case["hemodynamic_severe"]["hemodynamic_concern"],
    ]

    checks = {
        "respiratory_non_decreasing": respiratory_sequence == sorted(respiratory_sequence),
        "hemodynamic_non_decreasing": hemodynamic_sequence == sorted(hemodynamic_sequence),
        "stable_reassuring": by_case["stable"]["reassuring_stability"] > by_case["stable"]["overall_clinician_concern"],
        "severe_resp_high_concern": by_case["respiratory_severe"]["respiratory_concern"] >= 0.75,
        "severe_hemo_high_concern": by_case["hemodynamic_severe"]["hemodynamic_concern"] >= 0.75,
        "uncertainty_case_highest_uncertainty_vs_stable": by_case["diagnostic_uncertainty"]["diagnostic_uncertainty"] > by_case["stable"]["diagnostic_uncertainty"],
        "poor_response_case_above_stable": by_case["poor_treatment_response"]["poor_treatment_response"] > by_case["stable"]["poor_treatment_response"],
    }

    per_construct_unique = {
        name: sorted(set(row["scores"][name] for row in outputs))
        for name in EXPECTED
    }

    report = {
        "analysis": "Native Hugging Face DiffusionGemma graded synthetic semantic calibration",
        "status": "completed",
        "synthetic_only": True,
        "clinical_note_inference_performed": False,
        "network_required": False,
        "model": "google/diffusiongemma-26B-A4B-it",
        "backend": "transformers_native_bf16",
        "prompt_identical_to_initial_smoke": True,
        "score_definition": "Prompted zero-shot 0-1 support scores; not Jev noul probabilities.",
        "torch_version": torch.__version__,
        "torch_cuda_version": torch.version.cuda,
        "transformers_version": transformers.__version__,
        "seed": args.seed,
        "outputs": outputs,
        "global_unique_score_values": unique_values,
        "intermediate_value_count": len(intermediate_values),
        "total_score_count": len(all_values),
        "intermediate_value_fraction": len(intermediate_values) / len(all_values),
        "per_construct_unique_values": per_construct_unique,
        "respiratory_concern_sequence_mild_moderate_severe": respiratory_sequence,
        "hemodynamic_concern_sequence_mild_moderate_severe": hemodynamic_sequence,
        "sanity_checks": checks,
        "all_sanity_checks_passed": all(checks.values()),
        "graded_resolution_present": len(intermediate_values) > 0,
        "interpretation_gate": (
            "If graded_resolution_present is false or resolution is extremely coarse, do not treat these as continuous Jev-like scores; "
            "consider an alternate native scoring extraction before clinical inference."
        ),
    }
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
