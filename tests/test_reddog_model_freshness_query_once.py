"""Contract tests for the explicit RedDog model-freshness query."""

from __future__ import annotations

import asyncio

import scripts.reddog_model_freshness_query_once as subject
from scripts.reddog_model_freshness_query_once import (
    _digest,
    _model_rows,
    _rejection_reasons,
)


def test_model_rows_distinguish_availability_from_provider_recency() -> None:
    records = [
        {
            "id": "provider/model-2",
            "canonical_slug": "provider/model-2-20260702",
            "created": 200,
        },
        {
            "id": "provider/model-1",
            "canonical_slug": "provider/model-1-20260701",
            "created": 100,
        },
    ]

    rows = _model_rows(records, ("provider/model-1", "provider/model-2"))

    assert rows[0]["available"] is True
    assert rows[0]["chronology_known"] is True
    assert rows[0]["provider_latest_known"] is False
    assert rows[0]["newer_provider_model_ids"] == ["provider/model-2"]
    assert rows[1]["provider_latest_known"] is True


def test_model_rows_fail_closed_when_release_chronology_is_missing() -> None:
    rows = _model_rows([{"id": "provider/model-1"}], ("provider/model-1",))

    assert rows[0]["available"] is True
    assert rows[0]["chronology_known"] is False
    assert rows[0]["provider_latest_known"] is False
    assert rows[0]["newer_provider_model_ids"] == []


def test_receipt_digest_is_order_independent() -> None:
    assert _digest({"a": 1, "b": 2}) == _digest({"b": 2, "a": 1})


def test_chronology_failure_is_distinct_from_unavailable_model() -> None:
    assert _rejection_reasons("completed", True, True, False) == [
        "provider_chronology_incomplete"
    ]
    assert _rejection_reasons("completed", True, False, False) == [
        "configured_model_unavailable"
    ]


def test_incomplete_chronology_cannot_emit_accepted_receipt(
    monkeypatch,
    tmp_path,
) -> None:
    class Receipt:
        outcome = "COMPLETED"
        attempted = True
        reason = "completed"
        receipt_id = "model_provider_catalog_discovery_receipt:" + ("a" * 64)

    class Candidate:
        snapshot_id = "model_provider_catalog_candidate_snapshot:" + ("b" * 64)
        observed_at_ms = 100
        fresh_until_ms = 10_000
        catalog_payload = {"data": [{"id": "provider/model-1"}]}

    async def discover(*_args, **_kwargs):
        return type("Result", (), {"receipt": Receipt(), "candidate": Candidate()})()

    monkeypatch.setattr(subject, "discover_openrouter_model_catalog", discover)
    monkeypatch.setattr(subject.os, "environ", {"USERPROFILE": str(tmp_path)})

    result = asyncio.run(subject._query(("provider/model-1",)))

    assert result["accepted"] is False
    assert result["status"] == "MODEL_FRESHNESS_NOT_READY"
    assert result["chronology_complete"] is False


def test_credential_bearing_environment_blocks_before_catalog_call(
    monkeypatch,
) -> None:
    monkeypatch.setattr(subject.os, "environ", {"OPENROUTER_API_KEY": "not-exported"})

    result = asyncio.run(subject._query(("provider/model-1",)))

    assert result["accepted"] is False
    assert result["rejection_reasons"] == [
        "credential_bearing_environment_rejected"
    ]
    assert result["no_model_inference_performed"] is True
