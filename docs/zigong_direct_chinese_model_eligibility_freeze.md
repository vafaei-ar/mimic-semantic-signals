# Zigong direct-Chinese model eligibility freeze

This decision is frozen before any Zigong outcome performance is inspected.

## Source gate

Canonical RunRelay job: `H7R4K9M3`

Artifact: `outputs/zigong_external/bilingual_semantic_gate_v1.json`

Artifact SHA-256: `4a225fe589da282c528daa1159c909c83817e8e6fe78a8236c10b691cda99fac`

The gate was synthetic-only and used no Zigong outcome labels or patient data.

## Frozen eligibility

### DiffusionGemma: eligible

- cross-language Spearman: 0.9618
- median absolute English-Chinese score difference: 0.000
- target contrasts correct in both languages: 8/8
- strong target contrasts in both languages: 8/8
- passed all prespecified criteria

### Open-Jev: not eligible

- cross-language Spearman: 0.9389
- median absolute English-Chinese score difference: 0.0267
- target contrasts correct in both languages: 6/8
- strong target contrasts in both languages: 4/8
- failed the prespecified semantic-direction thresholds

Open-Jev must not be scored directly on Zigong outcome labels.

### Laya: not eligible

- cross-language Spearman: 0.5727
- median absolute English-Chinese score difference: 0.0596
- target contrasts correct in both languages: 4/8
- strong target contrasts in both languages: 1/8
- failed the prespecified correlation and semantic-direction thresholds

Laya must not be scored directly on Zigong outcome labels.

## Consequence

Only the frozen native-HF DiffusionGemma representation may proceed to direct-Chinese Zigong outcome evaluation.

No translation, prompt adaptation, threshold tuning, or model modification is permitted based on Zigong outcome performance.
