# OSF registration approval and attachment verification

Date: 2026-09-28

Registration: https://osf.io/ahxn9  
DOI: 10.17605/OSF.IO/AHXN9

## Approval state

The investigator confirmed that the OSF registration page displays the record as a public, frozen, non-editable registration. The DOI shown by OSF is `10.17605/OSF.IO/AHXN9`.

The exact approval timestamp was not available from the supplied evidence. The repository therefore records the approval state and the time at which approval was observed, not an invented approval time.

## Frozen-registration attachment verification

The investigator downloaded the three files directly from the frozen registration `ahxn9` and uploaded those copies for verification. Direct SHA-256 calculation produced:

- `OSF_v2_1_SAP.pdf`: `cf770e9cfe821ecc5250587fc29d6be404ffe3ecbf5324a0390e4061e25f4db4`
- `OSF_v2_1_Technical_Appendix.pdf`: `ebfa97ca32ae0c653bb075457acf7c3ea95eebe69ec1b5af3f6313de07aad6dd`
- `v2_1_registration_manifest.json`: `22ac9f815309d81ebf03d279087848e33f8c0a16b563efe8af114a196194fc7d`

These are the authoritative byte hashes for the files stored in the frozen OSF registration.

## Difference from the earlier local package

Before OSF submission, the locally generated package recorded:

- SAP PDF: `6532a5a72cd2ac6c3096c2a4d858c3f7106da9d4f7f2f1cbfd724a3384a415bc`
- Technical appendix PDF: `f67c156e3041b7cd2fcbd56f337346d20869e950d0605cb034e174f16ea96668`
- Manifest: `22ac9f815309d81ebf03d279087848e33f8c0a16b563efe8af114a196194fc7d`

The two PDF byte hashes differ from the frozen OSF copies. The manifest is byte-identical.

The frozen OSF copies are authoritative for the registration record. The earlier local PDF hashes remain preserved only as pre-upload package provenance. This difference is not treated as a scientific deviation because the registered files themselves are the binding record and their visible scientific content matches the submitted v2.1 SAP/technical-appendix plan.

## Remaining lock

Real-label v2.1 execution remains locked until the submitted OSF form text is imported verbatim into `docs/registration/osf_form_addendum_v2_1.md`, verified against the registration, and the resulting exact commit passes the synthetic/static preregistration validator.
