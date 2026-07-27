"""Runtime tests for durable architect-proposal signer policy provisioning."""

from __future__ import annotations

import base64
import dataclasses
import hashlib
import json
import multiprocessing
import threading
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.reddog_architect_proposal_authenticity import (
    ArchitectProposalPolicyAuthorization,
    ArchitectProposalSignerPolicy,
    PROPOSAL_AUTHENTICITY_SIGNING_OPERATION,
    PROPOSAL_AUTHENTICITY_SIGNER_ROLE,
    build_architect_proposal_authenticity_payload,
    build_architect_proposal_policy_authorization_payload,
    canonical_architect_proposal_policy_authorization_input,
    canonical_architect_proposal_signing_input,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signer_backend import (
    REJECT_ED25519_SIGNER_PROPOSAL_DOMAIN_ONLY,
    REJECT_ED25519_SIGNER_PROPOSAL_NONCE_REPLAY,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    encode_ed25519_public_key,
    encode_ed25519_signature,
)
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_protocol import (
    SignerPeerAttestation,
)
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_resident_service import (
    SIGNER_SOCKET_RESIDENT_SERVICE_SERVED,
    IsolatedSignerSocketResidentServiceResult,
)
from modules.communication.moltbot_bridge.src.reddog_proposal_authenticity_nonce_store import (
    AtomicProposalAuthenticityNonceStore,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    SigningRequest,
    public_key_fingerprint,
)
from modules.communication.moltbot_bridge.src.reddog_signer_key_provider_dryrun import (
    AUDIT_KEY_PREFIX,
    PROVIDER_MODE_TEST_ONLY_DRYRUN,
    SIGNING_KEY_PREFIX,
    SignerKeyProviderProfile,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_peer_credential_attestor import (
    PeerCredentialPolicy,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_config_supply import (
    FAIL_SIGNER_CONFIG_PROPOSAL_NONCE_PATH_INVALID,
    FAIL_SIGNER_CONFIG_PROPOSAL_POLICY_AUTHORIZATION_INVALID,
    FAIL_SIGNER_CONFIG_PROPOSAL_POLICY_INVALID,
    run_reddog_signer_socket_service_config_supply,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_runtime_bootstrap import (
    FAIL_SIGNER_BOOTSTRAP_CONFIG_DIGEST_MISMATCH,
    FAIL_SIGNER_BOOTSTRAP_CONFIG_MALFORMED,
    rehydrate_signer_socket_service_runtime_config,
    run_reddog_signer_socket_service_runtime_bootstrap,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_runtime_wiring import (
    FAIL_SIGNER_RUNTIME_PROPOSAL_NONCE_STORE_INVALID,
    FAIL_SIGNER_RUNTIME_PROPOSAL_POLICY_AUTHORIZATION_INVALID,
    FAIL_SIGNER_RUNTIME_PROPOSAL_POLICY_INVALID,
    SignerSocketServiceRuntimeWiringConfig,
    run_reddog_signer_socket_service_runtime_wiring,
    validate_signer_socket_service_runtime_config,
)
from modules.infrastructure.secrets_mcp.src.vault_resolver import (
    ResolveResult,
    hash_reference,
)


pytest.importorskip("cryptography")

NOW = int(time.time())
PRINCIPAL_PUBLIC = encode_ed25519_public_key(bytes(range(32)))
INTEGRITY_KEY = b"proposal-integrity-key-32-bytes!"


def _private_key():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
    )

    return Ed25519PrivateKey.generate()


def _private_key_secret(private_key) -> str:
    from cryptography.hazmat.primitives import serialization

    raw = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return SIGNING_KEY_PREFIX + base64.b64encode(raw).decode("ascii")


def _public_text(private_key) -> str:
    from cryptography.hazmat.primitives import serialization

    raw = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return encode_ed25519_public_key(raw)


def _payload(public_key: str, **overrides: object):
    proposal = {
        "receipt_id": "sha256:" + "1" * 64,
        "snapshot_receipt_id": "snapshot-1",
        "snapshot_content_digest": "sha256:" + "2" * 64,
        "repo_head_sha": "a" * 40,
        "work_state_revision": "revision-1",
        "report_bundle_id": "report-bundle-1",
        "wsp15_allocation_receipt_id": "wsp15-1",
        "wsp15_allocation_digest": "sha256:" + "3" * 64,
        "holoindex_generation_id": "generation-1",
        "holoindex_freshness_receipt_digest": "sha256:" + "4" * 64,
        "policy_digest": "sha256:" + "5" * 64,
        "allowed_paths": ["modules/example.py"],
        "denied_paths": [".env"],
        "required_tests": ["pytest focused"],
        "required_policy_gates": ["WSP_97"],
        "target_effect_plane": "REPOSITORY_CODE_CHANGE",
    }
    candidate = {
        "queue_candidate_id": "sha256:" + "6" * 64,
        "status": "CANDIDATE",
        "slice_id": "REDDOG_EXAMPLE_PHASE1",
    }
    determination = {
        "determination_receipt_id": "sha256:" + "7" * 64,
        "action": "FIX",
        "next_slice_name": "REDDOG_EXAMPLE_PHASE1",
        "queue_candidate": candidate,
    }
    values = {
        "proposal_admission": proposal,
        "determination": determination,
        "queue_candidate": candidate,
        "requester_principal_id": "github:mjtrout",
        "reddog_id": "reddog:foundups-agent",
        "signer_public_key": public_key,
        "key_epoch": "epoch-1",
        "consensus_receipt_digest": "sha256:" + "8" * 64,
        "authority_profile_source_receipt_id": "sha256:" + "9" * 64,
        "nonce": "proposal-runtime-nonce-1",
        "issued_at": NOW - 5,
        "expires_at": NOW + 120,
    }
    values.update(overrides)
    return build_architect_proposal_authenticity_payload(**values)


def _profile(
    public_key: str,
    *,
    principal_public_key: str = PRINCIPAL_PUBLIC,
) -> dict[str, object]:
    return {
        "principal_id": "github:mjtrout",
        "principal_public_key": principal_public_key,
        "reddog_id": "reddog:foundups-agent",
        "reddog_public_key": public_key,
        "permission_snapshot_digest": "sha256:" + "a" * 64,
        "key_epoch": "epoch-1",
        "consensus_receipt_digest": "sha256:" + "8" * 64,
        "authority_profile_source_receipt_id": "sha256:" + "9" * 64,
    }


def _policy_authorization(
    policy: ArchitectProposalSignerPolicy,
    *,
    principal_private,
    public_key: str,
    profile: dict[str, object] | None = None,
    issued_at: int = NOW - 5,
    expires_at: int = NOW + 120,
) -> ArchitectProposalPolicyAuthorization:
    authority_profile = profile or _profile(
        public_key,
        principal_public_key=_public_text(principal_private),
    )
    payload = build_architect_proposal_policy_authorization_payload(
        policy,
        principal_id=str(authority_profile["principal_id"]),
        principal_public_key=str(
            authority_profile["principal_public_key"]
        ),
        reddog_id=str(authority_profile["reddog_id"]),
        reddog_public_key=str(authority_profile["reddog_public_key"]),
        key_epoch=str(authority_profile["key_epoch"]),
        authority_profile_source_receipt_id=str(
            authority_profile["authority_profile_source_receipt_id"]
        ),
        nonce="proposal-policy-authorization-nonce-1",
        issued_at=issued_at,
        expires_at=expires_at,
    )
    signature = encode_ed25519_signature(
        principal_private.sign(
            canonical_architect_proposal_policy_authorization_input(
                payload
            ).encode("utf-8")
        )
    )
    return ArchitectProposalPolicyAuthorization(
        **payload,
        signature=signature,
    )


def _provider_profiles(
    *,
    principal_private,
    reddog_private,
) -> tuple[SignerKeyProviderProfile, SignerKeyProviderProfile]:
    principal_public = _public_text(principal_private)
    reddog_public = _public_text(reddog_private)
    common = {
        "expected_key_epoch": "epoch-1",
        "permission_snapshot_digest": "sha256:" + "a" * 64,
        "ttl_seconds": 60,
    }
    return (
        SignerKeyProviderProfile(
            signer_profile_id="principal-identity",
            signer_agent_id="signer:principal",
            signing_key_ref="op://test/principal/private",
            audit_mac_key_ref="op://test/principal/audit",
            expected_public_key=principal_public,
            expected_key_fingerprint=public_key_fingerprint(
                principal_public
            ),
            **common,
        ),
        SignerKeyProviderProfile(
            signer_profile_id="reddog-work-authority",
            signer_agent_id="signer:reddog",
            signing_key_ref="op://test/reddog/private",
            audit_mac_key_ref="op://test/reddog/audit",
            expected_public_key=reddog_public,
            expected_key_fingerprint=public_key_fingerprint(
                reddog_public
            ),
            **common,
        ),
    )


def _signing_request(payload) -> SigningRequest:
    signing_input = canonical_architect_proposal_signing_input(payload)
    payload_digest = "sha256:" + hashlib.sha256(
        json.dumps(
            {"signing_input": signing_input},
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()
    return SigningRequest(
        signing_input=signing_input,
        payload_digest=payload_digest,
        signer_role=PROPOSAL_AUTHENTICITY_SIGNER_ROLE,
        signer_public_key=payload.signer_public_key,
        requester_principal_id=payload.requester_principal_id,
        nonce=payload.nonce,
        key_epoch=payload.key_epoch,
        requested_operation=PROPOSAL_AUTHENTICITY_SIGNING_OPERATION,
        authority_tier="ULTRA",
        consensus_receipt_digest=payload.consensus_receipt_digest,
    )


def _peer() -> SignerPeerAttestation:
    return SignerPeerAttestation(
        peer_principal_id="github:mjtrout",
        transport="unix_socket",
        credential_source="kernel_peer_credential",
        boundary_attested=True,
    )


def _reserve_nonce_process(
    values: tuple[str, str, str, int],
) -> bool:
    repo, runtime, nonce, expires_at = values
    store = AtomicProposalAuthenticityNonceStore(
        Path(runtime) / "proposal-nonces.json",
        allowed_root=runtime,
        repo_root=repo,
        integrity_key=INTEGRITY_KEY,
    )
    return bool(
        store.reserve(
            nonce,
            expires_at=expires_at,
            subject="github:mjtrout",
        )
    )


def _config_kwargs(
    repo: Path,
    runtime: Path,
    public_key: str,
    policy: ArchitectProposalSignerPolicy,
    principal_private,
    **overrides: object,
) -> dict[str, object]:
    profile = _profile(
        public_key,
        principal_public_key=_public_text(principal_private),
    )
    values: dict[str, object] = {
        "repo_root": repo,
        "runtime_root": runtime,
        "signer_runtime_root": runtime.parent / "signer-state",
        "authority_profile": profile,
        "output_path": runtime / "signer-service.json",
        "socket_path": runtime / "reddog-signer.sock",
        "principal_signing_key_ref": "op://prod/principal/private",
        "principal_audit_mac_key_ref": "op://prod/principal/audit",
        "reddog_signing_key_ref": "op://prod/reddog/private",
        "reddog_audit_mac_key_ref": "op://prod/reddog/audit",
        "peer_uid_to_principal": {1001: "github:mjtrout"},
        "proposal_authority_policy": policy,
        "proposal_policy_authorization": _policy_authorization(
            policy,
            principal_private=principal_private,
            public_key=public_key,
            profile=profile,
        ),
        "now_epoch": NOW,
        "max_requests": 2,
    }
    values.update(overrides)
    return values


def test_atomic_nonce_store_survives_restart_and_rejects_replay(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    runtime = tmp_path / "signer-state"
    repo.mkdir()
    store_path = runtime / "proposal-nonces.json"
    first = AtomicProposalAuthenticityNonceStore(
        store_path,
        allowed_root=runtime,
        repo_root=repo,
        integrity_key=INTEGRITY_KEY,
    )

    reservation = first.reserve(
        "nonce-1",
        expires_at=NOW + 60,
        subject="github:mjtrout",
    )
    assert reservation
    first.commit(reservation)

    restarted = AtomicProposalAuthenticityNonceStore(
        store_path,
        allowed_root=runtime,
        repo_root=repo,
        integrity_key=INTEGRITY_KEY,
    )
    assert (
        restarted.reserve(
            "nonce-1",
            expires_at=NOW + 120,
            subject="github:mjtrout",
        )
        is None
    )
    state = json.loads(store_path.read_text(encoding="utf-8"))
    assert state["consumed"]
    assert "nonce-1" not in json.dumps(state, sort_keys=True)


def test_atomic_nonce_store_rollback_and_racing_reservations(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    runtime = tmp_path / "signer-state"
    repo.mkdir()
    store_path = runtime / "proposal-nonces.json"
    first = AtomicProposalAuthenticityNonceStore(
        store_path,
        allowed_root=runtime,
        repo_root=repo,
        integrity_key=INTEGRITY_KEY,
    )
    second = AtomicProposalAuthenticityNonceStore(
        store_path,
        allowed_root=runtime,
        repo_root=repo,
        integrity_key=INTEGRITY_KEY,
    )
    initial = first.reserve(
        "rollback-nonce",
        expires_at=NOW + 60,
        subject="github:mjtrout",
    )
    assert initial
    first.rollback(initial)
    assert second.reserve(
        "rollback-nonce",
        expires_at=NOW + 60,
        subject="github:mjtrout",
    )

    barrier = threading.Barrier(2)
    results: list[str | None] = []

    def reserve(store: AtomicProposalAuthenticityNonceStore) -> None:
        barrier.wait()
        results.append(
            store.reserve(
                "race-nonce",
                expires_at=NOW + 60,
                subject="github:mjtrout",
            )
        )

    threads = [
        threading.Thread(target=reserve, args=(first,)),
        threading.Thread(target=reserve, args=(second,)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sum(result is not None for result in results) == 1


def test_atomic_nonce_store_rejects_repo_path_and_malformed_state(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    runtime = tmp_path / "signer-state"
    repo.mkdir()
    with pytest.raises(ValueError):
        AtomicProposalAuthenticityNonceStore(
            repo / "nonce.json",
            allowed_root=repo,
            repo_root=repo,
            integrity_key=INTEGRITY_KEY,
        )

    store_path = runtime / "proposal-nonces.json"
    store_path.parent.mkdir()
    store_path.write_text('{"schema_version":"wrong"}', encoding="utf-8")
    store = AtomicProposalAuthenticityNonceStore(
        store_path,
        allowed_root=runtime,
        repo_root=repo,
        integrity_key=INTEGRITY_KEY,
    )
    with pytest.raises(ValueError):
        store.reserve(
            "nonce",
            expires_at=NOW + 60,
            subject="github:mjtrout",
        )


def test_atomic_nonce_store_rejects_structurally_valid_state_tampering(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    runtime = tmp_path / "signer-state"
    repo.mkdir()
    store_path = runtime / "proposal-nonces.json"
    store = AtomicProposalAuthenticityNonceStore(
        store_path,
        allowed_root=runtime,
        repo_root=repo,
        integrity_key=INTEGRITY_KEY,
    )
    reservation = store.reserve(
        "tamper-nonce",
        expires_at=NOW + 60,
        subject="github:mjtrout",
    )
    assert reservation
    store.commit(reservation)
    state = json.loads(store_path.read_text(encoding="utf-8"))
    state["consumed"] = {}
    store_path.write_text(
        json.dumps(state, sort_keys=True),
        encoding="utf-8",
    )

    restarted = AtomicProposalAuthenticityNonceStore(
        store_path,
        allowed_root=runtime,
        repo_root=repo,
        integrity_key=INTEGRITY_KEY,
    )
    with pytest.raises(
        ValueError,
        match="proposal_authenticity_nonce_store_integrity_invalid",
    ):
        restarted.reserve(
            "tamper-nonce",
            expires_at=NOW + 120,
            subject="github:mjtrout",
        )


def test_atomic_nonce_store_prunes_expired_crash_state_and_is_bounded(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    runtime = tmp_path / "signer-state"
    repo.mkdir()
    now = [NOW]
    store = AtomicProposalAuthenticityNonceStore(
        runtime / "proposal-nonces.json",
        allowed_root=runtime,
        repo_root=repo,
        integrity_key=INTEGRITY_KEY,
        clock=lambda: now[0],
        clock_skew_seconds=2,
        retention_seconds=4,
        max_entries=2,
    )
    stranded = store.reserve(
        "crash-nonce",
        expires_at=NOW + 1,
        subject="github:mjtrout",
    )
    assert stranded
    now[0] = NOW + 4
    reclaimed = store.reserve(
        "crash-nonce",
        expires_at=NOW + 20,
        subject="github:mjtrout",
    )
    assert reclaimed
    store.commit(reclaimed)
    assert store.reserve(
        "second-nonce",
        expires_at=NOW + 20,
        subject="github:mjtrout",
    )
    assert (
        store.reserve(
            "over-capacity",
            expires_at=NOW + 20,
            subject="github:mjtrout",
        )
        is None
    )


def test_atomic_nonce_store_serializes_cross_process_reservation(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    runtime = tmp_path / "signer-state"
    repo.mkdir()
    jobs = [
        (str(repo), str(runtime), "process-race", NOW + 60),
        (str(repo), str(runtime), "process-race", NOW + 60),
    ]
    with ProcessPoolExecutor(
        max_workers=2,
        mp_context=multiprocessing.get_context("spawn"),
    ) as executor:
        results = list(executor.map(_reserve_nonce_process, jobs))
    assert sum(results) == 1


def test_config_supply_binds_exact_policy_and_confined_nonce_store(
    tmp_path: Path,
) -> None:
    private_key = _private_key()
    principal_private = _private_key()
    public_key = _public_text(private_key)
    policy = ArchitectProposalSignerPolicy(_payload(public_key))
    repo = tmp_path / "repo"
    runtime = tmp_path / "runtime"
    repo.mkdir()

    result = run_reddog_signer_socket_service_config_supply(
        **_config_kwargs(
            repo,
            runtime,
            public_key,
            policy,
            principal_private,
        )
    )

    assert result.accepted is True
    assert result.proposal_policy_configured is True
    assert result.proposal_attestation_id == policy.expected_payload.attestation_id
    config = json.loads(
        (runtime / "signer-service.json").read_text(encoding="utf-8")
    )
    assert (
        config["proposal_authority_policy"]["expected_payload"]
        == policy.expected_payload.to_dict()
    )
    assert result.profile_count == 2
    assert [
        item["signer_profile_id"]
        for item in config["key_provider_profiles"]
    ] == ["principal-identity", "reddog-work-authority"]
    assert (
        config["proposal_policy_authorization"][
            "proposal_policy_digest"
        ]
        == _policy_authorization(
            policy,
            principal_private=principal_private,
            public_key=public_key,
        ).proposal_policy_digest
    )
    nonce_path = Path(config["proposal_nonce_store_path"])
    assert nonce_path.parent == (tmp_path / "signer-state").resolve()
    assert result.proposal_nonce_store_path == str(nonce_path)
    assert not nonce_path.exists()

    rehydrated = rehydrate_signer_socket_service_runtime_config(
        repo,
        runtime,
        config,
        expected_config_digest=result.config_digest,
    )
    assert rehydrated is not None
    assert rehydrated.proposal_nonce_store_path == nonce_path


def test_config_supply_requires_valid_principal_signed_policy_authorization(
    tmp_path: Path,
) -> None:
    reddog_private = _private_key()
    principal_private = _private_key()
    public_key = _public_text(reddog_private)
    policy = ArchitectProposalSignerPolicy(_payload(public_key))
    repo = tmp_path / "repo"
    repo.mkdir()

    missing_kwargs = _config_kwargs(
        repo,
        tmp_path / "missing",
        public_key,
        policy,
        principal_private,
    )
    missing_kwargs.pop("proposal_policy_authorization")
    missing = run_reddog_signer_socket_service_config_supply(
        **missing_kwargs
    )
    assert missing.accepted is False
    assert missing.rejection_reasons == (
        FAIL_SIGNER_CONFIG_PROPOSAL_POLICY_AUTHORIZATION_INVALID,
    )

    tampered_kwargs = _config_kwargs(
        repo,
        tmp_path / "tampered",
        public_key,
        policy,
        principal_private,
    )
    authorization = tampered_kwargs["proposal_policy_authorization"]
    assert isinstance(
        authorization,
        ArchitectProposalPolicyAuthorization,
    )
    tampered_kwargs["proposal_policy_authorization"] = dataclasses.replace(
        authorization,
        signature=encode_ed25519_signature(b"x" * 64),
    )
    tampered = run_reddog_signer_socket_service_config_supply(
        **tampered_kwargs
    )
    assert tampered.accepted is False
    assert tampered.rejection_reasons == (
        FAIL_SIGNER_CONFIG_PROPOSAL_POLICY_AUTHORIZATION_INVALID,
    )

    altered_policy_kwargs = _config_kwargs(
        repo,
        tmp_path / "altered-policy",
        public_key,
        policy,
        principal_private,
    )
    altered_policy_kwargs["proposal_authority_policy"] = (
        ArchitectProposalSignerPolicy(
            dataclasses.replace(
                policy.expected_payload,
                nonce="different-proposal-nonce",
            )
        )
    )
    altered = run_reddog_signer_socket_service_config_supply(
        **altered_policy_kwargs
    )
    assert altered.accepted is False
    assert altered.rejection_reasons == (
        FAIL_SIGNER_CONFIG_PROPOSAL_POLICY_AUTHORIZATION_INVALID,
    )

    expired_kwargs = _config_kwargs(
        repo,
        tmp_path / "expired",
        public_key,
        policy,
        principal_private,
    )
    expired_kwargs["proposal_policy_authorization"] = (
        _policy_authorization(
            policy,
            principal_private=principal_private,
            public_key=public_key,
            issued_at=NOW - 400,
            expires_at=NOW - 1,
        )
    )
    expired = run_reddog_signer_socket_service_config_supply(
        **expired_kwargs
    )
    assert expired.accepted is False
    assert expired.rejection_reasons == (
        FAIL_SIGNER_CONFIG_PROPOSAL_POLICY_AUTHORIZATION_INVALID,
    )


@pytest.mark.parametrize(
    ("payload_override", "call_override", "reason"),
    [
        (
            {"requester_principal_id": "github:attacker"},
            {},
            FAIL_SIGNER_CONFIG_PROPOSAL_POLICY_INVALID,
        ),
        (
            {"reddog_id": "reddog:attacker"},
            {},
            FAIL_SIGNER_CONFIG_PROPOSAL_POLICY_INVALID,
        ),
        (
            {},
            {"proposal_nonce_store_path": Path("relative/nonce.json")},
            FAIL_SIGNER_CONFIG_PROPOSAL_NONCE_PATH_INVALID,
        ),
    ],
)
def test_config_supply_rejects_identity_or_nonce_path_substitution(
    tmp_path: Path,
    payload_override: dict[str, object],
    call_override: dict[str, object],
    reason: str,
) -> None:
    private_key = _private_key()
    principal_private = _private_key()
    public_key = _public_text(private_key)
    policy = ArchitectProposalSignerPolicy(
        _payload(public_key, **payload_override)
    )
    repo = tmp_path / "repo"
    runtime = tmp_path / "runtime"
    repo.mkdir()

    result = run_reddog_signer_socket_service_config_supply(
        **_config_kwargs(
            repo,
            runtime,
            public_key,
            policy,
            principal_private,
            **call_override,
        )
    )

    assert result.accepted is False
    assert reason in result.rejection_reasons
    assert not (runtime / "signer-service.json").exists()


class _Resolver:
    def __init__(self, private_key, principal_private=None) -> None:
        self._values = {
            "op://test/reddog/private": _private_key_secret(private_key),
            "op://test/reddog/audit": (
                AUDIT_KEY_PREFIX
                + base64.b64encode(b"a" * 32).decode("ascii")
            ),
        }
        if principal_private is not None:
            self._values.update(
                {
                    "op://test/principal/private": (
                        _private_key_secret(principal_private)
                    ),
                    "op://test/principal/audit": (
                        AUDIT_KEY_PREFIX
                        + base64.b64encode(b"p" * 32).decode("ascii")
                    ),
                }
            )

    def resolve(
        self,
        reference: str,
        requester_id: str | None = None,
    ) -> ResolveResult:
        return ResolveResult(
            success=True,
            reference=reference,
            reference_hash=hash_reference(reference),
            ttl_remaining=60,
            session_id="test-session",
            _secret_value=self._values[reference],
        )


def test_runtime_wiring_injects_policy_and_durable_store_into_backend(
    tmp_path: Path,
) -> None:
    private_key = _private_key()
    principal_private = _private_key()
    public_key = _public_text(private_key)
    policy = ArchitectProposalSignerPolicy(_payload(public_key))
    repo = tmp_path / "repo"
    runtime = tmp_path / "runtime"
    signer_runtime = tmp_path / "signer-state"
    repo.mkdir()
    captured: dict[str, object] = {}

    def serve(**kwargs):
        captured.update(kwargs)
        return IsolatedSignerSocketResidentServiceResult(
            accepted=True,
            status=SIGNER_SOCKET_RESIDENT_SERVICE_SERVED,
            rejection_reasons=(),
            socket_path=str(kwargs["socket_path"]),
            requests_handled=0,
            response_digests=(),
            socket_removed=True,
        )

    profiles = _provider_profiles(
        principal_private=principal_private,
        reddog_private=private_key,
    )
    authority_profile = _profile(
        public_key,
        principal_public_key=_public_text(principal_private),
    )
    authorization = _policy_authorization(
        policy,
        principal_private=principal_private,
        public_key=public_key,
        profile=authority_profile,
    )
    config = SignerSocketServiceRuntimeWiringConfig(
        repo_root=repo,
        runtime_root=runtime,
        signer_runtime_root=signer_runtime,
        socket_path=runtime / "signer.sock",
        peer_policy=PeerCredentialPolicy(
            uid_to_principal={1001: "github:mjtrout"},
            allowed_gids=(),
        ),
        key_provider_profiles=profiles,
        provider_mode=PROVIDER_MODE_TEST_ONLY_DRYRUN,
        allow_test_only_key_material=True,
        permission_snapshot_fresh=True,
        control_loop_anchor_path=None,
        control_loop_authority_policy=None,
        proposal_authority_policy=policy,
        proposal_policy_authorization=authorization,
        proposal_nonce_store_path=signer_runtime / "proposal-nonces.json",
    )

    result = run_reddog_signer_socket_service_runtime_wiring(
        config,
        _Resolver(private_key, principal_private),
        serve_bounded=serve,
    )

    assert result.accepted is True
    backend = captured["backend"]
    assert backend.proposal_authority_policy == policy
    assert isinstance(
        backend.proposal_nonce_store,
        AtomicProposalAuthenticityNonceStore,
    )

    first = backend.sign(_signing_request(policy.expected_payload), _peer())
    assert first.accepted is True

    restarted = dataclasses.replace(
        backend,
        proposal_nonce_store=AtomicProposalAuthenticityNonceStore(
            signer_runtime / "proposal-nonces.json",
            allowed_root=signer_runtime,
            repo_root=repo,
            integrity_key=b"a" * 32,
        ),
    )
    replay = restarted.sign(
        _signing_request(policy.expected_payload),
        _peer(),
    )
    assert replay.accepted is False
    assert (
        replay.rejection_code
        == REJECT_ED25519_SIGNER_PROPOSAL_NONCE_REPLAY
    )
    generic = backend.sign(
        dataclasses.replace(
            _signing_request(policy.expected_payload),
            signing_input="reddog-workauth.v1.{}",
            requested_operation="create_foundup",
        ),
        _peer(),
    )
    assert generic.accepted is False
    assert (
        generic.rejection_code
        == REJECT_ED25519_SIGNER_PROPOSAL_DOMAIN_ONLY
    )
    principal_key_request = backend.sign(
        dataclasses.replace(
            _signing_request(policy.expected_payload),
            signer_public_key=_public_text(principal_private),
        ),
        _peer(),
    )
    assert principal_key_request.accepted is False

    class _FailCommitStore:
        rolled_back = False

        def reserve(
            self,
            nonce: str,
            *,
            expires_at: int,
            subject: str,
        ) -> str:
            return "reservation"

        def commit(self, reservation: str) -> None:
            raise RuntimeError("commit_failed")

        def rollback(self, reservation: str) -> None:
            self.rolled_back = True

    fail_store = _FailCommitStore()
    failed = dataclasses.replace(
        backend,
        proposal_nonce_store=fail_store,
    ).sign(_signing_request(policy.expected_payload), _peer())
    assert failed.accepted is False
    assert failed.signature == ""
    assert failed.audit_mac == ""
    assert fail_store.rolled_back is True


def test_bootstrap_rejects_tampered_serialized_proposal_policy(
    tmp_path: Path,
) -> None:
    private_key = _private_key()
    principal_private = _private_key()
    public_key = _public_text(private_key)
    policy = ArchitectProposalSignerPolicy(_payload(public_key))
    repo = tmp_path / "repo"
    runtime = tmp_path / "runtime"
    repo.mkdir()
    result = run_reddog_signer_socket_service_config_supply(
        **_config_kwargs(
            repo,
            runtime,
            public_key,
            policy,
            principal_private,
        )
    )
    assert result.accepted is True
    config_path = runtime / "signer-service.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    replacement_proposal = {
        **{
            "receipt_id": "sha256:" + "1" * 64,
            "snapshot_receipt_id": "snapshot-1",
            "snapshot_content_digest": "sha256:" + "2" * 64,
            "repo_head_sha": "a" * 40,
            "work_state_revision": "revision-1",
            "report_bundle_id": "report-bundle-1",
            "wsp15_allocation_receipt_id": "wsp15-1",
            "wsp15_allocation_digest": "sha256:" + "3" * 64,
            "holoindex_generation_id": "generation-1",
            "holoindex_freshness_receipt_digest": (
                "sha256:" + "4" * 64
            ),
            "policy_digest": "sha256:" + "5" * 64,
            "denied_paths": [".env"],
            "required_tests": ["pytest focused"],
            "required_policy_gates": ["WSP_97"],
            "target_effect_plane": "REPOSITORY_CODE_CHANGE",
        },
        "allowed_paths": ["modules/attacker.py"],
    }
    replacement = _payload(
        public_key,
        proposal_admission=replacement_proposal,
    )
    config["proposal_authority_policy"]["expected_payload"] = (
        replacement.to_dict()
    )

    assert (
        rehydrate_signer_socket_service_runtime_config(
            repo,
            runtime,
            config,
            expected_config_digest=result.config_digest,
        )
        is None
    )
    config_path.write_text(
        json.dumps(config, sort_keys=True),
        encoding="utf-8",
    )
    bootstrap = run_reddog_signer_socket_service_runtime_bootstrap(
        repo_root=repo,
        config_path=config_path,
        resolver=_Resolver(private_key),
        serve_bounded=lambda **kwargs: pytest.fail(
            "tampered config reached signer service"
        ),
        expected_config_digest=result.config_digest,
    )
    assert bootstrap.accepted is False
    assert bootstrap.rejection_reasons == (
        FAIL_SIGNER_BOOTSTRAP_CONFIG_DIGEST_MISMATCH,
    )
    replacement_digest = "sha256:" + hashlib.sha256(
        json.dumps(
            config,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()
    self_consistent = run_reddog_signer_socket_service_runtime_bootstrap(
        repo_root=repo,
        config_path=config_path,
        resolver=_Resolver(private_key, principal_private),
        serve_bounded=lambda **kwargs: pytest.fail(
            "self-consistent unauthorized policy reached signer service"
        ),
        expected_config_digest=replacement_digest,
    )
    assert self_consistent.accepted is False
    assert self_consistent.rejection_reasons == (
        FAIL_SIGNER_BOOTSTRAP_CONFIG_MALFORMED,
    )


def test_runtime_config_rejects_partial_or_mismatched_proposal_wiring(
    tmp_path: Path,
) -> None:
    private_key = _private_key()
    principal_private = _private_key()
    public_key = _public_text(private_key)
    other_key = _public_text(_private_key())
    repo = tmp_path / "repo"
    runtime = tmp_path / "runtime"
    signer_runtime = tmp_path / "signer-state"
    repo.mkdir()
    profiles = _provider_profiles(
        principal_private=principal_private,
        reddog_private=private_key,
    )
    policy = ArchitectProposalSignerPolicy(_payload(public_key))
    authorization = _policy_authorization(
        policy,
        principal_private=principal_private,
        public_key=public_key,
    )
    base = {
        "repo_root": repo,
        "runtime_root": runtime,
        "signer_runtime_root": signer_runtime,
        "socket_path": runtime / "signer.sock",
        "peer_policy": PeerCredentialPolicy(
            uid_to_principal={1001: "github:mjtrout"},
            allowed_gids=(),
        ),
        "key_provider_profiles": profiles,
        "provider_mode": PROVIDER_MODE_TEST_ONLY_DRYRUN,
        "allow_test_only_key_material": True,
        "permission_snapshot_fresh": True,
        "proposal_policy_authorization": authorization,
    }
    missing_store = SignerSocketServiceRuntimeWiringConfig(
        **base,
        proposal_authority_policy=policy,
    )
    mismatched_key = SignerSocketServiceRuntimeWiringConfig(
        **base,
        proposal_authority_policy=ArchitectProposalSignerPolicy(
            _payload(other_key)
        ),
        proposal_nonce_store_path=signer_runtime / "proposal-nonces.json",
    )
    substituted_profile = SignerSocketServiceRuntimeWiringConfig(
        **{
            **base,
            "key_provider_profiles": (
                profiles[0],
                dataclasses.replace(
                    profiles[1],
                    signer_profile_id="principal-identity",
                ),
            ),
        },
        proposal_authority_policy=policy,
        proposal_nonce_store_path=signer_runtime / "proposal-nonces.json",
    )
    excessive_ttl = SignerSocketServiceRuntimeWiringConfig(
        **base,
        proposal_authority_policy=ArchitectProposalSignerPolicy(
            _payload(public_key),
            max_ttl_seconds=301,
        ),
        proposal_nonce_store_path=signer_runtime / "proposal-nonces.json",
    )

    assert validate_signer_socket_service_runtime_config(missing_store) == (
        FAIL_SIGNER_RUNTIME_PROPOSAL_NONCE_STORE_INVALID,
    )
    assert validate_signer_socket_service_runtime_config(mismatched_key) == (
        FAIL_SIGNER_RUNTIME_PROPOSAL_POLICY_AUTHORIZATION_INVALID,
    )
    assert validate_signer_socket_service_runtime_config(
        substituted_profile
    ) == (FAIL_SIGNER_RUNTIME_PROPOSAL_POLICY_AUTHORIZATION_INVALID,)
    assert validate_signer_socket_service_runtime_config(excessive_ttl) == (
        FAIL_SIGNER_RUNTIME_PROPOSAL_POLICY_INVALID,
    )
