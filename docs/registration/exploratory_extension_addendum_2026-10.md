# Exploratory extension addendum: incremental bedside-text information across representations and comparator richness

Date frozen: 2026-10-04  
Parent registration: OSF `ahxn9`, DOI `10.17605/OSF.IO/AHXN9`  
Project: `wmyb2`

## Status

This addendum specifies post-registration exploratory analyses. It does not modify, replace, or reinterpret the registered H1-H9 analysis plan. Every result described below will be reported regardless of direction.

## Scope

In scope:

- T0.1 fixed-alert-burden analysis;
- T0.2 decision curves from registered thresholds;
- T0.3 reporting of upper 95% confidence limits for delta AUROC;
- T0.4 label-free note timing relative to support transitions;
- T1.1 cross-fitted supervised TF-IDF augmentation;
- T1.2 cross-fitted frozen-embedding augmentation;
- T1.2b 32-component embedding early-fusion sensitivity;
- T1.4 endpoint/treatment-language sensitivity using frozen unstripped notes;
- T1.5 comparator-richness decomposition for supervised text.

Deferred before extension outcomes are examined:

- fine-tuned transformer;
- scoping review;
- MIMIC-IV radiology arm;
- structured-only external datasets.

Only a newly accessible independent dataset containing genuine bedside narrative can interrupt this stop rule, and it would require a separate frozen protocol before outcome analysis.

## Primary metric by task

- T0.1: fixed-alert-rate event capture and paired alert reclassification at prespecified alert budgets.
- T0.2: net benefit at the already registered thresholds.
- T0.3: upper 95% confidence limit for registered delta AUROC.
- T0.4: subsequent-only transition proportion among high-score notes with any qualifying support transition.
- T1.1: delta AUROC for rich comparator D plus cross-fitted TF-IDF log-odds versus comparator D.
- T1.2: delta AUROC for rich comparator D plus cross-fitted embedding log-odds versus comparator D.
- T1.2b: delta AUROC for rich comparator D plus 32 training-fold PCA embedding components versus comparator D.
- T1.4: stripped versus unstripped T1.1 delta AUROC.
- T1.5: text-score delta AUROC across comparator levels A through D, with primary-partition refit-bootstrap intervals at A and D.

## Frozen embedding model

The embedding model was selected using label-free local availability and synthetic runtime only, before any extension label-reading job.

- model: `BAAI/bge-large-en-v1.5`
- revision: `d4aa6901d3a41ba39fb536a557fa166f842b0e09`
- output dimension: 1024
- maximum sequence length: 512
- runtime smoke: offline synthetic encoding passed
- chunking: 448 non-special tokenizer tokens per chunk with 64-token overlap
- chunk aggregation: normalized chunk embeddings are averaged without weighting; the document embedding is L2-normalized after averaging
- no query/task prefix is applied
- no alternative embedding model will be compared for outcome performance

## Shared Tier 1 design

Reuse the frozen v2.1 cohorts, five patient-grouped partitions, comparator definitions, HGB settings, and patient-cluster bootstrap framework.

Within every outer training fold, fit the supervised text model only on training-fold stays with an eligible note, obtain training-row text scores using inner five-fold patient-grouped cross-fitting, refit the text model on the full outer training fold, score the held-out fold, and then augment the rich HGB comparator.

For T1.1, T1.2, and T1.2b, refit the supervised text component and HGB inside every bootstrap replicate. All copies of a resampled patient remain in the same inner fold.

Runtime rule: use the first 10 frozen-seed bootstrap replicates for timing only. If median replicate runtime multiplied by 500 exceeds 72 hours, run exactly 200 valid replicates; otherwise run 500. The first 10 count toward the final set.

## Interpretive learnability threshold

Standalone out-of-fold text-score AUROC within note-available stays is reported together with standalone AUPRC and outcome prevalence. AUROC is the only predeclared interpretation threshold.

- **AUROC >= 0.60:** the text representation carries standalone outcome signal. A near-zero increment against comparator D supports a redundancy interpretation.
- **AUROC < 0.60:** insufficient standalone text discrimination to support a redundancy interpretation. Report the increment unchanged.

This threshold guides interpretation only. It is not a validity boundary. Every result is reported regardless, and values close to 0.60 are described as such. T1.2b inherits the T1.2 standalone learnability result.

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

Every row is a reportable result. No row is a failure.

## T0.4 timing definition

A qualifying transition is the first support start, or first FiO2 step-up under the frozen alignment-audit definition, after at least six hours without that support/state.

For each note, record the most recent qualifying transition in the 12 hours before note storetime and the first qualifying transition in the 12 hours after storetime. Classify each note as prior only, subsequent only, both, or neither. Report all four categories for high-score, low-score, and patient-shuffled notes. Also report whether the corresponding support is already ongoing at note storetime.

This is descriptive and does not constitute a new prediction claim.

## Data governance

No raw note text, row-level predictions, or row-level embeddings are uploaded to OSF, GitHub, RunRelay artifacts, or any external API. Only protocol text, code, aggregate result summaries, and safe aggregate figures/tables are shared.
