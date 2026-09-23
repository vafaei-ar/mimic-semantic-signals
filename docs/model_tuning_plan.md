# Clinical semantic decision-model tuning plan

## Goal

Compare the same clinical semantic decision task across local model implementations:

1. Open-Jev DeBERTa base
2. Laya typed-decisions base
3. DiffusionGemma-Jev base in local Jev-compatible structured-read mode
4. Open-Jev clinical-tuned
5. DiffusionGemma-Jev clinical-tuned, if a reproducible local adapter path is available

The scientific question is whether narrative semantic signals are robust across model architectures, not whether one branded model wins.

## Local-only inference policy

All credentialed clinical-note inference must remain on the bound local workstation.

- Do not send MIMIC, Zigong, or other restricted note text to Cloud Run or any remote inference API.
- `taeold/djev-run` is treated as a useful serving/reference implementation of the Jev-compatible `/v1/systemone` contract, not as a remote study endpoint.
- DiffusionGemma-Jev evaluation for this project must use a local `djev`/`djev-spark`-compatible server bound to localhost.
- Public or synthetic corpora may be used for local tuning and benchmarking, but study inference remains local.

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

The local djev/djev-spark stack implements Jev-compatible structured reads. Therefore:

1. run the untuned DiffusionGemma-Jev model locally through the Jev-compatible structured-read path;
2. train any adapter locally with Transformers/PEFT;
3. evaluate conventional structured decision prompting locally through Transformers;
4. add tuned structured-read evaluation only once the local serving path supports the adapter reproducibly.

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
