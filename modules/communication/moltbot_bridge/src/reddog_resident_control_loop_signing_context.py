"""Resolve the isolated signer context for resident control-loop receipts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_architect_fix_promotion_publication import (
    architect_fix_committed_publication_reasons,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    Ed25519SignatureVerifier,
    decode_ed25519_public_key,
)
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_client import (
    DEFAULT_SIGNER_SOCKET_MAX_RESPONSE_BYTES,
    DEFAULT_SIGNER_SOCKET_TIMEOUT_S,
    build_reddog_isolated_signer_socket_client,
)
from modules.communication.moltbot_bridge.src.reddog_resident_control_loop_receipt_auth import (
    ControlLoopReceiptSigningContext,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    HIGH_AUTHORITY_OPERATIONS,
    HIGH_AUTHORITY_TIER,
    HIGH_AUTHORITY_VALVE_STATES,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    secure_read_confined_bytes,
    validate_runtime_artifact_path,
)


MAX_AUTHORITY_PROFILE_BYTES = 256 * 1024


def build_control_loop_receipt_signing_context(
    *,
    repo_root: Path | str,
    authority_profile_path: Path | str | None,
    authority_profile_source_path: Path | str | None,
    signer_socket_path: Path | str | None,
    expected_authority_profile_source_receipt_id: str | None,
    authoritative_work_state_path: Path | str | None = None,
    signer_socket_timeout_s: float = DEFAULT_SIGNER_SOCKET_TIMEOUT_S,
    signer_socket_max_response_bytes: int = DEFAULT_SIGNER_SOCKET_MAX_RESPONSE_BYTES,
    signer_socket_connector: Any = None,
) -> ControlLoopReceiptSigningContext:
    """Resolve public authority bindings and an existing signer client."""

    profile = _load_authority_profile(repo_root, authority_profile_path)
    source_profile = _load_authority_profile(repo_root, authority_profile_source_path)
    source_receipt_id = validate_authority_profile_source(
        source_profile, expected_authority_profile_source_receipt_id
    )
    _validate_source_authority_basis(source_profile)
    validate_promoted_authority_profile_source(profile, source_profile)
    _validate_architect_fix_publication(
        repo_root,
        profile,
        authoritative_work_state_path,
    )
    fields = _validated_authority_profile_fields(profile)
    built = build_reddog_isolated_signer_socket_client(
        repo_root=repo_root,
        socket_path=signer_socket_path,
        timeout_s=signer_socket_timeout_s,
        max_response_bytes=signer_socket_max_response_bytes,
        connector=signer_socket_connector,
    )
    if not built.accepted or built.client is None:
        raise ValueError("resident_control_loop_signer_client_unavailable")
    return ControlLoopReceiptSigningContext(
        signer=built.client,
        signature_verifier=Ed25519SignatureVerifier(),
        issuer_principal_id=fields["principal_id"],
        signer_public_key=fields["signer_public_key"],
        key_epoch=fields["key_epoch"],
        authority_tier=fields["authority_tier"],
        consensus_receipt_digest=fields["consensus_receipt_digest"],
        authority_profile_digest="sha256:" + _digest(profile),
        authority_profile_source_receipt_id=source_receipt_id,
    )


def _validate_architect_fix_publication(
    repo_root: Path | str,
    profile: Mapping[str, Any],
    work_state_path: Path | str | None,
) -> None:
    if not work_state_path:
        raise ValueError(
            "resident_control_loop_architect_publication_state_required"
        )
    work_state = _load_authority_profile(repo_root, work_state_path)
    binding = profile.get("operational_context_binding")
    if not isinstance(binding, Mapping):
        binding = {}
    reasons = architect_fix_committed_publication_reasons(
        work_state,
        profile,
        queue_item_id=str(binding.get("queue_item_id") or ""),
        claim_id=str(binding.get("claim_id") or ""),
    )
    if reasons:
        raise ValueError(
            "resident_control_loop_architect_publication_not_committed"
        )


def _validated_authority_profile_fields(profile: Mapping[str, Any]) -> dict[str, str]:
    signer_public_key = _required_ascii(profile.get("reddog_public_key"), 512, "public_key")
    if decode_ed25519_public_key(signer_public_key) is None:
        raise ValueError("resident_control_loop_authority_public_key_invalid")
    operation = _required_ascii(
        profile.get("requested_operation"), 160, "requested_operation"
    )
    valve_state = _required_ascii(
        profile.get("valve_state_required"), 160, "valve_state_required"
    )
    if operation not in HIGH_AUTHORITY_OPERATIONS and valve_state not in HIGH_AUTHORITY_VALVE_STATES:
        raise ValueError("resident_control_loop_authority_tier_invalid")
    consensus = _required_ascii(
        profile.get("consensus_receipt_digest"), 256, "consensus_receipt_digest"
    )
    if not _is_sha256_digest(consensus):
        raise ValueError("resident_control_loop_authority_consensus_receipt_digest_invalid")
    sovereign = _required_ascii(
        profile.get("sovereign_authorization_digest"),
        256,
        "sovereign_authorization_digest",
    )
    if not _is_sha256_digest(sovereign):
        raise ValueError("resident_control_loop_authority_sovereign_authorization_digest_invalid")
    return {
        "principal_id": _required_ascii(profile.get("principal_id"), 256, "principal_id"),
        "signer_public_key": signer_public_key,
        "key_epoch": _required_ascii(profile.get("key_epoch"), 160, "key_epoch"),
        "authority_tier": HIGH_AUTHORITY_TIER,
        "consensus_receipt_digest": consensus,
    }


def _load_authority_profile(
    repo_root: Path | str,
    authority_profile_path: Path | str | None,
) -> Mapping[str, Any]:
    if not authority_profile_path:
        raise ValueError("resident_control_loop_authority_profile_required")
    path = validate_runtime_artifact_path(authority_profile_path, repo_root=repo_root)
    if not path.exists() or path.stat().st_size > MAX_AUTHORITY_PROFILE_BYTES:
        raise ValueError("resident_control_loop_authority_profile_invalid")
    raw, offset = secure_read_confined_bytes(
        path, allowed_root=path.parent, max_bytes=MAX_AUTHORITY_PROFILE_BYTES
    )
    if offset != path.stat().st_size:
        raise ValueError("resident_control_loop_authority_profile_incomplete")
    try:
        profile = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise ValueError("resident_control_loop_authority_profile_invalid") from exc
    if not isinstance(profile, Mapping):
        raise ValueError("resident_control_loop_authority_profile_invalid")
    return profile


def validate_authority_profile_source(
    profile: Mapping[str, Any], expected_receipt_id: str | None
) -> str:
    if profile.get("schema_version") != "reddog_authority_profile_source.v1":
        raise ValueError("resident_control_loop_authority_profile_schema_invalid")
    expected = str(expected_receipt_id or "").strip()
    if not _is_sha256_digest(expected):
        raise ValueError("resident_control_loop_authority_profile_source_receipt_required")
    supplied = str(profile.get("authority_profile_source_receipt_id") or "").strip()
    unsigned = dict(profile)
    unsigned.pop("authority_profile_source_receipt_id", None)
    computed = "sha256:" + _digest(unsigned)
    if supplied != computed or supplied != expected:
        raise ValueError("resident_control_loop_authority_profile_source_receipt_invalid")
    return supplied


def validate_promoted_authority_profile_source(
    profile: Mapping[str, Any], source_profile: Mapping[str, Any]
) -> None:
    """Require the promoted runtime profile to preserve its source verbatim."""

    if not profile or not source_profile:
        raise ValueError("resident_control_loop_authority_profile_source_binding_invalid")
    if any(profile.get(key) != value for key, value in source_profile.items()):
        raise ValueError("resident_control_loop_authority_profile_source_binding_invalid")
    binding = profile.get("operational_context_binding")
    if not isinstance(binding, Mapping):
        raise ValueError("resident_control_loop_authority_profile_promotion_binding_invalid")
    for field in (
        "queue_item_id",
        "claim_id",
        "architect_determination_receipt_id",
        "wsp15_allocation_receipt",
    ):
        if binding.get(field) in (None, "", (), [], {}):
            raise ValueError("resident_control_loop_authority_profile_promotion_binding_invalid")


def _validate_source_authority_basis(profile: Mapping[str, Any]) -> None:
    basis = profile.get("source_authority_basis")
    if not isinstance(basis, Mapping):
        raise ValueError("resident_control_loop_authority_profile_source_basis_invalid")
    principal_public_key = _required_ascii(
        profile.get("principal_public_key"), 512, "principal_public_key"
    )
    if decode_ed25519_public_key(principal_public_key) is None:
        raise ValueError("resident_control_loop_authority_principal_public_key_invalid")
    permission_digest = _required_ascii(
        profile.get("permission_snapshot_digest"),
        256,
        "permission_snapshot_digest",
    )
    subject_digest = str(basis.get("principal_verified_subject_digest") or "")
    if not _is_sha256_digest(permission_digest) or not _is_sha256_digest(subject_digest):
        raise ValueError("resident_control_loop_authority_profile_source_basis_invalid")
    if str(basis.get("permission_snapshot_digest") or "") != permission_digest:
        raise ValueError("resident_control_loop_authority_profile_source_basis_invalid")
    repo_scope = basis.get("principal_repo_scope")
    foundup_scope = basis.get("principal_foundup_scope")
    if (
        not isinstance(repo_scope, list)
        or str(profile.get("repo_full_name") or "") not in repo_scope
        or not isinstance(foundup_scope, list)
        or str(profile.get("foundup_id") or "") not in foundup_scope
    ):
        raise ValueError("resident_control_loop_authority_profile_source_basis_invalid")
    if basis.get("permission_snapshot_can_write") is not True and basis.get(
        "permission_snapshot_can_admin"
    ) is not True:
        raise ValueError("resident_control_loop_authority_profile_source_basis_invalid")


def _required_ascii(value: Any, max_chars: int, field: str) -> str:
    text = str(value or "").strip()
    if not text or len(text) > max_chars or any(ord(char) >= 128 for char in text):
        raise ValueError(f"resident_control_loop_authority_{field}_invalid")
    return text


def _is_sha256_digest(value: object) -> bool:
    text = str(value or "")
    return len(text) == 71 and text.startswith("sha256:") and all(
        char in "0123456789abcdef" for char in text[7:]
    )


def _digest(value: Any) -> str:
    import hashlib

    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


__all__ = [
    "build_control_loop_receipt_signing_context",
    "validate_authority_profile_source",
    "validate_promoted_authority_profile_source",
]
