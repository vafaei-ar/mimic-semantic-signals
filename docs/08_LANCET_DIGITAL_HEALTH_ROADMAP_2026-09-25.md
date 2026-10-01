# Lancet Digital Health roadmap - current checkpoint

Updated: 2026-10-01

This file retains the original roadmap filename for continuity but now reflects the current post-registration state. The authoritative execution order is docs/10_POSTREGISTRATION_EXECUTION_AND_EXTENSION_PLAN_2026-09-30.md.

## Current position

The project has moved through exploratory v1 analyses, external integrity review, v2/v2.1 redesign, preregistration, final OSF verification, and registered real-label execution.

OSF registration:

- ID: ahxn9
- DOI: 10.17605/OSF.IO/AHXN9
- cited repository commit: 873897e6c934cea3d558b6518ac1e399f9f75387
- manifest SHA-256: 22ac9f815309d81ebf03d279087848e33f8c0a16b563efe8af114a196194fc7d

The final OSF-form import/verification gate passed before real-label analyses opened.

## Completed manuscript-facing evidence

- H1-H3 primary Open-Jev analyses complete.
- H4 six-construct analyses complete.
- H5 common-logistic lexical comparisons complete.
- H6 unstripped-note Open-Jev sensitivity complete.
- H6 Laya alternative-instrument sensitivity complete.
- H6 DiffusionGemma ventilation analysis complete.

The current registered execution is DiffusionGemma RRT inference, job D4M8Q2VN.

## What the corrected results are saying

The primary Open-Jev delta-AUROC estimates are close to zero after the rich structured comparator:

- ventilation -0.00005;
- RRT -0.00079;
- MetaVision ICU death -0.00212.

H5 provides an important representation contrast within the same logistic family:

- TF-IDF increments are +0.00564, +0.00219, and +0.00123 for ventilation, RRT, and death;
- Open-Jev increments are negative for all three;
- adding Open-Jev after TF-IDF also lowers AUROC in all three primary analyses.

H6 does not currently rescue a simple positive semantic-increment story:

- unstripped Open-Jev remains near zero or negative;
- Laya ventilation has a +0.01031 point estimate but a wide interval spanning negative and positive values;
- Laya RRT and death are near zero;
- DiffusionGemma ventilation is -0.00811 with 95% interval -0.02030 to +0.01445.

The paper should therefore follow the evidence rather than protect the original hypothesis.

## Current high-value manuscript question

A stronger potential paper is increasingly:

Can clinically interpretable low-dimensional semantic measurements provide useful compression, human interpretability, stability, and transport of ICU narrative information even when they do not improve discrimination over a strong nonlinear structured comparator as much as high-dimensional lexical text?

That question remains open until H8 clinician validation and H9 transport are known.

## Remaining Lancet Digital Health path

1. Finish the DiffusionGemma H6 arm for RRT and MetaVision ICU death.
2. Complete all remaining registered H6 endpoint, timing, note-availability, and CareVue sensitivities.
3. Run H7 shuffled negative control.
4. Complete H8 blinded multi-rater clinician construct validation.
5. Run H9 corrected Zigong DiffusionGemma transport.
6. Freeze a single H1-H9 provenance/result index.
7. Quantify the practical compression tradeoff: dimensionality, runtime, hardware burden, stability, interpretability, and transport.
8. Generate manuscript tables/figures only from frozen aggregate artifacts.
9. Audit every manuscript number back to an exact commit, RunRelay job, and artifact hash.
10. Lock the central claim only after these steps.

A second independent narrative cohort remains desirable but is not a substitute for the registered Zigong analysis.

## Post-registration exploratory work

After the registered critical path is frozen, local Nimble 9B and Tev1 4B Jev-style decision-model comparisons can be run through Ollama using the frozen eight-construct schema and the same downstream cohorts/splits.

Hosted Jev remains post-registration exploratory. The vendor enabled ZDR on 2026-10-01 and stated that only operational telemetry is retained, but institutional/data-use permission for transmitting restricted MIMIC notes remains a separate unresolved gate.

OPUS remains a supplementary synthetic construct-validity stress test and does not replace clinical external validation.

## Decision rule for the paper narrative

If the remaining semantic instruments, H8 human ratings, and H9 transport show meaningful clinical construct validity and practical compression value despite limited incremental AUROC, the paper can emphasize interpretable semantic compression and its tradeoffs.

If construct validity or transport also fails, the paper should say so clearly and frame the work as a rigorous negative/limits study rather than model shopping.

A Lancet Digital Health submission remains aspirational. The evidence, not the target journal, determines the final claim.
