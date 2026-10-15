"""Lazy issuer LOAD-v2 proof using protected custody and current E0 authority."""
from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from . import foundup_verified_outcome_root_revocation_protocol as wire
from .foundup_verified_outcome_root_authority_wire_codec import (
    MAX_MESSAGE_BYTES, canonical_bytes, decode_message, encode_message,
)
from .reddog_grant_authority_startup_custody import current_grant_custody
from .reddog_signer_owner_e0_capability_state import freeze_owner_e0_policy, thaw_owner_e0_policy
from .reddog_signer_owner_e0_current_selection import lease_validated_owner_e0_current_admission
from .reddog_signer_system_service_manifest_selection_loader import _load_owner_config
from .reddog_signer_system_service_wsp71_resolver_supply import (
    _require_descriptor_policy, _require_root_permission_live, _sign_root_proof,
)
from modules.infrastructure.secrets_mcp.src.systemd_credential_secret_resolver import SystemdCredentialSecretResolver


def build_grant_root_request_signer(*, owner_config_path, repo_root, policy, descriptor,
                                  credential_binding):
    """Construct metadata only; caller must isolate before resolving any proof."""
    return _GrantRootRequestSigner(Path(owner_config_path), Path(repo_root).resolve(),
        freeze_owner_e0_policy(thaw_owner_e0_policy(policy)),
        freeze_owner_e0_policy(thaw_owner_e0_policy(descriptor)), credential_binding,
        SystemdCredentialSecretResolver(credential_binding), time.time(), time.monotonic())


@dataclass(frozen=True, slots=True)
class _GrantRootRequestSigner:
    owner_config_path: Path
    repo_root: Path
    policy: object
    descriptor: object
    credential_binding: object
    resolver: object
    wall_start: float
    mono_start: float

    def __call__(self, signing_input):
        request = _canonical_issuer_load(signing_input)
        with lease_validated_owner_e0_current_admission(
            owner_config_path=self.owner_config_path, repo_root=self.repo_root,
            policy=self.policy,
        ) as lease:
            permission = _checked_permission(self, request, lease)
            _require_root_permission_live(self, permission, lease.policy)
            result = self.resolver.resolve(permission["reference"], permission["requester_id"])
            if (result.success is not True or result.reference != permission["reference"]
                    or type(result.ttl_remaining) is not int or result.ttl_remaining < 1):
                raise ValueError("grant_root_proof_credential_rejected")
            signature = _sign_root_proof(result.get_value(), signing_input, permission, self, lease.policy)
            if _checked_permission(self, request, lease) != permission:
                raise ValueError("grant_root_proof_permission_changed")
            _require_root_permission_live(self, permission, lease.policy)
        _require_root_permission_live(self, permission, self.policy)
        return signature


def _canonical_issuer_load(value):
    if (type(value) is not str or not value.isascii() or len(value) > MAX_MESSAGE_BYTES
            or not value.startswith(wire.SIGNING_PREFIX_V2)):
        raise ValueError("grant_root_proof_input_invalid")
    payload = decode_message(value[len(wire.SIGNING_PREFIX_V2):].encode("ascii"))
    if "request_id" in payload or "signer_instance_signature" in payload:
        raise ValueError("grant_root_proof_input_invalid")
    payload["signer_instance_signature"] = "ed25519-sig-v1:" + "A" * 86
    payload["request_id"] = wire.request_id_for(payload)
    request = wire.request_from_bytes(encode_message({"schema_version": wire.SCHEMA_VERSION_V2, **payload}))
    if (request.operation != wire.OP_LOAD or request.requester_role != wire.GRANT_ROLE
            or wire.canonical_signer_input(request) != value):
        raise ValueError("grant_root_proof_scope_invalid")
    return request


def _checked_permission(signer, request, lease):
    owner = _load_owner_config(signer.owner_config_path, repo=signer.repo_root)
    policy = thaw_owner_e0_policy(lease.policy)
    descriptor = thaw_owner_e0_policy(signer.descriptor)
    value, _, loader, _ = current_grant_custody(owner, policy)
    if (owner["config_id"] != policy["owner_config_id"]
            or owner["verified_outcome_authority"]["descriptor"] != descriptor
            or loader != signer.credential_binding
            or canonical_bytes(policy) != canonical_bytes(thaw_owner_e0_policy(signer.policy))
            or request.owner_config_id != policy["owner_config_id"]
            or request.policy_id != policy["policy_id"]
            or canonical_bytes(request.policy) != canonical_bytes(policy)
            or request.descriptor_id != descriptor["descriptor_id"]
            or request.binding_digest != lease.revocation_binding.anchor_binding_digest()
            or request.requester_principal_id != policy["grant_authority_principal_id"]
            or request.requester_key_epoch != policy["grant_authority_key_epoch"]
            or abs(time.time() - request.issued_at) > 30):
        raise ValueError("grant_root_proof_context_invalid")
    _require_descriptor_policy(descriptor, policy)
    return dict(value["root_load_permission"])


__all__ = ["build_grant_root_request_signer"]
