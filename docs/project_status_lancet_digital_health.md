# Project status and Lancet Digital Health roadmap — compatibility pointer

Updated: 2026-09-24

> **This path is retained for backward compatibility with earlier commits and links.**
>
> The current status report is now:
>
> - `docs/02_CURRENT_SCIENTIFIC_STATUS.md`
>
> The ordered analysis provenance is:
>
> - `docs/03_V2_ANALYSIS_LINEAGE.md`
>
> The v1 integrity/provenance summary is:
>
> - `docs/04_V1_PROVENANCE_AND_HOLD.md`

## Current state in brief

The v1 manuscript-facing results are under an integrity hold after a code review and aggregate audit confirmed multiple cohort/implementation issues.

The primary manuscript lineage has entered a post-review **v2.1 correction gate**:

- v2 source-compatible cohort and note-selection corrections remain valid;
- adult/NICU eligibility must be added;
- ETT/tracheostomy-coded verbal GCS must be treated as missing rather than numeric 1;
- exact CV split files/hashes and corrected calibration terminology are being added;
- the pre-v2.1 structured evaluation job `E8R7Q5M3` must not be promoted as the manuscript-facing result;
- corrected semantic/TF-IDF analysis remains locked;
- clinician construct validation is still required;
- affected eICU/Zigong external analyses still require corrected reruns.

See `docs/06_POSTREVIEW_V2_1_CORRECTIONS.md`.

Do not use this compatibility file as the detailed scientific status. Read `docs/02_CURRENT_SCIENTIFIC_STATUS.md`.
