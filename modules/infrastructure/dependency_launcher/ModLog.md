# Dependency Launcher Module - ModLog

**Module:** infrastructure/dependency_launcher
**WSP Reference:** WSP 22 (ModLog Protocol)

---

## Change Log

### 2026-08-02: Governed Runtime Compatibility Evidence Supplier

**Slice:** `OPENCLAW_HERMES_QWEN_GOVERNED_FRESHNESS_EVIDENCE_SUPPLIER_PHASE1`

- Extended the existing OpenClaw ecosystem watchlist refresh instead of
  creating a second network updater.
- Added exact installed-observation and expected-binding source receipts with
  recomputed IDs, bounded ASCII fields, TTL/future-skew checks, and exact
  component-set enforcement.
- Restricted network retrieval to the official OpenClaw and Hermes latest
  release API endpoints, with redirect and response-size rejection.
- Required Qwen general, Qwen code, and inference-backend expectations to come
  from promoted runtime-binding references rather than model-name inference.
- Reused the canonical runtime-artifact safety layer for confined reads and
  descriptor-verified, locked replacement outside the repository.
- Boundary: advisory evidence only; no install/update, command execution,
  model load, route change, HoloIndex mutation, or update authority.
- Truth boundary: source self-hashes prove integrity, not signer identity.
  Integrity-only envelopes can report `OBSERVED_MATCH`/`OBSERVED_DRIFT`, but
  the overall receipt remains `NOT_READY` with
  `evidence_authentication_not_verified`; recomputed hashes never yield
  authenticated `CURRENT`.
- Rejected supply/output path aliasing before retrieval and added a regression
  that exercises the production redirect-handler construction.
- WSP references: WSP 00, WSP 15, WSP 22, WSP 50, WSP 62, WSP 84, WSP 97.

Focused validation covers recomputed-hash forgery, tampering, expiry,
source-set mismatch, unofficial release URLs, redirects, oversized responses,
prior-cache preservation, path aliasing, and the absence of
execution/model-loading surfaces.

---

### 2026-08-02: OpenClaw/Hermes/Qwen Runtime Compatibility Advisory

**Slice:** `OPENCLAW_HERMES_QWEN_RUNTIME_FRESHNESS_AND_COMPATIBILITY_RECEIPT_PHASE1`

- Added a typed, digest-bound compatibility receipt for OpenClaw, Hermes,
  general/coding Qwen bindings, and the inference backend.
- Added a bounded off-repo evidence loader and a nonblocking startup advisory.
- Reused the existing WRE ecosystem-watchlist and model-promotion direction;
  this slice does not create another updater or model selector.
- Fail-closed evidence rules cover schema, self-integrity, TTL, future timestamps,
  duplicate/missing components, component verification, and allowlisted scope.
- Boundary: no network, package update, model download/load, inference, route
  mutation, process execution, HoloIndex maintenance, or startup blocking.
- WSP references: WSP 00, WSP 15, WSP 22, WSP 50, WSP 62, WSP 84, WSP 97.

Focused validation: receipt/advisory tests plus the full `main.py` startup
bootstrap suite.

---

### 2026-06-17: Non-Destructive Attach Recovery - Open a Tab, Do NOT Kill (Phase 1)

**By:** 0102 (Worker-Lane: ATTACH-AUTHOR)
**Slice:** BROWSER_ATTACH_RECOVERY_NO_KILL_PHASE1
**WSP References:** WSP 22 (ModLog), WSP 50 (Pre-Action), WSP 84 (Code Reuse), WSP 87 (Navigation), WSP 97 (Truth Boundary)

**Problem (012 live-observed):** When the operator-prepared Chrome on 9222 is UP
(DevTools /json/version works) but has NO discoverable page target (/json
page-list empty -> Selenium raises "unable to discover open pages"),
`connect_chrome_with_retry` ran `taskkill /F /IM chrome.exe` and relaunched a
fresh Chrome. This DESTROYED the operator's authenticated/prepared window,
relaunched a Chrome whose auth/active-channel state is uncertain, and confounded
every live test. Edge had the identical destructive path.

**Solution (NO_KILL contract):** On the discover-pages (no-page) condition, RECOVER
NON-DESTRUCTIVELY:
1. New helper `open_devtools_page(port, url='about:blank')` opens a normal tab via
   the DevTools HTTP endpoint - HTTP PUT `/json/new?about:blank` (modern Chrome/Edge)
   with GET fallback. Reuses the existing `urllib.request` + `/json` pattern from
   `is_devtools_responding` (no new HTTP machinery, no new dependency).
2. `connect_chrome_with_retry` / `connect_edge_with_retry` no-page branch now calls
   `open_devtools_page`, re-checks `is_devtools_responding`, and RETRIES the attach.
3. If a tab cannot be opened (endpoint blocked), they log a CLEAR actionable error
   ("open a normal tab in the debug Chrome/Edge, or relaunch with
   --remote-allow-origins") and return None - NEVER taskkill. The success attach
   path is unchanged.

**Reuse:** Checked for an existing DevTools open-tab helper. `foundups_selenium/src/
devtools_mcp_adapter.py:new_page()` (:510) exists but requires an already-initialized
driver/MCP backend (`self._driver.execute_script("window.open")`), so it CANNOT
recover the pre-attach no-driver case. No repo code uses `/json/new` or
`Target.createTarget`. Reused the in-file urllib/`/json` HTTP pattern instead.

**Out of scope / follow-up:** The genuinely-DevTools-DOWN path (port not answering
/json/version twice) still taskkills+relaunches; left in place, logged loudly, and
tracked as **BROWSER_ATTACH_RECOVERY_DEVTOOLS_DOWN_PHASE2**.

**Files Changed:**
- `src/dae_dependencies.py`: added `open_devtools_page()`; rewrote the no-page branch
  of `connect_chrome_with_retry` and `connect_edge_with_retry` to be non-destructive.
- `tests/test_attach_recovery_no_kill.py`: 11 mock-only tests (no live browser).
- `INTERFACE.md`: documented `open_devtools_page` + recovery behavior.

**Tests:** `python -m pytest modules/infrastructure/dependency_launcher/` -> 11 passed.
No-kill proof: the core `test_*_no_kill_on_discover_pages` tests FAIL on the base
SHA (which invokes `taskkill /F /IM chrome.exe` at the discover-pages branch and
has no `open_devtools_page`); they PASS on this change.

**HONEST LIVE GAP:** Whether PUT/GET `/json/new` actually opens a discoverable tab
on real Chrome 149 is MOCK-validated ONLY. 012 live-validates by re-running with an
operator-prepared 9222 that has no normal tab: expect a NEW tab opened + successful
attach + NO "killing stale Chrome" in the logs.

---

### 2026-03-22: Multi-Model Auto-Loading (WSP 77 Agent Coordination)

**By:** 0102
**WSP References:** WSP 22 (ModLog), WSP 77 (Agent Coordination), WSP 84 (Code Reuse)

**Problem:** LM Studio launched but only UI-TARS model was auto-loaded. Gemma (pattern matching) and Qwen (intelligent reasoning) required manual loading.

**Solution:** Added multi-model auto-loading for WSP 77 Agent Coordination:

1. **`_load_gemma_model()`** - WSP 77 Phase 1: Fast pattern matching (50-100ms)
2. **`_load_qwen_model()`** - WSP 77 Phase 2: Intelligent reasoning (200-500ms)
3. **`load_all_models()`** - Orchestrates loading of all 3 models
4. **Updated `launch_lm_studio()`** - Now calls `load_all_models()` instead of just UI-TARS

**Model Configuration (ENV vars):**
| Variable | Default | Purpose |
|----------|---------|---------|
| `UI_TARS_MODEL_ID` | `lmstudio-community/UI-TARS-1.5-7B-GGUF` | Vision automation |
| `GEMMA_MODEL_ID` | `gemma-270m` | Fast pattern matching |
| `QWEN_MODEL_ID` | `qwen3.5-4b` | Intelligent reasoning |

**Files Changed:**
- `src/dae_dependencies.py`: Added model loading functions and env vars

**Test:**
```python
from modules.infrastructure.dependency_launcher.src.dae_dependencies import load_all_models
results = load_all_models()
# {'ui_tars': True, 'gemma': True, 'qwen': True}
```

**Impact:**
- All AI models auto-load when LM Studio starts
- Enables WSP 77 multi-phase agent coordination
- LinkedIn profile evaluation now uses Qwen for intelligent decisions

---

### 2026-02-22: Browser Connection Retry Helpers (Timing Race Fix)

**By:** 0102
**WSP References:** WSP 22 (ModLog), WSP 27 (DAE Architecture), WSP 50 (Pre-Action Verification)

**Problem:** Browser connections were failing due to timing race conditions. The system would:
1. Detect DevTools port open
2. Attempt Selenium connection
3. Fail because browser wasn't fully ready yet

The `is_devtools_responding()` HTTP check wasn't sufficient - the browser could respond to HTTP but not be ready for WebDriver.

**Solution:** Added robust connection helpers with retry logic:

1. **`connect_chrome_with_retry()`**:
   - Verifies DevTools responding before connection attempt
   - Retries up to 3 times with 2s delay
   - Auto-relaunches Chrome on persistent failure
   - Verifies connection is alive after connecting

2. **`connect_edge_with_retry()`**:
   - Same pattern for Edge browser

**Files Updated:**
- `src/dae_dependencies.py`: Added `connect_chrome_with_retry()` and `connect_edge_with_retry()` helpers
- `modules/communication/livechat/src/multi_channel_coordinator.py`: Uses new helpers for Chrome/Edge
- `modules/ai_intelligence/video_indexer/src/studio_ask_indexer.py`: Uses new helpers
- `modules/platform_integration/youtube_shorts_scheduler/src/scheduler.py`: Uses new helpers

**Impact:**
- Eliminates "session not created: cannot connect to chrome" timing errors
- Auto-recovery from browser crashes during connection
- Consistent behavior across all browser-using modules

---

### 2026-01-23: Session Restore Prevention (Multi-Tab Fix)

**By:** 0102
**WSP References:** WSP 22 (ModLog), WSP 27 (DAE Architecture)

**Problem:** Chrome and Edge were restoring previous session tabs, causing 3+ tabs to open instead of just the YouTube Studio URL. This caused confusion during channel rotation.

**Solution:** Added `--no-restore-session-state` flag to both Chrome and Edge launch commands:
- Prevents browser from restoring tabs from previous session
- Ensures only the YouTube Studio URL is loaded on launch
- Consistent behavior between fresh launches and restarts

**Files Changed:**
- `src/dae_dependencies.py`: Added `--no-restore-session-state` to Chrome (line 143) and Edge (line 200) launch commands

---

### 2025-12-13: ASCII-Safe Logging + `main.py --deps` Entry Point

**By:** 0102  
**WSP References:** WSP 12 (Dependency Management), WSP 27 (DAE Architecture), WSP 88 (Windows Unicode safety)

**Problem:** Emoji/VS16 characters in dependency logs could trigger `UnicodeEncodeError` on some Windows terminals, and operators needed a one-shot way to start dependencies without launching a full DAE.

**Solution:**
- Normalized dependency output to ASCII (`READY`/`NOT READY`, `[OK]`, `[WARN]`).
- Exposed dependency launcher via `main.py --deps` and menu option `15` for quick bring-up.

**Files Modified:**
- `modules/infrastructure/dependency_launcher/src/dae_dependencies.py`

### 2025-12-12: LM Studio Auto-Discovery (E:\ Support)

**By:** 0102
**WSP References:** WSP 27 (DAE Architecture), WSP 12 (Dependency Management)

**Problem:** YouTube DAE dependency launcher could not auto-start LM Studio when installed outside the default `C:` path.

**Solution:** Add `resolve_lm_studio_path()` with common-path discovery (including `E:\\LM_studio\\LM Studio\\LM Studio.exe`) and use it in `launch_lm_studio()`.

**Files Modified:**
- `modules/infrastructure/dependency_launcher/src/dae_dependencies.py`

### Module Creation: Auto-Launch Chrome + LM Studio for YouTube DAE

**By:** 0102
**WSP References:** WSP 27 (DAE Architecture), WSP 80 (Cube-Level Orchestration)

**Status:** ✅ **MODULE CREATED**

**Purpose:**
Auto-launches dependencies required for YouTube DAE comment engagement when DAE starts:
1. Chrome with remote debugging port 9222 (for Selenium/UI-TARS)
2. LM Studio on port 1234 (for UI-TARS vision model - optional)

**Files Created:**

1. **[dae_dependencies.py](src/dae_dependencies.py)**
   - `ensure_dependencies()` - Main entry point, checks and launches all deps
   - `launch_chrome()` - Launches Chrome with debug port and YouTube profile
   - `launch_lm_studio()` - Launches LM Studio (optional)
   - `is_chrome_running()` - Port 9222 check
   - `is_lm_studio_running()` - Port 1234 check
   - `get_dependency_status()` - Status without launching

2. **[README.md](README.md)** - Module documentation

**Integration in auto_moderator_dae.py:**

```python
# Phase -2: Launch dependencies (Chrome + LM Studio for comment engagement)
try:
    from modules.infrastructure.dependency_launcher.src.dae_dependencies import ensure_dependencies
    dep_status = await ensure_dependencies(require_lm_studio=True)
    if not dep_status.get('chrome'):
        logger.warning("[DEPS] Chrome not ready - comment engagement may fail")
except ImportError:
    logger.debug("[DEPS] Dependency launcher not available")
```

**Configuration (Environment Variables):**

| Variable | Default | Description |
|----------|---------|-------------|
| `CHROME_PATH` | `C:\Program Files\Google\Chrome\Application\chrome.exe` | Chrome executable |
| `FOUNDUPS_CHROME_PORT` | `9222` | Chrome debug port |
| `CHROME_PROFILE_PATH` | `O:/Foundups-Agent/.../youtube_move2japan/chrome` | Chrome profile |
| `LM_STUDIO_PATH` | `C:\Users\user\AppData\Local\Programs\LM Studio\LM Studio.exe` | LM Studio |
| `LM_STUDIO_PORT` | `1234` | LM Studio API port |

**NAVIGATION.py Entries Added:**

```python
# DAE Dependency Launcher (auto-start Chrome + LM Studio)
"ensure dae dependencies": "modules/infrastructure/dependency_launcher/src/dae_dependencies.py:ensure_dependencies()",
"launch chrome debug port": "modules/infrastructure/dependency_launcher/src/dae_dependencies.py:launch_chrome()",
"launch lm studio": "modules/infrastructure/dependency_launcher/src/dae_dependencies.py:launch_lm_studio()",
"check dependency status": "modules/infrastructure/dependency_launcher/src/dae_dependencies.py:get_dependency_status()",
```

**0102 Directive:** Dependencies are orchestrated, not installed. ✊✋🖐️

---









