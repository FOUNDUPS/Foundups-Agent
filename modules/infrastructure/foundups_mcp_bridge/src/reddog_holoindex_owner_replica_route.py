"""Sealed owner-routing capability for one verified active query replica."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .holo_query_binding import parse_exact_binding
from .holo_query_owner_health import BINDING_MISMATCH_ERROR
from .holo_query_replica_binding import (
    parse_replica_binding,
    replica_binding_is_complete,
)
from .reddog_holoindex_acceptance_guards import StoreProof
from .reddog_holoindex_query_replica_descriptor import (
    ActiveQueryReplicaBinding,
    verify_active_query_replica,
)


QUERY_REPLICA_REQUIRED_ERROR = "HOLOINDEX_QUERY_REPLICA_REQUIRED"

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
        observed = verify_active_query_replica(
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
    "QUERY_REPLICA_REQUIRED_ERROR", "replica_binding_is_complete",
    "replica_route_is_current",
]
