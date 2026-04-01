# TestModLog — public/member/tests/

Test evolution log for the p.fMALL member shell test suite.

---

## 2026-04-02 | Concierge Channel Attachment Phase 1 (WSP 97)

**File**: `test_concierge_channel_attachment_phase1.py`
**Tests**: 66 | **Classes**: 8 | **Result**: 66 passed
**Worker**: C

Validates channel/account attachment surface and Mall projection hooks:

| Class | Count | What it covers |
|-------|-------|----------------|
| TestChannelsModeAction | 6 | 'channels' mode in mode sheet, opens plane, injects section, scrolls |
| TestChannelListRendering | 13 | CHANNEL_PLATFORMS (4 types), catalog reader, row markup, video count |
| TestAttachDetachToggle | 6 | toggleChannelAttach, attach/detach commands, attached class, state |
| TestMallProjectionHooks | 9 | Populate/Personal/Search Mall buttons, commands, setProjection, typeof |
| TestRedDogAPIChannels | 6 | openChannels/getChannels/toggleChannel/populateMyMall/openPersonalMall/openSearchMall |
| TestChannelCSS | 10 | Section/row/icon/info/name/meta/toggle/actions classes, phone 44px |
| TestTruthfulHooks | 3 | No fake AI, no fetch, all commands use emitRedDogCommand |
| TestNoRegression | 13 | window.redDog, AI tools, briefing, recs, modes, CSS preserved |

**Key design decisions**:
- Channel data sourced from `window._mallVideoCatalog` (B's catalog)
- Attach/detach uses local state + `reddog:command` events (no backend)
- Mall projection hooks emit commands + call `setProjection()` with typeof guards
- All interactive elements 44px minimum on phone (WCAG)

---

## 2026-04-02 | Red Dog Mall Controls Phase 1 (WSP 97)

**File**: `test_reddog_mall_controls_phase1.py`
**Tests**: 81 | **Classes**: 9 | **Result**: 81 passed
**Worker**: C

Validates Red Dog AI tools controls for Mall projection:

| Class | Count | What it covers |
|-------|-------|----------------|
| TestAIToolsModeAction | 6 | 'tools' mode in mode sheet, opens plane, injects section |
| TestCategoryProjection | 13 | 6 categories, setCategory, typeof guards, default 'all' |
| TestCreatorEntityHook | 2 | Creator search button, command emission |
| TestDensityPresets | 10 | 4 presets (2x3/3x4/3x5/5x8), setDensity, API guard |
| TestMotionMode | 7 | Snap/Glide toggle, default snap, API guard, command event |
| TestTruthfulHooks | 9 | No fake AI, no fetch, CustomEvent dispatch, briefing state |
| TestRedDogAPIExtensions | 7 | openTools/set/getCategory/Density/MotionMode on window.redDog |
| TestAIToolsCSS | 10 | Pills, active state, mono font, 44px phone targets |
| TestNoRegression | 17 | All prior Red Dog behaviors preserved |

**Key design decisions**:
- All controls emit `reddog:command` CustomEvent for B to wire
- typeof guards on all `mallTileField` API calls
- No backend calls, no fake AI responses
- Briefing reflects current category/density/motion when non-default

---

## 2026-04-02 | Red Dog FoundUp Entry Alignment Phase 7

**File**: `test_reddog_foundup_entry_alignment_phase7.py`
**Tests**: 65 | **Classes**: 7 | **Result**: 65 passed
**Worker**: C

Validates entry-page Red Dog alignment with Mall Red Dog:

| Class | Count | What it covers |
|-------|-------|----------------|
| TestDigitalTwinIdentity | 4 | "Your digital twin" subtitle, logo, aria-label |
| TestEntryBriefing | 12 | Briefing container, 6 data fields, CSS, populate hook |
| TestEntryRecommendations | 16 | 4 local actions, pills, smooth scroll, clipboard, no backend |
| TestFABAlignment | 6 | State ring, active class, WCAG 44px, safe area, gradient |
| TestEntryRedDogAPI | 8 | window.entryRedDog: open/close/toggle/isOpen/getContext |
| TestConciergeTopicsUpdated | 4 | "Who is Red Dog?" digital-twin topic, 4 entry topics |
| TestNoRegression | 15 | Entry shell, Mall Red Dog, concierge.js all preserved |

---

## 2026-04-02 | Red Dog Mobile Ergonomics Phase 6

**File**: `test_reddog_mobile_ergonomics_phase6.py`
**Tests**: 43 | **Classes**: 5 | **Result**: 43 passed
**Worker**: C

| Class | Count | What it covers |
|-------|-------|----------------|
| TestAvatarTouchTarget | 4 | 44px WCAG minimum on avatar/trigger/img/placeholder |
| TestMobileSpacing | 10 | 480px query, safe-area, dvh, option/invite 44px targets |
| TestModeSheetPhone | 5 | Mode action 44px, sheet wider, briefing/rec phone styles |
| TestInteractionGrammar | 10 | Tap/double-tap/hold, pointer guards, swipe, escape, scrim |
| TestNoRegression | 14 | Briefing/recs/invites/options/mode sheet/desktop query |

---

## 2026-04-02 | Red Dog Recommended Actions Phase 5

**File**: `test_reddog_recommended_actions_phase5.py`
**Tests**: 63 | **Classes**: 6 | **Result**: 63 passed
**Worker**: C

---

## 2026-04-02 | Red Dog Context Briefing Phase 4

**File**: `test_reddog_context_briefing_phase4.py`
**Tests**: 48 | **Classes**: 6 | **Result**: 48 passed
**Worker**: C

---

## Suite Summary

| File | Tests | Worker | Phase |
|------|-------|--------|-------|
| test_concierge_channel_attachment_phase1.py | 66 | C | Channel attachment |
| test_reddog_mall_controls_phase1.py | 81 | C | WSP 97 controls |
| test_reddog_foundup_entry_alignment_phase7.py | 65 | C | Entry alignment |
| test_reddog_mobile_ergonomics_phase6.py | 43 | C | Phone ergonomics |
| test_reddog_recommended_actions_phase5.py | 63 | C | Recommended actions |
| test_reddog_context_briefing_phase4.py | 48 | C | Context briefing |
| (other member tests) | ~446 | B/mixed | Mall shell, tiles, etc. |
| **Total** | **812** | | |
