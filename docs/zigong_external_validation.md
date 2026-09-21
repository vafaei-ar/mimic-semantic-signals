# Zigong external validation

## Why Zigong

The Zigong Fourth People's Hospital critical-care infection database is the first
external-validation target for the semantic-vital-sign project.

The external analysis is intentionally frozen to the MIMIC-III primary question:

- endpoint: first vasopressor initiation within 6 hours;
- semantic constructs: unchanged eight-dimensional schema;
- primary comparison: structured physiology vs semantic features vs combined;
- explicit vasopressor language excluded from the note input;
- patient-level separation between model-development/evaluation units.

## Important data-specific differences

The Zigong database contains 2,790 adult ICU patients with infection from 2019-2020.
Times are represented as hours relative to hospital admission.

The nursing-chart table contains:
- Chinese bedside progress notes;
- vital signs and other structured nursing measurements;
- high-granularity critical-care events.

The medication table represents physician orders/prescriptions. The source publication
explicitly warns that a prescribed drug may not actually be administered; actual
administration may instead appear in the nursing chart. Therefore the external
vasopressor endpoint must be based on the nursing-chart evidence of administration
where possible, not on prescription time alone.

## First local step

After credentialed PhysioNet access and download, run the inventory against either
the version directory or any parent directory that contains `DataTables.zip`.
If the CSVs are still zipped, the script extracts the archive locally into an
`_inventory_extracted` subdirectory before scanning.

Example for wget's default recursive layout:

    python src/30_inventory_zigong.py \
      --root ~/datasets/zigong/physionet.org/files/icu-infection-zigong-fourth/1.1 \
      --output outputs/zigong_external/inventory.json

The inventory is safe to share: it contains table/column metadata and aggregate
counts, but no progress-note text or patient identifiers.

Do not upload the raw Zigong CSV files or derived files containing Chinese progress
notes to GitHub or external services.
