"""Pure builder for one exact configured AutoResearch call eligibility receipt."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Mapping

from .model_autoresearch_single_call_contracts import (
    ADMISSION_ID_PATTERN,
    ADMISSION_KEYS,
    CanonicalSingleCallAdmission,
    CanonicalSingleCallIntent,
    CanonicalSingleCallJobPolicy,
    GATEWAY_BASE_URL,
    HALTED_REASONS,
    HTTP_METHOD,
    MANDATORY_REQUEST_PARAMETERS,
    OMITTED_SAMPLING_PARAMETERS,
    PRICE_RECONCILIATION,
    PUBLIC_PRICING_SCHEMA_POLICY,
    REQUEST_PATH,
    RUNTIME_AUTHORITY,
    SCHEMA_VERSION,
    TRUST_CLASS,
    content_id,
    decimal_text,
    digest_payload,
    frozen,
    is_uint,
)
from .model_openrouter_endpoint_route_evidence import (
    EndpointObservationReceipt,
    OpenRouterEndpointRouteEvidence,
    rehydrate_openrouter_endpoint_route_evidence,
)
from .model_provider_catalog_snapshot import ProviderCatalogCandidateSnapshot
from .model_provider_execution_control_evidence import (
    ProviderModelExecutionControlEvidence,
    rehydrate_provider_model_execution_control_evidence,
)


def build_canonical_single_call_admission(
    *,
    raw_endpoint_payload: bytes,
    endpoint_observation_receipt: EndpointObservationReceipt,
    endpoint_route_evidence: OpenRouterEndpointRouteEvidence,
    model_candidate: ProviderCatalogCandidateSnapshot,
    model_control_evidence: ProviderModelExecutionControlEvidence,
    policy: CanonicalSingleCallJobPolicy,
    intent: CanonicalSingleCallIntent,
    now_ms: int,
) -> CanonicalSingleCallAdmission:
    if not is_uint(now_ms):
        raise ValueError("single_call_admission_invalid")
    endpoint = rehydrate_openrouter_endpoint_route_evidence(
        endpoint_route_evidence.to_dict(),
        raw=raw_endpoint_payload,
        observation_receipt=endpoint_observation_receipt,
        now_ms=now_ms,
    )
    model = rehydrate_provider_model_execution_control_evidence(
        model_control_evidence.to_dict(), candidate=model_candidate, now_ms=now_ms
    )
    job, call = policy.normalized(), intent.normalized()
    _validate_time(job, call, now_ms)
    _validate_identities(endpoint, model, job, call)
    _validate_controls(endpoint, model, job, call)
    pricing = _validated_pricing(endpoint, job, call)
    request_control = _request_control(job, pricing)
    values = _admission_values(
        endpoint, model, job, call, pricing, request_control, now_ms
    )
    return _materialize_admission(values, request_control)


def _materialize_admission(
    values: dict[str, Any], request_control: Mapping[str, Any]
) -> CanonicalSingleCallAdmission:
    admission_id = content_id(
        "canonical_single_call_admission",
        {"schema_version": SCHEMA_VERSION, **values},
    )
    constructor_values = {
        **{
            key: value
            for key, value in values.items()
            if key
            not in {
                "provider",
                "gateway_base_url",
                "http_method",
                "request_path",
                "trust_class",
                "runtime_authority",
            }
        },
        "request_control": frozen(request_control),
    }
    return CanonicalSingleCallAdmission(
        admission_id=admission_id,
        **constructor_values,
    )


def rehydrate_canonical_single_call_admission(
    payload: Mapping[str, Any], **sources: Any
) -> CanonicalSingleCallAdmission:
    if (
        not isinstance(payload, Mapping)
        or set(payload) != ADMISSION_KEYS
        or payload.get("schema_version") != SCHEMA_VERSION
        or not ADMISSION_ID_PATTERN.fullmatch(str(payload.get("admission_id")))
    ):
        raise ValueError("single_call_admission_invalid")
    try:
        expected = build_canonical_single_call_admission(**sources)
    except ValueError as exc:
        if str(exc) in {
            "endpoint_observation_stale",
            "endpoint_observation_future",
            "candidate_snapshot_stale",
            "candidate_snapshot_future_observation",
        }:
            raise
        raise ValueError("single_call_admission_invalid") from None
    if dict(payload) != expected.to_dict():
        raise ValueError("single_call_admission_invalid")
    return expected


def _validate_time(
    policy: CanonicalSingleCallJobPolicy,
    intent: CanonicalSingleCallIntent,
    now_ms: int,
) -> None:
    if now_ms > policy.expires_at_ms or now_ms > intent.expires_at_ms:
        raise ValueError("single_call_evidence_stale")
    if now_ms < intent.issued_at_ms:
        raise ValueError("single_call_intent_future")


def _validate_identities(endpoint, model, policy, intent) -> None:
    if len({endpoint.model_id, model.model_id, policy.model_id, intent.model_id}) != 1:
        raise ValueError("single_call_model_mismatch")
    if endpoint.endpoint_tag != policy.endpoint_tag:
        raise ValueError("single_call_route_ambiguous")
    if policy.task_type != intent.task_type or policy.output_use != intent.output_use:
        raise ValueError("single_call_intent_invalid")
    if policy.require_zdr:
        raise ValueError("single_call_zdr_evidence_missing")
    if policy.output_use == "training":
        raise ValueError("single_call_output_training_permission_missing")
    if policy.enforce_distillable_text:
        raise ValueError("single_call_policy_invalid")


def _validate_controls(endpoint, model, policy, intent) -> None:
    if not endpoint.status_present:
        raise ValueError("single_call_endpoint_status_missing")
    if endpoint.status not in policy.accepted_endpoint_statuses:
        raise ValueError("single_call_endpoint_status_not_accepted")
    if endpoint.max_prompt_tokens is None or endpoint.max_completion_tokens is None:
        raise ValueError("single_call_endpoint_caps_unknown")
    if intent.prompt_token_upper_bound > min(
        policy.max_prompt_tokens, endpoint.max_prompt_tokens
    ):
        raise ValueError("single_call_prompt_cap_exceeded")
    if policy.max_completion_tokens > endpoint.max_completion_tokens:
        raise ValueError("single_call_completion_cap_exceeded")
    if intent.prompt_token_upper_bound + policy.max_completion_tokens > endpoint.context_length:
        raise ValueError("single_call_context_cap_exceeded")
    _validate_top_provider(model, intent, policy)
    required = set(MANDATORY_REQUEST_PARAMETERS)
    if not required.issubset(endpoint.supported_parameters) or not required.issubset(
        model.supported_parameters
    ):
        raise ValueError("single_call_parameter_unsupported")
    _validate_reasoning(model, policy)


def _validate_top_provider(model, intent, policy) -> None:
    top = model.top_provider
    if top is None:
        return
    if top.context_length_present and top.context_length is not None:
        if intent.prompt_token_upper_bound + policy.max_completion_tokens > top.context_length:
            raise ValueError("single_call_context_cap_exceeded")
    if top.max_completion_tokens_present and top.max_completion_tokens is not None:
        if policy.max_completion_tokens > top.max_completion_tokens:
            raise ValueError("single_call_completion_cap_exceeded")


def _validate_reasoning(model, policy) -> None:
    reasoning = model.reasoning
    if (
        reasoning is None
        or not reasoning.supported_efforts_present
        or reasoning.supported_efforts is None
    ):
        raise ValueError("single_call_reasoning_controls_missing")
    if policy.reasoning_effort not in reasoning.supported_efforts:
        raise ValueError("single_call_reasoning_effort_unsupported")
    if reasoning.supports_max_tokens is False:
        raise ValueError("single_call_max_tokens_contradicted")
    if reasoning.mandatory and policy.reasoning_effort == "none":
        raise ValueError("single_call_reasoning_effort_unsupported")


def _validated_pricing(endpoint, policy, intent) -> dict[str, Any]:
    if endpoint.unsafe_cost_dimensions:
        raise ValueError("single_call_pricing_unsupported")
    schema_policy = _public_pricing_schema_policy()
    request_price = endpoint.request_price
    if not endpoint.request_price_present:
        request_price = schema_policy["absent_request_price"]
    if request_price != "0" or policy.max_request_price != "0":
        raise ValueError("single_call_pricing_unsupported")
    prompt_million = _per_million(endpoint.prompt_price)
    completion_million = _per_million(endpoint.completion_price)
    if Decimal(prompt_million) > Decimal(policy.max_prompt_price_per_million):
        raise ValueError("single_call_price_cap_exceeded")
    if Decimal(completion_million) > Decimal(policy.max_completion_price_per_million):
        raise ValueError("single_call_price_cap_exceeded")
    reserved = (
        Decimal(endpoint.prompt_price) * intent.prompt_token_upper_bound
        + Decimal(endpoint.completion_price) * policy.max_completion_tokens
        + Decimal(request_price)
    )
    return {
        "prompt_price_per_million": prompt_million,
        "completion_price_per_million": completion_million,
        "request_price": request_price,
        "request_price_present": endpoint.request_price_present,
        "request_price_schema_policy": PUBLIC_PRICING_SCHEMA_POLICY,
        "request_price_schema_policy_digest": digest_payload(schema_policy),
        "request_price_schema_policy_accepted": True,
        "reserved_upper_cost": decimal_text(reserved),
    }


def _public_pricing_schema_policy() -> dict[str, Any]:
    return {
        "schema_id": PUBLIC_PRICING_SCHEMA_POLICY,
        "required": ["prompt", "completion"],
        "request_presence": "optional",
        "absent_request_price": "0",
    }


def _request_control(policy, pricing) -> dict[str, Any]:
    return {
        "max_tokens": policy.max_completion_tokens,
        "reasoning": {"effort": policy.reasoning_effort},
        "provider": {
            "order": [policy.endpoint_tag],
            "allow_fallbacks": False,
            "require_parameters": True,
            "data_collection": "deny",
            "zdr": False,
            "max_price": {
                "prompt": pricing["prompt_price_per_million"],
                "completion": pricing["completion_price_per_million"],
                "request": pricing["request_price"],
            },
        },
    }


def _admission_values(endpoint, model, policy, intent, pricing, request, now_ms):
    return {
        "provider": "openrouter",
        "model_control_evidence_id": model.evidence_id,
        "model_control_digest": model.source_control_digest,
        "endpoint_route_evidence_id": endpoint.evidence_id,
        "endpoint_record_digest": endpoint.endpoint_record_digest,
        "policy_id": policy.policy_id,
        "intent_id": intent.intent_id,
        "route_contract_digest": _route_contract_digest(),
        "gateway_base_url": GATEWAY_BASE_URL,
        "http_method": HTTP_METHOD,
        "request_path": REQUEST_PATH,
        "model_id": endpoint.model_id,
        "endpoint_tag": endpoint.endpoint_tag,
        "provider_order": (endpoint.endpoint_tag,),
        "allow_fallbacks": False,
        "require_parameters": True,
        "data_collection": "deny",
        "require_zdr": False,
        "enforce_distillable_text": False,
        "reasoning_effort": policy.reasoning_effort,
        "omitted_sampling_parameters": OMITTED_SAMPLING_PARAMETERS,
        "mandatory_request_parameters": MANDATORY_REQUEST_PARAMETERS,
        **_status_proof(endpoint, policy),
        "prompt_token_upper_bound": intent.prompt_token_upper_bound,
        "max_completion_tokens": policy.max_completion_tokens,
        "context_length": endpoint.context_length,
        "max_response_bytes": policy.max_response_bytes,
        "prompt_price": endpoint.prompt_price,
        "completion_price": endpoint.completion_price,
        **pricing,
        "model_summary_prompt_price": model.prompt_price,
        "model_summary_completion_price": model.completion_price,
        "price_reconciliation": PRICE_RECONCILIATION,
        "request_control": request,
        "output_use": "evaluation_only",
        "output_training_permission": False,
        "issued_at_ms": now_ms,
        "fresh_until_ms": min(
            endpoint.fresh_until_ms,
            model.fresh_until_ms,
            policy.expires_at_ms,
            intent.expires_at_ms,
        ),
        "max_calls": 1,
        "halted_reasons": HALTED_REASONS,
        "trust_class": TRUST_CLASS,
        "runtime_authority": RUNTIME_AUTHORITY,
    }


def _status_proof(endpoint, policy) -> dict[str, Any]:
    return {
        "endpoint_status": endpoint.status,
        "accepted_endpoint_statuses": policy.accepted_endpoint_statuses,
        "endpoint_status_policy_accepted": True,
    }


def _route_contract_digest() -> str:
    return digest_payload({
        "gateway_base_url": GATEWAY_BASE_URL,
        "http_method": HTTP_METHOD,
        "request_path": REQUEST_PATH,
        "headers": {
            "Content-Type": "application/json",
            "X-OpenRouter-Metadata": "enabled",
        },
        "stream": False,
    })


def _per_million(value: str) -> str:
    return decimal_text(Decimal(value) * Decimal(1_000_000))


__all__ = [
    "CanonicalSingleCallAdmission",
    "CanonicalSingleCallIntent",
    "CanonicalSingleCallJobPolicy",
    "build_canonical_single_call_admission",
    "rehydrate_canonical_single_call_admission",
]
