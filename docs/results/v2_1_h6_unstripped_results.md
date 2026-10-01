# v2.1 registered H6 unstripped-note sensitivity results

Date updated: 2026-09-30

H6 asks whether the registered primary estimates materially change when the full unstripped predictor note is used instead of the stripped note. The same rich comparator, HistGradientBoosting specification, frozen patient-grouped partitions, and 500-valid-replicate patient-cluster refit-bootstrap procedure are retained.

| Outcome | Comparator AUROC | + unstripped Open-Jev AUROC | Delta AUROC | 95% refit-bootstrap interval | Delta AUPRC |
|---|---:|---:|---:|---:|---:|
| Invasive ventilation | 0.72468 | 0.71424 | -0.01043 | [-0.02177, +0.01773] | +0.00081 |
| RRT | 0.97394 | 0.97360 | -0.00034 | [-0.00308, +0.00310] | +0.00187 |
| ICU death, MetaVision | 0.93338 | 0.93447 | +0.00108 | [-0.00911, +0.00602] | -0.01028 |

Five frozen-partition delta-AUROC estimates:

- invasive ventilation: -0.01043, -0.00195, -0.01594, -0.00598, +0.00241;
- RRT: -0.00034, +0.00156, +0.00182, +0.00011, +0.00223;
- MetaVision ICU death: +0.00108, +0.00626, -0.00020, +0.00128, -0.00051.

All three analyses produced 500/500 valid refit-bootstrap replicates with zero deterministic replacements.

## Interpretation

The unstripped-note sensitivity does not reveal a consistent positive semantic increment that was removed by prespecified language stripping. Ventilation becomes more negative than the stripped-note primary estimate, RRT remains very close to zero, and MetaVision ICU death is slightly positive on the primary partition but varies around zero across the frozen partitions.

Because H6 is non-directional and estimation-first, these results should be reported descriptively rather than classified by interval crossing or significance.

## Canonical RunRelay provenance

- Ventilation: job `N5N7T9V2`; artifact `outputs/multitask_benchmark/h6_unstripped_openjev_v2_1_ventilation.json`; SHA-256 `17bc887375edef3b7222ef00cfb94f1663e338147c2835230c0dd69f08b3fde0`.
- RRT: job `R8N4T9V2`; artifact `outputs/multitask_benchmark/h6_unstripped_openjev_v2_1_rrt.json`; SHA-256 `510a94d30a6f55b718380ca64ca7fdfdef19dc400ecc15a686ea81dc47e8cf8a`.
- MetaVision ICU death: job `T4N7R9V2`; artifact `outputs/multitask_benchmark/h6_unstripped_openjev_v2_1_death.json`; SHA-256 `79717c4c236867a697e373c83b545b7cf42ae1609f461cf171d5333141232a5f`.
