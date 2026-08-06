"""Exact nested authority-profile schema regressions."""

from __future__ import annotations

import pytest

from modules.communication.moltbot_bridge.src.reddog_authority_profile_safety import (
    authority_profile_runtime_unknown_field_paths,
)


@pytest.mark.parametrize(
    ("profile", "expected_path"),
    (
        (
            {"operational_context_binding": {"attacker_extra": "value"}},
            "operational_context_binding.attacker_extra",
        ),
        (
            {"model_selection_receipt": {"attacker_extra": "value"}},
            "model_selection_receipt.attacker_extra",
        ),
        (
            {"proposal_admission": {"attacker_extra": "value"}},
            "proposal_admission.attacker_extra",
        ),
        (
            {
                "wsp15_allocation_receipt": {
                    "worker_plan": {"attacker_extra": "value"}
                }
            },
            "wsp15_allocation_receipt.worker_plan.attacker_extra",
        ),
        (
            {
                "model_selection_receipt": {
                    "rankings": [{"attacker_extra": "value"}]
                }
            },
            "model_selection_receipt.rankings[0].attacker_extra",
        ),
        (
            {
                "model_runtime_binding_receipt": {
                    "role_bindings": [{"attacker_extra": "value"}]
                }
            },
            "model_runtime_binding_receipt.role_bindings[0].attacker_extra",
        ),
    ),
)
def test_runtime_profile_rejects_nested_unknown_fields(
    profile: dict[str, object],
    expected_path: str,
) -> None:
    assert authority_profile_runtime_unknown_field_paths(profile) == (
        expected_path,
    )


@pytest.mark.parametrize(
    ("profile", "expected_path"),
    (
        ({"model_selection_receipt": None}, "model_selection_receipt"),
        (
            {"model_selection_receipt": {"rankings": "not-a-sequence"}},
            "model_selection_receipt.rankings",
        ),
        (
            {"model_selection_receipt": {"rankings": ["not-a-mapping"]}},
            "model_selection_receipt.rankings[0]",
        ),
    ),
)
def test_runtime_profile_rejects_malformed_nested_values(
    profile: dict[str, object],
    expected_path: str,
) -> None:
    assert authority_profile_runtime_unknown_field_paths(profile) == (
        expected_path,
    )
