"""Administrative first-manifest enrollment, separate from work authorization.

The installer approves one exact source bundle and artifact set. This loader
does not issue work, publication or consensus evidence. Initial generation CAS
remains mandatory; repeating the same signature does not create another grant.
"""
from __future__ import annotations

import json
import sys
import time
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from types import MappingProxyType

from .reddog_ed25519_signature_verifier_backend import (
    Ed25519SignatureVerifier, decode_ed25519_public_key, encode_ed25519_signature,
)
from .reddog_runtime_artifact_manifest_contract import (
    SCHEMA_VERSION_INITIAL, SCHEMA_VERSION_INITIAL_V2, SIGNER_ROLE_INITIAL, SIGNING_OPERATION_INITIAL,
    REQUIRED_INSTALLED_GRANT_RUNTIME_ARTIFACTS, validate_signed_payload,
    canonical_json, canonical_signing_input, digest, is_sha256, manifest_id_for,
    raw_digest, validate_freshness, validate_unsigned_payload,
)
from .reddog_signer_delegated_authority_runtime import (
    SigningResponse, public_key_fingerprint,
)
from .reddog_signer_key_provider_dryrun import _decode_ed25519_private_key, _public_key_text
from .reddog_signer_process_isolation_gate import enforce_signer_process_isolation
from .reddog_signer_socket_peer_credential_attestor import PeerCredentialPolicy
from .reddog_signer_system_service_manifest_selection_loader import _read_root_owned_bytes
from .reddog_signer_system_service_wsp71_resolver_supply import _startup_permission
from .reddog_signed_runtime_artifact_manifest import RuntimeArtifactManifestSigningContext
from modules.infrastructure.secrets_mcp.src.systemd_credential_secret_resolver import (
    SystemdCredentialBinding, SystemdCredentialSecretResolver,
)
from modules.infrastructure.shared_utilities.reddog_runtime_artifact_generation import (
    reddog_runtime_artifact_generation_lock,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    validate_runtime_artifact_path, validate_runtime_root_path,
)

SCHEMA_VERSION = "reddog_initial_runtime_manifest_approval.v1"
SCHEMA_VERSION_V2 = "reddog_initial_runtime_manifest_approval.v2"
PURPOSE = "initial_runtime_manifest"
AUTHORITY_TIER = "INITIAL_ENROLLMENT"
_FIELDS = {"schema_version", "repo_root_digest", "runtime_root", "source_commit_sha",
           "source_files", "manifest_spec", "credential_binding", "permission", "consumer_uids"}
_SPEC_FIELDS = {"issuer_principal_id", "signer_public_key", "key_epoch", "nonce",
                "issued_at", "expires_at", "authority_profile_digest",
                "signer_service_config_digest", "artifacts"}
_SPEC_FIELDS_V2 = _SPEC_FIELDS | {"runtime_profile", "owner_config_id",
                                "grant_authority_installed_runtime_descriptor_digest"}


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("initial_manifest_duplicate_key")
        result[key] = value
    return result


def _read_policy(path, repo):
    if not path.is_absolute():
        raise ValueError("initial_manifest_approval_path_invalid")
    root = validate_runtime_root_path(path.parent, repo_root=repo)
    target = validate_runtime_artifact_path(path, allowed_root=root, repo_root=repo)
    raw = _read_root_owned_bytes(target, root)
    value = json.loads(raw.decode("ascii"), object_pairs_hook=_unique)
    if (type(value) is not dict or set(value) != _FIELDS
            or value["schema_version"] not in {SCHEMA_VERSION, SCHEMA_VERSION_V2}):
        raise ValueError("initial_manifest_approval_shape_invalid")
    if value["repo_root_digest"] != raw_digest(str(repo).encode()):
        raise ValueError("initial_manifest_repo_mismatch")
    runtime = validate_runtime_root_path(value["runtime_root"], repo_root=repo)
    if str(runtime) != value["runtime_root"]:
        raise ValueError("initial_manifest_runtime_not_canonical")
    return raw, value, runtime


def _manifest(raw, policy, runtime):
    spec = policy["manifest_spec"]
    installed = policy["schema_version"] == SCHEMA_VERSION_V2
    if type(spec) is not dict or set(spec) != (_SPEC_FIELDS_V2 if installed else _SPEC_FIELDS):
        raise ValueError("initial_manifest_spec_invalid")
    payload = dict(spec, schema_version=SCHEMA_VERSION_INITIAL_V2 if installed else SCHEMA_VERSION_INITIAL,
                   repo_root_digest=policy["repo_root_digest"],
                   runtime_root_digest=raw_digest(str(runtime).encode()),
                   source_commit_sha=policy["source_commit_sha"],
                   enrollment_approval_digest=raw_digest(raw),
                   artifact_count=len(spec["artifacts"]),
                   artifact_generation_digest=digest(spec["artifacts"]),
                   signer_key_fingerprint=public_key_fingerprint(spec["signer_public_key"]))
    payload["manifest_id"] = manifest_id_for(payload)
    payload["revision"] = payload["manifest_id"][7:]
    validate_unsigned_payload(payload)
    if decode_ed25519_public_key(payload["signer_public_key"]) is None:
        raise ValueError("initial_manifest_key_invalid")
    return payload


def _check_installed_approval(repo, policy, runtime, payload):
    """Root approval binds exact installed metadata; it does not prove runtime confinement."""
    if policy["schema_version"] != SCHEMA_VERSION_V2:
        return
    from .reddog_grant_authority_service_artifact_contract import validate_installed_grant_service_artifacts
    bundle = validate_installed_grant_service_artifacts({name: _read_root_owned_bytes(runtime / name, runtime)
        for name in REQUIRED_INSTALLED_GRANT_RUNTIME_ARTIFACTS})
    config, descriptor = bundle["config"], bundle["source_descriptor"]
    if (bundle["config_digest"] != payload["signer_service_config_digest"]
            or bundle["installed_runtime_descriptor_digest"] != payload["grant_authority_installed_runtime_descriptor_digest"]
            or config["owner_config_id"] != payload["owner_config_id"]
            or config["repo_root_digest"] != policy["repo_root_digest"]
            or descriptor["source_commit_sha"] != policy["source_commit_sha"]
            or descriptor["source_files"] != policy["source_files"]
            or config["public_key"] == payload["signer_public_key"]):
        raise ValueError("initial_installed_approval_binding_invalid")


def verify_initial_runtime_manifest_approval(*, approval_path, repo_root,
                                            expected_approval_digest, manifest):
    """Verify a caller-pinned protected approval without loading signer custody.

    The caller must obtain the path and expected digest from its authenticated
    owner contract, never from the manifest being checked. No grant is issued.
    """
    repo, path = Path(repo_root).resolve(), Path(approval_path)
    raw, policy, runtime = _read_policy(path, repo)
    if not is_sha256(expected_approval_digest) or raw_digest(raw) != expected_approval_digest:
        raise ValueError("initial_manifest_approval_binding_invalid")
    expected = _manifest(raw, policy, runtime)
    _custody(policy, expected)  # Validate permission metadata without resolving its credential.
    checked = validate_signed_payload(manifest)
    if {k: v for k, v in checked.items() if k != "signature"} != expected:
        raise ValueError("initial_manifest_binding_mismatch")
    validate_freshness(expected, now_epoch=int(time.time()), max_ttl_seconds=300)
    _check_sources(repo, policy["source_files"])
    _check_installed_approval(repo, policy, runtime, expected)
    if not Ed25519SignatureVerifier().verify(expected["signer_public_key"],
            canonical_signing_input(expected), checked["signature"]):
        raise ValueError("initial_manifest_signature_invalid")
    if _read_policy(path, repo)[0] != raw:
        raise ValueError("initial_manifest_approval_changed")
    validate_freshness(expected, now_epoch=int(time.time()), max_ttl_seconds=300)
    return MappingProxyType(expected)


def _custody(policy, payload):
    metadata = dict(policy["credential_binding"])
    ids = metadata.get("credential_ids")
    if type(ids) is not list or len(ids) != 1 or type(ids[0]) is not str or not ids[0]:
        raise ValueError("initial_manifest_credential_scope_invalid")
    metadata["credential_ids"] = frozenset(ids)
    binding = SystemdCredentialBinding(**metadata)
    identity = {"public_key": payload["signer_public_key"], "key_epoch": payload["key_epoch"]}
    _startup_permission(policy["permission"], binding, PURPOSE, identity=identity)
    if any(policy["permission"][name] != payload[name] for name in ("issued_at", "expires_at")):
        raise ValueError("initial_manifest_permission_window_invalid")
    uids = policy["consumer_uids"]
    if (type(uids) is not list or not 1 <= len(uids) <= 32
            or any(type(uid) is not int or not 0 < uid < 2**32-1 for uid in uids)
            or len(set(uids)) != len(uids) or binding.expected_uid in uids):
        raise ValueError("initial_manifest_consumer_scope_invalid")
    return binding


def _check_sources(repo, sources):
    """Root installation attests Git provenance; recheck installed source bytes.

    The installer must derive this inventory from its pinned source closure.
    A commit-shaped string alone is not provenance verification.
    """
    if type(sources) is not dict or not 1 <= len(sources) <= 4096:
        raise ValueError("initial_manifest_source_inventory_invalid")
    for name, expected in sources.items():
        relative = PurePosixPath(name)
        if (type(name) is not str or not relative.parts or relative.is_absolute() or ".." in relative.parts
                or str(relative) != name or "\\" in name or ":" in name or not is_sha256(expected)):
            raise ValueError("initial_manifest_source_path_invalid")
        path = repo.joinpath(*relative.parts)
        # Empty package initializers are valid source only with an exact digest.
        if raw_digest(_read_root_owned_bytes(path, path.parent, allow_empty=True)) != expected:
            raise ValueError("initial_manifest_source_changed")
    own_path = Path(__file__).resolve()
    if not own_path.is_relative_to(repo) or own_path.relative_to(repo).as_posix() not in sources:
        raise ValueError("initial_manifest_authority_source_unbound")
    for name, module in tuple(sys.modules.items()):
        filename = getattr(module, "__file__", None)
        if not filename:
            continue
        path = Path(filename).resolve()
        if name.startswith(("modules.", "holo_index.")) and not path.is_relative_to(repo):
            raise ValueError("initial_manifest_loaded_source_outside_bundle")
        if path.is_relative_to(repo) and path.relative_to(repo).as_posix() not in sources:
            raise ValueError("initial_manifest_loaded_source_unbound")


class _State:
    def __init__(self, path, repo, raw, policy, runtime, payload, binding):
        self.path, self.repo, self.raw = path, repo, raw
        self.policy, self.runtime, self.payload, self.binding = policy, runtime, payload, binding
        self.wall, self.mono = time.time(), time.monotonic()
        self.deadline = self.mono + payload["expires_at"] - self.wall
        self.check()
        self.resolver = SystemdCredentialSecretResolver(binding)

    def check(self):
        self.check_time()
        if _read_policy(self.path, self.repo)[0] != self.raw:
            raise ValueError("initial_manifest_approval_changed")
        _check_installed_approval(self.repo, self.policy, self.runtime, self.payload)
        self.check_time()

    def check_time(self):
        wall, mono = time.time(), time.monotonic()
        if wall < self.wall or mono < self.mono or mono >= self.deadline:
            raise ValueError("initial_manifest_clock_or_expiry_invalid")
        validate_freshness(self.payload, now_epoch=int(wall), max_ttl_seconds=300)

    def values(self):
        self.check()
        return MappingProxyType({"repo_root": self.repo, "runtime_root": self.runtime,
            "signer_public_key": self.payload["signer_public_key"],
            "issuer_principal_id": self.payload["issuer_principal_id"],
            "key_epoch": self.payload["key_epoch"], "max_ttl_seconds": 300,
            "authority_profile_digest": self.payload["authority_profile_digest"],
            "signer_service_config_digest": self.payload["signer_service_config_digest"],
            "initial_manifest": json.loads(canonical_json(self.payload))})

    def sign(self, request):
        self.check()
        signing_input = canonical_signing_input(self.payload)
        expected = {"signing_input": signing_input, "payload_digest": digest({"signing_input": signing_input}),
            "signer_role": SIGNER_ROLE_INITIAL, "signer_public_key": self.payload["signer_public_key"],
            "requester_principal_id": self.payload["issuer_principal_id"], "nonce": self.payload["nonce"],
            "key_epoch": self.payload["key_epoch"], "requested_operation": SIGNING_OPERATION_INITIAL,
            "authority_tier": AUTHORITY_TIER, "consensus_receipt_digest": None}
        if request.to_dict() != expected:
            raise ValueError("initial_manifest_signing_scope_invalid")
        _check_sources(self.repo, self.policy["source_files"])
        self.check()
        result = self.resolver.resolve(self.policy["permission"]["reference"],
                                       requester_id=self.binding.expected_requester)
        if result.success is not True:
            raise ValueError("initial_manifest_custody_rejected")
        self.check()
        key = _decode_ed25519_private_key(result.get_value())
        if key is None or _public_key_text(key) != self.payload["signer_public_key"]:
            raise ValueError("initial_manifest_custody_key_mismatch")
        signature = encode_ed25519_signature(key.sign(signing_input.encode("ascii")))
        del key, result
        self.check()
        return SigningResponse(accepted=True, signature=signature,
            signer_public_key=self.payload["signer_public_key"], key_epoch=self.payload["key_epoch"],
            boundary_attested=True, requester_identity_attested=True,
            signer_loads_no_untrusted_code=True, no_secret_material_returned=True)


def _context(state):
    """Keep mutable custody state out of public capability/client attributes."""
    capability = object()

    class Boundary:
        __slots__ = ()

        def require(self, value):
            if value is not capability:
                raise ValueError("initial_manifest_authority_unverified")
            return state.values()

        def revalidate(self, value, *, now_epoch):
            values = self.require(value)
            validate_freshness(state.payload, now_epoch=now_epoch, max_ttl_seconds=300)
            return values

        @contextmanager
        def revalidation_fence(self, value, *, now_epoch):
            self.revalidate(value, now_epoch=now_epoch)
            with reddog_runtime_artifact_generation_lock(state.runtime, repo_root=state.repo, allow_sealed=True):
                _check_sources(state.repo, state.policy["source_files"])
                yield self.require(value)
                self.require(value)

    class Client:
        __slots__ = ()

        def sign(self, request):
            return state.sign(request)

    return RuntimeArtifactManifestSigningContext(signer=Client(),
        signature_verifier=Ed25519SignatureVerifier(), authority=capability,
        authority_boundary=Boundary(), authority_tier=AUTHORITY_TIER)


def load_initial_runtime_manifest_signing_context(*, approval_path, repo_root):
    """Consume protected installation approval; never issue a work grant.

    Requires a separately isolated signer UID and fresh systemd custody. The
    administrative installer owns source provenance and issuer identity. Workers
    cannot install approval. Same-process/root compromise is outside this boundary.
    """
    path, repo = Path(approval_path), Path(repo_root).resolve()
    raw, policy, runtime = _read_policy(path, repo)
    payload = _manifest(raw, policy, runtime)
    _check_installed_approval(repo, policy, runtime, payload)
    binding = _custody(policy, payload)
    validate_freshness(payload, now_epoch=int(time.time()), max_ttl_seconds=300)
    _check_sources(repo, policy["source_files"])
    peers = PeerCredentialPolicy({uid: f"consumer:{uid}" for uid in policy["consumer_uids"]})
    isolation = enforce_signer_process_isolation(peers, expected_signer_uid=binding.expected_uid,
                                                expected_signer_gid=binding.expected_gid)
    if isolation.accepted is not True:
        raise ValueError("initial_manifest_isolation_rejected")
    return _context(_State(path, repo, raw, policy, runtime, payload, binding))
