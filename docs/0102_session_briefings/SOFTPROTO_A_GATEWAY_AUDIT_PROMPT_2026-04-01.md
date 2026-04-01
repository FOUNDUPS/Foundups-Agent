# SoftProto Gateway Audit Prompt

Purpose: audit the public gateway surface against the SoftProto contract before
any SoftProto-aware gateway implementation begins.

This is an audit-first prompt.

Do not implement the gateway here.

## Read First

1. `WSP_framework/src/WSP_00_Zen_State_Attainment_Protocol.md`
2. `WSP_framework/src/WSP_102_FoundUps_Web_Design_Protocol.md`
3. `modules/foundups/docs/SOFTPROTO_FOUNDATION_ARCHITECTURE_2026-04-01.md`
4. `modules/foundups/docs/SOFTPROTO_ROLLOUT_PLAN_2026-04-01.md`
5. `public/index.html`
6. `public/alpha-access.html`
7. `public/legal/terms-of-access.html`
8. `public/legal/alpha-nda.html`
9. `public/manifest.json`

## Boundary Contract

This prompt is for audit work only.

Do:
- inspect the current gateway
- identify hard-coded UI placement
- identify current gesture or interaction assumptions
- identify legal-gate constraints that must remain fixed
- identify future SoftProto mount opportunities

Do not:
- rewrite `public/index.html`
- migrate the gateway into Svelte
- relax the legal gate
- build customization UI here
- invent a second auth flow

## Objective

Determine what parts of the public gateway can later become SoftProto-aware and
what parts must remain fixed or tightly constrained.

## Required Audit Questions

Answer explicitly:
1. Which gateway elements are hard-coded in placement?
2. Which gateway elements are good future SoftProto module candidates?
3. Which gateway elements should remain fixed for legal/comprehension reasons?
4. Which gestures or interactions are currently assumed globally?
5. Which of those interactions could be remappable later?
6. Which interactions must never be remapped on the gateway?
7. Where is the safest future mount point for a SoftProto-aware layer?
8. What current behaviors must not break during future adoption?

## Required Focus Areas

### 1. Hero / Entry Layer

Audit:
- logo
- ENTER
- ROC-first copy
- any helper or preview controls

Determine:
- what could become movable later
- what should remain fixed to preserve clarity

### 2. Terms / Access Gate

Audit:
- disclaimer modal
- embedded auth flow
- legal links
- decline path

Determine:
- which controls must remain fixed
- which gestures/remaps would weaken comprehension or compliance

### 3. Section Structure

Audit:
- snap sections
- ordering assumptions
- current section-specific interactions

Determine:
- where future schema-driven layout could safely exist
- where structure should remain protected

### 4. Nested Interaction Readiness

Using the SoftProto nested interaction model, identify likely future scopes:
- app
- plane
- module
- submodule
- object

Determine whether the gateway already contains any object-level interactions
that would need local gesture domains later.

## Output Directory

Write artifacts under:
- `docs/audits/softproto/gateway/`

## Required Output Artifacts

1. `AUDIT_REPORT.md`
   - current system map
   - fixed vs future-configurable surfaces
   - integration risks

2. `MODULE_CANDIDATES.md`
   - future gateway module candidates
   - why each is movable or not

3. `INTERACTION_SCOPE_MAP.md`
   - current interactions
   - future scope assignments
   - locked vs remappable interactions

4. `MOUNT_STRATEGY.md`
   - safest future SoftProto-aware gateway mount strategy
   - explicit recommendation whether gateway should wait until after member-shell proof

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
- audit
- fixed-vs-configurable map
- interaction-scope map
- bounded future mount recommendation
