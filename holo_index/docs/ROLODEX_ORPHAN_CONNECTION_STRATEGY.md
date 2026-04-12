# Rolodex Orphan Connection Strategy

**Worker**: CF
**Slice**: `ROLODEX_ORPHAN_CONNECTION_STRATEGY_PHASE1`
**Date**: 2026-04-12
**WSP**: 97 (Truth-First), 15 (Incremental Delivery)
**Prerequisite**: #333 merged — Rolodex counts are now truthful

---

## 1. Current Truth

| Metric | Value |
|--------|-------|
| Total CLI entrypoints | 732 |
| WRE-connected | 29 (4.0%) |
| Orphans | 703 (96.0%) |
| Registered SKILLz.md | 105 |

The 29 connected commands are those with a matching `SKILLz.md` in their directory tree — often but not exclusively wrapper-style files like `executor.py` or `run_skill.py`. The remaining 703 include everything from core infrastructure DAEmons to `__init__.py` files with trivial `if __name__` guards.

**The 96% orphan rate is not a crisis.** Most orphans are not WRE candidates. The meaningful question is: how many _should_ be connected, and what is the cheapest way to connect the ones that matter?

---

## 2. Orphan Categories

Categories below are based on primary classification heuristics (path, trigger type, line count). Counts marked with `~` are estimates — some commands could reasonably belong in multiple categories. The categories are presented as a triage lens, not a partition. Exact classification per-command is deferred to CF2 (the `orphan_class` field).

### Category A: False Positives (57 commands, ~8%)

These should **never** be counted as orphans. They are not CLI entrypoints in any meaningful sense.

| Type | Count | Example |
|------|-------|---------|
| `__init__.py` with `if __name__` guard | 51 | `modules/infrastructure/wre_core/src/__init__.py` |
| `__main__.py` module markers | 2 | `modules/infrastructure/cli/__main__.py` |
| Archived/deprecated | 1 | `modules/gamification/_archived_duplicates_per_wsp3/...` |
| Temp/scratch files | 3 | `holo_index/temp/main_head.py` |

**Action**: Exclude from scanner. These inflate the orphan count without representing real capabilities.

### Category B: DAEmon Processes (49 commands, ~7%)

Long-running autonomous processes with `cadence:continuous` trigger. These are the highest-value WRE candidates because:
- They run unsupervised
- They need monitoring, restart, and health-check integration
- WRE connection gives them observability and lifecycle management

Top candidates by line count:

| Lines | Path | Domain |
|-------|------|--------|
| 2633 | `modules/communication/livechat/src/auto_moderator_dae.py` | communication |
| 1321 | `modules/infrastructure/idle_automation/src/idle_automation_dae.py` | infrastructure |
| 1053 | `modules/platform_integration/x_twitter/src/x_twitter_dae.py` | platform |
| 1023 | `modules/infrastructure/git_push_dae/src/git_push_dae.py` | infrastructure |
| 965 | `modules/ai_intelligence/pqn_alignment/src/pqn_alignment_dae.py` | ai |
| 936 | `modules/infrastructure/dependency_launcher/src/dae_dependencies.py` | infrastructure |
| 782 | `holo_index/dae_cube_organizer/dae_cube_organizer.py` | holoindex |
| 698 | `modules/infrastructure/wsp_framework_dae/src/wsp_framework_dae.py` | infrastructure |
| 673 | `modules/infrastructure/doc_dae/src/doc_dae.py` | infrastructure |
| 659 | `modules/ai_intelligence/social_media_dae/src/social_media_dae.py` | ai |

### Category C: Core Infrastructure (estimated ~80 commands, ~11%)

Substantial CLI tools that are operationally critical but not DAEmons. Examples:
- `wre_master_orchestrator.py` (1814 lines) — the WRE itself
- `agent_db.py` (1542 lines) — database layer
- `pattern_memory.py` (1452 lines) — WRE learning substrate
- `openclaw_voice.py` (1655 lines) — CLI interface
- `action_router.py` (1128 lines) — browser action dispatch

These are candidates for WRE connection but need careful assessment — some are _part of_ WRE infrastructure and wrapping them creates circular dependencies.

### Category D: Platform Automation (estimated ~130 commands, ~18%)

Platform-specific tools (antifaFM, LinkedIn, YouTube, X/Twitter). Many are operationally used and event-triggered. Already the best-connected domain (8.4% rate). Key orphans:
- `antifafm_broadcaster/scripts/launch.py` (2297 lines, has --json)
- `youtube_go_live.py` (1931 lines, has --json)
- `git_linkedin_bridge.py` (1769 lines, has --json)
- `youtube_shorts_scheduler/src/scheduler.py` (1286 lines)

### Category E: Simulator / Economics (28 commands, ~4%)

Economics simulation tools (`modules/foundups/simulator/economics/`). Research and modeling tools, not operational infrastructure. Low WRE value — they produce analysis, not operational outcomes.

### Category F: Developer/Build Tools (estimated ~40 commands, ~6%)

Tools in `modules/development/`, `tools/`, and one-off scripts. Developer utilities, compliance scanners, audit scripts. Some (`modular_audit.py`, `wsp_compliance_guardian.py`) could benefit from periodic WRE scheduling, but most are manual.

### Category G: Small Utilities (<100 lines, 167 commands, ~24%)

Files under 100 lines with `if __name__` guards. Many are simple launchers, config scripts, or module-level smoke tests. Low WRE value individually — connecting them would inflate coverage without adding real autonomous capability.

### Category H: AI/Overseer Components (estimated ~110 commands, ~16%)

AI intelligence modules including the overseer itself (3584 lines), M2M compression sentinel (1557 lines), PQN alignment, digital twin, and video indexer components. Some are high-value WRE candidates (sentinel, PQN DAE), others are research tools.

---

## 3. Connection Criteria

An orphan CLI should be connected to WRE when **all** of these hold:

1. **Operationally reused** — it runs in production or near-production, not just during development
2. **Agent-safe** — it can execute without human intervention in at least some modes
3. **Stable interface** — its CLI flags and output format are settled enough to wrap
4. **Produces observable outcomes** — its success/failure can be measured (exit code, JSON output, log pattern)
5. **Benefits from WRE lifecycle** — scheduling, health monitoring, pattern memory, or fidelity tracking add value
6. **Not WRE-internal** — it is not part of WRE's own execution machinery (avoids circular dependency)

### Priority scoring (for triage)

| Factor | Weight |
|--------|--------|
| Has `--json` flag | +2 (already agent-parseable) |
| Is a DAEmon (continuous) | +3 (highest lifecycle value) |
| >500 lines | +1 (substantial enough to warrant wrapper) |
| Platform-critical path | +2 (FoundUp operations depend on it) |
| Has existing tests | +1 (interface is validated) |

---

## 4. Non-Connection Criteria

An orphan CLI should **remain outside WRE** when any of these hold:

1. **False positive** — `__init__.py`, `__main__.py`, temp files, archived code. Should be excluded from the scanner entirely.
2. **Developer-only tool** — manual audit scripts, one-off migrations, compliance check runners used only by 012/0102 during development sessions
3. **Research/simulation** — economics simulators, projection tools. They produce analysis, not operational outcomes.
4. **WRE-internal component** — `wre_master_orchestrator.py`, `pattern_memory.py`, `wre_skills_loader.py`. Wrapping WRE's own machinery creates circular dependencies.
5. **Unstable interface** — CLI flags still changing, no `--json` output, output format undefined
6. **Trivial** — <50 lines, simple launcher that delegates to another command

---

## 5. Priority Candidates — Top 10 for First Connection Slice

Ranked by connection value (trigger type + line count + JSON support + operational criticality):

| Rank | Path | Lines | JSON | Trigger | Why |
|------|------|-------|------|---------|-----|
| 1 | `antifafm_broadcaster/scripts/launch.py` | 2297 | YES | stream_start | Broadcaster launch — operational critical path |
| 2 | `antifafm_broadcaster/src/youtube_go_live.py` | 1931 | YES | stream_start | Go-live sequence — operational critical path |
| 3 | `livechat/src/auto_moderator_dae.py` | 2633 | NO | continuous | Chat moderation DAEmon — autonomous, needs lifecycle |
| 4 | `git_push_dae/src/git_push_dae.py` | 1023 | NO | continuous | Autonomous git operations — needs health monitoring |
| 5 | `idle_automation/src/idle_automation_dae.py` | 1321 | NO | continuous | Autonomous idle tasks — needs lifecycle management |
| 6 | `linkedin_agent/src/git_linkedin_bridge.py` | 1769 | YES | content_ready | LinkedIn posting pipeline — operational |
| 7 | `x_twitter/src/x_twitter_dae.py` | 1053 | NO | continuous | X/Twitter automation DAEmon — needs lifecycle |
| 8 | `youtube_shorts_scheduler/src/scheduler.py` | 1286 | NO | platform_trigger | Shorts scheduling — operational pipeline |
| 9 | `wsp_framework_dae/src/wsp_framework_dae.py` | 698 | NO | continuous | Framework health DAEmon — infrastructure lifecycle |
| 10 | `doc_dae/src/doc_dae.py` | 673 | NO | continuous | Documentation DAEmon — infrastructure lifecycle |

---

## 6. Recommended Immediate Actions

### Action 1: Exclude False Positives from Scanner

Modify `OrphanCapabilityScanner._find_cli_entrypoints()` to skip `__init__.py` files. This immediately drops the orphan count by ~51 without any SKILLz.md generation.

**Impact**: 703 orphans → ~652 genuine orphans. Connection rate rises from 4.0% to 4.3% truthfully.

### Action 2: Add Classification Field to Rolodex

Add an `orphan_class` field to rolodex entries: `candidate`, `false_positive`, `developer_tool`, `research`, `wre_internal`, `trivial`. This enables filtered queries without faking connection.

**Impact**: WRE discovery can query `orphan_class=candidate` to find what's worth connecting next, without inflating `wre_connected_count`.

---

## 7. Recommended Next Slice

### `CF2 — ROLODEX_FALSE_POSITIVE_EXCLUSION_AND_CLASSIFICATION_PHASE1`

**Scope**:
1. Exclude `__init__.py` files from `OrphanCapabilityScanner._find_cli_entrypoints()`
2. Add `orphan_class` field to rolodex schema (JSON + SQLite)
3. Classify the top ~50 orphans by line count into the categories above
4. Regenerate rolodex with classification
5. Update alignment tests to verify the new field

**Why this before mass SKILLz.md generation**: Classification is cheaper than connection and produces better data for deciding what to connect. Generating SKILLz.md wrappers for 703 commands is waste if 200+ of them shouldn't be wrapped.

**After CF2**: A targeted `CF3 — TOP_10_DAEMON_SKILLZ_GENERATION_PHASE1` slice can generate SKILLz.md wrappers for the 10 priority candidates listed above, with high confidence they belong in WRE.

---

## 8. Long-Term Target

Not all orphans need connection. A healthy steady state might look like:

| Category | Count (est.) | Target State |
|----------|-------------|-------------|
| WRE-connected | 29 → ~60 | Connect top DAEmons + critical platform tools |
| Classified candidates | ~150 | Queued for staged connection |
| Developer/research tools | ~120 | Remain orphaned, classified |
| False positives | ~57 | Excluded from scanner |
| Small utilities | ~170 | Remain orphaned, classified |
| WRE-internal | ~20 | Explicitly excluded |
| Remaining unclassified | ~120 | Gradually classified |

**Target connection rate**: ~8-10% (60/650 genuine CLIs). This is an honest target, not 100%. Most CLIs should remain outside WRE.

---

*Worker CF — strategy complete. Orphan surface classified into 8 categories. Connection and non-connection criteria explicit. Top 10 candidates identified. Next slice: false-positive exclusion + classification field, not mass wrapper generation.*
