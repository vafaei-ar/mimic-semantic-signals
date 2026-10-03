# Paper 1 label-free semantic alignment audit

Updated: 2026-10-03

This is a post-registration integrity audit performed before final manuscript interpretation of the registered near-null Open-Jev increments. It did not read outcome labels and does not modify any registered estimate.

## Canonical run

- RunRelay job: `V3K7R2M9`
- exact project commit: `3f3eb770e9d2b60726bb34868481e651f669672e`
- artifact: `outputs/multitask_benchmark/submission_semantic_alignment_audit_v2_1.json`
- artifact SHA-256: `da28306244f8fcfa07a5172abcb86e33bd1e2639af974240fcc3f3fa0ea5003b`
- outcome labels read: no
- semantic/note case IDs: exact match in all three primary MetaVision cohorts
- same-patient donor assignments in shuffled reference: 0

## Matched construct-state checks

Spearman correlations below compare the real Open-Jev construct with the corresponding pre-landmark structured state and the same statistic after complete semantic-score vectors were shuffled between different patients.

| Outcome | Construct-state pair | Real rho | Shuffled rho |
|---|---|---:|---:|
| Ventilation | Hemodynamic concern vs vasoactive active | +0.183 | +0.015 |
| Ventilation | Respiratory concern vs high-flow | +0.177 | +0.003 |
| Ventilation | Respiratory concern vs NIV | +0.081 | -0.003 |
| Ventilation | Respiratory concern vs FiO2 | +0.061 | +0.027 |
| RRT | Hemodynamic concern vs vasoactive active | +0.137 | +0.001 |
| RRT | Respiratory concern vs high-flow | +0.129 | +0.012 |
| RRT | Respiratory concern vs NIV | +0.106 | +0.000 |
| RRT | Respiratory concern vs FiO2 | +0.077 | -0.009 |
| ICU death | Hemodynamic concern vs vasoactive active | +0.145 | -0.019 |
| ICU death | Respiratory concern vs high-flow | +0.128 | +0.006 |
| ICU death | Respiratory concern vs NIV | +0.103 | -0.007 |
| ICU death | Respiratory concern vs FiO2 | +0.084 | -0.023 |

The binary-state mean-score contrasts show the same pattern. For example, respiratory concern was higher among high-flow rows by 0.0616 in ventilation, 0.0503 in RRT, and 0.0503 in ICU death, compared with shuffled contrasts of 0.0021, 0.0051, and 0.0025 respectively.

## Chunking sanity check

The number of scored chunks was strongly related to note length as expected:

| Outcome | Chunks vs note characters, rho | Chunks vs note tokens, rho |
|---|---:|---:|
| Ventilation | 0.979 | 0.983 |
| RRT | 0.974 | 0.982 |
| ICU death | 0.975 | 0.982 |

## Reassuring-stability caveat

`reassuring_stability` did not show the same consistent expected inverse relationship with support variables. Several correlations were near zero, and vasoactive-support associations in RRT and ICU death were weakly positive rather than negative.

This does not indicate row misalignment because the specifically matched hemodynamic and respiratory constructs consistently separate from shuffled references. It does mean the audit should **not** be presented as construct validation of all eight dimensions.

## Interpretation

The audit passes its narrow integrity purpose: gross semantic-score to note/stay misalignment is unlikely to explain the registered near-null incremental results.

The manuscript may state that a label-free integrity audit showed expected construct-state alignment for hemodynamic and respiratory concern relative to between-patient shuffled references.

The manuscript must not infer clinician construct validity from this audit. Human construct validation was not performed, and the inconsistent reassuring-stability behavior should be acknowledged when discussing interpretability.
