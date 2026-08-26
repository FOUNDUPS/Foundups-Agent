# Assumption Audit: RedDog Resident First-TURN Resolution Phase 1

## 1. Problem and allocation

- **What**: durably bind one exact empty-ID resident `TURN` to its authenticated
  E0 conversation ID and revision 0 before any handler can run.
- **Why**: scope-only persistence could not prove which original envelope
  resolved to the returned ID; rewriting it into journal v1 would falsify the
  request digest.
- **WSP 15**: complexity `4`, importance `5`, deferability `4`, impact `5`;
  total `18 / P0`.
- **Smallest layer**: resolution plus journal binding only. Host traffic,
  operation handlers, conversation CAS, response delivery, models, and workers
  remain separate.

## 2. Retrieval evaluation

The governed Holo owner query was attempted once and failed closed with
`HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH`: authority HEAD
`e656fd76fe906b3f3f860642b30ca47d685f9ce2`, workspace HEAD
`4c3e2f7d22e209ec5a548deeadb6b99e79457724`, freshness `UNKNOWN`,
`index_gap_detected=true`, and zero owner attempts. No retry, raw query,
reindex, route repair, activation, or Holo mutation was performed.

Because no result set was admitted, noise and ordering are unmeasured. Exact
local source, tests, navigation, module docs, and prior clarity audits were the
must-include retrieval set. The module has no `memory/README.md` or
`requirements.txt`; their absence is recorded rather than silently inferred.

## 3. Assumptions and falsification

| Assumption | Evidence | Verdict |
|---|---|---|
| Journal v1 can store the rewritten request unchanged. | Its `request_digest` must describe its own ID/revision fields. | FALSE; explicit v2 kind and source digest are required. |
| One verified authority can be copied or reopened for create and journal. | Authorities are opaque and one-use; two leases introduce generation/credential TOCTOU. | FALSE; one root atomically delegates two registered FoundUp siblings. |
| Idempotency key lookup may discover the resolved ID. | The key is client-supplied and the ID is authenticated identity. | FALSE; derive the ID after authentication, then require all four row identities. |
| Replay requires the scope to remain at revision 0. | The signed record retains a validated immutable receipt chain. | FALSE; later revisions may replay only when receipt 0 exactly matches the stored link. |
| Rehashing every journal field authenticates a changed idempotency identity. | Journal digests are unkeyed and therefore prove integrity, not origin. | FALSE; signed immutable E0 state must commit the exact source/resolved request pair. |
| Viewing then retiring one replay authority is one-use under concurrency. | Two callers can view the same registered seal before either retires it. | FALSE; replay must atomically pop and verify the seal. |
| A separate link table is simpler. | The journal already owns uniqueness, capacity, locking, corruption checks, and recovery. | FALSE; reuse it with an explicit schema. |

## 4. Decision and failure model

`reddog_resident_conversation_request_reservation.v2` with
`reservation_kind=RESOLVED_INITIAL_TURN` is stored in the existing journal.
`source_request_digest` covers the original empty-ID/-1 envelope;
`request_digest` covers the derived nonempty-ID/revision-0 envelope. The
reservation ID covers every immutable v2 field.

Authenticated conversation-scope schema v4 stores the exact source/resolved
request-pair commitment as immutable signed E0 state. The journal repeats that
commitment, but the signed scope is the authority: changing idempotency or any
other request identity and rehashing the complete row cannot replay.

The aggregate prevalidates request, intent, grounding, and registered FoundUp
before credential use. One current-generation lease retires its root into two
distinct FoundUp children. The primary creates or exactly recovers E0. The
secondary verifies that exact signed E0 record and mints the journal child.
The journal rechecks scope revision, record digest, initial receipt, expiry,
capacity, and uniqueness under its backend write lock.

If scope persistence succeeds and journal persistence fails, the scope remains
content-minimized and a retry exactly recovers it before inserting the row. A
scope change before insertion fails closed. Replay authenticates first,
derives the ID, loads only an exact conversation/idempotency/request/nonce row,
verifies current signed scope identity and expiry, and checks receipt zero,
including its empty predecessor, initial state digest, and signed request
commitment. Replay atomically pops and verifies the one-use scope authority;
corrupt, forged, divergent, expired, unavailable, duplicate, or ambiguous state
returns no authority.

## 5. Current boundary

This phase is transport-neutral and uses the existing SQLite/PostgreSQL
AgentDB locking contract. It does not expose a host endpoint, run a first-turn
handler, reserve conversation CAS, invoke a model, dispatch OpenClaw/Hermes,
mutate a repository, or maintain HoloIndex. The next independent WSP 15 gate is
host invocation plus immediate authenticated operation CAS.
