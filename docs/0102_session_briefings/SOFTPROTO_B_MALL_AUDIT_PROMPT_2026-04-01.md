# SoftProto Mall Audit Prompt

Purpose: audit the admitted Mall shell against the SoftProto contract before
the isolated SoftProto spike is mounted into `/member/`.

This is an audit-first prompt.

Do not implement SoftProto here.

## Read First

1. `WSP_framework/src/WSP_00_Zen_State_Attainment_Protocol.md`
2. `WSP_framework/src/WSP_102_FoundUps_Web_Design_Protocol.md`
3. `modules/foundups/docs/SOFTPROTO_FOUNDATION_ARCHITECTURE_2026-04-01.md`
4. `modules/foundups/docs/SOFTPROTO_ROLLOUT_PLAN_2026-04-01.md`
5. `public/member/index.html`
6. `public/member/foundup.html`
7. `public/member/js/gesture-engine.js`
8. `public/member/js/mall-planes.js`
9. `public/member/js/gesture-hints.js`
10. `public/member/css/member.css`
11. `public/member/css/mall-planes.css`
12. `public/member/tests/test_navigation_planes.py`

## Boundary Contract

This prompt is for audit work only.

Do:
- inspect the current Mall shell
- inspect current plane and gesture assumptions
- inspect current desktop parity behavior
- identify safest SoftProto spike mount points
- identify likely module-registry candidates

Do not:
- rewrite the Mall shell now
- replace current gesture logic
- invent a full global migration plan in code
- take ownership of the user panel content layer

## Objective

Determine how the current admitted Mall can host the first isolated SoftProto
spike safely, and identify which Mall controls and gesture domains should
eventually become schema-driven.

## Required Audit Questions

Answer explicitly:
1. What is the current Mall plane model?
2. Which interactions are currently hard-coded globally?
3. Which interactions are actually plane-local, module-local, or object-local?
4. Which current controls are strong phase-1 module-registry candidates?
5. Where is the safest mount point for an isolated Svelte SoftProto spike?
6. Which current gestures are most likely to conflict with edit mode?
7. How should mouse drag parity coexist with future SoftProto drag/edit mode?
8. What must not break during the first spike?

## Required Focus Areas

### 1. Mall As Default Plane

Audit:
- main Mall shell
- card browsing
- visual objects
- existing horizontal movement assumptions

Determine:
- which parts are shell structure
- which parts are future module surfaces

### 2. FoundUp View Plane

Audit:
- open/close behavior
- swipe left/right behavior
- swipe up behavior
- double-tap save behavior

Determine:
- which interactions are plane-level
- which are future object-level local domains

### 3. Hint System

Audit:
- existing hint/announcement structure
- dismissal behavior

Determine:
- whether hints should later become a module family inside SoftProto

### 4. Nested Interaction Readiness

Map likely future scopes for:
- Mall shell
- FoundUp card
- FoundUp visual object
- media or video object
- Red Dog trigger object

Determine which objects will clearly need local gesture domains later.

## Output Directory

Write artifacts under:
- `docs/audits/softproto/mall/`

## Required Output Artifacts

1. `AUDIT_REPORT.md`
   - current Mall system map
   - current gesture/plane ownership
   - spike integration risks

2. `MODULE_CANDIDATES.md`
   - likely module-registry candidates for the Mall

3. `INTERACTION_SCOPE_MAP.md`
   - global vs plane vs module vs object interactions

4. `MOUNT_STRATEGY.md`
   - safest isolated SoftProto spike mount strategy for `/member/`
   - explicit note on coexistence with `gesture-engine.js`

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
- shell map
- interaction-scope map
- mount strategy
- bounded spike-risk report
