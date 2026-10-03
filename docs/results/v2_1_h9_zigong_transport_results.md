# H9 Zigong transport: partial/deviated execution status

Updated: 2026-10-03

The numerical result below is preserved, but it is **not labeled as completed registered H9 external validation** for manuscript purposes. The formal deviation is recorded in `docs/registration/deviation_h9_partial_execution_2026-10-03.md`.

## Executed descriptive DiffusionGemma arm

RunRelay job `F2N7Q5K9` fit the eight-score DiffusionGemma semantic-only logistic model on the full corrected v2.1 MIMIC ventilation cohort:

- 11,116 stays;
- 279 cases;
- 10,837 controls;
- 4,499 note-available rows.

It then applied that model unchanged to the existing legacy frozen Zigong 24-hour cohort:

- 340 notes/patients;
- 85 cases;
- 255 controls;
- 85 matched sets.

No Zigong refitting, recalibration, threshold selection, coefficient modification, prompt adaptation, or post-hoc translation occurred within this executed arm.

## Descriptive result

| Metric | Estimate | 95% matched-set bootstrap interval |
|---|---:|---:|
| AUROC | 0.5546 | 0.4796 to 0.6308 |
| AUPRC | 0.3030 | 0.2485 to 0.3908 |
| Brier score | 0.2390 | 0.2379 to 0.2400 |

The interval for AUROC includes 0.50.

## Why this is not treated as completed registered H9

- the registered translated Open-Jev/Laya/TF-IDF arm was not performed;
- the executed arm reused `data/real_zigong_local/ventilation24_v1` rather than rebuilding the cohort after the legacy leakage-screen problem had been recognized;
- MIMIC used corrected v2.1 stripped-note scores while Zigong note selection came from the legacy cohort exclusion policy.

Paper 1 will not rerun H9 and will not rely on Zigong for its central claim.

## Provenance

- RunRelay job: `F2N7Q5K9`;
- exact scientific commit: `e173ffd79d78757e21426b02d33ecd75e32b96cd`;
- artifact: `outputs/zigong_external/h9_diffusiongemma_external_transport_v2_1.json`;
- artifact SHA-256: `14191cbef81c49dfe266500ec9eddb322254a10d17d9d82f75a1b39bf363f57f`.
