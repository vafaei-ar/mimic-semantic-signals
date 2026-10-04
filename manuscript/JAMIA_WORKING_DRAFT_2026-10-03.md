# Working manuscript draft for JAMIA

Updated: 2026-10-03

Working title: **Incremental predictive value of low-dimensional semantic scores from ICU notes: a preregistered evaluation in MIMIC-III**

Target article type: JAMIA Research and Applications

Target limits: structured abstract <=250 words; main text <=4000 words; <=4 tables; <=6 figures.

> Status: scientific working draft. References are intentionally not finalized here. Citation placeholders must be resolved from verified sources before submission. Internal RunRelay job IDs and artifact hashes should remain in the provenance supplement, not the submitted main text.

## Abstract

### Objective

To evaluate whether eight low-dimensional semantic scores derived from prospectively available intensive care unit notes improve short-horizon deterioration prediction beyond a strong structured electronic health record comparator.

### Materials and Methods

We conducted a preregistered evaluation in MIMIC-III MetaVision intensive care unit stays. At a fixed 12-hour landmark, we predicted invasive ventilation, renal replacement therapy, and ICU death during the subsequent 12 hours. The comparator included 34 physiology, laboratory, and urine features plus treatment/support, documentation-behavior, and note-context variables. The primary augmentation added eight Open-Jev semantic scores from the most recent eligible bedside note. Performance was estimated using frozen patient-grouped cross-validation and 500-replicate patient-cluster refit bootstrap intervals. Prespecified secondary analyses compared lexical TF-IDF features and alternative semantic instruments. Post-registration analyses examined score alignment, semantic-only discrimination, and nested comparator strength.

### Results

The primary Open-Jev delta AUROC was -0.00005 for ventilation (95% interval -0.02173 to 0.01910), -0.00079 for renal replacement therapy (-0.00323 to 0.00275), and -0.00212 for ICU death (-0.00802 to 0.00531). Within a common logistic model family, TF-IDF produced small positive increments while Open-Jev increments were negative for all three outcomes. In exploratory decomposition, the ventilation Open-Jev increment was +0.02032 over physiology alone, +0.01137 after treatment/support variables, and -0.00172 after documentation-behavior variables were added. ICU-death semantic scores had standalone AUROC 0.65682 but no positive incremental AUROC even over physiology alone.

### Discussion

Low-dimensional semantic scores contained some prognostic information but generally added little discrimination after structured clinical state and documentation processes were represented.

### Conclusion

Narrative information was not absent, but compact semantic compression did not consistently improve discrimination beyond a rich structured EHR comparator.

## Background and Significance

Clinical notes contain observations, assessments, treatment response, uncertainty, and plans that are incompletely represented in structured electronic health record data. Language models create a practical opportunity to transform this narrative information into structured features for risk prediction. A clinically appealing strategy is to reduce notes to a small set of semantic measurements, such as clinician concern, worsening trajectory, respiratory or hemodynamic concern, treatment response, escalation consideration, diagnostic uncertainty, and reassuring stability.

This approach has potential advantages over high-dimensional text representations. A compact semantic vector is easier to inspect, store, audit, and potentially transport across downstream tasks. Its predictive value, however, depends on whether the selected dimensions preserve information that is not already available in structured physiology, treatment state, and documentation behavior. A semantic score can be prognostic on its own yet add little after those variables are included.

Early exploratory analyses in this project suggested positive semantic increments for some deterioration outcomes. A subsequent integrity review identified methodological problems in that earlier analysis lineage, including source-system mixing, note-selection rules, semantic aggregation errors, and an insufficient structured comparator. Those results were placed on hold, the analysis was rebuilt, and the corrected v2.1 study was registered before its predictive performance was examined.

The primary objective of the registered analysis was to estimate the incremental discrimination provided by eight Open-Jev semantic scores beyond a rich structured comparator for three short-horizon intensive care unit outcomes. Secondary analyses examined alternative semantic instruments, lexical text representation, timing and endpoint sensitivities, source-specific replication, and a patient-shuffled semantic negative control. After the registered analyses were complete, two bounded exploratory analyses were added to clarify the null result: a label-free alignment audit and a nested comparator decomposition.

## Materials and Methods

### Study design and data source

We used MIMIC-III, a deidentified critical care database containing intensive care unit admissions from 2001 through 2012. [REFERENCE: MIMIC-III]

The corrected confirmatory populations were restricted to MetaVision stays so that structured measurement and documentation processes were source-compatible. Adults were eligible after excluding neonatal intensive care unit admissions. The prediction landmark was 12 hours after intensive care unit admission, and each outcome was assessed during the following 12 hours.

The registered analysis is available at OSF registration ahxn9, DOI 10.17605/OSF.IO/AHXN9. The repository preserves the corrected analysis code, frozen configuration, aggregate result summaries, and a manuscript-number provenance index.

### Outcomes and populations

The three confirmatory outcomes were:

1. new invasive ventilation;
2. renal replacement therapy;
3. ICU death.

The invasive-ventilation population contained 11,116 stays and 279 cases. The renal-replacement-therapy population contained 19,395 stays and 314 cases. The MetaVision ICU-death population contained 19,811 stays and 214 cases.

A separate CareVue ICU-death cohort of 25,632 stays and 306 cases was retained as a prespecified replication/sensitivity analysis rather than pooled with MetaVision.

### Structured comparator

The core structured block contained 34 variables representing demographics, recent vital signs and changes, Glasgow Coma Scale components, laboratory values, and urine output. Airway-coded verbal Glasgow Coma Scale entries were treated as missing rather than as a verbal score of 1.

The registered rich comparator additionally included pre-landmark respiratory and vasoactive support, sedative exposure, death-specific code status, documentation-behavior measures, and ordinary note context. Documentation behavior included note count, note length, category counts, and related metadata from the preceding 12 hours. Ordinary note context included note availability, selected-note age, and collapsed note category.

The primary learner was a HistGradientBoostingClassifier with prespecified settings shared across outcomes.

### Note selection and semantic representation

For each eligible stay, note identity was fixed before text processing. The primary corpus used the most recent eligible prospective bedside note and removed prespecified direct endpoint or treatment expressions without otherwise normalizing the text. Rows without an eligible note remained in the population and had semantic inputs treated as missing.

Open-Jev was the primary semantic instrument. It produced eight scores:

- overall clinician concern;
- worsening trajectory;
- respiratory concern;
- hemodynamic concern;
- poor treatment response;
- escalation considered;
- diagnostic uncertainty;
- reassuring stability.

The primary augmented model was identical to the rich structured comparator except for the addition of these eight semantic scores.

### Cross-validation and uncertainty

Patient-grouped fold assignments were frozen before predictive evaluation. The point estimate used the first of five prespecified five-fold partitions. Four additional partitions assessed sensitivity to fold assignment and refitting.

For the primary H1-H3 estimates, uncertainty was quantified using 500 valid patient-cluster bootstrap replicates of the complete repeat-1 cross-fitting procedure. Both comparator and augmented models were refit within each bootstrap replicate. We report percentile 95% intervals and do not use confirmatory p-values or binary significance classifications.

### Secondary and sensitivity analyses

Prespecified analyses included an unstripped-note Open-Jev sensitivity, Laya and DiffusionGemma semantic instruments, a six-construct subset, timing and laboratory-lag sensitivities, a broader respiratory-support endpoint, and separate CareVue ICU-death replication.

A lexical comparison used TF-IDF features in a common L2-penalized logistic-regression family. Within each training fold, the same encoded rich comparator was evaluated alone, with Open-Jev, with TF-IDF, and with both representations. This analysis was designed to compare representation types while holding the downstream learner family constant.

The registered patient-shuffled negative control reassigned complete eight-score vectors between different note-available patients within strata of structured-model risk while preserving score marginals and leaving no-note rows unchanged.

### Post-registration explanatory analyses

After the registered results were known, we performed two narrowly scoped exploratory analyses.

First, a label-free alignment audit evaluated whether semantic scores were associated with clinically corresponding structured support states and whether those associations exceeded between-patient shuffled references. Outcome labels were not read for this audit.

Second, among note-available rows only, we estimated discrimination from the eight Open-Jev scores alone. We also fit four nested HistGradientBoosting comparator levels using the same frozen populations and partitions:

- level A: the 34-feature physiology, laboratory, and urine block;
- level B: level A plus treatment/support context and death-specific code status;
- level C: level B plus documentation-behavior variables;
- level D: level C plus ordinary note context, corresponding to the registered rich comparator.

At each level, we estimated the Open-Jev delta AUROC across the five frozen partitions without a new bootstrap.

### Registered deviations

The preregistered clinician construct-validation analysis was prepared but not performed because independent qualified clinician raters and associated resources were unavailable in this single-author, unfunded study. No human ratings were collected.

The preregistered external Zigong validation was not completed as planned. The translated Open-Jev, Laya, and TF-IDF arm was not performed. A DiffusionGemma-only transport analysis was executed using a legacy frozen Zigong cohort whose note-exclusion regex was later recognized to contain specification problems. That result is retained as descriptive audit-trail evidence and is not used to support the central external-validity claim.

## Results

### Primary analyses

The rich structured comparator achieved AUROCs of 0.72468 for invasive ventilation, 0.97394 for renal replacement therapy, and 0.93338 for MetaVision ICU death.

Adding the eight Open-Jev scores changed AUROC by -0.00005 for ventilation, -0.00079 for renal replacement therapy, and -0.00212 for ICU death. The corresponding 95% refit-bootstrap intervals were -0.02173 to 0.01910, -0.00323 to 0.00275, and -0.00802 to 0.00531, respectively.

Across the five frozen patient-grouped partitions, ventilation delta AUROC ranged from -0.00551 to +0.00922, renal replacement therapy from -0.00079 to +0.00332, and ICU death from -0.00327 to +0.00390.

The registered primary analyses therefore did not show a consistent incremental discrimination gain from Open-Jev beyond the rich comparator.

### Lexical versus semantic representation

Within the common logistic-regression family, the Open-Jev increment was negative for all three outcomes: -0.00826 for ventilation, -0.00194 for renal replacement therapy, and -0.00631 for ICU death.

In the same models, TF-IDF increments were +0.00564, +0.00219, and +0.00123, respectively. Adding Open-Jev after TF-IDF reduced AUROC in all three primary analyses.

These results indicate that the bedside notes retained a small amount of residual predictive information under the common logistic specification, but that the eight-dimensional semantic representation did not preserve the same incremental discrimination.

### Registered sensitivity analyses

The prespecified semantic-instrument sensitivities did not materially change the primary conclusion.

For unstripped Open-Jev, delta AUROC was -0.01043 for ventilation, -0.00034 for renal replacement therapy, and +0.00108 for ICU death.

For Laya, delta AUROC was +0.01031 for ventilation, -0.00079 for renal replacement therapy, and +0.00141 for ICU death.

For DiffusionGemma, delta AUROC was -0.00811 for ventilation, -0.00083 for renal replacement therapy, and +0.00499 for ICU death.

All corresponding refit-bootstrap intervals included both negative and positive values. Endpoint, timing, laboratory-lag, and note-availability sensitivities likewise did not produce a reproducible positive semantic increment.

In the separate CareVue ICU-death replication, comparator AUROC was 0.93799 and comparator plus Open-Jev AUROC was 0.93544, for a delta of -0.00255 with a 95% interval of -0.00858 to 0.00812.

### Patient-shuffled negative control

The patient-shuffled semantic control did not show a reproducible positive increment. Delta AUROC was -0.01059 for ventilation, -0.00024 for renal replacement therapy, +0.00309 for MetaVision ICU death, and -0.00712 for CareVue ICU death. Each interval included both negative and positive values.

### Label-free alignment audit

Semantic and note case identifiers matched exactly in the corrected analysis files. Hemodynamic and respiratory concern scores showed stronger clinically expected associations with corresponding structured support states than did between-patient shuffled semantic vectors. This audit reduced concern about gross score-to-stay misalignment as an explanation for the null predictive results.

Reassuring stability showed weak or inconsistent alignment and was not treated as a construct-validated measurement.

### Semantic-only discrimination

Among note-available rows, the eight Open-Jev scores alone achieved AUROC 0.60257 for ventilation, 0.44790 for renal replacement therapy, and 0.65682 for MetaVision ICU death on the primary frozen partition.

The ICU-death result is particularly informative: the semantic scores carried standalone prognostic discrimination, yet their addition did not improve discrimination even over the physiology-only comparator.

### Comparator decomposition

For invasive ventilation, the Open-Jev delta AUROC was +0.02032 over the 34-feature physiology/laboratory/urine comparator. The increment decreased to +0.01137 after treatment/support context was added and to -0.00172 after documentation-behavior variables were added. With the registered rich comparator, the delta was -0.00005.

At the first two levels, the augmented model could also exploit semantic-score missingness as a marker of note availability because note-context variables had not yet been added to the comparator. The positive early-level increments therefore cannot be attributed entirely to semantic content.

For renal replacement therapy, the Open-Jev delta AUROC remained close to zero at every comparator level: -0.00054, -0.00070, +0.00014, and -0.00079 from levels A through D.

For MetaVision ICU death, the corresponding values were -0.00428, -0.00280, -0.00394, and -0.00212. Despite semantic-only AUROC 0.65682, the eight scores did not improve discrimination even over the physiology-only comparator.

## Discussion

In this preregistered corrected analysis, eight low-dimensional semantic scores derived from bedside ICU notes did not consistently improve short-horizon deterioration discrimination beyond a rich structured EHR comparator. The result was stable across three outcomes, alternative semantic instruments, text-processing sensitivities, timing analyses, a separate CareVue death replication, and patient-shuffled negative controls.

The findings do not imply that the notes contained no predictive information. In the common logistic family, TF-IDF produced small positive increments for all three outcomes while Open-Jev increments were negative. The semantic-only analysis also showed standalone discrimination for ventilation and especially ICU death. The central result is therefore better interpreted as a failure of incremental value after low-dimensional compression and structured adjustment, rather than absence of prognostic information in clinical text.

The exploratory comparator decomposition clarifies this distinction. For ventilation, semantic augmentation improved discrimination over physiology alone, but the increment attenuated after treatment/support variables were added and disappeared after documentation behavior was represented. Because semantic missingness also exposed note availability before note-context variables entered the comparator, the early positive increment cannot be assigned solely to semantic content. The pattern is consistent with a substantial portion of apparent narrative value reflecting treatment state, documentation process, or closely related clinical context.

The ICU-death analysis showed a different form of redundancy. The semantic scores achieved standalone AUROC 0.65682 among note-available rows but did not improve AUROC even when added only to the core physiology/laboratory comparator. In that outcome, prognostic information represented by the semantic scores appears largely recoverable from structured clinical state. Renal replacement therapy showed little standalone semantic discrimination and little incremental value at any comparator level.

These results also help explain why earlier exploratory analyses in the project appeared more favorable. The integrity review identified several analysis choices that could inflate or distort apparent semantic value, including source-system mixing, note-selection differences, semantic aggregation errors, and a thinner comparator. After those issues were corrected and the analysis was registered, the estimated increments moved toward zero. This history is scientifically relevant because incremental-value studies are especially sensitive to comparator definition. A text-derived feature can appear useful against an incomplete baseline while adding little once treatment state, documentation behavior, and other available clinical information are represented.

The H5 comparison suggests a performance-compression tradeoff. TF-IDF is high dimensional and not readily interpretable at the patient level, but it retained small positive predictive increments under the same logistic learner in which the eight Open-Jev scores did not. Compressing a note to eight predefined dimensions may improve auditability and dimensionality while discarding weak, distributed lexical signals that remain useful for prediction. Human construct validation was not available in this study, so the eight dimensions should not be described as clinically validated or inherently interpretable.

The study has several strengths. The corrected analysis was preregistered before v2.1 predictive performance was examined. Patient grouping, note identity, model settings, uncertainty estimation, and major sensitivity analyses were frozen in advance. The complete analysis lineage, including failed pre-result checks and post-registration deviations, is preserved. The label-free alignment audit further reduces concern that the null result arose from a gross score-to-stay join error.

Several limitations are important. First, MIMIC-III is a single-center database from an older clinical era, and the confirmatory populations were restricted to MetaVision. Second, the structured comparators were already highly discriminative for renal replacement therapy and ICU death, leaving limited headroom for AUROC improvement. Third, clinician construct validation was not performed, so semantic-score meaning was not independently confirmed by human raters. Fourth, external narrative transport was not completed as registered. The available DiffusionGemma Zigong result used a legacy cohort with a recognized note-exclusion specification problem and is not used as central evidence. Fifth, the comparator decomposition and semantic-only analyses were conducted after the registered results were known and are exploratory. Finally, discrimination does not capture every potential use of structured semantic features, including auditing, retrieval, cohort characterization, or other tasks outside short-horizon risk prediction.

The practical implication is narrow. For the three deterioration outcomes studied here, adding eight fixed semantic scores to a strong EHR model did not improve discrimination in a reproducible way. Researchers evaluating language-model-derived EHR features should therefore compare them with strong structured and documentation-process baselines and should distinguish standalone prognostic association from incremental predictive value.

## Conclusion

In corrected preregistered MIMIC-III analyses, eight low-dimensional semantic scores derived from prospective ICU notes did not consistently improve discrimination for invasive ventilation, renal replacement therapy, or ICU death beyond a rich structured EHR comparator. Clinical text still contained residual predictive information, particularly in high-dimensional lexical form, but the compact semantic representation did not preserve a consistent incremental advantage. For ventilation, apparent benefit over physiology alone disappeared after documentation behavior was represented; for ICU death, semantic scores were prognostic on their own but redundant with structured clinical state. These findings define a practical limit of low-dimensional semantic compression for short-horizon ICU deterioration prediction.

## Data and code availability

MIMIC-III data are available through PhysioNet subject to its credentialing and data-use requirements. Restricted clinical notes and row-level derived data are not redistributed by this repository. Analysis code, frozen configuration, aggregate result summaries, and provenance documentation are available in the public project repository.

The Zigong source data are subject to their original access and use conditions. The modified Zigong transport result is not central evidence for this manuscript.

## Funding

No external funding supported this study.

## Competing interests

[AUTHOR TO COMPLETE ACCORDING TO JOURNAL POLICY.]

## AI-assisted tools

[AUTHOR TO COMPLETE ACCORDING TO THE TARGET JOURNAL'S CURRENT DISCLOSURE POLICY. Describe factual tool use transparently. Do not use this placeholder in the submitted version.]

## Ethics / data-use statement

[FINALIZE FROM MIMIC-III/PHYSIONET TERMS AND ANY APPLICABLE INSTITUTIONAL DETERMINATION. Do not infer or invent an IRB determination.]

## Candidate tables and figures

### Main Table 1
Cohort characteristics and primary structured-comparator performance for the three MetaVision outcomes.

### Main Table 2
Registered H1-H3 primary results: comparator AUROC, augmented AUROC, delta AUROC, and 95% refit-bootstrap interval.

### Main Table 3
Common-logistic H5 representation comparison: comparator, Open-Jev, TF-IDF, TF-IDF + Open-Jev.

### Main Figure 1
Forest plot of registered delta AUROC estimates and 95% refit-bootstrap intervals for:
- H1-H3 primary Open-Jev;
- principal H6 alternative instruments;
- CareVue ICU-death replication;
- H7 patient-shuffled controls.

### Main Figure 2
Exploratory comparator decomposition showing Open-Jev delta AUROC across comparator levels A-D for ventilation, RRT, and ICU death, with five-partition ranges.

### Supplement
Complete H4-H7 sensitivity tables; timing and laboratory-lag results; label-free alignment audit; semantic-only results; H8/H9 deviation records; registration/provenance table; OSF attachment verification.

## References to resolve before submission

Use verified references only. At minimum the final manuscript will need references for:
- MIMIC-III;
- clinical prediction reporting standards, including TRIPOD+AI;
- TRIPOD-LLM;
- prior work on clinical-note prediction and language models;
- prior work on documentation behavior as predictive signal;
- the specific semantic/decision-model methods if citable publications or model papers exist.

Do not fabricate references from model cards or repository names. Verify DOI/PMID and claim support before inserting them.
