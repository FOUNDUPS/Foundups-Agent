#!/usr/bin/env python3
"""Run explicit isolated RedDog HoloIndex candidate acceptance."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

def _absolute_path(value: str) -> Path:
    candidate = Path(str(value).strip()).expanduser()
    if not candidate.is_absolute():
        raise argparse.ArgumentTypeError("absolute path required")
    return candidate


def _commit_sha(value: str) -> str:
    normalized = str(value).strip().lower()
    if re.fullmatch(r"[0-9a-f]{40}", normalized) is None:
        raise argparse.ArgumentTypeError("exact 40-character commit SHA required")
    return normalized


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate one candidate using a new isolated HoloIndex store."
    )
    parser.add_argument("--candidate-root", required=True, type=_absolute_path)
    parser.add_argument("--authority-root", required=True, type=_absolute_path)
    parser.add_argument("--runtime-root", required=True, type=_absolute_path)
    parser.add_argument("--canonical-store", required=True, type=_absolute_path)
    parser.add_argument("--isolated-store", required=True, type=_absolute_path)
    parser.add_argument("--receipt-path", required=True, type=_absolute_path)
    parser.add_argument("--expected-sha", required=True, type=_commit_sha)
    parser.add_argument("--port", type=int, default=8127)
    parser.add_argument("--timeout-seconds", type=float, default=900.0)
    parser.add_argument(
        "--real",
        action="store_true",
        help="Explicitly authorize isolated model copy, rebuild, owner start, and queries.",
    )
    return parser


def _public_result(result: Any) -> dict[str, object]:
    return {
        "error": str(result.error),
        "freshness_receipt_digest": str(result.freshness_receipt_digest),
        "generation_id": str(result.generation_id),
        "receipt_published": bool(result.receipt_published),
        "status": str(result.status),
        "verdict": str(result.verdict),
    }


def _emit(payload: dict[str, object]) -> None:
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))


def _load_candidate_acceptance() -> tuple[Any, Any, Any]:
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_candidate_acceptance import (
        CandidateAcceptanceConfig,
        CandidateAcceptanceResult,
        run_candidate_acceptance,
    )

    return CandidateAcceptanceConfig, CandidateAcceptanceResult, run_candidate_acceptance


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.real is not True:
        _emit(
            {
                "error": "",
                "freshness_receipt_digest": "",
                "generation_id": "",
                "receipt_published": False,
                "status": "REAL_MODE_REQUIRED",
                "verdict": "NOT_RUN",
            }
        )
        return 2
    config_type, result_type, run_acceptance = _load_candidate_acceptance()
    config = config_type(
        candidate_root=args.candidate_root,
        authority_root=args.authority_root,
        owner_runtime_root=args.runtime_root,
        canonical_store=args.canonical_store,
        isolated_store=args.isolated_store,
        receipt_path=args.receipt_path,
        expected_sha=args.expected_sha,
        real_mode=bool(args.real),
        port=int(args.port),
        timeout_seconds=float(args.timeout_seconds),
    )
    try:
        result = run_acceptance(config)
    except Exception:  # The CLI boundary never emits untrusted exception text.
        result = result_type(
            verdict="FAIL",
            status="COMPLETED",
            error="CANDIDATE_ACCEPTANCE_FAILED",
        )
    _emit(_public_result(result))
    if result.verdict == "PASS":
        return 0
    return 2 if result.verdict == "NOT_RUN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
