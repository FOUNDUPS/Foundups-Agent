# Main Menu AntifaFM Startup Boundary Fix - Phase 1

**Slice**: `MAIN_MENU_ANTIFAFM_STARTUP_BOUNDARY_FIX_PHASE1`
**Worker**: W6
**Agent**: 0102
**Date**: 2026-05-26
**Mode**: Runtime boundary fix (not feature, not refactor)
**Branch**: `feat/main-menu-antifafm-startup-boundary-fix-phase1`
**Base commit**: `349972ba1c6dd65e91fdda9cb916140f31fc159d` (origin/main)
**Predecessor**: PR #720 `OBS_WEBSOCKET_SECRET_LOGGING_FIX_PHASE1` (merge `349972ba1c`)
**WSP Lock**: WSP_00 → WSP_15 → WSP_50 → WSP_64 → WSP_87 → WSP_97 → WSP_22

---

## A. Mission and Scope

Ensure raw `python main.py` performs lightweight startup only:
- Environment preflight
- Logging setup (including OBS logging guard)
- Menu display / menu routing

It must NOT launch AntifaFM, OBS, metadata daemon, boot layer rotator, YouTube broadcast setup, or broadcaster tasks before explicit user action.

**Primary fix**: Remove/ignore legacy `ANTIFAFM_AUTO_START` from global `main.py` menu boot.

---

## B. HoloIndex Retrieval Evaluation

### B.1 Searches Performed

```bash
python holo_index.py --search "ANTIFAFM_AUTO_START main menu boot OBS metadata rotator"
# Result: main_menu.py top hit

python holo_index.py --search "antifaFM explicit launch menu option broadcaster startup"
# Result: antifafm_broadcaster/main.py, youtube_menu.py top hits

python holo_index.py --search "OBS logging guard PR 720 obs_logging_guard"
# Result: audit_logger.py, log_monitor_agent.py top hits
```

### B.2 Retrieval Quality

| Metric | Rating | Notes |
|--------|--------|-------|
| Relevance | Good | Found main_menu.py, youtube_menu.py, preflight.py |
| Ordering | Acceptable | Key files in top 5 |
| Missing | None critical | obs_logging_guard.py found via grep |
| Noise | Low | public/*.html noise filtered |

---

## C. Pre-State Boundary Map

With `ANTIFAFM_AUTO_START=1`, raw `python main.py` triggered:

| Component | Before Fix | Code Location |
|-----------|-----------|---------------|
| OBS Launch | YES | main.py:1271 `launch_obs()` |
| OBS Streaming | YES | main.py:1286 `OBSController().start_streaming()` |
| YouTube Broadcast | YES | main.py:1316 `YouTubeBroadcastManager().create_live_broadcast()` |
| Metadata Daemon | YES | main.py:1441 `DynamicMetadataDaemon()` |
| Boot Layer Rotator | YES | main.py:1473 `rotator_thread.start()` |
| Menu Display | After all above | main.py:1492 `run_main_menu()` |

---

## D. Post-State Boundary Map

With any `ANTIFAFM_AUTO_START` value, raw `python main.py` now triggers:

| Component | After Fix | Code Location |
|-----------|----------|---------------|
| OBS Launch | NO | Removed |
| OBS Streaming | NO | Removed |
| YouTube Broadcast | NO | Removed |
| Metadata Daemon | NO | Removed |
| Boot Layer Rotator | NO | Removed |
| Menu Display | Immediately | main.py:1271 `run_main_menu()` |

---

## E. Explicit AntifaFM Launch Paths Preserved

| Path | Location | Status |
|------|----------|--------|
| YouTube DAE menu option 1 (preflight) | youtube_menu.py:187 | Preserved |
| YouTube DAE menu option 10 (broadcaster) | youtube_menu.py:362 `_handle_antifafm_broadcaster_menu()` | Preserved |
| preflight_check_for_menu() | preflight.py:257 | Preserved |
| run_preflight() | preflight.py (called by above) | Preserved |

---

## F. Refactor Shape Chosen

**Shape**: Delete entire auto-start block (preferred)

**Rationale**:
1. The block was ~225 lines of complex async/threading code
2. All functionality is available via explicit menu paths
3. No CLI flag needed - explicit menu action is the interface
4. Preserves PR #720 guard (already installed at line 136)

**Alternatives Considered**:
- Move to separate function: Rejected - still executes at startup
- Add another env gate: Rejected - doesn't fix the boundary violation
- CLI flag: Rejected - explicit menu paths already exist

---

## G. OBS Logging Guard Preservation Proof

| Evidence | Location | Status |
|----------|----------|--------|
| Guard import | main.py:132-133 | Preserved |
| Guard install call | main.py:136 | Preserved |
| Call position | Line 136 (before line 200) | Early enough |
| obs_controller.py guard | obs_controller.py:41 | Preserved |

The guard is installed BEFORE any OBS client construction because:
1. It's at module level in main.py (line 136)
2. OBSController also calls it at import time (line 41)
3. Auto-start block (which constructed OBS) is now deleted

---

## H. Test Matrix

| Test | Purpose | Result |
|------|---------|--------|
| `test_main_py_does_not_execute_on_antifafm_auto_start_env` | No execution gate | PASS |
| `test_main_py_does_not_import_obs_controller_at_module_level_for_autostart` | No OBS auto-start pattern | PASS |
| `test_main_py_does_not_start_metadata_daemon_at_startup` | No daemon at startup | PASS |
| `test_main_py_does_not_start_boot_rotator_at_startup` | No rotator at startup | PASS |
| `test_main_py_documents_boundary_fix` | Slice ID documented | PASS |
| `test_youtube_menu_has_broadcaster_handler` | Explicit path exists | PASS |
| `test_preflight_module_exists` | Preflight functions exist | PASS |
| `test_obs_logging_guard_module_exists` | Guard module exists | PASS |
| `test_main_py_installs_logging_guard_early` | Guard at line <200 | PASS |
| `test_obs_controller_module_imports_guard` | OBS imports guard | PASS |
| `test_env_example_documents_auto_start_deprecation` | Deprecation noted | PASS |
| `test_no_real_secrets_in_test_file` | No real secrets | PASS |

**Total**: 12/12 PASS

**Additional Test Suites Verified**:
- test_obs_logging_guard.py: 4/4 PASS
- test_obs_controller_startup.py: 11/11 PASS
- test_boot_layer_rotator.py: 16/16 PASS
- test_gcc_shipping_tracker.py: 22/22 PASS

---

## I. Internal Review Verdict

**Verdict**: READY

**Checklist**:
- [x] Auto-start block removed from main.py
- [x] ANTIFAFM_AUTO_START env var ignored at menu boot
- [x] Explicit launch paths preserved and tested
- [x] PR #720 OBS logging guard preserved
- [x] .env.example documents deprecation
- [x] No live OBS/network calls in tests
- [x] No real secrets in code/tests/audit
- [x] All 12 boundary tests pass
- [x] All existing tests pass

---

## J. Deferred Work

| Item | Reason | Owner |
|------|--------|-------|
| LM Studio boundary | Separate concern | Future slice |
| Historical OBS password rotation/purge | Operational, not code | 012 manual |
| Broader dependency security queue | Separate audit | Security team |

---

## K. WSP_97 Truth Boundary Checklist

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | MAIN_MENU_STARTUP_BOUNDARY_ONLY | YES | Only main.py startup path changed |
| 2 | ANTIFAFM_AUTO_START_NOT_HONORED_ON_MENU_BOOT | YES | if-block deleted from main.py |
| 3 | PRESERVES_PR_720_OBS_LOGGING_GUARD | YES | main.py:136 unchanged |
| 4 | NO_REGRESSION_ON_EXPLICIT_ANTIFAFM_LAUNCH | YES | youtube_menu.py paths intact |
| 5 | NO_OBS_CLIENT_CONSTRUCTION_ON_MENU_BOOT | YES | OBSController import deleted |
| 6 | NO_BROADCASTER_THREAD_ON_MENU_BOOT | YES | Thread code deleted |
| 7 | NO_METADATA_WRITER_ON_MENU_BOOT | YES | Daemon code deleted |
| 8 | NO_BOOT_LAYER_ROTATOR_ON_MENU_BOOT | YES | Rotator code deleted |
| 9 | NO_YOUTUBE_BROADCAST_SETUP_ON_MENU_BOOT | YES | Broadcast code deleted |
| 10 | NO_LIVE_OBS_CONNECT_IN_TESTS | YES | File-based pattern tests only |
| 11 | NO_NETWORK_CALL_IN_TESTS | YES | No imports that trigger network |
| 12 | NO_DOTENV_READ_IN_TESTS | YES | File content checks only |
| 13 | NO_REAL_SECRET_VALUES_ANYWHERE | YES | test_no_real_secrets_in_test_file passes |
| 14 | SYNTHETIC_TEST_VALUES_ONLY | YES | No env values in tests |
| 15 | NO_DEPENDENCY_CHANGE | YES | Only asyncio import removed |
| 16 | NO_CI_CHANGE | YES | No workflow changes |
| 17 | NO_WSP_FRAMEWORK_MUTATION | YES | No WSP_*.md changed |
| 18 | NO_REGISTRY_MUTATION | YES | No registry files changed |
| 19 | NO_CATALOG_MUTATION | YES | No catalog files changed |
| 20 | NO_MANIFEST_MUTATION | YES | No manifest files changed |
| 21 | NO_PROJECTION_MUTATION | YES | No projection files changed |
| 22 | NO_PUBLIC_SURFACE_MUTATION | YES | No public/ changes |
| 23 | NO_DNS_CHANGE | YES | No DNS configuration changed |
| 24 | NO_TOKEN_ASSIGNMENT | YES | No token changes |
| 25 | NO_CABR_READY | YES | Not a CABR slice |
| 26 | NO_PAYOUT_READY | YES | Not a payout slice |
| 27 | NO_DAO_ACTIVATION | YES | No DAO changes |

**Verdict**: PASS (27/27)

---

## L. Files Changed

| File | Change | Lines |
|------|--------|-------|
| `main.py` | Remove auto-start block, remove asyncio import | -226, +8 |
| `.env.example` | Mark ANTIFAFM_AUTO_START deprecated | +2, -1 |
| `modules/platform_integration/antifafm_broadcaster/tests/test_main_menu_startup_boundary.py` | NEW | +175 |
| `modules/platform_integration/antifafm_broadcaster/ModLog.md` | Add V3.5.0 entry | +63 |
| `modules/platform_integration/antifafm_broadcaster/tests/TestModLog.md` | Add test entry | +33 |
| `docs/audits/architecture/MAIN_MENU_ANTIFAFM_STARTUP_BOUNDARY_FIX_PHASE1.md` | NEW (this file) | ~250 |

---

**Worker**: W6
**Slice**: MAIN_MENU_ANTIFAFM_STARTUP_BOUNDARY_FIX_PHASE1
**WSP Lock**: WSP_00 → WSP_15 → WSP_50 → WSP_64 → WSP_87 → WSP_97 → WSP_22
