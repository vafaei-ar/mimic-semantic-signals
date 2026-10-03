# v2.1 registered H8 clinician construct-validation preparation status

Updated: 2026-10-03

H8 human construct validation is not yet complete. This document records the frozen preparation state only.

## Frozen sample

Preparation job `D8K5W3R7` completed at corrected project commit `fbeb6297ea82cf20555726c0eef1909151145368`.

The preparation:

- used the registered MetaVision ICU-death language-stripped corpus;
- sampled 200 notes uniformly without replacement from 7,889 frozen note rows;
- used seed `20261003`;
- generated three blinded local rater packets;
- had all three primary raters assigned to rate all 200 notes in independent randomized order;
- did not read outcome labels;
- did not read model scores;
- did not compute predictive performance;
- shared no note text, identifiers, or row-level restricted data.

Shared preparation artifact SHA-256: `9324d00459693fa7ebec8bffbe2a1143be227757ea91110116375646b007cd8f`.

## Governance gate

Human annotation may not begin until the local governance gate documents:

- the applicable Penn State IRB determination;
- applicable PhysioNet/MIMIC authorization for all three primary raters.

The restricted note packets remain local and are not RunRelay artifacts.

## Next registered action

After the governance gate is documented and all three blinded rating files are complete, run the frozen manual task `evaluate_h8_clinician_validation_v2_1`.

Until that occurs, no H8 agreement or construct-validity result exists and none should be inferred from the sample preparation.
