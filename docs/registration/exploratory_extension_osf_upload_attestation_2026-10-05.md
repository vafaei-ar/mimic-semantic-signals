# OSF exploratory-extension upload attestation

Date: 2026-10-05  
Branch: `extension-v2_1`  
OSF project: `wmyb2`  
Frozen addendum: `docs/registration/exploratory_extension_addendum_2026-10.md`

Before any new extension task was allowed to read outcome labels, the user explicitly confirmed in the authoritative Medical JEV project conversation that the frozen exploratory-extension addendum had been uploaded to OSF.

A subsequent unauthenticated public-API verification attempt (RunRelay job `S4M8K2V7`) returned HTTP 401 for the project file endpoint. Therefore the project/file was not independently readable without OSF authentication from the runner. This does not alter the user's upload attestation; it means the runner cannot independently retrieve the OSF timestamp or byte-compare the private file.

No extension outcome-label analysis was executed before this attestation was recorded. The committed addendum and operational protocol remain the authoritative frozen analysis specification.

If the OSF project/file is later made publicly readable, the public metadata and file hash should be added to this record without changing the pre-analysis protocol.
