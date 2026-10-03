# 02 - Current scientific status

Updated: 2026-10-03

## Submission-status override, 2026-10-03

The active Paper 1 plan is now `docs/12_MINIMAL_SUBMISSION_PLAN_2026-10-03.md`.

- H8 human construct validation will not be performed; the frozen 200-note preparation remains provenance only under `docs/registration/deviation_h8_not_performed_2026-10-03.md`.
- The existing Zigong DiffusionGemma result is retained only as a post-registration modified descriptive arm using the legacy frozen 24-hour cohort. Registered external validation was not completed as planned; see `docs/registration/deviation_h9_partial_execution_2026-10-03.md`.
- The missingness-resilience and new decision-model panel are cut from Paper 1.
- The only remaining computational work is a label-free semantic-alignment audit, note-available semantic-only discrimination, and a four-level HGB comparator decomposition, all clearly post-registration exploratory except the integrity role of the alignment audit.
- After those analyses, complete the OSF attachment text diff, manuscript-number provenance index, manuscript, figures, supplement, and reporting checklists.

This override governs submission planning where older sections below describe H8/H9 or the broader exploratory roadmap as still pending.

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

Initial lab-lag preparation D3G8V5N2 failed during aggregate feature-change comparison with `KeyError: 'lactate'` because the preparation referenced base lab names rather than the structured `*_last` column names. No predictive model was fit or scored and no shared artifact was produced. The naming fix plus a synthetic assertion were validated by E4H9W6P3 at commit 1ec1ed7d7b6117463b0ec5627eee918ff7ea22af. Corrected preparation F5J2X7N4 then completed cleanly: among 1,183,133 valid in-window lab rows, the 1-hour lag retained 1,138,054 (96.19%) and the 2-hour lag retained 1,089,956 (92.12%). At least one lab feature changed versus primary in 11.07%/21.64% of ventilation rows, 15.51%/29.40% of RRT rows, and 17.19%/32.26% of all-source ICU-death preparation rows for 1h/2h respectively. Preparation artifact SHA-256: 5151e0690f3e2956e501a76bad92747086045777ea92a38a3ab97882ff34e440. The 1-hour invasive-ventilation lab-lag evaluation G6K3Y8P5 completed with comparator AUROC 0.71243, augmented AUROC 0.71960, delta AUROC +0.00717, 95% patient-cluster refit-bootstrap interval -0.02333 to +0.01829, primary delta AUPRC +0.00165, five frozen-partition delta-AUROCs +0.00717, -0.00119, -0.00005, -0.00035, and +0.00273, and 500/500 valid bootstrap replicates with zero replacements. Evaluation artifact SHA-256: 378cdbdc0fb29361434381c1168a99f88dab2e072161efa103f998238408fcdd. The 1-hour RRT lab-lag evaluation H7M4Z9Q2 completed with comparator AUROC 0.97075, augmented AUROC 0.97144, delta AUROC +0.00069, 95% patient-cluster refit-bootstrap interval -0.00331 to +0.00331, primary delta AUPRC -0.00781, five frozen-partition delta-AUROCs +0.00069, -0.00036, -0.00004, -0.00133, and -0.00001, and 500/500 valid bootstrap replicates with zero replacements. Evaluation artifact SHA-256: bdbcf7fb26c98f5a4af3df93f53949df5a00be76c7509c8bc1afeda4fca791a2. The 1-hour MetaVision ICU-death lab-lag evaluation J8N5V3R7 completed with comparator AUROC 0.93086, augmented AUROC 0.93239, delta AUROC +0.00153, 95% patient-cluster refit-bootstrap interval -0.00936 to +0.00618, primary delta AUPRC +0.00890, five frozen-partition delta-AUROCs +0.00153, +0.00504, -0.00347, +0.00560, and -0.00065, and 500/500 valid bootstrap replicates with zero replacements. Evaluation artifact SHA-256: 22b1c3cca2d663875b15421b5bb03ed6728b1cb7a6ff13588f8475a686f7dfb8. Across the three 1-hour lag outcomes, the incremental AUROC estimates are +0.00717 for ventilation, +0.00069 for RRT, and +0.00153 for MetaVision ICU death, with all three 95% intervals spanning both directions. The 2-hour invasive-ventilation lab-lag evaluation K9P6W4R2 completed with comparator AUROC 0.71475, augmented AUROC 0.71690, delta AUROC +0.00216, 95% patient-cluster refit-bootstrap interval -0.02269 to +0.01911, primary delta AUPRC +0.00262, five frozen-partition delta-AUROCs +0.00216, -0.00393, -0.00226, -0.00198, and +0.00674, and 500/500 valid bootstrap replicates with zero replacements. Evaluation artifact SHA-256: f8f34d5d8e1367e537a8f629a8946800a21a2baf3701ed391a199052c4c2d40d. The 2-hour RRT lab-lag evaluation M2R7X5Q9 completed with comparator AUROC 0.97093, augmented AUROC 0.96984, delta AUROC -0.00110, 95% patient-cluster refit-bootstrap interval -0.00294 to +0.00309, primary delta AUPRC -0.00056, five frozen-partition delta-AUROCs -0.00110, +0.00041, +0.00067, +0.00029, and +0.00032, and 500/500 valid bootstrap replicates with zero replacements. Evaluation artifact SHA-256: 9d20d76e9d44d8e5b3b7356c604b3b2a7e5d541b403f11c01e82db8687a31bf7. The 2-hour MetaVision ICU-death lab-lag evaluation N3S8Y6T4 completed with comparator AUROC 0.93575, augmented AUROC 0.93159, delta AUROC -0.00415, 95% patient-cluster refit-bootstrap interval -0.00849 to +0.00655, primary delta AUPRC -0.00883, five frozen-partition delta-AUROCs -0.00415, -0.00189, -0.00248, +0.00278, and -0.00112, and 500/500 valid bootstrap replicates with zero replacements. Evaluation artifact SHA-256: 49140104c0b5e9de3c74d7cd39a06a3cb80ded475f7c3225d7f449fea5577758. The complete 2-hour arm therefore has delta AUROCs +0.00216 for ventilation, -0.00110 for RRT, and -0.00415 for MetaVision ICU death, with all three 95% intervals spanning both directions. Both prespecified laboratory-lag arms are now complete and do not establish a consistent positive semantic increment. The note-availability audit implementation was validated by P4T9Z7M3 at exact commit e79124f195f88dbdf15f3712ebd6929e34085566; its validation artifact reports `real_clinical_data_read: false` and `real_outcome_performance_computed: false`. Q5V8Z2N7 then completed the label-free audit. Across 376,185 normalized bedside notes in the registered MetaVision admissions, storetime was nonmissing for every row. The observed eligible storetime delay distribution had p90 2.842 hours, so the prespecified deterministic rule freezes a 3-hour charttime fallback for missing-storetime notes. Because no such notes exist, both note-availability sensitivities reproduce the primary selected-note identities exactly: 4,499/4,499 ventilation, 7,709/7,709 RRT, and 7,889/7,889 MetaVision death, with zero losses, gains, or changed selected-note signatures. No semantic or predictive rerun is required. Audit artifact SHA-256: bbfe5bb2ff2747544f975c11318198026a5666124a25b87e4f5bac202ab256ef. The frozen fallback contract is config/v2_1_note_availability_fallback_freeze.json. CareVue replication path validation R6W3N8K5 passed at exact commit a1e7547333e9536dcbd651b44c2398589f4d1d7a without real-data/performance access. S7X4P9M2 then completed the registered offline Open-Jev inference on all 23,272 frozen CareVue ICU-death notes with 0 failures; labels were not read or used and no row-level content was shared. Aggregate inference artifact SHA-256: dacb7694da486e57725da76f74f5f9a8bc39a78b01073bd50a07e52786f248d5. CareVue ICU-death replication T8Y5Q2N6 completed at exact commit a1e7547333e9536dcbd651b44c2398589f4d1d7a with comparator AUROC 0.93799, augmented AUROC 0.93544, delta AUROC -0.00255, 95% patient-cluster refit-bootstrap interval -0.00858 to +0.00812, primary delta AUPRC -0.00414, five frozen-partition delta-AUROCs -0.00255, +0.00406, -0.00148, -0.00183, and -0.00206, and 500/500 valid bootstrap replicates with zero replacements. Evaluation artifact SHA-256: 024fdf839fa0625625da455511962dc84a5795b79855d49d985f38e63cc0c0c6. The CareVue result is reported separately from MetaVision without pooling. H6 is now complete. H7 implementation was frozen and validated by V9B4K7M2 at exact commit 5dfaa30dedd273c453b6205100f199097b2f71ee with no real clinical-data read and no outcome performance computed. Ventilation H7 job W2C7M9R4 completed with comparator AUROC 0.72468, shuffled-augmented AUROC 0.71408, delta AUROC -0.01059, 95% patient-cluster refit-bootstrap interval -0.02851 to +0.01432, primary delta AUPRC -0.00766, five frozen-partition delta-AUROCs -0.01059, -0.01455, -0.01341, -0.00070, and -0.00854, and 500/500 valid bootstrap replicates with zero replacements. The shuffle used 4,499 note rows from 3,793 note-available patients, had zero same-patient donor assignments, and preserved each semantic construct marginal exactly. Artifact SHA-256: fc44f7b3c3ac8648f5da74a1d5c7af9bfeaefafea3a4ed144e0612a1c92ee057. H7 RRT job X3D8N6Q2 completed with comparator AUROC 0.97394, shuffled-augmented AUROC 0.97369, delta AUROC -0.00024, 95% patient-cluster refit-bootstrap interval -0.00269 to +0.00313, primary delta AUPRC +0.00885, five frozen-partition delta-AUROCs -0.00024, +0.00075, -0.00064, +0.00029, and +0.00364, and 500/500 valid bootstrap replicates with zero replacements. The shuffle used 7,709 note rows from 6,257 note-available patients, had zero same-patient donor assignments, and preserved each semantic construct marginal exactly. Artifact SHA-256: 132799f693f36f8ed320c819ac76c368aadc47f5f21e968c4e3e816d5c893f54. H7 MetaVision ICU-death job Y4F9P7M2 completed with comparator AUROC 0.93338, shuffled-augmented AUROC 0.93647, delta AUROC +0.00309, 95% patient-cluster refit-bootstrap interval -0.00663 to +0.00599, primary delta AUPRC -0.00082, five frozen-partition delta-AUROCs +0.00309, +0.00257, -0.00122, +0.00117, and -0.00240, and 500/500 valid bootstrap replicates with zero replacements. The shuffle used 7,889 note rows from 6,367 note-available patients, had zero same-patient donor assignments, and preserved each semantic construct marginal exactly. Artifact SHA-256: e9fba18626f950cfabb1d87ed7d0377e08c115e34b83e0329bc2159ae4f0eb8d. H7 CareVue ICU-death job Z5G2R8N4 completed with comparator AUROC 0.93799, shuffled-augmented AUROC 0.93087, delta AUROC -0.00712, 95% patient-cluster refit-bootstrap interval -0.00784 to +0.00882, primary delta AUPRC -0.00299, five frozen-partition delta-AUROCs -0.00712, -0.00063, -0.00203, -0.00436, and +0.00173, and 500/500 valid bootstrap replicates with zero replacements. The shuffle used 23,272 note rows from 18,341 note-available patients, had zero same-patient donor assignments, and preserved each semantic construct marginal exactly. Artifact SHA-256: f9afb65cfef2264fabbf5c0e340535b94007aad932dab9df7c9c18d643294a36. H7 is now complete across all four registered outcome/source analyses.

See docs/results/v2_1_h6_diffusiongemma_results.md and docs/results/v2_1_h6_sensitivity_results.md.

## What the corrected evidence currently supports

The strongest current interpretation is:

1. The compact Open-Jev representation has little or no incremental AUROC beyond the rich structured comparator in the registered primary analyses.
2. High-dimensional lexical TF-IDF retains small positive increments in the common logistic comparison, while Open-Jev increments are negative there.
3. H6 unstripped-note results do not suggest that language stripping erased a major positive semantic effect.
4. Laya and DiffusionGemma show instrument-specific variation, but completed H6 estimates do not yet establish a consistently positive semantic increment.
5. The scientific value of semantic compression may therefore depend more on interpretability, dimensionality, human construct validity, stability, runtime, and transport than on predictive gain alone.

The central manuscript claim no longer depends on H8, which is formally not performed. H6 and H7 are complete. The existing H9 numerical result is preserved but is descriptive under a dated deviation rather than treated as completed registered external validation.

## Current registered execution order

1. H8 design/sample freeze is complete: 200 uniformly sampled MetaVision ICU-death stripped notes, three blinded rater packets, and the full rating/ICC/model-human/2,000-bootstrap analysis contract are frozen before ratings.
2. Begin H8 ratings only after the Penn State IRB determination and applicable PhysioNet credential/DUA requirements for every rater are documented.
3. Corrected H9 Zigong external validation is complete: AUROC 0.5546, 95% matched-set bootstrap interval 0.4796 to 0.6308.
4. After H8 is complete, freeze an authoritative H1-H9 result/provenance index.

Post-registration exploratory decision-model work begins only after the registered critical path is frozen. The frozen exploratory roster is Clef-Flash 9B, Clef 27B, Nimble 9B, and Tev1 4B. Clef-Flash is the first technical/preflight target, followed by Clef 27B if local hardware feasibility is clean, then Nimble and Tev1. All remain outside registered H6 and require a label-free local integration/score-quality gate before any outcome evaluation. See docs/11_POSTREGISTRATION_DECISION_MODEL_EXTENSION_PLAN_2026-10-01.md.

## Current publication-sprint priority

The project is now in a publication-sprint phase. H6 and H7 are complete, corrected computational H9 is complete, and H8 sample preparation is frozen. H8 human construct validation plus the final H1-H9 provenance freeze remain the registered critical path.

Post-registration additions are intentionally bounded:

- a structured-data missingness-resilience analysis will test whether narrative representations recover predictive information when prespecified blocks of structured EHR information are masked;
- the default new local decision-model clinical panel is limited to Nimble 9B, Tev1 4B, and Clef 27B;
- Clef-Flash 9B is the integration/preflight and fallback Cloudflare model rather than an automatic fourth clinical arm;
- all screened exploratory models must be reported, and full refit-bootstrap uncertainty will not be run automatically for every new model;
- later model releases do not interrupt Paper 1 unless they represent a qualitatively different measurement architecture that directly threatens the manuscript interpretation.

The missingness extension is an information-rescue experiment, not a claim of clinical-value imputation. The initial design begins from observed structured data, applies frozen masking rules, and measures how much performance is recovered by Open-Jev and TF-IDF, with any new decision-model representation added only after a separate label-free freeze.

See docs/12_PUBLICATION_SPRINT_AND_MISSINGNESS_RESILIENCE_PLAN_2026-10-03.md.

## Hosted Jev governance

On 2026-10-01 the vendor enabled Zero Data Retention for the organization and stated that only operational telemetry is retained under ZDR.

This resolves the vendor-side retention clarification. It does not itself establish that credentialed MIMIC note text may be transmitted to the hosted service under institutional, Penn State, PhysioNet, or other applicable data-use rules.

Therefore hosted Jev remains outside the current restricted-data execution path. If a hosted comparison later becomes permissible, it will be post-registration exploratory, with the exact hosted configuration frozen first and the integration validated on nonrestricted material.

## External validation

The corrected Zigong route is frozen as a 24-hour external narrative transport analysis because the source nursing-note cadence made the 12-hour design infeasible. The frozen cohort contains 85 cases, 255 controls, 340 patient-unique notes, and 85 matched sets, with zero blank predictor notes and zero direct ventilation leakage hits.

A label-free bilingual semantic gate made DiffusionGemma the only model eligible for direct Chinese outcome scoring. Corrected H9 job F2N7Q5K9 trained the semantic-only logistic pipeline on the full frozen corrected v2.1 MIMIC ventilation cohort (11,116 stays, 279 cases) and applied it unchanged to Zigong. AUROC was 0.5546 with 95% matched-set bootstrap interval 0.4796 to 0.6308. The earlier 0.5906 result is provenance only because its evaluator trained on the obsolete 1,460-row v1 benchmark rather than the protocol-required full cohort.

See docs/05_EXTERNAL_VALIDATION_STATUS.md.

## Manuscript framing

A plausible final story, if the remaining evidence is consistent, is not that semantic scores uniquely outperform physiology or raw text. A stronger framing may be that interpretable low-dimensional semantic compression captures clinically meaningful aspects of narrative information but can lose predictive efficiency relative to high-dimensional lexical representation and may add little discrimination once a strong nonlinear structured comparator is present.

This framing still requires:

- H8 human construct validity;
- final H1-H9 provenance freeze;
- the bounded missingness-resilience analysis or its prespecified stop condition;
- practical compression/runtime/stability analysis for the bounded representative model panel;
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
