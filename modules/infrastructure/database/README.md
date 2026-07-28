# Infrastructure Database Module

## Purpose
Shared persistence infrastructure for FoundUps runtime services.

This module provides:
- Backend-agnostic operational DB access (`sqlite` default, `postgres` optional)
- Module table prefix helpers
- Agent memory/state persistence helpers
- SQLite audit tooling for architecture drift checks

## Core Components
- `src/db_manager.py`: unified backend manager (WSP 78 runtime entrypoint)
- `src/module_db.py`: prefixed table helper for module-owned tables
- `src/agent_db.py`: agent memory/coordination schema and helpers
- `src/signed_worker_assurance_completion.py`: assurance completion inside the
  signed-worker result transaction
- `src/signed_worker_assurance_request.py`: canonical completion request
- `src/signed_worker_assurance_staging.py`: durable verifier-output staging
- `src/signed_worker_execution_binding.py`: pure claim/use/result binding checks
- `src/signed_worker_assignment.py`: protected namespace assignment and
  invalid-task quarantine
- `src/signed_worker_execution_lease.py`: durable bounded execution lease
  renewal
- `src/signed_worker_execution_store.py`: exact-CAS signed-worker finalization
- `src/signed_worker_result_history.py`: pure result-chain validation
- `src/signed_worker_result_ledger.py`: durable signed-worker result continuity
- `src/sqlite_audit.py`: repeatable SQLite health/inventory report utility

## What This Module Is Not
- Not the event store for FAM/DAE (those remain in their own modules).
- Not blockchain settlement logic.
- Not simulator render/state cache logic.

## Configuration

### Backend selection
- `FOUNDUPS_DB_ENGINE`: `sqlite` or `postgres` (optional)
- `FOUNDUPS_DB_PATH`: SQLite path (default `data/foundups.db`)
- `DATABASE_URL`: PostgreSQL URL when backend is postgres
- `FOUNDUPS_ENABLE_PGVECTOR`: `1` to attempt `CREATE EXTENSION vector` on postgres

### Default behavior
- Local default: SQLite at `data/foundups.db`
- If `DATABASE_URL` points to postgres and `FOUNDUPS_DB_ENGINE` is not forced to sqlite, postgres is used

## SQLite Audit Utility

Run audit with default target set:

```bash
python -m modules.infrastructure.database.src.sqlite_audit
```

Write report to file:

```bash
python -m modules.infrastructure.database.src.sqlite_audit \
  --output modules/infrastructure/database/memory/sqlite_audit_report.json
```

Audit specific targets:

```bash
python -m modules.infrastructure.database.src.sqlite_audit \
  --target data/foundups.db \
  --target modules/infrastructure/dae_daemon/memory/dae_audit.db
```

## Operational Rules
1. Use this module (or documented adapter boundaries) for relational operational state.
2. Do not treat derived UI/runtime state as accounting truth.
3. Keep event/audit and settlement boundaries explicit (see `ARCHITECTURE.md`).

## AgentDB Decomposition Plan

`src/agent_db.py` is an inherited compatibility monolith. New signed-worker
behavior must remain in bounded sibling modules; `AgentDB` may expose only
thin compatibility entrypoints. A dedicated migration must split schema
bootstrap, autonomous-task coordination, HoloIndex maintenance, and
independent-assurance APIs while preserving SQLite/PostgreSQL behavior and
the current public import surface. Until that migration lands, the exact
temporary WSP 62 no-growth ceiling is recorded in
`wsp_62_exemptions.yaml`.

## Signed-Worker Result Continuity

Every terminal or requeue attempt appends one chain-linked row to
`agents_signed_worker_result_history` in the same transaction as the task
transition. The durable ledger is not capped. Mutable task context carries
only the exact latest ten-entry tail. Admission compares that canonical tail
to the durable ledger before any runner call. The public finalizer requires a
result context containing exactly one new entry; unchanged history rejects.

Malformed or gapped durable rows, shortened context tails, recomputed context
history, and pre-ledger context history all fail closed. Legacy rows require a
separate authenticated migration; runtime admission never infers or imports
durable authority from task context. A ledger-insert failure rolls back the
task and assurance transitions and leaves the admitted task quarantined in
`executing` for explicit reconciliation.

Protected assignment and restart recovery are separate from result
finalization. Generic assignment rejects the `reddog-worker-dispatch-`
namespace. Dedicated assignment derives a task-bound principal from the
validated envelope and quarantines malformed pending tasks. A stale
pre-admission assignment is requeued only by exact CAS and only when no active
verifier reservation exists. Executing tasks hold a durable renewable lease
with a bounded four-hour horizon. Expired negative verifier evidence may roll
forward through the normal finalizer; missing, positive-only, corrupt, or
otherwise effect-unknown evidence is quarantined and is never reported as a
successful result.

