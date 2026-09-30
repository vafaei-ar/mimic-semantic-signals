# v2.1 registered H4 six-construct results

Date updated: 2026-09-30

H4 repeats the registered rich-comparator analysis using the six state-dominant Open-Jev constructs, excluding `poor_treatment_response` and `escalation_considered`. Results are estimation-first. No p-values or binary success/failure rules are used.

| Outcome | Comparator AUROC | + six constructs AUROC | Delta AUROC | 95% refit-bootstrap interval |
|---|---:|---:|---:|---:|
| Invasive ventilation | 0.72468 | 0.71126 | -0.01342 | -0.02301 to 0.01523 |
| RRT | 0.97394 | 0.97345 | -0.00049 | -0.00317 to 0.00282 |
| ICU death, MetaVision | 0.93338 | 0.92866 | -0.00472 | -0.00840 to 0.00530 |

Five frozen-partition Delta AUROC estimates:

- ventilation: -0.01342, -0.01171, -0.00424, -0.00880, -0.00487;
- RRT: -0.00049, +0.00145, -0.00158, -0.00015, +0.00208;
- ICU death: -0.00472, +0.00323, -0.00219, +0.00063, -0.00274.

All three H4 analyses completed 500/500 valid patient-cluster refit-bootstrap replicates with zero replacements.

Primary-partition Delta AUPRC was +0.00304 for ventilation, +0.00298 for RRT, and -0.00971 for MetaVision ICU death.

## Interpretation

The six-construct state-dominant subset did not retain a clearly positive AUROC increment in any outcome. Ventilation showed negative Delta AUROC in all five frozen partitions, with a primary estimate of -0.01342, but its refit-bootstrap interval remained wide and crossed zero. RRT remained close to zero. ICU-death estimates were mixed across partitions and the primary estimate was modestly negative.

These results do not support treating the six-construct subset as a stronger predictive representation than the full eight-score set. They remain secondary registered estimates and should be reported without a binary significance label.

## Canonical RunRelay provenance

- Ventilation H4: job `5EM7R5K9`; artifact SHA-256 `f7201952d8e69e0754e375b4082a35b6538e9a8a7d300dcb89b46e57a7d3ddd8`.
- RRT H4: job `7GM7R5K9`; artifact SHA-256 `00ccf6d08b0b95c5caab22f7886c4d441e914b4534e7d8ae1ef4c05ba5baac8f`.
- MetaVision ICU-death H4: job `8HM7R5K9`; artifact SHA-256 `662cd5f1e6d84cf902867f3abf12105d3c46a2746ffc0dd341ef8446bd3478f8`.
