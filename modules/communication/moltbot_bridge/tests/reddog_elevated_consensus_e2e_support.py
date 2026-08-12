"""Production-seam fixtures for elevated-consensus end-to-end tests."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    Ed25519SignatureVerifier,
    encode_ed25519_public_key,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signer_backend import (
    Ed25519SignerBackend,
)
from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_signer_verification import (
    ElevatedConsensusSignerAuthority,
)
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_client import (
    RedDogIsolatedSignerSocketClient,
)
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_protocol import (
    SignerPeerAttestation,
    handle_reddog_isolated_signer_socket_request,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    SigningRequest,
)
from modules.communication.moltbot_bridge.src.reddog_signer_independent_secret_grant_binding import (
    build_secret_grant_authority_policy,
)
from modules.communication.moltbot_bridge.src.reddog_signer_independent_secret_grant_provider import (
    IndependentGrantAuthorityBinding,
    IndependentSignerSecretGrantProvider,
)
from modules.communication.moltbot_bridge.src.reddog_signer_key_provider_dryrun import (
    SignerKeyProviderDryRunResult,
)
from modules.communication.moltbot_bridge.src.reddog_signer_resolve_per_sign_backend import (
    ResolvePerSignBinding,
    ResolvePerSignSignerBackend,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_access_grant import (
    SignerSecretAccessGrantBoundary,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_durable_rate_authority import (
    DurableSignerSecretGrantRateAuthority,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_revocation_oracle import (
    AtomicSignerSecretGrantRevocationOracle,
)
from modules.communication.moltbot_bridge.tests.test_reddog_external_signer_authoritative_use_lease import (
    NOW,
    _store,
)
from modules.communication.moltbot_bridge.tests.reddog_elevated_consensus_e2e_policy_support import (
    build_binding,
    owner_policy,
)


def public_key(key: Ed25519PrivateKey) -> str:
    return encode_ed25519_public_key(key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    ))


class Resolver:
    def __init__(self, principal: str, provider: str, key: str) -> None:
        self.binding = (principal, provider, key)

    def resolve(self, principal_id: str, provider: str) -> str | None:
        expected_principal, expected_provider, key = self.binding
        return key if (principal_id, provider) == (
            expected_principal, expected_provider
        ) else None


class AuditMac:
    def build(self, request: SigningRequest, _signature: str, peer: Any) -> str:
        value = (request.nonce + ":" + peer.peer_principal_id).encode("utf-8")
        return "audit-mac-v1:" + hashlib.sha256(value).hexdigest()


@dataclass
class EphemeralFactory:
    binding: ResolvePerSignBinding
    backend: Ed25519SignerBackend

    @property
    def signer_agent_id(self) -> str:
        return self.binding.signer_agent_id

    @property
    def permission_snapshot_digest(self) -> str:
        return self.binding.permission_snapshot_digest

    def __call__(self) -> SignerKeyProviderDryRunResult:
        item = self.binding
        return SignerKeyProviderDryRunResult(
            ok=True, rejection_code=None,
            signer_profile_id=item.signer_profile_id, key_epoch=item.key_epoch,
            public_key=item.signer_public_key,
            key_fingerprint=item.signer_key_fingerprint,
            signing_key_ref_hash=item.signing_key_ref_hash,
            audit_mac_key_ref_hash=item.audit_mac_key_ref_hash,
            ttl_remaining_seconds=60, secret_values_returned=False,
            backend=self.backend,
        )


def build_route(
    root: Path,
    role: str,
    target_key: Ed25519PrivateKey,
    grant_key: Ed25519PrivateKey,
    consensus_authority: ElevatedConsensusSignerAuthority,
) -> tuple[IndependentSignerSecretGrantProvider, RedDogIsolatedSignerSocketClient, dict[str, Any]]:
    store = _store(root)
    target_public, grant_public = public_key(target_key), public_key(grant_key)
    binding = build_binding(store, role, target_public, grant_public)
    policy = owner_policy(binding)
    provider = _grant_provider(
        root, role, store, binding, policy, grant_key, consensus_authority
    )
    return provider, _target_client(root, store, binding, target_key), policy


def _grant_provider(
    root: Path, role: str, store: Any, binding: ResolvePerSignBinding,
    policy: dict[str, Any], grant_key: Ed25519PrivateKey,
    consensus_authority: ElevatedConsensusSignerAuthority,
) -> IndependentSignerSecretGrantProvider:
    grant_public = public_key(grant_key)
    grant_policy = build_secret_grant_authority_policy(
        policy, binding, store,
        authority_principal_id=binding.issuer_principal_id,
        authority_principal_provider=binding.issuer_principal_provider,
        authority_public_key=grant_public,
        authority_key_epoch="grant-epoch-1",
        requester_principal_id="provider:grant-client",
    )
    grant_backend = Ed25519SignerBackend(
        private_key=grant_key, public_key=grant_public,
        key_epoch="grant-epoch-1", audit_mac_builder=AuditMac(),
        proposal_clock=lambda: NOW, secret_grant_authority_policy=grant_policy,
        secret_grant_rate_authority=DurableSignerSecretGrantRateAuthority(store),
        elevated_consensus_signer_authority=consensus_authority,
    )
    grant_client = _socket_client(root / "grant.sock", grant_backend, "provider:grant-client")
    return IndependentSignerSecretGrantProvider(
        repo_root=root, owner_config_path=root / f"owner-{role}.json",
        owner_policy=policy, replay_store=store,
        grant_authority=IndependentGrantAuthorityBinding(
            client=grant_client, principal_id=binding.issuer_principal_id,
            principal_provider=binding.issuer_principal_provider, public_key=grant_public,
            key_epoch="grant-epoch-1", requester_principal_id="provider:grant-client",
        ), clock=lambda: NOW, nonce_factory=lambda: f"grant-nonce-{role}-0001",
    )


def _target_client(
    root: Path, store: Any, binding: ResolvePerSignBinding,
    target_key: Ed25519PrivateKey,
) -> RedDogIsolatedSignerSocketClient:
    target_backend = ResolvePerSignSignerBackend(
        binding=binding,
        grant_boundary=SignerSecretAccessGrantBoundary(
            nonce_store=store, revocation_oracle=AtomicSignerSecretGrantRevocationOracle(),
            clock=lambda: NOW,
        ),
        signature_verifier=Ed25519SignatureVerifier(),
        principal_key_resolver=Resolver(binding.issuer_principal_id, binding.issuer_principal_provider, binding.issuer_public_key),
        backend_factory=EphemeralFactory(
            binding, Ed25519SignerBackend(
                private_key=target_key, public_key=binding.signer_public_key,
                key_epoch="epoch-1", audit_mac_builder=AuditMac(),
                proposal_clock=lambda: NOW,
            ),
        ),
    )
    return _socket_client(
        root / "target.sock", target_backend, "github:mjtrout"
    )


def _socket_client(path: Path, backend: Any, principal: str) -> RedDogIsolatedSignerSocketClient:
    peer = SignerPeerAttestation(principal, "unix_socket", "SO_PEERCRED", True)
    return RedDogIsolatedSignerSocketClient(
        socket_path=path,
        connector=lambda _p, payload, _t, limit: handle_reddog_isolated_signer_socket_request(
            payload, peer=peer, backend=backend, max_request_bytes=limit
        ),
        max_response_bytes=32768,
    )
