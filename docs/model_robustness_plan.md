> **Historical planning note (2026-09-24):** This is a v1-era model-planning document, not the current execution plan. DiffusionGemma was subsequently evaluated, and the project is now in the corrected v2 lineage. Read `docs/01_READ_FIRST.md` and `docs/03_V2_ANALYSIS_LINEAGE.md` before using this file.

# Model robustness plan

Updated: 2026-09-21

The primary scientific question is whether semantic information extracted from clinical
narrative adds incremental discrimination beyond structured physiology. Model additions
must strengthen that claim rather than turn the study into a model leaderboard.

## Prespecified roles

### Primary semantic model

- `com-kotobalabs/open-jev-deberta-v3-large`
- Role: primary semantic extractor for the MIMIC-III analysis.
- Reason: already used for the frozen proof-of-concept and returns typed probabilistic
  decisions directly.
- Do not replace after seeing external results.

### Independent typed-decision robustness model

- `convaiinnovations/laya-typed-decisions`
- Role: architecture/model-family robustness sensitivity analysis.
- Runtime: upstream `laya` package on CUDA/Linux, not the Apple-Silicon MLX port.
- Important limitation: published typed-decisions gains are from fine-tuning on that
  benchmark's own training split and do not establish clinical zero-shot superiority.
- Study use: evaluate the same eight semantic constructs using the same case/note inputs.
  Do not tune on outcome labels from MIMIC.
- If adaptation is needed, use only synthetic/public construct labels that are independent
  of the clinical outcome cohort.

### Cross-language candidate

- `convaiinnovations/laya-multilingual`
- Role: candidate native multilingual semantic extractor for Zigong Chinese notes.
- Context: 1024 tokens by default.
- Important limitation: the model card reports poor zero-shot typed-decisions performance
  and over-confidence; clinical calibration and construct validity require local validation.
- Do not treat model confidence as calibrated clinical probability without held-out
  construct-level validation.

## Secondary research candidate

### BioClinical ModernBERT-large

- `thomas-sounack/BioClinical-ModernBERT-large`
- 396M parameter, 8192-token clinical/biomedical encoder.
- Potential role: external-cohort encoder/classifier sensitivity analysis.
- Not preferred as primary MIMIC-III semantic model because its continued-pretraining
  corpus includes MIMIC-III and MIMIC-IV notes, creating avoidable corpus-overlap concerns.
- A task-specific classification head would also need to be trained; it does not natively
  expose the typed-decision interface.

## Not currently prioritized

### Laya-MLX

- `aac6fef/laya-mlx`
- Native Apple-Silicon MLX conversion of upstream Laya weights.
- Useful for Mac deployment, but not scientifically different from the upstream checkpoint.
- Current research workstation is Linux/NVIDIA; use the upstream CUDA-compatible model.

### DiffusionGemma

- `google/diffusiongemma-26B-A4B-it`
- High-quality/fast generative diffusion model.
- Not currently prioritized because our analysis requires stable bounded construct
  probabilities. A generative model adds decoding/prompt variability and does not naturally
  provide the same calibrated typed-decision output.
- Reconsider only if a reproducible forced-choice/probability extraction method becomes
  available and adds clear scientific value.

### MedGemma

- Clinically adapted generative model family.
- Useful for clinical language understanding but substantially larger and generative.
- Not necessary unless a clinical generative sensitivity analysis is requested by reviewers
  or materially changes construct validity.

## Model inclusion gate

A new model is added only if it meets at least one of these scientific purposes:

1. independent architecture robustness;
2. domain-specific clinical language robustness;
3. multilingual/cross-language validation;
4. materially better long-context handling relevant to clinical notes.

And it must satisfy:

- local/offline inference for credentialed notes;
- reproducible version and pinned revision;
- license compatible with research use;
- no outcome-label training on the evaluation cohort;
- probability/score output that can be compared consistently across cases;
- a prespecified analysis before examining its outcome performance.

This keeps the manuscript focused on the clinical phenomenon rather than on model shopping.
