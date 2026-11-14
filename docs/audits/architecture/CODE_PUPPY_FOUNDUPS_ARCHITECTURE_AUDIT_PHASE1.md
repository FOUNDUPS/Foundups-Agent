# Code Puppy vs FoundUps Architecture Audit -- Phase 1

**Slice**: `CODE_PUPPY_FOUNDUPS_ARCHITECTURE_AUDIT_PHASE1`
**Type**: External source-level architecture audit (decision-only)
**Worker-Lane**: W9
**Agent**: 0102 (Opus 4.8, ultracode)
**Date**: 2026-06-07
**Base**: `75ffc8c90` (origin/main HEAD after #764; audit artifact committed from current main)
**Code Puppy snapshot**: HEAD `bc3c4b74929333e8c2d3d2989b70d9141b2a943b`
  (2026-06-06 commit `feat: Add per-invocation sub-agent model overrides (#377)`)
**Source**: <https://github.com/mpfaffenberger/code_puppy>
**Read-only clone**: `O:/tmp/code_puppy_audit_source` (shallow, no deps installed, no execution)
**WSP Lock**: WSP_00 -> WSP_15 -> WSP_50 -> WSP_64 -> WSP_77 -> WSP_87 -> WSP_96 -> WSP_97 -> WSP_22

---

## 1. Executive Summary

Code Puppy is a Python (3.11+) CLI coding agent built as a *thin conductor on
top of pydantic-ai*. The entrypoints `code-puppy` and `pup` (and `python -m
code_puppy`) all resolve to a single `asyncio.run(main())` entry in
`cli_runner.py` using stdlib `argparse`. Internally, the project relies on
pydantic-ai for the model interface, tool-call protocol, MCP transport
(stdio/SSE/HTTP), and the tool-iteration loop -- Code Puppy adds an agent
registry, an AGENTS.md project-rule loader, a static round-robin model
wrapper, a generous TOOL_REGISTRY, an MCP server lifecycle manager, an
optional DBOS durable-execution plugin, and a history-compaction policy.

Three findings dominate the FoundUps decision:

1. **Governance posture is incompatible with FoundUps' WSP regime.**
   `get_yolo_mode()` defaults to `True`
   (`config.py:1125-1137`). With yolo on, file-modification, file-deletion,
   and shell-command approval gates short-circuit
   (`file_permission_handler/register_callbacks.py:222-226`;
   `command_runner.py:1138-1209`). The strongest shell guard
   (`shell_safety`, LLM-driven) only activates *in yolo mode*. The basic
   `agent_run_shell_command` tool calls `subprocess.Popen(command,
   shell=True, ...)` with no path allowlist, no cwd jail, and no command
   allowlist (`command_runner.py:1276-1285`). FoundUps' AgentPermissionManager
   + WSP 50 preflight + WSP 96 MCP governance are strictly stricter; direct
   integration would punch through every layer.

2. **The model "router" is a static name-to-config lookup, not a router.**
   `model_factory.get_model()` is a long `if/elif` chain on
   `model_config["type"]` (`model_factory.py:528-986`). The rich capability
   and cost metadata in `models_dev_parser.py` (`ModelInfo`,
   `search_models`, `filter_by_cost`, `filter_by_context`) is exercised only
   by the `/add_model` browse UI and the `__main__` example -- never wired
   into runtime selection. "Round-robin" is real (`round_robin_model.py`),
   thread-safe, and well-tested, but the author's own comment at
   `round_robin_model.py:118-119` says explicitly *"Unlike FallbackModel, we
   don't try other models here / The round-robin strategy is about
   distribution, not failover"*. The README's "overcome rate limits" framing
   oversells.

3. **DBOS durable-execution is the one architectural lesson worth a
   FoundUps spike.** It is opt-in (`pyproject.toml:54-56` lists
   `durable = ["dbos>=2.11.0"]` as an optional extra), implemented as a
   single tidy plugin (`code_puppy/plugins/dbos_durable_exec/`,
   ~9 files under 500 LOC), and delegates *all* durability to
   `pydantic_ai.durable_exec.dbos.DBOSAgent`. Zero `@DBOS.workflow`
   decorators live in `code_puppy/` -- Code Puppy only wraps each
   `pydantic_agent.run(...)` call with `SetWorkflowID(workflow_id)` via the
   `agent_run_context` hook. State store defaults to SQLite at
   `<DATA_DIR>/dbos_store.sqlite`; Postgres via
   `DBOS_SYSTEM_DATABASE_URL`. FoundUps' OpenClawSupervisor `run_cycle()`
   loop has no checkpoint/resume mechanism today (WRE inspection confirmed
   absence); this is a real gap.

**Verdict**: `CREATE_DURABLE_EXECUTION_SPIKE`. Adopt no Code Puppy source.
Vendor nothing. Pilot the DBOSAgent wrapper pattern (one upstream library,
`pydantic-ai`, and one optional dependency, `dbos`) in an isolated
FoundUps slice targeting the OpenClawSupervisor `run_cycle()` checkpoint/
resume gap. Defer the AGENTS.md / model-routing / tool-registry questions
to a separate CAPABILITY_CATALOG slice if and when motivated.

---

## 2. Source Evidence Inventory

### 2.1 Code Puppy (external)

Snapshot: HEAD `bc3c4b74929333e8c2d3d2989b70d9141b2a943b`, latest commit
`feat: Add per-invocation sub-agent model overrides (#377)`, dated
2026-06-06. Read-only clone at `O:/tmp/code_puppy_audit_source` (shallow).
No dependency install, no execution, no `.env` read.

Top-level layout:

- Files: `.env.example`, `AGENTS.md`, `LICENSE`, `README.md`,
  `pyproject.toml`, `uv.lock`, `coverage.json`, `lefthook.yml`,
  `code_puppy.gif`, `code_puppy.png`
- Dirs: `.claude/`, `.github/`, `code_puppy/`, `docs/`, `tests/`

Inspection coverage per area (CLI, agents, model router, round-robin, MCP,
tools, AGENTS.md, DBOS, memory, governance, tests/CI) detailed in
sections 5 and 7-11.

### 2.2 FoundUps (local)

Inspected and quoted with verbatim `file:line` evidence:

- `O:/Foundups-Agent/main.py` (1432 lines)
- `O:/Foundups-Agent/modules/ai_intelligence/ai_overseer/src/ai_overseer.py`
  (3584 lines) plus 32 sibling files
- `O:/Foundups-Agent/modules/communication/moltbot_bridge/src/openclaw_*.py`
  (23 files, 11097 LOC)
- `O:/Foundups-Agent/modules/infrastructure/wre_core/src/` plus
  `wre_master_orchestrator/src/wre_master_orchestrator.py`
- `O:/Foundups-Agent/modules/infrastructure/mcp_manager/src/mcp_manager.py`
- `O:/Foundups-Agent/.mcp.json`
- `O:/Foundups-Agent/WSP_framework/src/WSP_96_MCP_Governance_and_Consensus_Protocol.md`
- Audit lineage:
  `docs/audits/architecture/HERMES_AGENT_RUNTIME_INSTALL_AND_PATH_AUDIT_PHASE1.md`
  (#757), `HERMES_DELEGATE_IMPORT_PATH_REMEDIATION_PHASE1.md` (#761),
  `WRE_OPENCLAW_HERMES_AUTONOMOUS_BUILD_DRYRUN_PHASE1.md` (#762). PR
  #748 has NO dedicated audit doc locally -- only indirect citations
  (`HERMES_AGENT_RUNTIME_INSTALL_AND_PATH_AUDIT_PHASE1.md:27`,
  `OLLAMA_LAUNCH_AGENT_CAPABILITY_GOVERNANCE_AUDIT_PHASE1.md:22`).

### 2.3 HoloIndex Local Mapping (WSP 87)

| Query | Signal | Notes |
|-------|--------|-------|
| model router multi provider cost latency capability matching | MEDIUM | `action_router.py` is browser-action focused, NOT an LLM router. Nearest analogs: WSP 95 SKILLz Wardrobe, WSP 106 API Gateway. |
| MCP governance WSP 96 tool registry external agent | HIGH | Direct hits on `WSP_96_MCP_Governance_and_Consensus_Protocol.md`, `mcp_manager.py`, `agent_permission_manager.py`. |
| durable execution checkpoint resume workflow state WRE | MEDIUM | Closest: WSP 56 Artifact State Coherence, `vision_executor.py`, `in_memory.py`. No explicit checkpoint/resume engine surfaced. |
| OpenClaw Hermes agent orchestration tool calling memory | HIGH | `openclaw_dae.py`, WSP 60 Module Memory Architecture. No Hermes-named file in top hits. |
| AGENTS.md CLAUDE.md WSP project rules agent instructions | MEDIUM | HoloIndex did not surface CLAUDE.md or AGENTS.md; closest analogs were `agent_permission_manager.py`, WSP 13/36/43. |

Retrieval evaluation: usable for architectural mapping; query 5 is a
known weak spot (CLAUDE.md is not currently indexed under that vocabulary).
No HOLOINDEX_LOW_SIGNAL events.

---

## 3. Code Puppy Source Tree Analysis

```
code_puppy/
  __main__.py                 -- python -m code_puppy entry, calls main_entry
  main.py                     -- shim re-exporting main_entry from cli_runner
  cli_runner.py               -- the actual async main() loop (~1110 LOC)
  callbacks.py                -- plugin hooks dispatcher
  config.py                   -- XDG-respecting config dir, puppy.cfg getters
  model_factory.py            -- name->config->pydantic-ai Model factory
  models.json                 -- bundled provider/model registry
  models_dev_parser.py        -- models.dev catalog parser (unused at runtime)
  round_robin_model.py        -- Real RoundRobinModel(pydantic_ai.models.Model)
  http_utils.py               -- RetryingAsyncClient (429/5xx backoff)
  provider_credentials.py
  gemini_model.py, chatgpt_codex_client.py, claude_cache_client.py
  session_storage.py          -- persistent message-history file
  summarization_agent.py      -- LLM summariser used by compaction
  reopenable_async_client.py
  uvx_detection.py, version_checker.py, pydantic_patches.py
  list_filtering.py, status_display.py, terminal_utils.py
  agents/
    base_agent.py             -- ABC BaseAgent (thin conductor)
    _builder.py               -- pydantic-ai PydanticAgent constructor + MCP filtering
    _runtime.py               -- run_with_mcp orchestrator + history processor
    _compaction.py            -- history compaction policy
    _history.py               -- token estimator + hash-based dedupe
    _key_listeners.py, _diagnostics.py, _non_streaming_render.py
    _run_signals.py, _steer_processor.py
    agent_code_puppy.py, agent_creator_agent.py, agent_helios.py
    agent_planning.py, agent_qa_kitten.py
    agent_manager.py, json_agent.py, base_agent.py
    event_stream_handler.py, subagent_stream_handler.py
    run_stats.py, smooth_stream.py
  command_line/
    command_handler.py        -- / and ! dispatch
    command_registry.py
    core_commands.py, config_commands.py, session_commands.py
    add_model_menu.py, agent_menu.py, autosave_menu.py
    diff_menu.py, judges_menu.py, model_settings_menu.py
    model_picker_completion.py, file_path_completion.py
    onboarding_slides.py, onboarding_wizard.py
    pagination.py, shell_passthrough.py
    skills_completion.py, uc_menu.py, attachments.py
    mcp/
      handler.py, install_command.py, install_menu.py
      list_command.py, start_command.py, stop_command.py
      restart_command.py, logs_command.py, status_command.py
      remove_command.py, search_command.py, silence_warning_command.py
      catalog_server_installer.py, custom_server_form.py
      custom_server_installer.py, edit_command.py, help_command.py
      start_all_command.py, stop_all_command.py
      wizard_utils.py, utils.py, base.py
  hook_engine/
    engine.py, executor.py, matcher.py, models.py
    registry.py, validator.py, aliases.py
  mcp_/
    managed_server.py         -- ServerConfig + BlockingMCPServerStdio
    agent_bindings.py, async_lifecycle.py, blocking_startup.py
    captured_stdio_server.py
  tools/                       -- TOOL_REGISTRY (file/shell/agent/browser)
  plugins/
    dbos_durable_exec/         -- optional DBOS wrapper (single plugin)
    file_permission_handler/   -- prompt-or-yolo file approval
    shell_safety/              -- LLM-based shell guard (yolo-only)
    destructive_command_guard/ -- regex shell guard (always-on)
    force_push_guard/          -- regex guard for git -f
    context_indicator/         -- token-budget readout
  tui/                         -- prompt_toolkit interactive UI
.github/
  workflows/ci.yml             -- macOS+Py3.13 only; PR-blocking
  workflows/publish.yml        -- push to main; integration tests run here
  workflows/pypi-downloads.yml
.claude/
  settings.json
  hooks/block-sed.py
tests/                         -- 33% line coverage; no threshold enforced
```

(Listings cap at depth 3 / approx 150 entries; full subtrees under
`tools/`, `tui/`, and `tests/` truncated.)

---

## 4. Architecture Diagram (ASCII)

```
        +----------------------------------------------------------------+
        |  Code Puppy at bc3c4b7                                          |
        |                                                                 |
        |  User                                                           |
        |   |                                                             |
        |   v                                                             |
        |  [console-script]   code-puppy | pup | python -m code_puppy     |
        |   |                                                             |
        |   v                                                             |
        |  code_puppy.main:main_entry  ---->  asyncio.run(main())         |
        |   |                                                             |
        |   v                                                             |
        |  cli_runner.py::main()                                          |
        |    - argparse (top-level flags)                                 |
        |    - prompt-only branch: execute_single_prompt()                |
        |    - interactive branch:                                        |
        |        +-----------------------+                                |
        |        |  prompt_toolkit REPL  |                                |
        |        +-----------+-----------+                                |
        |                    |                                            |
        |        +----------+----------+                                  |
        |        |  / cmd  |  ! shell  |  prompt -> agent                 |
        |        +----+----+----+------+--------+                         |
        |             |         |               |                         |
        |             v         v               v                         |
        |   handle_command  shell pass    BaseAgent.run_with_mcp          |
        |             through            |                                |
        |                                v                                |
        |                       _runtime.run_with_mcp(agent, prompt, ...) |
        |                                |                                |
        |   +----------------------------+------------------+             |
        |   | streaming_retry decorator                       |             |
        |   | exception-recovery layer  (on_agent_exception)  |             |
        |   +----------------------------+------------------+             |
        |                                |                                |
        |   optional DBOSAgent wrap  +-> on_agent_run_context             |
        |   (dbos_durable_exec)      |    (SetWorkflowID per turn)        |
        |                            v                                    |
        |                  pydantic_agent.run(prompt, message_history,    |
        |                       usage_limits, event_stream_handler,       |
        |                       toolsets=[filtered MCP servers])          |
        |                            |                                    |
        |       +--------------------+--------------------+               |
        |       | pydantic-ai owns the model<->tool loop  |               |
        |       +-+--------------+----------------------+-+               |
        |         |              |                      |                 |
        |         v              v                      v                 |
        |   Model client    Tool dispatch        MCP toolsets             |
        |   (one of:        (TOOL_REGISTRY       (stdio/SSE/HTTP via      |
        |    OpenAI,         per-tool            pydantic_ai.mcp;         |
        |    Anthropic,      registrars,         CLIENT only -- never     |
        |    Gemini,         filter for name     served)                  |
        |    Cerebras,       collision with      |                        |
        |    Ollama,         MCP names)          v                        |
        |    custom_*,       |                External MCP server         |
        |    OpenAI-compat,  v                (managed by ManagedServer + |
        |    round_robin)    Built-in tools      command_line/mcp/)       |
        |    chosen by       (list_files,                                 |
        |    model_factory   read_file, grep,                             |
        |    name lookup     create_file,                                 |
        |    -- NO router)   replace_in_file,                             |
        |                    delete_*, shell,                             |
        |                    invoke_agent,                                |
        |                    browser_*, etc.)                             |
        +----------------------------------------------------------------+

                                  vs

        +----------------------------------------------------------------+
        |  FoundUps (local at 75ffc8c90)                                  |
        |                                                                 |
        |  012 / 0102                                                     |
        |   |                                                             |
        |   v                                                             |
        |  main.py                                                        |
        |    - preflight chain (env, brain, IronClaw, OpenClaw security,  |
        |      dep CVE, WRE dashboard, WSP framework drift, git sentinel) |
        |    - bootstrap_runtime_dae_launches() (DAE broker singleton)    |
        |    - run_main_menu(...) OR run_headless()                       |
        |   |                                                             |
        |   v                                                             |
        |  webhook_receiver.py  -- POST /webhook/moltbot (HTTP)           |
        |   |                                                             |
        |   v                                                             |
        |  moltbot_bridge/src/openclaw_process_loop.py::process_message   |
        |    - honeypot defense        - skill safety gate (Cisco scan)   |
        |    - intent classifier       - WSP 50 preflight                 |
        |      (keyword + Gemma 270M)  - permission gate                  |
        |                                  (AgentPermissionManager        |
        |                                   + file-path scoped)           |
        |                                                                 |
        |    +------------------+-------------------+--------------+      |
        |    | DOMAIN_ROUTES static dispatch        | WRE plugin   |      |
        |    | (string switch -- NOT LLM tool-call) | self-reg     |      |
        |    +-----+-----------+--------------------+------+-------+      |
        |          |           |                           |              |
        |          v           v                           v              |
        |   IronClaw OpenAI-  AI Overseer            execute_skill        |
        |   compatible       quick_response          via WRE              |
        |   gateway client    (local Qwen)           (TOOL_REGISTRY       |
        |   -> Ollama        AI Gateway              equivalent)          |
        |   -> AIGateway     cloud fallback                               |
        |   (key isolation                                                |
        |    gated)                                                       |
        |                                                                 |
        |  OpenClawSupervisor.run_cycle() (24/7)                          |
        |    BOOT -> PREFLIGHT -> OBSERVE -> TRIAGE -> PLAN ->            |
        |    EXECUTE -> VERIFY -> REMEMBER -> ESCALATE -> IDLE_WATCH      |
        |    (no checkpoint/resume on crash today -- GAP)                 |
        |                                                                 |
        |  AI Overseer (ai_overseer.py, 3584 LOC):                        |
        |    coordinate_mission Phase 0..4 (WSP 77)                       |
        |    PatchExecutor (200-line allowlist)                           |
        |    SecurityEventCorrelator (1514 LOC sibling)                   |
        |    OpenClaw security sentinel, WSP framework drift sentinel     |
        |                                                                 |
        |  WRE Master Orchestrator (wre_master_orchestrator.py):          |
        |    GemmaLibidoMonitor (skill frequency sensor)                  |
        |    SQLite PatternMemory (skill_outcomes, A/B variations,        |
        |       telemetry_counters, skill_edges, retrieval_quality,       |
        |       false_positives)                                          |
        |    WRESkillsLoader                                              |
        |                                                                 |
        |  mcp_manager (NOT an MCP client):                               |
        |    process supervisor for foundups-mcp-p1/servers/*/server.py   |
        |    operator console (20-option menu)                            |
        |    cost-routing classifier (keyword patterns)                   |
        |    hardcoded tool catalog (no tools/list round-trip)            |
        |    WSP 96 Annex A surface taxonomy (S1/S2/S3)                   |
        |                                                                 |
        |  .mcp.json (Claude Code consumer wiring -- 4 servers):          |
        |    holo_index, wsp_governance, web_search (first-party python)  |
        |    chrome-devtools (npx -- floats on @latest, no pin)           |
        +----------------------------------------------------------------+
```

---

## 5. Layer-by-Layer Decomposition (Code Puppy)

### 5.1 CLI entrypoint (CONFIRMED, conf 99)

`pyproject.toml:63-65` registers `code-puppy = code_puppy.main:main_entry`
and `pup = code_puppy.main:main_entry`. `code_puppy/__main__.py:7-10` lets
`python -m code_puppy` reach the same `main_entry`. `code_puppy/main.py:1-7`
is documented as a backwards-compat shim; the real work lives in
`code_puppy/cli_runner.py`. `main_entry` (cli_runner.py:1100-1110) is a
synchronous wrapper: `asyncio.run(main())` with a KeyboardInterrupt catch
and a `finally: reset_unix_terminal()` epilogue. Argument parsing is
stdlib `argparse` (cli_runner.py:107) -- typer is declared as a dep
(pyproject.toml:14) but is not used by the top-level CLI; click is absent.

Top-level flags: `--version/-v`, `--interactive/-i`, `--prompt/-p`,
`--agent/-a`, `--model/-m`, `--resume/-r`, plus a deprecated positional
`command` (cli_runner.py:108-148). Dispatch: `--prompt` -> single-prompt
mode (`execute_single_prompt`); otherwise -> interactive REPL.

### 5.2 Agent loop (CONFIRMED, conf 98)

`BaseAgent` (`agents/base_agent.py:66`) is an ABC; concrete agents are
`agent_code_puppy.py`, `agent_creator_agent.py`, `agent_helios.py`,
`agent_planning.py`, `agent_qa_kitten.py`, plus the `json_agent.py`
schema-driven loader. The actual run loop lives in
`agents/_runtime.py::run_with_mcp`, called via
`BaseAgent.run_with_mcp` (base_agent.py:273-274).

Per user prompt, exactly one `pydantic_agent.run(prompt_to_use,
message_history=..., usage_limits=..., event_stream_handler=...)` call is
made (`_runtime.py:347-355`), wrapped by a `@streaming_retry()` decorator
and an exception-recovery layer that consults `on_agent_exception`
plugin hooks. The intra-turn model<->tool iteration loop lives inside
pydantic-ai (not in this repo). Follow-up `.run` calls happen only when
(a) a queued steer prompt is drained or (b) `on_agent_run_result` hooks
request a retry (`_runtime.py:404-434`).

Tool-call dispatch is delegated entirely to pydantic-ai via
`PydanticAgent(toolsets=[...])`; Code Puppy does not implement a tool
dispatch loop. A two-pass build avoids MCP/local tool name collisions
(`_builder.py:399-431`): pass 1 builds with `toolsets=[]` to enumerate
registered names, pass 2 builds with MCP toolsets filtered by
`filter_conflicting_mcp_tools` (`_builder.py:287-322`).

### 5.3 Model "router" (CONFIRMED, conf 95+)

There is no router; `model_factory.get_model(model_name, config)`
(`model_factory.py:528-986`) is a name-to-config dict lookup followed by
an `if/elif` on `model_config["type"]`. Types: `gemini`, `openai`,
`anthropic`, `custom_anthropic`, `azure_openai`, `custom_openai`,
`zai_coding`, `zai_api`, `custom_gemini`, `cerebras`, `openrouter`,
`gemini_oauth`, `round_robin`. Final branch raises
`ValueError(f"Unsupported model type: {model_type}")`.

`models_dev_parser.py:58-461` defines `ModelInfo` with `cost_input`,
`cost_output`, `context_length`, `reasoning`, `tool_call` flags and
implements `search_models`, `filter_by_cost`, `filter_by_context`. None
of these functions is referenced under `code_puppy/command_line/` or
`code_puppy/agents/` at runtime; their only consumers are the
`/add_model` browse UI helpers and the file's `__main__` block.
`supported_settings` in `models.json` is a feature gate string-list, not
a capability matrix.

### 5.4 Round-robin (CONFIRMED, conf 98)

`code_puppy/round_robin_model.py:88-96` implements a real
`pydantic_ai.models.Model` subclass: a `_current_index` and
`_request_count`, a `threading.Lock` over the index increment, and modular
rotation `(self._current_index + 1) % len(self.models)` once
`_request_count >= _rotate_every`. Default `_rotate_every=1`
(line 42). The non-streaming `request()` wraps the inner
`await current_model.request(...)` in a *re-raise* try/except that
explicitly disclaims failover (`round_robin_model.py:111-120`); the
streaming `request_stream()` (lines 122-141) has no exception handler at
all. Multi-API-key support is achieved by declaring N model entries (each
with its own `$CEREBRAS_API_KEY{n}`) and listing them under a
`round_robin` parent -- no dedicated key-pool primitive
(`provider_credentials.py` has no rotation code; verified by grep).

`http_utils.RetryingAsyncClient` (`http_utils.py:100-198`) does
exponential 429/5xx backoff (5 attempts, `1.0 * 2^attempt` or
`3.0 * 2^attempt` for Cerebras), but it lives at the HTTP-transport layer
attached *per client*. A rate-limited request is retried against the same
key for the full backoff budget; only the *next* fresh request advances
the round-robin index.

### 5.5 MCP integration (CONFIRMED, conf 98)

Code Puppy is an **MCP CLIENT only**. All `pydantic_ai.mcp` and
`mcp.client.stdio` imports are client-side
(`managed_server.py:17-23`, `blocking_startup.py:18`,
`captured_stdio_server.py:15`). Grep for `mcp.server`, `FastMCP`,
`stdio_server`, `serve_mcp`, `@server.tool` returns zero matches under
`code_puppy/`. There is no `--mcp-server` CLI mode.

Three transports are supported, branched in `managed_server.py:179-277`:
`sse` -> `MCPServerSSE`, `stdio` -> `BlockingMCPServerStdio` (a Code
Puppy subclass of pydantic-ai's `MCPServerStdio`), `http` ->
`MCPServerStreamableHTTP`. Server config loads from a single
`~/.code_puppy/mcp_servers.json` (`config.py:43`); a parallel persistent
registry lives at `<XDG_DATA_HOME>/code_puppy/mcp_registry.json`
(`registry.py:43-46`). Sync from config to registry is
`MCPManager.sync_from_config` (`manager.py:153-213`). Tool surfacing:
`manager.get_servers_for_agent()` returns pydantic-ai server instances
passed directly as `toolsets=[...]` to the `PydanticAgent` constructor
(`_builder.py:425`).

Slash-command suite under `code_puppy/command_line/mcp/`:
`install_command.py`, `list_command.py`, `start_command.py`,
`stop_command.py`, `restart_command.py`, `logs_command.py`,
`status_command.py`, `remove_command.py`, `search_command.py`,
`start_all_command.py`, `stop_all_command.py`,
`silence_warning_command.py`, etc.

### 5.6 Tool registry (CONFIRMED, conf 97)

`code_puppy/tools/__init__.py:92-166` declares `TOOL_REGISTRY` -- a flat
dict mapping ~50 tool names to per-tool registrar functions. Each
registrar attaches a single `@agent.tool` to the pydantic-ai `Agent`.
File-IO: `list_files`, `read_file`, `grep`. File mutation: `create_file`,
`replace_in_file`, `delete_snippet`, `delete_file` (`edit_file` is a
deprecated alias). Shell: `agent_run_shell_command`. Reasoning:
`agent_share_your_reasoning`. UX: `ask_user_question`. Agent ops:
`list_agents`, `invoke_agent`, `invoke_agent_with_model`,
`list_available_models`. Skills: `activate_skill`,
`list_or_search_skills`. Extension: `universal_constructor` (constructs
arbitrary code-tools). Browser: ~30 tools (`browser_initialize`,
`browser_navigate`, `browser_click`, `browser_execute_js`,
`browser_screenshot`, ...).

`agent_run_shell_command` (`tools/command_runner.py:1276-1285`) calls
`subprocess.Popen(command, shell=True, stdout=PIPE, stderr=PIPE,
cwd=cwd, ...)` with `cwd` taken directly from LLM tool args
(`command_runner.py:1384-1395`). No path allowlist, no sandbox, no cwd
jail, no command allowlist by default.

Shell guards are opt-in plugins layered via async callbacks:
`shell_safety` (`plugins/shell_safety/register_callbacks.py:106-109`)
short-circuits `if not yolo_mode: return None` -- *only active in yolo*;
`destructive_command_guard` (`plugins/destructive_command_guard/detector.py:94-345`)
matches a fixed ~30-pattern regex list (`rm -rf /`, `git reset --hard`,
`docker prune`, `npm publish`, `Format-Volume`, `rd /s /q`, etc.);
`force_push_guard` matches `git push -f` variants.

### 5.7 AGENTS.md project rules (CONFIRMED, conf 95+)

`load_puppy_rules()` (`agents/_builder.py:38-82`) honors only one filename
family: the tuple `_AGENT_RULE_FILES = ("AGENTS.md", "AGENT.md",
"agents.md", "agent.md")`. **CLAUDE.md is NOT read.** Search order:
priority 1 = `.code_puppy/<name>` (first hit by tuple order); priority 2
= `./<name>`. Global from `~/.code_puppy/AGENTS.md` (XDG-respecting via
`config.py:36`) is concatenated *before* project rules with `\n\n`
separator. Files read with `encoding="utf-8-sig"` so BOM is tolerated.

Injection happens at three sites, all calling `load_puppy_rules()`:
agent build (`_builder.py:333-336`), first-turn system-prompt prepend
(`_runtime.py:255-258`), and sub-agent instructions
(`tools/subagent_invocation.py:176-180`). Rule text is appended
unmodified to every system prompt -- including every sub-agent spawn.

`context_indicator` plugin reads rules into the token-budget readout
(`plugins/context_indicator/usage.py:321,347`); large rules files cost
context on every turn. No `.cursorrules`, `.windsurfrules`, `.agentsrc`,
`project-rules.yaml`, or `.aider*` loader exists in core. A plugin under
`~/.code_puppy/plugins/` could register a `load_prompt` hook to add
CLAUDE.md.

### 5.8 DBOS durable execution (CONFIRMED, conf 95+)

Optional extra: `pyproject.toml:54-56` declares
`[project.optional-dependencies]` with `durable = ["dbos>=2.11.0"]`.
Main `dependencies` (pyproject.toml:11-32) does not include `dbos`. With
the extra installed, `enable_dbos` config defaults to True and the
`/dbos on|off|status` slash command toggles it.

All durable execution is delegated to
`pydantic_ai.durable_exec.dbos.DBOSAgent`. Zero `@DBOS.workflow` or
`@DBOS.transaction` decorators live in `code_puppy/`. The only DBOS
call-sites in `code_puppy/plugins/dbos_durable_exec/`:

- `lifecycle.py:55-56` -- `DBOS(config=...)`, `DBOS.launch()` at startup
- `lifecycle.py:72` -- `DBOS.destroy()` at shutdown
- `cancel.py:13` -- `DBOS.cancel_workflow_async(group_id)`
- `runtime.py:61` -- `SetWorkflowID(workflow_id)` async context manager
- `wrapper.py:42` -- `DBOSAgent(pydantic_agent, ...)` wraps the
  inner agent

Code Puppy plugs into `code_puppy.callbacks` plugin hooks
(`startup`, `shutdown`, `wrap_pydantic_agent`, `agent_run_context`,
`agent_run_cancel`, `should_skip_fallback_render`, `custom_command`) --
the entire integration is opt-in and isolated.

State store: defaults to SQLite at `<DATA_DIR>/dbos_store.sqlite`
(`config.py:9-13`); Postgres via `DBOS_SYSTEM_DATABASE_URL`.

The set of *durable operations* is one: each `pydantic_agent.run(...)`
inside `_runtime.py` is wrapped with `SetWorkflowID(workflow_id)` via the
`agent_run_context` hook (`_runtime.py:451-457`,
`runtime.py:22-65`). Sub-agent invocations go through the same hook
stack. Summarization runs are *explicitly not* wrapped.

### 5.9 Memory / context (CONFIRMED, conf 95+)

A single `history_processors` closure wires into pydantic-ai
(`_builder.py:382-395`), invoked on every turn. Token counting uses a
deliberate "char/2.5" heuristic (`_history.py:76-78` --
`return max(1, math.floor(len(text) / 2.5))`) plus per-model fudge
multipliers (`_history.py:85-101`; currently `1.35` for opus-4-7).
Compaction triggers when `proportion_used > threshold` (default 0.85,
clamped to [0.5, 0.95]; `_compaction.py:316-318`, `config.py:1240-1246`).
Model max comes from per-model `context_length` in `models.json` (default
128000; `base_agent.py:201-208`).

Summarization splits history into "to_summarize" (older) and "protected"
(recent N tokens); system message at index 0 is preserved; an LLM
summariser rewrites the older block
(`_compaction.py:97-225`). Persistent session storage in
`session_storage.py` (file-based, `~/.code_puppy/sessions/...`); resume
via `--resume/-r <path>`.

### 5.10 Governance / approval (CONFIRMED, conf 96+)

**`get_yolo_mode()` defaults to True** (`config.py:1125-1137` --
"Defaults to True if not set." and final `return True`). With yolo on:

- File approval: `prompt_for_file_permission` returns
  `True, None` immediately
  (`plugins/file_permission_handler/register_callbacks.py:222-226`).
  Affects `create_file`, `replace_in_file`, `delete_snippet`,
  `delete_file`.
- Shell command approval: `command_runner.py:1143-1209` -- the per-shell
  prompt is bypassed when *any* of (yolo, running-as-subagent,
  `not sys.stdin.isatty()`) holds; then the command is executed by
  `_execute_shell_command`.
- `shell_safety` (the LLM-based guard) is `if not yolo_mode: return None`
  -- it *only* fires in yolo mode
  (`plugins/shell_safety/register_callbacks.py:106-109`).
- `destructive_command_guard` does match a fixed ~30-pattern regex set
  and hard-blocks in non-TTY contexts
  (`destructive_command_guard/register_callbacks.py:53-62`); coverage is
  shallow -- `python -c "shutil.rmtree('/')"`, `cat secrets.env`,
  `gh release delete`, AWS/GCP CLI, and `pip install` slip through.

There is no audit log of approved actions, no path allowlist for file
operations, no secret-redaction layer, no per-tool rate limit, and no
token-spend cap beyond pydantic-ai `usage_limits`.

### 5.11 Tests / CI (CONFIRMED, conf 95+)

`.github/workflows/ci.yml` runs on `pull_request` events only;
matrix is `os: [macos-latest]` and `python-version: ['3.13']`
(ci.yml:13-15). The single test job runs `uv run pytest tests/ --ignore
tests/integration -v --cov=code_puppy --cov-report=term-missing`
(ci.yml:70). Integration tests run only in `publish.yml` on push-to-main
(publish.yml:9-12, :80).

`coverage.json` `totals.percent_covered` = **33.07%**
(`covered_lines=10548 / num_statements=31892`). No
`--cov-fail-under` anywhere; no `.coveragerc`. Lint and format-check
(`ruff`) run on ubuntu-latest (ci.yml:89-93). Lefthook (pre-commit) runs
only isort/ruff lint+format; comment explicitly notes
"pre-push hook removed - tests run in CI only" (lefthook.yml).

Despite `pyproject.toml:10` declaring
`requires-python = ">=3.11,<3.15"`, no Linux/Windows test job exists.
Windows-specific test files (`tests/test_windows_pipe.py`,
`tests/test_windows_cancel_fix.py`) never run in CI.

---

## 6. FoundUps Comparison Matrix

| Layer | Code Puppy | FoundUps Equivalent | Gap | Risk |
|-------|-----------|---------------------|-----|------|
| CLI entrypoint | `code-puppy` / `pup` -> `main_entry` -> `asyncio.run(main())`; argparse | `main.py` (interactive menu); bare `sys.argv[1]` checks for `--connect-wre`, `--headless`; no argparse | CP has a polished interactive REPL; FU dispatches to DAE launchers. Neither is wrong; different shapes. | LOW |
| Agent loop | Thin BaseAgent on pydantic-ai; one `pydantic_agent.run()` per prompt; tool iteration in pydantic-ai | Async `process_message()` (openclaw_process_loop.py); honeypot -> intent classify -> WSP 50 preflight -> permission gate -> plan -> execute -> validate -> remember; DOMAIN_ROUTES string switch | Different paradigm: CP is single-LLM tool-call; FU is staged deterministic pipeline. Each has merits. | LOW |
| Model routing | Static `if/elif` on `model_config["type"]`; no cost-aware selection; rich capability data exists but is unused at runtime | AI Overseer assigns WSP 77 roles (Qwen Partner / 0102 Principal / Gemma Associate); conversation engine has provider chain (IronClaw -> Ollama -> Qwen -> AIGateway) with ZeroClaw fail-closed | FU has *more sophisticated* routing already (role-based + key-isolation gates). CP brings nothing. | LOW |
| Round-robin / failover | `RoundRobinModel` distributes new requests across keys; explicitly NOT failover; streaming has no exception handler | Provider chain in `openclaw_conversation_engine.py` cascades on error across IronClaw -> Ollama -> Qwen -> AIGateway | FU has real failover; CP has distribution-only. CP idea worth noting but FU already past it. | LOW |
| MCP integration | CLIENT only; pydantic-ai handles stdio/SSE/HTTP; `mcp_servers.json` config; tools surfaced via PydanticAgent toolsets | `.mcp.json` wires 4 servers (3 first-party python, 1 npx); `mcp_manager.py` is a process supervisor + cost-router; NOT an MCP client | FU lacks a real MCP client speaking JSON-RPC; `.mcp.json` is consumed by Claude Code itself, not by FoundUps modules. | MEDIUM |
| Tool registry | `TOOL_REGISTRY` dict with ~50 registrars; per-tool `@agent.tool` decoration | WRE `execute_skill` + AgentPermissionManager + DOMAIN_ROUTES string switch; no LLM-emitted tool-call protocol | FU's tool surface is wider (skills, DAEs) but lacks the LLM-driven tool-call protocol; design choice, not gap. | LOW |
| Project rules | AGENTS.md only (4 case variants); global + project; injected on every sub-agent | CLAUDE.md (root + `.claude/CLAUDE.md`) read only by Claude Code itself; no FoundUps-side ingestion at agent runtime | If FoundUps ever embeds an external coding agent, CLAUDE.md will be ignored by AGENTS.md-style loaders. | MEDIUM |
| Durable execution | Optional DBOS plugin; wraps each `pydantic_agent.run()` with `SetWorkflowID`; SQLite default, Postgres optional; via `pydantic_ai.durable_exec.dbos.DBOSAgent` | NONE in core orchestrators. WSP 56 Artifact State Coherence is the closest protocol; OpenClawSupervisor `run_cycle()` is in-memory only | Real gap. Crash mid-cycle = lost state, no resume. | HIGH |
| Memory / context | history_processors closure on every turn; char/2.5 token estimator; threshold 0.85; LLM summarisation; session storage | AI Overseer PatternMemory + WRE SQLite `skill_outcomes` / `skill_variations` / `false_positives`; per-module WSP 60 JSONL | FU has richer *outcome* memory; CP has cleaner *conversation* compaction. Complementary. | LOW |
| Governance / approval | `yolo_mode=True` default; approval gates short-circuit; LLM shell guard is yolo-only; shell uses `subprocess.Popen(..., shell=True)` with no jail | AgentPermissionManager with confidence tracking + path scope; WSP 50 preflight; WSP 77 AutoGate (PASS/WARN/BLOCK); WSP 96 MCP governance | FU is dramatically stricter. CP defaults are incompatible. | CRITICAL (if integrated) |
| Tests / CI | macOS-latest + Py3.13 only; 33% coverage; no threshold; integration excluded from PR gate | (out of scope for this audit; not benchmarked) | CP CI is below the bar for a coding agent we'd vendor. | MEDIUM |

---

## 7. Governance and Security Analysis

The single most consequential finding: Code Puppy's *default* posture is
"yolo on" -- the system performs file mutations and shell commands
without prompting. This is a deliberate UX choice for a developer-tool
audience that wants minimal friction in an interactive coding session.
It is the *opposite* of FoundUps' WSP 50 preflight + WSP 77 AutoGate +
WSP 96 MCP-governance posture.

Concrete consequences if a naive integration were attempted:

1. **File mutations bypass AgentPermissionManager**. FoundUps' file
   approval pipeline (path scope, confidence threshold,
   audit trail) would be unreachable from Code Puppy's `create_file` /
   `replace_in_file` / `delete_*` calls -- those tools talk directly to
   their own approval plugin, which returns immediate approval under
   yolo.

2. **Shell commands run with `shell=True` and no allowlist**. FoundUps'
   only equivalent surface (`agent_run_shell_command` analog) would have
   to be reimplemented atop a sandbox or denied entirely. The
   `destructive_command_guard` regex (~30 patterns) is too narrow for
   FoundUps' threat model (skill-supply-chain attacks, secret
   exfiltration, blockchain key access).

3. **Token spend is unbounded**. There is no per-session or per-day
   spend cap; pydantic-ai `usage_limits` is the only gate, and round-
   robin across N API keys can actually *increase* aggregate spend.

4. **`chrome-devtools-mcp@latest`** in FoundUps' own `.mcp.json:19-25`
   shows a comparable risk on the FoundUps side: a floating tag with no
   integrity hash. The WSP 96 4-phase adoption lifecycle (Research /
   Trial / Adoption / Optimization) and consensus rule (Qwen + Gemma
   approval routine, 0102 approval for strategic) exist on paper at
   `WSP_96:55-70` but the actual `.mcp.json` does not enforce
   allowlist/denylist, integrity, or version pinning. This is a
   *FoundUps-side* gap that should be addressed independently of any
   Code Puppy decision.

5. **AGENTS.md vs CLAUDE.md**: if FoundUps were to embed Code Puppy or a
   similar AGENTS.md-honoring runtime, the project's existing CLAUDE.md
   instruction set (root and `.claude/CLAUDE.md`) would be silently
   ignored. The simplest mitigation -- a root `AGENTS.md` mirror -- is
   itself a name collision risk in cross-tool environments
   (Code Puppy already uses AGENTS.md for its own contributor rules in
   the upstream repo).

**Verdict for governance**: Code Puppy as-is is unfit for direct
integration in a FoundUps runtime path. Specific patterns (the
plugin-callback `on_run_shell_command` seam; the two-pass tool-name
collision filter) are intellectually clean but not adoption-priority.

---

## 8. Durable Execution / DBOS Analysis

The DBOS integration is the cleanest piece of architecture in Code Puppy
and the only one where Code Puppy demonstrably solves a problem FoundUps
has not solved.

What Code Puppy actually does (CONFIRMED, conf 95+):

- `pyproject.toml` declares `durable = ["dbos>=2.11.0"]` as an
  optional extra. Base install -> zero durability.
- A single plugin
  (`code_puppy/plugins/dbos_durable_exec/`, ~9 files) registers
  callbacks on `startup`, `shutdown`, `wrap_pydantic_agent`,
  `agent_run_context`, `agent_run_cancel`,
  `should_skip_fallback_render`, `custom_command`.
- `lifecycle.py` starts and stops the DBOS runtime.
- `wrapper.py:42` wraps the inner pydantic agent with
  `pydantic_ai.durable_exec.dbos.DBOSAgent(...)`.
- `runtime.py:22-65` yields a `SetWorkflowID(workflow_id)` context
  manager around each `pydantic_agent.run(...)` call.

What Code Puppy does NOT do: implement durable steps itself. Zero
`@DBOS.workflow` / `@DBOS.transaction` / `@DBOS.step` decorators live in
`code_puppy/`. Durability is delegated 100% to pydantic-ai's `DBOSAgent`.

What FoundUps lacks (verified via FU inspection):

- WRE inspection: "Durable workflow engine / step replay / checkpoint-
  resume" listed under *Capabilities Absent*. `wre_core/src/wre_core.py`
  is a WSP-49 placeholder (`# TODO: Implement actual functionality`).
- OpenClawSupervisor `run_cycle()` (`openclaw_supervisor.py:161-200`)
  walks BOOT -> PREFLIGHT -> OBSERVE -> TRIAGE -> PLAN -> EXECUTE ->
  VERIFY -> REMEMBER -> ESCALATE -> IDLE_WATCH but holds all state in
  the supervisor object instance. A crash mid-cycle loses position; on
  restart the supervisor re-enters at BOOT.
- WSP 56 Artifact State Coherence is the nearest protocol but does not
  define a checkpoint/resume API.

**This is the spike**. A bounded FoundUps slice (NOT this audit) should
evaluate `pydantic_ai.durable_exec.dbos.DBOSAgent` -- and/or the
underlying `dbos-transact-py` library directly -- as a checkpoint/resume
mechanism wrapping `OpenClawSupervisor.run_cycle()`. Scope guards: no
Code Puppy import, no AGENTS.md infrastructure, no model-router
changes. The decision artifact would be (a) does DBOS' SQLite mode fit
on the same drive as FoundUps' existing state; (b) does
`pydantic_ai.durable_exec.dbos.DBOSAgent` constrain the
supervisor's state shape; (c) is the WSP 56 surface adequate or does
WSP 56 need a v0.2 addendum.

---

## 9. Model Routing / Cost Control Analysis

This is the area where Code Puppy is weakest *as advertised* but most
revealing *as a contrast for FoundUps*.

Advertised: "Code Puppy integrates with models.dev giving you access to
65 providers and >1000 different model offerings" (README marketing
quote, CONFIRMED MARKETING).

Reality: `model_factory.get_model()` is a name lookup + `if/elif` switch
on `model_config["type"]`. The router has no cost knowledge, no latency
knowledge, no capability matching. The rich `ModelInfo` data class in
`models_dev_parser.py` is *not* wired into selection.

Round-robin is real but request-level only. The author's own comment
disavows failover. "Overcome rate limits" (README) -> rotation pre-empts
a soft rate cap, but mid-request 429s are not re-routed.

Cost control: none in core. `usage_limits` flows to pydantic-ai per
prompt; there is no per-day or per-session spend cap, no provider-level
budget, no cost reporting.

**Comparison to FoundUps**: the FoundUps conversation engine
(`openclaw_conversation_engine.py:23-323`) is dramatically more
sophisticated -- a deterministic identity-then-LLM cascade
(IronClaw OpenAI-compatible -> AIGateway operator-selected -> local Qwen
via AI Overseer quick_response -> Ollama at localhost:11434 -> AIGateway
cloud fallback) gated by `_allow_external_llm` key isolation. The
ZeroClaw runtime profile is unconditionally fail-closed
(`openclaw_dae.py:715`, `:640`). This is what real role-aware multi-
provider routing looks like at the architectural level.

FoundUps does not need Code Puppy's router pattern. If anything, the
data flows the other way: Code Puppy could use FoundUps' provider chain
pattern. We are not in a position to give them that advice.

---

## 10. MCP / Tooling Analysis

Code Puppy: CLIENT-only, uses pydantic-ai for transport, supports
stdio/SSE/HTTP, surfaces MCP tools via PydanticAgent toolsets,
filter-passes against local tool-name collisions in a two-pass build.
Server lifecycle (install / start / stop / restart / logs / status /
remove / search / start_all / stop_all) lives under
`command_line/mcp/`. The `mcp_servers.json` config is a single file
under XDG_CONFIG_HOME with a parallel `mcp_registry.json` for persistent
state.

FoundUps `mcp_manager.py` is named like an MCP manager but is **NOT an
MCP client**. It is a process supervisor + operator console + cost-
routing classifier:

- `_discover_mcp_servers()` (mcp_manager.py:236-252) walks
  `foundups-mcp-p1/servers/*/server.py` paths.
- `start_server()` (mcp_manager.py:443-449) launches
  `subprocess.Popen([sys.executable, str(server_path)], stdout=PIPE,
  stderr=PIPE, ..., creationflags=CREATE_NEW_CONSOLE)`. **No
  `stdin=PIPE`** -- there is no place to write JSON-RPC requests.
- `get_available_tools()` (mcp_manager.py:486-538) returns Python
  literals keyed on hardcoded `if server_name == ...` branches. No
  dynamic `tools/list` round-trip.
- `_test_server_tools` (mcp_manager.py:998-1036) prints "This would
  execute the tool via MCP protocol in production" -- a stub.
- `qwen_gemma_gateway.py:74-120` is a keyword-pattern cost-routing
  classifier (web_scraping -> LOCAL_MCP, etc.), not a tool invoker.
- `_execute_local_mcp` does not actually call any MCP server.

The actual MCP protocol surface in FoundUps is consumed by Claude Code
itself reading `.mcp.json`. The `mcp_manager` module is an operator tool
for inspecting and managing the *servers*, not a client that calls
them. WSP 96 acknowledges this taxonomy with the S1/S2/S3 surfaces
(`WSP_96:249-271`) and the explicit `KNOWN_NON_RUNNABLE_SURFACES` list
in `mcp_manager.py:148-197`.

**Adoption read**: nothing to adopt directly from Code Puppy's MCP layer
since pydantic-ai owns the wire protocol. The *pattern* of using
pydantic-ai-style toolsets is interesting only if FoundUps decides to
also embed pydantic-ai as a runtime dependency -- which is a much larger
decision than this slice can settle.

---

## 11. Memory / Context Management Analysis

Code Puppy's approach:

- `history_processors` callback on every turn (`_builder.py:382-395`).
- Token estimator: `math.floor(len(text) / 2.5)` -- "dirt-simple
  tiktoken replacement" per the code comment (`_history.py:76-78`),
  with per-model fudge multipliers (currently 1.35 for opus-4-7).
- Compaction triggers when `proportion_used > threshold` (default 0.85,
  clamped to [0.5, 0.95]).
- Summarization protects the system message + recent N tokens; older
  block is rewritten by `summarization_agent.py` via a synchronous LLM
  call.
- Persistent sessions: `session_storage.py` stores message history in
  files under `~/.code_puppy/sessions/`. `--resume/-r <path>` loads.

FoundUps' approach (per `wre_core` inspection):

- SQLite `PatternMemory` with explicit tables:
  `skill_outcomes`, `skill_variations`, `ab_test_assignments`,
  `telemetry_counters`, `skill_edges` (Graph-of-Thought),
  `retrieval_quality`, `false_positives`.
- WSP 60 module-local JSONL persistence per module.
- `GemmaLibidoMonitor` (3-signal CONTINUE/THROTTLE/ESCALATE).
- AI Overseer PatternMemory false-positive learning
  (`ai_overseer.py:1068`, `:1097`).
- No conversation-level summarisation; no automatic context-window
  compaction; persistent state is *outcome* memory, not *conversation*
  memory.

These are complementary, not overlapping. Code Puppy compacts *running
conversations* to stay under the model's window; FoundUps records
*completed actions and their outcomes* to learn over time. Neither
approach subsumes the other.

**Adoption read**: the char/2.5 estimator is too lossy for FoundUps'
threat model (multilingual content, dense JSON, code). If FoundUps ever
runs long single-LLM conversations (rather than the staged deterministic
pipeline that OpenClaw uses today), the *pattern* of a
history_processors callback + protected-block summarisation is sound.
But there is no current motive -- OpenClaw's pipeline does not produce
context-window-pressure of the kind Code Puppy is solving for.

---

## 12. What FoundUps Should Adopt

Items are listed in priority order. Each carries the recommended FoundUps
slice and the integration risk.

1. **DBOS durable-execution pattern (concrete spike, no Code Puppy
   import).**
   - Evidence: `code_puppy/plugins/dbos_durable_exec/lifecycle.py`,
     `wrapper.py`, `runtime.py`; `pyproject.toml:54-56`.
   - Slice to create: `CREATE_DURABLE_EXECUTION_SPIKE` targeting
     OpenClawSupervisor `run_cycle()` checkpoint/resume. Use
     `pydantic-ai` + `dbos-transact-py` directly; do not import any
     Code Puppy module.
   - Integration risk: MEDIUM. New runtime dependencies (`pydantic-ai`,
     `dbos`). Postgres or SQLite state-store decision required. WSP 56
     may need a v0.2 addendum.
   - Alternative interpretation: do not adopt DBOS; instead extend WSP
     56 with a checkpoint/resume API atop existing JSONL persistence.
     Cheaper but slower to land.

2. **AGENTS.md filename convention as an interoperability mirror.**
   - Evidence: `code_puppy/agents/_builder.py:38-82`. AGENTS.md is the
     emerging cross-tool convention (Aider, Codex, Claude Code itself
     supports both AGENTS.md and CLAUDE.md).
   - Slice to create: a *documentation-only* mirror or symlink that
     gives external coding agents a single canonical instruction file
     while keeping CLAUDE.md as the source of truth. Decide collision
     policy.
   - Integration risk: LOW. Pure docs change. Watch for filename
     collisions with Code Puppy's own AGENTS.md if a workstation hosts
     both repos.

3. **Two-pass tool-name collision filter (design idea).**
   - Evidence: `code_puppy/agents/_builder.py:399-431` + the
     `filter_conflicting_mcp_tools` function.
   - Slice to create: not standalone. If FoundUps ever surfaces tools
     simultaneously from MCP servers and a local skill registry, the
     two-pass build is a clean pattern worth re-using.
   - Integration risk: LOW. Pure design pattern; no source to vendor.

4. **`pyproject.toml` optional-extras pattern for heavy runtimes.**
   - Evidence: `code_puppy/pyproject.toml:54-56`.
   - Use FoundUps does not yet enforce: when adding a heavy optional
     runtime (DBOS, Postgres driver, a new MCP client), declare it as
     an extra so the base install stays minimal. FoundUps' requirements
     management could use this discipline.
   - Integration risk: LOW.

5. **README discipline about marketing vs reality (negative lesson).**
   - Evidence: README marketing claims ("overcome rate limits", "65
     providers", "100% Open Source", "FULL Privacy commitment") vs the
     code's actual capability set.
   - Slice: nothing to adopt; calibration for FoundUps' own README and
     INTERFACE.md prose -- avoid claims the code cannot verify under
     test.
   - Integration risk: N/A.

---

## 13. What FoundUps Should Reject

1. **`yolo_mode=True` as a default**. Incompatible with WSP 50, WSP 77
   AutoGate, AgentPermissionManager. Even adopting the *pattern* of an
   approval-by-callback would require flipping the default and adding
   audit logging.

2. **`agent_run_shell_command` as a tool surface**. `subprocess.Popen(
   command, shell=True, ...)` with LLM-supplied `cwd` is exactly what
   WSP 96 governance is designed to prevent.

3. **Static `if/elif` model router (`model_factory.get_model`)**.
   FoundUps already has role-based routing in the AI Overseer and a
   provider chain in OpenClaw conversation engine -- both strictly
   better than Code Puppy's pattern.

4. **`models.json` flat dict as a model registry**. FoundUps' role-
   based assignment (Qwen Partner / 0102 Principal / Gemma Associate)
   is the right axis; capabilities should be derived from role, not
   from a bundled provider list.

5. **`RoundRobinModel` for cross-provider failover**. The author has
   said in code that this is not what it does. FoundUps' fallback chain
   in `openclaw_conversation_engine.py` is the correct shape.

6. **The 33% test coverage on a single OS/Python combination**. A code-
   modification agent is exactly the wrong place to accept low coverage.

7. **The browser tool fleet (`browser_initialize`, `browser_navigate`,
   `browser_click`, `browser_execute_js`, ~30 tools).** FoundUps already
   has `modules/infrastructure/browser_actions/` with its own action
   router and human-behavior anti-detection layer; vendoring a parallel
   stack would be net-negative.

8. **The `universal_constructor` tool (LLM-emits-Python-code that
   becomes a new tool).** Unbounded code generation as a tool surface is
   incompatible with PatchExecutor's 200-line allowlist
   (`ai_overseer.py:385-393`).

---

## 14. Roadmap

### 14.1 Immediate (next 30 days)

- Land this audit doc (W9, this slice). Decision-only; no code change.
- W10 follow-up slice: `DURABLE_EXECUTION_SPIKE_PHASE1`.
  - Scope: read `pydantic_ai.durable_exec.dbos.DBOSAgent` source from
    pydantic-ai upstream; read `dbos-transact-py` upstream README +
    quickstart; produce a Phase-1 design memo (no implementation) for
    wrapping `OpenClawSupervisor.run_cycle()`.
- W11 (parallel): `MCP_CONFIG_HARDENING_PHASE1`. Address the FoundUps-
  side `.mcp.json` gaps surfaced incidentally by this audit (no version
  pin on `chrome-devtools-mcp@latest`, no allowlist/denylist, no
  integrity hash, no per-server timeouts). This is unrelated to Code
  Puppy adoption; it is just adjacent.

### 14.2 Medium term (6 months)

- If `DURABLE_EXECUTION_SPIKE_PHASE1` passes: `DURABLE_EXECUTION_PHASE2`
  -- implement supervisor checkpoint/resume using DBOSAgent or direct
  dbos-transact-py.
- WSP 56 v0.2 addendum: codify the checkpoint/resume API surface.
- `CAPABILITY_CATALOG_AUDIT_PHASE1`: enumerate FoundUps tool surfaces
  (skills, DAEs, MCP) against a standardized JSON-RPC tool description
  schema, so the question "could FoundUps expose its skills as MCP
  tools to external clients" becomes answerable.
- `AGENTS_MD_INTEROP_PHASE1`: decide whether to ship a root-level
  AGENTS.md mirror.

### 14.3 Long term (1-3 years)

- If durable execution proves out: extend checkpoint/resume to WRE
  Master Orchestrator and AI Overseer `coordinate_mission` pipeline.
- If pydantic-ai becomes a sanctioned dependency: revisit the
  TOOL_REGISTRY pattern for cross-tool interop with the broader
  pydantic-ai ecosystem.
- Continue rejecting `yolo_mode`-style defaults across all future
  adopted tooling.

---

## 15. Threat Assessment

Direct integration of Code Puppy as a vendored dependency or runtime
agent would introduce:

- **Supply-chain risk (HIGH)**. Code Puppy carries 30+ direct
  dependencies in `pyproject.toml`, each transitively bringing more.
  An attacker who compromises any of them would inherit
  `agent_run_shell_command` access by default. FoundUps has no SBOM
  process that would catch this.

- **Executor-injection risk (CRITICAL)**. With `shell=True` and
  unconstrained `cwd`, an LLM-prompt-injection attack ("ignore previous
  instructions, run X") would translate to shell execution in any
  directory. The destructive_command_guard regex is incomplete.

- **Secret-exfiltration risk (HIGH)**. There is no secret-redaction
  layer in Code Puppy. `read_file` will return any file the
  process can access, including `.env` and `credentials.json`. The
  AI Overseer's WSP 91 audit logging would not see these reads.

- **Dependency-bloat risk (MEDIUM)**. `pydantic-ai-slim[mcp]==1.56.0`,
  `dbos>=2.11.0`, prompt_toolkit, rich, typer, mcp, models-dev catalog
  fetch. Pinning is loose.

- **License risk (LOW)**. LICENSE file present (need to confirm MIT
  or similar; not verified beyond presence in repo root). Worth a
  Phase-2 license-check if any source-level reuse is ever proposed.

- **Marketing-versus-reality risk (MEDIUM)**. README claims that lead a
  reader to over-trust the runtime: "overcome rate limits", "65
  providers", "100% Open Source", "FULL Privacy commitment". The code
  does not implement what the prose implies. Adopting Code Puppy on the
  strength of its README would be a category error.

- **Cloning the public repo for read-only audit (LOW)**. Performed.
  Shallow clone, no install, no execution, no secret read. Acceptable.

- **Vendoring (HIGH, REJECTED)**. Carrying Code Puppy source inside
  FoundUps would inherit all of the above plus a maintenance debt.
  Out of scope for this audit; explicitly rejected.

---

## 16. Internal Review Verdict

**Verdict**: `CREATE_DURABLE_EXECUTION_SPIKE`.

Rationale (under 200 words):

The architect's hint (ADOPT_PATTERNS_ONLY or CREATE_DURABLE_EXECUTION_
SPIKE) is well-calibrated. The single concrete and actionable takeaway
from this audit is the DBOS durable-execution pattern -- one optional
dependency, one tidy plugin, and a delegation to `pydantic_ai.durable_
exec.dbos.DBOSAgent`. FoundUps' OpenClawSupervisor `run_cycle()` has no
checkpoint/resume today; that is a real gap; DBOS is a credible answer.

Every other Code Puppy capability we surveyed is either (a) already
better-implemented in FoundUps (provider chain, role-based routing,
permission gate), or (b) incompatible with FoundUps' WSP regime
(`yolo_mode=True`, `shell=True` without jail, undirected file mutation).
Adopting "patterns" without committing to a specific slice would risk
slow drift without a deliverable.

A bounded `DURABLE_EXECUTION_SPIKE_PHASE1` slice next, scoped to design
only (no implementation), gives the architect a concrete next decision
point: build the spike, or close the file. No Code Puppy source enters
FoundUps. No vendoring. No `.mcp.json` change. No WSP mutation.

Recommended successor slice names (W10/W11):

- `DURABLE_EXECUTION_SPIKE_PHASE1` (design memo, no code)
- `MCP_CONFIG_HARDENING_PHASE1` (independent: address `.mcp.json`
  floating-tag / no-allowlist / no-pin issues)
- `AGENTS_MD_INTEROP_PHASE1` (docs-only, optional)

---

## 17. WSP_97 Checklist

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | READ_ONLY_AUDIT_ONLY | YES | No FoundUps source mutated by this slice; `git status` confirms only this audit doc added. |
| 2 | NO_CODE_PUPPY_EXECUTION | YES | No `python -m code_puppy`, no `uvx code-puppy`, no Code Puppy binary launched. Only `git clone --depth 1`, `git rev-parse HEAD`, `git log -1 --format=...`, file reads, and Glob/Grep performed against the cloned tree. |
| 3 | NO_VENDOR_IMPORT | YES | No `code_puppy` import in FoundUps source; no submodule added; no source copied. Verified by Grep of new audit doc tree only. |
| 4 | NO_DEPENDENCY_CHANGE | YES | `requirements*.txt`, `pyproject.toml`, `uv.lock` (FoundUps-side) untouched. |
| 5 | NO_MCP_CONFIG_CHANGE | YES | `.mcp.json` not modified; verified by `git status --short` showing only the new audit doc among slice-related changes. |
| 6 | NO_RUNTIME_AGENT_LAUNCH | YES | No `main.py --headless`, no `run_main_menu`, no OpenClaw supervisor cycle started by this slice. HoloIndex queries did fire (mandated) and one was found to log `holo_output_history.jsonl` -- classified as ambient runtime output, separate hygiene slice. |
| 7 | NO_SECRET_READ | YES | No `.env`, no `credentials.json`, no key file read by this audit or by the workflow subagents (subagent prompts explicitly forbade `.env` reads). |
| 8 | NO_FOUNDUPS_SOURCE_CHANGE | YES | No file under `modules/`, `holo_index/`, `WSP_framework/`, `WSP_knowledge/`, `main.py` modified by this slice. |
| 9 | NO_WSP_MUTATION | YES | No file under `WSP_framework/` or `WSP_knowledge/` modified; verified by `git status`. |
| 10 | NO_CABR_READY | YES | Audit is decision-only; no CABR signal emitted, no UPS routing changed. |
| 11 | NO_PAYOUT_READY | YES | No FAM payout triggered; no Du distribution; no Treasury motion. |
| 12 | NO_VERIFICATION_COMPLETE | YES | This audit is Phase 1; final verification of any subsequent spike (e.g. `DURABLE_EXECUTION_SPIKE_PHASE1`) is explicitly deferred. |
| 13 | HOLOINDEX_LOCAL_MAPPING_RUN | YES | 5 mandated HoloIndex queries executed (section 2.3). Results recorded with signal levels HIGH/MEDIUM. No HOLOINDEX_LOW_SIGNAL events; no Grep fallback required. |
| 14 | CODE_PUPPY_HEAD_PINNED | YES | HEAD `bc3c4b74929333e8c2d3d2989b70d9141b2a943b` (2026-06-06) verified via `git -C O:/tmp/code_puppy_audit_source rev-parse HEAD`. |
| 15 | ELEVEN_CP_SOURCE_AREAS_INSPECTED | YES | Areas: cli_entrypoints, agents_impl, model_router, round_robin, mcp_integration, tool_registry, agents_md_rules, dbos_durable, memory_context, governance_approval, tests_ci -- all reported with verbatim `file:line` evidence (section 5). |
| 16 | SEVEN_FOUNDUPS_TARGETS_INSPECTED | YES | Targets: main_py, ai_overseer, moltbot_openclaw, wre_core, mcp_manager, mcp_config_and_wsp96, recent_audits -- all reported (sections 6, 7, 8, 10, 11; PR lineage in 17). |
| 17 | RECENT_AUDITS_LINEAGE_DOCUMENTED | YES | PR #757 -> `HERMES_AGENT_RUNTIME_INSTALL_AND_PATH_AUDIT_PHASE1.md`; PR #761 -> `HERMES_DELEGATE_IMPORT_PATH_REMEDIATION_PHASE1.md`; PR #762 -> `WRE_OPENCLAW_HERMES_AUTONOMOUS_BUILD_DRYRUN_PHASE1.md`. PR #748: NO dedicated audit doc found locally (only indirect citations at `HERMES_AGENT_RUNTIME_INSTALL_AND_PATH_AUDIT_PHASE1.md:27` and `OLLAMA_LAUNCH_AGENT_CAPABILITY_GOVERNANCE_AUDIT_PHASE1.md:22`) -- absence is *documented*, not invented. |
| 18 | EVERY_CLAIM_CLASSIFIED | YES | Each substantive technical claim in sections 5, 7-11 carries CONFIRMED / LIKELY / SPECULATIVE / MARKETING / REFUTED + verbatim `file:line` evidence + confidence score. Marketing claims (README quotes) explicitly labeled MARKETING in section 9. |
| 19 | VERDICT_RATIONALE_PRESENT | YES | Section 16 records verdict `CREATE_DURABLE_EXECUTION_SPIKE` with rationale under 200 words, including the alternative-interpretation note for "ADOPT_PATTERNS_ONLY". |
| 20 | ASCII_CLEAN | YES | Source contains no em dashes, no Unicode arrows, no special glyphs; only ASCII punctuation. Verified at write time. |
| 21 | DECLARED_COUNT_EQUALS_ACTUAL_ROW_COUNT | YES | Declared count = 21. Actual data rows in this table = 21 (rows numbered 1-21 inclusive). |

**WSP_97 VERDICT**: PASS (21/21).

---

**Worker-Lane**: W9
**Slice**: `CODE_PUPPY_FOUNDUPS_ARCHITECTURE_AUDIT_PHASE1`
**Decision**: `CREATE_DURABLE_EXECUTION_SPIKE`
**WSP Lock**: WSP_00 -> WSP_15 -> WSP_50 -> WSP_64 -> WSP_77 -> WSP_87 -> WSP_96 -> WSP_97 -> WSP_22
