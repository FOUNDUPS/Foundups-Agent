"""CI freshness gate for HoloIndex receipts.

WSP 97: freshness must be checked from evidence. This module only evaluates a
receipt against caller-supplied changed paths. It never runs git, never reindexes,
and never mutates the HoloIndex store.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

from holo_index.freshness_receipt import (
    FreshnessCheck,
    collections_for_changed_paths,
    evaluate_freshness_for_paths,
    load_freshness_receipt,
)


SCHEMA_VERSION = "holoindex_ci_freshness_gate.v1"

STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
STATUS_NOT_CONFIGURED = "NOT_CONFIGURED"
STATUS_NO_RELEVANT_CHANGES = "NO_RELEVANT_CHANGES"

EXIT_OK = 0
EXIT_STALE = 2


@dataclass(frozen=True)
class HoloIndexCIFreshnessGateResult:
    """Result emitted by the CI freshness gate."""

    schema_version: str
    status: str
    ok: bool
    configured: bool
    receipt_path: str | None
    expected_repo_head_sha: str | None
    changed_paths: list[str] = field(default_factory=list)
    required_collections: list[str] = field(default_factory=list)
    stale_collections: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    no_reindex_performed: bool = True
    no_runtime_reindex_performed: bool = True
    no_holoindex_mutation_performed: bool = True

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))


def _normalize_paths(paths: Iterable[str | Path]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for path in paths:
        text = str(path).replace("\\", "/").strip()
        while text.startswith("./"):
            text = text[2:]
        if not text or text.startswith("#"):
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
    return out


def _read_changed_paths_file(path: str | Path) -> list[str]:
    return _normalize_paths(Path(path).read_text(encoding="utf-8").splitlines())


def _missing_receipt_result(
    *,
    receipt_path: str | None,
    changed_paths: list[str],
    expected_repo_head_sha: str | None,
    reason: str,
    allow_not_configured: bool,
) -> HoloIndexCIFreshnessGateResult:
    required = collections_for_changed_paths(changed_paths)
    if allow_not_configured:
        return HoloIndexCIFreshnessGateResult(
            schema_version=SCHEMA_VERSION,
            status=STATUS_NOT_CONFIGURED,
            ok=True,
            configured=False,
            receipt_path=receipt_path,
            expected_repo_head_sha=expected_repo_head_sha,
            changed_paths=changed_paths,
            required_collections=required,
            stale_collections=[],
            reasons=[reason],
        )
    return HoloIndexCIFreshnessGateResult(
        schema_version=SCHEMA_VERSION,
        status=STATUS_FAIL,
        ok=False,
        configured=False,
        receipt_path=receipt_path,
        expected_repo_head_sha=expected_repo_head_sha,
        changed_paths=changed_paths,
        required_collections=required,
        stale_collections=required,
        reasons=[reason],
    )


def _from_freshness_check(
    *,
    check: FreshnessCheck,
    receipt_path: str,
    changed_paths: list[str],
    expected_repo_head_sha: str | None,
) -> HoloIndexCIFreshnessGateResult:
    status = STATUS_PASS if check.ok else STATUS_FAIL
    if check.ok and not check.required_collections:
        status = STATUS_NO_RELEVANT_CHANGES
    return HoloIndexCIFreshnessGateResult(
        schema_version=SCHEMA_VERSION,
        status=status,
        ok=check.ok,
        configured=True,
        receipt_path=receipt_path,
        expected_repo_head_sha=expected_repo_head_sha,
        changed_paths=changed_paths,
        required_collections=check.required_collections,
        stale_collections=check.stale_collections,
        reasons=check.reasons,
    )


def check_ci_freshness(
    *,
    receipt_path: str | Path | None,
    changed_paths: Iterable[str | Path],
    expected_repo_head_sha: str | None = None,
    allow_not_configured: bool = False,
) -> HoloIndexCIFreshnessGateResult:
    """Check whether a HoloIndex receipt covers changed paths for CI.

    The caller supplies the changed paths and expected SHA. This function is
    intentionally not a git wrapper; CI or WRE owns diff discovery.
    """

    normalized_paths = _normalize_paths(changed_paths)
    required = collections_for_changed_paths(normalized_paths)
    if not required:
        return HoloIndexCIFreshnessGateResult(
            schema_version=SCHEMA_VERSION,
            status=STATUS_NO_RELEVANT_CHANGES,
            ok=True,
            configured=bool(receipt_path),
            receipt_path=str(receipt_path) if receipt_path else None,
            expected_repo_head_sha=expected_repo_head_sha,
            changed_paths=normalized_paths,
            required_collections=[],
            stale_collections=[],
            reasons=[],
        )
    if not receipt_path:
        return _missing_receipt_result(
            receipt_path=None,
            changed_paths=normalized_paths,
            expected_repo_head_sha=expected_repo_head_sha,
            reason="missing_freshness_receipt_path",
            allow_not_configured=allow_not_configured,
        )

    receipt_file = Path(receipt_path)
    if not receipt_file.exists():
        return _missing_receipt_result(
            receipt_path=str(receipt_file),
            changed_paths=normalized_paths,
            expected_repo_head_sha=expected_repo_head_sha,
            reason="missing_freshness_receipt_file",
            allow_not_configured=allow_not_configured,
        )

    try:
        receipt = load_freshness_receipt(receipt_file)
    except Exception:
        required = collections_for_changed_paths(normalized_paths)
        return HoloIndexCIFreshnessGateResult(
            schema_version=SCHEMA_VERSION,
            status=STATUS_FAIL,
            ok=False,
            configured=True,
            receipt_path=str(receipt_file),
            expected_repo_head_sha=expected_repo_head_sha,
            changed_paths=normalized_paths,
            required_collections=required,
            stale_collections=required,
            reasons=["malformed_freshness_receipt"],
        )

    check = evaluate_freshness_for_paths(
        receipt,
        normalized_paths,
        expected_repo_head_sha=expected_repo_head_sha,
    )
    return _from_freshness_check(
        check=check,
        receipt_path=str(receipt_file),
        changed_paths=normalized_paths,
        expected_repo_head_sha=expected_repo_head_sha,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check HoloIndex freshness receipt for CI.")
    parser.add_argument("--receipt", help="Path to holoindex_freshness_receipt.json.")
    parser.add_argument(
        "--changed-path",
        action="append",
        default=[],
        help="Changed repository path. May be repeated.",
    )
    parser.add_argument(
        "--changed-paths-file",
        help="File containing one changed repository path per line.",
    )
    parser.add_argument("--expected-repo-head-sha", help="Expected repository HEAD SHA.")
    parser.add_argument(
        "--allow-not-configured",
        action="store_true",
        help="Return ok=true with NOT_CONFIGURED when the receipt is absent.",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    changed_paths = list(args.changed_path or [])
    if args.changed_paths_file:
        changed_paths.extend(_read_changed_paths_file(args.changed_paths_file))

    result = check_ci_freshness(
        receipt_path=args.receipt,
        changed_paths=changed_paths,
        expected_repo_head_sha=args.expected_repo_head_sha,
        allow_not_configured=args.allow_not_configured,
    )
    if args.pretty:
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    else:
        print(result.to_json())
    return EXIT_OK if result.ok else EXIT_STALE


__all__ = [
    "EXIT_OK",
    "EXIT_STALE",
    "HoloIndexCIFreshnessGateResult",
    "SCHEMA_VERSION",
    "STATUS_FAIL",
    "STATUS_NOT_CONFIGURED",
    "STATUS_NO_RELEVANT_CHANGES",
    "STATUS_PASS",
    "check_ci_freshness",
    "main",
]


if __name__ == "__main__":
    raise SystemExit(main())
