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
from modules.communication.moltbot_bridge.src.reddog_main_resident_queue_serial_loop_bootstrap import (
    run_reddog_main_resident_queue_serial_loop_bootstrap,
)
from modules.communication.moltbot_bridge.tests.test_reddog_architect_fix_signed_wsp15_work_order_promotion import (
    _authority_profile,
    _promote,
)
from modules.communication.moltbot_bridge.tests.test_reddog_main_resident_queue_serial_loop_bootstrap import (
    NOW,
    _profile,
    _repo,
    _snapshot,
    _write_runtime_json,
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


def test_runtime_profile_accepts_exact_slice_verifier_plan_schema() -> None:
    profile = _authority_profile()
    profile["slice_verifier_plan"] = {
        "slice_name": "REDDOG_TEST_SLICE_PHASE1",
        "worker_id": "worker:author",
        "verifier_id": "worker:verifier",
        "base_sha": "b" * 40,
        "head_sha": "a" * 40,
        "allowed_path_patterns": ["modules/foundups/test/**"],
        "expected_changed_paths": ["modules/foundups/test/README.md"],
        "forbidden_path_patterns": ["**/.env"],
        "required_checks": [{"name": "pytest", "argv": ["pytest", "-q"], "timeout_s": 30}],
        "signed_receipt_chain": {"accepted": True, "terminal_receipt_hash": "sha256:" + "a" * 64},
    }

    assert authority_profile_runtime_unknown_field_paths(profile) == ()
    assert rehydrate_authority_profile_runtime(profile) == profile


def test_runtime_profile_rejects_unknown_slice_verifier_check_field() -> None:
    profile = _authority_profile()
    profile["slice_verifier_plan"] = {
        "required_checks": [{"name": "pytest", "argv": ["pytest"], "timeout_s": 30, "shell": True}],
    }

    assert authority_profile_runtime_unknown_field_paths(profile) == (
        "slice_verifier_plan.required_checks[0].shell",
    )


def test_runtime_profile_accepts_env_names_but_rejects_secret_values() -> None:
    profile = _authority_profile()
    profile["bounded_worker_plan"] = {
        "shell_profile": {"secret_env_refs": ["OPENROUTER_API_KEY"]},
    }

    assert rehydrate_authority_profile_runtime(profile) == profile

    profile["bounded_worker_plan"]["shell_profile"]["secret_env_refs"] = [
        "sk-attacker-value",
    ]
    with pytest.raises(ValueError, match="secret_env_refs"):
        rehydrate_authority_profile_runtime(profile)


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
        ("denied_paths", None),
        ("consensus_receipt_digest", "not-a-digest"),
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
        ("denied_paths", None),
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


@pytest.mark.parametrize(
    "path",
    (
        ("proposal_admission", "no_execution_performed"),
        ("proposal_admission", "no_queue_mutation_performed"),
        ("wsp15_allocation_receipt", "no_model_call_performed"),
    ),
)
def test_runtime_rehydration_rejects_false_nested_no_effect_claim(
    path: tuple[str, str],
) -> None:
    promoted, _ = _promote()
    assert promoted.accepted is True
    profile = json.loads(json.dumps(promoted.authority_profile))
    profile[path[0]][path[1]] = False

    with pytest.raises(ValueError, match="authority_profile_invalid"):
        rehydrate_authority_profile_runtime(profile)


def test_runtime_rehydration_rejects_malformed_profile_digest() -> None:
    profile = _authority_profile()
    profile["consensus_receipt_digest"] = "not-a-digest"

    with pytest.raises(ValueError, match="authority_profile_invalid"):
        rehydrate_authority_profile_runtime(profile)


def test_runtime_rehydration_rejects_malformed_panel_topology_digest() -> None:
    promoted, _ = _promote()
    profile = json.loads(json.dumps(promoted.authority_profile))
    profile["model_selection_receipt"]["panel_topology_digest"] = "panel_topology:short"

    with pytest.raises(ValueError, match="authority_profile_invalid"):
        rehydrate_authority_profile_runtime(profile)


def test_queue_bootstrap_rejects_null_widened_profile_without_effects(
    tmp_path,
) -> None:
    repo = _repo(tmp_path)
    state = _write_runtime_json(tmp_path, "work_state.json", _snapshot())
    before = state.read_bytes()
    profile_payload = _profile()
    profile_payload["denied_paths"] = None
    profile = _write_runtime_json(tmp_path, "profile.json", profile_payload)
    chain = tmp_path / "runtime" / "chain_results.json"

    result = run_reddog_main_resident_queue_serial_loop_bootstrap(
        repo_root=repo, runtime_allowed_root=tmp_path / "runtime",
        work_state_path=state, chain_results_path=chain,
        authority_profile_path=profile,
        work_order_materializer_mode="authority_profile", now_iso=NOW,
    )

    assert result.accepted is False
    assert result.rejection_reasons == ("malformed_authority_profile",)
    assert state.read_bytes() == before
    assert not chain.exists()


def test_live_canary_reader_rejects_typed_profile_confusion(tmp_path) -> None:
    profile = _authority_profile()
    profile["allowed_paths"] = {"attacker_extra": "value"}
    (tmp_path / "authority_profile.json").write_text(
        json.dumps(profile), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="authority_profile_invalid"):
        _runtime_authority_profile(tmp_path)
