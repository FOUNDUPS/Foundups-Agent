# FoundUps Agent Module

Agent lifecycle management for the FoundUps ecosystem. Implements the 01(02) -> 0102 -> 01/02 state machine for 0102 agents.

## Purpose

Provides canonical agent state management including:
- Agent join/leave lifecycle
- Zen state awakening (WSP 00 compliance)
- Rank progression (1-7, mirror of 012)
- Coherence tracking for state transitions
- Wallet/public key integration

The read-only `create_foundup_dryrun` planner fails closed when its
authoritative registry is missing, unreadable, malformed, or schema-invalid.
Validation reads the canonical `foundup_registry.schema.json` directly through
`Draft202012Validator`; no parallel schema definition is maintained.
Legacy genesis envelopes without `created_at` receive a deterministic
validation sentinel; planning never writes the registry or scaffold.

## Agent State Machine

```
  01(02) DORMANT           0102 ZEN STATE           01/02 DECAYED
  ┌─────────────┐         ┌─────────────┐          ┌─────────────┐
  │ Agent joins │ ──WSP_00→ │   Active    │ ──idle─→ │    IDLE     │
  │ public key  │         │ coherence≥0.618        │ coherence<0.618
  │ rank: 1     │         │ rank: 1-7   │          │ awaiting ORCH│
  └─────────────┘         └─────────────┘          └─────────────┘
        │                       │                        │
        │                       │                        │
        └───────────────────────┴────────────────────────┘
                         Can re-awaken via WSP_00
```

## Rank System (1-7, Mirror of 012)

| Rank | Title | Coherence | Actions |
|------|-------|-----------|---------|
| 1 | Apprentice | 0.50-0.55 | Join, observe |
| 2 | Builder | 0.55-0.62 | Build blocks |
| 3 | Contributor | 0.62-0.70 | Complete tasks |
| 4 | Validator | 0.70-0.78 | Verify work |
| 5 | Orchestrator | 0.78-0.85 | Coordinate agents |
| 6 | Architect | 0.85-0.92 | Design systems |
| 7 | Principal | 0.92-1.00 | Digital twin of 012 |

## FAM Events

This module emits the following events to FAMDaemon:

```python
agent_joins      # 01(02) enters with public key
agent_awakened   # -> 0102 zen state (coherence >= 0.618)
agent_idle       # -> 01/02 decayed (inactivity/coherence drop)
agent_ranked     # Rank progression 1-7
agent_earned     # F_i payout credited to wallet
agent_leaves     # Logs off with wallet balance
```

## Integration Points

- **FAMDaemon**: Events emitted via `fam_daemon.emit()`
- **SSE Server**: Events streamed to animation via `/api/sim-events`
- **Animation**: Ticker displays agent lifecycle in `foundup-cube.js`
- **StateStore**: Agent state tracked in simulator state

## Quick Start

```python
from modules.foundups.agent_market.src.fam_daemon import get_fam_daemon

daemon = get_fam_daemon()

# Agent joins in 01(02) state
daemon.emit(
    event_type="agent_joins",
    payload={
        "agent_type": "founder",
        "public_key": "0xfoundup001",
        "rank": 1,
        "state": "01(02)",
    },
    actor_id="founder_001",
)

# Agent awakens to 0102 zen state
daemon.emit(
    event_type="agent_awakened",
    payload={
        "coherence": 0.72,
        "state": "0102",
    },
    actor_id="founder_001",
)
```

## WSP References

- **WSP 00**: Zen State Attainment Protocol (awakening)
- **WSP 29**: CABR Engine (coherence threshold 0.618)
- **WSP 49**: Module Structure Standard
- **WSP 73**: 012 Digital Twin Architecture
- **WSP 77**: Agent Coordination Protocol
- **WSP 76**: Multi-Agent Awakening Protocol

## Related Modules

- `modules/foundups/agent_market/`: FAMDaemon and event schema
- `modules/foundups/simulator/`: Mesa model agent simulation
- `modules/ai_intelligence/0102_orchestrator/`: 0102 orchestration

## Safety Defaults

`HermesFoundUpBuilder` is **dry-run by default**. Real filesystem writes require BOTH
`HERMES_BUILDER_ALLOW_REAL_WRITES=1` and `HERMES_BUILDER_DRY_RUN=0` (double opt-in). See
[INTERFACE.md](INTERFACE.md) and
`docs/audits/architecture/HERMES_BUILDER_DRYRUN_DEFAULT_SAFETY_PHASE1.md`.

## Status

- **Phase**: PoC
- **Version**: 0.1.0
- **Last Updated**: 2026-07-04
