# v2.1 registered H7 patient-shuffled negative-control results

Updated: 2026-10-03

H7 tests whether the incremental performance attributed to the eight semantic scores survives when complete eight-score vectors are reassigned between different patients within frozen rich-comparator risk deciles. The shuffle preserves each construct marginal exactly and uses the registered frozen downstream model/evaluation procedure.

## Results

| Outcome/source | N | Cases | Comparator AUROC | Shuffled + comparator AUROC | Delta AUROC | 95% refit-bootstrap interval |
|---|---:|---:|---:|---:|---:|---:|
| Invasive ventilation, MetaVision | 11,116 | 279 | 0.72468 | 0.71408 | -0.01059 | -0.02851 to +0.01432 |
| RRT, MetaVision | 19,395 | 314 | 0.97394 | 0.97369 | -0.00024 | -0.00269 to +0.00313 |
| ICU death, MetaVision | 19,811 | 214 | 0.93338 | 0.93647 | +0.00309 | -0.00663 to +0.00599 |
| ICU death, CareVue | 25,632 | 306 | 0.93799 | 0.93087 | -0.00712 | -0.00784 to +0.00882 |

All four analyses completed 500/500 valid patient-cluster refit-bootstrap replicates.

## Interpretation

The shuffled semantic vectors do not show a reproducible positive increment. Ventilation and CareVue death are negative, RRT is essentially null, and MetaVision death has a small positive point estimate with uncertainty spanning both directions.

H7 therefore does not support a stable patient-specific predictive contribution from the eight-score semantic vector after conditioning the shuffle within structured-risk strata. This is a negative-control result and should not be interpreted as proving equivalence.

## Provenance

- Ventilation: RunRelay job `W2C7M9R4`; artifact SHA-256 `fc44f7b3c3ac8648f5da74a1d5c7af9bfeaefafea3a4ed144e0612a1c92ee057`.
- RRT: RunRelay job `X3D8N6Q2`; artifact SHA-256 `132799f693f36f8ed320c819ac76c368aadc47f5f21e968c4e3e816d5c893f54`.
- MetaVision ICU death: RunRelay job `Y4F9P7M2`; artifact SHA-256 `e9fba18626f950cfabb1d87ed7d0377e08c115e34b83e0329bc2159ae4f0eb8d`.
- CareVue ICU death: RunRelay job `Z5G2R8N4`; artifact SHA-256 `f9afb65cfef2264fabbf5c0e340535b94007aad932dab9df7c9c18d643294a36`.

The H7 implementation/validation commit was `5dfaa30dedd273c453b6205100f199097b2f71ee`.
