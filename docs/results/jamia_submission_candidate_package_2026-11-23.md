# JAMIA author-review submission candidate: completed package

Date: 2026-11-23
Repository: `vafaei-ar/mimic-semantic-signals`
Branch: `extension-v2_1`
Status: **Source-controlled candidate package produced and automated structural checks passed. Author approval and visual/citation/ethics/statistical gates remain open.**

## Distinct scientific lineages

The primary H1-H3 preregistered populations, point estimates, 500-refit intervals, and fixed methods remain unchanged. Candidate manuscript: `manuscript/JAMIA_SUBMISSION_CANDIDATE_2026-11-23.md`. Candidate supplement: `manuscript/JAMIA_SUPPLEMENT_CANDIDATE_2026-11-23.md`. The latter adds explicitly post-registration exploratory T1.1, T1.2, T1.2b, T1.4, and T1.5 results plus the unresolved ventilation thin-comparator bootstrap warning, with no new clinical modeling.

The new main text acknowledges Peng et al. (JAMIA 2026, doi:10.1093/jamia/ocag146) as related competing work, includes brief post-registration extension results, and expands the verified bibliography to 18 entries. This is a new review candidate. It does not replace the protected original source.

## RunRelay provenance and artifacts

Initial package run `0BA10GHX` failed at commit `69d3ba87954840cc40015c20afe988d4d917e5f0` because the regenerated main DOCX target had a different basename from the generated HTML. The GitHub Actions dispatch log provided the Python traceback. No artifact was published and no clinical analysis ran.

A one-line builder basename repair was committed at `b4d96a3c41092a03e3b212e3b0c3fa97b1d8e728`. Corrected job **`C2NQ7W9H`**, task `build_jamia_submission_candidate_package_20261123`, completed with **exit 0** on the same corrected commit, machine `pshjl4vf24`. The five declared safe artifacts were shared to RunRelay R2.

- Inner complete author-review ZIP: `outputs/manuscript/jamia_submission_candidate_20261123/JAMIA_Submission_Candidate_2026-11-23.zip`, SHA-256 `da2ea1af63494b5b0e76ea540cba41abef0cfc7293b3e1adf00baf25dbbf7cdc`.
- Main DOCX SHA-256: `8b8108a79875a5be59404445d4ed064e8a20d5504cc085a1a3cc389d1b84d211`.
- Supplement DOCX SHA-256: `aeb2ba82b7776da74d2d6ba65e84c200f96f3bd8a54168bd368027d2f76b4fc7`.
- Cover letter DOCX SHA-256: `4e4fe19fef79ee33e94a46abb40804a88e810786e4e3b2837fc845de0d258afc`.
- QA JSON SHA-256: `e2ea5da9254a80530d0167cef73ca22ec67398d47557a68bbf9079fe870d1a4d`.

The **actual QA JSON** was read directly from declared RunRelay R2 storage. It reports a 13-page main PDF, 12-page supplement PDF, the three native primary Word tables, a landscape Table 3 on the main PDF, no off-page PDF words in either file, all six code-generated main-figure format assets, and 18 portable RIS reference entries. All enumerated package checks passed. No model fitting or patient-level data were used.

## Included files

The inner ZIP includes editable main and supplement DOCX, corresponding proof PDFs, editable cover letter DOCX/PDF, both registered figures as PDF, PNG and SVG, RIS for Zotero import, source Markdown, source-integrity QA reports, and `READ_FIRST_Submission_Review.txt`.

## Mandatory release gates

- Human visual inspection of all 25 manuscript/supplement PDF pages, and figures at final display size, remains pending. Geometric bounding boxes do not establish final legibility.
- Zotero Word fields are not yet linked. RIS metadata are for import and verification. They are not proof of library-synchronized citations.
- Competing interests, local ethics determination if applicable, final author details, funding and disclosure statements require author approval. Do not invent missing declarations.
- The T1.5 ventilation A TF-IDF original estimate exceeds the upper endpoint of its percentile bootstrap interval. The statistical adjudication preserves both numbers but recommends independent interpretation/sign-off before journal submission.
- Reconfirm the published Peng 2026 comparison, word count, all references, reporting checklist, and actual JAMIA portal requirements. No journal submission has been made.

**Verdict:** near-submission author-review package, not a certified submission-ready manuscript. Keep the JAMIA baseline and the post-T1.5 scientific stop rule intact.
