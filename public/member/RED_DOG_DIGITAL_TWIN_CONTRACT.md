# Red Dog Digital Twin Contract

**Version**: 1.0.0
**Status**: Contract Definition (Worker E)
**Audience**: Worker C (user panel/concierge implementation)

---

## 1. Identity

### What Red Dog IS

| Aspect | Definition |
|--------|------------|
| **Digital Twin** | Red Dog is the user's persistent AI companion inside the FoundUPS ecosystem. Not a mascot, not a helper widget — the user's actual agent. |
| **OpenClaw Agent** | Red Dog is the user's personal instance of the OpenClaw runtime. Each user gets their own Red Dog. |
| **Shell-Side AI** | Red Dog lives in the browser shell, not on a backend server. It represents the user's agency within pAVS. |
| **Best Friend** | Red Dog should feel loyal, personal, and useful — like a dog that knows its owner. |

### What Red Dog IS NOT

- NOT a chatbot that answers questions about the Mall
- NOT a mascot icon that opens a FAQ panel
- NOT a backend AI service the user queries
- NOT a static concierge with canned responses

### Identity Expression

- Red Dog barks `O!F` (the pAVS signal)
- Red Dog has personality: eager when fed, sleepy when starved
- Red Dog remembers context across sessions (within browser storage)
- Red Dog grows with the user's participation level

---

## 2. Surface Model

### The Unified Surface

**Current state** (what exists):
```
Red Dog button → Opens FAQ panel (red-dog-concierge.js)
Avatar trigger → Opens account plane (account-concierge.js)
```

**Target state** (what should exist):
```
Red Dog button → Opens THE UNIFIED PANEL (Red Dog = user panel = concierge)
Avatar → Also opens the same unified panel
```

**The concierge and user panel are the same thing.**

Red Dog IS the user panel. The user panel IS the concierge. They are one surface.

### Surface Hierarchy

```
Mall (index.html)
├── Browsing surface (carousel, cards)
└── Red Dog surface (THE unified panel)
    ├── Identity block (who am I)
    ├── My FoundUps (quick grid)
    ├── Red Dog state (am I fed?)
    ├── Invite drawer (my codes)
    ├── AI conversation area (FUTURE)
    └── Sign out

FoundUp Entry (foundup.html)
├── Entry content (readiness, details)
└── Red Dog surface (SAME panel, context-aware)
    ├── This FoundUp context
    ├── Red Dog guidance (not FAQ — actual guidance)
    └── Navigation help
```

### Where Red Dog Lives

| Surface | Red Dog Role |
|---------|-------------|
| **Mall** | Primary home. Shows identity, FoundUps, invites, state. |
| **User Panel** | IS Red Dog. Not a separate thing. |
| **FoundUp Entry** | Context-aware companion. Knows which FoundUp you're viewing. |
| **FoundUp Shell** (future) | Active participant. Helps user interact with the FoundUp. |

---

## 3. Capability Ladder

Red Dog evolves based on compute feeding. These are the operational states:

### State 0: Dormant

**Condition**: User has never fed compute to Red Dog
**Behavior**:
- Red Dog appears asleep/greyed out
- Panel shows "Red Dog is sleeping... Feed me to wake up!"
- Can still view identity, FoundUps, invites
- No AI interaction available

**Visual**: Closed eyes, muted colors, "zzz" indicator

### State 1: Awake (Freemium)

**Condition**: User has fed minimal compute (e.g., signed up, verified invite)
**Behavior**:
- Red Dog is awake and responsive
- Basic context awareness (knows current page, current FoundUp)
- Can provide static guidance (current FAQ functionality)
- Shows "hunger meter" — how recently fed

**Visual**: Open eyes, normal colors, wagging tail on interaction

### State 2: Active (Premium Lite)

**Condition**: User has staked compute or participated in FoundUp work
**Behavior**:
- Red Dog remembers conversation history
- Can make suggestions based on user's FoundUp portfolio
- Has access to limited OpenClaw inference
- Shows "energy level" based on compute balance

**Visual**: Bright eyes, gradient glow, active animations

### State 3: Empowered (Premium Full)

**Condition**: User has significant compute stake / active FoundUp participation
**Behavior**:
- Full OpenClaw agent capabilities
- Can take actions on user's behalf (with confirmation)
- Cross-FoundUp intelligence
- Priority inference queue

**Visual**: Full gradient animation, "powered up" state, confident posture

---

## 4. Compute Economics

### "Compute is Red Dog's Food"

| Concept | Meaning |
|---------|---------|
| **Feeding** | User provides compute (via stake, participation, or purchase) |
| **Hunger** | Time since last compute interaction |
| **Energy** | Current compute balance available for inference |
| **Starvation** | Compute depleted → Red Dog goes dormant |

### Operational Model

```
User feeds compute → Red Dog gains energy
Red Dog uses energy → Inference calls consume compute
Energy depletes → Red Dog gets hungry → needs feeding
```

### Display Elements (for Worker C)

1. **Hunger meter**: Visual bar showing time since last feed
2. **Energy level**: Current compute available
3. **Feed button**: CTA to add compute (links to wallet/stake flow)
4. **State indicator**: Which capability tier is active

---

## 5. Surface Behaviors

### In Mall

| Trigger | Red Dog Response |
|---------|-----------------|
| Panel opens | "Hey! Want to explore some FoundUps?" |
| Card swipe | Updates context: "You're looking at {FoundUp name}" |
| Idle > 30s | Subtle animation, waiting posture |
| Low energy | "I'm getting hungry... feed me?" |

### In User Panel (same surface)

| Section | Red Dog Role |
|---------|-------------|
| Identity | "This is you: @{username}" |
| FoundUps | "Your FoundUps — tap to visit" |
| Invites | "Share these with friends" |
| State | "I'm {state} — {context message}" |

### In FoundUp Entry

| Context | Red Dog Response |
|---------|-----------------|
| Ready FoundUp | "This one's live! You can enter soon." |
| Conditional | "Almost there — some gaps to close." |
| Discoverable | "Backend only — no shell yet." |
| User's own FoundUp | "This is YOUR FoundUp! Need help?" |

---

## 6. Out of Scope (for this contract)

The following are explicitly NOT part of this contract and should remain unimplemented:

| Item | Reason |
|------|--------|
| Backend AI inference | Requires OpenClaw gateway integration |
| Wallet connection | Requires blockchain layer |
| Compute staking | Requires tokenomics implementation |
| Cross-session memory | Requires backend persistence |
| Action execution | Requires permission system |
| Voice interaction | Future capability |
| FoundUp shell handoff | Worker B/C boundary |

### What Worker C SHOULD Implement

1. Unified panel (merge Red Dog + account concierge)
2. State display (dormant/awake/active/empowered) — can be mocked
3. Hunger/energy meters — can be mocked with localStorage
4. Context awareness (knows current page/FoundUp)
5. Personality expressions (messages, animations)
6. Feed CTA (button exists, links to "coming soon" or stub)

### What Worker C Should NOT Implement

1. Actual OpenClaw inference
2. Real compute tracking
3. Blockchain interactions
4. Backend API calls for AI
5. Auth changes

---

## 7. Implementation Guidance for Worker C

### Merge Strategy

```javascript
// BEFORE: Two separate surfaces
red-dog-concierge.js  → FAQ topics into #redDogPanel
account-concierge.js  → Account plane with identity/foundups

// AFTER: One unified surface
red-dog-unified.js    → Single panel with all content
                      → Red Dog state at top
                      → Identity below
                      → FoundUps grid
                      → Invites drawer
                      → Contextual guidance (replaces FAQ)
```

### State Machine (mockable)

```javascript
const RED_DOG_STATES = {
  DORMANT: {
    message: "Red Dog is sleeping... Feed me to wake up!",
    canInteract: false
  },
  AWAKE: {
    message: "Hey! What are we exploring today?",
    canInteract: true,
    tier: "freemium"
  },
  ACTIVE: {
    message: "I'm ready to help! What do you need?",
    canInteract: true,
    tier: "premium_lite"
  },
  EMPOWERED: {
    message: "Full power! Let's get things done.",
    canInteract: true,
    tier: "premium_full"
  }
};

// Mock: Always return AWAKE for now
function getRedDogState() {
  return RED_DOG_STATES.AWAKE;
}
```

### Personality Expressions

```javascript
const GREETINGS = {
  mall: ["Hey!", "What's up?", "Ready to explore?"],
  entry: ["Checking this one out?", "Interesting choice!"],
  return: ["Welcome back!", "Missed you!"],
  idle: ["Still here...", "Take your time.", "zzz..."]
};
```

### localStorage Keys (for mocking)

```javascript
"reddog_last_feed"    // ISO timestamp
"reddog_energy"       // 0-100 number
"reddog_state"        // DORMANT|AWAKE|ACTIVE|EMPOWERED
"reddog_greeting_idx" // For varying greetings
```

---

## 8. Success Criteria

Worker C implementation is complete when:

1. [ ] Single unified panel replaces both current surfaces
2. [ ] Red Dog state is displayed (can be mocked)
3. [ ] Hunger/energy meters are visible (can be mocked)
4. [ ] Identity block is present
5. [ ] FoundUps grid is present
6. [ ] Invites drawer is present
7. [ ] Context changes based on page (Mall vs Entry)
8. [ ] Feed CTA exists (stub is acceptable)
9. [ ] Personality messages vary
10. [ ] Red Dog feels like a companion, not a widget

---

## 9. Contract Signature

This contract defines the product truth for Red Dog as a digital twin. It does not prescribe implementation details beyond what Worker C needs to build the correct experience.

**Red Dog is:**
- The user's digital twin
- The user's OpenClaw agent
- The unified user panel and concierge
- Fed by compute
- The user's best friend in FoundUPS

**Red Dog barks `O!F`.**

---

*Contract Author: Worker E (0102)*
*Contract Date: 2026-04-01*
*Contract Status: ACTIVE*
