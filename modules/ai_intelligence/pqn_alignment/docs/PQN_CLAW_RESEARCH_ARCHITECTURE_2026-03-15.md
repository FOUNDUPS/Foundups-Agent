# PQN Claw Research Architecture

**Date**: 2026-03-15  
**Author**: 0102  
**WSP References**: WSP 22, WSP 77, WSP 80, WSP 84, WSP 96, WSP 97

## Purpose

Define the Claw-era architecture for PQN research now that OpenClaw exists as the active control plane.

This updates the older model where PQN research was framed primarily as direct AI Overseer / Qwen / Gemma coordination.

## Canonical Decision

PQN research should be treated as a `WSP_97` execution plane:

- `main.py` bootstraps readiness, preflights, and daemon registration
- `OpenClaw (0102)` owns conversational mission control and routing
- `PQNAlignmentDAE` owns detector-first research logic and memory
- `PQN MCP` owns external/tool-augmented research actions under WSP 96 governance
- `AI Overseer`, `Qwen`, `Gemma`, and other research agents act as workers or council participants

## Startup Policy

`main.py` should **not** automatically launch an uncontrolled PQN research swarm on every startup.

Under `WSP_97` the correct split is:

1. `Preflight`
   - verify PQN module health
   - verify detector dependencies
   - verify MCP/security gates
   - verify research artifacts/doc paths
2. `Bootstrap`
   - register PQN research services with DAEmon / Claw surfaces
   - make the research plane available to OpenClaw
3. `Runtime`
   - only start an actual research session when Claw or an approved automation policy invokes it

Reason:

- research is expensive
- research can touch external tools and models
- research should be mission-driven, not startup noise
- Claw must remain the governance point for agent participation

## Canonical Runtime Flow

```text
012 request or policy trigger
-> OpenClaw mission control
-> WSP 97 execution-plane resolution
-> PQN research plane selected
-> PQNAlignmentDAE / PQN MCP session created
-> AI Overseer + specialist agents participate
-> results written to memory/docs
-> OpenClaw reports status back to 012
```

## Agent Roles

### OpenClaw (0102)

- front door for natural-language research control
- decides whether the request is:
  - detector execution
  - literature/tool research
  - theory synthesis
  - documentation update
  - escalation to strategic council
- applies WSP 96 / WSP 97 gates before external or mutating research actions

### PQNAlignmentDAE

- canonical detector-first research module
- holds theory archive context
- runs detector, sweep, council, promotion, memory writeback

### PQN MCP

- optional tool surface for:
  - Google Scholar / external research
  - MCP tools
  - structured research coordination tasks
- remains gated by WSP 96 and OpenClaw policy

### AI Overseer / Qwen / Gemma / External Models

- worker roles, not top-level principals
- can be summoned into a research session by OpenClaw
- provide:
  - fast pattern detection
  - strategic synthesis
  - validation
  - cross-model comparison

## Siri-Like Research Sessions

The right analogue is not a permanently speaking Siri clone.

The correct model is:

- OpenClaw provides the single conversational surface
- OpenClaw can summon specialist research agents into a session
- the user still talks to `0102`
- worker agents remain behind the control plane unless explicitly surfaced

This preserves one identity boundary:

- `012` = principal
- `0102` = Claw
- all research workers are subordinate participants under `0102`

## Main.py Requirement

`main.py` should launch **PQN research readiness**, not default autonomous PQN research execution.

That means:

- yes: preflight and registration
- yes: expose PQN plane to OpenClaw
- no: start full research sessions automatically by default

An optional future mode may exist:

- `PQN_RESEARCH_AUTOSTART=1`

But this should be an explicit policy mode, not the default system behavior.

## MCP Gating Requirement

OpenClaw participation in PQN research must respect:

- WSP 96 MCP governance
- OpenClaw security sentinel
- Claw policy gates
- audit trail to DAEmon / memory

This means OpenClaw should not directly bypass the PQN MCP surface when the task requires external research tooling.

## Documentation Consequence

Older docs that describe PQN research as only:

- AI Overseer agents
- Qwen/Gemma local workers
- direct coordinator-led sessions

are now incomplete.

The canonical description is:

**OpenClaw-controlled, WSP 97 routed, detector-first research orchestration.**

## Implementation Direction

The next implementation stage should add:

1. PQN research plane registration in startup/bootstrap
2. OpenClaw routing phrases for PQN research
3. DAEmon visibility for research-session actions
4. optional policy-gated autonomous research sessions

Until then, docs should treat this as the target architecture.
