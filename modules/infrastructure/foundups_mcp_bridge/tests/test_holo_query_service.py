"""Focused contract tests for the private HoloIndex owner service."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping

import pytest

from holo_index.freshness_receipt import (
    ALL_COLLECTIONS,
    CollectionFreshness,
    SCHEMA_VERSION as FRESHNESS_SCHEMA_VERSION,
    _receipt_generation_id,
)
from holo_index.repository_state import repository_root_digest
from holo_index.source_scope import canonical_source_scope_id
from modules.infrastructure.foundups_mcp_bridge.src.holo_query_service import (
    HoloIndexQueryOwnerService,
    TOKEN_TOO_SHORT_ERROR,
    main,
    validate_bind_host,
)
from modules.infrastructure.foundups_mcp_bridge.tests.holo_query_service_fixtures import (
    QUERY,
    SHA,
    SPACE_FINGERPRINT,
    TOKEN,
    _Backend,
    _raw_result,
)



def _test_digest(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _bind_receipt_generation(receipt: Mapping[str, Any]) -> Mapping[str, Any]:
    """Bind a synthetic receipt with the production v2 integrity algorithm."""
    value = dict(receipt)
    entries = [CollectionFreshness(**entry) for entry in value["collections"]]
    value["generation_id"] = _receipt_generation_id(
        str(value["repo_head_sha"]),
        entries,
        generated_at=str(value["generated_at"]),
        base_generation_id=str(value["base_generation_id"]),
        repo_root=str(value["repo_root"]),
        ssd_path=str(value["ssd_path"]),
        source=str(value["source"]),
    )
    return value


def _receipt(
    *,
    sha: str = SHA,
    generation: str = "generation-1",
    omit: str = "",
    repo_root: Path | str = "O:/Foundups-Agent",
    ssd_path: Path | str = "E:/HoloIndex",
) -> Mapping[str, Any]:
    collections = []
    for name in sorted(ALL_COLLECTIONS):
        if name == omit:
            continue
        collections.append(
            {
                "name": name,
                "count": 3,
                "status": "indexed",
                "source": "test",
                "repo_head_sha": sha,
                "last_indexed_at": "2026-07-18T00:00:00+00:00",
                "source_manifest_digest": _test_digest(f"manifest:{name}"),
                "indexed_paths_digest": _test_digest(f"paths:{name}"),
                "removed_paths_digest": _test_digest(f"removed:{name}"),
                "embedding_backend": "sentence_transformers",
                "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
                "embedding_space_fingerprint": SPACE_FINGERPRINT,
                "verification": "PASS",
                "proof_kind": "complete_source_manifest",
                "source_scope_id": canonical_source_scope_id(name),
                "source_policy_digest": _test_digest(f"policy:{name}"),
                "collection_snapshot_digest": _test_digest(f"snapshot:{name}"),
            }
        )
    receipt = {
        "schema_version": FRESHNESS_SCHEMA_VERSION,
        "generated_at": "2026-07-18T00:00:00+00:00",
        "repo_root": str(repo_root),
        "repo_head_sha": sha,
        "ssd_path": str(ssd_path),
        "source": f"test:{generation}" if generation else "test",
        "generation_id": "",
        "base_generation_id": "",
        "collections": collections,
    }
    return _bind_receipt_generation(receipt) if generation else receipt


def _request(**overrides: Any) -> Mapping[str, Any]:
    request = {
        "query": QUERY,
        "limit": 8,
        "doc_type_filter": "all",
        "expected_repo_head_sha": SHA,
    }
    request.update(overrides)
    return request


def _service(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    backend: Any | None = None,
    receipt_loader: Any | None = None,
    backend_factory: Any | None = None,
    preserve_receipt_identity: bool = False,
    **kwargs: Any,
) -> HoloIndexQueryOwnerService:
    monkeypatch.setenv("HOLOINDEX_QUERY_SERVICE_TOKEN", TOKEN)
    selected_backend = backend or _Backend()
    factory = backend_factory or (lambda _path: selected_backend)
    raw_loader = receipt_loader or (lambda _path: _receipt())
    def loader(path: Path):
        receipt = raw_loader(path)
        if preserve_receipt_identity:
            return receipt
        normalized = dict(receipt)
        normalized["repo_root"] = str(tmp_path)
        normalized["ssd_path"] = str(tmp_path / "holo-store")
        return (
            _bind_receipt_generation(normalized)
            if normalized.get("generation_id")
            else normalized
        )
    kwargs.setdefault(
        "repository_state_reader",
        lambda _root: SimpleNamespace(
            proven_clean=True,
            head_sha=SHA,
            error="",
        ),
    )
    return HoloIndexQueryOwnerService(
        repo_root=tmp_path,
        ssd_path=tmp_path / "holo-store",
        backend_factory=factory,
        receipt_loader=loader,
        **kwargs,
    )


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("repo_root", "O:/another-repo", "freshness_repo_root_mismatch"),
        ("ssd_path", "E:/another-store", "freshness_ssd_path_mismatch"),
    ],
)
def test_receipt_identity_mismatch_fails_at_query_time(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: str,
    reason: str,
) -> None:
    receipt = dict(_receipt())
    receipt["repo_root"] = str(tmp_path)
    receipt["ssd_path"] = str(tmp_path / "holo-store")
    receipt[field] = value
    owner = _service(
        tmp_path,
        monkeypatch,
        receipt_loader=lambda _path: receipt,
        preserve_receipt_identity=True,
    )
    try:
        result = _query(owner)
        assert result["ok"] is False
        assert reason in result["stale_reasons"]
    finally:
        owner.close()


def test_health_rejects_semantic_backend_with_zero_canary_hits(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = dict(_raw_result())
    for key in (
        "code_hits", "wsp_hits", "test_hits", "code", "wsps", "tests",
        "skills", "skill_hits", "symbol_hits", "docs_hits", "knowledge_hits",
        "docs", "knowledge", "work_ledger_hits", "work_ledger",
    ):
        raw[key] = []
    metadata = dict(raw["metadata"])
    for key in tuple(name for name in metadata if name.endswith("_count")):
        metadata[key] = 0
    raw["metadata"] = metadata
    backend = _Backend(raw)
    owner = _service(tmp_path, monkeypatch, backend=backend)
    try:
        result = owner.handle_health(authorization=f"Bearer {TOKEN}")
        assert result["ok"] is False
        assert result["error"] == "SEMANTIC_CANARY_EMPTY"
        assert result["status"] == "unavailable"
        assert result["hits"] == []
        assert result["raw_result"] == {}
    finally:
        owner.close()


def _query(owner: HoloIndexQueryOwnerService, request: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
    return owner.handle_query(
        request or _request(),
        authorization=f"Bearer {TOKEN}",
    )


def test_auth_fails_closed_without_env_or_valid_bearer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    backend = _Backend()
    factory_calls = 0

    def factory(_path: Path) -> _Backend:
        nonlocal factory_calls
        factory_calls += 1
        return backend

    owner = _service(tmp_path, monkeypatch, backend_factory=factory)
    try:
        assert "HOLOINDEX_QUERY_SERVICE_TOKEN" not in os.environ
        owner._bearer_token = ""
        assert owner.handle_query(_request(), authorization=f"Bearer {TOKEN}")["error"] == "AUTH_NOT_CONFIGURED"
        owner._bearer_token = "short"
        weak = owner.handle_query(_request(), authorization="Bearer short")
        assert weak["error"] == TOKEN_TOO_SHORT_ERROR
        owner._bearer_token = TOKEN
        assert owner.handle_query(_request(), authorization=None)["error"] == "UNAUTHORIZED"
        assert owner.handle_query(_request(), authorization="Bearer wrong")["error"] == "UNAUTHORIZED"
        assert factory_calls == 0
    finally:
        owner.close()


@pytest.mark.parametrize(
    ("override", "expected_error"),
    [
        ({"expected_repo_head_sha": ""}, "EXPECTED_REPO_HEAD_SHA_REQUIRED"),
        ({"expected_repo_head_sha": "A" * 40}, "EXPECTED_REPO_HEAD_SHA_REQUIRED"),
        ({"limit": 0}, "INVALID_LIMIT"),
        ({"limit": 51}, "INVALID_LIMIT"),
        ({"limit": True}, "INVALID_LIMIT"),
        ({"doc_type_filter": "work_ledger"}, "INVALID_DOC_TYPE_FILTER"),
        ({"query": ""}, "EMPTY_QUERY"),
        ({"unexpected": "field"}, "UNSUPPORTED_REQUEST_FIELDS"),
    ],
)
def test_request_contract_is_strict_and_bounded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    override: Mapping[str, Any],
    expected_error: str,
) -> None:
    backend = _Backend()
    owner = _service(tmp_path, monkeypatch, backend=backend)
    try:
        result = _query(owner, _request(**override))
        assert result["ok"] is False
        assert result["error"] == expected_error
        assert backend.search_calls == 0
    finally:
        owner.close()


def test_query_rejects_mismatched_expected_repository_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = _Backend()
    owner = _service(tmp_path, monkeypatch, backend=backend)
    try:
        result = _query(
            owner,
            _request(expected_repo_root_digest="sha256:" + "f" * 64),
        )
        assert result["ok"] is False
        assert result["error"] == "REPO_ROOT_MISMATCH"
        assert backend.search_calls == 0
    finally:
        owner.close()


def test_query_binds_matching_repository_root_digest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = _service(tmp_path, monkeypatch)
    try:
        result = _query(
            owner,
            _request(
                expected_repo_root_digest=repository_root_digest(tmp_path)
            ),
        )
        assert result["ok"] is True
        assert result["repo_root_digest"] == repository_root_digest(tmp_path)
    finally:
        owner.close()


def test_query_and_request_size_bounds_prevent_backend_work(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    backend = _Backend()
    owner = _service(
        tmp_path,
        monkeypatch,
        backend=backend,
        max_query_chars=12,
        max_request_bytes=256,
    )
    try:
        assert _query(owner, _request(query="x" * 13))["error"] == "QUERY_TOO_LARGE"
        result = owner.handle_query(
            _request(),
            authorization=f"Bearer {TOKEN}",
            request_size=257,
        )
        assert result["error"] == "REQUEST_TOO_LARGE"
        assert backend.search_calls == 0
    finally:
        owner.close()


def test_loopback_binding_rejects_wildcard_and_remote_hosts() -> None:
    assert validate_bind_host("127.0.0.1") == "127.0.0.1"
    for host in (
        "localhost", "0.0.0.0", "::", "::1", "192.0.2.10", "service.internal"
    ):
        with pytest.raises(ValueError, match="LOOPBACK_REQUIRED"):
            validate_bind_host(host)


def test_cli_refuses_non_loopback_before_token_or_uvicorn(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--host", "0.0.0.0"]) == 2
    assert "LOOPBACK_REQUIRED" in capsys.readouterr().out


def test_cli_refuses_short_bearer_without_starting_owner(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("HOLOINDEX_QUERY_SERVICE_TOKEN", "short")
    assert main(["--host", "127.0.0.1"]) == 2
    assert capsys.readouterr().out.strip() == TOKEN_TOO_SHORT_ERROR


def test_missing_receipt_and_generation_fail_before_backend_init(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    factory_calls = 0

    def factory(_path: Path) -> _Backend:
        nonlocal factory_calls
        factory_calls += 1
        return _Backend()

    def missing(_path: Path) -> Any:
        raise FileNotFoundError

    owner = _service(tmp_path, monkeypatch, receipt_loader=missing, backend_factory=factory)
    try:
        result = _query(owner)
        assert result["freshness"] == "UNKNOWN"
        assert result["error"] == "MISSING_GENERATION_BINDING"
        assert result["stale_reasons"] == ["missing_freshness_receipt"]
        assert factory_calls == 0
    finally:
        owner.close()

    no_generation = dict(_receipt(generation=""))
    owner = _service(
        tmp_path,
        monkeypatch,
        receipt_loader=lambda _path: no_generation,
        backend_factory=factory,
    )
    try:
        result = _query(owner)
        assert result["freshness"] == "STALE"
        assert result["error"] == "MISSING_GENERATION_BINDING"
        assert "missing_holoindex_generation_id" in result["stale_reasons"]
        assert factory_calls == 0
    finally:
        owner.close()


def test_exact_sha_and_all_seven_collection_proofs_are_required(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    backend = _Backend()
    old_sha = "b" * 40
    owner = _service(
        tmp_path,
        monkeypatch,
        backend=backend,
        receipt_loader=lambda _path: _receipt(sha=old_sha),
    )
    try:
        result = _query(owner)
        assert result["error"] == "REPO_HEAD_MISMATCH"
        assert result["stale_reasons"][0] == "stale_repo_head_sha"
        assert len([r for r in result["stale_reasons"] if r.startswith("stale_collection_sha:")]) == 7
        assert backend.search_calls == 0
    finally:
        owner.close()


def test_invalid_first_valid_second_duplicate_receipt_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    receipt = dict(_receipt())
    collections = [dict(entry) for entry in receipt["collections"]]
    duplicate_name = collections[0]["name"]
    valid = dict(collections[0])
    collections[0]["embedding_space_fingerprint"] = ""
    collections.append(valid)
    receipt["collections"] = collections
    backend = _Backend()
    owner = _service(
        tmp_path,
        monkeypatch,
        backend=backend,
        receipt_loader=lambda _path: receipt,
    )
    try:
        result = _query(owner)
        assert result["ok"] is False
        assert f"duplicate_collection_receipt:{duplicate_name}" in result[
            "stale_reasons"
        ]
        assert f"duplicate_collection_embedding_space:{duplicate_name}" in result[
            "stale_reasons"
        ]
        assert backend.search_calls == 0
    finally:
        owner.close()

    owner = _service(
        tmp_path,
        monkeypatch,
        backend=backend,
        receipt_loader=lambda _path: _receipt(omit="navigation_knowledge"),
    )
    try:
        result = _query(owner)
        assert result["error"] == "STALE_INDEX"
        assert "missing_collection_receipt:navigation_knowledge" in result["stale_reasons"]
        assert backend.search_calls == 0
    finally:
        owner.close()


def test_stable_semantic_generation_preserves_complete_raw_wsp_and_knowledge(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw = _raw_result()
    backend = _Backend(raw)
    owner = _service(tmp_path, monkeypatch, backend=backend)
    try:
        result = _query(owner)
        assert result["ok"] is True
        assert result["freshness"] == "CURRENT"
        assert result["retrieval_mode"] == "semantic"
        assert result["freshness_generation_id"] == _receipt(
            repo_root=tmp_path,
            ssd_path=tmp_path / "holo-store",
        )["generation_id"]
        assert result["repo_head_sha"] == SHA
        assert result["raw_result"] == raw
        assert result["raw_result"]["wsp_hits"] == raw["wsp_hits"]
        assert result["raw_result"]["knowledge_hits"] == raw["knowledge_hits"]
        hit_types = {hit["type"] for hit in result["hits"]}
        assert {"wsp", "knowledge"}.issubset(hit_types)
        assert result["no_holoindex_reindex_performed"] is True
        assert backend.search_calls == 1
        assert backend.index_calls == 0
    finally:
        owner.close()


@pytest.mark.parametrize("mode", ["lexical", "failed", "unknown"])
def test_nonsemantic_modes_are_rejected_without_untrusted_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    raw = _raw_result(mode=mode)
    backend = _Backend(raw, mode=mode)
    owner = _service(tmp_path, monkeypatch, backend=backend)
    try:
        result = _query(owner)
        assert result["ok"] is False
        assert result["error"] == "SEMANTIC_BACKEND_UNAVAILABLE"
        assert result["retrieval_mode"] == mode
        assert result["raw_result"] == {}
        assert result["hits"] == []
    finally:
        owner.close()


def test_search_error_payload_is_not_accepted_as_semantic_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw = _raw_result(error="collection read failed")
    owner = _service(tmp_path, monkeypatch, backend=_Backend(raw))
    try:
        assert _query(owner)["error"] == "SEMANTIC_BACKEND_UNAVAILABLE"
    finally:
        owner.close()




def test_repository_is_reproven_after_semantic_retrieval(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    clean = SimpleNamespace(proven_clean=True, head_sha=SHA, error="")
    changed = SimpleNamespace(
        proven_clean=True, head_sha="b" * 40, error=""
    )
    states = iter([clean, changed])
    receipt_reads = 0

    def load_receipt(_path: Path) -> Mapping[str, Any]:
        nonlocal receipt_reads
        receipt_reads += 1
        return _receipt()

    backend = _Backend()
    owner = _service(
        tmp_path,
        monkeypatch,
        backend=backend,
        receipt_loader=load_receipt,
        repository_state_reader=lambda _root: next(states),
    )
    try:
        result = _query(owner)
        assert result["error"] == "REPO_HEAD_MISMATCH"
        assert result["raw_result"] == {}
        assert result["hits"] == []
        assert backend.search_calls == 1
        assert receipt_reads == 1
    finally:
        owner.close()


def test_repository_is_reproven_after_final_freshness_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    clean = SimpleNamespace(proven_clean=True, head_sha=SHA, error="")
    dirty = SimpleNamespace(
        proven_clean=False,
        head_sha=SHA,
        error="HOLOINDEX_REPOSITORY_DIRTY",
    )
    states = iter([clean, clean, dirty])
    receipt_reads = 0

    def load_receipt(_path: Path) -> Mapping[str, Any]:
        nonlocal receipt_reads
        receipt_reads += 1
        return _receipt()

    backend = _Backend()
    owner = _service(
        tmp_path,
        monkeypatch,
        backend=backend,
        receipt_loader=load_receipt,
        repository_state_reader=lambda _root: next(states),
    )
    try:
        result = _query(owner)
        assert result["error"] == "HOLOINDEX_REPOSITORY_DIRTY"
        assert result["raw_result"] == {}
        assert result["hits"] == []
        assert backend.search_calls == 1
        assert receipt_reads == 2
    finally:
        owner.close()
