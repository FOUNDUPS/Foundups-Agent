"""Root-installed, short-lived signing of initial generation records.

V1 signs only an anchor; explicit V2 also signs its initial high-water records.
Neither activates a generation nor admits a worker. Protected installation is
the trust root; credential custody alone does not supply authorization.
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
    _state_revision, _unsigned_state, _validate_binding,
)
from .reddog_signer_runtime_generation_contract import SignerRuntimeGenerationBinding
from .reddog_signer_runtime_generation_pending_codec import decode_high_water, decode_pending
from .reddog_runtime_artifact_manifest_contract import is_sha256
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
BOOTSTRAP_SCHEMA_VERSION = "reddog_generation_bootstrap.v2"
BOOTSTRAP_PURPOSE = "initial_generation_bootstrap"
_MAX_PAYLOAD_BYTES = 16384
_HIGH_WATER_SCHEMA = "reddog_signer_runtime_generation_high_water.v2"
_HIGH_WATER_FIELDS = {"rollback_domain_digest", "witness_store_id",
                      "witness_durability_receipt_id", "witness_binding_context_digest"}
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


def _load(path: Path, repo: Path, *, bootstrap: bool = False):
    root = validate_runtime_root_path(path.parent, repo_root=repo)
    target = validate_runtime_artifact_path(path, allowed_root=root, repo_root=repo)
    raw = _read_root_owned_bytes(target, root)
    value = json.loads(raw.decode("ascii"), object_pairs_hook=_unique)
    fields = _FIELDS | {"high_water_binding"} if bootstrap else _FIELDS
    schema = BOOTSTRAP_SCHEMA_VERSION if bootstrap else SCHEMA_VERSION
    if type(value) is not dict or set(value) != fields or value["schema_version"] != schema:
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
    purpose = BOOTSTRAP_PURPOSE if bootstrap else PURPOSE
    _startup_permission(value["permission"], binding, purpose, identity=identity)
    uids = value["consumer_uids"]
    if (type(uids) is not list or not uids or len(uids) > 32
            or any(type(uid) is not int or not 0 < uid < 2**32-1 for uid in uids)
            or len(set(uids)) != len(uids) or binding.expected_uid in uids):
        raise ValueError("generation_bootstrap_consumer_identity_invalid")
    generation = SignerRuntimeGenerationBinding(**value["generation_binding"])
    _validate_binding(generation)
    if generation.generation != 1:
        raise ValueError("generation_bootstrap_initial_only")
    if (not _text(value["anchor_id"]) or not _text(value["high_water_store_id"])
            or not is_sha256(value["high_water_durability_receipt_id"])):
        raise ValueError("generation_bootstrap_anchor_identity_invalid")
    authenticator_id = "ed25519-generation:" + hashlib.sha256(public).hexdigest()
    _high_water_header(value, authenticator_id)
    unsigned = _unsigned_state(
        generation, anchor_id=value["anchor_id"], authenticator_id=authenticator_id,
        high_water_store_id=value["high_water_store_id"],
        high_water_durability_receipt_id=value["high_water_durability_receipt_id"],
        previous_revision=None,
    )
    return raw, value, binding, authenticator_id, _canonical(unsigned)


def _text(value: object) -> bool:
    return type(value) is str and 0 < len(value) <= 256 and all(33 <= ord(c) <= 126 for c in value)


def _high_water_header(value, authenticator_id):
    if value["schema_version"] == SCHEMA_VERSION:
        return None
    binding = value["high_water_binding"]
    if (type(binding) is not dict or set(binding) != _HIGH_WATER_FIELDS
            or not _text(binding["witness_store_id"])
            or any(not is_sha256(binding[name]) for name in _HIGH_WATER_FIELDS - {"witness_store_id"})):
        raise ValueError("generation_bootstrap_high_water_binding_invalid")
    return {"schema_version": _HIGH_WATER_SCHEMA, "store_id": value["high_water_store_id"],
            "durability_receipt_id": value["high_water_durability_receipt_id"],
            "authenticator_id": authenticator_id, **binding}


def _initial_high_water_revision(payload, header, anchor_id):
    """Validate contents only; the existing writer owns CAS/transaction order."""
    value = json.loads(payload.decode("ascii"), object_pairs_hook=_unique)
    if (type(value) is not dict or set(value) != set(header) | {"entries"}
            or any(value[name] != expected for name, expected in header.items())
            or _canonical(value) != payload or type(value["entries"]) is not dict):
        raise ValueError("generation_bootstrap_high_water_payload_invalid")
    entries = value["entries"]
    if not entries:  # Aborting the initial transaction removes its entry.
        return None
    if set(entries) != {anchor_id}:
        raise ValueError("generation_bootstrap_high_water_anchor_invalid")
    entry = entries[anchor_id]
    if type(entry) is not dict or set(entry) != {"current", "pending"}:
        raise ValueError("generation_bootstrap_high_water_entry_invalid")
    current, pending = decode_high_water(entry["current"]), decode_pending(entry["pending"])
    if current is None and pending is not None:
        if pending.expected is not None or pending.previous_anchor_state_json != "{}":
            raise ValueError("generation_bootstrap_high_water_initial_only")
        current = pending.next_value
    elif current is None or pending is not None:
        raise ValueError("generation_bootstrap_high_water_initial_only")
    if current.generation != 1:
        raise ValueError("generation_bootstrap_high_water_initial_only")
    return current.revision


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
    _schema: str
    _high_water_header: object

    def __init__(self, path: Path, repo: Path, loaded) -> None:
        raw, value, binding, authenticator_id, payload = loaded
        wall, mono = time.time(), time.monotonic()
        values = dict(_path=path, _repo=repo, _raw=raw, _binding=binding,
                      _schema=value["schema_version"],
                      _high_water_header=(None if value["schema_version"] == SCHEMA_VERSION else
                                          MappingProxyType(_high_water_header(value, authenticator_id))),
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
        loaded = _load(self._path, self._repo, bootstrap=self._schema == BOOTSTRAP_SCHEMA_VERSION)
        if (loaded[0] != self._raw or loaded[1]["permission"] != self._permission
                or loaded[2] != self._binding or loaded[3] != self.authenticator_id
                or loaded[4] != self._payload or loaded[1]["identity"]["public_key"] != self._public_key
                or loaded[1]["schema_version"] != self._schema
                or _high_water_header(loaded[1], loaded[3]) != self._high_water_header):
            raise ValueError("generation_bootstrap_config_changed")
        self._check_time()

    def _check_time(self) -> None:
        wall, mono = time.time(), time.monotonic()
        if (wall < self._wall_start or mono < self._mono_start or mono >= self._deadline
                or not self._permission["issued_at"] <= wall < self._permission["expires_at"]):
            raise ValueError("generation_bootstrap_expired")

    def authenticate(self, payload: bytes) -> str:
        if type(payload) is not bytes or len(payload) > _MAX_PAYLOAD_BYTES:
            raise ValueError("generation_bootstrap_payload_not_authorized")
        if payload != self._payload:
            if self._high_water_header is None:
                raise ValueError("generation_bootstrap_payload_not_authorized")
            self._check()
            anchor = json.loads(self._payload)
            revision = _initial_high_water_revision(payload, self._high_water_header, anchor["anchor_id"])
            if revision is not None:
                # Reuse only the authorized anchor path, with fresh custody and verification.
                tag = self.authenticate(self._payload)
                if revision != _state_revision({**anchor, "authentication_tag": tag}):
                    raise ValueError("generation_bootstrap_high_water_revision_invalid")
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
    return _load_signer(bootstrap_path, repo_root, bootstrap=False)


def load_initial_generation_bootstrap_signer(*, bootstrap_path: Path | str, repo_root: Path | str):
    """V2: sign the exact initial anchor and bounded high-water record contents.

    Does not issue writer authority or attest paths, durability, transaction order,
    witness provenance or manifest admission. Those remain separate owner gates.
    """
    return _load_signer(bootstrap_path, repo_root, bootstrap=True)


def _load_signer(bootstrap_path, repo_root, *, bootstrap):
    path, repo = Path(bootstrap_path), Path(repo_root).resolve()
    if not path.is_absolute():
        raise ValueError("generation_bootstrap_path_not_absolute")
    loaded = _load(path, repo, bootstrap=bootstrap)
    binding = loaded[2]
    policy = PeerCredentialPolicy({uid: f"consumer:{uid}" for uid in loaded[1]["consumer_uids"]})
    isolation = enforce_signer_process_isolation(policy, expected_signer_uid=binding.expected_uid,
                                                 expected_signer_gid=binding.expected_gid)
    if not isolation.accepted:
        raise ValueError("generation_bootstrap_isolation_rejected")
    return _InitialGenerationSigner(path, repo, loaded)


__all__ = ["load_initial_generation_anchor_signer", "load_initial_generation_bootstrap_signer"]
