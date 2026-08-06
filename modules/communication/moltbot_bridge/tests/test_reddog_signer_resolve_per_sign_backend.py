from __future__ import annotations

import json
import ast
import shutil
import threading
from dataclasses import replace
from pathlib import Path
from typing import Any, Mapping

import pytest

from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_protocol import (
    SIGNER_SOCKET_REQUEST_SCHEMA_VERSION_V2,
    SignerPeerAttestation,
    handle_reddog_isolated_signer_socket_request,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    SigningRequest,
    SigningResponse,
    public_key_fingerprint,
)
from modules.communication.moltbot_bridge.src.reddog_signer_key_provider_dryrun import (
    SignerKeyProviderDryRunResult,
)
from modules.communication.moltbot_bridge.src.reddog_signer_resolve_per_sign_backend import (
    REJECT_EPHEMERAL_BACKEND_INVALID,
    REJECT_SECRET_GRANT_INVALID,
    REJECT_SECRET_GRANT_REQUIRED,
    REJECT_SECRET_RESOLUTION_FAILED,
    ResolvePerSignBinding,
    ResolvePerSignSignerBackend,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_access_grant import (
    GRANT_SCHEMA,
    SignerSecretAccessGrantBoundary,
    canonical_signer_secret_access_grant_input,
    signer_secret_access_grant_id,
    signer_secret_access_request_digest,
)
from modules.communication.moltbot_bridge.src.reddog_proposal_authenticity_nonce_store import (
    AtomicProposalAuthenticityNonceStore,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_durable_nonce_store import (
    DurableSignerSecretGrantNonceStore,
    SignerGrantReplayStoreConfig,
)
from modules.communication.moltbot_bridge.src.reddog_sqlite_monotonic_authority_store import (
    SqliteMonotonicAuthorityStore,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_revocation_oracle import (
    AtomicSignerSecretGrantRevocationOracle,
)

NOW = 1_780_000_000
INTEGRITY_KEY = b"grant-integrity-key-32-bytes!!!!"
SOURCE_ROOT = Path(__file__).parents[1] / "src"
SOURCES = tuple(
    SOURCE_ROOT / name
    for name in (
        "reddog_signer_resolve_per_sign_backend.py",
        "reddog_ed25519_signer_policy_gate.py",
        "reddog_signer_resolve_per_sign_validation.py",
        "reddog_signer_secret_grant_durable_nonce_store.py",
        "reddog_signer_secret_grant_revocation_oracle.py",
        "reddog_signer_wsp71_ephemeral_backend_factory.py",
    )
)
PROTOCOL_SOURCE = SOURCE_ROOT / "reddog_isolated_signer_socket_protocol.py"


def _digest(character: str) -> str:
    return "sha256:" + character * 64


def _request(**overrides: Any) -> SigningRequest:
    values = {
        "signing_input": "reddog-workauth.v1.{}",
        "payload_digest": _digest("a"),
        "signer_role": "reddog",
        "signer_public_key": "public-key-v1:signer",
        "requester_principal_id": "principal:founder",
        "nonce": "request-nonce-1",
        "key_epoch": "epoch-1",
        "requested_operation": "write_repo",
        "authority_tier": "HIGH",
        "consensus_receipt_digest": _digest("b"),
    }
    values.update(overrides)
    return SigningRequest(**values)


def _binding(
    nonce_store: DurableSignerSecretGrantNonceStore | None = None,
) -> ResolvePerSignBinding:
    return ResolvePerSignBinding(
        issuer_principal_id="principal:founder",
        issuer_principal_provider="github",
        issuer_public_key="public-key-v1:issuer",
        signer_agent_id="signer:reddog",
        signer_profile_id="reddog-work-authority",
        signing_key_ref_hash=_digest("1"),
        audit_mac_key_ref_hash=_digest("2"),
        key_epoch="epoch-1",
        permission_snapshot_digest=_digest("3"),
        owner_config_id=_digest("4"),
        signer_generation_id=_digest("5"),
        signer_public_key="public-key-v1:signer",
        signer_key_fingerprint=public_key_fingerprint(
            "public-key-v1:signer"
        ),
        replay_store_binding_digest=_digest("7"),
        replay_store_id="signer-grant-replay:test",
        replay_store_durability_receipt_id=_digest("8"),
        replay_store_instance_digest=(
            nonce_store.replay_store_instance_digest
            if nonce_store is not None
            else _digest("9")
        ),
    )


def _grant(
    request: SigningRequest,
    nonce_store: DurableSignerSecretGrantNonceStore | None = None,
    **overrides: Any,
) -> dict[str, Any]:
    value = {
        "schema_version": GRANT_SCHEMA,
        **_binding(nonce_store).__dict__,
        "signing_request_digest": signer_secret_access_request_digest(
            request.to_dict()
        ),
        "requested_operation": request.requested_operation,
        "authority_tier": request.authority_tier,
        "attested_peer_principal_id": request.requester_principal_id,
        "nonce": "grant-nonce-1",
        "issued_at": NOW - 10,
        "expires_at": NOW + 100,
        "grant_id": "",
        "signature": "fixture-signature-v2",
    }
    value.update(overrides)
    value["grant_id"] = signer_secret_access_grant_id(value)
    return value


class _Resolver:
    def resolve(self, principal_id: str, principal_provider: str) -> str | None:
        if (principal_id, principal_provider) == ("principal:founder", "github"):
            return "public-key-v1:issuer"
        return None


class _Verifier:
    def __init__(self, grant: Mapping[str, Any]) -> None:
        self.expected = (
            str(grant["issuer_public_key"]),
            canonical_signer_secret_access_grant_input(grant),
            str(grant["signature"]),
        )

    def verify(self, public_key: str, signing_input: str, signature: str) -> bool:
        return (public_key, signing_input, signature) == self.expected or (
            public_key == _binding().signer_public_key
            and signing_input == _request().signing_input
            and signature == "signature-v1"
        )


class _EphemeralBackend:
    def __init__(self) -> None:
        self.calls = 0
        self.public_key = _binding().signer_public_key
        self.key_epoch = _binding().key_epoch

    def sign(
        self, request: SigningRequest, peer: SignerPeerAttestation
    ) -> SigningResponse:
        self.calls += 1
        return SigningResponse(
            accepted=True,
            signature="signature-v1",
            signer_public_key=request.signer_public_key,
            key_fingerprint=public_key_fingerprint(request.signer_public_key),
            key_epoch=request.key_epoch,
            audit_mac="audit-mac-v1:" + "a" * 64,
            boundary_attested=True,
            requester_identity_attested=(
                request.requester_principal_id == peer.peer_principal_id
            ),
            signer_loads_no_untrusted_code=True,
            no_secret_material_returned=True,
        )


class _Factory:
    def __init__(self, backend: _EphemeralBackend, *, valid: bool = True) -> None:
        self.backend = backend
        self.valid = valid
        self.calls = 0
        self.signer_agent_id = _binding().signer_agent_id
        self.permission_snapshot_digest = _binding().permission_snapshot_digest

    def __call__(self) -> SignerKeyProviderDryRunResult:
        self.calls += 1
        binding = _binding()
        return SignerKeyProviderDryRunResult(
            ok=self.valid,
            rejection_code=None if self.valid else "resolve_failed",
            signer_profile_id=binding.signer_profile_id,
            key_epoch=binding.key_epoch,
            public_key="public-key-v1:signer",
            key_fingerprint=binding.signer_key_fingerprint,
            signing_key_ref_hash=binding.signing_key_ref_hash,
            audit_mac_key_ref_hash=binding.audit_mac_key_ref_hash,
            ttl_remaining_seconds=60,
            secret_values_returned=False,
            backend=self.backend if self.valid else None,
        )


def _backend(
    grant: Mapping[str, Any], factory: _Factory,
    nonce_store: DurableSignerSecretGrantNonceStore,
) -> ResolvePerSignSignerBackend:
    return ResolvePerSignSignerBackend(
        binding=_binding(nonce_store),
        grant_boundary=SignerSecretAccessGrantBoundary(
            nonce_store=nonce_store,
            revocation_oracle=AtomicSignerSecretGrantRevocationOracle(),
            clock=lambda: NOW,
        ),
        signature_verifier=_Verifier(grant),
        principal_key_resolver=_Resolver(),
        backend_factory=factory,
    )


def _store_config(tmp_path: Path) -> SignerGrantReplayStoreConfig:
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    return SignerGrantReplayStoreConfig(
        nonce_path=tmp_path / "nonces" / "grant-nonces.json",
        nonce_root=tmp_path / "nonces",
        high_water_path=tmp_path / "high-water" / "authority.sqlite3",
        high_water_root=tmp_path / "high-water",
        repo_root=repo,
        replay_store_binding_digest=_binding().replay_store_binding_digest,
        replay_store_id=_binding().replay_store_id,
        durability_receipt_id=_binding().replay_store_durability_receipt_id,
    )


def _provision_store(config: SignerGrantReplayStoreConfig) -> None:
    high_water = SqliteMonotonicAuthorityStore(
        config.high_water_path,
        allowed_root=config.high_water_root,
        repo_root=config.repo_root,
        store_id=config.replay_store_id,
        durability_receipt_id=config.durability_receipt_id,
    )
    store = AtomicProposalAuthenticityNonceStore(
        config.nonce_path,
        allowed_root=config.nonce_root,
        repo_root=config.repo_root,
        integrity_key=INTEGRITY_KEY,
        replay_store_binding_digest=config.replay_store_binding_digest,
        high_water_store=high_water,
        clock=lambda: NOW,
    )
    reservation = store.reserve(
        "fixture-provisioning-nonce",
        expires_at=NOW + 1000,
        subject="fixture-provisioning",
    )
    store.rollback(reservation)


def _store(tmp_path: Path) -> DurableSignerSecretGrantNonceStore:
    config = _store_config(tmp_path)
    if not config.nonce_path.exists() and not config.high_water_path.exists():
        _provision_store(config)
    return DurableSignerSecretGrantNonceStore(
        config, integrity_key=INTEGRITY_KEY, clock=lambda: NOW
    )


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("replay_store_binding_digest", "not-a-digest"),
        ("durability_receipt_id", "not-a-digest"),
        ("replay_store_id", ""),
        ("replay_store_id", "non-ascii-\u2603"),
    ),
)
def test_durable_nonce_store_rejects_invalid_identity_before_open(
    tmp_path: Path, field: str, value: str
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    config = SignerGrantReplayStoreConfig(
        nonce_path=tmp_path / "nonces" / "grant-nonces.json",
        nonce_root=tmp_path / "nonces",
        high_water_path=tmp_path / "high-water" / "authority.sqlite3",
        high_water_root=tmp_path / "high-water",
        repo_root=repo,
        replay_store_binding_digest=_digest("7"),
        replay_store_id="signer-grant-replay:test",
        durability_receipt_id=_digest("8"),
    )

    with pytest.raises(ValueError, match="signer_grant_replay_config_invalid"):
        DurableSignerSecretGrantNonceStore(
            replace(config, **{field: value}),
            integrity_key=b"test-integrity-key",
            clock=lambda: NOW,
        )

    assert not (tmp_path / "nonces").exists()
    assert not (tmp_path / "high-water").exists()


@pytest.mark.parametrize("nested", [False, True])
def test_durable_nonce_store_rejects_overlapping_rollback_domains(
    tmp_path: Path, nested: bool
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    common = tmp_path / "replay"
    high_water_root = common / "witness" if nested else common
    config = SignerGrantReplayStoreConfig(
        nonce_path=common / "grant-nonces.json",
        nonce_root=common,
        high_water_path=high_water_root / "authority.sqlite3",
        high_water_root=high_water_root,
        repo_root=repo,
        replay_store_binding_digest=_digest("7"),
        replay_store_id="signer-grant-replay:test",
        durability_receipt_id=_digest("8"),
    )

    with pytest.raises(ValueError, match="rollback_domains_overlap"):
        DurableSignerSecretGrantNonceStore(
            config,
            integrity_key=b"test-integrity-key",
            clock=lambda: NOW,
        )

    assert not common.exists()


def test_durable_nonce_store_rejects_unprovisioned_or_lost_state(
    tmp_path: Path,
) -> None:
    config = _store_config(tmp_path)
    with pytest.raises(ValueError, match="replay_store_not_provisioned"):
        DurableSignerSecretGrantNonceStore(
            config, integrity_key=INTEGRITY_KEY, clock=lambda: NOW
        )

    store = _store(tmp_path)
    request = _request()
    grant = _grant(request, store)
    assert _backend(
        grant, _Factory(_EphemeralBackend()), store
    ).sign_with_secret_grant(request, _peer(), grant).accepted is True

    shutil.rmtree(config.nonce_root)
    shutil.rmtree(config.high_water_root)
    replay = _backend(
        grant, _Factory(_EphemeralBackend()), store
    ).sign_with_secret_grant(request, _peer(), grant)

    assert replay.rejection_code == REJECT_SECRET_GRANT_INVALID
    with pytest.raises(ValueError, match="replay_store_not_provisioned"):
        DurableSignerSecretGrantNonceStore(
            config, integrity_key=INTEGRITY_KEY, clock=lambda: NOW
        )


@pytest.fixture
def nonce_store(tmp_path: Path) -> DurableSignerSecretGrantNonceStore:
    return _store(tmp_path)


def _peer() -> SignerPeerAttestation:
    return SignerPeerAttestation(
        peer_principal_id="principal:founder",
        transport="unix_socket",
        credential_source="SO_PEERCRED",
        boundary_attested=True,
    )


def test_v1_sign_without_grant_fails_before_resolution(nonce_store) -> None:
    request = _request()
    grant = _grant(request, nonce_store)
    factory = _Factory(_EphemeralBackend())

    result = _backend(grant, factory, nonce_store).sign(request, _peer())

    assert result.accepted is False
    assert result.rejection_code == REJECT_SECRET_GRANT_REQUIRED
    assert factory.calls == 0


def test_valid_grant_resolves_once_and_signs_exact_request(nonce_store) -> None:
    request = _request()
    grant = _grant(request, nonce_store)
    ephemeral = _EphemeralBackend()
    factory = _Factory(ephemeral)

    result = _backend(grant, factory, nonce_store).sign_with_secret_grant(
        request, _peer(), grant
    )

    assert result.accepted is True
    assert factory.calls == 1
    assert ephemeral.calls == 1


def test_request_or_peer_mismatch_rejects_before_resolution(nonce_store) -> None:
    request = _request()
    grant = _grant(request, nonce_store)
    factory = _Factory(_EphemeralBackend())
    backend = _backend(grant, factory, nonce_store)

    changed = backend.sign_with_secret_grant(
        replace(request, requested_operation="publish_draft_pr"), _peer(), grant
    )

    assert changed.accepted is False
    assert changed.rejection_code == REJECT_SECRET_GRANT_INVALID
    assert factory.calls == 0

    unattested = backend.sign_with_secret_grant(
        request, replace(_peer(), boundary_attested=False), grant
    )
    assert unattested.rejection_code == REJECT_SECRET_GRANT_INVALID
    assert factory.calls == 0

    changed_peer = backend.sign_with_secret_grant(
        request, replace(_peer(), peer_principal_id="principal:attacker"), grant
    )
    assert changed_peer.rejection_code == REJECT_SECRET_GRANT_INVALID
    assert factory.calls == 0


def test_resolution_failure_burns_one_shot_grant(nonce_store) -> None:
    request = _request()
    grant = _grant(request, nonce_store)
    factory = _Factory(_EphemeralBackend(), valid=False)
    backend = _backend(grant, factory, nonce_store)

    first = backend.sign_with_secret_grant(request, _peer(), grant)
    second = backend.sign_with_secret_grant(request, _peer(), grant)

    assert first.rejection_code == REJECT_SECRET_RESOLUTION_FAILED
    assert second.rejection_code == REJECT_SECRET_GRANT_INVALID
    assert factory.calls == 1


def test_factory_exception_is_sanitized_and_grant_is_burned(nonce_store) -> None:
    request = _request()
    grant = _grant(request, nonce_store)

    class _RaisingFactory:
        calls = 0
        signer_agent_id = _binding().signer_agent_id
        permission_snapshot_digest = _binding().permission_snapshot_digest

        def __call__(self):
            self.calls += 1
            raise RuntimeError("secret-value-must-not-escape")

    factory = _RaisingFactory()
    backend = ResolvePerSignSignerBackend(
        binding=_binding(nonce_store),
        grant_boundary=SignerSecretAccessGrantBoundary(
            nonce_store=nonce_store,
            revocation_oracle=AtomicSignerSecretGrantRevocationOracle(),
            clock=lambda: NOW,
        ),
        signature_verifier=_Verifier(grant),
        principal_key_resolver=_Resolver(),
        backend_factory=factory,
    )

    first = backend.sign_with_secret_grant(request, _peer(), grant)
    second = backend.sign_with_secret_grant(request, _peer(), grant)

    assert first.rejection_code == REJECT_SECRET_RESOLUTION_FAILED
    assert second.rejection_code == REJECT_SECRET_GRANT_INVALID
    assert "secret-value" not in json.dumps(first.to_dict())
    assert factory.calls == 1


def test_socket_v2_routes_grant_to_resolve_per_sign_backend(nonce_store) -> None:
    request = _request()
    grant = _grant(request, nonce_store)
    factory = _Factory(_EphemeralBackend())
    payload = {
        "schema_version": SIGNER_SOCKET_REQUEST_SCHEMA_VERSION_V2,
        "request": request.to_dict(),
        "secret_access_grant": grant,
    }

    raw = handle_reddog_isolated_signer_socket_request(
        json.dumps(payload).encode("utf-8"),
        peer=_peer(),
        backend=_backend(grant, factory, nonce_store),
    )
    result = json.loads(raw)

    assert result["accepted"] is True
    assert factory.calls == 1


def test_concurrent_grant_reuse_permits_exactly_one_resolution(nonce_store) -> None:
    request = _request()
    grant = _grant(request, nonce_store)
    factory = _Factory(_EphemeralBackend())
    backend = _backend(grant, factory, nonce_store)
    barrier = threading.Barrier(2)
    results: list[SigningResponse] = []

    def run() -> None:
        barrier.wait()
        results.append(backend.sign_with_secret_grant(request, _peer(), grant))

    threads = [threading.Thread(target=run) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sum(result.accepted for result in results) == 1
    assert factory.calls == 1


def test_restart_replay_rejects_with_shared_durable_nonce_store(tmp_path: Path) -> None:
    request = _request()
    store = _store(tmp_path)
    grant = _grant(request, store)

    def build() -> ResolvePerSignSignerBackend:
        return ResolvePerSignSignerBackend(
            binding=_binding(store),
            grant_boundary=SignerSecretAccessGrantBoundary(
                nonce_store=store,
                revocation_oracle=AtomicSignerSecretGrantRevocationOracle(),
                clock=lambda: NOW,
            ),
            signature_verifier=_Verifier(grant),
            principal_key_resolver=_Resolver(),
            backend_factory=_Factory(_EphemeralBackend()),
        )

    assert build().sign_with_secret_grant(request, _peer(), grant).accepted is True
    store = _store(tmp_path)
    replay = build().sign_with_secret_grant(request, _peer(), grant)
    assert replay.rejection_code == REJECT_SECRET_GRANT_INVALID

    cloned_identity = _store(tmp_path / "alternate-store")
    factory = _Factory(_EphemeralBackend())
    clone = _backend(grant, factory, cloned_identity).sign_with_secret_grant(
        request, _peer(), grant
    )
    assert clone.rejection_code == REJECT_SECRET_GRANT_INVALID
    assert factory.calls == 0


def test_non_durable_nonce_store_rejects_before_resolution(nonce_store) -> None:
    request = _request()
    grant = _grant(request, nonce_store)
    factory = _Factory(_EphemeralBackend())
    boundary = SignerSecretAccessGrantBoundary(
        nonce_store=type("VolatileStore", (), {"consume": lambda _self, _nonce: True})(),
        revocation_oracle=AtomicSignerSecretGrantRevocationOracle(),
        clock=lambda: NOW,
    )
    backend = replace(
        _backend(grant, factory, nonce_store), grant_boundary=boundary
    )

    result = backend.sign_with_secret_grant(request, _peer(), grant)

    assert result.rejection_code == REJECT_SECRET_GRANT_INVALID
    assert factory.calls == 0


def test_expiry_or_revocation_during_resolution_rejects_before_signing(
    nonce_store,
) -> None:
    request = _request()
    grant = _grant(request, nonce_store)
    clock = [NOW]
    oracle = AtomicSignerSecretGrantRevocationOracle()
    ephemeral = _EphemeralBackend()

    class _MutatingFactory(_Factory):
        def __call__(self) -> SignerKeyProviderDryRunResult:
            result = super().__call__()
            clock[0] = NOW + 101
            oracle.revoke_grant(str(grant["grant_id"]))
            return result

    factory = _MutatingFactory(ephemeral)
    backend = ResolvePerSignSignerBackend(
        binding=_binding(nonce_store),
        grant_boundary=SignerSecretAccessGrantBoundary(
            nonce_store=nonce_store,
            revocation_oracle=oracle,
            clock=lambda: clock[0],
        ),
        signature_verifier=_Verifier(grant),
        principal_key_resolver=_Resolver(),
        backend_factory=factory,
    )

    result = backend.sign_with_secret_grant(request, _peer(), grant)

    assert result.rejection_code == REJECT_SECRET_GRANT_INVALID
    assert ephemeral.calls == 0


def test_revocation_and_signing_are_linearized_by_one_authority_fence(
    nonce_store,
) -> None:
    request = _request()
    grant = _grant(request, nonce_store)
    oracle = AtomicSignerSecretGrantRevocationOracle()
    started = threading.Event()
    release = threading.Event()
    revoked = threading.Event()

    class _BlockingBackend(_EphemeralBackend):
        def sign(self, request, peer):
            started.set()
            assert release.wait(timeout=5)
            return super().sign(request, peer)

    factory = _Factory(_BlockingBackend())
    backend = ResolvePerSignSignerBackend(
        binding=_binding(nonce_store),
        grant_boundary=SignerSecretAccessGrantBoundary(
            nonce_store=nonce_store,
            revocation_oracle=oracle,
            clock=lambda: NOW,
        ),
        signature_verifier=_Verifier(grant),
        principal_key_resolver=_Resolver(),
        backend_factory=factory,
    )
    results: list[SigningResponse] = []
    signer = threading.Thread(
        target=lambda: results.append(
            backend.sign_with_secret_grant(request, _peer(), grant)
        )
    )
    revoker = threading.Thread(
        target=lambda: (oracle.revoke_grant(str(grant["grant_id"])), revoked.set())
    )
    signer.start()
    assert started.wait(timeout=5)
    revoker.start()
    assert revoked.wait(timeout=0.1) is False
    release.set()
    signer.join(timeout=5)
    revoker.join(timeout=5)

    assert results[0].accepted is True
    assert revoked.is_set()


def test_grant_expiring_inside_signing_callback_rejects_response(
    nonce_store,
) -> None:
    request = _request()
    grant = _grant(request, nonce_store)
    clock = [NOW]

    class _ExpiringBackend(_EphemeralBackend):
        def sign(self, request, peer):
            response = super().sign(request, peer)
            clock[0] = NOW + 101
            return response

    backend = ResolvePerSignSignerBackend(
        binding=_binding(nonce_store),
        grant_boundary=SignerSecretAccessGrantBoundary(
            nonce_store=nonce_store,
            revocation_oracle=AtomicSignerSecretGrantRevocationOracle(),
            clock=lambda: clock[0],
        ),
        signature_verifier=_Verifier(grant),
        principal_key_resolver=_Resolver(),
        backend_factory=_Factory(_ExpiringBackend()),
    )

    result = backend.sign_with_secret_grant(request, _peer(), grant)

    assert result.rejection_code == REJECT_SECRET_GRANT_INVALID


def test_zero_provider_ttl_or_substituted_backend_identity_rejects(
    nonce_store,
) -> None:
    request = _request()
    grant = _grant(request, nonce_store)

    class _TamperedFactory(_Factory):
        def __call__(self) -> SignerKeyProviderDryRunResult:
            result = super().__call__()
            return replace(result, ttl_remaining_seconds=0)

    zero_ttl = _TamperedFactory(_EphemeralBackend())
    result = _backend(grant, zero_ttl, nonce_store).sign_with_secret_grant(
        request, _peer(), grant
    )
    assert result.rejection_code == REJECT_EPHEMERAL_BACKEND_INVALID


def test_self_reported_identity_with_unverified_signature_rejects(
    nonce_store, tmp_path: Path,
) -> None:
    request = _request()
    grant = _grant(request, nonce_store)

    class _ForgedSignatureBackend(_EphemeralBackend):
        def sign(self, request, peer):
            return replace(
                super().sign(request, peer), signature="attacker-signature"
            )

    result = _backend(
        grant, _Factory(_ForgedSignatureBackend()), nonce_store
    ).sign_with_secret_grant(request, _peer(), grant)

    assert result.rejection_code == REJECT_EPHEMERAL_BACKEND_INVALID


    wrong_object = _EphemeralBackend()
    wrong_object.public_key = "public-key-v1:attacker"
    substituted = _Factory(wrong_object)
    store2 = _store(tmp_path / "identity-substitution")
    grant2 = _grant(request, store2, nonce="grant-nonce-2")
    result = _backend(
        grant2, substituted, store2
    ).sign_with_secret_grant(
        request, _peer(), grant2
    )
    assert result.rejection_code == REJECT_EPHEMERAL_BACKEND_INVALID

    class _WrongIdentityBackend(_EphemeralBackend):
        def sign(self, request, peer):
            return replace(
                super().sign(request, peer),
                signer_public_key="public-key-v1:attacker",
                key_fingerprint=public_key_fingerprint(
                    "public-key-v1:attacker"
                ),
            )

    substituted = _Factory(_WrongIdentityBackend())
    store3 = _store(tmp_path / "response-substitution")
    grant3 = _grant(request, store3, nonce="grant-nonce-3")
    result = _backend(
        grant3, substituted, store3
    ).sign_with_secret_grant(
        request, _peer(), grant3
    )
    assert result.rejection_code == REJECT_EPHEMERAL_BACKEND_INVALID


def test_rejected_backend_cannot_exfiltrate_secret_fields(nonce_store) -> None:
    request = _request()
    grant = _grant(request, nonce_store)

    class _SecretRejectingBackend(_EphemeralBackend):
        def sign(self, request, peer):
            self.calls += 1
            return SigningResponse(
                accepted=False,
                signature="secret-value",
                audit_mac="secret-audit-key",
                rejection_code="REJECTED",
                no_secret_material_returned=True,
            )

    result = _backend(
        grant, _Factory(_SecretRejectingBackend()), nonce_store
    ).sign_with_secret_grant(request, _peer(), grant)

    assert result.rejection_code == REJECT_EPHEMERAL_BACKEND_INVALID
    serialized = json.dumps(result.to_dict())
    assert "secret-value" not in serialized
    assert "secret-audit-key" not in serialized


def test_accepted_backend_cannot_use_unbound_response_fields(nonce_store) -> None:
    request = _request()
    grant = _grant(request, nonce_store)

    class _UnboundFieldsBackend(_EphemeralBackend):
        def sign(self, request, peer):
            return replace(
                super().sign(request, peer),
                rejection_code="SECRET_CODE",
                audit_attestation_signature="SECRET_AUX",
                boundary_attested=1,
            )

    result = _backend(
        grant, _Factory(_UnboundFieldsBackend()), nonce_store
    ).sign_with_secret_grant(request, _peer(), grant)

    assert result.rejection_code == REJECT_EPHEMERAL_BACKEND_INVALID
    serialized = json.dumps(result.to_dict())
    assert "SECRET_CODE" not in serialized
    assert "SECRET_AUX" not in serialized


def test_provider_reference_binding_mismatch_rejects_after_one_resolution(
    nonce_store,
) -> None:
    request = _request()
    grant = _grant(request, nonce_store)

    class _MismatchedFactory(_Factory):
        def __call__(self) -> SignerKeyProviderDryRunResult:
            return replace(super().__call__(), signing_key_ref_hash=_digest("9"))

    factory = _MismatchedFactory(_EphemeralBackend())
    backend = _backend(grant, factory, nonce_store)

    result = backend.sign_with_secret_grant(request, _peer(), grant)

    assert result.accepted is False
    assert result.rejection_code == REJECT_EPHEMERAL_BACKEND_INVALID


def test_factory_permission_binding_mismatch_rejects_before_grant_consumption(
    nonce_store,
) -> None:
    request = _request()
    grant = _grant(request, nonce_store)
    factory = _Factory(_EphemeralBackend())
    factory.permission_snapshot_digest = _digest("9")
    backend = _backend(grant, factory, nonce_store)

    result = backend.sign_with_secret_grant(request, _peer(), grant)

    assert result.rejection_code == REJECT_EPHEMERAL_BACKEND_INVALID
    assert factory.calls == 0


def test_resolve_per_sign_backend_is_bounded_and_has_no_effect_primitives() -> None:
    banned_imports = {"subprocess", "socket", "requests", "urllib", "httpx"}
    for source in SOURCES:
        text = source.read_text(encoding="utf-8")
        tree = ast.parse(text)
        assert len(text.splitlines()) <= 200
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert not any(
                    alias.name.split(".")[0] in banned_imports
                    for alias in node.names
                )
            elif isinstance(node, ast.ImportFrom):
                assert (node.module or "").split(".")[0] not in banned_imports
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert node.end_lineno - node.lineno + 1 <= 50


def test_modified_socket_parser_functions_remain_bounded() -> None:
    tree = ast.parse(PROTOCOL_SOURCE.read_text(encoding="utf-8"))
    functions = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    assert functions
    for node in functions:
        assert node.end_lineno - node.lineno + 1 <= 50
