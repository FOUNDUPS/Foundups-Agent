# EDUIT ModLog

## 2026-10-26 — Standalone Story Time watch/play PWA deployment

WSP 00/15/22/50/84/97/99. Final 012 correction: app/codebase **Story Time**;
YouTube remains Us Story Time and publisher `us_story_time`. Final target
`storytime.eduit.org` supersedes prior hostnames. Preserve `eduit`/`kids_episodes`.
Latest direction delivers the first episode independently of full Mall work.

Video now precedes the existing idle game; explicit Play/Resume/Retry pause
video, watching/hidden/expand/back pause the game and pending sounds. Preserved
unlimited retry, practice and touch/mouse/native keyboard controls. Added scoped
expand/back, Replay, More stories coming, local lifecycle/completion contracts,
visible revision, /about/ and Shorts-owned /review/. Scene/rig/engine untouched.

Build reuses the existing Shorts renderer, creates immutable scene/media asset
URLs, origin-specific manifest/icons and exact-origin worker. Bounded current
and prior shell caches; network-only media/ranges; no forced update during play.
`--previous-build` carries one previous immutable media revision. No second
catalog/auth/renderer/backend, fake voice, cross-origin bridge or child telemetry.

Verified one authenticated Firebase project and hosting permissions; created
dedicated `storytime-eduit`, staged/tested then deployed revision
`a73aaf94b71cd2b1` to https://storytime-eduit.web.app/. Corrected inherited Firebase
config: module-local target binding and public directory are required by CLI.
Existing `foundupscom` live version remained unchanged. GoDaddy connector absent;
existing browser session authenticated. Prepared exact provider CNAME/certificate
TXT; save is awaiting GoDaddy identity verification, requested from 012. DNS/TLS
cutover is not claimed complete. [Receipt](docs/DEPLOYMENT_RECEIPT_20261026.json)
and [runbook](DEPLOYMENT.md) preserve before-state, pending records and rollback.

Validation: 21 JavaScript and 6 packaging tests pass; full Cairo/FFmpeg build
produces 15s 1080p H.264/AAC. Staging checked 24 URLs, 206 media ranges and headers.
Browser verified watch-with-idle-game, success, expand/back, phone layout, genuine
install prompt, clean manifest/installability and offline game reload/input.
Physical touch device, actual OS install and listening remain unverified.
Independent review found no remaining material source blocker.

Retrieval evaluation: exact Holo error `HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH`,
freshness UNKNOWN/index gap true. Direct current-main must-include owner docs
were narrowed/deduplicated; staleness labelled rather than treating historical
receipts as current. No reindex; maintenance stays with existing admitted owner.
Added missing requirements/test reproduction/verification artifacts. Qwen/Gemma
Python dependency tooling cannot establish authenticated DNS/hosting or browser
lifecycle behavior, so bounded manual execution and parallel review were used.

## 2026-10-26 — Story Time proof of concept

Implemented parent-facing landing, browser-local two-tap game, shared SVG movie export and existing-renderer reuse. Four state/scene tests pass. Independent review checked actual rendered collapse and provenance; floating claw removed. No tracking or child profiles. Deployment handoff records observed Patreon forwarding, local Codex GoDaddy access boundary and isolated Firebase targets. Production domains unchanged.

Final steering: collapse is instantaneous into uniform dark earth; the foot lifts leaving its side-profile outline. Audio sequence is stomp (10s), crunch (10.56s), squish (10.82s). No rain/sky or surviving-family claim. Browser verified both tap transitions and success; automated tests also cover timeout/retry and practice. Actual audio listening remains unverified.

012 requires URL-only delivery: simplified game heading and documented agent-owned deployment, with future catalog/PWA reuse assigned to existing Moshpit instead of a duplicate shell. No public deployment claimed.

WSP 97 architecture correction: EDUIT is the education-scoped sleeve of the shared Play FoundUps Mall, not a parallel platform. Retrieved Move2Japan product-selection precedent. Recorded educational projection/search boundaries and tentative chronology/branching/unlock ideas as unimplemented; retained single-story scope.

Recorded 012's watch → play → optional faster challenge and on-device parent-report proposal. Verified current fixed windows/practice against engine and controller. Distinguished story learning from reaction speed, within-player trends from unvalidated age rankings, and local play records from ordinary hosting traffic. Documentation only; no child tracking or adaptive runtime activated.

Clarified educational child FoundUps versus category labels; audited registry, projection and existing return owners. Recorded missing EDUIT registry entry and unresolved historical memory-game identity without personal health details. Added explicit Back to EDUIT link to current game; no catalog-scope enforcement or shared-Mall return claimed implemented.

Resolved historical game identity through GitHub branch search: Memory Horizon (`memory_horizon`) exists on docs/memory-horizon-wsp109-intake-20260920 with manifest, registry candidate, design packet and work orders. Updated EDUIT reference; no implementation/merge/deployment claim and no duplicate registration.

## 2026-10-25 — Editor-owned review surface

WSP 97/3/49/84: verified the existing Shorts editor and EDUIT build before
placing the review UI in Shorts assets and mounting it through EDUIT. Reuses
the shared scene and generated video; no second renderer/server/PWA or WRE
activation. Lexical owner retrieval: workspace overlay at 15c888ac0, freshness
UNKNOWN, index gap true. Results identified the existing editor; optional
roadmap/test README/memory artifacts absent. Exact files inspected directly.
The bounded static tool is simpler than deploying the loopback render server
as a public service; hosting remains a separate unverified gate.

## 2026-10-26 — Composite episode architecture and continuity

WSP 97/3/11/15/22/50/84: read EDUIT module and four historical audit documents,
shared Mall/gesture/fullscreen/Red Dog contracts, registry and production owners.
Captured one tile = video+game, direct watch/play entry, Next, reused gestures,
locale sound words, parent membership hypothesis and privacy boundaries. Added
INTERFACE/ROADMAP and inbound owner links; no new registry, shell or runtime.
Lexical Holo bundle at a6fed6dd8: UNKNOWN freshness, index gap true. Semantic
maintenance stays with the admitted owner; no Memex ingestion claimed. WSP00
V2 could not import torch; documented tracker fallback opened the gate without
a detector witness. This docs-only work does not require WRE activation.

012 clarified the landing is the first episode tile and premium creators can
make their own paired stories/games. Recorded separate library/creation access,
bounded compute quotas, private draft tiles, reviewed publication and episode
ratings. Existing Mall search found no episode-rating API; owner unresolved.
No payment tier, generation cap, rating system or public editor implemented.

012 corrected the canonical display name to Us Story Time. Updated current
EDUIT/docs/review/game labels; preserved IDs, publisher key and channel handle.
Historical proposed hostname needs deployment reconciliation; no DNS changed.
