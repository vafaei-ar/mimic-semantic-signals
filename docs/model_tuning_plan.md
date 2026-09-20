# Clinical semantic decision-model tuning plan

## Goal

Compare the same clinical semantic decision task across:

1. Open-Jev DeBERTa base
2. Open-Jev DeBERTa clinical-tuned
3. DiffusionGemma base in Jev-compatible structured-read mode
4. DiffusionGemma clinical-tuned
5. Optional proprietary TypeSafe Jev comparator if compliant access is resolved

The scientific question is whether narrative semantic signals are robust across model architectures, not whether one branded model wins.

## Public vs private model tracks

### Public track

Training inputs must be synthetic or otherwise publicly redistributable.

Outputs may be published to Hugging Face when licensing and documentation requirements are satisfied.

Recommended release artifacts:

- adapter or checkpoint
- model card
- training manifest
- exact base-model revision
- exact code commit
- synthetic/public training-corpus manifest
- held-out and OOD benchmark metrics
- calibration results
- limitations and intended-use statement

### Private credentialed-data track

If a model is adapted on credentialed MIMIC data, treat the resulting model as a sensitive derivative.

Do not publish such a checkpoint openly on Hugging Face. If distribution is scientifically necessary, follow PhysioNet's requirements for sharing derived models under the same credentialed access agreement.

## Dataset design

Use patient/admission-group splits before training.

Required evaluation sets:

- in-domain held-out states
- OOD paraphrased questions
- note-category strata
- time-to-event strata
- narrative-physiology discordance strata
- stable non-event controls

Never expose future-derived metadata such as time to event to the model.

## Open-Jev tuning

Base:

- com-kotobalabs/open-jev-deberta-v3-large

Strategy:

- continue training from the released backbone AND released scoring head
- CE + Brier loss
- moderate gold-preserving question augmentation
- fit temperature on validation only
- report in-domain and OOD calibration separately

Current repository scripts:

- src/17_build_public_tuning_corpus.py
- src/18_finetune_open_jev.py

## DiffusionGemma tuning

Base:

- google/diffusiongemma-26B-A4B-it

Preferred first strategy:

- text-only PEFT/LoRA
- clinical semantic decision prompts
- exact same training/validation/test split as Open-Jev
- preserve a separate structured-read evaluation path

The current djev-spark server implements Jev-compatible structured reads, but does not yet expose a documented LoRA adapter path. Therefore:

1. train the adapter with Transformers/PEFT
2. evaluate conventional structured decision prompting through Transformers
3. separately evaluate the untuned model through djev-spark structured reads
4. add tuned structured-read evaluation once the serving path supports the adapter reproducibly

Do not merge the adapter into tied DiffusionGemma weights unless the upstream implementation explicitly supports it.

## Comparison metrics

Primary:

- AUROC per binary semantic construct
- Brier score
- ECE / calibration curve
- positive-negative probability separation

Scientific behavior:

- lead-time trend before deterioration
- hidden-concern / reassuring-physiology discordance
- note-category robustness
- OOD question robustness
- calibration shift from synthetic/public data to private real data

Engineering:

- latency
- throughput
- peak GPU memory
- training wall time
- trainable parameter count

## Publication gate

A public tuned checkpoint should be released only if:

1. it improves held-out and OOD performance, not only training/in-domain performance;
2. calibration is not materially worse;
3. gains reproduce across at least 3 seeds;
4. no credentialed clinical text or MIMIC-derived model weights are included;
5. the model card clearly distinguishes synthetic/public training from private study validation.
