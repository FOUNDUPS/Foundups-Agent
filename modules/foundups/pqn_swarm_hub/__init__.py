#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PQN Swarm Hub FoundUp

A FoundUp that coordinates bounded PQN work units, rESP submissions,
verification decisions, and ROC-style contribution measurement.

Usage:
    from modules.foundups.pqn_swarm_hub import (
        PQNWorkUnit,
        rESPSubmission,
        VerificationDecision,
        ContributionRecord,
    )
"""

from .src import (
    # Contracts
    ContributionRecord,
    PQNWorkUnit,
    rESPSubmission,
    SubmissionStatus,
    VerificationDecision,
    WorkUnitStatus,
    generate_id,
    utc_now,
    # Gate (Phase 1)
    ParticipantIdentity,
    ParticipantStatus,
    ParticipantTier,
    GateDecision,
    ParticipantGate,
    # Services
    WorkUnitRegistry,
    SubmissionSink,
    VerificationEngine,
    ContributionReporter,
    DetectorBridge,
    # FAM Adapter (Phase 1)
    FAMAdapter,
    FAMAdapterError,
    get_fam_adapter,
    # Persistence (Phase 1)
    SQLiteStore,
    get_sqlite_store,
    reset_sqlite_store,
    # Errors
    WorkUnitNotFoundError,
    InvalidStatusTransitionError,
    DuplicateSubmissionError,
)

__all__ = [
    # Contracts
    "PQNWorkUnit",
    "rESPSubmission",
    "VerificationDecision",
    "ContributionRecord",
    "WorkUnitStatus",
    "SubmissionStatus",
    "generate_id",
    "utc_now",
    # Gate (Phase 1)
    "ParticipantIdentity",
    "ParticipantStatus",
    "ParticipantTier",
    "GateDecision",
    "ParticipantGate",
    # Services
    "WorkUnitRegistry",
    "SubmissionSink",
    "VerificationEngine",
    "ContributionReporter",
    "DetectorBridge",
    # FAM Adapter (Phase 1)
    "FAMAdapter",
    "FAMAdapterError",
    "get_fam_adapter",
    # Persistence (Phase 1)
    "SQLiteStore",
    "get_sqlite_store",
    "reset_sqlite_store",
    # Errors
    "WorkUnitNotFoundError",
    "InvalidStatusTransitionError",
    "DuplicateSubmissionError",
]
