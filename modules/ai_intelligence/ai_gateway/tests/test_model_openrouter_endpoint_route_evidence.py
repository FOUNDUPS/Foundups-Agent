"""Offline adversarial contract for endpoint route evidence and call eligibility."""

from __future__ import annotations

import copy
import json
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest

from modules.ai_intelligence.ai_gateway.src.model_autoresearch_single_call_admission import (
    CanonicalSingleCallIntent,
    CanonicalSingleCallJobPolicy,
    build_canonical_single_call_admission,
)
from modules.ai_intelligence.ai_gateway.src.model_openrouter_endpoint_route_evidence import (
    DEFAULT_ENDPOINT_FRESHNESS_MS,
    build_endpoint_observation_receipt,
    build_openrouter_endpoint_route_evidence,
    endpoint_payload_id,
    parse_and_sanitize_openrouter_endpoint_payload,
    rehydrate_endpoint_observation_receipt,
    rehydrate_openrouter_endpoint_route_evidence,
    sha256_bytes,
)
from modules.ai_intelligence.ai_gateway.src.model_provider_catalog_snapshot import (
    build_candidate_snapshot,
    build_discovery_invocation,
    build_discovery_receipt,
    candidate_snapshot_id,
    sanitize_openrouter_catalog_payload,
)
from modules.ai_intelligence.ai_gateway.src.model_provider_execution_control_evidence import (
    build_provider_model_execution_control_evidence,
)


ROOT = Path(__file__).resolve().parents[4]
FIXTURE = Path(__file__).parent / "fixtures/openrouter_endpoints_k3_success.json"
K3_ID = "moonshotai/kimi-k3"
TAG = "moonshotai"


def _raw(payload: dict | None = None) -> bytes:
    if payload is None:
        return FIXTURE.read_bytes()
    return json.dumps(payload, sort_keys=True).encode("utf-8")


def _payload() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _endpoint_sources(
    raw: bytes | None = None,
    *,
    observed_at_ms: int = 10_000,
    tag: str = TAG,
):
    raw = _raw() if raw is None else raw
    sanitized = parse_and_sanitize_openrouter_endpoint_payload(
        raw, requested_model_id=K3_ID
    )
    receipt = build_endpoint_observation_receipt(
        requested_model_id=K3_ID,
        request_envelope_digest=sha256_bytes(b"fixed-endpoint-request"),
        response_body_digest=sha256_bytes(raw),
        response_byte_count=len(raw),
        payload_id=endpoint_payload_id(sanitized),
        observed_at_ms=observed_at_ms,
        http_status=200,
    )
    evidence = build_openrouter_endpoint_route_evidence(
        raw=raw,
        observation_receipt=receipt,
        endpoint_tag=tag,
        now_ms=observed_at_ms + 1,
    )
    return receipt, evidence


def _model_sources(
    *,
    observed_at_ms: int = 10_000,
    prompt_price: str = "0.000003",
    completion_price: str = "0.000015",
    supported_parameters: tuple[str, ...] = ("reasoning", "max_tokens"),
    reasoning_supports_max_tokens: bool | None = None,
):
    row = {
        "id": K3_ID,
        "context_length": 1_048_576,
        "pricing": {"prompt": prompt_price, "completion": completion_price},
        "architecture": {
            "input_modalities": ["text"],
            "output_modalities": ["text"],
        },
        "supported_parameters": list(supported_parameters),
        "reasoning": {
            "supported_efforts": ["max", "high", "low"],
            "default_effort": "max",
            "default_enabled": True,
            "mandatory": False,
        },
        "top_provider": {
            "context_length": 1_048_576,
            "max_completion_tokens": 131_072,
            "is_moderated": False,
        },
    }
    if reasoning_supports_max_tokens is not None:
        row["reasoning"]["supports_max_tokens"] = reasoning_supports_max_tokens
    payload, rejected, counts = sanitize_openrouter_catalog_payload({"data": [row]})
    snapshot_id = candidate_snapshot_id(payload)
    raw = _raw({"data": [row]})
    receipt = build_discovery_receipt(
        call_id="offline-b2a-model-controls",
        invocation=build_discovery_invocation(mode="manual"),
        request_envelope_digest=sha256_bytes(b"fixed-model-request"),
        attempted=True,
        outcome="COMPLETED",
        reason="completed",
        started_at_ms=observed_at_ms - 1,
        completed_at_ms=observed_at_ms,
        http_status=200,
        response_body_digest=sha256_bytes(raw),
        response_byte_count=len(raw),
        candidate_snapshot_id=snapshot_id,
        accepted_record_count=1,
        rejected_record_count=rejected,
        rejection_counts=counts,
    )
    candidate = build_candidate_snapshot(
        catalog_payload=payload,
        rejected_record_count=rejected,
        rejection_counts=counts,
        observed_at_ms=observed_at_ms,
        observation_receipt=receipt,
    )
    evidence = build_provider_model_execution_control_evidence(
        candidate=candidate, model_id=K3_ID, now_ms=observed_at_ms + 1
    )
    return candidate, evidence


def _policy(**changes):
    values = {
        "task_type": "model_autoresearch",
        "model_id": K3_ID,
        "endpoint_tag": TAG,
        "accepted_endpoint_statuses": (0,),
        "max_prompt_tokens": 20_000,
        "max_completion_tokens": 4_096,
        "max_response_bytes": 1_000_000,
        "reasoning_effort": "max",
        "required_parameters": ("max_tokens", "reasoning"),
        "omitted_sampling_parameters": (
            "min_p",
            "seed",
            "temperature",
            "top_a",
            "top_k",
            "top_p",
        ),
        "data_collection": "deny",
        "require_zdr": False,
        "output_use": "evaluation_only",
        "enforce_distillable_text": False,
        "max_prompt_price_per_million": "3",
        "max_completion_price_per_million": "15",
        "max_request_price": "0",
        "expires_at_ms": 20_000,
        "max_calls": 1,
    }
    values.update(changes)
    return CanonicalSingleCallJobPolicy(**values).normalized()


def _intent(**changes):
    values = {
        "task_type": "model_autoresearch",
        "model_id": K3_ID,
        "prompt_digest": sha256_bytes(b"fully-wrapped-held-out-prompt"),
        "prompt_token_upper_bound": 10_000,
        "output_use": "evaluation_only",
        "nonce": "b2a-intent-0001",
        "issued_at_ms": 10_000,
        "expires_at_ms": 20_000,
    }
    values.update(changes)
    return CanonicalSingleCallIntent(**values).normalized()


def _admission(**changes):
    raw = changes.pop("raw", _raw())
    receipt, endpoint = _endpoint_sources(raw)
    candidate, model = _model_sources()
    values = {
        "raw_endpoint_payload": raw,
        "endpoint_observation_receipt": receipt,
        "endpoint_route_evidence": endpoint,
        "model_candidate": candidate,
        "model_control_evidence": model,
        "policy": _policy(),
        "intent": _intent(),
        "now_ms": 10_001,
    }
    values.update(changes)
    return build_canonical_single_call_admission(**values), values


def test_endpoint_fixture_is_strictly_projected_and_lineage_bound() -> None:
    raw = _raw()
    receipt, evidence = _endpoint_sources(raw)
    assert evidence.model_id == K3_ID
    assert evidence.endpoint_tag == TAG
    assert evidence.provider_name == "Moonshot AI"
    assert evidence.context_length == 1_048_576
    assert evidence.max_prompt_tokens_present is True
    assert evidence.max_prompt_tokens == 917_504
    assert evidence.max_completion_tokens_present is True
    assert evidence.max_completion_tokens == 131_072
    assert evidence.prompt_price == "0.000003"
    assert evidence.completion_price == "0.000015"
    assert evidence.request_price_present is True
    assert evidence.request_price == "0"
    assert evidence.unsafe_cost_dimensions == ()
    assert evidence.supported_parameters == ("max_tokens", "reasoning")
    assert evidence.status_present is True
    assert evidence.status == 0
    assert evidence.quantization_present is True
    assert evidence.quantization is None
    assert evidence.trust_class == "provider_asserted_endpoint_route_controls"
    assert receipt.response_body_digest == sha256_bytes(raw)
    assert rehydrate_endpoint_observation_receipt(receipt.to_dict()) == receipt
    assert (
        rehydrate_openrouter_endpoint_route_evidence(
            evidence.to_dict(),
            raw=raw,
            observation_receipt=receipt,
            now_ms=10_001,
        )
        == evidence
    )
    with pytest.raises(FrozenInstanceError):
        evidence.endpoint_tag = "other"  # type: ignore[misc]
    with pytest.raises(TypeError):
        evidence.source_control["pricing"]["prompt"] = "0"  # type: ignore[index]


@pytest.mark.parametrize(
    "mutation,reason",
    (
        (lambda p: p["data"].pop("architecture"), "endpoint_payload_top_level_invalid"),
        (
            lambda p: p["data"]["endpoints"][0].pop("max_prompt_tokens"),
            "endpoint_record_invalid",
        ),
        (
            lambda p: p["data"]["endpoints"][0].update(context_length=True),
            "endpoint_record_invalid",
        ),
        (
            lambda p: p["data"]["endpoints"][0].update(max_completion_tokens=0),
            "endpoint_record_invalid",
        ),
        (
            lambda p: p["data"]["endpoints"][0]["pricing"].update(prompt="-1"),
            "endpoint_record_invalid",
        ),
        (
            lambda p: p["data"]["endpoints"][0].update(tag="Moonshot AI"),
            "endpoint_record_invalid",
        ),
    ),
)
def test_required_schema_and_recognized_malformed_values_fail_closed(
    mutation, reason: str
) -> None:
    payload = _payload()
    mutation(payload)
    with pytest.raises(ValueError, match=reason):
        parse_and_sanitize_openrouter_endpoint_payload(
            _raw(payload), requested_model_id=K3_ID
        )


def test_null_caps_and_optional_status_preserve_presence_semantics() -> None:
    payload = _payload()
    endpoint = payload["data"]["endpoints"][0]
    endpoint["max_prompt_tokens"] = None
    endpoint["max_completion_tokens"] = None
    endpoint.pop("status")
    receipt, evidence = _endpoint_sources(_raw(payload))
    assert evidence.max_prompt_tokens_present is True
    assert evidence.max_prompt_tokens is None
    assert evidence.max_completion_tokens_present is True
    assert evidence.max_completion_tokens is None
    assert evidence.status_present is False
    assert evidence.status is None
    assert "status" not in evidence.source_control
    assert receipt.payload_id


def test_strict_json_duplicate_keys_nonfinite_and_size_bound_reject() -> None:
    duplicate = b'{"data":{"id":"moonshotai/kimi-k3","id":"other/model"}}'
    nonfinite = b'{"data":{"id":NaN}}'
    oversized = b" " * (2 * 1024 * 1024 + 1)
    for raw in (duplicate, nonfinite):
        with pytest.raises(ValueError, match="endpoint_payload_json_invalid"):
            parse_and_sanitize_openrouter_endpoint_payload(
                raw, requested_model_id=K3_ID
            )
    with pytest.raises(ValueError, match="endpoint_payload_too_large"):
        parse_and_sanitize_openrouter_endpoint_payload(
            oversized, requested_model_id=K3_ID
        )


def test_exact_model_identity_duplicate_and_prefix_ambiguous_tags_reject() -> None:
    payload = _payload()
    payload["data"]["id"] = "moonshotai/Kimi-k3"
    with pytest.raises(ValueError, match="endpoint_payload_model_mismatch"):
        parse_and_sanitize_openrouter_endpoint_payload(
            _raw(payload), requested_model_id=K3_ID
        )

    payload = _payload()
    payload["data"]["endpoints"].append(
        copy.deepcopy(payload["data"]["endpoints"][0])
    )
    with pytest.raises(ValueError, match="endpoint_duplicate_tag"):
        parse_and_sanitize_openrouter_endpoint_payload(
            _raw(payload), requested_model_id=K3_ID
        )

    payload = _payload()
    variant = copy.deepcopy(payload["data"]["endpoints"][0])
    variant["tag"] = "moonshotai/turbo"
    payload["data"]["endpoints"].append(variant)
    raw = _raw(payload)
    sanitized = parse_and_sanitize_openrouter_endpoint_payload(
        raw, requested_model_id=K3_ID
    )
    receipt = build_endpoint_observation_receipt(
        requested_model_id=K3_ID,
        request_envelope_digest=sha256_bytes(b"fixed-endpoint-request"),
        response_body_digest=sha256_bytes(raw),
        response_byte_count=len(raw),
        payload_id=endpoint_payload_id(sanitized),
        observed_at_ms=10_000,
        http_status=200,
    )
    with pytest.raises(ValueError, match="endpoint_tag_prefix_collision"):
        build_openrouter_endpoint_route_evidence(
            raw=raw,
            observation_receipt=receipt,
            endpoint_tag=TAG,
            now_ms=10_001,
        )


@pytest.mark.parametrize(
    "field,value",
    (
        ("request", "0.01"),
        ("internal_reasoning", "0.000001"),
        ("input_cache_write", "0.000004"),
        ("discount", 0.5),
    ),
)
def test_nonzero_secondary_cost_dimensions_are_preserved_as_unsafe(
    field: str, value: object
) -> None:
    payload = _payload()
    payload["data"]["endpoints"][0]["pricing"][field] = value
    _, evidence = _endpoint_sources(_raw(payload))
    assert field in evidence.unsafe_cost_dimensions


def test_nonempty_pricing_overrides_are_unsafe() -> None:
    payload = _payload()
    payload["data"]["endpoints"][0]["pricing"]["overrides"] = [
        {"min_prompt_tokens": 1000, "prompt": "0.000006"}
    ]
    _, evidence = _endpoint_sources(_raw(payload))
    assert "overrides" in evidence.unsafe_cost_dimensions


def test_observation_and_evidence_stale_future_body_and_id_tamper_reject() -> None:
    raw = _raw()
    receipt, evidence = _endpoint_sources(raw)
    with pytest.raises(ValueError, match="endpoint_observation_stale"):
        build_openrouter_endpoint_route_evidence(
            raw=raw,
            observation_receipt=receipt,
            endpoint_tag=TAG,
            now_ms=10_000 + DEFAULT_ENDPOINT_FRESHNESS_MS + 1,
        )
    with pytest.raises(ValueError, match="endpoint_observation_future"):
        build_openrouter_endpoint_route_evidence(
            raw=raw,
            observation_receipt=receipt,
            endpoint_tag=TAG,
            now_ms=9_999,
        )
    with pytest.raises(ValueError, match="endpoint_observation_invalid"):
        build_openrouter_endpoint_route_evidence(
            raw=raw + b" ",
            observation_receipt=receipt,
            endpoint_tag=TAG,
            now_ms=10_001,
        )
    tampered = replace(evidence, endpoint_record_digest="sha256:" + "0" * 64)
    with pytest.raises(ValueError, match="endpoint_route_evidence_invalid"):
        rehydrate_openrouter_endpoint_route_evidence(
            tampered.to_dict(),
            raw=raw,
            observation_receipt=receipt,
            now_ms=10_001,
        )


def test_unknown_prose_and_secret_shaped_fields_do_not_survive_projection() -> None:
    payload = _payload()
    endpoint = payload["data"]["endpoints"][0]
    endpoint["description"] = "Bearer not-a-real-but-secret-shaped-value"
    endpoint["api_key"] = "sk-this-value-must-not-survive"
    _, evidence = _endpoint_sources(_raw(payload))
    serialized = json.dumps(evidence.to_dict(), sort_keys=True)
    assert "Bearer" not in serialized
    assert "api_key" not in serialized
    assert "sk-this" not in serialized


def test_wsp97_receipt_names_only_existing_retrieved_wsp_paths() -> None:
    receipt_path = (
        ROOT
        / "docs/audits/ai_intelligence/"
        "OPENROUTER_ENDPOINT_ROUTE_SINGLE_CALL_ADMISSION_PHASE_B2A_"
        "WSP97_EXECUTION_RECEIPT.json"
    )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    wsp_paths = receipt["action_evidence"]["retrieve_wsps"]
    assert wsp_paths
    assert all(path.startswith("WSP_framework/src/WSP_") for path in wsp_paths)
    assert all((ROOT / path).is_file() for path in wsp_paths)


def test_new_surfaces_are_pure_and_have_no_live_authority_tokens() -> None:
    paths = (
        ROOT
        / "modules/ai_intelligence/ai_gateway/src/"
        "model_openrouter_endpoint_payload_projection.py",
        ROOT
        / "modules/ai_intelligence/ai_gateway/src/"
        "model_openrouter_endpoint_route_evidence.py",
        ROOT
        / "modules/ai_intelligence/ai_gateway/src/"
        "model_autoresearch_single_call_contracts.py",
        ROOT
        / "modules/ai_intelligence/ai_gateway/src/"
        "model_autoresearch_single_call_admission.py",
    )
    forbidden = {
        "aiohttp",
        "httpx",
        "requests",
        "socket",
        "subprocess",
        "AIGateway",
        "GatewayModelCaller",
        "call_model",
        "Authorization",
        "os.environ",
    }
    for path in paths:
        source = path.read_text(encoding="utf-8")
        assert not forbidden.intersection(source.split())
        assert len(source.splitlines()) < 500
