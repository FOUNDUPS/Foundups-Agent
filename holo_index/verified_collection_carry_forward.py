"""Verified carry-forward evidence for targeted HoloIndex maintenance."""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from holo_index.source_scope import canonical_source_scope_id


SHA_PATTERN = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})")
SHARED_POLICY_FILES = (
    "holo_index/canonical_source_manifest.py",
    "holo_index/freshness_receipt.py",
    "holo_index/maintenance_session.py",
    "holo_index/cli_index_plan.py",
    "holo_index/verified_collection_carry_forward.py",
)
POLICY_ENVIRONMENT: dict[str, tuple[str, ...]] = {
    "navigation_code": (
        "HOLO_INDEX_WEB",
        "HOLO_WEB_INDEX_ROOTS",
        "HOLO_WEB_INDEX_EXTENSIONS",
        "HOLO_WEB_INDEX_MAX_FILES",
        "HOLO_WEB_INDEX_MAX_CHARS",
    ),
    "navigation_symbols": (
        "HOLO_SYMBOL_ROOTS",
        "HOLO_SYMBOL_MAX_FILES",
        "HOLO_SYMBOL_MAX_ENTRIES",
    ),
}
POLICY_FILES: dict[str, tuple[str, ...]] = {
    "navigation_code": (
        "holo_index/source_scope.py",
        "holo_index/core/holo_index.py",
        "holo_index/core/indexing_engine.py",
    ),
    "navigation_symbols": (
        "holo_index/source_scope.py",
        "holo_index/core/indexing_engine.py",
        "holo_index/symbol_indexer.py",
    ),
    "navigation_tests": (
        "holo_index/source_scope.py",
        "holo_index/core/indexing_engine.py",
        "holo_index/test_registry_indexer.py",
    ),
    "navigation_wsp": (
        "holo_index/source_scope.py",
        "holo_index/core/indexing_engine.py",
    ),
    "navigation_skills": (
        "holo_index/source_scope.py",
        "holo_index/core/indexing_engine.py",
    ),
    "navigation_docs": (
        "holo_index/source_scope.py",
        "holo_index/core/indexing_engine.py",
    ),
    "navigation_knowledge": (
        "holo_index/source_scope.py",
        "holo_index/core/indexing_engine.py",
    ),
}


@dataclass(frozen=True)
class VerifiedCarryForward:
    collection_name: str
    source_policy_digest: str
    current_source_manifest_digest: str
    carried_from_repo_head_sha: str
    carried_from_generation_id: str
    evidence_digest: str


def _digest(value: Any) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def carry_forward_evidence_digest(
    *,
    collection_name: str,
    source_manifest_digest: str,
    source_policy_digest: str,
    carried_from_repo_head_sha: str,
    carried_from_generation_id: str,
    current_repo_head_sha: str,
) -> str:
    """Return the canonical v2 carry-forward evidence digest."""

    return _digest(
        {
            "schema_version": "holoindex_carry_forward_evidence.v2",
            "collection_name": collection_name,
            "source_manifest_digest": source_manifest_digest,
            "source_policy_digest": source_policy_digest,
            "carried_from_repo_head_sha": carried_from_repo_head_sha,
            "carried_from_generation_id": carried_from_generation_id,
            "current_repo_head_sha": current_repo_head_sha,
        }
    )


def collection_source_policy_digest(
    repo_root: Path,
    collection_name: str,
) -> str:
    """Bind source-discovery code and relevant environment to one collection."""

    collection_paths = POLICY_FILES.get(collection_name)
    if not collection_paths:
        return ""
    relative_paths = (*SHARED_POLICY_FILES, *collection_paths)
    policy_root = repo_root
    if not (policy_root / ".git").exists():
        policy_root = Path(__file__).resolve().parents[1]
    files: list[dict[str, str]] = []
    for relative in relative_paths:
        path = policy_root / relative
        try:
            content_digest = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            return ""
        files.append({"path": relative, "content_sha256": content_digest})
    environment = {
        name: os.environ.get(name, "")
        for name in POLICY_ENVIRONMENT.get(collection_name, ())
    }
    return _digest(
        {
            "schema_version": "holoindex_source_policy.v1",
            "collection_name": collection_name,
            "files": files,
            "environment": environment,
        }
    )


def build_carry_forward_evidence(
    *,
    repo_root: Path,
    base_receipt: Any,
    collection_names: Sequence[str],
    head_sha: str,
    current_source_manifests: Mapping[str, Any],
) -> Mapping[str, VerifiedCarryForward]:
    """Prove exact source-manifest and policy stability for unrefreshed collections."""

    if not collection_names:
        return {}
    if not SHA_PATTERN.fullmatch(head_sha):
        raise ValueError("carry_forward_head_sha_invalid")
    raw_entries = getattr(base_receipt, "collections", ())
    entries = {str(entry.name): entry for entry in raw_entries}
    generation_id = str(getattr(base_receipt, "generation_id", "") or "")
    if not generation_id:
        raise ValueError("carry_forward_base_generation_missing")
    evidence: dict[str, VerifiedCarryForward] = {}
    for name in sorted(set(collection_names)):
        entry = entries.get(name)
        if entry is None:
            raise ValueError(f"carry_forward_entry_missing:{name}")
        base_sha = str(getattr(entry, "repo_head_sha", "") or "")
        if not SHA_PATTERN.fullmatch(base_sha):
            raise ValueError(f"carry_forward_base_sha_invalid:{name}")
        if base_sha != str(getattr(base_receipt, "repo_head_sha", "") or ""):
            raise ValueError(f"carry_forward_base_lineage_mismatch:{name}")
        expected_scope = canonical_source_scope_id(name)
        allowed_proofs = {
            "complete_source_manifest",
            "verified_unchanged_source_manifest",
        }
        if (
            str(getattr(entry, "status", "")) != "indexed"
            or str(getattr(entry, "verification", "")) != "PASS"
            or str(getattr(entry, "proof_kind", "")) not in allowed_proofs
            or not str(getattr(entry, "source_manifest_digest", "") or "")
            or not str(getattr(entry, "indexed_paths_digest", "") or "")
            or not str(getattr(entry, "collection_snapshot_digest", "") or "")
            or (expected_scope and getattr(entry, "source_scope_id", "") != expected_scope)
        ):
            raise ValueError(f"carry_forward_prior_proof_invalid:{name}")
        current_policy = collection_source_policy_digest(repo_root, name)
        if not current_policy or current_policy != str(
            getattr(entry, "source_policy_digest", "") or ""
        ):
            raise ValueError(f"carry_forward_policy_changed:{name}")
        current_manifest = current_source_manifests.get(name)
        manifest_digest = str(getattr(current_manifest, "digest", "") or "")
        manifest_scope = str(
            getattr(current_manifest, "source_scope_id", "") or ""
        )
        if (
            not manifest_digest
            or manifest_digest != entry.source_manifest_digest
            or manifest_scope != expected_scope
        ):
            raise ValueError(f"carry_forward_source_manifest_changed:{name}")
        evidence_digest = carry_forward_evidence_digest(
            collection_name=name,
            source_manifest_digest=manifest_digest,
            source_policy_digest=current_policy,
            carried_from_repo_head_sha=base_sha,
            carried_from_generation_id=generation_id,
            current_repo_head_sha=head_sha,
        )
        evidence[name] = VerifiedCarryForward(
            collection_name=name,
            source_policy_digest=current_policy,
            current_source_manifest_digest=manifest_digest,
            carried_from_repo_head_sha=base_sha,
            carried_from_generation_id=generation_id,
            evidence_digest=evidence_digest,
        )
    return evidence


__all__ = [
    "VerifiedCarryForward",
    "build_carry_forward_evidence",
    "carry_forward_evidence_digest",
    "collection_source_policy_digest",
]
