"""Signed snapshot contract for independent signer-grant revocations."""

from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_revocation_snapshot_validation import (
    MAX_SNAPSHOT_TTL_SECONDS,
    SNAPSHOT_FIELDS,
    SNAPSHOT_SCHEMA,
    canonical_signer_grant_revocation_snapshot_input,
    signer_grant_revocation_snapshot_id,
    validated_signer_grant_revocation_snapshot,
    validated_snapshot_integrity,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    PrincipalKeyResolver,
    SignatureVerifier,
    constant_time_compare,
)


@dataclass(frozen=True)
class ExpectedSignerGrantRevocationBinding:
    policy_id: str
    owner_config_id: str
    manifest_id: str
    artifact_generation_digest: str
    authority_principal_id: str
    authority_principal_provider: str
    authority_public_key: str
    target_signer_agent_id: str
    target_signer_profile_id: str
    target_signer_public_key: str
    target_signer_key_epoch: str
    target_signer_generation_id: str
    store_id: str
    durability_receipt_id: str


def verify_signer_grant_revocation_snapshot(
    value: Mapping[str, Any], *, expected: ExpectedSignerGrantRevocationBinding,
    principal_key_resolver: PrincipalKeyResolver,
    signature_verifier: SignatureVerifier, now_epoch: int,
    require_freshness: bool = True,
) -> dict[str, Any]:
    if type(require_freshness) is not bool:
        raise ValueError("signer_grant_revocation_snapshot_malformed")
    checked = (
        validated_signer_grant_revocation_snapshot(value, now_epoch=now_epoch)
        if require_freshness else validated_snapshot_integrity(value)
    )
    return _verify_binding_and_authority(
        checked, expected=expected,
        principal_key_resolver=principal_key_resolver,
        signature_verifier=signature_verifier,
    )


def _verify_binding_and_authority(
    checked: Mapping[str, Any], *, expected: ExpectedSignerGrantRevocationBinding,
    principal_key_resolver: PrincipalKeyResolver,
    signature_verifier: SignatureVerifier,
) -> dict[str, Any]:
    if type(expected) is not ExpectedSignerGrantRevocationBinding:
        raise ValueError("signer_grant_revocation_snapshot_binding_invalid")
    expected_values = {item.name: getattr(expected, item.name) for item in fields(expected)}
    if any(
        type(item) is not str or not item or not item.isascii()
        for item in expected_values.values()
    ):
        raise ValueError("signer_grant_revocation_snapshot_binding_invalid")
    for name, expected_value in expected_values.items():
        if not constant_time_compare(str(checked[name]), expected_value):
            raise ValueError("signer_grant_revocation_snapshot_binding_invalid")
    if constant_time_compare(
        checked["authority_public_key"], checked["target_signer_public_key"]
    ):
        raise ValueError("signer_grant_revocation_snapshot_self_authority_rejected")
    try:
        trusted = principal_key_resolver.resolve(
            checked["authority_principal_id"],
            checked["authority_principal_provider"],
        )
        verified = (
            isinstance(trusted, str)
            and constant_time_compare(trusted, checked["authority_public_key"])
            and signature_verifier.verify(
                checked["authority_public_key"],
                canonical_signer_grant_revocation_snapshot_input(checked),
                checked["signature"],
            ) is True
        )
    except Exception:
        verified = False
    if not verified:
        raise ValueError("signer_grant_revocation_snapshot_authority_invalid")
    return checked


__all__ = [
    "ExpectedSignerGrantRevocationBinding", "MAX_SNAPSHOT_TTL_SECONDS",
    "SNAPSHOT_FIELDS", "SNAPSHOT_SCHEMA",
    "canonical_signer_grant_revocation_snapshot_input",
    "signer_grant_revocation_snapshot_id",
    "validated_signer_grant_revocation_snapshot",
    "verify_signer_grant_revocation_snapshot",
]
