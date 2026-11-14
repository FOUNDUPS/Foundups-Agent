"""Focused model-runtime bootstrap integration for architect FIX promotion."""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_verified_admission import (
    verified_runtime_binding_receipt,
)
from modules.communication.moltbot_bridge.src.reddog_main_architect_fix_promotion_bootstrap import (
    run_reddog_main_architect_fix_promotion_bootstrap,
)
from modules.communication.moltbot_bridge.tests.architect_proposal_test_helpers import (
    ready_proposal_policy,
)
from modules.communication.moltbot_bridge.tests.architect_proposal_promotion_test_helpers import (
    build_proposal_runtime_inputs,
)
from modules.communication.moltbot_bridge.tests.model_runtime_binding_receipt_test_helpers import (
    model_runtime_binding_test_capability,
    model_selection_and_runtime_binding_receipts,
)
from modules.communication.moltbot_bridge.tests.test_reddog_main_architect_fix_promotion_bootstrap import (
    NOW,
    _repo,
    _runtime_files,
)
from modules.communication.moltbot_bridge.tests.test_reddog_architect_fix_promotion_exact_schema import (
    _plan_profile,
)
from modules.communication.moltbot_bridge.tests.test_reddog_authority_profile_seed_supply import (
    _plan_bound_determination,
)
from modules.communication.moltbot_bridge.src import (
    reddog_main_architect_fix_promotion_preparation as preparation,
)


@pytest.fixture(autouse=True)
def _current_holo_owner_binding(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "modules.communication.moltbot_bridge.src."
        "reddog_main_architect_fix_promotion_bootstrap.resolve_query_replica_owner_route",
        lambda **_kwargs: object(),
    )
    monkeypatch.setattr(
        "modules.communication.moltbot_bridge.src."
        "reddog_main_architect_fix_promotion_bootstrap.verify_reddog_holoindex_owner_binding",
        lambda **_kwargs: True,
    )


def test_bootstrap_forwards_runtime_binding_receipt_into_promotion(tmp_path: Path) -> None:
    repo, files = _repo(tmp_path), _runtime_files(tmp_path)
    selection, binding = model_selection_and_runtime_binding_receipts(
        runtime_surface="reddog_artifact_generation",
        task_family="reddog_architect_fix_promotion",
    )
    files["model_selection"].write_text(json.dumps(selection, sort_keys=True), encoding="utf-8")
    files["model_runtime_binding"].write_text(json.dumps(binding, sort_keys=True), encoding="utf-8")
    verification = verified_runtime_binding_receipt(binding)
    assert verification is not None
    capability = model_runtime_binding_test_capability(selection, binding)
    determination = json.loads(files["determination"].read_text(encoding="utf-8"))
    authority_profile = json.loads(files["authority_profile_source"].read_text(encoding="utf-8"))
    memex_supply = json.loads(files["memex_supply"].read_text(encoding="utf-8"))
    attestation, signer_config, key_resolver = build_proposal_runtime_inputs(
        determination,
        authority_profile,
        memex_supply,
        now_epoch=int(datetime.fromisoformat(NOW).timestamp()),
    )
    with (
        patch(
            "modules.communication.moltbot_bridge.src."
            "reddog_main_architect_fix_promotion_bootstrap.read_git_head_sha",
            return_value="sha256:repo-head",
        ),
        patch(
            "modules.communication.moltbot_bridge.src."
            "reddog_architect_proposal_admission_contract.current_architect_proposal_admission_policy",
            return_value=ready_proposal_policy(),
        ),
    ):
        result = run_reddog_main_architect_fix_promotion_bootstrap(
            repo_root=repo, runtime_root=tmp_path / "runtime",
            work_state_path=files["work_state"], architect_determination_path=files["determination"],
            model_selection_receipt_path=files["model_selection"],
            model_runtime_binding_receipt_path=files["model_runtime_binding"],
            model_runtime_binding_verification_capability=capability,
            proposal_authenticity_attestation=attestation,
            signer_runtime_config=signer_config,
            principal_key_resolver=key_resolver,
            memex_supply_receipt_path=files["memex_supply"],
            authority_profile_source_path=files["authority_profile_source"],
            authority_profile_output_path=files["authority_profile_output"],
            holoindex_receipt_path=files["holoindex_receipt"],
            worker_id="reddog-main-test", now_iso=NOW,
        )
    assert result.accepted is True, result.rejection_reasons
    profile = json.loads(files["authority_profile_output"].read_text(encoding="utf-8"))
    runtime = json.loads(files["model_runtime_binding"].read_text(encoding="utf-8"))
    assert profile["model_runtime_binding_receipt_id"] == runtime["receipt_id"]
    assert profile["operational_context_binding"]["model_runtime_binding_receipt_id"] == runtime["receipt_id"]


def _bootstrap_inputs(tmp_path, repo, files):
    return dict(
        repo_root=repo, runtime_root=tmp_path / "runtime",
        work_state_path=files["work_state"], architect_determination_path=files["determination"],
        model_selection_receipt_path=files["model_selection"],
        model_runtime_binding_receipt_path=files["model_runtime_binding"],
        memex_supply_receipt_path=files["memex_supply"],
        authority_profile_source_path=files["authority_profile_source"],
        authority_profile_output_path=files["authority_profile_output"],
        holoindex_receipt_path=files["holoindex_receipt"], now_iso=NOW,
    )


def _fixture_runtime_capability(files):
    selection, binding = model_selection_and_runtime_binding_receipts(
        runtime_surface="reddog_artifact_generation",
        task_family="reddog_architect_fix_promotion",
    )
    files["model_selection"].write_text(json.dumps(selection), encoding="utf-8")
    files["model_runtime_binding"].write_text(json.dumps(binding), encoding="utf-8")
    return model_runtime_binding_test_capability(selection, binding)


@pytest.mark.parametrize("kind", ("empty", "m2m"))
@pytest.mark.parametrize("wrapped", (False, True))
def test_bootstrap_preserves_matching_plan_at_all_three_profile_locations(tmp_path, kind, wrapped):
    repo, files = _repo(tmp_path), _runtime_files(tmp_path)
    determination = _plan_bound_determination({} if kind == "empty" else None)
    profile = _plan_profile(determination)
    attestation, config, resolver = build_proposal_runtime_inputs(
        determination, profile, json.loads(files["memex_supply"].read_text()),
        now_epoch=int(datetime.fromisoformat(NOW).timestamp()),
    )
    files["determination"].write_text(
        json.dumps({"receipt": determination} if wrapped else determination), encoding="utf-8",
    )
    files["authority_profile_source"].write_text(json.dumps(profile), encoding="utf-8")
    capability = _fixture_runtime_capability(files)
    with (
        patch("modules.communication.moltbot_bridge.src."
              "reddog_main_architect_fix_promotion_bootstrap.read_git_head_sha",
              return_value="sha256:repo-head"),
        patch("modules.communication.moltbot_bridge.src."
              "reddog_architect_proposal_admission_contract.current_architect_proposal_admission_policy",
              return_value=ready_proposal_policy()),
    ):
        result = run_reddog_main_architect_fix_promotion_bootstrap(
            **_bootstrap_inputs(tmp_path, repo, files),
            model_runtime_binding_verification_capability=capability,
            proposal_authenticity_attestation=attestation,
            signer_runtime_config=config, principal_key_resolver=resolver,
        )
    assert result.accepted is True, result.rejection_reasons
    projected = json.loads(files["authority_profile_output"].read_text())
    expected = profile["bounded_worker_plan"]
    assert projected["bounded_worker_plan"] == expected
    assert projected["proposal_admission"]["bounded_worker_plan"] == expected
    assert projected["operational_context_binding"]["proposal_admission"]["bounded_worker_plan"] == expected


@pytest.mark.parametrize("kind", ("missing", "conflicting", "scope", "null", "stale_receipt"))
def test_bootstrap_plan_rejection_precedes_capability_probe_lock_and_recovery(tmp_path, monkeypatch, kind):
    repo, files = _repo(tmp_path), _runtime_files(tmp_path)
    determination = _plan_bound_determination()
    profile = _plan_profile(determination)
    if kind == "missing":
        del profile["bounded_worker_plan"]
    elif kind == "conflicting":
        profile["bounded_worker_plan"]["m2m_envelope"]["A"] = "Conflicting action"
    elif kind == "scope":
        profile["requested_operation"] = "feature_slice"
    elif kind == "null":
        profile["bounded_worker_plan"] = None
    else:
        determination["proposal_admission"]["receipt_id"] = "sha256:" + "0" * 64
    files["determination"].write_text(json.dumps(determination), encoding="utf-8")
    files["authority_profile_source"].write_text(json.dumps(profile), encoding="utf-8")
    files["authority_profile_output"].write_bytes(b"preserved prior profile")
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}

    def unexpected(*args, **kwargs):
        pytest.fail("runtime operation reached before profile/proposal agreement")

    for name in ("_resolve_runtime_capability", "_probe_atomic_output", "run_locked_promotion"):
        monkeypatch.setattr(preparation, name, unexpected)
    result = run_reddog_main_architect_fix_promotion_bootstrap(
        **_bootstrap_inputs(tmp_path, repo, files),
    )
    assert result.accepted is False
    assert any("AUTHORITY_PROFILE_INCOMPLETE" in reason for reason in result.rejection_reasons)
    assert {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()} == before
