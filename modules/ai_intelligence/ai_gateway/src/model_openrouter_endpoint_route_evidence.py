"""Immutable lineage for supplied OpenRouter endpoint route controls."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from .model_openrouter_endpoint_payload_projection import (
    DIGEST_PATTERN,
    MAX_ENDPOINT_RESPONSE_BYTES,
    PAYLOAD_ID_PATTERN,
    content_id,
    digest_payload,
    endpoint_payload_id,
    is_uint,
    parse_and_sanitize_openrouter_endpoint_payload,
    sha256_bytes,
    valid_endpoint_tag,
    valid_model_id,
)


PROVIDER = "openrouter"
ENDPOINT_ID = "openrouter_model_endpoints_api_v1"
OBSERVATION_SCHEMA = "openrouter_endpoint_observation_receipt.v1"
ROUTE_SCHEMA = "openrouter_endpoint_route_evidence.v1"
DEFAULT_ENDPOINT_FRESHNESS_MS = 900_000
TRUST_CLASS = "provider_asserted_endpoint_route_controls"
OBSERVATION_TRUST_CLASS = "provider_asserted_endpoint_observation"
_RECEIPT_ID = re.compile(r"openrouter_endpoint_observation_receipt:[0-9a-f]{64}\Z")
_EVIDENCE_ID = re.compile(r"openrouter_endpoint_route_evidence:[0-9a-f]{64}\Z")
_OBSERVATION_KEYS = frozenset(
    """schema_version receipt_id provider endpoint_id requested_model_id
    request_envelope_digest response_body_digest response_byte_count payload_id
    observed_at_ms fresh_until_ms http_status trust_class""".split()
)
_EVIDENCE_KEYS = frozenset(
    """schema_version evidence_id provider endpoint_id observation_receipt_id
    request_envelope_digest response_body_digest payload_id observed_at_ms
    fresh_until_ms model_id endpoint_tag provider_name context_length
    max_prompt_tokens_present max_prompt_tokens max_completion_tokens_present
    max_completion_tokens prompt_price completion_price request_price_present
    request_price unsafe_cost_dimensions supported_parameters status_present
    status quantization_present quantization supports_implicit_caching
    endpoint_record_digest source_control trust_class""".split()
)


@dataclass(frozen=True)
class EndpointObservationReceipt:
    receipt_id: str
    requested_model_id: str
    request_envelope_digest: str
    response_body_digest: str
    response_byte_count: int
    payload_id: str
    observed_at_ms: int
    fresh_until_ms: int
    http_status: int
    provider: str = field(init=False, default=PROVIDER)
    endpoint_id: str = field(init=False, default=ENDPOINT_ID)
    trust_class: str = field(init=False, default=OBSERVATION_TRUST_CLASS)
    schema_version: str = field(init=False, default=OBSERVATION_SCHEMA)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "receipt_id": self.receipt_id,
            "provider": self.provider,
            "endpoint_id": self.endpoint_id,
            "requested_model_id": self.requested_model_id,
            "request_envelope_digest": self.request_envelope_digest,
            "response_body_digest": self.response_body_digest,
            "response_byte_count": self.response_byte_count,
            "payload_id": self.payload_id,
            "observed_at_ms": self.observed_at_ms,
            "fresh_until_ms": self.fresh_until_ms,
            "http_status": self.http_status,
            "trust_class": self.trust_class,
        }


@dataclass(frozen=True)
class OpenRouterEndpointRouteEvidence:
    evidence_id: str
    observation_receipt_id: str
    request_envelope_digest: str
    response_body_digest: str
    payload_id: str
    observed_at_ms: int
    fresh_until_ms: int
    model_id: str
    endpoint_tag: str
    provider_name: str
    context_length: int
    max_prompt_tokens_present: bool
    max_prompt_tokens: int | None
    max_completion_tokens_present: bool
    max_completion_tokens: int | None
    prompt_price: str
    completion_price: str
    request_price_present: bool
    request_price: str | None
    unsafe_cost_dimensions: tuple[str, ...]
    supported_parameters: tuple[str, ...]
    status_present: bool
    status: int | None
    quantization_present: bool
    quantization: str | None
    supports_implicit_caching: bool
    endpoint_record_digest: str
    source_control: Mapping[str, Any]
    provider: str = field(init=False, default=PROVIDER)
    endpoint_id: str = field(init=False, default=ENDPOINT_ID)
    trust_class: str = field(init=False, default=TRUST_CLASS)
    schema_version: str = field(init=False, default=ROUTE_SCHEMA)

    def to_dict(self) -> dict[str, Any]:
        values = {
            key: getattr(self, key)
            for key in _EVIDENCE_KEYS
            if key not in {"unsafe_cost_dimensions", "supported_parameters", "source_control"}
        }
        values["unsafe_cost_dimensions"] = list(self.unsafe_cost_dimensions)
        values["supported_parameters"] = list(self.supported_parameters)
        values["source_control"] = _mutable(self.source_control)
        return values


def build_endpoint_observation_receipt(
    *,
    requested_model_id: str,
    request_envelope_digest: str,
    response_body_digest: str,
    response_byte_count: int,
    payload_id: str,
    observed_at_ms: int,
    http_status: int,
) -> EndpointObservationReceipt:
    body = _observation_body(
        requested_model_id=requested_model_id,
        request_envelope_digest=request_envelope_digest,
        response_body_digest=response_body_digest,
        response_byte_count=response_byte_count,
        payload_id=payload_id,
        observed_at_ms=observed_at_ms,
        http_status=http_status,
    )
    body["receipt_id"] = content_id("openrouter_endpoint_observation_receipt", body)
    return rehydrate_endpoint_observation_receipt(body)


def rehydrate_endpoint_observation_receipt(
    payload: Mapping[str, Any],
) -> EndpointObservationReceipt:
    if not isinstance(payload, Mapping) or set(payload) != _OBSERVATION_KEYS:
        raise ValueError("endpoint_observation_invalid")
    if payload.get("schema_version") != OBSERVATION_SCHEMA:
        raise ValueError("endpoint_observation_invalid")
    body = _observation_body(**{
        key: payload[key]
        for key in (
            "requested_model_id", "request_envelope_digest",
            "response_body_digest", "response_byte_count", "payload_id",
            "observed_at_ms", "http_status",
        )
    })
    expected = content_id("openrouter_endpoint_observation_receipt", body)
    if payload.get("receipt_id") != expected or dict(payload) != {**body, "receipt_id": expected}:
        raise ValueError("endpoint_observation_invalid")
    return EndpointObservationReceipt(
        receipt_id=expected,
        requested_model_id=body["requested_model_id"],
        request_envelope_digest=body["request_envelope_digest"],
        response_body_digest=body["response_body_digest"],
        response_byte_count=body["response_byte_count"],
        payload_id=body["payload_id"],
        observed_at_ms=body["observed_at_ms"],
        fresh_until_ms=body["fresh_until_ms"],
        http_status=body["http_status"],
    )


def build_openrouter_endpoint_route_evidence(
    *,
    raw: bytes,
    observation_receipt: EndpointObservationReceipt,
    endpoint_tag: str,
    now_ms: int,
) -> OpenRouterEndpointRouteEvidence:
    receipt = _validated_observation(observation_receipt, raw, now_ms)
    payload = parse_and_sanitize_openrouter_endpoint_payload(
        raw, requested_model_id=receipt.requested_model_id
    )
    if endpoint_payload_id(payload) != receipt.payload_id:
        raise ValueError("endpoint_observation_invalid")
    record = _select_route(payload["endpoints"], endpoint_tag)
    values = _evidence_values(receipt, record)
    identity = {
        "schema_version": ROUTE_SCHEMA,
        "provider": PROVIDER,
        "endpoint_id": ENDPOINT_ID,
        **values,
        "trust_class": TRUST_CLASS,
    }
    evidence_id = content_id("openrouter_endpoint_route_evidence", identity)
    source_control = _frozen(values.pop("source_control"))
    return OpenRouterEndpointRouteEvidence(
        evidence_id=evidence_id, source_control=source_control, **values
    )


def rehydrate_openrouter_endpoint_route_evidence(
    payload: Mapping[str, Any],
    *,
    raw: bytes,
    observation_receipt: EndpointObservationReceipt,
    now_ms: int,
) -> OpenRouterEndpointRouteEvidence:
    if not isinstance(payload, Mapping) or set(payload) != _EVIDENCE_KEYS:
        raise ValueError("endpoint_route_evidence_invalid")
    if not _EVIDENCE_ID.fullmatch(str(payload.get("evidence_id"))):
        raise ValueError("endpoint_route_evidence_invalid")
    try:
        expected = build_openrouter_endpoint_route_evidence(
            raw=raw,
            observation_receipt=observation_receipt,
            endpoint_tag=payload.get("endpoint_tag"),  # type: ignore[arg-type]
            now_ms=now_ms,
        )
    except ValueError as exc:
        if str(exc) in {"endpoint_observation_stale", "endpoint_observation_future"}:
            raise
        raise ValueError("endpoint_route_evidence_invalid") from None
    if dict(payload) != expected.to_dict():
        raise ValueError("endpoint_route_evidence_invalid")
    return expected


def _frozen(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _frozen(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_frozen(item) for item in value)
    return value


def _mutable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _mutable(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_mutable(item) for item in value]
    return value


def _observation_body(**values: Any) -> dict[str, Any]:
    if not valid_model_id(values.get("requested_model_id")):
        raise ValueError("endpoint_observation_invalid")
    if not all(
        DIGEST_PATTERN.fullmatch(str(values.get(key)))
        for key in ("request_envelope_digest", "response_body_digest")
    ):
        raise ValueError("endpoint_observation_invalid")
    size, observed, status = (
        values.get("response_byte_count"),
        values.get("observed_at_ms"),
        values.get("http_status"),
    )
    if (
        not is_uint(size)
        or size > MAX_ENDPOINT_RESPONSE_BYTES
        or not is_uint(observed)
        or status != 200
        or not PAYLOAD_ID_PATTERN.fullmatch(str(values.get("payload_id")))
    ):
        raise ValueError("endpoint_observation_invalid")
    return {
        "schema_version": OBSERVATION_SCHEMA,
        "provider": PROVIDER,
        "endpoint_id": ENDPOINT_ID,
        "requested_model_id": values["requested_model_id"],
        "request_envelope_digest": values["request_envelope_digest"],
        "response_body_digest": values["response_body_digest"],
        "response_byte_count": size,
        "payload_id": values["payload_id"],
        "observed_at_ms": observed,
        "fresh_until_ms": observed + DEFAULT_ENDPOINT_FRESHNESS_MS,
        "http_status": 200,
        "trust_class": OBSERVATION_TRUST_CLASS,
    }


def _validated_observation(
    receipt: EndpointObservationReceipt, raw: bytes, now_ms: int
) -> EndpointObservationReceipt:
    if not isinstance(receipt, EndpointObservationReceipt) or not is_uint(now_ms):
        raise ValueError("endpoint_observation_invalid")
    item = rehydrate_endpoint_observation_receipt(receipt.to_dict())
    if now_ms < item.observed_at_ms:
        raise ValueError("endpoint_observation_future")
    if now_ms > item.fresh_until_ms:
        raise ValueError("endpoint_observation_stale")
    if len(raw) != item.response_byte_count or sha256_bytes(raw) != item.response_body_digest:
        raise ValueError("endpoint_observation_invalid")
    return item


def _evidence_values(receipt, record) -> dict[str, Any]:
    return {
        "observation_receipt_id": receipt.receipt_id,
        "request_envelope_digest": receipt.request_envelope_digest,
        "response_body_digest": receipt.response_body_digest,
        "payload_id": receipt.payload_id,
        "observed_at_ms": receipt.observed_at_ms,
        "fresh_until_ms": receipt.fresh_until_ms,
        "model_id": record["model_id"],
        "endpoint_tag": record["tag"],
        "provider_name": record["provider_name"],
        "context_length": record["context_length"],
        "max_prompt_tokens_present": True,
        "max_prompt_tokens": record["max_prompt_tokens"],
        "max_completion_tokens_present": True,
        "max_completion_tokens": record["max_completion_tokens"],
        "prompt_price": record["pricing"]["prompt"],
        "completion_price": record["pricing"]["completion"],
        "request_price_present": "request" in record["pricing"],
        "request_price": record["pricing"].get("request"),
        "unsafe_cost_dimensions": tuple(record["unsafe_cost_dimensions"]),
        "supported_parameters": tuple(record["supported_parameters"]),
        "status_present": "status" in record,
        "status": record.get("status"),
        "quantization_present": True,
        "quantization": record["quantization"],
        "supports_implicit_caching": record["supports_implicit_caching"],
        "endpoint_record_digest": digest_payload(record),
        "source_control": _source_control(record),
    }


def _source_control(record: Mapping[str, Any]) -> dict[str, Any]:
    result = {
        key: record[key]
        for key in (
            "model_id", "tag", "context_length", "max_prompt_tokens",
            "max_completion_tokens", "pricing", "unsafe_cost_dimensions",
            "supported_parameters", "quantization", "supports_implicit_caching",
        )
    }
    if "status" in record:
        result["status"] = record["status"]
    return result


def _select_route(
    endpoints: Sequence[Mapping[str, Any]], endpoint_tag: str
) -> Mapping[str, Any]:
    if not valid_endpoint_tag(endpoint_tag):
        raise ValueError("endpoint_route_missing")
    matches = [item for item in endpoints if item["tag"] == endpoint_tag]
    if len(matches) != 1:
        raise ValueError("endpoint_route_missing")
    if any(item["tag"].startswith(endpoint_tag + "/") for item in endpoints):
        raise ValueError("endpoint_tag_prefix_collision")
    return matches[0]


__all__ = [
    "DEFAULT_ENDPOINT_FRESHNESS_MS",
    "EndpointObservationReceipt",
    "OpenRouterEndpointRouteEvidence",
    "build_endpoint_observation_receipt",
    "build_openrouter_endpoint_route_evidence",
    "endpoint_payload_id",
    "parse_and_sanitize_openrouter_endpoint_payload",
    "rehydrate_endpoint_observation_receipt",
    "rehydrate_openrouter_endpoint_route_evidence",
    "sha256_bytes",
]
