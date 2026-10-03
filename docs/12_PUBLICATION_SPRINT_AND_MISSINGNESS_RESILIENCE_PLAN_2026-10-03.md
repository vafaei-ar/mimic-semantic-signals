# 12 - Publication sprint and structured-data missingness-resilience plan

Updated: 2026-10-03

This document records the current publication-priority amendment after completion of H6, H7, and corrected computational H9 and after freezing the H8 clinician-rating sample.

It does not modify OSF registration ahxn9, the registered H1-H9 estimands, or any frozen v2.1 result. All work described here is post-registration exploratory unless explicitly identified as registered H8 completion or the final H1-H9 provenance freeze.

## Why the project is changing mode

The registered evidence is now mature enough that the main scientific risk is scope creep rather than insufficient experimentation.

The corrected v2.1 primary analyses show little or no incremental discrimination from the eight low-dimensional semantic scores after a rich structured comparator. H5 shows that high-dimensional TF-IDF text retains small positive increments under a common logistic model family while Open-Jev increments are negative in all three primary outcome analyses. H6 does not overturn that pattern. H7 negative controls are complete. Corrected H9 external transport is weak. H8 human construct validity is the remaining registered scientific gate.

The project therefore enters a publication sprint with three priorities:

1. finish H8 and freeze the complete registered H1-H9 evidence/provenance index;
2. run one bounded missingness-resilience extension that can materially strengthen the manuscript mechanism;
3. run only a small representative post-registration decision-model panel, with explicit stopping rules.

No new experiment should be added merely because a new model becomes available.

## Submission-critical path

The submission-critical path is:

1. document the H8 governance gate;
2. complete the three blinded clinician-rating packets;
3. run the frozen H8 evaluator;
4. freeze the authoritative H1-H9 result/provenance index;
5. run the bounded structured-data missingness-resilience analysis using already-frozen representations where possible;
6. run the bounded representative local decision-model panel only if it does not delay manuscript assembly;
7. freeze figures, tables, supplement, reporting checklist, provenance audit, and manuscript.

H8 remains higher priority than any new model benchmark.

## Missingness-resilience question

The new scientific question is:

> When structured EHR information is incomplete, can prospectively available narrative information recover some of the predictive information lost from the structured record, and does high-dimensional lexical text recover more than low-dimensional semantic compression?

This is intentionally framed as **structured-data missingness resilience** or **narrative information rescue**, not as clinical imputation.

The first experiment should not claim to reconstruct a true missing laboratory value or vital sign. Instead, it should begin from rows with observed structured information, mask prespecified structured information, and ask how much predictive performance is recovered by narrative representations. Because the original structured values are known before masking, the perturbation is auditable and falsifiable.

## Minimal missingness-resilience design

Reuse the frozen v2.1 populations, patient-grouped partitions, note identities, and already-generated text representations.

Primary comparison within each outcome:

- full rich structured comparator;
- degraded structured comparator after a frozen masking rule;
- degraded structured + Open-Jev eight scores;
- degraded structured + TF-IDF.

A new decision-model representation may be added only after its separate label-free freeze and only if doing so does not delay the core analysis.

Use a small number of clinically coherent structured-information blocks rather than a large variable-by-variable grid. The initial implementation should prioritize:

- laboratory information;
- respiratory/hemodynamic information;
- neurologic/GCS information.

Before opening outcome results, freeze the exact feature membership, masking mechanism, masking severity or block-deletion rule, random seed if stochastic masking is used, preprocessing after masking, and handling of existing naturally missing values.

At minimum report:

- AUROC and AUPRC for full structured, degraded structured, degraded structured + Open-Jev, and degraded structured + TF-IDF;
- delta performance versus the degraded structured comparator;
- the performance loss caused by masking;
- the fraction of that lost performance recovered by each text representation when the denominator is positive;
- calibration summaries;
- frozen-partition stability;
- the amount and pattern of structured information removed.

A useful descriptive recovery estimand is:

```
recovery_fraction =
  (metric_degraded_plus_text - metric_degraded)
  / (metric_full_structured - metric_degraded)
```

Report this only when the full structured model actually outperforms the degraded model for that metric. Do not force or truncate the ratio.

## Interpretation guardrails for missingness work

A positive rescue effect would support the statement that narrative information becomes more useful when the structured record is incomplete.

It would not establish that:

- the narrative representation correctly imputes the hidden structured value;
- naturally missing EHR data are missing completely at random;
- text can safely replace laboratory measurement or bedside assessment;
- the result is causal;
- a semantic model is deployable for real-time clinical imputation.

If TF-IDF rescues more lost performance than the eight semantic scores, interpret that as further evidence that the narrative contains useful information that is lost during low-dimensional semantic compression.

If neither representation rescues performance, stop the extension rather than adding progressively more masking schemes.

## Representative local decision-model panel

The project will not become a model leaderboard.

The default clinical panel is limited to:

- Nimble 9B;
- Tev1 4B;
- Clef 27B.

Clef-Flash 9B is retained as the preferred integration/preflight model and as the fallback clinical Cloudflare model if Clef 27B is not feasible under a stable, frozen local resource plan.

Open-Jev, Laya, DiffusionGemma, and TF-IDF remain the reference representations.

All post-registration model work must remain local for restricted MIMIC text unless a separate governance decision explicitly permits otherwise.

## Model-panel stopping rules

Before any new model sees outcome labels, freeze its exact version/digest, runtime, context policy, eight-construct schema, preprocessing, note identities, failure handling, and aggregate output contract.

The first clinical pass should be cheap and uniform:

- the same frozen outcome populations;
- the same frozen partitions;
- the same rich structured comparator;
- point estimates and partition stability for every model that passes the label-free gate.

Report all screened models, not only favorable ones.

Do not automatically run the full 500-valid-replicate refit bootstrap for every new model. Before opening model outcomes, freeze a promotion rule for at most one representative new model to receive the expensive full uncertainty analysis. The promotion rule must use clinically meaningful effect size plus partition stability and must not be changed after results are seen.

If the representative panel reproduces the Open-Jev/Laya/DiffusionGemma pattern, stop adding models. That result is scientifically more useful than an ever-growing leaderboard because it supports a representation-level conclusion.

## Model-release cutoff

For Paper 1, the exploratory model roster is frozen to the models named above as of 2026-10-03.

A later model release should interrupt the manuscript only if it represents a qualitatively different measurement architecture that directly threatens the paper's interpretation. A new checkpoint, parameter scale, quantization, or incremental benchmark improvement is not sufficient reason.

## Publication decision logic

The preferred manuscript story depends on the remaining evidence.

If H8 shows good construct agreement but predictive increments remain near zero:

> The semantic scores may behave as clinically recognizable measurements even when they do not add discrimination beyond a strong structured EHR model.

If the missingness-resilience experiment shows narrative rescue:

> Narrative information is largely redundant when the structured record is rich, but becomes more useful when structured information is incomplete. High-dimensional lexical representation may preserve more of that recoverable information than compact semantic compression.

If H8 is weak and missingness rescue is absent:

> The study becomes a rigorous negative benchmark defining the limits of low-dimensional semantic decision representations in this setting.

Corrected H9 should be reported as limited external transport, not as evidence of deployment readiness or language invariance.

## Explicit non-priorities before submission

Do not make the following Paper 1 blockers:

- exhaustive evaluation of every JEV/System-One-compatible model;
- hosted Jev on credentialed MIMIC text without governance clearance;
- Penn State narrative-cohort construction;
- eICU/NWICU structured transport expansion;
- MIMIC-BR, HiRID, SICdb, or other new datasets;
- rebuilt vasopressor analyses;
- a new supervised text encoder;
- extensive semantic trajectories;
- broad equity analyses;
- hyperparameter searches intended to find a positive semantic result.

These can become revision work, Paper 2 work, or future extensions.

## Current stop condition for the research phase

The research phase is complete enough for manuscript lock when:

- H8 is complete;
- the H1-H9 provenance/result index is frozen;
- the bounded missingness-resilience analysis is complete or has met its prespecified stopping rule;
- the representative model panel is either complete or explicitly stopped by feasibility/scientific-value rules;
- every manuscript number is traceable to an exact aggregate artifact and project commit.

At that point, additional analyses require a concrete reviewer-facing or claim-critical justification.
