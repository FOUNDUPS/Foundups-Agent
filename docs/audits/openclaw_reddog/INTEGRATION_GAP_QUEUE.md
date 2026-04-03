# OpenClaw Red Dog Integration Gap Queue

**Audit Date**: 2026-04-03
**Worker**: G

---

## Gap Priority Matrix

| ID | Gap | Severity | Blocks Red Dog? | Effort |
|----|-----|----------|-----------------|--------|
| G1 | No browser-to-OpenClaw API | CRITICAL | YES | 4-6h |
| G2 | No audio ingress WebSocket | HIGH | Voice only | 2-3h |
| G3 | No compute tracking | HIGH | State machine | TBD |
| G4 | No permission tier enforcement | MEDIUM | Capability ladder | 2h |
| G5 | Training adapter not merged | LOW | No | PR review |
| G6 | No cross-session memory | LOW | Personality | TBD |

---

## Gap Details

### G1: No Browser-to-OpenClaw API (CRITICAL)

**Current state**: OpenClaw DAE is CLI/internal only.
**Red Dog needs**: Browser JS to call OpenClaw.
**Missing**: HTTP or WebSocket endpoint for text commands.

**Contract requirement**:
```
Red Dog (browser) → API Gateway → OpenClaw DAE → Response
```

**Files affected**:
- New: `gateway/routes/openclaw.py` or WebSocket handler
- Modify: `openclaw_dae.py` to expose message handler

---

### G2: No Audio Ingress WebSocket (HIGH - Voice Only)

**Current state**: Voice STT captures from local WASAPI.
**Red Dog needs**: Browser audio → backend → STT → text.
**Missing**: WebSocket endpoint for audio chunks.

**If voice is deferred**: Skip this gap.
**If voice is required**: ~2-3h to add WebSocket audio handler.

---

### G3: No Compute Tracking (HIGH)

**Current state**: Red Dog state is mocked (always AWAKE).
**Red Dog needs**: Real compute balance, feeding, consumption.
**Missing**: Backend compute ledger, staking integration.

**Contract defines**:
```
State 0: DORMANT (never fed)
State 1: AWAKE (minimal compute)
State 2: ACTIVE (staked/participating)
State 3: EMPOWERED (significant stake)
```

**Blocked by**: Tokenomics layer (out of scope for this audit).

---

### G4: No Permission Tier Enforcement (MEDIUM)

**Current state**: OpenClaw has 012-only auth.
**Red Dog needs**: Per-user permission tiers.
**Missing**: Capability ladder enforcement.

**Contract defines**:
```
DORMANT: No AI interaction
AWAKE: Basic context, static guidance
ACTIVE: Conversation history, limited inference
EMPOWERED: Full OpenClaw, action execution
```

**Files affected**:
- `openclaw_execution_routes.py`: Add tier checks
- New: `red_dog_permission_resolver.py`

---

### G5: Training Adapter Not Merged (LOW)

**Current state**: PR #250 open.
**Red Dog needs**: Nothing (training is 012-only).
**Action**: Review and merge for completeness.

---

### G6: No Cross-Session Memory (LOW)

**Current state**: localStorage mocks in browser.
**Red Dog needs**: Backend persistence for personality.
**Missing**: User session store.

**Contract says**: "Requires backend persistence" — out of scope for now.

---

## Gap Resolution Order

### Phase 1: Minimal Browser Integration

1. **G1**: Add text command API (HTTP POST or WebSocket)
2. **G4**: Add basic permission check (AWAKE required)

**Result**: Red Dog can send text commands, receive responses.

### Phase 2: State Machine

3. **G3**: Mock compute tracking (localStorage → real ledger later)

**Result**: Red Dog state reflects user activity.

### Phase 3: Voice (Optional)

4. **G2**: Add audio ingress WebSocket

**Result**: Red Dog can accept voice commands.

### Phase 4: Full Capability (Deferred)

5. **G6**: Backend session persistence
6. Tokenomics integration

---

## Out of Scope

| Item | Reason |
|------|--------|
| Blockchain/wallet | Requires tokenomics layer |
| Real compute staking | Requires blockchain |
| Training commands for Red Dog | 012-only operation |
| Action execution | Requires permission system |

---

*Worker G - 2026-04-03*
