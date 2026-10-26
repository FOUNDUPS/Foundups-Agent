# FoundUps Simulator

Visual simulation of the autonomous FoundUp ecosystem.

## Work, stake and unstake numeric validation — 2026-10-25

Selected economic operations now reject invalid quantities, mutable fees and
overflowing prospective balances before participating mutations. Existing finite
fee math, zero/fractional values and public signatures remain. A small private
scalar owner shares preparation formulas with standalone mutators. See the
[contract](INTERFACE.md#selected-economic-numeric-admission) and
[allocated plan](../../../docs/architecture/FOUNDUPS_NUMERIC_ADMISSION_20261025.md).
This is simulation arithmetic validation; asset units, aggregate issuance policy
and funded blockchain settlement remain separate work.

## Mock BTC anchor integrity — 2026-10-25

The existing optional connector now binds each FoundUp/epoch to the full known
`foundups.epoch.v2` payload and its fixed mock realm. SQLite serializes admission;
conflicting content, unknown legacy identity and unresolved records cannot be
overwritten or reported as successful retries. Legacy rows stay visible and
unclassified. Exact same-content mock force republication remains supported.

Only mock mode is implemented. Testnet/mainnet selection rejects before database
initialization, regardless of `LAYER_D_ENABLED`; invalid Mesa modes never select
mock implicitly. Mock confirmation counts are simulation. There is no real BTC
publisher, signer, network confirmation or funded reward transfer. See the
[connector contract](INTERFACE.md#mock-btc-anchor-contract) and
[allocated plan](../../../docs/architecture/FOUNDUPS_BTC_ANCHOR_INTEGRITY_20261025.md).

## Epoch commitment integrity — 2026-10-25

The existing epoch ledger now uses `foundups.epoch.v2` context-bound hashes,
immutable snapshots and atomic exact retries. Merkle verification requires an
externally trusted root, FoundUp, epoch and participant; a proof's own root is
not an authority source. Repeated commitment preparation retains its finalized
timestamp. See [INTERFACE.md](INTERFACE.md#epoch-evidence-contract) for encoding
and compatibility. This is process-local pre-settlement evidence, not a funded
balance, unique work-receipt consumption or confirmed payment. Old BTC connector
records have not been migrated to this changed hash format.

## FAM authorization compatibility — 2026-10-25

The FAM bridge supplies explicit host-configured simulation identities
`verifier_0` and `treasury_0` with exact per-FoundUp grants. Changing the wrapper's
requested actor ID does not create matching authority. FAM enforces stored proof
binding and independent verification; simulation completion is not on-chain
settlement or production authentication. See [the FAM contract](../agent_market/INTERFACE.md#taskpipelineservice).

## Planning References
- `modules/foundups/simulator/ROADMAP.md`
- `modules/foundups/docs/OCCAM_LAYERED_EXECUTION_PLAN.md`
- `modules/foundups/docs/CONTINUATION_RUNBOOK.md`

## Economics Documentation

### F_i Exit Fee System (2026-02-17)
- **Analysis**: `economics/FI_EXIT_SCENARIOS.md` - Full dialectic analysis of 5 fee models
- **Simulation**: `economics/exit_scenario_sim.py` - Monte Carlo comparison
- **Dynamic Taper**: `economics/dynamic_fee_taper.py` - Float system (fees adjust with reserve)

**Recommended Model**: HYBRID (creation fee + vesting + dynamic taper)
- Protocol capture: 22.4% average
- Protects against miner dumps (25.7% capture)
- Rewards long-term holders
- Self-regulating (fees drop as reserve strengthens)

```bash
# Run exit scenario simulation
python modules/foundups/simulator/economics/exit_scenario_sim.py

# Run dynamic fee taper demo
python modules/foundups/simulator/economics/dynamic_fee_taper.py
```

**WSP Reference**: WSP 26 Section 14.11

### 10-Year Projection Hardening (2026-02-17)
- Projection source: `economics/ten_year_projection.py`
- Export includes:
  - gross/protocol/platform fee lanes
  - downside/base/upside confidence ratios
  - market-calibrated daily volume (`raw` vs `adjusted`)
  - compute graph payload for litepaper (`compute_graph`)

## CABR Canonical Intent

- CABR = Consensus-Driven Autonomous Benefit Rate (also referred to as Collective Autonomous Benefit Rate).
- WHY: CABR exists to power Proof of Benefit (PoB).
- HOW: Collective 0102 consensus determines CABR (consensus-driven process).
- CABR = pipe size (flow rate), PoB validation = valve.
- RESULT: PoB drives protocol allocation/distribution; ROI is a downstream financial readout.

## Architecture

```
FAMDaemon (SSoT)
    ↓ emits events
event_bus.py
    ↓ normalizes
state_store.py (renderable state)
    ↓ reads
render/
├── terminal_view.py (ASCII grid - default)
├── cube_view.py (3D ASCII cube animation)
└── pygame_view.py (optional pixel art)

mesa_model.py (agent behaviors)
    ↓ calls
adapters/fam_bridge.py
    ↓ uses
FAM modules (no new logic)
```

## Key Principles

1. **FAMDaemon events = Single Source of Truth (SSoT)**
2. **state_store derives renderable state from event stream**
3. **Render layer reads ONLY from state_store**
4. **Adapters bridge to FAM contracts; only deterministic simulation hardening is allowed**
5. **Phantom plugs ONLY where logic is missing**

## Build Lifecycle Coverage

Simulator pipeline now covers full task progression:

1. `open -> claimed` via `UserAgent` and `FAMBridge.claim_task()`
2. `claimed -> submitted` via `FoundUpsModel._advance_task_pipeline()`
3. `submitted -> verified` via `FoundUpsModel._advance_task_pipeline()`
4. `verified -> paid` via `FoundUpsModel._advance_task_pipeline()`
5. milestone publication via `FAMBridge.publish_milestone()`

Primary wiring:

- `adapters/fam_bridge.py`: proof/verification/payout/milestone wrappers
- `mesa_model.py`: per-tick lifecycle advancement loop
- `step_core.py`: pure tick scheduler (`compute_step_decision`)
- `step_pipeline.py`: orchestration executor consuming scheduler decisions
- `state_contracts.py`: immutable simulation contracts (`SimState`, `ActorState`, `FoundUpState`)
- `step_pure.py`: side-effect-free `step(current_state, params, ...)` evolution path
- `tests/test_fam_lifecycle_flow.py`: deterministic lifecycle verification
- `tests/test_f0_mvp_offering_flow.py`: F_0 subscription -> MVP bid -> treasury injection verification
- `tests/test_allocation_and_treasury_runtime.py`: 012 allocation + pAVS treasury telemetry runtime wiring

FoundUps lifecycle policy in simulator:

- `PoC`: no paid task yet.
- `Proto`: at least one paid task (delivery proven).
- `MVP`: paying customers arrive (`customer_count >= 1`) after delivery. This is the beta launch threshold.

Investment and exchange model:

- `F_0` is the only investor source. Seed BTC enters once (`investor_funding_received` with `foundup_id=F_0`).
- Investor subscriptions accrue at `200 UPS/term` with a `max 5 terms` hoard (`mvp_subscription_accrued`).
- Proto-stage FoundUps accept UPS bids for MVP pre-launch access (`mvp_bid_submitted`).
- Winning bids inject UPS treasury capital into the target FoundUp (`mvp_offering_resolved`).
- F_i decentralized exchange trades remain continuous (`fi_trade_executed` events).

012 allocation + pAVS telemetry:

- User agents are bootstrapped as 012 subscription accounts (tiered `spark/explorer/builder/founder`).
- Subscription refresh emits `subscription_allocation_refreshed`; monthly rollovers emit `subscription_cycle_reset`.
- 0102 allocation batches emit `ups_allocation_executed` plus per-FoundUp `ups_allocation_result`.
- Demurrage cycles emit `demurrage_cycle_completed`, `pavs_treasury_updated`, and `treasury_separation_snapshot`.
- Treasury separation is explicit in events/stats: system pAVS treasury vs per-FoundUp UPS treasury lanes.

Compute access/paywall simulation direction:
- FAM paywall design is specified in `modules/foundups/agent_market/docs/COMPUTE_ACCESS_PAYWALL_SPEC.md`.
- Simulator scenario packs should test PoB yield under metered compute assumptions before production pricing.

## Usage

```bash
# Run with defaults (3 founders, 10 users, 2 ticks/sec)
python -m modules.foundups.simulator.run

# Run for 1000 ticks then stop
python -m modules.foundups.simulator.run --ticks 1000

# Customize agents and speed
python -m modules.foundups.simulator.run --founders 5 --users 20 --speed 4.0

# Verbose logging
python -m modules.foundups.simulator.run --verbose

# Scenario runner (manifest + metrics + frame snapshots)
python -m modules.foundups.simulator.scenario_runner --scenario baseline --ticks 500 --frame-every 10

# Monte Carlo batch
python -m modules.foundups.simulator.scenario_runner --scenario high_adoption --ticks 300 --monte-carlo 5

# Downside/base/upside confidence-band matrix (claim gate audit)
python -m modules.foundups.simulator.sustainability_matrix --ticks 1500 --runs 9
```

Scenario runner notes:
- Each run uses an isolated FAM daemon store (`<out>/<run_label>_fam_daemon`) to avoid cross-run state bleed.
- `frame_digest_sha256` is computed from a deterministic frame projection (state + pools + metrics), excluding volatile render fields.
- Sustainability claims are gated by downside scenario p10 pass on platform-capture lane (`downside_revenue_cost_ratio_p10 >= 1.0`).

## Configuration

Edit `config.py` to adjust:
- Number of agents
- Per-founder creation cap (`founder_max_foundups`, default `3`)
- Tick rate (simulation speed)
- Random seed (determinism)
- Viewport size
- Pure-step shadow parity gate (`pure_step_shadow_*` fields)

Pure-step shadow mode (disabled by default):
- Runs immutable `step_pure.step()` in parallel with runtime tick execution.
- Compares predicted vs runtime state on actor tokens, pool balances, and F_i totals.
- Updates simulator stats: `pure_step_shadow_checks`, `pure_step_shadow_failures`,
  `pure_step_shadow_last_tick`, `pure_step_shadow_last_ok`.
- Emits `pure_step_shadow_drift` event to the daemon only when drift exceeds configured
  thresholds.

## Views

### Terminal View (Default)
- Top: FoundUp Mall grid (tiles with likes/tokens)
- Bottom: FAMDaemon event log + agent states

```bash
python -m modules.foundups.simulator.run
```

### Cube View (3D Animation)
- Isometric ASCII cube that builds up as agents work
- Agents colored by WSP 15 priority level (P0-P4)
- Phase-based story: SCAFFOLD → BUILD → PROMOTE → STAKING → CUSTOMERS → LAUNCH
- Scrolling ticker with event notifications
- Agent behaviors: spazzing, recruiting, level-ups

```bash
python -m modules.foundups.simulator.run --cube
```

**WSP References for Cube View:**
- WSP 15: Build Order (priority levels P0-P4)
- WSP 27: Color System (Red=P0, Orange=P1, Yellow=P2, Green=P3, Blue=P4)
- WSP 54: Agent Roles (Founder ★, Coder $, Designer +, Tester v, Promoter >, Investor B)

### Pygame View (Optional)
- Pixel tiles with interaction glow
- HUD panel with token flow
- Scrollable event log

### SSE Server (Web Frontend Integration)

Streams simulator events to the web frontend cube animation at foundups.com:

```bash
# Run SSE server with simulated events (no FAMDaemon)
python -m modules.foundups.simulator.sse_server --port 8080 --simulate

# Run SSE server connected to FAMDaemon
python -m modules.foundups.simulator.sse_server --port 8080

# Health check
curl http://localhost:8080/api/health

# Stream events (SSE)
curl -N http://localhost:8080/api/sim-events
```

**Endpoints:**
- `GET /api/sim-events` - SSE stream of normalized events
- `GET /api/health` - Health check with mode status
- `GET /` - API info

**Member Gate (invite-only access):**
- `FAM_MEMBER_GATE_ENABLED=1` enables fail-closed gating on `/api/sim-events`
- `FAM_MEMBER_INVITE_KEY=<secret>` required as `x-invite-key` header (or `?invite_key=`)
- Optional role header: `x-member-role` (`observer_012`, `member`, `agent_trader`, `admin`)
- Optional localhost bypass for development: `FAM_MEMBER_GATE_ALLOW_LOCAL_BYPASS=1`
- Optional health protection: `FAM_MEMBER_GATE_PROTECT_HEALTH=1`

**Event Types Streamed:**
- `foundup_created`, `task_state_changed`, `fi_trade_executed`
- `order_placed`, `order_cancelled`, `order_matched`, `price_tick`, `orderbook_snapshot`
- `investor_funding_received`, `mvp_subscription_accrued`
- `mvp_bid_submitted`, `mvp_offering_resolved`, `milestone_published`

**Documentation:**
- [INTERFACE.md](INTERFACE.md) - SSE endpoint contract, event schemas, CORS config
- [docs/WSP_ALIGNMENT_CUBE_SSE_EARNINGS.md](/docs/WSP_ALIGNMENT_CUBE_SSE_EARNINGS.md) - Full integration spec

**Cloud Run Deployment:**

Deploy to Cloud Run for production use with Firebase Hosting:

```bash
# From this directory
./deploy-sse.sh

# Or manually:
gcloud run deploy sse-foundups \
    --source . \
    --project gen-lang-client-0061781628 \
    --region us-central1 \
    --platform managed \
    --allow-unauthenticated
```

After deployment, update `firebase.json` to add the SSE rewrites:

```json
"rewrites": [
  {
    "source": "/api/sim-events",
    "run": { "serviceId": "sse-foundups", "region": "us-central1" }
  },
  {
    "source": "/api/health",
    "run": { "serviceId": "sse-foundups", "region": "us-central1" }
  },
  { "source": "**", "destination": "/index.html" }
]
```

**Testing SSE on Web Frontend:**
- Local: `http://localhost:5000/?sse=1` (requires local SSE server)
- Production: `https://foundups.com/?sse=1` (after Cloud Run deployment)
- Custom endpoint: `?sse=1&sse_url=http://localhost:8080/api/sim-events`

## Agent Types

- **FounderAgent**: Creates FoundUps via TokenFactory + Foundup model
- **UserAgent**: Like/follow/stake behaviors using FAM interfaces

## Agent Lifecycle (01(02) → 0102 → 01/02)

Agents transition through three states based on activity and coherence:

```
  01(02) DORMANT           0102 ZEN STATE           01/02 DECAYED
  ┌─────────────┐         ┌─────────────┐          ┌─────────────┐
  │ Agent joins │ ──first─→│   Active    │ ──idle─→ │    IDLE     │
  │ public key  │  action │ coherence≥0.618        │ awaiting ORCH
  │ rank: 1     │         │ rank: 1-7   │          │              │
  └─────────────┘         └─────────────┘          └─────────────┘
```

### Agent Events

| Event | State | Trigger |
|-------|-------|---------|
| `agent_joins` | 01(02) | Agent created |
| `agent_awakened` | 0102 | First successful action |
| `agent_idle` | 01/02 | Inactivity > 100 ticks |
| `agent_ranked` | - | Earnings threshold crossed |
| `agent_earned` | - | Task payout credited |
| `agent_leaves` | - | Agent exits with wallet |

### Rank System (1-7)

| Rank | Title | Earnings Threshold |
|------|-------|--------------------|
| 1 | Apprentice | 0 |
| 2 | Builder | 100 |
| 3 | Contributor | 500 |
| 4 | Validator | 2000 |
| 5 | Orchestrator | 5000 |
| 6 | Architect | 10000 |
| 7 | Principal | 20000 |

See `modules/foundups/agent/` for full documentation.

## Event Flow

1. Mesa model steps agents
2. Agents call FAM adapters (fam_bridge.py)
3. FAM modules emit events to FAMDaemon
4. event_bus captures and normalizes events
5. state_store updates renderable state
6. Render reads state_store and draws

## Token Economics (WSP 26)

The simulator implements the full token economics model from WSP 26:

### Pool Distribution
```
Stakeholders: 80%
├── Un (0-Pool):  60%  (customers)
├── Dao (1-Pool): 16%  (team members)
└── Du (2-Pool):   4%  (founders)
Network: 20%
├── Network: 16%  (drip rewards)
└── Fund:     4%  (held)
```

### Digital Twin Model
- Humans are represented by their 0102 digital twin in the system
- Type (0/1/2) set at entry: Customer/Team/Founder
- Activity (0/1/2) dynamic based on work done

### Degradation Mechanics
- No work for X epochs → Activity drops automatically
- Inactive founder "20" earns 3.2% vs active team member "12" at 60.8%
- Engagement matters more than title

### Elevation Governance
- Digital twin recommends elevation based on work contribution
- Founder(s) approve → Type upgrade applied
- Prevents hostile takeovers while rewarding contributors

### Simulator Tests
1. Activity degradation curves
2. Elevation threshold tuning
3. Multi-founder reward splitting
4. Abandoned project scenarios
5. Pool math verification

## Usage (Token Economics)

```python
from modules.foundups.simulator.adapters.metagpt_adapter import (
    SwarmFoundUp, AgentSpecialization, ParticipantType, ActivityLevel
)

# Create FoundUp with digital twin swarm
foundup = SwarmFoundUp(
    foundup_id="test_001",
    name="TestFoundUp",
    domain="test",
    degradation_threshold=3,  # Epochs before degradation
    elevation_work_threshold=100.0,  # Work units for elevation
)

# Register participants (represented by digital twins)
foundup.register_human("alice", ParticipantType.DU, ActivityLevel.UN, 1000.0)
foundup.register_human("bob", ParticipantType.DAO, ActivityLevel.UN, 500.0)

# Register agent swarm
foundup.register_agent("agent_1", AgentSpecialization.CODE, "alice", 100.0)
foundup.register_agent("agent_2", AgentSpecialization.CODE, "bob", 100.0)

# Run simulation epochs
result = foundup.run_epoch()
print(f"Degraded: {result['degraded']}")
print(f"Elevation queue: {result['elevation_queue']}")
```

## Subscription Tiers (WSP 26 Section 4.9)

The simulator implements the full Freemium → Premium gamification loop:

### Tier Structure
| Tier | Price | Allocation | Cycles/Month | Effective | Fee Discount |
|------|-------|------------|--------------|-----------|--------------|
| Free | $0 | 1x | 1 | 1x | 0% |
| Spark | $2.95 | 2x | 2 | 4x | 10% |
| Explorer | $9.95 | 3x | 3 | 9x | 25% |
| Builder | $19.95 | 5x | 5 | 25x | 40% |
| Founder | $49.95 | 10x | 30 | ~300x | 60% |

### The Gamification Loop
```
User plays → uses allocated UPS to stake in FoundUps
  → UPS runs out (remaining_allocation = 0)
    → Motivation: Subscribe to Spark → 4x more UPS
      → Plays more → runs out again
        → Motivation: Upgrade to Explorer → 9x more UPS
          → Subscription revenue → BTC reserve → currency strengthens
```

### Usage (Subscription Testing)

```python
from modules.foundups.simulator.economics import (
    HumanUPSAccount, SubscriptionTier, SUBSCRIPTION_TIERS
)

# Create free-tier user
alice = HumanUPSAccount(human_id="alice")
print(f"Tier: {alice.subscription_tier.value}")  # "free"
print(f"Allocation: {alice.remaining_allocation}")  # 100.0 (base)

# Use UPS - gamification loop in action
alice.use_allocated_ups(80.0)  # Stake in FoundUps
alice.use_allocated_ups(30.0)  # FAILS - insufficient, triggers upgrade motivation

# User subscribes to Spark ($2.95/mo)
alice.upgrade_subscription(SubscriptionTier.SPARK)
print(f"New allocation: {alice.remaining_allocation}")  # 200.0 (2x base)

# Get subscription benefits
config = alice.get_subscription_config()
print(f"Effective monthly: {config.effective_monthly_multiplier}x")  # 4x
print(f"Staking fee discount: {config.staking_fee_discount * 100}%")  # 10%

# Refresh allocation (bi-weekly for Spark)
alice.refresh_allocation()  # +200 UPS (cycle 2/2)

# At month boundary
alice.reset_monthly_cycles()  # Reset to cycle 0
```

### FoundUp Token Mining (Bitcoin 2009 Analogy)
```python
# Agent "mines" FoundUp Tokens by completing work
# This is like Bitcoin mining in 2009 - early miners earn more
# Token release follows ADOPTION CURVE (S-curve), not discrete tiers

from modules.foundups.simulator.economics import (
    TokenEconomicsEngine, FoundUpTokenPool, adoption_curve
)

engine = TokenEconomicsEngine()
pool = engine.register_foundup("gotjunk_001")

# At Genesis: 0% adoption = 0% of 21M released
print(f"Initial adoption: {pool.adoption_score:.2%}")  # 0%
print(f"Available: {pool.available_supply:,.0f}")  # 0

# Growth increases adoption score (continuous, not discrete tiers)
pool.update_adoption(users=100, revenue_ups=10000, work_completed=500, milestone=True)
print(f"Adoption: {pool.adoption_score:.2%}")  # ~35%
print(f"Available: {pool.available_supply:,.0f}")  # ~2.5M tokens

# 0102 workers mine by completing work
minted = pool.mint_for_work(1000.0, "code_agent_1")
print(f"Minted: {minted}")  # 1000.0 FoundUp Tokens

# The S-curve naturally gates token release:
# 10% adoption = 0.57% released (120K tokens)
# 50% adoption = 50% released (10.5M tokens)
# 100% adoption = 100% released (21M tokens)
```

### Two Types of F_i Tokens (Critical Distinction)

The system distinguishes between TWO types of F_i tokens with different exit fees:

| F_i Type | Source | Exit Fee | Purpose |
|----------|--------|----------|---------|
| **MINED F_i** | Agent work (`mint_for_work`) | 11% | Discourages extraction, keeps value in ecosystem |
| **STAKED F_i** | UPS investment (`stake_ups`) | 5% | Value preservation (1:1 backed by UPS) |

```python
from modules.foundups.simulator.economics import TokenEconomicsEngine, FeeConfig

engine = TokenEconomicsEngine()
human = engine.register_human("alice", initial_ups=1000.0)
pool = engine.register_foundup("gotjunk_001")
pool.update_adoption(users=50, revenue_ups=5000)  # Grow to ~40% adoption

# STAKED F_i: User stakes UPS for value preservation
# 3% entry fee + 5% exit fee = 8% total round-trip
fi_received, entry_fee = engine.human_stakes_ups("alice", "gotjunk_001", 500.0)
print(f"Staked 500 UPS -> {fi_received:.2f} STAKED F_i (entry fee: {entry_fee:.2f})")

# Later: unstake to get UPS back (minus 5% exit fee)
ups_back, exit_fee = engine.human_unstakes_fi("alice", "gotjunk_001", fi_received)
print(f"Unstaked -> {ups_back:.2f} UPS (exit fee: {exit_fee:.2f})")
# Total lost: ~8% (value mostly preserved)

# MINED F_i: Agent earns by doing work, higher exit fee
# Agent completes task, human receives MINED F_i
agent = engine.register_agent("agent_1", "alice")
engine.human_allocates_to_agent("alice", "agent_1", 100.0)
success, fi_mined = engine.agent_completes_task("agent_1", "gotjunk_001", 10.0, 200.0)

# When human extracts MINED F_i -> 11% fee (discourages extraction)
ups_received, fees = engine.human_converts_mined_fi_to_ups("alice", "gotjunk_001", fi_mined)
print(f"Extracted {fi_mined:.2f} MINED F_i -> {ups_received:.2f} UPS (11% fee: {fees['total']:.2f})")
```

### Fee Configuration Simulation

The simulator lets you test different fee structures to find optimal parameters:

```python
from modules.foundups.simulator.economics import (
    FeeScenario, run_scenario, compare_scenarios, print_comparison
)

# Run predefined scenarios
results = compare_scenarios()
print_comparison(results)

# Or create custom scenarios
custom_scenario = FeeScenario(
    name="My Custom Fees",
    mined_exit_fee=0.08,  # 8% on MINED F_i extraction
    staked_entry_fee=0.02,  # 2% on staking entry
    staked_exit_fee=0.04,  # 4% on unstaking exit
)

result = run_scenario(
    custom_scenario,
    num_humans=20,
    num_foundups=5,
    num_epochs=24,  # 2 years
    ups_per_epoch=2000.0
)

print(f"Value preserved: {result.value_preserved_pct:.1f}%")
print(f"Extraction rate: {result.mined_extraction_rate:.1f}%")
print(f"BTC vault accumulated: {result.btc_vault_total:.2f}")
```

### Demurrage Warning System

UPS in wallets decays over time (demurrage). Staked UPS (as F_i) does NOT decay:

```python
from modules.foundups.simulator.economics import HumanUPSAccount

alice = HumanUPSAccount(human_id="alice")
alice.ups_balance = 500.0  # Sitting in wallet

# Check for warnings
warning = alice.get_demurrage_warning()
if warning:
    print(warning)  # "WARNING: 500.0 UPS is DECAYING! Stake into a FoundUp..."
```

## BTC Reserve - The "Hole in the Bucket"

FoundUps is a Bitcoin sink - BTC flows IN but NEVER flows OUT (Hotel California).

### BTC Sources
| Source | Description |
|--------|-------------|
| **Subscriptions** | Monthly payments → Buy BTC → Reserve |
| **Demurrage** | Decayed UPS → Burned → BTC backing stays |
| **Mined Exit Fees** | 11% fee → BTC vault |
| **Staked Exit Fees** | 5% fee → BTC vault |
| **Trading Fees** | 2% on F_i orderbook → BTC vault |
| **Cashout Fees** | 7% on UPS → external → BTC vault |

```python
from modules.foundups.simulator.economics import (
    BTCReserve, BTCSourceType, get_btc_reserve
)

# Get the singleton BTC Reserve
reserve = get_btc_reserve()

# Subscription payment adds BTC
btc_added = reserve.receive_subscription_payment(49.95, "alice")  # Founder tier
print(f"Added {btc_added:.8f} BTC to reserve")

# Check reserve stats
print(f"Total BTC: {reserve.total_btc:.8f}")
print(f"UPS capacity: {reserve.ups_capacity:,.2f}")
print(f"Backing ratio: {reserve.backing_ratio:.2%}")
```

## F_i Token Order Book

Buy/sell F_i tokens when supply is scarce or users want to trade:

```python
from modules.foundups.simulator.economics import (
    OrderBookManager, FiOrderBook
)

manager = OrderBookManager(trading_fee_rate=0.02)  # 2% fee

# User wants to BUY F_i tokens
order, trades = manager.place_buy(
    foundup_id="gotjunk_001",
    human_id="alice",
    price=1.5,  # Max UPS per F_i willing to pay
    quantity=100.0  # F_i wanted
)

# Another user offers to SELL
order, trades = manager.place_sell(
    foundup_id="gotjunk_001",
    human_id="bob",
    price=1.4,  # Min UPS per F_i
    quantity=50.0  # F_i offered
)

# If prices cross, trades execute automatically
for trade in trades:
    print(f"Trade: {trade.quantity} F_i @ {trade.price} (fee: {trade.fee_ups})")

# All trading fees → BTC Reserve
```

## Demurrage (Bio-Decay)

UPS in wallets decays over time using Michaelis-Menten kinetics:

### Token States (ICE/LIQUID/VAPOR)
| State | Location | Decay | Action |
|-------|----------|-------|--------|
| **LIQUID** | Wallet | 0.5%-5%/month adaptive | Transact or stake! |
| **ICE** | Staked in FoundUp | NONE | Earns yield, frozen |
| **VAPOR** | Exited to external | 15% fee | BTC locked forever |

```python
from modules.foundups.simulator.economics import (
    DemurrageEngine, DecayConfig, DECAY_RELIEF_ACTIVITIES
)

# Create engine with default config
engine = DemurrageEngine()

# Register wallet
engine.register_wallet("alice", initial_balance=1000.0)

# After 7 days of inactivity, check decay
decay_amount, new_balance = engine.apply_decay("alice", time_elapsed_days=7)
print(f"Decayed: {decay_amount:.2f} UPS -> new balance: {new_balance:.2f}")

# Get decay warning
warning = engine.get_decay_warning("alice")
if warning:
    print(warning)  # "WARNING: 950 UPS is decaying at 0.12%/day..."

# Activities that reset decay timer
print(DECAY_RELIEF_ACTIVITIES)
# {'list_item': {'relief_hours': 24, 'reward': 1.0}, ...}

# After activity, reset timer
engine.reset_activity("alice")  # Stops decay acceleration
```

### Decay Formula
```
λ(t) = λ_min + (λ_max - λ_min) · (D / (K + D))
U(t) = U₀ · e^(-λ(t)·t)

Where:
  D = days inactive
  K = 7 (half-maximal constant)
  λ_min = 0.0167%/day (0.5%/month)
  λ_max = 0.167%/day (5%/month)
```

## Complete Economic Flow

```
                         ┌─────────────────────────────────────┐
                         │        CIRCUIT BREAKER              │
                         │  (pauses exits if backing < 80%)    │
                         └─────────────────────────────────────┘
                                          │
Subscription $ ────┐                      │
                   │                      ▼
Demurrage decay ───┼──> BTC Reserve (Hotel California)
                   │         │
Exit fees ─────────┤         ├──> 10% → Emergency Reserve
                   │         │
Trading fees ──────┘         ▼
                      UPS = f(BTC Reserve)
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
   LIQUID (wallet)    ICE (staked)         VAPOR (exit)
   (2%/mo max decay)  (frozen, yield)      (via bonding curve)
        │                    │                    │
        │                    │                    ▼
        │                    │            RAGE QUIT available
        │                    │            if FoundUp failing
        │                    │            (2% fee vs 11%)
        │                    │
        └───── BONDING CURVE ─────────────────────┘
               (guaranteed liquidity, no orderbook)
```

## Safety Mechanisms

The simulator implements anti-fragile safety mechanisms based on DeFi research.

### Circuit Breaker (ERC-7265 inspired)

Prevents Terra-style death spirals by detecting and responding to stress:

```python
from modules.foundups.simulator.economics import (
    CircuitBreaker, BreakerState, get_circuit_breaker
)

# Get singleton circuit breaker
breaker = get_circuit_breaker()

# Check conditions (call periodically)
state = breaker.check_conditions(
    backing_ratio=0.75,  # 75% backed
    current_btc_price=85000.0
)

# States: NORMAL → CAUTION → RESTRICTED → EMERGENCY
if breaker.exits_blocked():
    print("Exits paused - emergency mode")
elif breaker.must_queue_exit():
    queued = breaker.queue_exit("alice", "foundup_001", 100.0)
    print(f"Exit queued: {queued}")
else:
    print("Exits allowed normally")

# Demurrage adjusts based on state
multiplier = breaker.get_demurrage_multiplier()
# NORMAL: 1.0, CAUTION: 0.5, RESTRICTED: 0.25, EMERGENCY: 0.0
```

### Bonding Curve (Bancor-style AMM)

Guarantees liquidity - no counterparty needed, no orderbook illiquidity:

```python
from modules.foundups.simulator.economics import (
    FiBondingCurve, BondingCurveManager
)

# Create manager for all FoundUps
manager = BondingCurveManager()

# Initialize a curve with starting liquidity
curve = manager.get_or_create_curve(
    "foundup_001",
    initial_ups=1000.0,  # UPS seeding the curve
    initial_price=1.0    # Starting price
)

# Always-available buy (no counterparty needed)
fi_received, fee = manager.buy("foundup_001", 100.0, "alice")
print(f"Bought: {fi_received:.2f} F_i (fee: {fee:.2f})")

# Always-available sell (guaranteed exit)
ups_received, fee = manager.sell("foundup_001", 50.0, "alice")
print(f"Sold: {ups_received:.2f} UPS (fee: {fee:.2f})")

# Check slippage before large trade
slippage = curve.get_slippage(1000.0, is_buy=True)
print(f"Slippage for 1000 UPS buy: {slippage*100:.1f}%")
```

### Rage Quit (Moloch DAO-style)

Fair exit when a FoundUp is failing - 2% fee vs normal 11%:

```python
from modules.foundups.simulator.economics import (
    RageQuitAdapter, FailureReason, get_rage_quit_adapter
)

# Get singleton adapter
rage_quit = get_rage_quit_adapter()

# Register FoundUp for health tracking
rage_quit.register_foundup(
    "foundup_001",
    treasury_value_ups=10000.0,
    total_fi_supply=5000.0,
    current_epoch=0
)

# Simulate 12 epochs of no activity
for epoch in range(1, 13):
    rage_quit.advance_epoch("foundup_001", epoch)

# After 12 epochs inactive, check eligibility
available, reason = rage_quit.is_rage_quit_available("foundup_001")
if available:
    # Exit at pro-rata value with 2% fee (vs 11% normal)
    result = rage_quit.rage_quit("alice", "foundup_001", 100.0)
    print(f"Rage quit: {result.fi_burned} F_i -> {result.ups_received:.2f} UPS")
    print(f"Reason: {result.failure_reason.value}")  # "no_activity"
```

### Emergency Reserve (Ethena-style)

10% of all fees go to emergency fund, deployed only during crisis:

```python
from modules.foundups.simulator.economics import (
    EmergencyReserve, ReserveSourceType, get_emergency_reserve
)

# Get singleton reserve
reserve = get_emergency_reserve()

# Collect 10% of every fee (called by fee handlers)
main_portion = reserve.collect_from_fee(
    fee_btc=0.001,
    source=ReserveSourceType.MINED_EXIT_FEE,
    foundup_id="foundup_001"
)
# 0.0001 BTC goes to emergency reserve, 0.0009 to main reserve

# Check health score (0-1)
score = reserve.get_health_score()
print(f"Reserve health: {score:.0%}")

# Deploy during crisis (only when circuit breaker active)
if reserve.can_deploy():
    success, amount = reserve.deploy_for_backing(
        current_backing=0.55,  # Below 60% threshold
        total_ups_supply=100000.0,
        btc_price=85000.0,
        target_backing=0.80
    )
    if success:
        print(f"Deployed {amount:.8f} BTC to restore backing")
```

## Failure Simulation Tests

Run these simulations to tune parameters:

```python
# 1. Death Spiral: 50% BTC crash + 30% user panic exit
# 2. Demurrage Gaming: 1000 users trying to avoid decay
# 3. Bootstrap: 0 → 100 users growth curve
# 4. Circuit Breaker: Test thresholds and recovery
# 5. Bonding Curve vs Orderbook: Liquidity and price stability
# 6. Rage Quit Abuse: Prevent gaming of failure criteria
```

## Early Investor Economics

**Full specification**: See [INVESTOR_ECONOMICS.md](economics/INVESTOR_ECONOMICS.md)

### Investment Rounds (Target: 755 BTC / ~$75.5M)

| Round | BTC Range | Target | Return Projection |
|-------|-----------|--------|-------------------|
| Pre-Seed | 0.1-1 BTC | 5 BTC | **6,000x** |
| Seed | 1-10 BTC | 50 BTC | **1,600x** |
| Series A | 10-50 BTC | 200 BTC | **118x** |
| Series B | 50-100 BTC | 500 BTC | **24x** |

### Key Features
- **BTC Escrow**: Investment sequestered for 3 years in "Dry Wallet"
- **Pool Participation**: 12.16% pre-hurdle, 0.64% post-hurdle
- **Perpetual Tail**: Once post-hurdle is reached, 0.64% remains locked
- **Transferable Rights**: Vested I_i rights can be transferred
- **Hybrid Exit**: 10x guaranteed buyout OR hold for 100x+

```python
from modules.foundups.simulator.economics import (
    InvestorPool, bonding_price, bonding_tokens_for_btc
)

pool = InvestorPool(k=0.0001, n=2.0)  # Quadratic bonding curve
tokens, tier = pool.invest_btc("seed_investor", btc_amount=10.0)
returns = pool.get_investor_returns("seed_investor")
# returns['price_return_multiple'] → 1,600x for seed investor
```

## Research Documents

Research driving simulator development (WSP 15 prioritized):

- [SYNTHETIC_PERSONAS_RESEARCH.md](docs/SYNTHETIC_PERSONAS_RESEARCH.md) - Simile AI ($100M), synthetic user simulation for pre-launch market testing. P1 priority for SyntheticUserAgent implementation.

## WSP References

- WSP 26: Token Pool Distribution (Un/Dao/Du + Network/Fund)
- WSP 26 Section 4.9: Subscription Tiers (Freemium → Premium)
- WSP 26 Section 6.7: Digital Twin Model, Degradation, Elevation
- WSP 26 Section 6.8: Human vs Agent Economic Boundary
- WSP 26 Section 6.9: Early Investor Economics (Bonding Curve + Escrow)
- WSP 91: Observability (FAMDaemon integration)
- WSP 72: Module independence (adapters don't invent logic)
- TOKENOMICS.md: Bio-Decay model (ICE/LIQUID/VAPOR)
- INVESTOR_ECONOMICS.md: Complete investor model specification

## Tokenomics Validation

Run deterministic simulator and tokenomics checks:

```powershell
cd o:\Foundups-Agent
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
.\.venv\Scripts\python.exe -m pytest modules/foundups/simulator/tests/test_alignment_and_tokenomics.py -q
```

Run investor underwriting and buyout coverage checks:

```powershell
cd o:\Foundups-Agent
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
.\.venv\Scripts\python.exe -m pytest modules/foundups/simulator/tests/test_investor_liability_engine.py -q
```

Run scenario underwriting matrix checks (3Y/10Y with S-curve and dynamic pool rates):

```powershell
cd o:\Foundups-Agent
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
.\.venv\Scripts\python.exe -m pytest modules/foundups/simulator/tests/test_underwriting_scenarios.py -q
```

Generate an underwriting table for a ticket size:

```powershell
cd o:\Foundups-Agent
.\.venv\Scripts\python.exe -m modules.foundups.simulator.economics.run_underwriting_matrix --principal-btc 10 --total-invested-btc 755 --repayment-multiple 10
```

Generate a pool-weighted underwriting table (seed pool + foundup-specific lane membership):

```powershell
cd o:\Foundups-Agent
.\.venv\Scripts\python.exe -m modules.foundups.simulator.economics.run_underwriting_matrix --principal-btc 10 --total-invested-btc 755 --repayment-multiple 10 --pool-weighted
```

Pool-weighted mode avoids straight scalar share assumptions:
- Seed members participate across all FoundUp lanes.
- FoundUp-specific members participate only in their target lane.
- Lane payouts are scaled by each FoundUp lane S-curve adoption.
