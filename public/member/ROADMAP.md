# Member Area Roadmap

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
[HPC reconciliation](../../../modules/foundups/hpc/ROADMAP.md) and
[test log](tests/TestModLog.md) for source-bound controlled evidence. Conflict,
hosted review, deployment and physical/real-provider gates remain open.

**Module**: `public/member/`
**Approach**: Occam's Layered (build/test one layer at a time)

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
