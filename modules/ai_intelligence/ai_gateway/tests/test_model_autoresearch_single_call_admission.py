"""Adversarial offline tests for canonical single-call eligibility admission."""

from __future__ import annotations

import hashlib
import json

import pytest

from modules.ai_intelligence.ai_gateway.src.model_autoresearch_single_call_admission import (
    rehydrate_canonical_single_call_admission,
)
from modules.ai_intelligence.ai_gateway.src.model_autoresearch_single_call_contracts import (
    digest_payload,
)
from modules.ai_intelligence.ai_gateway.tests.test_model_openrouter_endpoint_route_evidence import (
    TAG,
    _admission,
    _endpoint_sources,
    _intent,
    _model_sources,
    _payload,
    _policy,
    _raw,
)


def test_canonical_admission_binds_exact_route_controls_lineage_and_halt() -> None:
    admission, values = _admission()
    assert admission.gateway_base_url == "https://openrouter.ai/api/v1"
    assert admission.http_method == "POST"
    assert admission.request_path == "/chat/completions"
    assert admission.endpoint_tag == TAG
    assert admission.provider_order == (TAG,)
    assert admission.allow_fallbacks is False
    assert admission.require_parameters is True
    assert admission.data_collection == "deny"
    assert admission.require_zdr is False
    assert admission.enforce_distillable_text is False
    assert admission.reasoning_effort == "max"
    assert admission.prompt_price_per_million == "3"
    assert admission.completion_price_per_million == "15"
    assert admission.request_price == "0"
    assert admission.request_price_present is True
    assert admission.request_price_schema_policy == (
        "openrouter_public_pricing_request_optional_absence_as_zero.v1"
    )
    assert admission.request_price_schema_policy_accepted is True
    assert admission.mandatory_request_parameters == (
        "max_tokens",
        "reasoning",
    )
    assert admission.max_calls == 1
    assert admission.runtime_authority == "eligibility_only"
    assert admission.halted_reasons == (
        "atomic_admission_consumption_missing",
        "authenticated_endpoint_supply_missing",
        "authoritative_endpoint_availability_missing",
        "authoritative_usage_missing",
        "caller_wiring_absent",
        "prebuffer_response_bound_missing",
        "runtime_directory_identity_missing",
    )
    assert admission.model_control_evidence_id == values[
        "model_control_evidence"
    ].evidence_id
    assert admission.endpoint_route_evidence_id == values[
        "endpoint_route_evidence"
    ].evidence_id
    assert admission.max_response_bytes == 1_000_000
    assert admission.max_completion_tokens == 4_096
    assert admission.reserved_upper_cost == "0.09144"
    assert admission.endpoint_status == 0
    assert admission.accepted_endpoint_statuses == (0,)
    assert admission.endpoint_status_policy_accepted is True
    assert admission.route_contract_digest == digest_payload(
        {
            "gateway_base_url": "https://openrouter.ai/api/v1",
            "http_method": "POST",
            "request_path": "/chat/completions",
            "headers": {
                "Content-Type": "application/json",
                "X-OpenRouter-Metadata": "enabled",
            },
            "stream": False,
        }
    )
    assert admission.to_dict()["request_control"] == {
        "max_tokens": 4_096,
        "reasoning": {"effort": "max"},
        "provider": {
            "order": [TAG],
            "allow_fallbacks": False,
            "require_parameters": True,
            "data_collection": "deny",
            "zdr": False,
            "max_price": {
                "prompt": "3",
                "completion": "15",
                "request": "0",
            },
        },
    }


def test_wire_request_control_has_exact_chat_completions_keys() -> None:
    admission, _ = _admission()
    assert set(admission.request_control) == {
        "max_tokens",
        "reasoning",
        "provider",
    }


def test_wire_request_control_never_uses_internal_completion_budget_name() -> None:
    admission, _ = _admission()
    assert admission.request_control["max_tokens"] == 4_096
    assert "max_completion_tokens" not in admission.request_control


@pytest.mark.parametrize(
    "policy_change,intent_change,reason",
    (
        ({"model_id": "other/model"}, {}, "single_call_model_mismatch"),
        ({}, {"model_id": "other/model"}, "single_call_model_mismatch"),
        ({"max_prompt_tokens": 9_999}, {}, "single_call_prompt_cap_exceeded"),
        (
            {"max_completion_tokens": 131_073},
            {},
            "single_call_completion_cap_exceeded",
        ),
        (
            {"reasoning_effort": "medium"},
            {},
            "single_call_reasoning_effort_unsupported",
        ),
        (
            {"required_parameters": ("reasoning", "tools")},
            {},
            "single_call_required_parameters_invalid",
        ),
        (
            {"omitted_sampling_parameters": ("temperature",)},
            {},
            "single_call_sampling_policy_invalid",
        ),
        ({"data_collection": "allow"}, {}, "single_call_policy_invalid"),
        ({"require_zdr": True}, {}, "single_call_zdr_evidence_missing"),
        (
            {"output_use": "training", "enforce_distillable_text": True},
            {"output_use": "training"},
            "single_call_output_training_permission_missing",
        ),
    ),
)
def test_job_certification_rejects_mismatch_and_unsupported_authority(
    policy_change: dict, intent_change: dict, reason: str
) -> None:
    with pytest.raises(ValueError, match=reason):
        _admission(policy=_policy(**policy_change), intent=_intent(**intent_change))


@pytest.mark.parametrize(
    "supported_parameters",
    (("reasoning",), ("max_tokens",)),
)
def test_policy_cannot_self_weaken_emitted_request_controls(
    supported_parameters: tuple[str, ...],
) -> None:
    payload = _payload()
    payload["data"]["endpoints"][0]["supported_parameters"] = list(
        supported_parameters
    )
    raw = _raw(payload)
    receipt, endpoint = _endpoint_sources(raw)
    candidate, model = _model_sources(
        supported_parameters=supported_parameters
    )
    with pytest.raises(
        ValueError, match="single_call_required_parameters_invalid"
    ):
        _admission(
            raw=raw,
            endpoint_observation_receipt=receipt,
            endpoint_route_evidence=endpoint,
            model_candidate=candidate,
            model_control_evidence=model,
            policy=_policy(required_parameters=supported_parameters),
        )


def test_explicit_false_max_tokens_reasoning_claim_rejects_emitted_cap() -> None:
    candidate, model = _model_sources(reasoning_supports_max_tokens=False)
    with pytest.raises(ValueError, match="single_call_max_tokens_contradicted"):
        _admission(model_candidate=candidate, model_control_evidence=model)


@pytest.mark.parametrize("claim", (None, True))
def test_missing_or_true_max_tokens_claim_uses_exact_parameter_evidence(
    claim: bool | None,
) -> None:
    candidate, model = _model_sources(reasoning_supports_max_tokens=claim)
    admission, _ = _admission(
        model_candidate=candidate,
        model_control_evidence=model,
    )
    assert admission.mandatory_request_parameters == (
        "max_tokens",
        "reasoning",
    )


def test_null_caps_context_overflow_and_unsafe_price_dimensions_reject() -> None:
    payload = _payload()
    payload["data"]["endpoints"][0]["max_prompt_tokens"] = None
    raw = _raw(payload)
    receipt, endpoint = _endpoint_sources(raw)
    with pytest.raises(ValueError, match="single_call_endpoint_caps_unknown"):
        _admission(
            raw=raw,
            endpoint_observation_receipt=receipt,
            endpoint_route_evidence=endpoint,
        )

    payload = _payload()
    payload["data"]["endpoints"][0]["max_prompt_tokens"] = 1_048_576
    payload["data"]["endpoints"][0]["max_completion_tokens"] = 1_048_576
    raw = _raw(payload)
    receipt, endpoint = _endpoint_sources(raw)
    with pytest.raises(ValueError, match="single_call_context_cap_exceeded"):
        _admission(
            raw=raw,
            endpoint_observation_receipt=receipt,
            endpoint_route_evidence=endpoint,
            policy=_policy(
                max_prompt_tokens=1_047_000,
                max_completion_tokens=2_000,
            ),
            intent=_intent(prompt_token_upper_bound=1_047_000),
        )

    payload = _payload()
    payload["data"]["endpoints"][0]["pricing"]["request"] = "0.01"
    raw = _raw(payload)
    receipt, endpoint = _endpoint_sources(raw)
    with pytest.raises(ValueError, match="single_call_pricing_unsupported"):
        _admission(
            raw=raw,
            endpoint_observation_receipt=receipt,
            endpoint_route_evidence=endpoint,
        )


def test_endpoint_price_supersedes_model_summary_and_respects_policy_caps() -> None:
    candidate, model = _model_sources(prompt_price="0.000004")
    admission, _ = _admission(
        model_candidate=candidate,
        model_control_evidence=model,
    )
    assert admission.model_summary_prompt_price == "0.000004"
    assert admission.prompt_price == "0.000003"
    assert admission.price_reconciliation == (
        "endpoint_specific_supersedes_model_summary"
    )
    assert admission.reserved_upper_cost == "0.09144"

    with pytest.raises(ValueError, match="single_call_price_cap_exceeded"):
        _admission(policy=_policy(max_prompt_price_per_million="2.999999"))


def test_request_price_absence_is_preserved_under_named_schema_policy() -> None:
    payload = _payload()
    payload["data"]["endpoints"][0]["pricing"].pop("request")
    raw = _raw(payload)
    receipt, endpoint = _endpoint_sources(raw)
    admission, _ = _admission(
        raw=raw,
        endpoint_observation_receipt=receipt,
        endpoint_route_evidence=endpoint,
    )
    assert admission.request_price_present is False
    assert admission.request_price == "0"
    assert admission.request_price_schema_policy_accepted is True
    assert admission.request_price_schema_policy_digest == digest_payload(
        {
            "schema_id": (
                "openrouter_public_pricing_request_optional_absence_as_zero.v1"
            ),
            "required": ["prompt", "completion"],
            "request_presence": "optional",
            "absent_request_price": "0",
        }
    )


@pytest.mark.parametrize(
    "field,value",
    (
        ("request_price_present", False),
        ("request_price_schema_policy_accepted", False),
        ("request_price_schema_policy_digest", "sha256:" + "0" * 64),
    ),
)
def test_request_price_schema_proof_is_rehydration_bound(
    field: str, value: object
) -> None:
    admission, values = _admission()
    assert admission.request_price_present is True
    payload = admission.to_dict()
    payload[field] = value
    body = {key: value for key, value in payload.items() if key != "admission_id"}
    payload["admission_id"] = (
        "canonical_single_call_admission:"
        + hashlib.sha256(
            json.dumps(
                body, sort_keys=True, separators=(",", ":"), ensure_ascii=True
            ).encode("utf-8")
        ).hexdigest()
    )
    with pytest.raises(ValueError, match="single_call_admission_invalid"):
        rehydrate_canonical_single_call_admission(payload, **values)


def test_policy_and_intent_time_and_output_use_mismatch_fail_closed() -> None:
    with pytest.raises(ValueError, match="single_call_evidence_stale"):
        _admission(policy=_policy(expires_at_ms=10_000), now_ms=10_001)
    with pytest.raises(ValueError, match="single_call_evidence_stale"):
        _admission(intent=_intent(expires_at_ms=10_000), now_ms=10_001)
    with pytest.raises(ValueError, match="single_call_intent_future"):
        _admission(intent=_intent(issued_at_ms=10_002), now_ms=10_001)
    with pytest.raises(ValueError, match="single_call_intent_invalid"):
        _admission(intent=_intent(output_use="training"))


def test_status_is_required_by_job_policy() -> None:
    payload = _payload()
    payload["data"]["endpoints"][0].pop("status")
    raw = _raw(payload)
    receipt, endpoint = _endpoint_sources(raw)
    with pytest.raises(ValueError, match="single_call_endpoint_status_missing"):
        _admission(
            raw=raw,
            endpoint_observation_receipt=receipt,
            endpoint_route_evidence=endpoint,
        )


@pytest.mark.parametrize("status", (-1, -2, -3, -5, -10))
def test_known_negative_status_fails_job_policy(status: int) -> None:
    payload = _payload()
    payload["data"]["endpoints"][0]["status"] = status
    raw = _raw(payload)
    receipt, endpoint = _endpoint_sources(raw)
    with pytest.raises(
        ValueError, match="single_call_endpoint_status_not_accepted"
    ):
        _admission(
            raw=raw,
            endpoint_observation_receipt=receipt,
            endpoint_route_evidence=endpoint,
        )


@pytest.mark.parametrize(
    "field,value",
    (
        ("endpoint_status", -1),
        ("accepted_endpoint_statuses", [-1]),
        ("endpoint_status_policy_accepted", False),
    ),
)
def test_endpoint_status_policy_is_exact_and_tamper_bound(
    field: str, value: object
) -> None:
    assert _policy().accepted_endpoint_statuses == (0,)
    with pytest.raises(ValueError, match="single_call_policy_invalid"):
        _policy(accepted_endpoint_statuses=(-1,))

    admission, values = _admission()
    payload = admission.to_dict()
    payload[field] = value
    body = {key: value for key, value in payload.items() if key != "admission_id"}
    payload["admission_id"] = (
        "canonical_single_call_admission:"
        + hashlib.sha256(
            json.dumps(
                body, sort_keys=True, separators=(",", ":"), ensure_ascii=True
            ).encode("utf-8")
        ).hexdigest()
    )
    with pytest.raises(ValueError, match="single_call_admission_invalid"):
        rehydrate_canonical_single_call_admission(payload, **values)


def test_admission_rehydration_rebuilds_all_sources_and_rejects_recomputed_id() -> None:
    admission, values = _admission()
    assert (
        rehydrate_canonical_single_call_admission(admission.to_dict(), **values)
        == admission
    )
    payload = admission.to_dict()
    payload["runtime_authority"] = "live"
    body = {key: value for key, value in payload.items() if key != "admission_id"}
    payload["admission_id"] = (
        "canonical_single_call_admission:"
        + hashlib.sha256(
            json.dumps(
                body, sort_keys=True, separators=(",", ":"), ensure_ascii=True
            ).encode("utf-8")
        ).hexdigest()
    )
    with pytest.raises(ValueError, match="single_call_admission_invalid"):
        rehydrate_canonical_single_call_admission(payload, **values)


def test_availability_job_certification_and_training_permission_are_distinct() -> None:
    _, endpoint = _endpoint_sources()
    admission, _ = _admission()
    assert endpoint.trust_class == "provider_asserted_endpoint_route_controls"
    assert admission.trust_class == (
        "trusted_job_policy_over_provider_asserted_route_evidence"
    )
    assert admission.output_use == "evaluation_only"
    assert admission.output_training_permission is False
    assert admission.runtime_authority == "eligibility_only"
