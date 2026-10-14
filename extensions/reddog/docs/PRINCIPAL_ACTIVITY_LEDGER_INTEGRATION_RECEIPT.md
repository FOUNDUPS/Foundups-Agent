# Principal Activity Ledger Integration Receipt

PR: #1638
Branch: `feat/reddog-principal-activity-ledger`

## Executable closure

- `extension.js` already activates `principal_memex_disclosure_source.registerCommands(...)`.
- `principal_memex_disclosure_source.js` now registers `principal_activity_extension_adapter` commands.
- `principal_activity_extension_adapter.js` binds RedDog to `principal_activity_ledger.js`.
- `package.json` declares activation and command contributions for capture/context/status.
- package surface contracts include both PAL runtime files.
- fast-tier plan includes PAL ledger, adapter and registration contract tests.

## Storage boundary

- Activity records: extension-local `globalStorageUri/principal-activity-ledger/...`
- Encryption: AES-256-GCM
- Key: VS Code SecretStorage only; not stored beside the ledger
- Network transport: none in PAL/adapter
- Git: mechanism only; no principal activity data

## Authority boundary

A local context packet is not external disclosure authority. Any cloud/model/network egress remains subject to a separate governed disclosure/redaction path.

## Remaining slices

Automatic capture from every RedDog turn, phone capture, AutoPost intake, OCR/voice extraction, Contact Memory entity resolution, Breadcrumb emission, Brain/Memex projection, Mosh Pit rendering, backup, and multi-device E2EE sync remain separate implementation slices.
