# JAMIA submission candidate (author review required)

Updated: 2026-11-23

Working title: **Incremental predictive value of predefined semantic scores from ICU notes beyond documentation-aware EHR models: a preregistered evaluation**

Target article type: JAMIA Research and Applications

Target limits: structured abstract <=250 words; main text <=4000 words; <=4 tables; <=6 figures.

 > Status: submission-candidate draft, updated from frozen post-registration exploratory extension. Author approval, Zotero field linking, final visual inspection, and independent statistical sign-off remain pending. The scientific results, deviations, and references below have been checked against the frozen project record or verified publication metadata. Author identity and contact fields are populated from public Penn State and publication records; the competing-interest declaration, any applicable local institutional determination, and final submission confirmations remain author-completion items.

## Title page

**Title:** Incremental predictive value of predefined semantic scores from ICU notes beyond documentation-aware EHR models: a preregistered evaluation

**Author:** Alireza Vafaei Sadr, PhD, MS

**Affiliation:** Department of Public Health Sciences, Penn State College of Medicine, Hershey, Pennsylvania, USA

**Corresponding author:** Alireza Vafaei Sadr, Department of Public Health Sciences, Penn State College of Medicine, 700 HMC Crescent Road, Hershey, PA 17033, USA; asadr@pennstatehealth.psu.edu; 1-717-531-8521

**Keywords:** electronic health records; natural language processing; intensive care units; clinical prediction; machine learning

**Main-text word count:** 3,669

## Abstract

### Objective

To test whether eight low-dimensional semantic scores from prospectively available ICU notes improve short-horizon deterioration prediction beyond a strong structured electronic health record comparator.

### Materials and Methods

We conducted a preregistered MIMIC-III MetaVision study predicting invasive ventilation, renal replacement therapy, and ICU death during the 12 hours after a fixed 12-hour landmark. The comparator combined 34 physiology, laboratory, and urine features with treatment/support, documentation-behavior, and note-context variables. Eight Open-Jev scores were added to this comparator. Evaluation used frozen patient-grouped cross-validation and 500-replicate patient-cluster refit bootstrap intervals. Prespecified analyses compared TF-IDF and alternative semantic instruments.

### Results

Open-Jev delta AUROC was -0.0001 for ventilation (95% interval -0.0217 to 0.0191), -0.0008 for renal replacement therapy (-0.0032 to 0.0028), and -0.0021 for ICU death (-0.0080 to 0.0053). Delta Brier score and log loss were also near zero, with bootstrap intervals spanning both directions for all outcomes. In a common logistic model, the TF-IDF point differences were small and positive, without full-refit uncertainty intervals for that comparison. In exploratory decomposition, the ventilation Open-Jev increment decreased from +0.0203 over physiology alone to -0.0017 after documentation behavior was added. Separate exploratory supervised-text analyses did not show reliable gains over the rich comparator.

### Discussion

Semantic scores contained prognostic information but generally added little discrimination after structured clinical state and documentation processes were represented.

### Conclusion

Clinical narrative retained predictive information, but compact semantic compression did not consistently improve discrimination beyond a rich structured EHR comparator.

## Background and Significance

Clinical notes can contain findings that are incompletely represented in structured electronic health record (EHR) fields. For example, natural language processing of MIMIC-III notes has identified encephalopathy-related information in patients without corresponding structured diagnostic codes.[1] Earlier ICU studies also showed that text-derived topics or note representations can predict mortality and, in some settings, improve models based on structured physiology.[2,3] A systematic review of ICU mortality models using neural representations of clinical text found that studies combining notes with structured variables generally reported higher discrimination, but all included studies used MIMIC data, none had external validation, and the review judged the available studies to have high risk of bias.[4]

Recent work continues to test increasingly capable text models for clinical prediction. A JAMIA benchmark of long clinical documents found meaningful mortality signal across bag-of-words, neural, and instruction-tuned language-model approaches,[5] while a prospectively implemented sepsis system used a large language model to extract contextual information from notes for uncertain structured-model predictions.[6] These studies motivate a narrower question: how much information is retained when narrative text is compressed into a small set of predefined semantic measurements rather than represented at high dimensionality?

A compact semantic vector is easier to inspect, store, audit, and reuse than thousands of lexical features or a large embedding. Its predictive value, however, depends on whether the selected dimensions preserve information that is not already available in structured physiology, treatment state, and documentation behavior. A semantic score can be prognostic on its own yet add little after those variables are included.

An integrity review found source-system, note-selection, aggregation, and comparator problems in earlier exploratory analyses. We placed those results on hold, corrected the study, and registered v2.1 before examining its predictive performance.

The primary objective of the registered analysis was to estimate the incremental discrimination provided by eight Open-Jev semantic scores beyond a rich structured comparator for three short-horizon ICU outcomes. Secondary analyses examined alternative semantic instruments, lexical text representation, timing and endpoint sensitivities, source-specific replication, and a patient-shuffled semantic negative control. After the registered analyses were complete, four bounded exploratory analyses were used to clarify the null result: a label-free alignment audit, semantic-only discrimination, nested comparator decomposition, and a note-available frozen-prediction subgroup analysis.

## Materials and Methods

### Study design and data source

We used MIMIC-III, a deidentified, single-center critical care database containing detailed structured measurements and free-text clinical documentation from Beth Israel Deaconess Medical Center.[7] We selected MIMIC-III because this study required contemporaneous bedside notes before the prediction landmark. The released MIMIC-IV-Note module supplies discharge summaries and radiology reports, but not the same bedside-note corpus. The corrected confirmatory populations were restricted to MetaVision stays so that structured measurement and documentation processes were source-compatible. Adults were eligible after excluding neonatal intensive care unit admissions. The prediction landmark was 12 hours after ICU admission, and each outcome was assessed during the following 12 hours (Figure 1a).

The registered analysis is available at OSF registration ahxn9, DOI 10.17605/OSF.IO/AHXN9. The public repository (https://github.com/vafaei-ar/mimic-semantic-signals) preserves the corrected analysis code, frozen configuration, aggregate result summaries, and a manuscript-number provenance index.

### Outcomes and populations

The three confirmatory outcomes were new invasive ventilation, new renal replacement therapy (RRT), and ICU death. For ventilation and RRT, we excluded stays with recorded evidence of the respective intervention at or before the 12-hour landmark. We required outcome-free controls to remain observed throughout the subsequent 12 hours. Table 1 gives the frozen population counts and note availability. A separate CareVue ICU-death cohort of 25,632 stays and 306 cases was retained as a prespecified replication/sensitivity analysis rather than pooled with MetaVision.

**Table 1. Frozen MetaVision confirmatory cohort characteristics**

| Characteristic | Invasive ventilation (n=11,116) | RRT (n=19,395) | ICU death (n=19,811) |
|---|---:|---:|---:|
| Cases, n (%) | 279 (2.5) | 314 (1.6) | 214 (1.1) |
| Age, years, median [IQR] | 65.9 [53.3-79.0] | 66.1 [53.9-78.1] | 66.0 [53.9-78.1] |
| Male sex, n (%) | 6,003 (54.0) | 10,926 (56.3) | 11,160 (56.3) |
| Mean arterial pressure, mmHg, median [IQR] | 75 [66-86] | 75 [66-85] | 75 [66-85] |
| Lactate, mmol/L, median [IQR] | 1.6 [1.2-2.2] | 1.7 [1.2-2.4] | 1.7 [1.2-2.4] |
| Creatinine, mg/dL, median [IQR] | 1.0 [0.7-1.6] | 1.0 [0.7-1.4] | 1.0 [0.7-1.5] |
| ICU length of stay, days, median [IQR] | 2.04 [1.41-3.31] | 2.31 [1.52-4.31] | 2.31 [1.51-4.32] |
| Eligible note available, n (%) | 4,499 (40.5) | 7,709 (39.7) | 7,889 (39.8) |
| Eligible note among cases, n/N (%) | 135/279 (48.4) | 143/314 (45.5) | 83/214 (38.8) |
| Eligible note among controls, n/N (%) | 4,364/10,837 (40.3) | 7,566/19,081 (39.7) | 7,806/19,597 (39.8) |

Continuous summaries use available measurements without imputation. Nonmissing counts for mean arterial pressure were 10,910, 19,159, and 19,567; for lactate, 6,097, 13,458, and 13,790; and for creatinine, 10,913, 19,151, and 19,563, respectively. ICU length of stay is descriptive and was not used as a predictor.

### Structured comparator

The core structured block contained 34 variables representing demographics, recent vital signs and changes, Glasgow Coma Scale components, laboratory values, and urine output. Airway-coded verbal Glasgow Coma Scale entries were treated as missing rather than as a verbal score of 1.

The registered rich comparator additionally included pre-landmark respiratory and vasoactive support, sedative exposure, death-specific code status, documentation-behavior measures, and ordinary note context. The death comparator included documented code-status availability and limitation categories. We did not separately estimate the contribution of this predictor group to its high discrimination. Documentation behavior included note count, note length, category counts, and related metadata from the preceding 12 hours. Ordinary note context included note availability, selected-note age, and collapsed note category.

The primary learner was a HistGradientBoostingClassifier with prespecified settings shared across outcomes.

### Note selection and semantic representation

For each eligible stay, note identity was fixed before text processing. The primary corpus used the most recent eligible prospective bedside note and removed prespecified direct endpoint or treatment expressions without otherwise normalizing the text. Rows without an eligible note remained in the population and had semantic inputs treated as missing.

Open-Jev, an open-source DeBERTa-v3-large typed-decision model, was the primary semantic instrument.[8] It produced eight scores: overall clinician concern, worsening trajectory, respiratory concern, hemodynamic concern, poor treatment response, escalation considered, diagnostic uncertainty, and reassuring stability. Each construct was posed as a yes/no typed decision, and the Open-Jev score was the model probability assigned to the affirmative response. Notes were processed in overlapping chunks; chunk scores were combined by taking the maximum for the seven concern-oriented constructs and the minimum for reassuring stability. The Laya typed-decision model[9] used the same question schema and aggregation rule. DiffusionGemma[10] was prompted to return a zero-shot 0-1 support score for each construct, with the same across-chunk aggregation; these prompted scores were not treated as calibrated typed-decision probabilities. The exact frozen question wording, response criteria, and instrument versions are provided in Supplementary Section S4. The primary augmented model was identical to the rich structured comparator except for the addition of these eight scores. The released Open-Jev model card describes training on public banking-intent, movie-review, and question-answering datasets, rather than clinician-rated ICU notes. The Laya model card describes nonclinical decision-workflow training data. We found no documented MIMIC fine-tuning in those cards, but cannot independently exclude overlap in upstream encoder pretraining. We did not evaluate clinical-domain construct validity.

### Cross-validation and uncertainty

Patient-grouped fold assignments were frozen before predictive evaluation. The point estimate used the first of five prespecified five-fold partitions. Four additional partitions assessed sensitivity to fold assignment and refitting.

For the three primary outcome analyses, uncertainty was quantified using 500 valid patient-cluster bootstrap replicates of the complete repeat-1 cross-fitting procedure. Both comparator and augmented models were refit within each bootstrap replicate. We report percentile 95% intervals and do not use confirmatory p-values or binary significance classifications. Registered secondary metrics included AUPRC, Brier score, log loss, calibration-in-the-large, calibration slope, expected calibration error, and decision-curve net benefit.

### Secondary and sensitivity analyses

Prespecified analyses included an unstripped-note Open-Jev sensitivity, the Laya typed-decision model[9] and DiffusionGemma[10] as alternative semantic instruments, a six-construct subset, timing and laboratory-lag sensitivities, a broader respiratory-support endpoint, and separate CareVue ICU-death replication.

A lexical comparison used term frequency-inverse document frequency (TF-IDF) features in a common L2-penalized logistic-regression family. Within each training fold, the same encoded rich comparator was evaluated alone, with Open-Jev, with TF-IDF, and with both representations. This analysis was designed to compare representation types while holding the downstream learner family constant.

The registered patient-shuffled negative control reassigned complete eight-score vectors between different note-available patients within strata of structured-model risk while preserving score marginals and leaving no-note rows unchanged.

### Post-registration explanatory analyses

After the registered results were known, we performed four narrowly scoped exploratory analyses.

First, a label-free alignment audit evaluated whether semantic scores were associated with clinically corresponding structured support states and whether those associations exceeded between-patient shuffled references. Outcome labels were not read for this audit.

Second, among note-available rows only, we estimated discrimination from the eight Open-Jev scores alone.

Third, we fit four nested HistGradientBoosting comparator levels using the same frozen populations and partitions: level A, the 34-feature physiology/laboratory/urine block; level B, level A plus treatment/support context and death-specific code status; level C, level B plus documentation-behavior variables; and level D, level C plus ordinary note context, corresponding to the registered rich comparator. At each level, we estimated the Open-Jev delta AUROC across the five frozen partitions without a new bootstrap.

Fourth, we performed a post-registration exploratory subgroup analysis restricted to patients with an eligible note. This analysis did not refit any model. It restricted the already-frozen full-cohort out-of-fold comparator and augmented predictions to rows with `has_note=1` and summarized performance across the five frozen partitions.

### Subsequent post-registration supervised-text extensions

Under a separate, exploratory OSF extension (wmyb2), we compared supervised TF-IDF scores, frozen BGE embeddings reduced to a supervised scalar, 32-component embedding early fusion, and an unstripped-note TF-IDF sensitivity. A comparator-richness extension evaluated supervised TF-IDF and embedding scores against structured levels A through D. All models retained frozen patient-grouped partitions and the registered post-extension stopping rule. These analyses were not part of the primary preregistration.

### Registered deviations

The preregistered clinician construct-validation analysis was prepared but not performed because independent qualified clinician raters and associated resources were unavailable in this single-author, unfunded study. No human ratings were collected.

The preregistered external validation using the separate Chinese Zigong cohort was not completed as planned. The translated Open-Jev, Laya, and TF-IDF arm was not performed. A DiffusionGemma-only transport analysis was executed using a legacy frozen Zigong cohort whose note-exclusion regex was later recognized to contain specification problems. That result is retained as descriptive audit-trail evidence and is not used to support the central external-validity claim.

### Reporting framework

Manuscript reporting was cross-checked against TRIPOD+AI, the current reporting guideline for prediction-model studies using regression or machine-learning methods,[11] and TRIPOD-LLM, which extends reporting guidance to studies that use large language models.[12]

## Results

### Primary analyses

The rich structured comparator achieved AUROCs of 0.725 for invasive ventilation, 0.974 for RRT, and 0.933 for MetaVision ICU death. Adding the eight Open-Jev scores changed AUROC by -0.0001, -0.0008, and -0.0021, respectively (Table 2 and Figure 2). All three refit-bootstrap intervals included both negative and positive values. Across the five frozen patient-grouped partitions, ventilation delta AUROC ranged from -0.0055 to +0.0092, RRT from -0.0008 to +0.0033, and ICU death from -0.0033 to +0.0039.

**Table 2. Registered primary Open-Jev results**

| Outcome | Comparator AUROC | + Open-Jev AUROC | Delta AUROC | 95% refit-bootstrap interval | Delta AUPRC |
|---|---:|---:|---:|---:|---:|
| Invasive ventilation | 0.72468 | 0.72463 | -0.00005 | -0.02173 to +0.01910 | +0.00387 |
| Renal replacement therapy | 0.97394 | 0.97315 | -0.00079 | -0.00323 to +0.00275 | -0.00048 |
| ICU death, MetaVision | 0.93338 | 0.93126 | -0.00212 | -0.00802 to +0.00531 | +0.00087 |

Registered proper-scoring and calibration metrics gave the same overall interpretation. Delta Brier score was -0.00004 for ventilation (95% refit-bootstrap interval -0.00020 to +0.00024), +0.00011 for RRT (-0.00047 to +0.00038), and -0.00001 for ICU death (-0.00023 to +0.00019). Delta log loss was -0.00029 (-0.00124 to +0.00387), +0.00073 (-0.00154 to +0.00181), and +0.00074 (-0.00097 to +0.00167), respectively. Calibration slopes changed from 0.615 to 0.634, 0.713 to 0.699, and 0.762 to 0.748. Incremental decision-curve net-benefit intervals spanned zero at every prespecified threshold (Supplementary Table S9).


### Lexical versus semantic representation

Within the common logistic-regression family, TF-IDF produced small positive AUROC point differences and Open-Jev produced negative differences (Table 3). These registered estimates did not have complete-refit uncertainty intervals, so they do not demonstrate a reliable incremental advantage for either representation. The separate exploratory full-refit TF-IDF analyses also did not show a consistent gain over the rich comparator (Supplementary Table S11).

**Table 3. Registered representation comparison within a common logistic model family**

| Outcome | Comparator AUROC | + Open-Jev | + TF-IDF | + TF-IDF + Open-Jev | Open-Jev increment | TF-IDF increment | Open-Jev after TF-IDF |
|---|---:|---:|---:|---:|---:|---:|---:|
| Invasive ventilation | 0.714 | 0.706 | 0.720 | 0.713 | -0.0083 | +0.0056 | -0.0067 |
| Renal replacement therapy | 0.959 | 0.957 | 0.961 | 0.959 | -0.0019 | +0.0022 | -0.0015 |
| ICU death, MetaVision | 0.905 | 0.898 | 0.906 | 0.900 | -0.0063 | +0.0012 | -0.0058 |

### Registered sensitivity analyses

The prespecified semantic-instrument, endpoint, and prospective-timing sensitivities did not materially change the primary conclusion. For unstripped Open-Jev, delta AUROC was -0.0104 for ventilation, -0.0003 for RRT, and +0.0011 for ICU death. For Laya, the corresponding estimates were +0.0103, -0.0008, and +0.0014. For DiffusionGemma, they were -0.0081, -0.0008, and +0.0050. All corresponding refit-bootstrap intervals included both negative and positive values. Endpoint, timing, laboratory-lag, and note-availability sensitivities likewise did not produce a reproducible positive semantic increment.

In the separate CareVue ICU-death replication, comparator AUROC was 0.938 and comparator plus Open-Jev AUROC was 0.935, for a delta of -0.0026 with a 95% interval of -0.0086 to +0.0081.

### Patient-shuffled negative control

The patient-shuffled semantic control did not show a reproducible positive increment. Delta AUROC was -0.0106 for ventilation, -0.0002 for RRT, +0.0031 for MetaVision ICU death, and -0.0071 for CareVue ICU death. Each interval included both negative and positive values.

### Label-free alignment audit

Semantic and note case identifiers matched exactly in the corrected analysis files. Hemodynamic and respiratory concern scores showed stronger clinically expected associations with corresponding structured support states than did between-patient shuffled semantic vectors. This audit reduced concern about gross score-to-stay misalignment as an explanation for the null predictive results. Reassuring stability showed weak or inconsistent alignment and was not treated as a construct-validated measurement.

### Semantic-only discrimination

Among note-available rows, the eight Open-Jev scores alone achieved AUROC 0.603 for ventilation, 0.448 for RRT, and 0.657 for MetaVision ICU death on the primary frozen partition. The RRT semantic-only AUROC remained below 0.5 in all five prespecified partitions (0.448-0.491). This directional result suggests that the model scores ranked some RRT cases below controls, but the partitions used overlapping patients and no uncertainty interval was estimated for an inverse association. Outcome orientation was fixed in advance and predictions were not inverted after inspection. The ICU-death result is informative because the semantic scores carried standalone prognostic discrimination, yet their addition did not improve discrimination even over the physiology-only comparator.

### Note-available frozen-prediction subgroup

Restricting the already-frozen full-cohort out-of-fold predictions to patients with eligible notes did not reveal a stable positive incremental effect (Supplementary Table S10). For ventilation, primary-partition delta AUROC was +0.0109, but the five-partition values ranged from -0.0158 to +0.0279. For RRT, the primary estimate was -0.0012 and the five-partition range was -0.0012 to +0.0043. For ICU death, the primary estimate was -0.0076 and the range was -0.0076 to +0.0068. No model was refit for this exploratory subgroup analysis.

### Comparator decomposition

For invasive ventilation, the Open-Jev delta AUROC was +0.0203 over the 34-feature physiology/laboratory/urine comparator. The increment decreased to +0.0114 after treatment/support context was added and to -0.0017 after documentation-behavior variables were added. With the registered rich comparator, the delta was less than 0.0001 in magnitude. The five frozen partitions all produced positive ventilation increments at levels A and B; level C and D results were mixed.

At levels A and B, the augmented model could also exploit semantic-score missingness as a marker of note availability because note-context variables had not yet been added to the comparator. The positive early-level increments therefore cannot be attributed entirely to semantic content.

For RRT, the primary-partition Open-Jev delta AUROC remained close to zero at every comparator level: -0.0005, -0.0007, +0.0001, and -0.0008 from levels A through D. For MetaVision ICU death, the corresponding values were -0.0043, -0.0028, -0.0039, and -0.0021. Despite semantic-only AUROC 0.657, the eight scores did not improve discrimination even over the physiology-only comparator.

### Exploratory supervised-text extensions

Later post-registration TF-IDF, BGE embedding-scalar, 32-component embedding early-fusion, and unstripped TF-IDF experiments did not demonstrate reliable incremental AUROC beyond the rich structured comparator across the three outcomes. Their full-refit intervals included zero (Supplementary Table S11). Comparator-richness analyses also found no reliable positive increment at either the thin or rich comparator. These analyses cannot isolate narrative content from note availability, especially where thin comparators lacked documentation indicators (Supplementary Tables S12 and S13).

## Discussion

In this preregistered corrected analysis, eight low-dimensional semantic scores derived from bedside ICU notes did not consistently improve short-horizon deterioration discrimination beyond a rich structured EHR comparator. The result was similar across three outcomes, alternative semantic instruments, text-processing sensitivities, timing analyses, a separate CareVue death replication, and patient-shuffled negative controls.

This finding differs from much of the earlier ICU-note prediction literature, where note-derived representations often improved discrimination when added to structured variables.[2-4] The systematic review by Vagliano et al also found important limitations in that literature, including reliance on MIMIC, limited calibration reporting, no external validation, and high risk of bias across included studies.[4] Our analysis addresses a different representation question: whether a small set of predefined semantic scores retains incremental information after a deliberately strong structured and documentation-aware comparator.

The notes themselves were not devoid of predictive signal. TF-IDF produced small positive point differences in the prespecified common-logistic analysis, but these descriptive contrasts did not establish a reliable benefit. The semantic-only analysis showed standalone discrimination for ventilation and especially ICU death. This distinction is consistent with recent clinical-text benchmarks showing that high-dimensional lexical or language-model representations can extract meaningful predictive information from long clinical documents.[5] The central result is therefore a loss of incremental predictive value after low-dimensional semantic compression and structured adjustment, not absence of prognostic information in clinical text.

The exploratory comparator decomposition helps explain why a thinner baseline can make semantic augmentation appear more useful. For ventilation, Open-Jev improved discrimination over physiology alone, the increment attenuated after treatment/support variables were added, and it disappeared after documentation behavior was represented. Because semantic missingness also exposed note availability before note-context variables entered the comparator, the early positive increment cannot be assigned solely to semantic content. The pattern is consistent with treatment state, documentation process, note availability, and semantic content carrying overlapping predictive information.

This interpretation is consistent with work treating documentation behavior itself as a clinical signal. The CONCERN early-warning system uses nursing surveillance documentation patterns to estimate deterioration risk and was evaluated in a multisite pragmatic cluster-randomized trial.[13] A separate analysis found that a deterioration-prediction framework based on nursing documentation patterns reproduced and generalized across a large set of US hospitals,[14] and a systematic review of ICU prediction studies identified documentation frequency among the nursing-data modalities used for outcome prediction.[15] More broadly, missingness and measurement patterns in EHR data can themselves be informative about clinical state and clinician behavior.[16] These findings reinforce the need to distinguish narrative semantic content from the process by which clinical information is measured and documented.

The ICU-death analysis showed a different form of redundancy. The semantic scores achieved standalone AUROC 0.657 among note-available rows but did not improve AUROC even when added only to the core physiology/laboratory comparator. In that outcome, prognostic information represented by the semantic scores appears largely recoverable from structured clinical state. RRT semantic-only AUROCs were below 0.5 across all five partitions. We did not invert predictions after analysis, and this pattern does not by itself establish a stable reverse predictive effect. Adding the scores to structured comparators produced increments close to zero.

The findings do not argue against all uses of language models in clinical prediction. Other systems use text selectively or at higher dimensionality and have reported improved performance, including a prospectively implemented sepsis system that applied an LLM to uncertain structured-model predictions.[6] Our result is narrower: eight fixed semantic dimensions did not provide a reproducible incremental discrimination advantage for these three short-horizon ICU outcomes once a rich comparator was used.

The earlier exploratory estimates changed after correction of source-system, note-selection, aggregation, and comparator problems. This illustrates why incremental-value estimates require a clinically credible comparator and a transparent analysis lineage.

The common-logistic comparison raises a possible compression tradeoff. TF-IDF is high dimensional and difficult to interpret at the patient level. Its small positive AUROC point differences, however, lack inferential intervals in this analysis. We cannot conclude that lexical features add reliable discrimination or that compression caused a measurable loss. Human construct validation was not available, so these dimensions should not be described as clinically validated or inherently interpretable.

Assessment of added predictive value should consider scoring and calibration alongside AUROC.[17] Brier score, log loss, calibration, and decision-curve results showed no consistent additional benefit. A recent JAMIA multimodal study also found limited risk-prediction gains from adding radiology reports and imaging to structured data.[18] Its modalities, tasks, and methods differ from our fixed bedside-note semantic representation, but its findings constrain the novelty of a generic null result.

The corrected study preregistered its populations, patient grouping, notes, models, uncertainty procedure, and major sensitivities. A label-free audit reduced concern about gross score-to-stay misalignment.

This single-center MIMIC-III study used older MetaVision data and high-performing structured comparators for RRT and death. The comparator calibration slopes (0.615, 0.713, and 0.762) were below one, indicating imperfect probability calibration despite high discrimination. We did not isolate the contribution of code status to death prediction. The ventilation increment interval still allows a modest benefit and does not establish equivalence. We could not perform blinded clinician construct validation or complete registered external narrative validation. The legacy Zigong transport result had a note-exclusion specification problem and is not external-validation evidence. The decomposition and all supervised-text extensions are exploratory. The zero-for-no-note supervised scores could encode documentation availability when the comparator lacked an explicit note indicator. The exploratory ventilation thin-comparator TF-IDF result had a point estimate outside its percentile bootstrap interval. We report both the original estimate and interval with their interpretation limits in the supplement. Other possible semantic-feature uses were outside our prediction study.

For the outcomes studied here, adding eight fixed semantic scores to a strong EHR model did not improve discrimination in a reproducible way. Evaluation of text-derived EHR features should therefore distinguish standalone prognostic association from incremental predictive value and should compare narrative representations against strong structured and documentation-process baselines.

## Conclusion

In corrected preregistered MIMIC-III analyses, eight low-dimensional semantic scores derived from prospective ICU notes did not consistently improve discrimination for invasive ventilation, RRT, or ICU death beyond a rich structured EHR comparator. Some text-based representations showed descriptive prognostic associations, but neither the primary semantic representation nor the exploratory supervised-text extensions demonstrated a consistent incremental advantage over the rich structured comparator. For ventilation, apparent benefit over physiology alone disappeared after documentation behavior was represented; for ICU death, semantic scores were prognostic on their own but redundant with structured clinical state.

## Data and code availability

MIMIC-III data are available through PhysioNet subject to credentialing and the MIMIC data-use agreement.[7] Restricted clinical notes and row-level derived data are not redistributed by this repository. Analysis code, frozen configuration, aggregate result summaries, and provenance documentation are available in the public project repository.

The Zigong source data are subject to their original access and use conditions. The modified Zigong transport result is not central evidence for this manuscript.

## Ethics statement

The MIMIC-III project was approved by the institutional review boards of Beth Israel Deaconess Medical Center and the Massachusetts Institute of Technology; the requirement for individual patient consent was waived because the project did not affect clinical care and protected health information was deidentified.[7] This secondary analysis used deidentified MIMIC-III data under PhysioNet credentialing and its data-use agreement. [AUTHOR: add any applicable local institutional determination if one exists.]

## Funding

No external funding supported this study.

## Competing interests

[AUTHOR TO COMPLETE BEFORE SUBMISSION.]

## Acknowledgments and AI-assisted tools

OpenAI ChatGPT was used for code generation and review, organization of analysis documentation, literature-search support, drafting and editing manuscript text, and preparation of reproducible figure code. Anthropic Claude was used for independent code, study-design, and manuscript review. The author specified the scientific questions, made and adjudicated the analysis decisions, reviewed AI-assisted code and recommendations, verified manuscript-facing numerical results against frozen aggregate artifacts, verified cited references, and takes responsibility for the final manuscript. No AI system is listed as an author.

## References

1. Ariño H, Bae SK, Chaturvedi J, et al. Identifying encephalopathy in patients admitted to an intensive care unit: going beyond structured information using natural language processing. *Front Digit Health*. 2023;5:1085602. doi:10.3389/fdgth.2023.1085602
2. Lehman LW, Saeed M, Long W, et al. Risk stratification of ICU patients using topic models inferred from unstructured progress notes. *AMIA Annu Symp Proc*. 2012;2012:505-511. PMID:23304322
3. Mahbub M, Srinivasan S, Danciu I, et al. Unstructured clinical notes within the 24 hours since admission predict short, mid & long-term mortality in adult ICU patients. *PLoS One*. 2022;17(1):e0262182. doi:10.1371/journal.pone.0262182
4. Vagliano I, Dormosh N, Rios M, et al. Prognostic models of in-hospital mortality of intensive care patients using neural representation of unstructured text: a systematic review and critical appraisal. *J Biomed Inform*. 2023;146:104504. doi:10.1016/j.jbi.2023.104504
5. Yoon WJ, Chen S, Gao Y, et al. LCD benchmark: long clinical document benchmark on mortality prediction for language models. *J Am Med Inform Assoc*. 2025;32(2):285-295. doi:10.1093/jamia/ocae287
6. Shashikumar SP, Mohammadi S, Krishnamoorthy R, et al. Development and prospective implementation of a large language model based system for early sepsis prediction. *NPJ Digit Med*. 2025;8(1):290. doi:10.1038/s41746-025-01689-w
7. Johnson AEW, Pollard TJ, Shen L, et al. MIMIC-III, a freely accessible critical care database. *Sci Data*. 2016;3:160035. doi:10.1038/sdata.2016.35
8. com-kotobalabs. open-jev-deberta-v3-large [model card]. Hugging Face. https://huggingface.co/com-kotobalabs/open-jev-deberta-v3-large. Accessed October 4, 2026.
9. ConvAI Innovations. Laya typed-decisions [model card]. Hugging Face. https://huggingface.co/convaiinnovations/laya-typed-decisions. Accessed October 4, 2026.
10. Google. diffusiongemma-26B-A4B-it [model card]. Hugging Face. https://huggingface.co/google/diffusiongemma-26B-A4B-it. Accessed October 4, 2026.
11. Collins GS, Moons KGM, Dhiman P, et al. TRIPOD+AI statement: updated guidance for reporting clinical prediction models that use regression or machine learning methods. *BMJ*. 2024;385:e078378. doi:10.1136/bmj-2023-078378
12. Gallifant J, Afshar M, Ameen S, et al. The TRIPOD-LLM reporting guideline for studies using large language models. *Nat Med*. 2025;31(1):60-69. doi:10.1038/s41591-024-03425-5
13. Rossetti SC, Dykes PC, Knaplund C, et al. Real-time surveillance system for patient deterioration: a pragmatic cluster-randomized controlled trial. *Nat Med*. 2025;31(6):1895-1902. doi:10.1038/s41591-025-03609-7
14. Wan YKJ, Abdelrahman SE, Facelli JC, et al. Conceptual framework for prediction models of patient deterioration based on nursing documentation patterns: reproducibility and generalizability with a large number of hospitals across the United States. *J Biomed Inform*. 2025;169:104887. doi:10.1016/j.jbi.2025.104887
15. Kim M, Park S, Kim C, Choi M. Diagnostic accuracy of clinical outcome prediction using nursing data in intensive care patients: a systematic review. *Int J Nurs Stud*. 2023;138:104411. doi:10.1016/j.ijnurstu.2022.104411
16. Singh J, Sato M, Ohkuma T. On missingness features in machine learning models for critical care: observational study. *JMIR Med Inform*. 2021;9(12):e25022. doi:10.2196/25022
17. Pencina MJ, D'Agostino RB, Vasan RS. Statistical methods for assessment of added usefulness of new biomarkers. *Clin Chem Lab Med*. 2010;48(12):1703-1711. doi:10.1515/CCLM.2010.340
18. Peng C, Lyu M, Chen Z, Wu Y. Less can be better: decomposing clinical data modalities in large language model-based healthcare applications. *J Am Med Inform Assoc*. 2026;33(11):2147-2159. doi:10.1093/jamia/ocag146

## Figure legends

### Figure 1. Preregistered study design and semantic-score augmentation

**Legend.** **a,** Adults in the MetaVision ICU cohorts of MIMIC-III were evaluated at a fixed 12-hour landmark after ICU admission. The study used structured measurements and the latest eligible pre-landmark bedside note. Before semantic scoring, the primary corpus removed prespecified direct endpoint and treatment expressions. The study evaluated new invasive ventilation, renal replacement therapy (RRT), and ICU death during the subsequent 12 hours. **b,** The rich structured HistGradientBoosting comparator contained 34 core physiologic, laboratory, and urine features, plus treatment/support context, documentation-behavior measures, and ordinary note context. The augmented model added eight predefined Open-Jev semantic scores to the same comparator. Cohort sizes were 11,116 stays (279 events) for ventilation, 19,395 (314 events) for RRT, and 19,811 (214 deaths) for ICU death. CareVue ICU death was evaluated separately and not pooled with MetaVision. This conceptual diagram does not represent a patient inclusion flow.

**Alt text:** Two-part diagram. Panel a shows ICU admission, the 12-hour landmark, and the subsequent 12-hour outcome period. Panel b shows eligible MetaVision ICU stays, structured and bedside-note inputs, the rich structured comparator, addition of eight predefined semantic scores, and three separately assessed outcomes.

### Figure 2. Registered incremental discrimination from semantic-score augmentation

**Legend.** Points show the original primary-partition change in area under the receiver operating characteristic curve (ΔAUROC), defined as the Open-Jev-augmented model minus the rich structured comparator. Horizontal whiskers show two-sided 95% source-patient-cluster full-refit-bootstrap percentile intervals with 500 valid replicates per outcome. The dashed vertical line indicates zero incremental AUROC. Ventilation ΔAUROC was −0.00005 (95% CI, −0.02173 to +0.01910), RRT was −0.00079 (−0.00323 to +0.00275), and ICU death was −0.00212 (−0.00802 to +0.00531). All intervals include zero. Four additional frozen patient-grouped partitions were stability checks, not independent external-validation cohorts or part of the displayed intervals. These intervals do not establish equivalence.

**Alt text:** Three-row forest plot of incremental AUROC. Ventilation, RRT, and ICU death have point estimates near zero and horizontal 95% confidence intervals crossing a dashed vertical zero line. The ventilation interval is the widest.
