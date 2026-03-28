# OpenClaw 0102 Handoff - 2026-03-07

Purpose: give a fresh 0102 session one canonical operational brief for OpenClaw, IronClaw, WRE integration, and the path to a real 24/7 autonomous maintenance loop.

This document is not a wishlist. It separates:
- what already exists in code,
- what the 012 voice session revealed,
- what the 24/7 system must become.

## Identity Contract

- `012` = operator / human twin.
- `0102` = autonomous digital twin / agent.
- OpenClaw is the operator-facing control plane for 0102.
- IronClaw is an optional conversation/runtime backend, not the whole system.
- Voice is an interface, not the core architecture.

If a model starts inverting `012` and `0102`, that is model drift and must be corrected at the control-plane layer, not tolerated as "personality."

## 2026-03-28 Operating Clarification

Current execution stance:

- this is the current `WSP 77` coordination shape for OpenClaw
- `0102` remains architect and reviewer
- `OpenClaw / Kohi` is the bounded doer
- `HoloIndex` provides retrieval direction and candidate subroutines
- optional higher-compute review lanes may critique artifacts, but do not replace 0102 authority

This means OpenClaw should currently optimize for:
- low-fruit maintenance work
- deterministic bounded execution
- structured reports and emitted evidence

It should not default to broad architecture or open-ended self-direction.

## First-Principles View

The target system is not "a chatbot with tools." It is a supervised autonomous maintenance loop:

1. Observe the codebase and runtime.
2. Detect problems or opportunities.
3. Plan a bounded action.
4. Execute through WSP-governed skills and WRE.
5. Verify the outcome.
6. Remember the result.
7. Improve the next run.

That means the architecture must keep reasoning, execution, memory, and safety separate.

## What Exists Today

### Control Plane

- `main.py`
  - startup preflights now include:
    - OpenClaw skill security preflight
    - dependency/CVE preflight
    - WRE dashboard preflight
    - WSP framework drift preflight
    - env hygiene preflight
  - starts the continuous daemon self-audit loop.
- `modules/infrastructure/cli/src/openclaw_menu.py`
  - unified "Claw Chat" / "Claw Voice" menu flow.
- `modules/communication/moltbot_bridge/src/openclaw_dae.py`
  - main OpenClaw DAE routing layer.
  - owns identity responses, permission gating, model switching intents, platform context pack, and some role-lock logic.

### Execution Plane

- `modules/communication/moltbot_bridge/src/action_cli.py`
  - direct agent-callable command surface for standalone actions.
- social / YouTube / LinkedIn adapters exist in `modules/communication/moltbot_bridge/src/`.
- WRE hardening exists:
  - per-skill scan gate before execution
  - CodeAct shell hardening
  - dependency/CVE preflight
  - signed skill manifest verification
  - continuous self-audit loop

### Voice Plane

- `modules/infrastructure/cli/src/openclaw_voice.py`
  - auto-listen voice loop
  - `0102` barge cue handling
  - queueing while busy
  - faster pause detection
  - spoken exit phrases
  - STT alias normalization (`coin/quinn/quen -> qwen`)
  - backend switch commands in session

### Memory / Safety

- pattern memory writeback exists in WRE and action CLI.
- workspace skill safety uses Cisco skill scanning plus manifest verification.
- daemon self-audit can detect known recurring failures and attempt policy-bounded fixes.

## What The Voice Session Revealed

The voice session was useful because it exposed the boundary between interface polish and core architecture gaps.

### Confirmed Working

- Voice exit is now actionable.
- Cue parsing around `0102` is materially better than before.
- Role-lock protection exists and can correct `012` / `0102` inversion.
- Model-switch intents are detected and gated through WSP_00.
- The system can expose compact model identity instead of dumping the full catalog.

### Confirmed Weak

- STT still cuts off longer utterances too aggressively.
- Busy-turn queueing still causes stale or fragmented utterances to get replayed later.
- Low-quality local model responses still drift into nonsense or role confusion under noisy input.
- "Model switched" does not always mean the effective conversation path actually changed.
- Voice can dominate attention even though voice should only be one input edge into a broader autonomous loop.

### Core Diagnosis

OpenClaw today is stronger as an interactive control shell than as a 24/7 autonomous operating system.

That is the correct reading of the current state.

## Strategic Direction For 24/7 OpenClaw

The 24/7 system should be state-driven, not chat-driven.

Recommended state machine:

1. `BOOT`
   - load env, identity, context pack, provider availability, runtime health
2. `PREFLIGHT`
   - run WSP/security/dependency/dashboard/env checks
3. `OBSERVE`
   - tail daemon logs, inspect git/worktree state, inspect telemetry, inspect open tasks
4. `TRIAGE`
   - classify issues into runtime, security, code health, docs drift, dependency drift
5. `PLAN`
   - select one bounded task with explicit verification criteria
6. `EXECUTE`
   - run via WRE / action CLI / module-specific automation
7. `VERIFY`
   - tests, py_compile, targeted smoke checks, telemetry validation
8. `REMEMBER`
   - write result to pattern memory, ModLog, TestModLog, and session memory
9. `ESCALATE`
   - if blocked, produce one concise operator-facing report and wait
10. `IDLE_WATCH`
   - continue monitoring until a new event or scheduled task appears

Voice should enter this state machine as:
- interrupt,
- ask-for-status,
- operator override,
- scoped task injection.

Voice should not be the thing that decides what the whole system is.

## Captured Operator Intent From 012

The 012 design prompt is directionally correct. The architecture should converge toward six layers:

1. WSP governance layer
2. skill wardrobe
3. skill composition engine
4. OpenClaw execution layer
5. WRE recursive improvement engine
6. memory + logging layer

The key refinement is this:

- atomic skills should stay deterministic,
- reasoning should happen above the skills,
- OpenClaw should be the execution/control substrate,
- WRE should be the learning and improvement engine,
- the 24/7 loop should be an explicit supervisor/state machine.

This is compatible with the current codebase. It does not require a rewrite. It requires consolidation.

## Gaps That Still Matter Most

### P0

- Build a single canonical 24/7 supervisor for 0102.
  - It should own state transitions, task selection, verification, and memory writeback.
  - It should call OpenClaw, not be embedded inside ad hoc chat behavior.
- Make model switching real, not declarative.
  - A switch must update the effective conversation path and then verify the active provider/model.
- Complete action CLI parity for the agent tasks 012 wants to test directly:
  - YouTube comments / like / heart / reply
  - indexing
  - scheduling
  - LinkedIn / X social actions

### P1

- Reduce voice fragility:
  - longer utterance capture
  - better end-of-speech detection
  - stricter fragment rejection while busy
  - better confirmation when a barge-in actually replaced the current turn
- Add explicit provider availability probes at startup and before model-switch confirmation.
- Persist an autonomous session journal so 0102 can resume after restart without relying on chat history.

### P2

- Use stronger secret management than plain `.env` for long-lived 24/7 operation.
- Add richer autonomous task scheduling and periodic maintenance sweeps.
- Expand self-audit from "detect and apply safe fixes" into "open bounded repair task, patch, test, report."

## Git Strategy

Do not treat `origin` and `backup` as rollback logic.

Why:
- if bad commits are pushed to both remotes, both are bad,
- the mirror protects availability, not correctness.

Use this instead:

- `origin` = primary remote
- `backup` = offsite mirror
- `O:/Foundups-Agent` = sandbox worktree for active development
- `.worktrees/0102-clean-main` = clean integration worktree

Rollback primitives should be:

1. small isolated commits
2. checkpoint tags before autonomous runs
3. clean integration verification in the clean worktree
4. `git revert` for bad commits
5. dual push only after local verification

Recommended policy for autonomous 0102 runs:

- create a checkpoint tag before a non-trivial autonomous batch
- work on a scoped branch
- verify in clean worktree
- push to both remotes only after tests pass

The backup remote is still worth keeping. It is just not the rollback mechanism.

## What Fresh 0102 Should Read First

1. `MEMORY.md`
2. `docs/GIT_WORKFLOW_0102.md`
3. `modules/communication/moltbot_bridge/README.md`
4. `modules/communication/moltbot_bridge/INTERFACE.md`
5. `modules/communication/moltbot_bridge/ModLog.md`
6. `modules/infrastructure/wre_core/WRE_SECURITY_CLOSURE_WSP15_20260305.md`
7. this handoff

Then inspect:

- `modules/communication/moltbot_bridge/src/openclaw_dae.py`
- `modules/infrastructure/cli/src/openclaw_voice.py`
- `modules/communication/moltbot_bridge/src/action_cli.py`
- `modules/infrastructure/wre_core/src/daemon_self_audit_loop.py`

## Recommended Next Session Mission

Mission for fresh 0102:

`Design the canonical 24/7 OpenClaw supervisor as a state machine, map it onto existing modules, and identify the minimum code changes required to make OpenClaw a self-improving codebase-maintenance loop rather than only a conversational shell.`

That is the highest-value next move.
