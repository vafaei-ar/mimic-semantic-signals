# Cover letter draft for JAMIA

October 4, 2026

Editor-in-Chief  
Journal of the American Medical Informatics Association

Dear Editor:

Please consider our Research and Applications manuscript, **“Incremental predictive value of low-dimensional semantic scores from ICU notes: a preregistered evaluation in MIMIC-III.”**

This study asks a narrow but increasingly important informatics question: when narrative ICU notes are compressed into a small set of language-model-derived semantic measurements, do those measurements add predictive discrimination beyond a strong structured EHR model?

The corrected analysis was preregistered before its predictive performance was examined. Across invasive ventilation, renal replacement therapy, and ICU death, eight Open-Jev semantic scores did not produce a reproducible increase in AUROC beyond a rich comparator containing physiology, laboratory data, treatment/support context, documentation behavior, and note context. Registered Brier score, log-loss, calibration, and decision-curve summaries likewise did not reveal a hidden benefit. Prespecified sensitivity analyses using alternative semantic instruments and text-processing rules did not change that conclusion. In a common logistic model family, however, high-dimensional TF-IDF features retained small positive increments while the compact semantic scores did not.

Two post-registration explanatory analyses help make the negative result informative. First, a label-free alignment audit found expected hemodynamic and respiratory construct-state associations relative to shuffled-score references, reducing concern that the null result arose from gross score-to-stay misalignment. Second, comparator decomposition showed that the Open-Jev increment for ventilation was positive over physiology alone but attenuated after treatment/support variables and disappeared after documentation behavior was represented. For ICU death, the semantic scores showed standalone prognostic discrimination but no incremental value even over physiology alone. These analyses support a representation and redundancy interpretation rather than a claim that clinical narrative contains no predictive information.

We believe the manuscript is well suited to JAMIA because it evaluates an informatics representation strategy under a transparent preregistered design, documents an integrity-driven correction of earlier exploratory analyses, and shows how comparator construction can change conclusions about the incremental value of clinical text. The paper also provides complete provenance for manuscript-facing estimates and separates registered analyses from post-registration explanatory work.

The study uses deidentified MIMIC-III data under its credentialing and data-use requirements. No external funding supported the study. The manuscript has not been submitted elsewhere. [AUTHOR: confirm this sentence immediately before submission.]

Generative AI disclosure: OpenAI ChatGPT (GPT-5.6 Sol) assisted with code generation and review, organization of analysis documentation, literature-search support, drafting and editing manuscript text, and preparation of reproducible figure code. Anthropic Claude [exact model/version to be confirmed by the author] was used for independent code, study-design, and manuscript review. The author directed the scientific questions, made and adjudicated the analysis decisions, reviewed AI-assisted code and recommendations, verified manuscript-facing numerical results against frozen aggregate artifacts, verified cited references, and takes responsibility for the final manuscript. No AI system is listed as an author.

Thank you for considering this work.

Sincerely,

[AUTHOR NAME, DEGREES]  
[DEPARTMENT]  
[INSTITUTION]  
[EMAIL]  
[TELEPHONE]
