"""Sealed owner-routing capability for one verified active query replica."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .holo_query_binding import parse_exact_binding
from .holo_query_owner_health import BINDING_MISMATCH_ERROR
from .holo_query_replica_binding import (
    parse_replica_binding,
    replica_binding_is_complete,
)
from .reddog_holoindex_acceptance_guards import (
    AcceptanceGuardError,
    StoreProof,
    _normalized,
    prove_existing_isolated_store,
)
from .reddog_holoindex_query_replica_descriptor import (
    ActiveQueryReplicaBinding,
    QueryReplicaDescriptorError,
    revalidate_admitted_query_replica,
    verify_active_query_replica,
)
from .reddog_holoindex_query_route_contract import QueryRouteRecord
from .reddog_holoindex_query_route_io import QueryRouteStoreError
from .reddog_holoindex_query_route_store import QueryRouteStore


QUERY_REPLICA_REQUIRED_ERROR = "HOLOINDEX_QUERY_REPLICA_REQUIRED"
QUERY_REPLICA_ROOT_ENV = "REDDOG_HOLOINDEX_QUERY_REPLICA_ROOT"
QUERY_REPLICA_ROUTE_FILE_ENV = "REDDOG_HOLOINDEX_QUERY_ROUTE_FILE"
_QUERY_ROUTE_RESOLUTION_LOCK_TIMEOUT_SECONDS = 15.0

@dataclass(frozen=True)
class QueryReplicaOwnerRoute:
    """Exact canonical-authority/query-store split retained by the host."""

    canonical_repo_root: Path
    canonical_ssd_path: Path
    replica_root_proof: StoreProof
    binding: ActiveQueryReplicaBinding

    @property
    def expected_replica_binding(self) -> tuple[str, str, str, str]:
        return self.binding.reuse_binding

    def revalidate(self) -> ActiveQueryReplicaBinding:
        observed = revalidate_admitted_query_replica(
            admitted_binding=self.binding,
            replica_root_proof=self.replica_root_proof,
            canonical_repo_root=self.canonical_repo_root,
            canonical_ssd_path=self.canonical_ssd_path,
        )
        if observed != self.binding:
            raise ValueError("QUERY_REPLICA_BINDING_CHANGED")
        return observed


def build_query_replica_owner_route(
    *, canonical_repo_root: Path | str, canonical_ssd_path: Path | str,
    replica_root_proof: StoreProof,
) -> QueryReplicaOwnerRoute:
    """Build one route only after exact active-descriptor verification."""

    repo_root = Path(canonical_repo_root).resolve(strict=False)
    canonical = Path(canonical_ssd_path).resolve(strict=False)
    binding = verify_active_query_replica(
        replica_root_proof=replica_root_proof,
        canonical_repo_root=repo_root,
        canonical_ssd_path=canonical,
    )
    return QueryReplicaOwnerRoute(repo_root, canonical, replica_root_proof, binding)


def _route_record_matches_owner(
    record: QueryRouteRecord, route: QueryReplicaOwnerRoute,
) -> bool:
    binding = route.binding
    canonical = {
        "repo_head_sha": binding.canonical_repo_head_sha,
        "repo_root_digest": binding.canonical_repo_root_digest,
        "generation_id": binding.generation_id,
        "receipt_digest": binding.canonical_receipt_digest,
    }
    return (
        record.status == "CURRENT"
        and record.canonical == canonical
        and record.replica == binding.public_binding
        and record.replica_root == str(route.replica_root_proof.path)
    )


def _resolve_route_file(
    raw_route_file: str, *, canonical_repo_root: Path | str,
    canonical_ssd_path: Path | str,
) -> QueryReplicaOwnerRoute:
    if raw_route_file != raw_route_file.strip():
        raise ValueError(QUERY_REPLICA_REQUIRED_ERROR)
    route_path = Path(raw_route_file)
    if not route_path.is_absolute() or route_path.parent == route_path:
        raise ValueError(QUERY_REPLICA_REQUIRED_ERROR)
    repo_root = _normalized(canonical_repo_root)
    store = QueryRouteStore(
        route_path, runtime_root=route_path.parent,
        canonical_store=canonical_ssd_path, repo_roots=(repo_root,),
        lock_timeout_seconds=_QUERY_ROUTE_RESOLUTION_LOCK_TIMEOUT_SECONDS,
        create_runtime_root=False,
    )
    selected = store.load_readonly().record
    if selected.authority_repo_root != str(repo_root):
        raise ValueError(QUERY_REPLICA_REQUIRED_ERROR)
    proof = prove_existing_isolated_store(
        Path(selected.replica_root),
        canonical_store=canonical_ssd_path, repo_roots=(repo_root,),
    )
    route = build_query_replica_owner_route(
        canonical_repo_root=repo_root, canonical_ssd_path=canonical_ssd_path,
        replica_root_proof=proof,
    )
    if not _route_record_matches_owner(selected, route):
        raise ValueError(QUERY_REPLICA_REQUIRED_ERROR)
    return route


def _resolve_legacy_root(
    raw_root: str, *, canonical_repo_root: Path | str,
    canonical_ssd_path: Path | str,
) -> QueryReplicaOwnerRoute:
    replica_root = Path(raw_root.strip())
    if not replica_root.is_absolute():
        raise ValueError(QUERY_REPLICA_REQUIRED_ERROR)
    proof = prove_existing_isolated_store(
        replica_root,
        canonical_store=canonical_ssd_path, repo_roots=(canonical_repo_root,),
    )
    return build_query_replica_owner_route(
        canonical_repo_root=canonical_repo_root,
        canonical_ssd_path=canonical_ssd_path,
        replica_root_proof=proof,
    )


def resolve_query_replica_owner_route(
    *, canonical_repo_root: Path | str, canonical_ssd_path: Path | str,
    environment: Mapping[str, str] | None = None,
) -> QueryReplicaOwnerRoute:
    """Resolve one explicitly configured, existing, exact-generation route."""

    if environment is None or environment is os.environ:
        env = os.environ
    else:
        if type(environment) is not dict or any(
            type(key) is not str or type(value) is not str
            for key, value in environment.items()
        ):
            raise ValueError(QUERY_REPLICA_REQUIRED_ERROR)
        env = dict(environment)
    raw_root = env.get(QUERY_REPLICA_ROOT_ENV)
    raw_route_file = env.get(QUERY_REPLICA_ROUTE_FILE_ENV)
    root_configured = type(raw_root) is str and bool(raw_root.strip())
    route_file_configured = (
        type(raw_route_file) is str and bool(raw_route_file.strip())
    )
    if root_configured == route_file_configured:
        raise ValueError(QUERY_REPLICA_REQUIRED_ERROR)
    if (
        raw_root is not None and type(raw_root) is not str
        or raw_route_file is not None and type(raw_route_file) is not str
    ):
        raise ValueError(QUERY_REPLICA_REQUIRED_ERROR)
    try:
        if route_file_configured:
            return _resolve_route_file(
                raw_route_file, canonical_repo_root=canonical_repo_root,
                canonical_ssd_path=canonical_ssd_path,
            )
        return _resolve_legacy_root(
            raw_root, canonical_repo_root=canonical_repo_root,
            canonical_ssd_path=canonical_ssd_path,
        )
    except (
        AcceptanceGuardError, QueryReplicaDescriptorError,
        QueryRouteStoreError, OSError, TypeError, ValueError,
    ):
        raise ValueError(QUERY_REPLICA_REQUIRED_ERROR) from None


def owner_supervisor_configuration(
    *, repo_root: Path | str, runtime_root: Path | str | None,
    canonical_ssd_path: Path | str,
    route: QueryReplicaOwnerRoute | None,
) -> tuple[dict[str, object], tuple[str, str, str, str]]:
    """Build explicit owner argv/capability inputs without ambient routing."""

    arguments: dict[str, object] = {
        "repo_root": repo_root, "ssd_path": canonical_ssd_path,
    }
    binding = ("", "", "", "")
    if route is not None:
        parsed = parse_replica_binding(route.expected_replica_binding)
        if parsed is None:
            raise ValueError(QUERY_REPLICA_REQUIRED_ERROR)
        arguments.update(
            canonical_ssd_path=canonical_ssd_path,
            query_replica_root=route.replica_root_proof.path,
            replica_capability_verifier=route.revalidate,
        )
        binding = parsed
    if runtime_root is not None:
        arguments["runtime_root"] = runtime_root
    return arguments, binding


def owner_start_binding_kwargs(
    binding: tuple[str, str, str, str],
    replica_binding: tuple[str, str, str, str],
) -> dict[str, object]:
    canonical = parse_exact_binding(binding, allow_empty_fields=True)
    if canonical is None:
        raise ValueError(BINDING_MISMATCH_ERROR)
    parsed = parse_replica_binding(replica_binding)
    if parsed is None:
        raise ValueError(QUERY_REPLICA_REQUIRED_ERROR)
    arguments: dict[str, object] = {
        "expected_repo_head_sha": canonical[0],
        "expected_repo_root_digest": canonical[1],
        "expected_generation_id": canonical[2],
        "expected_receipt_digest": canonical[3],
    }
    arguments["expected_replica_binding"] = parsed
    return arguments


def replica_route_is_current(route: QueryReplicaOwnerRoute | None) -> bool:
    if route is None:
        return False
    try:
        route.revalidate()
        return replica_binding_is_complete(route.expected_replica_binding)
    except Exception:
        return False


__all__ = [
    "QueryReplicaOwnerRoute", "build_query_replica_owner_route",
    "owner_start_binding_kwargs", "owner_supervisor_configuration",
    "QUERY_REPLICA_REQUIRED_ERROR", "QUERY_REPLICA_ROOT_ENV",
    "QUERY_REPLICA_ROUTE_FILE_ENV",
    "replica_binding_is_complete", "replica_route_is_current",
    "resolve_query_replica_owner_route",
]
