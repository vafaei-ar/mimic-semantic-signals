# MIMIC Semantic Signals

This repository studies whether prospectively available ICU narrative documentation contains reusable information about near-term deterioration beyond structured physiology, and whether a small set of clinically interpretable semantic scores can provide useful low-dimensional compression of that narrative signal.

## Start here

The repository contains both a corrected **v2 manuscript-facing lineage** and an intentionally preserved **v1 provenance archive**.

Read these reports in order:

1. [01 — Read this first](docs/01_READ_FIRST.md)
2. [02 — Current scientific status](docs/02_CURRENT_SCIENTIFIC_STATUS.md)
3. [03 — Corrected v2 analysis lineage](docs/03_V2_ANALYSIS_LINEAGE.md)
4. [04 — v1 provenance and integrity hold](docs/04_V1_PROVENANCE_AND_HOLD.md)
5. [05 — External validation status](docs/05_EXTERNAL_VALIDATION_STATUS.md)
6. [06 — Post-review v2.1 correction gate](docs/06_POSTREVIEW_V2_1_CORRECTIONS.md)
7. [07 — Preregistration readiness checkpoint](docs/07_PREREGISTRATION_READINESS_2026-09-25.md)
8. [08 — Lancet Digital Health roadmap](docs/08_LANCET_DIGITAL_HEALTH_ROADMAP_2026-09-25.md)

Detailed frozen protocols and result documents under `docs/` remain authoritative for exact cohort definitions, item IDs, model settings, artifact hashes, and prespecified interpretation rules.

## Current stage

The corrected v2.1 confirmatory design is now **ready for human review and external OSF registration**. Real-label v2.1 predictive performance remains deliberately locked.

The final OSF review candidate is commit `c21b8db2f214e95b8f5b6e46e0e79e23426a9035`. Validation job `Z7M4Q8R2` completed successfully using synthetic/static checks only; it read no real clinical data and computed no real outcome performance.

The repository fails closed until a valid `docs/registration/osf_registration.json` is present. The immediate next step is human review and OSF submission, not another predictive analysis job.

See [07 — Preregistration readiness checkpoint](docs/07_PREREGISTRATION_READINESS_2026-09-25.md) and [08 — Lancet Digital Health roadmap](docs/08_LANCET_DIGITAL_HEALTH_ROADMAP_2026-09-25.md).

## Scientific framing

The study is not framed as “JEV beats LLMs.”

Open-Jev, Laya, and DiffusionGemma are semantic measurement instruments. The scientific questions are:

- whether narrative contains prospective information beyond strong structured physiology;
- whether a small interpretable semantic representation preserves useful parts of that information;
- how much is lost relative to high-dimensional lexical text;
- whether the signal is stable across outcomes, sites, and languages;
- whether the semantic constructs have clinician-validated meaning.

## Repository organization

- `docs/01_*.md`–`docs/06_*.md`: current navigation/synthesis layer.
- `docs/*protocol*.md`: frozen prespecified analysis protocols.
- `docs/*freeze*.md`: frozen cohort/result/mapping documents.
- `src/`: analysis and cohort code.
- `scripts/`: bounded execution wrappers.
- `.runrelay/project.yaml`: authoritative named RunRelay tasks.
- `data/real_mimic_local/`: local restricted/derived row-level data; never committed.
- `outputs/`: aggregate derived outputs; only explicitly declared safe artifacts may leave the workstation.

## Data governance

Credentialed MIMIC and other restricted clinical data remain local.

Do not commit or transmit:

- raw note text;
- patient identifiers;
- row-level restricted clinical data;
- credentials/secrets;
- unrestricted project directories containing sensitive material.

RunRelay jobs declare only safe aggregate artifacts for sharing.

## Local environment

Typical local layout:

```text
~/datasets/MIMIC/physionet.org/files/
├── mimiciii
├── mimiciv
├── mimic-iv-note
├── mimic-iv-ed
├── mimic-iv-ecg
├── mimic-iv-echo
└── mimic-cxr
```

Setup:

```bash
git clone https://github.com/vafaei-ar/mimic-semantic-signals.git
cd mimic-semantic-signals

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Historical material

Early reconnaissance, v1 matched cohorts, v1 population analyses, model-tuning experiments, and v1 external validation code are intentionally retained for provenance.

Do not infer current manuscript status from old filenames or scripts. Use [04 — v1 provenance and integrity hold](docs/04_V1_PROVENANCE_AND_HOLD.md) to understand what remains scientifically informative and what has been superseded.
