# Supplementary Material: JAMIA submission candidate

**Manuscript:** Incremental predictive value of predefined semantic scores from ICU notes beyond documentation-aware EHR models: a preregistered evaluation

Updated: 2026-11-23

## Supplementary Methods

### S1. Corrected v2.1 analysis lineage

An earlier exploratory analysis lineage produced larger positive semantic increments. Before those results were used for publication, an integrity review identified several design and implementation problems, including mixing CareVue and MetaVision documentation/source processes, note-selection rules that changed note availability, asymmetric case/control exclusions, incorrect cross-chunk semantic aggregation, and an insufficient structured comparator. The earlier positive estimates are not used as confirmatory evidence.

The corrected v2.1 analysis used source-compatible cohorts, adult/NICU eligibility rules, fixed note identities before stripping, corrected max/min semantic aggregation, a 34-feature structured block, prespecified treatment and documentation context, fixed patient-grouped partitions, and patient-cluster refit bootstrap uncertainty. The corrected analysis was registered on OSF before predictive performance was examined: registration `ahxn9`, DOI `10.17605/OSF.IO/AHXN9`.

### S2. Cohorts and prediction horizon

The prediction landmark was 12 hours after ICU admission. Primary outcomes were assessed during the subsequent 12 hours.

| Outcome | Source | Stays | Cases | Controls | Eligible-note rows |
|---|---|---:|---:|---:|---:|
| Invasive ventilation | MetaVision | 11,116 | 279 | 10,837 | 4,499 |
| Renal replacement therapy | MetaVision | 19,395 | 314 | 19,081 | 7,709 |
| ICU death | MetaVision | 19,811 | 214 | 19,597 | 7,889 |
| ICU death replication | CareVue | 25,632 | 306 | 25,326 | 23,272 |

MetaVision and CareVue death analyses were not pooled.

### S3. Structured predictor definitions

#### S3.1 Core 34-feature block

The registered core block contained the following 34 features in fixed order:

1. age at ICU admission, capped at 90 years;
2. sex;
3. heart rate, last value in prior 6 hours;
4. heart-rate change across prior 6 hours;
5. systolic blood pressure, last;
6. systolic blood-pressure change;
7. diastolic blood pressure, last;
8. diastolic blood-pressure change;
9. mean arterial pressure, last;
10. mean arterial-pressure change;
11. respiratory rate, last;
12. respiratory-rate change;
13. oxygen saturation, last;
14. oxygen-saturation change;
15. temperature, last;
16. temperature change;
17. Glasgow Coma Scale eye, last;
18. Glasgow Coma Scale verbal, last;
19. Glasgow Coma Scale motor, last;
20. lactate, last in prior 24 hours;
21. creatinine, last;
22. blood urea nitrogen, last;
23. white blood-cell count, last;
24. hemoglobin, last;
25. platelet count, last;
26. sodium, last;
27. potassium, last;
28. bicarbonate, last;
29. chloride, last;
30. glucose, last;
31. total bilirubin, last;
32. international normalized ratio, last;
33. pH, last;
34. net urine output in prior 6 hours.

Airway-coded verbal GCS values (`1.0 ET/Trach` and `No Response-ETT`) were treated as missing rather than as verbal GCS=1.

#### S3.2 Treatment/support context

Six-hour treatment/support context included:

- last FiO2;
- last oxygen flow;
- high-flow oxygen present;
- noninvasive ventilation present;
- vasoactive infusion present;
- number of vasoactive agents;
- sedative/analgesic infusion present;
- number of sedative/analgesic agents.

For ICU death only, code-status availability and limitation categories were additionally included.

#### S3.3 Documentation behavior

Twelve-hour documentation-behavior variables were:

- note count;
- total note characters;
- latest-note characters;
- number of note-category groups represented;
- nursing note count;
- physician note count;
- respiratory note count;
- other note count.

#### S3.4 Ordinary note context

Ordinary note context consisted of note availability, selected-note age at the prediction landmark, and collapsed note category (nursing, physician, respiratory, other, or no note).

### S4. Semantic instruments and text policy

The primary instrument was Open-Jev evaluated on the prespecified text corpus after endpoint-language removal. The Open-Jev model card reports training on public banking messages, sentiment reviews and BoolQ question answering. The Laya model card identifies four nonclinical typed-decision workflows (agent traces, customer service, invoices, and security incidents). These are out-of-domain applications for ICU narrative. Neither model card documents fine-tuning on MIMIC notes, although absence of documented training does not prove exclusion from all upstream encoder data. The present study did not independently evaluate clinician agreement or general-domain-to-clinical transfer. Eight constructs were scored:

1. overall clinician concern;
2. worsening trajectory;
3. respiratory concern;
4. hemodynamic concern;
5. poor treatment response;
6. escalation considered;
7. diagnostic uncertainty;
8. reassuring stability.

For multi-chunk notes, the registered aggregation used the maximum chunk score for the seven concern-oriented constructs and the minimum chunk score for reassuring stability.

Laya and DiffusionGemma were prespecified alternative instruments. The primary analysis used the same fixed note identities across representations.

#### S4.1 Frozen instrument versions

| Instrument | Frozen implementation |
|---|---|
| Open-Jev | `com-kotobalabs/open-jev-deberta-v3-large`, revision `19bf9a64815add579fbf6c907bef584d9277a8e4`; typed-decisions commit `10d7834d3b99041f890db4615fb38ef95ced50cc`; 220-token chunks, 40-token overlap, maximum 8 chunks |
| Laya | package version 0.3.4; checkpoint `convaiinnovations/laya-typed-decisions`, frozen revision `f9ab0b228f0fc0f14d873dbc99038f135c2da1b2`; 600-token chunks, 100-token overlap, maximum 8 chunks |
| DiffusionGemma | `google/diffusiongemma-26B-A4B-it`, revision `f7f5b7f5fa82ffc52addd066915886d497f5517b`; native Transformers BF16 backend |

The eight question definitions and model revisions were specified before outcome evaluation. Open-Jev and Laya treated each construct as a yes/no typed decision and used the model probability assigned to the affirmative response as the construct score. DiffusionGemma instead used prompted zero-shot 0-1 support scores; these were not treated as calibrated typed-decision probabilities. Across note chunks, the seven concern-oriented constructs used the maximum score and reassuring stability used the minimum score.

#### S4.2 Frozen semantic questions and response criteria

The same question schema was used for all eight score dimensions. Open-Jev and Laya returned the probability assigned to the affirmative response; DiffusionGemma returned a prompted 0-1 support score. The wording below is copied from the frozen `src/semantic_schema.py`.

| Construct | Frozen question | Affirmative criterion | Negative criterion |
|---|---|---|---|
| Overall clinician concern | Does `clinical_note` indicate that the clinician is concerned that the patient's overall clinical condition is worsening or may worsen soon? | The note communicates a meaningful current concern about deterioration or impending worsening. | The note is reassuring, neutral, or does not communicate concern about deterioration. |
| Worsening trajectory | Does `clinical_note` describe a worsening clinical trajectory compared with an earlier assessment or expected course? | The note explicitly or clearly implies that the patient's trajectory is getting worse. | The note describes stability, improvement, or no clear worsening trajectory. |
| Respiratory concern | Does `clinical_note` express concern about respiratory deterioration, increasing work of breathing, respiratory fatigue, oxygenation, or need for more respiratory support? | A respiratory problem is presented as clinically concerning or worsening. | Respiratory status is reassuring, unchanged, or not a meaningful concern in the note. |
| Hemodynamic concern | Does `clinical_note` express concern about circulatory or hemodynamic deterioration, perfusion, hypotension, shock, or possible need for vasoactive support? | The note communicates meaningful concern about circulation, perfusion, or hemodynamic instability. | Hemodynamics are reassuring, unchanged, or not a meaningful concern in the note. |
| Poor treatment response | Does `clinical_note` indicate that the patient is not responding as expected to current treatment or support? | The note indicates inadequate, incomplete, or disappointing response to treatment or support. | The note indicates adequate response, expected course, or gives no evidence of poor response. |
| Escalation considered | Does `clinical_note` indicate that escalation of monitoring, treatment, respiratory support, vasoactive support, or level of care is being considered? | The note states or clearly implies that stronger monitoring, treatment, support, or level of care is being considered. | No escalation is being considered, or the note supports continuing the current plan without escalation. |
| Diagnostic uncertainty | Does `clinical_note` indicate meaningful unresolved diagnostic uncertainty that affects current clinical management? | The note describes unresolved diagnostic uncertainty that is clinically consequential. | There is no meaningful unresolved diagnostic uncertainty affecting management. |
| Reassuring stability | Does `clinical_note` explicitly indicate that the patient's clinical condition is stable or reassuring without a new acute concern? | The note is explicitly reassuring or describes stable clinical status without a new acute concern. | The note communicates deterioration, concern, uncertainty, or does not clearly support reassuring stability. |

These definitions were fixed before outcome analysis. They are operational model questions, not clinician-validated constructs; registered clinician validation was not completed.


### S5. Cross-validation and uncertainty

Five deterministic patient-grouped 5-fold partitions were frozen before predictive evaluation. Partition 1 was the primary point estimate; partitions 2-5 assessed refit/split stability.

For H1-H3 and the registered H6/H7 inferential analyses, uncertainty used 500 valid patient-cluster bootstrap replicates of the full repeat-1 cross-fitting procedure. The comparator and augmented model were refit inside each bootstrap replicate. Reported intervals are percentile 95% intervals.

The post-registration semantic-only and comparator-decomposition analyses reused the five frozen partitions and did not run a new bootstrap.

## Supplementary Results

### Table S1. Five frozen-partition H1-H3 delta AUROC

| Outcome | Repeat 1 | Repeat 2 | Repeat 3 | Repeat 4 | Repeat 5 |
|---|---:|---:|---:|---:|---:|
| Ventilation | -0.00005 | -0.00551 | -0.00505 | -0.00537 | +0.00922 |
| RRT | -0.00079 | +0.00071 | +0.00003 | -0.00024 | +0.00332 |
| ICU death, MetaVision | -0.00212 | +0.00390 | -0.00327 | +0.00103 | -0.00042 |

### Table S2. Registered H4 six-construct analysis

| Outcome | Delta AUROC | 95% refit-bootstrap interval |
|---|---:|---:|
| Ventilation | -0.01342 | -0.02301 to +0.01523 |
| RRT | -0.00049 | -0.00317 to +0.00282 |
| ICU death, MetaVision | -0.00472 | -0.00840 to +0.00530 |

### Table S3. Registered common-logistic representation comparison

| Outcome | Open-Jev increment | TF-IDF increment | Open-Jev after TF-IDF |
|---|---:|---:|---:|
| Ventilation | -0.00826 | +0.00564 | -0.00673 |
| RRT | -0.00194 | +0.00219 | -0.00153 |
| ICU death, MetaVision | -0.00631 | +0.00123 | -0.00580 |

The H5 comparison holds the downstream model family constant. It should not be numerically conflated with the HGB comparator-decomposition analysis.

The registered common-logistic TF-IDF and Open-Jev comparisons report point differences only, without complete-refit uncertainty intervals. Positive TF-IDF point differences are descriptive and should not be interpreted as established incremental performance gains.

### Table S4. Registered H6 sensitivity results

| Instrument/sensitivity | Outcome | Delta AUROC | 95% interval |
|---|---|---:|---:|
| Unstripped Open-Jev | Ventilation | -0.01043 | -0.02177 to +0.01773 |
| Unstripped Open-Jev | RRT | -0.00034 | -0.00308 to +0.00310 |
| Unstripped Open-Jev | ICU death, MetaVision | +0.00108 | -0.00911 to +0.00602 |
| Laya | Ventilation | +0.01031 | -0.01595 to +0.02519 |
| Laya | RRT | -0.00079 | -0.00278 to +0.00302 |
| Laya | ICU death, MetaVision | +0.00141 | -0.00660 to +0.00728 |
| DiffusionGemma | Ventilation | -0.00811 | -0.02030 to +0.01445 |
| DiffusionGemma | RRT | -0.00083 | -0.00283 to +0.00244 |
| DiffusionGemma | ICU death, MetaVision | +0.00499 | -0.00654 to +0.00652 |
| Broad respiratory-support endpoint | Ventilation | -0.00643 | -0.01879 to +0.01046 |
| CHARTEVENTS storetime | Ventilation | +0.00668 | -0.02079 to +0.02286 |
| CHARTEVENTS storetime | RRT | +0.00053 | -0.00307 to +0.00261 |
| CHARTEVENTS storetime | ICU death, MetaVision | -0.00207 | -0.00923 to +0.00689 |
| 1-hour laboratory lag | Ventilation | +0.00717 | -0.02333 to +0.01829 |
| 1-hour laboratory lag | RRT | +0.00069 | -0.00331 to +0.00331 |
| 1-hour laboratory lag | ICU death, MetaVision | +0.00153 | -0.00936 to +0.00618 |
| 2-hour laboratory lag | Ventilation | +0.00216 | -0.02269 to +0.01911 |
| 2-hour laboratory lag | RRT | -0.00110 | -0.00294 to +0.00309 |
| 2-hour laboratory lag | ICU death, MetaVision | -0.00415 | -0.00849 to +0.00655 |
| CareVue replication | ICU death, CareVue | -0.00255 | -0.00858 to +0.00812 |

The explicit-intubation ventilation endpoint was empirically identical to the primary H1 endpoint. The note-availability/storetime fallback sensitivity selected exactly the same notes as the primary analysis in all three MetaVision outcomes and therefore required no semantic rerun.

### Table S5. Registered H7 patient-shuffled negative controls

| Outcome/source | Comparator AUROC | Shuffled + comparator AUROC | Delta AUROC | 95% interval |
|---|---:|---:|---:|---:|
| Ventilation, MetaVision | 0.72468 | 0.71408 | -0.01059 | -0.02851 to +0.01432 |
| RRT, MetaVision | 0.97394 | 0.97369 | -0.00024 | -0.00269 to +0.00313 |
| ICU death, MetaVision | 0.93338 | 0.93647 | +0.00309 | -0.00663 to +0.00599 |
| ICU death, CareVue | 0.93799 | 0.93087 | -0.00712 | -0.00784 to +0.00882 |

Complete semantic score vectors were shuffled only between different patients within structured-risk deciles. No-note rows were left unchanged.

### Table S6. Label-free semantic alignment audit

| Outcome | Construct-state pair | Real Spearman rho | Shuffled rho |
|---|---|---:|---:|
| Ventilation | Hemodynamic concern vs vasoactive active | +0.183 | +0.015 |
| Ventilation | Respiratory concern vs high-flow | +0.177 | +0.003 |
| Ventilation | Respiratory concern vs NIV | +0.081 | -0.003 |
| Ventilation | Respiratory concern vs FiO2 | +0.061 | +0.027 |
| RRT | Hemodynamic concern vs vasoactive active | +0.137 | +0.001 |
| RRT | Respiratory concern vs high-flow | +0.129 | +0.012 |
| RRT | Respiratory concern vs NIV | +0.106 | +0.000 |
| RRT | Respiratory concern vs FiO2 | +0.077 | -0.009 |
| ICU death | Hemodynamic concern vs vasoactive active | +0.145 | -0.019 |
| ICU death | Respiratory concern vs high-flow | +0.128 | +0.006 |
| ICU death | Respiratory concern vs NIV | +0.103 | -0.007 |
| ICU death | Respiratory concern vs FiO2 | +0.084 | -0.023 |

Semantic/note case identifiers matched exactly in all three primary cohorts, and the between-patient shuffled reference had zero same-patient donor assignments. The number of chunks scored was strongly associated with note length (rho 0.974-0.983 across outcomes). Reassuring stability showed weak or inconsistent expected alignment and is not treated as construct-validated.

### Table S7. Semantic-only discrimination on note-available rows

| Outcome | Note-available n | Cases | Repeat 1 AUROC | Repeat 2 | Repeat 3 | Repeat 4 | Repeat 5 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Ventilation | 4,499 | 135 | 0.60257 | 0.55253 | 0.53014 | 0.57123 | 0.57373 |
| RRT | 7,709 | 143 | 0.44790 | 0.45285 | 0.47306 | 0.48725 | 0.49073 |
| ICU death, MetaVision | 7,889 | 83 | 0.65682 | 0.70011 | 0.67292 | 0.68995 | 0.69343 |

The RRT semantic-only AUROC was below 0.5 in all five prespecified partitions (0.448-0.491). This direction could reflect inverse ranking of cases and controls, model misspecification, or sampling variation. The same patients contributed to all partitions, and we did not estimate a confidence interval for the inverse association. The outcome label was fixed and predictions were not inverted after evaluation.

### Table S8. Post-registration comparator decomposition: Open-Jev delta AUROC across five frozen partitions

| Outcome | Level | Repeat 1 | Repeat 2 | Repeat 3 | Repeat 4 | Repeat 5 |
|---|---|---:|---:|---:|---:|---:|
| Ventilation | A structured 34 | +0.02032 | +0.01225 | +0.00268 | +0.00706 | +0.00346 |
| Ventilation | B + treatment/support | +0.01137 | +0.00261 | +0.00579 | +0.00301 | +0.00017 |
| Ventilation | C + documentation behavior | -0.00172 | -0.00154 | +0.00849 | -0.00017 | +0.00452 |
| Ventilation | D + note context | -0.00005 | -0.00551 | -0.00505 | -0.00537 | +0.00922 |
| RRT | A structured 34 | -0.00054 | -0.00002 | -0.00024 | +0.00153 | +0.00160 |
| RRT | B + treatment/support | -0.00070 | +0.00065 | -0.00065 | +0.00001 | +0.00013 |
| RRT | C + documentation behavior | +0.00014 | -0.00028 | -0.00056 | -0.00053 | +0.00062 |
| RRT | D + note context | -0.00079 | +0.00071 | +0.00003 | -0.00024 | +0.00332 |
| ICU death | A structured 34 | -0.00428 | +0.00293 | +0.00020 | -0.00239 | -0.00339 |
| ICU death | B + treatment/support | -0.00280 | +0.00345 | -0.00630 | -0.00411 | -0.00083 |
| ICU death | C + documentation behavior | -0.00394 | +0.00194 | +0.00113 | -0.00270 | -0.00087 |
| ICU death | D + note context | -0.00212 | +0.00390 | -0.00327 | +0.00103 | -0.00042 |

No new bootstrap or confirmatory p-value was used. The ventilation level-A/B increments cannot be attributed solely to semantic content because semantic missingness also encodes note availability before documentation/note-context variables are included.


### Table S9. Registered H1-H3 secondary proper-scoring and calibration metrics

Lower Brier score and log loss are better. Delta values are augmented minus comparator. Bootstrap intervals come from the same 500-valid-replicate patient-cluster refit bootstrap used for the registered primary analysis.

| Outcome | Metric | Comparator | + Open-Jev | Delta (95% refit-bootstrap interval) |
|---|---|---:|---:|---:|
| Ventilation | Brier score | 0.02411 | 0.02407 | -0.00004 (-0.00020 to +0.00024) |
| Ventilation | Log loss | 0.11582 | 0.11553 | -0.00029 (-0.00124 to +0.00387) |
| RRT | Brier score | 0.01287 | 0.01298 | +0.00011 (-0.00047 to +0.00038) |
| RRT | Log loss | 0.04640 | 0.04713 | +0.00073 (-0.00154 to +0.00181) |
| ICU death, MetaVision | Brier score | 0.00912 | 0.00911 | -0.00001 (-0.00023 to +0.00019) |
| ICU death, MetaVision | Log loss | 0.04310 | 0.04384 | +0.00074 (-0.00097 to +0.00167) |

Primary-partition calibration slopes were 0.615 versus 0.634 for ventilation, 0.713 versus 0.699 for RRT, and 0.762 versus 0.748 for ICU death. Quantile-bin expected calibration error was 0.01119 versus 0.01147, 0.00493 versus 0.00480, and 0.00582 versus 0.00591, respectively. Calibration-in-the-large estimates were 0.636 versus 0.676 for ventilation, 0.615 versus 0.605 for RRT, and 1.201 versus 1.240 for ICU death. Across the prespecified decision-curve thresholds, the 95% bootstrap interval for incremental net benefit spanned zero for every outcome and threshold.

### Table S10. Exploratory note-available subgroup using frozen full-cohort OOF predictions

This post-registration analysis restricts the already-generated full-cohort out-of-fold predictions to rows with an eligible note. The comparator and augmented models were **not** refit in the subgroup. The table therefore evaluates whether the primary full-cohort predictions show a different incremental pattern among the patients for whom semantic scores existed; it is not a new subgroup-trained model.

| Outcome | Note-available n (cases) | Comparator AUROC, repeat 1 | + Open-Jev AUROC, repeat 1 | Delta AUROC, repeat 1 | Delta AUROC across five frozen partitions | Delta AUPRC, repeat 1 |
|---|---:|---:|---:|---:|---|---:|
| Ventilation | 4,499 (135) | 0.697 | 0.708 | +0.0109 | -0.0158, +0.0026, +0.0076, +0.0109, +0.0279 | +0.0055 |
| RRT | 7,709 (143) | 0.976 | 0.974 | -0.0012 | -0.0012, -0.0008, -0.0006, +0.0000, +0.0043 | -0.0039 |
| ICU death, MetaVision | 7,889 (83) | 0.947 | 0.940 | -0.0076 | -0.0076, -0.0031, +0.0000, +0.0001, +0.0068 | +0.0069 |

For ventilation, the primary-partition subgroup estimate was positive, but its direction was not stable across the five frozen partitions. RRT and ICU death likewise showed no stable positive incremental pattern. This analysis therefore does not support the hypothesis that the full-cohort null was simply dilution by rows without an eligible note.

## Registered deviations

### S9. H8 clinician construct validation not performed

The H8 design and 200-note sample were frozen before any human ratings. Three blinded rater packets were prepared locally, but no ratings were collected. The analysis was not performed because this single-author, unfunded study did not have the independent qualified clinician raters and associated logistical/governance resources required by the registered design. The decision therefore did not depend on H8 results.

No claim of human-validated construct validity or clinical interpretability is made.

### S10. H9 external-validation partial execution

The registration prespecified two Zigong narrative arms: a translated-text Open-Jev/Laya/TF-IDF arm and a native-Chinese DiffusionGemma arm. The translated arm was not performed.

A DiffusionGemma-only transport analysis was run using the existing frozen 340-note Zigong 24-hour cohort. The legacy cohort had been selected under a note-leakage regex later recognized to contain specification problems, including an overbroad bare Chinese airway term, a generic tube-removal term, and an incorrectly escaped English ETT word-boundary expression. The existing result (AUROC 0.5546; 95% matched-set bootstrap interval 0.4796-0.6308) is retained as descriptive provenance only and is not used as completed registered external validation.

## Registration and reproducibility

The corrected MIMIC-III analysis was registered at OSF `ahxn9` before its outcome performance was evaluated. A separate exploratory extension was registered at `wmyb2`. Source definitions, analysis code, and aggregate result files are available through the project repository. The original registration files and detailed verification history remain accessible through the project record. Restricted clinical notes and patient-level predictions are not redistributed.

## Post-registration exploratory extension (separate OSF project wmyb2)

The primary preregistered H1-H3 evaluation and its results remain unchanged. The analyses summarized below were conducted after the primary results were known, using separately frozen exploratory extension specifications. The extension stopped after completion of the T1.5 analyses. These outcomes do not constitute new registered primary hypotheses or independent external replications.

### S11. Supervised text representation and fusion: methods

The T1.1 analysis fitted a supervised TF-IDF/logistic score inside training folds and supplied that score as one added predictor to the structured HistGradientBoosting model. T1.2 used a pinned BGE-large sentence embedding, combined chunks without outcome labels, and fitted a training-only logistic supervised score. T1.2b fitted 32 principal components from frozen embeddings inside the training fold and added the components directly to the structured learner. T1.4 repeated the TF-IDF analysis on unstripped source text as a sensitivity.

The held-out evaluation used the same five frozen patient-grouped outer partitions, with the first partition supplying the displayed point estimate. Patient-cluster bootstrap refits provided the reported percentile intervals for the richest comparator D. Each method retained patients without notes in the target population and used the prespecified missing-score/availability treatment. These four extensions differed in text representation and fusion, so their estimates are not interchangeable or independent replications.

### Table S11. Exploratory supervised-text augmentation at registered rich comparator D

Each cell is the primary-partition ΔAUROC followed by its 95% patient-cluster full-refit percentile interval. ΔAUROC equals text-augmented minus rich structured comparator D.

| Text representation | Invasive ventilation | RRT | ICU death, MetaVision |
|---|---|---|---|
| T1.1, stripped TF-IDF supervised scalar | −0.001370 [−0.014930, +0.014680] | −0.000680 [−0.002300, +0.002690] | +0.003390 [−0.006250, +0.007840] |
| T1.2, frozen-BGE supervised scalar | +0.001937 [−0.014232, +0.017353] | −0.000800 [−0.002648, +0.002391] | −0.000462 [−0.006327, +0.006802] |
| T1.2b, 32-component BGE early fusion | −0.002830 [−0.024938, +0.026863] | −0.000485 [−0.003479, +0.003209] | +0.000240 [−0.010065, +0.006978] |
| T1.4, unstripped TF-IDF supervised scalar | +0.003773 [−0.016243, +0.014625] | +0.000619 [−0.001953, +0.003572] | +0.003294 [−0.005525, +0.008254] |

All intervals include zero. These tests do not establish equivalence or demonstrate that all possible text representations lack predictive value. Standalone primary-partition text AUROCs among note-available stays were 0.64023/0.87350/0.85626 for supervised TF-IDF and 0.615456/0.803578/0.794347 for the frozen BGE representation (ventilation/RRT/death). These standalone results describe a different estimand from augmentation against structured comparator D.

### S12. Supervised text augmentation across structured comparator richness

Levels A through D were fixed as: A, 34 physiology, laboratory and urine predictors; B, A plus treatment/support; C, B plus documentation behavior; and D, C plus ordinary note context, including explicit note availability. T1.5 tested the two scalar supervised scores (TF-IDF and frozen BGE embedding) at all four levels across five frozen patient-grouped partitions. Complete patient-cluster refit uncertainty was calculated for A and D only, using 200 valid replicates under the frozen 72-hour timing rule.

### Table S12. T1.5 exploratory primary-partition ΔAUROC at comparator levels A and D

Each cell gives the original ΔAUROC and its 95% full-refit percentile interval. These are level-specific intervals, not a paired A-minus-D comparison.

| Outcome | Representation | Level A ΔAUROC [95% CI] | Level D ΔAUROC [95% CI] |
|---|---|---|---|
| Invasive ventilation | TF-IDF scalar | +0.022888 [−0.012831, +0.020596] | −0.001372 [−0.014735, +0.014324] |
| Invasive ventilation | BGE embedding scalar | +0.007533 [−0.012389, +0.020793] | +0.001937 [−0.012622, +0.017966] |
| RRT | TF-IDF scalar | +0.000397 [−0.002030, +0.003366] | −0.000685 [−0.001830, +0.002553] |
| RRT | BGE embedding scalar | +0.000165 [−0.002686, +0.003096] | −0.000800 [−0.002685, +0.002289] |
| ICU death | TF-IDF scalar | +0.000503 [−0.007845, +0.007828] | +0.003389 [−0.005907, +0.007898] |
| ICU death | BGE embedding scalar | −0.004681 [−0.008746, +0.006446] | −0.000462 [−0.006668, +0.006261] |

All twelve ΔAUROC intervals include zero, as do the corresponding ΔAUPRC intervals. The study did not estimate a paired A-minus-D contrast and cannot claim statistically established attenuation from comparator enrichment. In particular, the death TF-IDF point estimates did not show a monotonic decline across A-D. The five partitions are within-dataset stability checks, not independent replication cohorts.

### S13. Interpretation limits of exploratory comparator analyses

In T1.5, supervised text score functions set values to exactly zero for stays without an eligible note. Levels A and B lack an explicit `has_note` variable, whereas level C includes documentation proxies and D includes explicit note availability, age and categories. Thus, early-level text-score augmentation can partially encode *documentation availability* rather than information present in the words themselves. The design does not identify separate content and availability contributions.

For ventilation level A, the original TF-IDF point estimate was +0.022888, but the 200-replicate bootstrap mean was +0.003558 and the percentile interval was [−0.012831, +0.020596]. The observed point lies above this interval's upper percentile. A percentile interval need not contain the original estimate. Nevertheless, the displacement requires independent statistical interpretation. We preserve the prespecified estimate and interval without recentering or declaring the result positive.

The original point-estimate and bootstrap text-model pipelines also use different deterministic inner-fold seed offsets, an inherited convention visible in the source code. Both preserve patient grouping. The available aggregate data do not show how much this seed difference contributes to the ventilation discrepancy. We did not run an unregistered follow-up outcome analysis to resolve it.

The fixed 5% alert-budget analyses across T1.1-T1.4 did not demonstrate a reliable operational benefit. T1.5 did not evaluate fixed alert budgets. None of these extensions establishes prospective deployment value, external generalization, causal redundancy, or lack of all clinical usefulness for narrative-derived measurements.

### S14. Exploratory extension provenance

Primary preregistration: OSF `ahxn9` (DOI `10.17605/OSF.IO/AHXN9`). Separate exploratory extension: OSF `wmyb2`. The scientific execution remained fixed to commit `e5772f7a1a40b2368465e1b95e24a04abc98cc2a`. The canonical supplementary data are in the project result freezes and in `docs/results/v2_1_extension_t1_cross_outcome_synthesis_method_qa_2026-11-10.md` and `docs/results/v2_1_extension_t1_5_statistical_adjudication_2026-11-11.md`. The extension did not read a new independent bedside-narrative dataset. Its findings belong to the exploratory supplement and do not supersede H1-H3.
