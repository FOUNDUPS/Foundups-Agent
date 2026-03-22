# Dependency Launcher Module - ModLog

**Module:** infrastructure/dependency_launcher
**WSP Reference:** WSP 22 (ModLog Protocol)

---

## Change Log

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









