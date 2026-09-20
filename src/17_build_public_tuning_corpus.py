from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path


OOD_INSTRUCTIONS = {
    "overall_clinician_concern": "Based only on the clinical note, is there meaningful concern that the patient's condition is deteriorating or may deteriorate?",
    "worsening_trajectory": "Does the clinical note indicate that the patient's course is getting worse rather than remaining stable or improving?",
    "respiratory_concern": "Is a worsening breathing or oxygenation problem a meaningful concern in this clinical note?",
    "hemodynamic_concern": "Is the clinical note meaningfully concerned about circulation, perfusion, blood pressure, shock, or vasoactive support?",
    "poor_treatment_response": "Does the clinical note indicate inadequate response to the treatment or support already being given?",
    "escalation_considered": "Does the note suggest that the team is considering stronger monitoring, treatment, support, or a higher level of care?",
    "diagnostic_uncertainty": "Does unresolved diagnostic uncertainty materially affect management in the clinical note?",
    "reassuring_stability": "Does the clinical note clearly describe a stable or reassuring condition without a new acute concern?",
}


def admission_group(case_id: str) -> str:
    parts = str(case_id).split("_")
    if len(parts) < 3 or parts[0] != "syn":
        raise ValueError(f"Unexpected synthetic case_id: {case_id}")
    return parts[1]


def instruction(q: dict) -> str:
    text = str(q["question"])
    criteria = q.get("criteria")
    if isinstance(criteria, dict):
        text += (
            "\nTrue criterion: " + str(criteria.get("true", "")) +
            "\nFalse criterion: " + str(criteria.get("false", ""))
        )
    return text


def typed_examples(
    case: dict,
    ood: bool = False,
    questions_per_pack: int = 4,
) -> list[dict]:
    qs = []
    golds = case["gold"]["constructs"]
    for q in case["questions"]:
        name = q["name"]
        instr = OOD_INSTRUCTIONS[name] if ood else instruction(q)
        qs.append(
            {
                "qid": name,
                "kind": "noul",
                "instructions": instr,
                "options": ["no", "yes"],
                "gold": int(golds[name]),
            }
        )

    rows = []
    for pack_index, i in enumerate(range(0, len(qs), questions_per_pack)):
        pack = qs[i:i + questions_per_pack]
        rows.append(
            {
                "state": str(case["model_state"]["clinical_note"]),
                "source": (
                    "synthetic_clinical_semantics_ood"
                    if ood
                    else "synthetic_clinical_semantics"
                ),
                "meta": {
                    "case_id": case["case_id"],
                    "group": admission_group(case["case_id"]),
                    "event_type": case.get("gold", {}).get("event_type"),
                    "discordant": case.get("gold", {}).get("discordant"),
                    "pack_index": pack_index,
                    "questions_in_pack": len(pack),
                },
                "questions": pack,
            }
        )
    return rows


def sft_example(case: dict) -> dict:
    questions = []
    golds = case["gold"]["constructs"]
    for q in case["questions"]:
        questions.append(
            {
                "id": q["name"],
                "instructions": instruction(q),
            }
        )
    target = {name: bool(value) for name, value in golds.items()}
    prompt = {
        "state": {"clinical_note": case["model_state"]["clinical_note"]},
        "questions": questions,
    }
    return {
        "case_id": case["case_id"],
        "messages": [
            {
                "role": "user",
                "content": (
                    "Evaluate each clinical question using only the supplied note. "
                    "Return one JSON object mapping question ids to true or false.\n"
                    + json.dumps(prompt, ensure_ascii=False)
                ),
            },
            {
                "role": "assistant",
                "content": json.dumps(target, ensure_ascii=False, sort_keys=True),
            },
        ],
    }


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--seed", type=int, default=20260919)
    ap.add_argument("--train-frac", type=float, default=0.70)
    ap.add_argument("--val-frac", type=float, default=0.15)
    ap.add_argument("--questions-per-pack", type=int, default=4)
    args = ap.parse_args()

    src = Path(args.cases).expanduser().resolve()
    out = Path(args.output_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)

    cases = []
    with src.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            case = json.loads(line)
            if case.get("synthetic_only") is not True:
                raise RuntimeError(
                    "Public tuning-corpus builder refuses any case not marked synthetic_only=true."
                )
            if "model_state" not in case:
                raise RuntimeError(
                    "Rebuild cases with the current pipeline; model_state is required."
                )
            cases.append(case)

    groups = sorted({admission_group(c["case_id"]) for c in cases})
    rng = random.Random(args.seed)
    rng.shuffle(groups)

    n = len(groups)
    n_train = int(n * args.train_frac)
    n_val = int(n * args.val_frac)
    train_g = set(groups[:n_train])
    val_g = set(groups[n_train:n_train + n_val])
    test_g = set(groups[n_train + n_val:])

    split_rows = {"train": [], "val": [], "test": []}
    split_sft = {"train": [], "val": [], "test": []}

    for case in cases:
        g = admission_group(case["case_id"])
        split = "train" if g in train_g else ("val" if g in val_g else "test")
        split_rows[split].extend(\n            typed_examples(\n                case,\n                ood=False,\n                questions_per_pack=args.questions_per_pack,\n            )\n        )
        split_sft[split].append(sft_example(case))

    for split in ("train", "val", "test"):
        write_jsonl(out / f"{split}.jsonl", split_rows[split])
        write_jsonl(out / f"diffusiongemma_{split}.jsonl", split_sft[split])

    ood = []
    for c in cases:
        if admission_group(c["case_id"]) in test_g:
            ood.extend(
                typed_examples(
                    c,
                    ood=True,
                    questions_per_pack=args.questions_per_pack,
                )
            )
    write_jsonl(out / "ood-test.jsonl", ood)

    fingerprint = hashlib.sha256(src.read_bytes()).hexdigest()
    summary = {
        "source_file": str(src),
        "source_sha256": fingerprint,
        "synthetic_only": True,
        "seed": args.seed,
        "groups": {
            "train": len(train_g),
            "val": len(val_g),
            "test": len(test_g),
        },
        "states": {
            "train": len(split_rows["train"]),
            "val": len(split_rows["val"]),
            "test": len(split_rows["test"]),
            "ood_test": len(ood),
        },
        "questions_per_original_case": 8,\n        "open_jev_questions_per_pack": args.questions_per_pack,
        "warning": (
            "This corpus is suitable for pipeline development only until the "
            "synthetic note generator has substantially more independent template families."
        ),
    }
    (out / "manifest.json").write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
