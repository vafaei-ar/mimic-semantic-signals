from __future__ import annotations

import argparse
import json
from pathlib import Path


DEFAULT_MODEL = "com-kotobalabs/open-jev-deberta-v3-large"


def load_cases(path: Path) -> list[dict]:
    cases = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            case = json.loads(line)
            model_state = case.get("model_state", {})
            if not isinstance(model_state, dict) or not model_state.get("clinical_note"):
                raise RuntimeError(
                    "Each case must contain model_state.clinical_note."
                )
            cases.append(case)
    return cases


def local_questions(case: dict) -> tuple[list[str], list[dict]]:
    names = []
    questions = []
    for q in case["questions"]:
        if q.get("type") != "noul":
            raise ValueError("Current local runner supports noul questions only.")
        instruction = str(q["question"])
        criteria = q.get("criteria")
        if isinstance(criteria, dict):
            instruction += (
                "\nTrue criterion: " + str(criteria.get("true", "")) +
                "\nFalse criterion: " + str(criteria.get("false", ""))
            )
        names.append(str(q["name"]))
        questions.append(
            {
                "type": "noul",
                "instructions": instruction,
            }
        )
    return names, questions


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Run the open Jev-shaped DeBERTa model locally."
    )
    ap.add_argument("--cases", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument(
        "--device",
        default=None,
        help="Optional torch device such as cuda, cpu, or mps. Default is automatic.",
    )
    args = ap.parse_args()

    # Import only after CLI parsing so --help works without the optional dependency.
    from typed_decisions.open_jev import OpenJev

    cases = load_cases(Path(args.cases).expanduser().resolve())
    if args.limit > 0:
        cases = cases[: args.limit]
    if not cases:
        raise RuntimeError("No cases found.")

    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    print(f"Loading local model: {args.model}")
    model = OpenJev.from_pretrained(args.model, device=args.device)
    print(f"Device: {model.device}")
    print(
        "Model context limits: "
        f"state={model.config.get('max_state_tokens', 256)} tokens; "
        f"total={model.config.get('max_len', 512)} tokens"
    )

    completed = 0
    with output.open("w", encoding="utf-8") as f:
        for case in cases:
            names, questions = local_questions(case)
            # Deliberately expose only clinical_note to the local model.
            state = str(case["model_state"]["clinical_note"])
            answers = model.decide(state, questions)
            response = {
                "answers": {
                    name: answer for name, answer in zip(names, answers)
                }
            }
            record = {
                "case_id": case.get("case_id"),
                "synthetic_only": case.get("synthetic_only"),
                "model_state": case.get("model_state", {}),
                "metadata": case.get("metadata", {}),
                "gold": case.get("gold"),
                "model": args.model,
                "backend": "open_jev_local",
                "response": response,
                "status": "ok",
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            f.flush()
            completed += 1

    print(
        json.dumps(
            {
                "cases_attempted": len(cases),
                "completed": completed,
                "failed": 0,
                "backend": "open_jev_local",
                "model": args.model,
                "output": str(output),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
