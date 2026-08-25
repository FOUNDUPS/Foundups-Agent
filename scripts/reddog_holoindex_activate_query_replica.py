#!/usr/bin/env python3
"""Default-inert CLI for governed RedDog HoloIndex replica activation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_replica_activation import (  # noqa: E402
    activate_query_replica,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_replica_activation_contract import (  # noqa: E402
    QueryReplicaActivationConfig,
    QueryReplicaActivationResult,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Activate one exact immutable RedDog HoloIndex query replica."
    )
    parser.add_argument("--real", action="store_true")
    parser.add_argument("--repo-root")
    parser.add_argument("--owner-runtime-root")
    parser.add_argument("--canonical-store")
    parser.add_argument("--replica-root")
    parser.add_argument("--route-file")
    parser.add_argument("--route-runtime-root")
    parser.add_argument("--receipt-file")
    parser.add_argument("--expected-sha")
    parser.add_argument("--timeout-seconds", type=float, default=1800.0)
    return parser


def _required(arguments: argparse.Namespace) -> tuple[str, ...]:
    names = (
        "repo_root",
        "owner_runtime_root",
        "canonical_store",
        "replica_root",
        "route_file",
        "route_runtime_root",
        "receipt_file",
        "expected_sha",
    )
    return tuple(name for name in names if not getattr(arguments, name, None))


def _config(arguments: argparse.Namespace) -> QueryReplicaActivationConfig:
    return QueryReplicaActivationConfig(
        repo_root=Path(arguments.repo_root),
        owner_runtime_root=Path(arguments.owner_runtime_root),
        canonical_store=Path(arguments.canonical_store),
        replica_root=Path(arguments.replica_root),
        route_path=Path(arguments.route_file),
        route_runtime_root=Path(arguments.route_runtime_root),
        receipt_path=Path(arguments.receipt_file),
        expected_repo_head_sha=arguments.expected_sha,
        timeout_seconds=arguments.timeout_seconds,
        real=True,
    )


def _emit(result: QueryReplicaActivationResult) -> int:
    print(json.dumps(result.to_dict(), sort_keys=True, separators=(",", ":")))
    return 0 if result.ok or result.verdict == "NOT_REQUESTED" else 2


def main(argv: Sequence[str] | None = None) -> int:
    try:
        arguments = _parser().parse_args(argv)
    except SystemExit as exc:
        return int(exc.code)
    if not arguments.real:
        return _emit(QueryReplicaActivationResult(False, "NOT_REQUESTED"))
    if _required(arguments):
        return _emit(
            QueryReplicaActivationResult(False, "FAILED", "ACTIVATION_ARGUMENTS_INVALID")
        )
    try:
        return _emit(activate_query_replica(_config(arguments)))
    except Exception:
        return _emit(
            QueryReplicaActivationResult(False, "FAILED", "QUERY_REPLICA_ACTIVATION_FAILED")
        )


if __name__ == "__main__":
    raise SystemExit(main())
