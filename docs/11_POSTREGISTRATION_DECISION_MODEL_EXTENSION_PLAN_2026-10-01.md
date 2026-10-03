# 11 - Post-registration exploratory decision-model extension plan

> **Deferred for Paper 1, 2026-10-03:** No Clef, Clef-Flash, Nimble, Tev1, hosted-Jev, or other new decision-model clinical evaluation will be run before initial submission. This document is retained only as a future/revision roadmap. The active plan is `docs/12_MINIMAL_SUBMISSION_PLAN_2026-10-03.md`.


Updated: 2026-10-03

This document freezes the scientific and operational basis for the local decision-model extension. The 2026-10-03 minimal-submission plan in docs/12_MINIMAL_SUBMISSION_PLAN_2026-10-03.md defers this entire extension until after initial submission or a concrete reviewer request.

This work is not part of OSF registration ahxn9 and must be labeled post-registration exploratory in code, RunRelay jobs, artifacts, tables, figures, and manuscript text.

## Scientific purpose

The registered analyses ask whether the frozen semantic instruments add useful information beyond a strong structured comparator. The exploratory extension asks a different question:

> Are the observed limits of compact semantic scoring specific to the registered instruments, or do they persist across independently developed typed decision-model architectures that implement the same clinically interpretable eight-construct measurement idea?

This extension is not a leaderboard. Its value is in separating three possibilities:

1. a representation-level limitation of low-dimensional semantic compression;
2. instrument-specific limitations of Open-Jev/Laya/DiffusionGemma;
3. context-window or implementation limitations that can be tested without changing the clinical estimand.

## Planned local roster

### 1. Cloudflare Clef-Flash 9B

Model repository: `Cloudflare/clef-flash`.

Role after the 2026-10-03 publication-sprint amendment: preferred technical/preflight target for validating the common Cloudflare integration, and fallback clinical Cloudflare model only if Clef 27B is not feasible under a stable frozen local resource plan. It is not a default fourth clinical model.

Verified model-card properties at plan freeze:

- 9B multimodal decision model;
- Apache-2.0 license;
- post-trained from Qwen/Qwen3.5-9B;
- typed `noul`, `choice`, and `score` questions;
- Jev/SystemOne-compatible `/v1/systemone` request/response semantics;
- direct option probabilities rather than free-text generation/parsing;
- `encode_record` default maximum length of 16,384 tokens.

Source: https://huggingface.co/Cloudflare/clef-flash

### 2. Cloudflare Clef 27B

Model repository: `Cloudflare/clef`.

Role: full-capacity independent decision-model comparison after Clef-Flash establishes a clean local integration and the workstation hardware preflight confirms feasibility.

Verified model-card properties at plan freeze:

- 27B multimodal decision model;
- Apache-2.0 license;
- post-trained from Qwen/Qwen3.8-27B;
- the same typed-question and Jev/SystemOne-compatible interface;
- direct option probabilities from a joint schema head;
- `encode_record` default maximum length of 16,384 tokens.

Source: https://huggingface.co/Cloudflare/clef

Do not silently introduce quantization to make Clef fit. If the released precision cannot be run locally under a stable resource plan, either use a predeclared multi-GPU/offload strategy that preserves the released model or freeze any quantized derivative as a separate exploratory instrument before labels are opened.

### 3. Nimble 9B

Role: local Jev-style decision-model comparison through Ollama/SystemOne-compatible tooling.

Freeze the exact Ollama version, model tag, and immutable model digest before clinical inference.

### 4. Tev1 4B

Role: smaller local Jev-style decision-model comparison through Ollama/SystemOne-compatible tooling.

Freeze the exact Ollama version, model tag, and immutable model digest before clinical inference.

## Reference instruments

The exploratory models will be interpreted against already-frozen reference results from:

- Open-Jev;
- Laya;
- DiffusionGemma;
- TF-IDF lexical representation;
- the identical rich structured comparator.

The extension must not change any registered result or redefine H6.

## Mandatory label-free gate

No exploratory model may be evaluated against MIMIC outcome labels until its integration is frozen and a label-free gate is complete.

For each model, freeze:

- exact model repository/tag;
- immutable Hugging Face revision or Ollama digest;
- local model-file/checkpoint hashes when practical;
- license;
- runtime/library versions;
- GPU topology and precision/offload policy;
- exact eight-construct schema and schema SHA-256;
- text preprocessing and selected-note identity;
- local-only execution contract;
- context-window, truncation, chunking, and overlap rules;
- cross-chunk aggregation if chunking is used;
- retry/failure handling;
- safe aggregate artifact schema.

Then run label-free diagnostics on the frozen note corpus:

- expected/completed/failed note counts;
- valid eight-score completion;
- context coverage and truncation;
- score support/resolution and intermediate-score fraction;
- per-construct score distributions;
- pairwise construct correlations;
- cross-instrument construct agreement;
- deterministic repeatability on a fixed nonclinical/synthetic test set;
- directional response to the frozen clinical synthetic contrast set.

Any integration repair must occur before outcome labels are used. Once the first outcome evaluation is opened for a model, its inference configuration is locked.

## Context policy for Clef and Clef-Flash

Clef/Clef-Flash expose substantially longer native context than the registered compact instruments. That is scientifically important but creates a potential source of post hoc flexibility.

Therefore:

1. determine the usable state-token budget from the frozen eight-question schema and local runtime before labels;
2. freeze one primary exploratory native-context policy before clinical outcome evaluation;
3. if a shorter context-matched sensitivity is desired, define it at the same time as a distinct secondary arm;
4. use deterministic truncation/chunking and aggregation;
5. do not change the context cap after observing AUROC, AUPRC, calibration, or any outcome association.

The purpose of any context sensitivity is to distinguish instrument architecture from available narrative context, not to search for the best-performing window.

## Clinical evaluation after the label-free gate

Use the same frozen clinical objects already established by the registered project:

- the same stripped-note selected-note corpus;
- the same outcome populations;
- the same rich structured comparator;
- the same exact patient-grouped split files/hashes;
- the same downstream preprocessing rules where applicable;
- the same primary delta-AUROC estimand;
- the same estimation-first reporting style.

For each exploratory instrument, report at minimum:

- comparator AUROC;
- comparator + instrument AUROC;
- delta AUROC;
- AUPRC and delta AUPRC;
- frozen-partition stability;
- calibration summaries;
- inference runtime and hardware burden;
- score dimensionality and storage footprint;
- construct-level agreement with the registered instruments.

The first exploratory clinical pass should report uniform point estimates and frozen-partition stability for every screened model that passed the label-free gate. Do not automatically spend the full 500-valid-replicate refit-bootstrap budget on every new model. Before opening exploratory outcomes, freeze a promotion rule for at most one representative new model to receive the expensive full uncertainty analysis. Report all screened models regardless of direction. If a different uncertainty method is used, freeze and justify it before opening outcome results.

## Planned order

After H8 and the registered H1-H9 provenance index are frozen:

1. implement and validate the common local decision-model adapter without clinical labels;
2. use Clef-Flash 9B for the Cloudflare technical/preflight gate;
3. preflight Clef 27B and use it as the default Cloudflare clinical model if feasible without changing its frozen execution policy;
4. preflight and evaluate Nimble 9B;
5. preflight and evaluate Tev1 4B;
6. use Clef-Flash clinically only if Clef 27B is not feasible under the frozen local resource plan;
7. synthesize the representative panel against Open-Jev, Laya, DiffusionGemma, and TF-IDF;
8. stop adding models if the representative panel reproduces the same scientific pattern.

The default clinical panel is therefore Clef 27B, Nimble 9B, and Tev1 4B, with Clef-Flash 9B serving as the preflight/fallback model rather than an automatic additional clinical arm.

Long jobs remain sequential, and no model-panel job should delay H8 completion or manuscript assembly.

## Interpretation rules

Do not choose a preferred decision instrument post hoc from the largest point estimate.

The scientifically useful patterns are:

- If Clef, Clef-Flash, Nimble, Tev1, Open-Jev, Laya, and DiffusionGemma all show limited incremental discrimination while TF-IDF retains signal, that supports a broader representation-level limitation of compact typed semantic compression.
- If Clef/Clef-Flash show a materially different pattern under a configuration frozen before labels, that suggests instrument architecture or available context matters and weakens a representation-general conclusion.
- If only a longer-context arm differs, interpret that as a context-availability result rather than evidence that one model family is intrinsically superior.
- General benchmark rankings from model vendors are not clinical evidence and will not determine model selection or manuscript claims.

## Hosted Jev remains separate

Hosted Jev is not part of this local model roster.

The vendor-side ZDR clarification is complete, but the institutional/data-use gate for transmitting restricted MIMIC text to a hosted third party remains separate. Any future hosted-Jev comparison requires that governance gate to be cleared first, must freeze the exact hosted configuration before clinical use, and remains post-registration exploratory.

## Manuscript placement

The registered H1-H9 results remain the primary evidentiary spine.

Clef, Clef-Flash, Nimble, Tev1, any future hosted-Jev analysis, and OPUS remain post-registration exploratory. Under the 2026-10-03 publication-sprint amendment, the manuscript-facing decision-model panel is intentionally bounded rather than exhaustive. Their purpose is to test the generality and mechanism of the registered findings, not to rescue or redefine the preregistered hypotheses.
