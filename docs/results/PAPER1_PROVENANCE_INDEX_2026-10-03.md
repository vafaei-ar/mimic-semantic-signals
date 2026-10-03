# Paper 1 manuscript-number provenance index

Updated: 2026-10-03

This file is the manuscript-facing provenance index for the corrected v2.1 Paper 1 lineage. It is intended to keep internal job/artifact identifiers out of ordinary manuscript prose while preserving an exact supplement/audit trail.

## Registration

- OSF registration: `ahxn9`
- DOI: `10.17605/OSF.IO/AHXN9`
- cited registration commit: `873897e6c934cea3d558b6518ac1e399f9f75387`
- registration manifest SHA-256: `22ac9f815309d81ebf03d279087848e33f8c0a16b563efe8af114a196194fc7d`
- OSF byte-level attachment verification: `docs/registration/osf_attachment_verification_2026-09-28.md`
- OSF scientific-text verification: `docs/registration/osf_attachment_text_verification_2026-10-03.md`

The frozen OSF PDFs differ byte-for-byte from the earlier local package PDFs, but their normalized ordered scientific word sequence matches the exact source at the cited registration commit.

## H1-H3 primary Open-Jev analyses

| Analysis | Primary delta AUROC | 95% refit-bootstrap interval | RunRelay job | Artifact SHA-256 |
|---|---:|---:|---|---|
| H1 invasive ventilation | -0.00005 | -0.02173 to +0.01910 | `T7V8M2K5` | `238c02d25a37cd4f0238d062f70b3e58ef6653181470cfefc62895035d7b5baa` |
| H2 RRT | -0.00079 | -0.00323 to +0.00275 | `Y8M2R5K7` | `cb8ae6d23138e03da4495998e5e2973f0f32169d513668cdd1863d82d53637d2` |
| H3 MetaVision ICU death | -0.00212 | -0.00802 to +0.00531 | `3CM7R5K9` | `e971eae985087a40b25c164228e6d36bce90bbfb3a207b60846df50832a52a47` |

Canonical summary: `docs/results/v2_1_primary_openjev_results.md`.

## H4 six-construct analysis

| Outcome | Delta AUROC | 95% interval | Job | Artifact SHA-256 |
|---|---:|---:|---|---|
| Ventilation | -0.01342 | -0.02301 to +0.01523 | `5EM7R5K9` | `f7201952d8e69e0754e375b4082a35b6538e9a8a7d300dcb89b46e57a7d3ddd8` |
| RRT | -0.00049 | -0.00317 to +0.00282 | `7GM7R5K9` | `00ccf6d08b0b95c5caab22f7886c4d441e914b4534e7d8ae1ef4c05ba5baac8f` |
| MetaVision ICU death | -0.00472 | -0.00840 to +0.00530 | `8HM7R5K9` | `662cd5f1e6d84cf902867f3abf12105d3c46a2746ffc0dd341ef8446bd3478f8` |

Canonical summary: `docs/results/v2_1_h4_six_construct_results.md`.

## H5 common-logistic representation comparison

| Outcome | Open-Jev increment | TF-IDF increment | Open-Jev after TF-IDF | Job | Artifact SHA-256 |
|---|---:|---:|---:|---|---|
| Ventilation | -0.00826 | +0.00564 | -0.00673 | `AJM7R5K9` | `babe8078e8018f187adb050b05b5031aeff3b7a6d1099d3e20f22c2b2657d6e0` |
| RRT | -0.00194 | +0.00219 | -0.00153 | `H8N4T7V2` | `00185d1b9a28dd9ada787eb55a8c18b6ef4c53bda9934dac4b052b5fb0076e36` |
| MetaVision ICU death | -0.00631 | +0.00123 | -0.00580 | `F6N7R5K9` | `ab8e58b43b6b058a9f72968f5ea7ba16ecadbc228e6bb56e546e1362f3657222` |

Canonical summary: `docs/results/v2_1_h5_lexical_results.md`.

## Principal H6 semantic-instrument sensitivities

### Unstripped Open-Jev

| Outcome | Delta AUROC | 95% interval | Job | Artifact SHA-256 |
|---|---:|---:|---|---|
| Ventilation | -0.01043 | -0.02177 to +0.01773 | `N5N7T9V2` | `17bc887375edef3b7222ef00cfb94f1663e338147c2835230c0dd69f08b3fde0` |
| RRT | -0.00034 | -0.00308 to +0.00310 | `R8N4T9V2` | `510a94d30a6f55b718380ca64ca7fdfdef19dc400ecc15a686ea81dc47e8cf8a` |
| MetaVision ICU death | +0.00108 | -0.00911 to +0.00602 | `T4N7R9V2` | `79717c4c236867a697e373c83b545b7cf42ae1609f461cf171d5333141232a5f` |

### Laya

| Outcome | Delta AUROC | 95% interval | Job | Artifact SHA-256 |
|---|---:|---:|---|---|
| Ventilation | +0.01031 | -0.01595 to +0.02519 | `Y8N4R9T2` | `0dc443a57a2b69063a126b4dc56bef81d9faf6bd89e867321fc31b2222e9b3fc` |
| RRT | -0.00079 | -0.00278 to +0.00302 | `2AN4R7T9` | `7a3c4448a63502cc71043da215efad0e51c3e428dd4583775da4b1936c59cd73` |
| MetaVision ICU death | +0.00141 | -0.00660 to +0.00728 | `4CN4R7T9` | `a4c7ab502b880071dbd3f0cbbb35284765d4d410b835045971fef2072460d992` |

### DiffusionGemma

| Outcome | Delta AUROC | 95% interval | Job | Artifact SHA-256 |
|---|---:|---:|---|---|
| Ventilation | -0.00811 | -0.02030 to +0.01445 | `B7Q2M9RK` | `126be5aa7b0af9302e39485dabdd64c291fab60c6b9abfccbf1dae553a464431` |
| RRT | -0.00083 | -0.00283 to +0.00244 | `F7K3Q9MV` | `179b0e6ea1ab6e4f60eeeb4027ae7c291eec51599597ce7dbcead318e884ef9a` |
| MetaVision ICU death | +0.00499 | -0.00654 to +0.00652 | `H9Q4M2VK` | `b12f961687c67c2ed25a689cd5f79d492b2db89010a8fc9c543cabbd19e0dc23` |

The complete H6 timing, endpoint, note-availability, laboratory-lag, and CareVue sensitivity provenance is in `docs/results/v2_1_h6_sensitivity_results.md`.

## CareVue ICU-death replication

- comparator AUROC: 0.93799
- comparator + Open-Jev AUROC: 0.93544
- delta AUROC: -0.00255
- 95% interval: -0.00858 to +0.00812
- evaluation job: `T8Y5Q2N6`
- artifact SHA-256: `024fdf839fa0625625da455511962dc84a5795b79855d49d985f38e63cc0c0c6`

## H7 patient-shuffled negative controls

| Outcome/source | Delta AUROC | 95% interval | Job | Artifact SHA-256 |
|---|---:|---:|---|---|
| Ventilation, MetaVision | -0.01059 | -0.02851 to +0.01432 | `W2C7M9R4` | `fc44f7b3c3ac8648f5da74a1d5c7af9bfeaefafea3a4ed144e0612a1c92ee057` |
| RRT, MetaVision | -0.00024 | -0.00269 to +0.00313 | `X3D8N6Q2` | `132799f693f36f8ed320c819ac76c368aadc47f5f21e968c4e3e816d5c893f54` |
| ICU death, MetaVision | +0.00309 | -0.00663 to +0.00599 | `Y4F9P7M2` | `e9fba18626f950cfabb1d87ed7d0377e08c115e34b83e0329bc2159ae4f0eb8d` |
| ICU death, CareVue | -0.00712 | -0.00784 to +0.00882 | `Z5G2R8N4` | `f9afb65cfef2264fabbf5c0e340535b94007aad932dab9df7c9c18d643294a36` |

Canonical summary: `docs/results/v2_1_h7_patient_shuffled_results.md`.

## H8 deviation

H8 clinician construct validation was prepared but not performed because independent qualified clinician raters and associated resources were unavailable in this single-author, unfunded study.

- preparation job: `D8K5W3R7`
- preparation artifact SHA-256: `9324d00459693fa7ebec8bffbe2a1143be227757ea91110116375646b007cd8f`
- ratings collected: none
- deviation: `docs/registration/deviation_h8_not_performed_2026-10-03.md`

No manuscript claim of clinician-validated construct validity is permitted.

## H9 deviation

The registered translated Zigong arm was not performed. The existing DiffusionGemma-only run reused the legacy frozen 24-hour Zigong cohort after a leakage-screen problem had been recognized and is therefore retained as descriptive modified transport evidence, not completed registered H9 external validation.

- descriptive AUROC: 0.5546
- 95% matched-set bootstrap interval: 0.4796 to 0.6308
- job: `F2N7Q5K9`
- artifact SHA-256: `14191cbef81c49dfe266500ec9eddb322254a10d17d9d82f75a1b39bf363f57f`
- deviation: `docs/registration/deviation_h9_partial_execution_2026-10-03.md`

Zigong is not central evidence for Paper 1.

## Post-registration label-free semantic alignment audit

- job: `V3K7R2M9`
- exact project commit: `3f3eb770e9d2b60726bb34868481e651f669672e`
- artifact SHA-256: `da28306244f8fcfa07a5172abcb86e33bd1e2639af974240fcc3f3fa0ea5003b`
- outcome labels read: no
- exact semantic/note case-ID match: yes
- between-patient shuffled same-patient assignments: 0

Matched hemodynamic and respiratory constructs showed consistently stronger expected construct-state associations than shuffled references. `reassuring_stability` was weak/inconsistent and is not treated as construct-validated.

Canonical summary: `docs/results/v2_1_submission_semantic_alignment_audit.md`.

## Post-registration semantic-only and comparator-decomposition analysis

The bounded exploratory analysis completed successfully:

- job: `W8D4K2R7`
- exact scientific commit: `3f3eb770e9d2b60726bb34868481e651f669672e`
- artifact: `outputs/multitask_benchmark/submission_exploratory_explanatory_v2_1.json`
- artifact SHA-256: `2d125d4f739057594ab066cabca1b5925c2b2c74960f701cadd32d7c923100aa`
- uncertainty: five pre-frozen patient-grouped partitions only; no new refit bootstrap
- status: post-registration exploratory

The scalar result table is frozen separately once extracted from the canonical safe artifact. This analysis does not modify H1-H3 or H5.

## Manuscript provenance rule

Every numerical value in the main text, abstract, figures, or supplement must map to one row/entry in this index or to a more detailed canonical result document linked from it.

Internal RunRelay job IDs, hashes, and freeze-language belong in the provenance supplement/table, not ordinary manuscript prose.
