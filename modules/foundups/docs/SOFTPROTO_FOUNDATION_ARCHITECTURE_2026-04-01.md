# SoftProto Foundation Architecture

## Purpose

This note defines the first-principles architecture for `SoftProto` inside
FoundUps.

`SoftProto` is not a page redesign.

`SoftProto` is the user-owned interface layer for FoundUps:
- layout is not hard coded
- gestures are not hard coded
- modules render from schema/state
- interaction scopes must resolve recursively
- later AI commands must mutate the same schema/state as direct user edits

This note exists to prevent four different surfaces from inventing four
different UI systems.

Companion rollout note:
- `modules/foundups/docs/SOFTPROTO_ROLLOUT_PLAN_2026-04-01.md`

## Canonical Rule

```text
UI = render(layout_schema + gesture_schema + module_registry + user_prefs)
```

Not:

```text
UI = fixed components with baked-in position and behavior
```

That rule is the SoftProto contract.

## Repo Truth On 2026-04-01

The live product is not a framework app yet.

Current public surfaces are still static hosted HTML/JS:
- `public/index.html`
- `public/member/index.html`
- `public/member/foundup.html`

The admitted Mall already has split runtime modules:
- `public/member/js/gesture-engine.js`
- `public/member/js/mall-planes.js`
- `public/member/js/account-concierge.js`
- `public/member/js/red-dog-concierge.js`

Current PWA status:
- `public/manifest.json` exists
- no real service worker is wired in `public/`
- current site is only partially PWA-shaped

Conclusion:
- FoundUps already has usable shell surfaces
- FoundUps does not yet have a schema-driven UI operating layer

## Architectural Decision

Use `Svelte` for SoftProto.

Do not rewrite the live gateway or member shell into Svelte first.

Correct decision:
- `Svelte` = rendering/runtime layer for SoftProto
- `SoftProto` = schema + registry + persistence + command layer above it

Why this is the correct fit:
- reactive state maps well to schema-driven UI
- custom elements allow safe mounting into the existing static shell
- static build output fits current Firebase hosting model
- SvelteKit can later support a real service worker and stronger PWA behavior

Primary references:
- Svelte `$state`: <https://svelte.dev/docs/svelte/$state>
- Svelte custom elements: <https://svelte.dev/docs/svelte/custom-elements>
- Svelte context: <https://svelte.dev/docs/svelte/context>
- SvelteKit adapter-static: <https://svelte.dev/docs/kit/adapter-static>
- SvelteKit service workers: <https://svelte.dev/docs/kit/service-workers>

## SoftProto System Model

SoftProto phase 1 should contain these parts:

### 1. Module Registry

Registry entries define what can be rendered.

Phase-1 proof modules:
- mic
- search
- logout/options
- menu trigger or Red Dog trigger

Important rule:
- module components do not decide their permanent position
- the registry only maps module type -> renderable component

### 2. Layout Schema

The layout schema defines placement and visibility.

Minimum shape:

```ts
type ModuleDefinition = {
  id: string;
  type: string;
  label: string;
  visible: boolean;
  draggable: boolean;
  resizable: boolean;
  locked: boolean;
  defaultPosition: { x: number; y: number };
  currentPosition: { x: number; y: number };
  size: { w: number; h: number };
  zIndex: number;
  allowedZones: string[];
};

type LayoutSchema = {
  version: string;
  pageId: string;
  modules: ModuleDefinition[];
  snapToGrid: boolean;
  gridSize: number;
  editMode: boolean;
};
```

### 3. Gesture Schema

Gestures must be data, not hard-coded switch statements.

Minimum shape:

```ts
type GestureSchema = {
  swipeUp: string | { action: string; target?: string };
  swipeDown: string | { action: string; target?: string };
  swipeLeft: string | { action: string; target?: string };
  swipeRight: string | { action: string; target?: string };
  doubleTap: string | { action: string; target?: string };
  longPress: string | { action: string; target?: string };
};
```

### 3A. Nested Interaction Model

Every object is its own interaction plane.

That means:
- app has gestures
- plane has gestures
- module has gestures
- submodule has gestures
- object has gestures

Core rule:

```text
global swipeUp != local swipeUp
```

A swipe on the whole app surface is not the same as a swipe on:
- camera
- mic
- search
- panel
- card
- video object
- Red Dog object
- future widgets

Each level needs:
- default behavior
- customizable behavior
- inheritance / override rules

### 3B. Tesseract Scope Model

```text
App
  -> Plane
    -> Module
      -> Submodule
        -> Object
          -> Action map
```

Each layer must be addressable.

Each layer can:
- inherit parent interaction defaults
- override parent interactions locally
- expose its own edit/customize contract
- later be modified by AI through the same command layer

### 3C. Interaction Scope Model

Every gesture/action binding must declare scope:
- `global`
- `plane`
- `module`
- `submodule`
- `object`

Example:

```json
{
  "gesture": "swipeUp",
  "scope": "object",
  "targetId": "camera.main",
  "action": "openCameraControls"
}
```

### 3D. Inheritance And Override Model

Required fallback path:

```text
object action -> submodule fallback -> module fallback -> plane fallback -> app fallback
```

Local objects must be able to override parent defaults.

Examples:
- app `swipeUp` = open global menu
- camera `swipeUp` = open camera controls
- video card `swipeUp` = expand metadata
- mic `swipeUp` = sensitivity / mode controls

### 3E. Command Path Model

Every target must have an addressable path.

Examples:
- `app.mall.camera.main`
- `app.mall.concierge.reddog`
- `app.mall.search.primary`
- `app.mall.video.feed.card_12`

This is what lets AI and the UI editor hit the same object cleanly.

### 4. User Preference Bundle

One bundle must hold the same truth used by the renderer and by future AI:

```ts
type UserPreferenceBundle = {
  layoutSchema: LayoutSchema;
  gestureSchema: GestureSchema;
  updatedAt: string;
};
```

### 5. Persistence Layer

Phase 1 persistence:
- localStorage
- versioned schema
- default fallback
- corrupt-state recovery

### 6. Command Layer

AI and direct user manipulation must hit the same actions:
- `enterEditMode()`
- `exitEditMode()`
- `moveModule(moduleId, position)`
- `showModule(moduleId)`
- `hideModule(moduleId)`
- `updateGesture(gestureName, action)`
- `resetLayout()`
- `resetGestures()`

This is non-negotiable.

If AI later says "move the mic to the top", it must call the same state
mutation path as drag-and-drop.

The same rule applies to scoped interactions:
- AI command paths
- drag/edit changes
- gesture remaps

must all resolve through the same addressable state tree.

## Updated Schema Direction

SoftProto phase 1 should begin with nested nodes and scoped bindings even if
not every scope gets custom behavior immediately.

### Layout Side

```ts
type LayoutNode = {
  id: string;
  type: "app" | "plane" | "module" | "submodule" | "object";
  parentId?: string;
  children?: string[];
  visible: boolean;
  draggable: boolean;
  resizable: boolean;
  locked: boolean;
  position?: { x: number; y: number };
  size?: { w: number; h: number };
  zIndex?: number;
};
```

### Interaction Side

```ts
type InteractionBinding = {
  gesture: "swipeUp" | "swipeDown" | "swipeLeft" | "swipeRight" | "tap" | "doubleTap" | "longPress";
  scope: "global" | "plane" | "module" | "submodule" | "object";
  targetId: string;
  action: string;
  enabled: boolean;
  customizable: boolean;
};
```

### Resolution Rule

```ts
resolveGesture(targetId, gesture) =>
  local binding
  or parent binding
  or app default
```

## Safe Integration Strategy

The first SoftProto build should be isolated and mounted into the current member
shell.

Preferred location:
- `modules/foundups/softproto/frontend/`

Preferred runtime strategy:
- Svelte 5
- TypeScript
- static build
- custom element or mountable bundle

Preferred mount target:
- admitted `/member/` shell only

Why:
- `/member/` is already the user-owned interior surface
- it has live gestures, planes, and a user panel
- the gateway is still changing and should not absorb a framework pivot first

## Surface Map

SoftProto is not one screen.

It must eventually describe several FoundUps surfaces:

### Surface A. Gateway
- `public/index.html`
- root landing
- terms gate
- login transition

### Surface B. Mall
- `public/member/index.html`
- swipe browsing
- FoundUp carousel/planes

### Surface C. User Panel / Red Dog
- `#accountPlane`
- personal control surface
- Red Dog digital twin surface

### Surface D. FoundUp View
- `public/member/foundup.html`
- FoundUp-specific shell view
- later candidate for live cube/simulation visual

SoftProto should eventually support all four.

Phase 1 should only prove the engine in the admitted shell.

## Sequencing Decision

Do not have A/B/C/D all invent SoftProto in parallel first.

Correct sequence:

1. Architect the SoftProto contract first
2. Run bounded audits on each surface
3. Build one isolated SoftProto spike
4. Plug each surface into the same contract later

This prevents:
- incompatible schema assumptions
- duplicated gesture engines
- page-specific hacks
- God modules hidden under different names
- flat gesture systems that collapse under later module growth

## Worker Split For SoftProto Preparation

### Architect / Spike Owner

One implementation owner should build the SoftProto core spike.

This owner builds:
- schema types
- registry
- persistence
- command layer
- demo mount
- proof modules

This should happen before A/B/C start real SoftProto integration work.

### Worker A Audit: Gateway Surface

Audit:
- which controls are currently fixed-position
- which hero/login/gate modules should become movable later
- which gestures should remain locked for legal reasons
- which interactions must never be remapped

Focus:
- root gateway only
- no SoftProto implementation yet

### Worker B Audit: Mall Surface

Audit:
- which Mall controls are now hard-coded
- which visual tiles or triggers should become module-registry items
- which gestures are global shell gestures vs per-view gestures
- which local objects will need their own gesture domains later
- where future image/video FoundUp cards would plug into SoftProto

Focus:
- Mall browsing plane
- navigation planes
- desktop parity for gestures

### Worker C Audit: User Panel / Red Dog Surface

Audit:
- which account-plane elements are personal modules
- which Red Dog controls should become movable/configurable
- which interactions belong to the user panel vs the Mall shell
- which Red Dog or user objects need local overrides
- what "digital twin" actions need stable command hooks later

Focus:
- user page
- concierge
- Red Dog as the user's OpenClaw agent

### Worker D Audit: Guardrails / Product Logic

Audit:
- which controls must stay visible or locked
- which gesture remaps would break comprehension
- which defaults should be protected
- which scopes must not allow unsafe overrides
- which phrases explain customization simply

Focus:
- coherence
- guardrails
- user comprehension

## Audit Template For Every Surface

Each worker audit should answer the same questions:

1. Which current UI elements are hard-coded in placement?
2. Which of those should become SoftProto modules?
3. Which gestures/actions are currently hard-coded?
4. Which gestures should be remappable later?
5. Which gestures must remain fixed?
6. Which pieces of state need persistence?
7. Which controls are personal, global, or view-local?
8. What must not be broken during first integration?

## Anti-God-Module Rule

SoftProto must not become a giant "all UI logic here" blob.

Minimum separation:
- `schema/`
- `registry/`
- `store/`
- `commands/`
- `persistence/`
- `renderer/`

Likely later split:
- `surfaces/gateway`
- `surfaces/mall`
- `surfaces/user-panel`
- `surfaces/foundup`

Bad outcome:
- one 1400-line `softproto.js`

Good outcome:
- one core contract
- multiple surface adapters

## Recommended Phase Plan

### Phase 0
- this architecture note
- worker audits for A/B/C/D

### Phase 1
- isolated Svelte SoftProto spike in member shell
- 4 proof modules
- edit mode
- drag/reposition
- layout persistence
- gesture map persistence
- nested scoped interaction bindings
- inheritance / override placeholders
- AI command hooks against the same store

### Phase 2
- integrate selected Mall controls into SoftProto
- bind gesture engine through gesture schema instead of fixed handlers

### Phase 3
- integrate user panel / Red Dog controls
- expose voice/AI command translation into the command layer

### Phase 4
- integrate FoundUp-specific views
- support visual module types like image/video/live cube

### Phase 5
- optional gateway adoption
- optional server sync
- optional multi-device profile persistence

## Current Recommendation

Do this next:
- keep live gateway/member shell stable
- run A/B/C/D audits against their surfaces
- assign one spike owner for `softproto_svelte_spike_phase1`

Do not do this next:
- full Svelte rewrite of `public/`
- parallel SoftProto implementation by four workers
- global gesture refactor before the contract exists

## Short Version

SoftProto should become the shared UI operating layer for FoundUps.

Svelte is a good rendering engine for it.

But the first correct move is:
- architecture contract first
- audits second
- isolated spike third
- production adoption after that
