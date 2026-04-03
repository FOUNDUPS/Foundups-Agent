# Next Safe Integration Step: Red Dog + OpenClaw

**Audit Date**: 2026-04-03
**Worker**: G
**Priority**: P2 (after pfMALL stabilizes)

---

## The Smallest Truthful Step

### Goal

Enable Red Dog (browser) to send a text command and receive a response from OpenClaw (backend).

### NOT The Goal

- Full AI inference
- Voice commands
- Compute tracking
- Cross-session memory
- Action execution

---

## Implementation Spec

### Step 1: Add OpenClaw Text Endpoint

**File**: `modules/communication/moltbot_bridge/src/openclaw_http_adapter.py` (NEW)

```python
"""HTTP adapter for browser-to-OpenClaw text commands."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/openclaw", tags=["openclaw"])

class TextCommandRequest(BaseModel):
    message: str
    session_id: str  # Browser session identifier

class TextCommandResponse(BaseModel):
    response: str
    state: str  # DORMANT|AWAKE|ACTIVE|EMPOWERED (mocked for now)

@router.post("/command", response_model=TextCommandResponse)
async def text_command(req: TextCommandRequest):
    """Process a text command from Red Dog."""
    # Mock state check (always AWAKE)
    state = "AWAKE"
    
    # Route to OpenClaw DAE
    from modules.communication.moltbot_bridge.src.openclaw_dae import OpenClawDAE
    dae = OpenClawDAE()
    
    # Process command
    response = await dae.process_message(req.message)
    
    return TextCommandResponse(response=response, state=state)
```

### Step 2: Wire Endpoint to Gateway

**File**: `modules/infrastructure/gateway/src/main.py`

```python
# Add import
from modules.communication.moltbot_bridge.src.openclaw_http_adapter import router as openclaw_router

# Add router
app.include_router(openclaw_router)
```

### Step 3: Add Browser Client

**File**: `public/member/js/red-dog-openclaw.js` (NEW)

```javascript
/**
 * Red Dog OpenClaw bridge (text commands only).
 */
window.redDogOpenClaw = {
  /**
   * Send a text command to OpenClaw.
   * @param {string} message - The command text
   * @returns {Promise<{response: string, state: string}>}
   */
  async sendCommand(message) {
    const sessionId = localStorage.getItem('reddog_session_id') || 
                      crypto.randomUUID();
    localStorage.setItem('reddog_session_id', sessionId);
    
    const res = await fetch('/api/openclaw/command', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, session_id: sessionId })
    });
    
    if (!res.ok) throw new Error('OpenClaw request failed');
    return res.json();
  }
};
```

### Step 4: Connect to Red Dog Concierge

**File**: `public/member/js/account-concierge.js`

Add to existing `redDog` API:

```javascript
// In the api object:
async askOpenClaw(message) {
  if (!window.redDogOpenClaw) {
    return { response: "OpenClaw not available", state: "DORMANT" };
  }
  try {
    return await window.redDogOpenClaw.sendCommand(message);
  } catch (err) {
    console.error('[RED-DOG] OpenClaw error:', err);
    return { response: "Failed to reach OpenClaw", state: "DORMANT" };
  }
}
```

---

## Test Plan

1. Start gateway with OpenClaw endpoint
2. Open Mall in browser
3. Open Red Dog panel
4. Type command in (future) AI conversation area
5. Verify response appears

---

## Files Changed

| File | Change |
|------|--------|
| `openclaw_http_adapter.py` | NEW |
| `gateway/main.py` | Add router |
| `red-dog-openclaw.js` | NEW |
| `account-concierge.js` | Add `askOpenClaw()` |

---

## Effort Estimate

| Task | Time |
|------|------|
| HTTP adapter | 1h |
| Gateway wiring | 30m |
| Browser client | 30m |
| Integration test | 1h |
| **Total** | **3h** |

---

## Safety Notes

1. **No auth enforcement yet** - acceptable for MVP (localhost only)
2. **No rate limiting** - add before production
3. **State is mocked** - always returns AWAKE
4. **No voice** - text only

---

## What This Enables

After this step:
- Red Dog can send text commands to OpenClaw
- Red Dog receives text responses
- State machine is mocked (future work)
- Foundation for capability ladder

---

## What This Does NOT Enable

- Voice commands (need audio ingress)
- Real compute tracking (need tokenomics)
- Action execution (need permission system)
- Training access (012-only, not Red Dog)

---

*Worker G - 2026-04-03*
