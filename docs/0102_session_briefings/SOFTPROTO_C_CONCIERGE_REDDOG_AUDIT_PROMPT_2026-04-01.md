# SoftProto Concierge / Red Dog Audit Prompt

Purpose: audit the user panel / concierge / Red Dog surface against the
SoftProto contract before any configurable Red Dog layer is built.

This is an audit-first prompt.

Do not implement Red Dog logic here.

## Read First

1. `WSP_framework/src/WSP_00_Zen_State_Attainment_Protocol.md`
2. `WSP_framework/src/WSP_102_FoundUps_Web_Design_Protocol.md`
3. `modules/foundups/docs/SOFTPROTO_FOUNDATION_ARCHITECTURE_2026-04-01.md`
4. `modules/foundups/docs/SOFTPROTO_ROLLOUT_PLAN_2026-04-01.md`
5. `public/member/index.html`
6. `public/member/foundup.html`
7. `public/member/js/account-concierge.js`
8. `public/member/js/red-dog-concierge.js`
9. `public/member/RED_DOG_DIGITAL_TWIN_CONTRACT.md`
10. `public/member/tests/test_account_concierge.py`
11. `public/member/tests/test_red_dog_concierge.py`

## Boundary Contract

This prompt is for audit work only.

Do:
- inspect the current user-panel / concierge layer
- inspect Red Dog’s current surface role
- identify which elements should become movable/configurable first
- identify command targets the digital-twin layer will need

Do not:
- build a fake AI backend
- rewrite the entire account plane
- take ownership of Mall shell structure
- invent a second concierge concept

## Objective

Determine how the current account plane and Red Dog layer should evolve into a
SoftProto-compatible digital-twin surface.

## Product Truth

Red Dog is:
- the user's digital twin
- the user's own OpenClaw agent
- the primary intelligence surface inside the user panel

The concierge and user panel are one surface.

## Required Audit Questions

Answer explicitly:
1. Which current UI elements belong to the personal user-owned agent layer?
2. Which of those should become movable/configurable first?
3. Which controls must remain visible and stable?
4. Which interactions are user-panel-level vs object-level?
5. Which Red Dog controls need addressable command targets later?
6. Which parts of the surface are freemium-only vs future premium expansion?
7. Which gesture domains belong locally to Red Dog or its sub-objects?
8. What must not break during first SoftProto adoption?

## Required Focus Areas

### 1. User Identity Surface

Audit:
- avatar/profile affordance
- identity block
- options
- invites
- FoundUps shortcuts

Determine:
- which parts are stable structural controls
- which parts could become movable modules

### 2. Red Dog Surface

Audit:
- current Red Dog trigger(s)
- current help/concierge content
- current relationship to the user panel

Determine:
- what should be treated as the primary Red Dog module
- what should become submodules or objects later

### 3. Nested Interaction Readiness

Map likely scope levels for:
- account plane
- invites drawer
- avatar object
- Red Dog trigger
- Red Dog panel
- future mic/camera/search agent affordances

Determine which objects need local override behavior later.

### 4. Freemium -> Premium Expansion

Determine:
- what Red Dog can plausibly do in phase 1
- what later premium/operator behaviors would require stronger command hooks
- what should remain placeholders for now

## Output Directory

Write artifacts under:
- `docs/audits/softproto/concierge_reddog/`

## Required Output Artifacts

1. `AUDIT_REPORT.md`
   - current user-panel / Red Dog surface map
   - current gaps and risks

2. `MODULE_CANDIDATES.md`
   - personal agent-surface module candidates
   - likely first configurable elements

3. `COMMAND_SURFACE_MAP.md`
   - future command targets
   - likely address paths
   - phase-1 vs later-phase command needs

4. `INTERACTION_SCOPE_MAP.md`
   - plane/module/object breakdown for the user-panel / Red Dog surface

## Evidence Standard

For each claim:
- cite file path
- cite line or symbol when possible
- distinguish:
  - `proven`
  - `inferred`
  - `unknown`

## Deliverable Rule

Do not start coding first.

Start with:
- surface map
- command-surface map
- interaction-scope map
- bounded configuration candidates
