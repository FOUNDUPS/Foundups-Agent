"""Fail-closed host resolution for RedDog query-replica owner routes."""

from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from modules.infrastructure.foundups_mcp_bridge.src import (
    reddog_holoindex_owner_replica_route as route_module,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_acceptance_guards import (
    AcceptanceGuardError,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_route_contract import (
    prove_route_record,
    route_record_from_mapping,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_route_store import (
    QueryRouteStore,
)
from modules.infrastructure.shared_utilities.runtime_atomic_replace import (
    atomic_replace_runtime_text,
)


def _digest(character: str) -> str:
    return "sha256:" + character * 64


def _file_state(path: Path) -> tuple[int, int, int, int, int, int]:
    metadata = os.lstat(path)
    return (
        int(metadata.st_dev), int(metadata.st_ino), int(metadata.st_mode),
        int(metadata.st_nlink), int(metadata.st_size), int(metadata.st_mtime_ns),
    )


def _install_route_file(
    tmp_path: Path,
) -> tuple[Path, Path, Path, Path, dict[str, str]]:
    repo, ssd, replica, runtime = (
        tmp_path / "repo", tmp_path / "ssd", tmp_path / "replica",
        tmp_path / "runtime",
    )
    for path in (repo, ssd, replica):
        path.mkdir()
    route_path = runtime / "reddog_holoindex_query_route.json"
    store = QueryRouteStore(
        route_path, runtime_root=runtime, canonical_store=ssd,
        repo_roots=(repo,),
    )
    previous = store.initialize_empty()
    public = {
        "query_replica_descriptor_digest": _digest("f"),
        "query_replica_generation_id": _digest("d"),
        "query_replica_id": _digest("1"),
        "query_replica_path_identity_digest": _digest("2"),
    }
    candidate = route_record_from_mapping({
        "schema_version": "reddog_holoindex_query_route.v1",
        "status": "CURRENT", "revision": 1,
        "activation_id": _digest("a"),
        "previous_route_digest": previous.digest,
        "activated_at": "2026-08-23T00:00:00Z",
        "authority_repo_root": str(repo), "replica_root": str(replica),
        "canonical": {
            "repo_head_sha": "b" * 40,
            "repo_root_digest": _digest("c"),
            "generation_id": _digest("d"), "receipt_digest": _digest("e"),
        },
        "replica": public,
    })
    with store.transition(
        candidate, expected_revision=0, expected_route_digest=previous.digest,
    ) as transition:
        transition.commit()
    return route_path, repo, ssd, replica, public


@pytest.mark.parametrize("value", [None, "", "relative/replica"])
def test_resolver_rejects_missing_or_nonabsolute_root_before_proof(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, value: str | None,
) -> None:
    proof = Mock(side_effect=AssertionError("unconfigured route must not be proved"))
    monkeypatch.setattr(route_module, "prove_existing_isolated_store", proof)
    environment = {}
    if value is not None:
        environment[route_module.QUERY_REPLICA_ROOT_ENV] = value

    with pytest.raises(ValueError, match=route_module.QUERY_REPLICA_REQUIRED_ERROR):
        route_module.resolve_query_replica_owner_route(
            canonical_repo_root=tmp_path / "repo",
            canonical_ssd_path=tmp_path / "ssd",
            environment=environment,
        )

    proof.assert_not_called()


@pytest.mark.parametrize("environment", [[], "x", object()])
def test_resolver_rejects_hostile_environment_container_with_stable_error(
    tmp_path: Path, environment: object,
) -> None:
    with pytest.raises(ValueError) as raised:
        route_module.resolve_query_replica_owner_route(
            canonical_repo_root=tmp_path / "repo",
            canonical_ssd_path=tmp_path / "ssd",
            environment=environment,
        )
    assert str(raised.value) == route_module.QUERY_REPLICA_REQUIRED_ERROR
    assert raised.value.__cause__ is None


def test_resolver_never_invokes_hostile_environment_accessor(tmp_path: Path) -> None:
    class HostileEnvironment(dict):
        def get(self, *_args, **_kwargs):
            raise RuntimeError("PRIVATE_SENTINEL:/secret/route")

    with pytest.raises(ValueError) as raised:
        route_module.resolve_query_replica_owner_route(
            canonical_repo_root=tmp_path / "repo",
            canonical_ssd_path=tmp_path / "ssd",
            environment=HostileEnvironment(),
        )
    assert str(raised.value) == route_module.QUERY_REPLICA_REQUIRED_ERROR
    assert "PRIVATE_SENTINEL" not in str(raised.value)
    assert raised.value.__cause__ is None


def test_resolver_never_compares_hostile_environment_key(tmp_path: Path) -> None:
    class HostileKey:
        def __hash__(self):
            return hash(route_module.QUERY_REPLICA_ROOT_ENV)

        def __eq__(self, _other):
            raise RuntimeError("PRIVATE_KEY_SENTINEL")

    environment = {HostileKey(): "x"}
    with pytest.raises(ValueError) as raised:
        route_module.resolve_query_replica_owner_route(
            canonical_repo_root=tmp_path / "repo",
            canonical_ssd_path=tmp_path / "ssd",
            environment=environment,
        )
    assert str(raised.value) == route_module.QUERY_REPLICA_REQUIRED_ERROR
    assert "PRIVATE_KEY_SENTINEL" not in str(raised.value)
    assert raised.value.__cause__ is None


def test_resolver_proves_existing_disjoint_root_and_builds_exact_route(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    replica, repo, ssd = (
        tmp_path / "replica", tmp_path / "repo", tmp_path / "ssd"
    )
    proof_capability, route = object(), object()
    prove = Mock(return_value=proof_capability)
    build = Mock(return_value=route)
    monkeypatch.setattr(route_module, "prove_existing_isolated_store", prove)
    monkeypatch.setattr(route_module, "build_query_replica_owner_route", build)

    observed = route_module.resolve_query_replica_owner_route(
        canonical_repo_root=repo,
        canonical_ssd_path=ssd,
        environment={route_module.QUERY_REPLICA_ROOT_ENV: str(replica)},
    )

    assert observed is route
    prove.assert_called_once_with(
        replica, canonical_store=ssd, repo_roots=(repo,),
    )
    build.assert_called_once_with(
        canonical_repo_root=repo,
        canonical_ssd_path=ssd,
        replica_root_proof=proof_capability,
    )


def test_resolver_accepts_identity_equal_process_environment_for_maintenance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    replica, repo, ssd = (
        tmp_path / "replica", tmp_path / "repo", tmp_path / "ssd"
    )
    proof_capability, route = object(), object()
    prove = Mock(return_value=proof_capability)
    build = Mock(return_value=route)
    monkeypatch.setattr(route_module, "prove_existing_isolated_store", prove)
    monkeypatch.setattr(route_module, "build_query_replica_owner_route", build)
    monkeypatch.setenv(route_module.QUERY_REPLICA_ROOT_ENV, str(replica))
    monkeypatch.delenv(route_module.QUERY_REPLICA_ROUTE_FILE_ENV, raising=False)

    observed = route_module.resolve_query_replica_owner_route(
        canonical_repo_root=repo, canonical_ssd_path=ssd, environment=os.environ,
    )

    assert observed is route
    prove.assert_called_once_with(replica, canonical_store=ssd, repo_roots=(repo,))


def test_resolver_reduces_store_or_descriptor_failure_to_stable_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        route_module,
        "prove_existing_isolated_store",
        Mock(side_effect=AcceptanceGuardError("STORE_PROOF_UNAVAILABLE")),
    )

    with pytest.raises(ValueError) as raised:
        route_module.resolve_query_replica_owner_route(
            canonical_repo_root=tmp_path / "repo",
            canonical_ssd_path=tmp_path / "ssd",
            environment={
                route_module.QUERY_REPLICA_ROOT_ENV: str(tmp_path / "replica")
            },
        )

    assert str(raised.value) == route_module.QUERY_REPLICA_REQUIRED_ERROR
    assert raised.value.__cause__ is None


def test_resolver_rejects_ambiguous_root_and_route_file_before_access(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    prove = Mock(side_effect=AssertionError("ambiguous route must not be proved"))
    store = Mock(side_effect=AssertionError("ambiguous route must not be read"))
    monkeypatch.setattr(route_module, "prove_existing_isolated_store", prove)
    monkeypatch.setattr(route_module, "QueryRouteStore", store)
    with pytest.raises(ValueError, match=route_module.QUERY_REPLICA_REQUIRED_ERROR):
        route_module.resolve_query_replica_owner_route(
            canonical_repo_root=tmp_path / "repo",
            canonical_ssd_path=tmp_path / "ssd",
            environment={
                route_module.QUERY_REPLICA_ROOT_ENV: str(tmp_path / "replica"),
                route_module.QUERY_REPLICA_ROUTE_FILE_ENV: str(tmp_path / "route.json"),
            },
        )
    prove.assert_not_called()
    store.assert_not_called()


@pytest.mark.parametrize("value", ["relative/route.json", " route.json"])
def test_resolver_rejects_noncanonical_route_file_before_store_access(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, value: str,
) -> None:
    store = Mock(side_effect=AssertionError("invalid route must not be read"))
    monkeypatch.setattr(route_module, "QueryRouteStore", store)
    with pytest.raises(ValueError, match=route_module.QUERY_REPLICA_REQUIRED_ERROR):
        route_module.resolve_query_replica_owner_route(
            canonical_repo_root=tmp_path / "repo",
            canonical_ssd_path=tmp_path / "ssd",
            environment={route_module.QUERY_REPLICA_ROUTE_FILE_ENV: value},
        )
    store.assert_not_called()


def test_resolver_never_creates_missing_route_parent(tmp_path: Path) -> None:
    repo, ssd = tmp_path / "repo", tmp_path / "ssd"
    repo.mkdir()
    ssd.mkdir()
    missing_parent = tmp_path / "unexpected" / "nested"
    route_path = missing_parent / "route.json"

    with pytest.raises(ValueError) as raised:
        route_module.resolve_query_replica_owner_route(
            canonical_repo_root=repo, canonical_ssd_path=ssd,
            environment={
                route_module.QUERY_REPLICA_ROUTE_FILE_ENV: str(route_path),
            },
        )

    assert str(raised.value) == route_module.QUERY_REPLICA_REQUIRED_ERROR
    assert not missing_parent.exists()


def test_resolver_constructs_bounded_noncreating_route_reader(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, ssd, runtime = tmp_path / "repo", tmp_path / "ssd", tmp_path / "runtime"
    route_path = runtime / "route.json"
    store_instance = Mock()
    store_instance.load_readonly.side_effect = route_module.QueryRouteStoreError(
        "QUERY_ROUTE_NOT_INITIALIZED"
    )
    store_factory = Mock(return_value=store_instance)
    monkeypatch.setattr(route_module, "QueryRouteStore", store_factory)

    with pytest.raises(ValueError, match=route_module.QUERY_REPLICA_REQUIRED_ERROR):
        route_module.resolve_query_replica_owner_route(
            canonical_repo_root=repo, canonical_ssd_path=ssd,
            environment={route_module.QUERY_REPLICA_ROUTE_FILE_ENV: str(route_path)},
        )

    store_factory.assert_called_once_with(
        route_path, runtime_root=runtime, canonical_store=ssd,
        repo_roots=(repo,), lock_timeout_seconds=15.0,
        create_runtime_root=False,
    )
    store_instance.load_readonly.assert_called_once_with()


def test_resolver_prepared_route_fails_without_route_or_journal_mutation(
    tmp_path: Path,
) -> None:
    route_path, repo, ssd, _replica, _public = _install_route_file(tmp_path)
    journal_path = route_path.with_name(route_path.name + ".journal")
    prepared = journal_path.read_text(encoding="ascii").replace(
        '"COMMITTED"', '"PREPARED"'
    )
    atomic_replace_runtime_text(journal_path, prepared)
    before = (
        route_path.read_bytes(), journal_path.read_bytes(),
        _file_state(route_path), _file_state(journal_path),
    )

    with pytest.raises(ValueError, match=route_module.QUERY_REPLICA_REQUIRED_ERROR):
        route_module.resolve_query_replica_owner_route(
            canonical_repo_root=repo, canonical_ssd_path=ssd,
            environment={route_module.QUERY_REPLICA_ROUTE_FILE_ENV: str(route_path)},
        )

    after = (
        route_path.read_bytes(), journal_path.read_bytes(),
        _file_state(route_path), _file_state(journal_path),
    )
    assert after == before


def test_resolver_rejects_current_route_without_commit_journal_and_preserves_it(
    tmp_path: Path,
) -> None:
    route_path, repo, ssd, _replica, _public = _install_route_file(tmp_path)
    journal_path = route_path.with_name(route_path.name + ".journal")
    journal_path.unlink()
    before = (route_path.read_bytes(), _file_state(route_path))

    with pytest.raises(ValueError) as raised:
        route_module.resolve_query_replica_owner_route(
            canonical_repo_root=repo, canonical_ssd_path=ssd,
            environment={route_module.QUERY_REPLICA_ROUTE_FILE_ENV: str(route_path)},
        )

    assert str(raised.value) == route_module.QUERY_REPLICA_REQUIRED_ERROR
    assert raised.value.__cause__ is None
    assert (route_path.read_bytes(), _file_state(route_path)) == before
    assert not journal_path.exists()


def test_resolver_loads_route_file_and_binds_exact_descriptor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    route_path, repo, ssd, replica, public = _install_route_file(tmp_path)
    proof = SimpleNamespace(path=replica)
    binding = SimpleNamespace(
        canonical_repo_head_sha="b" * 40,
        canonical_repo_root_digest=_digest("c"),
        generation_id=_digest("d"),
        canonical_receipt_digest=_digest("e"),
        public_binding=public,
    )
    expected = SimpleNamespace(replica_root_proof=proof, binding=binding)
    prove = Mock(return_value=proof)
    build = Mock(return_value=expected)
    monkeypatch.setattr(route_module, "prove_existing_isolated_store", prove)
    monkeypatch.setattr(route_module, "build_query_replica_owner_route", build)

    observed = route_module.resolve_query_replica_owner_route(
        canonical_repo_root=repo, canonical_ssd_path=ssd,
        environment={route_module.QUERY_REPLICA_ROUTE_FILE_ENV: str(route_path)},
    )

    assert observed is expected
    prove.assert_called_once_with(replica, canonical_store=ssd, repo_roots=(repo,))


def test_resolver_rejects_route_record_descriptor_binding_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    route_path, repo, ssd, replica, public = _install_route_file(tmp_path)
    proof = SimpleNamespace(path=replica)
    binding = SimpleNamespace(
        canonical_repo_head_sha="b" * 40,
        canonical_repo_root_digest=_digest("c"),
        generation_id=_digest("9"),
        canonical_receipt_digest=_digest("e"),
        public_binding=public,
    )
    monkeypatch.setattr(
        route_module, "prove_existing_isolated_store", Mock(return_value=proof),
    )
    monkeypatch.setattr(
        route_module, "build_query_replica_owner_route",
        Mock(return_value=SimpleNamespace(replica_root_proof=proof, binding=binding)),
    )
    with pytest.raises(ValueError) as raised:
        route_module.resolve_query_replica_owner_route(
            canonical_repo_root=repo, canonical_ssd_path=ssd,
            environment={route_module.QUERY_REPLICA_ROUTE_FILE_ENV: str(route_path)},
        )
    assert str(raised.value) == route_module.QUERY_REPLICA_REQUIRED_ERROR
    assert raised.value.__cause__ is None
