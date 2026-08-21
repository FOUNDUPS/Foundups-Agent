"""Request-truth contract tests for the exact OpenRouter Kimi K3 route."""

from __future__ import annotations

from dataclasses import replace

import pytest

from modules.ai_intelligence.ai_gateway.src.ai_gateway import AIGateway


class _Response:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return {"choices": [{"message": {"content": "ok"}}]}


def _gateway_request(monkeypatch, *, requested=None, effort=None, model="moonshotai/kimi-k3"):
    seen: list[dict[str, object]] = []
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(
        "modules.ai_intelligence.ai_gateway.src.ai_gateway.requests.post",
        lambda url, **kwargs: seen.append({"url": url, **kwargs}) or _Response(),
    )
    gateway = AIGateway()
    gateway._call_openai(
        gateway.providers["openrouter"],
        "audit",
        model,
        max_completion_tokens=requested,
        reasoning_effort=effort,
    )
    return seen[0]["json"]


@pytest.mark.parametrize(
    ("requested", "expected"),
    ((256, 4096), (4096, 4096), (8192, 8192), (131072, 131072)),
)
def test_explicit_k3_budget_is_floored_without_truncating_valid_requests(
    monkeypatch, requested, expected
):
    body = _gateway_request(monkeypatch, requested=requested, effort="low")
    assert body["max_tokens"] == expected
    assert body["reasoning"] == {"effort": "max"}
    assert "temperature" not in body


@pytest.mark.parametrize(("configured", "expected"), (("256", 4096), ("8192", 8192)))
def test_environment_k3_budget_is_resolved_then_floored(monkeypatch, configured, expected):
    monkeypatch.setenv("OPENROUTER_MAX_TOKENS", configured)
    body = _gateway_request(monkeypatch)
    assert body["max_tokens"] == expected


def test_explicit_k3_budget_overrides_environment_before_floor(monkeypatch):
    monkeypatch.setenv("OPENROUTER_MAX_TOKENS", "8192")
    body = _gateway_request(monkeypatch, requested=256)
    assert body["max_tokens"] == 4096


def test_k3_budget_above_endpoint_limit_fails_before_http(monkeypatch):
    seen: list[object] = []
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(
        "modules.ai_intelligence.ai_gateway.src.ai_gateway.requests.post",
        lambda *args, **kwargs: seen.append((args, kwargs)),
    )
    gateway = AIGateway()
    with pytest.raises(ValueError, match="max_completion_tokens"):
        gateway._call_openai(
            gateway.providers["openrouter"],
            "audit",
            "moonshotai/kimi-k3",
            max_completion_tokens=131073,
            reasoning_effort="low",
        )
    assert seen == []


def test_exact_provider_and_model_pair_only_gets_k3_contract(monkeypatch):
    seen: list[dict[str, object]] = []
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(
        "modules.ai_intelligence.ai_gateway.src.ai_gateway.requests.post",
        lambda url, **kwargs: seen.append(kwargs) or _Response(),
    )
    gateway = AIGateway()
    openai_provider = replace(gateway.providers["openai"], api_key="test-key")
    gateway._call_openai(
        openai_provider,
        "audit",
        "moonshotai/kimi-k3",
        max_completion_tokens=256,
        reasoning_effort="low",
    )
    assert seen[0]["json"]["max_tokens"] == 256
    assert seen[0]["json"]["temperature"] == 0.7
    assert "reasoning" not in seen[0]["json"]


def test_non_k3_openrouter_request_is_unchanged(monkeypatch):
    body = _gateway_request(
        monkeypatch, requested=256, effort="low", model="z-ai/glm-5.2"
    )
    assert body["max_tokens"] == 256
    assert body["reasoning"] == {"effort": "low"}
