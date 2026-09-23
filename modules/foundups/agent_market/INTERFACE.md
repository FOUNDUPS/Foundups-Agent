# INTERFACE - FoundUps Agent Market

## Module Contract
FoundUps Agent Market exposes stable contracts for launching tokenized FoundUps and coordinating task execution with auditable payout flow.

## CABR Canonical Intent
- CABR = Consensus-Driven Autonomous Benefit Rate (also referred to as Collective Autonomous Benefit Rate).
- WHY: CABR exists to power Proof of Benefit (PoB).
- HOW: Collective 0102 consensus determines CABR (consensus-driven process).
- RESULT: PoB drives protocol allocation/distribution; ROI is a downstream financial readout.

## Core Schemas

### Foundup
```python
Foundup(
    foundup_id: str,
    name: str,
    owner_id: str,
    token_symbol: str,
    immutable_metadata: dict[str, str],
    mutable_metadata: dict[str, str],
)
```

### TokenTerms
```python
TokenTerms(
    token_name: str,
    token_symbol: str,
    max_supply: int,
    treasury_account: str,
    vesting_policy: dict[str, str],
    chain_hint: str | None = None,
)
```

### AgentProfile
```python
AgentProfile(
    agent_id: str,
    display_name: str,
    capability_tags: list[str],
    role: str,
)
```

### Task
```python
Task(
    task_id: str,
    foundup_id: str,
    title: str,
    description: str,
    acceptance_criteria: list[str],
    reward_amount: int,
    creator_id: str,
    status: TaskStatus,
)
```

### Proof
```python
Proof(
    proof_id: str,
    task_id: str,
    submitter_id: str,
    artifact_uri: str,
    artifact_hash: str,
    notes: str,
)
```

### Verification
```python
Verification(
    verification_id: str,
    task_id: str,
    verifier_id: str,
    approved: bool,
    reason: str,
)
```

### Payout
```python
Payout(
    payout_id: str,
    task_id: str,
    recipient_id: str,
    amount: int,
    status: str,
    reference: str | None,
)
```

### DistributionPost
```python
DistributionPost(
    distribution_id: str,
    foundup_id: str,
    task_id: str,
    channel: str,
    content: str,
    actor_id: str,
    dedupe_key: str,
    external_ref: str | None = None,
)
```

### fam_event_v1 (DAEmon Observability Schema)
```python
FAMEvent(
    # Identity
    event_id: str,           # Deterministic: sha256(type:payload_hash:timestamp)[:16]
    sequence_id: int,        # Monotonic, gap-free, assigned by store
    dedupe_key: str,         # Idempotent replay protection key

    # Classification
    event_type: str,         # FAMEventType enum value
    schema_version: str,     # "fam_event_v1"

    # Context
    actor_id: str,           # Default: "system"
    foundup_id: str | None,  # Foundup context
    task_id: str | None,     # Task context

    # Payload
    payload: dict[str, object],

    # Timestamps
    timestamp: datetime,     # Event occurrence time (UTC)
    recorded_at: datetime,   # Store write time (UTC)
)
```

**FAMEventType enum:**
- `foundup_created`, `foundup_updated`
- `task_state_changed`
- `proof_submitted`, `verification_recorded`
- `payout_triggered`
- `milestone_published`
- `fi_trade_executed`, `investor_funding_received`
- `mvp_subscription_accrued`, `mvp_bid_submitted`, `mvp_offering_resolved`
- `compute_plan_activated`, `compute_credits_purchased`, `compute_credits_debited`
- `compute_session_recorded`, `compute_credits_rebated`, `paywall_access_denied`
- `security_alert_forwarded`, `incident_alert_forwarded`
- `heartbeat`, `daemon_started`, `daemon_stopped`

**Dedupe Key Generation:**
- `task_state_changed`: `task:{task_id}:{new_status}`
- `proof_submitted`: `proof:{proof_id}`
- `verification_recorded`: `verification:{verification_id}`
- `payout_triggered`: `payout:{payout_id}`
- `milestone_published`: `distribution:{distribution_id}`
- `heartbeat`: `heartbeat:{timestamp[:19]}` (per-second)
- Default: `{event_type}:{payload_hash[:12]}`

## Service Contracts

### FoundupRegistryService
- `create_foundup(foundup: Foundup) -> Foundup`
- `update_foundup(foundup_id: str, updates: dict[str, str]) -> Foundup`
- `get_foundup(foundup_id: str) -> Foundup`
- Invariant: immutable metadata keys cannot be changed after creation.
- Invariant: `token_symbol` is unique across FoundUps (case-insensitive).

### TokenFactoryAdapter (Chain-Agnostic)
- `deploy_token(foundup: Foundup, terms: TokenTerms) -> str`
- `configure_vesting(token_address: str, terms: TokenTerms) -> None`
- `get_treasury_account(foundup_id: str) -> str`
- Invariant: adapter must not leak chain-specific assumptions into upstream API.

### AgentJoinService
- `submit_join_request(foundup_id: str, profile: AgentProfile) -> str`
- `approve_join_request(request_id: str, approver_id: str) -> AgentProfile`
- `list_agents(foundup_id: str) -> list[AgentProfile]`

### TaskPipelineService
- `create_task(task: Task) -> Task`
- `claim_task(task_id: str, agent_id: str) -> Task`
- `submit_proof(proof: Proof) -> Task`
- `verify_proof(task_id: str, verification: Verification) -> Task`
- `trigger_payout(task_id: str, actor_id: str) -> Payout`
- `get_task(task_id: str) -> Task`
- `get_trace(task_id: str) -> dict[str, object]`
- In-memory simulation: `open -> claimed -> submitted -> verified -> paid` with a simulated completed payout.
- Persistent SQLite initiation: `trigger_payout` delegates to `SQLiteAdapter.initiate_payout(task_id, actor_id)`. One write transaction binds task/proof/approved verification, pending payout, configured compute debit and correlated event. The task stays `VERIFIED`, payout `INITIATED`, with no settlement reference or `paid_at`.
- Exact same-actor retry returns the persisted initiation without another debit/event, using its original cost snapshot. Conflicting or incomplete lineage and ambiguous legacy history reject before effects; missing scope cannot be guessed unrelated. No historical repair or settlement is performed. See [R24 acceptance](../../../docs/roadmaps/R24_AGENT_PRODUCTION_LINE_PACKET.md#persistent-reward-initiation-contract--2026-09-22).

### TreasuryGovernanceService
- `propose_transfer(foundup_id: str, amount: int, reason: str, proposer_id: str) -> str`
- `approve_transfer(proposal_id: str, approver_id: str) -> None`
- `execute_transfer(proposal_id: str, executor_id: str) -> str`
- `get_treasury_state(foundup_id: str) -> dict[str, object]`

### CABRHookService
- `build_cabr_input(foundup_id: str, window: str) -> dict[str, object]`
- `record_cabr_output(foundup_id: str, payload: dict[str, object]) -> None`

### ObservabilityService
- `emit_event(event_type: str, actor_id: str, payload: dict[str, object]) -> None`
- `query_events(foundup_id: str | None = None, task_id: str | None = None) -> list[dict[str, object]]`

### FAMDaemon (Prototype Observability Backbone)
```python
FAMDaemon(
    data_dir: Path | None = None,       # Default: module memory/
    heartbeat_interval_sec: float = 60.0,
    auto_start: bool = False,
)
```

**Runtime API:**
- `start() -> None`: Start heartbeat loop, emit `daemon_started`
- `stop() -> None`: Stop loop, emit `daemon_stopped`
- `emit(event_type, payload, actor_id, foundup_id, task_id) -> (bool, str)`: Write event
- `query_events(event_type, foundup_id, task_id, since_sequence, limit) -> list[FAMEvent]`
- `get_health() -> FAMDaemonHealth`: Health/status for Overseer polling
- `get_status() -> dict`: Alias for `get_health().to_dict()`
- `add_listener(fn) -> None`: Subscribe to events
- `remove_listener(fn) -> None`: Unsubscribe

**FAMDaemonHealth:**
```python
FAMDaemonHealth(
    running: bool,
    uptime_seconds: float,
    heartbeat_count: int,
    last_heartbeat: str | None,
    event_store_stats: dict,
    parity_ok: bool,
    parity_message: str,
    errors: list[str],      # Last 10 errors
)
```

**FAMEventStore (Persistence):**
- Dual-write: JSONL (append-only DR) + SQLite (indexed queries)
- Dedupe enforcement via `dedupe_key` unique constraint
- `verify_parity() -> (bool, str)`: JSONL/SQLite sync check
- `get_stats() -> dict`: Event counts by type

### Persistence Repository Layer (Prototype Tranche 2)

**SQLiteAdapter:**
- Primary persistence adapter for local/dev and deterministic test execution.
- Methods include CRUD coverage for:
  - Foundups, Tasks, Proofs, Verifications, Payouts
  - Events, Distribution posts, Agent profiles, Token terms

**PostgresAdapter:**
- CRUD adapter using the same ORM model set; atomic payout initiation rejects non-SQLite before session/compute effects. PostgreSQL compute initialization and backend locking require separate qualification.
- Selected through repository factory (`backend=postgres`).
- Requires a valid Postgres SQLAlchemy URL.

**Repository Factory:**
```python
RepositoryConfig(
    backend: str = "sqlite",
    sqlite_path: str | Path | None = None,
    postgres_url: str | None = None,
    auto_migrate: bool = True,
    schema_version: int | None = None,
)

create_repository(config: RepositoryConfig | None = None) -> SQLiteAdapter
```

**MigrationManager:**
- `ensure_migration_table() -> None`
- `get_current_version() -> int`
- `migrate(target_version: int = LATEST_SCHEMA_VERSION) -> int`
- `list_applied_versions() -> list[int]`

**Schema Versioning:**
- `LATEST_SCHEMA_VERSION = 2`
- Migrations tracked in `schema_migrations(version, description, applied_at)`
- Migrations are idempotent and ordered.

**Persistence Env Vars:**
- `FAM_DB_BACKEND` (`sqlite` default, `postgres` optional)
- `FAM_DB_PATH` (sqlite file path)
- `FAM_POSTGRES_URL` (postgres SQLAlchemy URL)
- `FAM_DB_AUTO_MIGRATE` (`1` default)
- `FAM_DB_SCHEMA_VERSION` (optional target schema version pin)
- `FAM_COMPUTE_ACCESS_ENFORCED` (`0` default; set `1` to enforce paywall gate)
- `FAM_COMPUTE_DEFAULT_CREDITS` (`0` default starting wallet credits per actor)

**Singleton Access:**
```python
from modules.foundups.agent_market.src.fam_daemon import get_fam_daemon
daemon = get_fam_daemon(auto_start=True)
```

### DistributionService
- `build_milestone_payload(task_id: str) -> dict[str, object]`
- `publish_verified_milestone(task_id: str, actor_id: str, channel: str = "moltbook", cabr_threshold: float = 0.0) -> DistributionPost`
- `get_distribution(task_id: str) -> DistributionPost | None`
- `get_latest_cabr_score(foundup_id: str) -> float | None`
- Invariant: publish is allowed only from `verified` or `paid` task states and is idempotent per `task_id + channel + milestone`.
- CABR Gate: If `cabr_threshold > 0`, publish requires CABR score >= threshold. Missing score raises `CABRGateError`.

### RepoProvisioningAdapter
- `provision_repo(foundup_id: str, repo_name: str, provider: str = "github", default_branch: str = "main") -> str`
- `get_repo_metadata(foundup_id: str) -> dict[str, object] | None`
- Invariant: In-memory PoC returns deterministic URL pattern `https://{provider}.com/foundups/{repo_name}`.

### MvpOfferingService (F_0 Investor Program)
- `accrue_investor_terms(investor_id: str, terms: int = 1, term_ups: int = 200, max_terms: int = 5) -> dict[str, int]`
- `place_mvp_bid(foundup_id: str, investor_id: str, bid_ups: int) -> str`
- `get_mvp_bids(foundup_id: str) -> list[dict[str, object]]`
- `resolve_mvp_offering(foundup_id: str, actor_id: str, token_amount: int, top_n: int = 1) -> list[dict[str, object]]`
- Invariant: investors subscribe only into `F_0` (global program), then bid for upcoming FoundUp MVP access with hoarded UPS.
- Invariant: term accrual caps at 5 terms by default (1000 UPS hoard at 200 UPS/term).
- Invariant: offering resolution requires `treasury` role and injects winning UPS bids into target FoundUp treasury.

### ComputeAccessService (Prototype Tranche 5 - P0 in-memory)
- `ensure_access(actor_id: str, capability: str, foundup_id: str | None = None) -> dict[str, object]`
- `get_wallet(actor_id: str) -> dict[str, object]`
- `purchase_credits(actor_id: str, amount: int, rail: str, payment_ref: str) -> dict[str, object]`
- `debit_credits(actor_id: str, amount: int, reason: str, foundup_id: str | None = None) -> dict[str, object]`
- `record_compute_session(actor_id: str, foundup_id: str, workload: dict[str, object]) -> str`
- `rebate_credits(actor_id: str, amount: int, reason: str) -> dict[str, object]`
- Invariant: metered actions fail closed on insufficient credits.
- Invariant: debit -> session -> proof -> verification -> payout must remain traceable via event lineage.
- Invariant: CABR remains quality gate for PoB; financial ROI reporting is downstream.
- InMemory status: implemented in `src/in_memory.py` for metered enforcement and ledger/session events.
- Persistence status: implemented in `src/persistence/sqlite_adapter.py` (and inherited by postgres adapter).
- Runtime wiring status: enabled in persistent `registry.py` and `task_pipeline.py` paths.

### LaunchOrchestrator
- `launch_foundup(foundup: Foundup, token_terms: TokenTerms | None, repo_name: str | None, ...) -> LaunchResult`
- Steps: (1) validate/create Foundup, (2) token deploy, (3) repo provision, (4) initial task create (when task pipeline adapter provided), (5) emit events
- Returns `LaunchResult` with all artifacts and auditable `LaunchEvent` list.

### MoltbookDistributionAdapter
- `publish_milestone(foundup_id: str, task_id: str, milestone_payload: dict, actor_id: str) -> dict`
- `get_publish_status(post_id: str) -> dict | None`
- `list_published_milestones(foundup_id: str, limit: int = 10) -> list[dict]`
- Invariant: Interface defined in FAM, implementation in `moltbot_bridge` domain.
- Stub implementation stores in-memory. Production pushes to Discord/Moltbook.

## OpenClaw/FAM Integration

### FAMAdapter (moltbot_bridge)
The `FAMAdapter` in `moltbot_bridge/src/fam_adapter.py` provides the OpenClaw -> FAM boundary:

- `FAMLaunchRequest`: Dataclass for launch parameters
- `FAMLaunchResponse`: Dataclass for launch results
- `FAMAdapter.launch_foundup(request, actor_id) -> FAMLaunchResponse`
- `FAMAdapter.parse_launch_intent(message, sender) -> FAMLaunchRequest | None`
- `handle_fam_intent(message, sender) -> str`: Entry point for OpenClaw routing

OpenClaw routes `IntentCategory.FOUNDUP` intents to `fam_adapter` domain.

## Persistent verification integration boundary (planned)

The [R24 handoff contract](../../../docs/roadmaps/R24_AGENT_PRODUCTION_LINE_PACKET.md#persistent-proof-verification-handoff-contract--2026-09-23) specifies a future internal call to the existing
`PersistentTaskPipeline.verify_proof` after durable independent terminal WRE ACCEPT.
Staged assurance, repository-write grants and compute debit are insufficient.
The domain entitlement issuer/delegation decision remains unresolved; no route or
bridge is enabled. Exact proof binding, atomic decision/debit/event application
and replay/recovery require qualification before integration. Payout is separate.

## Optional API Surface (Future)
- `POST /foundups`
- `PATCH /foundups/{foundup_id}`
- `POST /foundups/{foundup_id}/agents/join`
- `POST /tasks`
- `POST /tasks/{task_id}/claim`
- `POST /tasks/{task_id}/proof`
- `POST /tasks/{task_id}/verify`
- `POST /tasks/{task_id}/payout`
- `GET /tasks/{task_id}/trace`
- `POST /compute/plans/activate`
- `POST /compute/credits/purchase`
- `POST /compute/credits/debit`
- `GET /compute/wallet/{actor_id}`

## Event Contract (Audit)
Every mutation emits an event containing:
- `event_id`, `event_type`, `timestamp`, `actor_id`
- `foundup_id`, optional `task_id`, optional `proof_id`, optional `payout_id`
- `payload` (small structured dict)

## Permission Rules (PoC)
- These role checks describe the in-memory PoC. Persistent pipeline compute access does not authenticate verifier/treasury roles; production role admission and settlement remain separate unresolved gates.
- Task verification allowed only for actor role `verifier`.
- Payout trigger allowed only for actor role `treasury`.
- Distribution publish allowed only for actor role `distribution`.
- Non-compliant actor/action pair raises `PermissionDeniedError`.

## OpenClaw/WRE Integration Boundary
FAM is callable as a domain module by OpenClaw routing and WRE orchestration. It does not own ingress/auth policy. It owns domain validation and state transitions.
