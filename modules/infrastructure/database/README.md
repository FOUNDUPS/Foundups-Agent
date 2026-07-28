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

## Signed-Worker Result Continuity

Every terminal or requeue attempt appends one chain-linked row to
`agents_signed_worker_result_history` in the same transaction as the task
transition. The durable ledger is not capped. Mutable task context carries
only the exact latest ten-entry tail. Admission compares that canonical tail
to the durable ledger before any runner call.

Malformed or gapped durable rows, shortened context tails, recomputed context
history, and pre-ledger context history all fail closed. Legacy rows require a
separate authenticated migration; runtime admission never infers or imports
durable authority from task context. A ledger-insert failure rolls back the
task transition and leaves the admitted task executing for governed recovery.

