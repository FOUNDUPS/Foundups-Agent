# HoloIndex / RedDog Operational Truth Boundary POC Phase 1

**Slice:** HOLOINDEX_REDDOG_OPERATIONAL_TRUTH_BOUNDARY_POC_PHASE1
**Date:** 2026-07-18
**Base:** 69b0ccfc3289248164ef84f1078caba688afe020
**Owner:** 0102 architect operating in WSP_00 state for 012
**WSP:** 00, 05, 06, 15, 22, 34, 50, 62, 64, 84, 87, 96, 97
**Change class:** High-risk runtime autonomy, HoloIndex indexing/retrieval, and
private authentication boundary.

## Assumption Audit: HoloIndex / RedDog Operational Truth Boundary

### 1. Problem Statement

- **What:** Make the RedDog proof-of-concept able to obtain current semantic
  repository evidence through one private query owner while a separately
  authorized trusted-host maintenance path performs bounded full refreshes.
  Startup may route a maintenance request through governed WRE dispatch; WRE
  routing is not a transfer of store authority to the query worker.
- **Why:** The prior paths could open the persistent store from multiple
  processes, use divergent storage roots, treat lexical or stale evidence as
  operational, narrow a full refresh without recording the scope, or report
  success after an incomplete mutation.
- **Who:** 012 requested the implementation; 0102 is the architect/owner. The
  change is limited to this isolated worktree and a focused PR.

This phase gives the supported RedDog adapter no shell, Git, merge, credential,
or HoloIndex write surface. That API contract is not an OS privilege boundary;
host deployment must enforce process/filesystem permissions separately. It
does not claim that recursive
FoundUp construction is production-ready. It establishes the evidence and
maintenance boundary needed by later governed WRE execution.

### 2. Assumptions

| ID | Assumption | Evidence | Confidence |
|----|------------|----------|------------|
| A1 | Every migrated Phase-1 RedDog operational query and trusted refresh uses one canonical physical HoloIndex store. | Canonical storage resolver, store identity in the freshness receipt, owner identity validation, precedence/error tests. The legacy foundups_mcp_bridge `holo_tools.py` direct-store path is explicitly outside this scope. | HIGH |
| A2 | A freshness claim is meaningful only for a clean, exact repository HEAD. | Repository-state reader, linked-worktree commondir handling, pre/post query checks, pre/post maintenance checks. | HIGH |
| A3 | The seven baseline collections must each carry a complete canonical source-manifest proof. | Maintenance session, receipt evaluator, collection proof/scope checks, incomplete-plan tests. | HIGH |
| A4 | Lexical fallback cannot support an operational RedDog decision. | Semantic-only maintenance preflight, owner health canary, query response validation, lexical rejection tests. | HIGH |
| A5 | One bearer-authenticated owner at literal `127.0.0.1` can serialize supported adapter access without exposing an indexing API. | Literal-host URL validation, minimum token strength, query/health-only transports, proxy/redirect denial, and HTTP tests. | HIGH |
| A6 | Maintenance and query concurrency among migrated/cooperative participants must fail closed instead of serving a mixed generation. | Cross-process lease, atomic invalidation, generation binding, maintenance probes before and after retrieval. | HIGH |
| A7 | A scoped or capped diagnostic index is not equivalent to the canonical baseline. | Source-scope identifiers, full raw source manifests, cap/read-failure accounting, canonical-plan tests. | HIGH |
| A8 | A successful code merge does not make the existing store current for the merge commit. | Exact-HEAD receipt comparison; the activation runbook requires a post-merge full refresh and smoke receipt. | HIGH |
| A9 | A full refresh runs within an exclusive repository-writer window. | Required operator/host condition; pre/post clean-HEAD checks cannot detect every transient edit-and-revert while indexing. | MED |
| A10 | All concurrent collection writers honor the canonical maintenance lease. | New CLI/incremental/host-handshake paths use the lease; legacy direct collection writers have not all been migrated or mechanically excluded. | MED |
| A11 | Normal host shutdown reaches bounded cleanup. | Controlled shutdown/atexit seams exist; abrupt process/host death can leave an orphan owner and live token until OS/supervisor reclamation. | MED |
| A12 | The POC claim is limited to explicitly preflight-wired RedDog operational consumers. | Read-only audit/research, report-collection, audit-enqueue, and configured auto-task paths use the adapter; no all-consumer migration claim is made. | HIGH |
| A13 | Every baseline collection was encoded in the exact embedding space used for its operational query. | All seven receipt entries require a non-empty sha256: embedding-space fingerprint; semantic proof compares each receipt value with both the active backend map and the response metadata map. A legacy blank value is stale and enters maintenance. | HIGH |
| A14 | The authoritative POC embedding backend is available from a complete local model artifact. | Owner startup forces sentence_transformers, disables TurboQuant routing and generation-unbound SearchCache, and resolves both flat SentenceTransformer caches and complete Hugging Face models--.../snapshots/<revision> layouts. | HIGH |
| A15 | Cold semantic initialization needs a different budget from an ordinary query. | First authenticated health has a 270-second warmup budget, ordinary/warmed owner queries are capped at 30 seconds, and the supervisor has a 300-second total startup budget. | HIGH |
| A16 | Literal-loopback HTTP peers are trusted and cooperative during this POC. | Proxy and redirect use is denied, the response body is read against one monotonic absolute deadline, and owner work is deadline-bound. The stdlib connect/header phase remains socket-inactivity-bounded, so the POC assumes no hostile same-user 127.0.0.1 port squatter or deliberate header trickle. | MED |
| A17 | Direct repository bytes used by a cross-lane model report still match the HoloIndex query HEAD. | The model-backed audit worker proves a clean exact HEAD after direct reads and again immediately before accepting the report, each time binding to the HoloIndex query receipt. | HIGH |

### 3. Failure Modes

| ID | Failure Mode | Likelihood | Impact | Mitigation |
|----|--------------|------------|--------|------------|
| F1 | Two writers corrupt or interleave a generation. | MED | CRITICAL | Exclusive maintenance lease, IN_PROGRESS invalidation before mutation, one trusted maintenance handshake. |
| F2 | A scoped/capped run overwrites a global collection and is published as complete. | MED | CRITICAL | Canonical source-scope proof, reject or downgrade narrowing controls, discovered/processed/failed accounting. |
| F3 | Repository changes and remains changed during indexing or querying. | MED | HIGH | Clean exact-HEAD checks on both sides reject the mismatch and preserve invalidation. |
| F4 | Semantic model is missing and lexical fallback is labeled operational. | MED | HIGH | Semantic preflight before reset, semantic health canary, operational client rejects non-semantic metadata. |
| F5 | A timed-out backend continues serving uncertain state. | LOW | HIGH | Permanently poison that owner instance; the private adapter replaces the owned process and retries once, while external recovery remains externally supervised. |
| F6 | Bearer token leaks through arguments, logs, receipts, proxies, or the parent environment. | LOW | HIGH | Ephemeral token, stream isolation, process-private handoff, proxy/redirect denial, secret-free codes, cleanup erasure. |
| F7 | A malformed test registry, unreadable source, positive cap, or Python AST error is silently omitted. | MED | HIGH | Count raw declarations/files, record source-read/cap/AST failures, fail before reset where possible, and make any recorded failure proof incomplete. This is not a blanket guarantee for every legacy parser. |
| F8 | Incremental mutation reports APPLIED without a globally accepted proof. | MED | HIGH | Require complete_source_manifest in the final acceptance check; retain invalidation on snapshot-only output. |
| F9 | An external configured owner is stale but is stopped without ownership. | LOW | HIGH | Authenticated bound health check; reject external stale owner and stop only an auto-owned process. |
| F10 | POC wiring is mistaken for unrestricted autonomous production readiness. | MED | CRITICAL | Explicit POC boundary, governed WRE authority remains separate, post-merge activation checklist and observable receipts. |
| F11 | A source is edited and restored (or HEAD changes A->B->A) during refresh, so pre/post checks miss mixed bytes. | LOW-MED | CRITICAL | Phase 1 requires an exclusive writer window and records this residual limitation; a later slice must index from an immutable exact-commit snapshot. |
| F12 | An unleased legacy writer mutates a collection during canonical maintenance. | MED | CRITICAL | Phase 1 is cooperative-writer only; quiesce legacy writers, migrate/retire them, and later enforce one mechanically exclusive writer plane. |
| F13 | Host death bypasses cleanup and leaves an orphan owner with a still-valid token. | LOW | HIGH | Operator/supervisor verifies and kills the orphan, rotates the token, and reruns preflight; automatic orphan reclamation is future work. |
| F14 | The supported adapter is mistaken for an OS sandbox. | MED | HIGH | State the boundary explicitly and deploy worker identities without canonical-store write or owner process-control permissions. |
| F15 | Legacy `holo_tools.py` direct-store access is mistaken for owner-bound RedDog evidence. | MED | HIGH | Limit the POC claim to migrated operational consumers and register the legacy surface for migration/retirement. |
| F16 | Owner startup/health fails after a successful refresh and a valid CURRENT receipt is misreported as stale. | LOW-MED | MED | Return operational=false for the lifecycle failure while preserving the valid receipt; repair/restart the owner and re-run authenticated health without needless reindexing. |
| F17 | A legacy collection has no embedding-space fingerprint, or a live backend/report claims a different fingerprint. | MED | CRITICAL | Treat every missing or unequal per-collection value as stale; perform canonical maintenance rather than querying vectors across unproven spaces. |
| F18 | A cold local model cache is present but not discovered, or an ambiguous/incomplete snapshot is treated as usable. | LOW-MED | HIGH | Recognize complete flat and Hugging Face snapshot layouts, honor refs/main, accept an unreferenced snapshot only when exactly one complete candidate exists, and otherwise fail closed before reset. |
| F19 | Cold semantic initialization is killed by the ordinary query budget, or ordinary queries inherit the cold-start budget. | MED | HIGH | Isolate the first-health 270-second warmup from the <=30-second query budget and contain both within the supervisor's 300-second startup budget. |
| F20 | A same-user process occupies the loopback port or trickles HTTP headers indefinitely. | LOW under POC assumption | HIGH | Phase 1 explicitly requires a trusted cooperative host and no hostile port squatter; production hardening requires peer/process identity and a transport with an enforceable total connect/header/body deadline. |
| F21 | Repository files change after a cross-lane direct read or while its model report is being produced. | MED | HIGH | Re-prove the clean exact HoloIndex receipt HEAD after the reads and again before report acceptance; reject with REPOSITORY_STATE_CHANGED on either failure. |

### 4. Alternatives Considered

| Alternative | Why Rejected |
|-------------|--------------|
| Let each migrated RedDog consumer open Chroma directly. | Multiple owners, divergent caches, no central timeout poisoning, and no supported query-only API boundary. |
| Let RedDog refresh the store inline when a query is stale. | The evidence consumer would mutate its own evidence substrate and could validate against a mixed generation. |
| Treat collection counts and timestamps as freshness. | Counts do not bind source scope, exact file content, repository HEAD, or omitted failures. |
| Preserve environment narrowing knobs during trusted index-all. | A subset or capped corpus could falsely replace the canonical collection. |
| Accept lexical results when semantic initialization fails. | Lexical recall is useful diagnostics but cannot satisfy the operational semantic contract. |
| Publish an incremental snapshot-only receipt as APPLIED. | It does not prove the global collection after deletion/upsert and is rejected by the canonical evaluator. |
| Create a knowledge backup for MODULE_CONCATENATION_GATE.md. | It is a non-protocol quick-reference annex; WSP_81 mirroring applies to authoritative WSP protocol files, not derived annexes. |

### 5. Decision Record

- **Decision:** PROCEED with the bounded Phase-1 implementation, tests, focused
  PR, and merge validation. Do not label the live store CURRENT for the merge
  commit until the post-merge activation checklist succeeds.
- **Owner:** 0102 architect
- **Timestamp:** 2026-07-18T08:27:57+09:00
- **Activation conditions:** merge checks green; clean main checkout; exclusive
  repository-writer window; trusted
  seven-collection semantic refresh at the merge SHA; authenticated health
  canary bound to that SHA, generation, receipt digest, and all seven exact
  embedding-space fingerprints; one activation-style RedDog query
  receipt; no maintenance lease or invalidation remains. This activates only
  the migrated RedDog POC consumers and does not remove the cooperative-writer,
  abrupt-death/orphan, legacy-direct-store, or OS-isolation limitations.

## WSP_15 Priority Record

This is one cross-module work item, not a module maturity assessment.

| Dimension | Score | Rationale |
|-----------|------:|-----------|
| Complexity | 5 | Crosses storage, indexing, receipts, process lifecycle, authentication, and main bootstrap. |
| Importance | 5 | RedDog cannot safely reason or build from stale/lexical evidence. |
| Deferability | 5 | Existing false-current paths block the requested autonomous POC. |
| Impact | 5 | Establishes the evidence substrate boundary for repair and FoundUp-building loops. |
| **Total** | **20 / P0** | Immediate implementation priority. |

**LLME:** Not applied because the scored object is a cross-module work item,
not one module.

## Evidence and Claim Boundary

The validation set must include focused unit/integration suites for HoloIndex
maintenance and receipts, owner lifecycle/HTTP, RedDog query/dispatch/main
bootstrap, downstream operational receipt consumers, static JSON/Python/diff
checks, the WSP_00 tracker, and a WSP_97 structural receipt.

Passing those checks proves this implementation's bounded contracts. It does
not prove unrestricted recursive autonomy, ranking quality for arbitrary
FoundUps, production capacity, or that the pre-merge persistent store matches
the eventual merge commit. It also does not prove a hostile same-user process
cannot squat on literal loopback or extend the stdlib connect/header phase by
trickling bytes; that residual transport risk is accepted only for the trusted,
cooperative Phase-1 host.

## WSP Gap Disposition

- **WSP_97 versus WSP_96:** WSP_97 is the applicable coding-agent execution
  flow. WSP_96 governs WRE skills/wardrobe behavior and supplements that flow;
  it is not the coding-agent or chain-of-reasoning protocol.
- **WSP_62 enforcement gap:** WSP_62 defines file, function, class, and domain
  thresholds, but this repository does not expose one canonical validator or a
  fully specified exemption schema covering functions, classes, configuration,
  and WSP_22 journals. This slice therefore uses scoped AST/line audits and
  explicit temporary YAML ledgers. A separate reviewed protocol/tooling slice
  should standardize and enforce that schema; this security fix does not amend
  an authoritative WSP ad hoc.
- **WSP_81 mirror boundary:** Framework WSP protocols remain authoritative and
  their knowledge copies are backups. 'MODULE_CONCATENATION_GATE.md' is a
  derived annex, not a WSP protocol, so its lack of a knowledge backup is
  correct and no duplicate is created here.
- **WSP_97 receipt boundary:** The execution validator proves structural
  completeness only. Runtime truth remains grounded in the referenced tests,
  repository/receipt proofs, PR checks, and the post-merge activation receipt;
  the JSON receipt alone is not evidence that those side effects occurred.
