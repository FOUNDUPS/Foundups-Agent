# Assumption Audit: RedDog Holo Post-Merge Activation Order

- Status: PROCEED_WITH_FAIL_CLOSED_GATES
- Base commit: `a7302344424615dc9d061ef408c2de2508660b81`
- Execution plane: OpenClaw/AgentDB task -> Holo authority -> replica activation
- WSP_15: C4 / I5 / D5 / Impact5 = 19 (P0)

## 1. Problem Statement

- What: make the durable exact-SHA post-merge task finish only after canonical
  refresh, immutable query-replica activation, a CURRENT governed owner query,
  and final clean repository/receipt binding.
- Why: the exact-`a7302344` task refreshed successfully but failed with
  `HOLOINDEX_QUERY_REPLICA_REQUIRED`; the transaction held the same authority
  lease that the existing activation controller had to acquire.
- Who: OpenClaw executes the durable task; the Holo authority and activation
  controllers retain their separate maintenance and route authority; AgentDB
  owns durable status truth.

## 2. Assumptions

| ID | Assumption | Evidence | Confidence |
|---|---|---|---|
| A1 | One process lock can serialize the transaction while the authority lease is split. | `_PROCESS_LOCK` encloses refresh, activation, and final proof; focused ordering tests observe both lease windows. | HIGH |
| A2 | Activation must run outside the first authority lease. | The existing materializer/controller nonmutatingly acquires authority then maintenance leases; the historical task reproduced self-contention. | HIGH |
| A3 | A ready owner is insufficient unless it matches the just-refreshed canonical proof. | Candidate equality checks require exact HEAD, generation, and freshness-receipt digest before completion. | HIGH |
| A4 | New target names must never overwrite evidence. | Replica and receipt allocation accepts only absent paths and increments a bounded suffix. | HIGH |
| A5 | The final authority lease must be reacquired after activation. | Repository HEAD/origin/main, clean state, generation, and receipt are re-proved after the normal owner query. | HIGH |
| A6 | Task failure must not resolve the durable request. | FakeDB and real SQLite AgentDB regressions preserve failed task, pending request, and absent completion event. | HIGH |
| A7 | Stable route-file possession eliminates per-generation process restarts after one migration restart. | The route path is stable while its journaled record advances by CAS; a long-lived pre-migration process carrying only the retired direct-root variable failed closed until its child environment selected the route exclusively. | MEDIUM |

## 3. Failure Modes

| ID | Failure Mode | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| F1 | Activation runs under the first authority lease and self-contends. | HIGH before repair | CRITICAL | Release the first lease before invoking the existing controller; regression asserts exact effect order. |
| F2 | Repository advances during activation. | MED | HIGH | Reacquire authority lease, refetch origin/main, invalidate superseded generation, and never complete the stale task. |
| F3 | Activation publishes a route but the owner or immutable reproof fails. | LOW | CRITICAL | Require controller `ok`, `route_committed`, and `post_query_replica_unchanged`; final owner proof must be CURRENT and exactly bound. |
| F4 | A caller injects a fake refresh, activation, Git, or completion result into production. | MED | CRITICAL | Public authority, coordinator, and executor signatures expose only production dependencies; effect seams are private test adapters. |
| F5 | The second authority lease is busy after an owner starts. | MED | HIGH | Stop only the process-owned owner and return BUSY; never complete or resolve the request. |
| F6 | Existing replica/receipt evidence is overwritten. | LOW | CRITICAL | Bounded absent-only allocation; no delete, overwrite, or reuse authority. |
| F7 | A pre-migration long-lived process retains the legacy root while the user route pointer is newer. | MED during migration | HIGH | Dual configuration remains rejected. Restart once after route-pointer migration or construct the child with only the persisted stable route. Do not weaken the exclusive-capability rule. |
| F8 | Manual `a7302344` recovery is misreported as automatic acceptance. | MED | HIGH | Keep the historical task failed and label the current live route as manual evidence; require a new merged exact-main task for acceptance. |

## 4. Alternatives Considered

| Alternative | Why Rejected |
|---|---|
| Keep one authority lease and make activation skip its lease | Downgrades the existing artifact/authority proof and creates a second unsafe controller mode. |
| Treat canonical refresh as task completion | Leaves RedDog unable to query and falsely resolves durable work. |
| Reimplement materialization inside idle automation | Duplicates the audited controller and violates WSP_50/WSP_84. |
| Accept whichever of route file or direct root is newest | Environment text has no trustworthy recency or CAS proof; ambiguity must fail closed. |
| Reuse a pre-existing target path | Risks overwriting or laundering immutable evidence. |
| Mark the historical failed task complete after manual repair | Rewrites execution history and breaks AgentDB truth. |

## 5. Decision Record

- Decision: PROCEED with split authority leases under one process lock, compose
  the existing activation controller, seal production dependency seams, and
  preserve exact AgentDB completion truth.
- Owner: 0102 architect; independent WSP_00/WSP_97 audit required.
- Timestamp: `2026-08-27T00:00:00Z`
- Gates: focused and adjacent Python suites, real AgentDB regression, WSP_62,
  registry and authenticated-backend reprojection, extension release gates,
  squash merge, then one new exact-main OpenClaw replay and immutable query
  proof before declaring automatic production acceptance.
- Explicitly excluded: query-time reindex, lease bypass, route ambiguity,
  overwrite/delete/retention authority, provider/model changes, and relabeling
  historical failed work.
