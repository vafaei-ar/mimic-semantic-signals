# MIMIC Semantic Signals

This repository evaluates whether MIMIC can support publishable studies of **semantic clinical signals** before any Jev or LLM modeling is performed.

The first milestone is a local, privacy-preserving reconnaissance run over available MIMIC modules. It compares four candidate scientific directions:

1. **Semantic vital signs before deterioration** using longitudinal MIMIC-III notes.
2. **Hidden clinician concern / narrative-physiology discordance** using MIMIC-III notes plus structured physiology.
3. **Unresolved-care phenotype at discharge** using MIMIC-IV discharge summaries plus later ED/hospital utilization.
4. **Narrative-measurement discordance in cardiology** using MIMIC-IV ECG/echo/core data.

## Design rule

The reconnaissance scripts read patient-level MIMIC locally, but the export bundle is restricted to aggregate schemas, counts, overlaps, timing coverage, and feasibility summaries. The code does not intentionally export raw note text, `subject_id`, `hadm_id`, or `stay_id`.

## Expected local layout

```text
~/datasets/MIMIC/physionet.org/files/
├── mimiciii
├── mimiciv
├── mimic-iv-note
├── mimic-iv-ed
├── mimic-iv-ecg
├── mimic-iv-echo
└── mimic-cxr
```

Version subdirectories are discovered recursively.

## Setup

```bash
git clone https://github.com/vafaei-ar/mimic-semantic-signals.git
cd mimic-semantic-signals

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python run_reconnaissance.py \
  --root ~/datasets/MIMIC/physionet.org/files \
  --output outputs/recon_v1
```

The runner continues when an optional module is unavailable and records failures in the manifest.

## Main outputs

```text
outputs/recon_v1/
├── inventory.csv
├── inventory_summary.json
├── linkage_matrix.csv
├── linkage_details.csv
├── note_categories.csv
├── note_timing_summary.csv
├── candidate_outcomes.csv
├── outcome_event_counts.csv
├── outcome_itemid_discovery.json
├── pre_event_coverage.csv
├── pre_event_coverage_by_category.csv
├── discharge_followup.csv
├── cardiac_linkage.csv
├── candidate_feasibility.csv
├── feasibility_report.md
├── run_manifest.json
└── mimic_feasibility_results.zip
```

### What the first run tests

- Whether MIMIC-III has enough precisely timed notes before hard deterioration events at 6, 12, 24, and 48 hours.
- Whether vasopressor and intubation events can be discovered from the local MIMIC-III release using `D_ITEMS` labels rather than assumed item IDs.
- Whether MIMIC-IV discharge summaries have enough observable 7- and 30-day subsequent hospital/ED use for an unresolved-care phenotype study.
- Whether ECG, echo, core EHR, and notes overlap at a scale that could support narrative-measurement discordance analyses.

## What to send back

Send only:

```text
outputs/recon_v1/mimic_feasibility_results.zip
```

That archive is intended to contain aggregate reconnaissance outputs only.

## Next phase

We will inspect the reconnaissance results and select the strongest one or two scientific questions. Only then will we define semantic constructs, run a small Jev/LLM comparator pilot, and plan human validation.

**Current stage: reconnaissance only. No model has been selected and no study hypothesis is locked.**
