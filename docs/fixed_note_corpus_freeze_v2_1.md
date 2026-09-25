# Fixed-note text corpus freeze v2.1

Updated: 2026-09-25

## Status

**Frozen before semantic or lexical v2.1 inference.**

The primary text corpus for all three confirmatory outcomes is the **language-stripped fixed-note corpus**. The full prospective note is a prespecified secondary real-world-information sensitivity.

## Note identity

Stripping never participates in note selection.

For each eligible analysis row:

1. cohort eligibility and source-system eligibility are fixed;
2. the latest eligible prospective note is selected using the corrected v2.1 timing/category rules;
3. note identity, note time, category, and `has_note` are frozen;
4. only then is the selected note text transformed.

Patients without an eligible note remain without a note in both corpora.

## Transformation

For each outcome, compile the exact frozen patterns in:

- `config/v2_1_language_stripping_freeze.json`

with case-insensitive matching.

Apply the combined outcome-specific regex once to the selected note.

Each matched span is replaced by a single ASCII space.

**No other normalization is applied.**

In particular:

- no note is reselected after stripping;
- no sentence is deleted because it contains a match;
- line breaks are preserved;
- punctuation outside matched spans is preserved;
- whitespace is not globally collapsed;
- no semantic/LLM score is consulted.

## Outcome-specific principles

### Invasive ventilation

Strip invasive-specific terms including intubation/reintubation, endotracheal, mechanical ventilation, ventilator, and ETT.

BiPAP alone is not considered direct invasive-ventilation language.

### RRT

Strip unambiguous dialysis/RRT-treatment terminology such as dialysis, hemodialysis, CVVH/CRRT, hemofiltration, renal replacement, and trialysis.

Bare `HD` and bare `RRT` are not stripped because they can represent hospital day and rapid response team.

### ICU death

Strip direct death, comfort/palliative, DNR/DNI, hospice, goals-of-care, and withdrawal-of-care/support/treatment wording.

## Interpretation

The stripped corpus is intended to **reduce obvious outcome/treatment tautology**, not to prove that all treatment intent or prognostic information has been removed.

The prespecified state-dominant semantic ablation remains necessary because constructs such as treatment response and escalation intent can survive keyword stripping.

## Lexical comparator

The primary TF-IDF lexical reference must be trained and evaluated on this same stripped corpus.

An unstripped TF-IDF analysis belongs only to the unstripped text sensitivity.

## Outputs

The corpus materialization job will create local full and stripped JSONL files for:

- MetaVision ventilation;
- MetaVision RRT;
- MetaVision ICU death;
- CareVue ICU-death replication.

Only aggregate counts, note-identity hashes, and local file hashes are shareable artifacts.
