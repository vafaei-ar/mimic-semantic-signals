# Post-registration pre-inference clarification: Open-Jev question packing

Date: 2026-09-28

## Status

This clarification was recorded **before any v2.1 semantic inference result was generated or viewed**.

The approved OSF registration freezes:

- Open-Jev model `com-kotobalabs/open-jev-deberta-v3-large`;
- revision `19bf9a64815add579fbf6c907bef584d9277a8e4`;
- typed-decisions commit `10d7834d3b99041f890db4615fb38ef95ced50cc`;
- 220-token chunks;
- 40-token overlap;
- at most 8 chunks;
- the frozen semantic schema;
- maximum-across-chunks aggregation except minimum for `reassuring_stability`.

The registration does not specify how many construct questions are passed to Open-Jev in one model call.

## Frozen implementation detail

The existing pre-registration Open-Jev implementation in `src/22_run_open_jev_real_local.py` uses:

- maximum requested questions per pack: **4**;
- greedy context-safe packing;
- automatic reduction of pack size when required by the model context.

The v2.1 registered runner retains this existing implementation unchanged.

This is an execution clarification, not a change in the construct definitions, note corpus, model, model revision, chunking, aggregation, outcome, comparator, or inferential procedure.

The v2.1 runner additionally resolves the exact registered Hugging Face snapshot locally and verifies the installed typed-decisions git commit before reading the frozen note corpus.
