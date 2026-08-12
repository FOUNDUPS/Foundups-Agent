"""Adversarial tests for the external authoritative-use lease boundary."""

from __future__ import annotations

import hashlib
import json
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from modules.communication.moltbot_bridge.src import (
    reddog_authoritative_use_lease as lease_module,
)
from modules.communication.moltbot_bridge.src import (
    reddog_external_signer_authoritative_use_lease as issuer_module,
)
from modules.communication.moltbot_bridge.src.reddog_authoritative_use_lease import (
    AuthoritativeUseLease,
    consume_authoritative_use_lease,
    is_authoritative_use_lease,
)
from modules.communication.moltbot_bridge.src.reddog_authoritative_use_lease_contract import (
    authoritative_use_effect_digest,
    build_authoritative_use_lease_request,
    digest_text,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    Ed25519SignatureVerifier,
    encode_ed25519_public_key,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signer_backend import (
    Ed25519SignerBackend,
    bind_exact_signing_request,
)
from modules.communication.moltbot_bridge.src.reddog_external_signer_authoritative_use_lease import (
    ExternalSignerAuthoritativeUseLeaseIssuer,
)
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_protocol import (
    SignerPeerAttestation,
    handle_reddog_isolated_signer_socket_request,
)
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_client import (
    RedDogIsolatedSignerSocketClient,
)
from modules.communication.moltbot_bridge.src.reddog_proposal_authenticity_nonce_store import (
    AtomicProposalAuthenticityNonceStore,
)
from modules.communication.moltbot_bridge.src.reddog_signer_current_generation_runtime_binding import (
    SignerCurrentGenerationRuntimeAuthority,
    SignerCurrentGenerationRuntimeBinding,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    SigningRequest,
    SigningResponse,
    public_key_fingerprint,
)
from modules.communication.moltbot_bridge.src.reddog_signer_key_provider_dryrun import (
    SignerKeyProviderDryRunResult,
)
from modules.communication.moltbot_bridge.src.reddog_signer_mutual_peer_handshake import (
    SignerPeerInstanceBinding,
    SignerPeerProfileBinding,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_durable_nonce_store import (
    DurableSignerSecretGrantNonceStore,
    SignerGrantReplayStoreConfig,
)
from modules.communication.moltbot_bridge.src.reddog_signer_resolve_per_sign_backend import (
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
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_revocation_oracle import (
    AtomicSignerSecretGrantRevocationOracle,
)
from modules.communication.moltbot_bridge.src.reddog_extension_wre_operational_spine_invoke import (
    EXTENSION_WRE_OPERATIONAL_SPINE_INVOKE_ACCEPT,
    invoke_reddog_extension_wre_operational_spine_explicit_valve,
)
from modules.communication.moltbot_bridge.src.reddog_sqlite_monotonic_authority_store import (
    SqliteMonotonicAuthorityStore,
)
from modules.communication.moltbot_bridge.tests.test_reddog_extension_wre_operational_spine_invoke import (
    FakeRunner,
    _accepted_signature,
    _base_order,
    _open_worktree_env,
    _selection_receipt,
)


NOW = 2_000_000_000
INTEGRITY_KEY = b"lease-integrity-key-32-bytes!!!!"


class _AuditMac:
    def build(
        self, request: SigningRequest, _signature: str, peer: SignerPeerAttestation
    ) -> str:
        return "audit:" + request.nonce + ":" + peer.peer_principal_id


class _GrantAwareSigner:
    def sign_with_secret_grant(
        self, request: SigningRequest, secret_access_grant: Mapping[str, Any]
    ) -> SigningResponse:
        if secret_access_grant != {"grant_id": "root-grant-1"}:
            raise ValueError("grant mismatch")
        return _backend(request, exact=True).sign(request, _peer())


class _LeasedGrantProvider:
    def __init__(self, factory):
        self._factory = factory

    @contextmanager
    def lease(self, request: SigningRequest):
        yield self._factory(request)


class _ProtocolGrantBackend:
    def sign(self, _request: SigningRequest, _peer: SignerPeerAttestation) -> SigningResponse:
        raise AssertionError("lease domain must never reach socket v1 sign")

    def sign_with_secret_grant(
        self,
        request: SigningRequest,
        peer: SignerPeerAttestation,
        grant: Mapping[str, Any],
    ) -> SigningResponse:
        assert grant == {"grant_id": "root-grant-1"}
        return _backend(request, exact=True).sign(request, peer)


class _IssuerResolver:
    def resolve(self, principal_id: str, principal_provider: str) -> str | None:
        return (
            "issuer-public-key-v1"
            if (principal_id, principal_provider) == ("github:mjtrout", "github")
            else None
        )


class _GrantAndResponseVerifier:
    def __init__(self, grant: Mapping[str, Any]) -> None:
        self._grant = (
            str(grant["issuer_public_key"]),
            canonical_signer_secret_access_grant_input(grant),
            str(grant["signature"]),
        )

    def verify(self, public_key: str, signing_input: str, signature: str) -> bool:
        return (public_key, signing_input, signature) == self._grant or bool(
            Ed25519SignatureVerifier().verify(public_key, signing_input, signature)
        )


class _CanonicalAuditMac:
    def build(
        self, request: SigningRequest, _signature: str, peer: SignerPeerAttestation
    ) -> str:
        value = (request.nonce + ":" + peer.peer_principal_id).encode("utf-8")
        return "audit-mac-v1:" + hashlib.sha256(value).hexdigest()


class _ResolveFactory:
    signer_agent_id = "signer:reddog"
    permission_snapshot_digest = "sha256:" + "3" * 64

    def __call__(self) -> SignerKeyProviderDryRunResult:
        binding = _resolve_binding(self.store)
        backend = Ed25519SignerBackend(
            private_key=_private_key(),
            public_key=_public_key(),
            key_epoch="epoch-1",
            audit_mac_builder=_CanonicalAuditMac(),
            proposal_clock=lambda: NOW,
            signer_peer_instance_binding=_binding(),
        )
        return SignerKeyProviderDryRunResult(
            ok=True,
            rejection_code=None,
            signer_profile_id=binding.signer_profile_id,
            key_epoch=binding.key_epoch,
            public_key=binding.signer_public_key,
            key_fingerprint=binding.signer_key_fingerprint,
            signing_key_ref_hash=binding.signing_key_ref_hash,
            audit_mac_key_ref_hash=binding.audit_mac_key_ref_hash,
            ttl_remaining_seconds=60,
            secret_values_returned=False,
            backend=backend,
        )

    def __init__(self, store: DurableSignerSecretGrantNonceStore) -> None:
        self.store = store


def _private_key() -> Ed25519PrivateKey:
    return Ed25519PrivateKey.from_private_bytes(bytes(range(32)))


def _public_key() -> str:
    return encode_ed25519_public_key(
        _private_key().public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
    )


def _binding() -> SignerPeerInstanceBinding:
    return SignerPeerInstanceBinding(
        run_packet_id="sha256:" + "1" * 64,
        config_digest="sha256:" + "2" * 64,
        session_id="session-1",
        socket_path=str(Path("C:/runtime/reddog.sock").resolve()),
        signer_profiles=(
            SignerPeerProfileBinding(
                signer_profile_id="reddog-work-authority",
                signer_public_key=_public_key(),
                key_epoch="epoch-1",
            ),
        ),
        manifest_id="sha256:" + "3" * 64,
        artifact_generation_digest="sha256:" + "4" * 64,
        generation=7,
        generation_revision="revision-7",
        owner_config_id="sha256:" + "6" * 64,
    )


def _effect_payload(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "queue_item_id": "queue-1",
        "selected_slice": "REDDOG_TEST_PHASE1",
        "work_order_id": "work-order-1",
        "work_order_digest": "sha256:" + "c" * 64,
        "executor_plan_digest": "sha256:" + "d" * 64,
        "valve_decision_digest": "sha256:" + "e" * 64,
    }
    values.update(overrides)
    return values


def _payload(
    replay_store: DurableSignerSecretGrantNonceStore | None = None,
    **overrides: object,
) -> dict[str, object]:
    binding = _binding()
    effect = _effect_payload()
    values: dict[str, object] = {
        "schema_version": "reddog_authoritative_use_lease.v1",
        "lease_nonce": "a" * 64,
        "effect_kind": "worktree_create",
        "effect_payload": effect,
        "effect_request_digest": authoritative_use_effect_digest(
            "worktree_create", effect
        ),
        "requester_principal_id": "github:mjtrout",
        "signer_profile_id": "reddog-work-authority",
        "signer_public_key": _public_key(),
        "key_epoch": "epoch-1",
        "manifest_id": binding.manifest_id,
        "artifact_generation_digest": binding.artifact_generation_digest,
        "generation": binding.generation,
        "generation_revision": binding.generation_revision,
        "owner_config_id": binding.owner_config_id,
        "run_packet_id": binding.run_packet_id,
        "config_digest": binding.config_digest,
        "session_id": binding.session_id,
        "socket_path_digest": digest_text(binding.socket_path),
        "replay_store_binding_digest": "sha256:" + "7" * 64,
        "replay_store_id": "signer-grant-replay:test",
        "replay_store_durability_receipt_id": "sha256:" + "8" * 64,
        "replay_store_instance_digest": "sha256:" + "5" * 64,
        "work_authority_digest": "sha256:" + "9" * 64,
        "identity_digest": "sha256:" + "b" * 64,
        "expected_bindings_digest": "sha256:" + "f" * 64,
        "issued_at": NOW,
        "expires_at": NOW + 20,
    }
    if replay_store is not None:
        values.update(_replay_binding(replay_store))
    values.update(overrides)
    return values


def _request(
    replay_store: DurableSignerSecretGrantNonceStore | None = None,
    **overrides: object,
) -> SigningRequest:
    return build_authoritative_use_lease_request(
        _payload(replay_store, **overrides), authority_tier="HIGH"
    )


def _peer() -> SignerPeerAttestation:
    return SignerPeerAttestation(
        peer_principal_id="github:mjtrout",
        transport="unix_socket",
        credential_source=(
            "kernel_peer_credential:kernel_so_peercred:pid=1:uid=1:gid=1"
        ),
        boundary_attested=True,
    )


def _backend(request: SigningRequest, *, exact: bool) -> Ed25519SignerBackend:
    backend = Ed25519SignerBackend(
        private_key=_private_key(),
        public_key=_public_key(),
        key_epoch="epoch-1",
        audit_mac_builder=_AuditMac(),
        proposal_clock=lambda: NOW,
        signer_peer_instance_binding=_binding(),
    )
    return bind_exact_signing_request(backend, request) if exact else backend


def _current_generation() -> SignerCurrentGenerationRuntimeBinding:
    binding = _binding()
    return SignerCurrentGenerationRuntimeBinding(
        accepted=True,
        rejection_reasons=(),
        receipt_id="sha256:" + "7" * 64,
        manifest_id=binding.manifest_id,
        artifact_generation_digest=binding.artifact_generation_digest,
        generation=binding.generation,
        generation_revision=binding.generation_revision,
        owner_config_id=binding.owner_config_id,
        config_digest=binding.config_digest,
        run_packet_id=binding.run_packet_id,
        run_packet_digest="sha256:" + "8" * 64,
        session_id=binding.session_id,
        socket_path_digest=digest_text(binding.socket_path),
        signer_profile_id="reddog-work-authority",
        signer_public_key=_public_key(),
        key_epoch="epoch-1",
        selection_expires_at=NOW + 100,
    )


def _replay_binding(
    store: DurableSignerSecretGrantNonceStore,
) -> dict[str, str]:
    return {
        "replay_store_binding_digest": store.replay_store_binding_digest,
        "replay_store_id": store.replay_store_id,
        "replay_store_durability_receipt_id": store.durability_receipt_id,
        "replay_store_instance_digest": store.replay_store_instance_digest,
    }


def _resolve_binding(
    store: DurableSignerSecretGrantNonceStore,
) -> ResolvePerSignBinding:
    return ResolvePerSignBinding(
        issuer_principal_id="github:mjtrout",
        issuer_principal_provider="github",
        issuer_public_key="issuer-public-key-v1",
        signer_agent_id="signer:reddog",
        signer_profile_id="reddog-work-authority",
        signing_key_ref_hash="sha256:" + "1" * 64,
        audit_mac_key_ref_hash="sha256:" + "2" * 64,
        key_epoch="epoch-1",
        permission_snapshot_digest="sha256:" + "3" * 64,
        owner_config_id=_binding().owner_config_id,
        signer_generation_id=_binding().artifact_generation_digest,
        signer_public_key=_public_key(),
        signer_key_fingerprint=public_key_fingerprint(_public_key()),
        **_replay_binding(store),
    )


def _root_grant(
    request: SigningRequest, store: DurableSignerSecretGrantNonceStore
) -> dict[str, Any]:
    value = {
        "schema_version": GRANT_SCHEMA,
        **asdict(_resolve_binding(store)),
        "signing_request_digest": signer_secret_access_request_digest(
            request.to_dict()
        ),
        "requested_operation": request.requested_operation,
        "authority_tier": request.authority_tier,
        "attested_peer_principal_id": request.requester_principal_id,
        "nonce": "root-grant-nonce-1",
        "issued_at": NOW,
        "expires_at": NOW + 30,
        "grant_id": "",
        "signature": "root-grant-signature-v1",
    }
    value["grant_id"] = signer_secret_access_grant_id(value)
    return value


def _resolve_backend(
    grant: Mapping[str, Any], store: DurableSignerSecretGrantNonceStore
) -> ResolvePerSignSignerBackend:
    return ResolvePerSignSignerBackend(
        binding=_resolve_binding(store),
        grant_boundary=SignerSecretAccessGrantBoundary(
            nonce_store=store,
            revocation_oracle=AtomicSignerSecretGrantRevocationOracle(),
            clock=lambda: NOW,
        ),
        signature_verifier=_GrantAndResponseVerifier(grant),
        principal_key_resolver=_IssuerResolver(),
        backend_factory=_ResolveFactory(store),
    )


def _authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    binding: SignerCurrentGenerationRuntimeBinding | None = None,
) -> SignerCurrentGenerationRuntimeAuthority:
    authority = SignerCurrentGenerationRuntimeAuthority(tmp_path, tmp_path)
    current = binding or _current_generation()

    def resolve(_self, *, now_epoch: int, signer_profile_id: str):
        assert now_epoch == NOW
        assert signer_profile_id == "reddog-work-authority"
        return current

    monkeypatch.setattr(SignerCurrentGenerationRuntimeAuthority, "resolve", resolve)
    return authority


def _store(tmp_path: Path) -> DurableSignerSecretGrantNonceStore:
    repo = tmp_path / "repo"
    repo.mkdir(parents=True)
    config = SignerGrantReplayStoreConfig(
        nonce_path=tmp_path / "nonces" / "grant-nonces.json",
        nonce_root=tmp_path / "nonces",
        high_water_path=tmp_path / "high-water" / "authority.sqlite3",
        high_water_root=tmp_path / "high-water",
        repo_root=repo,
        replay_store_binding_digest="sha256:" + "7" * 64,
        replay_store_id="signer-grant-replay:test",
        durability_receipt_id="sha256:" + "8" * 64,
    )
    high_water = SqliteMonotonicAuthorityStore(
        config.high_water_path,
        allowed_root=config.high_water_root,
        repo_root=repo,
        store_id=config.replay_store_id,
        durability_receipt_id=config.durability_receipt_id,
    )
    raw_store = AtomicProposalAuthenticityNonceStore(
        config.nonce_path,
        allowed_root=config.nonce_root,
        repo_root=repo,
        integrity_key=INTEGRITY_KEY,
        replay_store_binding_digest=config.replay_store_binding_digest,
        high_water_store=high_water,
        clock=lambda: NOW,
    )
    reservation = raw_store.reserve(
        "fixture-provisioning", expires_at=NOW + 1000, subject="fixture"
    )
    raw_store.rollback(reservation)
    return DurableSignerSecretGrantNonceStore(
        config, integrity_key=INTEGRITY_KEY, clock=lambda: NOW
    )


def _lease(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(lease_module.time, "time", lambda: NOW)
    store = _store(tmp_path)
    request = _request(store)
    response = _backend(request, exact=True).sign(request, _peer())
    lease = lease_module._rehydrate_external_authoritative_use_lease(
        request=request,
        response=response,
        current_generation_authority=_authority(tmp_path, monkeypatch),
        replay_store=store,
        now_epoch=NOW,
    )
    return request, response, lease


def _effect_digest() -> str:
    return authoritative_use_effect_digest("worktree_create", _effect_payload())


def _mapping_digest(value: Mapping[str, Any]) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _invoke_direct_spine(
    order: Mapping[str, Any], repo: Path, lease: AuthoritativeUseLease | None
):
    fixed = datetime(2026, 7, 12, 12, 0, tzinfo=timezone.utc)
    return invoke_reddog_extension_wre_operational_spine_explicit_valve(
        order,
        explicit_wre_operational_spine_requested=True,
        selection_receipt=_selection_receipt(),
        seen_nonces=set(),
        valve_environment=_open_worktree_env(),
        signature_verification_result=_accepted_signature(order),
        runner=FakeRunner(),
        repo_root=repo,
        now=fixed,
        locks=set(),
        authoritative_use_lease=lease,
    )


def _spine_effect(
    order: Mapping[str, Any], spine: Any
) -> dict[str, object]:
    return {
        "queue_item_id": "queue-extension-wre-spine-001",
        "selected_slice": "REDDOG_EXTENSION_WRE_SPINE_TEST_PHASE1",
        "work_order_id": str(order["work_order_id"]),
        "work_order_digest": _mapping_digest(order),
        "executor_plan_digest": _mapping_digest(spine.executor_plan_result),
        "valve_decision_digest": _mapping_digest(spine.valve_decision),
    }


def _is_lease(value: object) -> bool:
    return is_authoritative_use_lease(
        value,
        effect_kind="worktree_create",
        effect_request_digest=_effect_digest(),
    )


def _consume_lease(value: object) -> bool:
    return consume_authoritative_use_lease(
        value,
        effect_kind="worktree_create",
        effect_request_digest=_effect_digest(),
    )


def test_exact_grant_bound_external_signer_releases_one_shot_lease(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, response, lease = _lease(tmp_path, monkeypatch)

    assert response.accepted is True
    assert _is_lease(lease) is True
    assert lease is not None and lease.expires_at_epoch == NOW + 20
    assert _consume_lease(lease) is True
    assert _consume_lease(lease) is False


def test_external_issuer_uses_root_generation_and_durable_replay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(issuer_module.time, "time", lambda: NOW)
    store = _store(tmp_path)
    issuer = ExternalSignerAuthoritativeUseLeaseIssuer(
        signer=_GrantAwareSigner(),
        grant_provider=_LeasedGrantProvider(
            lambda _request: {"grant_id": "root-grant-1"}
        ),
        replay_store=store,
        current_generation_authority=_authority(tmp_path, monkeypatch),
    )

    payload = _payload()
    for field in _replay_binding(store):
        payload.pop(field)
    lease = issuer.issue(payload=payload, authority_tier="HIGH")

    assert _is_lease(lease) is True
    assert _consume_lease(lease) is True


def test_real_lease_reaches_direct_wre_spine_without_monkeypatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(lease_module.time, "time", lambda: NOW)
    fixed = datetime(2026, 7, 12, 12, 0, tzinfo=timezone.utc)
    repo = tmp_path / "spine-repo"
    repo.mkdir()
    order = _base_order(
        fixed,
        queue_consumer_receipt={
            "queue_item_id": "queue-extension-wre-spine-001",
            "slice_id": "REDDOG_EXTENSION_WRE_SPINE_TEST_PHASE1",
        },
    )
    preview = _invoke_direct_spine(order, repo, None)
    assert preview.worktree_spine_result is not None
    spine = preview.worktree_spine_result
    effect = _spine_effect(order, spine)
    store = _store(tmp_path / "lease-store")
    payload = _payload(store, effect_payload=effect)
    payload["effect_request_digest"] = authoritative_use_effect_digest(
        "worktree_create", effect
    )
    request = build_authoritative_use_lease_request(payload, authority_tier="HIGH")
    response = _backend(request, exact=True).sign(request, _peer())
    lease = lease_module._rehydrate_external_authoritative_use_lease(
        request=request,
        response=response,
        current_generation_authority=_authority(tmp_path, monkeypatch),
        replay_store=store,
        now_epoch=NOW,
    )
    result = _invoke_direct_spine(order, repo, lease)
    assert result.decision == EXTENSION_WRE_OPERATIONAL_SPINE_INVOKE_ACCEPT


def test_composed_e0_socket_issuer_reaches_real_wre_spine(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(lease_module.time, "time", lambda: NOW)
    monkeypatch.setattr(issuer_module.time, "time", lambda: NOW)
    store = _store(tmp_path / "e0-store")
    repo = tmp_path / "spine-repo"
    repo.mkdir()
    fixed = datetime(2026, 7, 12, 12, 0, tzinfo=timezone.utc)
    order = _base_order(
        fixed,
        queue_consumer_receipt={
            "queue_item_id": "queue-extension-wre-spine-001",
            "slice_id": "REDDOG_EXTENSION_WRE_SPINE_TEST_PHASE1",
        },
    )
    preview = _invoke_direct_spine(order, repo, None)
    assert preview.worktree_spine_result is not None
    effect = _spine_effect(order, preview.worktree_spine_result)

    def connector(_path, raw: bytes, _timeout: float, _limit: int) -> bytes:
        message = json.loads(raw)
        grant = message["secret_access_grant"]
        return handle_reddog_isolated_signer_socket_request(
            raw, peer=_peer(), backend=_resolve_backend(grant, store)
        )

    client = RedDogIsolatedSignerSocketClient(
        socket_path=tmp_path / "signer.sock", connector=connector
    )
    issuer = ExternalSignerAuthoritativeUseLeaseIssuer(
        signer=client,
        grant_provider=_LeasedGrantProvider(
            lambda request: _root_grant(request, store)
        ),
        replay_store=store,
        current_generation_authority=_authority(tmp_path, monkeypatch),
    )
    payload = _payload(store, effect_payload=effect)
    payload["effect_request_digest"] = authoritative_use_effect_digest(
        "worktree_create", effect
    )

    lease = issuer.issue(payload=payload, authority_tier="HIGH")
    result = _invoke_direct_spine(order, repo, lease)

    assert _is_lease(lease) is False
    assert result.decision == EXTENSION_WRE_OPERATIONAL_SPINE_INVOKE_ACCEPT
