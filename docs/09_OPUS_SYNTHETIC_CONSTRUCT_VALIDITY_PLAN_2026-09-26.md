# OPUS synthetic construct-validity workstream

Updated: 2026-09-26

## Status

**Planned independent validation workstream. No OPUS-based Medical JEV result has been generated or inspected.**

This workstream is separate from the registered v2.1 MIMIC confirmatory analysis. It must not alter the registered v2.1 populations, outcomes, predictors, fixed-note corpora, split hashes, semantic-instrument revisions, hypotheses, inference rules, or execution order.

Candidate public dataset:

- Hugging Face: `nisten/opus-doctor-patient-conversations-all-human-diseases`
- user-supplied discovery URL: `https://huggingface.co/datasets/nisten/opus5-5-doctor-patient-conversations-all-human-diseases`
- modality: synthetic doctor-patient conversations;
- disease coverage: derived from the author's approximately 2,195-entry all-human-diseases list;
- intended role here: synthetic construct-validity and stress testing, **not** external clinical validation and **not** model training.

Before execution, pin the exact dataset repository revision and record the dataset card/license/provenance available at that revision.

## Why this can help

The registered MIMIC analysis asks whether prospectively available ICU narrative information adds predictive information beyond structured clinical data. OPUS cannot answer that question because it is synthetic and is not a longitudinal ICU outcome cohort.

Its useful role is different: it can test whether the frozen semantic measurement instruments respond to clinical meaning in the intended direction rather than merely responding to medical vocabulary, note density, laboratory mentions, or treatment terminology.

This addresses an important construct-validity question for the eight **registered frozen semantic measurements**:

- `overall_clinician_concern`;
- `worsening_trajectory`;
- `respiratory_concern`;
- `hemodynamic_concern`;
- `poor_treatment_response`;
- `escalation_considered`;
- `diagnostic_uncertainty`;
- `reassuring_stability`.

These names must match `src/semantic_schema.py` exactly. Earlier draft wording that used generic labels such as `acute_instability` or `organ_failure_burden` was incorrect and is superseded.

## Proposed experiments

### 1. Discriminant-validity / negative-control test

Use clinically detailed but non-acute or stable scenarios as negative controls.

Question: does rich medical language by itself spuriously produce high `overall_clinician_concern`, `respiratory_concern`, `hemodynamic_concern`, `poor_treatment_response`, or `escalation_considered` scores?

The analysis should distinguish **medical complexity or vocabulary density** from **acute physiologic/clinical deterioration**.

### 2. Directional perturbation test

Create paired synthetic variants while holding as much wording and disease identity constant as possible. Prespecify edits and expected directions before inference.

Candidate contrasts:

- reassuring/stable -> greater overall clinician concern;
- improving/stable course -> worsening trajectory;
- stable respiratory status -> explicit respiratory concern;
- stable circulation -> explicit hemodynamic concern;
- adequate response -> poor treatment response;
- routine management -> escalation considered;
- diagnostic certainty -> greater diagnostic uncertainty;
- concerning/uncertain note -> explicitly reassuring stability.

The primary object is within-pair score movement in the construct targeted by the perturbation. Non-target constructs should be examined for expected coupling and unintended cross-construct sensitivity.

### 3. Cross-instrument agreement and disagreement

Apply the same frozen construct definitions to Open-Jev, Laya, and DiffusionGemma only after the dataset protocol is frozen.

Evaluate:

- direction agreement under controlled perturbations;
- rank/score agreement by construct;
- systematic disagreement by disease family or scenario type;
- whether disagreement reveals construct ambiguity rather than treating one instrument as ground truth.

This is an instrument-robustness analysis, not a model leaderboard.

## Required safeguards

1. **No fine-tuning on OPUS for this validation.** Fine-tuning would weaken its value as an independent stress-test corpus.
2. **No MIMIC outcome labels or v2.1 performance results are used to design OPUS perturbations or thresholds.**
3. **No claim of external clinical validation.** The dataset is synthetic.
4. **Pin all inputs.** Freeze dataset revision, sampled case IDs, perturbation-generation procedure, prompts/templates if any, semantic schema hash, model revisions, chunking, aggregation, seeds, and output contracts before inference.
5. **Preserve the registered v2.1 instrument contract.** In particular, do not substitute the NVIDIA NVFP4 DiffusionGemma variant.
6. **Separate outputs and manuscript language.** OPUS results belong to a synthetic construct-validity section/supplement or a separate methods analysis. They do not replace blinded clinician validation or external clinical-cohort validation.
7. **Audit generator/provenance dependence.** If the conversations or perturbations are LLM-generated, report the generator and consider whether shared model-family language priors could make construct separation artificially easy.

## Execution plan

Before any OPUS inference:

1. inspect and pin the exact Hugging Face dataset revision;
2. record license and available provenance/generation details;
3. parse the raw dataset and produce a schema/data-quality report without semantic scoring;
4. define an eligible case sample spanning acute and non-acute disease families;
5. freeze negative controls and directional perturbation templates;
6. freeze expected construct directions and evaluation metrics;
7. add a dedicated RunRelay task with safe aggregate artifacts only;
8. validate the protocol/code without reading MIMIC outcomes;
9. run the frozen semantic instruments on OPUS;
10. report this explicitly as synthetic construct-validity evidence.

## Relationship to the Lancet Digital Health plan

**Priority: supplementary, off the critical path.**

OPUS is a weak genre match for the main ICU study because it consists of synthetic doctor-patient conversations rather than bedside nursing/physician ICU notes. Its long conversations can also exceed the registered Open-Jev coverage of at most 8 × 220 tokens, creating truncation as a potential confound. In addition, both the source dialogue and any synthetic perturbations may reflect LLM-generated language patterns.

For these reasons, OPUS should not delay or substitute for the stronger registered controlled-edit robustness analyses on real MIMIC notes. The MIMIC controlled edits are the preferred construct-robustness route because they preserve the target note genre and local context.

OPUS may still be useful as a small supplementary stress test if it shows that the compact semantic representation tracks controlled changes in clinical state and does not simply react to medically dense language.

It does **not** satisfy the planned blinded multi-rater clinician construct validation and does **not** establish transport to another health system.

The desired evidence stack is therefore complementary:

1. registered MIMIC v2.1 predictive incremental-value analysis;
2. registered controlled-edit robustness on real MIMIC notes;
3. blinded clinician construct validation;
4. corrected external clinical-cohort transport analyses;
5. optional OPUS synthetic stress testing as supplementary evidence.

## Current result

No OPUS Medical JEV result exists yet. The current conclusion is only that the dataset is a plausible candidate for a separate synthetic construct-validity workstream and merits a frozen protocol before inference.
