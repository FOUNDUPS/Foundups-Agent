"""Focused authority-profile slice-verifier plan materialization tests."""

from modules.communication.moltbot_bridge.src.reddog_main_resident_queue_serial_loop_bootstrap import (
    _materialize_work_orders_from_authority_profile,
)
from modules.communication.moltbot_bridge.tests.test_reddog_main_resident_queue_serial_loop_bootstrap import (
    NOW,
    WORK_ORDER_ID,
    _profile,
    _slice_verifier_plan,
    _snapshot,
)


def _materialize(profile):
    return _materialize_work_orders_from_authority_profile(
        snapshot=_snapshot(),
        authority_profile=profile,
        requested_queue_item_id="queue-1",
        now_iso=NOW,
    )


def test_materializer_carries_existing_slice_verifier_plan() -> None:
    plan = _slice_verifier_plan()

    work_orders, reasons = _materialize(_profile(slice_verifier_plan=plan))

    assert reasons == ()
    assert work_orders is not None
    assert work_orders[WORK_ORDER_ID]["slice_verifier_plan"] == plan


def test_materializer_rejects_non_mapping_slice_verifier_plan() -> None:
    work_orders, reasons = _materialize(_profile(slice_verifier_plan="forged"))

    assert work_orders is None
    assert reasons == ("work_order_materializer_slice_verifier_plan_invalid:type",)


def test_materializer_rejects_non_ascii_slice_verifier_plan() -> None:
    plan = _slice_verifier_plan()
    plan["slice_name"] = "invalid-\u2603"

    work_orders, reasons = _materialize(_profile(slice_verifier_plan=plan))

    assert work_orders is None
    assert reasons == ("work_order_materializer_authority:FAIL_PROFILE_NON_ASCII",)
