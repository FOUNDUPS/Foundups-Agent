#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PQN Swarm Hub FoundUp - Public API

Exports PoC contracts for the PQN work registry, submission sink,
verification, and contribution measurement.

Usage:
    from modules.foundups.pqn_swarm_hub import (
        PQNWorkUnit,
        rESPSubmission,
        VerificationDecision,
        ContributionRecord,
        WorkUnitStatus,
        SubmissionStatus,
    )
"""

from .contracts import (
    ContributionRecord,
    PQNWorkUnit,
    rESPSubmission,
    SubmissionStatus,
    VerificationDecision,
    WorkUnitStatus,
    generate_id,
    utc_now,
)
from .contribution import ContributionReporter
from .registry import (
    InvalidStatusTransitionError,
    WorkUnitNotFoundError,
    WorkUnitRegistry,
)
from .submission_sink import DuplicateSubmissionError, SubmissionSink
from .verification import VerificationEngine
from .detector_bridge import DetectorBridge
from .gate import (
    GateDecision,
    ParticipantGate,
    ParticipantIdentity,
    ParticipantStatus,
    ParticipantTier,
)
from .fam_adapter import FAMAdapter, FAMAdapterError, get_fam_adapter
from .persistence import SQLiteStore, get_sqlite_store, reset_sqlite_store
from .publication_adapter import (
    PublicationAdapter,
    PublicationAdapterError,
    PublicationResult,
    get_publication_adapter,
    reset_publication_adapter,
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
    # Publication Adapter (Phase 1)
    "PublicationAdapter",
    "PublicationAdapterError",
    "PublicationResult",
    "get_publication_adapter",
    "reset_publication_adapter",
    # Errors
    "WorkUnitNotFoundError",
    "InvalidStatusTransitionError",
    "DuplicateSubmissionError",
]
