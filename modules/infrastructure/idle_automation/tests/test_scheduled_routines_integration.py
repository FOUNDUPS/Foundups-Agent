#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integration tests for scheduled routines in idle automation.

Tests cover:
- Scheduled routine execution through idle automation DAE
- Dispatch to correct native paths
- Result recording and status reporting
"""

import asyncio
import json
import hashlib
import sys
import types
import pytest
from datetime import datetime, UTC
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from modules.infrastructure.idle_automation.src.schedule_evaluator import (
    ScheduleEvaluator,
)
from modules.infrastructure.idle_automation.src.schedule_claim_state import (
    ScheduleClaim,
    build_execution_id,
)

RECEIPT_ID = "model_provider_catalog_discovery_receipt:" + ("a" * 64)
CANDIDATE_ID = "model_provider_catalog_candidate_snapshot:" + ("b" * 64)


def _schedule_claim(
    *,
    routine: str = "openrouter_catalog_refresh",
    cadence: str = "daily",
) -> ScheduleClaim:
    start = "2026-07-24T00:00:00+00:00"
    end = "2026-07-25T00:00:00+00:00"
    schedule_id = hashlib.sha256(
        b"openrouter_catalog_refresh:daily"
    ).hexdigest()[:12]
    return ScheduleClaim(
        schedule_id=schedule_id,
        routine=routine,
        cadence=cadence,
        window_start=start,
        window_end=end,
        execution_id=build_execution_id(
            schedule_id, routine, cadence, start, end
        ),
        token="opaque-claim-token",
        claimant_id="idle-dae",
        lease_expires_at="2026-07-24T01:00:00+00:00",
        attempt=1,
    )


def _adapter_projection(
    status: str,
    reason: str,
    *,
    success: bool = False,
) -> dict:
    return {
        "success": success,
        "status": status,
        "reason": reason,
        "replayed": False,
        "receipt_id": RECEIPT_ID if success else None,
        "candidate_snapshot_id": CANDIDATE_ID if success else None,
    }


class TestScheduledRoutinesDispatch:
    """Test scheduled routine dispatch logic."""

    @pytest.fixture
    def temp_memory_path(self, tmp_path):
        """Create temporary memory directory."""
        memory_dir = tmp_path / "memory"
        memory_dir.mkdir()
        return memory_dir

    @pytest.fixture
    def mock_dae(self, temp_memory_path):
        """Create a mock IdleAutomationDAE with temp paths."""
        from modules.infrastructure.idle_automation.src.idle_automation_dae import (
            IdleAutomationDAE,
        )

        # Patch memory path before instantiation
        with patch.object(IdleAutomationDAE, "__init__", lambda self: None):
            dae = IdleAutomationDAE()
            dae.module_path = temp_memory_path.parent
            dae.memory_path = temp_memory_path
            dae.idle_state = {}
            dae.execution_history = []
            dae.config = {
                "auto_git_push": False,
                "auto_linkedin_post": False,
                "auto_self_research": True,
                "idle_task_timeout": 300,
                "max_daily_executions": 3,
                "self_research_timeout": 900,
                "health_critical_threshold": 20,
                "health_warning_threshold": 50,
            }
            dae.wre_integration = None

            # Add required methods
            dae._parse_bool_env = lambda key, default: default
            dae._save_idle_state = MagicMock()

            return dae

    def test_openrouter_runtime_config_defaults_safe(
        self, mock_dae, monkeypatch, tmp_path
    ):
        """Provider refresh is opt-in with one code-owned runtime root."""
        from modules.infrastructure.idle_automation.src.idle_automation_dae import (
            IdleAutomationDAE,
        )

        monkeypatch.delenv("AUTO_OPENROUTER_CATALOG_REFRESH", raising=False)
        monkeypatch.delenv("OPENROUTER_CATALOG_RUNTIME_ROOT", raising=False)
        with patch.object(Path, "home", return_value=tmp_path / "home"):
            config = IdleAutomationDAE._load_and_validate_config(mock_dae)

        assert config["auto_openrouter_catalog_refresh"] is False
        assert config["openrouter_catalog_runtime_root"] == (
            tmp_path
            / "home"
            / ".foundups-agent"
            / "ai_gateway"
            / "openrouter_catalog"
        )

    @pytest.mark.asyncio
    async def test_execute_scheduled_routines_no_due_schedules(
        self, mock_dae, temp_memory_path
    ):
        """When no schedules are due, returns success with 0 executed."""
        from modules.infrastructure.idle_automation.src.idle_automation_dae import (
            IdleAutomationDAE,
        )

        schedules_path = temp_memory_path / "schedules.json"
        mock_evaluator = ScheduleEvaluator(schedules_path=schedules_path)

        with patch(
            "modules.infrastructure.idle_automation.src.schedule_evaluator.ScheduleEvaluator",
            return_value=mock_evaluator,
        ):
            result = await IdleAutomationDAE._execute_scheduled_routines(mock_dae)

        assert result["success"] is True
        assert result["due_count"] == 0
        assert result["executed_count"] == 0

    @pytest.mark.asyncio
    async def test_execute_scheduled_routines_dispatches_self_research(
        self, mock_dae, temp_memory_path
    ):
        """Due self_research schedule dispatches to self research refresh."""
        from modules.infrastructure.idle_automation.src.idle_automation_dae import (
            IdleAutomationDAE,
        )

        # Create a due schedule
        schedules_path = temp_memory_path / "schedules.json"
        evaluator = ScheduleEvaluator(schedules_path=schedules_path)
        evaluator.add_schedule("run self research daily")

        # Mock the self-research execution
        mock_dae._execute_self_research_refresh = AsyncMock(
            return_value={
                "success": True,
                "update_candidates": 5,
                "autonomous_tasks": 2,
            }
        )

        with patch(
            "modules.infrastructure.idle_automation.src.schedule_evaluator.ScheduleEvaluator",
            return_value=evaluator,
        ):
            result = await IdleAutomationDAE._execute_scheduled_routines(mock_dae)

        assert result["success"] is True
        assert result["due_count"] == 1
        assert result["executed_count"] == 1
        mock_dae._execute_self_research_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_scheduled_routines_dispatches_queue_audit(
        self, mock_dae, temp_memory_path
    ):
        """Due queue_audit schedule dispatches to queue builder."""
        from modules.infrastructure.idle_automation.src.idle_automation_dae import (
            IdleAutomationDAE,
        )

        # Create a due schedule
        schedules_path = temp_memory_path / "schedules.json"
        evaluator = ScheduleEvaluator(schedules_path=schedules_path)
        evaluator.add_schedule("run queue audit daily")

        # Mock the queue audit execution
        mock_dae._run_queue_audit = AsyncMock(
            return_value={"success": True, "summary": "Queue refreshed"}
        )

        with patch(
            "modules.infrastructure.idle_automation.src.schedule_evaluator.ScheduleEvaluator",
            return_value=evaluator,
        ):
            result = await IdleAutomationDAE._execute_scheduled_routines(mock_dae)

        assert result["success"] is True
        assert result["executed_count"] == 1
        mock_dae._run_queue_audit.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_scheduled_routines_records_execution(
        self, mock_dae, temp_memory_path
    ):
        """Execution is recorded in schedule spec."""
        from modules.infrastructure.idle_automation.src.idle_automation_dae import (
            IdleAutomationDAE,
        )

        # Create a due schedule
        schedules_path = temp_memory_path / "schedules.json"
        evaluator = ScheduleEvaluator(schedules_path=schedules_path)
        spec = evaluator.add_schedule("run self research daily")
        assert spec.last_run is None

        # Mock the self-research execution
        mock_dae._execute_self_research_refresh = AsyncMock(
            return_value={
                "success": True,
                "update_candidates": 5,
                "autonomous_tasks": 2,
            }
        )

        with patch(
            "modules.infrastructure.idle_automation.src.schedule_evaluator.ScheduleEvaluator",
            return_value=evaluator,
        ):
            await IdleAutomationDAE._execute_scheduled_routines(mock_dae)

        # Check last_run is set on the evaluator instance we passed in
        updated = evaluator.get_schedule(spec.id)
        assert updated.last_run is not None

    @pytest.mark.asyncio
    async def test_execute_scheduled_routines_disabled_returns_early(
        self, mock_dae, temp_memory_path
    ):
        """When disabled via env, returns early without evaluating."""
        from modules.infrastructure.idle_automation.src.idle_automation_dae import (
            IdleAutomationDAE,
        )

        mock_dae._parse_bool_env = lambda key, default: (
            False if key == "AUTO_SCHEDULED_ROUTINES" else default
        )

        result = await IdleAutomationDAE._execute_scheduled_routines(mock_dae)

        assert result["success"] is False
        assert "disabled" in result["error"].lower()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("failure", ["malformed", "write_failed"])
    async def test_claim_state_failure_causes_zero_dispatch(
        self, mock_dae, failure
    ):
        """Uncertain claim durability fails closed before any routine runs."""
        from modules.infrastructure.idle_automation.src.idle_automation_dae import (
            IdleAutomationDAE,
        )
        from modules.infrastructure.idle_automation.src.schedule_claim_state import (
            ScheduleStateError,
        )

        evaluator = MagicMock()
        evaluator.get_due_schedules.return_value = [
            MagicMock(id="one", routine="self_research", cadence="daily")
        ]
        evaluator.claim_schedule.side_effect = ScheduleStateError(failure)
        mock_dae._dispatch_scheduled_routine = AsyncMock()

        with patch(
            "modules.infrastructure.idle_automation.src.schedule_evaluator.ScheduleEvaluator",
            return_value=evaluator,
        ):
            result = await IdleAutomationDAE._execute_scheduled_routines(mock_dae)

        assert result["success"] is False
        assert "claim state" in result["error"].lower()
        mock_dae._dispatch_scheduled_routine.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_disabled_mode_does_not_construct_or_dispatch(self, mock_dae):
        """Disabled scheduling performs zero claim-state or dispatch work."""
        from modules.infrastructure.idle_automation.src.idle_automation_dae import (
            IdleAutomationDAE,
        )

        mock_dae._parse_bool_env = lambda key, default: (
            False if key == "AUTO_SCHEDULED_ROUTINES" else default
        )
        mock_dae._dispatch_scheduled_routine = AsyncMock()
        with patch(
            "modules.infrastructure.idle_automation.src.schedule_evaluator.ScheduleEvaluator"
        ) as evaluator_type:
            result = await IdleAutomationDAE._execute_scheduled_routines(mock_dae)

        assert result["success"] is False
        evaluator_type.assert_not_called()
        mock_dae._dispatch_scheduled_routine.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_finalize_failure_is_completion_unknown(self, mock_dae):
        """A publish failure after dispatch does not update legacy last-run."""
        from modules.infrastructure.idle_automation.src.idle_automation_dae import (
            IdleAutomationDAE,
        )

        spec = MagicMock(id="one", routine="self_research", cadence="daily")
        claim = MagicMock(token="opaque", routine="self_research")
        evaluator = MagicMock()
        evaluator.get_due_schedules.return_value = [spec]
        evaluator.claim_schedule.return_value = claim
        evaluator.finalize_claim.side_effect = OSError("simulated")
        mock_dae._dispatch_scheduled_routine = AsyncMock(
            return_value={"success": True, "summary": "done"}
        )
        with patch(
            "modules.infrastructure.idle_automation.src.schedule_evaluator.ScheduleEvaluator",
            return_value=evaluator,
        ):
            result = await IdleAutomationDAE._execute_scheduled_routines(mock_dae)

        assert result["success"] is False
        assert result["finalization_failed_count"] == 1
        assert result["executed_count"] == 0
        evaluator.record_execution.assert_not_called()
        mock_dae._dispatch_scheduled_routine.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_claim_dispatch_passes_full_exact_schedule_claim(
        self, mock_dae
    ):
        """The durable claim identity must reach final dispatch intact."""
        from modules.infrastructure.idle_automation.src.idle_automation_dae import (
            IdleAutomationDAE,
        )

        spec = MagicMock(
            id="canonical-schedule",
            routine="openrouter_catalog_refresh",
            cadence="daily",
        )
        claim = _schedule_claim()
        evaluator = MagicMock()
        evaluator.claim_schedule.return_value = claim
        evaluator.finalize_claim.return_value = True
        mock_dae._dispatch_claimed_routine = AsyncMock(
            return_value={"success": True, "outcome": "completed"}
        )
        result = IdleAutomationDAE._scheduled_routines_result()

        continued = await IdleAutomationDAE._claim_and_dispatch(
            mock_dae, evaluator, spec, result
        )

        assert continued is True
        mock_dae._dispatch_claimed_routine.assert_awaited_once_with(claim)

    @pytest.mark.asyncio
    async def test_openrouter_final_dispatch_defaults_disabled(
        self, mock_dae, monkeypatch
    ):
        """The last dispatch boundary is opt-in and makes no adapter call."""
        from modules.infrastructure.idle_automation.src.idle_automation_dae import (
            IdleAutomationDAE,
        )

        adapter_name = (
            "modules.ai_intelligence.ai_gateway.src."
            "model_openrouter_schedule_adapter"
        )
        adapter = types.ModuleType(adapter_name)
        adapter.run_openrouter_catalog_schedule_claim = AsyncMock()
        monkeypatch.setitem(sys.modules, adapter_name, adapter)
        parsed = []

        def parse_bool(key, default):
            parsed.append((key, default))
            return default

        mock_dae._parse_bool_env = parse_bool
        result = await IdleAutomationDAE._dispatch_openrouter_catalog_claim(
            mock_dae, _schedule_claim()
        )

        assert parsed == [("AUTO_OPENROUTER_CATALOG_REFRESH", False)]
        assert result == {
            "success": False,
            "status": "BLOCKED_PRECALL",
            "reason": "refresh_disabled",
            "replayed": False,
            "receipt_id": None,
            "candidate_snapshot_id": None,
        }
        adapter.run_openrouter_catalog_schedule_claim.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_enabled_final_dispatch_passes_exact_claim_and_roots_once(
        self, mock_dae, monkeypatch, tmp_path
    ):
        """Enabled dispatch forwards only code/config-owned roots."""
        from modules.infrastructure.idle_automation.src.idle_automation_dae import (
            IdleAutomationDAE,
        )

        adapter_name = (
            "modules.ai_intelligence.ai_gateway.src."
            "model_openrouter_schedule_adapter"
        )
        adapter = types.ModuleType(adapter_name)
        expected = _adapter_projection(
            "COMPLETED", "completed", success=True
        )
        adapter.run_openrouter_catalog_schedule_claim = AsyncMock(
            return_value=expected
        )
        monkeypatch.setitem(sys.modules, adapter_name, adapter)
        mock_dae._parse_bool_env = lambda key, default: (
            True if key == "AUTO_OPENROUTER_CATALOG_REFRESH" else default
        )
        repo = tmp_path / "repo"
        mock_dae.module_path = (
            repo / "modules/infrastructure/idle_automation"
        )
        runtime = tmp_path / "trusted-catalog-runtime"
        mock_dae.config["openrouter_catalog_runtime_root"] = runtime
        claim = _schedule_claim()

        result = await IdleAutomationDAE._dispatch_openrouter_catalog_claim(
            mock_dae, claim
        )

        assert result == expected
        adapter.run_openrouter_catalog_schedule_claim.assert_awaited_once_with(
            claim,
            repo_root=repo,
            runtime_root=runtime,
        )

    @pytest.mark.asyncio
    async def test_forged_non_daily_claim_stops_before_adapter(
        self, mock_dae, monkeypatch
    ):
        """Persisted/forged cadence cannot reach adapter or provider."""
        from modules.infrastructure.idle_automation.src.idle_automation_dae import (
            IdleAutomationDAE,
        )

        adapter_name = (
            "modules.ai_intelligence.ai_gateway.src."
            "model_openrouter_schedule_adapter"
        )
        adapter = types.ModuleType(adapter_name)
        adapter.run_openrouter_catalog_schedule_claim = AsyncMock()
        monkeypatch.setitem(sys.modules, adapter_name, adapter)
        mock_dae._parse_bool_env = lambda key, default: (
            True if key == "AUTO_OPENROUTER_CATALOG_REFRESH" else default
        )

        result = await IdleAutomationDAE._dispatch_openrouter_catalog_claim(
            mock_dae, _schedule_claim(cadence="nightly")
        )

        assert result == {
            "success": False,
            "status": "BLOCKED_PRECALL",
            "reason": "claim_invalid",
            "replayed": False,
            "receipt_id": None,
            "candidate_snapshot_id": None,
        }
        adapter.run_openrouter_catalog_schedule_claim.assert_not_awaited()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("projection", "success", "outcome"),
        [
            (
                _adapter_projection(
                    "COMPLETED", "completed", success=True
                ),
                True,
                "success",
            ),
            (
                _adapter_projection("FAILED", "transport_failed"),
                False,
                "routine_failed",
            ),
            (
                _adapter_projection(
                    "INDETERMINATE", "replay_state_invalid"
                ),
                False,
                "routine_failed",
            ),
            (
                _adapter_projection(
                    "BLOCKED_PRECALL", "refresh_disabled"
                ),
                False,
                "routine_failed",
            ),
        ],
    )
    async def test_provider_projection_finalizes_exact_claim_token(
        self, mock_dae, projection, success, outcome
    ):
        """Only completed evidence finalizes the claim as success."""
        from modules.infrastructure.idle_automation.src.idle_automation_dae import (
            IdleAutomationDAE,
        )

        claim = _schedule_claim()
        spec = MagicMock(
            id=claim.schedule_id,
            routine=claim.routine,
            cadence=claim.cadence,
        )
        evaluator = MagicMock()
        evaluator.claim_schedule.return_value = claim
        evaluator.finalize_claim.return_value = True
        mock_dae._dispatch_openrouter_catalog_claim = AsyncMock(
            return_value=projection
        )
        result = IdleAutomationDAE._scheduled_routines_result()

        continued = await IdleAutomationDAE._claim_and_dispatch(
            mock_dae, evaluator, spec, result
        )

        assert continued is True
        evaluator.finalize_claim.assert_called_once_with(
            claim.token,
            success=success,
            outcome_code=outcome,
        )
        if success:
            evaluator.record_execution.assert_called_once()
            assert result["executed_count"] == 1
        else:
            evaluator.record_execution.assert_not_called()
            assert result["failed_count"] == 1

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "projection",
        [
            {**_adapter_projection("COMPLETED", "completed", success=True), "success": "false"},
            {**_adapter_projection("COMPLETED", "completed", success=True), "success": 1},
            {**_adapter_projection("COMPLETED", "completed", success=True), "status": "FAILED"},
            {**_adapter_projection("COMPLETED", "wrong", success=True)},
            {**_adapter_projection("COMPLETED", "completed", success=True), "receipt_id": None},
            {
                **_adapter_projection("COMPLETED", "completed", success=True),
                "candidate_snapshot_id": "forged",
            },
            {**_adapter_projection("COMPLETED", "completed", success=True), "extra": True},
            {
                key: value
                for key, value in _adapter_projection(
                    "COMPLETED", "completed", success=True
                ).items()
                if key != "reason"
            },
            {
                **_adapter_projection("COMPLETED", "completed", success=True),
                "reason": "Bearer sk-secret-must-not-escape",
            },
            {
                **_adapter_projection("COMPLETED", "completed", success=True),
                "replayed": 1,
            },
        ],
    )
    async def test_malformed_provider_projection_never_finalizes_success(
        self, mock_dae, projection
    ):
        """Truthy and malformed adapter projections fail closed without content."""
        from modules.infrastructure.idle_automation.src.idle_automation_dae import (
            IdleAutomationDAE,
        )

        claim = _schedule_claim()
        spec = MagicMock(
            id=claim.schedule_id,
            routine=claim.routine,
            cadence=claim.cadence,
        )
        evaluator = MagicMock()
        evaluator.claim_schedule.return_value = claim
        evaluator.finalize_claim.return_value = True
        mock_dae._dispatch_openrouter_catalog_claim = AsyncMock(
            return_value=projection
        )
        result = IdleAutomationDAE._scheduled_routines_result()

        continued = await IdleAutomationDAE._claim_and_dispatch(
            mock_dae, evaluator, spec, result
        )

        assert continued is True
        evaluator.finalize_claim.assert_called_once_with(
            claim.token,
            success=False,
            outcome_code="routine_failed",
        )
        evaluator.record_execution.assert_not_called()
        assert result["failed_count"] == 1
        encoded = json.dumps(result)
        assert "secret" not in encoded
        assert "Bearer" not in encoded
        assert "forged" not in encoded

    @pytest.mark.asyncio
    async def test_openrouter_schedule_claim_dispatch_finalize_concatenation(
        self, mock_dae, tmp_path, monkeypatch
    ):
        """The parser-owned ID survives real claim, dispatch, and finalization."""
        from modules.infrastructure.idle_automation.src import schedule_evaluator
        from modules.infrastructure.idle_automation.src.idle_automation_dae import (
            IdleAutomationDAE,
        )

        now = datetime(2026, 7, 24, 12, tzinfo=UTC)
        monkeypatch.setattr(schedule_evaluator, "utc_now", lambda: now)
        repo = tmp_path / "repo"
        repo.mkdir()
        evaluator = ScheduleEvaluator(
            schedules_path=repo / "memory" / "schedules.json",
            repo_root=repo,
            runtime_root=tmp_path / "claim-runtime",
        )
        spec = evaluator.add_schedule("run openrouter catalog refresh daily")
        assert spec is not None
        assert spec.id == "e324884d66c4"
        mock_dae._dispatch_openrouter_catalog_claim = AsyncMock(
            return_value=_adapter_projection(
                "COMPLETED", "completed", success=True
            )
        )
        result = IdleAutomationDAE._scheduled_routines_result()

        continued = await IdleAutomationDAE._claim_and_dispatch(
            mock_dae, evaluator, spec, result
        )

        assert continued is True
        claim = mock_dae._dispatch_openrouter_catalog_claim.await_args.args[0]
        assert type(claim) is ScheduleClaim
        assert claim.schedule_id == spec.id
        assert claim.routine == "openrouter_catalog_refresh"
        assert claim.cadence == "daily"
        assert result["executed_count"] == 1
        assert result["failed_count"] == 0
        assert evaluator.get_schedule(spec.id).last_result.startswith("success:")

    @pytest.mark.asyncio
    async def test_provider_cancellation_leaves_claim_unfinalized(
        self, mock_dae
    ):
        """Cancellation preserves the leased claim for expiry/replay recovery."""
        from modules.infrastructure.idle_automation.src.idle_automation_dae import (
            IdleAutomationDAE,
        )

        claim = _schedule_claim()
        spec = MagicMock(
            id=claim.schedule_id,
            routine=claim.routine,
            cadence=claim.cadence,
        )
        evaluator = MagicMock()
        evaluator.claim_schedule.return_value = claim
        mock_dae._dispatch_openrouter_catalog_claim = AsyncMock(
            side_effect=asyncio.CancelledError
        )
        result = IdleAutomationDAE._scheduled_routines_result()

        with pytest.raises(asyncio.CancelledError):
            await IdleAutomationDAE._claim_and_dispatch(
                mock_dae, evaluator, spec, result
            )

        evaluator.finalize_claim.assert_not_called()
        evaluator.record_execution.assert_not_called()

    @pytest.mark.asyncio
    async def test_provider_finalize_failure_keeps_legacy_last_run_untouched(
        self, mock_dae
    ):
        """Completion without durable token finalization remains unknown."""
        from modules.infrastructure.idle_automation.src.idle_automation_dae import (
            IdleAutomationDAE,
        )

        claim = _schedule_claim()
        spec = MagicMock(
            id=claim.schedule_id,
            routine=claim.routine,
            cadence=claim.cadence,
        )
        evaluator = MagicMock()
        evaluator.claim_schedule.return_value = claim
        evaluator.finalize_claim.return_value = False
        mock_dae._dispatch_openrouter_catalog_claim = AsyncMock(
            return_value=_adapter_projection(
                "COMPLETED", "completed", success=True
            )
        )
        result = IdleAutomationDAE._scheduled_routines_result()

        continued = await IdleAutomationDAE._claim_and_dispatch(
            mock_dae, evaluator, spec, result
        )

        assert continued is False
        evaluator.finalize_claim.assert_called_once_with(
            claim.token,
            success=True,
            outcome_code="success",
        )
        evaluator.record_execution.assert_not_called()
        assert result["finalization_failed_count"] == 1


class TestDispatchScheduledRoutine:
    """Test individual routine dispatch."""

    @pytest.fixture
    def mock_dae(self, tmp_path):
        """Create a mock DAE for dispatch testing."""
        from modules.infrastructure.idle_automation.src.idle_automation_dae import (
            IdleAutomationDAE,
        )

        with patch.object(IdleAutomationDAE, "__init__", lambda self: None):
            dae = IdleAutomationDAE()
            dae.module_path = tmp_path
            dae.config = {"self_research_timeout": 300}
            return dae

    @pytest.mark.asyncio
    async def test_dispatch_self_research(self, mock_dae):
        """self_research routine calls _execute_self_research_refresh."""
        from modules.infrastructure.idle_automation.src.idle_automation_dae import (
            IdleAutomationDAE,
        )

        mock_dae._execute_self_research_refresh = AsyncMock(
            return_value={
                "success": True,
                "update_candidates": 3,
                "autonomous_tasks": 1,
            }
        )

        result = await IdleAutomationDAE._dispatch_scheduled_routine(
            mock_dae, "self_research"
        )

        assert result["success"] is True
        assert "3 candidates" in result["summary"]
        mock_dae._execute_self_research_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_dispatch_grant_watchlist(self, mock_dae):
        """grant_watchlist routine calls refresh_grant_watchlist."""
        from modules.infrastructure.idle_automation.src.idle_automation_dae import (
            IdleAutomationDAE,
        )

        # Mock the refresher with proper method using correct status keys
        mock_refresher = MagicMock()
        mock_refresher.refresh_grant_watchlist.return_value = {
            "refresh_success": True,
            "status": {
                "watch_count": 15,
                "changed_count": 3,
                "error_count": 1,
            },
        }

        with patch(
            "modules.infrastructure.idle_automation.src.self_research_refresh.SelfResearchRefresher",
            return_value=mock_refresher,
        ):
            result = await IdleAutomationDAE._dispatch_scheduled_routine(
                mock_dae, "grant_watchlist"
            )

        assert result["success"] is True
        assert "15 watched" in result["summary"]
        assert "3 changed" in result["summary"]

    @pytest.mark.asyncio
    async def test_dispatch_unknown_routine(self, mock_dae):
        """Unknown routine returns error."""
        from modules.infrastructure.idle_automation.src.idle_automation_dae import (
            IdleAutomationDAE,
        )

        result = await IdleAutomationDAE._dispatch_scheduled_routine(
            mock_dae, "unknown_routine"
        )

        assert result["success"] is False
        assert "unknown" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_claimed_legacy_routine_keeps_native_string_dispatch(
        self, mock_dae
    ):
        """Full claims enter once, but legacy native dispatch stays unchanged."""
        from modules.infrastructure.idle_automation.src.idle_automation_dae import (
            IdleAutomationDAE,
        )

        claim = _schedule_claim(routine="self_research")
        mock_dae._dispatch_scheduled_routine = AsyncMock(
            return_value={"success": True}
        )

        result = await IdleAutomationDAE._dispatch_claimed_routine(
            mock_dae, claim
        )

        assert result["success"] is True
        mock_dae._dispatch_scheduled_routine.assert_awaited_once_with(
            "self_research"
        )

    @pytest.mark.asyncio
    async def test_claimed_provider_routine_uses_exact_final_boundary(
        self, mock_dae
    ):
        """Provider claims never fall through the legacy routine dispatcher."""
        from modules.infrastructure.idle_automation.src.idle_automation_dae import (
            IdleAutomationDAE,
        )

        claim = _schedule_claim()
        mock_dae._dispatch_openrouter_catalog_claim = AsyncMock(
            return_value={
                "success": False,
                "status": "BLOCKED_PRECALL",
                "reason": "refresh_disabled",
                "replayed": False,
                "receipt_id": None,
                "candidate_snapshot_id": None,
            }
        )
        mock_dae._dispatch_scheduled_routine = AsyncMock(
            return_value={
                "success": False,
                "error": "legacy path used",
            }
        )

        result = await IdleAutomationDAE._dispatch_claimed_routine(
            mock_dae, claim
        )

        assert result == {
            "success": False,
            "outcome": "routine_failed",
            "error": "Provider catalog refresh failed",
        }
        mock_dae._dispatch_openrouter_catalog_claim.assert_awaited_once_with(
            claim
        )
        mock_dae._dispatch_scheduled_routine.assert_not_awaited()


class TestGetScheduledRoutinesStatus:
    """Test status reporting for scheduled routines."""

    @pytest.fixture
    def temp_memory_path(self, tmp_path):
        """Create temporary memory directory."""
        memory_dir = tmp_path / "memory"
        memory_dir.mkdir()
        return memory_dir

    def test_status_with_no_schedules(self, temp_memory_path):
        """Status reports empty when no schedules exist."""
        from modules.infrastructure.idle_automation.src.idle_automation_dae import (
            IdleAutomationDAE,
        )

        schedules_path = temp_memory_path / "schedules.json"
        mock_evaluator = ScheduleEvaluator(schedules_path=schedules_path)

        with patch.object(IdleAutomationDAE, "__init__", lambda self: None):
            dae = IdleAutomationDAE()
            dae.module_path = temp_memory_path.parent
            dae.memory_path = temp_memory_path

            with patch(
                "modules.infrastructure.idle_automation.src.schedule_evaluator.ScheduleEvaluator",
                return_value=mock_evaluator,
            ):
                status = IdleAutomationDAE._get_scheduled_routines_status(dae)

            assert status["total_count"] == 0
            assert status["due_count"] == 0

    def test_status_with_schedules(self, temp_memory_path):
        """Status reports schedules correctly."""
        from modules.infrastructure.idle_automation.src.idle_automation_dae import (
            IdleAutomationDAE,
        )

        # Create schedules
        schedules_path = temp_memory_path / "schedules.json"
        evaluator = ScheduleEvaluator(schedules_path=schedules_path)
        evaluator.add_schedule("run self research daily")
        evaluator.add_schedule("run queue audit nightly")

        with patch.object(IdleAutomationDAE, "__init__", lambda self: None):
            dae = IdleAutomationDAE()
            dae.module_path = temp_memory_path.parent
            dae.memory_path = temp_memory_path

            with patch(
                "modules.infrastructure.idle_automation.src.schedule_evaluator.ScheduleEvaluator",
                return_value=evaluator,
            ):
                status = IdleAutomationDAE._get_scheduled_routines_status(dae)

            assert status["total_count"] == 2
            assert status["enabled_count"] == 2
            assert len(status["schedules"]) == 2


class TestPartialFailureReporting:
    """Test that partial failures are correctly reported."""

    @pytest.fixture
    def temp_memory_path(self, tmp_path):
        """Create temporary memory directory."""
        memory_dir = tmp_path / "memory"
        memory_dir.mkdir()
        return memory_dir

    @pytest.mark.asyncio
    async def test_one_failure_makes_overall_success_false(self, temp_memory_path):
        """If any due routine fails, overall success should be False."""
        from modules.infrastructure.idle_automation.src.idle_automation_dae import (
            IdleAutomationDAE,
        )

        # Create two schedules
        schedules_path = temp_memory_path / "schedules.json"
        evaluator = ScheduleEvaluator(schedules_path=schedules_path)
        evaluator.add_schedule("run self research daily")
        evaluator.add_schedule("run grant watchlist daily")

        with patch.object(IdleAutomationDAE, "__init__", lambda self: None):
            dae = IdleAutomationDAE()
            dae.module_path = temp_memory_path.parent
            dae.memory_path = temp_memory_path
            dae.idle_state = {}
            dae._parse_bool_env = lambda key, default: default
            dae._save_idle_state = MagicMock()

            # self_research succeeds, grant_watchlist fails
            dae._execute_self_research_refresh = AsyncMock(
                return_value={"success": True, "update_candidates": 1, "autonomous_tasks": 0}
            )
            dae._run_grant_watchlist_refresh = AsyncMock(
                return_value={"success": False, "error": "test failure"}
            )

            with patch(
                "modules.infrastructure.idle_automation.src.schedule_evaluator.ScheduleEvaluator",
                return_value=evaluator,
            ):
                result = await IdleAutomationDAE._execute_scheduled_routines(dae)

            # Overall success should be False because one routine failed
            assert result["success"] is False
            assert result["failed_count"] == 1
            assert result["executed_count"] == 1


class TestDuplicateRerunPrevention:
    """Test that duplicate immediate reruns are prevented."""

    @pytest.fixture
    def temp_memory_path(self, tmp_path):
        """Create temporary memory directory."""
        memory_dir = tmp_path / "memory"
        memory_dir.mkdir()
        return memory_dir

    @pytest.mark.asyncio
    async def test_second_run_same_window_skipped(self, temp_memory_path):
        """A schedule that just ran is not due again in same window."""
        from modules.infrastructure.idle_automation.src.idle_automation_dae import (
            IdleAutomationDAE,
        )

        # Create a schedule
        schedules_path = temp_memory_path / "schedules.json"
        evaluator = ScheduleEvaluator(schedules_path=schedules_path)
        spec = evaluator.add_schedule("run self research daily")

        # First run - should execute
        with patch.object(IdleAutomationDAE, "__init__", lambda self: None):
            dae = IdleAutomationDAE()
            dae.module_path = temp_memory_path.parent
            dae.memory_path = temp_memory_path
            dae.idle_state = {}
            dae._parse_bool_env = lambda key, default: default
            dae._save_idle_state = MagicMock()
            dae._execute_self_research_refresh = AsyncMock(
                return_value={"success": True, "update_candidates": 1, "autonomous_tasks": 0}
            )

            with patch(
                "modules.infrastructure.idle_automation.src.schedule_evaluator.ScheduleEvaluator",
                return_value=evaluator,
            ):
                result1 = await IdleAutomationDAE._execute_scheduled_routines(dae)
                assert result1["executed_count"] == 1

                # Second run immediately after - should skip (evaluator state persisted)
                result2 = await IdleAutomationDAE._execute_scheduled_routines(dae)
                assert result2["due_count"] == 0
                assert result2["executed_count"] == 0
