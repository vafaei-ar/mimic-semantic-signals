# JAMIA Paper 1 figure and table architecture

Date: 2026-11-19  
Status: **First reproducible main-figure render complete and hash-verified. Visual inspection and final manuscript integration are pending.**  
Journal: JAMIA Research and Applications. Current instruction limits are six figures, four tables, 4,000 main-text words, and a 250-word structured abstract. Figures require accessible alt text and separate uploads. The journal requires tables within the manuscript as Word tables.  
Scientific boundaries: registered primary H1-H3 versus explicitly labeled post-registration exploratory extensions. No new clinical outcome modeling or statistical estimator was introduced.

## Editorial visual thesis

The study tests whether adding eight fixed, clinically named semantic scores derived from prospectively eligible ICU notes improves 12-hour event prediction beyond a strong structured baseline. The high-priority evidence is not an algorithm architecture illustration or a colorful comparison of many text models. It is the three original registered ΔAUROC estimates with complete-refit uncertainty, after careful accounting for physiologic, treatment, and documentation-process context. The main figures must make this claim understandable while limiting the display of post hoc analyses.

## Locked main-article display plan

| Slot | Content and intended reader conclusion | Scientific source | Format | Publication decision |
|---|---|---|---|---|
| Figure 1 | Study design at 12-hour landmark, eligible pre-landmark notes, eight semantic scores, comparator construction and separate prospective 12-hour outcomes | Frozen `figure1_nature_style_data.json` design object and source methods | Vector schematic (PDF/SVG) | Main |
| Figure 2 | Registered H1-H3 ΔAUROC plus two-sided 95% patient-cluster full-refit percentile intervals, with a visible zero-reference line | Frozen `figure1_nature_style_data.json` primary forest records, checked against `docs/results/v2_1_primary_openjev_results.md` | Vector forest plot (PDF/SVG) | Main |
| Table 1 | Demographic/clinical characteristics, note availability overall and by event status | `docs/results/v2_1_submission_characteristics_results.md` | Editable Word table | Main |
| Table 2 | Comparator AUROC, augmented AUROC, ΔAUROC, full-refit CI, and ΔAUPRC for ventilation, RRT and MetaVision ICU death | `docs/results/v2_1_primary_openjev_results.md` | Editable Word table | Main |
| Table 3 | Prespecified representation comparison in one logistic family if needed to support the compression argument | `docs/results/v2_1_h5_lexical_results.md` | Word table | Optional, main only if it adds information not repeated by Figure 2 or Results prose |
| Figure 3 | Concise registered instrument/timing/control sensitivity forest only if the Discussion genuinely needs a visual robustness summary | `manuscript/figure1_nature_style_data.json` nonprimary records and registered freezes | Vector forest | Optional, otherwise supplementary |

**Reason for simplifying the older figures:** `manuscript/make_paper1_figures.py` and `manuscript/figure1_nature_style.py` place registered primary results alongside a large set of sensitivities. `manuscript/figure2_nature_style.py` combines registered lexical comparisons with post-registration A–D decomposition, label-free alignment and note-available subgroup estimates. These graphics mix levels of evidence. The new main figures separate orientation and registered inference, while keeping exploratory mechanisms in the supplement.

## Supplementary figure and table architecture

| Suggested slot | Content | Evidence tier and guardrail |
|---|---|---|
| Figure S1 | Instrument, endpoint, timing, CareVue replication and H7 negative-control forest | Registered H4/H6/H7. Include exact CI definitions. CareVue not pooled with MetaVision |
| Figure S2 | A–D Open-Jev comparator-richness profiles over five frozen partitions | Post-registration exploratory. No paired A-minus-D uncertainty and no causal attenuation claim |
| Figure S3 | Registered common-logistic Open-Jev versus TF-IDF representation results | Registered H5. No unreported inferential intervals |
| Figure S4 | Label-free construct/state alignment relative to shuffled vectors | Post-registration integrity audit, not human criterion validation |
| Figure S5 | Five-partition note-available subgroup and missing-note context | Post-registration exploratory. Full-cohort predictions were not refit in subgroup |
| Figure S6 | Post-registration T1.1–T1.5 text-model sensitivity/decomposition, with separate panels for TF-IDF, supervised BGE, BGE early fusion and unstripped notes | Exploratory. Show prespecified A/D intervals when available, five partition stability separately. No pooling of outcomes |
| Tables S1–S10 | Existing registered and explanatory supplemental tables, reconciled against manuscript and source | Preserve existing table identities as much as possible. Never silently overwrite frozen results |
| Tables S11 onward | Additional supervised-text comparisons, comparator feature inventory, exact study deviations and detailed T1.5 summaries | Exploratory, with explicit provenance and no inferential extrapolation beyond A and D |

Figure S6 is a planned synthesis, not a newly plotted result. Its values are available in completed GitHub result freezes. The registered post-T1.5 stop rule still applies.

## Generation and validation record

**Generation script:** `manuscript/make_jamia_main_figures.py`. It reads only the committed `manuscript/figure1_nature_style_data.json`. It validates the cohort denominators (11,116 / 19,395 / 19,811), event counts (279 / 314 / 214), exactly three registered primary records, and their exact point estimates and bootstrap interval endpoints. No external images, simulated patient data, clinical notes, model refits or new statistical testing are used.

**RunRelay task:** `build_jamia_main_figures`, job `T0EK5K79`, exact Git commit `a576c1ee0a6e9087e88b0417460538ccea02ae54`, bound machine `pshjl4vf24`, automatic low-risk execution, terminal status **completed**, exit **0**, six safe artifacts. Previous malformed duplicate YAML mapping keys in the unrelated matplotlib-figure section were repaired before submission without altering scientific code.

| Generated artifact | SHA-256 | Size (bytes) |
|---|---|---:|
| `outputs/manuscript/jamia_v1/JAMIA_Figure_1_Study_design.pdf` | `e09ac9812f5b87ff0e8994ab7427d8186b4cdd129d98c322ea9076fc7ac7e69e` | 27,200 |
| `outputs/manuscript/jamia_v1/JAMIA_Figure_1_Study_design.svg` | `f5198092d1536373ad96f57f6a2a682e99f5779558dd2f53c35f8207a9a7d8ba` | 12,380 |
| `outputs/manuscript/jamia_v1/JAMIA_Figure_1_Study_design.png` | `b1efd8ea22dfd115ee0f13c966c9233dbe567d13164538754acebdbeae7934a9` | 258,261 |
| `outputs/manuscript/jamia_v1/JAMIA_Figure_2_Primary_delta_AUROC.pdf` | `dbe823ec948e28815cd142ddf06f3eb25d522792c34d657089882f7f41bcc0c1` | 22,374 |
| `outputs/manuscript/jamia_v1/JAMIA_Figure_2_Primary_delta_AUROC.svg` | `be58ab3be817c697044e3cccb4e1df4ddfa6227f1aa42b9b5d7d2aa80a5840ad` | 10,090 |
| `outputs/manuscript/jamia_v1/JAMIA_Figure_2_Primary_delta_AUROC.png` | `bd89345a43bc3ae6ca0e35177dfd008486c6f5e9b32e6cd3adf145cf3853d3e0` | 141,610 |

The canonical Reader returned these six declared safe output hashes. Its R2 bundle share was published with expiry **2026-11-22 22:56 UTC**. The file bundle could not be transferred to this chat environment for visual QA because the container could not resolve the R2 host and the generic download interface did not accept the private share URL. Thus binary file existence, checksums, and successful rendering are verified, while **final-size visual inspection remains pending**. The generated outputs live as RunRelay artifacts and are not represented as tracked GitHub binary files.

## Working main-figure legends

**Figure 1. Study design and semantic-score augmentation.** Adults in MIMIC-III MetaVision ICU cohorts remained at risk at a fixed 12-hour landmark after ICU admission. The models used prior structured physiologic, laboratory, treatment and documentation information and the single latest eligible bedside note from the pre-landmark window. The study applied the prespecified endpoint/treatment-expression removal before deriving eight Open-Jev semantic scores. The rich HistGradientBoosting comparator already included documentation behavior and ordinary note context. The primary contrast added the eight semantic scores to that comparator. Ventilation (279 events/11,116 stays), renal replacement therapy (314/19,395), and ICU death (214/19,811) were evaluated separately over the next 12 hours. Eligible note absence did not exclude an otherwise eligible ICU stay. CareVue ICU death was analyzed separately as a registered sensitivity cohort. The figure is a conceptual summary of the implemented analysis rather than a patient-level flow diagram.

**Alt text, Figure 1:** Study schematic. A timeline shows the 12-hour ICU landmark and the following 12-hour outcome period. A flow diagram depicts eligible adult MetaVision ICU stays, structured and bedside-note inputs, comparison of the rich structured model with the same model plus eight semantic scores, and separate ventilation, renal-replacement-therapy and ICU-death outcomes.

**Figure 2. Incremental discrimination from registered semantic-score augmentation.** Points show original primary-partition ΔAUROC (augmented model minus structured comparator) for invasive ventilation, renal replacement therapy, and MetaVision ICU death. Horizontal whiskers show two-sided 95% patient-cluster bootstrap percentile intervals with complete refitting of the structured and augmented models, using 500 valid replicates for each outcome. The vertical dashed line denotes ΔAUROC = 0. Five patient-grouped outer partitions were evaluated, but only the prespecified first partition contributes to the displayed bootstrap intervals. The three effects are −0.00005 [−0.02173, +0.01910], −0.00079 [−0.00323, +0.00275], and −0.00212 [−0.00802, +0.00531]. All three intervals include zero. These are not equivalence intervals.

**Alt text, Figure 2:** Three-row forest plot of registered incremental AUROC. Ventilation, renal replacement therapy and ICU death have point estimates close to zero with horizontal 95% bootstrap intervals crossing a vertical zero-reference line. The ventilation interval is substantially wider than the other two intervals.

## Final-figure QC gates

1. Retrieve the actual binary outputs and inspect the PNG render at JAMIA submission size, checking label collisions, note-unavailability clarity, readability and line contrast.
2. Confirm that vector output retains editable text, no clipped marks, correct font embedding and a color-independent distinction wherever necessary.
3. Verify the three plotted points and six CI endpoints against the original registered result freeze and audit that no exploratory result entered the primary forest.
4. Place legends in the manuscript and supply alt text for both figures. Main Table 1 and Table 2 must remain editable Word tables and must not duplicate figures unnecessarily.
5. Publish no restricted MIMIC data, raw notes, patient-level features or predictions. Obtain final statistical and author review before submission.

The working publication goal remains sequential JAMIA, JAMIA Open, and PLOS Digital Health. This checkpoint does not authorize a journal submission.
