# Enhanced structured baseline discovery audit lineage note

Updated: 2026-09-24

The first two discovery runs are preserved for provenance but are not valid for freezing feature availability.

- `S8R3V6Q4`: dictionary candidates and raw item labels are usable, but availability fractions used the wrong denominator.
- `V6R9Q3M4`: the denominator bug was fixed, but the script deduplicated ICU stays across outcomes before event scanning. This caused shared ICU stays to be assigned only to the first outcome and invalidated outcome-specific availability counts/fractions.

The corrected audit code preserves `outcome` in the deduplication key. Exact feature mappings must not be frozen until a clean run from this corrected code is terminal and reviewed.
