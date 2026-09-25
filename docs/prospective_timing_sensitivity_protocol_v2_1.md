# Prospective timing sensitivity protocol v2.1

Status: **prespecified before corrected v2.1 predictive performance is opened**.

Purpose: test whether structured/narrative results depend on using clinical event timestamps that precede actual documentation/result availability.

## Primary continuity analysis

The v2.1 primary structured extraction keeps the established MIMIC convention:

- CHARTEVENTS selected by charttime;
- LABEVENTS selected by charttime/specimen time;
- NOTEEVENTS availability = max(charttime, storetime) when storetime exists, otherwise charttime.

This primary is retained for continuity with standard MIMIC feature construction.

## Sensitivity A — CHARTEVENTS storetime

For CHARTEVENTS features:

- charttime must remain within the frozen lookback window;
- when storetime is present, require storetime <= landmark;
- rows stored after the landmark are excluded.

Where storetime is unavailable, report the missing-storetime fraction and keep those rows only in the primary analysis unless a separate conservative fallback is prespecified.

## Sensitivity B — laboratory result lag

Because MIMIC-III LABEVENTS does not provide a direct universal result-release timestamp suitable for all tests, use fixed availability-lag sensitivities:

- 1-hour lag: effective availability = charttime + 1 hour;
- 2-hour lag: effective availability = charttime + 2 hours.

A laboratory value is eligible only if its effective availability is at or before the landmark.

All item mappings and lookback windows remain unchanged.

## Sensitivity C — note availability

Primary note availability remains:

- max(charttime, storetime) when storetime exists;
- charttime fallback otherwise.

Report separate sensitivities:

1. storetime-available notes only;
2. conservative charttime-fallback delay for notes without storetime.

The fallback delay should be frozen before outcome-performance inspection.

## Interpretation

If a semantic/text increment appears only under optimistic timing but disappears under conservative availability timing, manuscript language must state that the result depends on timestamp assumptions.

If structured performance falls materially under conservative timing, semantic increments must be compared against that timing-matched structured baseline rather than against the optimistic baseline.

## Guardrails

- do not change cohort labels in timing sensitivities;
- do not select delay values by performance;
- reuse the same patient-grouped split hashes;
- keep row-level timing data local;
- report aggregate availability loss before reporting predictive changes.
