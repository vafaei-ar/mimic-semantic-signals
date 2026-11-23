# JAMIA working manuscript: canonical RunRelay status and document layout preflight

Date: 2026-11-23  
Status: **Automated structural preflight passed with an actionable Table 3 layout warning. Full human visual QA remains pending.**  
Repository: `vafaei-ar/mimic-semantic-signals`, branch `extension-v2_1`.

## Bounded continuation and original job lineage

The three automated continuation jobs were independently checked through canonical RunRelay Reader status and their declared safe artifacts, rather than inferred from the notification.

| Job | Named task | Execution commit | Canonical result and safe artifacts |
|---|---|---|---|
| `D408FP7G` | `assemble_jamia_integrated_word_v1` | `4392c34221cdca5b2efb5e69fcba117d6a88d13b` | Failed, exit 1, no artifacts |
| `YXBF2F9G` | `diagnose_jamia_word_assembly_v1` | `38069d47ff4f8d6102416acff721b97fd273eb10` | Completed, exit 0, one safe diagnostic JSON |
| `N58C387J` | `assemble_jamia_integrated_word_v1` | `12d61beb4c2b7c3d21db8991c80937b9f351e339` | Completed, exit 0, DOCX, PDF and QA JSON |

The first build's failure is explained by the actual diagnostic R2 artifact: `ModuleNotFoundError: No module named 'docx'` for Python 3.13.5. Installed LibreOffice was available. The corrected builder used standard-library HTML to Word conversion via LibreOffice. The successful production job retained its own exact commit and unchanged registered manuscript input.

Final production DOCX SHA-256: `ea5730e0f6fe323a39e428043bbedfbfde56a49136aad629d307184c007b023d`.  
Final production PDF SHA-256: `9d2585b4aba9678c1c514e8767877a7d3ed16d991bd4bd500857712f98a8946a`.

The actual production R2 QA JSON was directly retrieved and reports three editable native tables, 17 numbered references, both main figure legends, exact registered Table 2 values, PDF rendering, and no new model fitting.

## One new bounded QA milestone

A read-only layout-preflight script `scripts/audit_jamia_integrated_layout_v1.py` and named RunRelay task `audit_jamia_integrated_layout_v1` were committed and executed at exact project commit `84b1c7a7025f93591dbaa3f7aef826bb79e167d8`.

**RunRelay job:** `CM39PPXZ`. Canonical status **completed**, exit 0.  
**Declared artifact:** `outputs/integrity/jamia_integrated_layout_preflight.json`, 5,255 bytes, SHA-256 `69dfca7b2dd02fe71e3d2a45bb70211c6c02ed2a5465f93b42ee7f5039d813cc`.  
**Retrieval:** The JSON was actually read through RunRelay Reader from the declared R2 direct-text artifact. It was not reconstructed from code.

### Positive checks

- Both working-document file SHA-256 values matched the original successful production job.
- The DOCX ZIP and XML contained three native Word tables, with row and column shapes (11, 4), (4, 6), and (4, 8).
- Poppler PDF bounding-box extraction succeeded and reported **10 pages**, each US Letter portrait at 612 by 792 points.
- Every PDF page had text, ranging from 364 to 627 detected words.
- Every table caption was present in the rendered PDF. Table 1 was detected on page 2, and Table 2 and Table 3 captions were both detected on page 5.
- The figure legends were detected on page 10.
- **Zero words had bounding boxes outside page boundaries.**
- All registered source consistency checks in the earlier production QA remained satisfied.

### Actionable layout defect or risk

The DOCX contains **only one portrait page section**, with page size 8.5 by 11 inches. The entire ten-page rendered PDF is portrait. Table 3 has eight columns, with measured Word grid-column widths from approximately 0.657 to 1.158 inches. This means the earlier proposed landscape handling was **not implemented** by the HTML-to-Word builder.

This does not prove clipping or illegibility. The bounding-box test detects text outside the page, not small text, awkward line wrapping, overlapping words inside cells or loss of intended visual hierarchy. Nevertheless, eight cramped columns on portrait Letter are an identifiable publication-readability risk.

**Disposition:** Treat the integrated working manuscript as source-consistent but **not publication-ready**. Change Table 3 to a landscape section or redesign the table with a simpler column structure, followed by Word/PDF re-render and final-size page inspection. Do not modify numerical values during that repair.

## Pending gates and limits

The QA JSON explicitly reports `manual_visual_review: null`. A human has not inspected all ten pages at actual reading size. Zotero-linked citation fields are also pending. Figure 1 and Figure 2 are generated and structurally checked as separate artifacts but still lack final-size visual QA. The complete supplement and final scientific narrative revision are outstanding.

The automatic layout audit executed only on the existing generated DOCX/PDF and produced a small aggregate JSON. It did not access restricted patient notes, row-level data or original model predictions. No model refitting or new inferential calculation occurred. It did not regenerate or alter the Word/PDF originals.

**Next single production milestone:** Repair Table 3 orientation or simplify its layout, render the revised Word manuscript, and verify final-size page geometry. No additional job was submitted after `CM39PPXZ` in this continuation.
