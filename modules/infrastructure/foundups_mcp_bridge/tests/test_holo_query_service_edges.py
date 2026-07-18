"""Fail-closed edge coverage for the HoloIndex owner core."""

from __future__ import annotations

from concurrent.futures import TimeoutError as FutureTimeoutError
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from modules.infrastructure.foundups_mcp_bridge.src import (
    holo_query_service as core,
)
from modules.infrastructure.foundups_mcp_bridge.tests.test_holo_query_service import (
    SHA,
    TOKEN,
    _Backend,
    _query,
    _receipt,
    _service,
)


@pytest.mark.parametrize(
    "overrides",
    [
        {"query_timeout_seconds": 0},
        {"query_timeout_seconds": float("nan")},
        {"query_timeout_seconds": float("inf")},
        {"startup_warmup_timeout_seconds": 301},
        {"startup_warmup_timeout_seconds": float("nan")},
        {"startup_warmup_timeout_seconds": float("inf")},
        {"max_query_chars": 0},
        {"max_limit": 51},
    ],
)
def test_constructor_rejects_unsafe_bounds(
    tmp_path: Path,
    overrides: dict[str, Any],
) -> None:
    with pytest.raises(ValueError):
        core.HoloIndexQueryOwnerService(
            repo_root=tmp_path,
            ssd_path=tmp_path / "store",
            **overrides,
        )


def test_malformed_receipt_and_evaluator_failure_are_truthful(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def malformed(_path: Path) -> Any:
        raise ValueError("bad receipt")

    owner = _service(tmp_path, monkeypatch, receipt_loader=malformed)
    try:
        result = _query(owner)
        assert result["stale_reasons"] == ["malformed_freshness_receipt"]
    finally:
        owner.close()

    def evaluator_failure(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError("evaluation unavailable")

    owner = _service(
        tmp_path,
        monkeypatch,
        freshness_evaluator=evaluator_failure,
    )
    try:
        reasons = _query(owner)["stale_reasons"]
        assert reasons == [
            "freshness_evaluation_failed",
            "baseline_collection_proof_incomplete",
        ]
    finally:
        owner.close()


def test_backend_exception_and_post_query_staleness_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class RaisingBackend(_Backend):
        def search(self, *_args: Any, **_kwargs: Any) -> Any:
            raise RuntimeError("backend failed")

    owner = _service(tmp_path, monkeypatch, backend=RaisingBackend())
    try:
        assert _query(owner)["error"] == "SEMANTIC_BACKEND_UNAVAILABLE"
    finally:
        owner.close()

    receipts = iter(
        [_receipt(), _receipt(omit="navigation_knowledge")]
    )
    owner = _service(
        tmp_path,
        monkeypatch,
        receipt_loader=lambda _path: next(receipts),
    )
    try:
        result = _query(owner)
        assert result["error"] == "STALE_INDEX"
        assert (
            "missing_collection_receipt:navigation_knowledge"
            in result["stale_reasons"]
        )
        assert result["raw_result"]
    finally:
        owner.close()


def _assert_unknown_timeout_and_poisoned_health(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = _service(
        tmp_path,
        monkeypatch,
        repository_state_reader=lambda _root: SimpleNamespace(
            proven_clean=False,
            head_sha="",
            error="HEALTH_UNAVAILABLE",
        ),
    )
    try:
        unknown = owner.handle_health(authorization=f"Bearer {TOKEN}")
        assert unknown["error"] == "HEALTH_UNAVAILABLE"
        owner._repository_state_reader = lambda _root: SimpleNamespace(
            proven_clean=True,
            head_sha=SHA,
            error="",
        )

        def timeout(*_args, **_kwargs):
            owner._poisoned.set()
            raise FutureTimeoutError()

        monkeypatch.setattr(owner, "_run", timeout)
        assert owner.handle_health(
            authorization=f"Bearer {TOKEN}"
        )["error"] == "QUERY_TIMEOUT"
        assert owner.handle_health(
            authorization=f"Bearer {TOKEN}"
        )["error"] == "QUERY_OWNER_POISONED"
    finally:
        owner.close()


def _assert_backend_failure_health(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = _service(tmp_path, monkeypatch)
    try:
        monkeypatch.setattr(
            owner,
            "_search",
            lambda *_args: (_ for _ in ()).throw(RuntimeError("backend")),
        )
        assert owner.handle_health(
            authorization=f"Bearer {TOKEN}"
        )["error"] == "SEMANTIC_BACKEND_UNAVAILABLE"
    finally:
        owner.close()


def _assert_stale_health(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = _service(
        tmp_path,
        monkeypatch,
        receipt_loader=lambda _path: _receipt(omit="navigation_docs"),
    )
    try:
        stale = owner.handle_health(authorization=f"Bearer {TOKEN}")
        assert stale["error"] == "STALE_INDEX"
    finally:
        owner.close()


def test_health_reports_unknown_stale_timeout_and_backend_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _assert_unknown_timeout_and_poisoned_health(tmp_path, monkeypatch)
    _assert_backend_failure_health(tmp_path, monkeypatch)
    _assert_stale_health(tmp_path, monkeypatch)


def test_internal_normalizers_reject_bad_payloads_and_dedupe_hits() -> None:
    request_args = {
        "request_size": None,
        "max_request_bytes": 100,
        "max_query_chars": 20,
        "max_limit": 8,
    }
    assert core._validate_payload([], **request_args)[1] == "INVALID_REQUEST"
    unserializable = {"query": object()}
    assert core._validate_payload(
        unserializable,
        **request_args,
    )[1] == "INVALID_REQUEST"
    assert core._validate_payload(
        {"query": "x"},
        request_size=None,
        max_request_bytes=1,
        max_query_chars=20,
        max_limit=8,
    )[1] == "REQUEST_TOO_LARGE"
    hits = core._flatten_hits(
        {
            "code_hits": [
                "bad",
                {"path": "same.py"},
                {"path": "same.py"},
                {"name": "pathless"},
            ]
        },
        10,
    )
    assert len(hits) == 2
    assert core._flatten_hits({"code_hits": [{"path": "one.py"}]}, 1)


def test_default_factory_and_transport_wrapper_delegate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from holo_index.core import holo_index as holo_module

    sentinel = object()
    monkeypatch.setattr(
        holo_module,
        "HoloIndex",
        lambda **_kwargs: sentinel,
    )
    assert core._default_backend_factory(tmp_path) is sentinel

    from modules.infrastructure.foundups_mcp_bridge.src import (
        holo_query_service_http,
    )

    monkeypatch.setattr(
        holo_query_service_http,
        "create_stdlib_server",
        lambda service, **kwargs: (service, kwargs),
    )
    service = object()
    assert core.create_stdlib_server(
        service,
        host="127.0.0.1",
        port=8127,
    ) == (service, {"host": "127.0.0.1", "port": 8127})
