# Assumption Audit: RedDog Resident Conversation Admission Aggregate Phase 1

## 1. Problem Statement

- **What**: Compose the already-verified resident request, current-generation
  signed-session, authenticated current-scope binding, and durable replay
  reservation contracts into one fail-closed host operation.
- **Why**: The individual LEGO layers were verified but a host otherwise had
  to reproduce their security-sensitive order and authority lifetime.
- **Who**: Authorized by 012; executed by `0102/architect` on 2026-08-26.

This phase is inert. It does not expose an endpoint, create a conversation,
run TURN/STATUS/CANCEL behavior, reserve conversation CAS, invoke a model,
dispatch a worker, mutate a repository, or modify HoloIndex.

## 2. WSP 15 Allocation

- Complexity `4`, importance `5`, deferability `4`, impact `5`.
- Total/priority: `18 / P0`.
- Smallest layer: one host aggregate for an existing conversation; new-scope
  resolution, handler effects, response transport, and adapters remain
  independent future layers.

## 3. Retrieval Evaluation

- The required governed Holo owner query was attempted once and failed closed
  with `HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH`.
- Query authority HEAD was
  `e656fd76fe906b3f3f860642b30ca47d685f9ce2`; workspace/base HEAD was
  `987c661427e73bc09fc3838f8c350ebf20b42a45`. Freshness was `UNKNOWN`,
  `index_gap_detected=true`, and owner attempts were zero.
- No retry, raw Holo query, reindex, replica activation, route repair, or Holo
  mutation occurred in this transaction.
- Direct must-include retrieval verified `NAVIGATION.py`, the strict transport
  request contract, session authority source, scope capability/record/store,
  existing binder, journal contract/service/store, their adversarial tests,
  and the module README/INTERFACE/ROADMAP/ModLog/test memory.
- No admitted Holo result set existed, so result noise and ordering were not
  measurable. The exact symbol graph removed duplication risk; explicit
  must-includes controlled missing-artifact risk. Staleness remains
  truth-labeled and prevents any claim of repository-wide semantic recall.

## 4. Assumptions and Falsification

| ID | Assumption | Evidence | Verdict |
|---|---|---|---|
| A1 | The production session source already consumes the root capability. | It yields one registered `VerifiedConversationScopeAuthority` under the current-generation lease. | VERIFIED |
| A2 | Reusing the root-capability binder would be safe. | It would require a second consumption that the session cannot supply. | FALSE; authority-native sibling added |
| A3 | Public fields on `VerifiedResidentConversationSession` prove identity. | The dataclass is constructible; only the private registry-backed authority view and signed record verifier are trusted. | FALSE; fields are ignored |
| A4 | Verification followed by `finally` retirement is one-use under concurrency. | Two coordinated callers both minted children before either `finally` ran. | FALSE; issuance and parent pop made atomic |
| A5 | The journal child can outlive atomic parent retirement for this request. | It is separately registered, one-use, exact-record-verified, canonical-reservation-bound, and consumed at the store boundary. | VERIFIED |
| A6 | Aggregate success authorizes handler execution. | The result explicitly grants no identity/effect/CAS authority and no handler is called. | FALSE |
| A7 | Every typed source error is safe to return. | The exception class accepts arbitrary text even though current production raises fixed reasons. | FALSE; exact allowlist added |
| A8 | Exact request type guarantees safe field access. | An uninitialized exact-class instance raised during preflight. | FALSE; total exception boundary added |
| A9 | E0 record signature plus FoundUp scope equates the record to the popped parent. | The E0 signer is service-level; a valid record from `window:one` initially minted a child under a `window:other` parent. | FALSE; full record/seal identity equality added |

## 5. Failure Modes

| Failure | Mitigation |
|---|---|
| Malformed, expired, future, or new-scope request consumes a credential. | Strict request/freshness/new-scope preflight runs before the lease. |
| Directly allocated, stale, or cross-session opaque authority is accepted. | Registry-backed authority plus exact signature and full record/seal principal/session/credential/repository equality are mandatory inside the atomic pop. |
| Authority from another principal/session/scope is transplanted. | `authority_matches()` binds all current identity, session, repository, and authentication fields. |
| Generation changes during persistence. | The current-generation lease encloses binding and journal completion. |
| Concurrent callers use one verified parent. | Atomic registry pop plus exact-record verification issues at most one child. |
| Journal or unexpected dependency fails. | Existing stable journal rejection or one aggregate unavailable reason; no exception detail is returned. |
| Credential/operator/principal data enters storage or result. | Only opaque digests and the content-free reservation contract cross the boundary. |

## 6. Decision Record

- **Decision**: PROCEED with the bounded inert aggregate.
- **Reuse**: Existing request validation, current-generation authority source,
  authenticated scope verifier, atomic reservation-child issuance, and durable
  journal are composed without parallel security implementations.
- **Scale boundary**: The aggregate is transport-neutral and AgentDB-backed;
  horizontal journal locking remains in the existing store. It does not claim
  horizontally scalable handlers, streaming, or multi-host event delivery.
- **Next**: trusted new-scope selection, host invocation wiring, and separate
  operation-specific handlers with immediate authenticated CAS.

## 7. Verification Record

- Repaired focused binder/journal/aggregate matrix: `51 passed`; broader
  binder/journal-store/session-source matrix: `72 passed`.
- Ruff and Python compilation: pass.
- WSP 62: both changed production modules are at most 500 lines and every
  function is at most 50 lines; no exemption was added.
- Adversarial cases cover pre-lease rejection, exact lease parameters,
  restart replay, direct opaque allocation, cross-session transplant, atomic
  sequential/concurrent parent consumption, typed/unknown source failures,
  malformed exact-type requests, pre-lease freshness rejection, lease lifetime
  through persistence, journal failure, disclosure, and absence of effect wiring.
- Fresh-context independent WSP 00/WSP 97 exact-byte review: **GO**, `36
  passed`; no requested correctness invariant remained unproven.
- Canonical test registry: `1,580` entries / `268` quarantined and current.
- Generated backend closure: `1,383` files, canonical digest
  `5d8ef0cf64ffc12c4a8dda5fef6259653791e91e5824b7baba815bdfccb5feea`;
  generator/staged parity matrix: `36 passed`.
- Release validation and deterministic package proof remain required before
  merge.
