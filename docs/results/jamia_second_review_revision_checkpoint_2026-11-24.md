# JAMIA second-review corrections: verified author-review package

Date: November 24, 2026 (Eastern)
Repository: `vafaei-ar/mimic-semantic-signals`
Branch: `extension-v2_1`
Production commit: `5a778256d8a7e12e56a64924401e7330668552b0`
Successful RunRelay production job: `4BQ59MHN`
Status: **New near-submission author-review package, not authorized for direct journal upload**

## Substantive manuscript clarification

The main Methods already documented nonclinical fine-tuning of Open-Jev (banking support, sentiment, question answering) and Laya (agent/customer-service, invoice, security workflows), with unknown upstream training exposure and no clinician construct validation. Its Discussion now distinguishes these off-the-shelf typed-decision instruments from clinical semantic compression in general. Alternative DiffusionGemma prompted scores and post-registration supervised TF-IDF/BGE text models did not show consistent gains over the rich comparator. These comparisons are neither independent cohorts nor proof that a clinically trained and validated semantic model could not improve a prediction task. The Limitations and Conclusion now explicitly respect this scope.

JAMIA *Research and Applications* specifies **Objective**, singular, in the structured abstract (https://academic.oup.com/jamia/pages/General_Instructions). The reviewer-suggested plural heading was therefore **not** adopted.

## Supplement cleanup

- Replaced S1-S5 method headings and S9-S14 note headings with **Supplementary Methods 1-5** and **Supplementary Notes 1-6**. Table S1-S12 numbering is unchanged. Removed H/T workflow codes from narrative table titles while preserving a compact T-code mapping in the provenance note.
- Corrected a nonexistent main-text reference to Table S13: it now points to Table S12 and Supplementary Note 5.
- Condensed the exploratory ventilation level-A TF-IDF inconsistency to facts: observed ΔAUROC +0.022888, percentile interval [−0.012831, +0.020596], bootstrap mean +0.003558, differing predefined inner-fold seeds, and no established positive increment. Did not recenter or reinterpret the result without additional analysis.

## Word metadata: truthful properties, no editing-history simulation

Added a source-controlled `manuscript/word_core_properties.py` postprocessor. The manuscript DOCX title and creator come from its actual title page; supplement and cover have accurate document titles and the stated corresponding author's name. No revision counts, editing times, application identity, history fields, or timestamps were falsified to disguise automated document production.

## RunRelay results and artifact QA

An initial execution `K3PVDJ8E` at source commit `6ec218a3c2fb560b056cd71a6a3689ef37e69415` failed (exit 1) because the new title-page parser used an incorrectly escaped regular expression. Its R2 artifacts included older files and **must not** be treated as the new package. The parser was corrected using literal Markdown title-page labels, at commit `5a778256d8a7e12e56a64924401e7330668552b0`.

Canonical Reader job `4BQ59MHN`: **completed, exit 0**, 17.803 seconds, machine `pshjl4vf24`, five safe declared artifacts shared. The actual R2 package QA JSON was retrieved and parsed. All checks true, including new `author_and_title_metadata`, 18 bibliographic records with 15 journal RIS fields, landscape Table 3, 6 generated figure assets, and no out-of-page words. The Word supplement builder enforced 12 native table structures. The PDFs contain 20 main pages and 12 supplement pages; Table 3 is on landscape page 10.

| Declared safe file | SHA-256 |
|---|---|
| Main manuscript DOCX | `f5abf45f1a15d34a09c82f4892f9008d814fbbbf4d49f1f2e12d2e75d4cac276` |
| Supplement DOCX | `3483f3f43139ffc097ea3c8228c9da12abfb99db9f1b844b87f35d7efab6be8d` |
| Cover letter DOCX | `3ae4cbba80fc069ac608e4f4e550f2be6e823fb00c9348c796ae795fdf285a7a` |
| Complete author-review inner ZIP | `d4328c4aa933a9daa268d977c11129ac3c0046a00707ab0bdc4df65346c6e43c` |
| Declared package QA JSON | `e738845ea12818b9645c21dc1bda202eb4b28c9e22df8c072ccc602853ba9260` |

RunRelay outer R2 bundle SHA-256: `0868e14f7705bfebd9e2d30307e1420dd42964f04b7a437e585c3c6f64346c39`; expires November 28, 2026 04:03 UTC.

## Release gates / stop rule

The author must provide a factual competing-interest statement and confirm local ethics determination, if applicable. The main DOCX still has plain-text citations, not Zotero-linked Word fields. Independent statistical sign-off is advisable if the exploratory level-A ventilation interval remains in the published supplement. Visual inspection of all pages remains pending in this environment even though an outside reviewer reported a clean Figure 2. The author-review ZIP contains internal source and QA files and must not be uploaded as-is. Only approved manuscript, supplement, cover and separate figures should go to the journal portal.

No new clinical modeling or restricted patient-data handling occurred. No further RunRelay jobs are authorized by this checkpoint.

## Follow-up: failed-job artifact consistency guard

On November 24, 2026 (Eastern), the repeat terminal notification for `K3PVDJ8E` and `4BQ59MHN` was independently checked against canonical RunRelay Reader status, both declared R2 artifact lists, and the actual JSON text of **both** declared package QA artifacts. No job was retried, submitted or run as part of this follow-up.

**Failed-job defect:** The `K3PVDJ8E` canonical lifecycle is `failed`, exit 1, at project commit `6ec218a3c2fb560b056cd71a6a3689ef37e69415`. Its R2 manuscript DOCX SHA-256 is `f8672a1748db810ad5d2fb440aa2e116e5498072501abd277293a56b51af3118`, but the QA JSON stored in the **same failed R2 bundle** reports a different main manuscript DOCX SHA-256, `c8741969dee8c5f7129a745c20abe20fdd7e0f58a60fd644b325513e10b3ed19`. This is an exact internal mismatch: the QA report is stale. The failed job's purported `all checks passed` pertains to an earlier package, not that failure's output. Its declared inner ZIP (`07a969dd971b69d38de6e03af6a1e5a9ccd01fd77e0be11e335215e090fe782a`) and supplement DOCX (`ab2d74361e726cc06045bdd95d7734691a4c5613de270e3d5720f5d5bba4a7b1`) also match prior-generation hashes. **Never distribute or accept `K3PVDJ8E` artifacts as the final candidate**, regardless of the presence of an R2 bundle.

**Successful-job consistency:** Canonical `4BQ59MHN` is `completed`, exit 0, at project commit `5a778256d8a7e12e56a64924401e7330668552b0`, with all five declared safe artifacts shared. The R2 QA report's three DOCX hashes each match the corresponding canonical declared artifact SHA-256: main `f5abf45f1a15d34a09c82f4892f9008d814fbbbf4d49f1f2e12d2e75d4cac276`, supplement `3483f3f43139ffc097ea3c8228c9da12abfb99db9f1b844b87f35d7efab6be8d`, and cover `3ae4cbba80fc069ac608e4f4e550f2be6e823fb00c9348c796ae795fdf285a7a`. All ten recorded automated package checks are true. This establishes a coherent successful package lineage, **not** full visual review, Zotero Word-field connectivity, statistical clearance, or completion of author ethics/competing-interest declarations.

**Disposition:** The sole valid latest author-review package remains the one produced by `4BQ59MHN`. Existing GitHub source and scientific results were not changed in this follow-up. This artifact-lineage reconciliation is the single completed milestone; stop without another RunRelay job.
