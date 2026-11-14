---
# Metadata (YAML Frontmatter)
name: shorts_live_schedule_signal
description: Read-only LIVE shorts-list signals - accurate "Has schedule" scheduled count (fixes the [CPS-AUDIT] false-0) + per-video view count -> low-viewed signal (agent-invoked)
domain: youtube  # WRE auto-fire tag (SkillTriggerMixin domain-discovery, skill_trigger.py:91-115) -> the youtube DAE discovers+fires this every cadence cycle. COST GATE: the live DOM round-trip is costly + contends with the daemon browser, so the executor SELF-GATES on YT_LIVE_SCHEDULE_SIGNAL_ENABLED (default "0"): auto-fires but NO-OPs (no browser, no scrape) until 012 sets it to "1" (SHORTS_SKILLZ_AUTONOMOUS_REGISTRATION_PHASE1)
version: 1.0_prototype
author: 0102
created: 2026-06-19
agents: [gemma, qwen]
primary_agent: gemma
intent_type: KNOWLEDGE
promotion_state: prototype
pattern_fidelity_threshold: 0.90
test_status: needs_live_validation

# Dependencies
dependencies:
  data_stores:
    - name: youtube_studio_shorts_list
      type: dom
      path: "https://studio.youtube.com/channel/{CHANNEL_ID}/videos/short"
  required_context:
    - channel: "Channel key (foundups, antifafm, ...) or UC... id; id resolved from registry"
  code_reuse:
    - name: shadow_dom_finder
      path: modules/infrastructure/foundups_selenium/src/shadow_dom_finder.py
      why: "Studio DOM is shadow-rooted; flat selectors silently fail. Reuse first_deep/find_deep (WSP 84)."
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
# shorts_live_schedule_signal

**Purpose**: Read TWO read-only LIVE signals from the YouTube Studio shorts list so
the scheduling priority is accurate and so 012's "re-schedule low viewed shorts" has a
signal:

1. **Accurate scheduled count** via the Filter chip-bar **"Has schedule"** checkbox
   (the path 012 confirmed reliable) -- this **fixes the false-0 audit bug**.
2. **Per-video view count** parsed from the list -> a **low-viewed** signal.

**Intent Type**: KNOWLEDGE (read/verify before any act).

**Agent**: Gemma (fast deterministic parse) / Qwen (consumes the signal to plan).

**For the agent, never for a human**: the WRE/daemon triggers this SKILLz and the
`--agent-command` surface invokes it programmatically. 012 only observes the emitted
breadcrumb + PatternMemory outcome and the JSON output. There is NO manual-012 menu.

---

## The false-0 bug this fixes

Today `content_page_scheduler.audit_calendar()` (`[CPS-AUDIT]`) does:

```
audit_calendar()
  -> navigate_to_scheduled()                        # content_page_scheduler.py:414
  -> navigate_to_content(visibility="SCHEDULED")    # content_page_scheduler.py:221
  -> _apply_visibility_filter_via_ui("SCHEDULED")   # content_page_scheduler.py:313-412
       # OLD sidebar flow: #filter-icon -> "Visibility" -> "Has schedule" checkbox.
       # This TIMES OUT on the Edge channels (foundups/antifaFM): the filter never
       # lands, the function returns False, and the audit "continues unfiltered".
  -> get_scheduled_videos_detailed()                # dom_automation.py:2466
       # scrapes XPATH_SCHEDULED_ROWS on the (unfiltered) page -> 0 rows
  -> "Total scheduled: 0"                            # content_page_scheduler.py:992
```

So a channel whose tracker holds **131 / 55** scheduled shorts reports **0**. The
reliable path 012 uses is the **chip-bar "Filter" input -> "Has schedule" checkbox in
the filter dialog**, not the sidebar visibility flow.

**This skill clicks that path with the shadow-piercing finder and, when the filter
cannot be applied, returns `scheduled_count = null` (UNKNOWN) -- NEVER a false 0.**

---

## Grounded DOM (012-confirmed; re-confirm live before graduation)

- **List URL**: `https://studio.youtube.com/channel/{CHANNEL_ID}/videos/short?filter=%5B%5D&sort={date}`
  (channel id from the registry, **never hardcoded**).
- **Filter input**: `ytcp-video-filter#video-filter ytcp-chip-bar#chip-bar input#text-input` (placeholder "Filter").
- **"Has schedule" option**: a `label` with text "Has schedule" inside
  `ytcp-filter-dialog tp-yt-paper-dialog#dialog`.
- **Video rows**: `ytcp-video-row` under `ytcp-video-section-content#video-list`;
  visibility cell `span.label-span` text "Scheduled"; the row also has a views column.

Studio is **shadow-rooted**, so these are reached with
`shadow_dom_finder.first_deep / find_deep` (WSP 84 reuse), not flat CSS.

---

## Output (consumed by daemon / Qwen)

```json
{
  "success": true,
  "skill": "shorts_live_schedule_signal",
  "channel": "foundups",
  "channel_id": "UC...",
  "filter_applied": true,
  "scheduled_count": 131,
  "scheduled_count_status": "ok",
  "low_view_threshold": 100,
  "low_viewed_count": 4,
  "low_viewed_videos": [{"video_id": "...", "scheduled": false, "scheduled_date": null, "views": 12}],
  "scheduled_videos": [{"video_id": "...", "scheduled": true, "scheduled_date": "Feb 5, 2026", "views": 0}],
  "videos": [ ... ],
  "row_count": 50,
  "breadcrumb_emitted": true,
  "outcome_stored": true
}
```

**Fail-safe contract**: when the "Has schedule" filter cannot be applied (timeout,
selector miss, no driver), `scheduled_count` is `null` with
`scheduled_count_status` in `{unknown_filter_not_applied, unknown_no_driver}` and
`success` is `false`. It is **never** a false `0`.

---

## Signal emission (WRE self-improvement testbed)

Every run emits BOTH:
- **Breadcrumb** (WSP 91): `event_type="live_schedule_signal"`,
  `source_dae="youtube_shorts_scheduler"`, full counts in metadata.
- **PatternMemory SkillOutcome** (WSP 60/48): `skill_name="shorts_live_schedule_signal"`.

---

## Invocation

**SKILLz (WRE / daemon):**
```python
from modules.platform_integration.youtube_shorts_scheduler.skillz.shorts_live_schedule_signal.executor import read_live_schedule_signal
signal = read_live_schedule_signal(driver, channel_id="UC...")
if signal["scheduled_count"] is None:
    ...  # UNKNOWN -- do NOT treat as 0
```

**--agent-command (agent/DAE-invocable, structured JSON):**
```bash
python main.py --agent-command "youtube action live_schedule_signal channel=foundups"
# adapter spawns:
python -m modules.platform_integration.youtube_shorts_scheduler.skillz.shorts_live_schedule_signal.run_skill --channel foundups --connect edge --json
```

---

## Malleable seams (intentional)

- **Parsing** is behind pure functions (`parse_view_count`, `parse_row_signal`,
  `summarize_rows`) -- swap the parser without touching scrape/orchestration.
- **The DOM scrape** is injected via `scrape_fn` (default: `scrape_live_rows`); the
  **"Has schedule" applier** is injected via `apply_filter_fn`. Tests inject a
  mock-DOM scrape; live runs use the real shadow-pierced ones. The math is identical.

---

## Out of scope (separate follow-ups -- NOT built here)

- Mode B re-schedule / apply (mutating) -- this skill is strictly read-only.
- Wiring this signal into the scheduler ordering / `what_should_i_schedule` ranking.
- music-vs-talk content gate.

---

## Auto-fire self-gate (cost control)

This skill now carries `domain: youtube`, so the youtube DAE's WRE trigger discovers
and fires it every cadence cycle WITHOUT manual invocation. But the live signal is a
DOM round-trip (browser cost + contention with the daemon's own browser), so firing it
unconditionally every ~10m is wasteful. The executor therefore **self-gates**:

- `run_skill(...)` checks `os.getenv("YT_LIVE_SCHEDULE_SIGNAL_ENABLED", "0")`. When it is
  not `"1"`, it returns a NO-OP result immediately -- it does **NOT** touch the browser,
  does **NOT** apply the filter, does **NOT** scrape the DOM. The no-op result carries
  `skipped=true`, `skip_reason="disabled_by_flag"`, `scheduled_count=null` (UNKNOWN,
  never a false 0), and still emits the breadcrumb/PatternMemory so the WRE records that
  the skill fired-but-skipped.
- When `YT_LIVE_SCHEDULE_SIGNAL_ENABLED=1`, it runs exactly as before (live DOM read).

Net: the skill auto-fires (no orphan), but is **default-off** so 012 enables the live
cost explicitly. `reschedule_plan` / `what_should_i_schedule` have NO such gate -- they
are cheap, offline, read-only and safe to auto-fire every cycle.

---

## Live gap (honest)

The DOM read path is **mock-tested only** (a simulated Studio DOM); no live browser
ran here. **012 live-validates** the real chip-bar / "Has schedule" / views selectors
against the Edge channels before this skill graduates from `prototype`. The selectors
above are 012-grounded but the live structure must be re-confirmed in-code.

---

## Expected patterns (WSP 95 fidelity)

```json
{
  "skill": "shorts_live_schedule_signal",
  "patterns": {
    "has_schedule_filter_attempted": true,
    "has_schedule_filter_applied": true,
    "rows_scraped": true,
    "rows_parsed": true,
    "views_parsed": true
  }
}
```

**WSP Compliance**: WSP 95 (SKILLz Wardrobe), WSP 77 (Agent Coordination),
WSP 91 (Observability), WSP 60/48 (Pattern Memory), WSP 84 (Code Reuse:
shadow_dom_finder), WSP 27 (Phase 0 KNOWLEDGE).
