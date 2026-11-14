"""Red contract tests for the idle schedule-to-discovery adapter."""

from __future__ import annotations

import asyncio
import hashlib
import importlib
import json
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from modules.ai_intelligence.ai_gateway.src.model_openrouter_scheduled_discovery import (
    ScheduledDiscoveryResult,
)
from modules.ai_intelligence.ai_gateway.src.model_provider_catalog_snapshot import (
    build_candidate_snapshot,
    build_discovery_invocation,
    build_discovery_receipt,
    candidate_snapshot_id,
    parse_and_sanitize_openrouter_catalog,
    sha256_bytes,
)
from modules.infrastructure.idle_automation.src.schedule_claim_state import (
    ScheduleClaim,
    build_execution_id,
)

FIXTURE = Path(__file__).parent / "fixtures/openrouter_models_success.json"
START = "2026-07-24T00:00:00+00:00"
END = "2026-07-25T00:00:00+00:00"
SCHEDULE_ID = hashlib.sha256(
    b"openrouter_catalog_refresh:daily"
).hexdigest()[:12]


def _adapter():
    return importlib.import_module(
        "modules.ai_intelligence.ai_gateway.src."
        "model_openrouter_schedule_adapter"
    )


def _claim(
    *,
    schedule_id: str = SCHEDULE_ID,
    routine: str = "openrouter_catalog_refresh",
    cadence: str = "daily",
    start: str = START,
    end: str = END,
    execution_id: str | None = None,
    token: str = "opaque-claim-token",
    claimant_id: str = "idle-dae",
    lease_expires_at: str = "2026-07-24T01:00:00+00:00",
    attempt: int = 1,
) -> ScheduleClaim:
    return ScheduleClaim(
        schedule_id=schedule_id,
        routine=routine,
        cadence=cadence,
        window_start=start,
        window_end=end,
        execution_id=execution_id
        or build_execution_id(
            schedule_id, routine, cadence, start, end
        ),
        token=token,
        claimant_id=claimant_id,
        lease_expires_at=lease_expires_at,
        attempt=attempt,
    )


class _ScheduleClaimSubclass(ScheduleClaim):
    """Structurally similar claims are not exact durable claim evidence."""


def _expected_invocation(claim: ScheduleClaim):
    start_ms = int(
        datetime.fromisoformat(claim.window_start).timestamp() * 1000
    )
    end_ms = int(
        datetime.fromisoformat(claim.window_end).timestamp() * 1000
    )
    return build_discovery_invocation(
        mode="scheduled",
        schedule_id=f"idle:{claim.execution_id}",
        scheduled_for_ms=start_ms,
        expires_at_ms=end_ms - 1,
    )


def _completed_guard_result(invocation) -> ScheduledDiscoveryResult:
    raw = FIXTURE.read_bytes()
    payload, rejected, counts = parse_and_sanitize_openrouter_catalog(raw)
    snapshot_id = candidate_snapshot_id(payload)
    completed = int(
        datetime.fromisoformat(START).timestamp() * 1000
    )
    receipt = build_discovery_receipt(
        invocation=invocation,
        call_id="offline-schedule-adapter",
        request_envelope_digest=sha256_bytes(b"fixed-request"),
        attempted=True,
        outcome="COMPLETED",
        reason="completed",
        started_at_ms=completed,
        completed_at_ms=completed,
        http_status=200,
        response_body_digest=sha256_bytes(raw),
        response_byte_count=len(raw),
        candidate_snapshot_id=snapshot_id,
        accepted_record_count=len(payload["data"]),
        rejected_record_count=rejected,
        rejection_counts=counts,
    )
    candidate = build_candidate_snapshot(
        catalog_payload=payload,
        rejected_record_count=rejected,
        rejection_counts=counts,
        observed_at_ms=completed,
        observation_receipt=receipt,
    )
    return ScheduledDiscoveryResult(
        status="COMPLETED",
        reason="completed",
        replayed=False,
        receipt=receipt,
        candidate=candidate,
        attempt_path=Path("not-exported-attempt"),
        candidate_path=Path("not-exported-candidate"),
        ledger_path=Path("not-exported-ledger"),
    )


@pytest.mark.asyncio
async def test_valid_daily_claim_maps_exact_guarded_invocation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    adapter = _adapter()
    claim = _claim()
    expected = _expected_invocation(claim)
    guard_result = _completed_guard_result(expected)
    guarded = AsyncMock(return_value=guard_result)
    monkeypatch.setattr(
        adapter, "discover_scheduled_openrouter_model_catalog", guarded
    )
    repo = tmp_path / "repo"
    runtime = tmp_path / "trusted-runtime"
    transport = object()

    result = await adapter.run_openrouter_catalog_schedule_claim(
        claim,
        repo_root=repo,
        runtime_root=runtime,
        transport=transport,
    )

    guarded.assert_awaited_once_with(
        expected,
        repo_root=repo,
        runtime_root=runtime,
        transport=transport,
    )
    assert result == {
        "success": True,
        "status": "COMPLETED",
        "reason": "completed",
        "replayed": False,
        "receipt_id": guard_result.receipt.receipt_id,
        "candidate_snapshot_id": guard_result.candidate.snapshot_id,
    }
    assert len(json.dumps(result)) < 1024
    assert not any("path" in key or "candidate" == key for key in result)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "claim",
    [
        _claim(cadence="nightly"),
        _claim(routine="self_research"),
        _claim(schedule_id="forged-schedule"),
        _claim(execution_id="0" * 64),
        _claim(
            start="2026-07-24T01:00:00+00:00",
            end="2026-07-25T01:00:00+00:00",
        ),
        _claim(
            start="2026-07-24T00:00:00Z",
            end="2026-07-25T00:00:00Z",
        ),
        _claim(
            start="2026-07-24T00:00:00+09:00",
            end="2026-07-25T00:00:00+09:00",
        ),
        _claim(end="2026-07-24T23:00:00+00:00"),
        _claim(token="x" * 257),
        _claim(claimant_id=""),
        _claim(lease_expires_at="not-a-time"),
        _claim(attempt=0),
    ],
)
async def test_forged_claim_fails_before_guarded_provider_call(
    claim: ScheduleClaim, monkeypatch: pytest.MonkeyPatch
) -> None:
    adapter = _adapter()
    guarded = AsyncMock()
    monkeypatch.setattr(
        adapter, "discover_scheduled_openrouter_model_catalog", guarded
    )

    result = await adapter.run_openrouter_catalog_schedule_claim(
        claim,
        repo_root=Path("repo"),
        runtime_root=Path("runtime"),
        transport=object(),
    )

    assert result == {
        "success": False,
        "status": "BLOCKED_PRECALL",
        "reason": "claim_invalid",
        "replayed": False,
        "receipt_id": None,
        "candidate_snapshot_id": None,
    }
    guarded.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "claim_like",
    [
        _claim().__dict__,
        _ScheduleClaimSubclass(**_claim().__dict__),
    ],
)
async def test_non_exact_claim_type_fails_before_guard(
    claim_like: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = _adapter()
    guarded = AsyncMock()
    monkeypatch.setattr(
        adapter, "discover_scheduled_openrouter_model_catalog", guarded
    )

    result = await adapter.run_openrouter_catalog_schedule_claim(
        claim_like,
        repo_root=Path("repo"),
        runtime_root=Path("runtime"),
        transport=object(),
    )

    assert result["reason"] == "claim_invalid"
    assert set(result) == {
        "success",
        "status",
        "reason",
        "replayed",
        "receipt_id",
        "candidate_snapshot_id",
    }
    guarded.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "reason", "expected_status", "expected_reason"),
    [
        ("FAILED", "transport_failed", "FAILED", "scheduled_discovery_failed"),
        (
            "INDETERMINATE",
            "replay_state_invalid",
            "INDETERMINATE",
            "scheduled_discovery_indeterminate",
        ),
        (
            "BLOCKED_PRECALL",
            "runtime_path_invalid",
            "BLOCKED_PRECALL",
            "scheduled_discovery_blocked",
        ),
    ],
)
async def test_noncompleted_guard_status_never_promotes_success(
    status: str,
    reason: str,
    expected_status: str,
    expected_reason: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = _adapter()
    completed = _completed_guard_result(_expected_invocation(_claim()))
    guarded = AsyncMock(
        return_value=replace(
            completed,
            status=status,
            reason=reason,
            receipt=None,
            candidate=None,
        )
    )
    monkeypatch.setattr(
        adapter, "discover_scheduled_openrouter_model_catalog", guarded
    )

    result = await adapter.run_openrouter_catalog_schedule_claim(
        _claim(),
        repo_root=Path("repo"),
        runtime_root=Path("runtime"),
        transport=object(),
    )

    assert result == {
        "success": False,
        "status": expected_status,
        "reason": expected_reason,
        "replayed": False,
        "receipt_id": None,
        "candidate_snapshot_id": None,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("completed", [False, True])
async def test_guard_status_and_reason_are_never_forwarded(
    completed: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = _adapter()
    secret = "Bearer sk-secret-must-not-escape"
    guard_result = _completed_guard_result(_expected_invocation(_claim()))
    if completed:
        guard_result = replace(guard_result, reason=secret)
    else:
        guard_result = replace(
            guard_result,
            status=f"FAILED-{secret}",
            reason=secret,
            receipt=None,
            candidate=None,
        )
    guarded = AsyncMock(return_value=guard_result)
    monkeypatch.setattr(
        adapter, "discover_scheduled_openrouter_model_catalog", guarded
    )

    result = await adapter.run_openrouter_catalog_schedule_claim(
        _claim(),
        repo_root=Path("repo"),
        runtime_root=Path("runtime"),
        transport=object(),
    )

    encoded = json.dumps(result)
    assert secret not in encoded
    assert len(encoded) < 1024
    if completed:
        assert result["status"] == "COMPLETED"
        assert result["reason"] == "completed"
        assert result["success"] is True
    else:
        assert result["status"] == "INDETERMINATE"
        assert result["reason"] == "scheduled_discovery_result_invalid"
        assert result["success"] is False


@pytest.mark.asyncio
async def test_unhashable_guard_status_returns_fixed_invalid_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = _adapter()
    guard_result = replace(
        _completed_guard_result(_expected_invocation(_claim())),
        status={},
        receipt=None,
        candidate=None,
    )
    monkeypatch.setattr(
        adapter,
        "discover_scheduled_openrouter_model_catalog",
        AsyncMock(return_value=guard_result),
    )

    result = await adapter.run_openrouter_catalog_schedule_claim(
        _claim(),
        repo_root=Path("repo"),
        runtime_root=Path("runtime"),
        transport=object(),
    )

    assert result["success"] is False
    assert result["status"] == "INDETERMINATE"
    assert result["reason"] == "scheduled_discovery_result_invalid"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "replacement",
    [
        {"receipt": None},
        {"candidate": None},
        {"receipt": object()},
        {"candidate": object()},
    ],
)
async def test_completed_requires_exact_receipt_and_candidate(
    replacement: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    adapter = _adapter()
    expected = _expected_invocation(_claim())
    guard_result = _completed_guard_result(expected)
    guarded = AsyncMock(return_value=replace(guard_result, **replacement))
    monkeypatch.setattr(
        adapter, "discover_scheduled_openrouter_model_catalog", guarded
    )

    result = await adapter.run_openrouter_catalog_schedule_claim(
        _claim(),
        repo_root=Path("repo"),
        runtime_root=Path("runtime"),
        transport=object(),
    )

    assert result["success"] is False
    assert set(result) == {
        "success",
        "status",
        "reason",
        "replayed",
        "receipt_id",
        "candidate_snapshot_id",
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("mismatch", ["receipt_invocation", "candidate"])
async def test_completed_requires_exact_derived_lineage(
    mismatch: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = _adapter()
    claim = _claim()
    expected = _expected_invocation(claim)
    expected_result = _completed_guard_result(expected)
    other = build_discovery_invocation(
        mode="scheduled",
        schedule_id=f"idle:{'a' * 64}",
        scheduled_for_ms=expected.scheduled_for_ms,
        expires_at_ms=expected.expires_at_ms,
    )
    other_result = _completed_guard_result(other)
    guard_result = (
        other_result
        if mismatch == "receipt_invocation"
        else replace(expected_result, candidate=other_result.candidate)
    )
    guarded = AsyncMock(return_value=guard_result)
    monkeypatch.setattr(
        adapter, "discover_scheduled_openrouter_model_catalog", guarded
    )

    result = await adapter.run_openrouter_catalog_schedule_claim(
        claim,
        repo_root=Path("repo"),
        runtime_root=Path("runtime"),
        transport=object(),
    )

    assert result == {
        "success": False,
        "status": "INDETERMINATE",
        "reason": "completed_lineage_invalid",
        "replayed": False,
        "receipt_id": None,
        "candidate_snapshot_id": None,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "forgery",
    ["receipt_id", "candidate_snapshot_id", "matching_oversized_ids"],
)
async def test_completed_evidence_is_canonically_rehydrated(
    forgery: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = _adapter()
    guard_result = _completed_guard_result(_expected_invocation(_claim()))
    receipt = guard_result.receipt
    candidate = guard_result.candidate
    if forgery == "receipt_id":
        receipt = replace(receipt, receipt_id="forged-receipt")
        candidate = replace(candidate, observation_receipt=receipt)
    elif forgery == "candidate_snapshot_id":
        candidate = replace(candidate, snapshot_id="forged-snapshot")
    else:
        oversized = "secret-" + ("x" * 10_000)
        receipt = replace(receipt, candidate_snapshot_id=oversized)
        candidate = replace(
            candidate,
            snapshot_id=oversized,
            observation_receipt=receipt,
        )
    guarded = AsyncMock(
        return_value=replace(
            guard_result,
            receipt=receipt,
            candidate=candidate,
        )
    )
    monkeypatch.setattr(
        adapter, "discover_scheduled_openrouter_model_catalog", guarded
    )

    result = await adapter.run_openrouter_catalog_schedule_claim(
        _claim(),
        repo_root=Path("repo"),
        runtime_root=Path("runtime"),
        transport=object(),
    )

    encoded = json.dumps(result)
    assert result["success"] is False
    assert result["reason"] in {
        "completed_receipt_invalid",
        "completed_candidate_invalid",
    }
    assert len(encoded) < 1024
    assert "secret" not in encoded
    assert "forged" not in encoded


@pytest.mark.asyncio
async def test_recursive_receipt_mapping_returns_fixed_invalid_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = _adapter()
    guard_result = _completed_guard_result(_expected_invocation(_claim()))
    recursive_counts = {}
    recursive_counts["secret"] = recursive_counts
    receipt = replace(
        guard_result.receipt,
        rejection_counts=recursive_counts,
    )
    candidate = replace(
        guard_result.candidate,
        observation_receipt=receipt,
    )
    monkeypatch.setattr(
        adapter,
        "discover_scheduled_openrouter_model_catalog",
        AsyncMock(
            return_value=replace(
                guard_result,
                receipt=receipt,
                candidate=candidate,
            )
        ),
    )

    result = await adapter.run_openrouter_catalog_schedule_claim(
        _claim(),
        repo_root=Path("repo"),
        runtime_root=Path("runtime"),
        transport=object(),
    )

    assert result["success"] is False
    assert result["status"] == "INDETERMINATE"
    assert result["reason"] == "completed_receipt_invalid"
    assert len(json.dumps(result)) < 1024


@pytest.mark.asyncio
async def test_guard_exception_returns_content_free_bounded_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = _adapter()
    guarded = AsyncMock(
        side_effect=RuntimeError("Bearer sk-secret-must-not-escape")
    )
    monkeypatch.setattr(
        adapter, "discover_scheduled_openrouter_model_catalog", guarded
    )

    result = await adapter.run_openrouter_catalog_schedule_claim(
        _claim(),
        repo_root=Path("repo"),
        runtime_root=Path("runtime"),
        transport=object(),
    )

    encoded = json.dumps(result)
    assert result["success"] is False
    assert result["reason"] == "scheduled_discovery_adapter_failed"
    assert "secret" not in encoded and "Bearer" not in encoded
    assert len(encoded) < 1024


@pytest.mark.asyncio
async def test_cancellation_from_guard_propagates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = _adapter()
    guarded = AsyncMock(side_effect=asyncio.CancelledError)
    monkeypatch.setattr(
        adapter, "discover_scheduled_openrouter_model_catalog", guarded
    )

    with pytest.raises(asyncio.CancelledError):
        await adapter.run_openrouter_catalog_schedule_claim(
            _claim(),
            repo_root=Path("repo"),
            runtime_root=Path("runtime"),
            transport=object(),
        )
