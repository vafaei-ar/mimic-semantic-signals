# Frozen multi-outcome zero-shot benchmark v1

Frozen after completion of the prespecified zero-shot semantic, structured, lexical, and third-model robustness analyses. No tuning result may replace, overwrite, or be reported as the frozen zero-shot benchmark.

## Frozen design

Protocol: `docs/multitask_benchmark_protocol_v1.md`

Native-HF DiffusionGemma implementation addendum: `docs/multitask_diffusiongemma_hf_addendum_v1.md`

New outcomes:

- invasive ventilation within 12 hours: 365 cases + 1,095 matched controls, n=1,460
- renal-replacement therapy within 12 hours: 583 cases + 1,749 matched controls, n=2,332
- ICU death within 12 hours: 2,060 cases + 6,180 matched controls, n=8,240

All three use the previously frozen 6-hour incident washout, prospective note availability, endpoint-language exclusion, contemporaneous structured features, 1:3 matched risk-set controls, and grouped cross-validation by matched set.

The earlier 6-hour vasopressor v5 analysis remains a separate frozen case study and is not altered by this benchmark.

## Semantic representations

### Open-Jev

Zero-shot typed semantic probabilities for the frozen eight constructs.

### Laya

Zero-shot typed semantic probabilities for the same frozen eight constructs.

### Native-HF DiffusionGemma

Official `google/diffusiongemma-26B-A4B-it` run fully offline through native Hugging Face Transformers. The eight outputs are prompted 0-1 support scores, not Jev `noul` probabilities. This arm is a distinct robustness representation, not a Jev replication.

## Frozen zero-shot discrimination

### Invasive ventilation

| Representation | 8 scores only AUROC | Structured + semantics AUROC | Increment over structured, matched-set bootstrap |
| --- | ---: | ---: | ---: |
| Open-Jev | 0.645 | 0.697 | +0.0206 [0.0044, 0.0366] |
| Laya | 0.639 | 0.704 | +0.0277 [0.0096, 0.0465] |
| Native-HF DiffusionGemma | 0.694 | 0.722 | +0.0452 [0.0253, 0.0655] |

Structured-only AUROC: 0.677.

### Renal-replacement therapy

| Representation | 8 scores only AUROC | Structured + semantics AUROC | Increment over structured, matched-set bootstrap |
| --- | ---: | ---: | ---: |
| Open-Jev | 0.666 | 0.968 | +0.00045 [-0.00078, 0.00157] |
| Laya | 0.653 | 0.968 | +0.00042 [-0.00150, 0.00252] |
| Native-HF DiffusionGemma | 0.659 | 0.967 | -0.00061 [-0.00170, 0.00043] |

Structured-only AUROC: 0.968. Prior structured ablation showed that contemporaneous creatinine accounts for much of this saturation.

### ICU death

| Representation | 8 scores only AUROC | Structured + semantics AUROC | Increment over structured, matched-set bootstrap |
| --- | ---: | ---: | ---: |
| Open-Jev | 0.751 | 0.882 | +0.0211 [0.0165, 0.0261] |
| Laya | 0.699 | 0.871 | +0.0099 [0.0064, 0.0133] |
| Native-HF DiffusionGemma | 0.792 | 0.888 | +0.0272 [0.0215, 0.0330] |

Structured-only AUROC: 0.861.

## Frozen TF-IDF lexical control

TF-IDF is fit within each training fold only, using unigrams + bigrams and a maximum vocabulary of 10,000 features.

### Open-Jev and Laya after structured + TF-IDF

Matched-set bootstrap AUROC increment of adding semantic scores to structured + TF-IDF:

| Outcome | Open-Jev | Laya |
| --- | ---: | ---: |
| Ventilation | -0.0010 [-0.0124, 0.0105] | +0.0003 [-0.0120, 0.0108] |
| RRT | -0.00030 [-0.00098, 0.00041] | -0.00010 [-0.00163, 0.00154] |
| ICU death | +0.00049 [-0.00122, 0.00220] | -0.00063 [-0.00186, 0.00052] |

### Native-HF DiffusionGemma after structured + TF-IDF

| Outcome | Structured + TF-IDF AUROC | + DiffusionGemma AUROC | Increment, matched-set bootstrap |
| --- | ---: | ---: | ---: |
| Ventilation | 0.772 | 0.778 | +0.00591 [-0.00833, 0.02015] |
| RRT | 0.971 | 0.970 | -0.00077 [-0.00175, 0.00012] |
| ICU death | 0.937 | 0.940 | +0.00307 [0.00070, 0.00533] |

The DiffusionGemma repeat-level ventilation increment was positive in all 10 repeats, but the matched-set bootstrap confidence interval includes zero. ICU death retains a small positive increment after TF-IDF.

## Frozen interpretation

The cross-outcome result supports a low-dimensional, clinically interpretable semantic compression of predictive note content.

It does not support a broad claim that the eight semantic scores contain substantial information unavailable to raw lexical text. Open-Jev and Laya show essentially no AUROC increment after fold-fitted TF-IDF across all three new outcomes. Native-HF DiffusionGemma shows no clear lexical-independent increment for ventilation or RRT and only a small positive increment for ICU death.

The central zero-shot finding is therefore:

1. the same eight clinically interpretable constructs carry prospective predictive signal across distinct deterioration outcomes;
2. their incremental value beyond structured physiology is outcome-dependent;
3. much of that information is also accessible to a simple high-dimensional lexical representation;
4. the eight-score layer is best interpreted as compact, reusable, interpretable compression rather than a uniquely informative representation.

## Calibration and utility guardrail

All new-outcome cohorts were sampled at 1:3 case-control matching, yielding artificial 25% prevalence. Brier scores and related calibration summaries from these sampled cohorts are descriptive only. Population calibration, decision curves, and clinical utility require prevalence-representative risk sets or justified weighting.

## Frozen source artifacts

- Open-Jev/Laya semantic evaluation: RunRelay job `C7M4V9R2`, artifact `outputs/multitask_benchmark/zero_shot_semantic_report_v1.json`, SHA-256 `ea182c2e85319ba961f71d08218f5f3d834feb273e3f6739a73ca51a687e1a2e`
- Open-Jev/Laya lexical control: RunRelay job `F7V3M8K2`, artifact `outputs/multitask_benchmark/lexical_report_v1.json`, SHA-256 `8328acc37009f3648422d316218a5fe792e43d29e58f9c573c82fa8247171afc`
- Native-HF DiffusionGemma inference: RunRelay job `G7K4M2R8`, artifact `outputs/multitask_benchmark/diffusiongemma_hf_native_inference_report.json`, SHA-256 `38ef5f6b47225a954a1d973d85653b9486f0d2e752788b06366929cfd8b05926`
- Native-HF DiffusionGemma semantic evaluation: RunRelay job `H8M3R7K2`, artifact `outputs/multitask_benchmark/diffusiongemma_hf_semantic_report_v1.json`, SHA-256 `a2b9719254955c5db302be5f19ae06f26c13e8fe17ce7b62d0c987ccea556789`
- Native-HF DiffusionGemma lexical control: RunRelay job `M9R4K7V2`, artifact `outputs/multitask_benchmark/diffusiongemma_lexical_report_v1.json`, SHA-256 `1ae6bc145ba34f1f7e13a3a452eecf2e98eadf6759b8ccd2f1b9823735327200`

## Rule for all later tuning

Any supervised adaptation, prompt optimization, calibration, fine-tuning, distillation, or outcome-specific model development is a separate post-freeze phase. It must use new result names and must never overwrite these zero-shot artifacts or relabel tuned results as zero-shot.
