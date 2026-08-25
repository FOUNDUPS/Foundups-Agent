"""Focused tests for governed query-replica activation."""

from __future__ import annotations

import json
import os
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from holo_index.query_receipt import build_query_receipt
from holo_index.repository_state import RepositoryState

from modules.infrastructure.foundups_mcp_bridge.src import (
    reddog_holoindex_query_replica_activation as activation,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_acceptance_guards import (
    create_isolated_store,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_replica_activation import (
    QueryReplicaActivationDependencies,
    activate_query_replica,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_replica_activation_contract import (
    ACTIVATION_SCHEMA_VERSION,
    QueryReplicaActivationConfig,
    validate_activation_config,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_route_store import (
    QueryRouteStore,
)


HEAD = "a" * 40
ROOT_DIGEST = "sha256:" + "b" * 64
GENERATION = "sha256:" + "c" * 64
RECEIPT = "sha256:" + "d" * 64
DESCRIPTOR = "sha256:" + "e" * 64
REPLICA_ID = "sha256:" + "f" * 64
PATH_ID = "sha256:" + "1" * 64


def _config(tmp_path: Path, *, real: bool = True) -> QueryReplicaActivationConfig:
    repo = tmp_path / "repo"
    owner = tmp_path / "owner"
    canonical = tmp_path / "canonical"
    runtime = tmp_path / "runtime"
    for path in (repo, owner, canonical):
        path.mkdir()
    return QueryReplicaActivationConfig(
        repo_root=repo,
        owner_runtime_root=owner,
        canonical_store=canonical,
        replica_root=tmp_path / "replica",
        route_path=runtime / "route.json",
        route_runtime_root=runtime,
        receipt_path=runtime / "activation.json",
        expected_repo_head_sha=HEAD,
        timeout_seconds=60.0,
        real=real,
    )


def _binding(config: QueryReplicaActivationConfig, proof: object) -> object:
    public = {
        "query_replica_descriptor_digest": DESCRIPTOR,
        "query_replica_generation_id": GENERATION,
        "query_replica_id": REPLICA_ID,
        "query_replica_path_identity_digest": PATH_ID,
    }
    return SimpleNamespace(
        descriptor_path=config.replica_root / "holoindex_query_replica.active.json",
        descriptor_digest=DESCRIPTOR,
        generation_id=GENERATION,
        generation_directory=config.replica_root / "generations" / GENERATION[7:],
        replica_id=REPLICA_ID,
        path_identity_digest=PATH_ID,
        canonical_repo_head_sha=HEAD,
        canonical_repo_root_digest=ROOT_DIGEST,
        canonical_receipt_digest=RECEIPT,
        public_binding=public,
        artifacts=(SimpleNamespace(size=7), SimpleNamespace(size=11)),
    )


def _query_result(binding: object) -> dict:
    result = {
        "ok": True,
        "source": "holoindex_owner_service",
        "query": "RedDog governed HoloIndex exact-main activation canary",
        "freshness": "CURRENT",
        "hits": [{"path": "modules/example.py", "score": 0.9}],
        "raw_result": {"code_hits": [{"path": "modules/example.py", "score": 0.9}]},
        "error": "",
        "index_gap_detected": False,
        "stale_reasons": [],
        "freshness_generation_id": GENERATION,
        "freshness_receipt_digest": RECEIPT,
        "repo_head_sha": HEAD,
        "repo_root_digest": ROOT_DIGEST,
        "workspace_repo_head_sha": HEAD,
        "authority_repo_head_sha": HEAD,
        "authority_repo_root_digest": ROOT_DIGEST,
        "workspace_overlay_present": False,
        "semantic_evidence_authority": "clean_workspace_head",
        "no_authority_worktree_mutation_performed": True,
        "retrieval_mode": "semantic",
        "no_holoindex_reindex_performed": True,
        "no_reindex": True,
        **binding.public_binding,
    }
    result["query_receipt"] = dict(
        build_query_receipt(
            source="holoindex_owner_service",
            source_class="holoindex",
            query=result["query"],
            result=result,
            require_generation=True,
        )
    )
    return result


def _route(config: QueryReplicaActivationConfig, proof: object) -> object:
    binding = _binding(config, proof)
    route = SimpleNamespace(
        canonical_repo_root=config.repo_root,
        canonical_ssd_path=config.canonical_store,
        replica_root_proof=proof,
        binding=binding,
    )
    route.revalidate = lambda: binding
    return route


def _materialization(config: QueryReplicaActivationConfig, proof: object) -> object:
    binding = _binding(config, proof)
    return SimpleNamespace(
        active_descriptor=binding.descriptor_path,
        descriptor_digest=binding.descriptor_digest,
        generation_directory=binding.generation_directory,
        file_count=2,
        total_bytes=18,
    )


def _query_runner(
    config: QueryReplicaActivationConfig,
    calls: dict[str, object],
    query_results: list[dict] | None,
):
    def run_query(_payload, **kwargs):
        calls["queries"].append(kwargs)
        route = calls["route"]
        resolved = kwargs["resolve_replica_route"](
            canonical_repo_root=config.repo_root,
            canonical_ssd_path=config.canonical_store,
        )
        assert resolved is route
        results = query_results or [_query_result(route.binding)]
        return results[min(len(calls["queries"]) - 1, len(results) - 1)]

    return run_query


def _dependencies(
    config: QueryReplicaActivationConfig,
    *,
    query_results: list[dict] | None = None,
) -> tuple[QueryReplicaActivationDependencies, dict[str, object]]:
    state = RepositoryState(HEAD, True, "sha256:state", "")
    calls: dict[str, object] = {"queries": [], "proof": None, "route": None}

    def create_store(path, **kwargs):
        proof = create_isolated_store(path, **kwargs)
        calls["proof"] = proof
        return proof

    def build_route(**kwargs):
        route = _route(config, kwargs["replica_root_proof"])
        calls["route"] = route
        return route

    def materialize(**_kwargs):
        return _materialization(config, calls["proof"])

    dependencies = QueryReplicaActivationDependencies(
        read_state=lambda _root: state,
        cleanup_owner=lambda: None,
        ensure_current=lambda **_kwargs: SimpleNamespace(
            ready=True,
            error="",
            repo_head_sha=HEAD,
            generation_id=GENERATION,
            freshness_receipt_digest=RECEIPT,
        ),
        build_plan=lambda **_kwargs: SimpleNamespace(
            binding=object(), manifests=()
        ),
        create_store=create_store,
        materialize=materialize,
        build_owner_route=build_route,
        query=_query_runner(config, calls, query_results),
        now=lambda: datetime(2026, 8, 23, tzinfo=timezone.utc),
    )
    return dependencies, calls


def _route_store(config: QueryReplicaActivationConfig) -> QueryRouteStore:
    return QueryRouteStore(
        config.route_path,
        runtime_root=config.route_runtime_root,
        canonical_store=config.canonical_store,
        repo_roots=(config.repo_root,),
        create_runtime_root=False,
    )


def test_real_activation_commits_after_candidate_then_normal_query(
    tmp_path: Path, monkeypatch,
) -> None:
    config = _config(tmp_path)
    dependencies, calls = _dependencies(config)
    monkeypatch.setattr(
        activation,
        "resolve_query_replica_owner_route",
        lambda **_kwargs: calls["route"],
    )

    result = activate_query_replica(config, dependencies=dependencies)

    assert result.ok is True
    assert result.verdict == "PASS"
    assert result.route_committed is True
    assert result.post_query_replica_unchanged is True
    assert len(calls["queries"]) == 2
    candidate_route = calls["queries"][0]["resolve_replica_route"]()
    assert candidate_route is calls["route"]
    selected = _route_store(config).load_readonly()
    assert selected.record.revision == 1
    assert selected.record.replica == calls["route"].binding.public_binding
    payload = json.loads(config.receipt_path.read_text(encoding="ascii"))
    assert payload["schema_version"] == ACTIVATION_SCHEMA_VERSION
    assert payload["verdict"] == "PASS"
    assert payload["route_committed"] is True
    assert str(config.repo_root) not in config.receipt_path.read_text(encoding="ascii")


def test_candidate_query_failure_rolls_back_route(tmp_path: Path) -> None:
    config = _config(tmp_path)
    dependencies, calls = _dependencies(config)
    dependencies.query = lambda _payload, **_kwargs: {
        "ok": False,
        "error": "CANARY_FAILED",
    }

    result = activate_query_replica(config, dependencies=dependencies)

    assert result.ok is False
    assert result.verdict == "FAILED"
    assert result.route_committed is False
    assert _route_store(config).load_readonly().record.status == "EMPTY"
    assert config.replica_root.is_dir()
    assert calls["route"] is not None


@pytest.mark.parametrize(("dirty_read", "query_count"), ((4, 0), (5, 1)))
def test_repository_drift_blocks_route_commit(
    tmp_path: Path, dirty_read: int, query_count: int,
) -> None:
    config = _config(tmp_path)
    dependencies, calls = _dependencies(config)
    read_count = 0

    def read_state(_root):
        nonlocal read_count
        read_count += 1
        clean = read_count != dirty_read
        return RepositoryState(HEAD, clean, "sha256:state", "dirty" if not clean else "")

    dependencies.read_state = read_state
    result = activate_query_replica(config, dependencies=dependencies)

    assert result.error == "ACTIVATION_REPOSITORY_STATE_INVALID"
    assert result.route_committed is False
    assert len(calls["queries"]) == query_count
    assert _route_store(config).load_readonly().record.status == "EMPTY"


def test_postcommit_query_failure_is_not_reported_as_rollback(
    tmp_path: Path, monkeypatch,
) -> None:
    config = _config(tmp_path)
    dependencies, calls = _dependencies(config)
    good = _query_result(_binding(config, object()))
    def query_once_then_fail(payload, **kwargs):
        seen = bool(calls.get("query_seen"))
        calls["query_seen"] = True
        return {"ok": False} if seen else good

    dependencies.query = query_once_then_fail
    monkeypatch.setattr(
        activation,
        "resolve_query_replica_owner_route",
        lambda **_kwargs: calls["route"],
    )

    result = activate_query_replica(config, dependencies=dependencies)

    assert result.ok is False
    assert result.verdict == "COMMITTED_UNVERIFIED"
    assert result.route_committed is True
    assert _route_store(config).load_readonly().record.status == "CURRENT"


def test_default_is_inert_and_does_not_touch_filesystem(tmp_path: Path) -> None:
    config = _config(tmp_path, real=False)
    dependencies, _calls = _dependencies(config)
    dependencies.read_state = lambda _root: (_ for _ in ()).throw(
        AssertionError("inert activation must not inspect state")
    )

    result = activate_query_replica(config, dependencies=dependencies)

    assert result.verdict == "NOT_REQUESTED"
    assert not config.route_runtime_root.exists()
    assert not config.replica_root.exists()


def test_reserved_receipt_collision_fails_before_route_mutation(tmp_path: Path) -> None:
    config = _config(tmp_path)
    config = replace(
        config,
        receipt_path=config.route_path.with_name(config.route_path.name + ".journal"),
    )
    dependencies, _calls = _dependencies(config)

    result = activate_query_replica(config, dependencies=dependencies)

    assert result.error == "ACTIVATION_RUNTIME_PATH_COLLISION"
    assert not config.route_runtime_root.exists()
    assert not config.replica_root.exists()


def test_config_keeps_link_component_lexical_for_sealed_guard(
    tmp_path: Path,
) -> None:
    config = _config(tmp_path)
    linked = tmp_path / "linked-repo"
    try:
        os.symlink(config.repo_root, linked, target_is_directory=True)
    except OSError:
        pytest.skip("host cannot create directory links")

    validated = validate_activation_config(replace(config, repo_root=linked))

    assert validated.repo_root == linked
    assert validated.repo_root != config.repo_root


def test_zero_semantic_evidence_rolls_back_candidate(tmp_path: Path) -> None:
    config = _config(tmp_path)
    dependencies, calls = _dependencies(config)

    def empty_query(_payload, **_kwargs):
        route = calls["route"]
        result = _query_result(route.binding)
        result["hits"] = []
        result["raw_result"] = {}
        result["query_receipt"] = dict(
            build_query_receipt(
                source="holoindex_owner_service",
                source_class="holoindex",
                query=result["query"],
                result=result,
                require_generation=True,
            )
        )
        return result

    dependencies.query = empty_query
    result = activate_query_replica(config, dependencies=dependencies)

    assert result.verdict == "FAILED"
    assert result.route_committed is False
    assert _route_store(config).load_readonly().record.status == "EMPTY"


def test_postcommit_read_failure_preserves_committed_truth(
    tmp_path: Path, monkeypatch,
) -> None:
    config = _config(tmp_path)
    dependencies, calls = _dependencies(config)
    real_store = activation._store(config)

    class StoreWithFailedPostRead:
        def __getattr__(self, name):
            return getattr(real_store, name)

        def load_readonly(self):
            raise OSError("postcommit read unavailable")

    monkeypatch.setattr(activation, "_store", lambda _config: StoreWithFailedPostRead())
    result = activate_query_replica(config, dependencies=dependencies)

    assert calls["route"] is not None
    assert result.verdict == "COMMITTED_UNVERIFIED"
    assert result.route_committed is True
    assert real_store.load_readonly().record.status == "CURRENT"


def test_preexisting_receipt_fails_before_route_mutation(tmp_path: Path) -> None:
    config = _config(tmp_path)
    config.route_runtime_root.mkdir()
    config.receipt_path.write_text("{}\n", encoding="ascii")
    dependencies, _calls = _dependencies(config)

    result = activate_query_replica(config, dependencies=dependencies)

    assert result.error == "ACTIVATION_RECEIPT_EXISTS"
    assert not config.route_path.exists()
    assert not config.replica_root.exists()


def test_interrupt_after_commit_publishes_then_reraises(
    tmp_path: Path, monkeypatch,
) -> None:
    config = _config(tmp_path)
    dependencies, calls = _dependencies(config)
    good = _query_result(_binding(config, object()))

    def interrupt_normal_query(_payload, **_kwargs):
        if calls.setdefault("candidate_done", False):
            raise KeyboardInterrupt()
        calls["candidate_done"] = True
        return good

    dependencies.query = interrupt_normal_query
    monkeypatch.setattr(
        activation,
        "resolve_query_replica_owner_route",
        lambda **_kwargs: calls["route"],
    )

    with pytest.raises(KeyboardInterrupt):
        activate_query_replica(config, dependencies=dependencies)

    payload = json.loads(config.receipt_path.read_text(encoding="ascii"))
    assert payload["verdict"] == "COMMITTED_UNVERIFIED"
    assert payload["route_committed"] is True


def test_missing_receipt_for_committed_target_is_recovered(
    tmp_path: Path, monkeypatch,
) -> None:
    config = _config(tmp_path)
    dependencies, calls = _dependencies(config)
    real_publish = dependencies.publish
    dependencies.publish = lambda *_args, **_kwargs: (
        (_ for _ in ()).throw(KeyboardInterrupt())
    )
    monkeypatch.setattr(
        activation,
        "resolve_query_replica_owner_route",
        lambda **_kwargs: calls["route"],
    )

    with pytest.raises(KeyboardInterrupt):
        activate_query_replica(config, dependencies=dependencies)

    assert not config.receipt_path.exists()
    dependencies.publish = real_publish
    calls["queries"] = []
    result = activate_query_replica(config, dependencies=dependencies)

    assert result.ok is True
    assert result.route_committed is True
    payload = json.loads(config.receipt_path.read_text(encoding="ascii"))
    assert payload["recovered_committed_route"] is True
    assert payload["candidate_query_receipt_id"] == ""
    assert payload["normal_query_receipt_id"]
