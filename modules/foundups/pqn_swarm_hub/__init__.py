#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PQN Swarm Hub - Monorepo Stub

This module has been exfoliated to standalone repositories:
- Origin: https://github.com/FOUNDUPS/science-swarm-hub
- Backup: https://github.com/Foundup/science-swarm-hub

Install with: pip install science-swarm-hub

For local development, this stub re-exports from the installed package.

Stub cutover: 2026-03-30
"""

try:
    from pqn_swarm_hub import (
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
        # Publication Adapter (Phase 1)
        PublicationAdapter,
        PublicationAdapterError,
        PublicationResult,
        get_publication_adapter,
        reset_publication_adapter,
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

except ImportError as e:
    raise ImportError(
        "pqn_swarm_hub has been externalized to standalone repositories.\n\n"
        "Install with: pip install science-swarm-hub\n\n"
        "Repositories:\n"
        "  - Origin: https://github.com/FOUNDUPS/science-swarm-hub\n"
        "  - Backup: https://github.com/Foundup/science-swarm-hub\n\n"
        f"Original error: {e}"
    ) from e
