"""Root-store topology helpers for revocation service tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src import (
    reddog_signer_owner_e0_current_selection as current_selection_module,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_state import (
    RootVerifiedOutcomeAuthorityState,
)
from modules.communication.moltbot_bridge.src.reddog_sqlite_monotonic_authority_store import (
    SqliteMonotonicAuthorityStore,
)
from modules.communication.moltbot_bridge.tests import (
    test_reddog_signer_owner_controlled_e0_admission as e0,
)


def bind_selection_loader(monkeypatch: Any) -> None:
    def load(**_kwargs: object):
        capability = object()
        return capability, e0._SelectionBoundary(capability, e0._CURRENT_SELECTION)

    monkeypatch.setattr(
        current_selection_module, "load_system_service_manifest_selection", load
    )


def root_state(
    base: Path, policy: Mapping[str, Any], repo: Path
) -> RootVerifiedOutcomeAuthorityState:
    stores = []
    identities = (
        (
            policy["revocation_anchor_store_id"],
            policy["revocation_anchor_store_durability_receipt_id"],
        ),
        ("revocation-root-witness", e0.DIGEST_A),
        ("revocation-root-installation", e0.DIGEST_B),
    )
    for index, (store_id, receipt_id) in enumerate(identities):
        root = base / str(index)
        stores.append(SqliteMonotonicAuthorityStore(
            root / "authority.sqlite3", allowed_root=root, repo_root=repo,
            store_id=str(store_id), durability_receipt_id=str(receipt_id),
        ))
    return RootVerifiedOutcomeAuthorityState(
        *stores, repo_root=repo, require_root_ownership=False
    )


def witness_store(binding: Any, repo: Path) -> SqliteMonotonicAuthorityStore:
    return SqliteMonotonicAuthorityStore(
        binding.witness_path, allowed_root=binding.witness_root, repo_root=repo,
        store_id=binding.witness_store_id,
        durability_receipt_id=binding.witness_durability_receipt_id,
    )


__all__ = ["bind_selection_loader", "root_state", "witness_store"]
