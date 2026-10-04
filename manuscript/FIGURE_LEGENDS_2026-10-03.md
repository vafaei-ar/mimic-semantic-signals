# Working figure legends and alt text

Updated: 2026-10-03

## Figure 1. Incremental discrimination from low-dimensional semantic scores

**Legend.** Delta area under the receiver operating characteristic curve (AUROC) for the registered primary Open-Jev analyses, principal registered H6 semantic-instrument sensitivities, separate CareVue ICU-death replication, and registered H7 patient-shuffled negative controls. Points show the primary-partition delta AUROC, defined as augmented model minus its corresponding comparator. Horizontal lines show 95% patient-cluster refit-bootstrap percentile intervals. Panel A presents the three MetaVision outcomes for primary stripped-note Open-Jev, unstripped-note Open-Jev, Laya, and DiffusionGemma. Panel B presents the CareVue Open-Jev replication and patient-shuffled semantic controls. All displayed intervals span zero. MetaVision and CareVue ICU-death analyses are shown separately and were not pooled.

**Alt text:** Two-panel forest plot of changes in AUROC after adding semantic scores. In panel A, estimates for invasive ventilation, renal replacement therapy, and MetaVision ICU death are clustered near zero for primary Open-Jev and the principal semantic-model sensitivities, with every confidence interval crossing zero. Panel B shows the CareVue ICU-death replication and patient-shuffled semantic controls; these estimates are also near zero or negative, and every confidence interval crosses zero.

## Figure 2. Exploratory attenuation of Open-Jev increment across comparator levels

**Planned legend.** Post-registration exploratory decomposition of Open-Jev incremental AUROC across four nested HistGradientBoosting comparators: A, 34 structured physiology/laboratory/urine features; B, A plus treatment/support context and death-specific code status; C, B plus documentation-behavior variables; and D, C plus ordinary note context, equal to the registered rich comparator. Points should show each frozen partition and the primary partition should be visually distinguished. No new bootstrap was performed; partition ranges are stability summaries, not confidence intervals. The ventilation A/B values require an explicit note-availability caveat because semantic missingness can reveal note availability before documentation/note-context variables enter the comparator.

**Alt text:** Planned plot showing Open-Jev delta AUROC across four increasingly rich comparators for three outcomes. Ventilation starts positive over physiology alone, decreases after treatment/support variables, and is approximately zero after documentation behavior is added. Renal replacement therapy remains near zero throughout. ICU-death estimates remain negative or near zero throughout.
