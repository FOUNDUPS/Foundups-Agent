"""Focused integration case extracted from the inherited matrix."""

from __future__ import annotations

from modules.communication.moltbot_bridge.tests.test_reddog_main_resident_queue_serial_loop_bootstrap import (
    Path,
    REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_BOOTSTRAP_APPLIED,
    REPO_ROOT,
    patch,
)


def test_main_serial_loop_preflight_pattern_memory_profile_derives_sink(
    tmp_path: Path,
) -> None:
    import main

    with patch(
        "modules.communication.moltbot_bridge.src.reddog_main_resident_queue_serial_loop_bootstrap.run_reddog_main_resident_queue_serial_loop_bootstrap",
        return_value=type(
            "Result",
            (),
            {
                "accepted": True,
                "status": REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_BOOTSTRAP_APPLIED,
                "queue_item_id": "queue-1",
                "selected_slice": "REDDOG_TEST_SLICE_PHASE1",
                "steps_run": 1,
                "dispatched_stages": ("pattern_memory_admission",),
                "next_action": "STOP_QUEUE_CHAIN_COMPLETE",
                "chain_results_path": str(tmp_path / "chain.json"),
                "store_revision": "sha256:revision",
                "rejection_reasons": (),
            },
        )(),
    ) as mocked:
        with patch.dict(
            "os.environ",
            {
                "REDDOG_RESIDENT_QUEUE_SERIAL_LOOP": "1",
                "REDDOG_RESIDENT_RUNTIME_ROOT": str(tmp_path),
                "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE": (
                    "signed_0102_bounded_code_fusion_worktree_draft_pr_pattern_memory"
                ),
                "REDDOG_AUTHORITATIVE_WORK_STATE_PATH": str(tmp_path / "state.json"),
                "REDDOG_RESIDENT_QUEUE_CHAIN_RESULTS_PATH": str(
                    tmp_path / "chain.json"
                ),
                "REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH": str(
                    tmp_path / "profile.json"
                ),
                "REDDOG_DRAFT_PR_RUNNER_TIMEOUT_S": "92",
            },
            clear=True,
        ):
            assert (
                main.run_reddog_resident_queue_serial_loop_preflight(REPO_ROOT) is True
            )

    assert mocked.call_args.kwargs["artifact_generator_mode"] == "foundups_fusion"
    assert mocked.call_args.kwargs["worktree_runner_mode"] == "real"
    assert mocked.call_args.kwargs["evidence_command_runner_mode"] == "real"
    assert mocked.call_args.kwargs["outcome_ratchet_store_path"] == str(
        tmp_path / "outcome_ratchet" / "verified_outcomes.jsonl"
    )
    assert mocked.call_args.kwargs["model_feedback_ledger_store_path"] == str(
        tmp_path / "model_feedback" / "model_feedback.jsonl"
    )
    sink = mocked.call_args.kwargs["pattern_memory_admission_sink"]
    assert sink is not None
    assert sink.__class__.__name__ == "RedDogVerifiedPatternMemorySink"
    assert str(sink.db_path) == str(tmp_path / "pattern_memory" / "pattern_memory.db")
    assert (
        mocked.call_args.kwargs["draft_pr_runner"].__class__.__name__
        == "RealWorktreeRunner"
    )
    assert mocked.call_args.kwargs["draft_pr_runner"].timeout_s == 92
