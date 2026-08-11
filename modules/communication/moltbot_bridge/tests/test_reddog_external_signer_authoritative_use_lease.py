"""Adversarial tests for the external authoritative-use lease boundary."""

from __future__ import annotations

import copy
import json
import pickle
from dataclasses import replace
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from modules.communication.moltbot_bridge.src.reddog_authoritative_use_lease import (
    AuthoritativeUseLease,
    consume_authoritative_use_lease,
    is_authoritative_use_lease,
    rehydrate_external_authoritative_use_lease,
)
from modules.communication.moltbot_bridge.src.reddog_authoritative_use_lease_contract import (
    authoritative_use_effect_digest,
    build_authoritative_use_lease_request,
    digest_text,
    validate_authoritative_use_lease_request,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    Ed25519SignatureVerifier,
    encode_ed25519_public_key,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signer_backend import (
    Ed25519SignerBackend,
    bind_exact_signing_request,
)
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_protocol import (
    SignerPeerAttestation,
)
from modules.communication.moltbot_bridge.src.reddog_external_signer_authoritative_use_lease import (
    ExternalSignerAuthoritativeUseLeaseIssuer,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    SigningRequest,
)
from modules.communication.moltbot_bridge.src.reddog_signer_mutual_peer_handshake import (
    SignerPeerInstanceBinding,
    SignerPeerProfileBinding,
)


NOW = 2_000_000_000


class _AuditMac:
    def build(
        self,
        request: SigningRequest,
        _signature: str,
        peer: SignerPeerAttestation,
    ) -> str:
        return "audit:" + request.nonce + ":" + peer.peer_principal_id


class _Clock:
    def __init__(self) -> None:
        self.value = NOW

    def __call__(self) -> int:
        return self.value


class _GrantAwareSigner:
    def sign_with_secret_grant(self, request, secret_access_grant):
        if secret_access_grant != {"grant_id": "root-grant-1"}:
            raise ValueError("grant mismatch")
        return _backend(request, exact=True).sign(request, _peer())


class _ReplaySet:
    def __init__(self) -> None:
        self.seen: set[str] = set()

    def consume_once(self, value: str) -> bool:
        if value in self.seen:
            return False
        self.seen.add(value)
        return True


def _private_key() -> Ed25519PrivateKey:
    return Ed25519PrivateKey.from_private_bytes(bytes(range(32)))


def _public_key() -> str:
    return encode_ed25519_public_key(
        _private_key()
        .public_key()
        .public_bytes(
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
    )


def _payload(**overrides: object) -> dict[str, object]:
    binding = _binding()
    values: dict[str, object] = {
        "schema_version": "reddog_authoritative_use_lease.v1",
        "lease_nonce": "a" * 64,
        "effect_kind": "worktree_create",
        "effect_request_digest": "sha256:" + "5" * 64,
        "requester_principal_id": "github:mjtrout",
        "signer_profile_id": "reddog-work-authority",
        "signer_public_key": _public_key(),
        "key_epoch": "epoch-1",
        "manifest_id": binding.manifest_id,
        "artifact_generation_digest": binding.artifact_generation_digest,
        "generation": 7,
        "generation_revision": "revision-7",
        "owner_config_id": "sha256:" + "6" * 64,
        "run_packet_id": binding.run_packet_id,
        "config_digest": binding.config_digest,
        "session_id": binding.session_id,
        "socket_path_digest": digest_text(binding.socket_path),
        "current_generation_receipt_id": "sha256:" + "7" * 64,
        "lifecycle_admission_receipt_id": "sha256:" + "8" * 64,
        "work_authority_digest": "sha256:" + "9" * 64,
        "identity_digest": "sha256:" + "b" * 64,
        "work_order_id": "work-order-1",
        "work_order_digest": "sha256:" + "c" * 64,
        "queue_item_id": "queue-1",
        "selected_slice": "REDDOG_TEST_PHASE1",
        "expected_bindings_digest": "sha256:" + "d" * 64,
        "issued_at": NOW,
        "expires_at": NOW + 20,
    }
    values.update(overrides)
    return values


def _request(**overrides: object) -> SigningRequest:
    return build_authoritative_use_lease_request(
        _payload(**overrides), authority_tier="HIGH"
    )


def _peer() -> SignerPeerAttestation:
    return SignerPeerAttestation(
        peer_principal_id="github:mjtrout",
        transport="unix_socket",
        credential_source="kernel_peer_credential",
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


def _lease(clock: _Clock, *, evidence: set[str] | None = None):
    request = _request()
    response = _backend(request, exact=True).sign(request, _peer())
    seen = evidence if evidence is not None else set()
    authority_calls: list[bool] = []

    def consume_evidence(value: str) -> bool:
        if value in seen:
            return False
        seen.add(value)
        return True

    lease = rehydrate_external_authoritative_use_lease(
        request=request,
        response=response,
        signature_verifier=Ed25519SignatureVerifier(),
        consume_evidence_once=consume_evidence,
        consume_authority_once=lambda: not authority_calls.append(True),
        trusted_now_epoch=clock,
    )
    return request, response, lease, seen, authority_calls


def _is_lease(value: object) -> bool:
    return is_authoritative_use_lease(
        value,
        effect_kind="worktree_create",
        effect_request_digest="sha256:" + "5" * 64,
    )


def _consume_lease(value: object) -> bool:
    return consume_authoritative_use_lease(
        value,
        effect_kind="worktree_create",
        effect_request_digest="sha256:" + "5" * 64,
    )


def test_exact_grant_bound_external_signer_releases_one_shot_lease() -> None:
    clock = _Clock()
    _, response, lease, _, calls = _lease(clock)

    assert response.accepted is True
    assert _is_lease(lease) is True
    assert lease is not None and lease.expires_at_epoch == NOW + 20
    assert _consume_lease(lease) is True
    assert _consume_lease(lease) is False
    assert calls == [True]


def test_external_issuer_requires_grant_provider_and_signed_response() -> None:
    clock = _Clock()
    replay = _ReplaySet()
    issuer = ExternalSignerAuthoritativeUseLeaseIssuer(
        signer=_GrantAwareSigner(),
        grant_provider=lambda _request: {"grant_id": "root-grant-1"},
        signature_verifier=Ed25519SignatureVerifier(),
        consume_evidence_once=replay.consume_once,
        trusted_now_epoch=clock,
    )

    lease = issuer.issue(
        payload=_payload(),
        authority_tier="HIGH",
        consume_authority_once=lambda: True,
    )

    assert _is_lease(lease) is True
    assert _consume_lease(lease) is True


def test_lease_cannot_be_substituted_for_another_effect() -> None:
    _, _, lease, _, calls = _lease(_Clock())

    assert is_authoritative_use_lease(
        lease,
        effect_kind="live_enqueue",
        effect_request_digest="sha256:" + "5" * 64,
    ) is False
    assert consume_authoritative_use_lease(
        lease,
        effect_kind="worktree_create",
        effect_request_digest="sha256:" + "e" * 64,
    ) is False
    assert calls == []
    assert _consume_lease(lease) is True


def test_signer_rejects_lease_without_exact_external_grant_binding() -> None:
    request = _request()
    response = _backend(request, exact=False).sign(request, _peer())
    assert response.accepted is False


def test_signer_rejects_wrong_current_instance_binding() -> None:
    request = _request(session_id="attacker-session")
    response = _backend(request, exact=True).sign(request, _peer())
    assert response.accepted is False


def test_contract_rejects_unknown_tier_and_binds_canonical_effect() -> None:
    with pytest.raises(ValueError):
        build_authoritative_use_lease_request(_payload(), authority_tier="LOW")
    first = authoritative_use_effect_digest(
        "worktree_create", {"work_order_id": "work-1", "path": "src/a.py"}
    )
    second = authoritative_use_effect_digest(
        "worktree_create", {"path": "src/a.py", "work_order_id": "work-1"}
    )
    assert first == second
    with pytest.raises(ValueError):
        authoritative_use_effect_digest("shell_anything", {})


@pytest.mark.parametrize(
    "field,value",
    [
        ("effect_kind", "shell_anything"),
        ("lease_nonce", "not-a-nonce"),
        ("generation", 0),
        ("expires_at", NOW + 31),
    ],
)
def test_malformed_or_overlong_requests_fail_closed(field: str, value: object) -> None:
    payload = _payload(**{field: value})
    if field == "expires_at":
        request = build_authoritative_use_lease_request(payload, authority_tier="HIGH")
        assert validate_authoritative_use_lease_request(request, now_epoch=NOW) is None
    else:
        with pytest.raises(ValueError):
            build_authoritative_use_lease_request(payload, authority_tier="HIGH")


def test_changed_signed_request_is_rejected_before_capability() -> None:
    request = _request()
    response = _backend(request, exact=True).sign(request, _peer())
    changed = replace(request, payload_digest="sha256:" + "e" * 64)
    lease = rehydrate_external_authoritative_use_lease(
        request=changed,
        response=response,
        signature_verifier=Ed25519SignatureVerifier(),
        consume_evidence_once=lambda _value: True,
        consume_authority_once=lambda: True,
        trusted_now_epoch=lambda: NOW,
    )
    assert lease is None


def test_signed_response_replay_is_rejected_durably() -> None:
    clock = _Clock()
    request, response, first, seen, _ = _lease(clock)
    second = rehydrate_external_authoritative_use_lease(
        request=request,
        response=response,
        signature_verifier=Ed25519SignatureVerifier(),
        consume_evidence_once=lambda value: False if value in seen else True,
        consume_authority_once=lambda: True,
        trusted_now_epoch=clock,
    )
    assert first is not None
    assert second is None


def test_expired_lease_rejects_without_consuming_parent_authority() -> None:
    clock = _Clock()
    _, _, lease, _, calls = _lease(clock)
    clock.value = NOW + 20
    assert _is_lease(lease) is False
    assert _consume_lease(lease) is False
    assert calls == []


def test_capability_cannot_be_constructed_copied_pickled_or_fabricated() -> None:
    with pytest.raises(TypeError):
        AuthoritativeUseLease()
    fabricated = object.__new__(AuthoritativeUseLease)
    assert _is_lease(fabricated) is False
    _, _, lease, _, _ = _lease(_Clock())
    assert lease is not None
    with pytest.raises(TypeError):
        copy.copy(lease)
    with pytest.raises(TypeError):
        copy.deepcopy(lease)
    with pytest.raises(TypeError):
        pickle.dumps(lease)


def test_contract_has_no_execution_or_private_key_surface() -> None:
    root = Path(__file__).parents[1]
    paths = (
        root / "src" / "reddog_authoritative_use_lease.py",
        root / "src" / "reddog_authoritative_use_lease_contract.py",
        root / "src" / "reddog_external_signer_authoritative_use_lease.py",
    )
    combined = "\n".join(path.read_text(encoding="utf-8") for path in paths)
    for forbidden in (
        "subprocess",
        "os.system",
        "shell=True",
        "private_key",
        "HoloIndex.reindex",
        "commit_all",
        "gh pr",
    ):
        assert forbidden not in combined
    assert json.dumps(_payload(), sort_keys=True, ensure_ascii=True).isascii()
