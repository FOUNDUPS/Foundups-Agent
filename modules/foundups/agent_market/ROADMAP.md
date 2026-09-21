# ROADMAP - FoundUps Agent Market
## Domain Alignment References
- `modules/foundups/ROADMAP.md`
- `modules/foundups/docs/OCCAM_LAYERED_EXECUTION_PLAN.md`
- `modules/foundups/docs/CONTINUATION_RUNBOOK.md`

## Versioning and Progression
- PoC: `0.0.x`
- Prototype: `0.1.x - 0.9.x`
- MVP: `1.0.x+`

## PoC (COMPLETE - 2026-02-07)
### Goal
Ship contract-complete, testable infrastructure for tokenized Foundup launch and agent task pipeline.

### Deliverables
- [x] Complete interface contracts for registry, token, agent join, task/proof/verify/payout, treasury/governance, CABR hooks, observability.
- [x] In-memory implementation with deterministic state transitions.
- [x] Test suite for schema validation, lifecycle transitions, and permission gates.
- [x] Holo retrieval discoverability updates.

### Exit Criteria
- [x] Tests pass in CI/local.
- [x] Contracts are stable enough for OpenClaw/WRE integration.

## Persistent reward correctness — qualified 2026-09-22

Current source still has non-atomic initiation and premature PAID labeling. The
historical tranche checkboxes below are component evidence, not proof of reward
retry safety, authorization or settlement. [R24 repair contract](../../../docs/roadmaps/R24_AGENT_PRODUCTION_LINE_PACKET.md#persistent-reward-initiation-contract--2026-09-22)
qualifies the existing-owner SQLite repair at14/P1 after13/P1 source/consumer review.

- [x] Bind prior failure witnesses to current source; map transaction, compute and event owners.
- [x] Fix acceptance for pending state, exact retry, rollback, concurrent writers and legacy rejection.
- [ ] Implement and independently verify one SQLite initiation transaction in existing owners.
- [ ] Qualify PostgreSQL compute initialization and actual backend locking before support claims.
- [ ] Independently admit persistent roles and settlement; compute payment is not authorization.

No new schema, module or live effect is authorized by this plan. Preserve the
in-memory completed-payment simulation and distinguish it from persistent initiation.

## Prototype (Current)
### Goal
Integrate real persistence and one chain adapter while keeping chain-agnostic interface.

### Tranche 1: Observability Backbone (COMPLETE - 2026-02-08)
**Deliverables:**
- [x] `fam_event_v1` schema with deterministic IDs, sequence IDs, dedupe keys
- [x] `FAMEventStore`: JSONL append-only sink + SQLite audit index
- [x] `FAMDaemon`: Heartbeat loop, health/status API, event listeners
- [x] Replay-safe writes with idempotent dedupe enforcement
- [x] Parity verification for JSONL/SQLite sync
- [x] Test suite: 26 tests covering schema, ordering, dedupe, parity, health, thread safety

**Files Added:**
- `src/fam_daemon.py` (737 LOC)
- `tests/test_fam_daemon.py` (comprehensive coverage)

### Tranche 2: Persistence Layer (COMPLETE - 2026-02-08)
**Deliverables:**
- [x] SQLite repository adapter with CRUD coverage for Foundups, Tasks, Proofs, Verifications, Payouts, Events, Distribution posts, Agent profiles, Token terms
- [x] Postgres adapter boundary (`PostgresAdapter`) preserving the same repository contract
- [x] Repository factory (`create_repository`) with env-driven backend selection (`sqlite`/`postgres`)
- [x] Schema migration/versioning (`schema_migrations` table + `MigrationManager`, `LATEST_SCHEMA_VERSION`)
- [x] Query indexes for hot read paths (`tasks`, `proofs`, `event_records`, `payouts`, `distribution_posts`)
- [x] Test coverage for migration idempotency/version guard and repository backend routing

**Files Added:**
- `src/persistence/migrations.py`
- `src/persistence/postgres_adapter.py`
- `src/persistence/repository_factory.py`
- `tests/test_migrations.py`
- `tests/test_repository_factory.py`

### Tranche 3: Chain Adapter (Planned)
- One concrete token adapter (Hedera or EVM)
- Chain-agnostic interface preservation
- Test doubles for CI

### Tranche 4: Role Refinement (Planned)
- Role model for verifiers/governance actors
- Permission matrix enforcement
- Audit trail per actor

### Tranche 5: Compute Access Paywall (In Progress, WSP 15 Ordered)
Goal: make FoundUps a one-stop paid build surface where execution compute is metered, quality-gated by CABR/PoB, and routed through pAVS treasury lanes.

**P0 (first)**
- [x] Access gate + credit debit ledger enforcement in in-memory adapter
- [x] Metering hooks at launch/orchestration/task-mutating boundaries
- [x] Compute access event emission for debit/purchase/rebate/session/denial
- [x] Persistence-backed compute wallet/ledger/session tables + migrations (SQLite/Postgres adapters)
- [x] Service-layer wiring in persistent registry/task pipeline paths
- [ ] Remaining service-layer wiring (distribution and treasury governance persistent paths)

**P1 (second)**
- Plan/tier lifecycle (scout, builder, swarm, sovereign)
- UPS to compute-credit conversion rails and constraints
- pAVS fee routing + credit rebate settlement
- Simulator scenario pack for PoB yield and paywall stress tests

**P2 (third)**
- Dynamic pricing and queueing optimization from utilization history

Reference design:
- `docs/COMPUTE_ACCESS_PAYWALL_SPEC.md`

### Exit Criteria
- End-to-end pipeline works with persistent storage and adapter test doubles.

## MVP (Requires Paying Users)
### Goal
Production deployment with governance, treasury safety controls, and operational observability.

**CRITICAL**: MVP status requires at least one paying user completing a full launch-to-payout cycle. Until then, this remains Prototype regardless of feature completeness.

### Planned Work
- FAM DAEmon: Vitals pump for 012/Overseer observability (WSP 91).
- Integration with breadcrumb_telemetry.db and DaemonMonitorMixin.
- Multisig/DAO adapter integration.
- Idempotent payout orchestration with retry/compensation.
- Operational dashboards and incident runbooks.
- Explicit launch gateway docs and user onboarding path.

### Exit Criteria
- [ ] At least ONE paying user with completed launch-to-payout cycle
- [ ] Production SLO/SLA with audited controls
- [ ] Real user launch workflow validated end-to-end
- [ ] Revenue generated through platform
