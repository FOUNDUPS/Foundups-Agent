# CLI Module - Modification Log

**WSP Compliance**: WSP 22 (ModLog Updates)

## V0.3.15 - Cohere Transcribe STT Backend (2026-03-30)

### Added
- `src/openclaw_voice.py`
  - **CohereTranscribeBackend**: Lazy singleton STT using Cohere Transcribe 2B
  - Lazy loading pattern (WSP 91): model loads on first transcribe, not on boot
  - Prevents 60s cold-start blocking voice REPL initialization
  - New env var: `OPENCLAW_VOICE_DISABLE_COHERE_STT=1` to skip Cohere

### Changed
- STT chain priority: Cohere (local, lazy) -> Whisper (local) -> Google (cloud)

### WSP Compliance
- **WSP 91**: DAEMON observability (load time logging)
- **WSP 22**: ModLog documentation

---

## V0.3.14 - OpenClaw menu aligned to resident broker runtime (2026-03-18)

### Changed
- `src/openclaw_menu.py`
  - Added broker-aware webhook launch path
  - Option `3` now:
    - checks broker runtime for `openclaw`
    - starts the resident service through the broker when registered
    - avoids spawning a competing webhook subprocess when the resident runtime already exists

### Purpose
- Keep manual CLI fallback aligned with the broker-managed control plane.
- Prevent the menu surface from fighting the new resident OpenClaw runtime.

### WSP Compliance
- **WSP 22**: ModLog documentation
- **WSP 97**: execution-plane alignment before new behavior

---

## V0.3.13 - antifaFM Preflight Check + Schema Testing (2026-03-06)

### Added
- `src/youtube_menu.py`
  - **PREFLIGHT CHECK**: When entering antifaFM menu, if stream is running:
    - Shows uptime in hours, health state, restart count
    - If uptime > 10 hours: prompts "Restart stream now? [y/N]"
    - Auto-restarts with stop → 3s pause → start
  - New options 5-9 in antifaFM Broadcaster submenu:
    - **5. [TEST] Cycle through all schemas** - Shows FFmpeg filters for all 6 schemas
    - **6. [TEST] Lookup karaoke lyrics** - Test song lookup in lyrics cache
    - **7. [TEST] View lyrics cache stats** - Shows source breakdown (whisper-stt, lrclib)
    - **8. [OPS] Set schema signal** - IPC signal for live schema switching
    - **9. [HEALTH] View stream health details** - Full diagnostics + recent telemetry
  - Added helper functions: `_test_all_schemas()`, `_test_karaoke_lookup()`, `_show_lyrics_cache_stats()`, `_set_schema_signal()`

### Preflight Check Flow
```
Enter antifaFM menu → get_status() → check if broadcasting
  ↓
If running > 10 hours → prompt restart [y/N]
  ↓
Show menu with health info
```

### Reuses Existing Code
- `broadcaster.get_status()` - uptime_seconds, health metrics
- `SchemeManager`, `OutputScheme` from `scheme_manager.py`
- `write_scheme_signal()`, `read_scheme_signal()` from `scheme_manager.py`
- `get_cached_lyrics()`, `_get_lyrics_db()` from `launch.py`

### Purpose
012 can now:
1. See if stream needs restart (>10 hours) with auto-prompt
2. Test karaoke lyrics display BEFORE going live
3. View detailed stream health diagnostics

### WSP Compliance
- **WSP 22**: ModLog documentation
- **WSP 84**: Code reuse (existing broadcaster and scheme_manager functions)

---

## V0.3.12 - LinkedIn Feed Engagement Integration (2026-02-24)

### Added
- `src/social_media_menu.py`
  - New option 5: "LinkedIn Feed Engagement (DOM-first)"
  - Added `_run_linkedin_feed_engagement()` function:
    - Uses `LinkedInActions` class from browser_actions
    - DOM-first architecture (fast, ~10ms/post)
    - 4 modes: Like+Reply, Like Only, Reply Only, Dry Run
    - Templates only (no YouTube LLM) - FoundUps brand-compliant
    - Full action logging for troubleshooting

### Production Pipeline
- **main.py** → option 4 → option 5 → LinkedIn DOM-first engagement
- Rotation schema: Feed refresh → Iterate → Detect (AI/capital/author) → Engage

### SKILLz Integration
- `browser_actions/skillz/linkedin_post_hunter/` - Post detection skill
- `browser_actions/skillz/linkedin_engagement_poster/` - Engagement skill
- `browser_actions/skillz/linkedin_feed_engagement.json` - v2.0.0

### WSP Compliance
- **WSP 22**: ModLog documentation
- **WSP 96**: WRE Skills protocol

---

## V0.3.11 - Voice Endpointing + Boot Model Availability Probe (2026-02-24)

### Changed
- `src/openclaw_voice.py`
  - Improved microphone endpointing to avoid premature cutoffs:
    - Added `min_recording_duration` support in `record_until_silence(...)`
    - Added `OPENCLAW_VOICE_MIN_UTTERANCE_SEC` (default `1.2`)
    - Increased default `OPENCLAW_VOICE_SILENCE_SEC` to `0.85`
  - Added configurable barge minimum utterance:
    - `OPENCLAW_VOICE_BARGE_MIN_UTTERANCE_SEC` (default `0.0`)
  - Wired startup model availability summary:
    - prints local model folder readiness
    - prints provider availability (`keys` or live `api` probe)
    - prints target/effective model at boot
  - Added STT VAD controls for faster-whisper path:
    - `OPENCLAW_VOICE_STT_VAD_FILTER` (default `0`)
    - `OPENCLAW_VOICE_STT_VAD_MIN_SILENCE_MS` (default `180`)

### WSP Compliance
- **WSP 22**: ModLog documentation

## V0.3.10 - Unified Menu 16 + In-Session Backend Switching (2026-02-24)

### Changed
- `src/openclaw_menu.py`
  - Simplified menu 16 to remove redundant OpenClaw/IronClaw branch split:
    - `1. Claw Chat (unified backend)`
    - `2. Claw Voice (unified backend)`
  - Kept existing CLI flags unchanged (`--chat`, `--voice`, `--ironclaw-chat`, `--ironclaw-voice`).
  - Added `OPENCLAW_DEFAULT_BACKEND` support for menu launches.
- `src/main_menu.py`
  - Updated option 16 label to reflect unified Chat/Voice flow.
- `src/openclaw_chat.py`
  - Added in-session backend switch command parsing:
    - `backend ironclaw`
    - `backend openclaw`
    - `switch backend to ...`
  - Runtime switch now reinitializes DAE with selected backend and prints updated identity line.
- `src/openclaw_voice.py`
  - Added local backend control commands:
    - `backend ironclaw`
    - `backend openclaw`
  - Voice loop now applies backend switch immediately, reinitializes DAE, and keeps session continuity.
  - Updated startup hints to advertise backend-switch commands.

### Added
- `tests/test_openclaw_chat_backend_switch.py`
  - backend command parsing coverage for chat mode.
- `tests/test_openclaw_voice_cue_parsing.py`
  - backend control command parsing coverage for voice mode.

### WSP Compliance
- **WSP 22**: ModLog documentation
- **WSP 5**: Added regression tests for unified backend control

## V0.3.9 - STT Alias Canonicalization (2026-02-24)

### Added
- `src/openclaw_voice.py`
  - `_normalize_stt_aliases(...)` to canonicalize common STT drift before routing:
    - `quinn/quin/queen/quen/gwen/coin -> qwen`
    - spoken cue prefixes (`zero one zero two`, `0 2 0 1`, etc.) normalized to `0102`
  - Live STT normalization hook applied to:
    - main voice capture path
    - push-to-talk capture path
    - busy-turn barge/queue capture path
  - New env controls:
    - `OPENCLAW_VOICE_STT_ALIAS_NORMALIZE` (default `1`)
    - `OPENCLAW_VOICE_STT_ALIAS_VERBOSE` (default `0`)

### Added
- `tests/test_openclaw_voice_cue_parsing.py`
  - alias normalization tests for `qwen` variants
  - spoken-prefix normalization tests for `0102`

### Validation
- `python -m py_compile modules/infrastructure/cli/src/openclaw_voice.py modules/infrastructure/cli/tests/test_openclaw_voice_cue_parsing.py`: PASS
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q -s modules/infrastructure/cli/tests/test_openclaw_voice_cue_parsing.py`: PASS (12 passed)

### WSP Compliance
- **WSP 22**: ModLog documentation
- **WSP 5**: Added regression tests for STT alias handling

## V0.3.8 - Voice Noise Gate Hardening (2026-02-24)

### Changed
- `src/openclaw_voice.py`
  - Added stricter STT noise/fragment filtering:
    - weak single-token noise (`well`, `next`, etc.) dropped
    - strict busy-queue gating rejects incomplete fragments (`what's your`)
    - punctuation-only and number-only fragments remain blocked
  - Applied main-turn noise gate before DAE routing to prevent low-signal prompts.
  - Added cooldown-based noise notice to avoid log spam:
    - `OPENCLAW_VOICE_NOISE_NOTICE_COOLDOWN_SEC` (default `3.0`)
  - Added env flags for gate tuning:
    - `OPENCLAW_VOICE_MAIN_NOISE_GATE` (default `1`)
    - `OPENCLAW_VOICE_QUEUE_STRICT_NOISE_GATE` (default `1`)

### Added
- `tests/test_openclaw_voice_cue_parsing.py`
  - coverage for single-word meaningful query (`model`)
  - weak single-token rejection (`well`, `next`)
  - strict queue-mode fragment rejection (`what's your`)

### Validation
- `python -m py_compile modules/infrastructure/cli/src/openclaw_voice.py modules/infrastructure/cli/tests/test_openclaw_voice_cue_parsing.py`: PASS
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q -s modules/infrastructure/cli/tests/test_openclaw_voice_cue_parsing.py`: PASS (10 passed)

### WSP Compliance
- **WSP 22**: ModLog documentation
- **WSP 5**: Added targeted regression coverage for voice noise gating

## V0.3.7 - Voice UX: Spoken Model-Switch Hints (2026-02-24)

### Changed
- `src/openclaw_voice.py`
  - Voice startup banner now advertises deterministic model-switch commands:
    - `switch model to qwen3`
    - `become codex`
    - `become grok`
  - Helps 012 discover runtime profile switching directly in live voice mode.

### WSP Compliance
- **WSP 22**: ModLog documentation

## V0.3.6 - Voice Exit Command + Faster Pause Detection (2026-02-24)

### Changed
- `src/openclaw_voice.py`
  - Natural-language control parsing now honors phrases containing `exit/quit`
    (example: "let's exit out of this voice mode").
  - While a turn is active, saying exit now cancels the active turn and exits promptly.
  - Added configurable voice capture timing with faster defaults:
    - `OPENCLAW_VOICE_SILENCE_SEC` (default `0.65`)
    - `OPENCLAW_VOICE_MAX_UTTERANCE_SEC` (default `15.0`)
    - `OPENCLAW_VOICE_SILENCE_THRESHOLD` (default `0.01`)
  - Suppressed barge-loop no-speech spam via `suppress_no_speech_log=True` for busy polling.
  - Queue guard now rejects punctuation/noise-only fragments (e.g., `. . . .`, `0 1 0`).

### Added
- Expanded parser tests in `tests/test_openclaw_voice_cue_parsing.py`:
  - spoken numeric cue phrase (`zero, one, zero, two ...`)
  - natural exit phrase mapping
  - noise-fragment filtering checks

### Validation
- `python -m py_compile modules/infrastructure/cli/src/openclaw_voice.py modules/infrastructure/cli/tests/test_openclaw_voice_cue_parsing.py`: PASS
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q --capture=no modules/infrastructure/cli/tests/test_openclaw_voice_cue_parsing.py`: PASS (7 passed)

### WSP Compliance
- **WSP 22**: ModLog documentation
- **WSP 5**: Added targeted regression tests

## V0.3.5 - OpenClaw Voice Barge Robustness + Queue Behavior (2026-02-24)

### Added
- STT cue tolerance for spoken/digit artifacts in `src/openclaw_voice.py`:
  - Numeric normalization fallback now accepts transcripts like `0, 2, 0, 1, 0`.
  - Repeated cue stripping now maps `0102 0102 ...` to payload-only conversation text.
- New tests in `tests/test_openclaw_voice_cue_parsing.py` for:
  - Standard cue parsing
  - Repeated cue parsing
  - Digit-artifact parsing
  - Non-cue rejection

### Changed
- Busy-turn queue behavior now supports replace-latest mode via
  `OPENCLAW_VOICE_QUEUE_REPLACE_LATEST` (default `1`) to avoid stale queued utterances.
- IronClaw voice/chat launch paths now auto-enable local continuity defaults when unset:
  - `OPENCLAW_IRONCLAW_ALLOW_LOCAL_FALLBACK=1`
  - tuned autostart wait/cooldown defaults

### Validation
- `python -m py_compile` on updated CLI sources: PASS
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q --capture=no modules/infrastructure/cli/tests/test_openclaw_voice_cue_parsing.py`: PASS (4 passed)

### WSP Compliance
- **WSP 22**: ModLog documentation
- **WSP 5**: Added targeted parser test coverage

## V0.3.4 - Follow-WSP CLI Wiring (2026-02-14)

### Added
- New CLI switch `--follow-wsp [task]` in `src/main_menu.py`.
- New interactive menu option `15` for follow-WSP execution.
- `_run_follow_wsp(task)` helper that routes to `WSPOrchestrator.follow_wsp(...)` and reports WSP_00 gate status.
- Test file `tests/test_follow_wsp_menu.py` covering:
  - empty task guard
  - success path output
  - blocked gate path output

### Changed
- `tests/README.md` updated with follow-WSP test and pytest command.

### WSP Compliance
- **WSP 22**: ModLog documentation
- **WSP 5**: test coverage for new CLI routing

## V0.3.1 - Channel Registry Controls (2026-02-02)

### Added
- **Channel Registry Menu** (`C` option in YouTube DAEs): list + add channels via shared registry
- Channel selection prompts now read from the registry (scheduler, persona, indexing, rotation status)

### Files Changed
- `src/youtube_menu.py`: New Channel Registry submenu + dynamic rotation/status mapping
- `src/youtube_controls.py`: Scheduler/persona channel lists now registry-driven
- `src/utilities.py`: `select_channel()` now uses registry
- `src/indexing_menu.py`: Indexing rotation now uses registry browser groups

### WSP Compliance
- **WSP 22**: ModLog documentation
- **WSP 60**: Registry stored in module memory

## V0.3.2 - Channel-Aware Batch Enhancement (2026-02-04)

### Changed
- **Batch Enhance Videos** now passes selected channel to enhancement runner
- Per-channel checkpoints used by indexing menu (`enhancement_checkpoint_<channel>.json`)

### Files Changed
- `src/indexing_menu.py`: pass `--channel` and use channel-scoped checkpoint

### WSP Compliance
- **WSP 22**: ModLog documentation

## V0.3.3 - Canonical Test Artifact Path (2026-02-06)

### Changed
- Test video indexing now writes JSON artifacts under `memory/video_index/test`

### Files Changed
- `src/indexing_menu.py`: test path now resolved from repo root

### WSP Compliance
- **WSP 22**: ModLog documentation

## V0.3.0 - Rotation Controls Menu (2026-01-28)

### Added

- **Rotation Controls Menu** (`R` option in YouTube DAEs):
  - Test swap to channel (with UI-TARS verification)
  - Check rotation status (current channel on Chrome/Edge)
  - Toggle rotation enable/disable
  - Toggle halt on error
  - Set rotation order
  - Quick swap shortcuts (Move2Japan <-> UnDaoDu)

- **Helper functions**:
  - `_handle_rotation_controls_menu()`: Main rotation controls submenu
  - `_test_swap_to_channel(target)`: Test account swap with TarsAccountSwapper
  - `_check_rotation_status()`: Check active channel on both browsers

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `YT_ROTATION_ENABLED` | true | Enable/disable rotation |
| `YT_ROTATION_ORDER` | Move2Japan,UnDaoDu,FoundUps,RavingANTIFA | Channel rotation order |
| `YT_ROTATION_HALT_ON_ERROR` | false | Stop rotation on errors |

### Files Changed
- `src/youtube_menu.py`: Added Rotation Controls menu and handlers

### WSP Compliance
- **WSP 22**: ModLog documentation
- **WSP 87**: Navigation Protocol (account swap testing)

---

## V0.2.1 - Video Lab Auto Mode (2026-01-22)

### Added
- Video Lab menu uses env defaults and supports auto mode for index-based Shorts.

### Changed
- Optional upload now runs across supported channels (including FoundUps).

### WSP Compliance
- **WSP 22**: ModLog documentation

## V0.2.0 - Path Resolution Fixes (2026-01-22)

### AUDIT: Deep Dive Indexing Menu

Conducted comprehensive audit of all 6 indexing menu options. Fixed critical path resolution issues that would cause failures when CWD != repo root.

### Fixed

- **`_handle_batch_indexing()`**: Replaced relative paths with absolute paths
  - `data/{channel}_video_ids.txt` -> `repo_root / "data" / f"{channel}_video_ids.txt"`
  - `scripts/batch_index_videos.py` -> `repo_root / "scripts" / "batch_index_videos.py"`
  - Added `cwd=str(repo_root)` to subprocess.run()

- **`_handle_batch_enhancement()`**: Replaced relative paths with absolute paths
  - `memory/enhancement_checkpoint.json` -> `repo_root / "memory" / "enhancement_checkpoint.json"`
  - `memory/video_index/{channel}` -> `repo_root / "memory" / "video_index" / channel`
  - `scripts/batch_enhance_videos.py` -> `repo_root / "scripts" / "batch_enhance_videos.py"`
  - Added `cwd=str(repo_root)` to subprocess.run()

- **`_handle_training_data_extraction()`**: Replaced relative paths with absolute paths
  - `memory/video_index/{channel}` -> `repo_root / "memory" / "video_index" / channel`
  - `memory/training_data/{channel}` -> `repo_root / "memory" / "training_data" / channel`

### Audit Results

| Option | Handler | Status | Notes |
|--------|---------|--------|-------|
| 1 | Gemini AI Indexing | OK (fragile) | Selenium/DOM-based |
| 2 | Whisper Indexing | OK | Dependencies available |
| 3 | Test Video Indexing | OK | API-based |
| 4 | Batch Index Channel | FIXED | Path resolution |
| 5 | Batch Enhance Videos | FIXED | Path resolution |
| 6 | Extract Training Data | FIXED | Path resolution |

### WSP Compliance
- **WSP 22**: ModLog documentation
- **WSP 50**: Pre-action verification (audited before fixing)
- **WSP 62**: File size enforcement (thin router pattern)

---

## V0.4.0 - Claw Runtime Identity Contract (2026-02-24)

### Changed
- Enforced runtime identity contract:
  - `012` = operator/commander (CLI prompt + sender identity)
  - `0102` = agent output identity
- Restored operator prompt and session continuity for command channels:
  - chat input prompt: `012>`
  - voice input prompt: `012>`
  - session keys: `local_repl_012`, `voice_repl_012`
- Updated Claw action command routing sender to `@012`:
  - `modules/infrastructure/cli/src/openclaw_chat.py`
  - `modules/infrastructure/cli/src/openclaw_voice.py`
  - `modules/infrastructure/cli/src/openclaw_menu.py`
  - `modules/infrastructure/cli/src/main_menu.py`
- Added regression guard test:
  - `modules/infrastructure/cli/tests/test_identity_contract_guard.py`

### WSP Compliance
- **WSP 22**: ModLog traceability
- **WSP 73**: OpenClaw command path remains Partner -> Principal -> Associate

---

## V0.4.1 - Connect WRE CLI Command (2026-02-24)

### Added
- `modules/infrastructure/cli/src/main_menu.py`
  - New CLI flag: `--connect-wre`
  - New interactive option: `19. Connect WRE (preflight + readiness check)`
  - New `_run_connect_wre(verbose=False)` status routine that reports:
    - command wiring (`coded=YES`)
    - preflight connection state (`CONNECTED|PARTIAL`)
    - runtime readiness (`READY|INSUFFICIENT_DATA|DEGRADED|BLOCKED|DISABLED`)
    - enforcement state (`manual_enforced`, `auto_enforced_now`)
    - sample coverage and alert counts

### WSP Updates
- Added `Connect WRE` operational CLI hook to:
  - `WSP_framework/src/WSP_97_System_Execution_Prompting_Protocol.md`
  - `WSP_knowledge/src/WSP_97_System_Execution_Prompting_Protocol.md`

### WSP Compliance
- **WSP 22**: ModLog traceability
- **WSP 97**: System execution protocol includes canonical WRE connection command

---

## V0.1.0 - Initial Extraction (2026-01-21)

### Created

Extracted CLI components from main.py per WSP 62 (file size enforcement).

### Files

- **indexing_menu.py**: YouTube indexing submenu handlers
- **youtube_menu.py**: YouTube DAEs submenu handlers
- **utilities.py**: Common helpers (select_channel, env_truthy, etc.)

### WSP Compliance
- **WSP 62**: File size enforcement
- **WSP 49**: Module structure

---

## Change Template

```markdown
## VX.X.X - Description (YYYY-MM-DD)

### Added
-

### Changed
-

### Fixed
-

### WSP Compliance
-
```
