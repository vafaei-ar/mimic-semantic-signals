# Population-representative structured calibration result freeze v1

Canonical RunRelay job: `S7K4R9V3`

- exact project commit: `1bafb15831238986b6b25921aaf9406c8addaf28`
- task: `evaluate_population_landmark12_structured`
- artifact: `outputs/multitask_benchmark/population_landmark12_structured_calibration_v1.json`
- artifact SHA-256: `cf923b46c1ff7c0659a6a942e3b9e84b8d4d340d3c215f9e6219fbb8a0869123`
- exit code: 0
- runtime: 481.7 seconds

The prior implementation `K4R8V2Q7` timed out because of an inefficient bootstrap. The scientific protocol was unchanged. The replacement implementation passed a synthetic equivalence check and used mathematically equivalent patient multiplicity weights for the same frozen patient-cluster bootstrap.

## Frozen design

- fixed landmark: 12 hours after ICU admission
- prediction horizon: next 12 hours
- prevalence-preserving population cohorts
- 5-fold StratifiedGroupKFold
- grouping by source patient
- 11 frozen structured physiology/laboratory variables
- median imputation with missingness indicators
- standard scaling
- logistic regression, liblinear, C=1.0
- no class weighting or resampling
- 1,000 patient-cluster bootstrap replicates
- prespecified decision thresholds: 0.25%, 0.5%, 0.75%, 1%, 1.5%, 2%, 3%, 5%

## Primary population results

| Outcome | Prevalence | AUROC (95% CI) | AUPRC (95% CI) | Brier | Calibration intercept | Calibration slope |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Invasive ventilation | 0.983% | 0.707 (0.679–0.734) | 0.0231 (0.0187–0.0292) | 0.00972 | -0.963 (-2.496 to 0.313) | 0.783 (0.444–1.082) |
| RRT | 0.801% | 0.948 (0.936–0.958) | 0.144 (0.124–0.173) | 0.00779 | -0.072 (-0.401 to 0.251) | 0.988 (0.923–1.056) |
| ICU death | 1.084% | 0.793 (0.771–0.818) | 0.177 (0.148–0.216) | 0.00980 | -0.184 (-0.428 to 0.254) | 0.959 (0.902–1.065) |

Expected calibration error across 10 equal-frequency bins:

- ventilation: 0.00076
- RRT: 0.00399
- ICU death: 0.00314

## Decision-curve interpretation

### Invasive ventilation

Model net benefit is positive with bootstrap 95% CI excluding zero from 0.25% through 2% thresholds. At 3% and 5%, the net-benefit CI crosses zero.

Point estimates exceed treat-all at every prespecified threshold, but no paired confidence interval for the difference versus treat-all was prespecified, so this is descriptive.

### RRT

Model net benefit is positive with bootstrap 95% CI excluding zero at every prespecified threshold from 0.25% through 5%.

Point estimates exceed treat-all at every prespecified threshold.

### ICU death

Model net benefit is positive with bootstrap 95% CI excluding zero at every prespecified threshold.

At 0.25%, treat-all has a slightly higher point net benefit than the model. At thresholds of 0.5% and above, the model point estimate exceeds treat-all.

## Frozen interpretation

The prevalence-preserving analysis resolves the prior calibration limitation for the structured benchmark:

- RRT is strongly discriminative and close to ideal calibration at the 12-hour landmark.
- ICU death has moderate-to-strong discrimination with calibration intercept and slope compatible with 0 and 1, respectively.
- Ventilation has weaker discrimination and materially greater calibration uncertainty, consistent with a harder early prediction problem.

Decision-curve results support potential utility over clinically low risk thresholds for all three outcomes, but they are exploratory and do not prescribe treatment thresholds.

## Guardrails

- these are structured-only results;
- no semantic or lexical features were used;
- row-level predictions remain local;
- no landmark, threshold, or model change may be made in response to these results;
- any narrative extension must be frozen prospectively and preserve the full population, including rows without eligible notes.
