# JAMIA Table 2: registered primary Open-Jev results

Date: 2026-11-19  
Status: **Native, editable Word table created and one-page render visually inspected.** The registered H1-H3 results remain unchanged. The current Word file is a conversation attachment, not a GitHub binary.

## Table 2. Registered primary Open-Jev results

| Outcome | Comparator AUROC | Augmented AUROC | ΔAUROC | 95% full-refit percentile CI | ΔAUPRC |
|---|---:|---:|---:|---|---:|
| Invasive ventilation | 0.72468 | 0.72463 | −0.00005 | [−0.02173, +0.01910] | +0.00387 |
| Renal replacement therapy | 0.97394 | 0.97315 | −0.00079 | [−0.00323, +0.00275] | −0.00048 |
| ICU death (MetaVision) | 0.93338 | 0.93126 | −0.00212 | [−0.00802, +0.00531] | +0.00087 |

**Notes.** AUROC is the area under the receiver operating characteristic curve. AUPRC is the area under the precision-recall curve. The augmented models add eight predefined Open-Jev semantic scores to the registered rich structured comparator. Δ is augmented minus comparator. The displayed point estimates come from the registered primary patient-grouped partition. Each two-sided 95% percentile interval comes from 500 valid source-patient-cluster bootstrap refits. ΔAUPRC is a registered secondary descriptive metric and has no displayed interval. Outcomes are evaluated at a 12-hour ICU landmark with a 12-hour subsequent prediction window.

**Limitations.** All three ΔAUROC intervals include zero. They do not establish equivalence or demonstrate the absence of narrative information.

## Source and output integrity

Source 1: `docs/results/v2_1_primary_openjev_results.md` at GitHub commit `fcfa26fa7adc9cc7182926e7895aed50a4b8ffb0`, blob SHA `7127316173ed7ffdfb44ee4204596c8b907eb6e5`. The original AUROC values, differences and CI endpoints for all three registered H1-H3 rows were checked independently against this file. The ΔAUPRC values were checked against its separate secondary-results paragraph rather than incorrectly assumed to be included in the primary row table.

Source 2: `manuscript/JAMIA_WORKING_DRAFT_2026-10-03.md`, blob SHA `eb25181d251effeb608c160856af111054da912c`, contains the earlier manuscript Table 2. The new table is a standalone Word file and does not modify the original manuscript.

Generated file: `JAMIA_Table_2_Registered_Primary_Results.docx`. SHA-256 `7934a8f0914d0ca12b733b7c3c5884a37b7851ab08ea7b82e49b32d64b0617a8`. Word table structure: 4 rows including header, 6 columns, with fully editable text. The DOCX rendered to one letter-size portrait PNG page, inspected for wrapping, clipping, typography and cell spacing.

## RunRelay continuation checkpoint

The automated notification for `RJEBN2DH` was verified against canonical status and the declared safe R2 artifact. Canonical status is **completed, exit 0** at exact execution commit `15ead3fff333221de5c8dc25ee289b52bb2c4cb3`. The retrieved aggregate QA report has SHA-256 `4b2c297746df43cb72f3081194c2e56a4b5fe96004637aa24eb0cfbfa009ea5b`, `integrity_pass: true`, six verified figure binaries and no errors.

Figure file integrity is resolved. Actual final-size visual QA of Figure 1 and Figure 2 remains open because the binary ZIP was not accessible in the inspection environment. No new RunRelay job or clinical model run was submitted during this continuation.

**Next small production milestone:** Generate editable JAMIA Table 1 from the frozen cohort characteristics report. Preserve the post-T1.5 no-new-exploratory-analysis rule.
