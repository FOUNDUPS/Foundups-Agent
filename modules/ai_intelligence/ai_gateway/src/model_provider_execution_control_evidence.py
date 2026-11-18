"""Pure provider-asserted model execution-control evidence boundary."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any, Mapping

from .model_provider_catalog_snapshot import (
    ENDPOINT_ID,
    PROVIDER,
    ProviderCatalogCandidateSnapshot,
    rehydrate_candidate_snapshot,
)


SCHEMA_VERSION = "provider_model_execution_control_evidence.v1"
TRUST_CLASS = "provider_asserted_model_execution_controls"
_EVIDENCE_KEYS = frozenset(
    """schema_version evidence_id provider endpoint_id candidate_snapshot_id
    candidate_payload_digest discovery_receipt_id observed_at_ms fresh_until_ms
    model_id prompt_price completion_price supported_parameters reasoning
    top_provider source_record_digest source_control_digest trust_class""".split()
)
_EVIDENCE_ID = re.compile(
    r"provider_model_execution_control_evidence:[0-9a-f]{64}\Z"
)


@dataclass(frozen=True)
class ProviderModelReasoningControl:
    supported_efforts_present: bool
    supported_efforts: tuple[str, ...] | None
    default_effort_present: bool
    default_effort: str | None
    default_enabled: bool | None
    supports_max_tokens: bool | None
    mandatory: bool | None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        if self.supported_efforts_present:
            result["supported_efforts"] = (
                None
                if self.supported_efforts is None
                else list(self.supported_efforts)
            )
        if self.default_effort_present:
            result["default_effort"] = self.default_effort
        if self.default_enabled is not None:
            result["default_enabled"] = self.default_enabled
        if self.supports_max_tokens is not None:
            result["supports_max_tokens"] = self.supports_max_tokens
        if self.mandatory is not None:
            result["mandatory"] = self.mandatory
        return result


@dataclass(frozen=True)
class ProviderModelTopProviderControl:
    context_length_present: bool
    context_length: int | None
    max_completion_tokens_present: bool
    max_completion_tokens: int | None
    is_moderated: bool | None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        if self.context_length_present:
            result["context_length"] = self.context_length
        if self.max_completion_tokens_present:
            result["max_completion_tokens"] = self.max_completion_tokens
        if self.is_moderated is not None:
            result["is_moderated"] = self.is_moderated
        return result


@dataclass(frozen=True)
class ProviderModelExecutionControlEvidence:
    evidence_id: str
    candidate_snapshot_id: str
    candidate_payload_digest: str
    discovery_receipt_id: str
    observed_at_ms: int
    fresh_until_ms: int
    model_id: str
    prompt_price: str
    completion_price: str
    supported_parameters: tuple[str, ...]
    reasoning: ProviderModelReasoningControl | None
    top_provider: ProviderModelTopProviderControl | None
    source_record_digest: str
    source_control_digest: str
    provider: str = field(init=False, default=PROVIDER)
    endpoint_id: str = field(init=False, default=ENDPOINT_ID)
    trust_class: str = field(init=False, default=TRUST_CLASS)
    schema_version: str = field(init=False, default=SCHEMA_VERSION)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "evidence_id": self.evidence_id,
            "provider": self.provider,
            "endpoint_id": self.endpoint_id,
            "candidate_snapshot_id": self.candidate_snapshot_id,
            "candidate_payload_digest": self.candidate_payload_digest,
            "discovery_receipt_id": self.discovery_receipt_id,
            "observed_at_ms": self.observed_at_ms,
            "fresh_until_ms": self.fresh_until_ms,
            "model_id": self.model_id,
            "prompt_price": self.prompt_price,
            "completion_price": self.completion_price,
            "supported_parameters": list(self.supported_parameters),
            "reasoning": None if self.reasoning is None else self.reasoning.to_dict(),
            "top_provider": (
                None if self.top_provider is None else self.top_provider.to_dict()
            ),
            "source_record_digest": self.source_record_digest,
            "source_control_digest": self.source_control_digest,
            "trust_class": self.trust_class,
        }


def build_provider_model_execution_control_evidence(
    *,
    candidate: ProviderCatalogCandidateSnapshot,
    model_id: str,
    now_ms: int,
) -> ProviderModelExecutionControlEvidence:
    if not isinstance(candidate, ProviderCatalogCandidateSnapshot):
        raise ValueError("candidate_snapshot_invalid")
    canonical = rehydrate_candidate_snapshot(candidate.to_dict(), now_ms=now_ms)
    return _build_from_candidate(canonical, model_id)


def rehydrate_provider_model_execution_control_evidence(
    payload: Mapping[str, Any],
    *,
    candidate: ProviderCatalogCandidateSnapshot,
    now_ms: int,
) -> ProviderModelExecutionControlEvidence:
    if not isinstance(payload, Mapping) or set(payload) != _EVIDENCE_KEYS:
        raise ValueError("execution_control_evidence_invalid")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("execution_control_evidence_invalid")
    if not _EVIDENCE_ID.fullmatch(str(payload.get("evidence_id"))):
        raise ValueError("execution_control_evidence_invalid")
    try:
        expected = build_provider_model_execution_control_evidence(
            candidate=candidate,
            model_id=payload.get("model_id"),  # type: ignore[arg-type]
            now_ms=now_ms,
        )
    except ValueError as exc:
        if str(exc) in {
            "candidate_snapshot_stale",
            "candidate_snapshot_future_observation",
            "candidate_snapshot_invalid",
        }:
            raise
        raise ValueError("execution_control_evidence_invalid") from None
    if dict(payload) != expected.to_dict():
        raise ValueError("execution_control_evidence_invalid")
    return expected


def _build_from_candidate(
    candidate: ProviderCatalogCandidateSnapshot,
    model_id: str,
) -> ProviderModelExecutionControlEvidence:
    record, pricing = _select_record(candidate, model_id)
    reasoning = _reasoning(record.get("reasoning")) if "reasoning" in record else None
    top_provider = (
        _top_provider(record.get("top_provider"))
        if "top_provider" in record
        else None
    )
    parameters = tuple(record["supported_parameters"])
    control = _control_body(
        model_id=model_id,
        prompt_price=pricing["prompt"],
        completion_price=pricing["completion"],
        supported_parameters=parameters,
        reasoning=reasoning,
        top_provider=top_provider,
    )
    values = _evidence_values(
        candidate, control, _sha256(record), _sha256(control)
    )
    identity_body = {
        "schema_version": SCHEMA_VERSION,
        "provider": PROVIDER,
        "endpoint_id": ENDPOINT_ID,
        **values,
        "trust_class": TRUST_CLASS,
    }
    evidence_id = _content_id(
        "provider_model_execution_control_evidence", identity_body
    )
    return ProviderModelExecutionControlEvidence(
        evidence_id=evidence_id,
        candidate_snapshot_id=values["candidate_snapshot_id"],
        candidate_payload_digest=values["candidate_payload_digest"],
        discovery_receipt_id=values["discovery_receipt_id"],
        observed_at_ms=values["observed_at_ms"],
        fresh_until_ms=values["fresh_until_ms"],
        model_id=values["model_id"],
        prompt_price=values["prompt_price"],
        completion_price=values["completion_price"],
        supported_parameters=tuple(values["supported_parameters"]),
        reasoning=reasoning,
        top_provider=top_provider,
        source_record_digest=values["source_record_digest"],
        source_control_digest=values["source_control_digest"],
    )


def _select_record(
    candidate: ProviderCatalogCandidateSnapshot,
    model_id: str,
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    if not isinstance(model_id, str):
        raise ValueError("execution_control_model_missing")
    matches = [
        item
        for item in candidate.catalog_payload["data"]
        if item.get("id") == model_id
    ]
    if len(matches) != 1:
        raise ValueError("execution_control_model_missing")
    record = matches[0]
    pricing = record.get("pricing")
    if (
        not isinstance(pricing, Mapping)
        or set(pricing) != {"prompt", "completion"}
        or not all(isinstance(pricing[key], str) for key in pricing)
    ):
        raise ValueError("execution_control_price_missing")
    return record, pricing


def _control_body(
    *,
    model_id: str,
    prompt_price: str,
    completion_price: str,
    supported_parameters: tuple[str, ...],
    reasoning: ProviderModelReasoningControl | None,
    top_provider: ProviderModelTopProviderControl | None,
) -> dict[str, Any]:
    return {
        "model_id": model_id,
        "prompt_price": prompt_price,
        "completion_price": completion_price,
        "supported_parameters": list(supported_parameters),
        "reasoning": None if reasoning is None else reasoning.to_dict(),
        "top_provider": None if top_provider is None else top_provider.to_dict(),
    }


def _evidence_values(
    candidate: ProviderCatalogCandidateSnapshot,
    control: Mapping[str, Any],
    source_record_digest: str,
    source_control_digest: str,
) -> dict[str, Any]:
    return {
        "candidate_snapshot_id": candidate.snapshot_id,
        "candidate_payload_digest": candidate.catalog_payload_digest,
        "discovery_receipt_id": candidate.observation_receipt.receipt_id,
        "observed_at_ms": candidate.observed_at_ms,
        "fresh_until_ms": candidate.fresh_until_ms,
        "model_id": control["model_id"],
        "prompt_price": control["prompt_price"],
        "completion_price": control["completion_price"],
        "supported_parameters": list(control["supported_parameters"]),
        "reasoning": control["reasoning"],
        "top_provider": control["top_provider"],
        "source_record_digest": source_record_digest,
        "source_control_digest": source_control_digest,
    }


def _reasoning(value: Any) -> ProviderModelReasoningControl:
    if not isinstance(value, Mapping):
        raise ValueError("execution_control_evidence_invalid")
    efforts_present = "supported_efforts" in value
    efforts = value.get("supported_efforts")
    return ProviderModelReasoningControl(
        supported_efforts_present=efforts_present,
        supported_efforts=None if efforts is None else tuple(efforts),
        default_effort_present="default_effort" in value,
        default_effort=value.get("default_effort"),
        default_enabled=value.get("default_enabled"),
        supports_max_tokens=value.get("supports_max_tokens"),
        mandatory=value.get("mandatory"),
    )


def _top_provider(value: Any) -> ProviderModelTopProviderControl:
    if not isinstance(value, Mapping):
        raise ValueError("execution_control_evidence_invalid")
    return ProviderModelTopProviderControl(
        context_length_present="context_length" in value,
        context_length=value.get("context_length"),
        max_completion_tokens_present="max_completion_tokens" in value,
        max_completion_tokens=value.get("max_completion_tokens"),
        is_moderated=value.get("is_moderated"),
    )


def _sha256(value: object) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value)).hexdigest()


def _content_id(prefix: str, value: object) -> str:
    return f"{prefix}:{hashlib.sha256(_canonical(value)).hexdigest()}"


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


__all__ = [
    "ProviderModelExecutionControlEvidence",
    "ProviderModelReasoningControl",
    "ProviderModelTopProviderControl",
    "build_provider_model_execution_control_evidence",
    "rehydrate_provider_model_execution_control_evidence",
]
