# ROADMAP - FoundUps Simulator

## 2026-10-25 — Selected numeric admission

- [x] Strict work/stake/unstake quantities, at-use fee validation and pure
  prospective-balance preflight; existing valid math and references retained.
- [x] Focused226 and independent28 pass; combined current-main BTC/numeric
  simulator736 pass with the same3 named SSE HTTP exclusions. Counts overlap.
- [ ] Derived source closure, exact-head security/CI, dedicated PR and main
  readback for the numeric layer.
- [ ] Aggregate F_i issuance, CABR epoch allowances, explicit asset units and
  funded/confirmed settlement remain separately governed accounting work.

## 2026-10-25 — Optional mock BTC replay integrity

- [x] Local current-v2 content/realm identity, additive legacy classification,
  canonical schema checks, atomic mock admission and honest confirmation gates.
- [x] Preserve exact-content force behavior; replace unsafe selected-mode coercion.
- [x] Repaired local focused211 and simulator513 pass, with the same3 named SSE
  HTTP exclusions; independent21 held-outs/source review pass. Counts overlap.
- [x] PR2198 passed all22 hosted checks and exact main readback at
  `6fe7eba424c17f7813043dfb104cd845617cab38`; historical local runs retain
  their actual execution context.
- [ ] Real BTC publishing/confirmation, legacy reconciliation and external-I/O
  recovery remain unimplemented. This is not an Algorand transfer prerequisite
  unless BTC evidence is explicitly chosen as downstream authority.

## 2026-10-25 — Epoch evidence integrity layer

- [x] Local v2 claim/context binding, immutable snapshots, atomic exact epoch
  retries/conflict rejection and stable pre-settlement commitment preparation.
- [x] Preserve original commitment oracles; repaired local focused106, independent41
  and affected simulator410 pass, with3 named SSE HTTP exclusions. Counts overlap.
- [x] Parent verified PR2192 hosted gates and squash-main convergence at
  `7d3d7f64390762040bc2ca737ff0964d94d887c1`; this branch's local evidence still
  originates at candidate `b6d2cf316`, not a new main execution claim.
- [ ] Reconcile unclassified connector rows and design real effects/recovery
  before non-mock activation; current local mock replay repair is above.
- [ ] Durable source-receipt consumption, aggregate F_i issuance, CABR epoch
  allowance and funded/confirmed settlement remain separate accounting gates.

## 2026-10-25 — FAM authority compatibility

- [x] Pass configured simulation caller contexts into the existing FAM boundary;
  reject caller-ID impersonation and legacy-role substitution.
- [x] Preserve existing lifecycle flow under scoped grants; combined local FAM
  and simulator run passes 690 cases, with three named SSE HTTP cases excluded.
- [ ] Production identity/issuer integration, asset accounting/proof/replay gates,
  real testnet effects and settlement remain separate delivery layers.

## Phase Status
- PoC: complete
- Prototype: in progress
- MVP: pending paying-user validation path

## Mission
Provide deterministic market + lifecycle simulation that mirrors FoundUps runtime
contracts and supports operator decisions (CABR/PoB, liquidity, allocation policy).

## Recent Progress (2026-02-22)
- Added simulator backend route toggle for Qwen lane:
  - `SIM_QWEN_BACKEND=local|ironclaw|wre_ironclaw`
- Enables direct IronClaw and WRE->IronClaw scenario modeling without changing agent behavior code.

Related strategy docs:
- `modules/foundups/docs/OCCAM_LAYERED_EXECUTION_PLAN.md`
- `modules/foundups/docs/FOUNDUPS_PAVS_IRONCLAW_AGENT_BUILDER_DIGITAL_TWIN_ROADMAP.md`

## Prototype Tranches

### Tranche S1 - Deterministic Core (Complete)
- State contracts (`state_contracts.py`)
- Pure-step path (`step_pure.py`)
- Step extraction and shadow parity checks
- Scenario runner with deterministic manifests

### Tranche S2 - Event Plane + Visualization (In Progress)
- SSE stream integration and event normalization
- Frame schema for animation adapter
- Cube visualization and lifecycle ticker integration
- Remaining:
  - tighten member-only gate behavior at API/SSE boundary
  - formalize DEX orderbook snapshot stream

### Tranche S3 - DEX and Market Dynamics (In Progress)
- Existing orderbook kernel (`economics/fi_orderbook.py`)
- Existing market events (`fi_trade_executed`)
- Remaining:
  - add canonical DEX contract events (`order_placed`, `order_cancelled`, `order_matched`, `price_tick`)
  - stress-pack scenarios for liquidity shocks and spread widening
  - role-aware behavior simulation (`observer_012`, `agent_trader`)

### Tranche S4 - Control Panel Read Models (Planned)
- Read-model emitters for:
  - portfolio summary,
  - FoundUp health (CABR, traction, active agents),
  - DEX tape and depth windows.
- Keep panel read-only defaults.

### Tranche S5 - Policy Tuning and Operations (Planned)
- Monte Carlo sweeps for policy sensitivity.
- Optimizer feedback loops into parameter scenarios.
- Operator runbook-grade metrics packs.

### Tranche S6 - IronClaw Agent Builder + Digital Twin Lane (Planned)
- Runtime parity validation against existing OpenClaw ingress contracts.
- Agent-builder scenario pack (template -> build -> verify -> publish) with deterministic evidence.
- Digital Twin scenario pack with role tiers, containment behavior, and observability assertions.
- Accounting linkage checks: runtime usage -> CC/UPS lane attribution.

## WSP 15 Priority Queue

### P0
1. Canonical DEX event contract parity with `agent_market`.
2. SSE/API member gate hardening.
3. Concatenated integration tests with `moltbot_bridge` and `agent_market`.
4. IronClaw integration parity tests for agent-builder and Digital Twin flows.

### P1
1. Read-model outputs for control panel.
2. DEX stress scenarios and reporting pack.

### P2
1. Auto-tuning guidance from scenario outputs.
2. Expanded behavior models for advanced agent strategy lanes.

## Validation Command
```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
.\.venv\Scripts\python.exe -m pytest modules/foundups/simulator/tests -q
```

