"""Verified query-replica runtime isolated from canonical freshness authority."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from holo_index.storage_contract import storage_path_identity

from .reddog_holoindex_acceptance_guards import StoreProof
from .reddog_holoindex_query_replica_descriptor import (
    ActiveQueryReplicaBinding,
    QueryReplicaDescriptorError,
    revalidate_admitted_query_replica,
    verify_active_query_replica,
)


@dataclass
class QueryReplicaRuntime:
    """Retain and reprove one exact replica generation for backend reads."""

    canonical_ssd_path: Path
    verifier: Callable[[], ActiveQueryReplicaBinding] | None
    binding: ActiveQueryReplicaBinding | None = None
    require_snapshot_generation: bool = False

    def verify(self) -> ActiveQueryReplicaBinding | None:
        if self.verifier is None:
            return None
        observed = self.verifier()
        if self.binding is not None and observed != self.binding:
            raise QueryReplicaDescriptorError("QUERY_REPLICA_BINDING_CHANGED")
        return observed

    @property
    def query_ssd_path(self) -> Path:
        return (
            self.binding.generation_directory
            if self.binding is not None else self.canonical_ssd_path
        )

    @property
    def public_binding(self) -> Mapping[str, str]:
        return self.binding.public_binding if self.binding is not None else {}


def build_query_replica_runtime(
    *, repo_root: Path, canonical_ssd_path: Path,
    proof: StoreProof | None,
    injected: Callable[[], ActiveQueryReplicaBinding] | None,
    require_replica: bool,
) -> QueryReplicaRuntime:
    """Construct a runtime only after its initial exact descriptor proof."""

    verifier = injected
    if verifier is None and proof is not None:
        verifier = lambda: verify_active_query_replica(
            replica_root_proof=proof,
            canonical_repo_root=repo_root,
            canonical_ssd_path=canonical_ssd_path,
        )
    runtime = QueryReplicaRuntime(
        canonical_ssd_path, verifier,
        require_snapshot_generation=require_replica,
    )
    runtime.binding = runtime.verify()
    if runtime.binding is None and require_replica:
        raise ValueError("HOLOINDEX_QUERY_REPLICA_REQUIRED")
    if injected is None and proof is not None and runtime.binding is not None:
        admitted = runtime.binding
        runtime.verifier = lambda: revalidate_admitted_query_replica(
            admitted_binding=admitted,
            replica_root_proof=proof,
            canonical_repo_root=repo_root,
            canonical_ssd_path=canonical_ssd_path,
        )
        runtime.verify()
    return runtime


def prepare_query_backend(
    runtime: QueryReplicaRuntime,
    factory: Callable[[Path], Any],
) -> Any:
    """Build one backend only on the twice-verified replica generation."""

    before = runtime.verify()
    os.environ.update({
        "HOLOINDEX_QUERY_READONLY": "1", "HOLO_OFFLINE": "1",
        "HOLO_DISABLE_PIP_INSTALL": "1", "HOLO_ALLOW_PIP_INSTALL": "0",
        "ANONYMIZED_TELEMETRY": "false", "HOLO_SILENT": "1",
        "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
        "HF_DATASETS_OFFLINE": "1", "HOLO_USE_TURBOQUANT": "0",
    })
    backend = factory(runtime.query_ssd_path)
    reported = getattr(backend, "ssd_path", None)
    if reported is not None and (
        storage_path_identity(reported) == storage_path_identity(runtime.canonical_ssd_path)
        or storage_path_identity(reported) != storage_path_identity(runtime.query_ssd_path)
    ):
        raise QueryReplicaDescriptorError("QUERY_REPLICA_BACKEND_STORAGE_MISMATCH")
    snapshot_generation = getattr(backend, "query_snapshot_generation_id", "")
    if (
        before is not None
        and runtime.require_snapshot_generation
        and snapshot_generation != before.generation_id
    ):
        raise QueryReplicaDescriptorError("QUERY_REPLICA_SNAPSHOT_GENERATION_MISMATCH")
    if before != runtime.verify():
        raise QueryReplicaDescriptorError("QUERY_REPLICA_BINDING_CHANGED")
    backend.search_cache = None
    backend.strict_semantic_owner = True
    return backend


__all__ = [
    "QueryReplicaRuntime", "build_query_replica_runtime", "prepare_query_backend",
]
