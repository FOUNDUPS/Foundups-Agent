"""Secret-free contracts for one governed query-replica activation."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import MappingProxyType

from .reddog_holoindex_owner_replica_route import QueryReplicaOwnerRoute
from .reddog_holoindex_query_route_contract import (
    ROUTE_SCHEMA_VERSION,
    QueryRouteRecord,
    QueryRouteStateProof,
    validate_route_record,
)


ACTIVATION_SCHEMA_VERSION = "reddog_holoindex_query_replica_activation.v1"
ACTIVATION_RECEIPT_MAX_BYTES = 16 * 1024
ACTIVATION_QUERY = "RedDog governed HoloIndex exact-main activation canary"
_HEAD = re.compile(r"[0-9a-f]{40}\Z")
_ERROR = re.compile(r"[A-Z][A-Z0-9_]{2,127}\Z")


class QueryReplicaActivationError(RuntimeError):
    """Stable fail-closed activation error."""


def fail_activation(code: str) -> None:
    raise QueryReplicaActivationError(code)


@dataclass(frozen=True)
class QueryReplicaActivationConfig:
    repo_root: Path
    owner_runtime_root: Path
    canonical_store: Path
    replica_root: Path
    route_path: Path
    route_runtime_root: Path
    receipt_path: Path
    expected_repo_head_sha: str
    timeout_seconds: float = 1800.0
    real: bool = False


@dataclass(frozen=True)
class QueryReplicaActivationResult:
    ok: bool
    verdict: str
    error: str = ""
    receipt_digest: str = ""
    route_committed: bool = False
    post_query_replica_unchanged: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "verdict": self.verdict,
            "error": self.error,
            "receipt_digest": self.receipt_digest,
            "route_committed": self.route_committed,
            "post_query_replica_unchanged": self.post_query_replica_unchanged,
        }


def _absolute(path: object, code: str) -> Path:
    if not isinstance(path, Path) or not path.is_absolute():
        fail_activation(code)
    return Path(os.path.abspath(path))


def validate_activation_config(
    config: QueryReplicaActivationConfig,
) -> QueryReplicaActivationConfig:
    if type(config) is not QueryReplicaActivationConfig:
        fail_activation("ACTIVATION_CONFIG_INVALID")
    paths = (
        config.repo_root,
        config.owner_runtime_root,
        config.canonical_store,
        config.replica_root,
        config.route_path,
        config.route_runtime_root,
        config.receipt_path,
    )
    normalized = tuple(_absolute(path, "ACTIVATION_PATH_INVALID") for path in paths)
    if _HEAD.fullmatch(config.expected_repo_head_sha) is None:
        fail_activation("ACTIVATION_HEAD_INVALID")
    if (
        isinstance(config.timeout_seconds, bool)
        or not math.isfinite(config.timeout_seconds)
        or not 1.0 <= config.timeout_seconds <= 7200.0
    ):
        fail_activation("ACTIVATION_TIMEOUT_INVALID")
    if type(config.real) is not bool:
        fail_activation("ACTIVATION_REAL_MODE_INVALID")
    if normalized[4].parent != normalized[5] or normalized[6].parent != normalized[5]:
        fail_activation("ACTIVATION_RUNTIME_PATH_INVALID")
    reserved = {
        normalized[4],
        normalized[4].with_name(normalized[4].name + ".journal"),
        normalized[4].with_name(normalized[4].name + ".activation.lock"),
        normalized[5] / ".private-json-orphans",
    }
    if normalized[4] == normalized[5] / ".private-json-orphans" or normalized[6] in reserved:
        fail_activation("ACTIVATION_RUNTIME_PATH_COLLISION")
    return QueryReplicaActivationConfig(
        *normalized,
        config.expected_repo_head_sha,
        config.timeout_seconds,
        config.real,
    )


def activation_id(
    previous: QueryRouteStateProof,
    route: QueryReplicaOwnerRoute,
) -> str:
    payload = {
        "previous_route_digest": previous.digest,
        "revision": previous.record.revision + 1,
        "canonical": {
            "repo_head_sha": route.binding.canonical_repo_head_sha,
            "repo_root_digest": route.binding.canonical_repo_root_digest,
            "generation_id": route.binding.generation_id,
            "receipt_digest": route.binding.canonical_receipt_digest,
        },
        "replica": dict(route.binding.public_binding),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("ascii")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def build_candidate_route_record(
    previous: QueryRouteStateProof,
    route: QueryReplicaOwnerRoute,
    *,
    now: datetime | None = None,
) -> QueryRouteRecord:
    activated_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    record = QueryRouteRecord(
        schema_version=ROUTE_SCHEMA_VERSION,
        status="CURRENT",
        revision=previous.record.revision + 1,
        activation_id=activation_id(previous, route),
        previous_route_digest=previous.digest,
        activated_at=activated_at.isoformat().replace("+00:00", "Z"),
        authority_repo_root=str(route.canonical_repo_root),
        replica_root=str(route.replica_root_proof.path),
        canonical=MappingProxyType(
            {
                "repo_head_sha": route.binding.canonical_repo_head_sha,
                "repo_root_digest": route.binding.canonical_repo_root_digest,
                "generation_id": route.binding.generation_id,
                "receipt_digest": route.binding.canonical_receipt_digest,
            }
        ),
        replica=MappingProxyType(dict(route.binding.public_binding)),
    )
    return validate_route_record(record)


def stable_activation_error(error: BaseException) -> str:
    value = str(error)
    return value if _ERROR.fullmatch(value) else "QUERY_REPLICA_ACTIVATION_FAILED"


__all__ = [
    "ACTIVATION_QUERY",
    "ACTIVATION_RECEIPT_MAX_BYTES",
    "ACTIVATION_SCHEMA_VERSION",
    "QueryReplicaActivationConfig",
    "QueryReplicaActivationError",
    "QueryReplicaActivationResult",
    "activation_id",
    "build_candidate_route_record",
    "fail_activation",
    "stable_activation_error",
    "validate_activation_config",
]
