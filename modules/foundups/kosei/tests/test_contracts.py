"""Tests for Kosei AI Systems contracts.

Validates that contract dataclasses are structurally correct
and that the Kosei/AutoPost boundary is explicitly declared.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from modules.foundups.kosei.src.contracts import (
    AuditRequest,
    AuditReport,
    AuditStatus,
    ClientWorkspace,
    EXTERNAL_DEPENDENCIES,
    OnboardingRequest,
    ServiceRequest,
    ServiceTier,
    TaskRouting,
    TrialDecision,
    TrialState,
    TrialStatus,
    WhiteLabelConfig,
)

MODULE_ROOT = Path(__file__).parent.parent


class TestContractStructure:
    """Contracts instantiate with defaults and required fields."""

    def test_audit_request(self):
        req = AuditRequest(lead_source="web_form")
        assert req.lead_source == "web_form"
        assert req.content_urls == []
        assert req.platform_handles == {}

    def test_audit_report(self):
        req = AuditRequest(lead_source="referral")
        report = AuditReport(request=req)
        assert report.status == AuditStatus.PENDING
        assert report.gaps == []
        assert report.recommendations == []

    def test_onboarding_request(self):
        req = AuditRequest(lead_source="pfmall")
        report = AuditReport(request=req, status=AuditStatus.COMPLETE)
        onboard = OnboardingRequest(audit_report=report, client_name="Test Client")
        assert onboard.client_name == "Test Client"
        assert onboard.branding == {}

    def test_client_workspace(self):
        ws = ClientWorkspace(workspace_id="ws_001", client_name="Acme Corp")
        assert ws.tier == ServiceTier.TRIAL
        assert ws.integrations == []

    def test_service_request(self):
        req = ServiceRequest(workspace_id="ws_001", intent="schedule_post")
        assert req.payload == {}

    def test_task_routing(self):
        req = ServiceRequest(workspace_id="ws_001", intent="create_video")
        routing = TaskRouting(request=req, target_service="autopost")
        assert routing.target_service == "autopost"

    def test_trial_state(self):
        trial = TrialState(workspace_id="ws_001")
        assert trial.status == TrialStatus.ACTIVE
        assert trial.days_remaining == 14

    def test_trial_decision(self):
        trial = TrialState(workspace_id="ws_001", days_remaining=0)
        decision = TrialDecision(trial=trial, action="expire")
        assert decision.action == "expire"

    def test_whitelabel_config(self):
        wl = WhiteLabelConfig(workspace_id="ws_001", brand_name="ClientCo")
        assert wl.brand_name == "ClientCo"
        assert wl.feature_flags == {}


class TestBoundaryDeclaration:
    """AutoPost boundary must be explicitly declared."""

    def test_autopost_is_external_dependency(self):
        assert "autopost" in EXTERNAL_DEPENDENCIES

    def test_autopost_relationship_is_service(self):
        assert EXTERNAL_DEPENDENCIES["autopost"]["relationship"] == "consumed_as_service"

    def test_autopost_is_external_repo(self):
        assert EXTERNAL_DEPENDENCIES["autopost"]["location"] == "external_repo"


class TestModuleScaffold:
    """Module scaffold files exist per WSP 49."""

    REQUIRED_FILES = [
        "README.md",
        "INTERFACE.md",
        "ROADMAP.md",
        "ModLog.md",
        "module.json",
        "src/contracts.py",
    ]

    def test_required_files_exist(self):
        for filename in self.REQUIRED_FILES:
            path = MODULE_ROOT / filename
            assert path.exists(), f"Missing required file: {filename}"

    def test_module_json_valid(self):
        module_json = MODULE_ROOT / "module.json"
        data = json.loads(module_json.read_text(encoding="utf-8"))
        assert data["name"] == "kosei"
        assert data["type"] == "foundup"
        assert data["domain"] == "foundups"

    def test_module_json_declares_autopost_boundary(self):
        module_json = MODULE_ROOT / "module.json"
        data = json.loads(module_json.read_text(encoding="utf-8"))
        assert "autopost" in data.get("external_dependencies", {})
        assert data["external_dependencies"]["autopost"]["relationship"] == "consumed_as_service"

    def test_boundary_lists_are_non_empty(self):
        module_json = MODULE_ROOT / "module.json"
        data = json.loads(module_json.read_text(encoding="utf-8"))
        boundary = data.get("boundary", {})
        assert len(boundary.get("kosei_owns", [])) > 0
        assert len(boundary.get("kosei_does_not_own", [])) > 0

    def test_kosei_does_not_own_content_engine(self):
        module_json = MODULE_ROOT / "module.json"
        data = json.loads(module_json.read_text(encoding="utf-8"))
        not_owned = data["boundary"]["kosei_does_not_own"]
        assert "content_creation_engine" in not_owned
