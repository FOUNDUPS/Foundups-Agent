# Hermes-Inspired FoundUps Native Roadmap

Date: 2026-03-23
Owner: 0102
Scope: OpenClaw-wide native enhancement plan

> **PLANNING SNAPSHOT — 2026-03-23**
> This document was a live backlog at time of writing. It is now a historical record.
> **Live slice authority**: [`docs/0102_session_briefings/ACTIVE_SLICE_LEDGER.md`](../../../../../docs/0102_session_briefings/ACTIVE_SLICE_LEDGER.md)
> Do not treat unmarked items here as open work. Verify against the ledger first.

---

## Slice Audit (2026-03-29)

| Slice | Status | Evidence |
|-------|--------|----------|
| `session_recall_search_foundation` | **CLOSED** | `1eb329d03` |
| `memory_nudge_engine` | **CLOSED** | `c0e676677`, `665963517`, `e8a16d7bd` |
| `openclaw_memory_queries` | **CLOSED** | `b9490db9e`, `387d4a735` |
| `scheduled_natural_language_automations` | **CLOSED** | `71f248d04` + backlog JSON |
| `gateway_continuity_layer` | **CLOSED** | `a70ddf15a`, `6d9620881`, `48d048143` |
| `model_provider_switching_cleanup` | **PARTIAL** | `openclaw_model_policy.py` landed at `4754953b2`; full "cleanup" not closed |
| `skill_evolution_loop` | **NOT STARTED** | No implementation in `moltbot_bridge/src`; backlog JSON status `?` |

---

## Goal

Build the useful Hermes patterns **inside FoundUps** so OpenClaw can keep the
system current, persistent, and self-cleaning while the human is offline.

This is not a Hermes adoption plan. It is a native FoundUps roadmap.

## Architecture Rule

Keep ownership here:

- `OpenClaw` = executive control plane
- `AI Overseer` = ranking, gating, incident correlation
- `OpenClawSupervisor` = scheduler and execution loop
- `WRE` = deterministic skill execution
- `AgentDB + PatternMemory + workspace memory + HoloIndex` = memory plane

Do not add a second runtime or second memory authority.

## 2026-03-28 Execution Rule

For the current tranche, OpenClaw should behave as a bounded maintenance worker under `WSP 15` prioritization and `WSP 77` coordination:

- start with simple, low-risk tasks
- use HoloIndex as retrieval and subroutine direction
- execute through existing adapters / WRE / native skillz
- generate reports and durable artifacts
- leave architecture review and tuning to `0102`

In this mode, OpenClaw is effectively `Kohi`: the doer, not the architect.

This roadmap is therefore optimized for:
- low-fruit fixes
- bounded maintenance loops
- retrieval-guided execution
- reviewable artifact generation

## Native Feature Set

### 1. Session Recall/Search — CLOSED

~~The system should answer:~~

- ~~`what did we decide about X`~~
- ~~`what was I working on last night`~~
- ~~`show past sessions related to OpenClaw autonomy`~~
- ~~`what unresolved work was left after the last architecture review`~~

**Status**: Landed at `1eb329d03`. See `openclaw_execution_routes.py` recall routes.

### 2. Memory Nudges — CLOSED

~~The system should not rely on the human remembering to write memory.~~

**Status**: Landed at `c0e676677`, `665963517`, `e8a16d7bd`. See `openclaw_supervisor.py` nudge emission.

### 3. Offline Work Continuity — CLOSED

~~The human is moving faster than the repo can absorb manually.~~

**Status**: Covered by gateway continuity (`a70ddf15a`+), memory nudges, and bounded maintenance loop (`71f248d04`).

## Roadmap

### P0: Session Recall/Search Foundation — ~~OPEN~~ → **CLOSED** (`1eb329d03`)

~~Outcome:~~
~~- OpenClaw can retrieve prior decisions and work context from native memory.~~

### P0: Memory Nudges — ~~OPEN~~ → **CLOSED** (`c0e676677`, `665963517`, `e8a16d7bd`)

~~Outcome:~~
~~- important context is captured automatically instead of being lost.~~

### P1: Scheduled Natural-Language Automations — ~~OPEN~~ → **CLOSED** (`71f248d04`)

~~Outcome:~~
~~- OpenClaw can run routine review/cleanup/report flows on a schedule.~~

### P1: Unified Gateway Continuity — ~~OPEN~~ → **CLOSED** (`a70ddf15a`, `6d9620881`, `48d048143`)

~~Outcome:~~
~~- one continuity layer across CLI, webhook, and platform messaging surfaces.~~

### P1: Model/Provider Switching Cleanup — **PARTIAL**

Outcome:
- switch providers and roles cleanly from one FoundUps control surface.

Native scope:
- centralize model routing and health/readiness decisions

**Status**: `openclaw_model_policy.py` landed at `4754953b2` with `has_model_switch_intent`, `parse_model_switch_target`, `wsp00_model_switch_gate`. Full "cleanup" (all surfaces unified) not yet closed. Not currently in ledger as open slice — add to ledger before picking up.

### P1: Skill Evolution Loop — **NOT STARTED**

Outcome:
- repeated tasks produce better native skills over time.

Native scope:
- use PatternMemory outcomes plus WRE promotion flow
- avoid autonomous skill sprawl without validation

**Status**: No implementation in `moltbot_bridge/src`. Backlog JSON shows `?`. Not in ledger as open slice. Add to ledger before picking up.

## First Three Slices — ALL CLOSED

1. `session_recall_search_foundation` — **CLOSED** `1eb329d03`
2. `memory_nudge_engine` — **CLOSED** `c0e676677`+
3. `openclaw_memory_queries` — **CLOSED** `b9490db9e`, `387d4a735`

## CTO Handling Rule

When a new external signal appears:

1. `0102` verifies the upstream source.
2. `0102` applies WSP 97 and WSP 15.
3. If useful, convert it into a **native backlog item**, not a runtime dependency by default.
4. `OpenClaw` and `AI Overseer` track the backlog.
5. `WRE` executes bounded slices once there is a real skill path.

This is how the system keeps up without turning into a pile of half-adopted frameworks.
