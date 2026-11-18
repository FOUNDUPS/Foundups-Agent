"""CI main-branch HoloIndex freshness gate.

This wrapper discovers changed paths for CI and delegates freshness evaluation
to ``holo_index.ci_freshness_gate``. It never runs an indexer and never writes
the HoloIndex store.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Iterable, Sequence

from holo_index.ci_freshness_gate import (
    EXIT_OK,
    EXIT_STALE,
    HoloIndexCIFreshnessGateResult,
    check_ci_freshness,
)
from holo_index.freshness_receipt import freshness_receipt_path


def discover_changed_paths(
    *,
    repo_root: str | Path,
    base_sha: str,
    head_sha: str,
) -> list[str]:
    """Read changed paths with a read-only git diff command."""

    _validate_sha(base_sha)
    _validate_sha(head_sha)
    completed = subprocess.run(
        (
            "git",
            "-C",
            str(Path(repo_root)),
            "diff",
            "--name-only",
            "--diff-filter=ACMRT",
            base_sha,
            head_sha,
        ),
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        raise RuntimeError("changed_path_discovery_failed")
    return _normalize_paths(completed.stdout.splitlines())


def run_ci_main_freshness_gate(
    *,
    changed_paths: Iterable[str | Path],
    expected_repo_head_sha: str | None,
    receipt_path: str | Path | None = None,
    ssd_path: str | Path | None = None,
    enforce_configured: bool = False,
) -> HoloIndexCIFreshnessGateResult:
    """Evaluate HoloIndex freshness for changed paths in CI."""

    resolved_receipt = _resolve_receipt_path(receipt_path=receipt_path, ssd_path=ssd_path)
    return check_ci_freshness(
        receipt_path=resolved_receipt,
        changed_paths=changed_paths,
        expected_repo_head_sha=expected_repo_head_sha,
        allow_not_configured=not enforce_configured,
    )


def _resolve_receipt_path(
    *,
    receipt_path: str | Path | None,
    ssd_path: str | Path | None,
) -> str | None:
    if receipt_path:
        return str(receipt_path)
    env_receipt = os.getenv("HOLOINDEX_FRESHNESS_RECEIPT", "").strip()
    if env_receipt:
        return env_receipt
    if ssd_path is not None:
        env_ssd = str(ssd_path).strip()
    else:
        env_ssd = os.getenv("HOLOINDEX_SSD_PATH", "").strip()
    if not env_ssd:
        return None
    return str(freshness_receipt_path(env_ssd))


def _normalize_paths(paths: Iterable[str | Path]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for path in paths:
        text = str(path).replace("\\", "/").strip()
        while text.startswith("./"):
            text = text[2:]
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
    return out


def _validate_sha(value: str) -> None:
    if not value or any(char not in "0123456789abcdefABCDEF" for char in value):
        raise ValueError("invalid_git_sha")


def _read_paths_file(path: str | Path) -> list[str]:
    return _normalize_paths(Path(path).read_text(encoding="utf-8").splitlines())


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run HoloIndex CI main freshness gate.")
    parser.add_argument("--receipt", help="Path to holoindex_freshness_receipt.json.")
    parser.add_argument("--ssd", help="HoloIndex SSD root. Defaults to HOLOINDEX_SSD_PATH when set.")
    parser.add_argument("--changed-path", action="append", default=[], help="Changed path. May repeat.")
    parser.add_argument("--changed-paths-file", help="File with one changed path per line.")
    parser.add_argument("--repo-root", default=".", help="Repository root for git diff discovery.")
    parser.add_argument("--base-sha", help="Base SHA for git diff discovery.")
    parser.add_argument("--head-sha", help="Head SHA for git diff discovery and freshness check.")
    parser.add_argument(
        "--enforce-configured",
        action="store_true",
        help="Fail when the freshness receipt is missing/not mounted.",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    changed_paths = list(args.changed_path or [])
    if args.changed_paths_file:
        changed_paths.extend(_read_paths_file(args.changed_paths_file))
    if not changed_paths and args.base_sha and args.head_sha:
        changed_paths = discover_changed_paths(
            repo_root=args.repo_root,
            base_sha=args.base_sha,
            head_sha=args.head_sha,
        )

    result = run_ci_main_freshness_gate(
        changed_paths=changed_paths,
        expected_repo_head_sha=args.head_sha,
        receipt_path=args.receipt,
        ssd_path=args.ssd,
        enforce_configured=args.enforce_configured,
    )
    payload = result.to_dict()
    if args.pretty:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(result.to_json())
    return EXIT_OK if result.ok else EXIT_STALE


__all__ = [
    "discover_changed_paths",
    "main",
    "run_ci_main_freshness_gate",
]


if __name__ == "__main__":
    raise SystemExit(main())
