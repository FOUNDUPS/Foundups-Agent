"""Kosei AI Systems — Service contracts.

Defines the data structures for Kosei's service boundaries.
These contracts are the interface between Kosei and its consumers.

Boundary rule: AutoPost is an external dependency consumed as a service.
Kosei does not embed AutoPost internals. AutoPost does not depend on Kosei.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


class AuditStatus(Enum):
    """Status of a content audit."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    EXPIRED = "expired"


class TrialStatus(Enum):
    """Status of a client trial."""
    ACTIVE = "active"
    EXPIRED = "expired"
    CONVERTED = "converted"
    CANCELLED = "cancelled"


class ServiceTier(Enum):
    """Client service tier."""
    TRIAL = "trial"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


# --- Audit Funnel ---

@dataclass
class AuditRequest:
    """Input to the audit funnel."""
    lead_source: str
    content_urls: List[str] = field(default_factory=list)
    platform_handles: Dict[str, str] = field(default_factory=dict)
    contact_email: Optional[str] = None


@dataclass
class AuditReport:
    """Output of the audit funnel."""
    request: AuditRequest
    gaps: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    status: AuditStatus = AuditStatus.PENDING
    created_at: Optional[datetime] = None


# --- Onboarding ---

@dataclass
class OnboardingRequest:
    """Input to onboarding flow."""
    audit_report: AuditReport
    client_name: str
    branding: Dict[str, str] = field(default_factory=dict)
    preferences: Dict[str, str] = field(default_factory=dict)


@dataclass
class ClientWorkspace:
    """Provisioned client workspace."""
    workspace_id: str
    client_name: str
    tier: ServiceTier = ServiceTier.TRIAL
    integrations: List[str] = field(default_factory=list)
    created_at: Optional[datetime] = None


# --- Service Orchestration ---

@dataclass
class ServiceRequest:
    """A client request routed through Kosei."""
    workspace_id: str
    intent: str
    payload: Dict = field(default_factory=dict)


@dataclass
class TaskRouting:
    """Routing decision for a service request."""
    request: ServiceRequest
    target_service: str
    routed_at: Optional[datetime] = None
    notes: str = ""


# --- Trial Management ---

@dataclass
class TrialState:
    """Current state of a client trial."""
    workspace_id: str
    status: TrialStatus = TrialStatus.ACTIVE
    days_remaining: int = 14
    usage_count: int = 0


@dataclass
class TrialDecision:
    """Decision output from trial evaluation."""
    trial: TrialState
    action: str = "continue"  # continue | prompt_conversion | expire
    message: str = ""


# --- White-Label Config ---

@dataclass
class WhiteLabelConfig:
    """Per-client branding and feature config."""
    workspace_id: str
    brand_name: str = ""
    logo_url: str = ""
    primary_color: str = "#000000"
    domain: str = ""
    feature_flags: Dict[str, bool] = field(default_factory=dict)


# --- External Dependency Declaration ---

EXTERNAL_DEPENDENCIES = {
    "autopost": {
        "relationship": "consumed_as_service",
        "location": "external_repo",
        "note": "Content creation engine. Kosei routes client requests to AutoPost "
                "but does not contain AutoPost source code.",
    },
}
