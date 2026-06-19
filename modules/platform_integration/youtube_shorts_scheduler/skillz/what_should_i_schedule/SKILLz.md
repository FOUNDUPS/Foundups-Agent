---
# Metadata (YAML Frontmatter)
name: what_should_i_schedule
description: Rank the shorts-enabled channels by scheduling NEED so the daemon works the most-needed channel next (read-only, agent-invoked)
domain: youtube  # WRE auto-fire tag (SkillTriggerMixin domain-discovery, skill_trigger.py:91-115) -> the youtube DAE fires this every cadence cycle (SHORTS_PRIORITY_WIRING_PHASE1)
version: 1.0_prototype
author: 0102
created: 2026-06-19
agents: [gemma, qwen]
primary_agent: gemma
intent_type: PRIORITIZATION
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
    - upcoming_days: "How many upcoming days to inspect per channel (default 7)"
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
# what_should_i_schedule

**Purpose**: Answer "which channel should I schedule next?" by ranking the four
shorts-enabled channels by scheduling NEED. A channel whose upcoming days are empty or
under-target ranks HIGH; a channel already full at the hard cap ranks LOWEST. This feeds
the daemon's scheduler so it works the most-needed channel first.

**Intent Type**: PRIORITIZATION

**Agent**: Gemma (fast deterministic ranking) / Qwen (consumes the ranking to plan).

**For the agent, never for a human**: the WRE/daemon triggers this SKILLz and the
`--agent-command` surface invokes it programmatically. 012 only observes the emitted
breadcrumb + PatternMemory outcome and the JSON output. There is NO manual-012 menu.

---

## Why (the problem)

The shorts daemon rotates across channels but had no signal for *where the gap is*. With
the cap now `HARD_CAP_PER_DAY = 3` (`schedule_tracker.py`, landed #844), a channel that
is empty for the next week is far more urgent than one already filled. This skill turns
the persisted per-channel schedule tracker into a ranked need list so the daemon stops
wasting work on already-covered channels.

---

## Data source (offline, reliable, no browser)

Reads `memory/schedule_<CHANNEL_ID>.json` (map `date -> count`) via the existing
`ScheduleTracker.get_count(date_str)`. Dates are built in the tracker's exact format
(`"Jan 5, 2026"`, Windows-safe). Channels + IDs come from `youtube_channel_registry`
(`get_channels(role="shorts")`). No DOM, no live model, no mutation.

---

## The need / deficit formula

For each channel, inspect the next `N` upcoming days (default 7):
- `count` = scheduled videos that day (tracker).
- per-day `deficit = max(0, HARD_CAP_PER_DAY - count)`.
- `total_deficit` = sum of per-day deficits.
- `days_empty` = days with `count <= 0`.
- `recommend = "schedule" if total_deficit > 0 else "sufficient"`.

Channels are sorted by `total_deficit` desc, then `days_empty` desc, then name asc.
An empty channel (max deficit) ranks first; a channel full at 3/day for every day ranks
last with `recommend="sufficient"`.

---

## Output (consumed by daemon / Qwen)

```json
{
  "success": true,
  "skill": "what_should_i_schedule",
  "upcoming_days": 7,
  "cap": 3,
  "channel_count": 4,
  "recommended_channel": {"channel_id": "...", "name": "FoundUps", "total_deficit": 21, "days_empty": 7, "recommend": "schedule", "...": "..."},
  "ranking": [ ... ],
  "breadcrumb_emitted": true,
  "outcome_stored": true
}
```

---

## Signal emission (WRE self-improvement testbed)

Every run emits BOTH:
- **Breadcrumb** (WSP 91) via `get_breadcrumb_telemetry().store_breadcrumb(source_dae="youtube_shorts_scheduler", event_type="schedule_priority", ...)` with the full ranking in metadata.
- **PatternMemory SkillOutcome** (WSP 60/48) via `PatternMemory().store_outcome(SkillOutcome(skill_name="what_should_i_schedule", ...))`.

So the WRE learns from each scheduling-priority decision.

---

## Invocation

**SKILLz (WRE / daemon):**
```python
from modules.platform_integration.youtube_shorts_scheduler.skillz.what_should_i_schedule.executor import rank_channels_by_need
ranking = rank_channels_by_need(upcoming_days=7)
next_channel = ranking[0]  # highest need
```

**--agent-command (agent/DAE-invocable, structured JSON):**
```bash
python main.py --agent-command "youtube action schedule_priority upcoming_days=7"
# adapter spawns:
python -m modules.platform_integration.youtube_shorts_scheduler.skillz.what_should_i_schedule.run_skill --upcoming-days 7 --json
```

---

## Malleable seams (intentional)

- **Data source** is injected via `count_fn` (default: `ScheduleTracker.get_count`). A
  future LIVE `Has schedule` DOM verify or engagement-learning signal plugs in here
  WITHOUT touching the ranking math.
- **Need formula** is injected via `deficit_fn` (default: hard-cap deficit). Swap the
  rule (e.g. weight near-term days, fold in engagement) without touching data loading
  or the sort.

---

## Out of scope (separate follow-ups -- NOT built here)

- The live `[CPS-AUDIT]` 'Has schedule' DOM filter-fix (live verification of coverage).
- Mode B re-schedule (mutating) -- this skill is strictly read-only.
- music-vs-talk content gate wiring.

---

## Expected patterns (WSP 95 fidelity)

```json
{
  "skill": "what_should_i_schedule",
  "patterns": {
    "channels_loaded": true,
    "upcoming_window_built": true,
    "deficit_computed": true,
    "ranking_sorted": true,
    "breadcrumb_emitted": true,
    "outcome_stored": true
  }
}
```

---

## Success criteria

- Empty-schedule channel ranks first; cap-full channel ranks last (`sufficient`).
- Deficit math exact: `sum(max(0, cap - count))` over the window.
- Breadcrumb + PatternMemory emitted on every run.
- Pure / configurable: data source + formula swappable.

**WSP Compliance**: WSP 95 (SKILLz Wardrobe), WSP 77 (Agent Coordination),
WSP 91 (Observability), WSP 60/48 (Pattern Memory), WSP 27 (Phase 0 KNOWLEDGE).
