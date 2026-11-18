"""Root-owned WSP 71 resolver supply for the signer system service."""

from __future__ import annotations

import stat
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

from modules.infrastructure.secrets_mcp.src.op_cli_secret_resolver import (
    DEFAULT_MAX_SECRET_CHARS,
    DEFAULT_OP_TIMEOUT_SECONDS,
    OpCliCommandRunner,
    OpCliSecretResolver,
)
from modules.infrastructure.secrets_mcp.src.systemd_credential_secret_resolver import (
    SystemdCredentialBinding,
    SystemdCredentialSecretResolver,
    parse_systemd_credential_reference,
)

from . import foundup_verified_outcome_root_protected_use_protocol as control_wire
from . import foundup_verified_outcome_root_revocation_protocol as load_wire
from .foundup_verified_outcome_root_authority import (
    DESCRIPTOR_SCHEMA_V2, validate_root_verified_outcome_descriptor_identity_public,
)
from .foundup_verified_outcome_root_authority_wire_codec import (
    MAX_MESSAGE_BYTES, canonical_bytes, decode_message, encode_message,
)
from .reddog_ed25519_signature_verifier_backend import (
    Ed25519SignatureVerifier, encode_ed25519_public_key, encode_ed25519_signature,
)
from .reddog_ed25519_signer_validation import public_bytes_from_private_key
from .reddog_signer_key_provider_dryrun import _decode_ed25519_private_key
from .reddog_signer_owner_e0_capability_state import (
    freeze_owner_e0_policy, thaw_owner_e0_policy,
)
from .reddog_signer_owner_e0_current_selection import (
    lease_validated_owner_e0_current_admission,
)
from .reddog_signer_system_service_manifest_selection_loader import _load_owner_config
from .reddog_runtime_artifact_manifest_contract import RuntimeArtifactManifestError, is_sha256
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    validate_runtime_artifact_path, validate_runtime_root_path,
)


SYSTEM_SERVICE_OP_EXECUTABLE = Path("/usr/bin/op")
SYSTEM_SERVICE_SECRET_TTL_SECONDS = 60
ROOT_LOAD_PURPOSE = "revocation-anchor-load.v1"
ROOT_CONTROL_PURPOSE = "protected-use-acquire-finish.v1"
_PERMISSION_FIELDS = frozenset({
    "operation", "reference", "requester_id", "purpose", "public_key",
    "key_epoch", "issued_at", "expires_at",
})


@dataclass(frozen=True, slots=True)
class SystemServiceWsp71ResolverFactory:
    """Create one resolve-per-sign client after signer admission."""

    owner_config_id: str
    runner: OpCliCommandRunner | None = None
    credential_binding: SystemdCredentialBinding | None = None

    def __call__(self) -> OpCliSecretResolver | SystemdCredentialSecretResolver:
        if not _sha256(self.owner_config_id):
            raise ValueError("system_service_owner_config_id_invalid")
        if self.credential_binding is not None:
            # This metadata is not admission. The caller must still authenticate
            # owner state and run process/grant gates before invoking the factory.
            if type(self.credential_binding) is not SystemdCredentialBinding or self.runner is not None:
                raise ValueError("system_service_credential_binding_invalid")
            return SystemdCredentialSecretResolver(self.credential_binding)
        _require_root_owned_executable(SYSTEM_SERVICE_OP_EXECUTABLE)
        return OpCliSecretResolver(
            op_executable=str(SYSTEM_SERVICE_OP_EXECUTABLE),
            timeout_s=DEFAULT_OP_TIMEOUT_SECONDS,
            ttl_seconds=SYSTEM_SERVICE_SECRET_TTL_SECONDS,
            max_secret_chars=DEFAULT_MAX_SECRET_CHARS,
            session_id="reddog-signer:" + self.owner_config_id[7:23],
            runner=self.runner,
        )


def build_system_service_wsp71_resolver_factory(
    *, owner_config_id: str, credential_binding: SystemdCredentialBinding | None = None,
) -> SystemServiceWsp71ResolverFactory:
    """Bind production resolver construction to root-selected authority."""

    return SystemServiceWsp71ResolverFactory(
        owner_config_id=owner_config_id, credential_binding=credential_binding,
    )


def _require_root_owned_executable(path: Path) -> None:
    if not sys.platform.startswith("linux"):
        raise ValueError("system_service_wsp71_linux_required")
    if not path.is_absolute() or path.is_symlink():
        raise ValueError("system_service_op_executable_invalid")
    try:
        metadata = path.stat(follow_symlinks=False)
    except OSError as exc:
        raise ValueError("system_service_op_executable_unavailable") from exc
    mode = stat.S_IMODE(metadata.st_mode)
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != 0
        or mode & 0o022
        or not mode & 0o111
    ):
        raise ValueError("system_service_op_executable_untrusted")
    _require_root_owned_ancestry(path.parent)


def _require_root_owned_ancestry(path: Path) -> None:
    for directory in (path, *path.parents):
        try:
            metadata = directory.stat(follow_symlinks=False)
        except OSError as exc:
            raise ValueError("system_service_op_ancestry_unavailable") from exc
        if (
            directory.is_symlink()
            or not stat.S_ISDIR(metadata.st_mode)
            or metadata.st_uid != 0
            or stat.S_IMODE(metadata.st_mode) & 0o022
        ):
            raise ValueError("system_service_op_ancestry_untrusted")


def _sha256(value: object) -> bool:
    text = value if isinstance(value, str) else ""
    return bool(
        len(text) == 71
        and text.startswith("sha256:")
        and all(char in "0123456789abcdef" for char in text[7:])
    )


def build_system_service_root_request_signer(
    *, owner_config_path: Path | str, repo_root: Path, policy: Mapping[str, Any],
    descriptor: Mapping[str, Any], purpose: str,
    credential_binding: SystemdCredentialBinding,
):
    """Build a lazy proof signer; every use authenticates owner and E0 policy.

    Retain metadata and one secret-free resolver, never a private key. Keeping
    that resolver preserves its original monotonic deadline across calls.
    The caller must enforce process isolation before invoking this capability.
    """
    if (type(purpose) is not str or purpose not in {ROOT_LOAD_PURPOSE, ROOT_CONTROL_PURPOSE}
            or type(credential_binding) is not SystemdCredentialBinding):
        raise ValueError("startup_root_request_supply_invalid")
    return _RootRequestSigner(
        Path(owner_config_path), Path(repo_root).resolve(),
        freeze_owner_e0_policy(decode_message(canonical_bytes(thaw_owner_e0_policy(policy)))),
        freeze_owner_e0_policy(decode_message(canonical_bytes(thaw_owner_e0_policy(descriptor)))), purpose,
        credential_binding, SystemdCredentialSecretResolver(
            credential_binding, clock=time.time, monotonic=time.monotonic,
        ), time.time(), time.monotonic(),
    )


@dataclass(frozen=True, slots=True)
class _RootRequestSigner:
    owner_config_path: Path
    repo_root: Path
    policy: Mapping[str, Any]
    descriptor: Mapping[str, Any]
    purpose: str
    credential_binding: SystemdCredentialBinding
    resolver: SystemdCredentialSecretResolver
    wall_start: float
    mono_start: float

    def __call__(self, signing_input: str) -> str:
        request = _canonical_root_request(signing_input, self.purpose)
        with lease_validated_owner_e0_current_admission(
            owner_config_path=self.owner_config_path, repo_root=self.repo_root,
            policy=self.policy,
        ) as lease:
            permission = _checked_root_permission(self, request, lease)
            _require_root_permission_live(self, permission, lease.policy)
            result = self.resolver.resolve(
                permission["reference"], permission["requester_id"],
            )
            if (result.success is not True or result.reference != permission["reference"]
                    or type(result.ttl_remaining) is not int or result.ttl_remaining < 1):
                raise ValueError("startup_root_request_credential_rejected")
            signature = _sign_root_proof(result.get_value(), signing_input, permission, self, lease.policy)
            _require_root_permission_live(self, permission, lease.policy)
            if _checked_root_permission(self, request, lease) != permission:
                raise ValueError("startup_root_request_permission_changed")
            _require_root_permission_live(self, permission, lease.policy)
        _require_root_permission_live(self, permission, self.policy)
        return signature


def _canonical_root_request(value: str, purpose: str):
    wire = load_wire if purpose == ROOT_LOAD_PURPOSE else control_wire
    if (type(value) is not str or not value.isascii()
            or len(value) > MAX_MESSAGE_BYTES or not value.startswith(wire.SIGNING_PREFIX)):
        raise ValueError("startup_root_request_input_invalid")
    payload = decode_message(value[len(wire.SIGNING_PREFIX):].encode("ascii"))
    if "request_id" in payload or "signer_instance_signature" in payload:
        raise ValueError("startup_root_request_input_invalid")
    payload["signer_instance_signature"] = "ed25519-sig-v1:" + "A" * 86
    payload["request_id"] = wire.request_id_for(payload)
    request = wire.request_from_bytes(encode_message({"schema_version": wire.SCHEMA_VERSION, **payload}))
    allowed = {load_wire.OP_LOAD} if purpose == ROOT_LOAD_PURPOSE else {
        control_wire.OP_ACQUIRE, control_wire.OP_FINISH,
    }
    if request.operation not in allowed or wire.canonical_signer_input(request) != value:
        raise ValueError("startup_root_request_purpose_invalid")
    return request


def _checked_root_permission(signer: _RootRequestSigner, request: Any, lease: Any) -> dict:
    owner = _load_owner_config(signer.owner_config_path, repo=signer.repo_root)
    descriptor = validate_root_verified_outcome_descriptor_identity_public(
        thaw_owner_e0_policy(signer.descriptor), now_epoch=int(time.time()),
    )
    raw_authority = owner.get("verified_outcome_authority", {})
    policy = thaw_owner_e0_policy(lease.policy)
    if (owner.get("config_id") != policy["owner_config_id"]
            or raw_authority.get("descriptor") != descriptor
            or descriptor["schema_version"] != DESCRIPTOR_SCHEMA_V2
            or request.owner_config_id != policy["owner_config_id"]
            or request.policy_id != policy["policy_id"]
            or canonical_bytes(request.policy) != canonical_bytes(policy)
            or request.descriptor_id != descriptor["descriptor_id"]
            or request.binding_digest != lease.revocation_binding.anchor_binding_digest()
            or abs(time.time() - request.issued_at) > 30):
        raise ValueError("startup_root_request_context_invalid")
    _require_descriptor_policy(descriptor, policy)
    if signer.purpose == ROOT_CONTROL_PURPOSE and (
        request.key_epoch != policy["target_signer_key_epoch"]
        or request.grant_expires_at > policy["expires_at"]
        or (request.operation == control_wire.OP_ACQUIRE and request.grant_expires_at <= time.time())
    ):
        raise ValueError("startup_root_request_grant_context_invalid")
    custody = owner.get("startup_custody", {})
    metadata = asdict(signer.credential_binding)
    metadata["credential_ids"] = sorted(metadata["credential_ids"])
    if canonical_bytes(custody.get("credential_binding", {})) != canonical_bytes(metadata):
        raise ValueError("startup_root_request_custody_mismatch")
    if (raw_authority.get("signer_uid") != metadata["expected_uid"]
            or raw_authority.get("signer_gid") != metadata["expected_gid"]
            or raw_authority.get("signer_principal_id") != metadata["expected_requester"]):
        raise ValueError("startup_root_request_peer_mismatch")
    permissions = custody.get("root_request_permissions", {})
    permission = permissions.get(signer.purpose)
    return _validate_root_permission(permission, signer, descriptor)


def _require_descriptor_policy(descriptor: Mapping, policy: Mapping) -> None:
    fields = {
        "signer_public_key": "target_signer_public_key",
        "signer_key_epoch": "target_signer_key_epoch",
        "signer_manifest_id": "manifest_id",
        "signer_artifact_generation_digest": "artifact_generation_digest",
        "signer_config_digest": "config_digest",
    }
    if any(descriptor[left] != policy[right] for left, right in fields.items()):
        raise ValueError("startup_root_request_descriptor_mismatch")


def _validate_root_permission(value: object, signer: _RootRequestSigner, descriptor: Mapping) -> dict:
    if type(value) is not dict or set(value) != _PERMISSION_FIELDS:
        raise ValueError("startup_root_request_permission_invalid")
    identity = descriptor["root_control_authentication"] if signer.purpose == ROOT_CONTROL_PURPOSE else {
        "public_key": descriptor["signer_public_key"], "key_epoch": descriptor["signer_key_epoch"],
    }
    if (any(type(value[k]) is not str for k in _PERMISSION_FIELDS - {"issued_at", "expires_at"})
            or value["operation"] != "SECRETS_READ" or value["purpose"] != signer.purpose
            or value["requester_id"] != signer.credential_binding.expected_requester
            or value["public_key"] != identity["public_key"] or value["key_epoch"] != identity["key_epoch"]
            or parse_systemd_credential_reference(value["reference"]) not in signer.credential_binding.credential_ids
            or type(value["issued_at"]) is not int or type(value["expires_at"]) is not int
            or not signer.credential_binding.issued_at <= value["issued_at"] < value["expires_at"]
            or value["expires_at"] > signer.credential_binding.expires_at):
        raise ValueError("startup_root_request_permission_invalid")
    return dict(value)


def _require_root_permission_live(signer: _RootRequestSigner, permission: Mapping, policy: Mapping) -> None:
    wall, mono = time.time(), time.monotonic()
    deadline = signer.mono_start + permission["expires_at"] - signer.wall_start
    if (not signer.wall_start <= wall or not signer.mono_start <= mono
            or not permission["issued_at"] <= wall < permission["expires_at"]
            or not policy["issued_at"] <= wall < policy["expires_at"] or not mono < deadline):
        raise ValueError("startup_root_request_permission_expired")
    try:
        signer.resolver._remaining()
    except Exception as exc:
        raise ValueError("startup_root_request_credential_expired") from exc


def _sign_root_proof(secret: object, signing_input: str, permission: Mapping,
                     signer: _RootRequestSigner, policy: Mapping) -> str:
    key = _decode_ed25519_private_key(secret)
    if key is None or encode_ed25519_public_key(public_bytes_from_private_key(key)) != permission["public_key"]:
        raise ValueError("startup_root_request_key_mismatch")
    _require_root_permission_live(signer, permission, policy)
    signature = encode_ed25519_signature(key.sign(signing_input.encode("ascii")))
    if Ed25519SignatureVerifier().verify(permission["public_key"], signing_input, signature) is not True:
        raise ValueError("startup_root_request_signature_invalid")
    return signature


__all__ = [
    "SYSTEM_SERVICE_OP_EXECUTABLE",
    "SYSTEM_SERVICE_SECRET_TTL_SECONDS",
    "SystemServiceWsp71ResolverFactory",
    "build_system_service_wsp71_resolver_factory",
    "build_system_service_root_request_signer",
    "ROOT_LOAD_PURPOSE",
    "ROOT_CONTROL_PURPOSE",
]


def validate_system_service_startup_custody(
    owner: Mapping[str, Any], *, repo_root: Path, owner_root: Path,
) -> None:
    """Validate v7 metadata only; signed E0/store admission remains deferred."""
    try:
        value = owner["startup_custody"]
        fields = {"policy_path", "credential_binding", "root_request_permissions",
                  "replay_store", "replay_integrity_permission", "proposal_replay_store"}
        if type(value) is not dict or set(value) != fields or type(value["policy_path"]) is not str:
            raise ValueError("shape")
        policy_path = validate_runtime_artifact_path(
            value["policy_path"], allowed_root=owner_root, repo_root=repo_root)
        if policy_path.parent != owner_root:
            raise ValueError("policy_path")
        authority = owner["verified_outcome_authority"]
        descriptor = validate_root_verified_outcome_descriptor_identity_public(
            authority["descriptor"], now_epoch=int(time.time()),
        )
        if descriptor["schema_version"] != DESCRIPTOR_SCHEMA_V2:
            raise ValueError("descriptor")
        binding = _startup_credential_binding(value["credential_binding"], authority)
        permissions = value["root_request_permissions"]
        if type(permissions) is not dict or set(permissions) != {ROOT_LOAD_PURPOSE, ROOT_CONTROL_PURPOSE}:
            raise ValueError("permissions")
        identities = {ROOT_LOAD_PURPOSE: {"public_key": descriptor["signer_public_key"],
                      "key_epoch": descriptor["signer_key_epoch"]},
                      ROOT_CONTROL_PURPOSE: descriptor["root_control_authentication"]}
        for purpose, identity in identities.items():
            _startup_permission(permissions[purpose], binding, purpose, identity=identity)
        _startup_permission(value["replay_integrity_permission"], binding,
                            "signer-grant-replay-integrity.v1")
        _startup_replay_store(value["replay_store"], repo_root, with_digest=True)
        if value["proposal_replay_store"] is not None:
            _startup_replay_store(value["proposal_replay_store"], repo_root, with_digest=False)
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeArtifactManifestError("signer_startup_custody_invalid") from exc


def _startup_credential_binding(value: object, authority: Mapping) -> SystemdCredentialBinding:
    if type(value) is not dict or set(value) != set(SystemdCredentialBinding.__dataclass_fields__):
        raise ValueError("credential_binding")
    identifiers = value["credential_ids"]
    if (type(identifiers) is not list or any(type(item) is not str for item in identifiers)
            or identifiers != sorted(set(identifiers))):
        raise ValueError("credential_ids")
    binding = SystemdCredentialBinding(**{**value, "credential_ids": frozenset(identifiers)})
    if (binding.expected_uid != authority["signer_uid"]
            or binding.expected_gid != authority["signer_gid"]
            or binding.expected_requester != authority["signer_principal_id"]):
        raise ValueError("credential_identity")
    return binding


def _startup_permission(value: object, binding: SystemdCredentialBinding,
                        purpose: str, *, identity: Mapping | None = None) -> None:
    fields = _PERMISSION_FIELDS if identity is not None else (
        _PERMISSION_FIELDS - {"public_key", "key_epoch"}) | {"encoding"}
    if type(value) is not dict or set(value) != fields:
        raise ValueError("permission_shape")
    if (any(type(value[k]) is not str for k in fields - {"issued_at", "expires_at"})
            or value["operation"] != "SECRETS_READ" or value["purpose"] != purpose
            or value["requester_id"] != binding.expected_requester
            or parse_systemd_credential_reference(value["reference"]) not in binding.credential_ids
            or type(value["issued_at"]) is not int or type(value["expires_at"]) is not int
            or not binding.issued_at <= value["issued_at"] < value["expires_at"] <= binding.expires_at):
        raise ValueError("permission_binding")
    if identity is not None:
        if any(value[name] != identity[name] for name in ("public_key", "key_epoch")):
            raise ValueError("permission_identity")
    elif value["encoding"] != "utf8":
        raise ValueError("permission_encoding")


def _startup_replay_store(value: object, repo_root: Path, *, with_digest: bool) -> None:
    fields = {"high_water_root", "high_water_path"}
    if with_digest:
        fields.add("replay_store_binding_digest")
    if (type(value) is not dict or set(value) != fields
            or any(type(value[name]) is not str for name in fields)):
        raise ValueError("replay_shape")
    if with_digest and not is_sha256(value["replay_store_binding_digest"]):
        raise ValueError("replay_binding")
    root = validate_runtime_root_path(value["high_water_root"], repo_root=repo_root)
    path = validate_runtime_artifact_path(value["high_water_path"], allowed_root=root, repo_root=repo_root)
    if path.parent != root:
        raise ValueError("replay_path")
