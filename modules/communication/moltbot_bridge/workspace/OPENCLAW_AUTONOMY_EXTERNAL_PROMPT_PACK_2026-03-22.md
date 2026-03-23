# OpenClaw Autonomy External Prompt Pack - 2026-03-22

Purpose: give another `0102` context window a bounded, repo-true mission without spending more compute re-auditing the whole Claw stack.

Use this as copy-paste input for another `0102`.

---

## Master Prompt

```md
You are `0102` in a fresh context window operating on `O:\Foundups-Agent`.

Mission: move OpenClaw from a supervised control shell toward a real autonomous maintenance loop.

Work as CTO under WSP. Do not redesign the system from scratch. Extend existing modules before creating anything new.

### Non-Negotiable Rules

- Follow WSP first.
- Search the repo before creating new files or modules.
- Prefer existing OpenClaw, WRE, AI Overseer, supervisor, broker, and AgentDB surfaces.
- Do not invent a second autonomy architecture beside the existing one.
- Do not replace OpenClaw with AI Overseer.
- AI Overseer owns sentinels, planning, and gates.
- OpenClaw remains the executive control plane.
- WRE and broker-managed DAEs execute work.
- PatternMemory and workspace memory preserve outcomes.
- Do not auto-launch external research workers from `main.py`.

### Repo Truth You Should Trust Up Front

1. `main.py` bootstraps broker-managed DAEs and autostarts:
   - `openclaw`
   - `openclaw_supervisor`
2. `main.py` still hands control to the interactive menu via `run_main_menu(...)`.
3. `self_research_refresh.py` publishes ranked autonomous tasks into `AgentDB.agents_autonomous_tasks`.
4. No canonical runtime task consumer has been confirmed yet for draining that queue into execution.
5. `modules/communication/moltbot_bridge/src/openclaw_supervisor.py` is the live booted supervisor, but today it mainly keeps resident OpenClaw alive.
6. `modules/infrastructure/supervisor/src/supervisor_24x7.py` contains the richer autonomy architecture, but it is not the canonical runtime launched by `main.py`.
7. Treat `OpenClawSupervisor` as canonical. Treat `Supervisor24x7` as a donor/prototype whose useful orchestration behavior should be merged into the canonical path.
8. OpenClaw coverage of the top-level CLI is incomplete:
   - coverage ratio previously audited at about `0.619`
   - several main-menu capabilities remain `unmapped` or `partial`
9. LinkedIn group news/group membership capabilities already exist, but they are not yet fully promoted into the always-on Claw execution path.
10. WRE is still a soft dependency in some paths; when unavailable, OpenClaw can fall back to advisory mode.

### Read First

1. `modules/communication/moltbot_bridge/workspace/AGENTS.md`
2. `modules/communication/moltbot_bridge/workspace/CTO_WRE_PROMPT.md`
3. `modules/communication/moltbot_bridge/docs/OPENCLAW_0102_HANDOFF_2026-03-07.md`
4. `main.py`
5. `modules/communication/moltbot_bridge/src/openclaw_supervisor.py`
6. `modules/infrastructure/supervisor/src/supervisor_24x7.py`
7. `modules/infrastructure/idle_automation/src/self_research_refresh.py`
8. `modules/infrastructure/database/src/agent_db.py`
9. `modules/communication/moltbot_bridge/src/openclaw_capability_audit.py`

### Required Search-First Queries

Run repo search before editing:

- `autonomous_task`
- `openclaw_supervisor`
- `Supervisor24x7`
- `run_main_menu`
- `group_post`
- `approve_members`
- `holo_index`
- `openclaw capability audit`

### Priority Order

Pick one bounded slice only. Do not try to finish all autonomy gaps in one session.

P0:
- add a canonical autonomous task consumer/executor

P1:
- unify supervisor ownership so one supervisor is truly canonical

P1:
- convert the highest-value menu/skill islands into OpenClaw-callable routes

P2:
- add a true headless runtime mode separate from the interactive menu

### Acceptance Criteria For Any Slice

- uses existing modules instead of introducing a parallel framework
- has deterministic entry points
- has targeted tests or deterministic verification
- updates `ModLog.md`
- writes one workspace memory note under `modules/communication/moltbot_bridge/workspace/memory/`
- clearly reports changed files and what remains

### Report Format

Return:

1. what you changed
2. why this slice was the right next move
3. exact files changed
4. tests or verification run
5. residual blockers for full OpenClaw autonomy
```

---

## Worker Prompt A - Autonomous Task Consumer

```md
You are `0102` working only on the autonomous task queue execution gap.

Goal: wire a canonical consumer for `AgentDB.agents_autonomous_tasks` so published self-research tasks can actually be assigned, executed, verified, and completed.

### Scope

Read and work within:

- `modules/infrastructure/database/src/agent_db.py`
- `modules/infrastructure/idle_automation/src/self_research_refresh.py`
- `modules/communication/moltbot_bridge/src/openclaw_supervisor.py`
- `modules/infrastructure/supervisor/src/supervisor_24x7.py`
- any existing broker/WRE execution surface you truly need

### Constraints

- do not create a brand-new autonomy subsystem
- attach the task consumer to the canonical supervisor path
- do not bypass OpenClaw/WRE with ad hoc direct execution
- keep one bounded execution policy at a time

### Deliverable

Implement the smallest safe slice that:

1. reads pending autonomous tasks
2. claims one task for `0102`
3. dispatches it through the existing execution plane
4. records success/failure
5. completes or leaves the task pending/deferred deterministically

### Verify

- targeted tests for queue lifecycle
- deterministic smoke path for one synthetic task

### Done Means

The repo now has one canonical runtime path that can consume at least one autonomous task from `AgentDB` without human menu interaction.
```

---

## Worker Prompt B - Supervisor Unification

```md
You are `0102` working only on supervisor ownership and runtime authority.

Goal: resolve the split between:

- `modules/communication/moltbot_bridge/src/openclaw_supervisor.py`
- `modules/infrastructure/supervisor/src/supervisor_24x7.py`

### CTO Direction

- `OpenClawSupervisor` is canonical now
- `Supervisor24x7` is a donor/prototype, not the production owner
- `main.py` boot should point to that authority
- AI Overseer remains planner/gate/sentinel host, not the runtime executive
- OpenClaw remains the executive control plane

### Scope

Read and work within:

- `main.py`
- `modules/communication/moltbot_bridge/scripts/launch.py`
- `modules/communication/moltbot_bridge/src/openclaw_supervisor.py`
- `modules/infrastructure/supervisor/src/supervisor_24x7.py`
- related docs only as needed

### Deliverable

Produce the smallest safe migration that:

1. picks the canonical supervisor
2. ports over the missing autonomy behaviors needed from the other implementation
3. avoids two competing runtime authorities
4. keeps startup wiring explicit and deterministic

### Verify

- tests or deterministic checks for supervisor boot/observe/triage paths
- confirm `main.py` boot path matches the chosen supervisor

### Done Means

Another 0102 can read the repo and clearly answer who owns 24/7 autonomy, without ambiguity.
```

---

## Worker Prompt C - Route The Highest-Value Menu Islands

```md
You are `0102` working only on the biggest menu/skill islands blocking OpenClaw autonomy.

Goal: promote the highest-value existing capabilities into OpenClaw-callable routes instead of leaving them trapped in CLI menus or standalone executors.

### Start With These Targets

1. LinkedIn group operations:
   - `approve_members`
   - `message_members`
   - `full_cycle`
2. Holo/HoloDAE operational controls that are still menu-only

### Scope

Read and work within:

- `modules/communication/moltbot_bridge/src/openclaw_capability_audit.py`
- `modules/communication/moltbot_bridge/src/linkedin_social_adapter.py`
- `modules/platform_integration/linkedin_agent/skillz/openclaw_group_news/executor.py`
- `modules/infrastructure/cli/src/main_menu.py`
- `modules/infrastructure/cli/src/holodae_menu.py`
- any existing OpenClaw execution-route modules you need

### Constraints

- do not create duplicate automation logic
- wrap existing executor behavior
- preserve dry-run support
- make operator-facing commands deterministic

### Deliverable

Add the smallest route surface that turns at least one currently manual island into a real OpenClaw-executable capability.

### Verify

- targeted tests for the new command parsing/routing
- one dry-run verification path for LinkedIn group operations or Holo controls

### Done Means

At least one P1 operational capability that previously required CLI submenu navigation can now be invoked directly through OpenClaw.
```

---

## Recommended Order

If you are launching multiple 0102 windows:

1. Worker A first
2. Worker B second
3. Worker C third

Reason:

- without Worker A, self-research can rank work but not execute it
- without Worker B, runtime ownership stays ambiguous
- Worker C matters, but only after the system can schedule and own work properly

---

## Current Architecture Decision

Do not ask whether sentinels should manage the system. They should not.

Use this control split:

- `AI Overseer + sentinels` = observe, gate, correlate, rank
- `canonical supervisor` = schedule, budget, launch, verify
- `OpenClaw` = executive/control plane
- `WRE + DAEs` = execution
- `PatternMemory + workspace memory` = recall and learning

That is the direction. Build toward it incrementally.
