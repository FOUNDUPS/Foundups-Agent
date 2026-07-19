"""Canonical HoloIndex v2 freshness receipts for RedDog runtime tests."""

from __future__ import annotations

import hashlib
from pathlib import Path
from types import SimpleNamespace

from holo_index.freshness_receipt import (
    ALL_COLLECTIONS,
    COLLECTION_ATTRS,
    HoloIndexFreshnessReceipt,
    build_freshness_receipt,
)
from holo_index.source_scope import canonical_source_scope_id
from holo_index.verified_collection_carry_forward import (
    collection_source_policy_digest,
)


class _FreshCollection:
    def __init__(self, name: str) -> None:
        self.name = name
        self.metadata: dict[str, str] = {}

    def count(self) -> int:
        return 1

    def get(self, include=None):
        return {
            "ids": [f"{self.name}:fixture"],
            "documents": [f"fresh fixture for {self.name}"],
            "metadatas": [{"path": f"fixtures/{self.name}.json"}],
            "embeddings": [[1.0]],
        }


def _fixture_digest(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("ascii")).hexdigest()


def build_fresh_holoindex_receipt(
    *,
    repo_root: Path,
    head_sha: str,
    generated_at: str,
    ssd_path: Path | str = "E:/HoloIndex",
) -> HoloIndexFreshnessReceipt:
    """Build the same complete source-proof shape required by runtime."""

    collections = {name: _FreshCollection(name) for name in ALL_COLLECTIONS}
    holo = SimpleNamespace(
        **{
            attr_name: collections[name]
            for name, attr_name in COLLECTION_ATTRS.items()
        },
        index_embedding_backend="",
        index_embedding_model_id="",
        index_embedding_space_fingerprint="",
    )
    return build_freshness_receipt(
        holo,
        generated_at=generated_at,
        repo_root=repo_root,
        repo_head_sha=head_sha,
        source="ci_targeted_reindex",
        ssd_path=ssd_path,
        refreshed_collections=ALL_COLLECTIONS,
        refresh_source_manifests={
            name: _fixture_digest(f"source:{name}") for name in ALL_COLLECTIONS
        },
        refresh_source_scopes={
            name: canonical_source_scope_id(name) for name in ALL_COLLECTIONS
        },
        refresh_source_policy_digests={
            name: collection_source_policy_digest(repo_root, name)
            or _fixture_digest(f"policy:{name}")
            for name in ALL_COLLECTIONS
        },
    )


__all__ = ["build_fresh_holoindex_receipt"]
