# Frozen corrected v2.1 H9 Zigong DiffusionGemma external transport result

Updated: 2026-10-03

This document freezes the manuscript-facing registered H9 external narrative transport result exactly as observed. No model, prompt, threshold, translation rule, coefficient, endpoint definition, cohort definition, or preprocessing rule may be changed in response to this result.

## Canonical corrected run

- RunRelay job: `F2N7Q5K9`
- task: `evaluate_h9_zigong_diffusiongemma_transport_v2_1`
- exact scientific commit: `e173ffd79d78757e21426b02d33ecd75e32b96cd`
- artifact: `outputs/zigong_external/h9_diffusiongemma_external_transport_v2_1.json`
- artifact SHA-256: `14191cbef81c49dfe266500ec9eddb322254a10d17d9d82f75a1b39bf363f57f`
- validation job: `E9M6X4T2`
- validation artifact SHA-256: `d337f0e9f15bc7f8fdd99901f8d39738a00e26d82ddb3689d919406cbe0c4486`

## Corrected training population

The transport model is trained on the **full registered corrected v2.1 MIMIC invasive-ventilation cohort**, as required by the frozen H9 protocol:

- 11,116 stays;
- 8,982 unique patients;
- 279 cases;
- 10,837 controls;
- 4,499 note-available rows with complete DiffusionGemma scores.

Rows without notes remain in the MIMIC training cohort with missing semantic values handled by the frozen median-imputation plus missing-indicator pipeline.

## External cohort

- Zigong 24-hour nursing-note ventilation risk-set cohort;
- 85 cases;
- 255 controls;
- 340 total notes;
- 85 complete 1:3 matched sets;
- no Zigong model fitting, recalibration, or threshold selection.

## Transport model

- eight frozen DiffusionGemma semantic scores only;
- median imputation with missing indicators;
- standard scaling;
- logistic regression;
- solver `liblinear`;
- C = 1.0;
- max_iter = 3000;
- coefficients fitted on MIMIC only;
- applied unchanged to Zigong.

## Primary corrected H9 result

- **AUROC: 0.5546**
- **95% matched-set bootstrap interval: 0.4796 to 0.6308**
- AUPRC: **0.3030**
- 95% interval: **0.2485 to 0.3908**
- Brier score: **0.2390**
- 95% interval: **0.2379 to 0.2400**
- 2,000 matched-set bootstrap replicates;
- bootstrap seed 20260924.

Because the analytic Zigong cohort has artificial 25% prevalence, AUPRC is conditional on the sampled cohort and Brier score is descriptive rather than population calibration.

## Construct-level exploratory discrimination

| Construct | Zigong AUROC |
| --- | ---: |
| Respiratory concern | 0.5779 |
| Hemodynamic concern | 0.5379 |
| Poor treatment response | 0.5319 |
| Overall clinician concern | 0.5290 |
| Worsening trajectory | 0.5149 |
| Escalation considered | 0.5114 |
| Diagnostic uncertainty | 0.4903 |
| Reassuring stability, risk-oriented as 1-score | 0.4479 |

## Superseded historical implementation

The historical result in `docs/zigong_diffusiongemma_external_transport_result_freeze_v1.md` reported AUROC 0.5906, but its evaluator trained on the obsolete 1,460-row v1 MIMIC benchmark with 365 cases.

That implementation did not follow the already-frozen protocol requirement to train on the **full frozen MIMIC ventilation cohort**. It remains provenance only and must not be used as manuscript-facing H9 evidence.

The corrected v2.1 run above is authoritative.

## Interpretation

The corrected MIMIC-trained compact semantic predictor shows **limited and uncertain external discrimination** in the independent Zigong site/language/24-hour setting. The interval spans 0.50, so H9 does not establish robust external discrimination.

This should not be interpreted as evidence that narrative contains no transportable information. H9 specifically tests transport of an eight-score DiffusionGemma semantic compression learned into a fixed logistic combination on corrected MIMIC and applied unchanged to a different hospital, language, documentation system, and prediction horizon.

## Guardrails

- DiffusionGemma is the only direct-Chinese model eligible under the frozen bilingual semantic gate.
- No Open-Jev or Laya Zigong outcome scoring is permitted.
- No Zigong refit, recalibration, threshold selection, coefficient modification, prompt adaptation, or post-hoc translation is permitted.
- No structured cross-table comparator is introduced because the Zigong cross-table timing issue remains unresolved.
- Row-level notes, model scores, and predictions remain local.
- This corrected H9 result is frozen regardless of performance.
