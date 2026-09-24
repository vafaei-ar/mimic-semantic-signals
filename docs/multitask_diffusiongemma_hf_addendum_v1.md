# Native Hugging Face DiffusionGemma implementation addendum v1

## Purpose

This document records a post-protocol implementation deviation for the frozen multi-outcome semantic benchmark without changing any endpoint, horizon, cohort, matching, note-availability, leakage-exclusion, structured-feature, or TF-IDF specification.

The original frozen protocol anticipated a local DiffusionGemma-Jev serving path. That path could not be executed on the bound workstation because the available NVIDIA driver was incompatible with the CUDA requirement of the attempted serving stack. No driver or system CUDA upgrade was performed for the study.

## Implemented robustness representation

The completed third-model arm instead uses the official `google/diffusiongemma-26B-A4B-it` checkpoint through native Hugging Face Transformers, fully offline on the bound workstation.

The model receives the same frozen eight semantic constructs used for the zero-shot benchmark and returns prompted 0-1 support scores. These scores are scientifically distinct from Open-Jev and Laya `noul` probabilities and must not be described as Jev-equivalent outputs.

Key constraints:

- local-only clinical-note inference;
- no remote API or note transmission;
- no outcome-specific encoder tuning;
- no change to frozen cohorts or outcome definitions;
- no change to the eight semantic constructs;
- row-level note text and patient-level predictions remain local;
- only aggregate diagnostics and evaluation summaries are shared.

## Interpretation

Native-HF DiffusionGemma is treated as a separate prompted robustness representation that tests whether a third local model can compress the same clinically interpretable constructs into predictive low-dimensional scores.

It does not replace the originally planned Jev-compatible implementation and does not establish equivalence to Jev `noul` probabilities.

Before the zero-shot benchmark is declared fully frozen, the native-HF DiffusionGemma representation must undergo the same fold-fitted TF-IDF lexical control already applied to Open-Jev and Laya:

- structured EHR only;
- structured EHR + TF-IDF;
- structured EHR + DiffusionGemma scores;
- structured EHR + TF-IDF + DiffusionGemma scores.

The primary scientific interpretation remains that compact semantic scores are interpretable compression of predictive note content. Any claim of information unique beyond raw lexical text requires a positive incremental result after the TF-IDF control.
