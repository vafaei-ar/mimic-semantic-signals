# Population-representative semantic extension result freeze v1

Canonical RunRelay job: `H8M3Q7V2`

- task: `evaluate_population_landmark12_semantic_extension`
- exact project commit: `419a80479d0a0e4abfbb97c8545909c85327a3cb`
- artifact: `outputs/multitask_benchmark/population_landmark12_semantic_extension_v1.json`
- artifact SHA-256: `35b95b124154c92f24aea4494065d66ddd8bccc1b7447474cdbb07ee40768eb7`
- exit code: 0
- runtime: 2864.454 seconds
- bootstrap: 1,000 paired patient-cluster replicates
- protocol: `docs/population_landmark12_semantic_extension_protocol_v1.md`

This document freezes the full-population semantic-extension result exactly as observed. No cohort, landmark, feature definition, semantic representation, lexical representation, threshold, or comparator may be changed in response to these results.

## Population cohorts

| Outcome | N | Cases | Prevalence | Eligible note coverage |
| --- | ---: | ---: | ---: | ---: |
| Invasive ventilation | 28,699 | 282 | 0.983% | 67.69% |
| RRT | 48,831 | 391 | 0.801% | 69.29% |
| ICU death | 49,555 | 537 | 1.084% | 68.10% |

All observable rows were retained. No-note rows were represented explicitly according to the frozen protocol.

## Model discrimination

### Invasive ventilation

| Model | AUROC | AUPRC |
| --- | ---: | ---: |
| Structured | 0.7071 | 0.0231 |
| Structured + note context | 0.8596 | 0.0468 |
| + Open-Jev | 0.8629 | 0.0461 |
| + Laya | 0.8549 | 0.0440 |
| Structured + context + TF-IDF | 0.8651 | 0.0493 |
| + TF-IDF + Open-Jev | 0.8666 | 0.0487 |
| + TF-IDF + Laya | 0.8611 | 0.0465 |

Primary paired semantic comparisons:

- Open-Jev versus context: ΔAUROC **+0.00338**, 95% CI **-0.00134 to +0.00823**.
- Laya versus context: ΔAUROC **-0.00469**, 95% CI **-0.00835 to -0.00131**.
- Open-Jev after TF-IDF: ΔAUROC **+0.00147**, 95% CI **-0.00260 to +0.00570**.
- Laya after TF-IDF: ΔAUROC **-0.00400**, 95% CI **-0.00739 to -0.00089**.

Neither semantic representation improved AUPRC or Brier score. Open-Jev produced a very small positive net-benefit difference at the 0.5% threshold, but no broad, consistent utility improvement was demonstrated.

### Renal-replacement therapy

| Model | AUROC | AUPRC |
| --- | ---: | ---: |
| Structured | 0.9476 | 0.1444 |
| Structured + note context | 0.9455 | 0.2217 |
| + Open-Jev | 0.9448 | 0.2209 |
| + Laya | 0.9452 | 0.2201 |
| Structured + context + TF-IDF | 0.9490 | 0.2253 |
| + TF-IDF + Open-Jev | 0.9481 | 0.2234 |
| + TF-IDF + Laya | 0.9488 | 0.2237 |

Primary paired semantic comparisons:

- Open-Jev versus context: ΔAUROC **-0.00075**, 95% CI **-0.00249 to +0.00132**.
- Laya versus context: ΔAUROC **-0.00033**, 95% CI **-0.00274 to +0.00207**.
- Open-Jev after TF-IDF: ΔAUROC **-0.00092**, 95% CI **-0.00244 to +0.00069**.
- Laya after TF-IDF: ΔAUROC **-0.00019**, 95% CI **-0.00236 to +0.00198**.

There is no demonstrated semantic increment for RRT. This is consistent with the earlier finding that structured renal information nearly saturates discrimination.

### ICU death

| Model | AUROC | AUPRC |
| --- | ---: | ---: |
| Structured | 0.7929 | 0.1770 |
| Structured + note context | 0.7978 | 0.1805 |
| + Open-Jev | 0.8111 | 0.1777 |
| + Laya | 0.8050 | 0.1794 |
| Structured + context + TF-IDF | 0.8431 | 0.1969 |
| + TF-IDF + Open-Jev | 0.8485 | 0.1935 |
| + TF-IDF + Laya | 0.8437 | 0.1947 |

Primary paired semantic comparisons:

- Open-Jev versus context: ΔAUROC **+0.01332**, 95% CI **+0.00576 to +0.02153**.
- Laya versus context: ΔAUROC **+0.00720**, 95% CI **+0.00160 to +0.01347**.
- Open-Jev after TF-IDF: ΔAUROC **+0.00537**, 95% CI **+0.00013 to +0.01073**.
- Laya after TF-IDF: ΔAUROC **+0.00060**, 95% CI **-0.00348 to +0.00478**.

For ICU death, Open-Jev retains a reproducible AUROC increment even after TF-IDF. However, AUPRC and Brier score do not improve. The incremental net-benefit signal is threshold-dependent rather than universal. Open-Jev versus context has positive paired net-benefit confidence intervals at 0.25%, 0.5%, and 1.0% thresholds. After TF-IDF, positive paired net-benefit confidence intervals remain at 0.25% and 0.5%.

## Note-context finding

The largest new result is not a semantic-model effect. Documentation context itself is strongly predictive for some outcomes.

For invasive ventilation, adding note availability/category/source/age to structured features raises AUROC from **0.7071 to 0.8596** and AUPRC from **0.0231 to 0.0468**.

For RRT, AUROC is essentially unchanged/slightly lower, but AUPRC rises from **0.1444 to 0.2217**.

For ICU death, note context produces only a small discrimination increase.

This means the process of whether, when, and what type of note is documented contains substantial predictive information. That observation must be separated conceptually from semantic content.

## Frozen interpretation

The population-representative analysis narrows the semantic claim.

1. **Invasive ventilation:** there is no clear incremental Open-Jev AUROC beyond note context, and Laya worsens discrimination. Note-documentation context carries far more signal than the eight semantic scores.
2. **RRT:** there is no semantic increment. Structured renal physiology remains dominant.
3. **ICU death:** both semantic representations add AUROC beyond note context, and Open-Jev retains a small positive AUROC increment after TF-IDF. This is the strongest population-level semantic result.
4. **Clinical utility:** semantic AUROC gains do not translate into consistent AUPRC, Brier, or net-benefit gains. Utility claims must therefore remain narrow and threshold-specific.
5. **Lexical qualification:** TF-IDF remains stronger than the compact semantic layer for overall discrimination, but ICU death provides evidence that Open-Jev may retain a small lexical-independent component.

The paper should not claim that compact semantic scores generally improve population prediction across deterioration outcomes. A defensible claim is that clinically interpretable semantic measurements capture outcome-dependent prospective information, with the most reproducible population-level evidence currently seen for ICU death.

## Required follow-up before manuscript lock

The unusually large effect of note context, especially for ventilation, needs explicit decomposition before manuscript submission. A prespecified secondary analysis should separate:

- note availability alone;
- note category/source;
- note age;
- structured + all note context;
- note-available-only semantic comparisons.

This is necessary to distinguish documentation-process signal from narrative-content signal. The note-available-only analysis must remain a conditional sensitivity analysis and must not be presented as population calibration or population utility.

## Guardrails

- no post-hoc model or threshold tuning may use these results;
- no matched-sample calibration claim may replace this population analysis;
- no-note rows remain part of the primary population analysis;
- any note-available-only analysis is secondary and conditional;
- zero-shot, supervised, external-transport, and population results remain separate result families.
