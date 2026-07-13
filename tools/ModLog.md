# Tools ModLog

## 2026-07-13 - WRE_WORKTREE_CWD_HAZARD_GUARD_PHASE1

- Added `tools/hooks/pre_commit_worktree_cwd_guard.py`, a local pre-commit guard that blocks direct commits from the shared `main` checkout unless `FOUNDUPS_ALLOW_SHARED_MAIN_COMMIT=1` is set.
- Added focused tests for shared-main rejection, explicit override, worker worktrees, Claude worktrees, detached unsafe checkouts, and detached clean build worktrees.
- Documented that the hook complements existing governed WRE `validate_wre_worker_operation_cwd(...)` checks and cannot intercept raw `git add`.
