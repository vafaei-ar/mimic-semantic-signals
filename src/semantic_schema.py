from __future__ import annotations

SEMANTIC_CONSTRUCTS = [
    {
        "name": "overall_clinician_concern",
        "type": "noul",
        "question": (
            "Does `clinical_note` indicate that the clinician is concerned that "
            "the patient's overall clinical condition is worsening or may worsen soon?"
        ),
        "criteria": {
            "true": "The note communicates a meaningful current concern about deterioration or impending worsening.",
            "false": "The note is reassuring, neutral, or does not communicate concern about deterioration.",
        },
    },
    {
        "name": "worsening_trajectory",
        "type": "noul",
        "question": (
            "Does `clinical_note` describe a worsening clinical trajectory compared "
            "with an earlier assessment or expected course?"
        ),
        "criteria": {
            "true": "The note explicitly or clearly implies that the patient's trajectory is getting worse.",
            "false": "The note describes stability, improvement, or no clear worsening trajectory.",
        },
    },
    {
        "name": "respiratory_concern",
        "type": "noul",
        "question": (
            "Does `clinical_note` express concern about respiratory deterioration, "
            "increasing work of breathing, respiratory fatigue, oxygenation, or need "
            "for more respiratory support?"
        ),
        "criteria": {
            "true": "A respiratory problem is presented as clinically concerning or worsening.",
            "false": "Respiratory status is reassuring, unchanged, or not a meaningful concern in the note.",
        },
    },
    {
        "name": "hemodynamic_concern",
        "type": "noul",
        "question": (
            "Does `clinical_note` express concern about circulatory or hemodynamic "
            "deterioration, perfusion, hypotension, shock, or possible need for "
            "vasoactive support?"
        ),
        "criteria": {
            "true": "The note communicates meaningful concern about circulation, perfusion, or hemodynamic instability.",
            "false": "Hemodynamics are reassuring, unchanged, or not a meaningful concern in the note.",
        },
    },
    {
        "name": "poor_treatment_response",
        "type": "noul",
        "question": (
            "Does `clinical_note` indicate that the patient is not responding as "
            "expected to current treatment or support?"
        ),
        "criteria": {
            "true": "The note indicates inadequate, incomplete, or disappointing response to treatment or support.",
            "false": "The note indicates adequate response, expected course, or gives no evidence of poor response.",
        },
    },
    {
        "name": "escalation_considered",
        "type": "noul",
        "question": (
            "Does `clinical_note` indicate that escalation of monitoring, treatment, "
            "respiratory support, vasoactive support, or level of care is being considered?"
        ),
        "criteria": {
            "true": "The note states or clearly implies that stronger monitoring, treatment, support, or level of care is being considered.",
            "false": "No escalation is being considered, or the note supports continuing the current plan without escalation.",
        },
    },
    {
        "name": "diagnostic_uncertainty",
        "type": "noul",
        "question": (
            "Does `clinical_note` indicate meaningful unresolved diagnostic uncertainty "
            "that affects current clinical management?"
        ),
        "criteria": {
            "true": "The note describes unresolved diagnostic uncertainty that is clinically consequential.",
            "false": "There is no meaningful unresolved diagnostic uncertainty affecting management.",
        },
    },
    {
        "name": "reassuring_stability",
        "type": "noul",
        "question": (
            "Does `clinical_note` explicitly indicate that the patient's clinical "
            "condition is stable or reassuring without a new acute concern?"
        ),
        "criteria": {
            "true": "The note is explicitly reassuring or describes stable clinical status without a new acute concern.",
            "false": "The note communicates deterioration, concern, uncertainty, or does not clearly support reassuring stability.",
        },
    },
]
