# Assumption Audit: RedDog Holo Post-Merge Activation Order

- Status: ACCEPTED_AT_EXACT_MAIN_CFD1E0051
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
| A7 | Stable route-file possession eliminates per-generation process restarts only when every supported long-lived caller selects the current route exclusively. | The route path is stable while its journaled record advances by CAS. The one-shot query already selected the allowlisted current-user route over an inherited legacy root; the post-merge composer initially omitted that shared boundary and reproduced the failure. | HIGH after repair |

## 3. Failure Modes

| ID | Failure Mode | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| F1 | Activation runs under the first authority lease and self-contends. | HIGH before repair | CRITICAL | Release the first lease before invoking the existing controller; regression asserts exact effect order. |
| F2 | Repository advances during activation. | MED | HIGH | Reacquire authority lease, refetch origin/main, invalidate superseded generation, and never complete the stale task. |
| F3 | Activation publishes a route but the owner or immutable reproof fails. | LOW | CRITICAL | Require controller `ok`, `route_committed`, and `post_query_replica_unchanged`; final owner proof must be CURRENT and exactly bound. |
| F4 | A caller injects a fake refresh, activation, Git, or completion result into production. | MED | CRITICAL | Public authority, coordinator, and executor signatures expose only production dependencies; effect seams are private test adapters. |
| F5 | The second authority lease is busy after an owner starts. | MED | HIGH | Stop only the process-owned owner and return BUSY; never complete or resolve the request. |
| F6 | Existing replica/receipt evidence is overwritten. | LOW | CRITICAL | Bounded absent-only allocation; no delete, overwrite, or reuse authority. |
| F7 | A pre-migration long-lived process retains the legacy root while the user route pointer is newer. | MED during migration | HIGH | Dual configuration remains rejected by the low-level resolver. Supported long-lived callers must build the shared allowlisted private route snapshot, where a current user route replaces the inherited legacy root without mutating ambient state. |
| F8 | Manual `a7302344` recovery is misreported as automatic acceptance. | MED | HIGH | Keep the historical task failed and label it manual evidence; automatic acceptance is separately bound to the completed `cfd1e0051` task. |

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
  proof. Those final gates completed at `cfd1e0051`; later HEADs require their
  own exact-SHA evidence.
- Explicitly excluded: query-time reindex, lease bypass, route ambiguity,
  overwrite/delete/retention authority, provider/model changes, and relabeling
  historical failed work.

## 6. Resolution Evidence

- The real broker-managed OpenClaw supervisor claimed and completed
  `holoindex_postmerge_refresh:cfd1e0051ea0e5624c7a7fcc8f7e2bc4e442aae9`
  through AgentDB with retry count zero.
- Completion binds generation `sha256:60d062749983...06f3c66` and freshness
  receipt `sha256:74be7db6ba21...ed0fa`.
- A subsequent normal governed query returned CURRENT/no-gap/no-reindex and
  full production revalidation preserved all 33 immutable artifacts. The
  historical `a7302344` task remains failed evidence.

## 7. Later-HEAD Falsification Addendum

- Exact main `938d1d01` refreshed canonical state but failed replica activation
  with `HOLOINDEX_POSTMERGE_ROUTE_CONFIG_INVALID` in a long-lived OpenClaw
  process. Read-only diagnosis proved that process held only the retired direct
  root while the current user environment held the stable route file.
- The post-merge composer now reuses the existing owner-acquisition environment
  builder once per transaction and passes that immutable private mapping to
  both owner probes and activation. It does not weaken ambiguous low-level
  input, mutate `os.environ`, copy credentials, or authorize route publication.
- This addendum corrects A7/F7; the historical `cfd1e0051` acceptance remains
  valid for that exact commit. The repair still requires merge and a new
  exact-main live replay before it is accepted operationally.

## 8. Exact-Main Route-Continuity Replay Addendum

- PR #1568 merged at `a48e9b61`. The real broker-managed OpenClaw transaction
  then refreshed canonical Holo, materialized generation
  `sha256:7102c478...`, passed the candidate query, and committed stable route
  revision 5. This proves the route-environment repair reached activation.
- The first normal post-commit proof returned
  `ACTIVATION_QUERY_PROOF_INVALID`; the activation receipt remains
  `COMMITTED_UNVERIFIED` and AgentDB remains failed. Later supported and
  activation-shaped queries were CURRENT/no-gap/no-reindex against that same
  immutable binding, so Holo is operational but the durable completion gate
  was a false negative.
- A separate focused P0 transaction adds exactly one typed, read-only
  post-commit recovery proof. It does not retry candidate admission, change
  route CAS, relabel the historical task, or widen Holo/Git/worker authority.

## 9. Exact-Main Stable-Resolver Contract Falsification

- PR #1569 merged at `f058f87b`. The real OpenClaw/AgentDB path refreshed
  generation `sha256:cf1433b1...`, passed candidate admission, and committed
  route revision 6. Both post-commit proofs still failed
  `ACTIVATION_QUERY_PROOF_INVALID`; the task and activation receipt remain
  failed/`COMMITTED_UNVERIFIED` even though a later governed query is CURRENT.
- A production-shaped direct query proved this was not transient owner timing.
  `query_once` passed canonical roots plus `environment` to the callback; the
  stable callback expanded those kwargs and supplied `environment` again.
  Python rejected the duplicate keyword before strict route resolution and the
  query boundary normalized it to `HOLOINDEX_QUERY_REPLICA_REQUIRED`.
- Decision: preserve the two-attempt resilience bound, but correct the resolver
  seam by explicitly projecting canonical roots and replacing caller route
  inputs with the single committed route-file capability. This closes A7/F7
  at the actual callback boundary and adds no route-publication, maintenance,
  retry, or mutation authority.
