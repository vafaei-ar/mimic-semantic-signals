# JAMIA Table 3 landscape repair: verified production and layout checkpoint

Date: 2026-11-23
Project: `vafaei-ar/mimic-semantic-signals`
Branch: `extension-v2_1`
Status: **Rebuilt document and read-only PDF geometry passed. Final human visual review and Zotero linkage remain pending.**

## Source and bounded repair

The immutable source remains `manuscript/JAMIA_WORKING_DRAFT_2026-10-03.md`, Git blob SHA-1 `98083181df9af60540b242af5f6b2b5ecdf38f33`. No scientific results, manuscript text, patient records, modeling code or frozen analyses were changed.

The reproducible document builder received a surgical Table 3 section-layout correction in commit `1dc887bbe843ff75884083ae395caf3e67c5e237`. The rebuilt DOCX now contains portrait, landscape, and portrait sections. The eight-column Table 3 grid was widened by a factor of 1.20; registered table data remain intact.

## Canonical RunRelay production

Production job `TVQ69QH7`, task `assemble_jamia_integrated_word_v1`, ran at exact commit `1dc887bbe843ff75884083ae395caf3e67c5e237` on bound machine `pshjl4vf24`. Canonical RunRelay Reader status: **completed, exit 0**, runtime 5.938 seconds. All three declared artifacts were shared to R2. Its actual QA JSON was retrieved and reports `status: passed`, unchanged source blob, three editable Word tables (11x4, 4x6, 4x8), the exact registered primary Table 2 values, 17 numbered references, both figure legends and successful PDF rendering.

| Declared production file | SHA-256 |
|---|---|
| `outputs/manuscript/jamia_integrated_v1/JAMIA_Working_Manuscript_Integrated_v1.docx` | `11ae173b5dc4e6ace79af6db19a6d279a3393c655ae2f98c37f613248cf68552` |
| `outputs/manuscript/jamia_integrated_v1/JAMIA_Working_Manuscript_Integrated_v1.pdf` | `024803e1999bfaeeed3f34500110157a420f34f56f561074c58c46678db4ca88` |
| `outputs/manuscript/jamia_integrated_v1/JAMIA_Working_Manuscript_Integrated_v1_QA.json` | `10cb1e7baedcce2b2b9f9f6ee9a987d3c804b6c990f5051d8a91c184b9b475b1` |

## One post-repair verification milestone

A read-only, non-overwriting post-repair QA script and named RunRelay task were registered at commit `b243dfe83c484a0a787bfb86d42509ed6266d6cf`. Job `5RRAJSYV`, task `audit_jamia_integrated_layout_postrepair_v2`, completed with **exit 0** (1.989 seconds). Its declared safe R2 artifact `outputs/integrity/jamia_integrated_layout_postrepair_v2.json` was read directly, SHA-256 `1cc599c63de82b681503df5598fb20810136c32951203aba66240e7737daf269`.

The post-repair report confirms:

- DOCX and PDF SHA-256 hashes match production job `TVQ69QH7`.
- Word has three page sections: portrait (8.5 x 11 in), landscape (11 x 8.5 in), portrait (8.5 x 11 in).
- The PDF has **11 pages**, and the Table 3 caption is on **landscape page 6** (792 x 612 pt). Other pages remain portrait.
- Word retains all three native tables with expected rows/columns, and all three PDF table captions are found.
- **Zero PDF words** have bounding boxes outside page boundaries.
- Every structural preflight check passed: `structural_preflight_pass: true`.

**Residual warning:** Page 6 has only **58 detected words** because the eight-column Table 3 sits alone on the landscape page. This can be legitimate but merits final-size human inspection for whitespace, wrapping and readability. A bounding-box check does not establish that table text is comfortably legible. `manual_visual_review` remains `null`.

## Remaining publication gates and stop rule

No additional scientific experiment is warranted by these layout checks. Before submission, visually inspect all 11 rendered pages, especially Table 3 at actual reading size; verify the journal figure files and complete Zotero-linked Word citation fields. The production QA still records `zotero_field_linking: pending`, and its figures are separate journal artifacts rather than embedded.

This checkpoint closes the **bounded Table 3 layout-repair verification** only. It does not certify the whole manuscript as submission-ready. Preserve the existing JAMIA baseline on `main` and do not initiate additional RunRelay jobs from this checkpoint without a separate need.
