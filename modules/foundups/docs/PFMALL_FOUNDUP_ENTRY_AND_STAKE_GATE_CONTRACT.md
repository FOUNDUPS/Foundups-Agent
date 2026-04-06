# p.fMALL FoundUp Entry and Stake Gate Contract

**Version**: 1.0.0  
**Date**: 2026-04-05  
**Status**: Architecture specification  
**Owner**: Worker F (0102)  
**Protocol**: WSP 97

---

## 1. Purpose

Define the entry flow from Mall discovery through gated FoundUp interior access.

This contract specifies:
- Entry gestures from the Mall
- Surface sequence (welcome → community → gate → interior)
- Stake gate mechanics (wallet + UPS + F_i)
- Sentinel agent role

This is the **target architecture**. Current runtime (`foundup.html`) is a transitional shell-owned surface, not the final experience pipe.

---

## 2. Entry Gestures

### 2.1 Primary Gesture: Double-Tap / Double-Click

| Context | Gesture | Result |
|---------|---------|--------|
| Mall tile (video playing) | double-tap | Enter FoundUp Welcome |
| Mall tile (video paused) | double-tap | Play video (first tap = play, second = enter) |
| Mall tile (desktop) | double-click | Enter FoundUp Welcome |

**Rationale**: Single-tap controls playback; double-tap signals entry intent.

### 2.2 Visible Fallback: Entry Control

A visible button/control on the tile provides explicit entry for:
- Users unfamiliar with gesture grammar
- Accessibility (screen readers, switch access)
- Touch devices where double-tap is unreliable

Placement: corner overlay on tile (e.g., expand icon or "Enter" label).

### 2.3 Entry from Fullscreen Player

| Context | Gesture | Result |
|---------|---------|--------|
| Fullscreen player | swipe-down | Exit to Mall |
| Fullscreen player | tap "info" or "more" | Show FoundUp info sheet with "Enter FoundUp" action |

The fullscreen player is a video consumption layer, not an entry surface. Entry requires explicit action from the info sheet.

---

## 3. Surface Sequence

The entry flow progresses through distinct surfaces:

```
Mall Discovery
    │
    ▼ (double-tap / entry control)
FoundUp Welcome
    │
    ▼ (public entry → Discord/community)
Public Community Entry
    │
    ▼ (stakeholder gate)
Stakeholder Gate
    │
    ▼ (wallet + stake verification)
Stakeholder Interior
```

### 3.1 Mall Discovery

**What it is**: The video-backed tile field in `public/member/index.html`.

**Capabilities**:
- Browse FoundUp lanes via tile field
- Play/preview videos in Mall context
- Filter by creator, category, tag
- Search via Red Dog

**No gate required**: Mall discovery is open to all admitted members.

### 3.2 FoundUp Welcome

**What it is**: The landing surface after entry intent (double-tap or entry control).

**Current implementation**: `public/member/foundup.html?id={foundup_id}` — transitional shell-owned surface.

**Target implementation**: In-scope route `/f/{foundup_id}` — shell delegates to FoundUp welcome view.

**Capabilities**:
- FoundUp identity (name, tagline, entity)
- Readiness posture (active / conditional / discoverable)
- Preview content (hero video, recent activity)
- Public community entry link (Discord, forum)
- Stakeholder gate CTA ("Connect Wallet to Enter")

**No wallet required**: Welcome surface is visible to all admitted members.

### 3.3 Public Community Entry

**What it is**: The public-facing community for a FoundUp (typically Discord).

**Important**: Discord is NOT the stakeholder gate. Discord is a public community surface that anyone can join.

**Purpose**:
- Onboard new users before they commit stake
- Build community awareness
- Provide support and discussion
- Funnel engaged users toward staking

**Relationship to gate**: Users may participate in Discord without staking. Stakeholder-only surfaces (interior dashboard, voting, rewards) are gated separately.

### 3.4 Stakeholder Gate

**What it is**: The wallet-connected verification checkpoint that grants interior access.

**Gate checks**:
1. **Wallet connected**: User has connected a wallet via WalletConnect or compatible provider
2. **Signature verified**: User has signed a challenge proving wallet ownership
3. **Stake threshold met**: User holds sufficient UPS + F_i to qualify as stakeholder

**NOT verified at gate**:
- Real-time on-chain balance (verified asynchronously, not blocking)
- External KYC/identity (not required in phase 1)
- Discord membership (public community is separate from gate)

**Gate UI**:
- "Connect Wallet" button
- Signature challenge modal
- Stake summary (UPS balance, F_i holdings, qualification status)
- Clear messaging on what stakeholder access provides

### 3.5 Stakeholder Interior

**What it is**: The gated surface for verified stakeholders of a specific FoundUp.

**Access requirements**:
- Passed stakeholder gate for this FoundUp
- Session remains valid (wallet still connected, signature not expired)

**Capabilities** (FoundUp-specific):
- Dashboard with FoundUp metrics
- Task assignment and agent coordination
- Voting on FoundUp decisions
- Reward distribution visibility
- Stakeholder-only content and channels

---

## 4. Stake Gate Mechanics

### 4.1 Entitlement Model

Stakeholder status is determined by:

| Asset | Role |
|-------|------|
| **UPS** | Universal Participation Stake — network-wide utility token. Stake UPS to participate in any FoundUp. |
| **F_i** | FoundUp-specific token. Holding F_i grants stakeholder rights in that specific FoundUp. |

**Qualification formula** (target, not implemented):
```
isStakeholder(user, foundup) =
  user.ups_staked >= MIN_UPS_STAKE
  AND user.f_i_balance[foundup.token_symbol] > 0
```

Phase 1 may use simplified thresholds (e.g., any F_i holding qualifies).

### 4.2 Wallet Connect Flow

```
1. User clicks "Connect Wallet" on gate UI
2. Shell invokes WalletConnect provider
3. User selects wallet and approves connection
4. Shell receives wallet address
5. Shell generates challenge message:
   "Sign to verify your identity for {foundup_name}
    Timestamp: {iso_timestamp}
    Nonce: {random_nonce}"
6. User signs challenge in wallet
7. Shell verifies signature matches wallet address
8. Shell queries stake balances (async, cached)
9. If qualified → grant interior access
   If not qualified → show stake requirement messaging
```

### 4.3 Session Persistence

- Wallet connection persists in browser session (localStorage/sessionStorage)
- Signature challenge is re-verified on session expiry (e.g., 24h)
- Interior access is revoked if wallet disconnects
- Stake balance is re-checked periodically (not on every page load)

### 4.4 No Fake Verification Claims

**Important**: The gate does NOT claim to verify:
- Real-time on-chain state (cached/async only)
- Transaction history
- Third-party KYC
- Discord role sync

The gate verifies:
- Wallet ownership (signature)
- Stake threshold (cached balance query)

Any live on-chain verification is out of scope for phase 1.

---

## 5. Sentinel Agent Role

Each FoundUp has a **sentinel agent** — an AI agent that manages the entry experience and interior coordination.

### 5.1 One Sentinel Per FoundUp

```
FoundUp "antifafm" → Sentinel "antifafm_sentinel"
FoundUp "move2japan" → Sentinel "move2japan_sentinel"
```

Sentinels are OpenClaw agents with FoundUp-scoped permissions.

### 5.2 Sentinel Responsibilities

| Function | Description |
|----------|-------------|
| **Greet** | Welcome users at FoundUp Welcome surface |
| **Route** | Direct users to appropriate surface (community, gate, interior) |
| **Enforce** | Verify gate requirements before granting interior access |
| **Onboard** | Guide new stakeholders through interior features |
| **Monitor** | Track engagement and surface health |

### 5.3 Sentinel Scope

The sentinel operates ONLY within its FoundUp's surfaces:
- FoundUp Welcome
- Stakeholder Gate
- Stakeholder Interior

The sentinel does NOT operate in:
- Mall discovery (Red Dog handles Mall-level AI)
- Other FoundUps (each has its own sentinel)
- Shell-owned surfaces (/wallet, /settings)

### 5.4 Sentinel-to-Shell Communication

Sentinels communicate with the shell via the standard `postMessage` protocol (see `PFMALL_SHELL_CONTRACT.md`):

```typescript
// Sentinel requests gate verification
{
  type: "foundup_event",
  foundup_id: "antifafm",
  event: "gate_verify_request",
  payload: { wallet_address: "0x..." }
}

// Shell responds with verification result
{
  type: "shell_event",
  event: "gate_verify_result",
  payload: { verified: true, stake_summary: {...} }
}
```

---

## 6. Transitional vs Target State

### 6.1 Current Transitional State

| Surface | Implementation | Route |
|---------|---------------|-------|
| Mall Discovery | `public/member/index.html` | `/member/` |
| FoundUp Welcome | `public/member/foundup.html` | `/member/foundup.html?id={id}` |
| Public Community | External (Discord) | `discord.gg/{invite}` |
| Stakeholder Gate | NOT IMPLEMENTED | — |
| Stakeholder Interior | NOT IMPLEMENTED | — |

### 6.2 Target State

| Surface | Implementation | Route |
|---------|---------------|-------|
| Mall Discovery | Shell catalog view | `/discover` |
| FoundUp Welcome | FoundUp-owned view | `/f/{foundup_id}` |
| Public Community | External (Discord) | `discord.gg/{invite}` |
| Stakeholder Gate | Shell-mediated | `/f/{foundup_id}/gate` |
| Stakeholder Interior | FoundUp-owned view | `/f/{foundup_id}/dashboard` |

---

## 7. Related Contracts

| Document | Relationship |
|----------|--------------|
| `PFMALL_SHELL_CONTRACT.md` | Shell responsibilities and postMessage protocol |
| `PFMALL_EXTERNAL_FOUNDUP_ROUTE_CONTRACT.md` | External repo model and route contract |
| `PFMALL_ROUTING_DISCOVERY_MODEL.md` | URL structure and navigation |
| `PFMALL_FULLSCREEN_PLAYER_CONTRACT.md` | Video player behavior (not an entry surface) |
| `public/member/RED_DOG_DIGITAL_TWIN_CONTRACT.md` | Red Dog role in Mall (not sentinel) |

---

## 8. Invariants

1. **Discord is not the gate**: Public community and stakeholder interior are separate surfaces.
2. **Wallet signature is required**: No fake verification claims.
3. **One sentinel per FoundUp**: Sentinels are scoped, not global.
4. **Double-tap is entry intent**: Single-tap controls playback.
5. **Welcome is ungated**: Any admitted member can view FoundUp Welcome.
6. **Interior requires stake**: Stakeholder-only surfaces require wallet + stake verification.
7. **Shell mediates gate**: The shell owns wallet connect and signature verification.

---

## 9. Phase Roadmap

**Phase 1** (current):
- Mall discovery with video tiles
- Transitional welcome surface (`foundup.html`)
- Discord links for public community
- No wallet connect or stake gate

**Phase 2** (planned):
- Wallet connect integration
- Stake threshold verification (cached)
- Gate UI with qualification messaging
- Sentinel agent greeter

**Phase 3** (planned):
- Interior dashboard surfaces
- Stakeholder-only content gating
- Sentinel routing and enforcement
- F_i holder benefits

---

*This contract defines the entry and gate architecture for p.fMALL FoundUps. Implementation requires wallet infrastructure and stake tracking services not yet deployed.*
