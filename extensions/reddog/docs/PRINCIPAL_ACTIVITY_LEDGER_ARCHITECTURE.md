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

## On-device / principal-possession rule

The storage root is supplied by the host application and is expected to be private app/device storage. The ledger:

- has no network client and no remote transport path;
- requires a caller-supplied 32-byte encryption key;
- never persists that key;
- separates principals by a one-way principal digest;
- encrypts event payloads with AES-256-GCM;
- stores only encrypted payloads plus minimum integrity metadata;
- uses an append-only hash chain so mutation/reordering fails closed;
- can build a decrypted context packet only inside the trusted local caller.

A mobile host should keep the key in platform secure storage (for example device keychain/keystore backed by hardware where available). Sync/export is **not** implicit. Any future sync lane must be separately governed, end-to-end encrypted for the principal, auditable, and opt-in.

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

`PrincipalActivityLedger.context()` creates a bounded local packet containing recent matching events and unresolved commitments. This is the seam by which 0102/RedDog can answer:

- what did 012 do today?
- what changed for this FoundUp?
- who was involved?
- what was promised?
- what remains open?

The context packet is not automatically sent anywhere. The host decides which local reasoning/runtime receives it and applies existing RedDog disclosure/redaction policy before any external boundary.

## Integration order

1. **Now:** local encrypted event ledger + integrity verification + bounded context projection.
2. **Next:** RedDog/AutoPost mobile capture adapter producing normalized activity events.
3. Contact Memory entity resolution consumes the same event/evidence refs.
4. Breadcrumb emitter turns project-material events into FoundUp Breadcrumbs without duplicating evidence.
5. Brain/Memex consolidates open commitments/current state from PAL/Breadcrumb projections.
6. Mosh Pit renders governed history views.
7. Optional multi-device sync only after a separate principal-controlled E2EE protocol and deletion model are reviewed.

## What this slice does not claim

This alpha does not yet wire phone capture, OCR, voice transcription, Contact Memory entity resolution, Breadcrumb emission, Memex mutation, Mosh Pit UI, secure-element key provisioning, backup, or multi-device synchronization. Those remain separate integration slices.
