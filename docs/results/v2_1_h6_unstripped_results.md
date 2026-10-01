# v2.1 registered H6 unstripped-note sensitivity results

Date updated: 2026-10-01

This document records the registered H6 sensitivity in which the same primary rich-comparator HGB analysis is repeated with Open-Jev scores from the frozen full unstripped predictor note rather than the language-stripped note. The cohorts, comparator, five frozen patient-grouped partitions, HGB specification, and 500-valid-replicate patient-cluster refit-bootstrap procedure are otherwise unchanged.

| Outcome | N | Cases | Notes scored | Comparator AUROC | + unstripped Open-Jev AUROC | Delta AUROC | 95% refit-bootstrap interval | Delta AUPRC |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Invasive ventilation | 11,116 | 279 | 4,499 | 0.72468 | 0.71424 | -0.01043 | -0.02177 to 0.01773 | +0.00081 |
| RRT | 19,395 | 314 | 7,709 | 0.97394 | 0.97360 | -0.00034 | -0.00308 to 0.00310 | +0.00187 |
| ICU death, MetaVision | 19,811 | 214 | 7,889 | 0.93338 | 0.93447 | +0.00108 | -0.00911 to 0.00602 | -0.01028 |

The five frozen-partition Delta AUROC estimates were:

- invasive ventilation: -0.01043, -0.00195, -0.01594, -0.00598, +0.00241;
- RRT: -0.00034, +0.00156, +0.00182, +0.00011, +0.00223;
- ICU death, MetaVision: +0.00108, +0.00626, -0.00020, +0.00128, -0.00051.

All three refit bootstraps completed 500/500 valid replicates with zero replacement replicates.

## Descriptive comparison with the registered stripped-note primary analyses

| Outcome | Stripped-note primary Delta AUROC | Unstripped-note H6 Delta AUROC | Difference in point estimate |
|---|---:|---:|---:|
| Invasive ventilation | -0.00005 | -0.01043 | -0.01038 |
| RRT | -0.00079 | -0.00034 | +0.00045 |
| ICU death, MetaVision | -0.00212 | +0.00108 | +0.00320 |

The unstripped-note sensitivity does not reveal a consistent positive incremental-discrimination pattern that was removed by treatment/outcome-language stripping. Ventilation becomes more negative on the primary partition, RRT remains close to zero, and MetaVision ICU death shifts slightly positive but remains close to zero with variation across frozen partitions. These are descriptive H6 sensitivity estimates, not separate hypothesis-test decisions.

## Canonical RunRelay provenance

- invasive ventilation: job `N5N7T9V2`; artifact SHA-256 `17bc887375edef3b7222ef00cfb94f1663e338147c2835230c0dd69f08b3fde0`.
- RRT: job `R8N4T9V2`; artifact SHA-256 `510a94d30a6f55b718380ca64ca7fdfdef19dc400ecc15a686ea81dc47e8cf8a`.
- MetaVision ICU death: job `T4N7R9V2`; artifact SHA-256 `79717c4c236867a697e373c83b545b7cf42ae1609f461cf171d5333141232a5f`.

The registered stripped-note H1-H3 estimates remain the primary analyses. This H6 document is a prespecified sensitivity result.
