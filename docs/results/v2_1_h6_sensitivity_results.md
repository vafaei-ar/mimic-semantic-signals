# v2.1 registered H6 sensitivity results

Updated: 2026-10-01

H6 is a registered non-directional sensitivity family. Results are reported descriptively and do not modify the frozen primary estimand or model specification.

## Unstripped-note Open-Jev sensitivity

| Outcome | Comparator AUROC | Augmented AUROC | Delta AUROC | 95% refit-bootstrap interval | Delta AUPRC |
|---|---:|---:|---:|---:|---:|
| Invasive ventilation | 0.72468 | 0.71424 | -0.01043 | [-0.02177, +0.01773] | +0.00081 |
| RRT | 0.97394 | 0.97360 | -0.00034 | [-0.00308, +0.00310] | +0.00187 |
| ICU death, MetaVision | 0.93338 | 0.93447 | +0.00108 | [-0.00911, +0.00602] | -0.01028 |

Five frozen-partition delta-AUROC estimates:

- invasive ventilation: -0.01043, -0.00195, -0.01594, -0.00598, +0.00241;
- RRT: -0.00034, +0.00156, +0.00182, +0.00011, +0.00223;
- MetaVision ICU death: +0.00108, +0.00626, -0.00020, +0.00128, -0.00051.

All three analyses completed 500/500 valid patient-cluster refit-bootstrap replicates with zero replacements.

Interpretation: using the full unstripped note does not reveal a consistently larger positive semantic increment than the stripped-note primary analyses. Ventilation is more negative on the primary partition, RRT remains near zero, and ICU death is near zero with mixed split-stability estimates.

Canonical RunRelay provenance:

- ventilation: job `N5N7T9V2`, artifact SHA-256 `17bc887375edef3b7222ef00cfb94f1663e338147c2835230c0dd69f08b3fde0`;
- RRT: job `R8N4T9V2`, artifact SHA-256 `510a94d30a6f55b718380ca64ca7fdfdef19dc400ecc15a686ea81dc47e8cf8a`;
- MetaVision ICU death: job `T4N7R9V2`, artifact SHA-256 `79717c4c236867a697e373c83b545b7cf42ae1609f461cf171d5333141232a5f`.

## Alternative semantic instrument: Laya

### Invasive ventilation

Registered Laya environment preflight confirmed package version 0.3.4, model repository `convaiinnovations/laya-typed-decisions`, revision `f9ab0b228f0fc0f14d873dbc99038f135c2da1b2`, model weights present, semantic-schema SHA-256 `72763082c314a4542817ccfcd42d2b10d9446fc8e84c3391a2140790b2483623`, 600-token chunks, 100-token overlap, and maximum 8 chunks.

Inference completed 4,499/4,499 frozen ventilation notes with zero failures and without reading outcome labels.

Ventilation evaluation:

- comparator AUROC: 0.72468;
- comparator + Laya AUROC: 0.73499;
- delta AUROC: +0.01031;
- 95% patient-cluster refit-bootstrap interval: [-0.01595, +0.02519];
- five frozen-partition delta-AUROCs: +0.01031, -0.00048, +0.01376, +0.00414, +0.00729;
- comparator AUPRC: 0.08127;
- augmented AUPRC: 0.08426;
- delta AUPRC: +0.00299;
- 500/500 valid bootstrap replicates, zero replacements.

This is a registered H6 sensitivity estimate. It is not used to redefine the primary Open-Jev result and is not interpreted with a binary significance rule.

Canonical RunRelay provenance:

- Laya environment preflight: job `W6N7R9T2`, artifact SHA-256 `c80df5c823c52ffdca170dbc170bf185ef9b01d8291014e24a9f2b546c9a934a`;
- ventilation inference: job `X7N4R9T2`, artifact SHA-256 `da82e74714b0c768d44080ae90347ae15db4f5fbff4daebf148effc2070ecde1`;
- ventilation evaluation: job `Y8N4R9T2`, artifact SHA-256 `0dc443a57a2b69063a126b4dc56bef81d9faf6bd89e867321fc31b2222e9b3fc`.

## Next registered H6 step

Proceed sequentially with Laya RRT inference/evaluation and then Laya MetaVision ICU-death inference/evaluation. After the three-outcome Laya arm is frozen, move to the registered DiffusionGemma arm, followed by endpoint, timing, and CareVue sensitivity analyses.
