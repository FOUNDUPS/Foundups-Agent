"""Direct async tests for the optional FastAPI adapter without TestClient."""

from __future__ import annotations

import asyncio
import threading
from types import SimpleNamespace
from typing import Any, Mapping

import pytest

from modules.infrastructure.foundups_mcp_bridge.src import (
    holo_query_service_http as http_module,
)
from modules.infrastructure.foundups_mcp_bridge.src.holo_query_service import (
    HEALTH_PATH,
    QUERY_PATH,
)


class _FakeResponse:
    def __init__(self, content: Mapping[str, Any], *, status_code: int) -> None:
        self.content = content
        self.status_code = status_code


class _FakeApp:
    def __init__(self, **_kwargs: Any) -> None:
        self.routes: dict[tuple[str, str], Any] = {}
        self.state = SimpleNamespace()

    def post(self, path: str) -> Any:
        return self._route("POST", path)

    def get(self, path: str) -> Any:
        return self._route("GET", path)

    def _route(self, method: str, path: str) -> Any:
        def decorator(function: Any) -> Any:
            self.routes[(method, path)] = function
            return function
        return decorator


class _Request:
    def __init__(
        self,
        *,
        authorization: str = "Bearer good",
        chunks: tuple[bytes, ...] = (),
    ) -> None:
        self.headers = {"authorization": authorization}
        self._chunks = chunks

    async def stream(self) -> Any:
        for chunk in self._chunks:
            yield chunk


class _Owner:
    max_request_bytes = 64

    def __init__(self) -> None:
        self.query_calls = 0
        self.health_calls = 0

    def authorization_error(self, authorization: str | None) -> str:
        return "" if authorization == "Bearer good" else "UNAUTHORIZED"

    def _auth_failure(self, error: str) -> Mapping[str, Any]:
        return {"ok": False, "error": error}

    def handle_query(self, *_args: Any, **_kwargs: Any) -> Mapping[str, Any]:
        self.query_calls += 1
        return {"ok": True, "error": ""}

    def handle_health(self, **_kwargs: Any) -> Mapping[str, Any]:
        self.health_calls += 1
        return {"ok": True, "error": ""}


def test_optional_fastapi_routes_execute_directly_without_testclient(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def run_inline(function: Any, *args: Any, **kwargs: Any) -> Any:
        return function(*args, **kwargs)

    owner = _Owner()
    monkeypatch.setattr(http_module, "FastAPI", _FakeApp)
    monkeypatch.setattr(http_module, "JSONResponse", _FakeResponse)
    monkeypatch.setattr(http_module, "run_in_threadpool", run_inline)
    monkeypatch.setattr(
        http_module,
        "HoloIndexQueryOwnerService",
        lambda **_kwargs: owner,
    )
    app = http_module.create_holo_query_app()
    assert set(app.routes) == {("POST", QUERY_PATH), ("GET", HEALTH_PATH)}
    assert app.state.holoindex_owner_service is owner
    query = app.routes[("POST", QUERY_PATH)]
    health = app.routes[("GET", HEALTH_PATH)]

    unauthorized = asyncio.run(
        query(_Request(authorization="Bearer wrong"))
    )
    assert unauthorized.status_code == 401

    owner.max_request_bytes = 3
    oversized = asyncio.run(query(_Request(chunks=(b"1234",))))
    assert oversized.status_code == 413
    owner.max_request_bytes = 64

    invalid = asyncio.run(query(_Request(chunks=(b"{",))))
    assert invalid.status_code == 400

    success = asyncio.run(query(_Request(chunks=(b"{}",))))
    assert success.status_code == 200
    assert owner.query_calls == 1

    ready = asyncio.run(health(_Request()))
    assert ready.status_code == 200
    assert owner.health_calls == 1


def test_fastapi_adapter_reports_stdlib_operational_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(http_module, "FastAPI", None)
    monkeypatch.setattr(http_module, "JSONResponse", None)
    with pytest.raises(
        RuntimeError,
        match="FASTAPI_DEPENDENCY_UNAVAILABLE_USE_STDLIB_RUNTIME",
    ):
        http_module.create_holo_query_app(_Owner())


def test_fastapi_routes_offload_blocking_owner_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class BlockingOwner(_Owner):
        def __init__(self) -> None:
            super().__init__()
            self.started = threading.Event()
            self.release = threading.Event()

        def handle_query(self, *_args: Any, **_kwargs: Any) -> Mapping[str, Any]:
            self.started.set()
            self.release.wait(timeout=1)
            return {"ok": True, "error": ""}

    async def threaded(function: Any, *args: Any, **kwargs: Any) -> Any:
        return await asyncio.to_thread(function, *args, **kwargs)

    async def exercise(query: Any, health: Any, owner: BlockingOwner) -> None:
        pending = asyncio.create_task(query(_Request(chunks=(b"{}",))))
        assert await asyncio.to_thread(owner.started.wait, 0.5)
        ready = await asyncio.wait_for(health(_Request()), timeout=0.2)
        assert ready.status_code == 200
        owner.release.set()
        assert (await pending).status_code == 200

    owner = BlockingOwner()
    monkeypatch.setattr(http_module, "FastAPI", _FakeApp)
    monkeypatch.setattr(http_module, "JSONResponse", _FakeResponse)
    monkeypatch.setattr(http_module, "run_in_threadpool", threaded)
    app = http_module.create_holo_query_app(owner)
    asyncio.run(exercise(
        app.routes[("POST", QUERY_PATH)],
        app.routes[("GET", HEALTH_PATH)],
        owner,
    ))
