"""HoloIndex freshness receipt helpers.

WSP 97: freshness is evidence, not an assumption. Missing receipts or missing
collection entries fail closed for write-sensitive RedDog/WRE gates.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping


SCHEMA_VERSION = "holoindex_freshness_receipt.v1"
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
    schema_version: str = "holoindex_collection_freshness.v1"
    embedding_backend: str = ""
    verification: str = "UNKNOWN"


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
        return {
            "source_manifest_digest": "",
            "indexed_paths_digest": "",
            "removed_paths_digest": _digest([]),
            "embedding_backend": "",
            "verification": "MISSING",
        }
    if count <= 0:
        return {
            "source_manifest_digest": _digest({"collection": name, "ids": [], "paths": []}),
            "indexed_paths_digest": _digest([]),
            "removed_paths_digest": _digest([]),
            "embedding_backend": "",
            "verification": "EMPTY",
        }

    try:
        snapshot = collection.get(include=["metadatas"])
    except Exception:
        return {
            "source_manifest_digest": "",
            "indexed_paths_digest": "",
            "removed_paths_digest": _digest([]),
            "embedding_backend": "",
            "verification": "UNVERIFIED",
        }

    ids = snapshot.get("ids", []) if isinstance(snapshot, Mapping) else []
    metadatas = snapshot.get("metadatas", []) if isinstance(snapshot, Mapping) else []
    if not isinstance(ids, list):
        ids = []
    if not isinstance(metadatas, list):
        metadatas = []

    indexed_paths = sorted(
        path for path in (_metadata_path(metadata) for metadata in metadatas) if path
    )
    source_manifest = {
        "collection": name,
        "count": count,
        "ids": sorted(str(item) for item in ids),
        "paths": indexed_paths,
    }
    metadata = getattr(collection, "metadata", None)
    embedding_backend = ""
    if isinstance(metadata, Mapping):
        raw_backend = metadata.get("embedding_backend") or metadata.get("embedding_model")
        if isinstance(raw_backend, str):
            embedding_backend = raw_backend

    return {
        "source_manifest_digest": _digest(source_manifest),
        "indexed_paths_digest": _digest(indexed_paths),
        "removed_paths_digest": _digest([]),
        "embedding_backend": embedding_backend,
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
    ref_path = git_dir / ref_name
    try:
        sha = ref_path.read_text(encoding="utf-8").strip()
        if sha:
            return sha
    except Exception:
        pass
    packed_refs = git_dir / "packed-refs"
    try:
        for line in packed_refs.read_text(encoding="utf-8").splitlines():
            if not line or line.startswith("#") or line.startswith("^"):
                continue
            parts = line.split(" ", 1)
            if len(parts) == 2 and parts[1].strip() == ref_name:
                return parts[0].strip()
    except Exception:
        pass
    return "unknown"


def build_freshness_receipt(
    holo: Any,
    *,
    ssd_path: Path | str,
    repo_root: Path | str,
    source: str,
    generated_at: str | None = None,
    repo_head_sha: str | None = None,
) -> HoloIndexFreshnessReceipt:
    """Build a receipt from the current HoloIndex collection handles."""

    generated = generated_at or utc_now_iso()
    head_sha = repo_head_sha or read_git_head_sha(repo_root)
    collections: list[CollectionFreshness] = []
    for name, attr_name in COLLECTION_ATTRS.items():
        collection = getattr(holo, attr_name, None)
        if collection is None and name == "navigation_vocabulary":
            client = getattr(holo, "client", None)
            if client is not None:
                try:
                    collection = client.get_collection(name)
                except Exception:
                    collection = None
        count = _safe_count(collection)
        manifest = _collection_snapshot_manifest(collection, name=name, count=count)
        collections.append(
            CollectionFreshness(
                name=name,
                count=count,
                status=_collection_status(collection, count),
                source=source,
                repo_head_sha=head_sha,
                last_indexed_at=generated,
                source_manifest_digest=manifest["source_manifest_digest"],
                indexed_paths_digest=manifest["indexed_paths_digest"],
                removed_paths_digest=manifest["removed_paths_digest"],
                embedding_backend=manifest["embedding_backend"],
                verification=manifest["verification"],
            )
        )

    generation_id = _digest(
        {
            "schema_version": SCHEMA_VERSION,
            "repo_head_sha": head_sha,
            "collections": [
                {
                    "name": entry.name,
                    "count": entry.count,
                    "status": entry.status,
                    "source_manifest_digest": entry.source_manifest_digest,
                    "indexed_paths_digest": entry.indexed_paths_digest,
                    "removed_paths_digest": entry.removed_paths_digest,
                    "verification": entry.verification,
                }
                for entry in collections
            ],
        }
    )

    return HoloIndexFreshnessReceipt(
        schema_version=SCHEMA_VERSION,
        generated_at=generated,
        repo_root=str(Path(repo_root)),
        repo_head_sha=head_sha,
        ssd_path=str(Path(ssd_path)),
        source=source,
        generation_id=generation_id,
        base_generation_id="",
        collections=collections,
    )


def write_freshness_receipt(receipt: HoloIndexFreshnessReceipt, path: Path | str) -> None:
    receipt_path = Path(path)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(receipt.to_json() + "\n", encoding="utf-8")


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

    if p.startswith("WSP_framework/src/") and name.startswith("WSP_") and lower.endswith(".md"):
        collections.add("navigation_wsp")
    elif p.startswith("WSP_knowledge/docs/Papers/"):
        collections.add("navigation_knowledge")
    elif p.startswith("docs/0102_session_briefings/") or name in {
        "ACTIVE_SLICE_LEDGER.md",
        "work_ledger.schema.json",
    }:
        collections.add("navigation_work_ledger")
    elif name == "SKILLz.md":
        collections.add("navigation_skills")
    elif "/tests/" in p or name.startswith("test_"):
        collections.add("navigation_tests")
    elif lower.endswith("navigation.py") or lower.endswith((".js", ".ts", ".tsx", ".jsx", ".html", ".css")):
        collections.add("navigation_code")
    elif lower.endswith(".py"):
        collections.add("navigation_symbols")
    elif lower.endswith((".md", ".json", ".yaml", ".yml", ".txt")):
        collections.add("navigation_docs")

    return collections


def collections_for_changed_paths(paths: Iterable[str | Path]) -> list[str]:
    collections: set[str] = set()
    for path in paths:
        collections.update(collections_for_path(path))
    return sorted(collections)


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

    if isinstance(receipt, Mapping):
        try:
            receipt = HoloIndexFreshnessReceipt(
                schema_version=str(receipt.get("schema_version", "")),
                generated_at=str(receipt.get("generated_at", "")),
                repo_root=str(receipt.get("repo_root", "")),
                repo_head_sha=str(receipt.get("repo_head_sha", "")),
                ssd_path=str(receipt.get("ssd_path", "")),
                source=str(receipt.get("source", "")),
                generation_id=str(receipt.get("generation_id", "")),
                base_generation_id=str(receipt.get("base_generation_id", "")),
                collections=[
                    CollectionFreshness(**entry)
                    for entry in receipt.get("collections", [])
                    if isinstance(entry, Mapping)
                ],
            )
        except Exception:
            return FreshnessCheck(False, required, required, ["malformed_freshness_receipt"])

    reasons: list[str] = []
    stale: set[str] = set()
    if receipt.schema_version != SCHEMA_VERSION:
        reasons.append("unsupported_freshness_receipt_schema")
        stale.update(required)
    if required and not receipt.generation_id:
        reasons.append("missing_holoindex_generation_id")
        stale.update(required)
    if expected_repo_head_sha and receipt.repo_head_sha != expected_repo_head_sha:
        reasons.append("stale_repo_head_sha")
        stale.update(required)

    by_name = {entry.name: entry for entry in receipt.collections}
    for name in required:
        entry = by_name.get(name)
        if entry is None:
            stale.add(name)
            reasons.append(f"missing_collection_receipt:{name}")
            continue
        if entry.status != "indexed" or entry.count <= 0:
            stale.add(name)
            reasons.append(f"collection_not_indexed:{name}")
        if entry.verification != "PASS":
            stale.add(name)
            reasons.append(f"collection_verification_not_pass:{name}")
        if not entry.source_manifest_digest:
            stale.add(name)
            reasons.append(f"collection_manifest_missing:{name}")
        if not entry.indexed_paths_digest:
            stale.add(name)
            reasons.append(f"collection_indexed_paths_missing:{name}")
        if expected_repo_head_sha and entry.repo_head_sha != expected_repo_head_sha:
            stale.add(name)
            reasons.append(f"stale_collection_sha:{name}")

    return FreshnessCheck(
        ok=not stale and not reasons,
        required_collections=required,
        stale_collections=sorted(stale),
        reasons=reasons,
    )


__all__ = [
    "ALL_COLLECTIONS",
    "COLLECTION_ATTRS",
    "CollectionFreshness",
    "FreshnessCheck",
    "FRESHNESS_RECEIPT_FILENAME",
    "HoloIndexFreshnessReceipt",
    "SCHEMA_VERSION",
    "build_freshness_receipt",
    "collections_for_changed_paths",
    "collections_for_path",
    "evaluate_freshness_for_paths",
    "freshness_receipt_path",
    "load_freshness_receipt",
    "read_git_head_sha",
    "write_freshness_receipt",
]
