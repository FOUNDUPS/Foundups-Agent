"""Transport-level tests for the dependency-free HoloIndex HTTP runtime."""

from __future__ import annotations

import http.client
import json
import threading
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping

import pytest

from holo_index.freshness_receipt import SCHEMA_VERSION
from holo_index.source_scope import canonical_source_scope_id
from modules.communication.moltbot_bridge.src import (
    reddog_holoindex_owner_query_client as owner_client,
)
from modules.communication.moltbot_bridge.src.reddog_holoindex_query_adapter import (
    HoloIndexReadOnlyQueryAdapter,
)
from modules.infrastructure.foundups_mcp_bridge.src import (
    holo_query_service_http as http_module,
)
from modules.infrastructure.foundups_mcp_bridge.src.holo_query_service import (
    BASELINE_COLLECTIONS,
    QUERY_PATH,
    HoloIndexQueryOwnerService,
    main,
)


TOKEN = "stdlib-owner-service-token-with-strong-length"
SHA = "a" * 40
SPACE_FINGERPRINT = "sha256:" + ("1" * 64)


def _receipt(repo_root: Path, ssd_path: Path) -> Mapping[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": "2026-07-18T00:00:00+00:00",
        "repo_root": str(repo_root.resolve(strict=False)),
        "repo_head_sha": SHA,
        "ssd_path": str(ssd_path.resolve(strict=False)),
        "source": "test",
        "generation_id": "generation-1",
        "base_generation_id": "",
        "collections": [
            {
                "name": name,
                "count": 1,
                "status": "indexed",
                "source": "test",
                "repo_head_sha": SHA,
                "last_indexed_at": "2026-07-18T00:00:00+00:00",
                "source_manifest_digest": f"sha256:manifest-{name}",
                "indexed_paths_digest": f"sha256:paths-{name}",
                "removed_paths_digest": "sha256:removed",
                "embedding_backend": "sentence_transformers",
                "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
                "embedding_space_fingerprint": SPACE_FINGERPRINT,
                "verification": "PASS",
                "proof_kind": "complete_source_manifest",
                "source_scope_id": canonical_source_scope_id(name),
            }
            for name in sorted(BASELINE_COLLECTIONS)
        ],
    }


class _Backend:
    retrieval_mode = "semantic"
    collection_embedding_space_map = {
        name: SPACE_FINGERPRINT for name in BASELINE_COLLECTIONS
    }

    def search(
        self,
        query: str,
        *,
        limit: int,
        doc_type_filter: str,
    ) -> Mapping[str, Any]:
        return {
            "wsp_hits": [{"path": "WSP_framework/src/WSP_97.md"}],
            "knowledge_hits": [{"path": "WSP_knowledge/docs/Papers/example.md"}],
            "metadata": {
                "retrieval_mode": "semantic",
                "embedding_backend": "sentence_transformers",
                "collection_embedding_space_map": {
                    name: SPACE_FINGERPRINT for name in BASELINE_COLLECTIONS
                },
            },
        }


def _owner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> HoloIndexQueryOwnerService:
    monkeypatch.setenv("HOLOINDEX_QUERY_SERVICE_TOKEN", TOKEN)
    ssd_path = tmp_path / "holo-store"
    return HoloIndexQueryOwnerService(
        repo_root=tmp_path,
        ssd_path=ssd_path,
        backend_factory=lambda _path: _Backend(),
        receipt_loader=lambda _path: _receipt(tmp_path, ssd_path),
        repository_state_reader=lambda _root: SimpleNamespace(
            proven_clean=True,
            head_sha=SHA,
            error="",
        ),
    )


def test_stdlib_runtime_serves_authenticated_generation_bound_query(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = _owner(tmp_path, monkeypatch)
    server = http_module.create_stdlib_server(
        owner,
        host="127.0.0.1",
        port=0,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    connection = http.client.HTTPConnection(
        "127.0.0.1",
        server.server_address[1],
        timeout=2,
    )
    try:
        body = json.dumps(
            {
                "query": "find operational contract",
                "limit": 8,
                "doc_type_filter": "all",
                "expected_repo_head_sha": SHA,
            }
        )
        connection.request(
            "POST",
            QUERY_PATH,
            body=body,
            headers={
                "Authorization": f"Bearer {TOKEN}",
                "Content-Type": "application/json",
            },
        )
        response = connection.getresponse()
        payload = json.loads(response.read())
        assert response.status == 200
        assert payload["ok"] is True
        assert payload["freshness"] == "CURRENT"
        assert payload["raw_result"]["wsp_hits"]
        assert payload["raw_result"]["knowledge_hits"]
    finally:
        connection.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        owner.close()


def test_reddog_adapter_queries_live_owner_without_opening_local_chroma(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = _owner(tmp_path, monkeypatch)
    server = http_module.create_stdlib_server(
        owner,
        host="127.0.0.1",
        port=0,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setattr(
        owner_client,
        "read_repository_state",
        lambda _root: SimpleNamespace(
            proven_clean=True,
            head_sha=SHA,
            error="",
        ),
    )
    try:
        result = HoloIndexReadOnlyQueryAdapter(
            repo_root=tmp_path,
            service_url=f"http://127.0.0.1:{server.server_address[1]}",
            service_token=TOKEN,
        ).query(
            query="find operational contract",
            allowed_paths=(
                "WSP_framework/src/WSP_97.md",
                "WSP_knowledge/docs/Papers/example.md",
            ),
            limit=8,
        )
        assert result["ok"] is True
        assert result["freshness"] == "CURRENT"
        assert result["retrieval_mode"] == "semantic"
        assert result["repo_head_sha"] == SHA
        assert result["freshness_generation_id"] == "generation-1"
        assert {hit["path"] for hit in result["hits"]} == {
            "WSP_framework/src/WSP_97.md",
            "WSP_knowledge/docs/Papers/example.md",
        }
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        owner.close()


def test_main_dispatches_to_stdlib_when_fastapi_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []

    class FakeOwner:
        def close(self) -> None:
            events.append("owner_closed")

    class FakeServer:
        def serve_forever(self) -> None:
            events.append("served")

        def server_close(self) -> None:
            events.append("server_closed")

    monkeypatch.setenv("HOLOINDEX_QUERY_SERVICE_TOKEN", TOKEN)
    monkeypatch.setattr(http_module, "FastAPI", None)
    monkeypatch.setattr(
        http_module,
        "HoloIndexQueryOwnerService",
        lambda **_kwargs: FakeOwner(),
    )
    monkeypatch.setattr(
        http_module,
        "create_stdlib_server",
        lambda _owner, **_kwargs: FakeServer(),
    )
    assert main(["--host", "127.0.0.1", "--port", "8127"]) == 0
    assert events == ["served", "server_closed", "owner_closed"]
