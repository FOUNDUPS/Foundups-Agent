# Worker execution prompt — CF3 Top 10 Daemon SKILLz Generation (Phase 1)

**Slice:** `CF3_TOP_10_DAEMON_SKILLZ_GENERATION_PHASE1`  
**Versioned in-repo for 012 / operator handoff.**

---

## Worker Identity Lock

You are acting as `WORKER: CF3` for this slice.

Rules:

1. `WORKER: CF3` is your only lane identity for this task.
2. Do not reinterpret prior lane letters from earlier slices.
3. Do not self-assign a different lane.
4. In your first response, state:  
   `IDENTITY LOCK: Acting as Worker CF3 for CF3_TOP_10_DAEMON_SKILLZ_GENERATION_PHASE1.`
5. In your completion report, begin with:  
   `Worker CF3 complete for CF3_TOP_10_DAEMON_SKILLZ_GENERATION_PHASE1.`

## WSP Lock

Apply `WSP 15` first (Incremental Delivery).  
Then apply `WSP 97` (Truth-First Execution).  
Then act.

---

# CF3_TOP_10_DAEMON_SKILLZ_GENERATION_PHASE1

# Repo: O:\Foundups-Agent  
# Priority: P1

SELF: 0102  
ROLE: worker  
WORKER: CF3

## Mission

Generate SKILLz.md wrappers for the 10 priority daemon candidates identified in the Rolodex Orphan Connection Strategy (Section 5). These are the highest-value WRE candidates because they run unsupervised and need lifecycle management.

Current truth:

- CF2 classification proves these are `candidate` class
- Connecting them raises connection rate from 4.1% to 5.6%
- All 10 are either DAEmons (continuous) or platform-critical operations
- No SKILLz.md currently exists for these entrypoints

## Critical Boundary

Do NOT:

- Modify any daemon source code
- Create mock implementations or stubs
- Run or execute the daemons
- Generate more than 10 SKILLz.md files
- Push `main` without verification
- Mix this work with unrelated slices

## Required Source of Truth

Read and follow exactly:

1. `holo_index/docs/ROLODEX_ORPHAN_CONNECTION_STRATEGY.md` (Section 5: Priority Candidates)
2. `holo_index/skillz/orphan_capability_scanner/SKILLz.md` (format reference)
3. Existing SKILLz.md files in `holo_index/skillz/` (style reference)

## Target Daemons (10)

Generate one SKILLz.md per daemon, placed in the daemon's directory:

### 1. antifafm_broadcaster/scripts/launch.py
- **Path:** `modules/platform_integration/antifafm_broadcaster/scripts/SKILLz.md`
- **Lines:** 2297
- **JSON flag:** YES
- **Trigger:** `stream_start` (event)
- **Domain:** platform

### 2. antifafm_broadcaster/src/youtube_go_live.py
- **Path:** `modules/platform_integration/antifafm_broadcaster/src/youtube_go_live_SKILLz.md`
- **Lines:** 1931
- **JSON flag:** YES
- **Trigger:** `stream_start` (event)
- **Domain:** platform

### 3. livechat/src/auto_moderator_dae.py
- **Path:** `modules/communication/livechat/src/auto_moderator_dae_SKILLz.md`
- **Lines:** 2633
- **JSON flag:** NO
- **Trigger:** `continuous` (cadence)
- **Domain:** communication

### 4. git_push_dae/src/git_push_dae.py
- **Path:** `modules/infrastructure/git_push_dae/src/SKILLz.md`
- **Lines:** 1023
- **JSON flag:** NO
- **Trigger:** `continuous` (cadence)
- **Domain:** infrastructure

### 5. idle_automation/src/idle_automation_dae.py
- **Path:** `modules/infrastructure/idle_automation/src/SKILLz.md`
- **Lines:** 1321
- **JSON flag:** NO
- **Trigger:** `continuous` (cadence)
- **Domain:** infrastructure

### 6. linkedin_agent/src/git_linkedin_bridge.py
- **Path:** `modules/platform_integration/linkedin_agent/src/git_linkedin_bridge_SKILLz.md`
- **Lines:** 1769
- **JSON flag:** YES
- **Trigger:** `content_ready` (event)
- **Domain:** platform

### 7. x_twitter/src/x_twitter_dae.py
- **Path:** `modules/platform_integration/x_twitter/src/SKILLz.md`
- **Lines:** 1053
- **JSON flag:** NO
- **Trigger:** `continuous` (cadence)
- **Domain:** platform

### 8. youtube_shorts_scheduler/src/scheduler.py
- **Path:** `modules/platform_integration/youtube_shorts_scheduler/src/SKILLz.md`
- **Lines:** 1286
- **JSON flag:** NO
- **Trigger:** `platform_trigger` (event)
- **Domain:** platform

### 9. wsp_framework_dae/src/wsp_framework_dae.py
- **Path:** `modules/infrastructure/wsp_framework_dae/src/SKILLz.md`
- **Lines:** 698
- **JSON flag:** NO
- **Trigger:** `continuous` (cadence)
- **Domain:** infrastructure

### 10. doc_dae/src/doc_dae.py
- **Path:** `modules/infrastructure/doc_dae/src/SKILLz.md`
- **Lines:** 673
- **JSON flag:** NO
- **Trigger:** `continuous` (cadence)
- **Domain:** infrastructure

## SKILLz.md Format Requirements

Each generated SKILLz.md MUST include:

### YAML Frontmatter (mandatory fields)

```yaml
---
name: <daemon_name>
description: <one-line description from reading the daemon source>
version: 1.0
author: 0102
created: <today's date>
agents: [qwen]  # or [gemma] for simple pattern matching
primary_agent: qwen
intent_type: <DAEMON|AUTOMATION|PIPELINE>
promotion_state: candidate  # per WSP 97 - truthful state
pattern_fidelity_threshold: 0.90
trigger:
  cadence: <continuous|daily|hourly>  # for DAEmons
  event: <stream_start|content_ready|platform_trigger>  # for event-driven
target_file: <filename.py>  # file-specific binding (CF4 pattern)
category: workflow
evals: []
retirement_date: null
---
```

### Markdown Body (mandatory sections)

```markdown
# <Daemon Name>

**Purpose**: <What this daemon does, from reading the source>

**Problem Solved**: <What operational problem it addresses>

---

## What This Skill Does

<Numbered list of daemon capabilities>

---

## Execution

<Bash command examples for running the daemon>

---

## WRE Connection

- **Trigger**: <cadence or event specification>
- **Agent**: <Qwen or Gemma>
- **JSON Output**: <Yes/No>
- **PatternMemory**: <What patterns it stores>

---

## Autonomy Test

**Question**: Can N compute cycles complete without 012?

**Answer**: <YES/NO with explanation>

---

## Implementation State (WSP 97)

| Field | Value |
|-------|-------|
| promotion_state | candidate |
| pattern_fidelity | <estimated 0.0-1.0> |
| last_execution | never |
| wre_connected | false |

**Note**: This SKILLz.md wrapper was generated to enable WRE connection. The daemon itself exists and is operational.

---

## Related WSPs

- **WSP 77**: Agent Coordination
- **WSP 91**: Observability
- **WSP 103**: CLI Standard (if --json)
- <other relevant WSPs>

---

## Dependencies

<List from reading the daemon source or requirements.txt>

---

*Created: <date> | Author: 0102 | Slice: CF3*
```

## Research Requirements

Before generating each SKILLz.md, you MUST:

1. **Read the daemon source file** to understand:
   - What it actually does (not guessed)
   - Its CLI interface (`argparse` patterns)
   - Whether it has `--json` output
   - What it logs/monitors

2. **Check for existing tests** in the daemon's `tests/` directory

3. **Check the daemon's ModLog.md** if present

4. **Verify the trigger type** matches the daemon's actual behavior:
   - `continuous` = runs in loop/background
   - `event` = triggered by external condition

## Stop Conditions

If daemon source cannot be read:

- Skip that daemon
- Document in completion report
- Continue to next daemon

If daemon has existing SKILLz.md:

- Skip that daemon (already connected)
- Document in completion report
- Continue to next daemon

## Git Guard

Before any push to `main`, you must run:

```powershell
git fetch origin main
git log --oneline origin/main..main
git diff --stat origin/main..main
```

If anything unrelated appears:

- Stop
- Do not push `main`
- Branch/cherry-pick instead

## Required Output

Return exactly one `CF3_SKILLZ_GENERATION_REPORT` with:

### CF3_SKILLZ_GENERATION_REPORT

- Slice: CF3_TOP_10_DAEMON_SKILLZ_GENERATION_PHASE1
- Source doc followed: `holo_index/docs/ROLODEX_ORPHAN_CONNECTION_STRATEGY.md`
- SKILLz.md files created:
  - (list each with path and status)
- SKILLz.md files skipped:
  - (list with reason)
- Daemons researched: (count)
- Total SKILLz.md generated: (count)
- Estimated WRE connection rate change: 4.1% -> X%
- Final result:
  - `CF3_COMPLETE` (all 10 generated)
  - or `CF3_PARTIAL` (some skipped with reasons)
  - or `CF3_BLOCKED` (critical issue)
- Commit hash: (if committed)

## Acceptance

- All 10 daemons researched
- SKILLz.md format matches reference (orphan_capability_scanner/SKILLz.md)
- YAML frontmatter is valid
- promotion_state = candidate (not production)
- No daemon source code was modified
- No blind `main` push occurred

## Suggested Completion Header

`Worker CF3 complete for CF3_TOP_10_DAEMON_SKILLZ_GENERATION_PHASE1.`
