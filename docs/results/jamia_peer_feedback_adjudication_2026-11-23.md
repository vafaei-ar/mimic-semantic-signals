# JAMIA external-review feedback: source correction and bounded rebuild

Date: 2026-11-23, evening Eastern
Status: **Corrected author-review package produced; visual, Zotero and author clearance still pending.**
Project branch: `extension-v2_1`.
Production commit: `6ec671f2bdbb0f35dda64ad1396b15de5ea5b2e8`.
Canonical RunRelay job: **`AQZCQ7PE`, completed, exit 0**, local document and figure work only.

## Scientific corrections made

1. The registered common-logistic TF-IDF effects remain descriptive point differences without complete-refit uncertainty intervals. Abstract, Results, Discussion, Conclusion and cover letter no longer imply reliable lexical improvement from them. Separately registered exploratory full-refit TF-IDF comparisons remain distinguished.
2. Main Methods now explicitly state that ventilation and RRT risk populations exclude documented intervention at or before the 12-hour landmark. This matches the `build_outcome` risk-set implementation in `src/104_build_corrected_landmark12_v2_1_cohorts.py`, lines 505-565, with MetaVision source restriction.
3. Main Results and Discussion report that note-available RRT semantic-only AUROCs ranged from 0.448 to 0.491 across the five overlapping grouped partitions. No post hoc reversal or unsupported inference of a reliable inverse association was added.
4. Calibration slopes below one are acknowledged despite high structured AUROCs (ventilation 0.615, RRT 0.713, ICU death 0.762). The separate contribution of the death-specific code-status predictor group was not estimated and is not invented.
5. The model-card training context is identified as nonclinical: Open-Jev reports public banking, sentiment and BoolQ training, and Laya reports business/agent decision-workflow data. Neither card establishes clinician validation or definitively excludes all MIMIC data from upstream encoder pretraining.
6. MIMIC-III is justified for prospectively eligible bedside notes because the released MIMIC-IV-Note module provides discharge summaries and radiology reports rather than the same bedside note corpus.
7. The external Chinese Zigong cohort is introduced, while incomplete transport remains explicitly disclosed. The ventilation primary confidence interval is not described as equivalence. The post-registration T1.5 ventilation point/percentile mismatch remains transparently reported in the supplement.
8. Removed stray punctuation spaces and uncertain suffixes in AI model-disclosure names. The required AI-use disclosure remains.
9. Removed internal OSF byte/hash audit discussion from the reader-facing supplement while preserving its source record in repository documentation.

## Editorial corrections and verified exceptions

- JAMIA **Research and Applications** currently requires the abstract heading **Objective** (singular), not `Objectives`. The source retains `Objective`. Official journal instructions: https://academic.oup.com/jamia/pages/General_Instructions
- For November 2026, the cover letter addresses **Suzanne R. Bakken, PhD, RN**, Editor-in-Chief. Thomas Kannampallil takes office January 1, 2027 (AMIA June 24, 2026 announcement).
- The revised Word builder omits repository preface labels, updates the manuscript title metadata, and inserts explicit 480/240 = 2.0 paragraph line spacing outside tables while preserving landscape Table 3 and compact table text.
- Main Figure 2 source removes the overlapping footnote, redundant in-figure title and incorrect single-panel `a` label. Figure graphics are still generated solely by repository code from previously verified aggregate JSON. This edit has not received independent visual inspection in this ChatGPT continuation.
- Recalculated source-based body word count, excluding tables/title/abstract/references/figure legends: **3,669**. Abstract body: **242 words** under the same tokenizer. Word-processor counts can differ marginally and require final author confirmation.
- The reviewer's recommendation to omit AI authorship/generation metadata would be inappropriate if it misrepresented provenance. Corrections to genuine titles and scientifically irrelevant metadata were made without fabricating an edit history or concealing the use of automation.

## Reference integrity

Source file `manuscript/JAMIA_REFERENCES_PUBMED_VERIFIED_2026-11-23.json` contains 15 PubMed-verified journal items and 3 identified model-card records. Package RIS now writes authors, journal, DOI, bibliographic fields, and provenance URLs. The package QA verifies 18 records and 15 journal fields. Zotero library import and Word citation fields remain **unverified and pending**. Do not claim the Word manuscript contains Zotero-linked citations.

## Verified production and artifact hashes

RunRelay job `AQZCQ7PE` used exact commit `6ec671f2bdbb0f35dda64ad1396b15de5ea5b2e8` on bound machine `pshjl4vf24`. Canonical Reader: **completed, exit 0, 18.798 seconds**, five declared safe artifacts shared.

| Artifact | SHA-256 |
|---|---|
| Main DOCX | `c8741969dee8c5f7129a745c20abe20fdd7e0f58a60fd644b325513e10b3ed19` |
| Supplement DOCX | `ab2d74361e726cc06045bdd95d7734691a4c5613de270e3d5720f5d5bba4a7b1` |
| Cover DOCX | `e043fef4b28e11afe0f2cbbabcb54f69ce222ffe297a21549e9058cb4e3cb594` |
| Complete inner ZIP | `07a969dd971b69d38de6e03af6a1e5a9ccd01fd77e0be11e335215e090fe782a` |
| Package QA JSON | `8b78a8b6ab4185fa1a191d0b43131e5b9cf24eae3361558266197443fb5fcef2` |

I read the actual declared R2 package QA artifact. It confirms 19 main PDF pages, 12 supplement PDF pages, landscape Table 3 on main page 10, no text boxes outside page boundaries, two figures in PDF/SVG/PNG, and the 15-journal RIS metadata check. This is an automated geometry/integrity pass, **not** full visual QA.

## Remaining author/submission gates

1. Final-size human visual examination of all 31 manuscript and supplement PDF pages plus figures. Do not infer legibility from bounding boxes.
2. Zotero item validation and proper citation/bibliography fields in the editable Word manuscript, with no fake citations or lost attribution.
3. Author-supplied conflict-of-interest declaration, local ethics determination if applicable, and confirmation of funding/affiliation/contact details. Do not fill in unknown declarations.
4. Independent statistical interpretation of exploratory T1.5 ventilation A point and percentile interval if those estimates remain in submission-facing supplement.
5. Confirm journal portal requirements, current editor at submission date, and final submission order. Do not upload internal QA, README, or Markdown source files.
6. No external validation or clinician construct validation is claimed. Do not initiate new outcome analyses under the existing post-T1.5 scientific stop rule.

**Verdict:** improved author-review candidate; submission is not yet cleared.
