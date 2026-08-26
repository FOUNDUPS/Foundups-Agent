# Assumption Audit: RedDog Resident New-Scope Admission Phase 1

## 1. Problem Statement

- **What**: Resolve one trusted empty-ID resident `TURN` into an authenticated,
  content-minimized AgentDB FoundUp conversation scope.
- **Why**: The transport envelope is deliberately zero-authority, while the
  existing current-session aggregate accepts only an existing conversation.
- **Who**: Authorized by 012; executed by `0102/architect` on 2026-08-26.

This phase creates or exactly recovers a scope only. It does not journal or
execute the first turn, expose traffic, reserve conversation CAS, call a model,
dispatch a worker, mutate a repository, or modify HoloIndex.

## 2. WSP 15 Allocation

- Complexity `4`, importance `5`, deferability `4`, impact `5`.
- Total/priority: `18 / P0`.
- Smallest layer: trusted resolution plus authority-native scope persistence.
  First-turn identity binding, handlers, responses, and adapters remain separate.

## 3. Retrieval Evaluation

- The governed owner query was attempted once and failed closed with
  `HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH`.
- Authority HEAD was `e656fd76fe906b3f3f860642b30ca47d685f9ce2`;
  workspace/base HEAD was `10d85a92f2d3a660741c28ab72b97a7117423499`.
  Freshness was `UNKNOWN`, `index_gap_detected=true`, and attempts were zero.
- No retry, raw query, reindex, route repair, activation, or Holo mutation was
  performed. Exact local source, tests, navigation, module memory, and earlier
  phase audits were read directly as must-includes.
- Because no result set was admitted, noise and ordering are unmeasured.
  Explicit must-includes controlled missing-artifact and duplication risk;
  repository-wide semantic freshness is not claimed.

## 4. Assumptions and Falsification

| ID | Assumption | Evidence | Verdict |
|---|---|---|---|
| A1 | An empty-ID TURN may select identity from client text. | The envelope intentionally excludes principal/FoundUp authority. | FALSE; exact intent, credential, grounding and registry bindings are required |
| A2 | The intent's digest authenticates it. | Canonical hashing proves equality only. | FALSE; current-generation signed session authority supplies identity |
| A3 | A fixed per-intent session binding is a safe nonce-conflict domain. | Production changes it with intent/request or grounding identity; turn-only identity is not claimed. | FALSE; signed stable session ID now fences authority-native new-scope identity |
| A4 | Any existing record with the derived ID is an exact retry. | Same nonce can carry changed turn, grounding or state. | FALSE; complete unsigned record, authority identity and E0 signature must match |
| A5 | Authority expiry alone guarantees a usable new scope. | A shorter requested TTL could expire before the resident request. | FALSE; scope expiry must also span request expiry |
| A6 | Scope creation executes the first turn. | No journal, handler or CAS transition is called. | FALSE |

## 5. Failure Modes

| Failure | Mitigation |
|---|---|
| Client injects principal, FoundUp, source or executable authority. | Exact `reddog_intent.v2` field set and fixed extension-origin/non-authority values. |
| Work focus, request ID or grounding receipt diverges. | Exact cross-contract equality before credential leasing. |
| Grounding names an unregistered or different FoundUp. | Full verified grounding and registered-target validation. |
| Same signed session and nonce submit divergent first turns. | Stable signed session ID yields the same conversation ID; exact recovery then rejects divergent records. |
| Credential/generation/signer expires or changes during create. | Current-generation lease encloses required E0 signing and persistence; scope/request expiry are bounded. |
| Existing row is corrupted, forged or merely similar. | Reload, complete unsigned-record equality, authority match and E0 verification are all mandatory. |
| Raw text or credential reaches durable scope/result. | Fixed objective plus digest/grounding state only; disclosure tests inspect result and row. |

## 6. Alternatives Considered

| Alternative | Why Rejected |
|---|---|
| Let the extension generate a conversation ID | The thin client has no identity or persistence authority. |
| Persist operator text as scope objective | Unnecessary disclosure and a second source of conversational truth. |
| Reuse the existing-conversation request journal immediately | Its frozen v1 contract requires a nonempty conversation ID and nonnegative revision; rewriting the first request without a resolution-link contract would falsify identity. |
| Add a new parallel database or signer | Duplicates AgentDB and E0 authority already present. |
| Wire handlers/host/adapters in the same slice | Couples identity, replay, state transition and transport before the scope seam is independently proven. |

## 7. Decision Record

- **Decision**: PROCEED with the repaired inert aggregate.
- **Reuse**: transport request, exact v2 intent, grounding/FoundUp validation,
  current-generation session source, E0 signer, AgentDB scope store, and opaque
  authority registry.
- **Scale boundary**: the aggregate is transport-neutral and durable through
  AgentDB, but does not claim streaming, horizontally scalable handler
  execution, or cross-device delivery.
- **Next**: define a durable first-turn resolution link that binds the original
  empty-ID request to the returned conversation ID and revision before handler
  execution, then add immediate authenticated CAS and thin adapters.

## 8. Verification Record

- Initial independent WSP 00/WSP 97 verdict: **NO-GO**; it exposed the
  production intent-derived session-binding split hidden by fixed test authority.
- Repaired focused suite: `17 passed`.
- Repaired authenticated state/session/signing/tamper/admission/binding/journal
  matrix: `127 passed`.
- Repaired-byte independent WSP 00/WSP 97 verdict: **GO**, `46 passed`.
- Ruff passes. Six production sources are at most 500 lines and every function
  is at most 50 lines; no exemption or threshold changed.
- Canonical registry: `1,581` entries / `268` quarantined. Authenticated backend
  closure: `1,384` files at
  `3211a4e5c83d7a8fca27ec7155933659164587fa5ca9813899d3dc79b51c8498`.
- Extension release and exact-main VSIX remain promotion gates.
