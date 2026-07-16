"""Tests for REDDOG_MAIN_OPENCLAW_SIGNED_WORKER_CLAIM_LOOP_PREFLIGHT_PHASE1."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[4]
CLAIM_LOOP = (
    "modules.communication.moltbot_bridge.src.openclaw_supervisor."
    "claim_reddog_signed_worker_dispatch_tasks_until_idle"
)


def test_main_openclaw_signed_worker_claim_loop_disabled_by_default() -> None:
    import main

    with patch(CLAIM_LOOP, side_effect=AssertionError("claim loop must not run")):
        with patch.dict("os.environ", {}, clear=True):
            assert main.run_reddog_openclaw_signed_worker_claim_loop_preflight(REPO_ROOT) is True


def test_main_openclaw_signed_worker_claim_loop_passes_when_idle(capsys) -> None:
    import main

    with patch(
        CLAIM_LOOP,
        return_value={
            "accepted": True,
            "status": "SIGNED_WORKER_OPENCLAW_CLAIM_LOOP_IDLE",
            "claimed_count": 0,
            "completed_task_ids": (),
            "requeued_task_ids": (),
            "failed_task_ids": (),
            "rejection_reasons": ("NO_PENDING_TASK",),
        },
    ) as mocked:
        with patch.dict(
            "os.environ",
            {
                "REDDOG_OPENCLAW_SIGNED_WORKER_CLAIM_LOOP": "1",
                "OPENCLAW_SIGNED_WORKER_TASK_MAX_CLAIMS": "3",
            },
            clear=True,
        ):
            assert main.run_reddog_openclaw_signed_worker_claim_loop_preflight(REPO_ROOT) is True

    assert mocked.call_args.kwargs["repo_root"] == REPO_ROOT
    assert mocked.call_args.kwargs["max_claims"] == 3
    captured = capsys.readouterr().out
    assert "[REDDOG-OPENCLAW-CLAIM-LOOP] preflight=PASS" in captured
    assert "claimed_count=0" in captured
    assert "max_claims=3" in captured


def test_main_openclaw_signed_worker_claim_loop_blocks_when_enforced() -> None:
    import main

    with patch(
        CLAIM_LOOP,
        return_value={
            "accepted": False,
            "status": "SIGNED_WORKER_OPENCLAW_CLAIM_LOOP_REJECT",
            "claimed_count": 0,
            "completed_task_ids": (),
            "requeued_task_ids": (),
            "failed_task_ids": ("task-1",),
            "rejection_reasons": ("CLAIM_REJECTED",),
        },
    ):
        with patch.dict(
            "os.environ",
            {
                "REDDOG_OPENCLAW_SIGNED_WORKER_CLAIM_LOOP": "1",
                "REDDOG_OPENCLAW_SIGNED_WORKER_CLAIM_LOOP_ENFORCED": "1",
            },
            clear=True,
        ):
            assert main.run_reddog_openclaw_signed_worker_claim_loop_preflight(REPO_ROOT) is False


def test_main_openclaw_signed_worker_claim_loop_rejects_invalid_max_claims_when_enforced() -> None:
    import main

    with patch(CLAIM_LOOP, side_effect=AssertionError("claim loop must not run")):
        with patch.dict(
            "os.environ",
            {
                "REDDOG_OPENCLAW_SIGNED_WORKER_CLAIM_LOOP": "1",
                "REDDOG_OPENCLAW_SIGNED_WORKER_CLAIM_LOOP_ENFORCED": "1",
                "OPENCLAW_SIGNED_WORKER_TASK_MAX_CLAIMS": "0",
            },
            clear=True,
        ):
            assert main.run_reddog_openclaw_signed_worker_claim_loop_preflight(REPO_ROOT) is False


def test_main_openclaw_signed_worker_claim_loop_exception_is_nonblocking_by_default() -> None:
    import main

    with patch(CLAIM_LOOP, side_effect=RuntimeError("agentdb unavailable")):
        with patch.dict(
            "os.environ",
            {"REDDOG_OPENCLAW_SIGNED_WORKER_CLAIM_LOOP": "1"},
            clear=True,
        ):
            assert main.run_reddog_openclaw_signed_worker_claim_loop_preflight(REPO_ROOT) is True
