# Assumption Audit: Pre-owner exact-HEAD HoloIndex repair admission

## 1. Problem Statement

- What: allow a fail-closed `REPO_HEAD_MISMATCH` produced before owner
  acquisition to reconcile the existing exact-HEAD HoloIndex maintenance task.
- Why: after every main commit, freshness admission rejects before owner
  acquisition; the repair bridge previously required two owner attempts and
  could never start the governed transaction.
- Who: 0102 architect, from the external-principal RedDog continuation.

## 2. Assumptions

| ID | Assumption | Evidence | Confidence |
|---|---|---|---|
| A1 | The failure occurs before owner acquisition. | Exact-main query returned `owner_attempts=0`, `REPO_HEAD_MISMATCH`, and explicit no-reindex/no-mutation fields. | HIGH |
| A2 | Restarting the resident owner cannot repair it. | `query_once` performs freshness admission before `ensure_reddog_holoindex_owner`. | HIGH |
| A3 | The existing post-merge task is the sole repair path. | Incident bridge and post-merge contract already bind one task/request/completion per exact HEAD. | HIGH |
| A4 | A zero-attempt result alone is not sufficient authority. | The bridge now requires exact authority binding and a second fixed-query reproduction. | HIGH |

## 3. Failure Modes

| ID | Failure Mode | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| F1 | Forged failure enqueues maintenance. | MEDIUM | HIGH | Exact query/source/HEAD/root/digest/no-effect/type validation plus independent reproduction. |
| F2 | Owner transient bypasses exhausted retry/receipt rules. | LOW | HIGH | The exception is confined to the incident bridge; the shared owner classifier remains receipt-bound and explicitly rejects the unreceipted result. |
| F3 | Query path gains indexing authority. | LOW | CRITICAL | Repair only emits the existing durable task; query result must assert no reindex and no authority mutation. |
| F4 | Duplicate commits create duplicate work. | LOW | MEDIUM | Existing `holoindex_postmerge_refresh:<HEAD>` idempotent task and event identities remain unchanged. |
| F5 | Candidate is called live-ready without exact-main proof. | MEDIUM | HIGH | Docs label it candidate; merge, live controller replay, governed query, and immutable replica verification are mandatory. |

## 4. Alternatives Considered

| Alternative | Why Rejected |
|---|---|
| Restart the owner | Admission rejects before owner acquisition and the stale receipt remains unchanged. |
| Run maintenance manually | Bypasses the controller contract and does not repair future exact-main transitions. |
| Treat all zero-attempt failures as repairable | Broadens authority and defeats receipt-bound owner-failure authentication. |
| Create a new repair task family | Duplicates the existing exact-HEAD transaction and weakens idempotency. |

## 5. Decision Record

- Decision: PROCEED with the narrow incident-kind and independent-recheck repair.
- Owner: 0102 architect.
- Timestamp: 2026-08-29T01:20:00+09:00.
- Process note: candidate code was drafted after direct failure/code/test
  retrieval but before this formal audit artifact existed. No live runtime,
  queue, maintenance, route, replica, or Git effect was executed. This artifact
  gates the first live transaction and records that ordering defect explicitly.
