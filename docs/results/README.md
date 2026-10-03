# Registered v2.1 result documents

Updated: 2026-10-02

This directory contains aggregate manuscript-facing result summaries. Row-level restricted data and patient-level predictions remain local.

## Current result index

| Analysis | Status | Document |
|---|---|---|
| H1-H3 primary stripped-note Open-Jev | Complete | v2_1_primary_openjev_results.md |
| H4 six-construct analysis | Complete | v2_1_h4_six_construct_results.md |
| H5 common-logistic lexical comparison | Complete | v2_1_h5_lexical_results.md |
| H6 unstripped-note Open-Jev | Complete | v2_1_h6_unstripped_results.md |
| H6 Laya alternative instrument | Complete | v2_1_h6_laya_results.md |
| H6 DiffusionGemma alternative instrument | Complete | v2_1_h6_diffusiongemma_results.md |
| H6 aggregate sensitivity index | In progress | v2_1_h6_sensitivity_results.md |

## Current live registered job

The registered DiffusionGemma arm is complete for all three outcomes: ventilation delta AUROC -0.00811 (95% interval -0.02030 to +0.01445), RRT -0.00083 (-0.00283 to +0.00244), and MetaVision ICU death +0.00499 (-0.00654 to +0.00652).

The broad respiratory-support endpoint arm is complete. W4Y8P6N2 reported comparator AUROC 0.70385, augmented AUROC 0.69741, delta AUROC -0.00643, and 95% refit-bootstrap interval -0.01879 to +0.01046, with 500/500 valid bootstrap replicates and zero replacements. Artifact SHA-256: 824114f7217a3a5af6806ce6b4e413e4ec070edd865f21ee2bb60e68c3c2ea80.

Y6Z3R8M4 completed the registered CHARTEVENTS storetime preparation at validated project commit 27a061c25d88e56a155c93c83514a7a63b6cb298. Of 2,588,698 in-window CHARTEVENTS rows, 87.83% were retained after requiring nonmissing storetime at or before the landmark; 4.93% lacked storetime and 7.24% were stored after the landmark. Preparation artifact SHA-256: 9cf9de723239481a0b42604482a0186885520c7dc56df6640ac08e80d9a12901.

Z7B4R9M5 completed the invasive-ventilation storetime evaluation: comparator AUROC 0.71690, augmented AUROC 0.72358, delta AUROC +0.00668, 95% refit-bootstrap interval -0.02079 to +0.02286, with 500/500 valid bootstrap replicates and zero replacements. Artifact SHA-256: ee34846501989672c7a4e3fc2dcfb2536f0ed086fce7af9c4357b9f723bbcca4.

A8C5R2M9 completed the RRT storetime evaluation: comparator AUROC 0.97401, augmented AUROC 0.97453, delta AUROC +0.00053, 95% refit-bootstrap interval -0.00307 to +0.00261, with 500/500 valid bootstrap replicates and zero replacements. Artifact SHA-256: 07b9dc303cdab37737274a7759fe6c098813d423b2b28b3ddbd8c0aa1510f839.

B9D6R3M2 completed the MetaVision ICU-death storetime evaluation: comparator AUROC 0.93367, augmented AUROC 0.93160, delta AUROC -0.00207, 95% refit-bootstrap interval -0.00923 to +0.00689, with 500/500 valid bootstrap replicates and zero replacements. Artifact SHA-256: 9b826a21bb6e382b6024870b7080eaf2a0d21c9f899010a8486a6d0c20a644ee.

The three-outcome CHARTEVENTS storetime sensitivity is complete. Initial lab-lag preparation D3G8V5N2 failed during aggregate feature-change comparison because the code referenced base lab names rather than the structured `*_last` columns; no predictive performance was opened and no artifact was shared. E4H9W6P3 validated the correction and a dedicated feature-name assertion. Corrected preparation F5J2X7N4 completed at commit 1ec1ed7d7b6117463b0ec5627eee918ff7ea22af. The 1-hour lag retained 96.19% of valid in-window lab rows and the 2-hour lag retained 92.12%; preparation artifact SHA-256 5151e0690f3e2956e501a76bad92747086045777ea92a38a3ab97882ff34e440. G6K3Y8P5 completed the registered 1-hour invasive-ventilation lab-lag evaluation: comparator AUROC 0.71243, augmented AUROC 0.71960, delta AUROC +0.00717, 95% refit-bootstrap interval -0.02333 to +0.01829, with 500/500 valid bootstrap replicates and zero replacements. Artifact SHA-256: 378cdbdc0fb29361434381c1168a99f88dab2e072161efa103f998238408fcdd. H7M4Z9Q2 completed the registered 1-hour RRT lab-lag evaluation: comparator AUROC 0.97075, augmented AUROC 0.97144, delta AUROC +0.00069, 95% refit-bootstrap interval -0.00331 to +0.00331, with 500/500 valid bootstrap replicates and zero replacements. Artifact SHA-256: bdbcf7fb26c98f5a4af3df93f53949df5a00be76c7509c8bc1afeda4fca791a2. J8N5V3R7 completed the registered 1-hour MetaVision ICU-death lab-lag evaluation: comparator AUROC 0.93086, augmented AUROC 0.93239, delta AUROC +0.00153, 95% refit-bootstrap interval -0.00936 to +0.00618, with 500/500 valid bootstrap replicates and zero replacements. Artifact SHA-256: 22b1c3cca2d663875b15421b5bb03ed6728b1cb7a6ff13588f8475a686f7dfb8. The complete 1-hour lab-lag arm does not show a consistent positive Open-Jev increment. K9P6W4R2 completed the registered 2-hour invasive-ventilation lab-lag evaluation: comparator AUROC 0.71475, augmented AUROC 0.71690, delta AUROC +0.00216, 95% refit-bootstrap interval -0.02269 to +0.01911, with 500/500 valid bootstrap replicates and zero replacements. Artifact SHA-256: f8f34d5d8e1367e537a8f629a8946800a21a2baf3701ed391a199052c4c2d40d. M2R7X5Q9 completed the registered 2-hour RRT lab-lag evaluation: comparator AUROC 0.97093, augmented AUROC 0.96984, delta AUROC -0.00110, 95% refit-bootstrap interval -0.00294 to +0.00309, with 500/500 valid bootstrap replicates and zero replacements. Artifact SHA-256: 9d20d76e9d44d8e5b3b7356c604b3b2a7e5d541b403f11c01e82db8687a31bf7. N3S8Y6T4 completed the registered 2-hour MetaVision ICU-death lab-lag evaluation: comparator AUROC 0.93575, augmented AUROC 0.93159, delta AUROC -0.00415, 95% refit-bootstrap interval -0.00849 to +0.00655, with 500/500 valid bootstrap replicates and zero replacements. Artifact SHA-256: 49140104c0b5e9de3c74d7cd39a06a3cb80ded475f7c3225d7f449fea5577758. Both laboratory-lag arms are complete. P4T9Z7M3 validated the note-availability timing-audit path at exact commit e79124f195f88dbdf15f3712ebd6929e34085566 without real-data/performance access. Q5V8Z2N7 then completed the label-free audit: p90 documentation delay 2.842 hours, frozen fallback 3 hours, and 0 missing-storetime rows among 376,185 normalized bedside notes. Storetime-only and fallback-delay sensitivities select exactly the primary notes for all three registered MetaVision outcomes, so no semantic/predictive rerun is required. Audit artifact SHA-256: bbfe5bb2ff2747544f975c11318198026a5666124a25b87e4f5bac202ab256ef. R6W3N8K5 validated the separate CareVue replication path at exact commit a1e7547333e9536dcbd651b44c2398589f4d1d7a. S7X4P9M2 completed CareVue Open-Jev inference on 23,272/23,272 frozen notes with 0 failures and no labels read; aggregate artifact SHA-256 dacb7694da486e57725da76f74f5f9a8bc39a78b01073bd50a07e52786f248d5. T8Y5Q2N6 completed the separate CareVue ICU-death HGB replication: comparator AUROC 0.93799, augmented AUROC 0.93544, delta AUROC -0.00255, 95% refit-bootstrap interval -0.00858 to +0.00812, primary delta AUPRC -0.00414, and 500/500 valid bootstrap replicates with zero replacements. Artifact SHA-256: 024fdf839fa0625625da455511962dc84a5795b79855d49d985f38e63cc0c0c6. H6 is now complete. V9B4K7M2 validated the H7 patient-shuffled negative-control path at exact commit 5dfaa30dedd273c453b6205100f199097b2f71ee without real-data/performance access. W2C7M9R4 completed H7 ventilation with comparator AUROC 0.72468, shuffled-augmented AUROC 0.71408, delta AUROC -0.01059, 95% refit-bootstrap interval -0.02851 to +0.01432, primary delta AUPRC -0.00766, five frozen-partition delta-AUROCs -0.01059, -0.01455, -0.01341, -0.00070, and -0.00854, and 500/500 valid bootstrap replicates with zero replacements. Artifact SHA-256: fc44f7b3c3ac8648f5da74a1d5c7af9bfeaefafea3a4ed144e0612a1c92ee057. X3D8N6Q2 is now running H7 RRT at the same exact commit.

The currently running job is not changed by documentation-only commits.

## Interpretation rule

Use canonical RunRelay aggregate artifacts and exact provenance for every numerical update. Do not populate a pending result from job progress, logs, or expectations.

H6 alternative instruments are sensitivities. Do not use point-estimate differences to select a preferred instrument post hoc.

The authoritative registered forward sequence is docs/10_POSTREGISTRATION_EXECUTION_AND_EXTENSION_PLAN_2026-09-30.md. The separate post-registration exploratory decision-model plan is docs/11_POSTREGISTRATION_DECISION_MODEL_EXTENSION_PLAN_2026-10-01.md.
