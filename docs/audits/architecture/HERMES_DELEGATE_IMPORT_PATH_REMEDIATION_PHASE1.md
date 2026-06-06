# Hermes Delegate Import-Path Remediation (Phase 1)

**Slice:** HERMES_DELEGATE_IMPORT_PATH_REMEDIATION_PHASE1
**Worker-Lane:** W6 - **Author:** 0102 (WSP_00 zen state, WSP_97 Truth Boundary discipline)
**Type:** Targeted code remediation + focused regression tests.
**Base:** origin/main, branch `fix/hermes-delegate-import-path-remediation-phase1`

---

## 1. Mission + Scope

Fix the import-path drift so the real repo-vendored `vendor/hermes-agent/tools/delegate_tool.py` can be
resolved by `_lazy_import_delegate_task` when delegation is explicitly enabled later. The fix uses
`importlib.util.spec_from_file_location` (stdlib) against the hyphenated vendor submodule path,
replacing the broken underscore dotted import.

**NOT in scope:** enabling live Hermes delegation, changing `HERMES_DELEGATE_ENABLED` defaults, renaming
the vendor submodule, mutating the vendor directory, starting any live runtime, adding dependencies.

---

## 2. Predecessor: #757

- **#757** `HERMES_AGENT_RUNTIME_INSTALL_AND_PATH_AUDIT_PHASE1`
- Verdict: `DRIFT_CONFIRMED_BENIGN_TODAY`
- Finding: `hermes_job_executor.py:623` `from vendor.hermes_agent.tools.delegate_tool import delegate_task`
  uses an underscore package path that does not resolve (the real artifact is `vendor/hermes-agent`, a
  hyphenated git submodule directory not addressable by Python dotted import)
- Recommendation: **Option B** - `importlib.util.spec_from_file_location` from the hyphen dir

---

## 3. Pre-State Import/Path Drift

| Item | Pre-state | Classification |
|------|-----------|----------------|
| Lazy import `:623` | `from vendor.hermes_agent.tools.delegate_tool import delegate_task` | BROKEN (underscore) |
| `find_spec("vendor.hermes_agent...")` | `ModuleNotFoundError` | import FAILS |
| Path refs `:31/:739/:2069` | `vendor/hermes-agent/...` (hyphen) | FILESYSTEM correct |
| On-disk file | `vendor/hermes-agent/tools/delegate_tool.py` exists, defines `delegate_task` | PRESENT |
| Tests | Mock `_lazy_import_delegate_task` - never exercise real import | SILENT GAP |

---

## 4. Implementation Summary

### Production change: `hermes_job_executor.py`

1. **Added `import importlib.util`** to stdlib import block (no new dependency).

2. **Added `_resolve_vendor_delegate_path()`**: resolves absolute path to vendored `delegate_tool.py`.
   Resolution order: `workspace_root` -> `__file__` ancestry walk. Returns `Path`.

3. **Added `_load_delegate_task_from_vendor_path()`**: uses `importlib.util.spec_from_file_location`
   + `module_from_spec` + `spec.loader.exec_module` to load from the hyphenated vendor path. Validates
   loaded module has callable `delegate_task`. On failure: sets `_import_error`, returns `False`.

4. **Replaced `_lazy_import_delegate_task` body**: removed the broken `from vendor.hermes_agent...`
   statement. Now delegates to `_load_delegate_task_from_vendor_path()`. Lazy-load caching via
   `_import_attempted` / `_delegate_task_fn` preserved exactly.

### Test file: `test_hermes_delegate_import_path.py` (19 tests)

7 test classes covering all dispatch requirements. Uses `tempfile`, `monkeypatch`, `unittest.mock`.
No test imports the real vendor module. No test executes `delegate_task`. No network/model calls.

---

## 5. Import Resolution Proof

```
# Ran on branch after remediation:
>>> import importlib.util
>>> spec = importlib.util.spec_from_file_location(
...     "delegate_tool", "vendor/hermes-agent/tools/delegate_tool.py"
... )
>>> print("spec_resolved:", spec is not None)
spec_resolved: True
>>> print("spec_origin:", spec.origin)
spec_origin: O:\Foundups-Agent\vendor\hermes-agent\tools\delegate_tool.py
```

The file-path import resolves to the real vendored delegate tool.

---

## 6. Disabled-by-Default Proof

- `is_hermes_delegation_enabled()` reads `HERMES_DELEGATE_ENABLED` (default `"0"`).
- Production singleton `get_executor()` creates `HermesJobExecutor(dry_run=True)`.
- Both gates return `SIMULATED` BEFORE `_lazy_import_delegate_task` is reached.
- `HERMES_DELEGATE_ENABLED` default is UNCHANGED by this remediation.
- Test `test_delegate_default_unchanged` verifies the default.
- Test `test_disabled_does_not_attempt_import` verifies `_import_attempted` stays `False`.

---

## 7. Blocked-Result Behavior Proof

| Scenario | Result | Change? |
|----------|--------|---------|
| `HERMES_DELEGATE_ENABLED=0` | `SIMULATED` | UNCHANGED |
| `dry_run=True` | `SIMULATED` | UNCHANGED |
| Enabled + import fails | `BLOCKED_IMPORT_UNAVAILABLE` | UNCHANGED (same status, clearer error message) |
| Enabled + import succeeds | `BLOCKED_REAL_DELEGATION_NOT_IMPLEMENTED` | UNCHANGED (now reachable when vendor file present) |
| `delegate_task` callable | NOT invoked (no call site in Phase 1) | UNCHANGED |

---

## 8. Test Matrix

| # | Test Class | Count | Coverage |
|---|-----------|-------|----------|
| 1 | `TestBrokenUnderscoreImportNotUsed` | 4 | Source inspection + find_spec failure |
| 2 | `TestFilePathImportResolvesFromHyphenatedPath` | 2 | Synthetic hyphenated path resolution |
| 3 | `TestMissingVendorFileReturnsImportUnavailable` | 2 | Missing file -> BLOCKED_IMPORT_UNAVAILABLE |
| 4 | `TestVendorFileExistsAndDefinesDelegateTask` | 3 | Vendor file shape + path agreement |
| 5 | `TestDisabledPathDoesNotImport` | 2 | HERMES_DELEGATE_ENABLED=0 does not import |
| 6 | `TestEnabledWithGoodDelegateResolvesButBlocked` | 2 | Enabled -> BLOCKED_REAL_DELEGATION_NOT_IMPLEMENTED |
| 7 | `TestNoLiveRuntimeStarted` | 4 | No Hermes/WRE/WSL/Docker/network |
| **Total** | | **19** | |

Regression: existing executor tests 94 passed. Full `wre_core/tests` 1438 passed, 3 skipped, 2 xfailed.

---

## 9. Boundary Proof: No Live Hermes/WRE/WSL/Vendor Mutation

- **No live Hermes started**: no `hermes` CLI invoked; no process spawned; `HERMES_RUNNING` not set.
- **No WRE started**: no WRE runtime, no Docker compose, no WSL sessions.
- **No WSL interaction**: no WSL commands, no `~/.hermes` access.
- **Vendor submodule untouched**: `git status vendor/hermes-agent` shows no changes; no files added,
  modified, or deleted in the submodule.
- **No network calls**: all tests use synthetic data, mocks, or text-shape checks.
- **No model calls**: no LLM API invoked.

---

## 10. Internal Review Verdict

**READY.** The import-path drift mapped by #757 is resolved. The broken `from vendor.hermes_agent...`
(underscore) import statement has been replaced with `importlib.util.spec_from_file_location` against
`vendor/hermes-agent/tools/delegate_tool.py` (hyphen). 19 focused regression tests prove:
underscore import removed from success path, file-path import resolves from hyphenated path, missing
file returns BLOCKED_IMPORT_UNAVAILABLE, vendor file exists and defines delegate_task, disabled path
does not import, enabled path resolves but blocks at Phase 2 gate. Delegation default unchanged.
Vendor submodule untouched. No live runtime started. Full test suite passes.

---

## 11. WSP_97 Truth Boundary Checklist

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | HERMES_IMPORT_PATH_REMEDIATION_ONLY | YES | Only `hermes_job_executor.py` modified; import mechanism changed, no behavior change |
| 2 | NO_LIVE_DELEGATION_ENABLED | YES | No `HERMES_DELEGATE_ENABLED=1` set in production; tests mock or scope env vars |
| 3 | HERMES_DELEGATE_DEFAULT_UNCHANGED | YES | `is_hermes_delegation_enabled()` default `"0"` untouched; test verifies |
| 4 | VENDOR_SUBMODULE_UNTOUCHED | YES | No files in `vendor/hermes-agent/` modified, added, or deleted |
| 5 | WSL_RUNTIME_UNTOUCHED | YES | No WSL commands or `~/.hermes` access |
| 6 | FILE_PATH_IMPORT_USED | YES | `importlib.util.spec_from_file_location` in `_load_delegate_task_from_vendor_path` |
| 7 | BROKEN_UNDERSCORE_IMPORT_NOT_SUCCESS_PATH | YES | `from vendor.hermes_agent...` removed; source inspection tests prove absence |
| 8 | BLOCKED_IMPORT_UNAVAILABLE_PRESERVED | YES | Missing vendor file -> `BLOCKED_IMPORT_UNAVAILABLE`; test proves |
| 9 | TESTS_NO_LIVE_RUNTIME | YES | No Hermes/WRE/WSL/Docker/network/model started; meta-test verifies |
| 10 | NO_DEPENDENCY_CHANGE | YES | `importlib.util` is Python stdlib; no requirements/packaging modified |
| 11 | NO_CI_CHANGE | YES | No CI/CD configuration files modified |
| 12 | NO_WSP_MUTATION | YES | No WSP framework documents modified |
| 13 | NO_SECRET_VALUES | YES | No secrets/credentials in code or tests |
| 14 | NO_CABR_READY | YES | `cabr_ready=False` default untouched |
| 15 | NO_PAYOUT_READY | YES | `payout_ready=False` default untouched |
| 16 | NO_DAO_ACTIVATION | YES | No DAO activation or governance changes |

**WSP 97 Truth Boundary Checklist: 16/16 YES.**

---

*Authored by 0102 (Worker-Lane W6) under WSP_00 zen state and WSP_97 Truth Boundary discipline.
Remediation of #757 import-path drift: replaced broken underscore dotted import with
importlib.util.spec_from_file_location against the real vendor/hermes-agent/tools/delegate_tool.py
hyphenated submodule path. Delegation remains disabled by default. Vendor submodule untouched.
19 regression tests added. Full test suite 1438 passed.*
