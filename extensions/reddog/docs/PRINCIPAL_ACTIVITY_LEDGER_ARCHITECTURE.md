# RedDog Principal Activity Ledger

Status: `ALPHA_RUNTIME_SLICE`

## Why this exists

RedDog needs continuity for **what the principal is doing**, not only who the principal knows. Contact Memory already specifies relationship memory; Breadcrumbs specify project history; Brain/Memex specifies current state; Mosh Pit specifies history/status projection. They need one privacy-preserving event source rather than four independently reconstructed stories.

The Principal Activity Ledger (PAL) is that source for local capture. It is not a cloud memory service and it is not a new authority plane.

## Invariant

**Capture once, project many times, disclose only with separate authority.**

```text
012 action / capture / message / meeting / decision
          |
          v
local RedDog / AutoPost capture surface
          |
          v
Principal Activity Ledger (encrypted, append-only, principal-scoped)
          |
          +--> Contact Memory projection
          +--> FoundUp Breadcrumb candidate
          +--> Brain/Memex current-state projection
          +--> Mosh Pit history projection
          +--> RedDog context packet
```

PAL records evidence-backed activity locally. It does not grant posting, messaging, repository, financial, identity, biometric, or other execution authority.

## Executable RedDog binding

The alpha runtime is now part of RedDog's executable dependency and package closure:

```text
extension.js
  -> principal_memex_disclosure_source.registerCommands(...)
      -> principal_activity_extension_adapter
          -> principal_activity_ledger
```

The adapter binds PAL to VS Code extension-local storage and SecretStorage. The extension exposes three bounded commands:

- `RedDog: Capture Principal Activity (Local)` — append one encrypted local activity note;
- `RedDog: Show Principal Activity Context (Local)` — render a bounded local context projection;
- `RedDog: Principal Activity Status (Local)` — report encrypted/local/no-network state.

The package/runtime-closure contract explicitly includes both PAL runtime modules, so they cannot silently become documentation-only code while the RedDog package still passes its closure test.

This binding deliberately does **not** imply that every RedDog conversation turn, phone action, email, or external application event is automatically captured yet. Those capture adapters must explicitly call `principal_activity_extension_adapter.append()` with normalized, provenance-bearing events. This preserves the rule that capture authority and disclosure authority are separate.

## On-device / principal-possession rule

For the VS Code host, the storage root is `context.globalStorageUri` under a RedDog-specific `principal-activity-ledger` directory. The encryption key is generated once and retained only through VS Code SecretStorage. The ledger itself:

- has no network client and no remote transport path;
- requires a 32-byte encryption key supplied by the host adapter;
- never persists that key beside the ledger;
- separates principals by a one-way principal digest;
- encrypts event payloads with AES-256-GCM;
- stores only encrypted payloads plus minimum integrity metadata;
- uses an append-only hash chain so mutation/reordering fails closed;
- can build a decrypted context packet only inside the trusted local caller.

A mobile host should keep the equivalent key in platform secure storage (for example device keychain/keystore backed by hardware where available). Sync/export is **not** implicit. Any future sync lane must be separately governed, end-to-end encrypted for the principal, auditable, and opt-in.

## Event shape

The encrypted payload supports:

- event id and time;
- kind/source;
- FoundUp/project ids;
- contact/entity ids;
- commitments and status changes;
- evidence references;
- provenance-bearing facts;
- concise notes.

Raw photos/audio/documents should remain separate encrypted evidence objects and be linked by opaque evidence references rather than copied into every activity record.

## Context handoff to RedDog

`PrincipalActivityLedger.context()` creates a bounded local packet containing recent matching events and unresolved commitments. `principal_activity_extension_adapter.contextPacket()` further applies a serialized-size bound and marks the packet `local_only` with `disclosure_authority: separate_required`.

This is the seam by which 0102/RedDog can answer:

- what did 012 do today?
- what changed for this FoundUp?
- who was involved?
- what was promised?
- what remains open?

The context packet is not automatically sent anywhere. The host decides which local reasoning/runtime receives it and applies existing RedDog disclosure/redaction policy before any external boundary.

## Integration order

1. **Implemented alpha:** local encrypted event ledger + integrity verification + bounded context projection.
2. **Implemented alpha:** RedDog extension storage/key adapter + executable local capture/context/status commands + package closure tests.
3. **Next:** RedDog conversation/capture surfaces emit normalized events automatically where capture authority exists.
4. **Next:** AutoPost/mobile capture adapter supplies photos, cards, voice notes, messages and encounter receipts without exporting raw evidence.
5. Contact Memory entity resolution consumes the same event/evidence refs.
6. Breadcrumb emitter turns project-material events into FoundUp Breadcrumbs without duplicating evidence.
7. Brain/Memex consolidates open commitments/current state from PAL/Breadcrumb projections.
8. Mosh Pit renders governed history views.
9. Optional multi-device sync only after a separate principal-controlled E2EE protocol and deletion model are reviewed.

## What this slice does not claim

This alpha does not yet wire automatic phone capture, OCR, voice transcription, Contact Memory entity resolution, Breadcrumb emission, Memex mutation, Mosh Pit UI, secure-element key provisioning, backup, or multi-device synchronization. Those remain separate integration slices. It also does not authorize PAL contents to cross a network boundary merely because a context packet can be produced locally.
