## 2026-11-10 — Pre-save audit and audience configuration

The existing protected directives runner selects114 cases, including48 new
pre-save audit/configuration controls. Synthetic drafts exercise actual preparation
and Save owners: metadata completeness, eligible analysis reuse, observed audience,
late changes, exact identity, invalid/DST slots and detail-owner handoff. Thirteen
configuration cases cover native-ID Yes/No without enabling channels, invalid or
conflicting configuration with zero writes, and registry audience round trips.
All66 prior directive/upload controls remain. No browser/model/public action occurs.

## 2026-11-05 — Native visibility readiness regression

The same four-file private-directive consumer selection now passes66 controls
(retained60 plus six readiness cases). Actual `open_visibility_dialog` uses a
synthetic driver: the existing visible native schedule radio and prior named/
legacy paths pass; hidden, stale or absent native controls alone remain unready. The regression
first failed only the native-radio case on the previous source. The existing
qualified replay uses fixed credential-free children, private paths and effect
denials; no real browser, Audience decision or schedule is exercised.

## 2026-11-01 — Private operator directive consumers

The fixed four-module consumer selection passed60 cases:19 detail/button,
16 real queue claim/reload,9 inline popup and16 Shorts controls. Canonical test
admission classified all four collectable without quarantine exceptions. Minimal
explicit environment, private paths and denied browser/model/network/process
effects were used; no captured JUnit streams or skipped cases.

`test_video_policy_consumers.py` tests late preserve/pause/foreign edits at actual
Save. `test_video_policy_save_readback.py` proves durable unknown retry refusal,
fresh-document metadata readback and no verification from a no-op refresh or a
metadata-only schedule read. `test_video_policy_inline.py` exercises actual popup
submission with strict target association and no fallback after uncertain click.
The fourth module is Shorts `test_operator_upload_policy.py`.

Adjacent185 cases passed: existing selected-batch147, metadata evidence23 and
publisher boundary15. Strict typed DOM fixtures gained the new explicit edit
session contract; valid synthetic native IDs replaced invalid placeholders.
All original assertions and selected-batch case counts remain.

## 2026-10-29 — Qualified scheduled inventory, offline only

`test_scheduled_inventory.py` exercises actual parser/collector and consumer
definitions with synthetic DOM snapshots: useful multi-page slots and qualified
empty; raw parse failures and upload-date rejection; native/URL account mismatch;
extra/missing filters; unknown first/final pagination; repeated pages, limits,
later drift and failed page transitions. Tracker/auditor/CPS/scheduler controls
verify positive reads plus no clean/absence/auto-heal/reset on unknown. Existing
visibility and post-audit breadcrumb tests remain adjacent regressions.
The local selection passed102 cases, zero failures/errors/skips:86 inventory and
consumer controls,9 existing visibility checks and7 breadcrumb controls. Useful
positive repairs use fake writers; no schedule is changed. Explicitly Scheduled
modern date cells/tooltips pass while generic/upload dates and contradictory
slots fail. This does not qualify a live selector or a real saved schedule.

The external local harness clears the child environment to a fixed credential-
free allowlist before source imports, disables dotenv/bytecode/plugin autoload,
denies process/HTTP/socket/SQLite effects and confines writes/registry/temporary
storage outside Git. A timers/tasks-only test loop avoids Windows asyncio's
otherwise real TCP wakeup socketpair. No browser, scheduler service, model or
main.py is started. Synthetic inputs qualify logic, not installed DOM selectors
or live scheduling. Manual browser suites below remain excluded.

## Offline selected-batch closure (2026-10-22)

The CI job `youtube-selected-batch` runs explicit mocked scheduler/adapter and
transcript-language cases using `--import-mode=importlib -p pytest_asyncio.plugin`
with dotenv loading and plugin autoload disabled. No browser/model is started.
`test_remote_cli.py` covers edit identity and visibility, malformed receipts,
partial results, attempted-write budgets, bounded pagination, repeatable preview,
channel-sync suppression and honest description-sync evidence. Other manual
browser suites below are not substituted by these offline checks.

# YouTube Shorts Scheduler - Test Documentation

Remote regression coverage: `test_remote_cli.py` exercises host preflight,
nonpersistent previews, exact recording batches (3/8/13 and 61 across pages),
whole-batch defaults, incomplete receipts and optional limits. It uses fake
browser/model boundaries; no live publication. For combined module runs use
`--import-mode=importlib` to avoid colliding `tests` package names.

> **WSP 34 Compliance**: Test documentation for the youtube_shorts_scheduler module.

## Test Overview

This module contains integration tests for YouTube Studio automation via Selenium.
Tests require a Chrome browser running in debug mode on port 9222.

## Selenium Test Suite (V0.8.x)

| Test File | Description |
|-----------|-------------|
| `test_full_chain.py` | Full cake via production scheduler (index → title → description → schedule → done/save → page save) |
| `test_layer0_entry.py` | Navigate to unlisted, select video |
| `test_layer1_filter.py` | Apply unlisted filter |
| `test_layer2_edit.py` | Open edit page, find visibility |
| `test_layer3_schedule.py` | Visibility → Schedule → date/time → Done |
| `test_layer4_schedule_audit.py` | Scan scheduled list, detect date/time conflicts |

## Quick Run

```bash
# Run the production-aligned full cake test
python -m modules.platform_integration.youtube_shorts_scheduler.tests.test_full_chain --selenium
```

## Key Features (V0.8.x)

### Deterministic 012 Interaction (Occam)
- Production scheduling favors stability in dense UI clusters (date/time/timezone):
  - `scrollIntoView` → delay → `.click()` → delay
  - ActionChains/JS fallbacks only when needed

## Test Modes

### Layer 1 Filter Tests

```bash
# URL-based filter (default, most reliable)
python -m modules.platform_integration.youtube_shorts_scheduler.tests.test_layer1_filter

# URL-first with DOM fallback
python -m modules.platform_integration.youtube_shorts_scheduler.tests.test_layer1_filter --fallback
```

### Layer 3 Schedule Test

```bash
# Full schedule flow (production-aligned DOM automation)
python -m modules.platform_integration.youtube_shorts_scheduler.tests.test_layer3_schedule --selenium
```

### Layer 4 Schedule Audit (Conflicts)

```bash
# Scan scheduled list and report duplicate date/time slots
python -m modules.platform_integration.youtube_shorts_scheduler.tests.test_layer4_schedule_audit --selenium
```

## Prerequisites

1. Chrome running with remote debugging:
   ```bash
   chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\chrome_profile"
   ```

2. Logged into YouTube Studio for the target channel

## Coverage Status (V0.7.0)

| Layer | Component | Status |
|-------|-----------|--------|
| L0 | Entry (navigate + select) | ✅ Selenium |
| L1 | Filter (URL-based) | ✅ Selenium |
| L2 | Edit (visibility section) | ✅ Selenium |
| L2.5 | SKILLz (FFCPLN enhance) | ✅ Selenium |
| L3.1 | Visibility button | ✅ Selenium |
| L3.2 | Schedule expand | ✅ Selenium + 3s wait |
| L3.3 | Date (Ctrl+A + type) | ✅ Selenium |
| L3.4 | Time (Ctrl+A + type) | ✅ Selenium |
| L4 | Done button | ✅ Selenium |
| L5 | Save + Return | ✅ Selenium (page save hardened) |

## DBA Logging (PatternMemory)

On successful scheduling, the production scheduler records an outcome into the existing WRE SQLite DBA:

- **DB**: `modules/infrastructure/wre_core/data/pattern_memory.db`
- **Skill name**: `youtube_shorts_scheduler_schedule`
- **Purpose**: 0102 can recall what was scheduled without rescanning Studio.

## Schedule → Index Weave (Digital Twin)

When `YT_SCHEDULER_INDEX_WEAVE_ENABLED=true` (default), the production scheduler will:

- Ensure an index artifact exists at `memory/video_index/{channel}/{video_id}.json` (Gemini Tier 1 when missing)
- Append a compact `0102 DIGITAL TWIN INDEX v1` JSON block into the video description
- Update the index JSON with `scheduling` + `description_sync` after successful scheduling

## Architecture Decisions

- **ADR-014**: Occam 012 Deterministic Clicks (V0.8.x)
  - Dense schedule UI (date/time/timezone) is prone to mis-targets with Bezier/jitter.
  - Deterministic click cadence reduces drift and improves repeatability.

## Last Updated

- **V0.8.x** (2026-01-18): Production-aligned full cake; deterministic click cadence; page save hardened
# Scheduling pre-save audit controls

`test_presave_audit.py` exercises incomplete metadata, exact channel audience,
unknown/changed controls, late draft changes, valid/invalid schedule intent,
matched evidence repair and the content-row handoff to the detail owner. No live
browser, GPU, model, upload or scheduling operation runs. Existing private-policy
and durable readback controls remain applicable with fully specified draft fixtures.
