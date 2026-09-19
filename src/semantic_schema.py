from __future__ import annotations

SEMANTIC_CONSTRUCTS = [
    {
        "name": "overall_clinician_concern",
        "type": "noul",
        "question": "Does the note indicate that the clinician is concerned that the patient's overall clinical condition is worsening or may worsen soon?",
    },
    {
        "name": "worsening_trajectory",
        "type": "noul",
        "question": "Does the note describe a worsening clinical trajectory compared with an earlier assessment?",
    },
    {
        "name": "respiratory_concern",
        "type": "noul",
        "question": "Does the note express concern about respiratory deterioration, increasing work of breathing, fatigue, oxygenation, or need for more respiratory support?",
    },
    {
        "name": "hemodynamic_concern",
        "type": "noul",
        "question": "Does the note express concern about circulatory or hemodynamic deterioration, perfusion, hypotension, shock, or possible need for vasoactive support?",
    },
    {
        "name": "poor_treatment_response",
        "type": "noul",
        "question": "Does the note indicate that the patient is not responding as expected to current treatment or support?",
    },
    {
        "name": "escalation_considered",
        "type": "noul",
        "question": "Does the note indicate that escalation of monitoring, treatment, respiratory support, vasoactive support, or level of care is being considered?",
    },
    {
        "name": "diagnostic_uncertainty",
        "type": "noul",
        "question": "Does the note indicate meaningful unresolved diagnostic uncertainty that affects current clinical management?",
    },
    {
        "name": "reassuring_stability",
        "type": "noul",
        "question": "Does the note explicitly indicate that the patient's clinical condition is stable or reassuring without a new acute concern?",
    },
]
