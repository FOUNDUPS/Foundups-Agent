"""Tests for the RedDog HoloIndex owner and direct query truth boundary."""

from __future__ import annotations

import io
import json
import os
from pathlib import Path
from types import SimpleNamespace
from urllib.error import HTTPError

import pytest

from holo_index.core.holo_index import HoloIndex
from holo_index.freshness_receipt import (
    CollectionFreshness,
    HoloIndexFreshnessReceipt,
    read_git_head_sha,
    write_freshness_receipt,
)
from holo_index.source_scope import canonical_source_scope_id
from modules.communication.moltbot_bridge.src.reddog_readonly_0102_audit_worker_runtime import (
    HoloIndexReadOnlyQueryAdapter,
)
import modules.communication.moltbot_bridge.src.reddog_holoindex_owner_query_client as owner_query_client
import modules.communication.moltbot_bridge.src.reddog_holoindex_query_adapter as holo_query_adapter


HOLO_BASELINE_COLLECTIONS = (
    "navigation_code",
    "navigation_symbols",
    "navigation_wsp",
    "navigation_tests",
    "navigation_skills",
    "navigation_docs",
    "navigation_knowledge",
)
SERVICE_TOKEN = "test-token-" + "x" * 32


@pytest.fixture(autouse=True)
def _clean_repository_state(monkeypatch):
    clean_state = lambda root: SimpleNamespace(
        proven_clean=True,
        head_sha=read_git_head_sha(root),
        error="",
    )
    monkeypatch.setattr(owner_query_client, "read_repository_state", clean_state)


def _write_holo_receipt(
    path: Path,
    *,
    repo_root: Path,
    head_sha: str,
    unverified: tuple[str, ...] = (),
) -> None:
    entries = [
        CollectionFreshness(
            name=name,
            source_scope_id=canonical_source_scope_id(name),
            count=1,
            status="indexed",
            source="test",
            repo_head_sha=head_sha,
            last_indexed_at="2026-07-18T00:00:00+00:00",
            source_manifest_digest=f"sha256:manifest:{name}",
            indexed_paths_digest=f"sha256:paths:{name}",
            removed_paths_digest="sha256:removed",
            verification="UNVERIFIED" if name in unverified else "PASS",
            proof_kind=(
                "unverified"
                if name in unverified
                else "complete_source_manifest"
            ),
        )
        for name in HOLO_BASELINE_COLLECTIONS
    ]
    write_freshness_receipt(
        HoloIndexFreshnessReceipt(
            schema_version="holoindex_freshness_receipt.v1",
            generated_at="2026-07-18T00:00:00+00:00",
            repo_root=str(repo_root),
            repo_head_sha=head_sha,
            ssd_path=str(path.parents[1]),
            source="test",
            generation_id="sha256:" + "a" * 64,
            collections=entries,
        ),
        path,
    )


def _set_repo_head(repo_root: Path, head_sha: str) -> None:
    git_dir = repo_root / ".git"
    git_dir.mkdir(parents=True, exist_ok=True)
    (git_dir / "HEAD").write_text(head_sha + "\n", encoding="utf-8")


def _patch_holo_search(monkeypatch, result: dict | None = None) -> None:
    monkeypatch.setattr(HoloIndex, "__init__", lambda self, *args, **kwargs: None)
    monkeypatch.setattr(
        HoloIndex,
        "search",
        lambda self, query, limit: result
        or {
            "wsp_hits": [
                {
                    "path": "WSP_framework/src/WSP_97_Truth_Boundary_Protocol.md",
                    "title": "WSP 97",
                    "score": 0.99,
                }
            ],
            "metadata": {"retrieval_mode": "semantic"},
        },
    )


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




def test_default_reddog_adapter_requires_owner_and_never_opens_local_chroma(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.delenv("HOLOINDEX_QUERY_SERVICE_URL", raising=False)
    monkeypatch.setattr(
        HoloIndex,
        "__init__",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("default RedDog adapter must not open local Chroma")
        ),
    )

    result = HoloIndexReadOnlyQueryAdapter(repo_root=tmp_path).query(
        query="evidence",
        allowed_paths=(),
        limit=8,
    )

    assert result["ok"] is False
    assert result["error"] == "HOLOINDEX_QUERY_SERVICE_NOT_CONFIGURED"
    assert result["stale_reasons"] == ["holoindex_owner_service_required"]


def test_default_adapter_uses_private_auto_owner_without_exporting_token(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.delenv("HOLOINDEX_QUERY_SERVICE_URL", raising=False)
    monkeypatch.delenv("HOLOINDEX_QUERY_SERVICE_TOKEN", raising=False)
    captured: list[dict] = []
    monkeypatch.setattr(
        holo_query_adapter,
        "resolve_reddog_holoindex_owner_handoff",
        lambda: ("http://127.0.0.1:8127", SERVICE_TOKEN),
    )

    def query_owner(**kwargs):
        captured.append(kwargs)
        return {
            "ok": True,
            "raw_result": {},
            "freshness": "CURRENT",
            "stale_reasons": [],
        }

    monkeypatch.setattr(holo_query_adapter, "query_holoindex_owner", query_owner)
    result = HoloIndexReadOnlyQueryAdapter(repo_root=tmp_path).query(
        query="evidence",
        allowed_paths=(),
        limit=8,
    )

    assert result["ok"] is True
    assert captured[0]["service_url"] == "http://127.0.0.1:8127"
    assert captured[0]["service_token"] == SERVICE_TOKEN
    assert "HOLOINDEX_QUERY_SERVICE_TOKEN" not in os.environ


def _poisoned_owner_payload(head_sha: str) -> dict:
    return {
        "schema_version": "holoindex_query_service.v1",
        "ok": False,
        "source": "holoindex",
        "freshness": "STALE",
        "error": "QUERY_TIMEOUT",
        "stale_reasons": ["backend_timeout_owner_poisoned"],
        "index_gap_detected": True,
        "no_holoindex_reindex_performed": True,
        "freshness_generation_id": "generation-old",
        "freshness_receipt_digest": "sha256:receipt-old",
        "repo_head_sha": head_sha,
        "retrieval_mode": "semantic",
        "raw_result": {},
    }


def _replacement_owner_payload(head_sha: str) -> dict:
    return {
        "schema_version": "holoindex_query_service.v1",
        "ok": True,
        "source": "holoindex",
        "freshness": "CURRENT",
        "error": "",
        "stale_reasons": [],
        "index_gap_detected": False,
        "no_holoindex_reindex_performed": True,
        "freshness_generation_id": "generation-new",
        "freshness_receipt_digest": "sha256:receipt-new",
        "repo_head_sha": head_sha,
        "retrieval_mode": "semantic",
        "raw_result": {
            "wsp_hits": [{"path": "WSP_framework/src/WSP_97.md"}],
        },
    }


def _poison_then_success_transport(
    head_sha: str,
    authorizations: list[str],
):
    attempts: list[int] = []

    def transport(request, timeout):
        del timeout
        attempts.append(1)
        authorizations.append(request.get_header("Authorization"))
        if len(attempts) == 1:
            payload = _poisoned_owner_payload(head_sha)
            raise HTTPError(
                request.full_url,
                504,
                "timeout",
                {},
                io.BytesIO(json.dumps(payload).encode("utf-8")),
            )
        return _HTTPResponse(_replacement_owner_payload(head_sha))

    return transport, attempts


def test_private_owner_poison_timeout_restarts_and_retries_once(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    head_sha = "7" * 40
    _set_repo_head(repo_root, head_sha)
    new_token = "replacement-" + ("r" * 32)
    authorizations: list[str] = []
    transport, attempts = _poison_then_success_transport(
        head_sha,
        authorizations,
    )

    monkeypatch.delenv("HOLOINDEX_QUERY_SERVICE_URL", raising=False)
    monkeypatch.delenv("HOLOINDEX_QUERY_SERVICE_TOKEN", raising=False)
    monkeypatch.setattr(owner_query_client, "urlopen", transport)
    monkeypatch.setattr(
        holo_query_adapter,
        "resolve_reddog_holoindex_owner_handoff",
        lambda: ("http://127.0.0.1:8127", SERVICE_TOKEN),
    )
    monkeypatch.setattr(
        holo_query_adapter,
        "restart_reddog_holoindex_owner",
        lambda **_kwargs: ("http://127.0.0.1:8127", new_token),
    )

    result = HoloIndexReadOnlyQueryAdapter(repo_root=repo_root).query(
        query="evidence",
        allowed_paths=("WSP_framework/src/WSP_97.md",),
        limit=8,
    )

    assert result["ok"] is True
    assert len(attempts) == 2
    assert authorizations == [
        f"Bearer {SERVICE_TOKEN}",
        f"Bearer {new_token}",
    ]


def test_explicit_external_owner_is_never_restarted(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        holo_query_adapter,
        "query_holoindex_owner",
        lambda **_kwargs: {
            "ok": False,
            "error": "QUERY_OWNER_POISONED",
            "stale_reasons": ["backend_timeout_owner_poisoned"],
            "raw_result": {},
        },
    )
    monkeypatch.setattr(
        holo_query_adapter,
        "restart_reddog_holoindex_owner",
        lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("external owner must not be restarted")
        ),
    )
    result = HoloIndexReadOnlyQueryAdapter(
        repo_root=tmp_path,
        service_url="http://127.0.0.1:8127",
        service_token=SERVICE_TOKEN,
    ).query(query="evidence", allowed_paths=(), limit=8)
    assert result["ok"] is False
    assert result["error"] == "QUERY_OWNER_POISONED"


def test_explicit_owner_configuration_precedes_private_handoff(
    tmp_path: Path,
    monkeypatch,
) -> None:
    explicit_token = "explicit-" + ("z" * 32)
    monkeypatch.setattr(
        holo_query_adapter,
        "resolve_reddog_holoindex_owner_handoff",
        lambda: (_ for _ in ()).throw(AssertionError("private fallback used")),
    )
    captured: list[dict] = []
    monkeypatch.setattr(
        holo_query_adapter,
        "query_holoindex_owner",
        lambda **kwargs: captured.append(kwargs)
        or {
            "ok": True,
            "raw_result": {},
            "freshness": "CURRENT",
            "stale_reasons": [],
        },
    )
    result = HoloIndexReadOnlyQueryAdapter(
        repo_root=tmp_path,
        service_url="http://127.0.0.1:9000",
        service_token=explicit_token,
    ).query(query="evidence", allowed_paths=(), limit=8)

    assert result["ok"] is True
    assert captured[0]["service_url"] == "http://127.0.0.1:9000"
    assert captured[0]["service_token"] == explicit_token


def test_holoindex_owner_service_client_rejects_missing_generation_binding(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    head_sha = "4" * 40
    _set_repo_head(repo_root, head_sha)
    monkeypatch.setattr(
        owner_query_client,
        "urlopen",
        lambda *args, **kwargs: _HTTPResponse(
            {
                "schema_version": "holoindex_query_service.v1",
                "ok": True,
                "source": "holoindex",
                "freshness": "CURRENT",
                "error": "",
                "stale_reasons": [],
                "index_gap_detected": False,
                "no_holoindex_reindex_performed": True,
                "repo_head_sha": head_sha,
                "retrieval_mode": "semantic",
                "raw_result": {"wsp_hits": []},
            }
        ),
    )

    result = HoloIndexReadOnlyQueryAdapter(
        repo_root=repo_root,
        service_url="http://127.0.0.1:8765/holoindex/v1/query",
        service_token=SERVICE_TOKEN,
    ).query(query="evidence", allowed_paths=(), limit=8)

    assert result["ok"] is False
    assert result["error"] == "MISSING_GENERATION_BINDING"
    assert result["freshness"] == "STALE"
    assert result["index_gap_detected"] is True


def test_client_rejects_incoherent_success_contract(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    head_sha = "8" * 40
    _set_repo_head(repo_root, head_sha)
    monkeypatch.setattr(
        owner_query_client,
        "urlopen",
        lambda *_args, **_kwargs: _HTTPResponse({
            "schema_version": "holoindex_query_service.v1",
            "ok": True, "source": "holoindex", "freshness": "CURRENT",
            "error": "", "stale_reasons": ["stale_collection"],
            "index_gap_detected": True,
            "no_holoindex_reindex_performed": True,
            "repo_head_sha": head_sha,
            "freshness_generation_id": "generation",
            "freshness_receipt_digest": "sha256:receipt",
            "retrieval_mode": "semantic", "raw_result": {},
        }),
    )
    result = HoloIndexReadOnlyQueryAdapter(
        repo_root=repo_root,
        service_url="http://127.0.0.1:8127",
        service_token=SERVICE_TOKEN,
    ).query(query="evidence", allowed_paths=(), limit=8)
    assert result["ok"] is False
    assert result["freshness"] == "STALE"
    assert result["error"] == "HOLOINDEX_QUERY_SERVICE_CONTRACT_INVALID"
    assert "owner_response_contract_invalid" in result["stale_reasons"]


@pytest.mark.parametrize(
    "post_state",
    [
        SimpleNamespace(proven_clean=False, head_sha="4" * 40, error="DIRTY_WORKTREE"),
        SimpleNamespace(proven_clean=True, head_sha="5" * 40, error=""),
    ],
)
def test_holoindex_owner_service_rejects_repository_change_during_query(
    tmp_path: Path,
    monkeypatch,
    post_state: SimpleNamespace,
) -> None:
    expected_head = "4" * 40
    states = iter(
        [
            SimpleNamespace(proven_clean=True, head_sha=expected_head, error=""),
            post_state,
        ]
    )
    monkeypatch.setattr(
        owner_query_client,
        "read_repository_state",
        lambda _root: next(states),
    )
    monkeypatch.setattr(
        owner_query_client,
        "urlopen",
        lambda *args, **kwargs: _HTTPResponse(
            {
                "schema_version": "holoindex_query_service.v1",
                "ok": True,
                "source": "holoindex",
                "freshness": "CURRENT",
                "error": "",
                "stale_reasons": [],
                "index_gap_detected": False,
                "no_holoindex_reindex_performed": True,
                "repo_head_sha": expected_head,
                "freshness_generation_id": "sha256:" + "a" * 64,
                "freshness_receipt_digest": "sha256:" + "b" * 64,
                "retrieval_mode": "semantic",
                "raw_result": {"wsp_hits": []},
            }
        ),
    )

    result = HoloIndexReadOnlyQueryAdapter(
        repo_root=tmp_path,
        service_url="http://127.0.0.1:8765",
        service_token=SERVICE_TOKEN,
    ).query(query="evidence", allowed_paths=(), limit=8)

    assert result["ok"] is False
    assert result["error"] == "REPOSITORY_STATE_CHANGED_DURING_QUERY"
    assert result["freshness"] == "STALE"
    assert result["stale_reasons"] == ["repository_state_changed_during_query"]
