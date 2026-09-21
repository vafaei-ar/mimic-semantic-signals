# External data portfolio for Semantic Vital Signs

Updated: 2026-09-20

This document freezes the external-data acquisition plan before additional model
development. Raw credentialed datasets must remain local and must not be committed
to GitHub.

## Roles

### Narrative external validation

1. Zigong Fourth People's Hospital critical care infection database v1.1
   - PhysioNet slug: icu-infection-zigong-fourth
   - Status: downloaded locally
   - Strength: Chinese bedside nursing narratives plus structured ICU data
   - Main issue: nursing-chart and HIS medication clocks require harmonization
   - Role: primary cross-language narrative external validation if timing can be
     resolved defensibly.

### Structured endpoint/physiology validation

2. eICU Collaborative Research Database v2.0
   - PhysioNet slug: eicu-crd
   - >200,000 ICU admissions across many US hospitals
   - Credentialed access + DUA
   - Strong multicenter structured validation.
   - Free-text narrative notes are not available in the released database.

3. Northwestern ICU (NWICU) v0.1.0
   - PhysioNet slug: nwicu-northwestern-icu
   - Northwestern Memorial HealthCare, Chicago
   - Credentialed access + DUA
   - MIMIC-like schema: admissions, labs, prescriptions/eMAR, ICU stays,
     charted events and procedures
   - Strong independent US health-system validation.

4. MIMIC-BR v1.0.1
   - PhysioNet slug: mimic-br
   - 28,799 adult patients from Einstein Hospital Israelita, Brazil
   - Contributor-review access
   - OMOP-derived structured ICU data
   - drug_exposure includes medication prescriptions/administrations, including
     vasoactive drugs and continuous infusions with precise timing
   - No free-text clinical notes in the current release.
   - Strong cross-country structured endpoint and physiology validation.

5. HiRID v1.1.1
   - PhysioNet slug: hirid
   - Bern University Hospital, Switzerland
   - ~34,000 ICU admissions with very high time resolution
   - Contributor-review access
   - Excellent circulatory-failure/physiology validation; no narrative notes.

6. SICdb v1.0.8
   - PhysioNet slug: sicdb
   - University Hospital Salzburg, Austria
   - ~27,350 ICU admissions
   - Contributor-review access
   - Vitals, labs, therapies and medications; structured-only external validation.

7. AmsterdamUMCdb v1.5.0
   - Amsterdam UMC, Netherlands
   - 23,106 ICU/HDU admissions
   - Access requested outside PhysioNet through Amsterdam Medical Data Science
   - Current release is OMOP CDM 5.4.
   - Legacy freetextitems are categorical/non-numeric observations rather than
     bedside narrative progress notes.
   - Structured European validation.

## Download directory convention

    ~/datasets/external_icu/
      eicu/
      nwicu/
      mimic_br/
      hirid/
      sicdb/
      amsterdamumcdb/
      zigong/

## PhysioNet download helper

Use the repository helper:

    bash scripts/download_external_physionet.sh DATASET PHYSIONET_USERNAME

Examples:

    bash scripts/download_external_physionet.sh eicu vafaeisa
    bash scripts/download_external_physionet.sh nwicu vafaeisa
    bash scripts/download_external_physionet.sh mimic-br vafaeisa
    bash scripts/download_external_physionet.sh hirid vafaeisa
    bash scripts/download_external_physionet.sh sicdb vafaeisa

The helper uses --ask-password. It never stores the password.

A 401 response generally means one of:
- the username/password is incorrect;
- the project-specific DUA has not been signed;
- contributor approval is still pending.

## Acquisition priority

Immediate:
1. eICU
2. NWICU

Request contributor approval now:
3. MIMIC-BR
4. HiRID
5. SICdb

Separate access request:
6. AmsterdamUMCdb

Already downloaded:
7. Zigong

## Analysis freeze

The MIMIC-III semantic constructs and six-hour vasopressor prediction horizon are
frozen before examining external performance.

External datasets may require data-specific endpoint mappings, but they should not
be used to tune the semantic construct definitions or retrospectively optimize the
MIMIC-III model.
