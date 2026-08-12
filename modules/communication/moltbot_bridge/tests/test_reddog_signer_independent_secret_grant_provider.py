"""Security tests for independent secret-grant issuance and provider use."""

from __future__ import annotations

import ast
import json
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import asdict, replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from modules.communication.moltbot_bridge.src import (
    reddog_signer_independent_secret_grant_provider as provider_module,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    Ed25519SignatureVerifier,
    encode_ed25519_public_key,
    encode_ed25519_signature,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signer_backend import (
    Ed25519SignerBackend,
    bind_exact_signing_request,
)
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_protocol import (
    SIGNER_SOCKET_REQUEST_SCHEMA_VERSION,
    SignerPeerAttestation,
    handle_reddog_isolated_signer_socket_request,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    SigningRequest,
    SigningResponse,
    public_key_fingerprint,
)
from modules.communication.moltbot_bridge.src.reddog_signer_independent_secret_grant_provider import (
    IndependentGrantAuthorityBinding,
    IndependentSignerSecretGrantProvider,
)
from modules.communication.moltbot_bridge.src.reddog_signer_resolve_per_sign_backend import (
    ResolvePerSignBinding,
)
from modules.communication.moltbot_bridge.src.reddog_signer_audit_attestation import (
    SECRET_GRANT_AUDIT_ATTESTATION_PREFIX,
    canonical_signer_audit_attestation_input,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_access_grant_contract import (
    GRANT_SCHEMA,
    canonical_signer_secret_access_grant_input,
    signer_secret_access_grant_id,
    signer_secret_access_request_digest,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_issuance import (
    SignerSecretGrantAuthorityPolicy,
    build_secret_grant_signing_request,
    validate_secret_grant_signing_request,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_durable_nonce_store import (
    DurableSignerSecretGrantNonceStore,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_durable_rate_authority import (
    DurableSignerSecretGrantRateAuthority,
)
from modules.communication.moltbot_bridge.tests.test_reddog_external_signer_authoritative_use_lease import (
    INTEGRITY_KEY,
    NOW,
    _store,
)


class _AuditMac:
    def build(self, request, _signature, peer):
        return "audit:" + request.nonce + ":" + peer.peer_principal_id


class _Resolver:
    def __init__(self, key: str) -> None:
        self.key = key

    def resolve(self, principal_id: str, provider: str) -> str | None:
        return self.key if (principal_id, provider) == ("grant:owner", "local") else None


class _GrantClient:
    def __init__(
        self, key: Ed25519PrivateKey, *, valid_audit_attestation: bool = True
    ) -> None:
        self.key = key
        self.valid_audit_attestation = valid_audit_attestation
        self.calls = 0

    def sign(self, request: SigningRequest) -> SigningResponse:
        self.calls += 1
        public = _public(self.key)
        signature = encode_ed25519_signature(
            self.key.sign(request.signing_input.encode("utf-8"))
        )
        audit_mac = "audit:grant"
        attestation_input = canonical_signer_audit_attestation_input(
            signing_input=request.signing_input,
            signature=signature,
            audit_mac=audit_mac,
            signer_public_key=public,
            key_epoch="grant-epoch-1",
            requester_principal_id=request.requester_principal_id,
            domain_prefix=SECRET_GRANT_AUDIT_ATTESTATION_PREFIX,
        )
        audit_attestation = encode_ed25519_signature(
            self.key.sign(attestation_input.encode("utf-8"))
        )
        if not self.valid_audit_attestation:
            audit_attestation = "invalid-audit-attestation"
        return SigningResponse(
            accepted=True,
            signature=signature,
            signer_public_key=public,
            key_fingerprint=public_key_fingerprint(public),
            key_epoch="grant-epoch-1",
            audit_mac=audit_mac,
            audit_attestation_signature=audit_attestation,
            boundary_attested=True,
            requester_identity_attested=True,
            signer_loads_no_untrusted_code=True,
            no_secret_material_returned=True,
        )


def _public(key: Ed25519PrivateKey) -> str:
    return encode_ed25519_public_key(
        key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
    )


def _binding(store, grant_public: str) -> ResolvePerSignBinding:
    target_public = _public(Ed25519PrivateKey.from_private_bytes(bytes(range(32))))
    return ResolvePerSignBinding(
        issuer_principal_id="grant:owner",
        issuer_principal_provider="local",
        issuer_public_key=grant_public,
        signer_agent_id="signer:target",
        signer_profile_id="target-profile",
        signing_key_ref_hash="sha256:" + "1" * 64,
        audit_mac_key_ref_hash="sha256:" + "2" * 64,
        key_epoch="target-epoch-1",
        permission_snapshot_digest="sha256:" + "3" * 64,
        owner_config_id="sha256:" + "4" * 64,
        signer_generation_id="sha256:" + "5" * 64,
        signer_public_key=target_public,
        signer_key_fingerprint=public_key_fingerprint(target_public),
        replay_store_binding_digest=store.replay_store_binding_digest,
        replay_store_id=store.replay_store_id,
        replay_store_durability_receipt_id=store.durability_receipt_id,
        replay_store_instance_digest=store.replay_store_instance_digest,
    )


def _policy(binding: ResolvePerSignBinding) -> SignerSecretGrantAuthorityPolicy:
    return SignerSecretGrantAuthorityPolicy(
        **asdict(binding),
        issuer_key_epoch="grant-epoch-1",
        requester_principal_id="provider:grant-client",
        allowed_operations=("bounded_edit",),
        allowed_authority_tiers=("HIGH", "LOW"),
        consensus_required_tiers=("HIGH",),
        rate_limit_window_seconds=60,
        rate_limit_max_requests=10,
    )


def _target_request(
    *, tier: str = "LOW", consensus: str | None = None, nonce: str = "target-request-1"
) -> SigningRequest:
    return SigningRequest(
        signing_input="reddog-workauth.v1.{}",
        payload_digest="sha256:" + "a" * 64,
        signer_role="reddog",
        signer_public_key="target-key",
        requester_principal_id="worker:0102",
        nonce=nonce,
        key_epoch="target-epoch-1",
        requested_operation="bounded_edit",
        authority_tier=tier,
        consensus_receipt_digest=consensus,
    )


def _grant(
    request: SigningRequest,
    binding: ResolvePerSignBinding,
    *,
    nonce: str = "grant-nonce-0001",
) -> dict[str, Any]:
    value = {
        "schema_version": GRANT_SCHEMA,
        **asdict(binding),
        "signing_request_digest": signer_secret_access_request_digest(request.to_dict()),
        "requested_operation": request.requested_operation,
        "authority_tier": request.authority_tier,
        "attested_peer_principal_id": request.requester_principal_id,
        "nonce": nonce,
        "issued_at": NOW,
        "expires_at": NOW + 30,
        "grant_id": "",
        "signature": "pending-signature",
    }
    value["grant_id"] = signer_secret_access_grant_id(value)
    return value


def _peer(principal_id: str = "provider:grant-client") -> SignerPeerAttestation:
    return SignerPeerAttestation(
        peer_principal_id=principal_id,
        transport="unix_socket",
        credential_source="SO_PEERCRED",
        boundary_attested=True,
    )


def test_grant_domain_signs_only_with_exact_policy(tmp_path: Path) -> None:
    store = _store(tmp_path)
    private = Ed25519PrivateKey.generate()
    binding = _binding(store, _public(private))
    policy = _policy(binding)
    grant = _grant(_target_request(), binding)
    request = build_secret_grant_signing_request(
        grant, policy=policy, consensus_receipt_digest=None
    )
    backend = Ed25519SignerBackend(
        private_key=private,
        public_key=_public(private),
        key_epoch="grant-epoch-1",
        audit_mac_builder=_AuditMac(),
        proposal_clock=lambda: NOW,
        secret_grant_authority_policy=policy,
        secret_grant_rate_authority=DurableSignerSecretGrantRateAuthority(store),
    )

    response = backend.sign(request, _peer())

    assert response.accepted is True
    assert response.audit_attestation_signature
    assert Ed25519SignatureVerifier().verify(
        _public(private), request.signing_input, response.signature
    )
    assert validate_secret_grant_signing_request(
        request, policy, now_epoch=NOW
    ) is not None


def test_missing_policy_rejects_even_when_exact_request_bound(tmp_path: Path) -> None:
    store = _store(tmp_path)
    private = Ed25519PrivateKey.generate()
    binding = _binding(store, _public(private))
    request = build_secret_grant_signing_request(
        _grant(_target_request(), binding),
        policy=_policy(binding),
        consensus_receipt_digest=None,
    )
    backend = Ed25519SignerBackend(
        private_key=private,
        public_key=_public(private),
        key_epoch="grant-epoch-1",
        audit_mac_builder=_AuditMac(),
        proposal_clock=lambda: NOW,
    )

    response = bind_exact_signing_request(backend, request).sign(request, _peer())

    assert response.accepted is False


def test_high_tier_digest_is_not_treated_as_verified_consensus(tmp_path: Path) -> None:
    store = _store(tmp_path)
    private = Ed25519PrivateKey.generate()
    binding = _binding(store, _public(private))
    request = _target_request(tier="HIGH", consensus="sha256:" + "c" * 64)

    with pytest.raises(ValueError, match="consensus"):
        build_secret_grant_signing_request(
            _grant(request, binding),
            policy=_policy(binding),
            consensus_receipt_digest=request.consensus_receipt_digest,
        )


def test_grant_signer_peer_is_distinct_from_worker_beneficiary(tmp_path: Path) -> None:
    store = _store(tmp_path)
    private = Ed25519PrivateKey.generate()
    binding = _binding(store, _public(private))
    grant = _grant(_target_request(), binding)

    request = build_secret_grant_signing_request(
        grant, policy=_policy(binding), consensus_receipt_digest=None
    )

    assert request.requester_principal_id == "provider:grant-client"
    assert request.requester_principal_id != binding.signer_agent_id
    assert grant["attested_peer_principal_id"] == "worker:0102"


def test_grant_socket_requires_signed_provider_principal(tmp_path: Path) -> None:
    store = _store(tmp_path)
    private = Ed25519PrivateKey.generate()
    binding = _binding(store, _public(private))
    policy = _policy(binding)
    request = build_secret_grant_signing_request(
        _grant(_target_request(), binding),
        policy=policy,
        consensus_receipt_digest=None,
    )
    backend = Ed25519SignerBackend(
        private_key=private,
        public_key=_public(private),
        key_epoch="grant-epoch-1",
        audit_mac_builder=_AuditMac(),
        proposal_clock=lambda: NOW,
        secret_grant_authority_policy=policy,
        secret_grant_rate_authority=DurableSignerSecretGrantRateAuthority(store),
    )
    wire = (
        json.dumps(
            {
                "schema_version": SIGNER_SOCKET_REQUEST_SCHEMA_VERSION,
                "request": request.to_dict(),
            },
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")

    accepted = json.loads(
        handle_reddog_isolated_signer_socket_request(
            wire, peer=_peer(), backend=backend
        ).decode("utf-8")
    )
    rejected = json.loads(
        handle_reddog_isolated_signer_socket_request(
            wire, peer=_peer(binding.signer_agent_id), backend=backend
        ).decode("utf-8")
    )

    assert accepted["accepted"] is True
    assert rejected["accepted"] is False


def test_durable_rate_limit_survives_restart_and_concurrency(tmp_path: Path) -> None:
    store = _store(tmp_path)
    private = Ed25519PrivateKey.generate()
    binding = _binding(store, _public(private))
    policy = replace(_policy(binding), rate_limit_max_requests=1)

    def sign(index: int, rate_store=store) -> SigningResponse:
        target = _target_request(nonce=f"target-request-{index}")
        request = build_secret_grant_signing_request(
            _grant(target, binding, nonce=f"grant-nonce-{index:04d}"),
            policy=policy,
            consensus_receipt_digest=None,
        )
        backend = Ed25519SignerBackend(
            private_key=private,
            public_key=_public(private),
            key_epoch="grant-epoch-1",
            audit_mac_builder=_AuditMac(),
            proposal_clock=lambda: NOW,
            secret_grant_authority_policy=policy,
            secret_grant_rate_authority=DurableSignerSecretGrantRateAuthority(
                rate_store
            ),
        )
        return backend.sign(request, _peer())

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(sign, (1, 2)))
    assert sum(response.accepted for response in responses) == 1

    reopened = DurableSignerSecretGrantNonceStore(
        store._config,
        integrity_key=INTEGRITY_KEY,
        clock=lambda: NOW,
    )
    assert sign(3, reopened).accepted is False


def test_durable_replay_store_rejects_malformed_grant_mapping(tmp_path: Path) -> None:
    store = _store(tmp_path)

    assert store.consume_grant({"nonce": "missing-bindings"}) is False


def test_signer_rejects_missing_durable_rate_authority(tmp_path: Path) -> None:
    store = _store(tmp_path)
    private = Ed25519PrivateKey.generate()
    binding = _binding(store, _public(private))
    policy = _policy(binding)
    request = build_secret_grant_signing_request(
        _grant(_target_request(), binding),
        policy=policy,
        consensus_receipt_digest=None,
    )
    backend = Ed25519SignerBackend(
        private_key=private,
        public_key=_public(private),
        key_epoch="grant-epoch-1",
        audit_mac_builder=_AuditMac(),
        proposal_clock=lambda: NOW,
        secret_grant_authority_policy=policy,
    )

    assert backend.sign(request, _peer()).accepted is False


def test_signer_rejects_substituted_rate_store_instance(tmp_path: Path) -> None:
    store = _store(tmp_path / "policy")
    substituted = _store(tmp_path / "substituted")
    private = Ed25519PrivateKey.generate()
    binding = _binding(store, _public(private))
    policy = _policy(binding)
    request = build_secret_grant_signing_request(
        _grant(_target_request(), binding),
        policy=policy,
        consensus_receipt_digest=None,
    )
    backend = Ed25519SignerBackend(
        private_key=private,
        public_key=_public(private),
        key_epoch="grant-epoch-1",
        audit_mac_builder=_AuditMac(),
        proposal_clock=lambda: NOW,
        secret_grant_authority_policy=policy,
        secret_grant_rate_authority=DurableSignerSecretGrantRateAuthority(
            substituted
        ),
    )

    assert backend.sign(request, _peer()).accepted is False


def test_signer_rejects_store_shaped_rate_authority_without_consuming(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    private = Ed25519PrivateKey.generate()
    binding = _binding(store, _public(private))
    policy = _policy(binding)
    request = build_secret_grant_signing_request(
        _grant(_target_request(), binding),
        policy=policy,
        consensus_receipt_digest=None,
    )
    fake_store = SimpleNamespace(
        replay_store_id=policy.replay_store_id,
        durability_receipt_id=policy.replay_store_durability_receipt_id,
        replay_store_binding_digest=policy.replay_store_binding_digest,
        replay_store_instance_digest=policy.replay_store_instance_digest,
        consume_scoped_nonce=lambda **_kwargs: pytest.fail("must not consume"),
    )
    rate = object.__new__(DurableSignerSecretGrantRateAuthority)
    object.__setattr__(rate, "replay_store", fake_store)
    backend = Ed25519SignerBackend(
        private_key=private,
        public_key=_public(private),
        key_epoch="grant-epoch-1",
        audit_mac_builder=_AuditMac(),
        proposal_clock=lambda: NOW,
        secret_grant_authority_policy=policy,
        secret_grant_rate_authority=rate,
    )

    assert backend.sign(request, _peer()).accepted is False


def test_changed_grant_with_old_id_rejects(tmp_path: Path) -> None:
    store = _store(tmp_path)
    private = Ed25519PrivateKey.generate()
    binding = _binding(store, _public(private))
    grant = _grant(_target_request(), binding)
    grant["signer_agent_id"] = "signer:attacker"

    with pytest.raises(ValueError):
        build_secret_grant_signing_request(
            grant, policy=_policy(binding), consensus_receipt_digest=None
        )


def _owner_policy(binding: ResolvePerSignBinding) -> dict[str, Any]:
    return {
        "grant_authority_principal_id": binding.issuer_principal_id,
        "grant_authority_principal_provider": binding.issuer_principal_provider,
        "grant_authority_public_key": binding.issuer_public_key,
        "grant_requester_principal_id": "provider:grant-client",
        "revocation_authority_principal_id": "revocation:owner",
        "revocation_authority_principal_provider": "local",
        "revocation_authority_public_key": "revocation-key",
        "target_signer_agent_id": binding.signer_agent_id,
        "target_signer_profile_id": binding.signer_profile_id,
        "target_signer_public_key": binding.signer_public_key,
        "target_signer_key_fingerprint": binding.signer_key_fingerprint,
        "target_signer_key_epoch": binding.key_epoch,
        "target_signer_generation_id": binding.signer_generation_id,
        "signing_key_ref_hash": binding.signing_key_ref_hash,
        "audit_mac_key_ref_hash": binding.audit_mac_key_ref_hash,
        "permission_snapshot_digest": binding.permission_snapshot_digest,
        "owner_config_id": binding.owner_config_id,
        "allowed_operations": ["bounded_edit"],
        "allowed_authority_tiers": ["HIGH", "LOW"],
        "consensus_required_tiers": ["HIGH"],
        "rate_limit_window_seconds": 60,
        "rate_limit_max_requests": 10,
        "replay_store_id": binding.replay_store_id,
        "replay_store_durability_receipt_id": (
            binding.replay_store_durability_receipt_id
        ),
        "expires_at": NOW + 120,
    }


def _provider_for(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    store: DurableSignerSecretGrantNonceStore,
    private: Ed25519PrivateKey,
    client: _GrantClient,
    policy: Mapping[str, Any],
) -> IndependentSignerSecretGrantProvider:
    @contextmanager
    def lease(**_kwargs):
        yield SimpleNamespace(policy=policy, resolver=_Resolver(_public(private)))

    monkeypatch.setattr(
        provider_module, "lease_validated_owner_e0_current_admission", lease
    )
    return IndependentSignerSecretGrantProvider(
        repo_root=tmp_path,
        owner_config_path=tmp_path / "owner.json",
        owner_policy=policy,
        replay_store=store,
        grant_authority=IndependentGrantAuthorityBinding(
            client=client,
            principal_id="grant:owner",
            principal_provider="local",
            public_key=_public(private),
            key_epoch="grant-epoch-1",
            requester_principal_id="provider:grant-client",
        ),
        clock=lambda: NOW,
        nonce_factory=lambda: "grant-nonce-0001",
    )


def test_provider_holds_generation_lease_through_caller_use(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = _store(tmp_path)
    private = Ed25519PrivateKey.generate()
    client = _GrantClient(private)
    binding = _binding(store, _public(private))
    policy = _owner_policy(binding)
    active = {"value": False}

    @contextmanager
    def lease(**_kwargs):
        active["value"] = True
        try:
            yield SimpleNamespace(policy=policy, resolver=_Resolver(_public(private)))
        finally:
            active["value"] = False

    monkeypatch.setattr(
        provider_module, "lease_validated_owner_e0_current_admission", lease
    )
    provider = IndependentSignerSecretGrantProvider(
        repo_root=tmp_path,
        owner_config_path=tmp_path / "owner.json",
        owner_policy=policy,
        replay_store=store,
        grant_authority=IndependentGrantAuthorityBinding(
            client=client,
            principal_id="grant:owner",
            principal_provider="local",
            public_key=_public(private),
            key_epoch="grant-epoch-1",
            requester_principal_id="provider:grant-client",
        ),
        clock=lambda: NOW,
        nonce_factory=lambda: "grant-nonce-0001",
    )

    with provider.lease(_target_request()) as grant:
        assert active["value"] is True
        assert grant["signature"] != "pending-signature"
        assert Ed25519SignatureVerifier().verify(
            _public(private),
            canonical_signer_secret_access_grant_input(grant),
            grant["signature"],
        )
    assert active["value"] is False
    assert client.calls == 1


def test_provider_rejects_invalid_audit_attestation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = _store(tmp_path)
    private = Ed25519PrivateKey.generate()
    binding = _binding(store, _public(private))
    client = _GrantClient(private, valid_audit_attestation=False)
    provider = _provider_for(
        tmp_path,
        monkeypatch,
        store=store,
        private=private,
        client=client,
        policy=_owner_policy(binding),
    )

    with pytest.raises(ValueError, match="response_invalid"):
        with provider.lease(_target_request()):
            pass


def test_provider_rejects_replay_store_policy_mismatch_before_signing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = _store(tmp_path)
    private = Ed25519PrivateKey.generate()
    binding = _binding(store, _public(private))
    policy = _owner_policy(binding)
    policy["replay_store_id"] = "signer-grant-replay:attacker"
    client = _GrantClient(private)
    provider = _provider_for(
        tmp_path,
        monkeypatch,
        store=store,
        private=private,
        client=client,
        policy=policy,
    )

    with pytest.raises(ValueError, match="authority_binding_invalid"):
        with provider.lease(_target_request()):
            pass
    assert client.calls == 0


@pytest.mark.parametrize(
    "field,value",
    [
        ("principal_id", "revocation:owner"),
        ("public_key", "revocation-key"),
        ("requester_principal_id", "provider:attacker"),
    ],
)
def test_provider_rejects_authority_substitution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: str,
) -> None:
    store = _store(tmp_path)
    private = Ed25519PrivateKey.generate()
    binding = _binding(store, _public(private))
    policy = _owner_policy(binding)

    @contextmanager
    def lease(**_kwargs):
        yield SimpleNamespace(policy=policy, resolver=_Resolver(_public(private)))

    monkeypatch.setattr(
        provider_module, "lease_validated_owner_e0_current_admission", lease
    )
    values = {
        "client": _GrantClient(private),
        "principal_id": "grant:owner",
        "principal_provider": "local",
        "public_key": _public(private),
        "key_epoch": "grant-epoch-1",
        "requester_principal_id": "provider:grant-client",
    }
    values[field] = value
    provider = IndependentSignerSecretGrantProvider(
        repo_root=tmp_path,
        owner_config_path=tmp_path / "owner.json",
        owner_policy=policy,
        replay_store=store,
        grant_authority=IndependentGrantAuthorityBinding(**values),
        clock=lambda: NOW,
        nonce_factory=lambda: "grant-nonce-0001",
    )

    with pytest.raises(ValueError):
        with provider.lease(_target_request()):
            pass


def test_new_secret_grant_modules_are_bounded_and_keyless() -> None:
    root = Path(provider_module.__file__).resolve().parent
    names = (
        "reddog_signer_secret_grant_authority_policy.py",
        "reddog_signer_secret_grant_issuance.py",
        "reddog_signer_secret_grant_signer_admission.py",
        "reddog_signer_secret_grant_durable_rate_authority.py",
        "reddog_signer_independent_secret_grant_binding.py",
        "reddog_signer_independent_secret_grant_verification.py",
        "reddog_signer_independent_secret_grant_provider.py",
    )
    denied_imports = {"os", "subprocess", "socket"}
    for name in names:
        source = (root / name).read_text(encoding="utf-8")
        assert len(source.splitlines()) <= 200
        tree = ast.parse(source)
        imported = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        assert imported.isdisjoint(denied_imports)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert node.end_lineno - node.lineno + 1 <= 50
