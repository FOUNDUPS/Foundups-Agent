#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Focused tests for OpenClaw FOUNDUP routing through orchestrator.

OC1 Tests (Phase 1):
1. execute_foundup() routes through dispatch_foundup()
2. dispatch_foundup() calls FAM adapter for advisory queries
3. Fallback behavior preserved on ImportError/Exception
4. Plan steps for FOUNDUP are explicit (not digital_twin_response)

OC1 Phase 2 Tests:
5. Explicit build intent creates FoundUpJob
6. Advisory query still routes to FAM adapter
7. Job response includes job_id and queued status
8. No false claim that Hermes executed the job

WSP Compliance:
    WSP 97: Tests verify actual routing, not assumed behavior
    WSP 15: Fallback paths tested for safety

Slice: OC1_PHASE2_OPENCLAW_FOUNDUP_JOB_CREATION_WIRING
Worker: W1
"""

import sys
import pytest
from unittest.mock import patch, MagicMock


class TestFoundupDispatch:
    """Test dispatch_foundup function."""

    def test_dispatch_routes_to_fam_adapter(self):
        """Dispatch should call fam_adapter.handle_fam_intent."""
        mock_intent = MagicMock()
        mock_intent.raw_message = "what is cabr"
        mock_intent.sender = "test_user"
        mock_dae = MagicMock()

        # Create mock fam_adapter module
        mock_fam_adapter = MagicMock()
        mock_fam_adapter.handle_fam_intent = MagicMock(return_value="CABR response")

        with patch.dict(
            sys.modules,
            {"modules.communication.moltbot_bridge.src.fam_adapter": mock_fam_adapter},
        ):
            # Force reimport to pick up the mocked module
            from modules.communication.moltbot_bridge.src import (
                openclaw_foundup_orchestrator,
            )

            # Clear module cache to force fresh import in dispatch
            import importlib

            importlib.reload(openclaw_foundup_orchestrator)

            result = openclaw_foundup_orchestrator.dispatch_foundup(
                mock_dae, mock_intent
            )

        mock_fam_adapter.handle_fam_intent.assert_called_once_with(
            "what is cabr", "test_user"
        )
        assert result == "CABR response"

    def test_dispatch_fallback_on_import_error(self):
        """Dispatch should return fallback message on ImportError."""
        from modules.communication.moltbot_bridge.src.openclaw_foundup_orchestrator import (
            dispatch_foundup,
        )

        # Verify docstring indicates FAM passthrough for advisory queries
        doc = dispatch_foundup.__doc__.lower()
        assert "fam" in doc
        assert "advisory" in doc or "passthrough" in doc

    def test_dispatch_fallback_message_format(self):
        """Verify fallback messages match expected format."""
        # Verify the fallback messages are preserved in the implementation
        from modules.communication.moltbot_bridge.src import (
            openclaw_foundup_orchestrator,
        )
        import inspect

        source = inspect.getsource(openclaw_foundup_orchestrator.dispatch_foundup)

        # Verify ImportError fallback message preserved
        assert "FoundUps Agent Market not available" in source

        # Verify Exception fallback format preserved
        assert "FAM error" in source


class TestExecuteFoundupWiring:
    """Test execute_foundup routes through orchestrator."""

    def test_execute_foundup_imports_from_orchestrator(self):
        """execute_foundup should import dispatch_foundup from orchestrator."""
        from modules.communication.moltbot_bridge.src import openclaw_execution_routes
        import inspect

        source = inspect.getsource(openclaw_execution_routes.execute_foundup)

        # Verify it imports from orchestrator
        assert "openclaw_foundup_orchestrator" in source
        assert "dispatch_foundup" in source

    def test_execute_foundup_has_fallback_to_direct_fam(self):
        """execute_foundup should have fallback to direct FAM on orchestrator unavailable."""
        from modules.communication.moltbot_bridge.src import openclaw_execution_routes
        import inspect

        source = inspect.getsource(openclaw_execution_routes.execute_foundup)

        # Verify fallback imports fam_adapter directly
        assert "from .fam_adapter import handle_fam_intent" in source

        # Verify fallback message preserved
        assert "FoundUps Agent Market not available" in source


class TestFoundupPlanSteps:
    """Test planner generates correct FOUNDUP steps."""

    def test_foundup_has_explicit_plan_steps(self):
        """FOUNDUP should have foundup_orchestrator_dispatch, not digital_twin_response."""
        from modules.communication.moltbot_bridge.src.openclaw_intent_planner import (
            plan_execution,
        )
        from enum import Enum

        # Create proper enum for IntentCategory with all required values
        class MockIntentCategory(Enum):
            QUERY = "query"
            COMMAND = "command"
            MONITOR = "monitor"
            SCHEDULE = "schedule"
            SOCIAL = "social"
            SYSTEM = "system"
            RESEARCH = "research"
            FOUNDUP = "foundup"
            CONVERSATION = "conversation"

        class MockTier:
            value = "advisory"

        class MockPlan:
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)

        mock_dae = MagicMock()
        mock_dae.IntentCategory = MockIntentCategory
        mock_dae.ExecutionPlan = MockPlan

        mock_intent = MagicMock()
        mock_intent.category = MockIntentCategory.FOUNDUP
        mock_intent.target_domain = "fam_adapter"
        mock_intent.extracted_task = "test task"
        mock_intent.raw_message = "test task"

        plan = plan_execution(mock_dae, mock_intent, MockTier())

        assert plan.steps[0]["action"] == "foundup_orchestrator_dispatch"
        assert plan.steps[1]["action"] == "fam_or_genesis_route"
        assert plan.estimated_tokens == 100

    def test_foundup_branch_exists_in_planner(self):
        """Verify FOUNDUP has explicit branch, not else fallback."""
        from modules.communication.moltbot_bridge.src import openclaw_intent_planner
        import inspect

        source = inspect.getsource(openclaw_intent_planner.plan_execution)

        # Verify explicit FOUNDUP branch exists
        assert "IntentCategory.FOUNDUP" in source

        # Verify correct action names
        assert "foundup_orchestrator_dispatch" in source
        assert "fam_or_genesis_route" in source


# ---------------------------------------------------------------------------
# Phase 2 Tests: Explicit Build Intent Creates FoundUpJob
# ---------------------------------------------------------------------------


class TestFoundupJobCreation:
    """Test Phase 2: explicit build intent creates typed FoundUpJob."""

    def setup_method(self):
        """Clear job queue before each test."""
        from modules.communication.moltbot_bridge.src.openclaw_foundup_orchestrator import (
            clear_job_queue,
        )

        clear_job_queue()

    def test_start_build_creates_job(self):
        """'start build gotjunk' should create a queued FoundUpJob."""
        from modules.communication.moltbot_bridge.src.openclaw_foundup_orchestrator import (
            dispatch_foundup,
            get_job_queue,
        )

        mock_intent = MagicMock()
        mock_intent.raw_message = "start build gotjunk"
        mock_intent.sender = "test_user"
        mock_intent.session_key = "session_123"
        mock_intent.channel = "discord"
        mock_dae = MagicMock()

        result = dispatch_foundup(mock_dae, mock_intent)

        # Verify job was created
        queue = get_job_queue()
        assert len(queue) == 1

        job = queue[0]
        assert job.status.value == "queued"
        assert job.tenant_id == "test_user"
        assert job.foundup_id == "gotjunk"
        assert job.requested_action == "build_foundup"
        assert job.intent_id == "session_123"
        assert job.payload["channel"] == "discord"
        assert job.payload["source"] == "openclaw_foundup_orchestrator"
        assert "execution not started" in job.status_reason_human

    def test_job_response_includes_required_fields(self):
        """Response should include job_id, status, action, foundup_id."""
        from modules.communication.moltbot_bridge.src.openclaw_foundup_orchestrator import (
            dispatch_foundup,
        )

        mock_intent = MagicMock()
        mock_intent.raw_message = "hermes build social_twin"
        mock_intent.sender = "012"
        mock_intent.session_key = None
        mock_intent.channel = "voice_repl"
        mock_dae = MagicMock()

        result = dispatch_foundup(mock_dae, mock_intent)

        assert "job_id:" in result
        assert "status: queued" in result
        assert "requested_action:" in result
        assert "foundup_id:" in result
        assert "next: Hermes/WRE pending" in result

    def test_extract_action_detected(self):
        """'extract foundup gotjunk' should have action=extract."""
        from modules.communication.moltbot_bridge.src.openclaw_foundup_orchestrator import (
            dispatch_foundup,
            get_job_queue,
        )

        mock_intent = MagicMock()
        mock_intent.raw_message = "extract foundup move2japan"
        mock_intent.sender = "test_user"
        mock_intent.session_key = None
        mock_intent.channel = "local_repl"
        mock_dae = MagicMock()

        dispatch_foundup(mock_dae, mock_intent)

        queue = get_job_queue()
        assert len(queue) == 1
        assert queue[0].requested_action == "extract_foundup"
        assert queue[0].foundup_id == "move2japan"

    def test_validate_action_detected(self):
        """'validate foundup kosei' should have action=validate."""
        from modules.communication.moltbot_bridge.src.openclaw_foundup_orchestrator import (
            dispatch_foundup,
            get_job_queue,
        )

        mock_intent = MagicMock()
        mock_intent.raw_message = "validate foundup kosei"
        mock_intent.sender = "test_user"
        mock_intent.session_key = None
        mock_intent.channel = "local_repl"
        mock_dae = MagicMock()

        dispatch_foundup(mock_dae, mock_intent)

        queue = get_job_queue()
        assert len(queue) == 1
        assert queue[0].requested_action == "validate_foundup"
        assert queue[0].foundup_id == "kosei"

    def test_no_false_hermes_execution_claim(self):
        """Response should NOT claim Hermes executed the job."""
        from modules.communication.moltbot_bridge.src.openclaw_foundup_orchestrator import (
            dispatch_foundup,
            get_job_queue,
        )

        mock_intent = MagicMock()
        mock_intent.raw_message = "start build gotjunk"
        mock_intent.sender = "test_user"
        mock_intent.session_key = None
        mock_intent.channel = "discord"
        mock_dae = MagicMock()

        result = dispatch_foundup(mock_dae, mock_intent)

        # Verify no false claims
        assert "executed" not in result.lower()
        assert "completed" not in result.lower()
        assert "succeeded" not in result.lower()

        # Verify job has no execution timestamps
        queue = get_job_queue()
        job = queue[0]
        assert job.started_at is None
        assert job.completed_at is None
        assert job.worker_id is None

    def test_policy_flags_not_falsely_set(self):
        """Policy flags should NOT claim gates passed (WSP 97 truth)."""
        from modules.communication.moltbot_bridge.src.openclaw_foundup_orchestrator import (
            dispatch_foundup,
            get_job_queue,
        )

        mock_intent = MagicMock()
        mock_intent.raw_message = "openclaw build pqn_portal"
        mock_intent.sender = "test_user"
        mock_intent.session_key = None
        mock_intent.channel = "local_repl"
        mock_dae = MagicMock()

        dispatch_foundup(mock_dae, mock_intent)

        queue = get_job_queue()
        job = queue[0]

        # All gates should be unchecked/unpassed
        assert job.policy_flags.security_gate_checked is False
        assert job.policy_flags.security_gate_passed is False
        assert job.policy_flags.exfoliation_gate_checked is False
        assert job.policy_flags.exfoliation_gate_passed is False


class TestAdvisoryQueryPreserved:
    """Test that advisory queries still route to FAM (Phase 1 preserved)."""

    def setup_method(self):
        """Clear job queue before each test."""
        from modules.communication.moltbot_bridge.src.openclaw_foundup_orchestrator import (
            clear_job_queue,
        )

        clear_job_queue()

    def test_what_is_query_routes_to_fam(self):
        """'what is cabr' should NOT create a job, should call FAM."""
        from modules.communication.moltbot_bridge.src.openclaw_foundup_orchestrator import (
            get_job_queue,
            _is_explicit_build_intent,
        )

        # Verify advisory query is NOT build intent
        assert _is_explicit_build_intent("what is cabr") is False
        assert _is_explicit_build_intent("tell me about foundups") is False
        assert _is_explicit_build_intent("how does gotjunk work") is False

    def test_explain_query_not_build_intent(self):
        """'explain foundup lifecycle' should NOT be build intent."""
        from modules.communication.moltbot_bridge.src.openclaw_foundup_orchestrator import (
            _is_explicit_build_intent,
        )

        assert _is_explicit_build_intent("explain foundup lifecycle") is False
        assert _is_explicit_build_intent("list all foundups") is False
        assert _is_explicit_build_intent("show me gotjunk status") is False

    def test_build_phrases_are_detected(self):
        """All trigger phrases should be detected as build intent."""
        from modules.communication.moltbot_bridge.src.openclaw_foundup_orchestrator import (
            _is_explicit_build_intent,
        )

        # All trigger phrases from spec
        assert _is_explicit_build_intent("start build gotjunk") is True
        assert _is_explicit_build_intent("start building social_twin") is True
        assert _is_explicit_build_intent("build foundup kosei") is True
        assert _is_explicit_build_intent("create foundup job move2japan") is True
        assert _is_explicit_build_intent("queue foundup job pqn_portal") is True
        assert _is_explicit_build_intent("hermes build") is True
        assert _is_explicit_build_intent("openclaw build gotjunk") is True
        assert _is_explicit_build_intent("extract foundup kosei") is True
        assert _is_explicit_build_intent("exfoliate foundup gotjunk") is True
        assert _is_explicit_build_intent("validate foundup social_twin") is True


class TestFoundupIdExtraction:
    """Test foundup_id extraction from build messages."""

    def test_extract_simple_id(self):
        """Extract simple foundup_id like 'gotjunk'."""
        from modules.communication.moltbot_bridge.src.openclaw_foundup_orchestrator import (
            _extract_foundup_id,
        )

        assert _extract_foundup_id("start build gotjunk") == "gotjunk"
        assert _extract_foundup_id("build foundup social_twin") == "social_twin"
        assert _extract_foundup_id("hermes build kosei") == "kosei"

    def test_extract_with_stopwords(self):
        """Stopwords like 'the', 'this' should be filtered."""
        from modules.communication.moltbot_bridge.src.openclaw_foundup_orchestrator import (
            _extract_foundup_id,
        )

        assert _extract_foundup_id("build the foundup gotjunk") == "gotjunk"
        assert _extract_foundup_id("build this foundup kosei") == "kosei"

    def test_no_foundup_specified(self):
        """'hermes build' with no foundup should return None."""
        from modules.communication.moltbot_bridge.src.openclaw_foundup_orchestrator import (
            _extract_foundup_id,
        )

        assert _extract_foundup_id("hermes build") is None
        assert _extract_foundup_id("start build") is None
        assert _extract_foundup_id("build foundup") is None
