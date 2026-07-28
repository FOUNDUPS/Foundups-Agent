# Database Interface Specification

## Public Exports
From `modules.infrastructure.database`:

- `DatabaseManager`
- `ModuleDB`
- `AgentDB`
- `Database`
- `audit_sqlite_file`
- `run_sqlite_audit`

## Signed Worker Execution Store
File: `modules/infrastructure/database/src/signed_worker_execution_store.py`

### Public Function
- `finalize_signed_worker_execution(db, task_id, *, context, accepted, result_context, target_status=None, retry_not_before=None, assurance_completion=None) -> bool`

The finalizer updates only the exact executing task row bound to the admitted
assignee, claim receipt, one-use receipt and preclaim context digest. Requeue
clears assignment ownership; terminal transitions retain it. Any concurrent
row, context or receipt change fails closed.
`result_context` is mandatory and must contain exactly one new canonical
result-history entry. Missing or unchanged history never reaches a terminal
or requeue state.

Signed-worker execution claims include a fixed 15-minute lease. The OpenClaw
supervisor runs a bounded recovery scan before claiming more work. An expired
claim is never retried automatically: exact durable negative assurance may
roll forward through the same finalizer, other effect-unknown executions
become failed, and digest-only positive assurance remains blocked. Generic
create, retry, requeue, and completion APIs reject the reserved
`reddog-worker-dispatch-` namespace.

## Signed Worker Result Ledger
File: `modules/infrastructure/database/src/signed_worker_result_ledger.py`

### Public Functions
- `validated_result_history(context) -> Mapping[str, Any]`
- `validate_result_history_ledger(connection, task_id, context) -> bool`
- `persist_result_history_ledger(connection, task_id, context, *, claim_receipt_id, use_receipt_id) -> bool`

The ledger is independently durable from mutable autonomous-task context.
Each result is appended in the same transaction as exact-CAS task
finalization. Both supervisor and direct task admission require the canonical
context tail to match the full ledger before execution. Fully re-hashed,
truncated, reordered, substituted, or unchanged final histories fail closed.

## DatabaseManager
File: `modules/infrastructure/database/src/db_manager.py`

### Responsibilities
- Resolve backend (`sqlite` or `postgres`)
- Provide transactional connection context manager
- Offer query/write helpers and metadata helpers

### Key Methods
- `get_connection() -> context manager`
- `execute_query(query, params=()) -> list[dict]`
- `execute_write(query, params=()) -> int`
- `table_exists(table_name) -> bool`
- `get_table_info(table_name) -> list[dict]`
- `backup_database(backup_path) -> bool` (sqlite only)
- `backend_info() -> dict`
- `get_stats() -> dict`
- `reset_for_tests() -> None` (class method)

### Environment Variables
- `FOUNDUPS_DB_ENGINE`
- `FOUNDUPS_DB_PATH`
- `DATABASE_URL`
- `FOUNDUPS_ENABLE_PGVECTOR`

## ModuleDB
File: `modules/infrastructure/database/src/module_db.py`

### Responsibilities
- Enforce module table prefix convention: `modules_{module_name}_{table}`
- Provide CRUD convenience methods over prefixed tables

### Key Methods
- `create_table(table_name, schema)`
- `insert(table_name, data)`
- `update(table_name, data, where_clause, where_params)`
- `delete(table_name, where_clause, where_params)`
- `select(table_name, where_clause="", where_params=(), order_by="", limit=0)`
- `count(table_name, where_clause="", where_params=())`
- `upsert(table_name, data, id_field="id")`

## AgentDB
File: `modules/infrastructure/database/src/agent_db.py`

### Responsibilities
- Persist shared agent state and coordination artifacts
- Manage agent-related schemas (`agents_*` and supporting tables)

### Representative Methods
- `record_awakening(agent_id, consciousness_level, koan=None)`
- `get_awakening_state(agent_id) -> dict | None`
- `learn_pattern(agent_id, pattern_type, pattern_data) -> int`
- `get_patterns(agent_id=None, pattern_type=None, limit=50) -> list[dict]`
- `record_error(error_hash, error_type, solution)`
- `get_error_solution(error_hash) -> dict | None`

### Independent Assurance Reservations

- `reserve_independent_assurance(request) -> dict`
- `get_independent_assurance_reservation(reservation_id) -> dict`
- `get_independent_assurance_reservation_for_task(task_id, task_kind=...) -> dict`
- `renew_independent_assurance(request) -> dict`
- `stage_independent_assurance_completion(request) -> dict`
- `complete_independent_assurance(...) -> REJECTED` (detached completion is
  forbidden)
- `revoke_independent_assurance(reservation_id, ...) -> dict`
- `expire_independent_assurance_reservations() -> dict`
- `finalize_signed_worker_execution(..., assurance_completion=...) -> bool`

Reservation admission atomically claims one pending verifier task and inserts
one digest-bound lease. Author and verifier principals must differ. Snapshot,
work order, queue item, WSP 15 allocation, runtime, capability, and task
bindings are revalidated from the persisted task contexts. Verifier
completion is accepted only inside the signed-worker task/result-ledger
transaction; the detached AgentDB method always rejects. Revocation,
expiration, replay, and competing reservations fail closed.
The verifier may first stage one exact completion request while its task is
`executing`; exact replay is idempotent and any altered second request rejects.
Renewal preserves the immutable admission digest, is limited to three
renewals and a six-hour total lease horizon, and requires the original author
task to have completed successfully. Admission rejects any author already
claimed by another worker. Terminal completion revalidates the immutable
admission digest, verifier task/principal, lease expiry, receipt-bound
completion request, exact task row, and result ledger before one commit.

### Exact-SHA HoloIndex Maintenance Transactions

- `create_autonomous_task_if_absent(...) -> bool`
- `claim_holoindex_postmerge_task(...) -> bool`
- `fail_holoindex_postmerge_task(...) -> bool`
- `reclaim_expired_holoindex_postmerge_task(...) -> bool`
- `commit_holoindex_postmerge_completion(...) -> bool`

The claim is a `pending -> assigned` compare-and-swap over the exact serialized
context. It publishes a one-use claim ID, canonical context digest, and
expiry in the same transaction. The executor must atomically consume that
claim through `assigned -> executing` before any effect. Completion is one
database transaction: validate the executing claim and request digest, insert
the completion event, resolve the request, and mark the task completed.
Both terminal updates compare the exact serialized task context and request
payload observed in that transaction.
Competing claims and partial completion writes fail closed.
Expired claims are reclaimed only by exact worker and assignment timestamp,
then re-enter the coordinator's bounded retry path.

### Signed-Worker Result Continuity

- `ensure_result_history_schema(connection) -> None`
- `validate_result_history_ledger(connection, task_id, context) -> bool`
- `persist_result_history_ledger(connection, task_id, context, ...) -> bool`
- `validated_result_history(context) -> Mapping[str, Any]`

The AgentDB ledger retains every attempt. Task context retains the canonical
latest ten attempts and must equal the ledger tail exactly. Supervisor and
direct `run_task` completion both build the same result receipt and append the
ledger row atomically with the task transition. Context history with no
corresponding durable rows is quarantined rather than promoted.

## SQLite Audit API
File: `modules/infrastructure/database/src/sqlite_audit.py`

### Types
- `AuditOptions(max_tables=20, include_table_counts=True)`

### Functions
- `audit_sqlite_file(path: Path, options: AuditOptions | None = None) -> dict`
- `run_sqlite_audit(targets: Sequence[Path | str] | None = None, options: AuditOptions | None = None) -> dict`

### CLI
```bash
python -m modules.infrastructure.database.src.sqlite_audit [options]
```

Options:
- `--target <path>` (repeatable)
- `--max-tables <n>`
- `--no-table-counts`
- `--output <path>`

## Contract Boundaries
1. This module owns operational relational persistence primitives.
2. FAM/DAE event stores are separate modules and should not be bypassed for audit/event writes.
3. Blockchain settlement anchoring is out of scope for this module.
