# MIMIC Semantic Signals

> **Current project status (2026-09-24):** The project has progressed well beyond reconnaissance. We now have frozen single-outcome and multi-outcome semantic benchmarks, supervised text-learning comparisons, structured external transport to eICU/NWICU, cross-language narrative transport to Zigong, and a prevalence-preserving population calibration branch. The active analysis is the full-population semantic extension. See [docs/project_status_lancet_digital_health.md](docs/project_status_lancet_digital_health.md) for the current scientific findings, limitations, and prioritized path toward a Lancet Digital Health submission.

Detailed protocol and result-freeze documents under `docs/` are authoritative. The historical reconnaissance material below is retained for provenance.

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


## Second-pass reconnaissance

After `recon_v1`, run:

```bash
git pull

python run_reconnaissance_v2.py \
  --root ~/datasets/MIMIC/physionet.org/files \
  --output outputs/recon_v2
```

Send back:

```text
outputs/recon_v2/mimic_feasibility_results_v2.zip
```

The second pass answers two specific questions:

1. Are **actual narrative clinician notes** (physician, nursing, respiratory, general, consult) present often enough before deterioration, independent of radiology coverage?
2. Are the preliminary vasopressor/intubation event definitions clinically defensible, or did broad text matching pull in inappropriate `D_ITEMS` labels?

## MIMIC + external model APIs

Do not send raw MIMIC text to Jev or any other external API unless the service configuration has been verified to satisfy the current PhysioNet requirements for credentialed data, including zero data retention, no training use, and no human review where required. Until that is established, semantic-model experiments in this repository should remain local.


## Synthetic development sandbox

While third-party retention requirements are being resolved, development can proceed using a schema-faithful synthetic MIMIC-III subset.

Run:

```bash
git pull

python run_synthetic_demo.py \
  --output-root data/synthetic_mimic \
  --n-admissions 500
```

Then verify the generated table headers against the exact locally downloaded MIMIC-III files:

```bash
python synthetic/validate_against_local_headers.py \
  --real-root ~/datasets/MIMIC/physionet.org/files \
  --synthetic-root data/synthetic_mimic \
  --output outputs/synthetic_schema_check.csv
```

The synthetic data contain a controlled latent clinician-concern signal, including narrative-physiology discordant cases, so the semantic pipeline can be developed and tested against known ground truth before any real clinical text is processed by an external service.

See `synthetic/README.md` for details.
