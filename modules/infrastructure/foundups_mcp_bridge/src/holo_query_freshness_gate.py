"""Fail-closed freshness and maintenance gates for HoloIndex queries.

The owner service has read-only authority.  It therefore observes, but never
creates, the canonical maintenance lease and rejects a query whenever a clear
lease state cannot be proven around repository or freshness evaluation.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from holo_index.freshness_receipt import (
    BASELINE_QUERY_COLLECTIONS,
    BASELINE_QUERY_FRESHNESS_PATHS,
)
from holo_index.maintenance_lock import (
    maintenance_lock_path,
    probe_maintenance_lock,
)
from holo_index.query_receipt import generation_binding_from_receipt
from holo_index.storage_contract import storage_path_identity


BASELINE_FRESHNESS_PATHS = BASELINE_QUERY_FRESHNESS_PATHS
BASELINE_COLLECTIONS = BASELINE_QUERY_COLLECTIONS
MAINTENANCE_ACTIVE_ERROR = "HOLOINDEX_MAINTENANCE_ACTIVE"
MAINTENANCE_ACTIVE_REASON = "holoindex_maintenance_active"
MAINTENANCE_UNPROVEN_ERROR = "HOLOINDEX_MAINTENANCE_LOCK_UNPROVEN"
MAINTENANCE_UNPROVEN_REASON = "holoindex_maintenance_lock_unproven"


@dataclass(frozen=True)
class FreshnessSnapshot:
    binding: Mapping[str, str]
    freshness: str
    stale_reasons: tuple[str, ...]
    valid: bool
    embedding_spaces: Mapping[str, str]


def _dedupe(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value for value in values if value))


def normalize_binding(value: Mapping[str, Any] | None = None) -> dict[str, str]:
    source = value or {}
    return {
        key: str(source.get(key) or "")
        for key in (
            "freshness_generation_id",
            "freshness_receipt_digest",
            "freshness_receipt_path",
            "repo_head_sha",
        )
    }


def _receipt_value(receipt: Any, name: str) -> str:
    if isinstance(receipt, Mapping):
        return str(receipt.get(name) or "")
    return str(getattr(receipt, name, "") or "")


def _entry_value(entry: Any, name: str) -> str:
    if isinstance(entry, Mapping):
        return str(entry.get(name) or "")
    return str(getattr(entry, name, "") or "")


def _receipt_embedding_spaces(
    receipt: Any,
    required: frozenset[str],
) -> tuple[dict[str, str], list[str]]:
    raw_entries = (
        receipt.get("collections", [])
        if isinstance(receipt, Mapping)
        else getattr(receipt, "collections", [])
    )
    entries = raw_entries if isinstance(raw_entries, Sequence) else []
    spaces: dict[str, str] = {}
    seen_names: set[str] = set()
    duplicate_names: set[str] = set()
    for entry in entries:
        name = _entry_value(entry, "name")
        if name not in required:
            continue
        if name in seen_names:
            duplicate_names.add(name)
        seen_names.add(name)
        fingerprint = _entry_value(entry, "embedding_space_fingerprint")
        if (
            fingerprint.startswith("sha256:")
            and len(fingerprint) == 71
            and all(character in "0123456789abcdef" for character in fingerprint[7:])
        ):
            spaces[name] = fingerprint
    reasons = [
        f"duplicate_collection_embedding_space:{name}"
        for name in sorted(duplicate_names)
    ]
    reasons.extend(
        f"collection_embedding_space_unproven:{name}"
        for name in sorted(required.difference(spaces))
    )
    return spaces, reasons


def _path_identity(path: Path | str) -> str:
    return str(Path(path).resolve(strict=False)).casefold()


class HoloQueryFreshnessGate:
    """Read-only repository, freshness, and maintenance proof boundary."""

    def __init__(
        self,
        repo_root: Path,
        ssd_path: Path,
        receipt_path: Path,
        loader: Callable[[Path], Any],
        evaluator: Callable[..., Any],
        maintenance_probe: Callable[[Path], Any] | None = None,
    ) -> None:
        self.repo_root = repo_root.resolve(strict=False)
        self.ssd_path = ssd_path.resolve(strict=False)
        self.receipt_path = receipt_path
        self.lock_path = maintenance_lock_path(ssd_path)
        self._loader, self._evaluator = loader, evaluator
        self._maintenance_probe = maintenance_probe or probe_maintenance_lock

    def maintenance_block(self) -> tuple[str, str]:
        try:
            probe = self._maintenance_probe(self.lock_path)
        except Exception:
            return MAINTENANCE_UNPROVEN_ERROR, MAINTENANCE_UNPROVEN_REASON
        if getattr(probe, "clear", False) is True:
            return "", ""
        if getattr(probe, "held", False) is True or getattr(probe, "status", "") == "held":
            return MAINTENANCE_ACTIVE_ERROR, MAINTENANCE_ACTIVE_REASON
        return MAINTENANCE_UNPROVEN_ERROR, MAINTENANCE_UNPROVEN_REASON

    def repository_error(
        self,
        reader: Callable[[Path], Any],
        repo_root: Path,
        expected_sha: str = "",
    ) -> tuple[str, str]:
        block = self.maintenance_block()
        if block[0]:
            return block[0], ""
        try:
            state = reader(repo_root)
        except Exception:
            block = self.maintenance_block()
            if block[0]:
                return block[0], ""
            return "HOLOINDEX_REPOSITORY_STATE_UNAVAILABLE", ""
        block = self.maintenance_block()
        if block[0]:
            return block[0], ""
        if not getattr(state, "proven_clean", False):
            return (
                str(
                    getattr(state, "error", "")
                    or "HOLOINDEX_REPOSITORY_STATE_UNAVAILABLE"
                ),
                "",
            )
        head_sha = str(getattr(state, "head_sha", "") or "")
        if expected_sha and head_sha != expected_sha:
            return "REPO_HEAD_MISMATCH", head_sha
        return "", head_sha

    def _unavailable(self, reason: str) -> FreshnessSnapshot:
        fields = generation_binding_from_receipt(
            None, receipt_path=self.receipt_path
        )
        return FreshnessSnapshot(
            normalize_binding(fields), "UNKNOWN", (reason,), False, {}
        )

    def _unavailable_after_probe(self, reason: str) -> FreshnessSnapshot:
        block = self.maintenance_block()
        return self._unavailable(block[1] if block[0] else reason)

    def _identity_reasons(self, receipt: Any) -> list[str]:
        reasons: list[str] = []
        receipt_repo = _receipt_value(receipt, "repo_root")
        receipt_ssd = _receipt_value(receipt, "ssd_path")
        if not receipt_repo or _path_identity(receipt_repo) != _path_identity(
            self.repo_root
        ):
            reasons.append("freshness_repo_root_mismatch")
        if not receipt_ssd or storage_path_identity(
            receipt_ssd
        ) != storage_path_identity(self.ssd_path):
            reasons.append("freshness_ssd_path_mismatch")
        return reasons

    def _evaluate_receipt(
        self,
        receipt: Any,
        expected_sha: str,
    ) -> tuple[list[str], set[str], bool]:
        try:
            check = self._evaluator(
                receipt,
                BASELINE_FRESHNESS_PATHS,
                expected_repo_head_sha=expected_sha,
            )
            return (
                self._identity_reasons(receipt) + list(check.reasons),
                set(check.required_collections),
                check.ok is True,
            )
        except Exception:
            return ["freshness_evaluation_failed"], set(), False

    def snapshot(self, expected_sha: str) -> FreshnessSnapshot:
        block = self.maintenance_block()
        if block[0]:
            return self._unavailable(block[1])
        try:
            receipt = self._loader(self.receipt_path)
        except FileNotFoundError:
            return self._unavailable_after_probe("missing_freshness_receipt")
        except Exception:
            return self._unavailable_after_probe("malformed_freshness_receipt")
        fields = normalize_binding(
            generation_binding_from_receipt(
                receipt, receipt_path=self.receipt_path
            )
        )
        reasons, required, check_ok = self._evaluate_receipt(
            receipt,
            expected_sha,
        )
        block = self.maintenance_block()
        if block[0]:
            return self._unavailable(block[1])
        if required != BASELINE_COLLECTIONS:
            reasons.append("baseline_collection_proof_incomplete")
        embedding_spaces, embedding_reasons = _receipt_embedding_spaces(
            receipt, BASELINE_COLLECTIONS
        )
        reasons.extend(embedding_reasons)
        if not fields["freshness_generation_id"]:
            reasons.append("missing_holoindex_generation_id")
        if not fields["freshness_receipt_digest"]:
            reasons.append("missing_holoindex_freshness_receipt_digest")
        if fields["repo_head_sha"] != expected_sha:
            reasons.append("stale_repo_head_sha")
        stale_reasons = _dedupe(reasons)
        valid = check_ok and not stale_reasons
        return FreshnessSnapshot(
            fields,
            "CURRENT" if valid else "STALE",
            stale_reasons,
            valid,
            embedding_spaces,
        )


def snapshot_error(snapshot: FreshnessSnapshot) -> str:
    if MAINTENANCE_ACTIVE_REASON in snapshot.stale_reasons:
        return MAINTENANCE_ACTIVE_ERROR
    if MAINTENANCE_UNPROVEN_REASON in snapshot.stale_reasons:
        return MAINTENANCE_UNPROVEN_ERROR
    if not snapshot.binding.get(
        "freshness_generation_id"
    ) or not snapshot.binding.get("freshness_receipt_digest"):
        return "MISSING_GENERATION_BINDING"
    if "stale_repo_head_sha" in snapshot.stale_reasons:
        return "REPO_HEAD_MISMATCH"
    return "STALE_INDEX"


def maintenance_reason_for_error(error: str) -> str:
    if error == MAINTENANCE_ACTIVE_ERROR:
        return MAINTENANCE_ACTIVE_REASON
    if error == MAINTENANCE_UNPROVEN_ERROR:
        return MAINTENANCE_UNPROVEN_REASON
    return ""


__all__ = [
    "BASELINE_COLLECTIONS",
    "BASELINE_FRESHNESS_PATHS",
    "FreshnessSnapshot",
    "HoloQueryFreshnessGate",
    "MAINTENANCE_ACTIVE_ERROR",
    "MAINTENANCE_ACTIVE_REASON",
    "MAINTENANCE_UNPROVEN_ERROR",
    "MAINTENANCE_UNPROVEN_REASON",
    "maintenance_reason_for_error",
    "normalize_binding",
    "snapshot_error",
]
