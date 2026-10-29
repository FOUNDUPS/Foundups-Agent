"""Tests for the governed Grok Bot RedDog tool-provider boundary."""

from __future__ import annotations

import ast
from pathlib import Path

from modules.foundups.agent.src.grokbot_reddog_tool_provider import (
    GROKBOT_TOOL_REQUEST_SCHEMA,
    GrokBotRedDogToolProvider,
)


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "grokbot_reddog_tool_provider.py"
)


def _request(operation="health", **extra):
    return {
        "schema_version": GROKBOT_TOOL_REQUEST_SCHEMA,
        "request_id": "grokbot-request-1",
        "operation": operation,
        **extra,
    }


def test_provider_is_disabled_by_default_and_fails_closed() -> None:
    provider = GrokBotRedDogToolProvider(dispatcher=lambda request: {"accepted": True})
    receipt = provider.handle(_request())

    assert receipt.accepted is False
    assert receipt.reddog_authority_retained is True
    assert receipt.grokbot_is_external_tool_only is True
    assert receipt.result["rejection_reason"] == "REJECT_GROKBOT_PROVIDER_DISABLED"


def test_enabled_provider_uses_only_injected_transport() -> None:
    calls = []

    def dispatcher(request):
        calls.append(dict(request))
        return {"accepted": True, "status": "READY", "job_id": "gb-1"}

    provider = GrokBotRedDogToolProvider(dispatcher=dispatcher, enabled=True)
    receipt = provider.handle(_request())

    assert receipt.accepted is True
    assert receipt.result["status"] == "READY"
    assert calls == [
        {
            "schema_version": GROKBOT_TOOL_REQUEST_SCHEMA,
            "request_id": "grokbot-request-1",
            "operation": "health",
        }
    ]


def test_execute_requires_pre_admitted_work_order() -> None:
    calls = []
    provider = GrokBotRedDogToolProvider(
        dispatcher=lambda request: calls.append(request) or {"accepted": True},
        enabled=True,
    )

    missing = provider.handle(_request("execute"))
    unadmitted = provider.handle(
        _request("execute", work_order={"work_order_id": "wo-1", "admitted": False})
    )
    admitted = provider.handle(
        _request(
            "execute",
            work_order={
                "work_order_id": "wo-2",
                "admitted": True,
                "mission": "Research a bounded target and return artifacts.",
                "effect_ceiling": "PROPOSAL",
            },
        )
    )

    assert missing.accepted is False
    assert unadmitted.accepted is False
    assert admitted.accepted is True
    assert len(calls) == 1
    assert calls[0]["work_order"]["work_order_id"] == "wo-2"


def test_payload_cannot_inject_principal_token_or_authority() -> None:
    calls = []
    provider = GrokBotRedDogToolProvider(
        dispatcher=lambda request: calls.append(request) or {"accepted": True},
        enabled=True,
    )

    for field in ("principal_ref", "authority", "token", "api_key"):
        receipt = provider.handle(_request(**{field: "attacker-controlled"}))
        assert receipt.accepted is False
        assert "AUTHORITY_INJECTION" in receipt.result["rejection_reason"]

    nested = provider.handle(
        _request(
            "execute",
            work_order={
                "work_order_id": "wo-3",
                "admitted": True,
                "credentials": "do-not-forward",
            },
        )
    )
    assert nested.accepted is False
    assert calls == []


def test_bad_schema_operation_transport_and_result_fail_closed() -> None:
    bad_schema = GrokBotRedDogToolProvider(dispatcher=lambda _: {"accepted": True}, enabled=True).handle(
        {"schema_version": "wrong", "request_id": "r", "operation": "health"}
    )
    bad_operation = GrokBotRedDogToolProvider(dispatcher=lambda _: {"accepted": True}, enabled=True).handle(
        _request("delete_everything")
    )
    no_transport = GrokBotRedDogToolProvider(dispatcher=None, enabled=True).handle(_request())
    broken_transport = GrokBotRedDogToolProvider(
        dispatcher=lambda _: (_ for _ in ()).throw(RuntimeError("boom")), enabled=True
    ).handle(_request())
    invalid_result = GrokBotRedDogToolProvider(dispatcher=lambda _: "not-a-mapping", enabled=True).handle(
        _request()
    )

    assert bad_schema.accepted is False
    assert bad_operation.accepted is False
    assert no_transport.accepted is False
    assert broken_transport.accepted is False
    assert invalid_result.accepted is False


def test_capabilities_record_shared_computer_and_no_public_api_assumption() -> None:
    capabilities = GrokBotRedDogToolProvider(dispatcher=None).capabilities()

    assert capabilities["provider"] == "grokbot"
    assert capabilities["persistent_computer"] is True
    assert capabilities["plugins_mcp"] is True
    assert capabilities["shared_account_computer_boundary"] is True
    assert capabilities["public_execution_api_assumed"] is False


def test_core_provider_has_no_network_shell_secret_or_repo_write_surface() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }

    for forbidden_import in ("subprocess", "requests", "httpx", "urllib", "socket", "os"):
        assert forbidden_import not in imported
    for forbidden_text in (
        "SAND_GATEWAY_TOKEN",
        "gateway.json",
        "GROKBOT_GATEWAY_URL",
        "git push",
        "gh pr",
        "write_text(",
    ):
        assert forbidden_text not in source
