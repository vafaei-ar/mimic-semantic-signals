# v2.1 registered H5 lexical comparison results

Date updated: 2026-09-30

H5 compares four models within the same registered L2-penalized logistic-regression family and the same five frozen patient-grouped partitions: comparator, comparator + Open-Jev, comparator + TF-IDF, and comparator + TF-IDF + Open-Jev. TF-IDF preprocessing is fitted within each training fold only. Results are estimation-first; no p-values or binary significance rule are used.

| Outcome | Comparator | + Open-Jev | + TF-IDF | + TF-IDF + Open-Jev | Open-Jev increment | TF-IDF increment | Open-Jev after TF-IDF |
|---|---:|---:|---:|---:|---:|---:|---:|
| Invasive ventilation | 0.71425 | 0.70599 | 0.71989 | 0.71316 | -0.00826 | +0.00564 | -0.00673 |
| RRT | 0.95853 | 0.95659 | 0.96072 | 0.95919 | -0.00194 | +0.00219 | -0.00153 |
| ICU death, MetaVision | 0.90460 | 0.89828 | 0.90582 | 0.90002 | -0.00631 | +0.00123 | -0.00580 |

Across all five frozen partitions:

- ventilation Open-Jev minus comparator remained negative; TF-IDF generally exceeded the Open-Jev increment; Open-Jev after TF-IDF remained negative.
- RRT Open-Jev minus comparator ranged from -0.00396 to -0.00172; TF-IDF minus comparator ranged from +0.00219 to +0.00331; Open-Jev after TF-IDF ranged from -0.00364 to -0.00144.
- MetaVision ICU death Open-Jev minus comparator ranged from -0.00631 to -0.00305; TF-IDF minus comparator ranged from +0.00123 to +0.00248; Open-Jev after TF-IDF ranged from -0.00581 to -0.00317.

## Interpretation

Within the registered common logistic family, the lexical TF-IDF representation had a larger AUROC increment than the Open-Jev scores in all three outcomes on the primary partition, and the same directional contrast persisted across the frozen partitions. Adding Open-Jev to the TF-IDF model reduced AUROC in all three primary analyses and remained negative across the frozen partitions for RRT and MetaVision ICU death.

These are registered secondary estimates. They should be interpreted as a representation comparison within a deliberately common model family, not as a claim that logistic regression is the optimal predictive model for any outcome.

## Canonical RunRelay provenance

- Ventilation H5: job `AJM7R5K9`; artifact SHA-256 `babe8078e8018f187adb050b05b5031aeff3b7a6d1099d3e20f22c2b2657d6e0`.
- RRT H5: job `H8N4T7V2`; artifact SHA-256 `00185d1b9a28dd9ada787eb55a8c18b6ef4c53bda9934dac4b052b5fb0076e36`.
- MetaVision ICU-death H5: job `F6N7R5K9`; artifact SHA-256 `ab8e58b43b6b058a9f72968f5ea7ba16ecadbc228e6bb56e546e1362f3657222`.
