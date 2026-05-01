"""Focused tests for OpenClaw IMPROVEMENT intent classification and routing.

Tests:
- IMPROVEMENT IntentCategory exists
- IMPROVEMENT keywords defined in INTENT_KEYWORDS
- IMPROVEMENT route defined in DOMAIN_ROUTES
- execute_improvement returns advisory (not execution claim)
- WSP 97 truth boundary: no repair capability claims

WSP 97 Truth Boundary:
  - These tests verify classification, NOT execution
  - These tests verify advisory messages, NOT repair actions
  - These tests verify truthful disclaimers exist
"""

from dataclasses import dataclass

import pytest


# ---------------------------------------------------------------------------
# Fixtures and Helpers
# ---------------------------------------------------------------------------


@dataclass
class MockIntent:
    """Mock OpenClawIntent for testing."""

    raw_message: str
    is_authorized_commander: bool = True
    extracted_task: str = ""
    sender: str = "test_sender"


class MockDAE:
    """Mock OpenClawDAE for testing."""

    pass


# ---------------------------------------------------------------------------
# Intent Classification Tests
# ---------------------------------------------------------------------------


class TestImprovementIntentClassification:
    """Test IMPROVEMENT IntentCategory classification."""

    def test_improvement_category_exists(self):
        """IMPROVEMENT IntentCategory is defined."""
        from modules.communication.moltbot_bridge.src.openclaw_dae import IntentCategory

        assert hasattr(IntentCategory, "IMPROVEMENT")
        assert IntentCategory.IMPROVEMENT.value == "improvement"

    def test_improvement_keywords_defined(self):
        """Improvement keywords are defined in INTENT_KEYWORDS."""
        from modules.communication.moltbot_bridge.src.openclaw_dae import (
            IntentCategory,
            OpenClawDAE,
        )

        keywords = OpenClawDAE.INTENT_KEYWORDS.get(IntentCategory.IMPROVEMENT, [])
        assert len(keywords) > 0
        assert "fix violation" in keywords
        assert "wsp violation" in keywords
        assert "repair module" in keywords
        assert "remediate" in keywords

    def test_improvement_route_defined(self):
        """Improvement route is defined in DOMAIN_ROUTES."""
        from modules.communication.moltbot_bridge.src.openclaw_dae import (
            IntentCategory,
            OpenClawDAE,
        )

        route = OpenClawDAE.DOMAIN_ROUTES.get(IntentCategory.IMPROVEMENT)
        assert route == "improvement_router"


# ---------------------------------------------------------------------------
# Improvement Route Tests
# ---------------------------------------------------------------------------


class TestImprovementRoute:
    """Test execute_improvement returns truthful advisory."""

    def test_improvement_returns_advisory(self):
        """execute_improvement returns advisory, not execution claim."""
        from modules.communication.moltbot_bridge.src.openclaw_execution_routes import (
            execute_improvement,
        )

        intent = MockIntent(
            raw_message="fix wsp violation in holo_index",
            extracted_task="fix wsp violation in holo_index",
        )
        result = execute_improvement(MockDAE(), intent)

        # Must acknowledge intent was recognized
        assert "Improvement Intent Recognized" in result
        assert "wsp_violation" in result

    def test_improvement_no_execution_claim(self):
        """WSP 97: execute_improvement must NOT claim repair was executed."""
        from modules.communication.moltbot_bridge.src.openclaw_execution_routes import (
            execute_improvement,
        )

        intent = MockIntent(
            raw_message="repair module agent_permissions",
            extracted_task="repair module agent_permissions",
        )
        result = execute_improvement(MockDAE(), intent)

        # Must NOT claim execution
        assert "not executed" in result.lower() or "not yet implemented" in result.lower()
        # Must acknowledge advisory status
        assert "WSP 97" in result

    def test_improvement_classifies_wsp_violation(self):
        """WSP violation keywords classify as wsp_violation type."""
        from modules.communication.moltbot_bridge.src.openclaw_execution_routes import (
            execute_improvement,
        )

        intent = MockIntent(
            raw_message="fix wsp violation wsp 49",
            extracted_task="fix wsp violation wsp 49",
        )
        result = execute_improvement(MockDAE(), intent)

        assert "wsp_violation" in result

    def test_improvement_classifies_module_repair(self):
        """Module repair keywords classify as module_repair type."""
        from modules.communication.moltbot_bridge.src.openclaw_execution_routes import (
            execute_improvement,
        )

        intent = MockIntent(
            raw_message="repair module wre_core",
            extracted_task="repair module wre_core",
        )
        result = execute_improvement(MockDAE(), intent)

        assert "module_repair" in result

    def test_improvement_classifies_test_hygiene(self):
        """Test hygiene keywords classify as test_hygiene type."""
        from modules.communication.moltbot_bridge.src.openclaw_execution_routes import (
            execute_improvement,
        )

        intent = MockIntent(
            raw_message="fix stale test in ai_overseer",
            extracted_task="fix stale test in ai_overseer",
        )
        result = execute_improvement(MockDAE(), intent)

        assert "test_hygiene" in result

    def test_improvement_classifies_drift_correction(self):
        """Drift keywords classify as drift_correction type."""
        from modules.communication.moltbot_bridge.src.openclaw_execution_routes import (
            execute_improvement,
        )

        intent = MockIntent(
            raw_message="fix drift in navigation module",
            extracted_task="fix drift in navigation module",
        )
        result = execute_improvement(MockDAE(), intent)

        assert "drift_correction" in result

    def test_improvement_classifies_fmas_scan(self):
        """FMAS keywords classify as fmas_scan type."""
        from modules.communication.moltbot_bridge.src.openclaw_execution_routes import (
            execute_improvement,
        )

        intent = MockIntent(
            raw_message="run fmas repair on communication",
            extracted_task="run fmas repair on communication",
        )
        result = execute_improvement(MockDAE(), intent)

        assert "fmas_scan" in result


# ---------------------------------------------------------------------------
# Intent Planner Tests
# ---------------------------------------------------------------------------


class TestImprovementPlanExecution:
    """Test IMPROVEMENT category in plan_execution."""

    def test_improvement_plan_has_stub_steps(self):
        """IMPROVEMENT plan includes improvement_route_stub action."""
        from dataclasses import dataclass, field
        from typing import List, Dict, Any

        from modules.communication.moltbot_bridge.src.openclaw_intent_planner import (
            plan_execution,
        )
        from modules.communication.moltbot_bridge.src.openclaw_dae import (
            IntentCategory,
            AutonomyTier,
        )

        # Create ExecutionPlan dataclass mimic
        @dataclass
        class ExecutionPlan:
            intent: Any
            route: str
            permission_level: Any
            wsp_preflight_passed: bool
            steps: List[Dict[str, Any]] = field(default_factory=list)
            estimated_tokens: int = 0

        # Create minimal mock DAE with required attributes
        mock_dae = type(
            "MockDAE",
            (),
            {
                "IntentCategory": IntentCategory,
                "ExecutionPlan": ExecutionPlan,
            },
        )()

        # Create minimal mock intent
        mock_intent = type(
            "MockIntent",
            (),
            {
                "category": IntentCategory.IMPROVEMENT,
                "extracted_task": "fix wsp violation",
                "raw_message": "fix wsp violation",
                "target_domain": "improvement_router",
            },
        )()

        plan = plan_execution(mock_dae, mock_intent, AutonomyTier.ADVISORY)

        # Plan should have improvement steps
        step_actions = [s.get("action") for s in plan.steps]
        assert "improvement_classify" in step_actions
        assert "improvement_route_stub" in step_actions


# ---------------------------------------------------------------------------
# ImprovementJob Creation Tests (OC_IMP3)
# ---------------------------------------------------------------------------


class TestImprovementJobCreation:
    """Test that execute_improvement creates ImprovementJob."""

    def setup_method(self):
        """Clear inspection hook before each test."""
        from modules.communication.moltbot_bridge.src.openclaw_execution_routes import (
            clear_improvement_job_hook,
        )
        clear_improvement_job_hook()

    def test_improvement_creates_job(self):
        """execute_improvement creates an ImprovementJob."""
        from modules.communication.moltbot_bridge.src.openclaw_execution_routes import (
            execute_improvement,
            get_last_improvement_job,
        )

        intent = MockIntent(
            raw_message="fix wsp violation in holo_index",
            extracted_task="fix wsp violation in holo_index",
            sender="test_user",
        )
        execute_improvement(MockDAE(), intent)

        job = get_last_improvement_job()
        assert job is not None
        assert job.job_id.startswith("imp_")

    def test_job_has_dry_run_true(self):
        """Created ImprovementJob always has dry_run=True."""
        from modules.communication.moltbot_bridge.src.openclaw_execution_routes import (
            execute_improvement,
            get_last_improvement_job,
        )

        intent = MockIntent(
            raw_message="repair module wre_core",
            extracted_task="repair module wre_core",
        )
        execute_improvement(MockDAE(), intent)

        job = get_last_improvement_job()
        assert job is not None
        assert job.dry_run is True

    def test_job_improvement_type_matches_classification(self):
        """ImprovementJob.improvement_type matches classification."""
        from modules.communication.moltbot_bridge.src.openclaw_execution_routes import (
            execute_improvement,
            get_last_improvement_job,
        )
        from modules.infrastructure.wre_core.src.improvement_job_contract import (
            ImprovementType,
        )

        # Test WSP violation
        intent = MockIntent(raw_message="fix wsp violation")
        execute_improvement(MockDAE(), intent)
        job = get_last_improvement_job()
        assert job.improvement_type == ImprovementType.WSP_VIOLATION

    def test_job_improvement_type_test_hygiene(self):
        """Test hygiene keyword creates TEST_HYGIENE job."""
        from modules.communication.moltbot_bridge.src.openclaw_execution_routes import (
            execute_improvement,
            get_last_improvement_job,
        )
        from modules.infrastructure.wre_core.src.improvement_job_contract import (
            ImprovementType,
        )

        intent = MockIntent(raw_message="fix stale test in ai_overseer")
        execute_improvement(MockDAE(), intent)
        job = get_last_improvement_job()
        assert job.improvement_type == ImprovementType.TEST_HYGIENE

    def test_job_improvement_type_fmas_scan(self):
        """FMAS keyword creates FMAS_SCAN job."""
        from modules.communication.moltbot_bridge.src.openclaw_execution_routes import (
            execute_improvement,
            get_last_improvement_job,
        )
        from modules.infrastructure.wre_core.src.improvement_job_contract import (
            ImprovementType,
        )

        intent = MockIntent(raw_message="run fmas repair on communication")
        execute_improvement(MockDAE(), intent)
        job = get_last_improvement_job()
        assert job.improvement_type == ImprovementType.FMAS_SCAN

    def test_response_includes_job_id(self):
        """Response text includes the job_id."""
        from modules.communication.moltbot_bridge.src.openclaw_execution_routes import (
            execute_improvement,
            get_last_improvement_job,
        )

        intent = MockIntent(raw_message="fix drift in navigation")
        result = execute_improvement(MockDAE(), intent)

        job = get_last_improvement_job()
        assert job is not None
        assert job.job_id in result

    def test_response_includes_dry_run_true(self):
        """Response text includes dry_run status."""
        from modules.communication.moltbot_bridge.src.openclaw_execution_routes import (
            execute_improvement,
        )

        intent = MockIntent(raw_message="repair module test")
        result = execute_improvement(MockDAE(), intent)

        assert "Dry Run" in result
        assert "True" in result

    def test_response_includes_wsp97_disclaimer(self):
        """Response includes WSP 97 truth boundary disclaimer."""
        from modules.communication.moltbot_bridge.src.openclaw_execution_routes import (
            execute_improvement,
        )

        intent = MockIntent(raw_message="fix wsp violation")
        result = execute_improvement(MockDAE(), intent)

        assert "WSP 97" in result
        assert "not executed" in result.lower() or "NOT executed" in result

    def test_no_execution_occurs(self):
        """Job is created but not executed - status is PENDING."""
        from modules.communication.moltbot_bridge.src.openclaw_execution_routes import (
            execute_improvement,
            get_last_improvement_job,
        )
        from modules.infrastructure.wre_core.src.improvement_job_contract import (
            ImprovementStatus,
        )

        intent = MockIntent(raw_message="repair module test")
        execute_improvement(MockDAE(), intent)

        job = get_last_improvement_job()
        assert job is not None
        assert job.status == ImprovementStatus.PENDING
        assert job.completed_at is None
        assert job.assigned_worker is None


class TestImprovementJobScopeExtraction:
    """Test scope extraction from improvement messages."""

    def setup_method(self):
        """Clear inspection hook before each test."""
        from modules.communication.moltbot_bridge.src.openclaw_execution_routes import (
            clear_improvement_job_hook,
        )
        clear_improvement_job_hook()

    def test_extracts_wsp_refs(self):
        """WSP references are extracted to scope.wsp_refs."""
        from modules.communication.moltbot_bridge.src.openclaw_execution_routes import (
            execute_improvement,
            get_last_improvement_job,
        )

        intent = MockIntent(raw_message="fix wsp 49 violation in module")
        execute_improvement(MockDAE(), intent)

        job = get_last_improvement_job()
        assert "WSP 49" in job.scope.wsp_refs

    def test_extracts_module_path(self):
        """Module path is extracted from message."""
        from modules.communication.moltbot_bridge.src.openclaw_execution_routes import (
            execute_improvement,
            get_last_improvement_job,
        )

        intent = MockIntent(raw_message="repair modules/infrastructure/wre_core")
        execute_improvement(MockDAE(), intent)

        job = get_last_improvement_job()
        assert "modules/infrastructure/wre_core" in job.scope.module_path


class TestImprovementJobRiskLevel:
    """Test risk level derivation."""

    def setup_method(self):
        """Clear inspection hook before each test."""
        from modules.communication.moltbot_bridge.src.openclaw_execution_routes import (
            clear_improvement_job_hook,
        )
        clear_improvement_job_hook()

    def test_security_keyword_high_risk(self):
        """Security-related keywords result in HIGH risk."""
        from modules.communication.moltbot_bridge.src.openclaw_execution_routes import (
            execute_improvement,
            get_last_improvement_job,
        )
        from modules.infrastructure.wre_core.src.improvement_job_contract import (
            ImprovementRiskLevel,
        )

        intent = MockIntent(raw_message="fix security vulnerability")
        execute_improvement(MockDAE(), intent)

        job = get_last_improvement_job()
        assert job.risk_level == ImprovementRiskLevel.HIGH

    def test_doc_hygiene_low_risk(self):
        """Documentation hygiene is LOW risk."""
        from modules.communication.moltbot_bridge.src.openclaw_execution_routes import (
            execute_improvement,
            get_last_improvement_job,
        )
        from modules.infrastructure.wre_core.src.improvement_job_contract import (
            ImprovementRiskLevel,
        )

        intent = MockIntent(raw_message="update modlog for test module")
        execute_improvement(MockDAE(), intent)

        job = get_last_improvement_job()
        assert job.risk_level == ImprovementRiskLevel.LOW


class TestImprovementAdvisoryTextWSP97:
    """Test WSP 97 compliance in advisory text."""

    def test_advisory_no_execution_claim(self):
        """Advisory does not claim repair was executed."""
        from modules.communication.moltbot_bridge.src.openclaw_execution_routes import (
            execute_improvement,
        )

        intent = MockIntent(raw_message="repair module test")
        result = execute_improvement(MockDAE(), intent)

        # Should NOT contain claims of execution
        assert "executed repair" not in result.lower()
        assert "fixed" not in result.lower()
        assert "repaired" not in result.lower()

        # Should contain disclaimer
        assert "not implemented" in result.lower() or "NOT executed" in result

    def test_advisory_states_job_created(self):
        """Advisory states job was created."""
        from modules.communication.moltbot_bridge.src.openclaw_execution_routes import (
            execute_improvement,
        )

        intent = MockIntent(raw_message="fix wsp violation")
        result = execute_improvement(MockDAE(), intent)

        assert "ImprovementJob Created" in result
        assert "Job ID" in result

    def test_advisory_includes_status_pending(self):
        """Advisory shows status as created/pending."""
        from modules.communication.moltbot_bridge.src.openclaw_execution_routes import (
            execute_improvement,
        )

        intent = MockIntent(raw_message="repair module")
        result = execute_improvement(MockDAE(), intent)

        assert "pending" in result.lower() or "created" in result.lower()
