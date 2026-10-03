# v2.1 registered corrected H9 Zigong external transport results

Updated: 2026-10-03

H9 evaluates the frozen direct-Chinese DiffusionGemma eight-score semantic transport pipeline from the corrected v2.1 MIMIC ventilation cohort to the frozen Zigong 24-hour invasive-ventilation narrative risk set.

## Frozen design

The transport model was fit on the full corrected v2.1 MIMIC ventilation cohort:

- 11,116 stays;
- 279 cases;
- 10,837 controls;
- 4,499 note-available rows.

It was then applied unchanged to the frozen Zigong cohort:

- 340 patients/notes;
- 85 cases;
- 255 controls;
- 85 matched sets.

The eight semantic scores were used in a logistic model fit on MIMIC only. No Zigong refitting, recalibration, threshold selection, coefficient modification, prompt adaptation, or translation was performed.

## Primary external result

| Metric | Estimate | 95% matched-set bootstrap interval |
|---|---:|---:|
| AUROC | 0.5546 | 0.4796 to 0.6308 |
| AUPRC | 0.3030 | 0.2485 to 0.3908 |
| Brier score | 0.2390 | 0.2379 to 0.2400 |

Uncertainty used 2,000 matched-set bootstrap replicates with the frozen seed.

AUPRC is conditional on the sampled 25% Zigong prevalence. The Brier score is descriptive rather than a population-calibration estimate.

## Interpretation

The corrected H9 result shows limited external discrimination and should not be described as strong transport, language invariance, or deployment readiness.

The historical H9 AUROC of approximately 0.5906 is superseded for manuscript-facing use because that implementation trained on the obsolete 1,460-row v1 MIMIC benchmark rather than the protocol-required full corrected v2.1 ventilation cohort.

## Provenance

- RunRelay job: `F2N7Q5K9`.
- Exact scientific commit: `e173ffd79d78757e21426b02d33ecd75e32b96cd`.
- Canonical artifact: `outputs/zigong_external/h9_diffusiongemma_external_transport_v2_1.json`.
- Artifact SHA-256: `14191cbef81c49dfe266500ec9eddb322254a10d17d9d82f75a1b39bf363f57f`.
