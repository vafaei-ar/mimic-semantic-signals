November 23, 2026

Suzanne R. Bakken, PhD, RN  
Editor-in-Chief  
Journal of the American Medical Informatics Association

Dear Dr. Bakken:

Please consider our Research and Applications manuscript, **“Incremental predictive value of predefined semantic scores from ICU notes beyond documentation-aware EHR models: a preregistered evaluation.”**

This study asks a narrow but increasingly important informatics question: when narrative ICU notes are compressed into a small set of language-model-derived semantic measurements, do those measurements add predictive discrimination beyond a strong structured EHR model?

The corrected analysis was preregistered before its predictive performance was examined. Across invasive ventilation, renal replacement therapy, and ICU death, eight Open-Jev semantic scores did not produce a reproducible increase in AUROC beyond a rich comparator containing physiology, laboratory data, treatment/support context, documentation behavior, and note context. Registered Brier score, log-loss, calibration, and decision-curve summaries likewise did not reveal a hidden benefit. Prespecified sensitivity analyses using alternative semantic instruments and text-processing rules did not change that conclusion. A prespecified common-logistic comparison gave small positive TF-IDF point differences without full-refit uncertainty intervals. We treat these as descriptive and do not claim reliable added performance.

Four post-registration explanatory analyses help make the negative result informative. A label-free alignment audit found expected hemodynamic and respiratory construct-state associations relative to shuffled-score references, reducing concern that the null arose from gross score-to-stay misalignment. Semantic-only discrimination showed that the scores could carry outcome information without necessarily adding value to the comparator. Comparator decomposition showed that the Open-Jev increment for ventilation was positive over physiology alone but attenuated after treatment/support variables and disappeared after documentation behavior was represented. Finally, restricting the already-frozen predictions to note-available patients did not reveal a stable positive incremental effect across partitions. These analyses distinguish standalone predictive association from added discrimination, while leaving causal attribution of note content and documentation availability unresolved.

We recognize the recent JAMIA report by Peng and colleagues (2026, doi:10.1093/jamia/ocag146) showing task-specific limits of adding radiology reports or imaging to structured EHR data. Our study evaluates a different and more targeted question, the incremental value of eight prespecified bedside-note semantic measurements under source-system-compatible cohorts, a documentation-aware comparator, and full-refit uncertainty. Separately frozen exploratory TF-IDF and embedding extensions also failed to establish a consistent gain above the richest comparator. These findings are explicitly secondary to the preregistered primary analysis.

We believe the manuscript is well suited to JAMIA because it evaluates an informatics representation strategy under a transparent preregistered design, documents an integrity-driven correction of earlier exploratory analyses, and shows how comparator construction can change conclusions about the incremental value of clinical text. The paper also provides complete provenance for manuscript-facing estimates and separates registered analyses from post-registration explanatory work.

The study uses deidentified MIMIC-III data under its credentialing and data-use requirements. No external funding supported the study. The planned human construct validation and full external bedside-narrative validation were not completed, and we report these limitations explicitly.

Generative AI disclosure: OpenAI ChatGPT assisted with code generation and review, organization of analysis documentation, literature-search support, drafting and editing manuscript text, and preparation of reproducible figure code. Anthropic Claude was used for independent code, study-design, and manuscript review. The author directed the scientific questions, made and adjudicated the analysis decisions, reviewed AI-assisted code and recommendations, verified manuscript-facing numerical results against frozen aggregate artifacts, verified cited references, and takes responsibility for the final manuscript. No AI system is listed as an author.

Thank you for considering this work.

Sincerely,

Alireza Vafaei Sadr, PhD, MS  
Assistant Professor, Department of Public Health Sciences  
Penn State College of Medicine  
700 HMC Crescent Road  
Hershey, PA 17033, USA  
asadr@pennstatehealth.psu.edu  
1-717-531-8521
