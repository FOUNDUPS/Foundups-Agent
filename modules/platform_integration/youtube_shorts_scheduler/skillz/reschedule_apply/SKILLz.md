---
# Metadata (YAML Frontmatter)
name: reschedule_apply
description: Flag-gated MUTATING apply of the #851 reschedule plan -- move a scheduled short to a target day+peak slot via the Studio visibility-edit popup picker. DEFAULT DRY-RUN (YT_RESCHEDULE_APPLY!="1"): logs would-apply moves, zero mutation. Agent-invoked.
version: 1.0_prototype
author: 0102
created: 2026-06-19
agents: [qwen, gemma]
primary_agent: qwen
intent_type: AUTOMATION
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
    - YT_RESCHEDULE_APPLY: "env gate; must == '1' for real apply (default '0' => dry-run)"
  throttles:
    - name: apply_gate
      max_rate: gated
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
# reschedule_apply

**Purpose**: Flag-gated MUTATING apply of the #851 reschedule PLAN. For each plan
move with a real `video_id`, move a scheduled short from its over-crowded
`from_date` onto the target `to_date` at the peak `slot_local` via the YouTube
Studio visibility-edit popup date/time picker.

**Intent Type**: AUTOMATION (Mode B Phase 2 -- the apply layer for #851's plan).

**Agent**: Qwen drives the apply, Gemma validates the deterministic guards.

**For the agent, never for a human**: the WRE/daemon triggers this SKILLz and the
`--agent-command` surface invokes it programmatically. 012 only observes the
emitted breadcrumb + PatternMemory outcomes and the JSON result. There is NO
manual-012 apply path.

---

## DEFAULT = DRY-RUN (merging mutates NOTHING)

This skill mutates NOTHING by default. Real DOM apply happens ONLY when:

```
YT_RESCHEDULE_APPLY == "1"   (default "0")   AND   a live DOM driver is connected
```

In dry-run (the default), each eligible move is only LOGGED as
`would move <video> <from> -> <to> @ <slot_local>` plus a per-move breadcrumb +
PatternMemory outcome with status `dry_run`. The picker/save DOM helpers are NEVER
called. 012 enables the flag after observing dry-runs and live-validates.

Via the `--agent-command` subprocess surface there is no live browser supplied, so
that surface is dry-run by construction; a live driver is wired through the daemon
path.

---

## Reuse (WSP 84)

- **Plan**: `reschedule_planner.plan_all_channels` / `MovePlan` rows / `NEEDS_LIVE_LIST`
  (#851). Each row is a complete move instruction
  (`channel_id, channel_name, from_date, to_date, slot_et, slot_local, video_id`).
  `slot_local` is the ready-to-type bare 12h Studio time (ET->channel-tz, #847).
- **DOM picker**: `dom_automation.YouTubeStudioDOM.reschedule_open_set_save`, which
  opens the `ytcp-video-visibility-edit-popup` via `open_scheduled_edit_popup`
  (clicking the list row's "Scheduled" `span.label-span`, shadow-pierced via
  `shadow_dom_finder.first_deep`) and then reuses `set_schedule_date`,
  `set_schedule_time`, `click_done`, `click_save` UNCHANGED.
- **Cap**: `HARD_CAP_PER_DAY` (`schedule_tracker.py`, #844).

---

## Safety guards

- `YT_RESCHEDULE_APPLY != "1"` -> dry-run hard (picker/save helpers never called).
- `video_id == "(needs-live-list)"` -> **skipped** (reason `needs_live_list`);
  naming those specific videos needs the live Studio list (out of scope).
- **CAP**: before applying a move, the batch re-counts how many items already target
  `to_date` for the channel. Applying past the cap -> **skipped** (reason `cap`).
- Per-move try/except: one failure -> status `error`, batch continues.

---

## Output (consumed by daemon / Qwen)

```json
{
  "skill": "reschedule_apply",
  "apply_env": "YT_RESCHEDULE_APPLY",
  "apply_enabled": false,
  "dry_run": true,
  "cap": 3,
  "total": 2,
  "applied": 0,
  "dry_run_count": 1,
  "skipped": 1,
  "errors": 0,
  "results": [
    {"video_id":"abc123","from_date":"Jan 5, 2026","to_date":"Jan 2, 2026","slot_local":"8:00 AM","status":"dry_run","reason":""},
    {"video_id":"(needs-live-list)","status":"skipped","reason":"needs_live_list"}
  ],
  "plan_summary": {"days_over_cap": 1, "total_moves": 2, "unplaceable_moves": 0},
  "success": true
}
```

---

## Invocation

**SKILLz (WRE / daemon, default dry-run):**
```python
from modules.platform_integration.youtube_shorts_scheduler.skillz.reschedule_apply.executor import run_skill
result = run_skill()              # dry-run; logs would-apply moves, emits signals
# live apply (012-enabled): set YT_RESCHEDULE_APPLY=1 and pass a connected driver:
# run_skill(dom=youtube_studio_dom)
```

**--agent-command (agent/DAE-invocable, structured JSON, dry-run by construction):**
```bash
python main.py --agent-command "youtube action reschedule_apply"
# adapter spawns:
python -m modules.platform_integration.youtube_shorts_scheduler.skillz.reschedule_apply.run_skill --json
```

---

## Live gap (honest)

The DOM apply path is **mock-tested only** in this slice (no live browser run).
012 enables `YT_RESCHEDULE_APPLY=1`, supplies a connected driver through the daemon,
and live-validates the popup picker against real Studio before trusting apply.

---

## Out of scope (separate follow-ups -- NOT built here)

- The planner itself (done, #851).
- Wiring into the scheduler loop / daemon cadence.
- View-based ("low-viewed first") move selection (needs per-video view data).
- The music-vs-talk content gate; the live filter-fix.
- Naming `(needs-live-list)` videos from the live Studio list.

---

## Success criteria

- Dry-run default: picker/save helpers NOT called; eligible moves logged as `dry_run`.
- `YT_RESCHEDULE_APPLY=1` + driver: picker called with the correct date+time per move.
- A move that would exceed the target-day cap -> `skipped` (reason `cap`).
- `(needs-live-list)` -> `skipped` (reason `needs_live_list`).
- Per-move error -> `error`; batch continues.
- Breadcrumb + PatternMemory emitted per move.

**WSP Compliance**: WSP 95, WSP 77, WSP 91, WSP 60/48, WSP 50 (flag-gated mutation),
WSP 84 (reuse planner + picker + shadow finder + cap).
