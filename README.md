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
9. [09 — OPUS synthetic construct-validity plan](docs/09_OPUS_SYNTHETIC_CONSTRUCT_VALIDITY_PLAN_2026-09-26.md)

Detailed frozen protocols and result documents under `docs/` remain authoritative for exact cohort definitions, item IDs, model settings, artifact hashes, and prespecified interpretation rules.

## Current stage

The post-review v2.1 analysis plan was submitted to OSF Registries as Secondary Data Preregistration `ahxn9` on 2026-09-25 15:53 America/New_York. The registration cites repository commit `873897e6c934cea3d558b6518ac1e399f9f75387` and manifest SHA-256 `22ac9f815309d81ebf03d279087848e33f8c0a16b563efe8af114a196194fc7d`.

The registration is currently recorded as **approved/public**. Real-label v2.1 predictive performance remains deliberately locked. The gate now requires OSF approval, DOI recording, OSF-hosted attachment hash verification, and verbatim import/verification of the submitted OSF form text.

Post-submission synthetic/static validation job `V4N8Q2R7 — Validate Post-OSF Locks` completed successfully on commit `296e082e8ee9b01211fa50b1be2f026edcb31bdf`. It read no real clinical data and computed no real outcome performance. Its declared integrity artifact SHA-256 is `4860c207938e332eab8385ab3084d7cc5fe34f957e9db40a857920ef7d680ae6`.

While the OSF approval gate remains closed, a separate public-data workstream is being planned for synthetic construct-validity testing using the OPUS doctor-patient conversation dataset. This is explicitly outside the registered v2.1 confirmatory analysis and has produced no Medical JEV results yet.

See [07 — Preregistration readiness checkpoint](docs/07_PREREGISTRATION_READINESS_2026-09-25.md), [08 — Lancet Digital Health roadmap](docs/08_LANCET_DIGITAL_HEALTH_ROADMAP_2026-09-25.md), and [09 — OPUS synthetic construct-validity plan](docs/09_OPUS_SYNTHETIC_CONSTRUCT_VALIDITY_PLAN_2026-09-26.md).

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
