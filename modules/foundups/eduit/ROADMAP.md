# EDUIT execution roadmap

Current direction: [Episode Mall architecture](docs/EPISODE_MALL_ARCHITECTURE.md).
This supersedes the earlier introduction-first landing proposal. It preserves
Kids Episodes' production priority and the existing renderer/Mall ownership.

## Resume without reconstructing the conversation

1. Verify current main and PR state. PR #2215 merged the local review/game/video
   foundation; it did not deploy domains or integrate the shared Mall.
2. Read README, architecture, INTERFACE, DEPLOYMENT, then shared Mall/Red Dog
   contracts and Kids Episodes roadmap. Reconcile any later changes first.
3. Confirm canonical EDUIT registry status; preserve `eduit`/`kids_episodes` IDs.
4. Use governed Holo retrieval; UNKNOWN freshness must stay UNKNOWN. No child
   data belongs in agent memory. Link source decisions instead of duplicating them.

## Current PoC priority — supersedes Mall-first ordering

012's latest deployment instruction targets `storytime.eduit.org`. The name in
the app/codebase is Story Time; Us Story Time remains the YouTube channel.

1. Compose and test the existing single episode: video above idle game, explicit
   Play, pause/retry/practice, expand/back, Replay and More stories coming.
2. Package bounded revisioned PWA assets for this separate origin; preserve the
   Shorts-owned creator review. No Mall shell, renderer or backend duplication.
3. Verify Firebase site ownership and GoDaddy session/zone/forwarding, preserve a
   sanitized before-state, deploy/test the provider preview, then deploy the same
   artifact live and apply only the provider-required Story Time DNS records.
4. Verify real HTTPS, media ranges, touch/mouse, installation, offline game and
   explicit update behavior. Record any pending certificate or device checks.

MPS: composition/packaging 3/5/5/4=17 P0; verified deployment 3/5/5/5=18 P0.
Hosting and DNS are dependency gates, not substitutes for a completed app.
Full Mall adapter, membership, ratings, locales and next episodes remain deferred.

## Later integration order — WSP 15 (historical Mall sequence)

C/I/D/Impact are complexity, importance, urgency and impact (1–5 each).
Scores are planning judgments, not runtime admission or billing authority.

| Order | Slice | Score | Exit evidence |
|---|---|---|---|
| 1 | Finish current episode sound/educational review | 3/5/5/4=17 P0 | Actual listening and independent output review |
| 2 | Shared-Mall EDUIT episode adapter, video above game, arrows/Next/return | 4/5/5/4=18 P0 | One paired tile; no autoplay game; lifecycle, scope and navigation regression checks |
| 3 | Deploy the same POC to verified EDUIT hosting | 3/5/4/4=16 P0 | Authenticated binding, TLS and phone URL playback/game proof |
| 4 | Next actual linked episode | 4/5/4/4=17 P0 | Connected story, reviewed media/activity; real Next destination |
| 5 | Spanish/Japanese sound-word variants | 3/4/3/4=14 P1 | Natural language review, aligned assets and fallback checks |
| 6 | Parent-only library/premium creation, quota and rating-owner integration | 4/3/2/4=13 P1 | Existing payment-owner audit, real entitlement/cancel/restore and failure tests |
| 7 | Memory Horizon, optional local reports, wider progression | 3/2/1/3=9 P3 | Separate reviewed scopes; no present activation |

Dependencies override score order: do not ship a payment plan before a useful
released library, or promise a public link before hosting is verified. Do not
build the entire education catalog to deliver the first episode.

Current connection/deployment evidence is recorded in [DEPLOYMENT](DEPLOYMENT.md) and its linked sanitized receipt. Historical workspace access observations are not current account state. Shared-Mall episode adapter, child/parent boundary,
locale variants and paid entitlement are implementation gaps, not access excuses.

## Creator expansion after first playable proof

Premium Create a story uses the existing editor/controller with bounded credit
reservations. Persist private draft tiles, pair video with a reviewed activity
template, review and publish into EDUIT's shared catalog. Confirm entitlement,
quota/retry settlement and rating/moderation owners before coding. Public
multi-user editing, creation pricing and automatic publication are not live.
