"""Fail-closed admission for read-only queries against a persistent store.

The canonical owner service remains authoritative for RedDog. This helper
reuses its freshness gate so raw CLI and direct diagnostic reads cannot bypass
repository-root, SSD, generation, baseline, or maintenance proof.
"""

from __future__ import annotations

import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from holo_index.freshness_receipt import (
    evaluate_freshness_for_paths,
    freshness_receipt_path,
    load_freshness_receipt,
)
from holo_index.repository_state import (
    REPOSITORY_DIRTY_CODE,
    REPOSITORY_STATE_UNAVAILABLE_CODE,
    read_repository_state,
)
from modules.infrastructure.foundups_mcp_bridge.src.holo_query_freshness_gate import (
    HoloQueryFreshnessGate,
    maintenance_reason_for_error,
    snapshot_error,
)

RECEIPT_PATH_MISMATCH_CODE = "HOLOINDEX_FRESHNESS_RECEIPT_PATH_MISMATCH"
RECEIPT_PATH_MISMATCH_REASON = "freshness_receipt_path_not_canonical"
EXPECTED_HEAD_INVALID_CODE = "HOLOINDEX_EXPECTED_REPO_HEAD_INVALID"
EXPECTED_HEAD_INVALID_REASON = "expected_repo_head_sha_invalid"
WINDOWS_REPARSE_POINT = 0x400


@dataclass(frozen=True)
class ReadonlyQueryAdmission:
    """Content-free decision returned before persistent backend construction."""

    allowed: bool
    error: str
    reasons: tuple[str, ...]
    freshness: str
    binding: Mapping[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.allowed,
            "error": self.error,
            "freshness": self.freshness,
            "stale_reasons": list(self.reasons),
            "index_gap_detected": not self.allowed,
            "no_holoindex_reindex_performed": True,
        }


def _repository_reason(error: str) -> str:
    maintenance_reason = maintenance_reason_for_error(error)
    if maintenance_reason:
        return maintenance_reason
    if error == REPOSITORY_DIRTY_CODE:
        return "repository_dirty"
    if error == REPOSITORY_STATE_UNAVAILABLE_CODE:
        return "repository_state_unavailable"
    return "repository_state_unproven"


def _final_receipt_link_or_reparse(path: Path) -> bool:
    """Reject a present final receipt component that redirects elsewhere."""
    try:
        metadata = os.lstat(path)
    except FileNotFoundError:
        return False
    except OSError:
        return True
    attributes = int(getattr(metadata, "st_file_attributes", 0) or 0)
    return stat.S_ISLNK(metadata.st_mode) or bool(
        attributes & WINDOWS_REPARSE_POINT
    )


def _stable_path_identity(path: Path | str) -> str:
    """Canonicalize through the stable existing ancestor for comparison."""
    try:
        return os.path.normcase(str(Path(path).resolve(strict=False)))
    except (OSError, RuntimeError, ValueError):
        return ""


def _canonical_receipt_binding(
    ssd: Path,
    supplied: Path | str | None,
) -> tuple[Path, bool]:
    expected = freshness_receipt_path(ssd)
    supplied_path = Path(supplied) if supplied is not None else expected
    invalid = (
        not _stable_path_identity(expected)
        or _stable_path_identity(supplied_path)
        != _stable_path_identity(expected)
        or _final_receipt_link_or_reparse(expected)
        or _final_receipt_link_or_reparse(supplied_path)
    )
    return expected, invalid


def _build_gate(
    root: Path,
    ssd: Path,
    receipt_path: Path,
    receipt_loader: Callable[[Path], Any] | None,
    freshness_evaluator: Callable[..., Any] | None,
    maintenance_probe: Callable[[Path], Any] | None,
) -> HoloQueryFreshnessGate:
    return HoloQueryFreshnessGate(
        root,
        ssd,
        receipt_path,
        receipt_loader or load_freshness_receipt,
        freshness_evaluator or evaluate_freshness_for_paths,
        maintenance_probe,
    )


def _evaluate_gate(
    gate: HoloQueryFreshnessGate,
    root: Path,
    repository_state_reader: Callable[[Path], Any] | None,
    expected_repo_head_sha: str = "",
) -> ReadonlyQueryAdmission:
    error, head_sha = gate.repository_error(
        repository_state_reader or read_repository_state,
        root,
        expected_repo_head_sha,
    )
    if error:
        return ReadonlyQueryAdmission(
            False, error, (_repository_reason(error),), "UNKNOWN", {}
        )
    snapshot = gate.snapshot(head_sha)
    if not snapshot.valid:
        return ReadonlyQueryAdmission(
            False,
            snapshot_error(snapshot),
            snapshot.stale_reasons,
            snapshot.freshness,
            snapshot.binding,
        )
    return ReadonlyQueryAdmission(
        True, "", (), snapshot.freshness, snapshot.binding
    )


def evaluate_readonly_query_admission(
    *,
    repo_root: Path | str,
    ssd_path: Path | str,
    receipt_path: Path | str | None = None,
    repository_state_reader: Callable[[Path], Any] | None = None,
    receipt_loader: Callable[[Path], Any] | None = None,
    freshness_evaluator: Callable[..., Any] | None = None,
    maintenance_probe: Callable[[Path], Any] | None = None,
) -> ReadonlyQueryAdmission:
    """Prove one exact repository generation before opening persistent Chroma."""

    root = Path(repo_root).resolve(strict=False)
    ssd = Path(ssd_path).resolve(strict=False)
    canonical_receipt, invalid_receipt = _canonical_receipt_binding(
        ssd,
        receipt_path,
    )
    if invalid_receipt:
        return ReadonlyQueryAdmission(
            False,
            RECEIPT_PATH_MISMATCH_CODE,
            (RECEIPT_PATH_MISMATCH_REASON,),
            "UNKNOWN",
            {},
        )
    gate = _build_gate(
        root,
        ssd,
        canonical_receipt,
        receipt_loader,
        freshness_evaluator,
        maintenance_probe,
    )
    return _evaluate_gate(gate, root, repository_state_reader)


def rehydrate_canonical_freshness_proof(
    *,
    repo_root: Path | str,
    ssd_path: Path | str,
    expected_repo_head_sha: str,
    repository_state_reader: Callable[[Path], Any] | None = None,
    receipt_loader: Callable[[Path], Any] | None = None,
    freshness_evaluator: Callable[..., Any] | None = None,
    maintenance_probe: Callable[[Path], Any] | None = None,
) -> ReadonlyQueryAdmission:
    """Rehydrate one canonical exact-HEAD proof without opening the index owner."""
    root = Path(repo_root).resolve(strict=False)
    ssd = Path(ssd_path).resolve(strict=False)
    expected_sha = str(expected_repo_head_sha or "").strip().lower()
    if re.fullmatch(r"[0-9a-f]{40}", expected_sha) is None:
        return ReadonlyQueryAdmission(
            False,
            EXPECTED_HEAD_INVALID_CODE,
            (EXPECTED_HEAD_INVALID_REASON,),
            "UNKNOWN",
            {},
        )
    canonical_receipt, invalid_receipt = _canonical_receipt_binding(ssd, None)
    if invalid_receipt:
        return ReadonlyQueryAdmission(
            False,
            RECEIPT_PATH_MISMATCH_CODE,
            (RECEIPT_PATH_MISMATCH_REASON,),
            "UNKNOWN",
            {},
        )
    gate = _build_gate(
        root,
        ssd,
        canonical_receipt,
        receipt_loader,
        freshness_evaluator,
        maintenance_probe,
    )
    return _evaluate_gate(
        gate,
        root,
        repository_state_reader,
        expected_sha,
    )


__all__ = [
    "EXPECTED_HEAD_INVALID_CODE",
    "EXPECTED_HEAD_INVALID_REASON",
    "RECEIPT_PATH_MISMATCH_CODE",
    "RECEIPT_PATH_MISMATCH_REASON",
    "ReadonlyQueryAdmission",
    "evaluate_readonly_query_admission",
    "rehydrate_canonical_freshness_proof",
]
