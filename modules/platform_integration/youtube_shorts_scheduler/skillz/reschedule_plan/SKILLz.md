---
# Metadata (YAML Frontmatter)
name: reschedule_plan
description: Compute a dry-run REBALANCE PLAN for over-crowded schedule days -- move count>cap excess onto under-target upcoming days into US-ET peak slots per channel tz (read-only, agent-invoked; apply is Phase 2)
version: 1.0_prototype
author: 0102
created: 2026-06-19
agents: [qwen, gemma]
primary_agent: qwen
intent_type: PLANNING
promotion_state: prototype
pattern_fidelity_threshold: 0.90
test_status: needs_validation

# Dependencies
dependencies:
  data_stores:
    - name: schedule_tracker
      type: json
      path: modules/platform_integration/youtube_shorts_scheduler/memory/schedule_{channel_id}.json
  required_context:
    - horizon_days: "How far ahead to search for under-target days (default 90)"
  throttles:
    - name: read_only
      max_rate: unlimited
      cost_per_call: 0

# Metrics Configuration
metrics:
  pattern_fidelity_scoring:
    enabled: true
    frequency: every_execution
    scorer_agent: gemma
  promotion_criteria:
    min_pattern_fidelity: 0.90
    min_outcome_quality: 0.85
    min_execution_count: 100
    required_test_pass_rate: 0.95
category: capability-uplift
evals: []
retirement_date: null
---
# reschedule_plan

**Purpose**: Compute a dry-run REBALANCE PLAN for over-crowded schedule days. The
historical backlog was scheduled at up to 8/day before the per-day cap landed
(`HARD_CAP_PER_DAY = 3`, `schedule_tracker.py`, #844). This skill proposes moving
the excess (`count > cap`) off each over-crowded day onto the nearest under-target
upcoming days, placing each moved item into a US-ET peak slot converted to the
channel's Studio-account timezone (`peak_window.py`, #847).

**Intent Type**: PLANNING

**Agent**: Qwen (plans the rebalance) / Gemma (validates the deterministic math).

**For the agent, never for a human**: the WRE/daemon triggers this SKILLz and the
`--agent-command` surface invokes it programmatically. 012 only observes the emitted
breadcrumb + PatternMemory outcome and the JSON plan. There is NO manual-012 apply.

---

## DRY-RUN / READ-ONLY (Mode B Phase 1)

This is the PREVIEW/decision layer. `DRY_RUN` is ALWAYS `True` in this slice: the
skill RETURNS the plan and emits learning signals, but NEVER mutates a schedule,
never opens a browser, never calls a live model. The mutating DOM apply (click
"Scheduled" -> `ytcp-video-visibility-edit-popup` date/time picker) is an explicit
**Phase-2** follow-up, NOT built here.

---

## Data source (offline, reliable, no browser)

Reads `memory/schedule_<CHANNEL_ID>.json` via `ScheduleTracker`. The tracker stores
BOTH `schedule` (`date -> count`) AND `video_ids` (`date -> [video_ids]`). Channels
+ IDs + IANA timezone come from `youtube_channel_registry` (`get_channels(role="shorts")`).
No DOM, no live model, no mutation.

---

## Plan granularity (Phase 0 finding)

A video<->date mapping EXISTS (`video_ids`), so the plan NAMES which videos move
when the ids are recorded for the over-crowded day. BUT `count` is authoritative
and can exceed the recorded id list (`set_count()`/`sync_from_youtube()` can leave
`video_ids` incomplete, and the historical 8/day backlog predates id tracking).
When recorded ids are fewer than the excess, the surplus moves are labelled
`video_id="(needs-live-list)"` -- naming those specific videos needs the LIVE
Studio list (**Phase 2**).

---

## The plan algorithm

For each channel:
1. `find_over_cap_days`: days with `count > cap`; `excess = count - cap` must move.
2. `find_target_days`: under-cap upcoming days (`count < cap`, after today, within
   horizon), excluding the over-crowded source days; nearest-first.
3. For each excess item, place it on the nearest target with free capacity, filling
   each target up to (NEVER over) the cap. Assign the peak slot by fill-index
   (0->08:00 ET morning, 1->12:00 ET lunch, 2->20:00 ET evening), converted to the
   channel tz (`convert_et_to_channel_tz`, DST-aware).

Excess that finds no under-cap target within the horizon is counted as
`unplaceable_moves`.

---

## Output (consumed by daemon / Qwen)

```json
{
  "dry_run": true,
  "skill": "reschedule_plan",
  "cap": 3,
  "channel_count": 4,
  "channels": [
    {
      "channel_id": "...", "channel_name": "FoundUps", "timezone": "America/New_York",
      "cap": 3, "days_over_cap": 1, "total_moves": 2, "unplaceable_moves": 0,
      "moves": [
        {"channel_id":"...","channel_name":"FoundUps","from_date":"Jan 5, 2026","to_date":"Jan 2, 2026","slot_et":"08:00","slot_local":"8:00 AM","video_id":"abc123"},
        {"channel_id":"...","channel_name":"FoundUps","from_date":"Jan 5, 2026","to_date":"Jan 2, 2026","slot_et":"12:00","slot_local":"12:00 PM","video_id":"(needs-live-list)"}
      ]
    }
  ],
  "summary": {"days_over_cap": 1, "total_moves": 2, "unplaceable_moves": 0, "channels_needing_rebalance": 1},
  "success": true,
  "breadcrumb_emitted": true,
  "outcome_stored": true
}
```

---

## Signal emission (WRE self-improvement testbed)

Every run emits BOTH:
- **Breadcrumb** (WSP 91) via `get_breadcrumb_telemetry().store_breadcrumb(source_dae="youtube_shorts_scheduler", event_type="reschedule_plan", ...)` with the full plan in metadata.
- **PatternMemory SkillOutcome** (WSP 60/48) via `PatternMemory().store_outcome(SkillOutcome(skill_name="reschedule_plan", ...))`.

---

## Invocation

**SKILLz (WRE / daemon):**
```python
from modules.platform_integration.youtube_shorts_scheduler.skillz.reschedule_plan.executor import run_skill
plan = run_skill()  # dry-run; emits breadcrumb + PatternMemory
```

**--agent-command (agent/DAE-invocable, structured JSON):**
```bash
python main.py --agent-command "youtube action reschedule_plan"
# adapter spawns:
python -m modules.platform_integration.youtube_shorts_scheduler.skillz.reschedule_plan.run_skill --json
```

---

## Malleable seams (intentional)

- **Data source** is injected via `load_schedule` (default: `ScheduleTracker` JSON).
  A future LIVE Studio scrape plugs in here WITHOUT touching the plan math.
- **Plan math** lives in `src/reschedule_planner.py` behind pure functions
  (`find_over_cap_days` / `find_target_days` / `assign_peak_slot`). Slot policy and
  target selection are independently swappable.

---

## Out of scope (separate Phase-2 follow-ups -- NOT built here)

- **DOM apply / mutation**: the `ytcp-video-visibility-edit-popup` date/time picker
  applier that consumes the plan rows. Each plan row is already a complete move
  instruction (channel, from_date, to_date, slot_et, slot_local, video_id).
- **View-based ("low-viewed first") prioritization**: choosing WHICH videos move by
  per-video view counts -- needs view data that is NOT in the tracker (separate
  Phase-2 signal). Target-DAY selection here is date-driven.
- The live filter-fix; the music-vs-talk content gate.

---

## Expected patterns (WSP 95 fidelity)

```json
{
  "skill": "reschedule_plan",
  "patterns": {
    "channels_loaded": true,
    "over_cap_days_found": true,
    "targets_selected": true,
    "moves_assigned_peak_slots": true,
    "cap_never_exceeded_on_targets": true,
    "breadcrumb_emitted": true,
    "outcome_stored": true
  }
}
```

---

## Success criteria

- A day at 5 (cap=3) plans exactly 2 moves; no target day exceeds the cap.
- A fully-<=cap schedule plans 0 moves (`total_moves == 0`).
- Peak slot + per-channel tz assignment correct (ET -> channel-tz wall clock).
- Breadcrumb + PatternMemory emitted on every run.
- Strictly dry-run: `dry_run == true`, no mutation, no browser, no live model.

**WSP Compliance**: WSP 95 (SKILLz Wardrobe), WSP 77 (Agent Coordination),
WSP 91 (Observability), WSP 60/48 (Pattern Memory), WSP 27 (Phase 0 KNOWLEDGE).
