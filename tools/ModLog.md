# Tools ModLog

## 2026-07-17 - WSP97_EXECUTION_RECEIPT_VALIDATOR_PHASE1

- Added `tools/wsp97_execution_validator.py` for deterministic structural validation of WSP 97 JSON receipts.
- Derives seven mantra stages from nine action-evidence slots plus applied-WSP/compliance evidence.
- Returns machine-readable JSON and exit codes 0 (complete), 1 (non-compliant), or 2 (input/contract error).
- Truth boundary: evidence pointers are not resolved; no private reasoning or runtime side effect is verified.

## 2026-07-13 - WRE_WORKTREE_CWD_HAZARD_GUARD_PHASE1

- Added `tools/hooks/pre_commit_worktree_cwd_guard.py`, a local pre-commit guard that blocks direct commits from the shared `main` checkout unless `FOUNDUPS_ALLOW_SHARED_MAIN_COMMIT=1` is set.
- Added focused tests for shared-main rejection, explicit override, worker worktrees, Claude worktrees, detached unsafe checkouts, and detached clean build worktrees.
- Documented that the hook complements existing governed WRE `validate_wre_worker_operation_cwd(...)` checks and cannot intercept raw `git add`.
