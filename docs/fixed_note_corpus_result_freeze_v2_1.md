# Fixed-note corpus result freeze v2.1

Updated: 2026-09-25

## Status

**Frozen before semantic or lexical v2.1 inference.**

Canonical RunRelay job:

- job: `R8Q6M4N2 — Build Fixed Note Corpora`;
- project commit: `0bbd69ad8d83df84ed90ad9772323b6bfc8b9b2f`;
- task: `build_fixed_note_corpora_v2_1`;
- status: completed;
- exit code: 0;
- runtime: 26.681 seconds;
- aggregate artifact: `outputs/multitask_benchmark/fixed_note_corpora_v2_1.json`;
- artifact SHA-256: `608cf993ba080afd54e2157a94d506d9406966795f91d78be2550960c600db5c`.

No semantic model, TF-IDF model, or clinical prediction model was run.

## Frozen transformation

Primary corpus: **language stripped**.

Secondary corpus: **full unstripped prospective note**.

Transformation:

- exact patterns from `config/v2_1_language_stripping_freeze.json`;
- case-insensitive;
- each matched span replaced by a single ASCII space;
- no other normalization;
- note identity/timing/category/eligibility/has_note unchanged.

## Strong equivalence check

For every source-specific analysis, the number of selected notes changed by the stripping regex exactly matched the corrected cohort's `direct_outcome_language_present` count.

| Analysis | Notes available | Direct-language flagged | Notes changed | Regex matches |
| --- | ---: | ---: | ---: | ---: |
| Ventilation, MetaVision | 4,499 | 618 | 618 | 849 |
| RRT, MetaVision | 7,709 | 347 | 347 | 670 |
| ICU death, MetaVision | 7,889 | 797 | 797 | 2,092 |
| ICU death, CareVue | 23,272 | 1,159 | 1,159 | 2,333 |

This equivalence is an executable guardrail against drift between cohort-language auditing and corpus materialization.

## Frozen note identities and corpus hashes

### Invasive ventilation — MetaVision
- eligible rows: 11,116;
- note identity SHA-256: `4a5f75dc9fd16fd0e3394c97d47d99d842230cc301ab01e4794ca969bd7271f3`;
- full corpus SHA-256: `ae47daa2a80e93960db4e68f65424b16a938cfb460da3727fda1668f446002f7`;
- stripped corpus SHA-256: `63278b2cd6da2d1a5b576b51df645e46c2860c8fa090409fd17a3b5365a29f4a`.

### RRT — MetaVision
- eligible rows: 19,395;
- note identity SHA-256: `750f84b5f887928c90592137e5b0c7bb035530ce446a3542b3def0f9d5eab858`;
- full corpus SHA-256: `5128d0f26ef52f4ea2dc20f1f2d6ae84b581e4d7063ccd2360b016238a68329c`;
- stripped corpus SHA-256: `5113938d11a04df39c2189fc91f7e71b487c5dec6c6f3119f192028e3329ee5f`.

### ICU death — MetaVision confirmatory
- eligible rows: 19,811;
- note identity SHA-256: `9d604176b53dac81f8a5e2d08e26dedcbea1f9e604baf200565d50a2e89b97dd`;
- full corpus SHA-256: `1ebb6c0a92a0c257f1e6d8d8f145f7b82c8c786aedff92a8b7478b4581823760`;
- stripped corpus SHA-256: `8e60221c0c5db1074c0f14f5bd39b78252d0e5388bec8c3ca90b992c5a1a4aba`.

### ICU death — CareVue replication
- eligible rows: 25,632;
- note identity SHA-256: `bc1c29e740b418cb0a5ad477e4de6be16ec9ce8d031fe8b6c2b1db2cce11bfc1`;
- full corpus SHA-256: `b98d6bed822bcfe4d1dce00557d5962f5199b9fb0741357891735b7b5bbc1c6f`;
- stripped corpus SHA-256: `b322015403eb2717919b153036e0f8ce97d872ecd67c9265632e485b3ff1c6e9`.

## Interpretation guardrail

Stripping is intended to reduce obvious outcome/treatment tautology, not to remove all prognostic content or treatment intent.

The primary TF-IDF lexical reference must use the same stripped corpus as the primary semantic analysis.

The state-dominant semantic ablation remains prespecified because management intent can survive keyword stripping.

## Superseded failed attempts

`J8R6Q4M2` and `N8R6Q4M2` produced no artifacts and no inference. They failed on representation-only note-hash checks. Their causes and corrections are documented in `docs/06_POSTREVIEW_V2_1_CORRECTIONS.md`.

## Downstream gate

The text preprocessing layer is now frozen. No semantic or lexical inference may run until the post-review confirmatory SAP is registered and the registration-ID execution lock is satisfied.
