# antifaFM Broadcaster - Test Module Log

## Test Suite Overview

| Test File | Status | Last Run | Purpose |
|-----------|--------|----------|---------|
| `test_main_menu_startup_boundary.py` | NEW | 2026-05-26 | Main menu startup boundary enforcement (12 tests) |
| `test_boot_layer_rotator.py` | NEW | 2026-03-22 | Boot layer schema rotation tests (16 tests) |
| `test_gcc_shipping_tracker.py` | NEW | 2026-03-22 | GCC shipping tracker + screenshot mode (22 tests) |
| `test_obs_controller_startup.py` | PASS | 2026-03-06 | OBS start verification (no false-positive stream started) |
| `test_suno_stt_extractor.py` | PASS | 2026-03-05 | Suno STT lyrics extraction pipeline tests |
| `test_go_live_steps.py` | PASS | 2026-02-28 | Step-by-step Go Live debugging + DOM verification |
| `test_discord_voice_broadcaster_integration.py` | PASS | 2026-04-09 | Discord voice lane boot/runtime wiring (+ invalid snowflake env case; 6 tests) |

---

## 2026-05-26: Main Menu Startup Boundary Tests (Worker W6)

**Slice**: `MAIN_MENU_ANTIFAFM_STARTUP_BOUNDARY_FIX_PHASE1`

**Test File**: `test_main_menu_startup_boundary.py` (NEW)

**Tests Added** (12 tests, all PASS):
| Test | What it covers |
|------|----------------|
| `test_main_py_does_not_execute_on_antifafm_auto_start_env` | No ANTIFAFM_AUTO_START execution gate in main.py |
| `test_main_py_does_not_import_obs_controller_at_module_level_for_autostart` | No OBSController auto-start pattern |
| `test_main_py_does_not_start_metadata_daemon_at_startup` | No init_dynamic_metadata() at startup |
| `test_main_py_does_not_start_boot_rotator_at_startup` | No rotator_thread.start() at startup |
| `test_main_py_documents_boundary_fix` | main.py documents the slice ID |
| `test_youtube_menu_has_broadcaster_handler` | Explicit launch handler exists |
| `test_preflight_module_exists` | Preflight functions exist |
| `test_obs_logging_guard_module_exists` | OBS logging guard module exists |
| `test_main_py_installs_logging_guard_early` | Guard installed before line 200 |
| `test_obs_controller_module_imports_guard` | OBSController imports guard |
| `test_env_example_documents_auto_start_deprecation` | .env.example marks deprecated |
| `test_no_real_secrets_in_test_file` | No real secrets in test code |

**What Tests Verify** (code pattern checks, no runtime imports):
- main.py code patterns removed (auto-start block deleted)
- Explicit launch paths preserved (youtube_menu.py, preflight.py)
- PR #720 OBS logging guard preserved
- .env.example documents deprecation

**Run Command**:
```bash
pytest modules/platform_integration/antifafm_broadcaster/tests/test_main_menu_startup_boundary.py -v
```

**Result**: 12 passed in 0.12s

---

## 2026-04-09: Discord Voice Live Guild Verification (Worker AY)

**Slice**: `ANTIFAFM_DISCORD_VOICE_LIVE_GUILD_VERIFICATION_PHASE1`

**Test File**: `test_discord_voice_broadcaster_integration.py` (no changes — verification only)

**Tests Re-verified** (6 tests, all PASS):
| Test | What it covers |
|------|----------------|
| `test_discord_lane_absent_when_flag_off` | Lane not initialized when `ANTIFAFM_DISCORD_VOICE_ENABLED` unset |
| `test_discord_flag_on_without_token_no_adapter` | No adapter when token missing |
| `test_broadcaster_start_await_discord_start_when_configured` | Discord starts after YouTube success |
| `test_discord_start_failure_does_not_fail_youtube` | Isolated failure — YouTube continues |
| `test_build_discord_voice_from_env_returns_none_without_token` | `build_discord_voice_from_env` returns None without token |
| `test_build_discord_voice_from_env_invalid_guild_skips_lane` | Invalid snowflake fails closed |

**What Tests Verify** (code-level, no live Discord):
- Env parsing and fail-closed behavior
- Adapter construction via `build_discord_voice_from_env()`
- Isolated failure handling (Discord doesn't cascade to YouTube)
- Health monitor wiring

**What Requires Manual Live VC Run** (not testable without real Discord):
- Actual bot→guild→channel connection
- FFmpeg→Opus audio quality
- Reconnect behavior under network disruption
- Real health monitor recovery cycle

**Run Command**:
```bash
pytest modules/platform_integration/antifafm_broadcaster/tests/test_discord_voice_broadcaster_integration.py -v
```

**Result**: 6 passed in 14.84s

---

## 2026-03-22: Boot Layer Rotator + GCC Shipping Tracker Tests

### Added: `test_boot_layer_rotator.py`
**Purpose**: Test schema rotation configuration and Coming Soon fallbacks

**Test Classes** (16 tests total):
1. `TestSchemaRegistry` - Schema registry validation
   - `test_schemas_not_empty`: Registry has entries
   - `test_rotation_order_has_implemented_schemas`: Only implemented schemas in rotation
   - `test_required_schema_fields`: All schemas have name/description/implemented
   - `test_gcc_schema_exists`: GCC schema configured
   - `test_video_schema_exists`: Video schema configured
   - `test_news_schema_exists`: News schema configured

2. `TestComingSoonURI` - Coming Soon fallback generation
   - `test_generates_valid_data_uri`: Valid base64 data URI
   - `test_uri_contains_schema_name`: HTML contains schema name
   - `test_uri_contains_signature`: HTML contains 0102 signature

3. `TestSchemaVisibilityConfiguration` - OBS visibility (mocked)
   - `test_gcc_schema_hides_video_sources`: GCC hides video grid
   - `test_video_schema_shows_video_grid`: Video shows grid

4. `TestEventEmission` - Telemetry logging
   - `test_emit_event_creates_telemetry_dir`: Creates telemetry directory

5. `TestRotationOrder` - Rotation configuration
   - `test_rotation_order_is_list`: Order is a list
   - `test_rotation_order_minimum_schemas`: At least 2 schemas
   - `test_rotation_order_no_duplicates`: No duplicate schemas
   - `test_rotation_starts_with_gcc`: GCC is first

### Added: `test_gcc_shipping_tracker.py`
**Purpose**: Test shipping tracker URLs, screenshot mode, and timing

**Test Classes** (22 tests total):
1. `TestURLConstants` - URL validation
   - VesselFinder URLs (Hormuz, Gulf, Tankers)
   - MarineTraffic URLs (Hormuz, Gulf)
   - All URLs have proper domains and filters

2. `TestTrustedDomains` - WAF bypass domains
   - MarineTraffic, VesselFinder, FleetMon are trusted
   - Random domains are not trusted

3. `TestTimingConstants` - Timing configuration
   - View interval is 120s (2 min)
   - Schema duration is 600s (10 min)
   - 5 views fit in one schema

4. `TestHormuzBounds` - Region bounding box
   - Has required lat/lon keys
   - Valid coordinate ranges

5. `TestTankerFocusURL` - Tanker filter
   - Returns VesselFinder URL
   - Has type=8 tanker filter

6. `TestComingSoonURI` - Fallback validation
   - Valid data URI format

7. `TestScreenshotFunctions` - 012 behavior mode
   - Screenshot cache directory exists
   - PNG to data URI conversion works
   - Returns None for missing screenshots

8. `TestViewRotation` - Rotation logic
   - Function accepts use_screenshots parameter
   - Screenshot mode is available

**Run Tests**:
```bash
pytest modules/platform_integration/antifafm_broadcaster/tests/test_boot_layer_rotator.py -v
pytest modules/platform_integration/antifafm_broadcaster/tests/test_gcc_shipping_tracker.py -v
```

**Results**: 38/38 PASSED (2026-03-22)

**WSP Compliance**:
- WSP 5: Test coverage for new schema rotation
- WSP 72: Module independence (mocked OBS client)
- WSP 91: Telemetry event emission tested

---

## 2026-03-06: OBS Startup Verification + Broadcast Setup Guard

### Added: `test_obs_controller_startup.py`
**Purpose**: Ensure OBS auto-start only reports success when stream output becomes active.

**Test Cases**:
1. `test_start_streaming_already_active`: returns success without redundant StartStream call.
2. `test_start_streaming_waits_until_active`: waits/polls until `output_active=True`.
3. `test_start_streaming_reports_inactive_timeout`: fails with deterministic error when output never activates.
4. `test_ensure_stream_service_custom_updates_service`: configures `rtmp_custom` server/key in OBS service settings.
5. `test_ensure_stream_service_custom_noop_when_already_set`: avoids unnecessary reconfiguration when target already matches.

**Why**:
- Fixed false-positive startup where logs said `Streaming started!` while OBS was still waiting on
  "Create broadcast and start streaming" UI flow.

**Run Tests**:
```bash
pytest modules/platform_integration/antifafm_broadcaster/tests/test_obs_controller_startup.py -v
```

---

## 2026-03-05: Suno STT Lyrics Extractor Tests

### Added: `test_suno_stt_extractor.py`
**Purpose**: Test fully automated Suno lyrics extraction via Speech-to-Text

**Test Classes**:
1. `TestSunoAudioDownloader` - CDN URL construction, cache directory
2. `TestLyricsDeduplicator` - Hash generation, normalization, duplicate detection
3. `TestSunoSTTTranscriber` - WSP 84 FasterWhisperSTT reuse verification
4. `TestSunoSTTLyricsExtractor` - Full pipeline integration
5. `TestCLIIntegration` - CLI --help, --stats commands
6. `TestLaunchIntegration` - launch.py import, SKILLz JSON validation

**Key Tests**:
- `test_hash_normalization`: Verifies lyrics with different whitespace/case produce same hash
- `test_deduplicator_detects_duplicate`: Verifies duplicate lyrics are detected across songs
- `test_wsp84_reuse_import`: Verifies FasterWhisperSTT imported from voice_command_ingestion
- `test_skill_json_valid`: Verifies suno_stt_extract.json SKILLz file is valid

**WSP Compliance**:
- WSP 5: Test coverage for new STT functionality
- WSP 72: Module independence (no cross-module test dependencies)
- WSP 84: Validates code reuse of FasterWhisperSTT

**Run Tests**:
```bash
pytest modules/platform_integration/antifafm_broadcaster/tests/test_suno_stt_extractor.py -v
```

---

## 2026-02-28: Exact DOM Selectors (012-provided)

### Updated: `src/youtube_go_live.py`
**Changes**:
- Edit button: Now uses `#edit-button` (exact selector from 012)
- Title input: Now uses `#title-textarea` inside `#title-wrapper`
- Description: Now uses `#description-textarea` inside `#description-wrapper`
- Save button: Now uses `#save-button` (exact selector from 012)
- CLI: Added `--json` and `--status` flags for OpenClaw/IronClaw

**Selector Priority**:
```
Method 1: Direct ID (#edit-button, #title-textarea, etc.)
Method 2: Wrapper + nested ID (#title-wrapper > #title-textarea)
Method 3: Fallback (aria-label, text match)
```

---

## 2026-02-28: Stream Edit Testing + 15s Studio Wait

### Updated: `test_go_live_steps.py`
**Changes**:
- Added `test_edit_stream()` function - scans for Edit buttons and input fields
- Increased studio load wait: 3s → 15s (YouTube Studio is slow)
- Added screenshot after studio loads
- Added screenshot of edit dialog

**New Test Step (6b)**:
```
[STEP 6b] Testing stream edit functionality...
  - Scans for edit buttons (aria-label, icon)
  - Clicks Edit button if found
  - Scans input fields in dialog
  - Takes screenshot of edit dialog
```

---

## 2026-02-28: DOM Polling Verification

### Updated: `test_go_live_steps.py`
**Change**: Replaced fixed 2-second wait with DOM polling verification

**Before**:
```python
print("  [INFO] Waiting 2 seconds for dropdown menu...")
time.sleep(2)
```

**After**:
```python
dropdown_verified = verify_dropdown_appeared(driver, timeout=5)
# Polls DOM every 300ms for menu items
```

**Why Changed**:
- Fixed delays are fragile (too fast = miss dropdown, too slow = waste time)
- DOM polling verifies dropdown actually appeared
- Reports item count and detection time for debugging
- Fails gracefully if dropdown doesn't appear

**New Function**: `verify_dropdown_appeared(driver, timeout=5)`
- Polls every 300ms for menu items
- Returns True when items detected, False on timeout
- Prints detection time and item list

---

## 2026-02-27: Initial Test Suite Creation

### Added: `test_go_live_steps.py`
**Purpose**: Debug YouTube Go Live automation step-by-step

**Test Steps**:
1. Check Chrome debug port 9222
2. Connect via Selenium
3. Navigate to YouTube Studio `/livestreaming/dashboard`
4. Scan and print all visible buttons
5. Click CREATE button
6. Scan and print menu items
7. Click "Go live" in dropdown
8. Check stream status
9. Take screenshots at each step

**Why Created**:
- Go Live automation not clicking buttons
- Need visibility into what buttons exist on page
- YouTube Studio UI uses shadow DOM and custom elements
- Screenshots help debug without manual inspection

**Output**:
- Console: Step-by-step progress with button lists
- Screenshots: `logs/screenshot_*.png`

---

## Planned Tests

### `test_obs_logging_guard.py`
- Verifies synthetic OBS WebSocket passwords are redacted from formatted log records.
- Verifies `obsws_python` logger levels are raised above INFO.
- Verifies guarded OBS client construction redacts constructor-time third-party logs.
- Uses synthetic secrets only; does not read `.env`, connect to OBS, or run network calls.

### `test_ffmpeg_stream.py` (TODO)
- Test FFmpeg command generation
- Test RTMP connection to YouTube
- Verify keyframe settings
- Check bitrate/buffer configuration

### `test_stream_verification.py` (TODO)
- Test `verify_stream_connected()` function
- Mock DOM responses
- Test timeout handling

### `test_login_detection.py` (TODO)
- Test all 5 login detection methods
- Test signed-out state detection
- Test Studio vs regular YouTube detection

---

## Test Infrastructure

### Chrome Debug Mode
Tests require Chrome running with debug port:
```powershell
chrome.exe --remote-debugging-port=9222
```

### Dependencies
- `selenium` - Browser automation
- Chrome browser with YouTube login

### Screenshot Storage
Screenshots saved to `logs/` with timestamps for debugging.
