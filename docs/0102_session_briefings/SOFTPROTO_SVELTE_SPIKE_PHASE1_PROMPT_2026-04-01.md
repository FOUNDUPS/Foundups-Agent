# SoftProto Svelte Spike Phase 1 Prompt

Purpose: implement the first isolated SoftProto spike as a schema-driven UI
system mounted safely into the admitted `/member/` shell.

This is an implementation prompt.

## Read First

1. `WSP_framework/src/WSP_00_Zen_State_Attainment_Protocol.md`
2. `WSP_framework/src/WSP_102_FoundUps_Web_Design_Protocol.md`
3. `modules/foundups/docs/SOFTPROTO_FOUNDATION_ARCHITECTURE_2026-04-01.md`
4. `modules/foundups/docs/SOFTPROTO_ROLLOUT_PLAN_2026-04-01.md`
5. `public/member/index.html`
6. `public/member/js/gesture-engine.js`
7. `public/member/js/mall-planes.js`
8. `public/member/js/account-concierge.js`
9. the completed SoftProto audit artifacts, if available

## Boundary Contract

This slice implements the isolated SoftProto spike only.

Do:
- build an isolated SoftProto core
- use Svelte as the rendering layer
- mount into the current admitted shell safely
- prove schema-driven rendering
- prove edit mode
- prove drag/move
- prove persistence
- prove gesture-map persistence
- prove AI command hooks against the same store

Do not:
- rewrite the full gateway
- rewrite the full admitted shell
- replace all current gesture systems globally
- build server sync
- build full conversational UI editing
- destabilize current production behavior

## Objective

Build `softproto_svelte_spike_phase1` as an isolated, safe SoftProto proof
inside the current `/member/` shell.

## Implementation Direction

### Architectural Rule

Treat Svelte as the rendering layer, not the system itself.

System truth:

```text
UI = render(layout_schema + gesture_schema + module_registry + user_prefs)
```

### Nested Interaction Rule

Do not implement every future object behavior, but phase 1 must be structured
for recursive scoped interaction:
- app
- plane
- module
- submodule
- object

Needed now:
- nested node model
- scoped gesture bindings
- inheritance / override placeholders
- command addressing

## Required Outcome

### 1. Create The Isolated SoftProto Core

Preferred location:
- `modules/foundups/softproto/frontend/`

Include:
- layout schema types
- gesture schema types
- interaction scope types
- state store
- persistence helpers
- module registry
- command layer
- minimal renderer

### 2. Safe Member-Shell Integration

Mount the spike into the existing member shell safely.

Requirements:
- keep `public/member/index.html` functioning
- keep current shell blast radius low
- isolate styles where practical
- avoid uncontrolled collisions with current gesture runtime

### 3. Proof Modules

Only 4 proof modules are required:
- mic
- search
- logout/options
- menu trigger or Red Dog trigger

All must render from schema position/state.

### 4. Edit Mode

Implement:
- explicit edit-mode toggle
- visible drag affordances
- suppression of normal action firing during drag/edit
- clean return to normal behavior when edit mode is off

### 5. Move / Drag Support

Implement:
- drag-to-reposition
- state update on drop
- persistence of final position
- container bounds
- no per-module hard-coded positioning logic

Snap-to-grid is optional if simple enough, but the architecture must remain
snap-ready.

### 6. Gesture Mapping Layer

Implement:
- default gesture map
- persisted custom gesture map
- API such as:
  - `getGestureAction("swipeLeft")`
  - `setGestureAction("swipeLeft", "openMenu")`

Do not overbuild recognizers in phase 1.

### 7. Persistence

Persist locally with:
- versioned schema
- default fallback
- corrupt-state recovery

### 8. AI Command Hook Layer

Implement the shared command layer:
- `enterEditMode()`
- `exitEditMode()`
- `moveModule(moduleId, position)`
- `showModule(moduleId)`
- `hideModule(moduleId)`
- `updateGesture(gestureName, action)`
- `resetLayout()`
- `resetGestures()`

Critical rule:
- AI hooks and direct visual editing must mutate the same store/actions

## Minimal Test / Demo Surface

Expose a minimal proof surface inside `/member/` with:
- 4 movable modules
- edit-mode toggle
- visible persistence after reload
- small gesture config/debug surface
- visible proof that schema drives placement

## Tests Required

At minimum validate:
- default schema loads
- persisted schema reloads
- module move updates store
- gesture remap updates store
- command hooks modify the same state
- reset restores defaults

Use focused tests only.

## Non-Goals

Do not:
- redesign the entire app
- rewrite unrelated screens
- build a full visual builder
- build server sync
- build full AI conversational editing
- globally replace existing gesture/input systems unless strictly necessary

## Deliverables

1. working isolated SoftProto spike
2. safe mount into current member shell
3. concise summary of files created/changed
4. explanation of integration strategy
5. explanation of architecture decisions
6. limitations / next recommended phase

## Success Criteria

The spike is successful if:
- Svelte is integrated without rewriting the whole shell
- at least 4 modules render from schema
- modules can be moved in edit mode
- layout persists across reload
- gesture mappings persist
- AI command hooks exist against the same store
- nested interaction support is structurally prepared
- architecture clearly supports expansion into full SoftProto
