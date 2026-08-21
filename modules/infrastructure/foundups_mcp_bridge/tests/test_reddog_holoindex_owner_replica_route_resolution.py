"""Fail-closed host resolution for RedDog query-replica owner routes."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest

from modules.infrastructure.foundups_mcp_bridge.src import (
    reddog_holoindex_owner_replica_route as route_module,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_acceptance_guards import (
    AcceptanceGuardError,
)


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
