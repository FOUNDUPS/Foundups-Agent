"""Shared SQLAlchemy mappings for the existing FoundUps Agent Market persistence layer.

SQLite and PostgreSQL retain one declarative registry through compatibility
exports in sqlite_adapter. Domain dataclasses remain in the parent models module.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import JSON, Boolean, DateTime, Enum, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from ..models import PayoutStatus, TaskStatus


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""

    pass


# ORM Models mirroring dataclasses from models.py


class FoundupRow(Base):
    """ORM model for Foundup."""

    __tablename__ = "foundups"

    foundup_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    owner_id: Mapped[str] = mapped_column(String(64), nullable=False)
    token_symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    immutable_metadata: Mapped[Dict[str, str]] = mapped_column(JSON, default=dict)
    mutable_metadata: Mapped[Dict[str, str]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class TokenTermsRow(Base):
    """ORM model for TokenTerms."""

    __tablename__ = "token_terms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    foundup_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    token_name: Mapped[str] = mapped_column(String(256), nullable=False)
    token_symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    max_supply: Mapped[int] = mapped_column(Integer, nullable=False)
    treasury_account: Mapped[str] = mapped_column(String(128), nullable=False)
    vesting_policy: Mapped[Dict[str, str]] = mapped_column(JSON, default=dict)
    chain_hint: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)


class AgentProfileRow(Base):
    """ORM model for AgentProfile."""

    __tablename__ = "agent_profiles"

    agent_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    foundup_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(256), nullable=False)
    capability_tags: Mapped[List[str]] = mapped_column(JSON, default=list)
    role: Mapped[str] = mapped_column(String(64), nullable=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class TaskRow(Base):
    """ORM model for Task."""

    __tablename__ = "tasks"
    __table_args__ = (
        Index("idx_tasks_foundup_status", "foundup_id", "status"),
    )

    task_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    foundup_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    acceptance_criteria: Mapped[List[str]] = mapped_column(JSON, default=list)
    reward_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    creator_id: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), default=TaskStatus.OPEN)
    assignee_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    proof_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    verification_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    payout_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ProofRow(Base):
    """ORM model for Proof."""

    __tablename__ = "proofs"
    __table_args__ = (
        Index("idx_proofs_task_submitted_at", "task_id", "submitted_at"),
    )

    proof_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    submitter_id: Mapped[str] = mapped_column(String(64), nullable=False)
    artifact_uri: Mapped[str] = mapped_column(String(1024), nullable=False)
    artifact_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="")
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class VerificationRow(Base):
    """ORM model for Verification."""

    __tablename__ = "verifications"

    verification_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    verifier_id: Mapped[str] = mapped_column(String(64), nullable=False)
    approved: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PayoutRow(Base):
    """ORM model for Payout."""

    __tablename__ = "payouts"
    __table_args__ = (
        Index("idx_payouts_task_status", "task_id", "status"),
    )

    payout_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    recipient_id: Mapped[str] = mapped_column(String(64), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[PayoutStatus] = mapped_column(Enum(PayoutStatus), default=PayoutStatus.INITIATED)
    reference: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class DistributionPostRow(Base):
    """ORM model for DistributionPost."""

    __tablename__ = "distribution_posts"
    __table_args__ = (
        Index("idx_distribution_foundup_published", "foundup_id", "published_at"),
    )

    distribution_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    foundup_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    task_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(64), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    actor_id: Mapped[str] = mapped_column(String(64), nullable=False)
    dedupe_key: Mapped[str] = mapped_column(String(256), nullable=False, unique=True)
    external_ref: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EventRecordRow(Base):
    """ORM model for EventRecord."""

    __tablename__ = "event_records"
    __table_args__ = (
        Index("idx_events_foundup_timestamp", "foundup_id", "timestamp"),
    )

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    actor_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    payload: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    foundup_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    task_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    proof_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    payout_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)


class ComputePlanRow(Base):
    """ORM model for compute access plans."""

    __tablename__ = "compute_plans"

    actor_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    plan_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    tier: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    monthly_credit_allocation: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ComputeWalletRow(Base):
    """ORM model for compute credit wallets."""

    __tablename__ = "compute_wallets"

    actor_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    wallet_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    credit_balance: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reserved_credits: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ComputeLedgerEntryRow(Base):
    """ORM model for compute credit ledger entries."""

    __tablename__ = "compute_ledger_entries"
    __table_args__ = (
        Index("idx_compute_ledger_actor_created", "actor_id", "created_at"),
        Index("idx_compute_ledger_foundup_created", "foundup_id", "created_at"),
    )

    entry_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    actor_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    foundup_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    entry_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    rail: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    reason: Mapped[str] = mapped_column(String(256), nullable=False)
    payment_ref: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    event_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)


class ComputeSessionRow(Base):
    """ORM model for metered compute sessions."""

    __tablename__ = "compute_sessions"
    __table_args__ = (
        Index("idx_compute_sessions_foundup_created", "foundup_id", "created_at"),
    )

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    actor_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    foundup_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    workload: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    credits_debited: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    proof_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
