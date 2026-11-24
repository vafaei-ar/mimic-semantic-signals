# JAMIA submission release gate after job AQZCQ7PE

Date: 2026-11-23 (Eastern)
Project: `vafaei-ar/mimic-semantic-signals`
Branch: `extension-v2_1`
Scientific/package production commit: `6ec671f2bdbb0f35dda64ad1396b15de5ea5b2e8`
Canonical RunRelay job: `AQZCQ7PE`
Disposition: **AUTHOR REVIEW ONLY; DO NOT UPLOAD TO JOURNAL YET**

## One bounded continuation milestone: reconcile the actual R2 QA and source-only Figure 2 checks

RunRelay Reader independently confirmed `AQZCQ7PE` terminal status `completed`, exit code `0`, task `build_jamia_submission_candidate_package_20261123`, project `mimic-semantic-signals`, machine `pshjl4vf24`, 18.798 s execution, and five declared R2 artifacts. The declared safe QA file `outputs/manuscript/jamia_submission_candidate_20261123/JAMIA_Submission_Candidate_2026-11-23_Package_QA.json` was retrieved through the Reader and parsed, rather than inferred from the notification.

Automated checks in the QA report: source manuscript and supplement present; 18 reference records; 15 journal entries with journal fields in RIS; landscape Table 3 in main PDF; valid supplement PDF; zero out-of-page word bounding boxes in either PDF; six generated figure assets. Main PDF: **19 pages**; supplement PDF: **12 pages**. Table 3 caption occurs on landscape page **10**. All recorded automated package checks were true.

| Declared output | SHA-256 |
|---|---|
| `JAMIA_Submission_Candidate_2026-11-23.docx` | `c8741969dee8c5f7129a745c20abe20fdd7e0f58a60fd644b325513e10b3ed19` |
| `JAMIA_Supplement_Candidate_2026-11-23.docx` | `ab2d74361e726cc06045bdd95d7734691a4c5613de270e3d5720f5d5bba4a7b1` |
| `Cover_Letter_2026-11-23.docx` | `e043fef4b28e11afe0f2cbbabcb54f69ce222ffe297a21549e9058cb4e3cb594` |
| `JAMIA_Submission_Candidate_2026-11-23.zip` (inner author-review ZIP) | `07a969dd971b69d38de6e03af6a1e5a9ccd01fd77e0be11e335215e090fe782a` |
| `JAMIA_Submission_Candidate_2026-11-23_Package_QA.json` | `8b78a8b6ab4185fa1a191d0b43131e5b9cf24eae3361558266197443fb5fcef2` |

Inner-package Figure 2 PNG SHA-256 reported by QA: `387778e7d51bca57e4ac7cebb57bd04de4cd529011f71bfb5f27b223c9178c4d`. This is a file-integrity identifier, **not** a visual approval.

### Figure 2 status

At the checked `extension-v2_1` branch, the `figure_2` implementation in `manuscript/make_jamia_main_figures.py` no longer contains the redundant title, the lone panel label `a`, or the former bottom explanatory footnote. Its axis label and output save call remain intact. The manuscript builder also contains an explicit `w:line="480"` double-spacing postprocessing step. These are **code-level checks only**.

An attempt to download the actual R2 ZIP to this inspection environment was blocked by transport/DNS restrictions. No image pixels or rendered PDF pages were directly inspected in this continuation. **Figure 2 visual QA remains PENDING**, including typography, axis label spacing and legend fit. Do not transform removal of the offending source strings or PDF bounding-box QA into a claim of human visual sign-off. The canonical R2 artifacts remain available through RunRelay Reader.

### Upload inventory and exclusion rule

The files expected to proceed to the journal **only after author approval** are the finalized editable main manuscript DOCX, supplement DOCX (or portal-prescribed supplemental format), final cover letter, and Figures 1 and 2 in accepted journal formats. The complete inner ZIP is for author review, not a journal upload packet. **Do not upload** `*_QA.json`, `READ_FIRST_Submission_Review.txt`, `sources/*.md`, `*.ris` unless specifically requested, internal build scripts, or internal provenance notes.

### Hard blockers still open

1. Full visual inspection of the actual main and supplemental PDFs (19 + 12 pages), prioritizing main Table 3 landscape page 10 and Figure 2 at final size.
2. Word citations and bibliography are plain text. Zotero import metadata have improved, but there is no verified functioning Zotero Word-field linkage.
3. The manuscript source still contains an author-only **competing-interests placeholder** and an **ethics determination bracketed note**; these require the author's factual declarations.
4. Independent statistical interpretation of the exploratory T1.5 ventilation TF-IDF A-level bootstrap percentile interval versus the observed point estimate.
5. Final author approval of submission wording, editor/title page and any journal portal-specific requirements.

The existing post-T1.5 scientific stop rule remains in force. No outcome model, restricted clinical file, regression/bootstrap computation, deployment or journal submission was initiated from this continuation.

## Action / stop

**Milestone completed:** an exact-commit verified release-gate checkpoint with status distinctions and file inventory. No duplicate RunRelay job, retry or new scientific analysis was submitted. Preserve the author-review package and obtain actual visual inspection and author declarations before release.
