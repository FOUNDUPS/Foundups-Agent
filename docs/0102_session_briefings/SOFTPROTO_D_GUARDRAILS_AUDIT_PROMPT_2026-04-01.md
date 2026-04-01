# SoftProto Guardrails Audit Prompt

Purpose: audit the system guardrails required before SoftProto customization can
be safely introduced across FoundUps surfaces.

This is an audit-first prompt.

Do not implement runtime changes here.

## Read First

1. `WSP_framework/src/WSP_00_Zen_State_Attainment_Protocol.md`
2. `WSP_framework/src/WSP_102_FoundUps_Web_Design_Protocol.md`
3. `modules/foundups/docs/SOFTPROTO_FOUNDATION_ARCHITECTURE_2026-04-01.md`
4. `modules/foundups/docs/SOFTPROTO_ROLLOUT_PLAN_2026-04-01.md`
5. `public/index.html`
6. `public/member/index.html`
7. `public/member/foundup.html`
8. `public/member/js/gesture-engine.js`
9. `public/member/js/mall-planes.js`
10. `public/member/js/account-concierge.js`
11. `public/member/js/red-dog-concierge.js`
12. any current tests that exercise these surfaces

## Boundary Contract

This prompt is for guardrail analysis only.

Do:
- inspect failure modes
- inspect gesture collisions
- inspect edit-mode conflict risks
- inspect persistence corruption risks
- inspect AI/user command conflict risks
- define bounded permissions and override rules

Do not:
- implement SoftProto
- rewrite gesture logic directly
- invent runtime policy without repo evidence

## Objective

Determine the minimum safety/guardrail contract that must exist before
SoftProto begins changing layout, gesture mappings, and object behavior.

## Required Audit Questions

Answer explicitly:
1. Which interactions must never become remappable?
2. Which interactions can become remappable only within bounded scopes?
3. Which controls must always remain visible or recoverable?
4. How should normal app actions be suppressed during edit mode?
5. Which drag/gesture collisions are most likely in the current shell?
6. What should happen when persisted schema is corrupt or outdated?
7. What command targets should AI never be allowed to hide or disable?
8. Which scope overrides would be unsafe or confusing?

## Required Focus Areas

### 1. Edit Mode Safety

Audit:
- where drag would conflict with normal click/tap behavior
- where swipe gestures would conflict with normal shell navigation

Determine:
- which actions must be suppressed in edit mode
- which fallback/escape actions must always remain available

### 2. Persistence Safety

Audit:
- what preference corruption would look like
- how the system should recover

Determine:
- minimum reset path
- minimum versioning requirements
- minimum protected defaults

### 3. Scoped Interaction Safety

Using the nested interaction model, determine:
- which scopes must support overrides
- which scopes should inherit only
- which scopes should not allow local override

### 4. AI Command Guardrails

Determine:
- which command paths should be writable by future AI
- which should be read-only
- which should be protected or approval-gated

## Output Directory

Write artifacts under:
- `docs/audits/softproto/guardrails/`

## Required Output Artifacts

1. `GUARDRAILS_REPORT.md`
   - core safety contract
   - protected controls
   - non-remappable actions

2. `OVERRIDE_MATRIX.md`
   - allowed vs disallowed overrides by scope

3. `FAILURE_MODES.md`
   - edit-mode conflicts
   - persistence corruption cases
   - command-path conflict cases

4. `RESET_AND_RECOVERY.md`
   - minimum required recovery behavior
   - safe fallback defaults

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
- guardrail map
- override matrix
- failure-mode analysis
- reset/recovery contract
