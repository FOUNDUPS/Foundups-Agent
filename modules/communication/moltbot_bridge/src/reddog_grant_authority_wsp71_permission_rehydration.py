"""Authenticate the grant service's WSP 71 permission artifact."""

from __future__ import annotations

import json
import time
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable, Mapping, TypeVar

from modules.communication.moltbot_bridge.src.reddog_grant_authority_service_manifest_verifier import (
    verify_current_grant_service_artifacts,
)
from modules.communication.moltbot_bridge.src.reddog_grant_authority_service_owner_binding import (
    grant_authority_owner_runtime_root,
)
from modules.communication.moltbot_bridge.src.reddog_grant_authority_wsp71_permission_contract import (
    GET_SECRET,
    MAX_RECEIPT_BYTES,
    PERMISSION_FILENAME,
    SCHEMA_VERSION,
    SECRETS_READ,
    permission_receipt_id,
    validate_permission_receipt,
    expected_permission_bindings as _expected,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    RuntimeArtifactManifestError,
    canonical_json,
    raw_digest,
)
from modules.communication.moltbot_bridge.src.reddog_signer_owner_e0_current_selection import (
    lease_validated_owner_e0_current_admission,
)
from modules.communication.moltbot_bridge.src.reddog_signer_owner_e0_policy_contract import (
    POLICY_SCHEMA_V7, POLICY_SCHEMA_V8, POLICY_SCHEMA_V9,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_root_protected_use_oracle import (
    RootAuthorizedSignerGrantRevocationOracle,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    constant_time_compare,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    secure_read_confined_bytes,
    validate_runtime_artifact_path,
)

_T = TypeVar("_T")


def authorize_current_grant_authority_wsp71_use(
    *, owner_config_path: Path | str, repo_root: Path | str,
    owner_policy: Mapping[str, Any], now_epoch: int,
    revocation_oracle: RootAuthorizedSignerGrantRevocationOracle,
    action: Callable[[], _T],
) -> _T:
    """Execute one operation while E0 and revocation authority remain current."""

    if not callable(action):
        raise RuntimeArtifactManifestError("grant_permission_action_invalid")
    repo = Path(repo_root).resolve()
    inputs = dict(owner_config_path=owner_config_path, repo_root=repo, policy=owner_policy)
    with lease_validated_owner_e0_current_admission(**inputs) as admission:
        before, receipt = _permission_state(admission, repo, owner_config_path, revocation_oracle, now_epoch)

    def guarded_action():
        # Root LOAD happens outside this lease; caller effects remain fenced.
        with lease_validated_owner_e0_current_admission(**inputs) as current:
            after, _ = _permission_state(current, repo, owner_config_path, revocation_oracle, int(time.time()))
            if before != after:
                raise RuntimeArtifactManifestError("grant_permission_authority_changed")
            result = action()
            final, _ = _permission_state(current, repo, owner_config_path, revocation_oracle, int(time.time()))
            if before != final:
                raise RuntimeArtifactManifestError("grant_permission_authority_changed")
        return result

    return revocation_oracle.authorize_key_epoch_use(
        key_epoch=str(receipt["issuer_key_epoch"]), at_epoch=now_epoch,
        expires_at=int(receipt["expires_at"]), action=guarded_action,
    )


def _permission_state(admission, repo, owner_path, oracle, now_epoch):
    from .reddog_signer_independent_secret_grant_verification import _owner_authority_snapshot
    policy = admission.policy
    if policy.get("schema_version") not in {POLICY_SCHEMA_V7, POLICY_SCHEMA_V8, POLICY_SCHEMA_V9}:
        raise RuntimeArtifactManifestError("grant_permission_e0_schema_invalid")
    root = grant_authority_owner_runtime_root(owner_path, repo, str(policy["owner_config_id"]))
    verified = verify_current_grant_service_artifacts(repo_root=repo, grant_root=root, policy=policy)
    receipt, snapshot_digest = _load_receipt(repo, root)
    _require_receipt(receipt, policy, verified, snapshot_digest, now_epoch)
    if type(oracle) is not RootAuthorizedSignerGrantRevocationOracle or oracle.binding != admission.revocation_binding:
        raise RuntimeArtifactManifestError("grant_permission_oracle_mismatch")
    return (deepcopy((_owner_authority_snapshot(admission), admission.revocation_binding,
        str(root), dict(verified), receipt, snapshot_digest)), receipt)


def _load_receipt(repo: Path, root: Path) -> tuple[dict[str, Any], str]:
    target = validate_runtime_artifact_path(
        root / PERMISSION_FILENAME, repo_root=repo, allowed_root=root
    )
    raw, _ = secure_read_confined_bytes(
        target, allowed_root=root, max_bytes=MAX_RECEIPT_BYTES + 1
    )
    if len(raw) > MAX_RECEIPT_BYTES:
        raise RuntimeArtifactManifestError("grant_permission_receipt_oversized")
    try:
        value = json.loads(raw.decode("ascii"))
        canonical = canonical_json(value).encode("ascii")
    except (UnicodeDecodeError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeArtifactManifestError("grant_permission_receipt_malformed") from exc
    if raw != canonical or not isinstance(value, dict):
        raise RuntimeArtifactManifestError("grant_permission_receipt_malformed")
    return validate_permission_receipt(value), raw_digest(raw)


def _require_receipt(
    receipt: Mapping[str, Any], policy: Mapping[str, Any],
    verified: Mapping[str, Any], snapshot_digest: str, now_epoch: int,
) -> None:
    config = verified.get("config")
    if not isinstance(config, Mapping):
        raise RuntimeArtifactManifestError("grant_permission_receipt_malformed")
    expected = _expected(policy, verified, config)
    compared = tuple((receipt[name], value) for name, value in expected.items())
    if any(not constant_time_compare(str(left), str(right)) for left, right in compared):
        raise RuntimeArtifactManifestError("grant_permission_binding_mismatch")
    if (
        not constant_time_compare(
            snapshot_digest, str(policy["grant_authority_permission_snapshot_digest"])
        )
        or not constant_time_compare(
            str(receipt["receipt_id"]),
            str(policy["grant_authority_permission_snapshot_receipt_id"]),
        )
        or not constant_time_compare(
            snapshot_digest, str(config["permission_snapshot_digest"])
        )
        or not constant_time_compare(
            str(receipt["receipt_id"]),
            str(config["permission_snapshot_receipt_id"]),
        )
        or not receipt["issued_at"] <= now_epoch < receipt["expires_at"]
        or receipt["issued_at"] != policy["issued_at"]
        or receipt["expires_at"] != policy["expires_at"]
    ):
        raise RuntimeArtifactManifestError("grant_permission_receipt_rejected")




__all__ = [
    "GET_SECRET", "PERMISSION_FILENAME", "SCHEMA_VERSION", "SECRETS_READ",
    "authorize_current_grant_authority_wsp71_use", "permission_receipt_id",
]
