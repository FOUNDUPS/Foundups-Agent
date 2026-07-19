"""HoloIndex freshness receipt helpers.

WSP 97: freshness is evidence, not an assumption. Missing receipts or missing
collection entries fail closed for write-sensitive RedDog/WRE gates.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import tempfile
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from holo_index.source_scope import canonical_source_scope_id
from holo_index.verified_collection_carry_forward import (
    carry_forward_evidence_digest,
)


SCHEMA_VERSION = "holoindex_freshness_receipt.v2"
COLLECTION_SCHEMA_VERSION = "holoindex_collection_freshness.v2"
FRESHNESS_RECEIPT_FILENAME = "holoindex_freshness_receipt.json"

COLLECTION_ATTRS: dict[str, str] = {
    "navigation_code": "code_collection",
    "navigation_wsp": "wsp_collection",
    "navigation_tests": "test_collection",
    "navigation_skills": "skill_collection",
    "navigation_symbols": "symbol_collection",
    "navigation_docs": "docs_collection",
    "navigation_knowledge": "knowledge_collection",
    "navigation_work_ledger": "work_ledger_collection",
    "navigation_vocabulary": "vocabulary_collection",
}

ALL_COLLECTIONS: tuple[str, ...] = tuple(COLLECTION_ATTRS)
BASELINE_QUERY_COLLECTIONS = frozenset(
    {
        "navigation_code",
        "navigation_symbols",
        "navigation_wsp",
        "navigation_tests",
        "navigation_skills",
        "navigation_docs",
        "navigation_knowledge",
    }
)
BASELINE_QUERY_FRESHNESS_PATHS = (
    "NAVIGATION.py",
    "modules/_holoindex_baseline/source.py",
    "WSP_framework/src/WSP_00_Zen_State_Attainment_Protocol.md",
    "modules/_holoindex_baseline/tests/test_baseline.py",
    "modules/_holoindex_baseline/SKILLz.md",
    "modules/_holoindex_baseline/README.md",
    "WSP_knowledge/docs/Papers/_holoindex_baseline.md",
)
SHA_PATTERN = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})")
DIGEST_PATTERN = re.compile(r"sha256:[0-9a-f]{64}")


@dataclass(frozen=True)
class CollectionFreshness:
    """Freshness metadata for one HoloIndex collection."""

    name: str
    count: int
    status: str
    source: str
    repo_head_sha: str
    last_indexed_at: str
    source_manifest_digest: str = ""
    indexed_paths_digest: str = ""
    removed_paths_digest: str = ""
    schema_version: str = COLLECTION_SCHEMA_VERSION
    embedding_backend: str = ""
    embedding_model: str = ""
    embedding_space_fingerprint: str = ""
    verification: str = "UNKNOWN"
    proof_kind: str = "snapshot_only"
    source_scope_id: str = ""
    source_policy_digest: str = ""
    carried_from_repo_head_sha: str = ""
    carried_from_generation_id: str = ""
    carry_forward_evidence_digest: str = ""
    collection_snapshot_digest: str = ""


@dataclass(frozen=True)
class HoloIndexFreshnessReceipt:
    """Durable receipt emitted after HoloIndex maintenance writes."""

    schema_version: str
    generated_at: str
    repo_root: str
    repo_head_sha: str
    ssd_path: str
    source: str
    generation_id: str = ""
    base_generation_id: str = ""
    collections: list[CollectionFreshness] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)


@dataclass(frozen=True)
class FreshnessCheck:
    """Result of checking whether a receipt covers changed paths."""

    ok: bool
    required_collections: list[str]
    stale_collections: list[str]
    reasons: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def freshness_receipt_path(ssd_path: Path | str) -> Path:
    return Path(ssd_path) / "indexes" / FRESHNESS_RECEIPT_FILENAME


def _safe_count(collection: Any) -> int:
    if collection is None:
        return 0
    try:
        return int(collection.count())
    except Exception:
        return 0


def _collection_status(collection: Any, count: int) -> str:
    if collection is None:
        return "missing"
    if count <= 0:
        return "empty"
    return "indexed"


def _digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _metadata_path(metadata: Any) -> str:
    if not isinstance(metadata, Mapping):
        return ""
    for key in ("path", "file_path", "filepath", "source_path", "source"):
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            return _norm_path(value)
    return ""


def _collection_embedding_metadata(collection: Any) -> dict[str, str]:
    metadata = getattr(collection, "metadata", None)
    if not isinstance(metadata, Mapping):
        return {
            "embedding_backend": "",
            "embedding_model": "",
            "embedding_space_fingerprint": "",
        }
    return {
        key: str(metadata.get(key) or "")
        for key in (
            "embedding_backend",
            "embedding_model",
            "embedding_space_fingerprint",
        )
    }


def _unavailable_snapshot_manifest(verification: str) -> dict[str, str]:
    return {
        "source_manifest_digest": "",
        "indexed_paths_digest": "",
        "removed_paths_digest": _digest([]),
        "embedding_backend": "",
        "embedding_model": "",
        "embedding_space_fingerprint": "",
        "verification": verification,
    }


def _empty_snapshot_manifest(name: str) -> dict[str, str]:
    return {
        "source_manifest_digest": _digest(
            {"collection": name, "ids": [], "paths": []}
        ),
        "indexed_paths_digest": _digest([]),
        "removed_paths_digest": _digest([]),
        "embedding_backend": "",
        "embedding_model": "",
        "embedding_space_fingerprint": "",
        "verification": "EMPTY",
    }


def _snapshot_list(snapshot: Any, key: str) -> list[Any]:
    value = snapshot.get(key, []) if isinstance(snapshot, Mapping) else []
    if hasattr(value, "tolist"):
        value = value.tolist()
    return value if isinstance(value, list) else []


def _canonical_snapshot_value(value: Any) -> Any:
    if hasattr(value, "tolist"):
        value = value.tolist()
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non_finite_snapshot_value")
        return value
    if isinstance(value, Mapping):
        return {
            str(key): _canonical_snapshot_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_canonical_snapshot_value(item) for item in value]
    raise TypeError(f"unsupported_snapshot_value:{type(value).__name__}")


def _collection_snapshot_manifest(
    collection: Any,
    *,
    name: str,
    count: int,
) -> dict[str, str]:
    """Return deterministic per-collection proof fields.

    A count-only collection handle is not enough evidence that a collection was
    refreshed. Consumers that depend on freshness require this manifest proof.
    """

    if collection is None:
        return _unavailable_snapshot_manifest("MISSING")
    if count <= 0:
        return _empty_snapshot_manifest(name)

    try:
        snapshot = collection.get(include=["documents", "metadatas", "embeddings"])
    except Exception:
        return _unavailable_snapshot_manifest("UNVERIFIED")

    ids = _snapshot_list(snapshot, "ids")
    documents = _snapshot_list(snapshot, "documents")
    metadatas = _snapshot_list(snapshot, "metadatas")
    embeddings = _snapshot_list(snapshot, "embeddings")
    if (
        len(ids) != count
        or len(documents) != count
        or len(metadatas) != count
        or len(embeddings) != count
        or len({str(item) for item in ids}) != count
    ):
        return _unavailable_snapshot_manifest("UNVERIFIED")
    try:
        rows = sorted(
            (
                {
                    "id": str(item_id),
                    "document": _canonical_snapshot_value(document),
                    "metadata": _canonical_snapshot_value(metadata),
                    "embedding": _canonical_snapshot_value(embedding),
                }
                for item_id, document, metadata, embedding in zip(
                    ids,
                    documents,
                    metadatas,
                    embeddings,
                )
            ),
            key=lambda row: row["id"],
        )
    except (TypeError, ValueError):
        return _unavailable_snapshot_manifest("UNVERIFIED")
    indexed_paths = sorted(
        path for path in (_metadata_path(metadata) for metadata in metadatas) if path
    )
    source_manifest = {
        "collection": name,
        "count": count,
        "rows": rows,
        "paths": indexed_paths,
    }
    embedding = _collection_embedding_metadata(collection)

    return {
        "source_manifest_digest": _digest(source_manifest),
        "indexed_paths_digest": _digest(indexed_paths),
        "removed_paths_digest": _digest([]),
        **embedding,
        "verification": "PASS" if ids else "UNVERIFIED",
    }


def _resolve_git_dir(repo_root: Path) -> Path | None:
    git_entry = repo_root / ".git"
    if git_entry.is_dir():
        return git_entry
    if git_entry.is_file():
        try:
            text = git_entry.read_text(encoding="utf-8").strip()
        except Exception:
            return None
        prefix = "gitdir:"
        if text.lower().startswith(prefix):
            raw_path = text[len(prefix):].strip()
            git_dir = Path(raw_path)
            if not git_dir.is_absolute():
                git_dir = (repo_root / git_dir).resolve()
            return git_dir
    return None


def _git_ref_roots(git_dir: Path) -> list[Path]:
    """Return worktree-local then shared Git roots for symbolic refs."""
    roots = [git_dir]
    common_file = git_dir / "commondir"
    try:
        common_value = common_file.read_text(encoding="utf-8").strip()
    except OSError:
        return roots
    if not common_value:
        return roots
    common_dir = Path(common_value)
    if not common_dir.is_absolute():
        common_dir = (git_dir / common_dir).resolve(strict=False)
    if common_dir not in roots:
        roots.append(common_dir)
    return roots


def read_git_head_sha(repo_root: Path | str) -> str:
    """Read the current git HEAD SHA without invoking git."""

    root = Path(repo_root)
    git_dir = _resolve_git_dir(root)
    if git_dir is None:
        return "unknown"
    head_path = git_dir / "HEAD"
    try:
        head = head_path.read_text(encoding="utf-8").strip()
    except Exception:
        return "unknown"
    ref_prefix = "ref:"
    if not head.startswith(ref_prefix):
        return head or "unknown"
    ref_name = head[len(ref_prefix):].strip()
    for ref_root in _git_ref_roots(git_dir):
        ref_path = ref_root / ref_name
        try:
            sha = ref_path.read_text(encoding="utf-8").strip()
            if sha:
                return sha
        except OSError:
            pass
        packed_refs = ref_root / "packed-refs"
        try:
            packed_lines = packed_refs.read_text(encoding="utf-8").splitlines()
        except OSError:
            packed_lines = []
        for line in packed_lines:
            if not line or line.startswith("#") or line.startswith("^"):
                continue
            parts = line.split(" ", 1)
            if len(parts) == 2 and parts[1].strip() == ref_name:
                return parts[0].strip()
    return "unknown"


def _receipt_from_mapping(value: Mapping[str, Any]) -> HoloIndexFreshnessReceipt:
    return HoloIndexFreshnessReceipt(
        schema_version=str(value.get("schema_version", "")),
        generated_at=str(value.get("generated_at", "")),
        repo_root=str(value.get("repo_root", "")),
        repo_head_sha=str(value.get("repo_head_sha", "")),
        ssd_path=str(value.get("ssd_path", "")),
        source=str(value.get("source", "")),
        generation_id=str(value.get("generation_id", "")),
        base_generation_id=str(value.get("base_generation_id", "")),
        collections=[
            CollectionFreshness(**entry)
            for entry in value.get("collections", [])
            if isinstance(entry, Mapping)
        ],
    )


def _collection_handle(holo: Any, name: str, attr_name: str) -> Any:
    collection = getattr(holo, attr_name, None)
    if collection is not None or name != "navigation_vocabulary":
        return collection
    client = getattr(holo, "client", None)
    if client is None:
        return None
    try:
        return client.get_collection(name)
    except Exception:
        return None


def _persisted_collection_handle(holo: Any, name: str, attr_name: str) -> Any:
    """Reopen persisted state for verification without replacing write handles."""

    client = getattr(holo, "client", None)
    if client is not None:
        try:
            return client.get_collection(name, embedding_function=None)
        except Exception:
            return None
    return getattr(holo, attr_name, None)


def _unrefreshed_collection_entry(name: str, collection: Any) -> CollectionFreshness:
    return CollectionFreshness(
        name=name,
        count=_safe_count(collection),
        status="unverified",
        source="unrefreshed",
        repo_head_sha="",
        last_indexed_at="",
        removed_paths_digest=_digest([]),
        verification="UNVERIFIED",
        proof_kind="unverified",
    )


def _refreshed_collection_entry(
    *,
    holo: Any,
    name: str,
    collection: Any,
    source: str,
    head_sha: str,
    generated: str,
    source_manifest: str,
    source_scope_id: str,
    source_policy_digest: str,
) -> CollectionFreshness:
    count = _safe_count(collection)
    manifest = _collection_snapshot_manifest(collection, name=name, count=count)
    runtime_backend = str(getattr(holo, "index_embedding_backend", "") or "")
    runtime_model = str(getattr(holo, "index_embedding_model_id", "") or "")
    runtime_fingerprint = str(
        getattr(holo, "index_embedding_space_fingerprint", "") or ""
    )
    stored_fingerprint = manifest["embedding_space_fingerprint"]
    runtime_declared = hasattr(holo, "index_embedding_space_fingerprint")
    if runtime_declared and (
        not runtime_fingerprint
        or stored_fingerprint != runtime_fingerprint
        or manifest["embedding_backend"] != runtime_backend
        or manifest["embedding_model"] != runtime_model
    ):
        stored_fingerprint = ""
    expected_scope_id = canonical_source_scope_id(name)
    canonical_scope = not expected_scope_id or source_scope_id == expected_scope_id
    return CollectionFreshness(
        name=name,
        count=count,
        status=_collection_status(collection, count),
        source=source,
        repo_head_sha=head_sha,
        last_indexed_at=generated,
        source_manifest_digest=source_manifest or manifest["source_manifest_digest"],
        indexed_paths_digest=manifest["indexed_paths_digest"],
        removed_paths_digest=manifest["removed_paths_digest"],
        embedding_backend=manifest["embedding_backend"],
        embedding_model=manifest["embedding_model"],
        embedding_space_fingerprint=stored_fingerprint,
        verification=manifest["verification"],
        proof_kind=(
            "complete_source_manifest"
            if source_manifest and canonical_scope
            else "snapshot_only"
        ),
        source_scope_id=source_scope_id,
        source_policy_digest=source_policy_digest,
        collection_snapshot_digest=manifest["source_manifest_digest"],
    )


def _verified_carried_entry(
    previous: CollectionFreshness,
    *,
    head_sha: str,
    evidence: Any,
) -> CollectionFreshness:
    return replace(
        previous,
        source="verified_carry_forward",
        repo_head_sha=head_sha,
        proof_kind="verified_unchanged_source_manifest",
        source_policy_digest=str(
            getattr(evidence, "source_policy_digest", "") or ""
        ),
        carried_from_repo_head_sha=str(
            getattr(evidence, "carried_from_repo_head_sha", "") or ""
        ),
        carried_from_generation_id=str(
            getattr(evidence, "carried_from_generation_id", "") or ""
        ),
        carry_forward_evidence_digest=str(
            getattr(evidence, "evidence_digest", "") or ""
        ),
    )


def _build_collection_entries(
    holo: Any,
    *,
    refreshed: set[str] | None,
    previous_by_name: Mapping[str, CollectionFreshness],
    source: str,
    head_sha: str,
    generated: str,
    source_manifests: Mapping[str, str],
    source_scopes: Mapping[str, str],
    source_policy_digests: Mapping[str, str],
    carry_forward_evidence: Mapping[str, Any],
) -> list[CollectionFreshness]:
    entries: list[CollectionFreshness] = []
    for name, attr_name in COLLECTION_ATTRS.items():
        collection = _collection_handle(holo, name, attr_name)
        if refreshed is not None and name not in refreshed:
            previous = previous_by_name.get(name)
            evidence = carry_forward_evidence.get(name)
            entries.append(
                _verified_carried_entry(
                    previous,
                    head_sha=head_sha,
                    evidence=evidence,
                )
                if previous is not None and evidence is not None
                else previous
                or _unrefreshed_collection_entry(name, collection)
            )
            continue
        entries.append(
            _refreshed_collection_entry(
                holo=holo,
                name=name,
                collection=collection,
                source=source,
                head_sha=head_sha,
                generated=generated,
                source_manifest=source_manifests.get(name, ""),
                source_scope_id=source_scopes.get(name, ""),
                source_policy_digest=source_policy_digests.get(name, ""),
            )
        )
    return entries


def _receipt_generation_id(
    head_sha: str,
    entries: Iterable[CollectionFreshness],
    *,
    generated_at: str = "",
    base_generation_id: str = "",
    repo_root: str = "",
    ssd_path: str = "",
    source: str = "",
) -> str:
    return _digest(
        {
            "schema_version": SCHEMA_VERSION,
            "generated_at": generated_at,
            "repo_head_sha": head_sha,
            "base_generation_id": base_generation_id,
            "repo_root": repo_root,
            "ssd_path": ssd_path,
            "source": source,
            "collections": [asdict(entry) for entry in entries],
        }
    )


def _normalized_refresh_evidence(
    refresh_source_manifests: Mapping[str, str] | None,
    refresh_source_scopes: Mapping[str, str] | None,
) -> tuple[dict[str, str], dict[str, str]]:
    manifests = {
        str(name): str(digest)
        for name, digest in (refresh_source_manifests or {}).items()
        if str(name) and str(digest)
    }
    scopes = {
        str(name): str(scope)
        for name, scope in (refresh_source_scopes or {}).items()
        if str(name) and str(scope)
    }
    return manifests, scopes


def _coerce_build_base_receipt(
    base_receipt: HoloIndexFreshnessReceipt | Mapping[str, Any] | None,
) -> HoloIndexFreshnessReceipt | None:
    if not isinstance(base_receipt, Mapping):
        return base_receipt
    try:
        return _receipt_from_mapping(base_receipt)
    except (TypeError, ValueError):
        return None


def _freshness_build_state(
    holo: Any,
    *,
    repo_root: Path | str,
    source: str,
    generated_at: str | None,
    repo_head_sha: str | None,
    refreshed_collections: Iterable[str] | None,
    base_receipt: HoloIndexFreshnessReceipt | Mapping[str, Any] | None,
    refresh_source_manifests: Mapping[str, str] | None,
    refresh_source_scopes: Mapping[str, str] | None,
    refresh_source_policy_digests: Mapping[str, str] | None,
    carry_forward_evidence: Mapping[str, Any] | None,
) -> tuple[
    str,
    str,
    HoloIndexFreshnessReceipt | None,
    list[CollectionFreshness],
]:
    generated = generated_at or utc_now_iso()
    head_sha = repo_head_sha or read_git_head_sha(repo_root)
    refreshed = None if refreshed_collections is None else set(refreshed_collections)
    unknown = set() if refreshed is None else refreshed.difference(ALL_COLLECTIONS)
    if unknown:
        raise ValueError(f"unknown HoloIndex collections: {sorted(unknown)}")
    manifests, scopes = _normalized_refresh_evidence(
        refresh_source_manifests,
        refresh_source_scopes,
    )
    policies = {
        str(name): str(digest)
        for name, digest in (refresh_source_policy_digests or {}).items()
        if str(name) and str(digest)
    }
    base = _coerce_build_base_receipt(base_receipt)
    if base is not None and not freshness_receipt_integrity_ok(base):
        raise ValueError("invalid base freshness receipt integrity")
    previous = {entry.name: entry for entry in (base.collections if base else [])}
    collections = _build_collection_entries(
        holo,
        refreshed=refreshed,
        previous_by_name=previous,
        source=source,
        head_sha=head_sha,
        generated=generated,
        source_manifests=manifests,
        source_scopes=scopes,
        source_policy_digests=policies,
        carry_forward_evidence=dict(carry_forward_evidence or {}),
    )
    return generated, head_sha, base, collections


def freshness_receipt_integrity_ok(
    receipt: HoloIndexFreshnessReceipt | None,
) -> bool:
    """Verify schema, uniqueness, and the complete generation payload."""

    if receipt is None or receipt.schema_version != SCHEMA_VERSION:
        return False
    names = [entry.name for entry in receipt.collections]
    return bool(
        receipt.generation_id
        and len(names) == len(set(names))
        and set(names) == set(ALL_COLLECTIONS)
        and all(
            entry.schema_version == COLLECTION_SCHEMA_VERSION
            for entry in receipt.collections
        )
        and receipt.generation_id
        == _receipt_generation_id(
            receipt.repo_head_sha,
            receipt.collections,
            generated_at=receipt.generated_at,
            base_generation_id=receipt.base_generation_id,
            repo_root=receipt.repo_root,
            ssd_path=receipt.ssd_path,
            source=receipt.source,
        )
    )


def collection_snapshot_matches_entry(
    holo: Any,
    name: str,
    entry: CollectionFreshness,
) -> bool:
    """Re-prove that an untouched collection still matches its receipt."""

    attr_name = COLLECTION_ATTRS.get(name)
    if not attr_name:
        return False
    collection = _persisted_collection_handle(holo, name, attr_name)
    count = _safe_count(collection)
    manifest = _collection_snapshot_manifest(collection, name=name, count=count)
    return bool(
        count == entry.count
        and manifest["verification"] == "PASS"
        and manifest["source_manifest_digest"] == entry.collection_snapshot_digest
        and manifest["indexed_paths_digest"] == entry.indexed_paths_digest
        and manifest["removed_paths_digest"] == entry.removed_paths_digest
        and manifest["embedding_backend"] == entry.embedding_backend
        and manifest["embedding_model"] == entry.embedding_model
        and manifest["embedding_space_fingerprint"]
        == entry.embedding_space_fingerprint
    )


def build_freshness_receipt(
    holo: Any,
    *,
    ssd_path: Path | str,
    repo_root: Path | str,
    source: str,
    generated_at: str | None = None,
    repo_head_sha: str | None = None,
    refreshed_collections: Iterable[str] | None = None,
    base_receipt: HoloIndexFreshnessReceipt | Mapping[str, Any] | None = None,
    refresh_source_manifests: Mapping[str, str] | None = None,
    refresh_source_scopes: Mapping[str, str] | None = None,
    refresh_source_policy_digests: Mapping[str, str] | None = None,
    _carry_forward_evidence: Mapping[str, Any] | None = None,
) -> HoloIndexFreshnessReceipt:
    """Build a truthful receipt from current and previously proven state.

    Omitting refreshed_collections preserves the original full-snapshot
    behaviour. A scoped maintenance caller must pass the collections it
    actually refreshed. Untouched entries are carried forward from the base
    receipt with their original repository SHA and proof; when no prior proof
    exists they are emitted as unverified instead of falsely stamped current.
    """

    generated, head_sha, base_receipt, collections = _freshness_build_state(
        holo,
        repo_root=repo_root,
        source=source,
        generated_at=generated_at,
        repo_head_sha=repo_head_sha,
        refreshed_collections=refreshed_collections,
        base_receipt=base_receipt,
        refresh_source_manifests=refresh_source_manifests,
        refresh_source_scopes=refresh_source_scopes,
        refresh_source_policy_digests=refresh_source_policy_digests,
        carry_forward_evidence=_carry_forward_evidence,
    )
    base_generation_id = base_receipt.generation_id if base_receipt is not None else ""
    generation_id = _receipt_generation_id(
        head_sha,
        collections,
        generated_at=generated,
        base_generation_id=base_generation_id,
        repo_root=str(Path(repo_root)),
        ssd_path=str(Path(ssd_path)),
        source=source,
    )

    return HoloIndexFreshnessReceipt(
        schema_version=SCHEMA_VERSION,
        generated_at=generated,
        repo_root=str(Path(repo_root)),
        repo_head_sha=head_sha,
        ssd_path=str(Path(ssd_path)),
        source=source,
        generation_id=generation_id,
        base_generation_id=base_generation_id,
        collections=collections,
    )


def _coerce_base_receipt(
    value: HoloIndexFreshnessReceipt | Mapping[str, Any] | None,
) -> HoloIndexFreshnessReceipt | None:
    if value is None or isinstance(value, HoloIndexFreshnessReceipt):
        receipt = value
    elif isinstance(value, Mapping):
        try:
            receipt = _receipt_from_mapping(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("malformed base freshness receipt") from exc
    else:
        raise TypeError("base_receipt must be a freshness receipt, mapping, or None")

    if receipt is None:
        return None
    if receipt.schema_version != SCHEMA_VERSION:
        raise ValueError("unsupported base freshness receipt schema")
    names = [entry.name for entry in receipt.collections]
    if len(names) != len(set(names)):
        raise ValueError("duplicate collection proof in base freshness receipt")
    return receipt


def _planned_collection_set(planned_collections: Iterable[str]) -> set[str]:
    if isinstance(planned_collections, (str, bytes)):
        raise ValueError("planned_collections must be a collection of names")
    planned = set(planned_collections)
    if not planned:
        raise ValueError("planned_collections must not be empty")
    unknown = planned.difference(ALL_COLLECTIONS)
    if unknown:
        raise ValueError(f"unknown HoloIndex collections: {sorted(unknown)}")
    return planned


def _maintenance_invalidation_entry(
    name: str,
    *,
    planned: set[str],
    previous: CollectionFreshness | None,
    source: str,
) -> CollectionFreshness:
    if name in planned:
        return CollectionFreshness(
            name=name,
            count=0,
            status="maintenance_in_progress",
            source=source,
            repo_head_sha="",
            last_indexed_at="",
            verification="IN_PROGRESS",
            proof_kind="invalidated",
        )
    if previous is not None:
        return previous
    return CollectionFreshness(
        name=name,
        count=0,
        status="unverified",
        source="unrefreshed",
        repo_head_sha="",
        last_indexed_at="",
        verification="UNVERIFIED",
        proof_kind="unverified",
    )


def build_maintenance_invalidation(
    planned_collections: Iterable[str],
    *,
    ssd_path: Path | str,
    repo_root: Path | str,
    base_receipt: HoloIndexFreshnessReceipt | Mapping[str, Any] | None,
    source: str = "maintenance_in_progress",
    generated_at: str | None = None,
    repo_head_sha: str | None = None,
) -> HoloIndexFreshnessReceipt:
    """Build a fail-closed receipt before maintenance writes begin.

    Planned collection proof is erased. Unplanned proof is copied unchanged
    from the prior receipt; without prior proof, an entry is unverified.
    """

    planned = _planned_collection_set(planned_collections)
    base = _coerce_base_receipt(base_receipt)
    previous_by_name = {
        entry.name: entry for entry in (base.collections if base is not None else [])
    }
    generated = generated_at or utc_now_iso()
    head_sha = repo_head_sha or read_git_head_sha(repo_root)
    entries = [
        _maintenance_invalidation_entry(
            name,
            planned=planned,
            previous=previous_by_name.get(name),
            source=source,
        )
        for name in ALL_COLLECTIONS
    ]
    base_generation_id = base.generation_id if base is not None else ""
    generation_id = _receipt_generation_id(
        head_sha,
        entries,
        generated_at=generated,
        base_generation_id=base_generation_id,
        repo_root=str(Path(repo_root)),
        ssd_path=str(Path(ssd_path)),
        source=source,
    )
    return HoloIndexFreshnessReceipt(
        schema_version=SCHEMA_VERSION,
        generated_at=generated,
        repo_root=str(Path(repo_root)),
        repo_head_sha=head_sha,
        ssd_path=str(Path(ssd_path)),
        source=source,
        generation_id=generation_id,
        base_generation_id=base_generation_id,
        collections=entries,
    )


def _fsync_parent_directory(parent: Path) -> None:
    if os.name == "nt":
        return
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    directory_fd = os.open(str(parent), flags)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def write_freshness_receipt(receipt: HoloIndexFreshnessReceipt, path: Path | str) -> None:
    """Atomically publish a durable freshness receipt."""

    receipt_path = Path(path)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(
        dir=str(receipt_path.parent),
        prefix=f".{receipt_path.name}.",
        suffix=".tmp",
    )
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(receipt.to_json() + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, receipt_path)
        _fsync_parent_directory(receipt_path.parent)
    except BaseException:
        try:
            os.close(file_descriptor)
        except OSError:
            pass
        try:
            Path(temporary_name).unlink()
        except FileNotFoundError:
            pass
        raise


def publish_maintenance_invalidation(
    receipt_path: Path | str,
    planned_collections: Iterable[str],
    *,
    ssd_path: Path | str,
    repo_root: Path | str,
    base_receipt: HoloIndexFreshnessReceipt | Mapping[str, Any] | None,
    source: str = "maintenance_in_progress",
    generated_at: str | None = None,
    repo_head_sha: str | None = None,
) -> HoloIndexFreshnessReceipt:
    """Build and atomically publish the pre-maintenance invalidation receipt."""

    receipt = build_maintenance_invalidation(
        planned_collections,
        ssd_path=ssd_path,
        repo_root=repo_root,
        base_receipt=base_receipt,
        source=source,
        generated_at=generated_at,
        repo_head_sha=repo_head_sha,
    )
    write_freshness_receipt(receipt, receipt_path)
    return receipt


def load_freshness_receipt(path: Path | str) -> HoloIndexFreshnessReceipt:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    collections = [CollectionFreshness(**entry) for entry in data.get("collections", [])]
    return HoloIndexFreshnessReceipt(
        schema_version=data.get("schema_version", ""),
        generated_at=data.get("generated_at", ""),
        repo_root=data.get("repo_root", ""),
        repo_head_sha=data.get("repo_head_sha", ""),
        ssd_path=data.get("ssd_path", ""),
        source=data.get("source", ""),
        generation_id=data.get("generation_id", ""),
        base_generation_id=data.get("base_generation_id", ""),
        collections=collections,
    )


def _norm_path(path: str | Path) -> str:
    text = str(path).replace("\\", "/").strip()
    while text.startswith("./"):
        text = text[2:]
    return text


def collections_for_path(path: str | Path) -> set[str]:
    """Return collections that should be fresh for a changed path."""

    p = _norm_path(path)
    lower = p.lower()
    name = Path(p).name
    collections: set[str] = set()

    if not p or p.startswith("../") or p.startswith("/"):
        return collections

    if (
        p.startswith("WSP_framework/src/")
        and name.startswith("WSP_")
        and lower.endswith(".md")
    ):
        collections.add("navigation_wsp")
        return collections
    if p.startswith("WSP_knowledge/docs/Papers/"):
        collections.add("navigation_knowledge")
        return collections
    if p.startswith("docs/0102_session_briefings/") or name in {
        "ACTIVE_SLICE_LEDGER.md",
        "work_ledger.schema.json",
    }:
        collections.add("navigation_work_ledger")
    if name == "WSP_Test_Registry.json":
        collections.add("navigation_tests")
        return collections
    if name == "SKILLz.md":
        collections.add("navigation_skills")
        if p.startswith("modules/"):
            collections.add("navigation_docs")
    if "/tests/" in p or name.startswith("test_"):
        collections.add("navigation_tests")
    if lower.endswith("navigation.py") or lower.endswith(
        (".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".html", ".css")
    ):
        collections.add("navigation_code")
    if lower.endswith(".py") and p.startswith(("modules/", "scripts/", "holo_index/")):
        collections.add("navigation_symbols")
    if lower.endswith(".md") and p.startswith(
        ("modules/", "docs/", "holo_index/docs/", "WSP_framework/docs/")
    ):
        collections.add("navigation_docs")

    return collections


def collections_for_changed_paths(paths: Iterable[str | Path]) -> list[str]:
    collections: set[str] = set()
    for path in paths:
        collections.update(collections_for_path(path))
    return sorted(collections)


def _evaluation_receipt(
    value: HoloIndexFreshnessReceipt | Mapping[str, Any],
) -> HoloIndexFreshnessReceipt | None:
    if isinstance(value, HoloIndexFreshnessReceipt):
        return value
    if not isinstance(value, Mapping):
        return None
    try:
        return _receipt_from_mapping(value)
    except Exception:
        return None


def _collection_freshness_reasons(
    name: str,
    entry: CollectionFreshness,
    *,
    expected_repo_head_sha: str | None,
    entry_generation_id: str,
) -> list[str]:
    reasons: list[str] = []
    if entry.status != "indexed" or entry.count <= 0:
        reasons.append(f"collection_not_indexed:{name}")
    if entry.verification != "PASS":
        reasons.append(f"collection_verification_not_pass:{name}")
    allowed_proofs = {
        "complete_source_manifest",
        "verified_unchanged_source_manifest",
    }
    if entry.proof_kind not in allowed_proofs:
        reasons.append(f"collection_source_proof_incomplete:{name}")
    required_digests = {
        "source_manifest": entry.source_manifest_digest,
        "indexed_paths": entry.indexed_paths_digest,
        "removed_paths": entry.removed_paths_digest,
        "source_policy": entry.source_policy_digest,
        "collection_snapshot": entry.collection_snapshot_digest,
    }
    for field_name, digest in required_digests.items():
        if not DIGEST_PATTERN.fullmatch(digest):
            reasons.append(f"collection_{field_name}_digest_invalid:{name}")
    if entry.proof_kind == "verified_unchanged_source_manifest" and not all(
        (
            entry.source_policy_digest,
            entry.carried_from_repo_head_sha,
            entry.carried_from_generation_id,
            entry.carry_forward_evidence_digest,
            entry.collection_snapshot_digest,
        )
    ):
        reasons.append(f"collection_carry_forward_proof_incomplete:{name}")
    if entry.proof_kind == "verified_unchanged_source_manifest":
        if entry.carried_from_generation_id != entry_generation_id:
            reasons.append(f"collection_carry_forward_lineage_mismatch:{name}")
        if (
            not SHA_PATTERN.fullmatch(entry.carried_from_repo_head_sha)
            or not DIGEST_PATTERN.fullmatch(entry.source_manifest_digest)
            or not DIGEST_PATTERN.fullmatch(entry.source_policy_digest)
            or not DIGEST_PATTERN.fullmatch(entry.collection_snapshot_digest)
        ):
            reasons.append(f"collection_carry_forward_format_invalid:{name}")
        expected_evidence = carry_forward_evidence_digest(
            collection_name=name,
            source_manifest_digest=entry.source_manifest_digest,
            source_policy_digest=entry.source_policy_digest,
            carried_from_repo_head_sha=entry.carried_from_repo_head_sha,
            carried_from_generation_id=entry.carried_from_generation_id,
            current_repo_head_sha=entry.repo_head_sha,
        )
        if entry.carry_forward_evidence_digest != expected_evidence:
            reasons.append(f"collection_carry_forward_evidence_invalid:{name}")
    expected_scope_id = canonical_source_scope_id(name)
    if expected_scope_id and entry.source_scope_id != expected_scope_id:
        reasons.append(f"collection_source_scope_mismatch:{name}")
    if not entry.source_manifest_digest:
        reasons.append(f"collection_manifest_missing:{name}")
    if not entry.indexed_paths_digest:
        reasons.append(f"collection_indexed_paths_missing:{name}")
    if expected_repo_head_sha and entry.repo_head_sha != expected_repo_head_sha:
        reasons.append(f"stale_collection_sha:{name}")
    return reasons


def _duplicate_required_collections(
    receipt: HoloIndexFreshnessReceipt,
    required: Iterable[str],
) -> set[str]:
    seen_names: set[str] = set()
    duplicate_names: set[str] = set()
    for entry in receipt.collections:
        if entry.name in seen_names:
            duplicate_names.add(entry.name)
        seen_names.add(entry.name)
    return set(required).intersection(duplicate_names)


def _required_collection_failures(
    receipt: HoloIndexFreshnessReceipt,
    required: Iterable[str],
    *,
    expected_repo_head_sha: str | None,
) -> tuple[set[str], list[str]]:
    stale: set[str] = set()
    reasons: list[str] = []
    by_name = {entry.name: entry for entry in receipt.collections}
    for name in required:
        entry = by_name.get(name)
        if entry is None:
            stale.add(name)
            reasons.append(f"missing_collection_receipt:{name}")
            continue
        entry_reasons = _collection_freshness_reasons(
            name,
            entry,
            expected_repo_head_sha=expected_repo_head_sha,
            entry_generation_id=receipt.base_generation_id,
        )
        if entry_reasons:
            stale.add(name)
            reasons.extend(entry_reasons)
    return stale, reasons


def evaluate_freshness_for_paths(
    receipt: HoloIndexFreshnessReceipt | Mapping[str, Any] | None,
    changed_paths: Iterable[str | Path],
    *,
    expected_repo_head_sha: str | None = None,
) -> FreshnessCheck:
    """Fail-closed freshness check for write-sensitive consumers."""

    required = collections_for_changed_paths(changed_paths)
    if receipt is None:
        return FreshnessCheck(False, required, required, ["missing_freshness_receipt"])

    receipt = _evaluation_receipt(receipt)
    if receipt is None:
        return FreshnessCheck(False, required, required, ["malformed_freshness_receipt"])

    reasons: list[str] = []
    stale: set[str] = set()
    if receipt.schema_version != SCHEMA_VERSION:
        reasons.append("unsupported_freshness_receipt_schema")
        stale.update(required)
    if not freshness_receipt_integrity_ok(receipt):
        reasons.append("invalid_freshness_receipt_integrity")
        stale.update(required)
    if required and not receipt.generation_id:
        reasons.append("missing_holoindex_generation_id")
        stale.update(required)
    if expected_repo_head_sha and receipt.repo_head_sha != expected_repo_head_sha:
        reasons.append("stale_repo_head_sha")
        stale.update(required)

    for name in sorted(_duplicate_required_collections(receipt, required)):
        stale.add(name)
        reasons.append(f"duplicate_collection_receipt:{name}")
    collection_stale, collection_reasons = _required_collection_failures(
        receipt,
        required,
        expected_repo_head_sha=expected_repo_head_sha,
    )
    stale.update(collection_stale)
    reasons.extend(collection_reasons)

    return FreshnessCheck(
        ok=not stale and not reasons,
        required_collections=required,
        stale_collections=sorted(stale),
        reasons=reasons,
    )


__all__ = [
    "ALL_COLLECTIONS",
    "BASELINE_QUERY_COLLECTIONS",
    "BASELINE_QUERY_FRESHNESS_PATHS",
    "COLLECTION_ATTRS",
    "COLLECTION_SCHEMA_VERSION",
    "CollectionFreshness",
    "FreshnessCheck",
    "FRESHNESS_RECEIPT_FILENAME",
    "HoloIndexFreshnessReceipt",
    "collection_snapshot_matches_entry",
    "SCHEMA_VERSION",
    "build_freshness_receipt",
    "build_maintenance_invalidation",
    "collections_for_changed_paths",
    "collections_for_path",
    "evaluate_freshness_for_paths",
    "freshness_receipt_path",
    "freshness_receipt_integrity_ok",
    "load_freshness_receipt",
    "publish_maintenance_invalidation",
    "read_git_head_sha",
    "write_freshness_receipt",
]
