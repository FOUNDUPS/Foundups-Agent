"""Transport-security tests for the RedDog HoloIndex owner client."""

from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace

import pytest

from holo_index.core.holo_index import HoloIndex
from holo_index.freshness_receipt import read_git_head_sha
from holo_index.repository_state import repository_root_digest
from modules.communication.moltbot_bridge.src.reddog_readonly_0102_audit_worker_runtime import (
    HoloIndexReadOnlyQueryAdapter,
)
import modules.communication.moltbot_bridge.src.reddog_holoindex_owner_query_client as owner_query_client
import modules.communication.moltbot_bridge.src.reddog_holoindex_query_adapter as holo_query_adapter


SERVICE_TOKEN = "test-token-" + "x" * 32
REDIRECT_TOKEN = "redirect-secret-" + "y" * 32
REPLICA_BINDING = (
    "sha256:" + "c" * 64,
    "sha256:" + "d" * 64,
    "sha256:" + "e" * 64,
    "sha256:" + "f" * 64,
)
REPLICA_FIELDS = (
    "query_replica_descriptor_digest",
    "query_replica_generation_id",
    "query_replica_id",
    "query_replica_path_identity_digest",
)


@pytest.fixture(autouse=True)
def _clean_repository_state(monkeypatch):
    clean_state = lambda root: SimpleNamespace(
        proven_clean=True,
        head_sha=read_git_head_sha(root),
        error="",
    )
    monkeypatch.setattr(owner_query_client, "read_repository_state", clean_state)


def _set_repo_head(repo_root: Path, head_sha: str) -> None:
    git_dir = repo_root / ".git"
    git_dir.mkdir(parents=True, exist_ok=True)
    (git_dir / "HEAD").write_text(head_sha + "\n", encoding="utf-8")


class _HTTPResponse:
    def __init__(self, payload: dict) -> None:
        self.body = json.dumps(payload).encode("utf-8")
        self.offset = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            size = len(self.body) - self.offset
        start = self.offset
        self.offset = min(len(self.body), self.offset + size)
        return self.body[start : self.offset]

    read1 = read


def _successful_query_payload(head_sha: str, repo_root: Path) -> dict:
    payload = {
        "schema_version": "holoindex_query_service.v1",
        "ok": True,
        "source": "holoindex",
        "query": "WSP 97 research",
        "freshness": "CURRENT",
        "error": "",
        "stale_reasons": [],
        "index_gap_detected": False,
        "no_holoindex_reindex_performed": True,
        "freshness_generation_id": "sha256:" + "a" * 64,
        "freshness_receipt_digest": "sha256:" + "b" * 64,
        "repo_head_sha": head_sha,
        "repo_root_digest": repository_root_digest(repo_root),
        "retrieval_mode": "semantic",
        "raw_result": {
            "wsp_hits": [
                {
                    "path": "WSP_framework/src/WSP_97_Truth_Boundary_Protocol.md",
                    "title": "WSP 97",
                }
            ],
            "knowledge_hits": [
                {
                    "path": "WSP_knowledge/docs/Papers/PQN_Deep_Dive.md",
                    "title": "PQN",
                }
            ],
        },
    }
    payload.update(dict(zip(REPLICA_FIELDS, REPLICA_BINDING)))
    return payload


def test_holoindex_owner_service_avoids_local_store_and_preserves_evidence(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    head_sha = "2" * 40
    _set_repo_head(repo_root, head_sha)
    captured: dict = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["authorization"] = request.get_header("Authorization")
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return _HTTPResponse(_successful_query_payload(head_sha, repo_root))

    monkeypatch.setattr(owner_query_client, "urlopen", fake_urlopen)
    monkeypatch.setattr(
        HoloIndex,
        "__init__",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("remote query must not initialize local HoloIndex")
        ),
    )

    result = HoloIndexReadOnlyQueryAdapter(
        repo_root=repo_root,
        service_url="http://127.0.0.1:8765",
        service_token=SERVICE_TOKEN,
        service_timeout_seconds=4,
    ).query(
        query="WSP 97 research",
        allowed_paths=(
            "WSP_framework/src/WSP_97_Truth_Boundary_Protocol.md",
            "WSP_knowledge/docs/Papers/PQN_Deep_Dive.md",
        ),
        limit=8,
    )

    assert result["ok"] is True
    assert result["freshness"] == "CURRENT"
    assert result["source"] == "holoindex_owner_service"
    assert [hit["path"] for hit in result["hits"]] == [
        "WSP_framework/src/WSP_97_Truth_Boundary_Protocol.md",
        "WSP_knowledge/docs/Papers/PQN_Deep_Dive.md",
    ]
    assert captured["url"] == "http://127.0.0.1:8765/holoindex/v1/query"
    assert captured["authorization"] == f"Bearer {SERVICE_TOKEN}"
    assert captured["body"]["expected_repo_head_sha"] == head_sha
    assert captured["body"]["expected_repo_root_digest"] == repository_root_digest(
        repo_root
    )
    assert 0 < captured["timeout"] <= 4


def test_owner_client_rejects_foreign_root_digest(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    head_sha = "8" * 40
    _set_repo_head(repo_root, head_sha)
    payload = _successful_query_payload(head_sha, repo_root)
    payload["repo_root_digest"] = "sha256:" + "f" * 64
    monkeypatch.setattr(
        owner_query_client,
        "urlopen",
        lambda *_args, **_kwargs: _HTTPResponse(payload),
    )

    result = owner_query_client.query_holoindex_owner(
        repo_root=repo_root,
        query="WSP 97 research",
        limit=8,
        service_url="http://127.0.0.1:8765",
        service_token=SERVICE_TOKEN,
    )

    assert result["ok"] is False
    assert result["error"] == "REPO_ROOT_MISMATCH"
    assert "repository_root_mismatch" in result["stale_reasons"]


@pytest.mark.parametrize("missing_field", REPLICA_FIELDS)
def test_owner_client_requires_complete_replica_binding(
    tmp_path: Path, monkeypatch, missing_field: str,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    head_sha = "9" * 40
    _set_repo_head(repo_root, head_sha)
    payload = _successful_query_payload(head_sha, repo_root)
    payload.pop(missing_field)
    monkeypatch.setattr(
        owner_query_client, "urlopen", lambda *_args, **_kwargs: _HTTPResponse(payload)
    )

    result = owner_query_client.query_holoindex_owner(
        repo_root=repo_root, query="WSP 97 research", limit=8,
        service_url="http://127.0.0.1:8765", service_token=SERVICE_TOKEN,
    )

    assert result["ok"] is False
    assert result["error"] == "HOLOINDEX_QUERY_SERVICE_BINDING_MISMATCH"
    assert "query_replica_binding_mismatch" in result["stale_reasons"]


def test_explicit_empty_service_url_never_falls_back_to_environment(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _set_repo_head(repo_root, "3" * 40)
    monkeypatch.setenv(
        owner_query_client.HOLOINDEX_QUERY_SERVICE_URL_ENV,
        "http://127.0.0.1:8765",
    )

    result = owner_query_client.query_holoindex_owner(
        repo_root=repo_root,
        query="WSP 97 research",
        limit=8,
        service_url="",
        service_token=SERVICE_TOKEN,
    )

    assert result["ok"] is False
    assert result["error"] == "HOLOINDEX_QUERY_SERVICE_URL_MISSING"


def test_owner_client_response_body_obeys_absolute_deadline(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _set_repo_head(repo_root, "7" * 40)

    class SlowDripResponse:
        def __init__(self) -> None:
            self.closed = False

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            self.closed = True

        def read1(self, size: int = -1) -> bytes:
            del size
            time.sleep(0.03)
            return b"{"

    monkeypatch.setattr(
        owner_query_client,
        "urlopen",
        lambda *args, **kwargs: SlowDripResponse(),
    )

    started = time.monotonic()
    result = owner_query_client.query_holoindex_owner(
        repo_root=repo_root,
        query="WSP 97 research",
        limit=8,
        service_url="http://127.0.0.1:8765",
        service_token=SERVICE_TOKEN,
        timeout_seconds=0.12,
    )
    elapsed = time.monotonic() - started

    assert result["ok"] is False
    assert result["error"] == "HOLOINDEX_QUERY_DEADLINE_EXCEEDED"
    assert elapsed < 0.5


def _redirect_handler(
    status_code: int,
    received: list[tuple[str, str]],
) -> type[BaseHTTPRequestHandler]:
    class RedirectHandler(BaseHTTPRequestHandler):
        def _record(self) -> None:
            received.append((self.path, self.headers.get("Authorization", "")))

        def do_POST(self) -> None:
            content_length = int(self.headers.get("Content-Length", "0"))
            if content_length:
                self.rfile.read(content_length)
            self._record()
            if self.path == "/holoindex/v1/query":
                port = self.server.server_address[1]
                self.send_response(status_code)
                self.send_header("Location", f"http://127.0.0.1:{port}/capture")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            self.send_response(204)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def do_GET(self) -> None:
            self._record()
            self.send_response(204)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def log_message(self, *_args) -> None:
            return None

    return RedirectHandler


@pytest.mark.parametrize("status_code", [301, 302, 303, 307, 308])
def test_holoindex_owner_service_client_never_follows_redirects(
    tmp_path: Path,
    status_code: int,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _set_repo_head(repo_root, "6" * 40)
    received: list[tuple[str, str]] = []

    server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        _redirect_handler(status_code, received),
    )
    thread = threading.Thread(
        target=server.serve_forever,
        kwargs={"poll_interval": 0.01},
        daemon=True,
    )
    thread.start()
    try:
        result = owner_query_client.query_holoindex_owner(
            repo_root=repo_root,
            query="redirect safety",
            limit=8,
            service_url=(
                f"http://127.0.0.1:{server.server_address[1]}"
                "/holoindex/v1/query"
            ),
            service_token=REDIRECT_TOKEN,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=1)

    assert result["ok"] is False
    assert result["error"] == f"HOLOINDEX_QUERY_SERVICE_HTTP_{status_code}"
    assert received == [
        ("/holoindex/v1/query", f"Bearer {REDIRECT_TOKEN}")
    ]


def test_holoindex_owner_service_rejects_missing_token(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _set_repo_head(repo_root, "3" * 40)
    monkeypatch.delenv("HOLOINDEX_QUERY_SERVICE_TOKEN", raising=False)
    monkeypatch.setattr(
        owner_query_client,
        "urlopen",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("missing token must fail before HTTP")
        ),
    )

    result = HoloIndexReadOnlyQueryAdapter(
        repo_root=repo_root,
        service_url="http://127.0.0.1:8765",
    ).query(query="evidence", allowed_paths=(), limit=8)

    assert result["ok"] is False
    assert result["error"] == "HOLOINDEX_QUERY_SERVICE_TOKEN_MISSING"


def test_holoindex_owner_service_rejects_short_token_before_http(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        owner_query_client,
        "urlopen",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("short token must fail before HTTP")
        ),
    )

    result = HoloIndexReadOnlyQueryAdapter(
        repo_root=tmp_path,
        service_url="http://127.0.0.1:8765",
        service_token="too-short",
    ).query(query="evidence", allowed_paths=(), limit=8)

    assert result["ok"] is False
    assert result["error"] == "HOLOINDEX_QUERY_SERVICE_TOKEN_TOO_SHORT"


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com:8765",
        "http://localhost:8765",
        "http://[::1]:8765",
    ],
)
def test_holoindex_owner_service_rejects_non_loopback_url(
    tmp_path: Path,
    url: str,
) -> None:
    result = HoloIndexReadOnlyQueryAdapter(
        repo_root=tmp_path,
        service_url=url,
        service_token="token",
    ).query(query="evidence", allowed_paths=(), limit=8)

    assert result["ok"] is False
    assert result["error"] == "HOLOINDEX_QUERY_SERVICE_URL_NOT_LOOPBACK"


def test_owner_client_disables_environment_proxy_forwarding() -> None:
    proxy_handlers = [
        handler
        for handler in owner_query_client._NO_REDIRECT_OPENER.handlers
        if isinstance(handler, owner_query_client.ProxyHandler)
    ]
    assert proxy_handlers == []


def test_signed_path_scope_rejects_traversal_and_ambiguous_globs() -> None:
    allowed = ("modules/communication/moltbot_bridge/**",)
    assert holo_query_adapter.path_is_allowed(
        "modules/communication/moltbot_bridge/src/runtime.py",
        allowed,
    )
    assert not holo_query_adapter.path_is_allowed(
        "modules/communication/moltbot_bridge/../../.env",
        allowed,
    )
    assert not holo_query_adapter.path_is_allowed(
        "modules/communication/other.py",
        ("modules/*/other.py",),
    )


def test_client_repository_proof_obeys_total_deadline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def slow_repository(*_args, **_kwargs):
        time.sleep(0.2)
        return SimpleNamespace(proven_clean=True, head_sha="a" * 40, error="")

    monkeypatch.setattr(owner_query_client, "read_repository_state", slow_repository)
    monkeypatch.setattr(
        owner_query_client,
        "urlopen",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("deadline must fail before HTTP")
        ),
    )
    started = time.monotonic()
    result = owner_query_client.query_holoindex_owner(
        repo_root=tmp_path,
        query="evidence",
        limit=8,
        service_url="http://127.0.0.1:8127",
        service_token=SERVICE_TOKEN,
        timeout_seconds=0.03,
    )
    assert time.monotonic() - started < 0.15
    assert result["error"] == "HOLOINDEX_QUERY_DEADLINE_EXCEEDED"


@pytest.mark.parametrize(
    "timeout_seconds",
    (0, -1, float("nan"), float("inf"), "invalid"),
)
def test_owner_client_rejects_invalid_or_nonfinite_timeout(
    tmp_path: Path,
    timeout_seconds,
) -> None:
    result = owner_query_client.query_holoindex_owner(
        repo_root=tmp_path,
        query="evidence",
        limit=8,
        service_url="http://127.0.0.1:8127",
        service_token=SERVICE_TOKEN,
        timeout_seconds=timeout_seconds,
    )

    assert result["ok"] is False
    assert result["error"] == "HOLOINDEX_QUERY_TIMEOUT_INVALID"
