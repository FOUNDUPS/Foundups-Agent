"""Root-installed, short-lived signing of one initial generation anchor.

This administrative adapter does not sign work orders or high-water state,
activate a generation, or admit a worker. Installation of its protected policy
is the trust root; credential custody alone does not supply authorization.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

from .reddog_ed25519_signature_verifier_backend import (
    Ed25519SignatureVerifier, decode_ed25519_public_key, encode_ed25519_signature,
)
from .reddog_signer_key_provider_dryrun import (
    _decode_ed25519_private_key, _public_key_text,
)
from .reddog_signer_process_isolation_gate import enforce_signer_process_isolation
from .reddog_signer_socket_peer_credential_attestor import PeerCredentialPolicy
from .reddog_signer_runtime_generation_anchor_codec import (
    _unsigned_state, _validate_binding,
)
from .reddog_signer_runtime_generation_contract import SignerRuntimeGenerationBinding
from .reddog_signer_system_service_manifest_selection_loader import _read_root_owned_bytes
from .reddog_signer_system_service_wsp71_resolver_supply import _startup_permission
from modules.infrastructure.secrets_mcp.src.systemd_credential_secret_resolver import (
    SystemdCredentialBinding, SystemdCredentialSecretResolver,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    validate_runtime_artifact_path, validate_runtime_root_path,
)

SCHEMA_VERSION = "reddog_generation_anchor_bootstrap.v1"
PURPOSE = "initial_generation_anchor"
_FIELDS = {"schema_version", "repo_root_digest", "identity", "credential_binding",
           "permission", "consumer_uids", "anchor_id", "high_water_store_id",
           "high_water_durability_receipt_id", "generation_binding"}


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("ascii")


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("generation_bootstrap_duplicate_key")
        result[key] = value
    return result


def _load(path: Path, repo: Path):
    root = validate_runtime_root_path(path.parent, repo_root=repo)
    target = validate_runtime_artifact_path(path, allowed_root=root, repo_root=repo)
    raw = _read_root_owned_bytes(target, root)
    value = json.loads(raw.decode("ascii"), object_pairs_hook=_unique)
    if type(value) is not dict or set(value) != _FIELDS or value["schema_version"] != SCHEMA_VERSION:
        raise ValueError("generation_bootstrap_shape_invalid")
    if value["repo_root_digest"] != "sha256:" + hashlib.sha256(str(repo).encode()).hexdigest():
        raise ValueError("generation_bootstrap_repo_mismatch")
    identity = value["identity"]
    if type(identity) is not dict or set(identity) != {"public_key", "key_epoch"}:
        raise ValueError("generation_bootstrap_identity_invalid")
    public = decode_ed25519_public_key(identity["public_key"])
    if public is None or not _text(identity["key_epoch"]):
        raise ValueError("generation_bootstrap_identity_invalid")
    metadata = dict(value["credential_binding"])
    ids = metadata.get("credential_ids")
    if type(ids) is not list or len(ids) != 1 or not _text(ids[0]):
        raise ValueError("generation_bootstrap_credential_scope_invalid")
    metadata["credential_ids"] = frozenset(ids)
    binding = SystemdCredentialBinding(**metadata)
    _startup_permission(value["permission"], binding, PURPOSE, identity=identity)
    uids = value["consumer_uids"]
    if (type(uids) is not list or not uids or len(uids) > 32
            or any(type(uid) is not int or not 0 < uid < 2**32-1 for uid in uids)
            or len(set(uids)) != len(uids) or binding.expected_uid in uids):
        raise ValueError("generation_bootstrap_consumer_identity_invalid")
    generation = SignerRuntimeGenerationBinding(**value["generation_binding"])
    _validate_binding(generation)
    if generation.generation != 1:
        raise ValueError("generation_bootstrap_initial_only")
    from .reddog_runtime_artifact_manifest_contract import is_sha256
    if (not _text(value["anchor_id"]) or not _text(value["high_water_store_id"])
            or not is_sha256(value["high_water_durability_receipt_id"])):
        raise ValueError("generation_bootstrap_anchor_identity_invalid")
    authenticator_id = "ed25519-generation:" + hashlib.sha256(public).hexdigest()
    unsigned = _unsigned_state(
        generation, anchor_id=value["anchor_id"], authenticator_id=authenticator_id,
        high_water_store_id=value["high_water_store_id"],
        high_water_durability_receipt_id=value["high_water_durability_receipt_id"],
        previous_revision=None,
    )
    return raw, value, binding, authenticator_id, _canonical(unsigned)


def _text(value: object) -> bool:
    return type(value) is str and 0 < len(value) <= 256 and all(33 <= ord(c) <= 126 for c in value)


@dataclass(frozen=True, slots=True, init=False)
class _InitialGenerationSigner:
    """Created by the protected loader; never retains decoded private keys."""

    _path: Path
    _repo: Path
    _raw: bytes
    _binding: SystemdCredentialBinding
    authenticator_id: str
    _payload: bytes
    _permission: object
    _public_key: str
    _wall_start: float
    _mono_start: float
    _deadline: float
    _resolver: object

    def __init__(self, path: Path, repo: Path, loaded) -> None:
        raw, value, binding, authenticator_id, payload = loaded
        wall, mono = time.time(), time.monotonic()
        values = dict(_path=path, _repo=repo, _raw=raw, _binding=binding,
                      authenticator_id=authenticator_id, _payload=payload,
                      _permission=MappingProxyType(dict(value["permission"])),
                      _public_key=value["identity"]["public_key"], _wall_start=wall,
                      _mono_start=mono, _deadline=mono + value["permission"]["expires_at"] - wall)
        for name, entry in values.items():
            object.__setattr__(self, name, entry)
        self._check()
        object.__setattr__(self, "_resolver", SystemdCredentialSecretResolver(self._binding))

    def _check(self) -> None:
        self._check_time()
        loaded = _load(self._path, self._repo)
        if (loaded[0] != self._raw or loaded[1]["permission"] != self._permission
                or loaded[2] != self._binding or loaded[3] != self.authenticator_id
                or loaded[4] != self._payload or loaded[1]["identity"]["public_key"] != self._public_key):
            raise ValueError("generation_bootstrap_config_changed")
        self._check_time()

    def _check_time(self) -> None:
        wall, mono = time.time(), time.monotonic()
        if (wall < self._wall_start or mono < self._mono_start or mono >= self._deadline
                or not self._permission["issued_at"] <= wall < self._permission["expires_at"]):
            raise ValueError("generation_bootstrap_expired")

    def authenticate(self, payload: bytes) -> str:
        if type(payload) is not bytes or payload != self._payload:
            raise ValueError("generation_bootstrap_payload_not_authorized")
        self._check()
        result = self._resolver.resolve(self._permission["reference"],
                                        requester_id=self._binding.expected_requester)
        if result.success is not True:
            raise ValueError("generation_bootstrap_custody_rejected")
        self._check()
        key = _decode_ed25519_private_key(result.get_value())
        if key is None or _public_key_text(key) != self._public_key:
            raise ValueError("generation_bootstrap_key_mismatch")
        signature = encode_ed25519_signature(key.sign(payload))
        del key, result
        if not Ed25519SignatureVerifier().verify(self._public_key, payload.decode("ascii"), signature):
            raise ValueError("generation_bootstrap_signature_rejected")
        self._check()
        return signature


def load_initial_generation_anchor_signer(*, bootstrap_path: Path | str, repo_root: Path | str):
    """Consume root installation policy; enforce isolation before secret access.

    Repeating an identical signature is safe and does not activate anything.
    Existing durable anchor CAS must reject repeated initial activation. Policy
    receipt IDs bind declared store identities; they are not durability proofs.
    """
    path, repo = Path(bootstrap_path), Path(repo_root).resolve()
    if not path.is_absolute():
        raise ValueError("generation_bootstrap_path_not_absolute")
    loaded = _load(path, repo)
    binding = loaded[2]
    policy = PeerCredentialPolicy({uid: f"consumer:{uid}" for uid in loaded[1]["consumer_uids"]})
    isolation = enforce_signer_process_isolation(policy, expected_signer_uid=binding.expected_uid,
                                                 expected_signer_gid=binding.expected_gid)
    if not isolation.accepted:
        raise ValueError("generation_bootstrap_isolation_rejected")
    return _InitialGenerationSigner(path, repo, loaded)


__all__ = ["load_initial_generation_anchor_signer"]
