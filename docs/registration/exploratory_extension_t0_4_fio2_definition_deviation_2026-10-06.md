# Exploratory extension T0.4 clarification: missing frozen FiO2 step-up definition

Date: 2026-10-06  
Branch: `extension-v2_1`  
Parent protocol: `docs/registration/exploratory_extension_protocol_v2_1_2026-10-04.md`

## Problem identified before T0.4 execution

The frozen extension protocol states that the T0.4 respiratory pair should include a "FiO2 increase" defined as the first FiO2 step-up under the "frozen alignment-audit definition."

Repository and project-record review found that no such FiO2 transition definition was ever frozen:

- the prior semantic alignment audit (`src/159_audit_semantic_alignment_v2_1.py`) uses the contemporaneous field `treat_fio2_last_6h` only;
- it defines no FiO2 change threshold, no step-up episode, and no six-hour transition washout;
- the context freeze defines FiO2 cleaning/normalization to percent but does not define a clinically meaningful increase threshold.

Therefore the parent protocol contains a dangling reference rather than an executable frozen definition.

## Resolution

No T0.4 support-timing result has been computed or inspected.

To avoid selecting a FiO2 threshold after other extension results are known, the FiO2-transition arm is **not implemented from an invented threshold**. It is recorded as not executable as written unless an exact pre-existing, time-stamped definition can be recovered from project provenance.

T0.4 may proceed for the three transition pairs whose support states have explicit source definitions:

1. hemodynamic concern / vasoactive start;
2. respiratory concern / high-flow start;
3. respiratory concern / NIV start.

For these three pairs, the parent protocol is unchanged:

- a qualifying transition is the first support start after at least 6 hours without that support;
- prior transition = most recent qualifying transition in the 12 hours before note storetime;
- subsequent transition = first qualifying transition in the 12 hours after note storetime;
- categories = prior only, subsequent only, both, neither;
- top/bottom construct-score quartiles come from score distribution only;
- patient-shuffled scores use the existing between-patient shuffle logic;
- ongoing support at note storetime is reported by score quartile;
- interpretation remains descriptive, not predictive.

## Reporting

The final extension report and supplement must state that the FiO2 T0.4 arm was not performed because the protocol referenced a nonexistent frozen transition definition. This is an implementation/provenance deviation, not a scientific result.

No threshold may be selected later based on observed T0.4 patterns.
