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

Detailed frozen protocols and result documents under `docs/` remain authoritative for exact cohort definitions, item IDs, model settings, artifact hashes, and prespecified interpretation rules.

## Current stage

The v1 manuscript-facing results are under an integrity hold after an external review identified cohort and implementation problems that were confirmed by a local aggregate audit.

The current primary analysis has been rebuilt as a corrected v2 lineage:

- source-compatible 12-hour landmark cohorts are frozen;
- note hygiene and note selection are corrected;
- a stronger 34-feature structured baseline is frozen and extracted;
- the active analysis is the **structured-only v2 predictive evaluation**;
- corrected semantic/TF-IDF analyses remain locked until the structured result is complete and frozen.

Current RunRelay gate at the latest documentation update:

- `E8R7Q5M3 — Evaluate Enhanced Structured V2`
- exact commit: `0f72c995d240900e15d65dd7b6e3c4f7048453ea`

See [03 — Corrected v2 analysis lineage](docs/03_V2_ANALYSIS_LINEAGE.md) for the full ordered chain.

## Scientific framing

The study is not framed as “JEV beats LLMs.”

Open-Jev, Laya, and DiffusionGemma are semantic measurement instruments. The scientific questions are:

- whether narrative contains prospective information beyond strong structured physiology;
- whether a small interpretable semantic representation preserves useful parts of that information;
- how much is lost relative to high-dimensional lexical text;
- whether the signal is stable across outcomes, sites, and languages;
- whether the semantic constructs have clinician-validated meaning.

## Repository organization

- `docs/01_*.md`–`docs/05_*.md`: current navigation/synthesis layer.
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
