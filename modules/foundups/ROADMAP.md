# FoundUps Domain Roadmap

## Purpose
Keep FoundUps delivery coherent across sessions and agents by using an Occam-first
layered plan from PoC to MVP.

This roadmap is the domain-level coordination plan. Submodule roadmaps remain
implementation sources of truth:
- `modules/foundups/agent_market/ROADMAP.md`
- `modules/foundups/simulator/ROADMAP.md`
- `modules/foundups/agent/ROADMAP.md`
- `modules/foundups/docs/FOUNDUPS_PAVS_IRONCLAW_AGENT_BUILDER_DIGITAL_TWIN_ROADMAP.md`
- `modules/foundups/social_twin/ROADMAP.md`

## First-Principles Constraints
1. No market claims without an auditable event/state trail.
2. No DEX visibility without deterministic order/settlement contracts.
3. No member-only surface without fail-closed access gating at API/SSE layer.
4. No UI promise without read models fed by canonical events.
5. No phase promotion without concatenated tests and updated module docs.

## Layered Delivery Model (Occam Cake)

### Layer 0 - Access + Observability Foundation
- Scope: invite/member access, role claims, event lineage, health checks.
- Modules:
  - `modules/foundups/agent_market/src/fam_daemon.py`
  - `modules/foundups/simulator/sse_server.py`
  - `modules/communication/moltbot_bridge/src/openclaw_dae.py`
- Exit criteria:
  - Member-only endpoints fail closed.
  - Event ordering/dedupe invariants covered in tests.

### Layer 1 - FoundUp Execution Core
- Scope: launch, task pipeline, proof/verify/payout, CABR/PoB gates.
- Module: `modules/foundups/agent_market/`
- Exit criteria:
  - End-to-end launch-to-payout deterministic path.
  - Persistent adapters (sqlite/postgres boundary) validated.

### Layer 2 - DEX Mechanics
- Scope: symbol uniqueness, order placement, matching, settlement, portfolio state.
- Modules:
  - `modules/foundups/agent_market/src` (production contracts and ledgers)
  - `modules/foundups/simulator/economics/fi_orderbook.py` (simulation kernel)
- Exit criteria:
  - DEX event contract stable (`order_placed`, `order_matched`, etc.).
  - Role gates enforced (`observer_012`, `member`, `agent_trader`).

### Layer 3 - Simulation + pVAS Forecasting
- Scope: adoption trajectory, CABR/PoB behavior, stress scenarios, policy tuning.
- Module: `modules/foundups/simulator/`
- Exit criteria:
  - Scenario runner emits deterministic manifests and metrics.
  - Market + lifecycle outputs stay reproducible by seed.
  - IronClaw execution lane parity with OpenClaw control contracts is validated.

### Layer 4 - Operator and Member Control Panel
- Scope: portfolio, FoundUp health, DEX tape, live events.
- Modules:
  - `public/index.html`
  - `public/js/foundup-cube.js`
  - upcoming panel scripts/read-model APIs
- Exit criteria:
  - Observer dashboard read-only by default.
  - Member/agent trading controls gated by role.

### Layer 5 - MVP Operations
- Scope: paying users, operational runbooks, incident handling, release governance.
- Exit criteria:
  - At least one paying user completes launch-to-payout cycle.
  - Production SLO/SLA and incident runbooks verified.

## Current Snapshot (2026-02-16)
- Layer 0: In progress (events/health are present; member gate hardening still needed).
- Layer 1: In progress (core complete; persistent compute wiring still finishing).
- Layer 2: In progress in simulator, partial in market contracts.
- Layer 3: In progress (scenario + SSE operational, deeper DEX stress packs pending).
- Layer 4: In progress (cube visualization live; full control panel not complete).
- Layer 5: Not started (MVP gate requires paying-user evidence).

## WSP 15 Priority Queue

### P0 (Do now)
1. Member access gate on SSE/API (fail closed).
2. DEX symbol registry and reservation policy.
3. DEX event contract normalization across market and simulator.
4. Concatenated tests across bridge + market + simulator.
5. IronClaw sidecar lane for pAVS Agent Builder + Digital Twin (adapter-first, no control-plane rewrite).

### P1 (Next)
1. Read models for control panel (portfolio, CABR, traction, active agents).
2. Member control panel widgets and live tape.
3. Simulator stress packs for DEX/liquidity and PoB yield.
4. Social Twin FoundUp vertical slice:
   Discord/OpenClaw review plane -> approved social execution -> follow-up queue.

### P2 (After)
1. Dynamic pricing and queue optimization.
2. Advanced market analytics and policy auto-tuning.
3. Operator automation and escalation loops.

## Continuity Requirements (must stay current)
- Update:
  - `ModLog.md` and `tests/TestModLog.md` in every touched module
  - this roadmap when phase status changes
  - interface docs when event/contracts change
- Keep a reproducible validation command in logs.
- Re-index Holo after structural/documentation updates that affect retrieval.

## Canonical Validation Command
```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
.\.venv\Scripts\python.exe -m pytest `
  modules/communication/moltbot_bridge/tests `
  modules/foundups/agent_market/tests `
  modules/foundups/simulator/tests -q
```

