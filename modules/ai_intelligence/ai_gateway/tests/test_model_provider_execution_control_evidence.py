"""Offline contract for provider-asserted model execution-control evidence."""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest

from modules.ai_intelligence.ai_gateway.src.model_provider_catalog_snapshot import (
    DEFAULT_FRESHNESS_MS,
    build_candidate_snapshot,
    build_discovery_invocation,
    build_discovery_receipt,
    candidate_snapshot_id,
    rehydrate_candidate_snapshot,
    sanitize_openrouter_catalog_payload,
    sha256_bytes,
)
from modules.ai_intelligence.ai_gateway.src.model_provider_execution_control_evidence import (
    build_provider_model_execution_control_evidence,
    rehydrate_provider_model_execution_control_evidence,
)


K3_ID = "moonshotai/kimi-k3"


def _k3_row() -> dict:
    return {
        "id": K3_ID,
        "description": "discard provider prose; prices/context match current metadata",
        "context_length": 1_048_576,
        "pricing": {"prompt": "0.0000030", "completion": "0.000015"},
        "architecture": {
            "input_modalities": ["text"],
            "output_modalities": ["text"],
        },
        "supported_parameters": ["reasoning", "max_tokens"],
        "reasoning": {
            "supported_efforts": ["max", "high", "low"],
            "default_effort": "max",
            "default_enabled": True,
            "mandatory": False,
        },
        "top_provider": {
            "context_length": 1_048_576,
            "max_completion_tokens": None,
            "is_moderated": False,
        },
        "default_parameters": {"temperature": 0.7},
        "per_request_limits": {"prompt_tokens": 1},
    }


def _legacy_row() -> dict:
    return {
        "id": "legacy/model",
        "context_length": 8_192,
        "pricing": {"prompt": "0.000001", "completion": "0.000003"},
        "architecture": {
            "input_modalities": ["text"],
            "output_modalities": ["text"],
        },
        "supported_parameters": ["tools"],
    }


def _snapshot(rows: list[dict], *, observed_at_ms: int = 1_000):
    payload, rejected, counts = sanitize_openrouter_catalog_payload({"data": rows})
    snapshot_id = candidate_snapshot_id(payload)
    raw = json.dumps({"data": rows}, sort_keys=True).encode("utf-8")
    receipt = build_discovery_receipt(
        call_id=f"offline-controls-{observed_at_ms}",
        invocation=build_discovery_invocation(mode="manual"),
        request_envelope_digest=sha256_bytes(b"fixed-request"),
        attempted=True,
        outcome="COMPLETED",
        reason="completed",
        started_at_ms=observed_at_ms - 1,
        completed_at_ms=observed_at_ms,
        http_status=200,
        response_body_digest=sha256_bytes(raw),
        response_byte_count=len(raw),
        candidate_snapshot_id=snapshot_id,
        accepted_record_count=len(payload["data"]),
        rejected_record_count=rejected,
        rejection_counts=counts,
    )
    return build_candidate_snapshot(
        catalog_payload=payload,
        rejected_record_count=rejected,
        rejection_counts=counts,
        observed_at_ms=observed_at_ms,
        observation_receipt=receipt,
    )


def _sha256(value: object) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _evidence_id(payload: dict) -> str:
    body = {key: value for key, value in payload.items() if key != "evidence_id"}
    return "provider_model_execution_control_evidence:" + _sha256(body)[7:]


def test_k3_controls_survive_sanitization_and_bind_exact_lineage() -> None:
    candidate = _snapshot([_k3_row()])
    record = candidate.catalog_payload["data"][0]
    assert record["reasoning"] == {
        "supported_efforts": ["max", "high", "low"],
        "default_effort": "max",
        "default_enabled": True,
        "mandatory": False,
    }
    assert record["top_provider"] == {
        "context_length": 1_048_576,
        "max_completion_tokens": None,
        "is_moderated": False,
    }
    assert "description" not in record
    assert "default_parameters" not in record
    assert "per_request_limits" not in record

    evidence = build_provider_model_execution_control_evidence(
        candidate=candidate,
        model_id=K3_ID,
        now_ms=1_001,
    )
    assert evidence.provider == "openrouter"
    assert evidence.endpoint_id == "openrouter_models_api_v1"
    assert evidence.candidate_snapshot_id == candidate.snapshot_id
    assert evidence.candidate_payload_digest == candidate.catalog_payload_digest
    assert evidence.discovery_receipt_id == candidate.observation_receipt.receipt_id
    assert evidence.observed_at_ms == candidate.observed_at_ms
    assert evidence.fresh_until_ms == candidate.fresh_until_ms
    assert evidence.model_id == K3_ID
    assert evidence.prompt_price == "0.000003"
    assert evidence.completion_price == "0.000015"
    assert evidence.supported_parameters == ("max_tokens", "reasoning")
    assert evidence.reasoning is not None
    assert evidence.reasoning.mandatory is False
    assert evidence.top_provider is not None
    assert evidence.top_provider.context_length == 1_048_576
    assert evidence.top_provider.context_length_present is True
    assert evidence.top_provider.max_completion_tokens is None
    assert evidence.top_provider.max_completion_tokens_present is True
    assert evidence.top_provider.to_dict()["max_completion_tokens"] is None
    assert evidence.trust_class == "provider_asserted_model_execution_controls"
    assert rehydrate_provider_model_execution_control_evidence(
        evidence.to_dict(),
        candidate=candidate,
        now_ms=1_001,
    ) == evidence
    with pytest.raises(FrozenInstanceError):
        evidence.model_id = "other/model"  # type: ignore[misc]


def test_legacy_v1_candidate_rehydrates_and_emits_explicit_absent_controls() -> None:
    candidate = _snapshot([_legacy_row()])
    legacy = rehydrate_candidate_snapshot(candidate.to_dict(), now_ms=1_001)
    evidence = build_provider_model_execution_control_evidence(
        candidate=legacy,
        model_id="legacy/model",
        now_ms=1_001,
    )
    assert "reasoning" not in legacy.catalog_payload["data"][0]
    assert "top_provider" not in legacy.catalog_payload["data"][0]
    assert evidence.reasoning is None
    assert evidence.top_provider is None
    assert evidence.to_dict()["reasoning"] is None
    assert evidence.to_dict()["top_provider"] is None


@pytest.mark.parametrize(
    "field,value",
    (
        ("supported_efforts", ["medium", "high"]),
        ("supported_efforts", ["medium", "medium"]),
        ("supported_efforts", ["turbo"]),
        ("supported_efforts", ["max", None]),
        ("supported_efforts", ["max", "xhigh", "high", "medium", "low", "minimal", "none", "none"]),
        ("default_effort", "turbo"),
        ("default_effort", True),
        ("default_enabled", 1),
        ("supports_max_tokens", 0),
        ("mandatory", 1),
    ),
)
def test_reasoning_control_types_bounds_enum_order_and_duplicates_poison(
    field: str, value: object
) -> None:
    row = _k3_row()
    row["reasoning"]["supported_efforts"] = ["high", "medium"]
    row["reasoning"]["default_effort"] = "high"
    row["reasoning"][field] = value
    payload, rejected, counts = sanitize_openrouter_catalog_payload(
        {"data": [_legacy_row(), row]}
    )
    assert [item["id"] for item in payload["data"]] == ["legacy/model"]
    assert rejected == 1
    assert counts == {"record_invalid": 1}


def test_reasoning_default_membership_and_mandatory_semantics_are_exact() -> None:
    missing_default = _k3_row()
    missing_default["reasoning"]["supported_efforts"] = ["medium", "low"]
    missing_default["reasoning"]["default_effort"] = "high"
    mandatory_disabled = _k3_row()
    mandatory_disabled["id"] = "other/model"
    mandatory_disabled["reasoning"]["default_enabled"] = False
    mandatory_disabled["reasoning"]["mandatory"] = True
    mandatory_none = _k3_row()
    mandatory_none["id"] = "third/model"
    mandatory_none["reasoning"]["supported_efforts"] = ["max", "none"]
    mandatory_none["reasoning"]["mandatory"] = True
    mandatory_default_none = _k3_row()
    mandatory_default_none["id"] = "fourth/model"
    mandatory_default_none["reasoning"]["supported_efforts"] = ["none"]
    mandatory_default_none["reasoning"]["default_effort"] = "none"
    mandatory_default_none["reasoning"]["mandatory"] = True
    payload, rejected, counts = sanitize_openrouter_catalog_payload(
        {
            "data": [
                _legacy_row(),
                missing_default,
                mandatory_disabled,
                mandatory_none,
                mandatory_default_none,
            ]
        }
    )
    assert [item["id"] for item in payload["data"]] == ["legacy/model"]
    assert rejected == 4
    assert counts == {"record_invalid": 4}


def test_optional_reasoning_list_and_nonmandatory_disabled_are_preserved() -> None:
    row = _k3_row()
    row["reasoning"] = {
        "supported_efforts": ["max", "xhigh", "high", "medium", "low", "minimal", "none"],
        "default_effort": "medium",
        "default_enabled": False,
        "supports_max_tokens": True,
        "mandatory": False,
    }
    candidate = _snapshot([row])
    evidence = build_provider_model_execution_control_evidence(
        candidate=candidate, model_id=K3_ID, now_ms=1_001
    )
    assert evidence.reasoning is not None
    assert evidence.reasoning.supported_efforts == (
        "max",
        "xhigh",
        "high",
        "medium",
        "low",
        "minimal",
        "none",
    )
    assert evidence.reasoning.default_enabled is False
    assert evidence.reasoning.mandatory is False


def test_null_and_omitted_effort_controls_remain_distinct() -> None:
    null_row = _k3_row()
    null_row["id"] = "synthetic/null-efforts"
    null_row["reasoning"] = {
        "supported_efforts": None,
        "default_effort": "high",
        "default_enabled": True,
        "mandatory": False,
    }
    omitted_row = _k3_row()
    omitted_row["id"] = "synthetic/omitted-efforts"
    omitted_row["reasoning"] = {
        "default_effort": "high",
        "default_enabled": True,
        "mandatory": False,
        "provider_note": "drop me",
    }
    candidate = _snapshot([null_row, omitted_row])
    null_evidence = build_provider_model_execution_control_evidence(
        candidate=candidate, model_id="synthetic/null-efforts", now_ms=1_001
    )
    omitted_evidence = build_provider_model_execution_control_evidence(
        candidate=candidate, model_id="synthetic/omitted-efforts", now_ms=1_001
    )
    assert null_evidence.reasoning is not None
    assert null_evidence.reasoning.supported_efforts_present is True
    assert null_evidence.reasoning.supported_efforts is None
    assert null_evidence.reasoning.supports_max_tokens is None
    assert null_evidence.reasoning.to_dict()["supported_efforts"] is None
    assert "supports_max_tokens" not in null_evidence.reasoning.to_dict()
    assert omitted_evidence.reasoning is not None
    assert omitted_evidence.reasoning.supported_efforts_present is False
    assert "supported_efforts" not in omitted_evidence.reasoning.to_dict()
    assert "supports_max_tokens" not in omitted_evidence.reasoning.to_dict()


def test_null_and_omitted_default_effort_remain_distinct() -> None:
    null_row = _k3_row()
    null_row["id"] = "synthetic/null-default-effort"
    null_row["reasoning"] = {"mandatory": False, "default_effort": None}
    omitted_row = _k3_row()
    omitted_row["id"] = "synthetic/omitted-default-effort"
    omitted_row["reasoning"] = {"mandatory": False}
    candidate = _snapshot([null_row, omitted_row])
    null_evidence = build_provider_model_execution_control_evidence(
        candidate=candidate, model_id="synthetic/null-default-effort", now_ms=1_001
    )
    omitted_evidence = build_provider_model_execution_control_evidence(
        candidate=candidate,
        model_id="synthetic/omitted-default-effort",
        now_ms=1_001,
    )
    assert null_evidence.reasoning is not None
    assert null_evidence.reasoning.default_effort_present is True
    assert null_evidence.reasoning.default_effort is None
    assert null_evidence.reasoning.to_dict()["default_effort"] is None
    assert omitted_evidence.reasoning is not None
    assert omitted_evidence.reasoning.default_effort_present is False
    assert "default_effort" not in omitted_evidence.reasoning.to_dict()


@pytest.mark.parametrize(
    ("reasoning", "expected"),
    (
        ({"supported_efforts": []}, {"supported_efforts": []}),
        ({"supported_efforts": None}, {"supported_efforts": None}),
        ({"default_effort": "high"}, {"default_effort": "high"}),
        ({"default_enabled": False}, {"default_enabled": False}),
        ({"supports_max_tokens": True}, {"supports_max_tokens": True}),
        ({"mandatory": True}, {"mandatory": True}),
        (
            {"supported_efforts": None, "mandatory": True},
            {"supported_efforts": None, "mandatory": True},
        ),
    ),
)
def test_partial_reasoning_assertions_remain_candidate_evidence(
    reasoning: dict, expected: dict
) -> None:
    row = _k3_row()
    row["reasoning"] = reasoning
    candidate = _snapshot([row])
    evidence = build_provider_model_execution_control_evidence(
        candidate=candidate, model_id=K3_ID, now_ms=1_001
    )
    assert candidate.catalog_payload["data"][0]["reasoning"] == expected
    assert evidence.reasoning is not None
    assert evidence.reasoning.to_dict() == expected


def test_unknown_only_reasoning_projection_is_omitted() -> None:
    row = _k3_row()
    row["reasoning"] = {"provider_note": "ignored"}
    candidate = _snapshot([row])
    evidence = build_provider_model_execution_control_evidence(
        candidate=candidate, model_id=K3_ID, now_ms=1_001
    )
    assert "reasoning" not in candidate.catalog_payload["data"][0]
    assert evidence.reasoning is None


@pytest.mark.parametrize(
    "top_provider",
    (
        {"context_length": True},
        {"context_length": 0},
        {"context_length": 100_000_001},
        {"max_completion_tokens": True},
        {"max_completion_tokens": 0},
        {"max_completion_tokens": 100_000_001},
        {"context_length": 1_000, "max_completion_tokens": 1_001},
        {"is_moderated": 1},
    ),
)
def test_top_provider_recognized_bool_cap_and_relationship_values_poison(
    top_provider: object,
) -> None:
    row = _k3_row()
    row["top_provider"] = top_provider
    payload, rejected, counts = sanitize_openrouter_catalog_payload(
        {"data": [_legacy_row(), row]}
    )
    assert [item["id"] for item in payload["data"]] == ["legacy/model"]
    assert rejected == 1
    assert counts == {"record_invalid": 1}


def test_top_provider_null_and_omitted_numeric_claims_remain_distinct() -> None:
    nullable = _k3_row()
    nullable["id"] = "synthetic/nullable-top-provider"
    nullable["top_provider"] = {
        "context_length": None,
        "max_completion_tokens": None,
        "is_moderated": False,
    }
    omitted = _k3_row()
    omitted["id"] = "synthetic/omitted-top-provider"
    omitted["top_provider"] = {"is_moderated": False}
    candidate = _snapshot([nullable, omitted])
    nullable_evidence = build_provider_model_execution_control_evidence(
        candidate=candidate,
        model_id="synthetic/nullable-top-provider",
        now_ms=1_001,
    )
    omitted_evidence = build_provider_model_execution_control_evidence(
        candidate=candidate,
        model_id="synthetic/omitted-top-provider",
        now_ms=1_001,
    )
    assert nullable_evidence.top_provider is not None
    assert nullable_evidence.top_provider.context_length_present is True
    assert nullable_evidence.top_provider.max_completion_tokens_present is True
    assert nullable_evidence.top_provider.to_dict()["context_length"] is None
    assert nullable_evidence.top_provider.to_dict()["max_completion_tokens"] is None
    assert omitted_evidence.top_provider is not None
    assert omitted_evidence.top_provider.context_length_present is False
    assert omitted_evidence.top_provider.max_completion_tokens_present is False
    assert "context_length" not in omitted_evidence.top_provider.to_dict()
    assert "max_completion_tokens" not in omitted_evidence.top_provider.to_dict()


def test_unknown_control_fields_are_dropped_without_leak_or_poison() -> None:
    row = _k3_row()
    row["reasoning"]["provider_note"] = "drop reasoning prose"
    row["top_provider"].update(
        {
            "provider_name": "drop-provider",
            "api_key": "sensitive-provider-value",
            "default_parameters": {"temperature": 0.7},
            "per_request_limits": {"prompt_tokens": 1},
        }
    )
    candidate = _snapshot([row])
    record = candidate.catalog_payload["data"][0]
    serialized = json.dumps(record, sort_keys=True)
    assert "provider_note" not in serialized
    assert "provider_name" not in serialized
    assert "api_key" not in serialized
    assert "sensitive-provider-value" not in serialized
    assert "default_parameters" not in serialized
    assert "per_request_limits" not in serialized

    unknown_only = _k3_row()
    unknown_only["id"] = "synthetic/unknown-top-provider"
    unknown_only["top_provider"] = {"provider_name": "drop-me"}
    candidate = _snapshot([unknown_only])
    assert "top_provider" not in candidate.catalog_payload["data"][0]


def test_duplicate_control_groups_collapse_conflict_and_poison() -> None:
    first = _k3_row()
    identical = copy.deepcopy(first)
    identical["top_provider"]["provider_name"] = "ignored-before-equality"
    collapsed, rejected, counts = sanitize_openrouter_catalog_payload(
        {"data": [first, identical]}
    )
    assert [item["id"] for item in collapsed["data"]] == [K3_ID]
    assert rejected == 1
    assert counts == {"duplicate_identical_collapsed": 1}

    conflict = copy.deepcopy(first)
    conflict["reasoning"]["default_effort"] = "high"
    conflict["reasoning"]["supported_efforts"] = ["max", "high"]
    payload, rejected, counts = sanitize_openrouter_catalog_payload(
        {"data": [_legacy_row(), first, conflict]}
    )
    assert [item["id"] for item in payload["data"]] == ["legacy/model"]
    assert rejected == 2
    assert counts == {"duplicate_id_conflict": 2}

    poisoned = copy.deepcopy(first)
    poisoned["top_provider"]["context_length"] = True
    payload, rejected, counts = sanitize_openrouter_catalog_payload(
        {"data": [_legacy_row(), first, poisoned]}
    )
    assert [item["id"] for item in payload["data"]] == ["legacy/model"]
    assert rejected == 2
    assert counts == {"duplicate_group_poisoned": 2}


@pytest.mark.parametrize(
    "model_id",
    (
        "moonshotai/Kimi-k3",
        "moonshotai/kimi-k3:free",
        "openrouter/moonshotai/kimi-k3",
        "moonshotai/kimi-k3 ",
    ),
)
def test_exact_model_case_and_alias_mismatch_reject(model_id: str) -> None:
    candidate = _snapshot([_k3_row()])
    with pytest.raises(ValueError, match="model_missing"):
        build_provider_model_execution_control_evidence(
            candidate=candidate,
            model_id=model_id,
            now_ms=1_001,
        )


def test_stale_future_and_tampered_candidate_reject() -> None:
    candidate = _snapshot([_k3_row()])
    with pytest.raises(ValueError, match="candidate_snapshot_stale"):
        build_provider_model_execution_control_evidence(
            candidate=candidate,
            model_id=K3_ID,
            now_ms=1_000 + DEFAULT_FRESHNESS_MS + 1,
        )
    with pytest.raises(ValueError, match="candidate_snapshot_future_observation"):
        build_provider_model_execution_control_evidence(
            candidate=candidate,
            model_id=K3_ID,
            now_ms=999,
        )
    tampered = replace(candidate, catalog_payload_digest="sha256:" + "0" * 64)
    with pytest.raises(ValueError, match="candidate_snapshot_invalid"):
        build_provider_model_execution_control_evidence(
            candidate=tampered,
            model_id=K3_ID,
            now_ms=1_001,
        )


def test_source_record_and_control_digests_are_exact() -> None:
    candidate = _snapshot([_k3_row()])
    evidence = build_provider_model_execution_control_evidence(
        candidate=candidate,
        model_id=K3_ID,
        now_ms=1_001,
    )
    record = candidate.catalog_payload["data"][0]
    control = {
        "model_id": K3_ID,
        "prompt_price": "0.000003",
        "completion_price": "0.000015",
        "supported_parameters": ["max_tokens", "reasoning"],
        "reasoning": record["reasoning"],
        "top_provider": record["top_provider"],
    }
    assert evidence.source_record_digest == _sha256(record)
    assert evidence.source_control_digest == _sha256(control)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("provider", "openai"),
        ("endpoint_id", "alias"),
        ("candidate_snapshot_id", "model_provider_catalog_candidate_snapshot:" + "0" * 64),
        ("candidate_payload_digest", "sha256:" + "0" * 64),
        ("discovery_receipt_id", "model_provider_catalog_discovery_receipt:" + "0" * 64),
        ("observed_at_ms", 999),
        ("fresh_until_ms", 1_001),
        ("model_id", "other/model"),
        ("prompt_price", "0.5"),
        ("completion_price", "0.5"),
        ("supported_parameters", []),
        ("reasoning", None),
        ("top_provider", None),
        ("source_record_digest", "sha256:" + "0" * 64),
        ("source_control_digest", "sha256:" + "0" * 64),
        ("trust_class", "canonical_route_admission"),
    ),
)
def test_evidence_tamper_rejects_even_when_attacker_recomputes_id(
    field: str, value: object
) -> None:
    candidate = _snapshot([_k3_row()])
    evidence = build_provider_model_execution_control_evidence(
        candidate=candidate,
        model_id=K3_ID,
        now_ms=1_001,
    )
    payload = copy.deepcopy(evidence.to_dict())
    payload[field] = value
    payload["evidence_id"] = _evidence_id(payload)
    with pytest.raises(ValueError, match="execution_control_evidence_invalid"):
        rehydrate_provider_model_execution_control_evidence(
            payload,
            candidate=candidate,
            now_ms=1_001,
        )


def test_evidence_missing_extra_fields_and_id_mismatch_reject() -> None:
    candidate = _snapshot([_k3_row()])
    evidence = build_provider_model_execution_control_evidence(
        candidate=candidate,
        model_id=K3_ID,
        now_ms=1_001,
    )
    missing = evidence.to_dict()
    missing.pop("reasoning")
    extra = evidence.to_dict()
    extra["description"] = "not allowlisted"
    mismatch = evidence.to_dict()
    mismatch["evidence_id"] = "provider_model_execution_control_evidence:" + "0" * 64
    for payload in (missing, extra, mismatch):
        with pytest.raises(ValueError, match="execution_control_evidence_invalid"):
            rehydrate_provider_model_execution_control_evidence(
                payload,
                candidate=candidate,
                now_ms=1_001,
            )


def test_execution_control_module_has_zero_network_or_caller_surface() -> None:
    path = (
        "modules/ai_intelligence/ai_gateway/src/"
        "model_provider_execution_control_evidence.py"
    )
    source = Path(path).read_text(encoding="utf-8")
    assert not {
        "requests",
        "aiohttp",
        "urllib",
        "socket",
        "subprocess",
        "AIGateway",
        "call_model",
    }.intersection(source.split())
