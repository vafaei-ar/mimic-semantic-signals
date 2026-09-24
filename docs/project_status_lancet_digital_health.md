# Project status and Lancet Digital Health roadmap

Updated: 2026-09-24

This is the high-level scientific status document for the project. Detailed protocols and result freezes in `docs/` remain authoritative for exact cohort definitions, model settings, artifact hashes, and prespecified analyses.

## Integrity hold

As of 2026-09-24, manuscript-facing interpretation is paused after an external code review identified cohort and implementation issues that can affect headline estimates. Several are already confirmed directly from code, including ventilation endpoint/source observability, asymmetric matched risk-set logic, Open-Jev/Laya chunk-aggregation inconsistency, the eICU lab-window clamp, and Zigong leakage-regex problems. See `docs/integrity_review_hold_2026-09-24.md` and `docs/external_review_integrity_audit_protocol_v1.md`.

All v1 results remain preserved for provenance. Do not use them as final Lancet Digital Health estimates until a corrected v2 lineage is frozen and rerun.

## Scientific question

The project asks whether prospectively available ICU narrative documentation contains reusable information about near-term deterioration that is not fully represented by structured physiology, and whether a small set of clinically interpretable semantic scores can serve as a portable low-dimensional representation of that narrative signal.

The project is deliberately not framed as "JEV versus LLMs." Open-Jev, Laya, and prompted DiffusionGemma are measurement instruments. The scientific object is the narrative semantic signal, its incremental value, its interpretability, and its transport across outcomes and settings.

## What has been completed

### 1. Data reconnaissance and governance

Initial MIMIC reconnaissance established that longitudinal bedside documentation is usable for prospective deterioration analyses, but note availability is incomplete and outcome-dependent. Raw MIMIC text is kept local. External semantic inference is not used unless data-governance requirements are satisfied; current model inference is offline/local.

### 2. Primary vasopressor case study

A frozen MIMIC-III 6-hour vasopressor study used 2,465 cases and 7,395 matched controls.

Primary incremental AUROC beyond linear structured physiology:

- Open-Jev: +0.0148
- Laya: +0.0107

Against a stronger post-timeout nonlinear random-forest physiology comparator:

- Open-Jev: +0.0064, positive bootstrap CI
- Laya: +0.0033, CI narrowly crossing zero

The semantic increment survived treatment-language exclusion, note-length adjustment, exact note-category matching, and increasing lead time. Open-Jev remained clearly incremental when the selected note was available at least 4 hours before vasopressor initiation.

The major qualification is lexical control. TF-IDF note text was substantially stronger than the eight semantic scores. Once structured physiology plus TF-IDF was present, Open-Jev and Laya added essentially no further AUROC. The correct interpretation is therefore compact interpretable compression of narrative risk information, not unique information unavailable to ordinary text features.

### 3. Multi-outcome zero-shot benchmark

The same frozen eight semantic constructs were tested without outcome-specific tuning on three additional 12-hour outcomes:

- invasive ventilation: 365 cases + 1,095 controls
- renal-replacement therapy: 583 cases + 1,749 controls
- ICU death: 2,060 cases + 6,180 controls

Open-Jev, Laya, and native-HF DiffusionGemma all carried standalone signal above chance.

Increment over structured physiology:

| Outcome | Open-Jev | Laya | DiffusionGemma |
| --- | ---: | ---: | ---: |
| Ventilation | +0.0206 | +0.0277 | +0.0452 |
| RRT | +0.00045 | +0.00042 | -0.00061 |
| ICU death | +0.0211 | +0.0099 | +0.0272 |

RRT is the informative negative case: structured renal information is already highly discriminative, largely because contemporaneous creatinine carries much of the signal.

The TF-IDF control again showed that the eight semantic scores generally add little after a high-dimensional lexical representation. DiffusionGemma retained only a small lexical-independent increment for ICU death.

Authoritative freeze: `docs/multitask_zero_shot_freeze_v1.md`.

### 4. Supervised text-learning upper bound

A separate post-freeze supervised text-encoder arm tested whether outcome-specific text learning could exceed the zero-shot semantic compression.

A patient-first 70/15/15 train/validation/locked-test design was frozen before training. The locked test was opened once.

Final locked-test AUROC:

| Outcome | Supervised encoder | Structured | Context + TF-IDF | Structured + TF-IDF |
| --- | ---: | ---: | ---: | ---: |
| Ventilation | 0.721 | 0.628 | 0.770 | 0.702 |
| RRT | 0.808 | 0.961 | 0.863 | 0.964 |
| ICU death | 0.922 | 0.875 | 0.924 | 0.938 |

The supervised encoder is therefore a useful upper-bound comparator, but it is not generally superior to TF-IDF or structured data. No further tuning may use the locked test.

Authoritative freeze: `docs/multitask_supervised_text_encoder_v2_final_test_freeze.md`.

### 5. External validation

#### Structured transport

The frozen structured vasopressor model was transported without refitting from MIMIC to eICU and NWICU. Approximate portable-core AUROC was 0.720 in eICU and 0.663 in NWICU. Removing missingness indicators reduced performance to about 0.705 and 0.640, respectively. Missingness patterns therefore contribute, especially in NWICU, but do not explain the full transported signal.

#### Cross-language narrative transport to Zigong

Zigong supplied a defensible 24-hour invasive-ventilation nursing-note cohort after timing and endpoint audits. A label-free bilingual semantic gate allowed direct-Chinese outcome scoring only for DiffusionGemma; Open-Jev and Laya were frozen out.

The MIMIC-trained eight-score DiffusionGemma semantic-only model was applied unchanged to 85 Zigong cases and 255 controls:

- AUROC 0.591, 95% CI 0.514 to 0.668
- AUPRC 0.374

This is limited but non-zero external discrimination. It is not evidence of language invariance or deployment readiness.

Authoritative freeze: `docs/zigong_diffusiongemma_external_transport_result_freeze_v1.md`.

Additional external structured datasets remain planned/pending, including MIMIC-BR, HiRID, and SICdb. These can strengthen structured transport, calibration, and endpoint generalizability, but they do not replace external narrative validation because they do not provide comparable bedside narrative notes.

### 6. Population-representative calibration and utility

The earlier matched cohorts had artificial 25% prevalence and could not support population calibration or decision-curve claims. A new 12-hour landmark analysis therefore retained all outcome-observable ICU stays, including patients with no eligible note.

Frozen population cohorts:

| Outcome | Observable stays | Cases | Prevalence | Note coverage |
| --- | ---: | ---: | ---: | ---: |
| Ventilation | 28,699 | 282 | 0.983% | 67.69% |
| RRT | 48,831 | 391 | 0.801% | 69.29% |
| ICU death | 49,555 | 537 | 1.084% | 68.10% |

Structured-only population results:

| Outcome | AUROC | AUPRC | Calibration slope |
| --- | ---: | ---: | ---: |
| Ventilation | 0.707 | 0.023 | 0.783 |
| RRT | 0.948 | 0.144 | 0.988 |
| ICU death | 0.793 | 0.177 | 0.959 |

Decision-curve net benefit is positive across the full prespecified threshold range for RRT and ICU death, and mainly through 2% risk for ventilation.

The population semantic extension is complete and frozen in `docs/population_landmark12_semantic_extension_result_freeze_v1.md`.

The main result is outcome-dependent:

| Outcome | Open-Jev ΔAUROC vs note context | Laya ΔAUROC vs note context | Open-Jev ΔAUROC after TF-IDF |
| --- | ---: | ---: | ---: |
| Ventilation | +0.00338 [-0.00134, 0.00823] | -0.00469 [-0.00835, -0.00131] | +0.00147 [-0.00260, 0.00570] |
| RRT | -0.00075 [-0.00249, 0.00132] | -0.00033 [-0.00274, 0.00207] | -0.00092 [-0.00244, 0.00069] |
| ICU death | **+0.01332 [0.00576, 0.02153]** | **+0.00720 [0.00160, 0.01347]** | **+0.00537 [0.00013, 0.01073]** |

For ICU death, Open-Jev retains a small lexical-independent AUROC increment. However, semantic additions do not improve AUPRC or Brier score consistently, and net-benefit gains are threshold-specific.

The largest new observation is documentation-process signal. For ventilation, adding note availability/category/source/age to structured physiology increases AUROC from **0.707 to 0.860**. For RRT, the same context raises AUPRC from **0.144 to 0.222** while AUROC changes little. This effect must be decomposed before manuscript lock so that documentation-process signal is not conflated with narrative-content signal.

## Current interpretation

The project has established four consistent facts:

1. Prospective clinical narrative contains predictive information about deterioration beyond structured physiology for some outcomes.
2. The same eight semantic constructs generalize across several outcomes and multiple model families, but the incremental value is strongly outcome-dependent.
3. High-dimensional lexical text usually captures more predictive information than the compact semantic scores. The semantic layer should be presented as interpretable compression, not as uniquely predictive hidden information.
4. Transport is possible but imperfect. The strongest current external narrative evidence is modest cross-language DiffusionGemma transport to Zigong.

## Lancet Digital Health readiness

The project is stronger than a single-outcome prediction paper, but it is not yet an obvious Lancet Digital Health submission.

The main remaining weaknesses are scientific rather than computational:

- construct validity: the eight semantic scores have not yet been validated against blinded clinician annotation;
- external narrative replication: Zigong transport is promising but modest and model/language-specific;
- documentation-process confounding: note availability/timing/type carry substantial signal, especially for ventilation, and require explicit decomposition before manuscript lock;
- general clinical relevance: a top-tier paper needs to show why interpretable semantic compression is useful beyond AUROC, for example reproducibility, portability, calibration, decision support, or efficiency.

## Prioritized path toward Lancet Digital Health

1. **Decompose the population note-context effect.** This is now the immediate analytic gate. Separate note availability, category/source, note age, and note-available-only semantic performance. Keep it explicitly labeled as a post-result sensitivity and do not reinterpret it as population calibration.
2. **Add construct validation by clinicians.** Use a prespecified blinded sample of notes, multiple clinical raters, explicit definitions for the eight constructs, inter-rater reliability, and model-versus-human agreement/calibration. This is the most important missing validation of the semantic measurement layer.
3. **Complete additional external structured validation** in MIMIC-BR, HiRID, and SICdb when approvals arrive, using frozen endpoints/models and no external tuning.
4. **Seek another external narrative cohort if feasible.** The current external narrative evidence rests on Zigong and a cross-language model gate. A second independent narrative dataset would materially strengthen the claim of reusable semantic signals.
5. **Quantify the value of compression, not only discrimination.** Compare eight-score semantics with TF-IDF and the supervised encoder on dimensionality, computational cost, stability across outcomes/sites, interpretability, and calibration/transport. The paper needs a reason to prefer a compact semantic layer even when lexical AUROC is higher.
6. **Freeze the manuscript claim before further expansion.** The likely central claim is that low-dimensional, clinically interpretable semantic measurements capture reusable prospective information from clinical narratives across multiple deterioration outcomes, with outcome-dependent incremental value and measurable but imperfect transport.

## Claim guardrails

Do not claim:

- that JEV/Open-Jev/Laya outperform raw text generally;
- that the eight constructs contain information unavailable to lexical models;
- that external transport is strong or deployment-ready;
- that matched-cohort Brier scores or decision curves represent population calibration;
- that the supervised encoder is a semantic-preserving JEV model.

Do claim only what the frozen analyses support, and keep zero-shot, supervised tuning, external validation, and population analyses clearly separated.
