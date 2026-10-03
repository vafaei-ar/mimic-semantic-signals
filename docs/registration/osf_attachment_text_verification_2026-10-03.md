# OSF attachment scientific-text verification

Date: 2026-10-03  
Registration: OSF `ahxn9`, DOI `10.17605/OSF.IO/AHXN9`  
Cited registration commit: `873897e6c934cea3d558b6518ac1e399f9f75387`

## Purpose

The frozen OSF-hosted SAP and technical-appendix PDFs are not byte-identical to the earlier locally packaged PDFs whose hashes were cited during registration preparation. That byte-level discrepancy was already recorded in `docs/registration/osf_attachment_verification_2026-09-28.md`.

This check addresses the remaining scientific-content question by comparing text extracted from the authoritative frozen OSF PDF copies with the exact Markdown source files at the cited registration commit.

## Files

Authoritative frozen OSF hashes previously verified:

- `OSF_v2_1_SAP.pdf`: `cf770e9cfe821ecc5250587fc29d6be404ffe3ecbf5324a0390e4061e25f4db4`
- `OSF_v2_1_Technical_Appendix.pdf`: `ebfa97ca32ae0c653bb075457acf7c3ea95eebe69ec1b5af3f6313de07aad6dd`
- `v2_1_registration_manifest.json`: `22ac9f815309d81ebf03d279087848e33f8c0a16b563efe8af114a196194fc7d`

Exact registered source files:

- `docs/postreview_confirmatory_sap_v2_1_draft.md` at commit `873897e6c934cea3d558b6518ac1e399f9f75387`
- `docs/postreview_confirmatory_sap_technical_appendix_v2_1_draft.md` at the same commit

## Comparison method

The OSF-hosted PDFs were rendered successfully as a visual sanity check before text comparison.

For the scientific-text comparison, PDF-extracted text and the exact registered Markdown source were normalized only to remove representation artifacts that cannot encode scientific wording:

- PDF page-parser labels;
- soft/control hyphenation characters;
- line-wrap hyphenation;
- Markdown/PDF compound-word hyphen differences;
- case.

The comparison then used the ordered alphabetic word-token sequence. Numbers and punctuation were not used for this specific identity test because page numbers and document-formatting punctuation differ across PDF serialization. Numerical content remains independently frozen in the exact source files and registration manifest.

## Result

| Attachment | Registered-source word tokens | OSF-PDF word tokens | Ordered token sequence |
|---|---:|---:|---|
| SAP | 1,291 | 1,291 | Exact match |
| Technical appendix | 1,832 | 1,832 | Exact match |

After the defined formatting normalization, there were **zero word additions, deletions, substitutions, or reorderings** in either attachment.

## Interpretation

The two OSF PDFs differ byte-for-byte from the earlier local package PDFs, but their scientific word sequence is identical to the exact source text at the cited registration commit.

The byte mismatch should remain in the provenance record because PDF serialization changed. It should not be described as a scientific-content change or registration corruption.

This verification is a text-content check, not a claim of byte, punctuation, font, layout, or PDF-metadata identity.
