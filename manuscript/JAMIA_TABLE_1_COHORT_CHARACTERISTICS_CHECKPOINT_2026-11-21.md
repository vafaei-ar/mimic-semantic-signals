# JAMIA Table 1: frozen MetaVision confirmatory cohort characteristics

Date: 2026-11-21  
Status: **Editable Word table generated, rendered and visually reviewed.** Registered cohort results remain unchanged. The Word file is attached to the ChatGPT conversation, not committed to GitHub.

## Table 1. Frozen MetaVision confirmatory cohort characteristics

| Characteristic | Invasive ventilation | RRT | ICU death |
|---|---:|---:|---:|
| Stays, n | 11,116 | 19,395 | 19,811 |
| Cases, n (%) | 279 (2.5) | 314 (1.6) | 214 (1.1) |
| Age, years, median [IQR] | 65.9 [53.3-79.0] | 66.1 [53.9-78.1] | 66.0 [53.9-78.1] |
| Male sex, n (%) | 6,003 (54.0) | 10,926 (56.3) | 11,160 (56.3) |
| Mean arterial pressure, mmHg, median [IQR] | 75 [66-86] | 75 [66-85] | 75 [66-85] |
| Lactate, mmol/L, median [IQR] | 1.6 [1.2-2.2] | 1.7 [1.2-2.4] | 1.7 [1.2-2.4] |
| Creatinine, mg/dL, median [IQR] | 1.0 [0.7-1.6] | 1.0 [0.7-1.4] | 1.0 [0.7-1.5] |
| ICU length of stay, days, median [IQR] | 2.04 [1.41-3.31] | 2.31 [1.52-4.31] | 2.31 [1.51-4.32] |
| Eligible note available, n (%) | 4,499 (40.5) | 7,709 (39.7) | 7,889 (39.8) |
| Eligible note among cases, n/N (%) | 135/279 (48.4) | 143/314 (45.5) | 83/214 (38.8) |
| Eligible note among controls, n/N (%) | 4,364/10,837 (40.3) | 7,566/19,081 (39.7) | 7,806/19,597 (39.8) |

**Notes.** IQR is the interquartile range. The three outcomes use separate frozen MetaVision confirmatory cohorts. Continuous summaries use available measurements without imputation. Nonmissing counts for mean arterial pressure were 10,910, 19,159, and 19,567, for lactate 6,097, 13,458, and 13,790, and for creatinine 10,913, 19,151, and 19,563 (ventilation, RRT, and ICU death respectively). ICU length of stay is descriptive and was not used as a predictor.

## Source and correctness checks

- Canonical source: `docs/results/v2_1_submission_characteristics_results.md` at repository commit `21f9f745ab8c52a18f40cdba9a6da9f5c532dcf9` and source blob `5dbea1e773fc57907e56cd564655cb8f292b5242`.
- Cross-reference: `manuscript/JAMIA_WORKING_DRAFT_2026-10-03.md`, blob `eb25181d251effeb608c160856af111054da912c`, Table 1.
- The Word table reproduces every source cell. Eleven characteristic rows appear beneath four column headers.
- Programmatic checks confirmed cohort totals 11,116, 19,395, and 19,811, event counts, eligible note counts, case/control denominator partitioning, note-availability numerators, and one-decimal percentages.
- The Word file uses native editable table cells, no embedded table image, and US Letter portrait page size.
- Rendering produced a single page. Visual inspection of that rendered page found no clipped or overlapping cells, and the footnote remained readable.

## Generated artifact and provenance

- **DOCX:** `JAMIA_Table_1_Cohort_Characteristics.docx` (delivered through the conversation file surface).
- **DOCX SHA-256:** `4cac8bee1251e12c8bd6db8a4c368057ec3cc9cf509f66d8d23040f4661f2771`.
- **Local generator:** `create_jamia_table1.py` generated a Word table from the exact frozen public aggregate cells. No raw data, patient predictions, note text, model fitting, or new inference was involved.
- This checkpoint preserves the source values and artifact hash. It is not a replacement for the source aggregate record or its original RunRelay artifact.

## Remaining publication work

JAMIA Table 2 has been prepared separately in `manuscript/JAMIA_TABLE_2_REGISTERED_RESULTS_CHECKPOINT_2026-11-19.md`. Table 1 and Table 2 still need integration into the complete submission manuscript, together with captions and cross-references. The actual final-size visual inspection of generated Figures 1 and 2 remains a separate open gate, even though their file integrity checks passed. No new RunRelay job was submitted in this continuation. Preserve the post-T1.5 scientific stop rule.
