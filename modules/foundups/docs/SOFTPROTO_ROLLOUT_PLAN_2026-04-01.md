# SoftProto Rollout Plan

## Status

Proposed architectural branch for FoundUps UI evolution.

SoftProto is now defined as a core UI systems layer for FoundUps.

It is not:
- a theme
- a visual redesign
- a framework migration by itself

It is:
- the schema-driven interface system for user-owned layout
- the gesture-remapping system
- the movable-module system
- the future AI-mediated UI control layer

This plan formalizes:
- rollout order
- worker boundaries
- repo tracking
- indexing requirements

## Source Context

Current repo truth:
- the admitted surface is still the static `/public/member/` shell
- active split modules already exist:
  - `public/member/js/gesture-engine.js`
  - `public/member/js/mall-planes.js`
  - `public/member/js/account-concierge.js`
  - `public/member/js/red-dog-concierge.js`
- the correct first move is an isolated SoftProto spike mounted into
  `/member/`, not a full rewrite

## Architectural Decision

### Locked Decision

Svelte is the rendering layer.

SoftProto is the system above it:
- layout schema
- gesture schema
- interaction scope model
- module registry
- preference store
- persistence layer
- command layer
- renderer integration

### Correct Model

```text
UI = render(layout_schema + gesture_schema + module_registry + user_prefs)
```

### Incorrect Model

```text
UI = fixed components with baked-in positions and gestures
```

### Practical Implication

We will not begin by rewriting the live gateway or admitted shell into Svelte.

We will:
1. architect SoftProto as a contract/system
2. audit current planes against that contract
3. build one isolated Svelte spike inside `/member/`
4. prove coexistence before broader migration

## Why This Matters

FoundUps pages cannot remain hard-coded if the user is expected to own the
interface.

Target behavior:
- the user can move the mic
- the user can move search
- the user can remap swipe logic
- the user can enter edit/customize mode
- AI can later modify the same layout through commands
- all of this persists across sessions

## Scope

### In Scope

- schema-driven UI foundation
- isolated Svelte SoftProto spike
- safe mount into admitted `/member/` shell
- local persistence for layout and gesture preferences
- future AI command hooks
- worker audits by plane
- roadmap / ModLog / WSP index integration
- HoloIndex reindex

### Out Of Scope For This Phase

- full site rewrite
- gateway migration
- full visual builder
- server sync
- full conversational AI UI editing
- replacing all current gesture systems globally
- broad framework migration across repo

## Rollout Order

### Phase 0 - Architecture Lock

Create and commit the canonical SoftProto architecture note.

Deliverable:
- `modules/foundups/docs/SOFTPROTO_FOUNDATION_ARCHITECTURE_2026-04-01.md`

### Phase 1 - Root Tracking + Retrieval Wiring

Update top-level tracking and retrieval surfaces.

Required updates:
- root roadmap
- root ModLog
- WSP index
- FoundUps domain canonical index
- HoloIndex refresh

### Phase 2 - Plane Audits

Run bounded audits by worker/plane before implementation.

Workers:
- `A` = gateway audit
- `B` = Mall shell audit
- `C` = user panel / concierge / Red Dog audit
- `D` = guardrails / coherence / interaction conflict audit

### Phase 3 - Isolated Spike

Implement:
- `softproto_svelte_spike_phase1`

Target:
- admitted `/member/` shell only

### Phase 4 - Contract Expansion

After spike success:
- formalize module contracts
- define per-plane adoption strategy
- expand gesture compatibility rules
- define shared command API for AI + user editing
- define migration path for additional surfaces

## Worker Responsibilities

### Architect First

Do not let A/B/C/D independently implement SoftProto first.

The contract must be defined once, then each worker audits against it.

### Worker A - Gateway

Audit:
- hard-coded layout assumptions
- future mount points
- what must remain static
- what can become SoftProto-aware later

### Worker B - Mall Shell

Audit:
- current shell composition
- gesture dependencies
- safest mount options for isolated SoftProto spike
- future image/video FoundUp card integration points

### Worker C - User Panel / Concierge / Red Dog

Audit:
- which UI modules belong to the user-owned agent layer
- what should become movable/configurable first
- how Red Dog remains the user's own agent surface
- freemium -> premium interaction needs

### Worker D - Guardrails / Coherence

Audit:
- drag/edit conflicts
- gesture collisions
- suppression of normal actions during edit
- AI-command vs manual-edit conflicts
- persistence corruption fallback
- bounded command permissions

## First Implementation Target

### Surface

`/public/member/`

### Reason

This admitted experience already carries:
- `gesture-engine.js`
- `mall-planes.js`
- `account-concierge.js`

It is the correct place to prove SoftProto without detonating the public
gateway or forcing a full migration.

### First Proof Modules

Only 4 modules for the spike:
- mic
- search
- logout/options
- menu trigger / Red Dog trigger

## Canonical Design Rules

1. No hard-coded permanent placement for registered modules.
2. Layout must be driven by schema/state.
3. Gesture mappings must be data-driven and user-remappable.
4. AI commands and visual editing must use the same underlying store/actions.
5. Edit mode must clearly separate customization from normal interaction.
6. Current shell stability takes priority over framework purity.
7. Svelte is the rendering layer, not the full system definition.
8. Architecture first, audits second, spike third.

## Nested Interaction Rule

SoftProto must support recursive interaction scopes across:
- app
- plane
- module
- submodule
- object

Every scope needs:
- default bindings
- local overrides
- inheritance fallback
- addressable command targets

This prevents future gesture rewrites every time a new widget, camera tool,
Red Dog affordance, or FoundUp object appears.

## Required Root Repo Updates

### Root Roadmap

Add SoftProto as a top-level architectural branch under UI / interface
evolution.

### Root ModLog

Record:
- SoftProto architecture decision locked
- Svelte selected as rendering layer
- no full shell rewrite authorized for phase 1
- admitted `/member/` selected as first spike surface
- worker audit split defined

### WSP Index

Point canonical discovery toward:
- `modules/foundups/docs/SOFTPROTO_FOUNDATION_ARCHITECTURE_2026-04-01.md`
- `modules/foundups/docs/SOFTPROTO_ROLLOUT_PLAN_2026-04-01.md`

### HoloIndex

SoftProto docs must be reindexed after roadmap / ModLog / WSP updates.

## Risks

### 1. Parallel Drift

If A/B/C/D all implement their own interpretation first, the system fragments.

Mitigation:
- architect once
- bounded audits only
- single spike first

### 2. Framework Overreach

A full Svelte rewrite of gateway/member shell creates unnecessary blast radius.

Mitigation:
- isolated spike only
- mount into current shell
- prove coexistence first

### 3. Gesture Conflicts

Current gesture engine may collide with edit-mode or drag behaviors.

Mitigation:
- D audit first
- scoped event handling
- explicit edit-mode suppression rules

### 4. Persistence Inconsistency

Local preference corruption or schema version drift could break UX.

Mitigation:
- versioned schema
- safe defaults
- reset path
- corruption recovery

### 5. AI/User Command Divergence

If AI controls one path and visual editing another, state will drift.

Mitigation:
- one command/store layer only
- all changes pass through shared commands

## Immediate Next Moves

Required now:
1. update root roadmap
2. update root ModLog
3. update WSP index / references
4. add this rollout plan
5. reindex HoloIndex

Then:
- write plane audit prompts
- write the isolated spike prompt

## Acceptance Condition

This rollout plan is complete when:
- SoftProto is visible in root planning docs
- WSP-linked docs point to SoftProto canon
- HoloIndex retrieval includes SoftProto docs
- worker boundaries are explicit
- the spike target is fixed to `/member/`
- no one mistakes Svelte for the whole system

## Final Decision

SoftProto is now a major FoundUps architectural branch.

It will be rolled out as:
- contract first
- repo memory second
- plane audits third
- isolated admitted-shell spike fourth
- expansion only after proof
