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

## Persistent reward correctness — implementation 2026-09-22

The existing SQLite adapter now owns atomic pending initiation and exact retry.
The historical tranche checkboxes below remain component evidence, not proof of
production authorization or settlement. [R24 repair contract](../../../docs/roadmaps/R24_AGENT_PRODUCTION_LINE_PACKET.md#persistent-reward-initiation-contract--2026-09-22)
defines the local14/P1 repair and its independent validation boundary.

- [x] Bind prior failure witnesses to current source; map transaction, compute and event owners.
- [x] Fix acceptance for pending state, exact retry, rollback, concurrent writers and legacy rejection.
- [x] Implement and independently verify one SQLite initiation transaction in existing owners (120 connected local cases; production roles/settlement excluded).
- [ ] Qualify PostgreSQL compute initialization and actual backend locking before support claims.
- [ ] Independently admit persistent roles and settlement; compute payment is not authorization.

WSP62 task-budget reconciliation: the proposed1154-line adapter no-growth target
was not met. Complete historical-scope and immutable replay checks require1330
lines (+176); its class shrinks875→816 and the pipeline446→400/class405→359.
New functions are at most40lines. Retain1330 as this owner's no-growth ceiling
pending a separately scoped cohesion/decomposition review before further growth.
The adapter remains in the critical review window; this is no protocol exemption
or claim that inherited oversized classes/functions are clean. Avoid unrelated
CRUD compression or a duplicate module merely to conceal this debt.

This repair changes no schema, adds no module and activates no live effect. The
in-memory completed-payment simulation remains distinct from persistent initiation.

## Shared ORM cohesion prerequisite — 2026-09-23

- [x] Extract Base/13 row mappings once into internal `persistence/orm_models.py`; preserve existing sqlite_adapter export identities and single registry.
- [x] Validate unchanged declaration/adapter ASTs and128 connected cases locally/independently (three compatibility controls plus125 existing cases, including the five known verification failure witnesses).
- Adapter1330→1125; ORM owner238; adapter class remains816. Combined source+33 lines is extraction/import documentation overhead, not removed functionality. The1330 ceiling above remains a maximum; inherited critical-window/class debt still needs scoped remediation.
- Old pickle globals resolve; new pickles use the ORM file's module path. Preserve that file when handling new pickles during rollback. No schema/migration or PostgreSQL runtime qualification is implied.
- Next14/P1 verification repair can reuse existing transaction/compute helpers after fixing acceptance and legacy-record reconciliation. Do not preserve defective characterization outcomes as desired repair behavior.

## Persistent proof verification — contract checkpoint 2026-09-23

- [x] Specify existing post-finalization WRE to FAM handoff and exact identity/recovery boundaries in [R24](../../../docs/roadmaps/R24_AGENT_PRODUCTION_LINE_PACKET.md#persistent-proof-verification-handoff-contract--2026-09-23); planning14/P1, independently source-reviewed.
- [x] Qualify five disposable SQLite verification retry/failure controls in the existing persistent compute test owner (12/P2): same five cases pass locally/independently and reproduce double debit, partial commits and non-idempotent retry. These are failure witnesses, not production acceptance.
- [ ] Next candidate14/P1: repair verification atomicity/replay in existing pipeline/SQLite owners after fixed desired acceptance and legacy-history reconciliation; ORM cohesion prerequisite is qualified,1330 ceiling and class debt remain; independently validate. No authority or payout integration.
- [ ] Obtain explicit domain issuer/delegation policy before signed verification integration; repository-write and compute access are not verifier entitlement.
- [ ] Qualify the integrated admitted caller and independent verifier before any native AmIBot/RSI claim. Settlement remains separately admitted.

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
