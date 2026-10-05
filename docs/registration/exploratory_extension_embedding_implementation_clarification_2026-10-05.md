# Exploratory extension implementation clarification: frozen BGE cache

Date frozen: 2026-10-05  
Branch: `extension-v2_1`  
Parent protocol: `docs/registration/exploratory_extension_protocol_v2_1_2026-10-04.md`

This label-free implementation clarification is frozen before any T1.2 or T1.2b outcome evaluation. It does not change the frozen model, model revision, representation, chunk size, overlap, pooling rule, or downstream analysis.

## Exact chunk encoding path

The frozen model is `BAAI/bge-large-en-v1.5` at revision `d4aa6901d3a41ba39fb536a557fa166f842b0e09`, loaded only from the local Hugging Face snapshot with network access disabled.

For each frozen stripped note:

1. tokenize the note with the frozen model tokenizer using `add_special_tokens=False`;
2. split the resulting content-token IDs into windows of exactly 448 tokens with 64-token overlap (step size 384), allowing a shorter final window;
3. decode each token window with the same frozen tokenizer using `skip_special_tokens=True` and `clean_up_tokenization_spaces=False`;
4. encode the decoded window text through the frozen SentenceTransformers pipeline with no query/task prefix and `normalize_embeddings=True`;
5. average the normalized chunk embeddings with equal weight;
6. L2-normalize the document-level mean vector;
7. store the resulting 1024-dimensional float32 document vector locally.

The decode/re-encode step is used because the frozen SentenceTransformers `encode` API is string-based while the protocol freezes chunk boundaries in tokenizer-token space. No alternative tokenizer, model, pooling scheme, weighting scheme, or prompt is compared.

## Cache and privacy contract

- The cache contains only `case_id` and the 1024-dimensional document embedding.
- Row-level embeddings remain on the bound workstation and are never declared as RunRelay artifacts.
- The shared cache report contains only aggregate counts, shapes, and cryptographic hashes.
- No outcome label is read while generating the cache.
- T1.2/T1.2b downstream supervised fitting remains exactly as specified in the parent protocol.
