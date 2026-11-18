"""Grounding-to-WSP 15 ordering regression for the resident bootstrap."""

from modules.communication.moltbot_bridge.src.reddog_main_readonly_operational_bootstrap import run_reddog_main_readonly_operational_bootstrap
from modules.communication.moltbot_bridge.tests.grounding_v2_test_helpers import exact_head_repo_target_grounding_receipt
from modules.communication.moltbot_bridge.tests.test_reddog_main_readonly_operational_bootstrap import NOW, REPO_ROOT, _fresh_holo_receipt, _repo_state, _work_state


def test_grounded_repo_target_is_bound_before_wsp15_allocation() -> None:
    target = "holo_index/adaptive_learning/breadcrumb_tracer.py"
    focus = f"Read first: {target}"
    grounding = exact_head_repo_target_grounding_receipt(
        repo_root=REPO_ROOT, work_focus=focus, repo_target=target,
    )
    result = run_reddog_main_readonly_operational_bootstrap(
        repo_root=REPO_ROOT, repo_state_override=_repo_state(),
        work_state_snapshot_override=_work_state(),
        holoindex_receipt_override=_fresh_holo_receipt(),
        grounding_receipt=grounding, grounding_work_focus=focus, now_iso=NOW,
    )
    assert result.ready is True
    assert target in result.allowed_read_targets
    assert tuple(result.wsp15_allocation_receipt["allowed_read_targets"]) == result.allowed_read_targets
