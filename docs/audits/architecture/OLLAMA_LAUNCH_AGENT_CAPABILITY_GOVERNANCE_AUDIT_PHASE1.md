# Ollama Launch Agent Capability Governance Audit (Phase 1)

**Slice:** OLLAMA_LAUNCH_AGENT_CAPABILITY_GOVERNANCE_AUDIT_PHASE1
**Worker-Lane:** W9 - **Author:** 0102 (WSP_00 zen state, WSP_97 Truth Boundary discipline)
**Type:** READ-ONLY governance audit. No code/config/.mcp.json/source change. No agent launched (only
`ollama launch --help` / `ollama --version` probes). ONE doc.
**Base:** origin/main @ 176da8a13.

---

## 1. Mission and Scope

Determine how `ollama launch` agent choices should be represented in FoundUps-Agent as GOVERNED external
agent capabilities for AI Overseer, OpenClaw, and WRE - i.e. how much the system should *know* about them vs
how much authority it may have to *run* them. Decide a verdict from {CATALOG_ONLY, ALLOW_RECOMMENDATION_ONLY,
ALLOW_SANDBOXED_DRYRUN_LAUNCH, BLOCK_PENDING_SECURITY_GATE}.

---

## 2. Predecessors / Context

- #748 RedDog capture: Nous Hermes v0.15.1 in WSL (~/.hermes) - an external agent runtime.
- #757 Hermes import-path audit: repo-vendored Hermes delegate is import-broken-but-benign; delegation
  gated off (HERMES_DELEGATE_ENABLED default 0).
- The PolicyFlags/HXA security chain (#744-#760): the repo's established disabled-by-default + dry-run +
  blocked-result + destructive-action-guard pattern (hermes_job_executor) is the governance template.
- WSP 96 (MCP Governance + Consensus): the model for governing external execution surfaces.

---

## 3. Q1 - Which `ollama launch` agents are available locally?

`ollama --version` = 0.24.0 (Windows, `C:\Users\user\AppData\Local\Programs\Ollama\ollama.exe`; WSL has no
ollama). `ollama launch --help` exposes **13 integrations**:

`claude` (Claude Code) | `codex-app` (Codex App; aliases codex-desktop/codex-gui) | `hermes` (Hermes Agent) |
`openclaw` (OpenClaw; aliases clawdbot/moltbot) | `opencode` (OpenCode) | `codex` (Codex) | `copilot`
(Copilot CLI) | `droid` (Droid) | `kimi` (Kimi Code CLI) | `pi` (Pi) | `pool` (Pool) | `cline` (Cline) |
`vscode` (VS Code; alias code).

Notable launch flags: `-y/--yes` auto-answers confirmation prompts; `--config` configures without launching;
`-- --sandbox workspace-write` / `-- --sandbox` passes sandbox modes to the integration (e.g. codex). These
are **agent runtimes**, not models: `ollama run qwen` is a model; `ollama launch codex` starts a coding agent
with its own shell/file/git/network/credential authority.

---

## 4. Q2/Q3 - Agent classification + authority

| Agent | Class | FS | Shell | Git | Network | Credentials | Notes |
|-------|-------|----|-------|-----|---------|-------------|-------|
| `claude` (Claude Code) | coding worker | RW | yes | yes | API | model key | this very agent class |
| `codex-app` | coding worker (GUI) | RW | yes | yes | API | model key | desktop app |
| `codex` | coding worker (CLI) | RW | yes | yes | API | model key | `--sandbox workspace-write` available |
| `opencode` | coding worker | RW | yes | yes | API | model key | |
| `copilot` | coding worker | RW | yes | **GitHub** | API+GitHub | GitHub auth | GitHub surface = repo authority |
| `droid` | coding worker | RW | yes | yes | API | model key | `--config` does not auto-launch |
| `kimi` | coding worker | RW | yes | yes | API | model key | |
| `cline` | coding agent (editor) | RW | yes | yes | API | model key | |
| `hermes` | **orchestrator / self-improving** | RW | yes | yes | yes | yes | **highest risk**; the WSL v0.15.1 runtime (#748) |
| `openclaw` | personal AI / skills runtime | RW | yes | yes | yes | yes | broad; overlaps our own OpenClaw |
| `pool` | agent pool / multi-agent | RW | yes | yes | yes | yes | orchestration surface |
| `pi` | minimal plugin agent | partial | maybe | no | API | model key | smallest surface |
| `vscode` | editor launch | RW (via editor) | via editor | via editor | - | - | launches the IDE, not an autonomous agent |

**Every coding agent has filesystem-write + shell + git + network + credential authority.** Orchestrators
(`hermes`, `openclaw`, `pool`) are self-directed multi-step and the highest risk. These sit at the same
authority tier as **Hermes delegation / OpenClaw execution**, NOT at the `ollama run <model>` tier.

---

## 5. Repo governance surface (re-verified on current main)

### Q4/Q5 - AI Overseer launch authority: it ALREADY has live shell execution (CORRECTION)

A first-pass map suggested AI Overseer is "observe/recommend/route only." **That is FALSE - re-verified
against source:** AI Overseer has a live, autonomous shell-execution surface:
- `modules/ai_intelligence/ai_overseer/src/auto_fix_engine.py:118-124`: `subprocess.run(fix_command,
  shell=True, capture_output=True, timeout=30)` where `fix_command = bug["config"].get("fix_command")` -
  a shell command sourced from skill config, run autonomously on an auto-fix trigger (complexity 1-2 bugs;
  e.g. OAuth reauth). No per-invocation 012 gate at the call site.
- `modules/ai_intelligence/ai_overseer/src/ai_overseer.py:2659-2665`: the same `subprocess.run(fix_command,
  shell=True, ...)` pattern; plus other `subprocess.run` at :1842/:1910 (git status, read-ish) and :2228/:2243.

So AI Overseer is NOT a pure decision layer - it **already has uncontrolled-ish hands** (autonomous
`shell=True` with a config-sourced command). The ollama-launch question therefore sits ON TOP OF a pre-existing
governance gap, which raises the stakes and is surfaced as a finding (Sec 8).

### Existing governed launch paths (the templates)

| Surface | File | Mechanism | Gates / default |
|---------|------|-----------|-----------------|
| DAE Launch Broker | `modules/infrastructure/dae_daemon/src/dae_launch_broker.py` | **thread-based** (not subprocess); `threading.Thread` :199 | allowlist via `register_launch_spec`, `is_enabled` check, circuit-breaker (3 import failures -> detach) |
| Hermes Job Executor | `modules/infrastructure/wre_core/src/hermes_job_executor.py` | external delegation (gated OFF) | `HERMES_DELEGATE_ENABLED=0` default; `dry_run=True`; destructive-action guard D0-D6; `BLOCKED_*` states. **THE template** for disabled-by-default + dry-run + blocked-result |
| OpenClaw Genesis Gate | `modules/communication/moltbot_bridge/src/openclaw_foundup_orchestrator.py` | FoundUp launch validation (#740 WSP-109) | mandatory genesis-envelope validation; NOT_READY/W10 handoff on fail; 012-bypass gated |
| MCP servers | `.mcp.json` | holo_index, wsp_governance, web_search, chrome-devtools | WSP 96 consensus + Bell-state + supply-chain scan |

### Q4 (catalog precedent) - NONE exists

No repo-owned external-agent capability catalog/registry. WSP 96 Annex A has a "Surface Ownership Table" for
MCP servers (S1/S2/S3) but no equivalent for external AGENT runtimes (claude/codex/hermes/ollama-launch).

### Q6 (sandbox feasibility)

Coding agents could in principle run in a scratch git worktree / container with secrets stripped - the repo
already uses throwaway worktrees and the Hermes `dry_run`/sandbox pattern. But no such governed AgentLauncher
exists today; building one is itself a gated slice.

---

## 6. Q7 - Recommended repo-owned capability catalog shape

A read-only **inventory** (`agent_capability_catalog.json`) - knowledge WITHOUT hands. Proposed shape
(decision-only; not created in this slice):

```json
{
  "schema": "agent_capability_catalog/v1",
  "source": "ollama launch (ollama 0.24.0)",
  "governance_default": "BLOCK_PENDING_SECURITY_GATE",
  "agents": [
    {
      "id": "codex",
      "display_name": "Codex (CLI)",
      "aliases": [],
      "class": "coding_worker",
      "authority": {"filesystem": "rw", "shell": true, "git": true, "network": true, "credentials": "model_key"},
      "default_autonomy": "BLOCKED",
      "ai_overseer_use": "RECOMMEND_ONLY",
      "launch_governance": "BLOCK_PENDING_SECURITY_GATE",
      "required_gates_before_launch": ["explicit_allowlist", "sandbox_or_worktree", "secrets_stripped", "dry_run_first", "logged_evidence", "w10_or_012_approval"],
      "truth_status": "CATALOG_INVENTORY_ONLY",
      "notes": "supports -- --sandbox workspace-write"
    }
  ]
}
```

Per-agent fields: `id/aliases/class/authority/default_autonomy(BLOCKED)/ai_overseer_use(RECOMMEND_ONLY)/
launch_governance/required_gates/truth_status(CATALOG_INVENTORY_ONLY)`. The catalog is **inventory + routing
metadata only** - no launch wiring, no executable binding.

---

## 7. Verdict (tiered)

**Representation:** `CATALOG_ONLY` -> `ALLOW_RECOMMENDATION_ONLY`. **Launch:** `BLOCK_PENDING_SECURITY_GATE`.

- **Add to repo: YES, as `CATALOG_ONLY`** - a repo-owned `agent_capability_catalog.json` (inventory +
  authority classification + governance metadata). Knowledge, not hands.
- **AI Overseer: `ALLOW_RECOMMENDATION_ONLY`** - may read the catalog to recommend/health-check/route-analyze.
  It may NOT launch these agents. (And its EXISTING auto-fix `shell=True` path is a separate concern, Sec 8.)
- **Launch by AI Overseer / WRE / OpenClaw / any non-012 path: `BLOCK_PENDING_SECURITY_GATE`** - no
  `ollama launch <agent>` from any automated path until a governed AgentLauncher adapter exists AND passes a
  security gate. `ALLOW_SANDBOXED_DRYRUN_LAUNCH` is NOT granted now (no such adapter exists).

### Q8 - What stays blocked pending the security gate
- Any automated `ollama launch <agent>` (esp. the `-y/--yes` auto-confirm flag).
- OAuth/login, Docker container start, agent profile creation, messaging/gateway/OAuth wiring.
- Granting AI Overseer (or WRE/OpenClaw) the authority to start an external agent runtime.

### The safe architecture (recommended, deferred to later gated slices)
```
AI Overseer  observes / ranks / recommends (reads catalog)
   -> OpenClaw / WRE  decides task + policy
   -> Governed AgentLauncher adapter (mirrors hermes_job_executor: disabled-by-default, dry-run-first,
      allowlist, destructive-action guard, capability-token scope)
   -> sandbox / worktree / container, secrets stripped
   -> evidence artifact -> W10 gate
```
NOT: `AI Overseer -> ollama launch codex-app` (uncontrolled delegation).

---

## 8. Finding surfaced (pre-existing, beyond this slice's scope)

AI Overseer's auto-fix engine already executes `subprocess.run(fix_command, shell=True, timeout=30)` with a
config-sourced command, autonomously, on an auto-fix trigger (`auto_fix_engine.py:118`, `ai_overseer.py:2659`).
This is a live shell-exec surface that predates the ollama question and is not bounded by an explicit
per-command allowlist or 012 gate at the call site. **Recommended follow-up:** a separate read-only audit
`AI_OVERSEER_AUTOFIX_SHELL_EXEC_GOVERNANCE_AUDIT_PHASE1` to confirm the `fix_command` provenance is
trusted/allowlisted and the auto-fix trigger is appropriately gated. (Not actioned here.)

---

## 9. Recommended Next Slices (decision-only outputs)
1. **W6 `AGENT_CAPABILITY_CATALOG_PHASE1`** (if approved): add the read-only `agent_capability_catalog.json`
   (13 agents, classified) + tests asserting it is inventory-only (no launch wiring; no executable binding;
   AI Overseer may read but not launch). Mirrors the catalog-not-hands principle.
2. **W9 `AI_OVERSEER_AUTOFIX_SHELL_EXEC_GOVERNANCE_AUDIT_PHASE1`** - review the existing shell=True auto-fix path (Sec 8).
3. (Later, gated) **`GOVERNED_AGENT_LAUNCHER_PHASE1`** - the disabled-by-default sandboxed adapter, only after a security gate.

---

## 10. Internal Review Verdict

**READY.** All 8 dispatch questions answered with file:line / `--help` evidence. Q1: 13 agents enumerated.
Q2/Q3: classified - all coding agents have fs/shell/git/network/credential authority; orchestrators
(hermes/openclaw/pool) highest. Q4/Q5: **AI Overseer already has a live autonomous shell-exec path
(correction to the first-pass map)**; no external-agent catalog exists; WSP 96 is the governance template. Q6:
sandboxing is feasible but unbuilt. Q7: catalog shape proposed. Q8: launch stays blocked. Verdict:
CATALOG_ONLY/ALLOW_RECOMMENDATION_ONLY for representation; BLOCK_PENDING_SECURITY_GATE for launch. NO_OVERCLAIM:
no adapter exists, so no sandboxed-launch is endorsed now. Read-only - no agent launched, no source/config/
.mcp.json change.

---

## 11. WSP_97 Truth Boundary Checklist

Declared items: 17 - Rows: 17 - All YES.

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | READ_ONLY_GOVERNANCE_AUDIT | YES | One doc; only `--help`/version probes + file reads |
| 2 | NO_OLLAMA_LAUNCH_EXECUTED | YES | Only `ollama launch --help` / `ollama --version`; no `ollama launch <agent>` |
| 3 | NO_OAUTH_LOGIN | YES | No login/auth performed |
| 4 | NO_DOCKER_START | YES | No container started |
| 5 | NO_AGENT_PROFILE_CREATED | YES | No `--config`/profile created |
| 6 | NO_SECRETS | YES | MCP server names only; no `.env`/key values read |
| 7 | NO_CONFIG_MUTATION | YES | No config changed |
| 8 | NO_MCP_JSON_EDIT | YES | `.mcp.json` read-only (names only) |
| 9 | NO_SOURCE_CHANGE | YES | No `.py` modified |
| 10 | CITES_748_757 | YES | Sec 2 |
| 11 | AI_OVERSEER_LAUNCH_AUTHORITY_REVERIFIED | YES | Sec 5: live `shell=True` paths at auto_fix_engine.py:118 / ai_overseer.py:2659 (first-pass map corrected) |
| 12 | SUBAGENT_CLAIM_VERIFIED | YES | Explore subagent's "no launch authority" claim independently refuted via src grep |
| 13 | CURRENT_MAIN_VERIFIED | YES | Probes/reads on origin/main @ 176da8a13 |
| 14 | ASCII_CLEAN_AUDIT | YES | Doc is ASCII-only |
| 15 | NO_CABR_READY | YES | Not touched |
| 16 | NO_PAYOUT_READY | YES | Not touched |
| 17 | NO_DAO_ACTIVATION | YES | Not touched |

**WSP 97 Truth Boundary Checklist: 17/17 YES.**

---

*Authored by 0102 (Worker-Lane W9) under WSP_00 zen state and WSP_97 Truth Boundary discipline. Read-only on
origin/main @ 176da8a13. `ollama launch` exposes 13 external agent RUNTIMES (claude/codex/hermes/openclaw/...)
with fs/shell/git/network/credential authority. Verdict: represent them as a repo-owned CATALOG_ONLY inventory
that AI Overseer may use for RECOMMENDATION_ONLY; all automated launch is BLOCK_PENDING_SECURITY_GATE until a
governed, sandboxed, dry-run-first, allowlisted, logged AgentLauncher adapter passes a security gate.
Correction surfaced: AI Overseer already has a live autonomous `shell=True` auto-fix path (separate follow-up).*
