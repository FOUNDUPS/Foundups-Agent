# Assumption Audit: RedDog Holo Query Route Consumer

- Status: PROCEED_WITH_FAIL_CLOSED_GATES
- Base commit: `7da03c62ac45179626662e1d0f3ff8157d25e0a4`
- Execution plane: local trusted-host runtime contract; no live activation
- WSP_15: C4 / I5 / D5 / Impact5 = 19 (P0)

## 1. Problem Statement

- What: bind RedDog query consumers to one stable private route file without
  giving those consumers route publication or crash-recovery authority.
- Why: a per-generation environment root is mutable, process-stale, and cannot
  prove serialized activation; a route record without terminal journal proof
  can represent an interrupted candidate swap.
- Who: 012 directed completion of the RedDog activation path; 0102 architect
  owns this bounded implementation and independent WSP_97 verification.

## 2. Assumptions

| ID | Assumption | Evidence | Confidence |
|---|---|---|---|
| A1 | A `CURRENT` route is admitted by consumers only when a `COMMITTED` journal selects its exact digest. | `QueryRouteStore.transition()` writes PREPARED before the route and COMMITTED after the explicit request. | HIGH |
| A2 | The terminal journal is durable commit/rollback proof and must remain beside the route. | Store contract and adversarial journal-loss reproduction. | HIGH |
| A3 | Query consumers require only a terminal read and exact descriptor comparison. | Existing owner resolver, one-shot, maintenance, and promotion call graph. | HIGH |
| A4 | Activation recovery must remain a separate explicit controller operation. | `load()` is mutating recovery; `load_readonly()` is the consumer boundary. | HIGH |
| A5 | Start Operations is a third bounded propagation boundary, separate from bridge profiles. | `startOperationsEnvironment.build(process.env)` and `ALLOWED_KEYS`. | HIGH |

## 3. Failure Modes

| ID | Failure Mode | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| F1 | PREPARED consumer read rolls back or publishes state. | MED | CRITICAL | `load_readonly()` returns `QUERY_ROUTE_TRANSITION_PENDING` and performs no write. |
| F2 | Candidate route survives while its journal is deleted. | MED | CRITICAL | No-journal admits only schema-valid EMPTY; CURRENT returns `QUERY_ROUTE_JOURNAL_REQUIRED`. |
| F3 | Terminal journal selects a different route digest. | MED | CRITICAL | Exact constant-time digest comparison fails closed. |
| F4 | Missing route parent is created by a query. | LOW | HIGH | Consumer constructs the store with `create_runtime_root=False`. |
| F5 | Ambient or hostile environment values cross into Python. | MED | HIGH | Exact built-in-string validation in Python and `copyPresentStrings` at JavaScript boundaries. |
| F6 | A normal process hot-switches after environment or route change. | MED | HIGH | No hot-switch claim; owner/process restart remains required and activation is separately gated. |
| F7 | Capacity caps are widened to hide closure growth. | MED | HIGH | Keep fixed caps; record file, manifest-byte, and package-byte headroom as P1 debt. |

## 4. Alternatives Considered

| Alternative | Why Rejected |
|---|---|
| Mutate `REDDOG_HOLOINDEX_QUERY_REPLICA_ROOT` for every generation | No atomic cross-process CAS, already-running processes remain stale, and there is no durable transition proof. |
| Let every consumer call mutating `load()` | A read path would gain rollback publication authority and could hide an interrupted activation. |
| Accept schema-valid CURRENT without a journal | Reproduced uncommitted-candidate promotion after PREPARED journal loss. |
| Delete terminal journals after commit | No separately specified cleanup checkpoint exists; deletion would remove commit proof. |
| Increase backend/package caps | Masks scale pressure without reducing closure or verification cost. |

## 5. Decision Record

- Decision: PROCEED with nonmutating terminal consumer admission.
- Owner: 0102 architect; independent verifier lane required before commit.
- Timestamp: `2026-08-23T13:24:40+09:00`
- Gates: focused and adjacent tests, regenerated backend manifest/pins, WSP_62
  scan, exact staged-diff audit, no live route/environment/owner/Holo mutation.
- Explicitly excluded: activation controller, environment installation,
  materialization, live query, provider/model calls, PR merge, and production
  promotion.
