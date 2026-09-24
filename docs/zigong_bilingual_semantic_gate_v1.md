# Zigong bilingual semantic applicability gate v1

This protocol is frozen before any semantic-model performance is inspected on the Zigong outcome labels.

## Purpose

Tokenizer coverage is necessary but does not establish that an English-developed semantic model interprets Chinese clinical language correctly. Before any model is allowed to score the frozen Zigong ventilation cohort for outcome analysis, it must pass a label-free bilingual semantic-consistency gate.

The gate uses only synthetic clinical text. No Zigong labels, outcomes, source identifiers, or patient text are used.

## Frozen inputs

Machine-readable input: `configs/zigong_bilingual_semantic_gate_v1.json`.

Eight construct-specific contrast pairs are defined. Each contrast has:

- a semantically negative state;
- a semantically positive state for the target construct;
- an English version;
- a Chinese version conveying the same intended meaning.

The eight target constructs are exactly the frozen project semantic constructs:

1. overall clinician concern
2. worsening trajectory
3. respiratory concern
4. hemodynamic concern
5. poor treatment response
6. escalation considered
7. diagnostic uncertainty
8. reassuring stability

## Model-specific scoring

### Open-Jev

Use the same local `OpenJev.from_pretrained(...)` implementation, eight noul questions, question criteria, and question-packing logic as the frozen MIMIC pipeline.

### Laya

Use the same pinned local `laya.load(...)` implementation and eight noul questions as the frozen MIMIC pipeline.

### DiffusionGemma

Use the same official local `google/diffusiongemma-26B-A4B-it` checkpoint, native Hugging Face block-diffusion implementation, prompt, score definition, and parsing logic as the frozen MIMIC DiffusionGemma arm.

DiffusionGemma scores remain prompted 0-1 support scores and are not treated as Jev noul probabilities.

## Frozen metrics

For each model:

1. **Cross-language Spearman correlation**
   - Flatten the eight semantic scores across all 16 semantic states.
   - Correlate the English score vector with the matched Chinese score vector.

2. **Absolute cross-language score difference**
   - Compute the absolute English-Chinese difference for every state × construct score.
   - Report the mean, median, 90th percentile, and maximum.

3. **Target-contrast direction**
   - For each target construct, compute positive-state minus negative-state score separately in English and Chinese.
   - A direction is correct only if the difference is positive in both languages.
   - A strong direction requires a difference of at least 0.15 in both languages.

## Frozen pass rule

A model passes the direct-Chinese semantic gate only if all are true:

- every one of the 32 synthetic notes returns all eight valid scores;
- cross-language Spearman correlation is at least 0.70;
- median absolute English-Chinese score difference is at most 0.15;
- at least 7 of 8 target contrasts have the correct direction in both languages;
- at least 6 of 8 target contrasts have a margin of at least 0.15 in both languages.

These thresholds are pragmatic applicability criteria, not estimates of clinical accuracy.

## Consequences

- Only models that pass may be evaluated directly on the frozen Chinese Zigong narrative cohort.
- A failed model is excluded from direct-Chinese Zigong outcome scoring.
- There is no post-hoc translation, prompt rewriting, threshold tuning, or model adaptation based on Zigong labels.
- If translation is studied later, it must be a separately frozen analysis with a translation method selected without Zigong outcome performance.

## Reporting

The shared gate artifact may contain synthetic per-contrast score deltas and aggregate consistency metrics because the inputs are synthetic and contain no patient information.

Passing this gate does not establish clinical external validity. It only establishes a minimum language/semantic applicability condition for proceeding to the frozen outcome evaluation.
