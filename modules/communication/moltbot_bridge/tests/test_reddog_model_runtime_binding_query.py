from __future__ import annotations

import hashlib
import json
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_model_runtime_binding_query import (
    EXPECTED_SURFACE,
    STATUS_NOT_READY,
    STATUS_READY,
    STATUS_UNCONFIGURED,
    query_model_runtime_binding,
)
from modules.communication.moltbot_bridge.tests.model_runtime_binding_receipt_test_helpers import (
    model_runtime_binding_test_verifier,
    model_selection_and_runtime_binding_receipts,
)


def _digest(char: str) -> str:
    return "sha256:" + char * 64


def _valid_inputs() -> tuple[dict, dict]:
    return model_selection_and_runtime_binding_receipts(
        runtime_surface=EXPECTED_SURFACE,
        model_id="openai/gpt-5.6-sol",
        panel_model_ids=("openrouter/deepseek-v4-pro", "openrouter/kimi-k3"),
    )


def _resign(receipt: dict) -> dict:
    body = {
        key: value
        for key, value in receipt.items()
        if key not in {"receipt_id", "verification_receipt"}
    }
    encoded = json.dumps(
        body, sort_keys=True, separators=(",", ":"), default=str
    ).encode("utf-8")
    receipt["receipt_id"] = (
        "reddog_model_runtime_binding:"
        + hashlib.sha256(encoded).hexdigest()
    )
    return receipt


def _configured(runtime_root: Path, artifact: Path, selection: dict) -> dict[str, str]:
    selection_path = runtime_root / "selection.json"
    selection_path.write_text(json.dumps(selection), encoding="utf-8")
    return {
        "REDDOG_RESIDENT_MODEL_RUNTIME_BINDING_ROOT": str(runtime_root),
        "REDDOG_BACKEND_ARCHITECT_MODEL_RUNTIME_BINDING_RECEIPT_PATH": str(artifact),
        "REDDOG_MODEL_SELECTION_RECEIPT_PATH": str(selection_path),
        "REDDOG_MODEL_RUNTIME_AVAILABLE_PROVIDERS": "openai,openrouter",
    }


def _write(runtime_root: Path, receipt: dict) -> Path:
    runtime_root.mkdir(parents=True, exist_ok=True)
    artifact = runtime_root / "architect-binding.json"
    artifact.write_text(json.dumps(receipt), encoding="utf-8")
    return artifact


def test_unconfigured_returns_explicit_evaluation_fallback_state(tmp_path: Path) -> None:
    result = query_model_runtime_binding(repo_root=tmp_path / "repo", environ={})
    assert result.status == STATUS_UNCONFIGURED
    assert result.configured is False
    assert result.accepted is False
    assert result.no_model_call_performed is True


def test_valid_receipt_returns_role_bound_worker(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    runtime = tmp_path / "runtime"
    repo.mkdir()
    selection, receipt = _valid_inputs()
    artifact = _write(runtime, receipt)
    result = query_model_runtime_binding(
        repo_root=repo,
        environ=_configured(runtime, artifact, selection),
        model_runtime_verifier=model_runtime_binding_test_verifier(receipt),
        trusted_now_epoch=lambda: 1_800_000_000,
    )
    assert result.status == STATUS_READY
    assert result.accepted is True
    assert result.principal_model == "openai/gpt-5.6-sol"
    assert result.panel_models == (
        "openrouter/deepseek-v4-pro",
        "openrouter/kimi-k3",
    )
    assert [item["role"] for item in result.role_bindings] == [
        "principal",
        "critic_1",
        "critic_2",
    ]
    assert result.min_verifier_pass_rate == 0.9


def test_partial_configuration_fails_closed(tmp_path: Path) -> None:
    result = query_model_runtime_binding(
        repo_root=tmp_path / "repo",
        environ={"REDDOG_RESIDENT_MODEL_RUNTIME_BINDING_ROOT": str(tmp_path)},
    )
    assert result.status == STATUS_NOT_READY
    assert result.configured is True
    assert "missing_architect_model_runtime_binding_path" in result.rejection_reasons


def test_missing_available_provider_configuration_fails_closed(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    runtime = tmp_path / "runtime"
    repo.mkdir()
    selection, receipt = _valid_inputs()
    artifact = _write(runtime, receipt)
    env = _configured(runtime, artifact, selection)
    env.pop("REDDOG_MODEL_RUNTIME_AVAILABLE_PROVIDERS")
    result = query_model_runtime_binding(
        repo_root=repo,
        environ=env,
        model_runtime_verifier=model_runtime_binding_test_verifier(receipt),
    )
    assert result.accepted is False
    assert result.rejection_reasons == ("model_runtime_available_providers_missing",)


def test_unavailable_selected_provider_fails_before_consumption(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    runtime = tmp_path / "runtime"
    repo.mkdir()
    selection, receipt = _valid_inputs()
    artifact = _write(runtime, receipt)
    env = _configured(runtime, artifact, selection)
    env["REDDOG_MODEL_RUNTIME_AVAILABLE_PROVIDERS"] = "openai"
    result = query_model_runtime_binding(
        repo_root=repo,
        environ=env,
        model_runtime_verifier=model_runtime_binding_test_verifier(receipt),
        trusted_now_epoch=lambda: 1_800_000_000,
    )
    assert result.accepted is False
    assert result.rejection_reasons == ("model_runtime_topology_resolution_rejected",)


def test_artifact_inside_repo_fails_before_consumption(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    runtime = repo / "runtime"
    selection, receipt = _valid_inputs()
    artifact = _write(runtime, receipt)
    result = query_model_runtime_binding(
        repo_root=repo,
        environ=_configured(runtime, artifact, selection),
    )
    assert result.accepted is False
    assert "model_runtime_binding_root_inside_repo" in result.rejection_reasons


def test_tampered_artifact_digest_fails_closed(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    runtime = tmp_path / "runtime"
    repo.mkdir()
    selection, receipt = _valid_inputs()
    receipt["principal_model"] = "attacker/forged"
    artifact = _write(runtime, receipt)
    result = query_model_runtime_binding(
        repo_root=repo,
        environ=_configured(runtime, artifact, selection),
    )
    assert result.accepted is False
    assert result.rejection_reasons == ("model_runtime_binding_artifact_invalid",)


def test_structurally_rehashed_verifier_role_still_fails(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    runtime = tmp_path / "runtime"
    repo.mkdir()
    selection, receipt = _valid_inputs()
    receipt["role_bindings"][1]["role"] = "verifier"
    artifact = _write(runtime, _resign(receipt))
    result = query_model_runtime_binding(
        repo_root=repo,
        environ=_configured(runtime, artifact, selection),
    )
    assert result.accepted is False
    assert "model_runtime_binding_role_boundary_invalid" in result.rejection_reasons


def test_structurally_rehashed_role_model_mismatch_fails(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    runtime = tmp_path / "runtime"
    repo.mkdir()
    selection, receipt = _valid_inputs()
    receipt["role_bindings"][1]["model_id"] = "other/model"
    artifact = _write(runtime, _resign(receipt))
    result = query_model_runtime_binding(
        repo_root=repo,
        environ=_configured(runtime, artifact, selection),
    )
    assert result.accepted is False
    assert "model_runtime_binding_role_topology_mismatch" in result.rejection_reasons


def test_policy_and_evidence_invariants_fail_closed(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    runtime = tmp_path / "runtime"
    repo.mkdir()
    selection, receipt = _valid_inputs()
    receipt["policy"]["required_task_set_digest"] = "placeholder"
    receipt["signed_promotion_receipt_ids"].pop()
    artifact = _write(runtime, _resign(receipt))
    result = query_model_runtime_binding(
        repo_root=repo,
        environ=_configured(runtime, artifact, selection),
    )
    assert result.accepted is False
    assert set(result.rejection_reasons) >= {
        "model_runtime_binding_policy_digest_invalid",
        "model_runtime_binding_evidence_count_mismatch",
    }


def test_zero_verifier_threshold_is_rejected_during_rehydration(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    runtime = tmp_path / "runtime"
    repo.mkdir()
    selection, receipt = _valid_inputs()
    receipt["policy"]["min_verifier_pass_rate"] = 0.0
    artifact = _write(runtime, _resign(receipt))
    result = query_model_runtime_binding(
        repo_root=repo,
        environ=_configured(runtime, artifact, selection),
    )
    assert result.accepted is False
    assert result.rejection_reasons == ("model_runtime_binding_artifact_invalid",)
