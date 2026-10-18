# Member Area Roadmap

**Module**: `public/member/`
**Approach**: Occam's Layered (build/test one layer at a time)

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
