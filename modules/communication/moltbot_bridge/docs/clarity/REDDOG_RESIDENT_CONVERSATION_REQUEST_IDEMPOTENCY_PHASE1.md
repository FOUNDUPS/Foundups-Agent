# Assumption Audit: RedDog Resident Conversation Request Idempotency Phase 1

## 1. Problem Statement

- **What**: Durably reserve one already-admitted resident conversation request
  identity in the existing AgentDB database.
- **Why**: The transport envelope supplies nonce and idempotency digests, but
  the admission-only binding intentionally persisted nothing. Enabling handlers
  without a replay fence would permit duplicate work after retry or restart.
- **Who**: Authorized by 012; executed by `0102/architect` on 2026-08-26.

This phase does not create a conversation, accept unauthenticated scope, store
operator text, reserve the conversation CAS revision, invoke a model, dispatch
a worker, expose a network endpoint, or mutate HoloIndex.

## 2. WSP 15 Allocation

- Rescored after WSP 97 falsification: complexity `5`, importance `5`,
  deferability `5`, impact `5`.
- Total/priority: `20 / P0`.
- Reasoning tier: `ULTRA`.
- Smallest layer: one content-free AgentDB reservation journal after the
  existing authenticated scope binding; handlers and adapters remain separate.

## 3. Retrieval Evaluation

- The required governed owner query was attempted once from the exact work
  slice and failed closed with `HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH`.
- Query authority HEAD was `e656fd76fe906b3f3f860642b30ca47d685f9ce2`;
  the current repository base was
  `b4813a25662f674aacdb8bade6adb7ef789d012d`. Freshness was `UNKNOWN`,
  `index_gap_detected=true`, and owner attempts were zero.
- No retry, direct query, reindex, route activation, replica mutation, or Holo
  repair was performed in this RedDog transaction.
- Structured-memory fallback used exact source and direct must-include reads:
  the transport contract, authenticated scope state/store/contract/capability,
  admission binding and tests, `NAVIGATION.py`, module `README.md`,
  `INTERFACE.md`, `ROADMAP.md`, `ModLog.md`, `tests/README.md`, and
  `tests/TestModLog.md`.
- Noise and ordering could not be evaluated because no result set was admitted.
  Missing-artifact risk was controlled by the explicit must-include list.
  Staleness risk remains non-zero and is truth-labeled; exact local symbols,
  tests, and Git base—not Holo freshness—ground this bounded implementation.

## 4. Assumptions

| ID | Assumption | Evidence | Confidence |
|---|---|---|---|
| A1 | A journal may consume only a successful exact binding, never a reconstructed result or client identity assertion. | The binder derives a non-constructible one-use child from the still-registered secret-backed verified authority, binds the canonical reservation identity, and excludes it from serialization. | HIGH |
| A2 | Idempotency must survive process restart. | Existing AgentDB scope already provides the durable database boundary. | HIGH |
| A3 | Exact replay is the only accepted collision. | Request digest covers operator text and all envelope identity fields. | HIGH |
| A4 | A new insert must fence state changes after binding. | Admission does not reserve CAS; AgentDB state can advance before persistence. | HIGH |
| A5 | A reservation is not permission to execute. | It stores equality evidence only and carries explicit no-authority flags. | HIGH |
| A6 | Raw text and principal/FoundUp identifiers are unnecessary for replay equality. | Request, binding, scope and receipt digests provide the required comparison inputs. | HIGH |

## 5. Failure Modes

| ID | Failure Mode | Impact | Mitigation |
|---|---|---|---|
| F1 | Same key replays altered operator text. | HIGH | Request digest changes; divergent identity rejects. |
| F2 | Request ID or client nonce is reused under another key/conversation. | HIGH | Global unique constraints plus related-row comparison reject. |
| F3 | Scope advances or expires between binding and insert. | HIGH | Opaque proof expiry plus store-owned-clock and exact revision/digest/latest-receipt/expiry recheck under a scope lock. |
| F4 | Processes reserve concurrently across one or many conversations. | HIGH | SQLite immediate write lock; PostgreSQL scope/global-counter row locks; unique constraints select one writer. |
| F5 | Stored JSON, digest, or an indexed SQL column is corrupted. | HIGH | Every load/replay binds all four index columns to a schema/digest-valid canonical record. |
| F6 | Journal grows without bound or concurrent counts overshoot. | MEDIUM | Per-conversation limit plus locked durable global counter and actual-count integrity check. |
| F7 | A binding result or digest-only admission issuer is forged. | CRITICAL | The removed digest registrar cannot mint proof; derivation requires a live registered verified parent and the store consumes the exact reservation-bound child. |
| F8 | A stale replay is mistaken for fresh execution authority. | CRITICAL | Result declares no CAS/effect authority; every future handler must re-authenticate and CAS current state. |

## 6. Alternatives Considered

| Alternative | Why Rejected |
|---|---|
| Add idempotency to the VSIX | The extension is an untrusted thin adapter and cannot own durable authority. |
| Store request text for replay | Unnecessary disclosure; digest equality is sufficient for this layer. |
| Extend the scope table with request columns | Mixes conversation state CAS with an append-like replay journal and complicates retention. |
| Add model invocation or handlers now | Collapses replay, state transition, execution and response behavior into an unverified big-bang layer. |
| Treat insert as conversation-CAS reservation | The journal does not own or advance the authenticated scope revision. |

## 7. Decision Record

- **Decision**: PROCEED with the isolated durable replay fence.
- **Boundary**: Existing authenticated conversations only; stored records are
  content-free and grant no identity, model, worker, repository, or effect
  authority.
- **Next layer**: extract/consume the current-generation session credential
  lease and aggregate credential admission, binding, and reservation without
  enabling traffic. Then add trusted new-scope resolution and operation-specific
  handlers with immediate authenticated CAS, followed by thin adapters.

## 8. Verification Record

- Authenticated conversation/journal/signing matrix: `94 passed`.
- Extended RedDog/WSP-62 matrix: `110 passed`; registry governance: `45 passed`.
- Transport-neutral request contract: `36 passed`.
- Python compilation and Ruff: pass.
- RedDog release gate: `4/4 PASS`; deterministic package surface: `67 files /
  965,192 bytes` under the `1 MiB` cap. Exact-final timing is recorded only in
  the external WSP-97 receipt to avoid self-referential documentation reruns.
- PostgreSQL evidence is a production-interface SQL/locking contract over
  mapping rows, not a live PostgreSQL service canary.
- WSP 62: six touched/new production sources are at most `394` lines; longest
  function is `41` lines; no threshold or exemption change.
- Independent WSP 00/WSP 97 exact-diff verdict and canonical registry/release
  verification are required before promotion.
