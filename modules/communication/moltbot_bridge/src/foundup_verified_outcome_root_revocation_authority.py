"""Opaque server authority for current-generation revocation validation."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Mapping

from modules.communication.moltbot_bridge.src.reddog_signer_owner_e0_current_selection import (
    ValidatedOwnerE0Lease,
    lease_validated_owner_e0_current_admission,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_contract import (
    _build_process_local_registry,
)


@dataclass(frozen=True)
class _AuthorityState:
    owner_config_path: Path
    repo_root: Path


_issue_authority, _lookup_authority = _build_process_local_registry(
    "root_revocation_service_authority_unverified"
)
del _build_process_local_registry


class RootRevocationServiceAuthority:
    """Process-local proof that root selected the policy validation source."""

    __slots__ = ("__weakref__",)

    def __new__(cls, *_args: Any, **_kwargs: Any) -> "RootRevocationServiceAuthority":
        raise TypeError("root_revocation_service_authority_factory_required")

    def __copy__(self) -> "RootRevocationServiceAuthority":
        raise TypeError("root_revocation_service_authority_copy_forbidden")

    def __deepcopy__(self, _memo: Any) -> "RootRevocationServiceAuthority":
        raise TypeError("root_revocation_service_authority_copy_forbidden")

    def __reduce__(self) -> Any:
        raise TypeError("root_revocation_service_authority_pickle_forbidden")


def _create_root_revocation_service_authority(
    *, owner_config_path: Path | str, repo_root: Path | str,
) -> RootRevocationServiceAuthority:
    repo = Path(repo_root).resolve()
    owner = Path(owner_config_path).resolve()
    if repo == owner or repo in owner.parents:
        raise ValueError("root_revocation_owner_config_path_invalid")
    authority = object.__new__(RootRevocationServiceAuthority)
    _issue_authority(authority, _AuthorityState(owner, repo))
    return authority


@contextmanager
def lease_root_revocation_policy(
    authority: object, policy: Mapping[str, Any],
) -> Iterator[ValidatedOwnerE0Lease]:
    state = _lookup_authority(authority)
    with lease_validated_owner_e0_current_admission(
        owner_config_path=state.owner_config_path,
        repo_root=state.repo_root,
        policy=policy,
    ) as lease:
        yield lease


def root_revocation_authority_repo(authority: object) -> Path:
    return _lookup_authority(authority).repo_root


def root_revocation_grant_identity(authority, policy, snapshot):
    """Read the protected assignment; caller already holds current E0 lease."""
    from .reddog_signer_system_service_manifest_selection_loader import _load_owner_config
    from .reddog_signer_system_service_wsp71_resolver_supply import _require_descriptor_policy

    state = _lookup_authority(authority)
    owner = _load_owner_config(state.owner_config_path, repo=state.repo_root)
    _require_descriptor_policy(snapshot.descriptor, policy)
    raw = owner["independent_grant_authority"]
    target = owner["verified_outcome_authority"]
    if (owner["config_id"] != policy["owner_config_id"]
            or target["descriptor"] != snapshot.descriptor
            or target["signer_principal_id"] != snapshot.signer_principal_id
            or target["signer_uid"] != snapshot.signer_uid
            or target["signer_gid"] != snapshot.signer_gid
            or raw["authority_service_uid"] == snapshot.signer_uid):
        raise ValueError("root_revocation_grant_owner_mismatch")
    return raw["authority_service_uid"], raw["authority_service_gid"]


def _require_grant_load(request, peer, identity, policy):
    from .reddog_signer_socket_peer_credential_attestor import KernelPeerIdentity
    from .reddog_ed25519_signature_verifier_backend import Ed25519SignatureVerifier
    from .foundup_verified_outcome_root_revocation_protocol import OP_LOAD, GRANT_PEER_PRINCIPAL, canonical_signer_input

    if (request.operation != OP_LOAD or type(peer) is not KernelPeerIdentity
            or peer.attestation.boundary_attested is not True
            or peer.attestation.peer_principal_id != GRANT_PEER_PRINCIPAL
            or (peer.uid, peer.gid) != identity
            or request.requester_principal_id != policy["grant_authority_principal_id"]
            or request.requester_key_epoch != policy["grant_authority_key_epoch"]
            or Ed25519SignatureVerifier().verify(policy["grant_authority_public_key"],
                canonical_signer_input(request), request.signer_instance_signature) is not True):
        raise ValueError("root_revocation_grant_load_identity_invalid")


def _require_issuer_epoch_current(request, state, lease, repo, now_epoch):
    """Check installed signed state directly; never RPC back into this LOAD."""
    from .reddog_signer_secret_grant_revocation_authority_reader import SignerGrantRevocationAuthorityReader
    from .reddog_sqlite_monotonic_authority_store import SqliteMonotonicAuthorityReader
    from .foundup_verified_outcome_root_revocation_validation import verified_root_revocation_snapshot, revocation_high_water

    binding = lease.revocation_binding
    local = SignerGrantRevocationAuthorityReader(binding, repo_root=repo).state()
    current = verified_root_revocation_snapshot(local.current, binding,
        lease.policy, lease.resolver, now_epoch, fresh=True)
    if local.pending is not None or current is None:
        raise ValueError("root_revocation_grant_state_unavailable")
    high = revocation_high_water(current)
    witness = SqliteMonotonicAuthorityReader(binding.witness_path,
        allowed_root=binding.witness_root, repo_root=repo, store_id=binding.witness_store_id,
        durability_receipt_id=binding.witness_durability_receipt_id)
    if (witness.load(binding.witness_binding_digest()) != high
            or state.load(binding.anchor_binding_digest()) != high
            or request.requester_key_epoch in current["revoked_key_epochs"]):
        raise ValueError("root_revocation_grant_epoch_rejected")


__all__ = [
    "RootRevocationServiceAuthority",
    "lease_root_revocation_policy",
    "root_revocation_authority_repo",
]
