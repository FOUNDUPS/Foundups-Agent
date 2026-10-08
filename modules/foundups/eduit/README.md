# EDUIT — Education Using Information Technology

**FoundUp status:** SPECIFIED_NOT_IMPLEMENTED  
**Product module:** EDUIT Discovery — adaptive learning through play  
**Historical educational vision:** eSingularity — learn anything, anytime, anywhere (LAAA)

EDUIT is an independent educational FoundUp. The existing `modules/foundups/esingularity/` application is a separate, live Fukui campaign and must not be modified by EDUIT work.

## Purpose and history

The 2007 EDUIT mission proposed freely accessible online education. The 2007 eSingularity initiative described **The Tool + The Content + The Experience**; the 2009 book and 2010 Malaysian prize proposal described adaptive games, learning-object assessment and identifying underserved talent. The 2023 EDUIT AI Teaching Touch Tablet and Baby0 discussions explored infant multilingual learning and explicitly proposed starting with an app. These are **historical proposals**, not evidence of measured outcomes.

[Historical lineage and primary sources](../../../docs/audits/pfmall_eduit/EDUIT_DISCOVERY_HISTORICAL_LINEAGE_2026-10-08.md)

## MVP: EDUIT Discovery

A browser-first, device-independent adaptive learning game. The initial product measures **game-specific learning progress**, not intelligence, diagnosis, or genius. Opportunity referrals and any profiling of minors require independent validation, parental/guardian consent, and human review. Do not collect child-identifying data for the initial synthetic demonstration.

## WSP 104 — Route namespace and tenant isolation

- Proposed `foundup_id`: `eduit` (requires registry reconciliation)
- Declared landing route: `/f/eduit`
- Declared app mount: `/f/eduit/app`
- Data namespace: `eduit`; no cross-tenant access to eSingularity or other FoundUps
- **Runtime:** planned, not implemented; no route activation claimed

## AI hooks — contract only

| Hook | Status | Meaning |
|---|---|---|
| `get_status` | Planned | Report bounded operational status |
| `get_context` | Planned | Return consent-scoped game context |
| `navigate` | Planned | Navigate within EDUIT tenant routes |
| `launch_capability` | Planned | Launch a reviewed educational game |
| Shell handoff / return | Planned | Return safely to pfMALL |

## WSP 91 — DAEmon observability

No autonomous production worker exists. Planned outputs: health status, last action, error classification, recommended next action, queue/work state (N/A until worker exists), and telemetry under the `eduit` namespace. Never emit child identifiers or raw learner interaction data into telemetry.

## Next implementation slice

1. Verify current FoundUp registry and schema; do not create a duplicate ID or public route.
2. Define a deterministic adaptive-difficulty game and synthetic tests.
3. Review accessibility, age-appropriate design, data minimization and consent.
4. Only then consider a public prototype. No DAO-driven model changes or child-data sharing in the MVP.

**Evidence status:** documentation scaffold only. No runtime, validation study, game engine, child profiles, deployment, or token.
