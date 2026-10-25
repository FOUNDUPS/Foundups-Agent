# EDUIT — Education Using Information Technology

**FoundUp status:** local Story Time proof of concept implemented; domain deployment pending
**Product module:** Play EDUIT — adaptive learning through play  
**Historical educational vision:** eSingularity — learn anything, anytime, anywhere (LAAA)

EDUIT is the educational FoundUp and education-scoped sleeve of the existing Play FoundUps Mall. Its own identity does not imply a separate platform or duplicated shell. The existing `modules/foundups/esingularity/` application is a separate, live Fukui campaign and must not be modified by EDUIT work.

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

## Education Mall sleeve — operator direction

**Observed:** `public/member/INTERFACE.md` and `public/member/index.html` already
provide a registered product selection in the shared Mall shell. Move2Japan
reuses the tile field, controllers, gestures and product-scoped state. This is
the architectural precedent for EDUIT, not a second catalog application.

**Specified by 012:** EDUIT itself is discoverable as a FoundUp in the main Mall.
Inside EDUIT, discovery/search is restricted to educational content; unrelated
FoundUps results must not leak through global search, restored state or Red Dog
discovery. Some story records may be discoverable only within EDUIT's projection.
This projection boundary is distinct from authorization: hiding a public JSON
record is not access control. Reuse existing admission owners for protected data.

**Proposed, not implemented:** rows represent linked stories/epochs, horizontal
tiles their ordered playable episodes, and vertical travel moves through the
chronology. Divergent branches may follow a common ancestor. Completing a story
line could unlock the next level. Exact axes and progression rules remain open;
012 is exploring the idea, not authorizing a full progression system now.
Evolutionary ancestry and dates must be checked before becoming educational
claims; a fictional Little Shrew character is not proof of a specific ancestor.

**Current slice:** retain one Little Shrew game/video at Our Story Time and the
EDUIT introduction landing. Neither constitutes the integrated education Mall.
Do not build a duplicate PWA, generic catalog, learner account or unlock service
for this proof of concept. Future work should add a bounded EDUIT product adapter
to the existing shell, with tests that out-of-scope catalog items cannot appear.

**WSP 97 closure:** exact owner/adjacent product interfaces retrieved; existing
product reuse chosen over a new shell. Documentation/design change only for the
Mall sleeve. No production routing, PWA integration or unlock behavior claimed.

## Watch, play, progress — local parent report proposal

**012 proposal, not implemented:** a child watches the episode, plays its
corresponding game, then may repeat an optional faster challenge. The learning
objective is tied to the story: notice the cue, choose the appropriate action,
and complete the sequence. Speed is a separate challenge, not proof of learning.
Successful repetitions could gradually shorten the response window, within
reviewed limits; misses should ease the challenge or offer untimed practice.
Story access should not depend on reaction speed alone. Keep practice and an
accessible progression path available. Exact difficulty rules remain undecided.

**Observed now:** `public/eduit/storytime/engine.mjs` has two fixed four-second
cue windows and untimed practice. `game.js` pauses on hidden pages. There is no
adaptive speed, persistent progress store or parent report in this prototype.

**Proposed parent view:** describe a learning/progress curve, without assuming
it is a mathematical parabola. Show completed sequences, attempts, success rate,
challenge level and response-time trends compared with that child's own earlier
play. Separate first attempts from practiced attempts and compare like-for-like
game versions, difficulty, input method and device conditions. Show the number
of observations and insufficient-data states; do not infer a trend from one try.
Input timing includes rendering, device latency, anticipation and familiarity.
Use an actual monotonic timing measurement for future reporting, not the current
animation clock whose per-frame increment is capped. Paused/hidden attempts must
not produce misleading reaction-time results.

**Exploratory goal:** 012 is interested in whether unusual strengths, including
fast responses, might become visible to parents. No age percentile, 'gifted',
IQ, diagnostic or innate-ability label is justified by this game. Age-relative
comparisons would require separate suitable reference data and validation;
they are not part of this proof of concept. Do not gather birthdays or build a
cross-child dataset to support this speculative feature.

**Proposed data boundary:** optional progress remains in browser/device-local
storage, processed locally for the parent's view. No server upload, cross-family
comparison, advertising use, telemetry payload, agent memory ingestion or model
training from children's play. No account or identifying child details required.
Parent controls should enable/disable recording and clear all recorded progress;
any export must be an explicit parent action, never an automatic sync. Local
browser storage may be cleared and is shared by users of that browser profile;
it is not guaranteed backup or a private per-child identity boundary. Explain
that limitation and separate optional local player slots only if needed later.
The no-upload claim concerns play records, not ordinary hosting requests or an
external YouTube visit. Verify network behavior before making privacy claims.

**Integration/scope:** use EDUIT's adapter within the existing Mall and reuse its
appropriate storage infrastructure after checking ownership and isolation. Do
not mix child progress with account data or the global Mall's browsing history.
This turn preserves the design only: no tracker, database, speed ladder or
report UI is activated. A future bounded implementation needs synthetic tests
for timing, difficulty bounds, pause/resume, deletion and no-network leakage.
