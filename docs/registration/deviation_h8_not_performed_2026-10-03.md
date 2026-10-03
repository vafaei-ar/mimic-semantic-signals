# Registered H8 deviation: clinician construct validation not performed

Date: 2026-10-03  
Registration: OSF ahxn9, DOI 10.17605/OSF.IO/AHXN9

## Registered plan

The v2.1 SAP prespecified blinded clinician construct validation of the eight semantic constructs using independent human raters. The registered analysis included inter-rater reliability, same-construct model-human agreement, cross-construct discrimination, and association with clinician-rated deterioration probability.

## Work completed before the deviation

The computational preparation was completed without outcome-label or model-score access. RunRelay job `D8K5W3R7` froze a uniform random 200-note sample from the 7,889-note MetaVision ICU-death stripped-note corpus using seed 20261003 and generated three blinded local rater packets.

No human ratings were collected.

The shared preparation artifact is:

- `outputs/multitask_benchmark/h8_clinician_validation_preparation_v2_1.json`
- SHA-256 `9324d00459693fa7ebec8bffbe2a1143be227757ea91110116375646b007cd8f`

## Deviation

H8 clinician annotation will not be performed for Paper 1.

Reason: this is a single-author, unfunded study and the required independent qualified clinician raters and associated governance/logistical resources are not available. No rating result exists, so this decision was not made in response to H8 performance.

The frozen sample and packet hashes remain in the repository as provenance. Restricted note packets remain local.

## Consequence for interpretation

The manuscript must not claim clinician-validated construct validity or clinical interpretability of the eight semantic scores.

Lack of human construct validation must be reported as a limitation and future-work need.

H8 is removed from the submission-critical path. No attempt will be made to replace independent clinician ratings with synthetic raters or model-generated ratings for the main paper.
