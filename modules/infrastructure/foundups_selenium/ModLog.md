# ModLog — FoundUps Selenium

## V1.2.0 — Shadow-DOM deep finder (returns real WebElements)

**Date**: 2026-06-17
**WSP Compliance**: WSP 3 (infrastructure), WSP 11 (Interface), WSP 84 (Reuse)

### Summary
NEW `src/shadow_dom_finder.py`: `find_deep` / `shadow_query` / `first_deep`
pierce nested shadow roots and return REAL Selenium WebElements (the matched DOM
node is RETURNED by `execute_script`, so `human_type` + `.click()` keep working).
Flat `find_element` does not pierce shadow roots; YouTube Studio's DOM is
shadow-rooted, so flat selectors silently fail even when the element exists.

WSP 84 REUSE: the recursive `findInShadow` traversal is the SAME algorithm
already used by the YT comment-reply path
(`modules/communication/video_comments/skillz/tars_like_heart_reply/src/reply_executor.py`
`findInShadow`); the difference is the return contract (a node, not text/boolean).
`shadow_query` resolves a CHAIN across shadow boundaries (e.g.
`ytcp-creator-chat-trigger -> ytcp-icon-button`). Exported via `src/__init__.py`.
Consumed by `ai_intelligence/video_indexer/studio_ask_indexer.py`
(STUDIO_ASK_SHADOW_DOM_SELECTORS_PHASE1).

### Tests
- NEW `tests/test_shadow_dom_finder.py` (7 mock tests): flat-fails/shadow-finds,
  flat fallback when no shadow match, cross-shadow chain resolution, first_deep
  ordering. NO live browser.

## V1.1.0 — Chrome DevTools MCP Adapter

**Date**: 2026-03-18
**WSP Compliance**: WSP 72 (Module Independence), WSP 91 (Observability), WSP 11 (Interface)

### Summary

Added BrowserAdapter class that provides unified interface for Selenium AND Chrome DevTools MCP. Enables gradual migration from Selenium to MCP while maintaining backwards compatibility.

### New Files

- `src/devtools_mcp_adapter.py`:
  - `MCPClient`: Connects to Chrome DevTools MCP server via stdio
  - `BrowserAdapter`: Unified interface with auto-detection
  - `BrowserResult`: Standardized result dataclass
  - `get_browser_adapter()`: Factory function

### API

```python
from modules.infrastructure.foundups_selenium import BrowserAdapter, get_browser_adapter

# Auto-detect best backend
adapter = get_browser_adapter(backend="auto")
await adapter.initialize()

# Unified operations work on both backends
await adapter.navigate("https://youtube.com")
await adapter.click("button#submit")
await adapter.type_text("input#search", "hello")
result = await adapter.take_screenshot()

# Check which backend is active
print(adapter.backend)  # "mcp" or "selenium"
```

### Methods

| Method | MCP Tool | Selenium Equivalent |
|--------|----------|---------------------|
| `navigate(url)` | `navigate_page` | `driver.get()` |
| `click(selector)` | `click` | `find_element().click()` |
| `type_text(selector, text)` | `type_text` | `send_keys()` |
| `fill(selector, value)` | `fill` | `clear()` + `send_keys()` |
| `hover(selector)` | `hover` | `ActionChains.move_to_element()` |
| `press_key(key)` | `press_key` | `send_keys(Keys.X)` |
| `take_screenshot()` | `take_screenshot` | `get_screenshot_as_png()` |
| `evaluate_script(js)` | `evaluate_script` | `execute_script()` |
| `wait_for(selector)` | `wait_for` | `WebDriverWait` |
| `new_page()` | `new_page` | `window.open()` |
| `close_page()` | `close_page` | `window.close()` |
| `list_pages()` | `list_pages` | `window_handles` |

### Phase 1 of Chrome DevTools MCP Integration

See: `wre_core/docs/CHROME_DEVTOOLS_MCP_INTEGRATION_TASK.md`

---

## V0.8.1 — LinkedIn Registry Migration

**Date**: 2026-03-07
**WSP Compliance**: WSP 22 (ModLog), WSP 60 (Module Memory), WSP 3 (Shared Utilities)

### Changes
- Migrated hardcoded LinkedIn profile mappings to central registry
- `src/browser_manager.py`: Profile mappings now built dynamically from registry

### Impact
- LinkedIn browser profiles now managed via `LINKEDIN_ACCOUNTS_JSON` env var

---

## V0.8.0 — Cross-Process Browser Reconnection (CDP Support)

**Date**: 2026-02-24
**WSP Compliance**: WSP 3 (Architecture), WSP 77 (AI Coordination)

### Problem
When CLI restarts (new Python process), the BrowserManager singleton loses track of browsers running from previous process. It tries to create a new Chrome with same profile → "session not created: Chrome instance exited" error.

### Solution: CDP-Based Cross-Process Reconnection

1. **Debug Port**: Chrome now starts with `--remote-debugging-port` for reconnection
2. **Session Files**: Port/profile info saved to `foundups_selenium/data/sessions/*.json`
3. **Reconnection Logic**: On `get_browser()`:
   - Check in-process `_browsers` dict first
   - Check session file for existing port
   - If Chrome running on port → connect via `debuggerAddress` CDP
   - Only create new browser if nothing found

### Changes
- Added `_get_debug_port()`: Deterministic port per profile (9222-9322 range)
- Added `_save_session()`: Persist port info to JSON
- Added `_load_session()`: Load session on startup
- Added `_is_browser_running()`: CDP health check (GET /json/version)
- Added `_connect_to_existing()`: Connect via `debuggerAddress` option

### Migration
**IMPORTANT**: Existing running Chrome browsers were NOT started with debug ports.
You must close all Chrome windows first, then restart the flow.
Future runs will reconnect automatically.

### Files Changed
- `src/browser_manager.py`: Full CDP support

---

## V0.7.0 — Unified Typing Module (FoundupsTyper)

**WSP Compliance**: WSP 49 (Module Structure), WSP 77 (AI Coordination)

### Problem
Four separate typing implementations existed across the codebase:
- `human_behavior.py` - send_keys() for standard inputs
- `reply_executor.py` - JS injection for YouTube contenteditable
- `x_anti_detection_poster.py` - inline send_keys() implementation
- LinkedIn poster - delegated to human_behavior

This duplication caused:
- Inconsistent typing speeds across platforms
- Maintenance burden (4 places to update)
- No auto-detection of element type

### Solution: FoundupsTyper (`src/foundup_typer.py`)

**Single lego piece** that unifies all typing operations:
- **Auto-detects element type**: input/textarea → send_keys, contenteditable → JS injection
- **Configurable via env vars**: FOUNDUP_TYPING_SPEED, FOUNDUP_TYPO_RATE, FOUNDUP_HESITATION_RATE
- **Async + Sync APIs**: Works with both asyncio DAEs and synchronous code
- **Anti-detection features**: Typos (5%), hesitations (3%), variable delays

### Usage
```python
from modules.infrastructure.foundups_selenium.src import FoundupsTyper, get_typer

# Async
typer = FoundupsTyper(driver)
await typer.type_text(element, "Hello world!")

# Sync
typer.type_text_sync(element, "Hello world!")
```

### Speed Configuration
```bash
FOUNDUP_TYPING_SPEED=0.5   # 2x faster
FOUNDUP_TYPING_SPEED=1.0   # Normal (default)
FOUNDUP_TYPING_SPEED=2.0   # 2x slower
```

### Migration Path
Replace existing typing calls:
- `reply_executor.py` → use FoundupsTyper
- `x_anti_detection_poster.py` → use FoundupsTyper
- Any new DAE → use FoundupsTyper

---

## V0.6.0 — Anti-Detection Infrastructure (2025-12-15)

**Integration Type**: 🔴 CRITICAL - YouTube Automation Detection Hardening
**WSP Compliance**: WSP 49 (Platform Integration Safety), WSP 77 (AI Coordination), WSP 91 (Observability)

### Problem
YouTube detected automation via:
- DOM manipulation (`execute_script()` 6 uses)
- Fixed timing patterns (0.8s, 1s, 5s always identical)
- Systematic behavior (every comment processed identically)
- No mouse movement (clicks at exact coordinates)
- navigator.webdriver flag exposed

Detection probability: **85-95%** (CRITICAL)

### Additions

**1. HumanBehavior Module** (`src/human_behavior.py` - 300+ lines)
- **Bezier Curve Mouse Movement** - Natural curved paths with acceleration/deceleration
- **Randomized Timing** - `human_delay(base, variance)` for variable reaction times
- **Human-like Typing** - Variable speed + occasional typos + backspace (5% chance)
- **Probabilistic Actions** - `should_perform_action(0.85)` for selective behavior
- **Micro-movements** - Random fidgeting while "thinking"
- **Smooth Scrolling** - Gradual scroll with pauses

**2. Undetected Browser Module** (`src/undetected_browser.py` - 200+ lines)
- **Undetected ChromeDriver** - Hides navigator.webdriver flag
- **Stealth JavaScript Injection** - Spoofs plugins, languages, chrome.runtime, connection
- **Advanced Fingerprinting** - Device memory, hardware concurrency
- **Detection Testing** - Built-in test suite (`test_detection()`)

### Documentation
- [YOUTUBE_AUTOMATION_DETECTION_HARDENING_20251215.md](../../../docs/YOUTUBE_AUTOMATION_DETECTION_HARDENING_20251215.md) - Detection vector analysis
- [ANTI_DETECTION_IMPLEMENTATION_GUIDE_20251215.md](../../../docs/ANTI_DETECTION_IMPLEMENTATION_GUIDE_20251215.md) - Implementation guide

### Impact
**Before Hardening**: 85-95% detection probability
**After Sprint 1** (Bezier curves + random timing): 35-50% ⬇️
**After Sprint 2** (Undetected Chrome + session hygiene): 5-15% ⬇️⬇️

### Implementation Required
This module provides the INFRASTRUCTURE - integration into comment_engagement_dae.py required:
1. Replace `execute_script()` with `human.human_click()`
2. Replace fixed `asyncio.sleep()` with `human.human_delay()`
3. Replace `send_keys()` with `human.human_type()`
4. Integrate undetected Chrome in browser_manager.py
5. Add session hygiene (4-hour browser restarts)

See: [Implementation Guide](../../../docs/ANTI_DETECTION_IMPLEMENTATION_GUIDE_20251215.md)

### Configuration
```bash
# Install requirement
pip install undetected-chromedriver

# .env settings
YT_AUTOMATION_ENABLED=false  # Keep disabled until hardening complete
USE_UNDETECTED_CHROME=true
HUMAN_BEHAVIOR_ENABLED=true
```

### WSP Compliance
- **WSP 49**: Platform Integration Safety (anti-detection measures)
- **WSP 77**: AI Coordination (human behavior simulation)
- **WSP 91**: DAEMON Observability (detection telemetry)
- **WSP 22**: Documentation (complete guides + cross-references)

---

## V0.5.1 — Cross-DAE Browser Allocation Guard (2025-12-14)

**Integration Type**: Reliability Guardrail (Browser Coordination)
**WSP Compliance**: WSP 3 (Architecture), WSP 77 (Agent Coordination), WSP 50 (Pre-action verification)

### Problem
Multiple DAEs can attempt to reuse the same browser/profile session without coordination, causing session hijacking (especially around the shared Chrome debug session used for YouTube Studio work).

### Changes
- **BrowserManager allocation tracking** (`src/browser_manager.py`)
  - Added optional `dae_name` parameter to `get_browser(...)` (legacy callers unchanged).
  - Tracks `browser_key -> dae_name` allocations in-memory and blocks conflicting claims.
  - Added `release_browser(...)` and `get_allocations()` helpers for future orchestration/telemetry.
  - Ensures allocations are cleared on browser death/close.

### Impact
- Enables safe parallel DAEs by preventing accidental cross-domain browser session hijacking.
- Keeps backwards compatibility: coordination only activates when `dae_name` is provided.

## V0.5.0 — Browser Manager Migration (Sprint V4 - 2025-12-02)

**Integration Type**: Infrastructure Consolidation
**WSP Compliance**: WSP 3 (Architecture), WSP 72 (Module Independence), WSP 77 (Telemetry)

### Sprint V4: Browser Manager Migration

**Rationale**: BrowserManager was located in `platform_integration/social_media_orchestrator/src/core/` but is infrastructure-level functionality used across multiple domains. Migrating to `foundups_selenium` aligns with WSP 3 (proper domain placement) and enables use by new modules (browser_actions, foundups_vision).

### Additions
- **BrowserManager**: Migrated from social_media_orchestrator to foundups_selenium
  - File: `src/browser_manager.py` (293 lines)
  - Class: `BrowserManager` - Singleton browser session manager
  - Function: `get_browser_manager()` - Factory function
  - Export: Added to `src/__init__.py` for public API

- **YouTube Profile Support**: Added 4 new YouTube Chrome profiles
  - `youtube_move2japan` - Move2Japan channel (primary use case)
  - `youtube_foundups` - FoundUps channel
  - `youtube_geozai` - GeoZai channel
  - `youtube_undaodu` - UnDaoDu channel
  - Profile paths: `modules/platform_integration/youtube_auth/data/chrome_profile_*`

### Changes
- **Import Updates**: Updated 2 files to use new location
  - `modules/platform_integration/x_twitter/src/x_anti_detection_poster.py` (line 267)
  - `modules/platform_integration/linkedin_agent/src/anti_detection_poster.py` (line 119)

- **Backwards Compatibility**: Created shim in old location
  - File: `social_media_orchestrator/src/core/browser_manager.py` (now 22 lines - import shim)
  - Old imports still work: Forwards to new location automatically
  - Updated: `social_media_orchestrator/src/core/__init__.py` imports from new location
  - Zero breaking changes for existing code

- **NAVIGATION.py**: Added 6 browser session management entries
  - "get browser instance" → BrowserManager.get_browser()
  - "reuse browser session" → BrowserManager.get_browser()
  - "browser singleton manager" → get_browser_manager()
  - "close browser session" → BrowserManager.close_browser()
  - "chrome profile management" → BrowserManager._create_chrome_browser()
  - "youtube browser profile" → BrowserManager._create_chrome_browser() - youtube_move2japan

### Vision Automation Integration
This migration enables Sprint A2 (YouTube Actions) and Sprint V5 (RealtimeCommentDialogue):
- **browser_actions** module can now access BrowserManager from infrastructure
- **foundups_vision** UI-TARS integration can share browser sessions
- **youtube_auth** profiles are ready for vision-based engagement

### WSP Compliance
- **WSP 3**: Module organization - Infrastructure domain for cross-domain functionality
- **WSP 72**: Module independence - BrowserManager no longer tied to social_media_orchestrator
- **WSP 77**: Telemetry - Browser event telemetry still operational (FoundUpsDriver observers)
- **WSP 22**: Documentation - ModLog updated in both modules

### Migration Checklist
✅ BrowserManager migrated to foundups_selenium
✅ YouTube profile mappings added
✅ All imports updated to new location
✅ Backwards-compatible shim created
✅ NAVIGATION.py entries added
✅ ModLog updated (foundups_vision + foundups_selenium)
✅ Public API exported via __init__.py
✅ Zero breaking changes verified

**Token Efficiency**: 200 tokens (as budgeted) - Clean migration with full backwards compatibility

---

## V0.4.0 — GCP Console Automation + AI Overseer Integration (2025-11-03)

**Integration Type**: AI Overseer Infrastructure Automation
**WSP Compliance**: WSP 77 (Agent Coordination), WSP 96 (MCP Governance), WSP 3 (Module Organization)

### Additions
- **GCP Console Automator**: New `src/gcp_console_automator.py` for autonomous cloud infrastructure tasks
  - Class: `GCPConsoleAutomator` - FoundUpsDriver + Gemini Vision automation
  - Methods: `create_secret_manager_secret()`, `create_cloud_build_trigger()`, `setup_gotjunk_deployment()`
  - Skills Integration: Reads from `modules/communication/livechat/skillz/gcp_console_automation.json`
  - Vision DAE Integration: Screenshots saved to `docs/session_backups/gcp_automation/screenshots/`
  - Result Tracking: `AutomationResult` dataclass with success status, steps completed, telemetry

- **Live Test Script**: Created `src/live_test_github_connection.py`
  - Real-time browser automation for GitHub → Cloud Build connection
  - OAuth flow handling with human-in-the-loop checkpoints
  - Vision DAE validation at each step
  - Connects to existing Chrome instance (port 9222) for session reuse

### AI Overseer Mission Support
This module now serves as the **execution engine** for AI Overseer infrastructure missions:
- **Phase 1 (Gemma)**: Uses Vision DAE to validate UI state (binary classification)
- **Phase 2 (Qwen)**: Receives strategic plan from AI Overseer
- **Phase 3 (0102)**: Executes browser automation with FoundUpsDriver
- **Phase 4 (Learning)**: Stores successful patterns for future missions

### First Mission: GotJunk Cloud Deployment
- Mission Definition: `modules/ai_intelligence/ai_overseer/missions/gotjunk_cloud_deployment_setup.json`
- Target: Automate GitHub → Cloud Build → Cloud Run deployment
- Components: Secret Manager, Cloud Build triggers, IAM permissions
- Outcome: Future FoundUp deployments require ZERO manual intervention

### Technical Details
- **Smart Element Finding**: Vision-guided selector fallbacks when CSS/XPath fails
- **Human-Like Interaction**: Random delays, character-by-character typing
- **Error Handling**: Graceful degradation with detailed error messages
- **Browser Reuse**: Connects to port 9222 for authenticated session persistence

### WSP Compliance
- **WSP 77**: Agent coordination (Qwen plans → 0102 executes → Gemma validates)
- **WSP 96**: MCP governance (HoloIndex, Vision DAE, Secrets MCP integration)
- **WSP 3**: Module organization (automation in infrastructure/foundups_selenium)
- **WSP 48**: Recursive learning (patterns stored in ai_overseer/memory/)

### Related Modules
- `modules/ai_intelligence/ai_overseer` - Mission planning and coordination
- `modules/infrastructure/dae_infrastructure/foundups_vision_dae` - UI validation
- `modules/communication/livechat/skills` - Reusable automation skill definitions

---

## V0.3.0 — Telemetry Storage & Database Integration (2025-10-19)

**Sprint 2 – Telemetry & Logging** ✅

### Additions
- **SQLite Telemetry Store**: Implemented lightweight session storage in `src/telemetry_store.py`
  - Table: `selenium_sessions` with 7 columns (id, timestamp, url, screenshot_hash, screenshot_path, annotated_path, analysis_json)
  - Indexes: timestamp (DESC) and screenshot_hash for performance
  - Thread-safe: Autocommit mode (`isolation_level=None`) for concurrent writes
  - Auto-creation: Table and indexes created automatically on first use
  - Database location: `O:/Foundups-Agent/data/foundups.db`

- **Comprehensive Test Suite**: Created `tests/test_telemetry_store.py`
  - Coverage: 17/17 tests passing (100% pass rate)
  - Test categories:
    - Table auto-creation and schema validation
    - Session recording (minimal/full, timestamps, JSON handling)
    - Session retrieval (by ID, recent sessions, ordering)
    - Error handling (missing fields, malformed JSON)
    - Concurrent write safety (10 simultaneous writes)
    - Standalone helper function
  - Windows-safe: Handles file locking issues in temp DB cleanup

- **Documentation**: Updated README.md with "Telemetry Storage - SQLite Database" section
  - Schema table with column descriptions
  - Usage example with record_session()
  - MCP integration guidance for Gemma/Qwen pattern learning
  - WSP references: WSP 72 (Module Independence), WSP 22 (Documentation)

### Technical Details
- **Standalone Function**: `record_session(entry: dict) -> int` for simple usage without class instantiation
- **TelemetryStore Class**: Full-featured store with get_session(), get_recent_sessions()
- **JSON Handling**: Automatic serialization/deserialization of analysis_json field
- **Timestamp Auto-generation**: ISO8601 UTC format if not provided
- **Deduplication Support**: screenshot_hash column with index for detecting duplicate screenshots

### Integration Points
- **MCP Servers**: Can query session history for pattern learning
- **Gemma 3 270M**: Fast policy gates can validate telemetry completeness
- **Qwen 1.5B**: Deep reasoning for UI state transition analysis
- **VisionDAE**: Will consume telemetry for browser/desktop monitoring (Sprint 3)

### WSP Compliance
- **WSP 22**: ModLog updated with implementation details
- **WSP 72**: Module independence maintained (standalone SQLite, no external deps)
- **WSP 5**: Test coverage requirements met (17 tests, all passing)
- **WSP 50**: Pre-action verification (table auto-creation, safe concurrent writes)

### Next Steps (Sprint 3)
- Integrate record_session() into FoundUpsDriver.analyze_ui()
- Add MCP server endpoint for session queries
- Implement session replay functionality
- Connect to VisionDAE telemetry pipeline

---

## V0.2.0 — Vision & Platform Integration (2025-10-18)

### Additions
- Gemini Vision integration for UI analysis
- X/Twitter posting with vision guidance
- Browser reuse via port 9222 (connect_or_create)
- Human-like behavior helpers (human_type, random_delay)
- Anti-detection measures (stealth mode default)
- Observer pattern for telemetry events

### Features
- `analyze_ui()` - Gemini Vision-powered UI state analysis
- `post_to_x()` - High-level X posting with retry logic
- `smart_find_element()` - Multi-selector fallback with vision option
- Event emission: init, connect, vision, posting lifecycle

---

## V0.1.0 — Foundation & Anti-Detection (2025-10-16)

### Additions
- FoundUpsDriver class extending selenium.webdriver.Chrome
- Anti-detection by default (navigator.webdriver override, Chrome flags)
- Profile-based session persistence
- Basic element interaction helpers

### Architecture
- Wrapper pattern (not fork) for maintainability
- WSP 3 compliant module structure (README, INTERFACE, src, tests, requirements)
- Integration with social_media_orchestrator and x_twitter modules

---

**Current Status**: Sprint 2 complete - Telemetry storage operational
**Test Coverage**: 17/17 passing (telemetry_store), additional driver tests in test_foundups_driver.py
**Next Sprint**: MCP Interface Stub (Sprint 3)

---

## 2026-01-04 — Dynamic Randomness Mode + ZERO1 Profile Hook

**WSP References**: WSP 49 (Platform Integration Safety), WSP 77 (Agent Coordination), WSP 91 (Observability), WSP 22 (Change tracking)

### Problem
Fixed-percent action gating creates stable signatures (e.g., 85% like rate) and makes behavior easier to fingerprint.

### Solution
- Updated `src/human_behavior.py` to support **dice-on-dice** action gating by default:
  - The probability itself is re-sampled from an entropy-backed distribution each decision.
  - **Fixed mode** remains available for deterministic testing.
- Added 0102 behavior interface hook:
  - `YT_0102_BEHAVIOR_INTERFACE=0102` enables higher variability and rare pattern-breakers.

### Controls
```bash
YT_ACTION_RANDOMNESS_MODE=dynamic          # default
YT_ACTION_RANDOMNESS_MODE=fixed            # deterministic
YT_0102_BEHAVIOR_INTERFACE=0102            # recommended

# Legacy name (still supported)
YT_BEHAVIOR_PROFILE=0102
```
