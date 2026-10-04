# JAMIA submission and reporting cross-check

Updated: 2026-10-03

Target: **Journal of the American Medical Informatics Association (JAMIA), Research and Applications**

This is an internal pre-submission cross-check, not a reproduced journal or reporting-guideline checklist.

## JAMIA format status

| Requirement | Current status | Action |
|---|---|---|
| Research and Applications main text <=4,000 words | Pending final DOCX count | Verify after Word export |
| Structured abstract <=250 words | Draft designed to comply | Verify exact count |
| Abstract headings: Objective; Materials and Methods; Results; Discussion; Conclusion | Present | None |
| Background and Significance section | Present | None |
| Main tables <=4 | 3 | None |
| Main figures <=6 | 2 | None |
| Manuscript double-spaced | To be applied in DOCX | Verify render |
| Tables in Word at first citation | To be applied in DOCX | Verify render |
| Figures supplied separately | Figure 1 and Figure 2 SVG generated | Export/submit in accepted format if needed |
| Figure legends at manuscript end | Present | None |
| Alt text for main figures | Present | None |
| References numbered in order of citation | Present | Final citation-order check |
| Data/code availability | Present | Add public repository URL in submission version |
| Funding | “No external funding supported this study” | Confirm |
| Competing interests | Placeholder | Author must complete |
| Corresponding-author details | Placeholder | Author must complete |
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

- Replace author, degree, department, institutional affiliation, postal address, email, and telephone placeholders.
- Complete the competing-interest declaration.
- Confirm whether any local institutional/IRB determination should be named.
- Confirm that the manuscript is not under consideration elsewhere.
- Add the exact public GitHub/archival URL.
- Confirm Penn State affiliation as entered in the submission system.
- Select JAMIA's standard subscription route if no open-access agreement is being used, so no voluntary OA charge is incurred.
