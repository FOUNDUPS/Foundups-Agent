"""Security and integration tests for the start-operations control adapter."""

from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from modules.communication.moltbot_bridge.src.reddog_start_operations_control import (
    CONTROL_SCHEMA,
    run_start_operations_control,
)
from modules.communication.moltbot_bridge.src.reddog_start_operations_profile import (
    PROFILE_ID,
    READ_TARGETS,
    WORK_FOCUS,
)
from modules.communication.moltbot_bridge.src.reddog_transport_neutral_grounding_service import (
    TransportGroundingResult,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULES = tuple(
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / name
    for name in (
        "reddog_resident_model_runtime_bindings.py",
        "reddog_start_operations_control.py",
        "reddog_start_operations_control_actions.py",
        "reddog_start_operations_control_authority.py",
        "reddog_start_operations_control_binding.py",
        "reddog_start_operations_control_receipt.py",
        "reddog_start_operations_result.py",
        "reddog_start_operations_profile.py",
    )
)
SOURCE_FILES = (*MODULES, REPO_ROOT / "scripts" / "reddog_start_operations_control_once.py")


def _request(action: str = "submit", intent_id: str = "") -> dict[str, str]:
    return {
        "schema_version": CONTROL_SCHEMA,
        "action": action,
        "control_request_id": "sha256:" + "9" * 64,
        "operations_profile_id": PROFILE_ID,
        "intent_id": intent_id,
    }


def _env() -> dict[str, str]:
    return {
        "REDDOG_AUTHENTICATED_PRINCIPAL_ID": "principal-012",
        "REDDOG_AUTHORIZED_FOUNDUP_IDS": "foundups_agent",
        "REDDOG_RESIDENT_ARCHITECT_FOUNDUP_ID": "foundups_agent",
        "REDDOG_RESIDENT_MODEL_RUNTIME_BINDING_ROOT": "O:/runtime",
        "REDDOG_READONLY_AUDIT_MODEL_RUNTIME_BINDING_RECEIPT_PATH": "O:/runtime/audit.json",
        "REDDOG_BACKEND_ARCHITECT_MODEL_RUNTIME_BINDING_RECEIPT_PATH": "O:/runtime/architect.json",
        "REDDOG_READONLY_AUDIT_MODEL_RUNTIME_BINDING_EXPECTED_RECEIPT_ID": "audit:receipt",
        "REDDOG_BACKEND_ARCHITECT_MODEL_RUNTIME_BINDING_EXPECTED_RECEIPT_ID": "architect:receipt",
    }


def _grounding() -> TransportGroundingResult:
    return TransportGroundingResult(
        schema_version="reddog_transport_grounding_result.v1",
        accepted=True,
        intent={
            "schema_version": "reddog_intent.v2",
            "intent_id": "sha256:grounding",
            "source_surface": "editor_thin_client",
            "origin": "extension",
            "principal_ref": "principal-012",
            "foundup_id": "foundups_agent",
            "work_focus": WORK_FOCUS,
            "grounding_receipt": {"receipt_id": "sha256:grounding"},
            "submits_executable_authority": False,
        },
    )


def _response(**overrides):
    values = {
        "accepted": True,
        "intent_id": "sha256:intent",
        "cycle_id": "sha256:cycle",
        "status": "DETERMINED",
        "architect_action": "FIX",
        "architect_next_slice": "NEXT_PHASE1",
        "determination_id": "sha256:determination",
        "task_status_counts": {"completed": 5},
        "duplicate_intent_reused": False,
        "recovered_existing_cycle": False,
        "rejection_reasons": (),
        "client_no_shell_command_executed": True,
        "client_no_repo_mutation_performed": True,
        "client_no_holoindex_reindex_performed": True,
        "client_no_hermes_execution_performed": True,
        "client_no_worktree_operation_performed": True,
        "client_no_pr_created": True,
        "client_no_merge_performed": True,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class _Client:
    instances: list["_Client"] = []

    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs
        self.calls = []
        self.__class__.instances.append(self)

    def submit(self, intent):
        self.calls.append(("submit", dict(intent)))
        return _response(intent_id=intent["intent_id"])

    def status(self, intent_id):
        self.calls.append(("status", intent_id))
        return _response(intent_id=intent_id)

    def cancel(self, intent_id):
        self.calls.append(("cancel", intent_id))
        return _response(accepted=False, status="CANCELLED", intent_id=intent_id)

    def resume(self, intent_id):
        self.calls.append(("resume", intent_id))
        return _response(intent_id=intent_id)


@pytest.fixture(autouse=True)
def _clear_clients():
    _Client.instances.clear()


def _run(request=None, env=None, grounding=None, repo_state=None):
    audit = {"receipt_id": "audit:receipt", "runtime_surface": "reddog_readonly_audit_worker"}
    architect = {"receipt_id": "architect:receipt", "runtime_surface": "reddog_backend_architect"}
    with (
        patch(
            "modules.communication.moltbot_bridge.src.reddog_start_operations_control."
            "observe_repo_state",
            return_value=repo_state or {"head_sha": "a" * 40, "dirty_paths": ()},
        ),
        patch(
            "modules.communication.moltbot_bridge.src.reddog_start_operations_control_authority."
            "load_resident_model_runtime_bindings",
            return_value=(audit, architect, ""),
        ),
    ):
        return run_start_operations_control(
            repo_root=REPO_ROOT,
            request=_request() if request is None else request,
            environ=_env() if env is None else env,
            client_factory=_Client,
            grounding_runner=Mock(return_value=grounding or _grounding()),
        )


def test_submit_binds_profile_head_models_scope_and_budgets() -> None:
    result = _run()
    client = _Client.instances[0]
    intent = client.calls[0][1]

    assert result.accepted is True
    assert result.control_request_id == _request()["control_request_id"]
    assert result.effect_evidence_level == "IMPLEMENTATION_BOUNDARY_ATTESTATION"
    assert client.calls[0][0] == "submit"
    assert intent["operations_profile_id"] == PROFILE_ID
    assert intent["repo_head_sha"] == "a" * 40
    assert intent["audit_model_runtime_binding_receipt_id"] == "audit:receipt"
    assert intent["architect_model_runtime_binding_receipt_id"] == "architect:receipt"
    assert intent["max_claims"] == 5
    assert intent["timeout_seconds"] == 180
    assert client.kwargs["authenticated_principal_id"] == "principal-012"
    assert client.kwargs["authorized_foundup_ids"] == ("foundups_agent",)
    assert client.kwargs["runtime_defaults"]["audit_lanes"]


def test_request_cannot_override_principal_model_or_budget() -> None:
    request = {
        **_request(),
        "principal_id": "attacker",
        "foundup_id": "attacker_foundup",
        "model": "attacker/model",
        "max_claims": 999,
        "timeout_seconds": 999999,
    }
    result = _run(request=request)
    client = _Client.instances[0]
    intent = client.calls[0][1]

    assert result.accepted is True
    assert client.kwargs["authenticated_principal_id"] == "principal-012"
    assert intent["foundup_id"] == "foundups_agent"
    assert intent["max_claims"] == 5
    assert intent["timeout_seconds"] == 180
    assert "model" not in intent


def test_dirty_repo_rejects_before_grounding_or_client() -> None:
    result = _run(repo_state={"head_sha": "a" * 40, "dirty_paths": (" M file.py",)})
    assert result.accepted is False
    assert result.rejection_reasons == ("start_operations_repo_dirty",)
    assert not _Client.instances


@pytest.mark.parametrize(
    ("payload", "reason"),
    (
        ({}, "start_operations_control_schema_invalid"),
        ({**_request(), "action": "execute"}, "start_operations_control_action_invalid"),
        (
            {**_request(), "operations_profile_id": "attacker-profile"},
            "start_operations_profile_invalid",
        ),
        (_request("status"), "start_operations_control_intent_id_invalid"),
        (
            {**_request(), "control_request_id": "attacker"},
            "start_operations_control_request_id_invalid",
        ),
    ),
)
def test_invalid_control_request_returns_typed_rejection(payload, reason) -> None:
    result = _run(request=payload)
    assert result.accepted is False
    assert result.rejection_reasons == (reason,)
    assert result.no_repo_mutation_performed is True
    assert not _Client.instances


def test_missing_authenticated_scope_returns_typed_rejection() -> None:
    result = _run(env={})
    assert result.accepted is False
    assert result.rejection_reasons == (
        "start_operations_authenticated_scope_missing",
    )
    assert not _Client.instances


def test_repository_observation_failure_returns_typed_rejection() -> None:
    with patch(
        "modules.communication.moltbot_bridge.src.reddog_start_operations_control."
        "observe_repo_state",
        side_effect=RuntimeError("do not leak"),
    ):
        result = run_start_operations_control(
            repo_root=REPO_ROOT,
            request=_request(),
            environ=_env(),
            client_factory=_Client,
            grounding_runner=Mock(return_value=_grounding()),
        )
    assert result.accepted is False
    assert result.rejection_reasons == (
        "start_operations_repository_observation_failed",
    )
    assert "do not leak" not in str(result.to_dict())
    assert not _Client.instances


@pytest.mark.parametrize(
    ("key", "value", "reason"),
    (
        ("REDDOG_START_OPERATIONS_MAX_CLAIMS", "0", "start_operations_max_claims_invalid"),
        ("REDDOG_START_OPERATIONS_MAX_CLAIMS", "6", "start_operations_max_claims_invalid"),
        ("REDDOG_START_OPERATIONS_TIMEOUT_SECONDS", "-1", "start_operations_timeout_invalid"),
        ("REDDOG_START_OPERATIONS_TIMEOUT_SECONDS", "601", "start_operations_timeout_invalid"),
    ),
)
def test_invalid_budget_fails_closed(key: str, value: str, reason: str) -> None:
    env = {**_env(), key: value}
    result = _run(env=env)
    assert result.accepted is False
    assert result.rejection_reasons == (reason,)
    assert not _Client.instances


def test_grounding_failure_is_deferred_without_maintenance() -> None:
    grounding = TransportGroundingResult(
        schema_version="reddog_transport_grounding_result.v1",
        accepted=False,
        rejection_reasons=("grounding_holoindex_owner_query_failed",),
    )
    result = _run(grounding=grounding)
    assert result.accepted is False
    assert result.deferred_holo_maintenance is True
    assert result.no_maintenance_performed is True
    assert not _Client.instances


@pytest.mark.parametrize("action", ("status", "cancel", "resume"))
def test_existing_cycle_controls_use_canonical_client(action: str) -> None:
    result = _run(request=_request(action, "sha256:existing"))
    assert _Client.instances[0].calls == [(action, "sha256:existing")]
    assert result.intent_id == "sha256:existing"


def test_runtime_boundary_fails_closed() -> None:
    class _UnsafeClient(_Client):
        def submit(self, intent):
            return _response(client_no_repo_mutation_performed=False)

    with (
        patch(
            "modules.communication.moltbot_bridge.src.reddog_start_operations_control."
            "observe_repo_state",
            return_value={"head_sha": "a" * 40, "dirty_paths": ()},
        ),
        patch(
            "modules.communication.moltbot_bridge.src.reddog_start_operations_control_authority."
            "load_resident_model_runtime_bindings",
            return_value=({"receipt_id": "a"}, {"receipt_id": "b"}, ""),
        ),
    ):
        result = run_start_operations_control(
            repo_root=REPO_ROOT,
            request=_request(),
            environ=_env(),
            client_factory=_UnsafeClient,
            grounding_runner=Mock(return_value=_grounding()),
        )
    assert result.accepted is False
    assert "runtime_boundary_invalid" in result.rejection_reasons
    assert result.no_repo_mutation_performed is False


def test_operations_profile_targets_exist_and_are_not_empty_grounding() -> None:
    assert READ_TARGETS
    assert all((REPO_ROOT / target).is_file() for target in READ_TARGETS)
    assert all(target in WORK_FOCUS for target in READ_TARGETS)


def test_control_modules_have_no_execution_or_indexing_imports() -> None:
    banned_imports = {"subprocess", "openai", "requests"}
    banned_calls = {"os.system", "os.popen"}
    for module in SOURCE_FILES:
        source = module.read_text(encoding="utf-8")
        tree = ast.parse(source)
        assert len(source.splitlines()) <= 200
        assert all(
            (node.end_lineno or node.lineno) - node.lineno + 1 <= 50
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        )
        imports = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in (
                node.names
                if isinstance(node, ast.Import)
                else [ast.alias(name=node.module or "")]
            )
        }
        calls = {
            f"{node.func.value.id}.{node.func.attr}"
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
        }
        assert not imports.intersection(banned_imports)
        assert not calls.intersection(banned_calls)
