from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path

from semantic_schema import SEMANTIC_CONSTRUCTS


# Each family uses distinct label-bearing language. Whole families, not just
# admissions, are held out from training.
FAMILIES = {
    "train_direct": {
        "concern_pos": ["The team is concerned about the patient's condition.", "There is clear clinical concern at the bedside."],
        "concern_neg": ["The team has no new clinical concern.", "There is no current concern for deterioration."],
        "worsening_pos": ["The patient looks worse than on the prior assessment.", "The clinical course is worsening."],
        "worsening_neg": ["The condition has not worsened since the prior assessment.", "No interval deterioration is seen."],
        "resp_pos": ["Work of breathing is increased and respiratory decline is a concern.", "Breathing is more labored and respiratory support may be needed."],
        "resp_neg": ["Breathing remains comfortable without respiratory concern.", "No increase in work of breathing is present."],
        "hemo_pos": ["Perfusion appears poor and hemodynamic instability is a concern.", "Circulatory status is concerning with possible evolving shock."],
        "hemo_neg": ["Perfusion remains adequate without hemodynamic concern.", "There is no evidence of circulatory instability."],
        "response_pos": ["The patient has not responded as expected to treatment.", "Response to the current treatment remains inadequate."],
        "response_neg": ["The patient is responding appropriately to treatment.", "Current treatment is having the expected effect."],
        "escalation_pos": ["The team is considering escalation of care.", "A higher level of support is being discussed."],
        "escalation_neg": ["No escalation of care is being considered.", "The current level of support remains appropriate."],
        "uncertainty_pos": ["The diagnosis remains unclear and this uncertainty affects management.", "The cause of the change is unresolved and is altering the plan."],
        "uncertainty_neg": ["The working diagnosis is clear enough to guide management.", "There is no meaningful diagnostic uncertainty at present."],
        "stable_pos": ["The patient remains clinically stable and reassuring.", "Overall status is stable without a new acute issue."],
    },
    "train_reassessment": {
        "concern_pos": ["Reassessment raises concern that the patient may deteriorate.", "Bedside reassessment is worrisome despite limited objective change."],
        "concern_neg": ["Reassessment is reassuring and raises no new concern.", "Repeat assessment does not suggest impending deterioration."],
        "worsening_pos": ["Compared with earlier, the patient is doing less well.", "There has been a downward change from the earlier examination."],
        "worsening_neg": ["Compared with earlier, the patient is unchanged.", "The trajectory remains flat rather than declining."],
        "resp_pos": ["Respiratory effort has increased and the patient appears to be tiring.", "The breathing pattern is becoming less sustainable."],
        "resp_neg": ["Respiratory effort is unchanged and non-labored.", "The breathing pattern remains reassuring."],
        "hemo_pos": ["Cool extremities and weaker perfusion raise concern for circulatory compromise.", "The bedside examination suggests developing hemodynamic compromise."],
        "hemo_neg": ["Extremities remain warm with preserved perfusion.", "The bedside examination does not suggest hemodynamic compromise."],
        "response_pos": ["There has been little benefit from the intervention so far.", "The expected improvement after treatment has not occurred."],
        "response_neg": ["The intervention produced the expected improvement.", "The patient improved appropriately after treatment."],
        "escalation_pos": ["Additional support is being considered if the trend continues.", "The team is discussing whether closer monitoring or stronger support is needed."],
        "escalation_neg": ["Additional support is not thought necessary at this time.", "The team plans to continue the present level of monitoring."],
        "uncertainty_pos": ["The reason for the change is still uncertain and different causes are being considered.", "The etiology remains unresolved enough to change the workup."],
        "uncertainty_neg": ["The reason for the current findings is understood.", "The etiology is sufficiently established for the present plan."],
        "stable_pos": ["Repeat examination remains reassuring.", "The patient continues to look clinically unchanged and stable."],
    },
    "train_handoff": {
        "concern_pos": ["Handoff: watch closely because there is meaningful concern for deterioration.", "Handoff: clinical concern is increasing."],
        "concern_neg": ["Handoff: no active deterioration concern.", "Handoff: current condition is reassuring."],
        "worsening_pos": ["Handoff: status has been declining over the shift.", "Handoff: trajectory is worse than at the start of the shift."],
        "worsening_neg": ["Handoff: no decline over the shift.", "Handoff: trajectory has remained unchanged."],
        "resp_pos": ["Handoff: breathing is becoming more difficult and respiratory deterioration is a concern.", "Handoff: respiratory reserve appears to be decreasing."],
        "resp_neg": ["Handoff: respiratory status has remained comfortable.", "Handoff: no respiratory deterioration is evident."],
        "hemo_pos": ["Handoff: perfusion is becoming concerning and circulatory support may be needed.", "Handoff: there is concern for emerging hemodynamic instability."],
        "hemo_neg": ["Handoff: circulation remains adequate.", "Handoff: no hemodynamic instability has been identified."],
        "response_pos": ["Handoff: limited response to treatment so far.", "Handoff: the current intervention has not achieved the intended effect."],
        "response_neg": ["Handoff: treatment response has been satisfactory.", "Handoff: current intervention achieved the intended effect."],
        "escalation_pos": ["Handoff: escalation options have been discussed.", "Handoff: be prepared for a higher level of support."],
        "escalation_neg": ["Handoff: escalation is not currently planned.", "Handoff: no higher level of support is anticipated."],
        "uncertainty_pos": ["Handoff: the underlying cause remains uncertain and is affecting decisions.", "Handoff: unresolved diagnostic possibilities remain clinically important."],
        "uncertainty_neg": ["Handoff: the diagnosis is not in meaningful doubt.", "Handoff: diagnostic uncertainty is not affecting decisions."],
        "stable_pos": ["Handoff: clinically stable with no new acute concern.", "Handoff: current status is reassuring."],
    },
    "train_indirect": {
        "concern_pos": ["The bedside appearance warrants closer attention.", "The current examination is more worrisome than the numbers alone suggest."],
        "concern_neg": ["Nothing on the current examination warrants additional concern.", "The bedside appearance is reassuring."],
        "worsening_pos": ["The patient is moving in the wrong direction clinically.", "The overall course is trending unfavorably."],
        "worsening_neg": ["The overall course is not trending downward.", "There is no adverse change in the clinical trajectory."],
        "resp_pos": ["The patient is using more effort to breathe and has less respiratory reserve.", "Breathing has become harder to sustain."],
        "resp_neg": ["Respiratory reserve appears preserved.", "Breathing remains easy without signs of fatigue."],
        "hemo_pos": ["Clinical signs point to reduced effective circulation.", "The examination suggests that perfusion may be failing."],
        "hemo_neg": ["Clinical signs support preserved circulation.", "Perfusion appears intact."],
        "response_pos": ["The current approach is not accomplishing what was intended.", "Support has produced less improvement than expected."],
        "response_neg": ["The current approach is accomplishing its intended effect.", "Support has produced the expected improvement."],
        "escalation_pos": ["The present plan may need to be intensified.", "A more intensive level of care is under consideration."],
        "escalation_neg": ["There is no reason to intensify the present plan.", "A more intensive level of care is not under consideration."],
        "uncertainty_pos": ["Several explanations remain plausible and the distinction matters for treatment.", "The clinical picture has not yet been explained well enough to settle management."],
        "uncertainty_neg": ["One working explanation adequately accounts for the findings.", "The clinical picture is sufficiently explained for management."],
        "stable_pos": ["The overall picture remains reassuring.", "The current examination supports continued stability."],
    },
    "val_compact": {
        "concern_pos": ["Clinically worrisome appearance.", "Meaningful concern for near-term decline."],
        "concern_neg": ["No meaningful deterioration concern.", "Current appearance is reassuring."],
        "worsening_pos": ["Interval decline is present.", "Course is deteriorating."],
        "worsening_neg": ["No interval decline.", "Course is not deteriorating."],
        "resp_pos": ["Increasing respiratory effort with reduced reserve.", "Respiratory deterioration is suspected."],
        "resp_neg": ["Respiratory effort is normal and unchanged.", "No respiratory deterioration is suspected."],
        "hemo_pos": ["Findings suggest impaired perfusion.", "Hemodynamic deterioration is suspected."],
        "hemo_neg": ["Perfusion remains preserved.", "No hemodynamic deterioration is suspected."],
        "response_pos": ["Treatment effect is insufficient.", "Current therapy has not produced adequate improvement."],
        "response_neg": ["Treatment effect is adequate.", "Current therapy produced adequate improvement."],
        "escalation_pos": ["Escalated support is under consideration.", "Higher-acuity management is being considered."],
        "escalation_neg": ["Escalated support is not under consideration.", "Higher-acuity management is not planned."],
        "uncertainty_pos": ["Etiology remains unresolved and management-relevant.", "Diagnostic ambiguity is affecting management."],
        "uncertainty_neg": ["Etiology is sufficiently established.", "No management-relevant diagnostic ambiguity remains."],
        "stable_pos": ["Condition is stable and reassuring.", "No new acute issue; status remains stable."],
    },
    "test_narrative": {
        "concern_pos": ["At the bedside, the overall picture gives reason to worry about further decline.", "The examination conveys more risk than a routine stable assessment."],
        "concern_neg": ["At the bedside, the overall picture does not raise concern for decline.", "The examination remains comfortably within the expected course."],
        "worsening_pos": ["The patient has lost ground since the last review.", "The course has shifted toward deterioration."],
        "worsening_neg": ["The patient has not lost ground since the last review.", "The course has not shifted toward deterioration."],
        "resp_pos": ["Breathing is increasingly taxing and the patient seems to have less reserve.", "Ventilatory effort is rising and fatigue is becoming a concern."],
        "resp_neg": ["Breathing remains effortless with preserved reserve.", "Ventilatory effort is not increasing and fatigue is not evident."],
        "hemo_pos": ["The circulation appears less effective, with bedside signs of compromised perfusion.", "Perfusion findings raise concern that cardiovascular support may become necessary."],
        "hemo_neg": ["The circulation appears effective with reassuring perfusion.", "Perfusion findings do not suggest a need for cardiovascular support."],
        "response_pos": ["Despite the intervention, the clinical problem has changed little.", "The treatment has yielded less benefit than anticipated."],
        "response_neg": ["The intervention has improved the clinical problem as anticipated.", "The treatment has yielded the anticipated benefit."],
        "escalation_pos": ["The team is weighing a move to more intensive support.", "More aggressive monitoring or support is being actively considered."],
        "escalation_neg": ["The team is not weighing a move to more intensive support.", "More aggressive monitoring or support is not being considered."],
        "uncertainty_pos": ["It is still unclear which process is driving the findings, and that uncertainty changes the next step.", "Competing explanations remain open and lead to different management choices."],
        "uncertainty_neg": ["The process driving the findings is sufficiently clear for the next step.", "Competing explanations are not materially changing management."],
        "stable_pos": ["The patient remains on a reassuring, steady course.", "The clinical picture is steady without an acute concern."],
    },
    "test_clinician_style": {
        "concern_pos": ["Assessment: overall appearance is concerning for decompensation.", "Assessment: bedside findings raise concern for further clinical decline."],
        "concern_neg": ["Assessment: no concern for decompensation at present.", "Assessment: bedside findings are reassuring."],
        "worsening_pos": ["Assessment: clear negative change from prior examination.", "Assessment: clinical trajectory has declined."],
        "worsening_neg": ["Assessment: no negative change from prior examination.", "Assessment: clinical trajectory has not declined."],
        "resp_pos": ["Assessment: increased ventilatory demand with concern for respiratory failure.", "Assessment: progressive breathing difficulty with limited respiratory reserve."],
        "resp_neg": ["Assessment: ventilatory demand remains unchanged.", "Assessment: no evidence of progressive breathing difficulty."],
        "hemo_pos": ["Assessment: signs of compromised perfusion raise concern for hemodynamic failure.", "Assessment: circulation appears tenuous with possible need for vasoactive support."],
        "hemo_neg": ["Assessment: perfusion is preserved without evidence of hemodynamic failure.", "Assessment: circulation is not tenuous and vasoactive support is not indicated."],
        "response_pos": ["Assessment: inadequate clinical response to current therapy.", "Assessment: expected therapeutic response has not occurred."],
        "response_neg": ["Assessment: adequate clinical response to current therapy.", "Assessment: expected therapeutic response has occurred."],
        "escalation_pos": ["Plan: consider transfer to a higher level of monitoring or support.", "Plan: escalation of support remains an active option."],
        "escalation_neg": ["Plan: no transfer to higher-acuity monitoring is indicated.", "Plan: escalation of support is not an active option."],
        "uncertainty_pos": ["Assessment: unresolved diagnostic possibilities remain important to management.", "Assessment: diagnostic uncertainty persists and is directing additional evaluation."],
        "uncertainty_neg": ["Assessment: diagnostic possibilities are sufficiently resolved for management.", "Assessment: no consequential diagnostic uncertainty remains."],
        "stable_pos": ["Assessment: clinically stable without a new acute issue.", "Assessment: reassuring stability on the current plan."],
    },
}

SPLIT_FAMILIES = {
    "train": ["train_direct", "train_reassessment", "train_handoff", "train_indirect"],
    "val": ["val_compact"],
    "test": ["test_narrative", "test_clinician_style"],
}

OOD_PARAPHRASES = {
    "overall_clinician_concern": [
        "Does the note convey meaningful concern about deterioration?",
        "Would a clinician reading this note regard the patient's current condition as concerning?",
        "Is the documented clinical picture worrisome rather than reassuring?",
    ],
    "worsening_trajectory": [
        "Does the note indicate a downward clinical trajectory?",
        "Has the patient's course deteriorated relative to the earlier assessment?",
        "Is there evidence in the note that the patient is getting clinically worse?",
    ],
    "respiratory_concern": [
        "Is worsening respiratory status a meaningful concern in this note?",
        "Does the note suggest declining breathing reserve or need for respiratory support?",
        "Is respiratory deterioration documented as an active problem?",
    ],
    "hemodynamic_concern": [
        "Does the note suggest clinically important circulatory or perfusion compromise?",
        "Is hemodynamic deterioration an active concern in the note?",
        "Does the documentation raise concern for shock or need for vasoactive support?",
    ],
    "poor_treatment_response": [
        "Does the note say that treatment has produced less benefit than expected?",
        "Is there evidence of inadequate response to the current intervention?",
        "Does the documentation indicate that the present therapy is not working well enough?",
    ],
    "escalation_considered": [
        "Is a higher level of monitoring, treatment, or support being considered?",
        "Does the note indicate possible escalation beyond the current care plan?",
        "Is the team considering intensifying care?",
    ],
    "diagnostic_uncertainty": [
        "Does unresolved diagnostic uncertainty materially affect management?",
        "Are competing diagnoses still important enough to change the care plan?",
        "Does the note indicate that uncertainty about the cause is influencing decisions?",
    ],
    "reassuring_stability": [
        "Does the note clearly describe a stable and reassuring clinical state?",
        "Is the documentation reassuring without a new acute concern?",
        "Does the note support clinical stability rather than deterioration?",
    ],
}

NEGATED_QUESTIONS = {
    "overall_clinician_concern": "Does the note indicate that there is NO meaningful concern about deterioration?",
    "worsening_trajectory": "Does the note indicate that the patient's course is NOT worsening?",
    "respiratory_concern": "Does the note indicate that respiratory deterioration is NOT a meaningful concern?",
    "hemodynamic_concern": "Does the note indicate that hemodynamic deterioration is NOT a meaningful concern?",
    "poor_treatment_response": "Does the note indicate that treatment response is NOT inadequate?",
    "escalation_considered": "Does the note indicate that escalation of care is NOT being considered?",
    "diagnostic_uncertainty": "Does the note indicate that there is NO meaningful unresolved diagnostic uncertainty?",
    "reassuring_stability": "Does the note indicate that the patient's condition is NOT reassuringly stable?",
}

NEUTRAL = [
    "The patient was seen at the bedside.",
    "The current plan and overnight events were reviewed.",
    "The bedside examination was repeated.",
    "The team reviewed the interval course.",
    "Current medications and recent observations were reviewed.",
    "The patient remains under routine clinical observation.",
]


def instruction(q: dict) -> str:
    text = str(q["question"])
    criteria = q.get("criteria")
    if isinstance(criteria, dict):
        text += (
            "\nTrue criterion: " + str(criteria.get("true", "")) +
            "\nFalse criterion: " + str(criteria.get("false", ""))
        )
    return text


def scenario(index: int, rng: random.Random) -> dict[str, int]:
    # Deliberately break the strong correlations present in the v0 sandbox.
    patterns = [
        {},
        {"diagnostic_uncertainty": 1},
        {"overall_clinician_concern": 1},
        {"overall_clinician_concern": 1, "worsening_trajectory": 1},
        {"overall_clinician_concern": 1, "respiratory_concern": 1},
        {"overall_clinician_concern": 1, "respiratory_concern": 1, "worsening_trajectory": 1},
        {"overall_clinician_concern": 1, "hemodynamic_concern": 1},
        {"overall_clinician_concern": 1, "hemodynamic_concern": 1, "worsening_trajectory": 1},
        {"overall_clinician_concern": 1, "poor_treatment_response": 1},
        {"overall_clinician_concern": 1, "escalation_considered": 1},
        {"overall_clinician_concern": 1, "poor_treatment_response": 1, "escalation_considered": 1},
        {"overall_clinician_concern": 1, "worsening_trajectory": 1, "diagnostic_uncertainty": 1},
        {"overall_clinician_concern": 1, "respiratory_concern": 1, "poor_treatment_response": 1},
        {"overall_clinician_concern": 1, "hemodynamic_concern": 1, "escalation_considered": 1},
        {"overall_clinician_concern": 1, "respiratory_concern": 1, "hemodynamic_concern": 1},
    ]
    labels = {q["name"]: 0 for q in SEMANTIC_CONSTRUCTS}
    labels.update(patterns[index % len(patterns)])

    # Uncertainty is partly independent of physiologic concern.
    if rng.random() < 0.18:
        labels["diagnostic_uncertainty"] = 1 - labels["diagnostic_uncertainty"]

    concerning = any(
        labels[k]
        for k in [
            "overall_clinician_concern",
            "worsening_trajectory",
            "respiratory_concern",
            "hemodynamic_concern",
            "poor_treatment_response",
            "escalation_considered",
        ]
    )
    labels["reassuring_stability"] = int(not concerning)
    if labels["respiratory_concern"] or labels["hemodynamic_concern"]:
        labels["overall_clinician_concern"] = 1
        labels["reassuring_stability"] = 0
    return labels


def render_note(labels: dict[str, int], family: str, rng: random.Random) -> str:
    bank = FAMILIES[family]
    clauses = [rng.choice(NEUTRAL)]

    positive_map = {
        "overall_clinician_concern": "concern_pos",
        "worsening_trajectory": "worsening_pos",
        "respiratory_concern": "resp_pos",
        "hemodynamic_concern": "hemo_pos",
        "poor_treatment_response": "response_pos",
        "escalation_considered": "escalation_pos",
        "diagnostic_uncertainty": "uncertainty_pos",
        "reassuring_stability": "stable_pos",
    }
    negative_map = {
        "overall_clinician_concern": "concern_neg",
        "worsening_trajectory": "worsening_neg",
        "respiratory_concern": "resp_neg",
        "hemodynamic_concern": "hemo_neg",
        "poor_treatment_response": "response_neg",
        "escalation_considered": "escalation_neg",
        "diagnostic_uncertainty": "uncertainty_neg",
    }

    positives = [k for k, v in labels.items() if v and k in positive_map]
    rng.shuffle(positives)
    for key in positives:
        # Overall concern can be left implicit when organ-specific concern is present.
        if key == "overall_clinician_concern" and rng.random() < 0.35 and (
            labels["respiratory_concern"] or labels["hemodynamic_concern"]
        ):
            continue
        clauses.append(rng.choice(bank[positive_map[key]]))

    # Hard negatives: explicitly mention some absent concepts using negation or
    # reassuring language, so keyword presence alone is insufficient.
    negatives = [k for k, v in labels.items() if not v and k in negative_map]
    rng.shuffle(negatives)
    for key in negatives[: rng.randint(1, 3)]:
        clauses.append(rng.choice(bank[negative_map[key]]))

    rng.shuffle(clauses)
    return " ".join(clauses)


def typed_rows(
    case_id: str,
    note: str,
    labels: dict[str, int],
    family: str,
    question_mode: str,
    rng: random.Random,
    questions_per_pack: int,
) -> list[dict]:
    questions = []
    for q in SEMANTIC_CONSTRUCTS:
        name = q["name"]
        gold = int(labels[name])
        if question_mode == "canonical":
            instr = instruction(q)
            qid = name
        elif question_mode == "ood":
            instr = rng.choice(OOD_PARAPHRASES[name])
            qid = name
        elif question_mode == "negated":
            instr = NEGATED_QUESTIONS[name]
            qid = name
            gold = 1 - gold
        else:
            raise ValueError(question_mode)

        questions.append(
            {
                "qid": qid,
                "kind": "noul",
                "instructions": instr,
                "options": ["no", "yes"],
                "gold": gold,
            }
        )

    rows = []
    for pack_index, i in enumerate(range(0, len(questions), questions_per_pack)):
        pack = questions[i:i + questions_per_pack]
        rows.append(
            {
                "state": note,
                "source": f"public_clinical_semantics_v1_{question_mode}",
                "meta": {
                    "case_id": case_id,
                    "template_family": family,
                    "pack_index": pack_index,
                    "question_mode": question_mode,
                },
                "questions": pack,
            }
        )
    return rows


def diffusion_row(case_id: str, note: str, labels: dict[str, int]) -> dict:
    prompt = {
        "state": {"clinical_note": note},
        "questions": [
            {"id": q["name"], "instructions": instruction(q)}
            for q in SEMANTIC_CONSTRUCTS
        ],
    }
    return {
        "case_id": case_id,
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
                "content": json.dumps(
                    {k: bool(v) for k, v in labels.items()},
                    ensure_ascii=False,
                    sort_keys=True,
                ),
            },
        ],
    }


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--train-cases", type=int, default=12000)
    ap.add_argument("--val-cases", type=int, default=2000)
    ap.add_argument("--test-cases", type=int, default=4000)
    ap.add_argument("--questions-per-pack", type=int, default=4)
    ap.add_argument("--seed", type=int, default=20260920)
    args = ap.parse_args()

    out = Path(args.output_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)

    split_counts = {
        "train": args.train_cases,
        "val": args.val_cases,
        "test": args.test_cases,
    }
    typed = {"train": [], "val": [], "test": []}
    diffusion = {"train": [], "val": [], "test": []}
    canonical = {"train": [], "val": [], "test": []}
    ood = []
    negated = []

    global_index = 0
    label_counts = {split: {q["name"]: 0 for q in SEMANTIC_CONSTRUCTS} for split in split_counts}

    for split, n_cases in split_counts.items():
        families = SPLIT_FAMILIES[split]
        for local_index in range(n_cases):
            family = families[local_index % len(families)]
            labels = scenario(global_index, rng)
            note = render_note(labels, family, rng)
            case_id = f"pubv1_{split}_{global_index:06d}"
            global_index += 1

            for name, value in labels.items():
                label_counts[split][name] += int(value)

            canonical_case = {
                "case_id": case_id,
                "synthetic_only": True,
                "model_state": {"clinical_note": note},
                "metadata": {
                    "template_family": family,
                    "split": split,
                },
                "gold": {"constructs": labels},
                "questions": SEMANTIC_CONSTRUCTS,
            }
            canonical[split].append(canonical_case)
            typed[split].extend(
                typed_rows(
                    case_id,
                    note,
                    labels,
                    family,
                    "canonical",
                    rng,
                    args.questions_per_pack,
                )
            )
            diffusion[split].append(diffusion_row(case_id, note, labels))

            if split == "test":
                ood.extend(
                    typed_rows(
                        case_id,
                        note,
                        labels,
                        family,
                        "ood",
                        rng,
                        args.questions_per_pack,
                    )
                )
                negated.extend(
                    typed_rows(
                        case_id,
                        note,
                        labels,
                        family,
                        "negated",
                        rng,
                        args.questions_per_pack,
                    )
                )

    for split in ("train", "val", "test"):
        write_jsonl(out / f"canonical_{split}.jsonl", canonical[split])
        write_jsonl(out / f"{split}.jsonl", typed[split])
        write_jsonl(out / f"diffusiongemma_{split}.jsonl", diffusion[split])
    write_jsonl(out / "ood-test.jsonl", ood)
    write_jsonl(out / "negation-test.jsonl", negated)

    manifest = {
        "synthetic_only": True,
        "version": "public_clinical_semantics_v1",
        "seed": args.seed,
        "split_by_unseen_template_family": True,
        "template_families": SPLIT_FAMILIES,
        "original_cases": split_counts,
        "typed_packs": {k: len(v) for k, v in typed.items()},
        "ood_packs": len(ood),
        "negation_packs": len(negated),
        "questions_per_original_case": len(SEMANTIC_CONSTRUCTS),
        "questions_per_pack": args.questions_per_pack,
        "positive_label_counts": label_counts,
        "notes": [
            "Gold labels are sampled as latent semantics before text is rendered.",
            "No gold label is recovered by phrase matching.",
            "Test note-generation families are absent from training.",
            "Negative clauses explicitly mention absent concepts to create hard negatives.",
            "Diagnostic uncertainty has both positive and negative examples.",
            "Negation-test reverses question polarity and therefore reverses gold labels.",
        ],
    }
    payload = json.dumps(manifest, indent=2) + "\n"
    (out / "manifest.json").write_text(payload, encoding="utf-8")
    (out / "manifest.sha256").write_text(
        hashlib.sha256(payload.encode("utf-8")).hexdigest() + "\n",
        encoding="utf-8",
    )
    print(payload)


if __name__ == "__main__":
    main()
