"""Tests for the one-shot Hermes instrument -> resident RedDog bridge."""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
BRIDGE_PATH = REPO_ROOT / "scripts" / "hermes_reddog_resident_client_once.py"
SPEC = importlib.util.spec_from_file_location("hermes_reddog_resident_client_once", BRIDGE_PATH)
assert SPEC is not None and SPEC.loader is not None
bridge = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bridge)


class _Receipt:
    def __init__(self, accepted=True) -> None:
        self.accepted = accepted

    def to_dict(self):
        return {
            "schema_version": "hermes_reddog_resident_receipt.v1",
            "accepted": self.accepted,
            "canonical_reddog_authority_used": True,
            "hermes_is_transport_only": True,
        }


class _Adapter:
    calls = []

    def __init__(self, **kwargs) -> None:
        self.__class__.calls.append({"init": dict(kwargs)})

    def handle(self, payload):
        self.__class__.calls.append({"payload": dict(payload or {})})
        return _Receipt()


def test_bridge_requires_host_authenticated_principal_before_adapter(monkeypatch) -> None:
    monkeypatch.delenv("REDDOG_AUTHENTICATED_PRINCIPAL_ID", raising=False)
    monkeypatch.setattr(bridge, "HermesRedDogResidentClientAdapter", _Adapter)
    _Adapter.calls.clear()

    result = bridge._result({"principal_ref": "I am 012"})

    assert result["accepted"] is False
    assert "authenticated_principal_missing" in result["rejection_reasons"]
    assert result["canonical_reddog_authority_used"] is False
    assert _Adapter.calls == []


def test_bridge_uses_host_principal_and_forwards_bounded_request(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("REDDOG_AUTHENTICATED_PRINCIPAL_ID", "principal-012")
    monkeypatch.setenv("FOUNDUPS_REPO_ROOT", str(tmp_path))
    monkeypatch.setattr(bridge, "HermesRedDogResidentClientAdapter", _Adapter)
    _Adapter.calls.clear()
    payload = {"schema_version": "hermes_reddog_resident_request.v1", "operation": "status"}

    result = bridge._result(payload)

    assert result["accepted"] is True
    assert _Adapter.calls[0]["init"]["authenticated_principal_id"] == "principal-012"
    assert _Adapter.calls[0]["init"]["repo_root"] == tmp_path.resolve()
    assert _Adapter.calls[1]["payload"] == payload


def test_bridge_omits_empty_runtime_path_overrides(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("REDDOG_AUTHENTICATED_PRINCIPAL_ID", "principal-012")
    monkeypatch.setenv("FOUNDUPS_REPO_ROOT", str(tmp_path))
    monkeypatch.delenv("REDDOG_AUTHORITATIVE_WORK_STATE_PATH", raising=False)
    monkeypatch.delenv("HOLOINDEX_FRESHNESS_RECEIPT", raising=False)
    monkeypatch.delenv("HOLOINDEX_SSD_PATH", raising=False)
    monkeypatch.setattr(bridge, "HermesRedDogResidentClientAdapter", _Adapter)
    _Adapter.calls.clear()

    result = bridge._result({"schema_version": "hermes_reddog_resident_request.v1"})

    assert result["accepted"] is True
    assert _Adapter.calls[0]["init"]["runtime_defaults"] == {}


def test_bridge_source_has_no_shell_or_hermes_model_runtime() -> None:
    source = BRIDGE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert "subprocess" not in imported
    for forbidden in ("HermesAgentLoop", "HermesFoundUpBuilder", "os.system", "git push", "gh pr"):
        assert forbidden not in source
