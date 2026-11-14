"""Fail-closed tests for endpoint cost and status schema drift."""

from __future__ import annotations

import pytest

from modules.ai_intelligence.ai_gateway.src.model_openrouter_endpoint_route_evidence import (
    parse_and_sanitize_openrouter_endpoint_payload,
)
from modules.ai_intelligence.ai_gateway.tests.test_model_openrouter_endpoint_route_evidence import (
    K3_ID,
    _endpoint_sources,
    _payload,
    _raw,
)


@pytest.mark.parametrize("value", ("0", "0.000001"))
def test_unknown_endpoint_pricing_key_is_never_inferred_free(value: str) -> None:
    payload = _payload()
    payload["data"]["endpoints"][0]["pricing"]["future_cost_dimension"] = value
    with pytest.raises(ValueError, match="endpoint_record_invalid"):
        parse_and_sanitize_openrouter_endpoint_payload(
            _raw(payload), requested_model_id=K3_ID
        )


@pytest.mark.parametrize("status", (1, -4, -11))
def test_forward_unknown_endpoint_status_is_rejected(status: int) -> None:
    payload = _payload()
    payload["data"]["endpoints"][0]["status"] = status
    with pytest.raises(ValueError, match="endpoint_record_invalid"):
        parse_and_sanitize_openrouter_endpoint_payload(
            _raw(payload), requested_model_id=K3_ID
        )


@pytest.mark.parametrize("status", (-1, -2, -3, -5, -10))
def test_known_negative_endpoint_status_remains_bounded_evidence(status: int) -> None:
    payload = _payload()
    payload["data"]["endpoints"][0]["status"] = status
    _, evidence = _endpoint_sources(_raw(payload))
    assert evidence.status_present is True
    assert evidence.status == status
