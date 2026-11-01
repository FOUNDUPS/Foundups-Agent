# INTERFACE - FoundUps Agent Market

## Module Contract
FoundUps Agent Market exposes stable contracts for launching tokenized FoundUps and coordinating task execution with auditable payout flow.

## CABR Canonical Intent
- CABR = Consensus-Driven Autonomous Benefit Rate (also referred to as Collective Autonomous Benefit Rate).
- WHY: CABR exists to power Proof of Benefit (PoB).
- HOW: Collective 0102 consensus determines CABR (consensus-driven process).
- RESULT: PoB drives protocol allocation/distribution; ROI is a downstream financial readout.

## Core Schemas

Quantity validation requires `type(value) is int` for TokenTerms.max_supply,
Task.reward_amount, Payout.amount, ComputePlan.monthly_credit_allocation,
ComputeWallet.credit_balance/reserved_credits, ComputeLedgerEntry.amount and
ComputeSession.credits_debited. Existing positive/nonnegative minima are unchanged;
no upper bound or asset denomination is established by these constructors.
LaunchOrchestrator preserves the raw initial reward and validates the planned Task
before domain adapter calls. Invalid input returns a failed LaunchResult with no
created artifacts; the existing launch.failed audit event remains. This is not
whole-launch rollback or validation of separate compute dictionary/ORM ingress.

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

`ChainAgnosticTokenFactory` selection contract:
- `chain_hint=None` uses only the configured default, initially `ChainType.MOCK`
  for local simulation; explicit `"mock"` selects the mock backend.
- Explicit chain names are trimmed/case-normalized. Empty, unsupported and
  non-string hints raise domain `ValidationError` rather than selecting a default.
- Missing/disconnected backends, health-check errors and chain identity changes
  raise `ValidationError`; deployment and vesting never select a fallback backend.
- The requested enum remains fixed through health checks and deployment-result
  validation. A successful result reporting another chain is rejected before
  caching/returning success. Such a result is checked after the backend call;
  this does not roll back an effect that backend may already have attempted.
- Backend deployment failure still raises `RuntimeError`. No public signatures
  changed. The launch orchestrator catches selection `ValidationError` and stops
  downstream work; a previously created registry row may remain.
- Mock metadata/addresses remain explicitly synthetic. No independent chain
  confirmation, real network/signer admission or durable deployment receipt is
  provided by these checks.

### AgentJoinService
- `submit_join_request(foundup_id: str, profile: AgentProfile) -> str`
- `approve_join_request(request_id: str, approver_id: str) -> AgentProfile`
- `list_agents(foundup_id: str) -> list[AgentProfile]`

### TaskPipelineService
- `create_task(task: Task) -> Task`
- `claim_task(task_id: str, agent_id: str) -> Task`
- `submit_proof(proof: Proof) -> Task`
- `verify_proof(task_id: str, verification: Verification, *, authorization: CallerAuthorization | None = None) -> Task`
- `trigger_payout(task_id: str, actor_id: str, *, authorization: CallerAuthorization | None = None) -> Payout`
- `get_task(task_id: str) -> Task`
- `get_trace(task_id: str) -> dict[str, object]`
- In-memory simulation: `open -> claimed -> submitted -> verified -> paid` with a simulated completed payout.
- Persistent SQLite initiation: `trigger_payout` delegates to `SQLiteAdapter.initiate_payout(task_id, actor_id)`. One write transaction binds task/proof/approved verification, pending payout, configured compute debit and correlated event. The task stays `VERIFIED`, payout `INITIATED`, with no settlement reference or `paid_at`.
- Exact same-actor retry returns the persisted initiation without another debit/event, using its original cost snapshot. Conflicting or incomplete lineage and ambiguous legacy history reject before effects; missing scope cannot be guessed unrelated. No historical repair or settlement is performed. See [R24 acceptance](../../../docs/roadmaps/R24_AGENT_PRODUCTION_LINE_PACKET.md#persistent-reward-initiation-contract--2026-09-22).

- Persistent SQLite verification uses one transaction for decision, debit, correlated event and approved task state. Rejection records its result once before raising `ValidationError`; exact rejected retries repeat that error without writes. Exact accepted retries return the current task and preserve pending payout linkage.
- Verification ID binds task/FoundUp/proof/artifact/verifier/approval/reason and normalized decision time. New naive times mean UTC; aware times convert to UTC with microseconds preserved. Replay uses original cost, without current-policy recharging. Conflicts, incomplete lineage and ambiguous relevant legacy history require reconciliation before further effects. See [fixed acceptance](../../../docs/roadmaps/R24_AGENT_PRODUCTION_LINE_PACKET.md#atomic-verification-acceptance--2026-09-23).
- This operation rejects non-SQLite before session/compute effects, leaves schema and adapter CRUD APIs unchanged, and confers no verifier/domain entitlement. SQLite history scans are complete rather than limited to the public ledger's 100-row view; large-history capacity is unqualified.

Host authorization contract (P0B, 2026-10-25):
- `CallerAuthorization(principal_id: str, role_grants: frozenset[tuple[str, str]])`
  is immutable host input, with exact `(foundup_id, role)` grants. Its constructor
  validates content; it is not an authentication credential or client payload.
- Missing/wrong-shaped context, wrong principal, wrong tenant or missing exact
  `verifier`/`treasury` role raises `PermissionDeniedError`. There is no implicit
  administrator, wildcard, paid-compute or profile-role entitlement.
- Verification must bind the requested task, its stored proof and assignee, and
  the supplied decision. The verifier must differ from the proof submitter and
  assignee, even if a host verifier grant exists.
- Both adapters require this context before privileged effects. SQLite checks it
  inside the existing write transaction, including exact retries and direct
  `SQLiteAdapter.initiate_payout(..., authorization=...)`; the pipeline forwards
  rather than duplicating the operation. Denial does not debit or write records.
- Authorized retries preserve the original accepted/rejected outcome and compute
  cost. Every retry requires explicit context; absent context or insufficient
  supplied grants deny. The host must re-resolve current identity/grants for each
  call: FAM implements no expiry or revocation detector for an old context object.
- Persistent initiation still returns an `INITIATED` payout without transaction
  reference or payment time; its task remains `VERIFIED`. In-memory completion
  is local simulation. Neither this context nor compute payment confirms funds.
- The host must obtain identity and grants independently from authenticated
  transport and an admitted issuer/policy. No FAM issuer or transport binding is
  implemented here. Never construct authority from request JSON, `verifier_id`,
  `actor_id`, an editable profile or a repository public-key claim.

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

**Shared persistence mappings:**
- `src/persistence/orm_models.py` owns the single Base and 14 row declarations. The original 13 mappings and `sqlite_adapter.Base`/row re-export identities remain unchanged; the probe row is imported directly from `orm_models`.
- Legacy pickle globals resolve; newly emitted row pickles name `orm_models` and require that module when loading, including rollback. No repository FAM pickle consumer was found; this is not a durable serialization-format guarantee. Migration3 adds only the probe-intent table; existing adapter methods are unchanged.

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
- `LATEST_SCHEMA_VERSION = 3`
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

### TestnetTransferIntentService (opt-in local API)

Explicit import owner: `src.persistence.testnet_transfer_intents`. Four frozen
slot dataclasses define `HostTestnetPolicy`, `SubmittedTestnetBinding`,
`PreparedTestnetIntent` and the service. No package export, resident runtime
caller, HTTP route, automatic task hook or transport is installed by this layer.

```python
service = TestnetTransferIntentService(adapter, host_policy)
prepared = service.prepare(
    payout_id, actor_id, binding, authorization=current_treasury_context,
)
```

The trusted host supplies policy independently of submitted fields. Its exact
`principal_id`, `foundup_id` and `payout_recipient_id` bind the pending payout;
`policy_id`/`policy_version` bind both records. Network must be
`algorand-testnet`, genesis ID `testnet-v1.0`, with a lowercase 64-hex genesis
hash. Both records bind asset ID/decimals, sender and expected authorization
address. The selected recipient must belong to the host's immutable nonempty
allowlist. Positive builtin integer `amount_atoms` and `fee_cap_microalgos` must
not exceed the host's per-intent caps. These caps do not reserve or aggregate
spending. No conversion from the payout's `reward_amount` occurs.

Exact declaration types and builtin scalar fields are checked before
serialization. Integers exclude booleans/coercions and are bounded by signed
SQLite 64-bit capacity; asset decimals are 0–19. IDs/text are nonempty bounded
strings without normalization. Submitted `format_version=1` and
`purpose="TEST_TRANSPORT_PROBE"` are required. Policy and binding expiry must
match exactly. The host UTC clock is sampled after acquiring the writer fence;
preparation and replay reject at or after expiry. There is no renewal API.

Each call, including a retry, requires current `CallerAuthorization` matching
the actor and exact FoundUp/treasury grant. The actor must equal the original
initiation actor. The host must authenticate the principal and resolve current
grants independently; the Python context supplies no issuer proof, signature,
revocation or credential-expiry service. Public address/genesis/asset strings
remain expected identity, without checksum, node, signer or funding verification.

Within the existing SQLite `BEGIN IMMEDIATE`/session commit owner, preparation
qualifies migration history exactly `[1,2,3]` and the actual table: exact columns,
TEXT/INTEGER affinities, nullability/primary key, no hidden/generated columns or
intent triggers, and unconditional binary-collated uniqueness on
`(payout_id,purpose)`. Missing/unqualified migration history, future versions and
supplied unsupported schemas fail closed; no rebuild, backfill or repair is
attempted. A constructor pin or disabled auto-migration does not by itself reject
an already qualified v3 database; actual recorded history/schema decides.
The existing `_payout_history` validates pending payout, independent stored
proof/decision and complete initiation lineage in that same session.

The new row stores full canonical host policy/submitted binding/payout scope
and initiation event ID/payload digest, with a content SHA-256. Retry compares
the complete expected content and stored mirrored fields, state and timestamps;
digest equality alone is insufficient. An exact unexpired retry after reopen
returns the original immutable scalar DTO, preserving creation time. Changed
content rejects; rollback and competing adapters retain one durable winner.
`NotFoundError` denotes an absent payout, `PermissionDeniedError` an authority
denial, and `ValidationError` rejected binding/history/schema/time. Existing
database/lock errors propagate with the existing session rollback semantics.

Only this row is inserted. The old 13 mapped tables remain unchanged: payout
`INITIATED`, task `VERIFIED`, no new correlated payout event or compute debit.
No SDK, private key, unsigned transaction, signer, broadcast, confirmation,
reservation or paid reward is implemented. This probe does not establish UPS/F_i
issuance, vesting, reserve backing or transfer/trading policy; the WSP26 policy
conflict remains unresolved. Local qualification and corrections are recorded in
[TestModLog](tests/TestModLog.md) and the
[allocated plan](../../../docs/architecture/FOUNDUPS_TESTNET_TRANSFER_INTENT_20261025.md).

#### Existing-only revalidation contract

```python
revalidate_existing(expected: PreparedTestnetIntent, actor_id: str,
    binding: SubmittedTestnetBinding, *, authorization=None) -> PreparedTestnetIntent
```

`expected` must be the exact captured DTO with exact builtin scalar types,
checked before rich equality. All fields bind: ID, scope, canonical identity JSON,
content hash, state, creation time and expiry. It supplies no authority.
The host independently resolves current policy and caller grants before each
call, including after later I/O; an old immutable context cannot detect revocation.
Reuse the current schema-3, payout/proof/decision/history, binding, actor and expiry
admission in one transaction. Require the row already exists and matches the full
captured DTO; absence, replacement or tampering rejects without insert or repair.
Success and denial preserve database/accounting state. `prepare` keeps its existing
get-or-create contract. This check proves only current admitted state, not continuous
presence or future signer authority; no formatter or resident consumer is added.

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
bridge is enabled. Local SQLite proof binding, atomic decision/debit/event and replay acceptance are
qualified in 164 cases. Cross-store delivery, signed domain authorization and runtime
admission still require qualification before integration. Payout is separate.

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
Domain event mutations emit an event containing:
- `event_id`, `event_type`, `timestamp`, `actor_id`
- `foundup_id`, optional `task_id`, optional `proof_id`, optional `payout_id`
- `payload` (small structured dict)

Local TestNet probe preparation stores only its intent row and deliberately emits
no payout event; it is not a domain payout transition.

## Permission Rules (PoC)
- These role checks describe the in-memory PoC. Persistent pipeline compute access does not authenticate verifier/treasury roles; production role admission and settlement remain separate unresolved gates.
- Task verification allowed only for actor role `verifier`.
- Payout trigger allowed only for actor role `treasury`.
- Distribution publish allowed only for actor role `distribution`.
- Non-compliant actor/action pair raises `PermissionDeniedError`.

## OpenClaw/WRE Integration Boundary
FAM is callable as a domain module by OpenClaw routing and WRE orchestration. It does not own ingress/auth policy. It owns domain validation and state transitions.
