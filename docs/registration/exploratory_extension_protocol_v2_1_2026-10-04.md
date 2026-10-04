# Paper 1 exploratory extension protocol v2.1

Frozen: 2026-10-04  
Branch: `extension-v2_1`  
Parent JAMIA-ready commit: `f57ddfbdc5ac6c700431a96b281b40cdd1505382`  
Primary registration: OSF `ahxn9`, DOI `10.17605/OSF.IO/AHXN9`

This file operationalizes `docs/EXTENSION_PLAN_v2_1_2026-10-04.md`. Every analysis in this extension is post-registration exploratory and does not alter H1-H9.

## Scope

In scope: T0.1, T0.2, T0.3, T0.4, T1.1, T1.2, T1.2b, T1.4, and T1.5.

Prospectively deferred before extension results are read:

- fine-tuned transformer;
- scoping review;
- MIMIC-IV radiology arm;
- structured-only external datasets.

A newly available independent dataset with real bedside narrative is the only exception, and would require a separate frozen protocol before any outcome analysis.

## Frozen embedding model

Selection was made using label-free local-cache and synthetic-runtime information only.

- model ID: `BAAI/bge-large-en-v1.5`
- revision: `d4aa6901d3a41ba39fb536a557fa166f842b0e09`
- architecture metadata: BERT, hidden size 1024, maximum position embeddings 512
- local runtime: `/home/asadr/miniconda3/envs/lc/bin/python`
- sentence-transformers: 3.2.1
- transformers: 4.46.2
- torch: 2.5.1
- label-free cache audit: RunRelay `G6R4M2T8`, artifact SHA-256 `02671d78fb435682a2255b768eaa3bb5e55f2c390c93e14f3620d1b20cf5188c`
- synthetic offline smoke: RunRelay `M2V6R4K8`, artifact SHA-256 `1a88cf187c6c126ebd83e4f359b7005b461e8aea5bf9103f506dc18b4a5c1f95`

No alternative embedding model will be evaluated for outcome performance.

### Frozen embedding preprocessing

1. Use the frozen stripped primary landmark note.
2. Tokenize with the frozen model tokenizer without network access.
3. Split tokenized note content into windows of 448 non-special tokens with 64-token overlap.
4. Encode every window with the frozen SentenceTransformers pipeline using normalized embeddings and no task instruction/prefix.
5. For a note with multiple windows, take the unweighted arithmetic mean of the window embeddings and L2-normalize the resulting document vector.
6. Cache only local row-level embeddings. They are never declared as RunRelay artifacts or transmitted externally.
7. T1.2 uses an L2-logistic classifier on these frozen label-free embeddings, with C selected by inner patient-grouped CV on the outer training fold only.
8. T1.2b fits PCA on the outer-training-fold document embeddings only, retains exactly 32 components, and passes those components directly to the registered HGB comparator. PCA is refit inside every bootstrap replicate.

## Shared cross-fitting and bootstrap rules

The five frozen patient-grouped outer partitions are reused.

Within each outer training fold:

1. fit the supervised text model only on training-fold stays with an eligible note;
2. generate training-row text scores by inner five-fold patient-grouped cross-fitting;
3. refit the supervised text model on the complete outer training fold;
4. score the held-out outer fold;
5. add the text score to comparator D for late-fusion analyses.

For T1.1, T1.2, and T1.2b, both the supervised text component and HGB are refit inside every patient-cluster bootstrap replicate. All copies of a resampled patient remain in the same inner fold.

Runtime rule: run the first 10 bootstrap replicates from the frozen seed sequence and record wall time only, without inspecting performance estimates. Multiply the median replicate runtime by 500. If the projection exceeds 72 hours, run exactly 200 valid replicates; otherwise run 500. The first 10 replicates count toward the final set.

Primary metric: delta AUROC versus comparator D on the primary frozen partition.

Secondary metrics: delta AUPRC, five-partition range, and fixed 5% alert-rate contrasts.

## Interpretive learnability threshold

For every scalar supervised text model, report standalone out-of-fold AUROC and AUPRC among note-available stays, including outcome prevalence.

- AUROC >= 0.60: the text representation carries standalone outcome signal. A near-zero increment against D supports a redundancy interpretation.
- AUROC < 0.60: insufficient standalone text discrimination to support a redundancy interpretation. Report the increment unchanged.

The threshold guides interpretation only. It is not a validity boundary. Every result is reported. T1.2b has no separate standalone score and inherits the T1.2 learnability result.

## T0.1 fixed alert burden

At 2%, 5%, 10%, and 20% alert budgets, rank predicted risks descending and frozen `case_id` ascending, then alert exactly the first ceiling(rate x N) stays.

Report sensitivity, PPV, events caught per 1,000 stays, alerts per true event, alert-status changes in/out per 1,000, events among changed stays, and net events caught per 1,000.

Uncertainty: five-partition range and 2,000-replicate patient-cluster bootstrap of frozen primary-partition predictions, labelled conditional on the fitted models.

## T0.2 decision curves

Use the registered net-benefit arrays when stored. Otherwise recompute from frozen OOF predictions at the registered thresholds. No model is refit.

## T0.3 compatible upper confidence limits

Manuscript wording will report that the upper 95% confidence limit for delta AUROC is +0.019 for ventilation, +0.003 for RRT, and +0.005 for ICU death, and compare those values with the prespecified detectable magnitudes 0.0233, 0.0113, and 0.0241. The words "equivalent" and "ruled out" are prohibited.

## T0.4 note timing relative to support transitions

Outcome labels are not read.

A qualifying transition is the first start of the support, or first FiO2 step-up under the frozen alignment-audit definition, after at least six hours without that support/state.

For each note and construct-state pair:

- prior transition: most recent qualifying transition in the 12 hours before note storetime;
- subsequent transition: first qualifying transition in the 12 hours after storetime;
- category: prior only, subsequent only, both, or neither.

Pairs:

- hemodynamic concern / vasoactive start;
- respiratory concern / high-flow start;
- respiratory concern / NIV start;
- respiratory concern / FiO2 increase.

Score groups are top and bottom quartiles using score-distribution-only cutoffs. The primary summary is the subsequent-only proportion among high-score notes with any transition, with patient-cluster bootstrap interval. Report the full four-category distribution for high-score, low-score, and patient-shuffled scores, and report ongoing support at note storetime by quartile.

## T1.1 TF-IDF supervised text benchmark

Use the exact H5 TF-IDF/tokenization/n-gram specification, capped at 10,000 features, with L2 logistic regression. Vocabulary fitting occurs inside the relevant training fold. The cross-fitted log-odds are added as one feature to comparator D.

## T1.2 frozen-embedding supervised text benchmark

Use the frozen BGE embeddings above. Fit L2 logistic regression with C selected by inner CV within the training data only. Add the cross-fitted log-odds as one feature to comparator D.

## T1.2b 32-component early fusion

Fit PCA on training-fold BGE embeddings only and retain exactly 32 components. Feed the components directly to HGB with comparator D. Refit PCA inside every bootstrap replicate.

## T1.4 endpoint/treatment-language sensitivity

Repeat T1.1 with the frozen unstripped H6 notes. Report stripped versus unstripped delta AUROC. The difference is not called pure leakage.

## T1.5 comparator-richness decomposition

Repeat comparator levels A through D with the T1.1 and T1.2 text scores.

Report all five frozen partitions at every level and primary-partition refit-bootstrap intervals at levels A and D only.

## Predeclared interpretation table

| Result pattern | Allowed claim |
|---|---|
| Text AUROC >= 0.60; increments at D near zero for TF-IDF, embedding and early fusion | Bedside text carries outcome information, but little incremental discrimination remains once physiology, treatment/support, documentation behaviour and note context are represented |
| Increments clearly positive at A and shrinking toward D (T1.5) | Estimated incremental text value depends on comparator richness; thinner comparators yield larger apparent gains |
| TF-IDF, embedding or early fusion positive at D (CI excludes 0) | The Open-Jev null partly reflects compression to eight constructs; residual narrative information exists |
| Early fusion positive at D (CI excludes 0) while scalar stacking is near zero | Interactions between text and individual structured variables carry information that a single text score misses |
| Text AUROC < 0.60 | Insufficient standalone text discrimination to support a redundancy interpretation for that outcome |
| Unstripped >> stripped (T1.4) | Naive pipelines are vulnerable to inflated performance from direct endpoint/treatment language |
| T0.4: mostly prior or ongoing support at high-score notes | High semantic concern often coincides with or follows support already visible in structured data, consistent with documentation of existing clinical state |
| T0.4: notes often precede transitions | Notes sometimes anticipate support changes; describe this, with no new prediction claim |

Every row is reportable. No row is a failure.

## Stop rule

No new analysis is added after the planned T1.5 freeze unless an independent dataset with genuine bedside narrative becomes available. Such a dataset requires its own protocol before any outcome analysis.
