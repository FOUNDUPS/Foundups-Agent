#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FoundUp Genesis Envelope — Typed schema for FoundUp ideation intake.

This is the first artifact created when 012 requests a new FoundUp.
It captures intent, acceptance criteria, and truth state BEFORE any
implementation or scaffold is created.

WSP Compliance:
    WSP 97: Implementation Truth — truth_state_map uses markers
    WSP 104: Namespace Protocol — foundup_id format validation
    WSP 3: Module Organization — domain placement

Pattern Sources:
    - modules/ai_intelligence/ai_overseer/src/types.py (dataclass patterns)
    - modules/foundups/gotjunk/foundup_manifest.json (manifest fields)
    - modules/foundups/docs/PFMALL_FOUNDUP_MANIFEST_SCHEMA.md (schema spec)
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# -----------------------------------------------------------------------------
# Enums
# -----------------------------------------------------------------------------


class LifecycleStage(Enum):
    """
    Valid lifecycle stages for genesis envelope.

    At genesis, only IDEA or INCUBATING are valid.
    Other stages require evidence of implementation.
    """
    IDEA = "idea"
    INCUBATING = "incubating"
    # These are NOT valid at genesis — require implementation evidence
    # POC = "poc"
    # SOFT_PROTO = "soft-proto"
    # PROTO = "proto"
    # MVP = "mvp"
    # LAUNCH = "launch"


class BindingState(Enum):
    """
    pfMALL binding state for genesis envelope.

    At genesis, only UNBOUND or DISCOVERABLE_ONLY are valid.
    """
    UNBOUND = "unbound"
    DISCOVERABLE_ONLY = "discoverable_only"
    # NOT valid at genesis — requires working frontend
    # CONDITIONAL = "conditional"
    # READY = "ready"


class TruthMarker(Enum):
    """
    WSP 97 truth markers for feature state.

    Used in truth_state_map to distinguish claims from reality.
    """
    IDEA_ONLY = "IDEA_ONLY"                              # Concept described
    SPECIFIED = "SPECIFIED"                              # Spec written, no code
    SPECIFIED_NOT_IMPLEMENTED = "SPECIFIED_NOT_IMPLEMENTED"
    IMPLEMENTED = "IMPLEMENTED"                          # Code exists
    IMPLEMENTED_IN_TESTS = "IMPLEMENTED_IN_TESTS"        # Tests prove it works
    ARCHITECTURAL_CONTRACT = "ARCHITECTURAL_CONTRACT"    # Backend enforces
    PARTIAL = "PARTIAL"                                  # Some code exists
    FUTURE_PHASE = "FUTURE_PHASE"                        # Planned, not started


# -----------------------------------------------------------------------------
# Acceptance Criterion
# -----------------------------------------------------------------------------


@dataclass
class AcceptanceCriterion:
    """
    Single acceptance criterion with observable outcome.

    Every FoundUp must have testable acceptance criteria BEFORE
    implementation begins. This prevents "vibes-based" development.

    Attributes:
        observable: What can be observed when this criterion is met
        method: How to observe it (test, manual check, metric)
        oracle: What determines pass/fail (expected value, threshold)
        pass_condition: Concrete condition that must be true
    """
    observable: str
    method: str
    oracle: str
    pass_condition: str

    def to_dict(self) -> Dict[str, str]:
        return {
            "observable": self.observable,
            "method": self.method,
            "oracle": self.oracle,
            "pass_condition": self.pass_condition,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> AcceptanceCriterion:
        return cls(
            observable=data.get("observable", ""),
            method=data.get("method", ""),
            oracle=data.get("oracle", ""),
            pass_condition=data.get("pass_condition", ""),
        )


# -----------------------------------------------------------------------------
# Truth State Entry
# -----------------------------------------------------------------------------


@dataclass
class TruthStateEntry:
    """
    Single entry in the truth state map.

    Documents what is claimed vs what is implemented for each feature.
    """
    feature: str
    marker: TruthMarker
    evidence: str = ""

    def to_dict(self) -> Dict[str, str]:
        return {
            "feature": self.feature,
            "marker": self.marker.value,
            "evidence": self.evidence,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> TruthStateEntry:
        return cls(
            feature=data.get("feature", ""),
            marker=TruthMarker(data.get("marker", "IDEA_ONLY")),
            evidence=data.get("evidence", ""),
        )


# -----------------------------------------------------------------------------
# FoundUp Genesis Envelope
# -----------------------------------------------------------------------------


@dataclass
class FoundUpGenesisEnvelope:
    """
    Genesis envelope for a new FoundUp.

    This is created BEFORE any code, scaffold, or manifest exists.
    It captures the intent, acceptance criteria, and current truth state.

    Validators enforce:
        - foundup_id follows WSP 104 format (lowercase, underscores)
        - lifecycle_stage is IDEA or INCUBATING only
        - acceptance_criteria have all four fields
        - truth_state_map uses WSP 97 markers
        - external_repo_requested is False at genesis
        - binding_state is UNBOUND or DISCOVERABLE_ONLY

    Attributes:
        foundup_id: Unique identifier (lowercase alphanumeric + underscore)
        name: Human-readable name
        tagline: One-line description
        description: Full description of the FoundUp
        category: Domain category (marketplace, media, science, etc.)
        requested_by: Who requested this FoundUp (usually "012")
        lifecycle_stage: Current stage (IDEA or INCUBATING at genesis)
        acceptance_criteria: List of testable acceptance criteria
        truth_state_map: WSP 97 feature -> marker mapping
        external_repo_requested: Whether external repo is needed (False at genesis)
        binding_state: pfMALL binding state (UNBOUND or DISCOVERABLE_ONLY)
        holo_recall_results: HoloIndex search results for similar patterns
        prior_art: Links to existing similar FoundUps or modules
        created_at: Timestamp of envelope creation
        created_by: Who created the envelope (usually "0102")
        notes: Additional context or constraints
    """

    # Required at creation
    foundup_id: str
    name: str
    tagline: str
    description: str
    category: str
    requested_by: str = "012"

    # Lifecycle (constrained at genesis)
    lifecycle_stage: LifecycleStage = LifecycleStage.IDEA
    binding_state: BindingState = BindingState.UNBOUND
    external_repo_requested: bool = False

    # Acceptance criteria (required for validation)
    acceptance_criteria: List[AcceptanceCriterion] = field(default_factory=list)

    # Truth state map (WSP 97)
    truth_state_map: List[TruthStateEntry] = field(default_factory=list)

    # HoloIndex recall
    holo_recall_results: List[Dict[str, Any]] = field(default_factory=list)
    prior_art: List[str] = field(default_factory=list)

    # Metadata
    created_at: float = field(default_factory=time.time)
    created_by: str = "0102"
    notes: str = ""

    # Validation state (set by validator)
    is_valid: bool = False
    validation_errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize envelope to dict for JSON storage."""
        return {
            "foundup_id": self.foundup_id,
            "name": self.name,
            "tagline": self.tagline,
            "description": self.description,
            "category": self.category,
            "requested_by": self.requested_by,
            "lifecycle_stage": self.lifecycle_stage.value,
            "binding_state": self.binding_state.value,
            "external_repo_requested": self.external_repo_requested,
            "acceptance_criteria": [ac.to_dict() for ac in self.acceptance_criteria],
            "truth_state_map": [ts.to_dict() for ts in self.truth_state_map],
            "holo_recall_results": self.holo_recall_results,
            "prior_art": self.prior_art,
            "created_at": self.created_at,
            "created_by": self.created_by,
            "notes": self.notes,
            "is_valid": self.is_valid,
            "validation_errors": self.validation_errors,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> FoundUpGenesisEnvelope:
        """Deserialize envelope from dict."""
        return cls(
            foundup_id=data.get("foundup_id", ""),
            name=data.get("name", ""),
            tagline=data.get("tagline", ""),
            description=data.get("description", ""),
            category=data.get("category", ""),
            requested_by=data.get("requested_by", "012"),
            lifecycle_stage=LifecycleStage(data.get("lifecycle_stage", "idea")),
            binding_state=BindingState(data.get("binding_state", "unbound")),
            external_repo_requested=data.get("external_repo_requested", False),
            acceptance_criteria=[
                AcceptanceCriterion.from_dict(ac)
                for ac in data.get("acceptance_criteria", [])
            ],
            truth_state_map=[
                TruthStateEntry.from_dict(ts)
                for ts in data.get("truth_state_map", [])
            ],
            holo_recall_results=data.get("holo_recall_results", []),
            prior_art=data.get("prior_art", []),
            created_at=data.get("created_at", time.time()),
            created_by=data.get("created_by", "0102"),
            notes=data.get("notes", ""),
            is_valid=data.get("is_valid", False),
            validation_errors=data.get("validation_errors", []),
        )


# -----------------------------------------------------------------------------
# ID Format Validation (WSP 104)
# -----------------------------------------------------------------------------


# Pattern: lowercase letters, digits, underscores. 3-50 chars. Must start with letter.
FOUNDUP_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]{2,49}$")


def is_valid_foundup_id(foundup_id: str) -> bool:
    """
    Validate foundup_id format per WSP 104.

    Rules:
        - 3-50 characters
        - Lowercase letters, digits, underscores only
        - Must start with a letter
        - Examples: gotjunk_001, kosei, science_swarm_hub
    """
    if not foundup_id:
        return False
    return bool(FOUNDUP_ID_PATTERN.match(foundup_id))
