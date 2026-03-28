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
    # Services
    WorkUnitRegistry,
    SubmissionSink,
    VerificationEngine,
    ContributionReporter,
    # Errors
    WorkUnitNotFoundError,
    InvalidStatusTransitionError,
    DuplicateSubmissionError,
)

__all__ = [
    "PQNWorkUnit",
    "rESPSubmission",
    "VerificationDecision",
    "ContributionRecord",
    "WorkUnitStatus",
    "SubmissionStatus",
    "generate_id",
    "utc_now",
    "WorkUnitRegistry",
    "SubmissionSink",
    "VerificationEngine",
    "ContributionReporter",
    "WorkUnitNotFoundError",
    "InvalidStatusTransitionError",
    "DuplicateSubmissionError",
]
