"""SQLite persistence adapter for FoundUps Agent Market.

Provides CRUD operations for all FAM domain models using SQLAlchemy 2.0 ORM.
WAL mode enabled for concurrency support.

WSP References:
- WSP 11: Interface contract adherence
- WSP 30: Persistence layer design
- WSP 50: Error handling standards
"""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from ..exceptions import InvalidStateTransitionError, NotFoundError, PermissionDeniedError, ValidationError
from .migrations import LATEST_SCHEMA_VERSION, MigrationManager
from ..models import (
    AgentProfile,
    DistributionPost,
    EventRecord,
    Foundup,
    Payout,
    PayoutStatus,
    Proof,
    Task,
    TaskStatus,
    TokenTerms,
    Verification,
)

# Compatibility exports preserve existing persistence imports.
from .orm_models import (
    Base as Base,
    FoundupRow as FoundupRow,
    TokenTermsRow as TokenTermsRow,
    AgentProfileRow as AgentProfileRow,
    TaskRow as TaskRow,
    ProofRow as ProofRow,
    VerificationRow as VerificationRow,
    PayoutRow as PayoutRow,
    DistributionPostRow as DistributionPostRow,
    EventRecordRow as EventRecordRow,
    ComputePlanRow as ComputePlanRow,
    ComputeWalletRow as ComputeWalletRow,
    ComputeLedgerEntryRow as ComputeLedgerEntryRow,
    ComputeSessionRow as ComputeSessionRow,
)

logger = logging.getLogger(__name__)


# Enable WAL mode for SQLite
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection: Any, connection_record: Any) -> None:
    # Guard PRAGMA calls so non-SQLite engines (e.g. Postgres) are unaffected.
    if not dbapi_connection.__class__.__module__.startswith("sqlite3"):
        return
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def _compute_decision(adapter, sess, actor_id, capability, foundup_id):
    """Evaluate the existing compute policy using the caller's transaction."""
    required = max(0, int(adapter.compute_meter_costs.get(capability, 0)))
    wallet = adapter._ensure_wallet_row(sess, actor_id)
    plan = sess.get(ComputePlanRow, actor_id)
    tier = plan.tier if plan else "scout"
    available = int(wallet.credit_balance)
    allowed, reason = True, "ok"
    if not adapter.compute_access_enforced or required <= 0:
        reason = "access not enforced" if not adapter.compute_access_enforced else "unmetered capability"
    elif plan is None or plan.status != "active":
        allowed, reason = False, "active compute plan required"
    elif tier == "scout":
        allowed, reason = False, "tier 'scout' cannot execute metered capabilities"
    elif available < required:
        allowed, reason = False, "insufficient compute credits"
    return {
        "allowed": allowed, "reason": reason, "required_credits": required,
        "available_credits": available, "tier": tier, "capability": capability,
        "foundup_id": foundup_id,
    }


def _debit_in_session(adapter, sess, actor_id, amount, reason, foundup_id, event_id=None):
    """Stage the ordinary debit, optionally linked to an initiation event."""
    now = adapter._now_utc()
    wallet = adapter._ensure_wallet_row(sess, actor_id)
    if int(wallet.credit_balance) < int(amount):
        raise PermissionDeniedError(
            f"insufficient compute credits (available={wallet.credit_balance}, requested={amount})"
        )
    wallet.credit_balance -= int(amount)
    wallet.updated_at = now
    entry = ComputeLedgerEntryRow(
        entry_id=adapter._next_id("cc"), actor_id=actor_id, foundup_id=foundup_id,
        entry_type="debit", amount=int(amount), rail="metered_execution",
        reason=reason, payment_ref=None, event_id=event_id, created_at=now,
    )
    sess.add(entry)
    return {
        "entry_id": entry.entry_id, "actor_id": actor_id, "entry_type": entry.entry_type,
        "amount": int(entry.amount), "reason": entry.reason, "foundup_id": foundup_id,
        "credit_balance": int(wallet.credit_balance),
    }


def _payout_require(condition, reason):
    if not condition:
        raise ValidationError(f"Payout initiation requires reconciliation: {reason}")


def _payout_text(value):
    return isinstance(value, str) and bool(value.strip())


def _payout_identity(sess, task):
    """Snapshot existing proof/verification bindings, not settlement authority."""
    if task.status != TaskStatus.VERIFIED:
        raise InvalidStateTransitionError("Payout initiation requires VERIFIED task")
    _payout_require(all(_payout_text(value) for value in (
        task.task_id, task.foundup_id, task.assignee_id, task.proof_id, task.verification_id,
    )), "missing task identity")
    _payout_require(sess.get(FoundupRow, task.foundup_id) is not None, "missing FoundUp")
    _payout_require(type(task.reward_amount) is int and task.reward_amount > 0, "invalid reward")
    proof = sess.get(ProofRow, task.proof_id)
    verification = sess.get(VerificationRow, task.verification_id)
    _payout_require(proof is not None and verification is not None, "missing proof/verification")
    _payout_require(proof.task_id == task.task_id and proof.submitter_id == task.assignee_id,
                    "proof does not bind task and recipient")
    _payout_require(verification.task_id == task.task_id and verification.approved is True,
                    "verification does not approve task")
    _payout_require(all(_payout_text(value) for value in (
        proof.artifact_uri, proof.artifact_hash, verification.verifier_id, verification.reason,
    )), "incomplete proof/verification")
    return {
        "initiation_version": 1, "foundup_id": task.foundup_id, "task_id": task.task_id,
        "proof_id": proof.proof_id, "verification_id": verification.verification_id,
        "recipient_id": task.assignee_id, "amount": task.reward_amount,
        "proof_snapshot": {
            "submitter_id": proof.submitter_id, "artifact_uri": proof.artifact_uri,
            "artifact_hash": proof.artifact_hash, "notes": proof.notes,
            "submitted_at": proof.submitted_at.isoformat(),
        },
        "verification_snapshot": {
            "verifier_id": verification.verifier_id, "approved": verification.approved,
            "reason": verification.reason, "verified_at": verification.verified_at.isoformat(),
        },
    }


def _payout_reference_scopes(sess, refs):
    """Follow supplied identities before classifying a record as unrelated."""
    scopes = []
    for model, identity in refs:
        if not _payout_text(identity):
            scopes.append(None)
            continue
        row = sess.get(model, identity)
        if row is not None and model is not TaskRow:
            row = sess.get(TaskRow, row.task_id)
        scopes.append(row.foundup_id if row is not None else None)
    return scopes


def _payout_event_scopes(sess, event_row):
    scopes, refs = [event_row.foundup_id], []
    payload = event_row.payload
    if not isinstance(payload, dict):
        return scopes + [None]
    if "foundup_id" in payload:
        scopes.append(payload["foundup_id"])
    for field, model in (("task_id", TaskRow), ("proof_id", ProofRow),
                         ("payout_id", PayoutRow), ("verification_id", VerificationRow)):
        value = getattr(event_row, field, None)
        if value is not None:
            refs.append((model, value))
        if field in payload:
            refs.append((model, payload[field]))
    return scopes + _payout_reference_scopes(sess, refs)


def _payout_scope_requires_check(sess, foundup_id, scopes):
    if any(not _payout_text(scope) or sess.get(FoundupRow, scope) is None for scope in scopes):
        return True
    return len(set(scopes)) != 1 or foundup_id in scopes


def _payout_event_mentions(event_row, task_id, payout_id):
    payload = event_row.payload if isinstance(event_row.payload, dict) else {}
    return (event_row.task_id == task_id or event_row.payout_id == payout_id
            or payload.get("task_id") == task_id or payload.get("payout_id") == payout_id)


def _validate_pending_payout(sess, event_row, events, payouts, ledger):
    """Require complete durable identity, including every linked ledger row."""
    _payout_require(event_row.event_type == "payout.initiated" and _payout_text(event_row.event_id)
                    and _payout_text(event_row.actor_id),
                    "invalid initiation event")
    task = sess.get(TaskRow, event_row.task_id) if _payout_text(event_row.task_id) else None
    _payout_require(task is not None, "event has no task")
    identity = _payout_identity(sess, task)
    rows = [row for row in payouts if row.task_id == task.task_id]
    _payout_require(len(rows) == 1, "missing or duplicate payouts")
    payout = rows[0]
    _payout_require(_payout_text(payout.payout_id)
                    and task.payout_id == payout.payout_id == event_row.payout_id,
                    "unbound payout")
    _payout_require(payout.status == PayoutStatus.INITIATED and payout.reference is None
                    and payout.paid_at is None, "not an unsettled initiation")
    _payout_require(payout.recipient_id == task.assignee_id and payout.amount == task.reward_amount,
                    "payout recipient/amount mismatch")
    _payout_require(event_row.foundup_id == task.foundup_id and event_row.proof_id == task.proof_id,
                    "event scope/proof mismatch")
    payload = event_row.payload
    _payout_require(isinstance(payload, dict), "invalid event payload")
    cost = payload.get("required_credits")
    _payout_require(type(cost) is int and cost >= 0, "missing historical compute cost")
    expected = dict(identity, payout_id=payout.payout_id, required_credits=cost)
    _payout_require(payload == expected and type(payload.get("amount")) is int
                    and type(payload.get("initiation_version")) is int
                    and payload["verification_snapshot"]["approved"] is True,
                    "event identity changed or incomplete")
    _payout_require(sum(_payout_event_mentions(row, task.task_id, payout.payout_id)
                        for row in events) == 1, "duplicate or conflicting initiation events")
    debits = [row for row in ledger if row.event_id == event_row.event_id]
    _payout_require(len(debits) == (1 if cost else 0), "historical debit cardinality mismatch")
    for debit in debits:
        _payout_require(debit.actor_id == event_row.actor_id and debit.foundup_id == task.foundup_id
                        and debit.entry_type == "debit" and debit.reason == "trigger_payout"
                        and debit.rail == "metered_execution" and debit.payment_ref is None
                        and type(debit.amount) is int and debit.amount == cost,
                        "historical debit identity mismatch")
    return payout


def _payout_history(sess, foundup_id):
    """Check complete relevant history; missing scope holds across FoundUps."""
    all_events = {row.event_id: row for row in sess.query(EventRecordRow).all()}
    ledger, payouts = sess.query(ComputeLedgerEntryRow).all(), sess.query(PayoutRow).all()
    referenced = {row.event_id for row in ledger if row.reason == "trigger_payout"}
    events = [row for row in all_events.values() if row.event_id in referenced
              or row.event_type.startswith("payout.") or row.payout_id is not None
              or isinstance(row.payload, dict) and "payout_id" in row.payload]
    checked = {}
    for event_row in events:
        scopes = _payout_event_scopes(sess, event_row)
        scopes += [row.foundup_id for row in ledger if row.event_id == event_row.event_id]
        if _payout_scope_requires_check(sess, foundup_id, scopes):
            payout = _validate_pending_payout(sess, event_row, events, payouts, ledger)
            checked[payout.payout_id] = event_row
    event_ids = {row.event_id for row in events}
    for debit in ledger:
        if debit.reason != "trigger_payout" and debit.event_id not in event_ids:
            continue
        event_row = all_events.get(debit.event_id)
        scopes = [debit.foundup_id]
        if debit.event_id is not None:
            scopes += _payout_event_scopes(sess, event_row) if event_row is not None else [None]
        if _payout_scope_requires_check(sess, foundup_id, scopes):
            _payout_require(event_row is not None and event_row.payout_id in checked,
                            "ambiguous legacy debit residue")
    for payout in payouts:
        scopes = _payout_reference_scopes(sess, [(TaskRow, payout.task_id)])
        if _payout_scope_requires_check(sess, foundup_id, scopes):
            _payout_require(payout.payout_id in checked, "orphaned or legacy payout")
    return checked


def _stage_payout(adapter, sess, task, actor_id, identity):
    decision = _compute_decision(adapter, sess, actor_id, "payout.trigger", task.foundup_id)
    if not decision["allowed"]:
        raise PermissionDeniedError(str(decision["reason"]))
    cost, event_id = decision["required_credits"], adapter._next_id("evt")
    payout = PayoutRow(
        payout_id=adapter._next_id("pay"), task_id=task.task_id, recipient_id=task.assignee_id,
        amount=task.reward_amount, status=PayoutStatus.INITIATED, reference=None, paid_at=None,
    )
    if cost > 0:
        _debit_in_session(adapter, sess, actor_id, cost, "trigger_payout", task.foundup_id, event_id)
    task.payout_id = payout.payout_id
    sess.add(payout)
    sess.add(EventRecordRow(
        event_id=event_id, event_type="payout.initiated", actor_id=actor_id,
        payload=dict(identity, payout_id=payout.payout_id, required_credits=cost),
        foundup_id=task.foundup_id, task_id=task.task_id, proof_id=task.proof_id,
        payout_id=payout.payout_id, timestamp=adapter._now_utc(),
    ))
    return payout


def _payout_value(row):
    return Payout(payout_id=row.payout_id, task_id=row.task_id, recipient_id=row.recipient_id,
                  amount=row.amount, status=row.status, reference=row.reference, paid_at=row.paid_at)


class SQLiteAdapter:
    """SQLite persistence adapter with SQLAlchemy 2.0 ORM.

    Provides CRUD operations for all FAM domain models.
    Uses WAL mode for concurrent access support.

    Example:
        adapter = SQLiteAdapter("path/to/fam.db")
        foundup = adapter.create_foundup(foundup_data)
        adapter.close()
    """

    def __init__(
        self,
        db_path: str | Path | None = None,
        *,
        auto_migrate: bool | None = None,
        schema_version: int | None = None,
    ) -> None:
        """Initialize SQLite adapter.

        Args:
            db_path: Path to SQLite database file. Defaults to
                     FAM_DB_PATH env var or './fam_data/fam.db'.
        """
        if db_path is None:
            db_path = os.environ.get("FAM_DB_PATH", "./fam_data/fam.db")

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            echo=os.environ.get("FAM_DB_ECHO", "").lower() == "true",
            pool_pre_ping=True,
        )
        self._SessionFactory = sessionmaker(bind=self.engine, expire_on_commit=False)

        # Create tables and run idempotent migrations.
        Base.metadata.create_all(self.engine)
        migrate = (
            auto_migrate
            if auto_migrate is not None
            else os.environ.get("FAM_DB_AUTO_MIGRATE", "1").strip() not in {"0", "false", "False"}
        )
        if migrate:
            target_version = schema_version if schema_version is not None else LATEST_SCHEMA_VERSION
            MigrationManager(self.engine).migrate(target_version=target_version)
        logger.info("SQLiteAdapter initialized: %s", self.db_path)
        self.compute_access_enforced = (
            os.environ.get("FAM_COMPUTE_ACCESS_ENFORCED", "0").strip() in {"1", "true", "True"}
        )
        self.compute_default_credits = max(
            0,
            int(os.environ.get("FAM_COMPUTE_DEFAULT_CREDITS", "0")),
        )
        self.compute_meter_costs: Dict[str, int] = {
            "foundup.launch": 10,
            "task.create": 2,
            "task.claim": 1,
            "proof.submit": 2,
            "proof.verify": 2,
            "payout.trigger": 1,
            "distribution.publish": 1,
            "treasury.transfer_propose": 1,
        }

    def close(self) -> None:
        """Close database connection."""
        self.engine.dispose()
        logger.info("SQLiteAdapter closed")

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """Context manager for database sessions."""
        sess = self._SessionFactory()
        try:
            yield sess
            sess.commit()
        except Exception:
            sess.rollback()
            raise
        finally:
            sess.close()

    # --- Foundup CRUD ---

    def create_foundup(self, foundup: Foundup) -> Foundup:
        """Create a new Foundup record."""
        with self.session() as sess:
            existing_symbol = (
                sess.query(FoundupRow)
                .filter(FoundupRow.token_symbol.ilike(foundup.token_symbol))
                .first()
            )
            if existing_symbol is not None:
                raise ValidationError(
                    f"token_symbol '{foundup.token_symbol}' already exists"
                )
            row = FoundupRow(
                foundup_id=foundup.foundup_id,
                name=foundup.name,
                owner_id=foundup.owner_id,
                token_symbol=foundup.token_symbol,
                immutable_metadata=foundup.immutable_metadata,
                mutable_metadata=foundup.mutable_metadata,
                created_at=foundup.created_at,
            )
            sess.add(row)
        logger.debug("Created Foundup: %s", foundup.foundup_id)
        return foundup

    def get_foundup(self, foundup_id: str) -> Foundup:
        """Get a Foundup by ID."""
        with self.session() as sess:
            row = sess.get(FoundupRow, foundup_id)
            if row is None:
                raise NotFoundError(f"Foundup not found: {foundup_id}")
            return Foundup(
                foundup_id=row.foundup_id,
                name=row.name,
                owner_id=row.owner_id,
                token_symbol=row.token_symbol,
                immutable_metadata=dict(row.immutable_metadata),
                mutable_metadata=dict(row.mutable_metadata),
                created_at=row.created_at,
            )

    def update_foundup(self, foundup_id: str, updates: Dict[str, str]) -> Foundup:
        """Update mutable_metadata of a Foundup."""
        with self.session() as sess:
            row = sess.get(FoundupRow, foundup_id)
            if row is None:
                raise NotFoundError(f"Foundup not found: {foundup_id}")
            current = dict(row.mutable_metadata)
            current.update(updates)
            row.mutable_metadata = current
        return self.get_foundup(foundup_id)

    def list_foundups(self, limit: int = 100) -> List[Foundup]:
        """List all Foundups."""
        with self.session() as sess:
            rows = sess.query(FoundupRow).limit(limit).all()
            return [
                Foundup(
                    foundup_id=r.foundup_id,
                    name=r.name,
                    owner_id=r.owner_id,
                    token_symbol=r.token_symbol,
                    immutable_metadata=dict(r.immutable_metadata),
                    mutable_metadata=dict(r.mutable_metadata),
                    created_at=r.created_at,
                )
                for r in rows
            ]

    # --- Task CRUD ---

    def create_task(self, task: Task) -> Task:
        """Create a new Task record."""
        with self.session() as sess:
            row = TaskRow(
                task_id=task.task_id,
                foundup_id=task.foundup_id,
                title=task.title,
                description=task.description,
                acceptance_criteria=task.acceptance_criteria,
                reward_amount=task.reward_amount,
                creator_id=task.creator_id,
                status=task.status,
                assignee_id=task.assignee_id,
                proof_id=task.proof_id,
                verification_id=task.verification_id,
                payout_id=task.payout_id,
                created_at=task.created_at,
            )
            sess.add(row)
        logger.debug("Created Task: %s", task.task_id)
        return task

    def get_task(self, task_id: str) -> Task:
        """Get a Task by ID."""
        with self.session() as sess:
            row = sess.get(TaskRow, task_id)
            if row is None:
                raise NotFoundError(f"Task not found: {task_id}")
            return self._row_to_task(row)

    def update_task(self, task: Task) -> Task:
        """Update a Task record."""
        with self.session() as sess:
            row = sess.get(TaskRow, task.task_id)
            if row is None:
                raise NotFoundError(f"Task not found: {task.task_id}")
            row.status = task.status
            row.assignee_id = task.assignee_id
            row.proof_id = task.proof_id
            row.verification_id = task.verification_id
            row.payout_id = task.payout_id
        return self.get_task(task.task_id)

    def list_tasks(self, foundup_id: str, limit: int = 100) -> List[Task]:
        """List Tasks for a Foundup."""
        with self.session() as sess:
            rows = sess.query(TaskRow).filter(TaskRow.foundup_id == foundup_id).limit(limit).all()
            return [self._row_to_task(r) for r in rows]

    def _row_to_task(self, row: TaskRow) -> Task:
        return Task(
            task_id=row.task_id,
            foundup_id=row.foundup_id,
            title=row.title,
            description=row.description,
            acceptance_criteria=list(row.acceptance_criteria),
            reward_amount=row.reward_amount,
            creator_id=row.creator_id,
            status=row.status,
            assignee_id=row.assignee_id,
            proof_id=row.proof_id,
            verification_id=row.verification_id,
            payout_id=row.payout_id,
            created_at=row.created_at,
        )

    # --- Proof CRUD ---

    def create_proof(self, proof: Proof) -> Proof:
        """Create a new Proof record."""
        with self.session() as sess:
            row = ProofRow(
                proof_id=proof.proof_id,
                task_id=proof.task_id,
                submitter_id=proof.submitter_id,
                artifact_uri=proof.artifact_uri,
                artifact_hash=proof.artifact_hash,
                notes=proof.notes,
                submitted_at=proof.submitted_at,
            )
            sess.add(row)
        logger.debug("Created Proof: %s", proof.proof_id)
        return proof

    def get_proof(self, proof_id: str) -> Proof:
        """Get a Proof by ID."""
        with self.session() as sess:
            row = sess.get(ProofRow, proof_id)
            if row is None:
                raise NotFoundError(f"Proof not found: {proof_id}")
            return Proof(
                proof_id=row.proof_id,
                task_id=row.task_id,
                submitter_id=row.submitter_id,
                artifact_uri=row.artifact_uri,
                artifact_hash=row.artifact_hash,
                notes=row.notes,
                submitted_at=row.submitted_at,
            )

    # --- Verification CRUD ---

    def create_verification(self, verification: Verification) -> Verification:
        """Create a new Verification record."""
        with self.session() as sess:
            row = VerificationRow(
                verification_id=verification.verification_id,
                task_id=verification.task_id,
                verifier_id=verification.verifier_id,
                approved=verification.approved,
                reason=verification.reason,
                verified_at=verification.verified_at,
            )
            sess.add(row)
        logger.debug("Created Verification: %s", verification.verification_id)
        return verification

    def get_verification(self, verification_id: str) -> Verification:
        """Get a Verification by ID."""
        with self.session() as sess:
            row = sess.get(VerificationRow, verification_id)
            if row is None:
                raise NotFoundError(f"Verification not found: {verification_id}")
            return Verification(
                verification_id=row.verification_id,
                task_id=row.task_id,
                verifier_id=row.verifier_id,
                approved=row.approved,
                reason=row.reason,
                verified_at=row.verified_at,
            )

    # --- Payout CRUD ---

    def create_payout(self, payout: Payout) -> Payout:
        """Create a new Payout record."""
        with self.session() as sess:
            row = PayoutRow(
                payout_id=payout.payout_id,
                task_id=payout.task_id,
                recipient_id=payout.recipient_id,
                amount=payout.amount,
                status=payout.status,
                reference=payout.reference,
                paid_at=payout.paid_at,
            )
            sess.add(row)
        logger.debug("Created Payout: %s", payout.payout_id)
        return payout

    def get_payout(self, payout_id: str) -> Payout:
        """Get a Payout by ID."""
        with self.session() as sess:
            row = sess.get(PayoutRow, payout_id)
            if row is None:
                raise NotFoundError(f"Payout not found: {payout_id}")
            return Payout(
                payout_id=row.payout_id,
                task_id=row.task_id,
                recipient_id=row.recipient_id,
                amount=row.amount,
                status=row.status,
                reference=row.reference,
                paid_at=row.paid_at,
            )

    def update_payout(self, payout: Payout) -> Payout:
        """Update a Payout record."""
        with self.session() as sess:
            row = sess.get(PayoutRow, payout.payout_id)
            if row is None:
                raise NotFoundError(f"Payout not found: {payout.payout_id}")
            row.status = payout.status
            row.reference = payout.reference
            row.paid_at = payout.paid_at
        return self.get_payout(payout.payout_id)

    def initiate_payout(self, task_id: str, actor_id: str) -> Payout:
        """Atomically record an unsettled SQLite initiation or its exact retry.

        The write fence covers this operation, not unrelated wallet writers.
        No treasury role or external settlement authority is conferred here.
        """
        if self.engine.dialect.name != "sqlite":
            raise ValidationError("Atomic payout initiation supports SQLite only")
        _payout_require(_payout_text(task_id) and _payout_text(actor_id), "missing caller identity")
        with self.session() as sess:
            sess.execute(text("BEGIN IMMEDIATE"))
            task = sess.get(TaskRow, task_id)
            if task is None:
                raise NotFoundError(f"Task not found: {task_id}")
            identity = _payout_identity(sess, task)
            checked = _payout_history(sess, task.foundup_id)
            rows = sess.query(PayoutRow).filter(PayoutRow.task_id == task_id).all()
            if task.payout_id is not None:
                event_row = checked.get(task.payout_id)
                _payout_require(len(rows) == 1 and rows[0].payout_id == task.payout_id
                                and event_row is not None and event_row.task_id == task_id
                                and event_row.actor_id == actor_id,
                                "retry actor or payout identity mismatch")
                return _payout_value(rows[0])
            _payout_require(not rows, "unbound task payout")
            payout = _stage_payout(self, sess, task, actor_id, identity)
            return _payout_value(payout)

    # --- EventRecord CRUD ---

    def create_event(self, event: EventRecord) -> EventRecord:
        """Create a new EventRecord."""
        with self.session() as sess:
            row = EventRecordRow(
                event_id=event.event_id,
                event_type=event.event_type,
                actor_id=event.actor_id,
                payload=event.payload,
                foundup_id=event.foundup_id,
                task_id=event.task_id,
                proof_id=event.proof_id,
                payout_id=event.payout_id,
                timestamp=event.timestamp,
            )
            sess.add(row)
        logger.debug("Created EventRecord: %s", event.event_id)
        return event

    def query_events(
        self,
        foundup_id: Optional[str] = None,
        task_id: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[EventRecord]:
        """Query EventRecords with optional filters."""
        with self.session() as sess:
            query = sess.query(EventRecordRow)
            if foundup_id:
                query = query.filter(EventRecordRow.foundup_id == foundup_id)
            if task_id:
                query = query.filter(EventRecordRow.task_id == task_id)
            if event_type:
                query = query.filter(EventRecordRow.event_type == event_type)
            rows = query.order_by(EventRecordRow.timestamp.desc()).limit(limit).all()
            return [
                EventRecord(
                    event_id=r.event_id,
                    event_type=r.event_type,
                    actor_id=r.actor_id,
                    payload=dict(r.payload),
                    foundup_id=r.foundup_id,
                    task_id=r.task_id,
                    proof_id=r.proof_id,
                    payout_id=r.payout_id,
                    timestamp=r.timestamp,
                )
                for r in rows
            ]

    # --- Distribution CRUD ---

    def create_distribution(self, post: DistributionPost) -> DistributionPost:
        """Create a new DistributionPost record."""
        with self.session() as sess:
            row = DistributionPostRow(
                distribution_id=post.distribution_id,
                foundup_id=post.foundup_id,
                task_id=post.task_id,
                channel=post.channel,
                content=post.content,
                actor_id=post.actor_id,
                dedupe_key=post.dedupe_key,
                external_ref=post.external_ref,
                published_at=post.published_at,
            )
            sess.add(row)
        logger.debug("Created DistributionPost: %s", post.distribution_id)
        return post

    def get_distribution(self, distribution_id: str) -> DistributionPost:
        """Get a DistributionPost by ID."""
        with self.session() as sess:
            row = sess.get(DistributionPostRow, distribution_id)
            if row is None:
                raise NotFoundError(f"DistributionPost not found: {distribution_id}")
            return DistributionPost(
                distribution_id=row.distribution_id,
                foundup_id=row.foundup_id,
                task_id=row.task_id,
                channel=row.channel,
                content=row.content,
                actor_id=row.actor_id,
                dedupe_key=row.dedupe_key,
                external_ref=row.external_ref,
                published_at=row.published_at,
            )

    def get_distribution_by_task(self, task_id: str) -> Optional[DistributionPost]:
        """Get DistributionPost by task_id."""
        with self.session() as sess:
            row = sess.query(DistributionPostRow).filter(DistributionPostRow.task_id == task_id).first()
            if row is None:
                return None
            return DistributionPost(
                distribution_id=row.distribution_id,
                foundup_id=row.foundup_id,
                task_id=row.task_id,
                channel=row.channel,
                content=row.content,
                actor_id=row.actor_id,
                dedupe_key=row.dedupe_key,
                external_ref=row.external_ref,
                published_at=row.published_at,
            )

    # --- AgentProfile CRUD ---

    def create_agent_profile(self, foundup_id: str, profile: AgentProfile) -> AgentProfile:
        """Create a new AgentProfile record."""
        with self.session() as sess:
            row = AgentProfileRow(
                agent_id=profile.agent_id,
                foundup_id=foundup_id,
                display_name=profile.display_name,
                capability_tags=profile.capability_tags,
                role=profile.role,
                joined_at=profile.joined_at,
            )
            sess.add(row)
        logger.debug("Created AgentProfile: %s", profile.agent_id)
        return profile

    def get_agent_profile(self, agent_id: str) -> AgentProfile:
        """Get an AgentProfile by ID."""
        with self.session() as sess:
            row = sess.get(AgentProfileRow, agent_id)
            if row is None:
                raise NotFoundError(f"AgentProfile not found: {agent_id}")
            return AgentProfile(
                agent_id=row.agent_id,
                display_name=row.display_name,
                capability_tags=list(row.capability_tags),
                role=row.role,
                joined_at=row.joined_at,
            )

    def list_agents(self, foundup_id: str) -> List[AgentProfile]:
        """List AgentProfiles for a Foundup."""
        with self.session() as sess:
            rows = sess.query(AgentProfileRow).filter(AgentProfileRow.foundup_id == foundup_id).all()
            return [
                AgentProfile(
                    agent_id=r.agent_id,
                    display_name=r.display_name,
                    capability_tags=list(r.capability_tags),
                    role=r.role,
                    joined_at=r.joined_at,
                )
                for r in rows
            ]

    # --- TokenTerms CRUD ---

    def save_token_terms(self, foundup_id: str, terms: TokenTerms) -> TokenTerms:
        """Save TokenTerms for a Foundup."""
        with self.session() as sess:
            # Check if exists
            existing = sess.query(TokenTermsRow).filter(TokenTermsRow.foundup_id == foundup_id).first()
            if existing:
                existing.token_name = terms.token_name
                existing.token_symbol = terms.token_symbol
                existing.max_supply = terms.max_supply
                existing.treasury_account = terms.treasury_account
                existing.vesting_policy = terms.vesting_policy
                existing.chain_hint = terms.chain_hint
            else:
                row = TokenTermsRow(
                    foundup_id=foundup_id,
                    token_name=terms.token_name,
                    token_symbol=terms.token_symbol,
                    max_supply=terms.max_supply,
                    treasury_account=terms.treasury_account,
                    vesting_policy=terms.vesting_policy,
                    chain_hint=terms.chain_hint,
                )
                sess.add(row)
        logger.debug("Saved TokenTerms for: %s", foundup_id)
        return terms

    def get_token_terms(self, foundup_id: str) -> Optional[TokenTerms]:
        """Get TokenTerms for a Foundup."""
        with self.session() as sess:
            row = sess.query(TokenTermsRow).filter(TokenTermsRow.foundup_id == foundup_id).first()
            if row is None:
                return None
            return TokenTerms(
                token_name=row.token_name,
                token_symbol=row.token_symbol,
                max_supply=row.max_supply,
                treasury_account=row.treasury_account,
                vesting_policy=dict(row.vesting_policy),
                chain_hint=row.chain_hint,
            )

    # --- Compute Access (Tranche 5) ---

    def _now_utc(self) -> datetime:
        return datetime.now(timezone.utc)

    def _next_id(self, prefix: str) -> str:
        from uuid import uuid4

        return f"{prefix}_{uuid4().hex[:12]}"

    def _ensure_wallet_row(self, sess: Session, actor_id: str) -> ComputeWalletRow:
        row = sess.get(ComputeWalletRow, actor_id)
        if row is None:
            row = ComputeWalletRow(
                actor_id=actor_id,
                wallet_id=self._next_id("wallet"),
                credit_balance=self.compute_default_credits,
                reserved_credits=0,
                updated_at=self._now_utc(),
            )
            sess.add(row)
        return row

    def activate_compute_plan(
        self,
        actor_id: str,
        tier: str = "builder",
        monthly_credit_allocation: int = 0,
    ) -> Dict[str, object]:
        """Create or update compute plan for actor."""
        if tier not in {"scout", "builder", "swarm", "sovereign"}:
            raise ValidationError(f"unsupported tier '{tier}'")
        allocation = max(0, int(monthly_credit_allocation))
        now = self._now_utc()
        with self.session() as sess:
            plan = sess.get(ComputePlanRow, actor_id)
            if plan is None:
                plan = ComputePlanRow(
                    actor_id=actor_id,
                    plan_id=self._next_id("plan"),
                    tier=tier,
                    status="active",
                    monthly_credit_allocation=allocation,
                    created_at=now,
                    updated_at=now,
                )
                sess.add(plan)
            else:
                plan.tier = tier
                plan.status = "active"
                plan.monthly_credit_allocation = allocation
                plan.updated_at = now

            wallet = self._ensure_wallet_row(sess, actor_id)
            if allocation > 0:
                wallet.credit_balance += allocation
            wallet.updated_at = now

        return {
            "plan_id": plan.plan_id,
            "actor_id": actor_id,
            "tier": tier,
            "status": "active",
            "monthly_credit_allocation": allocation,
        }

    def get_wallet(self, actor_id: str) -> Dict[str, object]:
        """Get or initialize compute wallet for actor."""
        with self.session() as sess:
            wallet = self._ensure_wallet_row(sess, actor_id)
            plan = sess.get(ComputePlanRow, actor_id)
            return {
                "actor_id": actor_id,
                "wallet_id": wallet.wallet_id,
                "credit_balance": int(wallet.credit_balance),
                "reserved_credits": int(wallet.reserved_credits),
                "tier": plan.tier if plan else "scout",
                "plan_status": plan.status if plan else "none",
            }

    def ensure_access(
        self,
        actor_id: str,
        capability: str,
        foundup_id: Optional[str] = None,
    ) -> Dict[str, object]:
        """Return allow/deny decision for capability execution."""
        with self.session() as sess:
            return _compute_decision(self, sess, actor_id, capability, foundup_id)

    def purchase_credits(
        self,
        actor_id: str,
        amount: int,
        rail: str,
        payment_ref: str,
    ) -> Dict[str, object]:
        """Credit wallet via subscription/top-up rail."""
        if amount <= 0:
            raise ValidationError("amount must be positive")
        if not rail:
            raise ValidationError("rail is required")
        if not payment_ref:
            raise ValidationError("payment_ref is required")

        now = self._now_utc()
        with self.session() as sess:
            wallet = self._ensure_wallet_row(sess, actor_id)
            wallet.credit_balance += int(amount)
            wallet.updated_at = now
            entry = ComputeLedgerEntryRow(
                entry_id=self._next_id("cc"),
                actor_id=actor_id,
                foundup_id=None,
                entry_type="purchase",
                amount=int(amount),
                rail=rail,
                reason="purchase_credits",
                payment_ref=payment_ref,
                event_id=None,
                created_at=now,
            )
            sess.add(entry)
            return {
                "entry_id": entry.entry_id,
                "actor_id": actor_id,
                "entry_type": entry.entry_type,
                "amount": int(entry.amount),
                "rail": entry.rail,
                "reason": entry.reason,
                "payment_ref": entry.payment_ref,
                "credit_balance": int(wallet.credit_balance),
            }

    def debit_credits(
        self,
        actor_id: str,
        amount: int,
        reason: str,
        foundup_id: Optional[str] = None,
    ) -> Dict[str, object]:
        """Debit wallet for metered execution."""
        if amount <= 0:
            raise ValidationError("amount must be positive")
        if not reason:
            raise ValidationError("reason is required")

        with self.session() as sess:
            return _debit_in_session(self, sess, actor_id, amount, reason, foundup_id)

    def rebate_credits(self, actor_id: str, amount: int, reason: str) -> Dict[str, object]:
        """Rebate credits into wallet."""
        if amount <= 0:
            raise ValidationError("amount must be positive")
        if not reason:
            raise ValidationError("reason is required")

        now = self._now_utc()
        with self.session() as sess:
            wallet = self._ensure_wallet_row(sess, actor_id)
            wallet.credit_balance += int(amount)
            wallet.updated_at = now
            entry = ComputeLedgerEntryRow(
                entry_id=self._next_id("cc"),
                actor_id=actor_id,
                foundup_id=None,
                entry_type="rebate",
                amount=int(amount),
                rail="rebate",
                reason=reason,
                payment_ref=None,
                event_id=None,
                created_at=now,
            )
            sess.add(entry)
            return {
                "entry_id": entry.entry_id,
                "actor_id": actor_id,
                "entry_type": entry.entry_type,
                "amount": int(entry.amount),
                "reason": entry.reason,
                "credit_balance": int(wallet.credit_balance),
            }

    def record_compute_session(
        self,
        actor_id: str,
        foundup_id: str,
        workload: Dict[str, object],
        credits_debited: int = 0,
        proof_id: Optional[str] = None,
    ) -> str:
        """Persist metered compute session metadata."""
        if not foundup_id:
            raise ValidationError("foundup_id is required")
        if not isinstance(workload, dict):
            raise ValidationError("workload must be a dict")
        if credits_debited < 0:
            raise ValidationError("credits_debited must be non-negative")

        session_id = self._next_id("ccsess")
        with self.session() as sess:
            sess.add(
                ComputeSessionRow(
                    session_id=session_id,
                    actor_id=actor_id,
                    foundup_id=foundup_id,
                    workload=dict(workload),
                    credits_debited=int(credits_debited),
                    proof_id=proof_id,
                    created_at=self._now_utc(),
                )
            )
        return session_id

    def get_compute_session(self, session_id: str) -> Dict[str, object]:
        """Get compute session by ID."""
        with self.session() as sess:
            row = sess.get(ComputeSessionRow, session_id)
            if row is None:
                raise NotFoundError(f"ComputeSession not found: {session_id}")
            return {
                "session_id": row.session_id,
                "actor_id": row.actor_id,
                "foundup_id": row.foundup_id,
                "workload": dict(row.workload),
                "credits_debited": int(row.credits_debited),
                "proof_id": row.proof_id,
                "created_at": row.created_at,
            }

    def list_compute_ledger(self, actor_id: str, limit: int = 100) -> List[Dict[str, object]]:
        """List compute ledger entries for actor ordered newest first."""
        with self.session() as sess:
            rows = (
                sess.query(ComputeLedgerEntryRow)
                .filter(ComputeLedgerEntryRow.actor_id == actor_id)
                .order_by(ComputeLedgerEntryRow.created_at.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "entry_id": row.entry_id,
                    "actor_id": row.actor_id,
                    "foundup_id": row.foundup_id,
                    "entry_type": row.entry_type,
                    "amount": int(row.amount),
                    "rail": row.rail,
                    "reason": row.reason,
                    "payment_ref": row.payment_ref,
                    "event_id": row.event_id,
                    "created_at": row.created_at,
                }
                for row in rows
            ]
