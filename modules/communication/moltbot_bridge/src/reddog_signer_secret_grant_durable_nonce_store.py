"""Durable signer-grant replay state built from existing authority stores."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from modules.communication.moltbot_bridge.src.reddog_proposal_authenticity_nonce_store import (
    AtomicProposalAuthenticityNonceStore,
)
from modules.communication.moltbot_bridge.src.reddog_sqlite_monotonic_authority_store import (
    SqliteMonotonicAuthorityStore,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    is_sha256,
)


@dataclass(frozen=True)
class SignerGrantReplayStoreConfig:
    nonce_path: Path
    nonce_root: Path
    high_water_path: Path
    high_water_root: Path
    repo_root: Path
    replay_store_binding_digest: str
    replay_store_id: str
    durability_receipt_id: str


class DurableSignerSecretGrantNonceStore:
    """Consume grant nonces through MAC state plus a SQLite high-water."""

    def __init__(
        self,
        config: SignerGrantReplayStoreConfig,
        *,
        integrity_key: bytes,
        clock: Callable[[], float],
    ) -> None:
        _validate_config(config)
        _require_store_files(config)
        high_water = SqliteMonotonicAuthorityStore(
            config.high_water_path,
            allowed_root=config.high_water_root,
            repo_root=config.repo_root,
            store_id=config.replay_store_id,
            durability_receipt_id=config.durability_receipt_id,
        )
        self._store = AtomicProposalAuthenticityNonceStore(
            config.nonce_path,
            allowed_root=config.nonce_root,
            repo_root=config.repo_root,
            integrity_key=integrity_key,
            replay_store_binding_digest=config.replay_store_binding_digest,
            high_water_store=high_water,
            clock=clock,
        )
        self._config = config
        self._instance_digest = signer_grant_replay_store_instance_digest(config)

    @property
    def replay_store_binding_digest(self) -> str:
        return self._config.replay_store_binding_digest

    @property
    def replay_store_id(self) -> str:
        return self._config.replay_store_id

    @property
    def durability_receipt_id(self) -> str:
        return self._config.durability_receipt_id

    @property
    def replay_store_instance_digest(self) -> str:
        return self._instance_digest

    def consume_grant(self, grant: Mapping[str, Any]) -> bool:
        try:
            _require_store_files(self._config)
            reservation = self._store.reserve(
                str(grant["nonce"]),
                expires_at=int(grant["expires_at"]),
                subject=str(grant["grant_id"]),
            )
            if not reservation:
                return False
            self._store.commit(reservation)
            return True
        except Exception:
            return False


def _validate_config(config: object) -> None:
    if not isinstance(config, SignerGrantReplayStoreConfig):
        raise ValueError("signer_grant_replay_config_invalid")
    digests = (
        config.replay_store_binding_digest,
        config.durability_receipt_id,
    )
    if not all(type(value) is str and is_sha256(value) for value in digests):
        raise ValueError("signer_grant_replay_config_invalid")
    if (
        type(config.replay_store_id) is not str
        or not config.replay_store_id
        or not config.replay_store_id.isascii()
    ):
        raise ValueError("signer_grant_replay_config_invalid")
    nonce_root = config.nonce_root.resolve()
    high_water_root = config.high_water_root.resolve()
    if _paths_overlap(nonce_root, high_water_root):
        raise ValueError("signer_grant_replay_rollback_domains_overlap")
    if not _is_beneath(config.nonce_path.resolve(), nonce_root):
        raise ValueError("signer_grant_replay_config_invalid")
    if not _is_beneath(config.high_water_path.resolve(), high_water_root):
        raise ValueError("signer_grant_replay_config_invalid")


def _is_beneath(path: Path, root: Path) -> bool:
    return path != root and path.is_relative_to(root)


def _paths_overlap(left: Path, right: Path) -> bool:
    return left == right or left.is_relative_to(right) or right.is_relative_to(left)


def _require_store_files(config: SignerGrantReplayStoreConfig) -> None:
    if not config.nonce_path.is_file() or not config.high_water_path.is_file():
        raise ValueError("signer_grant_replay_store_not_provisioned")


def signer_grant_replay_store_instance_digest(
    config: SignerGrantReplayStoreConfig,
) -> str:
    _validate_config(config)
    payload = {
        "durability_receipt_id": config.durability_receipt_id,
        "high_water_path": str(config.high_water_path.resolve()),
        "high_water_root": str(config.high_water_root.resolve()),
        "nonce_path": str(config.nonce_path.resolve()),
        "nonce_root": str(config.nonce_root.resolve()),
        "replay_store_binding_digest": config.replay_store_binding_digest,
        "replay_store_id": config.replay_store_id,
        "repo_root": str(config.repo_root.resolve()),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


__all__ = [
    "DurableSignerSecretGrantNonceStore",
    "SignerGrantReplayStoreConfig",
    "signer_grant_replay_store_instance_digest",
]
