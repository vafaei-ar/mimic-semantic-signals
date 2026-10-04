# Exploratory extension: incremental bedside-text information across representations and comparator richness

Version 2.1, 2026-10-04. Replaces all earlier versions of `paper1_extension_plan_2026-10-04.md`. v2.1 adds five wording and protocol refinements from the final methodological review; the analysis program is unchanged.
Repo: `vafaei-ar/mimic-semantic-signals`

This version keeps the bounded scope agreed after review and adds six changes: an early-fusion arm, an interpretive learnability threshold, a pre-declared interpretation table, patient-level grouping inside bootstrap replicates, an exact timing definition, and a hard runtime cap.

Constraints:

- no Penn State data;
- no clinician rating;
- no paid annotation;
- raw notes and row-level predictions stay local;
- no note text goes to any external API;
- every result below is **post-registration exploratory**.

---

## 0. Protect the finished paper (before anything else)

1. Tag the current commit `paper1-jamia-ready-2026-10-04`. Archive the submission ZIP and its SHA-256 checksums under `outputs/manuscript/archive/`.
2. Do all extension work on branch `extension-v2_1`. Nothing on `main` changes until the extension is complete and reviewed.
3. If the extension takes more than 3 weeks or fails technically, submit the tagged package unchanged.

## 1. Scope (frozen now)

**In scope:** A, T0.1, T0.2, T0.3, T0.4, T1.1, T1.2, T1.2b, T1.4, T1.5.

**Deferred** (written into the addendum now, so the deferral is not a result-dependent decision):

- T1.3 fine-tuned transformer (kept as a possible revision analysis);
- scoping review (separate paper);
- MIMIC-IV radiology arm;
- any structured-only external dataset.

**The only exception:** a newly accessible external dataset with real bedside narrative notes. If one arrives, stop and write a separate protocol before touching it.

## 2. Ground rules

- Commit a protocol file under `docs/` before any job reads outcome labels. Record the commit hash in each result freeze.
- No changes to hyperparameters, features, thresholds or models after outcome-dependent metrics are seen. A technical failure is logged as a deviation, with the job ID, and only the bug is fixed.
- Reuse the frozen pieces:
  - cohorts: vent 11,116/279; RRT 19,395/314; MetaVision death 19,811/214; CareVue death 25,632/306;
  - the five patient-grouped partitions;
  - HGB settings: lr 0.05, 300 iterations, 15 leaves, min leaf 50, L2 1.0;
  - the 500-replicate paired patient-cluster refit bootstrap;
  - `scripts/set_hgb_thread_env_v2_1.sh`.
- Each task produces one aggregate JSON (with SHA-256), one `docs/results/` markdown, and one provenance-index entry. New source files start at `src/165_`.

---

## Step A. OSF exploratory addendum (~1 hour, first)

File: `docs/registration/exploratory_extension_addendum_2026-10.md`. Commit it, then upload it to the OSF project (wmyb2) with a reference to `10.17605/OSF.IO/AHXN9` before any T-task reads labels. Contents:

- title as above (neutral);
- task list, primary metric per task, and the deferred list in Section 1;
- the interpretive learnability threshold (Tier 1) and the interpretation table (Section 4), word for word;
- the frozen embedding model ID, revision hash and chunking rule (T1.2).
- the statement that these analyses are exploratory, do not alter H1–H9, and that any pattern of results will be reported.

---

## Tier 0: frozen out-of-fold predictions, no refitting (~2–4 days)

These already exist and must not be recomputed:

- ΔBrier
- Δlog loss
- calibration slope
- net benefit at the registered thresholds
- primary-partition ΔAUPRC

### T0.1 Alert burden at fixed alert rates

- **Inputs:** frozen OOF predictions (comparator, comparator + Open-Jev) for H1, H2, H3 and CareVue death, all five partitions.
- **Alert rates:** top 2%, 5%, 10% and 20% of predicted risk within each cohort.
- **Ties:** rank by predicted risk (descending), then by frozen `case_id` (ascending), and alert exactly the first ⌈rate × N⌉ stays, so every model uses the exact same alert budget.
- **Per model and rate:**
  - sensitivity
  - PPV
  - events caught per 1,000 stays
  - alerts per true event
- **Paired contrast:**
  - stays per 1,000 whose alert status changes (in and out separately);
  - events among those stays;
  - net events caught per 1,000.
- **Uncertainty:**
  - range across the five partitions;
  - a 2,000-replicate patient-cluster bootstrap of the frozen primary-partition predictions, labelled "conditional on the fitted models".
- **Outputs:** `extension_alert_burden_v2_1.json`, a results markdown, and one supplementary table.

### T0.2 Decision curves (supplementary figure)

Plot the registered net-benefit arrays if they are stored. If not, recompute them from the frozen OOF predictions at the registered thresholds. Use three panels (comparator, augmented, treat-all, treat-none) in the `make_paper1_figures.py` style.

### T0.3 Upper confidence limits (writing only)

Add this to the Abstract: "The upper 95% confidence limit for ΔAUROC was +0.019 for ventilation, +0.003 for RRT, and +0.005 for ICU death." In the Discussion, compare these limits with the prespecified detectable magnitudes (0.0233, 0.0113, 0.0241). Do not use the words "equivalent" or "ruled out".

### T0.4 Note timing relative to support transitions (label-free)

- **Inputs:**
  - frozen primary landmark notes (storetime);
  - Open-Jev construct scores;
  - support-event timestamps from the alignment audit.
- **Excluded events:** outcome events (invasive ventilation, RRT, death). No outcome labels are read.
- **Pairs:**
  - hemodynamic concern ↔ vasoactive start;
  - respiratory concern ↔ high-flow start;
  - respiratory concern ↔ NIV start;
  - respiratory concern ↔ FiO2 increase (the audit's frozen definition).
- **Exact definition.** A *qualifying transition* is the first start of the support (or the first FiO2 step-up) after at least 6 h without it. For each note:
  - *prior transition*: the most recent qualifying transition in the 12 h before storetime;
  - *subsequent transition*: the first qualifying transition in the 12 h after storetime;
  - each note is classified as prior only, subsequent only, both, or neither.
- **Score groups:** top vs bottom quartile of the construct score. Quartile cutoffs come from the score distribution only.
- **Primary summary:** among high-score notes with any transition in the window, the proportion that are subsequent only, with a patient-cluster bootstrap 95% CI.
- **Full distribution:** also report all four categories (prior only, subsequent only, both, neither) with counts and percentages for high-score, low-score and shuffled-score notes, so the "both" group stays visible.
- **Comparisons:**
  - bottom-quartile notes;
  - patient-shuffled scores (reuse the H7 shuffle).
- **Secondary:** prevalence of an *ongoing* support at storetime (started earlier, still active) by score quartile. This directly measures how often the note describes something the structured comparator already sees.
- **Guardrail:** this is a descriptive analysis, not a prediction claim.

---

## Tier 1: cross-fitted supervised text augmentation (~1.5–2 weeks)

Naming: "supervised text benchmark", not "ceiling". The earlier supervised encoder (`multitask_supervised_text_encoder_v2_final_test_freeze.md`) belongs to the obsolete v1 benchmark and is not evidence for this paper.

### Shared design

- **Text input:** the frozen stripped primary landmark note. Stays without a note get a missing text feature.
- **Within each outer training fold (five frozen partitions):**
  - fit the text model on training-fold stays that have a note;
  - generate training-row text scores by inner 5-fold cross-fitting, grouped by patient;
  - refit on the full training fold to score the held-out fold;
  - add the result to the rich comparator HGB.
- **Bootstrap:** refit both the text model and HGB inside every bootstrap replicate for T1.1, T1.2 and T1.2b. Embeddings and TF-IDF vocabularies are label-free. The vocabulary is fit within each training fold; embeddings are cached once.
- **Grouping rule inside replicates:** all copies of a resampled patient go to the same inner fold. Duplicated patients split across inner folds leak.
- **Primary metric:** ΔAUROC against comparator D, primary partition, with a 500-replicate paired refit-bootstrap 95% CI.
- **Secondary metrics:** five-partition range, ΔAUPRC, and T0.1-style alert counts at a 5% alert rate.
- **Runtime cap (mechanical, outcome-independent):** for each task, run the first 10 bootstrap replicates and record only their wall time, not their performance estimates. Multiply the median replicate runtime by 500. If the projection exceeds 72 h, run exactly 200 valid replicates; otherwise run 500. The 10 timing replicates use the frozen seed sequence and count toward the final set. Log the projection in the result freeze.

### Interpretive learnability threshold (reported for every text model)

Standalone out-of-fold text-score AUROC within note-available stays, against the outcome. Standalone AUPRC (with the outcome prevalence among note-available stays) is reported alongside, but AUROC is the only pre-declared threshold. Early fusion (T1.2b) has no standalone score and uses the T1.2 value.

- **AUROC ≥ 0.60:** the text representation carries standalone outcome signal. A near-zero increment against D supports a redundancy interpretation.
- **AUROC < 0.60:** insufficient standalone text discrimination to support a redundancy interpretation. Report the increment unchanged.

The threshold guides interpretation only. It is not a validity boundary: all results are reported regardless, and values close to 0.60 are described as such.

This matters most for ventilation, which has only about 135 events among note-available stays.

### T1.1 Supervised TF-IDF score → rich HGB

TF-IDF and L2-logistic settings are identical to H5. The output log-odds are added as one feature to the registered HGB comparator.

### T1.2 Frozen-embedding score → rich HGB

- **Model:** one open-weight sentence-embedding model, chosen label-free on Day 1 before the OSF addendum is uploaded and before any label-reading job runs. Record the model ID, revision hash, max length, chunking and pooling rule in the protocol. No comparison of several models.
- **Long notes:** fixed chunking and mean-pooling rule.
- **Classifier:** L2-logistic on the embeddings, with C chosen by inner CV on training folds only. The resulting log-odds are added as one feature to HGB.

### T1.2b Early-fusion sensitivity (added in v2)

Late fusion through a single score cannot capture interactions between text features and individual structured variables.

- **Method:** reduce the T1.2 embeddings to 32 principal components (PCA fit label-free on the training fold, refit inside each bootstrap replicate). Feed them directly into HGB with comparator D.
- **Cost:** about the same as T1.2.
- **Why:** it answers the obvious reviewer question without a fine-tuned model.

### T1.4 Direct-term stripping sensitivity

Repeat T1.1 on the frozen **unstripped** H6 notes. Report stripped vs unstripped ΔAUROC. Wording: "endpoint/treatment-language sensitivity". The difference is not called pure leakage.

### T1.5 Comparator-richness decomposition with supervised text

- **Repeat:** the existing A→D decomposition (physiology/lab/urine → + treatment/support → + documentation behaviour → + note context) with the T1.1 and T1.2 scores.
- **Reporting:** point estimates per level and partition, plus primary-partition refit-bootstrap CIs at levels A and D.
- **Planned figure:** Figure 2a style, with Open-Jev, TF-IDF and embedding lines side by side.

---

## 4. Interpretation table (pre-declared, goes into the addendum)

| Result pattern | Allowed claim |
|---|---|
| Text AUROC ≥ 0.60; increments at D near zero for TF-IDF, embedding and early fusion | Bedside text carries outcome information, but little incremental discrimination remains once physiology, treatment/support, documentation behaviour and note context are represented |
| Increments clearly positive at A and shrinking toward D (T1.5) | Estimated incremental text value depends on comparator richness; thinner comparators yield larger apparent gains |
| TF-IDF, embedding or early fusion positive at D (CI excludes 0) | The Open-Jev null partly reflects compression to eight constructs; residual narrative information exists |
| Early fusion positive at D (CI excludes 0) while scalar stacking is near zero | Interactions between text and individual structured variables carry information that a single text score misses |
| Text AUROC < 0.60 | Insufficient standalone text discrimination to support a redundancy interpretation for that outcome |
| Unstripped ≫ stripped (T1.4) | Naive pipelines are vulnerable to inflated performance from direct endpoint/treatment language |
| T0.4: mostly prior or ongoing support at high-score notes | High semantic concern often coincides with or follows support already visible in structured data, consistent with documentation of existing clinical state |
| T0.4: notes often precede transitions | Notes sometimes anticipate support changes; describe this, with no new prediction claim |

Every row is a reportable result. No row is a failure.

---

## 5. Schedule (bounded, 2–3 weeks)

| Days | Work |
|---|---|
| 1 | In this order: tag and branch → choose embedding model label-free and record ID/revision/chunking → commit protocols and addendum → upload addendum to OSF → only then permit label-reading jobs |
| 2–4 | T0.1, T0.2, T0.3; label-free embedding pass; T1.1 runs |
| 5–9 | T0.4; T1.2 and T1.2b; T1.4 |
| 10–13 | T1.5; result freezes; provenance index |
| 14–18 | Manuscript revision, figures, supplement, `audit_paper1_submission_repo.py`, metadata and prose checks |

Stop rule: no new analyses after day 13 unless a narrative external dataset arrives, and that gets its own protocol.

## 6. Manuscript changes

- **Framing:** does bedside text add discrimination beyond a rich structured comparator? Open-Jev stays the registered primary instrument.
- **Figure 2b:** replaced by a multi-representation comparison: Open-Jev, Laya and DiffusionGemma (registered), plus TF-IDF, embedding and early fusion (exploratory), each with 95% CIs and its standalone text AUROC relative to the 0.60 threshold.
- **New panel or figure:** T1.5 decomposition with supervised text.
- **T0.1:** one main-text sentence plus a supplementary table. **T0.2 and T0.4:** supplement, with one main-text sentence for T0.4.
- **Labelling:** every extension result is marked "post-registration exploratory" in captions and table footnotes.
- **Target:** npj Digital Medicine if Tier 1 is informative. Lancet Digital Health is realistic only with an independent narrative dataset. JAMIA stays the fallback with the tagged package.
