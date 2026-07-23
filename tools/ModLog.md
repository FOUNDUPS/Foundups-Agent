# Tools ModLog

## 2026-07-24 - WSP97_REPOSITORY_EVIDENCE_V11_PHASE1

- Split repository path and Git-base verification into `tools/wsp97_repository_evidence.py`; validator functions remain below the WSP 62 50-line limit.
- Default admission now requires receipt v1.1, explicit exact Git root, valid ancestor base, canonical tracked exact-case WSP paths, and `wsps_applied` coverage.
- All evidence outside `retrieve_wsps` remains opaque; no URL or non-WSP path is opened.
- Added distinct non-admitting legacy diagnostics and exit codes 0 (v1.1 compliant), 1 (non-compliant/non-admitting), and 2 (unreadable setup).
- Added pre-parse receipt and evidence-shape/size caps. Malformed or over-limit evidence stops before repository processes.
- Cheap exact context/base/path/WSP syntax checks stop malformed receipts before root resolution or Git; missing context is structurally incomplete.
- Root components are lstatted before all other root operations. Git inspection has a shared 72-call budget and 5-second timeout. Output is redirected to tempfiles to avoid RAM amplification; 65,536 bytes is checked after process exit as an accepted-output cap, not enforced while the tempfile is written. Exact-path queries never scan the full tracked-file catalog.

## 2026-07-17 - WSP97_EXECUTION_RECEIPT_VALIDATOR_PHASE1

- Added `tools/wsp97_execution_validator.py` for deterministic structural validation of WSP 97 JSON receipts.
- Derives seven mantra stages from nine action-evidence slots plus applied-WSP/compliance evidence.
- Returns machine-readable JSON and exit codes 0 (complete), 1 (non-compliant), or 2 (input/contract error).
- Truth boundary: evidence pointers are not resolved; no private reasoning or runtime side effect is verified.

## 2026-07-13 - WRE_WORKTREE_CWD_HAZARD_GUARD_PHASE1

- Added `tools/hooks/pre_commit_worktree_cwd_guard.py`, a local pre-commit guard that blocks direct commits from the shared `main` checkout unless `FOUNDUPS_ALLOW_SHARED_MAIN_COMMIT=1` is set.
- Added focused tests for shared-main rejection, explicit override, worker worktrees, Claude worktrees, detached unsafe checkouts, and detached clean build worktrees.
- Documented that the hook complements existing governed WRE `validate_wre_worker_operation_cwd(...)` checks and cannot intercept raw `git add`.
