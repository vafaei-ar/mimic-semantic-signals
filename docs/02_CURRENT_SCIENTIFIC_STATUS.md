# 02 - Current scientific status

Updated: 2026-10-02

## Scientific question

The study asks whether prospectively available ICU narrative documentation contains reusable information about near-term deterioration that is not fully represented by structured physiology, and whether a small set of clinically interpretable semantic scores can provide useful low-dimensional compression of that narrative information.

The project is not a model leaderboard. Open-Jev, Laya, and DiffusionGemma are semantic measurement instruments. The scientific objects are incremental narrative signal, semantic compression, interpretability, stability, and transport.

## Corrected v2.1 design

The corrected registered analysis uses:

- source-compatible primary populations;
- adult eligibility and NICU exclusion;
- corrected airway-coded GCS verbal handling;
- fixed 12-hour ICU landmark and 12-hour primary prediction horizon;
- normalized note categories and error flags;
- note identity frozen before language stripping;
- a rich 34-feature structured physiology/laboratory/urine comparator plus frozen context;
- exact patient-grouped repeated CV partitions;
- fixed note corpora;
- 500-valid-replicate patient-cluster refit bootstrap as primary uncertainty;
- no confirmatory p-values, Holm testing, or binary interval-crossing decision rule.

Confirmatory populations:

| Outcome | Source | N | Cases |
|---|---|---:|---:|
| Invasive ventilation | MetaVision | 11,116 | 279 |
| RRT | MetaVision | 19,395 | 314 |
| ICU death | MetaVision | 19,811 | 214 |

CareVue ICU death is a separate prespecified replication/sensitivity and is not pooled with MetaVision.

## Registered primary Open-Jev results, H1-H3

| Outcome | Comparator AUROC | + Open-Jev AUROC | Delta AUROC | 95% refit-bootstrap interval |
|---|---:|---:|---:|---:|
| Invasive ventilation | 0.72468 | 0.72463 | -0.00005 | -0.02173 to +0.01910 |
| RRT | 0.97394 | 0.97315 | -0.00079 | -0.00323 to +0.00275 |
| ICU death, MetaVision | 0.93338 | 0.93126 | -0.00212 | -0.00802 to +0.00531 |

All three primary analyses completed 500/500 valid refit-bootstrap replicates with zero replacements.

Current interpretation: the registered Open-Jev point estimates do not show a clear incremental discrimination gain beyond the rich structured comparator.

See docs/results/v2_1_primary_openjev_results.md.

## H4 and H5

H4 six-construct analyses are complete for all three outcomes. See docs/results/v2_1_h4_six_construct_results.md.

H5 uses a common L2-penalized logistic family for comparator, comparator + Open-Jev, comparator + TF-IDF, and comparator + TF-IDF + Open-Jev.

| Outcome | Open-Jev increment | TF-IDF increment | Open-Jev after TF-IDF |
|---|---:|---:|---:|
| Invasive ventilation | -0.00826 | +0.00564 | -0.00673 |
| RRT | -0.00194 | +0.00219 | -0.00153 |
| ICU death, MetaVision | -0.00631 | +0.00123 | -0.00580 |

Within this deliberately common model family, TF-IDF has the larger primary-partition increment in all three outcomes, and adding Open-Jev after TF-IDF lowers AUROC in all three primary analyses.

See docs/results/v2_1_h5_lexical_results.md.

## H6 sensitivity status

### Unstripped-note Open-Jev

| Outcome | Delta AUROC | 95% refit-bootstrap interval |
|---|---:|---:|
| Invasive ventilation | -0.01043 | -0.02177 to +0.01773 |
| RRT | -0.00034 | -0.00308 to +0.00310 |
| ICU death, MetaVision | +0.00108 | -0.00911 to +0.00602 |

Using the full unstripped note does not reveal a consistent positive increment that was hidden by language stripping.

### Laya alternative instrument

| Outcome | Delta AUROC | 95% refit-bootstrap interval |
|---|---:|---:|
| Invasive ventilation | +0.01031 | -0.01595 to +0.02519 |
| RRT | -0.00079 | -0.00278 to +0.00302 |
| ICU death, MetaVision | +0.00141 | -0.00660 to +0.00728 |

The ventilation Laya point estimate is positive but uncertain and not stable enough to redefine the primary result. RRT and death remain near zero.

### DiffusionGemma alternative instrument

Invasive-ventilation inference completed 4,499/4,499 frozen notes with zero failures and without reading outcome labels.

Ventilation evaluation:

- comparator AUROC: 0.72468;
- comparator + DiffusionGemma AUROC: 0.71657;
- delta AUROC: -0.00811;
- 95% patient-cluster refit-bootstrap interval: -0.02030 to +0.01445;
- five frozen-partition delta-AUROCs: -0.00811, -0.00892, -0.00108, -0.00478, +0.00423;
- 500/500 valid bootstrap replicates, zero replacements.

DiffusionGemma RRT inference job D4M8Q2VN completed 7,709/7,709 frozen notes with zero failures, zero outcome-label access, and zero max-chunk truncations. Evaluation job F7K3Q9MV then completed: comparator AUROC 0.97394, comparator + DiffusionGemma AUROC 0.97310, delta AUROC -0.00083, 95% patient-cluster refit-bootstrap interval -0.00283 to +0.00244, primary delta AUPRC +0.01231, and 500/500 valid bootstrap replicates with zero replacements. The five frozen-partition delta-AUROCs were -0.00083, -0.00037, +0.00047, -0.00038, and +0.00324. Evaluation artifact SHA-256: 179b0e6ea1ab6e4f60eeeb4027ae7c291eec51599597ce7dbcead318e884ef9a.

DiffusionGemma MetaVision ICU-death inference job G8M4Q2VN completed 7,889/7,889 frozen notes with zero failures, zero outcome-label access, and zero max-chunk truncations. Evaluation job H9Q4M2VK completed: comparator AUROC 0.93338, comparator + DiffusionGemma AUROC 0.93837, delta AUROC +0.00499, 95% patient-cluster refit-bootstrap interval -0.00654 to +0.00652, primary delta AUPRC +0.00882, and 500/500 valid bootstrap replicates with zero replacements. The five frozen-partition delta-AUROCs were +0.00499, +0.00613, +0.00188, -0.00066, and +0.00152. Evaluation artifact SHA-256: b12f961687c67c2ed25a689cd5f79d492b2db89010a8fc9c543cabbd19e0dc23.

The completed DiffusionGemma three-outcome arm therefore does not establish a consistent positive incremental-AUROC effect: ventilation is negative, RRT is essentially null, and death has a small positive point estimate with uncertainty spanning both directions.

For the registered ventilation endpoint sensitivity, aggregate audit R8V4N2M7 confirmed that the explicit-intubation arm is empirically identical to primary H1 and needs no separate predictive rerun. The broad respiratory-support arm contains 11,380 stays, 543 cases, 10,837 unchanged controls, and 4,590 note-available rows. Preparation job T2X6P4N8 completed cleanly with 34 structured features, the frozen context block, five patient-grouped split repeats, and a 4,590-note stripped corpus. Label-free Open-Jev inference V3X7P5N9 then completed 4,590/4,590 notes with zero failures and zero outcome-label access. Evaluation W4Y8P6N2 completed with comparator AUROC 0.70385, augmented AUROC 0.69741, delta AUROC -0.00643, 95% patient-cluster refit-bootstrap interval -0.01879 to +0.01046, primary delta AUPRC -0.00296, five frozen-partition delta-AUROCs -0.00643, +0.00160, -0.01098, -0.00698, and -0.00634, and 500/500 valid bootstrap replicates with zero replacements. Evaluation artifact SHA-256: 824114f7217a3a5af6806ce6b4e413e4ec070edd865f21ee2bb60e68c3c2ea80.

CHARTEVENTS storetime preparation Y6Z3R8M4 completed under the prespecified rule that eligible rows retain the original charttime lookback and also have nonmissing storetime at or before the landmark. Of 2,588,698 in-window CHARTEVENTS rows, 127,617 (4.93%) lacked storetime, 187,322 (7.24%) were stored after the landmark, and 2,273,759 (87.83%) were retained. At least one CHARTEVENTS-derived feature changed versus the primary comparator in 56.18% of ventilation rows, 53.24% of RRT rows, and 45.33% of the all-source ICU-death preparation rows. Ventilation evaluation Z7B4R9M5 completed with comparator AUROC 0.71690, augmented AUROC 0.72358, delta AUROC +0.00668, 95% patient-cluster refit-bootstrap interval -0.02079 to +0.02286, primary delta AUPRC -0.00605, five frozen-partition delta-AUROCs +0.00668, -0.01056, -0.00523, -0.00220, and +0.00336, and 500/500 valid bootstrap replicates with zero replacements. RRT evaluation A8C5R2M9 completed with comparator AUROC 0.97401, augmented AUROC 0.97453, delta AUROC +0.00053, 95% patient-cluster refit-bootstrap interval -0.00307 to +0.00261, primary delta AUPRC +0.00329, five frozen-partition delta-AUROCs +0.00053, -0.00002, +0.00137, +0.00009, and +0.00342, and 500/500 valid bootstrap replicates with zero replacements. The RRT artifact contains one copied guardrail sentence saying “ventilation population,” but its outcome, cohort, cases, semantic count, hashes, and task are correctly RRT. MetaVision ICU-death evaluation B9D6R3M2 completed with comparator AUROC 0.93367, augmented AUROC 0.93160, delta AUROC -0.00207, 95% patient-cluster refit-bootstrap interval -0.00923 to +0.00689, primary delta AUPRC -0.01119, five frozen-partition delta-AUROCs -0.00207, -0.00191, -0.00221, +0.00217, and -0.00231, and 500/500 valid bootstrap replicates with zero replacements. Evaluation artifact SHA-256: 9b826a21bb6e382b6024870b7080eaf2a0d21c9f899010a8486a6d0c20a644ee. The complete CHARTEVENTS storetime sensitivity therefore does not establish a consistent positive incremental-AUROC effect across outcomes.

Initial lab-lag preparation D3G8V5N2 failed during aggregate feature-change comparison with `KeyError: 'lactate'` because the preparation referenced base lab names rather than the structured `*_last` column names. No predictive model was fit or scored and no shared artifact was produced. The naming fix plus a synthetic assertion were validated by E4H9W6P3 at commit 1ec1ed7d7b6117463b0ec5627eee918ff7ea22af. Corrected preparation F5J2X7N4 then completed cleanly: among 1,183,133 valid in-window lab rows, the 1-hour lag retained 1,138,054 (96.19%) and the 2-hour lag retained 1,089,956 (92.12%). At least one lab feature changed versus primary in 11.07%/21.64% of ventilation rows, 15.51%/29.40% of RRT rows, and 17.19%/32.26% of all-source ICU-death preparation rows for 1h/2h respectively. Preparation artifact SHA-256: 5151e0690f3e2956e501a76bad92747086045777ea92a38a3ab97882ff34e440. Current job G6K3Y8P5 is running the 1-hour invasive-ventilation lab-lag evaluation at the same corrected commit.

See docs/results/v2_1_h6_diffusiongemma_results.md and docs/results/v2_1_h6_sensitivity_results.md.

## What the corrected evidence currently supports

The strongest current interpretation is:

1. The compact Open-Jev representation has little or no incremental AUROC beyond the rich structured comparator in the registered primary analyses.
2. High-dimensional lexical TF-IDF retains small positive increments in the common logistic comparison, while Open-Jev increments are negative there.
3. H6 unstripped-note results do not suggest that language stripping erased a major positive semantic effect.
4. Laya and DiffusionGemma show instrument-specific variation, but completed H6 estimates do not yet establish a consistently positive semantic increment.
5. The scientific value of semantic compression may therefore depend more on interpretability, dimensionality, human construct validity, stability, runtime, and transport than on predictive gain alone.

The central manuscript claim remains unlocked until the registered H6-H9 sequence is complete.

## Current registered execution order

1. Complete the running 1-hour invasive-ventilation lab-lag evaluation, then evaluate 1-hour RRT and MetaVision ICU death before the 2-hour arm.
2. Run the registered note-availability sensitivity.
3. Run the separate CareVue ICU-death sensitivity.
4. Run H7 comparator-risk-decile patient-shuffled negative control.
5. Run H8 blinded clinician construct validation.
6. Run H9 corrected Zigong external validation.
7. Freeze an authoritative H1-H9 result/provenance index.

Post-registration exploratory decision-model work begins only after the registered critical path is frozen. The frozen exploratory roster is Clef-Flash 9B, Clef 27B, Nimble 9B, and Tev1 4B. Clef-Flash is the first technical/preflight target, followed by Clef 27B if local hardware feasibility is clean, then Nimble and Tev1. All remain outside registered H6 and require a label-free local integration/score-quality gate before any outcome evaluation. See docs/11_POSTREGISTRATION_DECISION_MODEL_EXTENSION_PLAN_2026-10-01.md.

## Hosted Jev governance

On 2026-10-01 the vendor enabled Zero Data Retention for the organization and stated that only operational telemetry is retained under ZDR.

This resolves the vendor-side retention clarification. It does not itself establish that credentialed MIMIC note text may be transmitted to the hosted service under institutional, Penn State, PhysioNet, or other applicable data-use rules.

Therefore hosted Jev remains outside the current restricted-data execution path. If a hosted comparison later becomes permissible, it will be post-registration exploratory, with the exact hosted configuration frozen first and the integration validated on nonrestricted material.

## External validation

The corrected Zigong route is frozen as a 24-hour external narrative transport analysis because the source nursing-note cadence made the 12-hour design infeasible. The frozen cohort contains 85 cases, 255 controls, 340 patient-unique notes, and 85 matched sets, with zero blank predictor notes and zero direct ventilation leakage hits.

A label-free bilingual semantic gate made DiffusionGemma the only model eligible for direct Chinese outcome scoring. The final transport model is trained on the full frozen MIMIC ventilation cohort and applied unchanged to Zigong with no Zigong refit or recalibration.

See docs/05_EXTERNAL_VALIDATION_STATUS.md.

## Manuscript framing

A plausible final story, if the remaining evidence is consistent, is not that semantic scores uniquely outperform physiology or raw text. A stronger framing may be that interpretable low-dimensional semantic compression captures clinically meaningful aspects of narrative information but can lose predictive efficiency relative to high-dimensional lexical representation and may add little discrimination once a strong nonlinear structured comparator is present.

This framing still requires:

- H8 human construct validity;
- H9 corrected external transport;
- completion of all registered H6 sensitivities;
- practical compression/runtime/stability analysis;
- exact provenance audit of every manuscript number.

## Claim guardrails

Do not claim that:

- JEV/Open-Jev/Laya/DiffusionGemma outperform raw text generally;
- the eight constructs contain information unavailable to lexical models;
- v1 matched-cohort or context-model estimates are current primary evidence;
- external transport is strong or deployment-ready;
- note-availability/context effects are causal;
- one H6 instrument is superior based on post hoc point-estimate selection.

Use docs/03_V2_ANALYSIS_LINEAGE.md for provenance and docs/10_POSTREGISTRATION_EXECUTION_AND_EXTENSION_PLAN_2026-09-30.md for the authoritative forward plan.
