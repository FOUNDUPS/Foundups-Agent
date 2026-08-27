# Assumption Audit: RedDog Holo Query Replica Activation

- Status: PROCEED_WITH_FAIL_CLOSED_GATES
- Base commit: `5aa374e12e38a4ac7eb32a98b5d0714cf5bffaf7`
- Execution plane: trusted-host maintenance/materialization/route transaction
- WSP_15: C4 / I5 / D5 / Impact5 = 19 (P0)

## 1. Problem Statement

- What: convert one clean exact-HEAD canonical Holo generation into a narrow
  immutable query replica and select it through the existing revision/digest
  CAS only after a real candidate canary.
- Why: maintenance, planning, materialization, descriptor proof, route CAS,
  and query consumers existed, but no production controller joined them.
- Who: 0102 owns the bounded transaction; an independent WSP_00/WSP_97 lane
  must falsify it before merge and live activation.

## 2. Assumptions

| ID | Assumption | Evidence | Confidence |
|---|---|---|---|
| A1 | Maintenance can prove exact HEAD without requiring the necessarily stale selected route. | `ensure_reddog_holoindex_current()` performs maintenance/current proof and never resolves or starts an owner. | HIGH |
| A2 | Copying and full hashing need not hold the route lock. | Plan, isolated-root creation, materialization, and descriptor admission precede `QueryRouteStore.transition()`. | HIGH |
| A3 | The candidate canary must not recursively acquire the route-file lock. | While PREPARED is held, `query_once()` receives the already verified `QueryReplicaOwnerRoute` capability directly. | HIGH |
| A4 | A normal consumer canary is distinct evidence. | After commit/unlock, the second query resolves only the stable route-file pointer. | HIGH |
| A5 | A successful query is insufficient without immutable reproof. | The admitted descriptor and every reachable model/snapshot artifact are revalidated before commit and after the normal query. | HIGH |
| A6 | Concurrent activators may copy the same generation safely. | New roots are no-replace and disjoint; prior revision/digest CAS admits only one route winner. | HIGH |

## 3. Failure Modes

| ID | Failure Mode | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| F1 | Repository or canonical receipt changes during planning/copy. | MED | CRITICAL | Exact state/receipt/manifests are reproved by planner, materializer, descriptor verifier, and final revalidation. |
| F2 | Candidate query recursively waits on the route lock. | MED | HIGH | Candidate receives an explicit route capability; only the post-commit query uses the route-file resolver. |
| F3 | Candidate succeeds but mutates a reachable artifact. | LOW | CRITICAL | Full admitted-replica revalidation runs inside the transaction before commit. |
| F4 | The first post-commit normal query proof fails transiently after route commit. | MED | CRITICAL | Make exactly one additional typed, read-only stable-route proof; require immutable revalidation after recovery; otherwise emit `COMMITTED_UNVERIFIED`, never PASS or a false rollback claim. |
| F5 | A CAS loser deletes or overwrites its materialization. | MED | HIGH | Preserve the immutable unselected root as evidence; this slice performs no retention or deletion. |
| F6 | Receipt exposes private roots, environment, URL, token, or executable. | MED | CRITICAL | Receipt is an exact digest/count/status projection and private publication rejects absolute path values. |
| F7 | Receipt publication fails after commit. | LOW | HIGH | Return `ACTIVATION_RECEIPT_PUBLICATION_FAILED` and `COMMITTED_UNVERIFIED`; never claim PASS. |

## 4. Alternatives Considered

| Alternative | Why Rejected |
|---|---|
| Interpret `HOLOINDEX_QUERY_REPLICA_REQUIRED` after maintenance as success | Conflates two boundaries and could hide an unrelated failure. |
| Call private `_run_full_refresh()` from an operational script | Bypasses the public maintenance contract and its secret-free result. |
| Query the candidate through the stable route while PREPARED | Recursively takes the same machine-wide lock and can deadlock. |
| Commit before candidate semantic proof | Makes rollback unavailable for a bad replica. |
| Automatically delete old or losing replicas | Retention authority is not specified and historical roots are evidence. |
| Make route state network-shared | Locks and filesystem identity proofs are host-local; fleet activation must run independently per host. |

## 5. Decision Record

- Decision: PROCEED with the bounded controller and default-inert CLI.
- Owner: 0102 architect; independent WSP_97 verification required.
- Timestamp: `2026-08-23T00:00:00Z`
- Gates: focused and adjacent suites, WSP_62, backend manifest and package
  regeneration, exact staged-diff audit, merge, then one authorized exact-main
  activation with post-query immutable proof.
- Explicitly excluded: replica deletion/retention, network-shared routes,
  model download, provider calls, candidate retry, unbounded/broad retry, and
  ambient route selection.

## 6. 2026-08-27 Post-Commit Falsification Addendum

- Exact main `a48e9b61` passed candidate query admission and committed route
  revision 5 for generation `sha256:7102c478...`, then returned
  `ACTIVATION_QUERY_PROOF_INVALID` on the first stable-route proof. The receipt
  remains `COMMITTED_UNVERIFIED` and the AgentDB task remains failed.
- Later supported and activation-shaped queries returned CURRENT/no-gap/
  no-reindex with the same route and replica binding. This falsifies the
  assumption that one post-commit attempt is a sufficient availability gate;
  it does not weaken candidate, route, receipt, or immutability proof.
- Decision: permit exactly two total stable-route proof attempts after commit,
  catching only `CandidateAcceptanceError`. A recovered query still must pass
  `QueryReplicaOwnerRoute.revalidate()`. Two failures preserve the original
  fail-closed outcome.

## 7. 2026-08-27 Stable-Resolver Contract Falsification Addendum

- Exact main `f058f87b` repeated the failure after both bounded proofs while
  committing a usable revision-6 route for generation `sha256:cf1433b1...`.
  This falsified the transient-only reading of F4; the retry was bounded and
  safe but insufficient.
- The production callback contract supplied `environment` in resolver kwargs.
  The stable callback also supplied `environment`, causing a deterministic
  duplicate-keyword `TypeError` before the strict resolver ran. The query
  boundary correctly hid the exception as `HOLOINDEX_QUERY_REPLICA_REQUIRED`,
  but the activation receipt necessarily retained only the outer stable error.
- RED now exercises the exact callback shape and fails committed-unverified on
  the old code. The correction replaces caller route inputs with the committed
  route-file capability while preserving canonical roots. Candidate admission,
  two-attempt bounds, exact authority, semantic evidence, immutable reproof,
  and terminal failure truth remain unchanged.
