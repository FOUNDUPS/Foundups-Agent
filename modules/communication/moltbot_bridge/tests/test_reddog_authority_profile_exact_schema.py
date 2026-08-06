"""Exact nested authority-profile schema regressions."""

from __future__ import annotations

import json
import pytest

from modules.communication.moltbot_bridge.src.reddog_authority_profile_safety import (
    authority_profile_runtime_unknown_field_paths,
)
from modules.communication.moltbot_bridge.src.reddog_authority_profile_rehydration import (
    rehydrate_authority_profile_effect_scope,
    rehydrate_authority_profile_runtime,
    rehydrate_authority_profile_seed,
    rehydrate_authority_profile_source,
)
from modules.communication.moltbot_bridge.src.reddog_resident_live_canary_evidence import (
    _runtime_authority_profile,
)
from modules.communication.moltbot_bridge.tests.test_reddog_architect_fix_signed_wsp15_work_order_promotion import (
    _authority_profile,
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


def test_authority_profile_typed_rehydration_preserves_canonical_source() -> None:
    profile = _authority_profile()

    assert rehydrate_authority_profile_source(profile) == profile
    assert rehydrate_authority_profile_runtime(profile) == profile


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("allowed_paths", {"attacker_extra": "value"}),
        ("denied_paths", ["safe", {"attacker_extra": "value"}]),
        ("required_tests", "pytest tests"),
        ("required_policy_gates", ["WSP_97", 97]),
        ("issued_at", True),
        ("holoindex_evidence", ["not", "a", "mapping"]),
    ),
)
def test_source_rehydration_rejects_type_confusion_without_coercion(
    field: str,
    value: object,
) -> None:
    profile = _authority_profile()
    profile[field] = value

    with pytest.raises(ValueError, match="authority_profile_invalid"):
        rehydrate_authority_profile_source(profile)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("allowed_paths", {"attacker_extra": "value"}),
        ("denied_paths", ["safe", {"attacker_extra": "value"}]),
        ("no_repo_mutation_performed", False),
    ),
)
def test_seed_and_materializer_effect_scope_reject_type_confusion(
    field: str,
    value: object,
) -> None:
    with pytest.raises(ValueError, match="authority_profile_invalid"):
        rehydrate_authority_profile_seed({field: value})
    profile = _authority_profile()
    profile[field] = value
    with pytest.raises(ValueError, match="authority_profile_invalid"):
        rehydrate_authority_profile_effect_scope(profile)


def test_source_rehydration_rejects_present_null_optional_field() -> None:
    profile = _authority_profile()
    profile["owner_dae"] = None

    with pytest.raises(ValueError, match="authority_profile_invalid:owner_dae"):
        rehydrate_authority_profile_source(profile)


def test_live_canary_reader_rejects_typed_profile_confusion(tmp_path) -> None:
    profile = _authority_profile()
    profile["allowed_paths"] = {"attacker_extra": "value"}
    (tmp_path / "authority_profile.json").write_text(
        json.dumps(profile), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="authority_profile_invalid"):
        _runtime_authority_profile(tmp_path)
