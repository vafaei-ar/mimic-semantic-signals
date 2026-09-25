# Fixed-note corpus result freeze v2.1

Updated: 2026-09-25

## Status

**Frozen before semantic or lexical v2.1 inference.**

Canonical corrected RunRelay job:

- job: `P7R4Q9V2 — Refreeze Corrected Note Corpus`;
- exact project commit: `c1d862bd76c8bb4baea61d6c48b9109b0dbae669`;
- task: `build_fixed_note_corpora_v2_1`;
- status: completed;
- exit code: 0;
- runtime: 30.852 seconds;
- aggregate artifact: `outputs/multitask_benchmark/fixed_note_corpora_v2_1.json`;
- artifact SHA-256: `b6ace04ec469261d0c25b6c685c3c027c1b5bd8154b9dc028c7baa95e1edb4a0`.

No semantic model, TF-IDF model, or clinical prediction model was run.

## Corrected preregistration vocabulary

The primary corpus remains the **language-stripped fixed-note corpus**. The full note remains a prespecified secondary sensitivity.

The preregistration review broadened stripping before any v2.1 predictive performance by adding:

- standalone `vent` as direct ventilation language;
- `ultrafiltration` as direct renal-replacement/treatment language;
- context-limited `HD` expressions that indicate hemodialysis while still avoiding bare `HD` because of its hospital-day ambiguity.

Bare `RRT` remains unstripped because it can mean rapid response team.

The exact transformation remains:

- case-insensitive matching;
- each matched span replaced by one ASCII space;
- no other normalization;
- note identity, timing, category, eligibility, and `has_note` unchanged.

## Corrected stripping counts

The old cohort-level direct-language flags were computed before this vocabulary broadening. They are retained as provenance only and are **not** an equality target for the corrected corpus.

| Analysis | Note rows | Pre-review flagged | Corrected notes changed | Additional notes | Regex matches |
| --- | ---: | ---: | ---: | ---: | ---: |
| Ventilation, MetaVision | 4,499 | 618 | **646** | **28** | 897 |
| RRT, MetaVision | 7,709 | 347 | **465** | **118** | 1,303 |
| ICU death, MetaVision | 7,889 | 797 | **797** | 0 | 2,092 |
| ICU death, CareVue | 23,272 | 1,159 | **1,159** | 0 | 2,333 |

The change is confined to the outcomes whose vocabulary was intentionally broadened.

## Frozen note identities and corpus hashes

### Invasive ventilation — MetaVision

- eligible rows: 11,116;
- note identity SHA-256: `4a5f75dc9fd16fd0e3394c97d47d99d842230cc301ab01e4794ca969bd7271f3`;
- full corpus SHA-256: `ae47daa2a80e93960db4e68f65424b16a938cfb460da3727fda1668f446002f7`;
- corrected stripped corpus SHA-256: `42ea0a0c220c9cf21354451acd621a4e8ce90494a9498082abd2197920c7fa33`.

### RRT — MetaVision

- eligible rows: 19,395;
- note identity SHA-256: `750f84b5f887928c90592137e5b0c7bb035530ce446a3542b3def0f9d5eab858`;
- full corpus SHA-256: `5128d0f26ef52f4ea2dc20f1f2d6ae84b581e4d7063ccd2360b016238a68329c`;
- corrected stripped corpus SHA-256: `3b6637762e716f8318d0c1d7b38981a6fd3cbbaf2e6b4e95d5047ac5b280c715`.

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

## Superseded corpus

The earlier R8 corpus artifact (SHA-256 `608cf993...`) remains provenance only. It was superseded before any v2.1 semantic, lexical, or clinical predictive performance because the preregistration review deliberately broadened stripping vocabulary.

## Downstream rule

All primary semantic and TF-IDF text analyses must use the corrected stripped hashes frozen here.

No text inference may run until the post-review confirmatory SAP is externally registered and the registration-ID execution gate is satisfied.
