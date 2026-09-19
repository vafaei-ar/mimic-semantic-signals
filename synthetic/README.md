# Synthetic MIMIC-III semantic-signals sandbox

This sandbox is for development only. It contains no source clinical text and no patient-level records from MIMIC.

## What is structurally matched

The generator creates a MIMIC-III 1.4-compatible study subset with the same column names and column order as the local tables used by this project:

- ADMISSIONS
- ICUSTAYS
- NOTEEVENTS
- D_ITEMS
- D_LABITEMS
- CHARTEVENTS
- LABEVENTS
- INPUTEVENTS_MV
- INPUTEVENTS_CV
- PROCEDUREEVENTS_MV

Foreign-key relationships use the same SUBJECT_ID -> HADM_ID -> ICUSTAY_ID hierarchy. Timestamps, note categories, CareVue/MetaVision source labels, vital-sign events, laboratory events, vasopressor starts, and intubation procedures are represented in MIMIC-like locations.

The content is not intended to reproduce real MIMIC distributions. It is a controlled test fixture.

## Scientific signal embedded in the synthetic data

Admissions are assigned one of four trajectories:

- no major deterioration
- vasopressor initiation
- intubation
- in-hospital death

For event admissions, narrative concern begins before the structured physiologic deterioration. A subset is explicitly generated as narrative-physiology discordant: bedside concern becomes high while structured measurements remain relatively reassuring until close to the event.

This gives us known ground truth for testing the proposed "hidden clinician concern" pipeline.

## Generate the sandbox

From the repository root:

    python run_synthetic_demo.py       --output-root data/synthetic_mimic       --n-admissions 500

This creates:

    data/synthetic_mimic/
    ├── mimiciii/1.4/
    │   ├── ADMISSIONS.csv.gz
    │   ├── ICUSTAYS.csv.gz
    │   ├── NOTEEVENTS.csv.gz
    │   ├── D_ITEMS.csv.gz
    │   ├── D_LABITEMS.csv.gz
    │   ├── CHARTEVENTS.csv.gz
    │   ├── LABEVENTS.csv.gz
    │   ├── INPUTEVENTS_MV.csv.gz
    │   ├── INPUTEVENTS_CV.csv.gz
    │   └── PROCEDUREEVENTS_MV.csv.gz
    ├── synthetic_truth.csv
    ├── synthetic_manifest.json
    ├── semantic_eval_cases_24h.jsonl
    └── semantic_eval_cases_24h.summary.json

The JSONL file is provider-neutral. It contains the state, eight semantic questions, and hidden synthetic truth. A Jev-specific adapter can consume it without changing the data-extraction pipeline.

## Verify against the exact local MIMIC headers

Run:

    python synthetic/validate_against_local_headers.py       --real-root ~/datasets/MIMIC/physionet.org/files       --synthetic-root data/synthetic_mimic       --output outputs/synthetic_schema_check.csv

The validator reads only table headers from the real local MIMIC files. It does not read or export patient rows or clinical text.

Every included table should report:

    same_column_names = True
    same_column_order = True

If a local table differs, we should update the synthetic schema before building further pipeline code.

## Important limitation

This synthetic sandbox validates software behavior and study logic. It cannot establish performance on real clinical language or real clinical outcomes. Final scientific results must come from the credentialed dataset under an approved data-processing configuration.
