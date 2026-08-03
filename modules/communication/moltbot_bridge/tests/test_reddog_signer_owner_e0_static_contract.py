"""Static and capability-state tests for signer owner E0 admission."""

from __future__ import annotations

import ast
import copy
import pickle
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.tests.test_reddog_signer_owner_controlled_e0_admission import (
    SLICE_MODULES,
    _CURRENT_SELECTION,
    _SelectionBoundary,
    _fixture,
    _resign,
)
from modules.communication.moltbot_bridge.src import (
    reddog_signer_owner_e0_current_selection as current_selection_module,
)


@pytest.fixture(autouse=True)
def _root_owned_selection_loader(monkeypatch: pytest.MonkeyPatch) -> None:
    def load(**_kwargs: object) -> tuple[object, _SelectionBoundary]:
        capability = object()
        return capability, _SelectionBoundary(capability, _CURRENT_SELECTION)

    monkeypatch.setattr(
        current_selection_module,
        "load_system_service_manifest_selection",
        load,
    )


def test_caller_cannot_mutate_policy_after_admission(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    result = fixture["boundary"].admit(
        fixture["owner_config_path"], fixture["policy"]
    )
    assert result.accepted is True
    fixture["policy"]["allowed_operations"].append("issue_principal_identity")
    receipt = fixture["boundary"].consume(result.capability)
    assert receipt.policy_id == result.policy_id


def test_admission_capability_is_one_use(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    result = fixture["boundary"].admit(
        fixture["owner_config_path"], fixture["policy"]
    )
    assert result.accepted is True
    fixture["boundary"].consume(result.capability)
    with pytest.raises(ValueError):
        fixture["boundary"].consume(result.capability)


def test_runtime_roots_must_be_disjoint(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    fixture["policy"]["revocation_root"] = fixture["policy"]["replay_root"]
    fixture["policy"]["revocation_path"] = str(
        Path(str(fixture["policy"]["replay_root"])) / "revocations.db"
    )
    _resign(fixture)
    assert fixture["boundary"].admit(
        fixture["owner_config_path"], fixture["policy"]
    ).accepted is False


def test_capability_cannot_be_copied_or_pickled(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    result = fixture["boundary"].admit(
        fixture["owner_config_path"], fixture["policy"]
    )
    assert result.accepted is True
    with pytest.raises(TypeError):
        copy.copy(result.capability)
    with pytest.raises(TypeError):
        copy.deepcopy(result.capability)
    with pytest.raises(TypeError):
        pickle.dumps(result.capability)


def test_slice_has_no_effect_runtime_imports_or_calls() -> None:
    source_root = Path(__file__).parents[1] / "src"
    banned_imports = {
        "subprocess",
        "socket",
        "secrets_mcp.src.op_cli_secret_resolver",
    }
    banned_calls = {
        "bind",
        "connect",
        "listen",
        "popen",
        "run",
        "start",
        "resolve_signer_key",
        "build_signer_backend_from_provider",
    }
    for filename in SLICE_MODULES:
        tree = ast.parse((source_root / filename).read_text(encoding="ascii"))
        imports = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        imports.update(
            str(node.module or "")
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        )
        calls = {
            node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, (ast.Attribute, ast.Name))
        }
        assert not any(
            item == banned or item.endswith("." + banned)
            for item in imports
            for banned in banned_imports
        )
        assert calls.isdisjoint(banned_calls)


def test_slice_obeys_wsp62_module_and_function_limits() -> None:
    source_root = Path(__file__).parents[1] / "src"
    for filename in SLICE_MODULES:
        text = (source_root / filename).read_text(encoding="ascii")
        assert len(text.splitlines()) <= 200
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert (node.end_lineno or node.lineno) - node.lineno + 1 <= 50


def test_slice_test_helpers_obey_wsp62_function_limit() -> None:
    test_root = Path(__file__).parent
    for filename in (
        "test_reddog_signer_owner_controlled_e0_admission.py",
        "test_reddog_signer_owner_e0_static_contract.py",
    ):
        text = (test_root / filename).read_text(encoding="ascii")
        assert len(text.splitlines()) <= 675
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert (node.end_lineno or node.lineno) - node.lineno + 1 <= 60
