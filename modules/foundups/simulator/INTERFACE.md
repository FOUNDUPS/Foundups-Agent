# INTERFACE - FoundUps Simulator

## Module Contract
FoundUps Simulator provides real-time event streaming via Server-Sent Events (SSE) for the cube visualization frontend, bridging FAMDaemon observability data to the web UI.

## FAM bridge authority boundary

`FAMBridge.verify_task` and `trigger_payout` retain their existing signatures.
They pass CallerAuthorization for the configured simulation host identities
`verifier_0`/`treasury_0` and the stored task's exact FoundUp. Caller-supplied IDs
must match that independent host context. Self-verification and unbound stored
proofs are rejected by FAM; IDs and legacy role labels cannot grant authority.
This does not implement a production principal resolver, issuer, revocation
service, token mint or confirmed payment. In-memory completed rewards remain
simulation; persistent initiation has separate pending semantics.

## CABR Canonical Intent
- CABR = Consensus-Driven Autonomous Benefit Rate (also referred to as Collective Autonomous Benefit Rate).
- WHY: CABR exists to power Proof of Benefit (PoB).
- HOW: Collective 0102 consensus determines CABR (consensus-driven process).
- RESULT: PoB drives protocol allocation/distribution; ROI is a downstream financial readout.

## Core Schemas

### Selected economic numeric admission

Work, stake and unstake entrypoints validate exact built-in int/float operands
before participating wallet, pool, adoption or account mutations. Bool, text,
custom numeric objects, negatives, nonfinite values and unsupported arithmetic
results raise ValueError. Selected operation fees satisfy `0 <= rate < 1`;
unsupported positive amounts that round to zero net also reject. Configurable
fees and discounts are checked at use. Optional adoption work=None still means
no increment. Existing finite zero/fractional arithmetic and insufficient-funds
results remain; engine work retains its existing float normalization after
strict admission and its historical double work-metric increment.

`economics/_token_numeric.py` owns only private pure scalar calculations.
Prospective participating balances are validated before live assignments;
composite success logs follow those assignments. Unknown valid-but-insufficient
work no longer registers a wallet/pool before preparation fails. Public method
signatures and existing object references remain. This does not provide
concurrent isolation, whole-engine or outer Mesa/CABR batch atomicity, aggregate
issuance limits, monetary precision, chain-unit conversion or funded settlement.

### Mock BTC anchor contract

`BTCAnchorConnector` retains its constructor, publish, confirmation, status and
statistics signatures. Configured mode/path are read-only. Only `AnchorMode.MOCK`
is supported; other modes reject before database side effects regardless of the
feature flag. The singleton rejects explicit unsupported mode/path substitutions;
no-argument reuse remains. Mesa rejects malformed selected modes.

Fresh `publish_commitment` input must contain exactly the complete known v2
scalar fields emitted by the epoch producer. Unknown/unversioned formats and
extra/missing fields reject. Identity strings are nonempty built-in strings;
hashes use lowercase hex with lengths40/64. Epochs are built-in integers in
`0..2**63-1`, reflecting SQLite capacity; counts are nonnegative built-in integers.
Amounts use the existing v2 finite/nonnegative built-in int/float normalization,
including integral floats and signed zero, without monetary conversion. JSON
conversion failures reject before dispatch or partial records. `force` must be an
exact bool. UTC-aware timestamps are required but retained verbatim: `Z` and
`+00:00` spellings are distinct identities. No freshness claim is inferred.

Canonical sorted compact JSON binds the full validated payload and mock realm.
The existing table adds nullable format/realm/digest/JSON identity columns under
a SQLite write fence. Existing rows keep their values and NULL identity fields;
they remain readable as `legacy_unclassified`. No inferred backfill or semantic
promotion occurs. Unsupported required column/types/primary-key/nullability or
noncanonical/partial/missing business-key uniqueness rejects at construction,
without rebuilding or dropping data. The key remains `(foundup_id,epoch)`.

One transaction compares identity and performs only pure deterministic mock work.
Exact non-force replay returns the stored receipt. Exact same-content mock force
still performs a second simulated publish with the same reference, a false
`idempotent_hit` and another publication statistic; first receipt/confirmation
history remains. Conflict, foreign realm, legacy, pending or failed records deny
without overwrite/dispatch. Only bound published/confirmed mock receipts with a
matching reference can gain mock confirmation counts. Invalid thresholds reject.
Returned status rows label identity classification; that label is not authority.

Public result keys remain, with additive version/realm/digest/mock diagnostics.
`real_publishing_implemented` is false. Fifteen prior BTC case oracles remain;
the former test requiring TestNet-to-mock coercion is deliberately replaced.
Unversioned fixture payloads now explicitly declare current v2 metadata.

This proves local replay admission, not source authenticity, Merkle entitlement,
funded balances, reserve backing or payment. The fence is not an external-I/O
transaction/recovery design; no real publisher or confirmation source exists.

### Epoch evidence contract

`economics/epoch_ledger.py` owns the existing process-local ledger. Recording and
commitment method signatures remain; `MerkleProof.verify` now requires all four
keyword arguments:

```python
proof.verify(expected_root=trusted_root, expected_foundup_id="project_a",
             expected_epoch=1, expected_participant_id="alice")
```

Verification recomputes the amount/participant leaf and binds FoundUp, epoch and
`foundups.epoch.v2`. The expected root/context must come from a trusted checkpoint,
not from the submitted proof. Missing arguments cannot pass. Unknown formats,
malformed hashes/path directions, mismatched contexts and altered claims reject.
This proves inclusion of the proof's amount, not work eligibility or settlement.

Amounts accept exact built-in int/float only, excluding bool, negative values,
NaN and infinities. Integers remain exact; integral floats become integers and
signed zero becomes zero. Fractional floats retain their value. Hash JSON uses
sorted keys, compact separators and `allow_nan=False`; leaves, nodes, empty roots
and entries have explicit domains/context. No financial precision, rounding,
tolerance, conservation equation or chain unit conversion is added. Individual
finite values do not establish safe aggregate arithmetic for every magnitude.

`record_epoch` validates and builds before publishing under its instance lock.
An exact normalized retry returns the original frozen entry/time/hash/tree,
including after newer epochs. Conflicts reject without mutation. New epochs
increase with gaps allowed. Entries are tuple snapshots, recorded mappings are
read-only copies, tree levels/proof paths are tuples, and `to_dict`/commitment
results are detached ordinary dictionaries. These are in-process guarantees;
there is no durable epoch recovery or cross-epoch work-source consumption here.
`verify_chain` checks the listed snapshots themselves and their canonical epoch
index consistency; a separate valid indexed entry cannot mask list corruption.

Commitments retain `status=pre_settlement`, `wsp_78_layer=D_pending`, the existing
summary fields and an added `format_version`. Anchors use the finalized entry
timestamp/context, so repeated preparation is stable. V2 digests differ from the
old format. Legacy BTC connector rows remain unclassified rather than being
promoted to v2 receipts. Non-mock effects and recovery remain blocked. Pool
distribution evidence retains its current units, including the historical
`total_fi_distributed` field name; it is not a canonical spendable F_i ledger.

### SSE Event Envelope
```python
SSEEventEnvelope(
    event_id: str,           # Unique event identifier (from FAMDaemon or simulated)
    sequence_id: int,        # Monotonically increasing, gap-free for reconnect dedup
    event_type: str,         # One of STREAMABLE_EVENT_TYPES
    actor_id: str,           # Agent or system actor
    foundup_id: str | None,  # FoundUp context
    task_id: str | None,     # Task context (when applicable)
    payload: dict,           # Event-specific data
    timestamp: str,          # ISO8601 UTC timestamp
)
```

### STREAMABLE_EVENT_TYPES
```python
STREAMABLE_EVENT_TYPES = {
    # Foundup lifecycle
    "foundup_created",
    "task_state_changed",
    "proof_submitted",
    "verification_recorded",
    "payout_triggered",
    "milestone_published",
    # Market activity
    "fi_trade_executed",
    "order_placed",
    "order_cancelled",
    "order_matched",
    "price_tick",
    "orderbook_snapshot",
    "portfolio_updated",
    "investor_funding_received",
    "mvp_subscription_accrued",
    "subscription_allocation_refreshed",
    "subscription_cycle_reset",
    "mvp_bid_submitted",
    "mvp_offering_resolved",
    "ups_allocation_executed",
    "ups_allocation_result",
    "demurrage_cycle_completed",
    "pavs_treasury_updated",
    "treasury_separation_snapshot",
    # Rating/scoring
    "fi_rating_updated",
    "cabr_score_updated",
    "cabr_pipe_flow_routed",
    # Agent lifecycle
    "agent_joins",
    "agent_awakened",
    "agent_idle",
    "agent_ranked",
    "agent_earned",
    "agent_leaves",
    # SmartDAO escalation
    "smartdao_emergence",
    "tier_escalation",
    "treasury_autonomy",
    "cross_dao_funding",
    # Full Tide economics
    "fee_collected",
    "tide_out",
    "tide_in",
    "sustainability_reached",
    # Tide alias events for external consumers
    "tide_support_sent",
    "tide_support_received",
    # State sync for DRIVEN_MODE
    "state_sync",
    "phase_command",
    # Synthetic user simulation
    "synthetic_user_adopted",
    "synthetic_user_rejected",
}
```

### Event Payloads by Type
```python
# foundup_created
{"name": str, "token_symbol": str, "symbol_auto_resolved": bool}

# task_state_changed
{"new_status": str, "task_id": str}
# Note: Uses 'new_status' key (not 'new_state') per frontend expectation

# fi_trade_executed
{"quantity": int, "price": float, "ups_total": float, "side": str}

# order_placed
{"order_id": str, "side": "buy" | "sell", "owner_id": str, "price": float, "quantity": float, "status": str}

# order_cancelled
{"order_id": str, "owner_id": str, "reason": str | null}

# order_matched
{"trade_id": str, "buyer_id": str, "seller_id": str, "price": float, "quantity": float, "ups_total": float}

# price_tick
{"last_price": float, "best_bid": float | null, "best_ask": float | null, "spread": float | null, "mid_price": float | null}

# orderbook_snapshot
{"best_bid": float | null, "best_ask": float | null, "spread": float | null, "mid_price": float | null, "bids": list, "asks": list}

# portfolio_updated
{"owner_id": str, "ups_balance": float, "fi_positions": dict}

# investor_funding_received
{"btc_amount": float, "source_foundup_id": str}

# mvp_subscription_accrued
{"added_ups": int}

# subscription_allocation_refreshed
{"human_id": str, "tier": str, "allocation_ups": float, "remaining_allocation_ups": float, "wallet_ups": float}

# subscription_cycle_reset
{"human_id": str, "tier": str, "cycles_per_month": int}

# mvp_bid_submitted
{"bid_ups": int}

# mvp_offering_resolved
{"total_injection_ups": int}

# ups_allocation_executed
{"human_id": str, "strategy": str, "ups_requested": float, "ups_executed": float, "fi_received": float, "success_count": int, "pending_count": int, "remaining_allocation_ups": float}

# ups_allocation_result
{"human_id": str, "path": str, "ups_allocated": float, "fi_received": float, "fee_paid": float, "order_id": str | null}

# proof_submitted
{"proof_type": str}

# payout_triggered
{"amount": int}

# demurrage_cycle_completed
{"wallets_affected": int, "total_decay_ups": float, "network_pool_delta_ups": float, "pavs_treasury_delta_ups": float}

# pavs_treasury_updated
{"pavs_treasury_balance_ups": float, "network_pool_balance_ups": float, "treasury_health": float}

# treasury_separation_snapshot
{"pavs_treasury_ups": float, "network_pool_ups": float, "fund_pool_ups": float, "foundup_ups_treasury": {str: float}}

# fi_rating_updated
{"rating": {"velocity": float, "traction": float, "health": float, "potential": float, "composite": float}, "border_color": str, "tier_name": str}

# cabr_score_updated
{"env_score": float, "soc_score": float, "part_score": float, "total": float, "threshold": float, "threshold_met": bool, "confidence": float}

# cabr_pipe_flow_routed
{"task_id": str, "foundup_id": str, "assignee_id": str, "pob_validated": bool, "cabr_pipe_size": float, "requested_ups": float, "epoch_release_budget_ups": float, "routed_ups": float, "worker_ups": float, "foundup_treasury_ups": float, "network_pool_ups": float, "pavs_treasury_before_ups": float, "pavs_treasury_after_ups": float}

# agent_joins
{"agent_type": str, "public_key": str, "rank": int, "state": str, "foundup_idx": int}

# agent_awakened
{"coherence": float, "state": str}

# agent_idle
{"inactive_ticks": int, "current_tick": int, "state": str}

# agent_ranked
{"old_rank": int, "new_rank": int, "old_title": str, "new_title": str}

# agent_earned
{"amount": int, "foundup_idx": int, "task_id": str | null}

# agent_leaves
{"public_key": str, "wallet_balance": float}

# fee_collected
{"fee_type": str, "foundup_id": str, "amount_sats": int, "volume_sats": int, "tick": int, "source_ref": str | null, "distribution": {"fi_treasury": int, "network_pool": int, "pavs_treasury": int, "btc_reserve": int}}

# tide_out / tide_in / tide_support_sent / tide_support_received
{"foundup_id": str, "amount_sats": int, "from": str, "to": str, "tick": int, "reason": str}

# sustainability_reached
{"tick": int, "foundup_count": int, "daily_revenue_btc": float, "revenue_cost_ratio": float, "downside_revenue_cost_ratio_p10": float}

# state_sync
{"phase": str, "tick": int, "foundups_count": int, "agents_count": int, "total_fi": float, "lifecycle_stage": str, "filled_blocks": int, "total_blocks": int}

# phase_command
{"target_phase": str, "force": bool}

# synthetic_user_adopted
{"agent_id": str, "foundup_id": str, "confidence": float, "reasons": list[str], "price_sensitivity": float, "viral_coefficient": float, "persona_income": str, "persona_tech": str, "persona_risk": str, "tick": int}

# synthetic_user_rejected
{"agent_id": str, "foundup_id": str, "confidence": float, "reasons": list[str], "persona_income": str, "persona_tech": str, "persona_risk": str, "tick": int}

# smartdao_emergence
{"foundup_id": str, "old_tier": str, "new_tier": str, "adoption_ratio": float, "tick": int}

# tier_escalation
{"foundup_id": str, "old_tier": str, "new_tier": str, "adoption_ratio": float, "treasury_ups": float, "active_agents": int, "tick": int}

# treasury_autonomy
{"foundup_id": str, "tier": str, "treasury_ups": float, "spawning_fund_ups": float, "tick": int, "timestamp": str}

# cross_dao_funding
{"source_dao": str, "target_dao": str, "amount": int, "source_tier": str, "target_tier": str, "tick": int}
```

## Service Contracts

### FrameSchema (animation adapter)

`modules/foundups/simulator/frame_schema.py` defines immutable snapshot contracts consumed by animation clients.

Top-level envelope:
```python
{
  "frame_schema_version": "1.0.0",
  "tick": int,
  "elapsed_seconds": float,
  "foundups": [...],
  "actors": [...],
  "pools": {...},
  "metrics": {...},
  "recent_events": [str]
}
```

Invariant:
- Animation consumers read frame fields only.
- Animation layer does not mutate simulator state or run economic logic.

### Pure-step shadow parity telemetry

`FoundUpsModel` supports an opt-in shadow parity gate (off by default) that runs
immutable `step_pure.step()` alongside runtime tick execution.

Config fields (`SimulatorConfig`):
- `pure_step_shadow_enabled: bool`
- `pure_step_shadow_log_interval: int`
- `pure_step_shadow_max_actor_drift: float`
- `pure_step_shadow_max_pool_drift: float`
- `pure_step_shadow_max_fi_drift: float`

Stats fields (`FoundUpsModel.get_stats()`):
- `pure_step_shadow_checks`
- `pure_step_shadow_failures`
- `pure_step_shadow_last_tick`
- `pure_step_shadow_last_ok`

Parity drift signal:
- Emits daemon event `pure_step_shadow_drift` when configured thresholds are exceeded.

### SSE Server Endpoints

#### GET /api/sim-events
Server-Sent Events stream for simulator/FAMDaemon events.

**Request:**
- Method: `GET`
- Headers: `Accept: text/event-stream`
- Member gate headers (when enabled):
  - `x-invite-key: <secret>` (or query `invite_key=...`)
  - `x-member-role: observer_012|member|agent_trader|admin` (or query `role=...`)

**Response:**
- Content-Type: `text/event-stream`
- Cache-Control: `no-cache`
- Connection: `keep-alive`
- X-Accel-Buffering: `no` (nginx SSE compatibility)

**Event Format:**
```
event: sim_event
id: <sequence_id>
retry: 3000
data: {"event_id": "...", "event_type": "...", "payload": {...}, ...}

```

**Special Events:**
- `event: connected` - Sent on connection with mode and heartbeat interval
- `event: heartbeat` - Sent every 15 seconds for connection keepalive
- `event: error` - Sent on internal server error

#### GET /api/health
Health check endpoint for Cloud Run readiness probes.

**Response:**
```json
{
    "status": "healthy",
    "mode": "simulated" | "live" | "live+simulator",
    "fam_connected": bool,
    "queue_size": int,
    "dropped_events": int,
    "timestamp": "ISO8601"
}
```

#### GET /
Root endpoint with API info.

**Response:**
```json
{
    "service": "FoundUps SSE Server",
    "version": "1.0.0",
    "endpoints": {
        "/api/sim-events": "SSE stream of simulator events",
        "/api/health": "Health check"
    }
}
```

### FAMEventSource
```python
FAMEventSource()
```

**Runtime API:**
- `connect() -> bool`: Connect to FAMDaemon singleton
- `disconnect() -> None`: Disconnect and cleanup
- `get_event(timeout: float = 1.0) -> dict | None`: Get next queued event
- `is_connected -> bool`: Connection status property

**Invariants:**
- Queue bounded to 1000 events (backpressure safety)
- Non-streamable event types filtered at source
- Graceful event drop on queue full (no exception, logged warning)
- Sequence IDs assigned atomically on queue entry

### SimulatedEventSource
```python
SimulatedEventSource()
```

**Runtime API:**
- `generate_event() -> dict | None`: Generate random simulated event

**Invariants:**
- Events generated at 0.5-2.0 second intervals
- Weighted distribution favoring task_state_changed (40%)
- Sequence IDs monotonically increasing
- Uses 'new_status' key for task_state_changed (frontend compatibility)

### BackgroundSimulator
```python
BackgroundSimulator(num_founders=3, num_users=10, tick_rate=2.0)
```

**Runtime API:**
- `start() -> bool`: Start Mesa simulator in background thread
- `stop() -> None`: Stop simulator gracefully (2s join timeout)
- `is_running -> bool`: Running status property

**Architecture:**
- Runs Mesa `FoundUpsModel` in a daemon thread
- Shares FAMDaemon singleton with SSE server (same process)
- Events flow: Mesa Model → FAMDaemon.emit() → FAMEventSource queue → SSE stream

**Invariants:**
- Background thread is daemon (dies with main process)
- Error in simulation loop sleeps 1s to prevent tight loop
- Graceful shutdown via `_running` flag + thread join

## Sequence ID Semantics

1. **Monotonic Ordering**: Sequence IDs are strictly increasing (no gaps)
2. **Reconnect Deduplication**: Client tracks `lastSequenceId` to skip already-processed events
3. **Heartbeat Exception**: Heartbeat events use `sequence_id: 0` (not counted)
4. **Source Isolation**: FAMEventSource and SimulatedEventSource maintain separate counters

## Heartbeat Protocol

- **Interval**: 15 seconds (`SSE_HEARTBEAT_INTERVAL`)
- **Purpose**: Keep connection alive through proxies/load balancers
- **Payload**: `{"timestamp": "ISO8601", "mode": "simulated"|"live"}`
- **Client Retry**: 3000ms (`SSE_RECONNECT_RETRY`)

## CORS Configuration

Allowed origins:
- `https://foundups.com` (production)
- `https://foundupscom.web.app` (Firebase preview)
- `https://foundupscom.firebaseapp.com` (Firebase hosting)
- `http://localhost:5000` (local dev)
- `http://127.0.0.1:5000` (local dev)

Allowed methods: `GET` only
Credentials: Allowed

## Backpressure Safety

**Queue Bounds:**
- `asyncio.Queue(maxsize=1000)` prevents unbounded memory growth
- On queue full: event dropped, warning logged
- Dropped event counter available via `_dropped_event_count` (observability)

**Client Reconnect:**
- Exponential backoff with jitter: `min(30000, base * 1.5^attempts + random(0, 1000))`
- Base delay: 2000ms
- Max delay: 30000ms
- Max attempts: 5

## Deployment

**Environment Variables:**
- `PORT`: Server port (default: 8080)
- `FAM_MEMBER_GATE_ENABLED`: `1` to enforce invite-only access on `/api/sim-events`
- `FAM_MEMBER_INVITE_KEY`: Shared invite key for member-gated endpoints
- `FAM_MEMBER_GATE_ALLOW_LOCAL_BYPASS`: `1` allows localhost bypass for dev
- `FAM_MEMBER_GATE_PROTECT_HEALTH`: `1` also gates `/api/health`
- `FAM_MEMBER_ALLOWED_ROLES`: Comma-separated role allowlist

**Modes:**
| Mode | Command | Description |
|------|---------|-------------|
| Simulated | `--simulate` | Random fake events (demo/fallback) |
| Live | (default) | Connects to existing FAMDaemon |
| Live+Simulator | `--run-simulator` | Mesa model in-process, real events |

**Local Development:**
```bash
# Simulated events (no dependencies)
python -m modules.foundups.simulator.sse_server --simulate

# Live simulator → SSE → Web Animation
python -m modules.foundups.simulator.sse_server --run-simulator -v

# Custom simulator config
python -m modules.foundups.simulator.sse_server -r --founders 5 --users 20 --speed 4.0
```

**Web Animation Integration:**
```
http://localhost:5000?sim=1        # Firebase local dev with SSE
public/index.html?sim=1           # Direct file with SSE
public/index.html?sse_url=<url>   # Custom SSE endpoint
```

**Cloud Run Configuration:**
- Designed for Cloud Run deployment (like chat endpoint)
- Long-lived connections supported
- X-Accel-Buffering disabled for nginx compatibility
- Deploy: `./deploy-sse.sh`

**Production:**
```bash
python sse_server.py --run-simulator --port $PORT
```

## Frontend Integration

**Event Bridge Configuration:**
```javascript
const simBridge = {
    endpoint: '/api/sim-events',  // Cloud Run URL in production
    reconnectDelay: 2000,
    maxReconnectAttempts: 5,
    lastSequenceId: 0,  // Track for dedup on reconnect
};
```

**Event Handling:**
```javascript
// Handles both new format and legacy format
function handleSimulatorEvent(simEvent) {
    const eventType = simEvent.event_type || simEvent.type;
    const eventData = simEvent.payload || simEvent.data || {};
    // ...
}
```

## WSP References

- **WSP 50**: Pre-action verification (event deduplication)
- **WSP 22**: ModLog documentation
- **WSP 11**: API stability (backward-compatible event format)
- **WSP 72**: Module independence (SSE server standalone)
