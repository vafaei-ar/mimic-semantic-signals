# JAMIA integrated Word manuscript: reproducible assembly checkpoint

Date: 2026-11-23  
Status: **Editable Word manuscript built and source/numerical structural QA passed. Human visual and Zotero citation QA remain open.**  
Project: `vafaei-ar/mimic-semantic-signals`, branch `extension-v2_1`.  
Execution commit: `12d61beb4c2b7c3d21db8991c80937b9f351e339`.

## Scope of this milestone

This milestone converted the **entire current GitHub working manuscript** to one editable Word DOCX. It did not rewrite Methods or Results or conduct clinical reanalysis. Its source is `manuscript/JAMIA_WORKING_DRAFT_2026-10-03.md`, immutable Git blob SHA-1 `98083181df9af60540b242af5f6b2b5ecdf38f33`.

The conversion starts at the manuscript's Title page and intentionally omits only the internal project metadata preceding that section. The remainder, including abstract, complete main text, three editable tables, statements, all 17 numbered references, and both current figure legends, is retained from the GitHub source. The figures themselves remain separate journal files rather than being embedded.

## Execution and diagnosed implementation issue

Initial assembly job `D408FP7G` at commit `4392c34221cdca5b2efb5e69fcba117d6a88d13b` failed, exit 1, and produced no artifacts. Canonical Reader status was checked. A diagnostic RunRelay job `YXBF2F9G` completed at commit `38069d47ff4f8d6102416acff721b97fd273eb10`. Its R2-read JSON established that the workstation's configured Python 3.13 interpreter lacked `python-docx` (`ModuleNotFoundError: No module named 'docx'`). LibreOffice was already installed at `/usr/bin/libreoffice`.

We corrected only the document builder, `manuscript/build_jamia_integrated_docx.py`, to use Python standard-library HTML assembly and LibreOffice conversion. No package installation, changes to scientific code, registered analysis or patient data occurred.

Final production RunRelay job **`N58C387J`**, named task `assemble_jamia_integrated_word_v1`, ran at exact commit `12d61beb4c2b7c3d21db8991c80937b9f351e339`. Canonical status: **completed**, exit 0, 7.89 seconds. It published all three declared safe artifacts.

## Delivered production artifacts

| Artifact | SHA-256 | Bytes |
|---|---|---:|
| `outputs/manuscript/jamia_integrated_v1/JAMIA_Working_Manuscript_Integrated_v1.docx` | `ea5730e0f6fe323a39e428043bbedfbfde56a49136aad629d307184c007b023d` | 20,827 |
| `outputs/manuscript/jamia_integrated_v1/JAMIA_Working_Manuscript_Integrated_v1.pdf` | `9d2585b4aba9678c1c514e8767877a7d3ed16d991bd4bd500857712f98a8946a` | 87,616 |
| `outputs/manuscript/jamia_integrated_v1/JAMIA_Working_Manuscript_Integrated_v1_QA.json` | `b67447b0645427ad4a1417ff16b7a8b2e7a914d535e57d2f2249b309034f8002` | 983 |

The final RunRelay bundle share expiry is **2026-11-26 05:58:45 UTC**. Do not commit its private temporary download URL to the public project repository.

## Verified QA from directly retrieved R2 JSON

- `status: passed`, and the PDF was rendered through the existing LibreOffice installation.
- **Three native editable Word tables** with row counts `[11, 4, 4]` and column counts `[4, 6, 8]`.
- Every cell of the registered primary **Table 2** matches the frozen five-decimal source values.
- All **17 originally numbered bibliography entries** remain in the Word document.
- Both current main-figure legend headings are present.
- Source Git blob SHA-1 and DOCX SHA-256 are recorded and cross-checked.
- No patient-level data, clinical notes, model refits or new outcome analyses were used.

The QA result was actually read from the declared `JAMIA_Working_Manuscript_Integrated_v1_QA.json` R2 direct-text artifact by the RunRelay Reader. It was not inferred from script source alone.

## Explicit publication release gates

**Visual review is pending.** The LibreOffice-produced PDF exists and passed creation checks, but the temporary R2 binary ZIP could not be downloaded into the chat's document-rendering container, and no human inspection of each rendered page was completed. The QA JSON records `manual_visual_qa: null`. Do not call the Word file submission ready based only on structural QA. Inspect page breaks, long tables, cell text legibility, heading flow, and the figure legend pages.

**Zotero integration is pending.** Source citations remain numbered manuscript text, not connected Zotero Word citation fields. Preserve the original reference numbering and perform reference verification, portable RIS export, Zotero field insertion and a further DOCX render in a separate citation milestone. Do not claim live Zotero synchronization.

**Figure placement is pending.** Both figures are generated separately but have not been embedded in this Word file. The journal submission will require appropriate final-size visual QA, alt-text consistency, and separate figure files.

**Scientific readiness is conditional.** The existing manuscript is a working draft and predates the final scientific novelty and T1.5 statistical adjudication reports. It still requires a focused scientific narrative pass and supplementary synthesis. Do not promote exploratory results to registered findings.

## Next milestone

Retrieve or otherwise inspect the actual Word/PDF pages at final size and complete visual QA. Then integrate the manuscript's Zotero citation fields, revise the abstract and Discussion against the evidence/novelty ledger, and prepare the full supplement.

No further RunRelay jobs were submitted after `N58C387J`. The registered post-T1.5 stop rule remains in force.
