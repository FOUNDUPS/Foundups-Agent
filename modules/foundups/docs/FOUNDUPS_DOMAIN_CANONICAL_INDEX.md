# FoundUps Domain Canonical Index

**Status**: Active domain guidance
**Owner**: 0102
**Scope**: FoundUps domain truth, document classification, portfolio classification, documentation audit custody

---

## Purpose

Provide one current index for:
- what is canonical in `modules/foundups/`
- what is planning-only
- what is historical context
- what still needs audit before automation mutates it

This document is the current FoundUps domain navigation layer.
It does not replace core WSP documents.

---

## WSP Baseline

FoundUps domain work should be read through:
- `WSP 3`: domain placement and ownership
- `WSP 22`: README / ROADMAP / ModLog discipline
- `WSP 49`: module structure
- `WSP 65`: consolidation / separation when boundaries drift
- `WSP 102`: FoundUps web design and interface direction
- `WSP 77`: multi-agent audit coordination
- `WSP 97`: execution discipline for slices, audits, and corrections

Important:
`WSP 97` does **not** mean every document becomes a WSP protocol document.
It means document changes should follow:
- inspect
- compare against repo truth
- identify drift
- make the smallest valid correction
- preserve chain of custody

---

## Current WSP Audit Call

### Correct

The current FoundUps domain direction is correct in:
- `modules/foundups/ROADMAP.md`
- `modules/foundups/docs/FOUNDUP_EXFOLIATION_PROTOCOL.md`
- `modules/foundups/docs/PQN_SWARM_HUB_FOUNDUP_BRIEF.md`

These documents correctly establish:
- default internal PoC, external at Proto
- core vs product boundary
- FoundUp exfoliation readiness
- PQN Swarm Hub as internal-first

### Not Correct To Assume

Do not assume every older FoundUps document is current just because it references WSP.

A document can be WSP-adjacent and still be historical if it:
- is superseded by newer canonical planning docs
- describes interfaces not backed by current code
- reflects an older architecture framing
- mixes core-platform and product-FoundUp ownership

### Pending Audit

These root docs should be treated carefully until explicitly tightened:
- `modules/foundups/README.md`
  - the top "Current Canonical Planning References" block is current
  - the rest is mostly legacy platform framing / historical context
- `modules/foundups/INTERFACE.md`
  - contains planned platform surfaces that exceed current active domain guidance
  - should not be treated as the sole source of truth for current FoundUps scope

---

## How "Historical" Is Determined

Historical does **not** mean "non-WSP."

A FoundUps document is historical when one or more are true:
1. It has been superseded by a newer canonical planning or policy document.
2. It describes ownership or architecture that no longer matches repo truth.
3. It documents planned interfaces that are not the active execution surface.
4. It predates a later architect lock on boundary decisions.

A document is active when it:
1. matches current repo ownership and boundary decisions
2. is referenced by the canonical planning block
3. is still the current source for execution or classification decisions

Use four statuses:
- `canonical`
- `planning_reference`
- `pending_audit`
- `historical_context`

---

## Current Document Classification

### Canonical

- `modules/foundups/ROADMAP.md`
- `modules/foundups/docs/FOUNDUPS_MASTER_ARCHITECTURE.md`
  - **master document**: five-layer funnel (Discovery → Welcome → Community → Gate → Interior), entitlement tiers, repeating unit per FoundUp, document map
- `modules/foundups/docs/FOUNDUPS_DISCORD_BLUEPRINT.md`
  - embedded server layout (14 channels), role hierarchy, permission matrix, automation, onboarding flow, per-FoundUp category pattern
- `modules/foundups/docs/FOUNDUPS_ENTITLEMENT_TIERS.md`
  - formal tier definitions (Guest/Visitor/Community/Stakeholder/Operator), per-surface access matrix, agent participation rules, graceful denial
- `modules/foundups/docs/FOUNDUP_TEMPLATE.md`
  - repeatable 7-component checklist for adding a new FoundUp to the system
- `modules/foundups/docs/FOUNDUP_EXFOLIATION_PROTOCOL.md`
- `modules/foundups/docs/PQN_SWARM_HUB_FOUNDUP_BRIEF.md`
- `modules/foundups/docs/PFMALL_MALL_NAVIGATION_CONTRACT.md`
  - runtime contract for Mall gesture grammar, field scope APIs
- `modules/foundups/docs/PFMALL_VIDEO_MALL_RUNTIME_FOUNDATION_2026-04-02.md`
  - runtime foundation (phase 1 landed 2026-04-03)
- `modules/foundups/docs/PFMALL_MEDIA_DELIVERY_CONTRACT.md`
  - media path conventions, cache headers, embed allowlist, fallback rules (50 tests)
- `modules/foundups/docs/PFMALL_VIDEO_MALL_CATALOG_SCHEMA.md`
  - active runtime schema for `mall-video-catalog.json` (1,163 videos, 8 lanes, 25 tests)
- `modules/foundups/docs/PFMALL_FULLSCREEN_PLAYER_CONTRACT.md`
  - fullscreen video player and queue rail contract (entry, gestures, safe-area, no cross-FoundUp drift)

### Planning Reference

- `modules/foundups/docs/OCCAM_LAYERED_EXECUTION_PLAN.md`
- `modules/foundups/docs/CONTINUATION_RUNBOOK.md`
- `modules/foundups/docs/SOFTPROTO_FOUNDATION_ARCHITECTURE_2026-04-01.md`
  - current architecture lock for the future schema-driven UI operating layer
- `modules/foundups/docs/SOFTPROTO_ROLLOUT_PLAN_2026-04-01.md`
  - current rollout order, worker boundaries, and indexing requirements
- `modules/foundups/docs/PFMALL_EXTERNAL_FOUNDUP_ROUTE_CONTRACT.md`
  - current runtime boundary for Mall shell vs external FoundUp repos and
    in-scope route deployment
- `modules/foundups/docs/PFMALL_FOUNDUP_MANIFEST_SCHEMA.md`
  - future full FoundUp runtime manifest (CABR, signing, capabilities)
  - distinct from current Video Mall catalog
- `modules/foundups/docs/FOUNDUP_FEDERATION_MIGRATION_PLAN.md`
  - useful, but still draft and not proof that all migrations have happened
- submodule roadmaps:
  - `modules/foundups/agent_market/ROADMAP.md`
  - `modules/foundups/simulator/ROADMAP.md`
  - `modules/foundups/social_twin/ROADMAP.md`
  - `modules/foundups/agent/ROADMAP.md`

### Pending Audit

- `modules/foundups/README.md` beyond the canonical references block
- `modules/foundups/INTERFACE.md`

### Historical Context

Anything in the FoundUps domain that:
- is not in the canonical/planning lists above
- and is not the active README/ROADMAP/INTERFACE/ModLog for a live submodule
- should be treated as context until revalidated

---

## Current Portfolio Classification

### Core

These remain part of the core FoundUps platform substrate:
- `WSP_framework/`
- `modules/communication/moltbot_bridge/`
- `modules/infrastructure/wre_core/`
- `modules/infrastructure/database/`
- `modules/ai_intelligence/ai_overseer/`
- `holo_index/`
- `modules/foundups/agent_market/`
- `modules/foundups/simulator/`

Reason:
- they provide shared control plane, execution, retrieval, audit, registry, or economics primitives
- they are not single-product FoundUps

### Incubating FoundUps

- `modules/foundups/move2japan/`
  - internal FoundUp instance; not yet promoted by active domain docs to spin-out
- `modules/foundups/social_twin/`
  - explicitly `PoC architecture lock`
- `modules/foundups/pqn_portal/`
  - PoC -> Prototype -> MVP portal module still incubating in monorepo
- `PQN Swarm Hub`
  - canonical decision is internal PoC first
  - brief exists, module scaffold does not yet exist

### Proto-Ready Spin-Out Candidates

- `modules/foundups/gotjunk/`
  - product boundary is clear
  - Cloud Run deployment exists
  - roadmap is already in Prototype
  - active domain guidance says prepare for exfoliation now

### Already Externalized

- `AutoPost`
  - repo: `FOUNDUPS/autopost` (live on GitHub)
  - web: `autopost.foundups.com` (redirect)
  - status: PoC — Vite + React + TypeScript + Gemini API, camera capture-to-post
  - classification: `CANDIDATE_FOUNDUP` (HIGH priority) — both a FoundUp AND a tool
  - role: content pipeline for entire FOUNDUPS ecosystem (users post unlisted videos → YouTube → FoundUp routing → pfMALL display + social distribution)
  - part of: AI Automation service FoundUp
  - Discord: AUTOPOST category planned (#autopost-general doubles as user troubleshooting, monitored by 0102/OBAI)
  - docs: ROADMAP.md and ModLog.md added 2026-04-06
  - dual-remote normalization: `FOUNDUPS/autopost` is origin (confirmed), backup TBD
  - **monorepo footprint**: references only — no `modules/foundups/autopost/` directory
  - **boundary audit**: `docs/audits/kosei_ai_systems/AUTOPOST_VS_KOSEI_BOUNDARY_REPORT.md`

#### Externalized FoundUp Monorepo Rules

Externalized FoundUps (like AutoPost) carry only the following in the monorepo:

1. **Catalog taxonomy reference** — `PFMALL_LAUNCH_CATALOG_TAXONOMY.md` entry
2. **Canonical index entry** — this document
3. **Channel platform type** — `account-concierge.js` CHANNEL_PLATFORMS (if applicable)
4. **pfMALL catalog entry** — deferred until schema supports `external_app` source type

No product code, no business logic, no `modules/foundups/{name}/` directory.

### Future Candidate, Not Yet Classified As A FoundUp

- `Whack-a-Magot` / `Whack-a-Anything`
  - current repo placement is under `modules/gamification/`
  - architecturally it looks like a product-family candidate
  - but it should not be promoted into the FoundUps portfolio list until there is:
    - an explicit FoundUp brief
    - a module boundary
    - a PoC ownership decision

---

## Jobs And Queue Management

Do **not** create a new "Claw jobs module" for FoundUps right now.

Repo truth already has a task/control plane:
- `AgentDB.create_autonomous_task(...)`
- `OpenClawSupervisor._triage()`
- `modules/communication/moltbot_bridge/scripts/run_task.py`
- `modules/infrastructure/idle_automation/src/self_research_refresh.py`

That means new FoundUps audit or doc-cleanup work should enter the existing queue as bounded tasks, not a parallel jobs system.

Preferred pattern:
1. identify bounded audit/canonicalization task
2. create stable AgentDB task
3. let OpenClaw bounded maintenance or a dedicated audit slice consume it
4. require verification artifacts before docs are promoted

---

## Documentation Chain Of Custody

Use this process before automated documentation mutation:

### 1. Canon Audit

`0102` checks:
- current FoundUps domain docs
- relevant core WSPs
- current module surfaces

Output:
- what is canonical
- what is pending audit
- what is historical context

### 2. Inventory / Classification

Use `DocDAE` in dry-run mode to inventory candidate docs and classify obvious placement/cleanup opportunities.

Role:
- documentation inventory
- movement suggestions
- low-level hygiene support

Not role:
- final architectural authority

### 3. Drift / Oversight Validation

Use AI Overseer-owned validation where appropriate:
- `AIIntelligenceOverseer`
- `WSPFrameworkSentinel`

Role:
- audit report generation
- drift detection
- persistent machine-readable evidence

### 4. Secondary Verification

A second `0102` or verifier lane reviews:
- diff scope
- ownership correctness
- whether the mutation matches the canon audit

### 5. Mutation

Only after the first 4 steps:
- update canonical docs
- mark historical context explicitly
- log the slice in `ModLog.md`

This keeps documentation cleanup from becoming silent drift.

---

## Immediate Next Slice

If continuing this thread, the next proper documentation slice is:

- `foundups_domain_canonicalization`

Goal:
- tighten `modules/foundups/README.md`
- tighten `modules/foundups/INTERFACE.md`
- mark legacy sections explicitly instead of leaving them ambiguous
- create stable queue tasks for remaining FoundUps doc audit work
