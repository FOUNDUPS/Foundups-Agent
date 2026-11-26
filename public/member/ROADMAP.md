# Member Area Roadmap

## 2026-11-23 — Clean video gestures and local DAEmon candidate

**IMPLEMENTED_CANDIDATE.** The [interaction contract](INTERFACE.md#2026-11-23--clean-video-gestures-and-local-daemon-candidate)
specifies app-only chrome removal, mode-specific configurable right-swipes,
full-height external grips and opt-in bounded local activity. Shared player,
queue and preference owners are reused; preview diagnostics are nested.
Exact-source tests, independent review and physical iPhone/PWA evidence remain
required. Existing source62/livev25 previews are retained as rollback references.

## 2026-11-22 — Floating controls and camera follow-through

**IMPLEMENTED_PENDING_VERIFICATION.** The existing #2439 owner supplies bounded
drag/frame gestures, a video-height restore rail, independent video preferences,
accessible actions in the shared menu and the canonical AutoPost camera handoff.
The dock dog stays in context when conversation is unavailable. Preserve the
ordinary account/product controller and native provider controls. Qualify both
browser engines, shared regressions and exact-source preview before phone
acceptance. The [HPC acceptance record](../../modules/foundups/hpc/ROADMAP.md#2026-11-22--floating-controls-and-camera-continuation)
and [incident](../../modules/foundups/pfmall/MEDIA_PLAYBACK_INCIDENT_HPC.md)
retain the backend, browser-model, speech and physical-device blockers.

## 2026-11-22 - selective shared return and tile-tap continuation

The existing #2439 owner selectively adopts the private review's reversible
Mall return and confirmed Floating/WikiTube/app Full Video tile-tap choices.
Use one shared player, state/history owner and bottom dock. Return pauses and
retains a ready controllable session; Forward remains paused, deliberate
selection may play, and final Close disposes playback. Field-owned pagination
survives closing/reopening a selected lane; late pages cannot restart playback.

The guest Fractal prototype, new lenses/face loans and unresolved gesture
defaults are excluded. Frame destination is independent of tile-tap preference;
no legacy field seeds the three held gesture choices. Existing AI pilot and
fail-closed contribution/admission boundaries are preserved. See the current
[HPC reconciliation](../../modules/foundups/hpc/ROADMAP.md) and
[test log](tests/TestModLog.md) for source-bound controlled evidence. Conflict,
hosted review, deployment and physical/real-provider gates remain open.

**Module**: `public/member/`
**Approach**: Occam's Layered (build/test one layer at a time)

## Shared Search Dock and player behavior — 2026-11-21

**PFDOCK-20261121 / CHANGES_POC_ACCEPTANCE / SPECIFIED_NOT_IMPLEMENTED.**
This shell must supply the same floating Search Dock for the public Mall,
admitted views, every FoundUp and fractal navigation. HPC is the first
qualification surface. The authoritative acceptance matrix is
[navigation contract section 14](../../modules/foundups/docs/PFMALL_MALL_NAVIGATION_CONTRACT.md#14-shared-search-dock-and-video-preferences);
the [shared roadmap](../../modules/foundups/pfmall/ROADMAP.md#shared-search-dock-and-video-preferences--2026-11-21)
owns delivery order and [HPC H1H](../../modules/foundups/hpc/ROADMAP.md#h1h--shared-dock-and-configurable-video-behavior--2026-11-21)
owns the first device acceptance. This replaces HPC-only scope and fixed
video-gesture assumptions where they conflict, without changing runtime here.

- `mall-video-projection.js`: one active, thumb-accessible dock; the `+` menu
  lists AI choices first, then a visible top-level **Video** entry, then
  functional current-scope actions. Keep contribution `+` separate, including
  its existing permission checks. Native fullscreen remains provider-owned.
- `mall-state-restore.js` and `mall-tile-field.js`: share validated preferences
  and tile selection across skins. Tap destinations are Floating, WikiTube and
  Fullscreen; **Floating is the confirmed default**. Migrate existing stored
  options without claiming cross-origin synchronization. Signed-out local
  settings confer no contribution or execution authority.
- `mall-video-player.js`: separate pinch-out, pinch-in return and video-swipe-up
  return choices; allow direct Fullscreen expansion. Pinch-in from Fullscreen
  and video swipe-up each choose WikiTube or Mall tiles, independently. Their
  default values are not finalized. Preserve grid/queue/modal gesture contexts.
  Rotate Floating into landscape Fullscreen and back to Floating, respecting
  intervening deliberate mode/navigation changes. Rotation lock is an open
  design idea. Preserve same-player state, right tuck/restore and compact
  recovery; fully hidden YouTube playback pauses.
- Existing AI owner: lightweight startup and a real supported-model list only
  after qualification, with download size, explicit selection/confirmation,
  Cancel/Unload and truthful unavailable states. The v26 41-byte WASM fixture
  tests compatibility only; it does not implement model selection or inference.

Reconcile current main with the existing PR #2439 implementation lane; extend
its partial Video Options and shared dock instead of replacing its work.
Documentation allocation is C2, I4, D4, Impact4 = **14/P1**; runtime and device
costs require separate owner scoring. Reuse existing browser/VM fixtures for
each destination, migration, intent-preserving rotation, one dock/player,
keyboard/safe areas and Back. Qualify HPC, Play, another FoundUp/fractal path,
non-video products and guest/member boundaries. Physical Safari/PWA and desktop
acceptance, merge and release remain separate from this documentation change.

## Fractal projection sequence — 2026-11-19

**Specified; no implementation in this documentation slice.** Follow the
[Mall roadmap](../../modules/foundups/pfmall/ROADMAP.md#fractal-tile-graph-and-agent-work-navigation):
census first, with up to three eligible independent auditor packets in parallel
(discovery, dependency, duplicate review or integration). Immature and unwired
candidates remain discoverable with explicit evidence gaps. Keep functionality,
integration, venture maturity and WSP_15 work priority separate.

Sprint 2 reuses the reported local graph/projector/viewer once its pinned
artifacts are recovered, for a Tools → Benchmark walkthrough and a separately
evidenced builder-to-component path. One component
ID can appear under several views. Retain graph and source revisions, caller,
lens and selection; qualify Back, direct entry, stale/restricted evidence and
public/architect boundaries under the [navigation contract](../../modules/foundups/docs/PFMALL_MALL_NAVIGATION_CONTRACT.md#13-fractal-work-navigation).
Record rendering, observed tool execution and live playback separately. When a
render needs an unapproved code change, retain the query/path and mark visual
acceptance pending.

Historical lifecycle and economic reconciliation remain separate owners in
Sprint 3; evidence closure follows in Sprint 4. This documentation update
reconciles the existing owners now. The [documentation audit](https://github.com/FOUNDUPS/Foundups-Agent/blob/dc7c34aa6444aa1fc37de1217f99f0e75e4d2f0b/docs/audits/architecture/PFMALL_FRACTAL_DOCUMENTATION_AUDIT_20261119.md)
records inspected main, reported local `121c50666` evidence and unresolved gaps.
This plan creates no new graph engine, model route or co-build write authority.

The dated v26 subset below records implementation at `2a65e7983acb489084cecf1229fcfd582f68f19b`;
it does not close the broader shared contract above. Requalify the reconciled
head separately; physical Safari/PWA and publication remain distinct.

## v26 phone subset and Browse AI compatibility pilot - 2026-11-21

Current work starts from `9b85e9cbb874b3720e453d3e3d3a3974dca53504`.
v25 remains the frozen comparison; its tests/artifact do not qualify the changed
v26 shell. Build label, versioned assets and member worker request v26 in source.
Combined exact-head/browser tests, deployed parity and physical acceptance
remain pending in this entry.

The [projection/dock owner](js/mall-video-projection.js) puts Video Options in
the leading `+`: next-clip autoplay while visible, the app frame's WikiTube or
Full Video destination, collapse destination and selected-player reveal.
Native YouTube taps/fullscreen remain provider-owned. The same menu lazily
imports [Browse AI](js/mall-browser-ai-pilot.js); trailing `+` opens contribution
review. Preserve one visible bottom dock and the existing player/state owners.
Compact Play chrome and the Hasan-banner link are distinct from Play Mall
return navigation; qualify layout, focus, scroll and return behavior together.

Browse AI has **no approved model or AI runtime**. Its sole pilot is
[`pilot-add.wasm`](wasm/pilot-add.wasm), exactly 41 bytes, SHA-256
`f61fd62f57c41269c3c23f360eeaf1090b1db9c38651106674d48bc65dba88ba`.
It computes `add(2, 40) = 42`, with no imports or memory. Explicit Review/Confirm
precedes bounded same-origin fetching and size/hash verification before execution.
Cancellation, timeout and unsupported states are explicit; no artifact/model
preload, reload or cloud fallback. The [component VM](tests/mall_browser_ai_pilot_vm.mjs)
covers controlled local behavior. Browser-reported standalone mode and detected
WebGPU APIs do not qualify a physical device or model; WebGPU is UNQUALIFIED.

Graph `22374b` is not integrated. Depth-specific access and writer actions stay
unavailable/fail closed pending backend membership/editor checks; browser
state, sign-in or an invite result grants no writer authority. Contribution
review does not publish. The [shared roadmap](../../modules/foundups/pfmall/ROADMAP.md)
owns the proposed paid-service phase. Next: combined source/CI, isolated
HTTPS/worker parity, then real YouTube time advancement and physical iPhone
Safari plus installed PWA on Wi-Fi/cellular, retaining v25 for comparison.

## Build v22 Brand Chrome, Canonical Catalog, OSP Tile Flip & Phone Patch-Load — 2026-11-16

- Updated top-left `.mall-brand-cluster` to `/logo-foundups.svg` + FoundUPS LinkedIn link while keeping Red Dog in the bottom-right anchor; consolidated redundant `linkedin_*` pseudo-tiles into header/About/`linkedin_url` links, reconciled `voteballots`, `trade`, `magadoom_001`, and `kids_episodes` from `foundup_registry.json`, and grounded `foundups.com` `#foundupTicker` in real catalog count.
- Added WSP 109 `Outcome · Solution · Pain` card backs with desktop hover-hold (`650ms`), mobile press-and-hold (`450ms`), and keyboard/button flip controls, plus phone viewport DOM patch-loading (`PHONE_PATCH_BATCH = 9`) and `IntersectionObserver` deferred poster hydration under `Build v22` / `pfmall-member-v22`.

## Build v21 Open Mall Landing (`play.foundups.com`) & Member Portal Gate (`foundups.com`) — 2026-11-16

- Configured `play.foundups.com` (`dedicatedHosts.get('play.foundups.com') === 'mall'`) as the open guest p.fMALL discovery landing for all catalog FoundUps without Clerk SDK or Firestore admission reads, mirroring `hpc.foundups.com` across the full Mall catalog while supporting `?foundup=hpc` and `?foundup=move2japan` public projections.
- Enforced membership gating across all FoundUp entry paths from `play.foundups.com` (`mall-tile-field.js` `navigateToFoundUp`, `mall-video-player.js` `Enter FoundUp`, `mall-planes.js` quick-view `Enter FoundUp · Member Portal ↗`, `foundup.html`, and `/f/{id}/app`) via `https://foundups.com/member/?enter={foundup_id}` + `pfmall_product_return_v1` single-use 15-minute return continuity into `/member/foundup.html?id={foundup_id}` after Clerk + invite + `@username` admission under `Build v21` / `pfmall-member-v21`.

## Build v20 Floating Player, Tuck/Restore & WikiTube Gestures — 2026-11-16

- Replaced row-replacing `.mall-inline-player-slot` playback with a single top-anchored floating player (`#videoPlayerFullscreen.video-player-floating`) permanently mounted in `document.body`, keeping the grid scrolling smoothly underneath while preserving `<iframe>` / `<video>`, playback time, audio, and queue across Floating, Tucked, WikiTube, and Desktop Theater modes.
- Added swipe-right edge tuck + `.video-player-tuck-handle` tap/swipe-left restore, disambiguated 2-finger pinch-in / pinch-out transitions with accessible button alternatives (`Tuck player`, `Restore player`, `Open WikiTube`, `Floating player`, `Close player` / `Back`), `375px` phone tile width `>= 120px` RMF compliance, warm `loadVideoById` YouTube reuse, truthful `Play video` fallback when blocked, and bounded WikiTube sequential error recovery (`MAX_CONSECUTIVE_AUTO_SKIPS = 5`, `queueHalted = true`) under `Build v20` / `pfmall-member-v20`. Physical iPhone preview verification and production Hosting promotion remain separate gates.

## Build v19 Mall Truth & Continuity — 2026-11-16

- Reconciled `mall-video-catalog.json` (16 entries) with `foundup_registry.json` and `foundup_manifest.json` contracts: added `esingularity_001`, aligned `holoindex_prod_01` (`F3_INFRA` / `conditional` / `infrastructure`), `gotjunk_001` (`012` creator + `external_url`), and `autopost` (`external_url`), and normalized video `duration_seconds` and `YYYY-MM-DDTHH:MM:SSZ` timestamps.
- Unified `internal_app` (`Open App`) CTA parity across `index.html`, `foundup.html`, and `mall-planes.js`.
- Closed Phase 3 continuity gaps under `Build v19` / `pfmall-member-v19`: ordinary `/member/` `hpc` tile navigation to `/member/?foundup=hpc`, desktop inline `queueQuery` inheritance in `openDesktopVideo`, and reload-safe `activeVideo` (`{ foundupId, videoId, queueQuery }`) persistence in `pfmall_mall_state_v1` without altering HPC's tab-local `sessionStorage` boundary.

## FX1 Public Directory — 2026-10-25

- Implemented locally: homepage FX link to the existing `/f/` public directory,
  honest project/ticker framing and declared-symbol search using the existing
  filter. Existing routes and member admission remain the owners.
- Verified with existing route/gateway test files; see
  [tests/TestModLog.md](tests/TestModLog.md). Deployment, actual browser layout,
  repository claims and chain/market readiness remain separate gates.

## Move2Japan Product Integration (2026-10-18)

The registered Move2Japan entry now targets the actual member page with houses
selected. The shared field owns geographic navigation and detail planes; Red Dog,
identity, account return, view persistence and the service worker retain their
existing Mall owners. New responsive category browsing from the parallel Mall
change remains the ordinary Mall default. House controls cannot mutate its video
scope or overwrite its saved position.

| Stage | Acceptance gate | Current implementation |
| --- | --- | --- |
| POC | People can search sourced houses | Eight dated Fukui observations, five area rows, combined location/land/price filters in the actual Mall |
| Prototype | Brokers/owners publish through the shared account system | Pending: authority verification, listing lifecycle, consent/media rights, review and a durable provider |
| MVP | Actual paying customers receive the promised benefit | Pending: shared server-side entitlement checks, settled payment evidence, delivery, expiry/refund handling |

Account admission is not a housing subscription or publishing permission. No paid
inventory, subscription issuer or token issuance is introduced. The module's
[roadmap](../../modules/foundups/move2japan/ROADMAP.md) owns publisher and membership
work. Repository merge, private review publication, production Firebase deployment
and primary-domain cutover require separate receipts; see the
[rebaseline](../../modules/foundups/move2japan/docs/08_HOUSING_DISCOVERY_REBASELINE.md).

## Current Runtime and Creator Studio Direction (updated 2026-10-18)

The current implementation has Clerk admission, a video Mall, creator/category
filtering, queue playback and bounded presentation controls. Source contracts are
[README.md](README.md) and [INTERFACE.md](INTERFACE.md). The original dashboard,
wallet and marketplace plan below is historical; its Firebase-auth checkbox and
layer labels do not describe the complete current runtime.

The proposed creator-facing Live mode belongs to external
[AutoPost](https://github.com/FOUNDUPS/autopost/blob/main/ROADMAP.md#phase-4b--autopost-live-mode-planned).
The [p.fMALL roadmap](../../modules/foundups/pfmall/ROADMAP.md) owns shared
integration and presentation planning. Consume its
[build contract](../../modules/foundups/docs/mobile_studio/PFMALL_MOBILE_STUDIO_CONTRACT.md),
[API constraints](../../modules/foundups/docs/mobile_studio/PFMALL_CREATOR_LIVE_API_CONSTRAINTS.md)
and [machine outcome](../../modules/foundups/docs/mobile_studio/mobile_studio_outcome.v1.json)
before any implementation. This member browser remains a discovery/playback
surface. AutoPost already implements browser capture and recorded-file YouTube
upload; its continuous Live transport, durable creator service and shared live
projection are specified or planned, not implemented by this update. The first
AutoPost media proof is foreground WebRTC/relay, with native adoption based on
device evidence. Existing
presentation messages and player-open events confer no publishing authority or
proof of live playback.

- **Build v18 (2026-11-15)**: Progressive `#mallProjection` discovery pills (`Videos`, `Apps`, `HPC` via JS without modifying `index.html`), `internal_app` quick-view CTA (`GotJunk`), `localStorage` `source_group` persistence, desktop inline `queueQuery` + `ended` auto-advance, and Red Dog concierge category filtering.

## Historical Layer Plan

Retained for lineage. Use the current contracts above for implementation truth.

## Layer Progression

```
Layer 1 (Shell)      ████████████ COMPLETE
Layer 2 (Dashboard)  ░░░░░░░░░░░░ PENDING
Layer 3 (Wallet)     ░░░░░░░░░░░░ PENDING
Layer 4 (FoundUps)   ░░░░░░░░░░░░ PENDING
Layer 5 (Agents)     ░░░░░░░░░░░░ PENDING
Layer 6 (Marketplace)░░░░░░░░░░░░ PENDING
```

## Layer 1: Shell (COMPLETE)

**Files Created**:
- `index.html` - Auth state, navigation, section routing
- `css/member.css` - Shared styles

**Features**:
- [x] Firebase auth state listener
- [x] Redirect if not authenticated
- [x] Sidebar navigation
- [x] Section routing (hash-based)
- [x] Mobile responsive
- [x] User info display
- [x] Invite codes display
- [x] Sign out functionality
- [x] Placeholder sections for all modules

## Layer 2: Dashboard (NEXT)

**Goal**: Real data in dashboard overview

**Tasks**:
- [ ] Load UPS balance from Firestore
- [ ] Load FoundUp count
- [ ] Load agent count
- [ ] Activity feed (last 10 events)
- [ ] Quick actions (create FoundUp, deploy agent)

**Files**: `js/dashboard.js`

## Layer 3: Wallet

**Goal**: UPS token management

**Tasks**:
- [ ] UPS balance display
- [ ] Staked positions list
- [ ] Transaction history
- [ ] Stake/unstake interface
- [ ] Transfer UPS

**Files**: `js/wallet.js`

**Firestore Collections**:
- `users/{uid}.upsBalance`
- `stakes/{stakeId}`
- `transactions/{txId}`

## Layer 4: FoundUps

**Goal**: Create and manage FoundUps

**Tasks**:
- [ ] Create new FoundUp form
- [ ] My FoundUps list
- [ ] FoundUp detail view
- [ ] Contribution tracking
- [ ] F_i token holdings

**Files**: `js/foundups.js`

**Firestore Collections**:
- `foundups/{foundupId}`
- `contributions/{contributionId}`

## Layer 5: Agents

**Goal**: Deploy and monitor OpenClaw agents

**Tasks**:
- [ ] Agent deployment wizard
- [ ] Active agents list
- [ ] Agent earnings tracker
- [ ] Task assignment
- [ ] Agent health monitoring

**Files**: `js/agents.js`

**Firestore Collections**:
- `agents/{agentId}`
- `agent_tasks/{taskId}`
- `agent_earnings/{earningId}`

## Layer 6: Marketplace

**Goal**: Discover and join FoundUps

**Tasks**:
- [ ] Browse all public FoundUps
- [ ] Search and filter
- [ ] FoundUp detail view
- [ ] Join/stake interface
- [ ] Trending FoundUps

**Files**: `js/marketplace.js`

## Dependencies Between Layers

```
Layer 1 (Shell)
    │
    ├── Layer 2 (Dashboard) ── reads from all
    │
    ├── Layer 3 (Wallet) ── independent
    │
    ├── Layer 4 (FoundUps) ── uses Wallet for staking
    │       │
    │       └── Layer 5 (Agents) ── deploys to FoundUps
    │
    └── Layer 6 (Marketplace) ── uses Wallet, creates FoundUp links
```

**Key**: Each layer can be built independently. Layer 2 (Dashboard) aggregates data from all others but doesn't depend on their implementation.

## Anti-God-Module Principles

1. **No shared state** - Each module manages its own state
2. **Firebase as source of truth** - No client-side caching across modules
3. **Independent testing** - Each module has its own test file
4. **Lazy loading** - Load module JS only when section is active
5. **Clear boundaries** - Interfaces defined in INTERFACE.md

---

*WSP 84 Compliant | Created: 2026-02-18*
