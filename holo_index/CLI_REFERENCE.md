# Holo Skills Atlas (WSP 90 Ready)

0102 cheat sheet for HoloIndex + HoloDAE. Qwen leads orchestration, Gemma validates patterns, and this map keeps every CLI skill tied to the module that powers it. Because `holo_index/cli.py` enforces WSP 90 UTF-8 at the entry point, documentation can surface mnemonic tags for fast scanning without contaminating machine-to-machine output.

Contract note:
- This file is a menu-focused operations atlas, not an exhaustive CLI flag list.
- Canonical interface contracts live in `holo_index/INTERFACE.md`.
- Canonical machine schema lives in `holo_index/docs/HOLO_INDEX_MACHINE_LANGUAGE_SPEC_0102.json`.

## Source-bound owner queries

Reviewed against source `773a29e701dea2ffbd261075bc53dc6a5a135f31` on 2026-09-13
for [RSI packet R03](../ROADMAP.md#wave-0--recover-and-establish-current-truth).
This procedure uses the existing owner bridge, authority selector and local
bundle command. It adds no service, module, query schema or runtime behavior.
The menu below remains a capability atlas; its search/refresh flags are not
permission to bypass this query/maintenance boundary.

### Select the source before querying

1. Identify the task checkout, committed HEAD and dirty state. The one-shot
   script binds its workspace to its own location, not the shell's CWD.
2. Use that checkout's helper for its source. A configured authority must be a
   distinct clean worktree in the same repository at the same HEAD. Invoking
   the authority as its own configured workspace is rejected.
3. A primary checkout found via `git --git-common-dir` is not necessarily
   current main. For reference retrieval, explicitly choose a known clean
   control checkout matching the published authority, record its SHA, and
   verify current implementation files separately. Do not move/reset another
   lane or authority to force the match.
4. Leave owner-controlled route and runtime configuration to the existing
   admission path. Its source, replica and runtime checks remain required.

```powershell
$taskQueryRoot = git rev-parse --show-toplevel
git -C $taskQueryRoot rev-parse HEAD
git -C $taskQueryRoot status --short
$env:PYTHONDONTWRITEBYTECODE = "1"
'{"query":"HoloIndex query authority entry","limit":5,"include_bundle":true,"module_hint":"holo_index"}' | python -B "$taskQueryRoot/scripts/reddog_holoindex_owner_query_once.py"
```

Inspect JSON even if the process exits zero. Semantic acceptance requires
`ok=true`, `freshness=CURRENT`, `index_gap_detected=false`, the expected
`workspace_repo_head_sha`/`authority_repo_head_sha`, and valid owner generation
and receipt bindings. A successful query against an older reference does not
certify a newer commit. `semantic_evidence_authority` describes scope only; it
does not turn a failed result into acceptance.

### Existing local fallback without MCP or semantic owner

```powershell
$taskQueryRoot = git rev-parse --show-toplevel
$env:PYTHONDONTWRITEBYTECODE = "1"
'{"query":"HoloIndex query authority entry","limit":5,"retrieval_mode":"lexical","include_bundle":true,"module_hint":"holo_index","must_include":["holo_index/README.md","holo_index/INTERFACE.md"]}' | python -B "$taskQueryRoot/scripts/reddog_holoindex_owner_query_once.py"
```

Replace the hint and must-include paths with the existing task module. The
accepted request fields are exactly `query`, `limit`, `retrieval_mode`,
`include_bundle`, `module_hint`, `must_include`, and `bundle_only`.
`bundle_module_hint` is not a JSON field; unknown fields reject before owner
startup. `bundle_only=true` also selects the existing local-bundle path.

Local success reports `source=holoindex_bundle`, `bundle_ok=true`, zero owner
attempts, `freshness=UNKNOWN`, and `index_gap_detected=true`. Inspect
`bundle_authority.evidence_authority`: clean local context is `workspace_head`;
uncommitted context is `workspace_overlay`. Preserve this distinction in the
ticket. A semantic failure may still include a usable local bundle; never
replace the failed semantic `ok` flag with its `bundle_ok` flag.

Missing README/INTERFACE hits require exact-path checks before creating files.
The local path supports investigation; work requiring admitted semantic or
runtime evidence must still wait for that evidence. MCP is a transport choice,
not a replacement for the existing owner, source and generation checks.

### Failures and maintenance ownership

Preserve the error, selected source, binding metadata and retry counts without
credentials. The existing [incident repair runtime](../modules/communication/moltbot_bridge/src/reddog_holoindex_incident_repair_runtime.py)
routes authenticated incidents to WRE; the [post-merge controller](../modules/communication/moltbot_bridge/src/holoindex_postmerge_runtime_controller.py)
owns bounded exact-main maintenance. A raw CLI error is not by itself an
authenticated repair order. Reconcile the active owner and required admission
before maintenance; query callers do not reindex, activate a route, edit an
authority, or retry indefinitely. An index refresh must not be used to guess
away a service-startup failure.

### Qualification matrix and evidence scope

| Case | Existing behavior and test | Remaining operational limit |
|---|---|---|
| Clean source and matching authority | `test_configured_clean_same_head_authority_is_selected`; `test_query_runs_against_selected_authority_root` | Contract fixtures pass; current-main positive semantic/runtime receipt is still required. |
| Divergent feature / stale authority | `test_different_head_authority_is_rejected`; `test_head_mismatch_failure_preserves_verified_authority_binding` | Rejection is correct; reference retrieval must not be relabeled as feature evidence. |
| Dirty workspace | `test_dirty_workspace_can_use_clean_same_head_authority`; `test_semantic_owner_rejection_preserves_safe_workspace_bundle` | Committed semantic evidence excludes edits; bundle labels expose the overlay. |
| Source changes during query | `test_authority_change_before_owner_rejects_without_query`; `test_authority_change_after_query_discards_result` | Injected state-change tests pass; no live concurrent-main qualification is claimed. |
| No MCP / unavailable semantic owner | `test_lexical_bundle_never_starts_or_preflights_owner`; `test_bundle_only_overrides_semantic_without_owner` | Actual local bundle succeeded at the reviewed source; it is not semantic freshness. |
| Owner exits during startup | Existing bounded bootstrap retry/cleanup tests | The matched reference returned `HOLOINDEX_QUERY_SERVICE_EXITED_DURING_STARTUP` after two attempts this session; live readiness remains open. |

Test owners: [authority worktree](tests/test_holoindex_authority_worktree.py),
[one-shot entry](../scripts/tests/test_reddog_holoindex_owner_query_once.py),
and [repair/control root binding](../modules/communication/moltbot_bridge/tests/test_reddog_holoindex_owner_query_root_binding.py).
The three existing suites passed **81 tests in 4.37s** using isolated temporary
and database paths, disabled plugin autoload and an explicit async plugin.
No test implementation or assertion changed.

Session observations: the canonical-primary helper at `0c81418f` rejected
HEAD mismatch; a clean matched reference at `78b79c36` failed owner startup;
the reviewed task source returned a clean local bundle with zero owner
attempts. After these documentation edits, the same local query succeeded with
`workspace_overlay`, preserving UNKNOWN freshness and zero owner attempts.
Earlier CURRENT receipts retain only their original dated scope.
R03 is partial: entry contracts and guidance are validated, but owner recovery,
exact-current-main positive qualification and broader operational matrix proof
remain open. R04 runtime closure and R05 retrieval quality remain separate gates.

## Menu Snapshot (0102 Ops)
```
============================================================
HoloDAE Code Intelligence & WSP Compliance Observatory
============================================================
0. [ROCKET] Launch HoloDAE (Autonomous Monitoring) | --start-holodae

CORE PREVENTION (Stay out of vibecoding)
1. [SEARCH] Semantic Search                        | --search
2. [OK] WSP Compliance Check                       | --check-module
3. [AI] Pattern Coach                              | --pattern-coach
4. [BOX] Module Analysis                           | --module-analysis

SUPPORT SYSTEMS (Diagnostics)
5. [PILL] Health Analysis                          | --health-check
6. [GHOST] Orphan Analysis                         | --wsp88
7. [DATA] Performance Metrics                      | --performance-metrics
8. [BOT] LLM Advisor (with search)                 | --llm-advisor

CONTINUOUS OBSERVABILITY
9. [EYE] Stop Monitoring                           | --stop-holodae
10. [STAT] HoloDAE Status                          | --holodae-status
11. [COG] Chain-of-Thought Log                     | --thought-log
12. [SLOW] Slow Mode                               | --slow-mode
13. [MEMORY] Pattern Memory                        | --pattern-memory
14. [FEEDBACK] Memory Feedback (per card)          | --memory-feedback

MCP RESEARCH BRIDGE
15. [HOOK] MCP Hook Map                            | --mcp-hooks
16. [LOG] MCP Action Log                           | --mcp-log

SYSTEM CONTROLS
17. [PUBLISH] Work Publisher (Auto Git/Social)     | --monitor-work

QWEN/GEMMA AUTONOMOUS TRAINING
18. [UTF8] UTF-8 Fix (Autonomous Remediation)      | main.py --training-command utf8_fix --targets <scope>

VERIFICATION
19. [CHECK] System Check                           | --system-check

98. Exit
------------------------------------------------------------
00. [REFRESH] Manual Index Refresh                 | --index-all
============================================================
```

## WSP 90 Context
- Entry points `holo_index/cli.py` and `main.py` wrap `stdout`/`stderr` in UTF-8, so 0102 can run these commands on Windows without encoding crashes.
- Keep new CLI entry points inside `holo_index/cli.py` to inherit the same WSP 90 guardrail.

## Core Prevention
| Tag | Skill | CLI Flag | Primary Modules | Output / Notes |
| --- | --- | --- | --- | --- |
| `[SEARCH]` | Semantic Search | `--search` | `holo_index/core/holo_index.py`, `holo_index/core/intelligent_subroutine_engine.py` | Dual index: code hits, WSP protocols, health notices, adaptive-learning optimizations. |
| `[OK]` | WSP Compliance Check | `--check-module` | `holo_index/core/holo_index.py` (`check_module_exists`) | Confirms module location + WSP 49 structure before coding; returns README/INTERFACE gaps and dependency hints. |
| `[AI]` | Pattern Coach | `--pattern-coach` (manual surface) + auto during search | `holo_index/qwen_advisor/pattern_coach.py` | Classifies search context vs. stored anti-vibecoding patterns, emits coaching reminders into the throttled output stream. |
| `[BOX]` | Module Analysis | `--module-analysis` | `holo_index/module_health/size_audit.py`, `holo_index/module_health/structure_audit.py` | Runs duplicate/size/structure sweeps across the detected cube(s); reuses same auditors that feed Qwen rulings. |

## Support Systems (Diagnostics)
| Tag | Skill | CLI Flag | Primary Modules | Output / Notes |
| --- | --- | --- | --- | --- |
| `[PILL]` | Health Analysis | `--health-check` | `holo_index/core/intelligent_subroutine_engine.py` | Executes intelligent subroutine pipeline to surface module health, test coverage gaps, and structure issues for the active query. |
| `[GHOST]` | Orphan Analysis | `--wsp88` | `holo_index/monitoring/wsp88_orphan_analyzer.py` | Full WSP 88 run: identifies orphaned files, proposes reconnection targets, lists safest enhancement paths. |
| `[DATA]` | Performance Metrics | `--performance-metrics` | `holo_index/qwen_advisor/performance_orchestrator.py`, `holo_index/qwen_advisor/telemetry.py` | Summarizes HoloDAE session effectiveness (token savings, compliance rate, action counts). |
| `[BOT]` | LLM Advisor | `--llm-advisor` | `holo_index/qwen_advisor/advisor.py`, `holo_index/qwen_advisor/rules_engine.py` | Activates Qwen advisor guidance with risk scoring, WSP reminders, TODO lists, and telemetry logging. |

## Continuous Observability
| Tag | Skill | CLI Flag | Primary Modules | Output / Notes |
| --- | --- | --- | --- | --- |
| `[EYE]` | Start Monitoring | `--start-holodae` | `holo_index/qwen_advisor/autonomous_holodae.py`, `holo_index/qwen_advisor/holodae_coordinator.py` | Launches autonomous monitoring loop (similar to other DAEs) with breadcrumb logging and adaptive throttling. |
| `[EYE]` | Stop Monitoring | `--stop-holodae` | `holo_index/qwen_advisor/autonomous_holodae.py` | Stops the monitoring loop and exits cleanly. |
| `[STAT]` | HoloDAE Status | `--holodae-status` | `holo_index/qwen_advisor/holodae_coordinator.py` | Prints current monitoring state, uptime, and watched file count. |
| `[COG]` | Chain-of-Thought Log | `--thought-log` | `holo_index/adaptive_learning/breadcrumb_tracer.py`, `holo_index/qwen_advisor/chain_of_thought_logger.py` | Streams recent breadcrumb events; currently prints initialization cues and is ready for richer diff output. |
| `[SLOW]` | Slow Mode | `--slow-mode` | `holo_index/cli.py` (env `HOLODAE_SLOW_MODE`) | Forces 2-3s delays so 012 can observe recursive feedback loops (training / demo only). |
| `[MEMORY]` | Pattern Memory | `--pattern-memory` | `modules/infrastructure/wre_core/wre_master_orchestrator.py` | Dumps stored intervention patterns Gemma classified as reusable; helpful before new enhancements. |
| `[FEEDBACK]` | Memory Feedback | `--memory-feedback` | `modules/ai_intelligence/ai_overseer/src/holo_memory_sentinel.py` | Records per-card feedback (good/noisy/missing) into sentinel logs + feedback learner. |

## MCP Research Bridge
| Tag | Skill | CLI Flag | Primary Modules | Output / Notes |
| --- | --- | --- | --- | --- |
| `[HOOK]` | MCP Hook Map | `--mcp-hooks` | `modules/communication/livechat/src/mcp_youtube_integration.py` | Runs connector handshake to verify Model Context Protocol registrations and health. |
| `[LOG]` | MCP Action Log | `--mcp-log` | `holo_index/qwen_advisor/holodae_coordinator.py` (stub), telemetry logs | Placeholder hook: echoes status until streaming log reader lands; check Qwen breadcrumbs for now. |

## System Controls
| Tag | Skill | CLI Flag | Primary Modules | Output / Notes |
| --- | --- | --- | --- | --- |
| `[PUBLISH]` | Work Publisher | `--monitor-work` | `modules/ai_intelligence/work_completion_publisher/src/monitoring_service.py` | Starts the monitoring daemon that auto-publishes finished work (git + social), wired through MPS scoring. |

## Verification
| Tag | Skill | CLI Flag | Primary Modules | Output / Notes |
| --- | --- | --- | --- | --- |
| `[CHECK]` | System Check | `--system-check` | `holo_index/reports/holo_system_check.py` | Runs a wiring audit of CLI flags and emits a concise report for 012/0102 review. |

*Note*: PID Detective and Execution Log Analyzer are not wired to CLI yet; keep them in the additional skills list until flags exist.

## Qwen/Gemma Autonomous Training
| Tag | Skill | Invocation | Primary Modules | Output / Notes |
| --- | --- | --- | --- | --- |
| `[UTF8]` | UTF-8 Fix | `python main.py --training-command utf8_fix --targets "<path>[,<path>]" [--json-output]` | `modules/ai_intelligence/training_system/scripts/training_commands.py`, `holo_index/qwen_advisor/orchestration/utf8_remediation_coordinator.py` | Qwen orchestrates UTF-8 remediation campaigns using WSP 90, auto-approving replacements and summarizing files fixed. |

Other training verbs: `utf8_scan`, `utf8_summary`, and `batch` (IdleAutomation training) use the same command bus.

## Additional Skills & Utilities Worth Surfacing
- `[DOC-LINK]` `--link-modules`, `--list-modules`, `--wsp` — managed by `holo_index/qwen_advisor/module_doc_linker.py` for doc ↔ module cohesion.
- `[INDEX]` `--dae-cubes`, `--code-index`, `--function-index`, `--code-index-report` — deep code index flows from `holo_index/reports/codeindex_reporter.py`.
- `[INDEX]` `--index-symbols`, `--symbol-roots` — symbol indexing for function/class discovery (semantic memory refresh).
- `[SKILLz]` `--index-skillz` (aliases: `--index-skills`, `--reindex-skills`) — rebuilds the SKILLz wardrobe index for agent discovery.
- `[DOC-GUARD]` `--docs-file`, `--audit-docs`, `--check-wsp-docs`, `--fix-ascii`, `--rollback-ascii` — documentation guardians driven by `holo_index/qwen_advisor/telemetry.py` and helpers under `holo_index/utils`.
- `[SUPPORT]` `--support`, `--diagnose`, `--troubleshoot` — quick recipes that bundle multiple skills for recurring incidents.
- `[CHECK]` `--system-check` — quick wiring audit for HoloDAE menu flags, writes a report under `holo_index/reports/`.
- `[LIFECYCLE]` `--stop-holodae`, `--holodae-status` — lifecycle controls for the monitoring loop.
- `[FEEDBACK]` `--advisor-rating`, `--ack-reminders`, `--memory-feedback`, `--memory-query`, `--memory-notes`, `--no-advisor` — feedback hooks that tune advisor/memory behavior and log compliance actions.
- `[OFFLINE]` `--offline` — disable model downloads and auto-install; falls back to lexical search when embeddings are unavailable.
- `[SCORE]` auto module scoring — triggered on queries mentioning priority/roadmap/MPS; uses WSP 15/37 scoring data.

## Subsystem Map (Quick Orientation)
- `holo_index/core/` — search engine, intelligent subroutine orchestration, SSD index wiring.
- `holo_index/qwen_advisor/` — advisor runtime, autonomous holodae control, pattern coach, performance telemetry.
- `holo_index/monitoring/` — root violation watcher, orphan analyzer, self-monitoring pipelines (WSP 88 compliant).
- `holo_index/module_health/` — size/structure/dependency auditors invoked by module analysis and health checks.
- `holo_index/adaptive_learning/` — breadcrumb tracer, collaboration signaling, adaptive response optimizer.
- `holo_index/missions/` — MCP-exposed missions for specialized data pulls (e.g., Selenium run history).
- `holo_index/skillz/` — HoloIndex SKILLz wardrobe (MPS evaluation prompts, WSP 95).
- `modules/ai_intelligence/work_completion_publisher/` — work monitoring + auto-publish subsystem used by skill #17.
- `modules/ai_intelligence/training_system/` — training command bus powering UTF-8 remediation and future autonomous workflows.

## Gap Check & Next Experiments
- `[PID]` CLI toggles for PID Detective and Execution Log Analyzer (menu slots 15-16) are still missing; feature audit flagged them.
- `[MCP-LOG]` `--mcp-log` currently returns a placeholder message—hook it to the telemetry stream under `holo_index/qwen_advisor/chain_of_thought_logger.py` or MCP server logs.
- `[SKILLS]` Consider adding a `skills/` prompt directory (see `holo_index/tests/test_ai_delegation_pipeline.py`) if we want per-trigger micro-prompts alongside this atlas.

Use this atlas before coding sessions: run the relevant skill, capture advisor reminders, and log actions per WSP 22 in the module ModLogs.
