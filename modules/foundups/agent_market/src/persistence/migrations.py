"""Schema migration utilities for FoundUps Agent Market persistence.

WSP References:
- WSP 30: Persistence layer design and versioning
- WSP 50: Deterministic migration failure handling
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from sqlalchemy import text
from sqlalchemy.engine import Engine

from ..exceptions import ValidationError

LATEST_SCHEMA_VERSION = 3


@dataclass(frozen=True)
class SchemaMigration:
    """Represents a single schema migration step."""

    version: int
    description: str
    statements: tuple[str, ...]


MIGRATIONS: tuple[SchemaMigration, ...] = (
    SchemaMigration(
        version=1,
        description="create query indexes for hot read paths",
        statements=(
            "CREATE INDEX IF NOT EXISTS idx_tasks_foundup_status ON tasks(foundup_id, status)",
            "CREATE INDEX IF NOT EXISTS idx_proofs_task_submitted_at ON proofs(task_id, submitted_at)",
            "CREATE INDEX IF NOT EXISTS idx_events_foundup_timestamp ON event_records(foundup_id, timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_payouts_task_status ON payouts(task_id, status)",
            "CREATE INDEX IF NOT EXISTS idx_distribution_foundup_published ON distribution_posts(foundup_id, published_at)",
        ),
    ),
    SchemaMigration(
        version=2,
        description="add compute access persistence tables and indexes",
        statements=(
            """
            CREATE TABLE IF NOT EXISTS compute_plans (
                actor_id TEXT PRIMARY KEY,
                plan_id TEXT NOT NULL UNIQUE,
                tier TEXT NOT NULL,
                status TEXT NOT NULL,
                monthly_credit_allocation INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS compute_wallets (
                actor_id TEXT PRIMARY KEY,
                wallet_id TEXT NOT NULL UNIQUE,
                credit_balance INTEGER NOT NULL DEFAULT 0,
                reserved_credits INTEGER NOT NULL DEFAULT 0,
                updated_at TIMESTAMP NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS compute_ledger_entries (
                entry_id TEXT PRIMARY KEY,
                actor_id TEXT NOT NULL,
                foundup_id TEXT,
                entry_type TEXT NOT NULL,
                amount INTEGER NOT NULL,
                rail TEXT,
                reason TEXT NOT NULL,
                payment_ref TEXT,
                event_id TEXT,
                created_at TIMESTAMP NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS compute_sessions (
                session_id TEXT PRIMARY KEY,
                actor_id TEXT NOT NULL,
                foundup_id TEXT NOT NULL,
                workload JSON NOT NULL,
                credits_debited INTEGER NOT NULL DEFAULT 0,
                proof_id TEXT,
                created_at TIMESTAMP NOT NULL
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_compute_plans_tier_status ON compute_plans(tier, status)",
            "CREATE INDEX IF NOT EXISTS idx_compute_wallets_balance ON compute_wallets(credit_balance)",
            "CREATE INDEX IF NOT EXISTS idx_compute_ledger_actor_created ON compute_ledger_entries(actor_id, created_at)",
            "CREATE INDEX IF NOT EXISTS idx_compute_ledger_foundup_created ON compute_ledger_entries(foundup_id, created_at)",
            "CREATE INDEX IF NOT EXISTS idx_compute_sessions_foundup_created ON compute_sessions(foundup_id, created_at)",
        ),
    ),
    SchemaMigration(
        version=3,
        description="add immutable local TestNet probe intents",
        statements=(
            """
            CREATE TABLE IF NOT EXISTS testnet_transfer_intents (
                intent_id TEXT NOT NULL PRIMARY KEY,
                payout_id TEXT NOT NULL,
                purpose TEXT NOT NULL CHECK(purpose='TEST_TRANSPORT_PROBE'),
                format_version INTEGER NOT NULL CHECK(format_version=1),
                state TEXT NOT NULL CHECK(state='PREPARED'),
                foundup_id TEXT NOT NULL,
                task_id TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                identity_json TEXT NOT NULL,
                identity_sha256 TEXT NOT NULL,
                created_at_epoch_s INTEGER NOT NULL,
                expires_at_epoch_s INTEGER NOT NULL,
                CONSTRAINT uq_testnet_payout_purpose UNIQUE(payout_id,purpose)
            )
            """,
        ),
    ),
)


class MigrationManager:
    """Applies idempotent, ordered schema migrations."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def ensure_migration_table(self) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        version INTEGER PRIMARY KEY,
                        description TEXT NOT NULL,
                        applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
            )

    def get_current_version(self) -> int:
        self.ensure_migration_table()
        with self.engine.begin() as conn:
            row = conn.execute(text("SELECT MAX(version) FROM schema_migrations")).scalar_one()
        return int(row or 0)

    def migrate(self, target_version: int = LATEST_SCHEMA_VERSION) -> int:
        """Apply migrations up to target_version."""
        self.ensure_migration_table()
        current = self.get_current_version()
        if target_version < current:
            raise ValidationError(
                f"Target schema version {target_version} is behind current version {current}"
            )

        pending = [m for m in MIGRATIONS if current < m.version <= target_version]
        for migration in pending:
            self._apply_migration(migration)
            current = migration.version
        return current

    def list_applied_versions(self) -> List[int]:
        """Return applied migration versions in ascending order."""
        self.ensure_migration_table()
        with self.engine.begin() as conn:
            rows = conn.execute(
                text("SELECT version FROM schema_migrations ORDER BY version ASC")
            ).fetchall()
        return [int(r[0]) for r in rows]

    def _apply_migration(self, migration: SchemaMigration) -> None:
        with self.engine.begin() as conn:
            for stmt in migration.statements:
                conn.execute(text(stmt))
            conn.execute(
                text(
                    """
                    INSERT INTO schema_migrations(version, description)
                    VALUES (:version, :description)
                    ON CONFLICT(version) DO NOTHING
                    """
                ),
                {"version": migration.version, "description": migration.description},
            )
