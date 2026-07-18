"""Truthful HoloIndex maintenance transaction boundary.

This module coordinates the cross-process lease and freshness receipt used by
CLI/WRE maintenance owners. Query workers never import this writer API.
"""

from __future__ import annotations

import atexit
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

from holo_index.freshness_receipt import (
    HoloIndexFreshnessReceipt,
    build_freshness_receipt,
    freshness_receipt_path,
    load_freshness_receipt,
    publish_maintenance_invalidation,
    write_freshness_receipt,
)
from holo_index.embedding_space import CANONICAL_INDEX_BACKEND
from holo_index.maintenance_lock import (
    MaintenanceLease,
    MaintenanceLockError,
    acquire_maintenance_lease,
    maintenance_lock_path,
)
from holo_index.repository_state import read_repository_state
from holo_index.source_scope import canonical_source_scope_id


MAINTENANCE_FAILURE_EXIT_CODE = 4


class MaintenanceSessionError(RuntimeError):
    """Stable fail-closed maintenance boundary error."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"ok": False, "error": self.code}
        if self.detail:
            payload["detail"] = self.detail
        return payload


def _complete_source_proofs(
    planned: frozenset[str],
    refresh_proofs: Mapping[str, Any] | None,
) -> tuple[dict[str, str], dict[str, str]]:
    proofs = dict(refresh_proofs or {})
    if set(proofs) != set(planned):
        raise MaintenanceSessionError(
            "HOLOINDEX_MAINTENANCE_SOURCE_PROOF_INCOMPLETE",
            f"expected={sorted(planned)}; actual={sorted(proofs)}",
        )
    manifests: dict[str, str] = {}
    scopes: dict[str, str] = {}
    failed: list[str] = []
    for name in sorted(planned):
        proof = proofs[name]
        digest = str(getattr(proof, "source_manifest_digest", "") or "")
        scope = str(getattr(proof, "source_scope_id", "") or "")
        expected_scope = canonical_source_scope_id(name)
        if (
            getattr(proof, "complete", False) is not True
            or str(getattr(proof, "collection_name", "")) != name
            or not digest.startswith("sha256:")
            or (expected_scope and scope != expected_scope)
        ):
            failed.append(name)
            continue
        manifests[name] = digest
        if scope:
            scopes[name] = scope
    if failed:
        raise MaintenanceSessionError(
            "HOLOINDEX_MAINTENANCE_SOURCE_PROOF_INCOMPLETE",
            f"collections={failed}",
        )
    return manifests, scopes


def _final_proof_failures(
    receipt: HoloIndexFreshnessReceipt,
    *,
    refreshed: frozenset[str],
    refresh_proofs: Mapping[str, Any],
    head_sha: str,
) -> list[str]:
    by_name = {entry.name: entry for entry in receipt.collections}
    failed: list[str] = []
    for name in refreshed:
        entry = by_name.get(name)
        expected_scope = canonical_source_scope_id(name)
        if (
            entry is None
            or entry.status != "indexed"
            or entry.verification != "PASS"
            or entry.proof_kind != "complete_source_manifest"
            or entry.repo_head_sha != head_sha
            or entry.count != int(getattr(refresh_proofs[name], "indexed_count", -1))
            or not entry.source_manifest_digest
            or not entry.indexed_paths_digest
            or entry.embedding_backend != CANONICAL_INDEX_BACKEND
            or not entry.embedding_model
            or not entry.embedding_space_fingerprint.startswith("sha256:")
            or (expected_scope and entry.source_scope_id != expected_scope)
        ):
            failed.append(name)
    return sorted(failed)


def _clean_repository_head(
    repo_root: Path,
    state_reader: Callable[[Path], Any],
    *,
    require_head: bool = True,
) -> str:
    state = state_reader(repo_root)
    if not getattr(state, "proven_clean", False):
        raise MaintenanceSessionError(
            str(
                getattr(state, "error", "")
                or "HOLOINDEX_REPOSITORY_STATE_UNAVAILABLE"
            )
        )
    head_sha = str(getattr(state, "head_sha", "") or "")
    if require_head and not head_sha:
        raise MaintenanceSessionError("HOLOINDEX_REPOSITORY_STATE_UNAVAILABLE")
    return head_sha


def _begin_invalidation(
    *,
    ssd_path: Path,
    repo_root: Path,
    planned: frozenset[str],
    source: str,
    head_sha: str,
) -> tuple[MaintenanceLease, HoloIndexFreshnessReceipt]:
    try:
        lease = acquire_maintenance_lease(maintenance_lock_path(ssd_path))
    except MaintenanceLockError as exc:
        raise MaintenanceSessionError(
            "HOLOINDEX_MAINTENANCE_LEASE_UNAVAILABLE", str(exc)
        ) from exc
    receipt_path = freshness_receipt_path(ssd_path)
    try:
        base_receipt = None
        if receipt_path.exists():
            try:
                base_receipt = load_freshness_receipt(receipt_path)
            except (OSError, TypeError, ValueError, json.JSONDecodeError):
                base_receipt = None
        invalidation = publish_maintenance_invalidation(
            receipt_path,
            planned,
            ssd_path=ssd_path,
            repo_root=repo_root,
            base_receipt=base_receipt,
            source=source,
            repo_head_sha=head_sha,
        )
    except Exception as exc:
        lease.release()
        raise MaintenanceSessionError(
            "HOLOINDEX_MAINTENANCE_INVALIDATION_FAILED", str(exc)
        ) from exc
    return lease, invalidation


def _validate_completed_plan(
    planned: frozenset[str],
    refreshed_collections: Iterable[str],
) -> frozenset[str]:
    refreshed = frozenset(refreshed_collections)
    if refreshed != planned:
        missing = sorted(planned.difference(refreshed))
        unexpected = sorted(refreshed.difference(planned))
        raise MaintenanceSessionError(
            "HOLOINDEX_MAINTENANCE_INCOMPLETE",
            f"missing={missing}; unexpected={unexpected}",
        )
    return refreshed


def _build_completed_receipt(
    session: Any,
    holo: Any,
    *,
    refreshed: frozenset[str],
    source: str,
    refresh_proofs: Mapping[str, Any] | None,
    source_manifests: Mapping[str, str],
    source_scopes: Mapping[str, str],
    head_sha: str,
) -> HoloIndexFreshnessReceipt:
    receipt = build_freshness_receipt(
        holo,
        ssd_path=session.ssd_path,
        repo_root=session.repo_root,
        source=source,
        repo_head_sha=head_sha,
        refreshed_collections=refreshed,
        base_receipt=session.invalidation_receipt,
        refresh_source_manifests=source_manifests,
        refresh_source_scopes=source_scopes,
    )
    failed = _final_proof_failures(
        receipt,
        refreshed=refreshed,
        refresh_proofs=refresh_proofs or {},
        head_sha=head_sha,
    )
    if failed:
        raise MaintenanceSessionError(
            "HOLOINDEX_MAINTENANCE_PROOF_FAILED", f"collections={failed}"
        )
    return receipt


def _write_completed_receipt(
    session: Any,
    receipt: HoloIndexFreshnessReceipt,
) -> None:
    try:
        write_freshness_receipt(receipt, session.receipt_path)
    except Exception as exc:
        raise MaintenanceSessionError(
            "HOLOINDEX_MAINTENANCE_RECEIPT_WRITE_FAILED", str(exc)
        ) from exc


@dataclass
class MaintenanceSession:
    """Exclusive maintenance lease plus an already-published invalidation."""

    ssd_path: Path
    repo_root: Path
    planned_collections: frozenset[str]
    starting_head_sha: str
    invalidation_receipt: HoloIndexFreshnessReceipt
    _lease: MaintenanceLease
    _repository_state_reader: Callable[[Path], Any]
    _closed: bool = False

    @classmethod
    def begin(
        cls,
        *,
        ssd_path: Path | str,
        repo_root: Path | str,
        planned_collections: Iterable[str],
        source: str = "cli_maintenance_in_progress",
        repository_state_reader: Callable[[Path], Any] | None = None,
    ) -> "MaintenanceSession":
        """Acquire the lease and publish invalidation before store mutation."""

        ssd = Path(ssd_path)
        root = Path(repo_root)
        planned = frozenset(planned_collections)
        if not planned:
            raise MaintenanceSessionError("HOLOINDEX_MAINTENANCE_PLAN_EMPTY")
        state_reader = repository_state_reader or read_repository_state
        head_sha = _clean_repository_head(root, state_reader)
        lease, invalidation = _begin_invalidation(
            ssd_path=ssd,
            repo_root=root,
            planned=planned,
            source=source,
            head_sha=head_sha,
        )

        session = cls(
            ssd_path=ssd,
            repo_root=root,
            planned_collections=planned,
            starting_head_sha=head_sha,
            invalidation_receipt=invalidation,
            _lease=lease,
            _repository_state_reader=state_reader,
        )
        atexit.register(session.close)
        return session

    @property
    def receipt_path(self) -> Path:
        return freshness_receipt_path(self.ssd_path)

    def complete(
        self,
        holo: Any,
        *,
        refreshed_collections: Iterable[str],
        source: str,
        refresh_proofs: Mapping[str, Any] | None = None,
    ) -> HoloIndexFreshnessReceipt:
        """Publish PASS only when the whole declared plan is proven complete."""

        refreshed = _validate_completed_plan(
            self.planned_collections,
            refreshed_collections,
        )
        source_manifests, source_scopes = _complete_source_proofs(
            self.planned_collections,
            refresh_proofs,
        )
        head_sha = _clean_repository_head(
            self.repo_root,
            self._repository_state_reader,
            require_head=False,
        )
        if head_sha != self.starting_head_sha:
            raise MaintenanceSessionError(
                "HOLOINDEX_REPOSITORY_HEAD_CHANGED",
                f"expected={self.starting_head_sha}; actual={head_sha}",
            )
        receipt = _build_completed_receipt(
            self,
            holo,
            refreshed=refreshed,
            source=source,
            refresh_proofs=refresh_proofs,
            source_manifests=source_manifests,
            source_scopes=source_scopes,
            head_sha=head_sha,
        )
        _write_completed_receipt(self, receipt)
        return receipt

    def close(self) -> None:
        if self._closed:
            return
        self._lease.release()
        self._closed = True

    def __enter__(self) -> "MaintenanceSession":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()


__all__ = [
    "MAINTENANCE_FAILURE_EXIT_CODE",
    "MaintenanceSession",
    "MaintenanceSessionError",
]
