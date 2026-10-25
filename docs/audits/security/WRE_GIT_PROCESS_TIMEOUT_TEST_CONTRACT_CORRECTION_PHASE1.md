# Assumption Audit: WRE Git Process Timeout Test Contract Correction Phase 1

**Date:** 2026-08-29
**Base commit:** `7269deb66f638cc6bbb8239aecf0c8b5ae6b8d22`
**Owner:** 0102 architect
**Decision:** CORRECT THE TEST; PRESERVE PRODUCTION BEHAVIOR

## 1. Problem Statement

- **What:** `test_wre_git_commit_archive.py` called the removed private helper
  `wre_git_bounded_io._terminate_reader` after the process pump moved to
  `wre_git_process_io.run_bounded_process`.
- **Why:** The inherited failure invalidated the adjacent WRE baseline needed
  to judge the RedDog Phase 2C packaging materializer.
- **Who authorized:** 012 directed continued autonomous RedDog construction
  under WSP_00 and WSP_97. The canonical WSP 15 allocation is 20/P0.
- **Boundary:** This transaction changes one test contract and its audit
  memory. It does not change production process behavior, runtime authority,
  Holo routes, RedDog activation, or packaging materialization.

## 2. Retrieved Evidence and Quality

The governed owner query returned `ok=true`, `freshness=CURRENT`, exact base
HEAD, `index_gap_detected=false`, and `no_holoindex_reindex_performed=true`.
It ranked the exact current process-pump module and stale test first. Direct
reads of both files and Git history confirmed that commit `dff50350e` removed
the private helper while leaving the old direct test call behind. Retrieval
was precise, current, non-duplicative, and sufficient; no Holo repair was
needed.

## 3. Assumptions

| ID | Assumption | Evidence | Confidence |
|---|---|---|---|
| A1 | Production timeout cleanup is now owned by `run_bounded_process`. | Current `wre_git_process_io.py` call graph | HIGH |
| A2 | Restoring the removed private helper would create compatibility debt. | Git history and current public `__all__` | HIGH |
| A3 | A public-behavior test can prove the same kill/reap/close/join invariant. | Injected process/thread falsifier | HIGH |

## 4. Failure Modes

| ID | Failure Mode | Likelihood | Impact | Mitigation |
|---|---:|---:|---:|---|
| F1 | Test passes without traversing timeout cleanup. | MEDIUM | HIGH | Make the fake process raise `TimeoutExpired` on the public call. |
| F2 | Test binds another private seam and drifts again. | MEDIUM | MEDIUM | Invoke only `run_bounded_process`; inject dependencies at module boundaries. |
| F3 | Production behavior changes while repairing a test. | LOW | HIGH | Do not edit `src/`; run the full archive test module. |
| F4 | Aggregate pass counts mask a different failure. | MEDIUM | HIGH | Record exact command and failure signature, then rerun exact identifiers. |

## 5. Alternatives Considered

| Alternative | Why Rejected |
|---|---|
| Restore `_terminate_reader` | Recreates a dead private API and duplicates `_terminate_threads`. |
| Patch `_terminate_threads` directly | Repeats the private-seam coupling that caused the drift. |
| Delete the timeout test | Removes a load-bearing process cleanup falsifier. |

## 6. Decision Record

**PROCEED** with a public `run_bounded_process(...)` timeout test that proves
kill, reap, both pipe closes, thread join, and propagation of
`subprocess.TimeoutExpired`. Validate the focused module, adjacent bounded Git
I/O suites, WSP 62 differential size, WSP 15 receipt, and WSP 97 receipt before
merge. Resume Phase 2C only on the corrected exact main.
