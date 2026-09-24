# Post-freeze supervised text-encoder development protocol v1

This protocol is separate from the frozen zero-shot semantic benchmark and from the frozen tuning-cohort build.

## Scientific role

The first supervised development arm is an outcome-specific predictive upper bound using the same local Open-Jev DeBERTa encoder checkpoint as a starting representation.

It is not a semantic-preserving JEV model and must not be described as improving the eight frozen semantic constructs.

Its purpose is to quantify how much discrimination becomes available when the note encoder itself is allowed to learn directly from outcome labels under a leakage-safe patient split.

## Frozen cohorts

Cohorts: `docs/multitask_tuning_cohort_freeze_v1.md`

Only train and validation are available during model development.

The locked test split must not be read by the development script.

## Base checkpoint

- local cached checkpoint: `com-kotobalabs/open-jev-deberta-v3-large`
- architecture: DeBERTa-v2 large encoder
- network disabled before model or clinical-note loading
- no remote inference or external API

The original typed-decision semantic head is not used for this supervised upper-bound model.

## Model

Shared encoder with three binary classification heads:

1. invasive ventilation within 12 hours
2. renal-replacement therapy within 12 hours
3. ICU death within 12 hours

Each note belongs to exactly one outcome task and contributes loss only to that outcome head.

All encoder parameters and the three heads are trainable.

## Long-note handling

- tokenizer: checkpoint tokenizer
- note chunk size: 384 tokens
- overlap: 64 tokens
- maximum chunks per note: 5
- chunking occurs after prospective note selection and endpoint-language exclusion
- truncation by the five-chunk limit is counted and reported

A note is treated as a multiple-instance bag.

For its assigned outcome, chunk logits are aggregated by maximum logit. The note-level binary cross-entropy loss is computed from that maximum. This makes a positive note require at least one predictive passage while penalizing any strongly positive passage in negative notes.

## Outcome balancing

The matched cohorts all have 1:3 case-control sampling but differ substantially in size.

Each note receives an outcome weight inversely proportional to the number of train notes for its outcome, normalized so the mean train weight is 1. This prevents ICU-death volume from dominating the shared encoder.

No additional case-control class weighting is used.

## Optimization

Frozen development settings:

- optimizer: AdamW
- learning rate: 2e-5
- weight decay: 0.01
- epochs: 3
- note batch size: 2
- gradient accumulation: 8
- effective note batch size: 16 before outcome weighting
- precision: bfloat16
- gradient clipping: 1.0
- scheduler: linear decay
- warm-up: 10% of optimizer steps
- gradient checkpointing: disabled after the pre-performance smoke test exposed a reproducible autograd graph-reuse failure; GPU diagnostic peak allocation was 6.6 GB, so checkpointing is not required for memory feasibility
- seed: 20260924

No hyperparameter search is planned for v1.

## Validation and checkpoint selection

After each epoch, evaluate note-level AUROC and AUPRC separately for the three outcomes on the validation split.

Primary checkpoint-selection statistic:

mean of the three validation AUROCs.

Tie-breaker:

mean of the three validation AUPRCs.

The selected checkpoint is stored only in the local project data area and is never declared as a RunRelay artifact because a fine-tuned clinical language model may encode restricted training information.

Only aggregate training diagnostics are shared.

## Development gates

1. Run a bounded smoke test on a small train/validation subset.
2. If the smoke test passes model loading, forward/backward, memory, chunk aggregation, and aggregate reporting, run the full three-epoch development training.
3. Review validation metrics and operational diagnostics.
4. Freeze the selected checkpoint, final comparators, and final test analysis plan.
5. Only then unlock the test split for one-time final evaluation.

## Test prohibition

The development code must not enumerate, open, tokenize, score, or inspect files under the `test` split.

Any accidental test access invalidates the development phase and requires a new untouched test partition before final evaluation.

## Pre-performance implementation note

Before any successful validation performance was observed, the initial smoke run failed on the second accumulated backward pass with a reproducible autograd graph-reuse error while DeBERTa gradient checkpointing was enabled. A PHI-safe diagnostic confirmed checkpoint discovery, tokenization, train/validation loading, collation, forward, and a single backward pass, with approximately 6.6 GB peak allocated GPU memory. Gradient checkpointing was therefore disabled as an operational compatibility fix before model development. All other frozen training settings remain unchanged.
