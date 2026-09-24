# Supervised text-encoder v2 validation freeze

This document freezes the development result before any access to the locked test split.

## Canonical development run

- RunRelay job: `Y8R4K2M7`
- task: `train_supervised_text_encoder_v2`
- exact project commit: `a4020ea16aceb5a2ac33c17bf292fe4e2a08d455`
- aggregate artifact: `outputs/multitask_benchmark/supervised_text_encoder_development_v2.json`
- artifact SHA-256: `755dcdd4cfbb695cb6f2d52101e0256c3ee30d4b70cd04fd2cb2e9765ebfa99f`

The run completed all five epochs with `test_split_read: false`.

## Frozen checkpoint-selection rule

The prespecified rule was highest mean validation AUROC across ventilation, RRT, and ICU death, with mean validation AUPRC as tie-breaker.

Epoch 4 is therefore selected.

### Epoch-4 validation performance

| Outcome | AUROC | AUPRC |
| --- | ---: | ---: |
| Invasive ventilation | 0.6719 | 0.4761 |
| Renal-replacement therapy | 0.8335 | 0.6087 |
| ICU death | 0.9173 | 0.8235 |
| Mean | 0.8075 | 0.6361 |

No later epoch is substituted even though individual outcome metrics vary.

## Scientific interpretation

This model is an outcome-supervised predictive upper-bound/comparator initialized from the local Open-Jev DeBERTa encoder. It is not a semantic-preserving JEV model and does not replace the frozen zero-shot semantic benchmark.

## Test lock

The locked test split remains closed until:

1. the selected epoch-4 local checkpoint is hashed and verified;
2. its checkpoint hash is committed to the final-test protocol;
3. the final test comparators, metrics, bootstrap procedure, and reporting rules are frozen.

Only then may a one-time test job open the test split.
