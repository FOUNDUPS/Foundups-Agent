"""Offline tests for bounded, explicit OpenRouter catalog discovery."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

import pytest

from modules.ai_intelligence.ai_gateway.src.model_provider_catalog_artifact_store import (
    AtomicArtifactOps,
)
from modules.ai_intelligence.ai_gateway.src.model_openrouter_direct_discovery import (
    HTTPResponse,
    discover_openrouter_model_catalog,
)
from modules.ai_intelligence.ai_gateway.src.model_provider_catalog_snapshot import (
    MAX_RESPONSE_BYTES,
    build_discovery_invocation,
    rehydrate_candidate_snapshot,
    rehydrate_discovery_receipt,
)

FIXTURES = Path(__file__).parent / "fixtures"


class _FakeTransport:
    def __init__(self, response: HTTPResponse | None = None, error: Exception | None = None):
        self.response = response
        self.error = error
        self.requests = []

    async def fetch(self, request):
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        return self.response


class _Clock:
    def __init__(self, value: int = 1_000):
        self.value = value

    def __call__(self) -> int:
        self.value += 1
        return self.value


def _success_transport() -> _FakeTransport:
    return _FakeTransport(
        HTTPResponse(
            200,
            {"Content-Type": "application/json; charset=utf-8"},
            (FIXTURES / "openrouter_models_success.json").read_bytes(),
        )
    )


def _run(tmp_path: Path, transport: _FakeTransport, **overrides):
    values = {
        "invocation": build_discovery_invocation(mode="manual"),
        "repo_root": Path.cwd(),
        "runtime_root": tmp_path,
        "attempt_path": "attempt.json",
        "candidate_path": "candidate.json",
        "transport": transport,
        "clock_ms": _Clock(),
    }
    values.update(overrides)
    return asyncio.run(discover_openrouter_model_catalog(**values))


def test_success_uses_fixed_unauthenticated_envelope_and_writes_both_artifacts(
    tmp_path: Path,
) -> None:
    transport = _success_transport()
    result = _run(tmp_path, transport)

    assert result.receipt.outcome == "COMPLETED"
    assert result.candidate is not None
    assert len(transport.requests) == 1
    request = transport.requests[0]
    assert request.method == "GET"
    assert request.url == "https://openrouter.ai/api/v1/models"
    assert request.headers == {"Accept": "application/json"}
    assert all(key.lower() != "authorization" for key in request.headers)
    assert request.body is None
    assert request.allow_redirects is False
    assert request.timeout_seconds == 15.0
    assert request.max_response_bytes == 8 * 1024 * 1024
    assert request.max_records == 2048

    attempt = json.loads((tmp_path / "attempt.json").read_text(encoding="utf-8"))
    candidate = json.loads((tmp_path / "candidate.json").read_text(encoding="utf-8"))
    assert rehydrate_discovery_receipt(attempt) == result.receipt
    assert rehydrate_candidate_snapshot(
        candidate, now_ms=result.candidate.observed_at_ms
    ) == result.candidate


@pytest.mark.parametrize(
    "response,error,reason",
    [
        (HTTPResponse(302, {"Location": "https://example.invalid"}, b""), None, "redirect_rejected"),
        (HTTPResponse(503, {"Content-Type": "application/json"}, b"{}"), None, "http_status_rejected"),
        (HTTPResponse(200, {"Content-Type": "text/html"}, b"{}"), None, "content_type_rejected"),
        (HTTPResponse(200, {"Content-Type": "application/json"}, b"{"), None, "json_invalid"),
        (None, asyncio.TimeoutError(), "transport_timeout"),
        (None, RuntimeError("sensitive provider detail"), "transport_failed"),
    ],
)
def test_failed_refresh_preserves_lkg_and_emits_content_free_terminal_reason(
    tmp_path: Path,
    response: HTTPResponse | None,
    error: Exception | None,
    reason: str,
) -> None:
    old = b'{"existing":"last-known-good"}\n'
    (tmp_path / "candidate.json").write_bytes(old)

    result = _run(tmp_path, _FakeTransport(response, error))

    assert result.receipt.outcome == "FAILED"
    assert result.receipt.reason == reason
    assert (tmp_path / "candidate.json").read_bytes() == old
    persisted = json.loads((tmp_path / "attempt.json").read_text(encoding="utf-8"))
    assert persisted["reason"] == reason
    assert "sensitive provider detail" not in json.dumps(persisted)


def test_oversized_response_is_rejected_without_hashing_or_lkg_replacement(
    tmp_path: Path,
) -> None:
    old = b"last-known-good"
    (tmp_path / "candidate.json").write_bytes(old)
    response = HTTPResponse(
        200,
        {"Content-Type": "application/json"},
        b"x" * (MAX_RESPONSE_BYTES + 1),
    )

    result = _run(tmp_path, _FakeTransport(response))

    assert result.receipt.reason == "body_too_large"
    assert result.receipt.response_body_digest is None
    assert result.receipt.response_byte_count is None
    assert (tmp_path / "candidate.json").read_bytes() == old


def test_candidate_write_failure_preserves_lkg_and_updates_attempt(tmp_path: Path) -> None:
    old = b'{"existing":"last-known-good"}\n'
    candidate_path = tmp_path / "candidate.json"
    candidate_path.write_bytes(old)
    def guarded(source: Path, target: Path) -> None:
        if target == candidate_path:
            raise OSError("simulated")
        os.replace(source, target)

    result = _run(
        tmp_path, _success_transport(),
        artifact_ops=AtomicArtifactOps(replacer=guarded),
    )

    assert result.receipt.outcome == "FAILED"
    assert result.receipt.reason == "candidate_write_failed"
    assert candidate_path.read_bytes() == old
    persisted = json.loads((tmp_path / "attempt.json").read_text(encoding="utf-8"))
    assert persisted["reason"] == "candidate_write_failed"
    assert persisted["outcome"] != "COMPLETED"


def test_terminal_receipt_failure_occurs_after_lkg_and_leaves_attempt_armed(
    tmp_path: Path,
) -> None:
    old = b"last-known-good"
    candidate_path = tmp_path / "candidate.json"
    candidate_path.write_bytes(old)
    def guarded(source: Path, target: Path) -> None:
        text = source.read_text(encoding="utf-8")
        if target.name == "attempt.json" and '"outcome":"COMPLETED"' in text:
            raise OSError("simulated")
        os.replace(source, target)

    result = _run(
        tmp_path, _success_transport(),
        artifact_ops=AtomicArtifactOps(replacer=guarded),
    )

    assert result.receipt.outcome == "INDETERMINATE"
    assert result.receipt.reason == "terminal_receipt_write_failed"
    assert result.candidate is not None
    assert candidate_path.read_bytes() != old
    rehydrate_candidate_snapshot(
        json.loads(candidate_path.read_text(encoding="utf-8")),
        now_ms=result.candidate.observed_at_ms,
    )
    persisted = json.loads((tmp_path / "attempt.json").read_text(encoding="utf-8"))
    assert persisted["outcome"] == "INDETERMINATE"
    assert persisted["reason"] == "transport_pending"


def test_candidate_and_failed_receipt_write_failure_preserves_armed_truth(
    tmp_path: Path,
) -> None:
    old = b"last-known-good"
    candidate_path = tmp_path / "candidate.json"
    candidate_path.write_bytes(old)
    def guarded(source: Path, target: Path) -> None:
        text = source.read_text(encoding="utf-8")
        if target == candidate_path or '"outcome":"FAILED"' in text:
            raise OSError("raw failure detail")
        os.replace(source, target)

    result = _run(
        tmp_path, _success_transport(),
        artifact_ops=AtomicArtifactOps(replacer=guarded),
    )
    assert (result.receipt.outcome, result.receipt.reason) == (
        "INDETERMINATE", "terminal_receipt_write_failed"
    )
    assert candidate_path.read_bytes() == old
    persisted = json.loads((tmp_path / "attempt.json").read_text(encoding="utf-8"))
    assert (persisted["outcome"], persisted["reason"], persisted["attempted"]) == (
        "INDETERMINATE", "transport_pending", True
    )
    assert "raw failure detail" not in json.dumps(result.receipt.to_dict())


def test_first_precall_write_failure_never_arms_or_calls_transport(
    tmp_path: Path,
) -> None:
    transport = _success_transport()
    result = _run(
        tmp_path, transport,
        artifact_ops=AtomicArtifactOps(
            replacer=lambda *_: (_ for _ in ()).throw(OSError("raw detail"))
        ),
    )
    assert (result.receipt.outcome, result.receipt.reason, result.receipt.attempted) == (
        "BLOCKED_PRECALL", "precall_write_failed", False
    )
    assert transport.requests == []
    assert not (tmp_path / "attempt.json").exists()


def test_second_precall_write_failure_returns_durable_intent(
    tmp_path: Path,
) -> None:
    def guarded(source: Path, target: Path) -> None:
        text = source.read_text(encoding="utf-8")
        if '"outcome":"INDETERMINATE"' in text:
            raise OSError("raw detail")
        os.replace(source, target)

    transport = _success_transport()
    result = _run(
        tmp_path, transport,
        artifact_ops=AtomicArtifactOps(replacer=guarded),
    )
    persisted = json.loads((tmp_path / "attempt.json").read_text(encoding="utf-8"))
    assert result.receipt.to_dict() == persisted
    assert (persisted["outcome"], persisted["reason"], persisted["attempted"]) == (
        "BLOCKED_PRECALL", "precall_intent", False
    )
    assert transport.requests == []


class _HostileResponse:
    @property
    def status(self):
        raise RuntimeError("raw hostile getter")


class _HeadersSubclass(dict):
    pass


@pytest.mark.parametrize(
    "response",
    [
        _HostileResponse(),
        HTTPResponse(999, {"Content-Type": "application/json"}, b"{}"),
        HTTPResponse(200, _HeadersSubclass({"Content-Type": "application/json"}), b"{}"),
        HTTPResponse(200, {"Content-Type": None}, b"{}"),
        HTTPResponse(200, {"Content-Type": "application/json"}, bytearray(b"{}")),
        HTTPResponse(200, {"Content-Type": "application/json"}, b"{}", redirected=1),
    ],
)
def test_hostile_http_metadata_becomes_content_free_terminal_transport_failure(
    tmp_path: Path, response
) -> None:
    old = b"last-known-good"
    (tmp_path / "candidate.json").write_bytes(old)
    result = _run(tmp_path, _FakeTransport(response))
    assert (result.receipt.outcome, result.receipt.reason) == (
        "FAILED", "transport_failed"
    )
    assert result.receipt.http_status is None
    assert (tmp_path / "candidate.json").read_bytes() == old
    persisted = (tmp_path / "attempt.json").read_text(encoding="utf-8")
    assert "hostile" not in persisted and "getter" not in persisted


@pytest.mark.parametrize(
    "attempt,candidate",
    [
        ("same.json", "same.json"),
        ("../escape.json", "candidate.json"),
        ("NUL", "candidate.json"),
    ],
)
def test_invalid_output_paths_block_before_transport(
    tmp_path: Path, attempt: str, candidate: str
) -> None:
    transport = _success_transport()
    result = _run(
        tmp_path,
        transport,
        attempt_path=attempt,
        candidate_path=candidate,
    )

    assert result.receipt.outcome == "BLOCKED_PRECALL"
    assert result.receipt.reason == "output_path_invalid"
    assert transport.requests == []


def test_inside_repo_paths_block_before_transport(tmp_path: Path) -> None:
    transport = _success_transport()
    result = _run(
        tmp_path,
        transport,
        runtime_root=Path.cwd(),
        attempt_path="attempt.json",
        candidate_path="candidate.json",
    )
    assert result.receipt.reason == "output_path_invalid"
    assert transport.requests == []


def test_link_component_blocks_before_transport(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    try:
        os.symlink(target, link, target_is_directory=True)
    except (OSError, NotImplementedError):
        link.mkdir()
        original = Path.is_junction
        monkeypatch.setattr(
            Path, "is_junction",
            lambda self: self == link or original(self),
        )
    transport = _success_transport()
    result = _run(
        tmp_path,
        transport,
        attempt_path=link / "attempt.json",
        candidate_path="candidate.json",
    )
    assert result.receipt.reason == "output_path_invalid"
    assert transport.requests == []


def test_scheduled_not_due_is_durable_blocked_precall(tmp_path: Path) -> None:
    invocation = build_discovery_invocation(
        mode="scheduled",
        schedule_id="daily",
        scheduled_for_ms=2_000,
        expires_at_ms=3_000,
    )
    transport = _success_transport()
    result = _run(tmp_path, transport, invocation=invocation)
    assert result.receipt.outcome == "BLOCKED_PRECALL"
    assert result.receipt.reason == "scheduled_invocation_not_due"
    assert transport.requests == []
    persisted = json.loads((tmp_path / "attempt.json").read_text(encoding="utf-8"))
    assert persisted["reason"] == "scheduled_invocation_not_due"


def test_attempt_receipt_transitions_precall_indeterminate_terminal(
    tmp_path: Path,
) -> None:
    writes = []

    def recording(source: Path, target: Path) -> None:
        if target.name == "attempt.json":
            text = source.read_text(encoding="utf-8")
            writes.append(json.loads(text))
        os.replace(source, target)

    result = _run(
        tmp_path, _success_transport(),
        artifact_ops=AtomicArtifactOps(replacer=recording),
    )

    assert result.receipt.outcome == "COMPLETED"
    assert [(item["attempted"], item["outcome"]) for item in writes] == [
        (False, "BLOCKED_PRECALL"),
        (True, "INDETERMINATE"),
        (True, "COMPLETED"),
    ]
    assert writes[0]["reason"] == "precall_intent"


def test_candidate_is_durable_before_completed_attempt(
    tmp_path: Path,
) -> None:
    order = []

    def recording(source: Path, target: Path) -> None:
        text = source.read_text(encoding="utf-8")
        payload = json.loads(text)
        order.append((target.name, payload.get("outcome")))
        os.replace(source, target)

    result = _run(
        tmp_path, _success_transport(),
        artifact_ops=AtomicArtifactOps(replacer=recording),
    )
    assert result.receipt.outcome == "COMPLETED"
    assert order == [
        ("attempt.json", "BLOCKED_PRECALL"),
        ("attempt.json", "INDETERMINATE"),
        ("candidate.json", None),
        ("attempt.json", "COMPLETED"),
    ]
