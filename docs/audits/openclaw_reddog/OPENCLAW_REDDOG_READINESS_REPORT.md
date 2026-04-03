# OpenClaw Red Dog Readiness Report

**Audit Date**: 2026-04-03
**Worker**: G
**Slice**: `OPENCLAW_REDDOG_READINESS_AUDIT_PHASE1`
**Priority**: P1

---

## Executive Summary

| Question | Answer |
|----------|--------|
| Is OpenClaw real? | YES - DAE, routes, STT backends exist |
| Is Red Dog real? | YES - unified panel, API, state machine (mocked) |
| Can they connect today? | NO - no browser-to-backend API |
| What's the smallest next step? | HTTP text command endpoint (~3h) |
| What's blocked? | Compute tracking, tokenomics, voice |

---

## Audit Scope

### Read

1. `RED_DOG_DIGITAL_TWIN_CONTRACT.md` - Red Dog identity and state machine
2. `account-concierge.js` - Browser-side Red Dog implementation
3. `openclaw_execution_routes.py` - Training route (lines 711-848)
4. `openclaw_voice.py` - STT backends (Cohere, Whisper, Google)
5. PR #250 (training adapter) - OPEN
6. PR #258 (Cohere STT) - MERGED

### Questions Answered

1. What does training route expose? → Status/batch commands, 012-only
2. What does voice STT expose? → Transcription API, local CLI only
3. Are they browser-callable? → NO
4. What boundary does Red Dog need? → HTTP/WS text command API
5. What auth gaps exist? → No per-user permission tiers
6. Smallest next step? → HTTP adapter for text commands

---

## What Is Real

### OpenClaw (Backend)

| Component | Status | Location |
|-----------|--------|----------|
| `OpenClawDAE` | REAL | `moltbot_bridge/src/openclaw_dae.py` |
| Execution routes | REAL | `openclaw_execution_routes.py` |
| Training route | REAL (PR) | Lines 711-848, PR #250 |
| Voice STT chain | REAL | `openclaw_voice.py` |
| Cohere Transcribe | MERGED | 2B local model |
| Whisper fallback | REAL | faster-whisper |
| Google fallback | REAL | Cloud API |

### Red Dog (Browser)

| Component | Status | Location |
|-----------|--------|----------|
| Unified panel | REAL | `account-concierge.js` |
| `window.redDog` API | REAL | Lines 1087-1243 |
| Identity block | REAL | `setIdentity()` |
| FoundUps grid | REAL | `setFoundUps()` |
| AI tools | REAL | Projection, density, motion |
| Channels | REAL | Personal Mall, Search Mall |
| State machine | MOCKED | Always AWAKE |
| Compute tracking | MOCKED | localStorage stubs |

---

## What Is Partial

| Component | State | Gap |
|-----------|-------|-----|
| Training adapter | PR OPEN | Needs merge |
| Permission tiers | SPEC ONLY | No enforcement |
| Hunger/energy meters | SPEC ONLY | No UI |
| Feed CTA | SPEC ONLY | No UI |
| Cross-session memory | SPEC ONLY | No backend |

---

## What Is Missing

| Component | Severity | Notes |
|-----------|----------|-------|
| Browser-to-OpenClaw API | CRITICAL | No HTTP/WS endpoint |
| Audio ingress | HIGH | Voice blocked |
| Compute ledger | HIGH | State machine blocked |
| Permission resolver | MEDIUM | Tier enforcement blocked |
| Action execution | MEDIUM | Deferred per contract |

---

## APIs/Routes/Events That Exist

### OpenClaw Routes (Internal)

```python
# In openclaw_execution_routes.py
execute_plan(dae, plan)           # Route dispatcher
execute_query(dae, intent)        # Query handler
execute_command(dae, intent)      # Command handler
execute_training(dae, intent)     # Training (012-only)
execute_schedule(dae, intent)     # Scheduling
execute_monitor(dae, intent)      # Monitoring
```

### STT Transcription

```python
# In openclaw_voice.py
CohereTranscribeBackend.transcribe(audio, sample_rate)
WhisperSTTBackend.transcribe(audio, sample_rate)
GoogleSTTBackend.transcribe(audio, sample_rate)
```

### Red Dog Browser API

```javascript
// In account-concierge.js
window.redDog.getContext()        // Current page context
window.redDog.setIdentity(data)   // Set user identity
window.redDog.setFoundUps(list)   // Set FoundUps grid
window.redDog.setInvites(list)    // Set invite codes
window.redDog.show() / hide()     // Panel visibility
window.redDog.updateRecommendations(list)
window.redDog.askOpenClaw(msg)    // FUTURE (not implemented)
```

---

## Contract Boundary for Red Dog

### What Red Dog Needs from OpenClaw

```
Red Dog (browser)
    |
    | HTTP POST /api/openclaw/command
    | { message: string, session_id: string }
    |
    v
OpenClaw Gateway
    |
    | Route to OpenClawDAE.process_message()
    |
    v
Response
    |
    | { response: string, state: string }
    |
    v
Red Dog updates UI
```

### Permission Boundary (Future)

```
User tier → OpenClaw permission check → Allow/deny capability

DORMANT   → Reject all commands
AWAKE     → Allow read-only queries
ACTIVE    → Allow inference queries
EMPOWERED → Allow action commands
```

---

## Auth/Permission/Safety Gaps

| Gap | Risk | Mitigation |
|-----|------|------------|
| No per-user auth | HIGH | Add session-based auth |
| No rate limiting | MEDIUM | Add request throttle |
| No tier enforcement | MEDIUM | Add permission resolver |
| 012-only training | LOW | Correct, keep as-is |
| No audit logging | LOW | Add request logging |

---

## Recommendations

### Do Now (Phase 1)

1. Merge PR #250 (training adapter) for completeness
2. Do NOT integrate training into Red Dog

### Do Next (Phase 2)

1. Add HTTP text command endpoint (~3h)
2. Wire to Red Dog `askOpenClaw()` method
3. Mock state as AWAKE for all users

### Do Later (Phase 3+)

1. Add permission tier resolver
2. Add compute tracking (requires tokenomics)
3. Add voice ingress (if voice desired)
4. Add cross-session memory

---

## Attached Documents

1. [TRAINING_ROUTE_STATUS.md](TRAINING_ROUTE_STATUS.md)
2. [VOICE_STT_STATUS.md](VOICE_STT_STATUS.md)
3. [INTEGRATION_GAP_QUEUE.md](INTEGRATION_GAP_QUEUE.md)
4. [NEXT_SAFE_INTEGRATION_STEP.md](NEXT_SAFE_INTEGRATION_STEP.md)

---

## Conclusion

**OpenClaw and Red Dog are both real. They cannot connect today.**

The smallest safe integration step is an HTTP text command endpoint (~3h).
Training route is not Red Dog relevant (012-only).
Voice STT exists but lacks browser ingress (separate effort).

**Red Dog is ready for OpenClaw integration when the HTTP bridge is built.**

---

*Worker G - 2026-04-03*
*Slice: OPENCLAW_REDDOG_READINESS_AUDIT_PHASE1*
