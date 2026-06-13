# -*- coding: utf-8 -*-
"""GetK monorepo-PoC dry-run PROOF (W6).

Slice: GETK_FOUNDUP_MONOREPO_POC_BOOTSTRAP_PHASE1

Proves the NEW FoundUp ``getk`` routes through the EXISTING OpenClaw/WRE
create+drain dry-run seam -- the same path exercised by
test_operational_wre_monorepo_poc_vertical_proof.py for gotjunk_001. This is a
PROOF that reuses the path AS-IS; it adds NO production code and NO new wiring.

  REAL CREATE: orchestrator.dispatch_foundup(None, "validate foundup getk --dry-run")
               -> create_job(validate_foundup, foundup_id="getk") -> queue
  REAL DRAIN : FoundUpJobConsumer.drain_openclaw_queue_with_retention()
               -> consume -> dispatch -> hermes executor (SIMULATED)
               -> ContextBundle dry-run, resolver derives module_path from the
                  validated getk manifest (payload carries none).

Boundary: HERMES_DELEGATE_ENABLED unset (dry-run branch only); the only mocks
are the real-execution sinks, asserted not-called through the full seam. The
seam itself is never mocked. No network, no real execution.
"""

from __future__ import annotations

import tempfile
import types
from unittest import mock

import pytest

from modules.communication.moltbot_bridge.src import (
    openclaw_foundup_orchestrator as orchestrator,
)
from modules.infrastructure.wre_core.src import hermes_job_executor as hje
from modules.infrastructure.wre_core.src.foundup_job_consumer import (
    ConsumerResult,
    FoundUpJobConsumer,
)

GETK_FOUNDUP_ID = "getk"
GETK_MODULE_PATH = "modules/foundups/getk"


@pytest.fixture(autouse=True)
def _dry_run_branch_and_isolated_workspace(monkeypatch):
    monkeypatch.delenv("HERMES_DELEGATE_ENABLED", raising=False)
    tmp_ws = tempfile.mkdtemp(prefix="w6_getk_proof_")
    monkeypatch.setenv("FOUNDUPS_WORKSPACE_ROOT", tmp_ws)
    monkeypatch.setattr(hje, "_executor_singleton", None, raising=False)
    orchestrator.clear_job_queue()
    yield
    orchestrator.clear_job_queue()
    monkeypatch.setattr(hje, "_executor_singleton", None, raising=False)


def _intent(foundup_id):
    return types.SimpleNamespace(
        raw_message=f"validate foundup {foundup_id} --dry-run",
        sender="tenant_w6",
        session_key="w6_getk_session",
        channel="w6_getk_channel",
    )


class TestGetKReachesDryRunSimulated:
    def test_validate_getk_reaches_simulated(self):
        """validate_foundup for getk reaches the SIMULATED dry-run branch."""
        from modules.communication.moltbot_bridge.src.foundup_job_contract import (
            create_job,
        )
        job = create_job(
            tenant_id="tenant_w6",
            requested_action="validate_foundup",
            foundup_id=GETK_FOUNDUP_ID,
            payload={},
        )
        assert hje.execute_foundup_job(job).status.value == "SIMULATED"


class TestGetKMonorepoPoCDryRunProof:
    def test_getk_full_dry_run_through_existing_seam(self):
        with mock.patch("subprocess.Popen") as m_popen, \
                mock.patch("subprocess.run") as m_run, \
                mock.patch("subprocess.call") as m_call, \
                mock.patch(
                    "modules.infrastructure.wre_core.src.hermes_job_executor."
                    "HermesJobExecutor._lazy_import_delegate_task",
                    side_effect=AssertionError("real delegate must not run"),
                ) as m_delegate:

            # REAL create entry over the OpenClaw queue.
            response = orchestrator.dispatch_foundup(None, _intent(GETK_FOUNDUP_ID))
            assert "FoundUpJob created" in response
            queue = orchestrator.get_job_queue()
            assert len(queue) == 1
            job = queue[0]
            assert job.requested_action == "validate_foundup"
            assert job.foundup_id == GETK_FOUNDUP_ID
            assert job.policy_flags.dry_run_mode is True
            # Create entry carries no module_path -> resolver must derive it.
            assert "module_path" not in job.payload

            # REAL drain entry over the same queue.
            consumer = FoundUpJobConsumer(dry_run=True)
            drain = consumer.drain_openclaw_queue_with_retention(clear=False)
            assert len(drain.results) == 1
            result = drain.results[0]

            m_popen.assert_not_called()
            m_run.assert_not_called()
            m_call.assert_not_called()
            m_delegate.assert_not_called()

        assert isinstance(result, ConsumerResult)
        assert result.checkpoint_state == "SIMULATED"
        assert result.real_execution_performed is False

        cb = result.context_bundle_dry_run
        assert cb is not None
        # GetK manifest resolves cleanly through the shared validated resolver.
        assert "context_bundle_error" not in cb
        assert cb["dry_run"] is True
        assert cb["real_execution_performed"] is False
        assert cb["source_authority"] == "monorepo_poc"
        assert cb["resolved_module_path"] == GETK_MODULE_PATH

        # Readiness stays false; existing WSP 97 truth fields stay false.
        for name, value in cb["readiness_flags"].items():
            assert value is False, f"readiness promoted: {name}"
        receipt = result.to_dict()
        assert receipt["verification_complete"] is False
        assert receipt["cabr_ready"] is False
        assert receipt["payout_ready"] is False
        assert receipt["context_bundle_dry_run"]["source_authority"] == "monorepo_poc"
