"""Offline tests for the direct-provider candidate snapshot trust boundary."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from modules.ai_intelligence.ai_gateway.src.model_intelligence_catalog import Availability
from modules.ai_intelligence.ai_gateway.src.model_provider_catalog_snapshot import (
    DEFAULT_FRESHNESS_MS,
    admit_discovery_invocation,
    bridge_candidate_to_canonical_catalog,
    build_candidate_snapshot,
    build_discovery_invocation,
    build_discovery_receipt,
    candidate_snapshot_id,
    parse_and_sanitize_openrouter_catalog,
    rehydrate_candidate_snapshot,
    sanitize_openrouter_catalog_payload,
    sha256_bytes,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _raw(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def _candidate(raw: bytes, *, completed: int = 1_000):
    payload, rejected, counts = parse_and_sanitize_openrouter_catalog(raw)
    invocation = build_discovery_invocation(mode="manual")
    snapshot_id = candidate_snapshot_id(payload)
    receipt = build_discovery_receipt(
        call_id=f"offline-{completed}",
        invocation=invocation,
        request_envelope_digest=sha256_bytes(b"fixed-request"),
        attempted=True,
        outcome="COMPLETED",
        reason="completed",
        started_at_ms=completed - 1,
        completed_at_ms=completed,
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
        observed_at_ms=completed,
        observation_receipt=receipt,
    )


def test_success_fixture_is_allowlisted_canonical_and_sorted() -> None:
    payload, rejected, counts = parse_and_sanitize_openrouter_catalog(
        _raw("openrouter_models_success.json")
    )

    assert rejected == 0
    assert counts == {}
    assert [item["id"] for item in payload["data"]] == [
        "alpha/model-a:free",
        "zeta/model-b",
    ]
    zeta = payload["data"][1]
    assert zeta["pricing"] == {"completion": "0.000015", "prompt": "0.000003"}
    assert zeta["architecture"]["input_modalities"] == ["image", "text"]
    assert zeta["supported_parameters"] == ["response_format", "tools"]
    assert set(zeta) == {
        "id", "context_length", "pricing", "architecture", "supported_parameters"
    }
    assert "name" not in json.dumps(payload)
    assert "top_provider" not in json.dumps(payload)


def test_duplicate_groups_collapse_conflict_and_poison_fail_closed() -> None:
    identical, rejected, counts = parse_and_sanitize_openrouter_catalog(
        _raw("openrouter_models_duplicate_identical.json")
    )
    assert [item["id"] for item in identical["data"]] == ["publisher/model"]
    assert rejected == 1
    assert counts == {"duplicate_identical_collapsed": 1}

    conflict, rejected, counts = parse_and_sanitize_openrouter_catalog(
        _raw("openrouter_models_duplicate_conflict.json")
    )
    assert [item["id"] for item in conflict["data"]] == ["safe/model"]
    assert rejected == 2
    assert counts == {"duplicate_id_conflict": 2}

    poison, rejected, counts = parse_and_sanitize_openrouter_catalog(
        _raw("openrouter_models_poison.json")
    )
    assert [item["id"] for item in poison["data"]] == ["safe/model"]
    assert rejected == 4
    assert counts == {"duplicate_group_poisoned": 2, "record_invalid": 2}


@pytest.mark.parametrize(
    "raw,reason",
    [
        (b'{"data":[],"data":[]}', "json_invalid"),
        (_raw("openrouter_models_invalid_constants.txt"), "json_invalid"),
        (b'{"data":{}}', "top_level_invalid"),
        (b'{"data":[]}', "no_acceptable_records"),
    ],
)
def test_strict_json_and_zero_accepted_fail_with_content_free_reason(
    raw: bytes, reason: str
) -> None:
    with pytest.raises(ValueError, match=f"^{reason}$"):
        parse_and_sanitize_openrouter_catalog(raw)


def test_record_scalar_bounds_and_secret_shaped_ids_are_rejected() -> None:
    payload, rejected, counts = sanitize_openrouter_catalog_payload(
        {
            "data": [
                {"id": "safe/model", "context_length": 1},
                {"id": "upper/Model", "context_length": 1},
                {"id": " spaced/model", "context_length": 1},
                {"id": "secret/sk-abcdefghijklmnopqrstuvwxyz", "context_length": 1},
                {"id": "bad/bool", "context_length": True},
                {"id": "bad/price", "pricing": {"prompt": "1e-6"}},
            ]
        }
    )
    assert [item["id"] for item in payload["data"]] == ["safe/model"]
    assert rejected == 5
    assert counts == {"record_invalid": 5}


def test_model_ids_require_exact_bounded_lowercase_publisher_model_segments() -> None:
    publisher64 = "p" * 64
    model128 = "m" * 128
    invalid = [
        "/model", "publisher/", "publisher//model", "publisher/model/extra",
        "./model", "../model", "publisher/.", "publisher/..",
        "Publisher/model", "publisher/Model", "publisher/model:FREE",
        "publisher/model:paid", "publisher/../model", f"{'p' * 65}/model",
        f"publisher/{'m' * 129}",
    ]
    payload, rejected, counts = sanitize_openrouter_catalog_payload(
        {"data": [
            {"id": "publisher/model"}, {"id": "publisher/model:free"},
            {"id": f"{publisher64}/{model128}"},
            *({"id": model_id} for model_id in invalid),
        ]}
    )
    assert [item["id"] for item in payload["data"]] == [
        f"{publisher64}/{model128}", "publisher/model", "publisher/model:free"
    ]
    assert rejected == len(invalid)
    assert counts == {"record_invalid": len(invalid)}


def test_content_id_excludes_observation_time_and_rehydration_detects_tamper() -> None:
    raw = _raw("openrouter_models_success.json")
    first = _candidate(raw, completed=1_000)
    second = _candidate(raw, completed=2_000)

    assert first.snapshot_id == second.snapshot_id
    assert first.observation_receipt.receipt_id != second.observation_receipt.receipt_id
    assert rehydrate_candidate_snapshot(first.to_dict(), now_ms=1_001) == first

    bad_payload = copy.deepcopy(first.to_dict())
    bad_payload["catalog_payload"]["data"][0]["context_length"] = 99
    with pytest.raises(ValueError):
        rehydrate_candidate_snapshot(bad_payload, now_ms=1_001)

    bad_receipt = copy.deepcopy(first.to_dict())
    bad_receipt["observation_receipt"]["receipt_id"] = "tampered"
    with pytest.raises(ValueError):
        rehydrate_candidate_snapshot(bad_receipt, now_ms=1_001)

    with pytest.raises(ValueError, match="candidate_snapshot_stale"):
        rehydrate_candidate_snapshot(
            first.to_dict(), now_ms=first.observed_at_ms + DEFAULT_FRESHNESS_MS + 1
        )


def test_candidate_rehydration_rejects_future_observation_and_invalid_interval() -> None:
    candidate = _candidate(_raw("openrouter_models_success.json"))
    future = copy.deepcopy(candidate.to_dict())
    future["observed_at_ms"] = 1_002
    future["fresh_until_ms"] = 1_002 + DEFAULT_FRESHNESS_MS
    with pytest.raises(ValueError, match="candidate_snapshot_future_observation"):
        rehydrate_candidate_snapshot(future, now_ms=1_001)

    interval = copy.deepcopy(candidate.to_dict())
    interval["fresh_until_ms"] = interval["observed_at_ms"] - 1
    with pytest.raises(ValueError, match="candidate_snapshot_invalid"):
        rehydrate_candidate_snapshot(interval, now_ms=1_001)


@pytest.mark.parametrize(
    "changes",
    [
        {"attempted": False},
        {"reason": "transport_pending"},
        {"http_status": 201},
        {"response_body_digest": None, "response_byte_count": None},
        {"candidate_snapshot_id": "other_receipt:" + "0" * 64},
        {"accepted_record_count": 0},
        {"completed_at_ms": -1},
    ],
)
def test_completed_receipt_requires_exact_terminal_evidence(changes) -> None:
    candidate = _candidate(_raw("openrouter_models_success.json"))
    values = candidate.observation_receipt.to_dict()
    values.update(changes)
    values.pop("receipt_id")
    with pytest.raises(ValueError, match="discovery_receipt_invalid"):
        build_discovery_receipt(**values)


@pytest.mark.parametrize(
    "outcome,attempted,reason,details",
    [
        ("BLOCKED_PRECALL", False, "precall_intent", {"http_status": 200}),
        ("INDETERMINATE", False, "transport_pending", {}),
        ("INDETERMINATE", True, "precall_intent", {}),
        ("FAILED", False, "transport_failed", {}),
        ("FAILED", True, "transport_failed", {
            "candidate_snapshot_id": "model_provider_catalog_candidate_snapshot:" + "0" * 64,
        }),
    ],
)
def test_noncompleted_receipts_reject_incoherent_state(
    outcome: str, attempted: bool, reason: str, details: dict
) -> None:
    with pytest.raises(ValueError, match="discovery_receipt_invalid"):
        build_discovery_receipt(
            call_id="offline-incoherent",
            invocation=build_discovery_invocation(mode="manual"),
            request_envelope_digest=sha256_bytes(b"request"),
            attempted=attempted,
            outcome=outcome,
            reason=reason,
            started_at_ms=1,
            completed_at_ms=2,
            **details,
        )


@pytest.mark.parametrize(
    "reason,details",
    [
        ("redirect_rejected", {"http_status": 200, "response_body_digest": sha256_bytes(b"x"), "response_byte_count": 1}),
        ("redirect_rejected", {"http_status": 302}),
        ("http_status_rejected", {"http_status": 200, "response_body_digest": sha256_bytes(b"x"), "response_byte_count": 1}),
        ("http_status_rejected", {"http_status": 302, "response_body_digest": sha256_bytes(b"x"), "response_byte_count": 1}),
        ("content_type_rejected", {"http_status": 415, "response_body_digest": sha256_bytes(b"x"), "response_byte_count": 1}),
        ("json_invalid", {"http_status": 500, "response_body_digest": sha256_bytes(b"x"), "response_byte_count": 1}),
        ("transport_failed", {"http_status": 500, "response_body_digest": sha256_bytes(b"x"), "response_byte_count": 1}),
        ("body_too_large", {"http_status": 200, "response_body_digest": sha256_bytes(b"x"), "response_byte_count": 1}),
        ("candidate_write_failed", {}),
    ],
)
def test_failed_receipt_reason_requires_coherent_transport_evidence(
    reason: str, details: dict
) -> None:
    with pytest.raises(ValueError, match="discovery_receipt_invalid"):
        build_discovery_receipt(
            call_id="offline-reason-evidence",
            invocation=build_discovery_invocation(mode="manual"),
            request_envelope_digest=sha256_bytes(b"request"),
            attempted=True,
            outcome="FAILED",
            reason=reason,
            started_at_ms=1,
            completed_at_ms=2,
            **details,
        )


@pytest.mark.parametrize(
    "reason,details",
    [
        ("redirect_rejected", {"http_status": 302, "response_body_digest": sha256_bytes(b"x"), "response_byte_count": 1}),
        ("http_status_rejected", {"http_status": 503, "response_body_digest": sha256_bytes(b"x"), "response_byte_count": 1}),
        ("content_type_rejected", {"http_status": 200, "response_body_digest": sha256_bytes(b"x"), "response_byte_count": 1}),
        ("json_invalid", {"http_status": 200, "response_body_digest": sha256_bytes(b"x"), "response_byte_count": 1}),
        ("transport_timeout", {}),
        ("body_too_large", {"http_status": 200}),
        ("candidate_write_failed", {"http_status": 200, "response_body_digest": sha256_bytes(b"x"), "response_byte_count": 1}),
    ],
)
def test_failed_receipt_accepts_only_reason_specific_evidence(
    reason: str, details: dict
) -> None:
    receipt = build_discovery_receipt(
        call_id="offline-valid-reason-evidence",
        invocation=build_discovery_invocation(mode="manual"),
        request_envelope_digest=sha256_bytes(b"request"),
        attempted=True,
        outcome="FAILED",
        reason=reason,
        started_at_ms=1,
        completed_at_ms=2,
        **details,
    )
    assert receipt.reason == reason


def test_bridge_is_freshness_checked_idempotent_and_does_not_merge_static() -> None:
    candidate = _candidate(_raw("openrouter_models_success.json"))
    built = bridge_candidate_to_canonical_catalog(candidate, now_ms=1_001)

    assert built.catalog_build_required is True
    assert built.catalog_snapshot is not None
    assert len(built.catalog_snapshot.cards) == 2
    assert set(built.catalog_snapshot.source_receipts) == {
        candidate.observation_receipt.receipt_id
    }
    for card in built.catalog_snapshot.cards:
        assert card.provider == "openrouter"
        assert card.availability == Availability.UNKNOWN
        assert card.freshness == "provider_catalog_listing"
        assert card.privacy_policy == "provider_policy_unknown"
        assert card.task_families == ()

    unchanged = bridge_candidate_to_canonical_catalog(
        candidate,
        now_ms=1_001,
        prior_admitted_candidate_id=candidate.snapshot_id,
    )
    assert unchanged.catalog_build_required is False
    assert unchanged.catalog_snapshot is None
    with pytest.raises(ValueError, match="prior_candidate_id_invalid"):
        bridge_candidate_to_canonical_catalog(
            candidate,
            now_ms=1_001,
            prior_admitted_candidate_id="model_provider_catalog_discovery_receipt:" + "0" * 64,
        )


def test_scheduled_invocation_admission_is_inclusive_and_digest_bound() -> None:
    invocation = build_discovery_invocation(
        mode="scheduled",
        schedule_id="daily",
        scheduled_for_ms=100,
        expires_at_ms=200,
    )
    admit_discovery_invocation(invocation, now_ms=100)
    admit_discovery_invocation(invocation, now_ms=200)
    with pytest.raises(ValueError, match="scheduled_invocation_not_due"):
        admit_discovery_invocation(invocation, now_ms=99)
    with pytest.raises(ValueError, match="scheduled_invocation_expired"):
        admit_discovery_invocation(invocation, now_ms=201)
