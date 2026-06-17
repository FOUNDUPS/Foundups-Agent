# Video Indexer Tests - ModLog
**WSP Compliance**: WSP 34 (Test Documentation), WSP 22 (Change Log)

## 2026-06-17 - STUDIO_ASK_SHADOW_DOM_SELECTORS_PHASE1

### Test Run
- **Command**: `python -m pytest modules/ai_intelligence/video_indexer/tests/ -q`
- **Result**: 90 passed, 2 skipped, 8 FAILED (all pre-existing, unrelated:
  4x `gemini_video_analyzer.py` `_pattern_memory` AttributeError; 4x live-browser
  integration/stage tests needing a signed-in Chrome on 9222 - "Chrome not
  running on port 9222" / "Expected 10 videos, got 0"). None touch
  `studio_ask_indexer.py` or the new shadow-DOM files.
- New `test_studio_ask_shadow_dom.py`: 10 passed. Prior #825/#827 suites
  (`test_studio_ask_header.py` + `test_studio_ask_human_input.py` +
  `test_studio_ask_channel_context.py`): 44 passed (unchanged behavior via the
  flat fallback).

### Notes
- `test_studio_ask_shadow_dom.py`: NON-VACUOUS flat-fails/shadow-finds. A
  `ShadowDriver` models a shadow tree where the OLD flat selector is ABSENT
  (`find_element` raises) but the element exists under a shadow root (resolved by
  `execute_script`). The flat path returns None (pre-fix flat-only code fails)
  while the deep finder returns the real element. Covers title + Ask button +
  full primary path + dialog-open-via-children + zero-state-not-scraped +
  wrong/error page fail-closed (#827) + no-persist-on-failure + #825 single
  submit preserved. NON-VACUITY also proven by disabling the deep finder (the
  pre-slice flat-only model) -> both shadow-rooted elements resolve to None/False.

## 2026-06-16 - STUDIO_ASK_HUMAN_INPUT_BEHAVIOR_PHASE1

### Test Run
- **Command**: `python -m pytest modules/ai_intelligence/video_indexer/tests/test_studio_ask_human_input.py modules/ai_intelligence/video_indexer/tests/test_studio_ask_header.py -q`
- **Result**: PASS (14 new + 12 updated = 26 tests)
- **Full module**: 62 passed, 2 skipped, 8 FAILED (all pre-existing, unrelated:
  4x `gemini_video_analyzer.py` `_pattern_memory` AttributeError; 4x live-browser
  integration tests needing a signed-in Chrome on 9222 - the attached Chrome was
  on a Gemini page, `0 videos found`). None touch `studio_ask_indexer.py`.

### Notes
- `test_studio_ask_human_input.py`: NON-VACUOUS single-submit regression. A mock
  contenteditable models submit-on-Enter; asserts EXACTLY 1 submit on a multi-line
  prompt. Old code (`send_keys(ASK_PROMPT)` + Enter) yields 16 submits -> regression
  FAILS on old code. Also covers human_type reuse, Shift+Enter soft newlines,
  wait-for-stabilization scraping, and fail-closed refusal (nothing persisted).
- `test_studio_ask_header.py`: two #817 assertions updated from whole-string
  `send_keys` to char-by-char content (helper `_typed_text`) - reflects the new
  newline-safe typing contract.
- MOCK-ONLY: selectors / real send-button presence / streaming timing are NOT
  live-verified (#817 KNOWN-GAP class); 012 live re-test required.

## 2026-02-06

### Test Run
- **Command**: `python -m pytest modules/ai_intelligence/video_indexer/tests/test_studio_ask_indexer_persistence.py -v`
- **Result**: PASS (1 test)
- **Warnings**:
  - PytestConfigWarning: Unknown config option `asyncio_default_fixture_loop_scope`
  - PytestConfigWarning: Unknown config option `asyncio_mode`
  - Pydantic warning about `<built-in function any>` type

### Notes
- Validates Ask-Gemini JSON persistence path and IndexData conversion.

### Test Run
- **Command**: `python -m pytest modules/ai_intelligence/video_indexer/tests/test_studio_ask_indexer_persistence.py modules/ai_intelligence/video_indexer/tests/test_studio_ask_indexer_signals.py -v`
- **Result**: PASS (3 tests)
- **Warnings**:
  - PytestConfigWarning: Unknown config option `asyncio_default_fixture_loop_scope`
  - PytestConfigWarning: Unknown config option `asyncio_mode`
  - Pydantic warning about `<built-in function any>` type

### Notes
- Validates signal helpers (STOP/REINDEX) and index count telemetry helpers.

## 2026-03-11

### Browser Isolation Fix
- **Change**: Added `group_channels_by_browser()` filter in `studio_ask_indexer.py`
- **Purpose**: Prevent Chrome OOPS on Edge-only channels (antifaFM, FoundUps)
- **Test**: Manual verification of channel grouping
  ```
  CHROME: ['move2japan', 'undaodu']
  EDGE: ['foundups', 'antifafm']
  ```
- **Result**: PASS - Chrome no longer accesses antifaFM/FoundUps channels

### WSP Compliance
- WSP 50: Verified channel registry before modifying indexer
- WSP 72: Browser isolation respects module boundaries
