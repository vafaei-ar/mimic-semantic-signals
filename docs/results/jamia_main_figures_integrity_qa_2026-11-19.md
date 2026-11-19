# JAMIA main figures: verified artifact integrity and registered-data QA

Date: 2026-11-19  
Status: **Automated integrity PASS. Visual layout QA still pending.**  
Project: `vafaei-ar/mimic-semantic-signals`  
Branch: `extension-v2_1`

## Purpose

This bounded continuation verified the exact six safe aggregate figure artifacts produced by RunRelay job `T0EK5K79`. It did not regenerate figures, refit models, open patient-level data or revise frozen clinical results.

## Canonical execution and artifact lineage

| Role | Job | Task | Exact scientific repository commit | Outcome |
|---|---|---|---|---|
| Main figure rendering | `T0EK5K79` | `build_jamia_main_figures` | `a576c1ee0a6e9087e88b0417460538ccea02ae54` | Completed, exit 0, six artifacts |
| Read-only integrity QA | `RJEBN2DH` | `audit_jamia_main_figures_v1` | `15ead3fff333221de5c8dc25ee289b52bb2c4cb3` | Completed, exit 0, one JSON artifact |

The QA report was retrieved **as actual JSON text through RunRelay Reader from the declared R2 direct-text artifact**, not reconstructed from the Python script. It is `outputs/integrity/jamia_main_figures_v1_audit.json`, 2,942 bytes, SHA-256 `4b2c297746df43cb72f3081194c2e56a4b5fe96004637aa24eb0cfbfa009ea5b`. The R2 share expires on 2026-11-22 at 23:02:08 UTC.

## Verified checks

- **Six of six files verified.** All generated PDF, SVG and PNG files matched the SHA-256 checksums in the original T0 RunRelay declaration.
- **PNG structure and scale:** Figure 1 is 2,120 × 1,195 pixels. Figure 2 is 1,863 × 904 pixels.
- **SVG:** XML structure parsed, and the files retain 40 and 13 editable text elements respectively. Expected title, cohort, model-comparison, time-landmark and ΔAUROC labels were present.
- **PDF:** Both files have a valid PDF header and EOF marker. This checks basic file integrity only, not complete PDF rendering or publication compliance.
- **Registered source:** The script checked three primary outcome rows, cohort counts 11,116 / 19,395 / 19,811, event counts 279 / 314 / 214, the 12-hour landmark and horizon, and the original primary-partition points and interval endpoints:
  - Ventilation: ΔAUROC −0.00005, CI [−0.02173, +0.01910]
  - Renal replacement therapy: ΔAUROC −0.00079, CI [−0.00323, +0.00275]
  - MetaVision ICU death: ΔAUROC −0.00212, CI [−0.00802, +0.00531]
- **Overall automated integrity:** `integrity_pass = true`, `errors = []`. The JSON explicitly records `scientific_model_execution = false` and `figure_render_execution = false` for this audit.

## Explicit limitation and release disposition

The direct R2 binary ZIP could not be retrieved into the local visual-inspection environment. The audit ran on the original project-bound workstation and verified the files in place.

**Manual visual inspection remains unperformed and must not be reported as passed.** The report records `manual_visual_inspection_pass = null`. Before submission, inspect the raster or PDF rendering at the intended JAMIA figure size, including font legibility, label collisions, clipping, legends and any ambiguity in note absence.

The QA validates that the existing figures preserve expected frozen primary values and basic file structure. It does not establish that the visual design is publication ready, that the plot artist locations are free of collisions, or that the inferential estimands are scientifically correct in an independent reanalysis.

## Next production milestone

Perform actual final-size visual review and fix documented layout issues if present. After this gate, develop editable main Tables 1 and 2 from their frozen registered source and reconcile them against manuscript numbers. The figure/table architecture remains documented in `manuscript/JAMIA_FIGURE_TABLE_ARCHITECTURE_2026-11-19.md`.

This milestone changes no protocol, clinical code, model fitting or registered result. The post-T1.5 stop rule remains active. No additional job was submitted after `RJEBN2DH`.
