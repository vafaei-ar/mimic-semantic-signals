# JAMIA submission and reporting cross-check

Updated: 2026-10-04

Target: **Journal of the American Medical Informatics Association (JAMIA), Research and Applications**

This is an internal pre-submission cross-check, not a reproduced journal or reporting-guideline checklist.

## JAMIA format status

| Requirement | Current status | Action |
|---|---|---|
| Research and Applications main text <=4,000 words | Pass: 3,904 words | None |
| Structured abstract <=250 words | Pass: 234 words | None |
| Abstract headings: Objective; Materials and Methods; Results; Discussion; Conclusion | Present | None |
| Background and Significance section | Present | None |
| Main tables <=4 | 3 | None |
| Main figures <=6 | 2 | None |
| Manuscript double-spaced | Pass in final DOCX | Render verified |
| Tables in Word at first citation | Pass in final DOCX | Render verified |
| Figures supplied separately | Pass: final code-generated vector PDFs; editable SVG source and generators retained | None |
| Figure legends at manuscript end | Present | None |
| Alt text for main figures | Present | None |
| References numbered in order of citation | Present | Final citation-order check |
| Data/code availability | Present with public repository URL | Verify before upload |
| Funding | “No external funding supported this study” | Confirm |
| Competing interests | Placeholder | Author must complete |
| Corresponding-author details | Complete from public Penn State records | Verify before upload |
| Ethics/data-use statement | MIMIC source ethics and DUA stated | Add local determination only if applicable |
| AI use disclosed in manuscript | Present | Keep |
| AI use disclosed in cover letter | Present | Keep |
| Related/overlapping publications supplied if applicable | Unknown | Author to verify before submission |

## TRIPOD+AI high-level cross-check

The paper identifies the target outcomes, prediction horizon, source population, eligibility restrictions, predictors, prediction time point, modeling approach, patient-grouped validation strategy, discrimination metrics, calibration-related analysis provenance, missing-value handling, uncertainty procedure, and limitations.

Items requiring final attention before submission:

1. Confirm the final manuscript states the exact software/library versions or directs readers to a versioned code/configuration repository.
2. Decide how much calibration information belongs in the main text versus Supplementary Material. The frozen analysis contains calibration metrics even though incremental AUROC is the main estimand.
3. Ensure every model-evaluation population reports outcome frequency and sample size.
4. Ensure the post-registration semantic-only and comparator-decomposition analyses are labeled exploratory everywhere.
5. Keep external validation language precise: registered external transport was not completed as planned.
6. Add the public repository URL and, if available, a version/archive identifier.

## TRIPOD-LLM high-level cross-check

The manuscript describes the role of the language-model-derived representation, the eight semantic tasks, text selection, preprocessing, chunk aggregation, missing-score handling, comparator models, evaluation cohorts, and alternative instruments.

Items requiring final attention:

1. Include exact Open-Jev model/revision and runtime details in Supplementary Methods or a reproducibility table.
2. Include exact Laya and DiffusionGemma revisions for the sensitivity analyses in the supplement.
3. State clearly that no model was tuned using outcome performance after registration.
4. State clearly that human construct validation was planned but not performed and therefore the eight scores are not described as clinically validated constructs.
5. Preserve the label-free alignment audit as an integrity check, not a substitute for clinician validation.
6. Keep prompt/question schema and model configuration available in the public repository.

## Scientific integrity cross-check

- Registered H1-H7 results are separated from post-registration exploratory analyses.
- H8 not performed is documented before any human rating result existed.
- H9 partial execution is documented and is not used as central external-validity evidence.
- Earlier v1 positive results are provenance only and are not mixed with corrected v2.1 estimates.
- The OSF PDF byte mismatch and text-equivalence check are documented.
- Figure 1 uses registered/replication/shuffled estimates with refit-bootstrap intervals.
- Figure 2 is labeled exploratory and uses frozen partition spread, not confidence intervals.
- HGB comparator decomposition is not numerically conflated with the H5 common-logistic TF-IDF comparison.

## Author-only items before upload

- Author name, degrees, department, institution, postal address, public email, and public telephone are filled from verified Penn State and publication records; verify before upload.
- Complete the competing-interest declaration.
- Confirm whether any local institutional/IRB determination should be named.
- Confirm that the manuscript is not under consideration elsewhere.
- Add the exact public GitHub/archival URL.
- Confirm Penn State affiliation as entered in the submission system.
- Select JAMIA's standard subscription route if no open-access agreement is being used, so no voluntary OA charge is incurred.


## Mock-review response status

- Registered Brier score, log loss, calibration, ECE, and decision-curve results added.
- Exploratory note-available subgroup added using frozen full-cohort OOF predictions without refitting.
- Exact eight frozen semantic questions and response criteria added to the supplement.
- Open-Jev, Laya, and DiffusionGemma model-card references added.
- Documentation-process, informative-missingness, nursing-data, and added-value literature added.
- Main-text absolute AUROCs rounded to three decimals; incremental estimates retain sufficient precision to show very small effects.
- RRT semantic-only AUROC below 0.5 explicitly reported without post-hoc inversion.
- Negative common-logistic Open-Jev increments explicitly explained as valid held-out results.
- AI disclosure expanded to include Anthropic Claude.
- **Author action required:** complete the competing-interest statement and add a local ethics determination only if one genuinely applies.


## Final mock-review cleanup

- Claude disclosure now identifies Anthropic Claude (Opus 5.5).
- Post-registration explanatory work is consistently described as four exploratory analyses.
- The phrase referring to external mock review was removed from the Methods.
- Main-text ventilation delta AUROC is rounded to -0.0001; standalone ICU-death semantic AUROC is 0.657.
- Table 1 expanded with age, sex, MAP, lactate, creatinine, ICU length of stay, and case/control note availability using aggregate frozen-cohort summaries.
- Calibration-slope interpretation added, while retaining calibration as a secondary outcome.
- Instrument score generation and across-chunk aggregation are described explicitly.
- Main-text hypothesis shorthand (H1-H3/H5/H6/H7) was replaced with plain descriptions.
- Laya wording changed to “the Laya typed-decision model.”
- Author identity, affiliation, public email, and public telephone have been entered from Penn State/publication records; verify them before upload.


## Final figure redesign status

- Figure 1a is a code-drawn study-design schematic using the actual 12-hour landmark, single latest eligible pre-landmark note, exact eight constructs, rich comparator blocks, and 12-hour outcomes.
- Figure 1b is one comprehensive registered forest plot grouped by outcome, combining primary estimates, semantic-instrument sensitivities, endpoint/timing analyses, CareVue replication, and shuffled controls.
- The approximate pre-analysis 80% detectable full-cohort delta-AUROC magnitudes appear as outcome-specific pale bands and are explicitly labeled interpretive precision context, not equivalence margins.
- Figure 2a retains the post-registration comparator decomposition with level D defined as ordinary note context (availability, age, category), not a text embedding.
- Figure 2b compares Open-Jev and TF-IDF only within the same registered L2-logistic model family; TF-IDF uses up to 10,000 features.
- Figure 2c uses the actual label-free alignment audit (real versus between-patient shuffled construct-state correlations), not a fabricated time-course analysis.
- Figure 2d uses the actual note-available frozen-prediction subgroup across five partitions, with no subgroup refitting.
- Registered Brier score, log loss, calibration, and decision-curve results remain in Supplementary Table S9 rather than a main absolute-metric graphics panel.
- All manuscript figure graphics are generated with repository code from frozen aggregate values. No generative-image output is used in the submission figures.
- Final figures are generated by `manuscript/make_paper1_figures.py` from the frozen manuscript JSON files. Canonical RunRelay job: `Z5K2R8M4` at commit `6596d4f905f975ec45b29515708dd8bad8687353`. Figure 1 SVG SHA-256: `4ee5ab74cc3ddaca6a492ff6c4b250ae446267ea03f750bf61d16bdb98f22320`; Figure 2 SVG SHA-256: `72288cf2eecb183900fd96756eaa96eeb7a1244f71c9b76ca02749b0af9d6723`.
