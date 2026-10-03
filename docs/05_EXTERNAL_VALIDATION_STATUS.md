# 05 - External validation status

Updated: 2026-10-01

## Manuscript-status override, 2026-10-03

The active manuscript interpretation has changed after external review of the executed H9 path.

The DiffusionGemma run `F2N7Q5K9` is retained as a **post-registration modified descriptive transport arm using the legacy frozen Zigong 24-hour cohort**, not as completed registered external validation. The registered translated Open-Jev/Laya/TF-IDF arm was not performed, and the legacy cohort was not rebuilt after the known leakage-screen problem was recognized.

See `docs/registration/deviation_h9_partial_execution_2026-10-03.md` for the exact deviation record. The numerical AUROC 0.5546 (95% matched-set bootstrap interval 0.4796 to 0.6308) remains in the audit trail, but Paper 1 will not rely on Zigong for its central claim and will not rerun H9 before initial submission.

Older wording below that calls this a corrected registered H9 result is preserved as execution-history context and is superseded for manuscript labeling by this override.

This report distinguishes available external datasets, historical v1 external results, and the corrected manuscript-facing transport path.

## Current status summary

| Dataset | Narrative available | Current role | Manuscript status |
|---|---|---|---|
| Zigong | Chinese nursing narratives | registered external narrative transport | corrected H9 complete; AUROC 0.5546 (95% CI 0.4796 to 0.6308) |
| eICU | no comparable bedside narrative | structured transport | v1 affected by lab-window bug; corrected rerun required if used |
| NWICU | no comparable bedside narrative | structured transport | v1 provenance; align to corrected structured lineage if used |
| MIMIC-BR | no comparable narrative | possible structured cross-country validation | pending/access dependent |
| HiRID | no comparable narrative | possible structured validation | pending/access dependent |
| SICdb | no comparable narrative | possible European structured validation | pending/access dependent |
| AmsterdamUMCdb | no comparable progress-note narrative | possible structured validation | separate access path |

## Corrected Zigong route

The old v1 Zigong narrative result is not manuscript-ready because the original leakage regex was defective.

A corrected 12-hour design was tested and found infeasible because the Zigong nursing narrative cadence is approximately daily. The frozen external design therefore uses a 24-hour ventilation horizon and within-nursing-table relative chronology.

Frozen Zigong cohort:

- 85 cases;
- 255 controls;
- 340 total notes;
- 85 matched sets;
- 1:3 case-control sampling;
- patient unique across all 340 notes;
- zero blank predictor notes;
- zero direct ventilation leakage-term hits after screening;
- case predictor narrative approximately 24 hours before the ventilation event.

Read docs/zigong_ventilation_external_protocol_v1.md.

## Bilingual semantic applicability gate

Before any Zigong outcome performance was inspected, Open-Jev, Laya, and DiffusionGemma were tested on a synthetic label-free English/Chinese semantic-consistency gate.

Only DiffusionGemma met the frozen direct-Chinese eligibility rule. Its English-Chinese Spearman correlation was 0.962, median absolute score difference was 0, and all 8 target contrasts met the strong-direction criterion.

Open-Jev and Laya did not pass the frozen direct-Chinese gate and are excluded from direct-Chinese Zigong outcome scoring.

Passing this gate establishes only minimum language/semantic applicability. It does not establish external clinical validity.

Read:

- docs/zigong_bilingual_semantic_gate_v1.md
- docs/zigong_direct_chinese_model_eligibility_freeze.md

## Frozen H9 transport analysis

The corrected Zigong external narrative transport uses DiffusionGemma only.

The transported predictor is fit on the full frozen MIMIC invasive-ventilation cohort using the eight DiffusionGemma semantic scores only. The fitted preprocessing and logistic-regression coefficients are then applied unchanged to Zigong.

No Zigong:

- model refit;
- recalibration;
- threshold selection;
- coefficient modification;
- post hoc translation;
- prompt adaptation.

Primary metric: Zigong AUROC.

Secondary metrics: AUPRC and descriptive Brier score, with 2,000 matched-set bootstrap replicates for intervals.

Because the Zigong analytic cohort has artificial 25% prevalence, AUPRC is conditional on the sampled cohort and Brier score is not population calibration.

Corrected registered H9 job `F2N7Q5K9` used the full v2.1 MIMIC ventilation cohort (11,116 stays, 279 cases) and produced AUROC **0.5546** with 95% matched-set bootstrap interval **0.4796 to 0.6308**, AUPRC 0.3030, and descriptive Brier score 0.2390. The aggregate artifact SHA-256 is `14191cbef81c49dfe266500ec9eddb322254a10d17d9d82f75a1b39bf363f57f`.

The older frozen result reporting AUROC 0.5906 is historical provenance only: its implementation trained on the obsolete 1,460-row v1 MIMIC benchmark and did not follow the frozen requirement to use the full corrected MIMIC cohort.

Read:

- docs/zigong_diffusiongemma_external_transport_protocol_v1.md
- docs/zigong_diffusiongemma_external_transport_result_freeze_v2_1.md.

## eICU

The v1 eICU implementation clipped laboratory lookback at ICU-relative hour zero, excluding 37,330 of 92,616 relevant rows that were inside the intended pre-anchor window. The old eICU transport estimate therefore cannot be used as final manuscript evidence.

A corrected structured rerun, if retained for the paper, must use the full intended lookback and a mapping frozen before transported performance is opened.

## NWICU

The eICU clipping bug does not establish that NWICU is wrong. However, the old NWICU result belongs to the v1 structured feature lineage and should be treated as provenance until aligned with the corrected v2.1 feature/model definition.

## Additional external datasets

MIMIC-BR, HiRID, SICdb, and AmsterdamUMCdb may provide useful structured transport evidence if access and mapping permit, but they do not replace an independent narrative transport test because they lack comparable bedside narrative documentation.

A second external narrative cohort would strengthen the paper if a suitable dataset and governance route become available.

## Next external-analysis order

1. corrected registered H9 Zigong transport is complete and frozen regardless of performance;
2. complete H8 human construct validation under its governance gate;
3. freeze the final H1-H9 provenance index;
4. add corrected structured transport or a second narrative cohort only as clearly labeled additional validation.
