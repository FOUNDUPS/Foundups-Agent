# EDUIT — Education Using Information Technology

**FoundUp status:** local Story Time proof of concept implemented; domain deployment pending
**Product module:** Play EDUIT — adaptive learning through play  
**Historical educational vision:** eSingularity — learn anything, anytime, anywhere (LAAA)

EDUIT is an independent educational FoundUp. The existing `modules/foundups/esingularity/` application is a separate, live Fukui campaign and must not be modified by EDUIT work.

## Purpose and history

The 2007 EDUIT mission proposed freely accessible online education. The 2007 eSingularity initiative described **The Tool + The Content + The Experience**; the 2009 book and 2010 Malaysian prize proposal described adaptive games, learning-object assessment and identifying underserved talent. The 2023 EDUIT AI Teaching Touch Tablet and Baby0 discussions explored infant multilingual learning and explicitly proposed starting with an app. In the project's operator interpretation, Baby0 is an early conceptual ancestor of the OBAI/0102/Red Dog lineage; this is not a verified claim of uninterrupted software or model identity since 2001–2003. These are **historical proposals**, not evidence of measured outcomes.

[Historical lineage and primary sources](../../../docs/audits/pfmall_eduit/EDUIT_DISCOVERY_HISTORICAL_LINEAGE_2026-10-08.md)

## MVP: Play EDUIT

A browser-first, device-independent adaptive learning game. The initial product measures **game-specific learning progress**, not intelligence, diagnosis, or genius. Opportunity referrals and any profiling of minors require independent validation, parental/guardian consent, and human review. Do not collect child-identifying data for the initial synthetic demonstration.

## WSP 104 — Route namespace and tenant isolation

- Proposed `foundup_id`: `eduit` (requires registry reconciliation)
- Declared landing route: `/f/eduit`
- Declared app mount: `/f/eduit/app`
- Data namespace: `eduit`; no cross-tenant access to eSingularity or other FoundUps
- **Runtime:** local static proof of concept at `public/eduit`; no WSP 104 tenant route activation claimed

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

## Autonomous operator continuity

0102 / Red Dog owns the next small verified implementation slices, WSP 97 closure and merge-to-main receipts. README and other module documentation are machine-operational context, not required reading for 012. Keep decisions, evidence, current state, and next steps inside the repository. No background execution is implied by this instruction.

## Next implementation slice

1. Verify current FoundUp registry and schema; do not create a duplicate ID or public route.
2. Define a deterministic adaptive-difficulty game and synthetic tests.
3. Review accessibility, age-appropriate design, data minimization and consent.
4. Only then consider a public prototype. No DAO-driven model changes or child-data sharing in the MVP.

**Evidence status:** local landing, shared story/video scene and two-tap game implemented and tested. No validation study, child profiles, public deployment, autonomous worker or token. Registry production status remains unchanged.

## Linked educational media

[Kids Episodes](../kids_episodes/README.md) (`kids_episodes`) is the related story-to-linked-episodes FoundUp using existing YouTube production components. The local Story Time game now shares its scene with the episode video export. No autonomous story-production runtime is claimed. EDUIT retains its existing ID and independent scope.

## Story Time proof of concept

Source: `public/eduit/`. Read [deployment and local Codex handoff](DEPLOYMENT.md). Canonical planned domains are `eduit.org`, `ourstorytime.eduit.org`, and the redirect `eduit.foundups.com`. Kids Episodes remains `kids_episodes`; EDUIT remains `eduit`. No new FoundUp registration.
