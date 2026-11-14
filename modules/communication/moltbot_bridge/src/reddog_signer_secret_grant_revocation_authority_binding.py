"""Signed E0 topology binding for durable signer-grant revocations."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    is_sha256,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_revocation_contract import (
    SNAPSHOT_SCHEMA,
    ExpectedSignerGrantRevocationBinding,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    validate_runtime_artifact_path,
    validate_runtime_root_path,
)

BINDING_SCHEMA = "reddog-signer-grant-revocation-authority-binding.v1"
STORE_SCHEMA = "reddog-signer-grant-revocation-store.v1"


@dataclass(frozen=True)
class SignerGrantRevocationAuthorityBinding:
    policy_id: str
    snapshot_schema: str
    store_schema: str
    primary_root: str
    primary_path: str
    primary_store_id: str
    primary_durability_receipt_id: str
    witness_root: str
    witness_path: str
    witness_store_id: str
    witness_durability_receipt_id: str
    anchor_store_id: str
    anchor_durability_receipt_id: str
    anchor_state_binding_digest: str
    operation_lock_path: str

    def context_digest(self) -> str:
        return _digest({"schema_version": BINDING_SCHEMA, **asdict(self)})

    def witness_binding_digest(self) -> str:
        return _digest(
            {
                "schema_version": BINDING_SCHEMA,
                "context_digest": self.context_digest(),
                "purpose": "revocation-sequence-witness",
            }
        )

    def anchor_binding_digest(self) -> str:
        return _digest(
            {
                "schema_version": BINDING_SCHEMA,
                "context_digest": self.context_digest(),
                "purpose": "revocation-root-high-water",
            }
        )


def revocation_authority_binding_from_policy(
    policy: Mapping[str, Any], *, repo_root: Path | str,
    signer_runtime_root: Path | str,
) -> SignerGrantRevocationAuthorityBinding:
    if not isinstance(policy, Mapping):
        raise ValueError("revocation_authority_policy_invalid")
    repo = Path(repo_root).resolve()
    signer = validate_runtime_root_path(signer_runtime_root, repo_root=repo)
    primary_root = _root(policy["revocation_root"], repo, signer)
    witness_root = _root(policy["revocation_witness_root"], repo, signer)
    if _overlap(primary_root, witness_root):
        raise ValueError("revocation_authority_domains_overlap")
    primary_path = _path(policy["revocation_path"], primary_root, repo)
    witness_path = _path(policy["revocation_witness_path"], witness_root, repo)
    lock_path = _path(policy["revocation_lock_path"], primary_root, repo)
    expected_lock = primary_path.with_name(primary_path.name + ".authority.lock")
    if lock_path != expected_lock:
        raise ValueError("revocation_authority_lock_path_invalid")
    binding = SignerGrantRevocationAuthorityBinding(
        policy_id=_sha(policy["policy_id"]),
        snapshot_schema=_exact(policy["revocation_snapshot_schema"], SNAPSHOT_SCHEMA),
        store_schema=_exact(policy["revocation_store_schema"], STORE_SCHEMA),
        primary_root=str(primary_root), primary_path=str(primary_path),
        primary_store_id=_ascii(policy["revocation_store_id"]),
        primary_durability_receipt_id=_sha(
            policy["revocation_store_durability_receipt_id"]
        ),
        witness_root=str(witness_root), witness_path=str(witness_path),
        witness_store_id=_ascii(policy["revocation_witness_store_id"]),
        witness_durability_receipt_id=_sha(
            policy["revocation_witness_store_durability_receipt_id"]
        ),
        anchor_store_id=_ascii(policy["revocation_anchor_store_id"]),
        anchor_durability_receipt_id=_sha(
            policy["revocation_anchor_store_durability_receipt_id"]
        ),
        anchor_state_binding_digest=_sha(
            policy["revocation_anchor_state_binding_digest"]
        ),
        operation_lock_path=str(lock_path),
    )
    binding.context_digest()
    return binding


def expected_snapshot_binding(
    policy: Mapping[str, Any], binding: SignerGrantRevocationAuthorityBinding,
) -> ExpectedSignerGrantRevocationBinding:
    if binding.policy_id != policy.get("policy_id"):
        raise ValueError("revocation_authority_policy_binding_invalid")
    names = ExpectedSignerGrantRevocationBinding.__dataclass_fields__
    values = {
        "policy_id": policy["policy_id"], "owner_config_id": policy["owner_config_id"],
        "manifest_id": policy["manifest_id"],
        "artifact_generation_digest": policy["artifact_generation_digest"],
        "authority_principal_id": policy["revocation_authority_principal_id"],
        "authority_principal_provider": policy["revocation_authority_principal_provider"],
        "authority_public_key": policy["revocation_authority_public_key"],
        "target_signer_agent_id": policy["target_signer_agent_id"],
        "target_signer_profile_id": policy["target_signer_profile_id"],
        "target_signer_public_key": policy["target_signer_public_key"],
        "target_signer_key_epoch": policy["target_signer_key_epoch"],
        "target_signer_generation_id": policy["target_signer_generation_id"],
        "store_id": binding.primary_store_id,
        "durability_receipt_id": binding.primary_durability_receipt_id,
    }
    if set(values) != set(names):
        raise ValueError("revocation_authority_snapshot_binding_invalid")
    return ExpectedSignerGrantRevocationBinding(**values)


def _root(value: Any, repo: Path, signer: Path) -> Path:
    root = validate_runtime_root_path(value, repo_root=repo)
    if _overlap(root, signer):
        raise ValueError("revocation_authority_signer_domain_overlap")
    return root


def _path(value: Any, root: Path, repo: Path) -> Path:
    path = validate_runtime_artifact_path(value, allowed_root=root, repo_root=repo)
    if path.parent != root:
        raise ValueError("revocation_authority_path_invalid")
    return path


def _overlap(left: Path, right: Path) -> bool:
    return left == right or left in right.parents or right in left.parents


def _ascii(value: Any) -> str:
    if type(value) is not str or not value or not value.isascii() or len(value) > 1024:
        raise ValueError("revocation_authority_identity_invalid")
    return value


def _sha(value: Any) -> str:
    if not is_sha256(value):
        raise ValueError("revocation_authority_digest_invalid")
    return str(value)


def _exact(value: Any, expected: str) -> str:
    if value != expected:
        raise ValueError("revocation_authority_schema_invalid")
    return expected


def _digest(value: Mapping[str, Any]) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(raw.encode("ascii")).hexdigest()


__all__ = [
    "BINDING_SCHEMA", "STORE_SCHEMA", "SignerGrantRevocationAuthorityBinding",
    "expected_snapshot_binding", "revocation_authority_binding_from_policy",
]
