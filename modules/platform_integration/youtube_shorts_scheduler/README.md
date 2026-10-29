# YouTube Shorts Scheduler

## Local scheduler qualification — 2026-10-29

Calendar audits and optional tracker sync now use `YouTubeStudioDOM.read_scheduled_inventory`.
The additive receipt reports `complete`, `partial` or `failed`, the expected
channel, page/row coverage, retained parsed rows and unparsed raw observations.
Every page must bind the known native `CHANNEL_ID` locations to the exact Studio channel URL and an
actual Scheduled/Has schedule chip. A whole-list read requires the known first
page, bounded progress and known final pagination state; an explicit qualified
empty state can establish zero. Unknown totals remain `None`. A visibility-cell
slot or an explicitly Scheduled-labeled modern Date cell/tooltip can supply a
slot; Uploaded, Published and unlabeled generic dates cannot. Failed filtering refuses an unfiltered read;
the existing Skillz chip-bar filter path is reused.

Partial/failed reads cannot certify a clean calendar, establish absence for
auto-heal, reset tracker state, or supply a known-zero channel cache. Useful
positive slots and observed conflicts remain visible. Tracker reset requires
the matching complete inventory receipt. Legacy list-returning DOM methods are
compatibility helpers, not completeness evidence.
Calendar repair consumers also require that receipt and matching video/slot
bindings; a caller-supplied `status="complete"` alone grants no repair input.

Rotation freezes the canonical receiving ID and verifies first and later
switches using native ID, Studio path and known permission state. Scheduler,
config, tracker, alternate receipts and cache bind to that ID. Failed/unknown
access bypasses writers; permission fallback waits for its canonical once-per-ID
entry. Legacy, unbound or incomplete zero caches cannot suppress a channel.

This layer is locally qualified with synthetic DOM/permission inputs. Installed
browser selectors, account access, full daemon startup and saved schedules still
require separate authorized live qualification. No existing schedule or content
was changed by the offline checks.
An installed page showing only `Scheduled` plus an unlabeled Date column remains
an explicit selector-evidence gap, with unknown slots rather than inferred dates.

**WSP Compliant Module** - YouTube Studio automation for Shorts scheduling.

Remote use: [host requirements and command receipts](docs/REMOTE_SCHEDULING.md)
and the [existing Work skill audit](docs/PRIOR_WORK_AUDIT_2026-09-22.md).
Start with `youtube action scheduling channel=move2japan preflight=true` through
the existing agent adapter. A one-shot command does not require `main.py`.

Skill composition: [ordered workflow and evidence handoffs](skillz/README.md).

## Overview

Automated scheduling system for YouTube Shorts across multiple channels:
- **Move2Japan** (UC-LSSlOZwpGIRIYihaz8zCw)
- **UnDaoDu** (UCfHM9Fw9HD-NwiS0seD_oIA)
- **FoundUps** (UCSNTUXjAgpd4sgWYP0xoJgw)

## Features

- Selenium/UI-TARS DOM automation for YouTube Studio
- Multi-channel scheduling with time slot management
- Channel-specific slot allocation; resolve limits through the shared scheduling policy
- Evidence-gated title/description generation with metadata preservation fallback
- Optional **Schedule → Index Weave**:
  - Reads existing `memory/video_index/{channel}/{video_id}.json` artifacts; this scheduler does not run Gemini or create missing index evidence.
  - Metadata generation can reuse existing index context. Preserving metadata retains the current description.
  - Records scheduling on existing index artifacts. Changed descriptions require independent saved-state readback before sync can be verified; preserving metadata preserves prior sync evidence.
- **Index Utility Routing (POC)**:
  - If indexing identifies 012 voice → route to Digital Twin memory
  - If indexing identifies music/video → route to RavingANTIFA or faceless-video pipeline (module in development)
- Schedule tracking with JSON persistence
- Visibility workflow automation (Unlisted -> Scheduled -> Public)

## Architecture

```
youtube_shorts_scheduler/
├── README.md           # This file
├── INTERFACE.md        # Public API documentation
├── ModLog.md           # Change log
├── requirements.txt    # Dependencies
├── src/
│   ├── __init__.py
│   ├── scheduler.py           # Main scheduler orchestrator
│   ├── channel_config.py      # Multi-channel configuration
│   ├── dom_automation.py      # Selenium DOM interactions
│   ├── schedule_tracker.py    # Schedule state management
│   ├── index_weave.py         # Schedule ↔ Index ↔ Description integration
│   └── content_generator.py   # Title/description templates
└── tests/
    ├── __init__.py
    └── test_scheduler.py
```

## Time Slot Strategy

| Slot | Japan Time | EST Time | Purpose |
|------|------------|----------|---------|
| 1    | 5:00 AM    | 3:00 PM  | US afternoon engagement |
| 2    | 11:00 AM   | 9:00 PM  | US prime time |
| 3    | 5:00 PM    | 3:00 AM  | Japan morning / EU |

## Usage

```python
from modules.platform_integration.youtube_shorts_scheduler.src.scheduler import YouTubeShortsScheduler

# Initialize for a channel
scheduler = YouTubeShortsScheduler(channel="move2japan")

# Gather existing schedule
scheduler.gather_existing_schedule()

# Schedule unlisted videos
scheduler.run_scheduling_workflow(max_videos=10)
```

## DOM Selectors Reference

See `src/dom_automation.py` for comprehensive selector documentation:
- Page 1: Channel Content (Shorts List)
- Page 2: Video Details/Edit Page
- Page 3: Visibility/Scheduling Dialog

## CLI Usage (V0.9.x)

```bash
python main.py
# Select 1 (YouTube DAEs) → 3 (Shorts Scheduler)
# Options:
#   1. Schedule NEXT unlisted Short (full cake)
#   2. Schedule ALL unlisted Shorts (until empty; safety stops on no slots)
#   3. DRY RUN preview (no save)
#   4-5. Multi-channel rotation (browser-grouped)
#   6. Indexing handoff (use YouTube DAEs → 8 [INDEX])
#   7. Full videos placeholder (future layer)
```

## WRE Layer Stack

```
L0:   Select unlisted video
L1:   Open visibility dialog + expand schedule
L2:   Set DATE
L3:   Set TIME
L4:   Click Done → "Scheduled"
L5.1: Related Video modal
L5.2: Select video
L5.3: SAVE
L5.4: Return to list
L5.5: REFRESH (F5) ← CRITICAL before loop
```

## WSP Compliance

- WSP 3: Platform Integration domain
- WSP 22: ModLog documentation
- WSP 49: Standard module structure
- WSP 62: scripts/launch.py extraction
- WSP 80: DAE pattern for autonomous scheduling
- WSP 95: SKILLz.md for content enhancement
- WSP 60 / WSP 73: Index JSON + description-as-cloud-memory (Digital Twin weave)

## Feature Flags

- **`YT_SCHEDULER_INDEX_WEAVE_ENABLED`**: default `true`
  - When enabled, scheduler attempts to index each video (if missing) and append the Digital Twin index block to the description.

- **`YT_SCHEDULER_CONTENT_TYPE`**: default `shorts`
  - Control-plane selector for what the scheduler targets: `shorts` or `videos`.
  - **`videos` is a placeholder surface only** until DOM selectors are implemented (next layer after Shorts stability).

- **`YT_SCHEDULER_VERIFY_MODE`**: default `none`
  - Control-plane placeholder for verification gating: `none` or `wre-tars`.
  - Currently used as a run-intent switch only (tests may consume it); production Shorts scheduling does not hard-require UI‑TARS.

- **`YT_SCHEDULER_INDEX_INFORM_TITLE`**: default `false`
  - When enabled, the local index artifact informs the clickbait title hint (deterministic extraction; no LLM).

- **`YT_SCHEDULER_PRE_SAVE_DELAY_SEC`**: default `1.0`
  - Delay between dialog Done/Save and page-level Save click (stabilizes Studio animation timing).
