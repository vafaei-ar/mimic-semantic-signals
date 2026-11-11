# Publication sequence and production plan

Decision date: 2026-11-11  
Status: **Author-approved sequential journal targeting, not submitted**  
Repository branch: `extension-v2_1`. The registered scientific execution remains frozen at `e5772f7a1a40b2368465e1b95e24a04abc98cc2a`. The JAMIA-ready primary paper remains distinct from post-registration exploratory extension material.

## Submission order

1. **JAMIA, Research and Applications**. Prepare a complete paper and independently reviewed supplement. First submission only after novelty, reporting, source verification, statistical framing, and author approval.
2. **JAMIA Open, Research and Applications**. Use only if JAMIA formally declines or the manuscript is otherwise no longer under consideration there. Incorporate decision-letter feedback, adapt the manuscript and supporting files, and add the required lay summary. Do not assume an automatic transfer.
3. **PLOS Digital Health, Research Article**. Use only after the second journal is no longer considering the paper. Rework the article for its broader readership and submission structure. Assess the PLOS data-availability policy and the restricted-access MIMIC source-data terms before attempting this submission.

**No simultaneous submission.** An editorial transfer, if offered, requires a deliberate author decision. A desk rejection does not itself invalidate the scientific findings. Do not claim any manuscript was submitted without the author's actual approval and completed submission confirmation.

## Current journal requirements verified November 11, 2026

| Journal | Target article type | Manuscript and abstract | Tables and figures | Additional requirements |
|---|---|---|---|---|
| JAMIA | Research and Applications | Main text up to 4,000 words, structured abstract up to 250 words | Up to 4 tables and 6 figures | Structured sections: Objective, Materials and Methods, Results, Discussion and Conclusion. Include Background and Significance. Provide figure alt text and a reproducible reporting package |
| JAMIA Open | Research and Applications | Main text up to 4,000 words, structured abstract up to 250 words | Up to 4 tables and 6 figures | Word manuscript, separate figures, up to 200-word lay summary at revision, funding and competing-interest declarations, code availability |
| PLOS Digital Health | Research Article | No main-text word limit, abstract up to 300 words | No fixed limits | 150–200-word nontechnical Author Summary, explicit Data Availability Statement, accessible underlying findings data where permitted, and appropriate ethics/disclosure statements |

Authoritative instructions:
- JAMIA: https://academic.oup.com/jamia/pages/General_Instructions
- JAMIA Open: https://academic.oup.com/jamiaopen/pages/general_instructions
- PLOS Digital Health: https://journals.plos.org/digitalhealth/s/submission-guidelines

Recheck requirements at the actual submission date. These constraints are not a guarantee of editorial fit or acceptance.

## Scientific positioning for JAMIA

The paper's primary question is whether a small, interpretable set of clinician-concern semantic measurements adds short-horizon ICU outcome discrimination beyond a strong structured comparator that captures physiology, treatment/support, documentation behavior, and note context.

The registered primary Open-Jev contrasts remain the center of the manuscript. Their primary uncertainty intervals included zero across invasive ventilation, renal replacement therapy, and ICU death. After registration, supervised TF-IDF scalar scores, frozen BGE embeddings, 32-component early fusion, unstripped-note sensitivity and comparator-richness analysis offered mechanistic context, but did not establish robust incremental AUROC improvements over the rich structured comparator.

The manuscript should distinguish **prognostic information in available clinical notes** from **additional information above the specified structured model**. The findings are not equivalence tests, causal evidence of redundancy, or evidence that all possible narrative representations would be unhelpful.

A novelty review must compare this study to relevant recent text-versus-structured-data studies, especially work in JAMIA, and explain the added scientific value of the registered clinician-concern instrument, strong documented comparator, stringent source/patient design and full-refit uncertainty. A simple statement that text does not improve discrimination is insufficient as the entire novelty claim.

The study currently lacks a convincing independent external validation of the full analysis. Do not suggest prospective generalization or demonstrated clinical deployment value.

## Source-of-truth and interpretation boundary

Primary manuscript: `manuscript/JAMIA_WORKING_DRAFT_2026-10-03.md`. This is an older draft and must not be assumed to include the completed October–November exploratory extensions.

Primary supplement: `manuscript/SUPPLEMENT_2026-10-03.md`. Reconcile it with completed registrations, source code and results before producing submission files.

Cross-outcome synthesis: `docs/results/v2_1_extension_t1_cross_outcome_synthesis_method_qa_2026-11-10.md`.

Statistical adjudication: `docs/results/v2_1_extension_t1_5_statistical_adjudication_2026-11-11.md`.

Known remaining inferential limitation: the A-level supervised text score assigns zero for no-note stays, which can encode note availability absent from the thin structured comparator. Ventilation A TF-IDF's original ΔAUROC point estimate lies above its 200-refit percentile interval's upper endpoint. The inherited original-versus-bootstrap inner-fold seed convention is code-confirmed, but the numerical influence on that shift is not resolved by aggregate results. Preserve the original values and report their limitations without changing the frozen method.

The registered post-T1.5 stop rule forbids new exploratory outcome analyses without an independent bedside-narrative dataset and a separate protocol. Publication work can verify aggregate results and regenerate figures from actual permitted data, but must not silently introduce outcome models or reselect analyses after inspecting outcomes.

## Package production order and acceptance checks

### 1. Evidence and novelty ledger

- Reconcile cohort counts, primary metrics, CIs, exact comparator and note-population definitions across registered reports, aggregate JSON and manuscript.
- Check the newest directly competing work, define what is novel and what is corroboration, then formulate a falsifiable, non-overstated paper contribution.
- Resolve the publication interpretation of the original-versus-bootstrap distribution discrepancy through transparent code review and expert statistical sign-off, without unregistered model fitting.
- Build a numbered provenance table so each manuscript statistic points to a validated source.

### 2. Figures and tables

- Prepare an evidence-first figure plan from the registered scientific question.
- Generate all research graphs with scripts in the repository on actual allowed frozen data or validated aggregate artifacts. Never use a text-to-image generator for scientific figures.
- Verify each point/interval/denominator against source output and render the final files for visual review. Keep figure legends, alt text and scripts synchronized.

### 3. Main manuscript and supplementary material

- Revise the main text to the 4,000-word JAMIA limit and five-part structured abstract with at most 250 words.
- Separate preregistered results from post-registration exploratory results. Move necessary method detail and secondary evidence to supplement while retaining an interpretable main paper.
- Provide complete supplemental methods, cohort and predictor definitions, all planned sensitivities and exploratory findings, statistical method details, extra tables/figures and provenance.
- Check reporting guidelines such as TRIPOD+AI against the actual modeling study and document unmet items rather than marking them done without evidence.

### 4. References and reproducibility

- Verify citations against primary literature, use PubMed first, preserve Zotero-compatible citations and bibliography.
- Confirm code and aggregate data availability statements are true. Restricted MIMIC notes and patient-level records must not be deposited publicly. Clearly explain access restrictions.
- Prepare appropriate ethics, conflicts, funding, author-contribution and generative-AI declarations without inventing contributor information.

### 5. Final submission deliverables

- JAMIA-ready DOCX manuscript and an independently numbered DOCX/PDF supplement.
- Separate high-resolution figure files with legends, source scripts, alt text and final figure/table inventory.
- Complete reference database, required reporting checklist, cover letter, title page, disclosures and submission QA report.
- Author approval of final package, then one actual journal submission.

## Adaptive fallback

JAMIA Open uses closely related word, abstract, figure and table limits, so the first completed package should need limited formatting changes, though its scientific framing may need revision after JAMIA feedback. Prepare its patient-facing summary when adapting the files.

PLOS Digital Health places stronger emphasis on broad-reader interpretation, a dedicated Author Summary and rigorous underlying-data accessibility. Before resubmission, distinguish which MIMIC inputs require credentialed access and which derived aggregate materials and code can be provided publicly. Verify that the Data Availability Statement satisfies PLOS policy without releasing restricted patient-level data.

## Decision and scope

**Approved journal sequence: JAMIA -> JAMIA Open -> PLOS Digital Health.** There is no authorization to submit automatically, contact editors, publish manuscript files as a preprint, or run additional outcome analyses. The next concrete production milestone is the JAMIA evidence/novelty ledger followed by figure/table architecture.
