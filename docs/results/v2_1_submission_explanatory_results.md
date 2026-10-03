# Paper 1 post-registration explanatory results

Updated: 2026-10-03

This analysis is post-registration exploratory. It does not modify the registered H1-H7 estimates.

Its purpose is to answer two narrow questions needed to interpret the registered null result:

1. Do the eight Open-Jev scores carry outcome discrimination on their own among patients with an eligible note?
2. At what point in a nested structured comparator does any apparent Open-Jev increment disappear?

No new bootstrap was run. Stability is assessed using the five already-frozen patient-grouped partitions.

## Canonical execution

- scientific job: `W8D4K2R7`
- exact scientific commit: `3f3eb770e9d2b60726bb34868481e651f669672e`
- aggregate artifact: `outputs/multitask_benchmark/submission_exploratory_explanatory_v2_1.json`
- artifact SHA-256: `2d125d4f739057594ab066cabca1b5925c2b2c74960f701cadd32d7c923100aa`
- compact scalar extraction job: `A5N9R3K7`
- compact-summary artifact SHA-256: `b1a2c9b02cb7c07fb12d0b326ba10517ecc4e3ddcc3a8146000f4b3804fac113`

## Semantic-only discrimination

The semantic-only analysis uses only note-available rows and the same HGB specification with the frozen patient-grouped partitions.

Primary-partition AUROC:

| Outcome | Semantic-only AUROC |
|---|---:|
| Invasive ventilation | 0.60257 |
| RRT | 0.44790 |
| MetaVision ICU death | 0.65682 |

These values answer a different question from incremental discrimination. In particular, MetaVision death shows meaningful standalone discrimination but no positive increment after structured physiology is included.

RRT shows little useful standalone discrimination in this specification.

## Four-level HGB comparator decomposition

Comparator levels:

- **A:** frozen 34-feature physiology/laboratory/urine block only;
- **B:** A plus treatment/support context and death-only code status;
- **C:** B plus documentation-behavior features;
- **D:** C plus ordinary note context, equal to the registered rich comparator.

Primary-partition Open-Jev delta AUROC:

| Outcome | A: structured 34 | B: + treatment/support | C: + documentation behavior | D: registered rich comparator |
|---|---:|---:|---:|---:|
| Invasive ventilation | **+0.02032** | **+0.01137** | -0.00172 | -0.00005 |
| RRT | -0.00054 | -0.00070 | +0.00014 | -0.00079 |
| MetaVision ICU death | -0.00428 | -0.00280 | -0.00394 | -0.00212 |

## Interpretation

### Invasive ventilation

Ventilation is the only outcome in which semantic augmentation shows a material positive increment over the physiology-only model on the primary partition.

The increment falls from +0.02032 at level A to +0.01137 after treatment/support context and then disappears after documentation behavior is represented (-0.00172). The registered rich-comparator result remains essentially zero (-0.00005).

This pattern provides a plausible explanation for why earlier thinner-baseline analyses looked more favorable: apparent narrative/semantic predictive value can be absorbed by treatment/support and, especially, documentation-process information.

### Important availability caveat

At levels A and B, the comparator itself does not contain ordinary note-availability context. Because semantic values are missing for patients without an eligible note, the augmented model can use semantic missingness as a proxy for note availability.

Therefore the positive A/B ventilation increments must **not** be attributed purely to semantic content.

The fact that the increment disappears once documentation behavior is added is consistent with a substantial documentation-process/note-availability component. This is an explanatory decomposition, not a causal mediation analysis.

### RRT

Open-Jev adds essentially no AUROC at any comparator level. The very strong structured prediction problem therefore does not appear to conceal a substantial semantic increment that is specifically removed by documentation context.

### MetaVision ICU death

The eight scores have standalone discrimination (AUROC 0.65682 among note-available rows), but they do not improve AUROC even over the physiology-only comparator on the primary partition (-0.00428).

This supports a redundancy interpretation: the semantic scores contain prognostic information, but that information is not incrementally useful once standard structured clinical state is represented.

## Relationship to H5

Do not place the HGB decomposition and H5 TF-IDF increments in the same numerical comparison as if learner family were held constant.

H5 remains the appropriate semantic-versus-lexical representation comparison because Open-Jev and TF-IDF are evaluated within the same L2-penalized logistic family there. H5 shows small positive TF-IDF increments and negative Open-Jev increments across all three primary outcomes.

## Manuscript use

A defensible explanatory statement is:

> For ventilation, semantic augmentation improved discrimination over physiology alone, but this increment attenuated after treatment/support variables and disappeared after documentation behavior was included. For death, the semantic scores showed standalone prognostic discrimination but no incremental gain even over physiology alone; RRT showed neither pattern.

The ventilation statement must be accompanied by the note-availability caveat above.

Partition ranges from the five frozen splits should be reported as stability summaries, not inferential confidence intervals.
