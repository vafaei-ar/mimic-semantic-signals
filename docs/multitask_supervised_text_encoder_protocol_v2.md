# Post-freeze supervised text-encoder development protocol v2

This is a single prespecified repair of the failed v1 supervised encoder development arm. It does not alter the frozen zero-shot benchmark, tuning cohorts, or locked test set.

## Why v2 exists

The v1 development run completed operationally but produced chance-level validation discrimination:

- ventilation AUROC 0.517 at the selected epoch;
- RRT AUROC 0.500;
- ICU death AUROC 0.503.

A train/validation diagnostic showed that the rebuilt cohorts still contain strong predictive text signal, because a train-fitted TF-IDF model achieved validation AUROCs of 0.719, 0.883, and 0.930 respectively.

The selected v1 neural checkpoint also remained near chance on a deterministic train sample, with almost constant probabilities. A train-only overfit probe using the original unweighted objective collapsed toward the negative class.

A second diagnostic used train data only and compared fixed mechanistic variants. With positive class weight 3.0 and differential learning rates, the original CLS architecture achieved AUROC 1.0 for all three outcomes on the tiny train subset. Mean pooling also achieved 1.0, so CLS is retained to minimize architectural change.

No v2 choice below was selected from validation performance.

## Scientific role

As in v1, this model is an outcome-supervised predictive upper bound/comparator.

It is not a semantic-preserving JEV model and cannot be used to claim improvement of the frozen eight semantic constructs.

## Frozen cohorts

Use `docs/multitask_tuning_cohort_freeze_v1.md`.

Train and validation are available during development. The test split remains locked and must not be enumerated, opened, tokenized, or scored.

## Model

- base checkpoint: local cached `com-kotobalabs/open-jev-deberta-v3-large`;
- shared DeBERTa-v2 encoder;
- original CLS pooling retained;
- three binary outcome heads;
- all encoder and head parameters trainable;
- same multiple-instance maximum over chunk logits;
- same 384-token chunks, 64-token overlap, maximum 5 chunks.

## Prespecified v2 repair

The following settings are frozen before the v2 validation run:

- positive class weight: 3.0, exactly matching the frozen 1:3 case-control sampling ratio;
- encoder learning rate: 5e-6;
- classification-head learning rate: 1e-4;
- optimizer: AdamW;
- weight decay: 0.01;
- epochs: 5;
- note batch size: 2;
- gradient accumulation: 8;
- effective note batch size: 16;
- precision: bfloat16;
- gradient clipping: 1.0;
- linear learning-rate decay;
- warm-up: 10% of optimizer steps;
- gradient checkpointing: disabled;
- seed: 20260924;
- outcome-size weighting retained from v1 so the large ICU-death cohort does not dominate the shared encoder.

The 5-epoch window is fixed before v2 validation. The selected checkpoint is the epoch with highest mean validation AUROC across the three outcomes, with mean validation AUPRC as tie-breaker.

## Development stopping rule

This is the only repaired neural training recipe planned for this arm.

If v2 still shows broadly chance-level validation discrimination or clear optimization collapse, the supervised encoder arm will be reported as unsuccessful and will not be iteratively tuned against validation.

If v2 shows coherent validation discrimination, the selected checkpoint and a final test analysis plan will be frozen before the locked test split is accessed.

## Provenance

- v1 development: RunRelay `M7K3V8R2`
- learning diagnostic: RunRelay `P7K4M9R2`
- train-only recipe probe: RunRelay `R7K4M9V2`

These diagnostics are development evidence only and are not final performance claims.
