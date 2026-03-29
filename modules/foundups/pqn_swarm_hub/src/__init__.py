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
    # Services
    "WorkUnitRegistry",
    "SubmissionSink",
    "VerificationEngine",
    "ContributionReporter",
    "DetectorBridge",
    # Errors
    "WorkUnitNotFoundError",
    "InvalidStatusTransitionError",
    "DuplicateSubmissionError",
]
