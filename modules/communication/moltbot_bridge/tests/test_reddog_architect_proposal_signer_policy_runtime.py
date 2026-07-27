"""Runtime tests for durable architect-proposal signer policy provisioning."""

from __future__ import annotations

import base64
import dataclasses
import hashlib
import hmac
import json
import multiprocessing
import sqlite3
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
    architect_proposal_replay_store_binding_digest,
    architect_proposal_signer_instance_id,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signer_backend import (
    REJECT_ED25519_SIGNER_PROPOSAL_DOMAIN_ONLY,
    REJECT_ED25519_SIGNER_PROPOSAL_NONCE_REPLAY,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    decode_ed25519_signature,
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
    InMemoryProposalReplayHighWaterStore,
    ProposalReplayHighWater,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    SigningRequest,
    public_key_fingerprint,
)
from modules.communication.moltbot_bridge.src.reddog_signer_key_provider_dryrun import (
    AUDIT_KEY_PREFIX,
    PROVIDER_MODE_TEST_ONLY_DRYRUN,
    PROVIDER_MODE_WSP71_PERMISSIONED,
    SIGNING_KEY_PREFIX,
    SignerKeyProviderProfile,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_peer_credential_attestor import (
    PeerCredentialPolicy,
)
from modules.communication.moltbot_bridge.src import (
    reddog_signer_socket_service_config_supply as config_supply,
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
    architect_proposal_security_context_digest,
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
HIGH_WATER_STORE_ID = "proposal-replay-authority:test"
HIGH_WATER_DURABILITY_RECEIPT_ID = "sha256:" + "d" * 64


class _SqliteProposalReplayHighWaterStore:
    """Cross-process test authority kept outside the signer-state directory."""

    def __init__(self, path: Path | str) -> None:
        self._path = str(Path(path))
        Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._path) as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS replay_high_water ("
                "binding_digest TEXT PRIMARY KEY,"
                "sequence INTEGER NOT NULL,"
                "state_revision TEXT NOT NULL)"
            )

    @property
    def store_id(self) -> str:
        return HIGH_WATER_STORE_ID

    @property
    def durable(self) -> bool:
        return True

    @property
    def durability_receipt_id(self) -> str:
        return HIGH_WATER_DURABILITY_RECEIPT_ID

    def load(
        self,
        replay_store_binding_digest: str,
    ) -> ProposalReplayHighWater | None:
        with sqlite3.connect(self._path) as connection:
            row = connection.execute(
                "SELECT sequence, state_revision FROM replay_high_water "
                "WHERE binding_digest = ?",
                (replay_store_binding_digest,),
            ).fetchone()
        return (
            ProposalReplayHighWater(
                sequence=int(row[0]),
                state_revision=str(row[1]),
            )
            if row is not None
            else None
        )

    def advance(
        self,
        replay_store_binding_digest: str,
        *,
        expected: ProposalReplayHighWater | None,
        next_value: ProposalReplayHighWater,
    ) -> None:
        with sqlite3.connect(
            self._path,
            timeout=10.0,
            isolation_level=None,
        ) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT sequence, state_revision FROM replay_high_water "
                "WHERE binding_digest = ?",
                (replay_store_binding_digest,),
            ).fetchone()
            current = (
                ProposalReplayHighWater(
                    sequence=int(row[0]),
                    state_revision=str(row[1]),
                )
                if row is not None
                else None
            )
            if current != expected:
                connection.execute("ROLLBACK")
                raise RuntimeError("proposal_replay_high_water_conflict")
            if next_value.sequence != (
                current.sequence + 1 if current is not None else 1
            ):
                connection.execute("ROLLBACK")
                raise ValueError("proposal_replay_high_water_invalid")
            connection.execute(
                "INSERT INTO replay_high_water "
                "(binding_digest, sequence, state_revision) VALUES (?, ?, ?) "
                "ON CONFLICT(binding_digest) DO UPDATE SET "
                "sequence = excluded.sequence, "
                "state_revision = excluded.state_revision",
                (
                    replay_store_binding_digest,
                    next_value.sequence,
                    next_value.state_revision,
                ),
            )
            connection.execute("COMMIT")


class _FailOnceProposalReplayHighWaterStore:
    def __init__(self, store_id: str) -> None:
        self._delegate = InMemoryProposalReplayHighWaterStore(store_id)
        self._failed = False

    @property
    def store_id(self) -> str:
        return self._delegate.store_id

    @property
    def durable(self) -> bool:
        return False

    @property
    def durability_receipt_id(self) -> None:
        return None

    def load(self, replay_store_binding_digest: str):
        return self._delegate.load(replay_store_binding_digest)

    def advance(
        self,
        replay_store_binding_digest: str,
        *,
        expected: ProposalReplayHighWater | None,
        next_value: ProposalReplayHighWater,
    ) -> None:
        if not self._failed:
            self._failed = True
            raise OSError("simulated_high_water_outage")
        self._delegate.advance(
            replay_store_binding_digest,
            expected=expected,
            next_value=next_value,
        )


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
        "principal_provider": "github",
        "principal_public_key": principal_public_key,
        "reddog_id": "reddog:foundups-agent",
        "reddog_public_key": public_key,
        "permission_snapshot_digest": "sha256:" + "a" * 64,
        "key_epoch": "epoch-1",
        "consensus_receipt_digest": "sha256:" + "8" * 64,
        "authority_profile_source_receipt_id": "sha256:" + "9" * 64,
    }


class _PrincipalKeyResolver:
    def __init__(self, public_key: str) -> None:
        self._public_key = public_key

    def resolve(
        self,
        principal_id: str,
        principal_provider: str,
    ) -> str | None:
        if (
            principal_id == "github:mjtrout"
            and principal_provider == "github"
        ):
            return self._public_key
        return None


def _policy_authorization(
    policy: ArchitectProposalSignerPolicy,
    *,
    principal_private,
    public_key: str,
    signer_runtime_root: Path,
    security_context_digest: str,
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
        principal_provider=str(authority_profile["principal_provider"]),
        principal_public_key=str(
            authority_profile["principal_public_key"]
        ),
        reddog_id=str(authority_profile["reddog_id"]),
        reddog_public_key=str(authority_profile["reddog_public_key"]),
        key_epoch=str(authority_profile["key_epoch"]),
        authority_profile_source_receipt_id=str(
            authority_profile["authority_profile_source_receipt_id"]
        ),
        signer_instance_id=architect_proposal_signer_instance_id(
            signer_runtime_root,
            public_key,
            str(authority_profile["key_epoch"]),
        ),
        replay_store_binding_digest=(
            architect_proposal_replay_store_binding_digest(
                architect_proposal_signer_instance_id(
                    signer_runtime_root,
                    public_key,
                    str(authority_profile["key_epoch"]),
                ),
                signer_runtime_root
                / "architect_proposal_nonce_store.json",
                HIGH_WATER_STORE_ID,
            )
        ),
        security_context_digest=security_context_digest,
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
    reddog_private,
) -> tuple[SignerKeyProviderProfile]:
    reddog_public = _public_text(reddog_private)
    common = {
        "expected_key_epoch": "epoch-1",
        "permission_snapshot_digest": "sha256:" + "a" * 64,
        "ttl_seconds": 60,
    }
    return (
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
    values: tuple[str, str, str, str, int],
) -> bool:
    repo, runtime, high_water_path, nonce, expires_at = values
    store = AtomicProposalAuthenticityNonceStore(
        Path(runtime) / "proposal-nonces.json",
        allowed_root=runtime,
        repo_root=repo,
        integrity_key=INTEGRITY_KEY,
        replay_store_binding_digest="sha256:" + "b" * 64,
        high_water_store=_SqliteProposalReplayHighWaterStore(
            high_water_path
        ),
        clock=lambda: expires_at - 60,
    )
    return bool(
        store.reserve(
            nonce,
            expires_at=expires_at,
            subject="github:mjtrout",
        )
    )


def _nonce_store_kwargs(
    repo: Path,
    runtime: Path,
    *,
    high_water_store=None,
    clock=None,
) -> dict[str, object]:
    return {
        "allowed_root": runtime,
        "repo_root": repo,
        "integrity_key": INTEGRITY_KEY,
        "replay_store_binding_digest": "sha256:" + "b" * 64,
        "high_water_store": (
            high_water_store
            or _SqliteProposalReplayHighWaterStore(
                runtime.parent / "proposal-high-water.sqlite3"
            )
        ),
        "clock": clock or (lambda: NOW),
    }


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
    signer_runtime = runtime.parent / "signer-state"
    peer_policy, peer_reasons = config_supply._peer_policy(
        {1001: "github:mjtrout"},
        (),
    )
    assert not peer_reasons and peer_policy is not None
    unsigned_config = config_supply._config(
        authority_profile=profile,
        runtime_root=runtime.resolve(),
        signer_runtime_root=signer_runtime.resolve(),
        socket_path=(runtime / "reddog-signer.sock").resolve(),
        principal_signing_key_ref="op://prod/principal/private",
        principal_audit_mac_key_ref="op://prod/principal/audit",
        reddog_signing_key_ref="op://prod/reddog/private",
        reddog_audit_mac_key_ref="op://prod/reddog/audit",
        peer_policy=peer_policy,
        max_requests=2,
        timeout_s=5.0,
        max_request_bytes=16384,
        max_response_bytes=16384,
        principal_signer_agent_id="signer:principal",
        reddog_signer_agent_id="signer:reddog",
        control_loop_anchor_path=(
            signer_runtime / "signer_control_loop_anchor.json"
        ).resolve(),
        proposal_authority_policy=policy,
        proposal_policy_authorization=None,
        proposal_nonce_store_path=(
            signer_runtime / "architect_proposal_nonce_store.json"
        ).resolve(),
        proposal_replay_high_water_store_id=HIGH_WATER_STORE_ID,
        proposal_replay_high_water_durability_receipt_id=(
            HIGH_WATER_DURABILITY_RECEIPT_ID
        ),
    )
    security_context_digest = architect_proposal_security_context_digest(
        SignerSocketServiceRuntimeWiringConfig(
            repo_root=repo,
            runtime_root=runtime.resolve(),
            signer_runtime_root=signer_runtime.resolve(),
            socket_path=(runtime / "reddog-signer.sock").resolve(),
            peer_policy=peer_policy,
            provider_mode=PROVIDER_MODE_WSP71_PERMISSIONED,
            allow_test_only_key_material=False,
            permission_snapshot_fresh=True,
            max_requests=2,
            timeout_s=5.0,
            max_request_bytes=16384,
            max_response_bytes=16384,
            key_provider_profiles=tuple(
                unsigned_config["key_provider_profiles"]
            ),
            control_loop_anchor_path=(
                signer_runtime / "signer_control_loop_anchor.json"
            ).resolve(),
            proposal_authority_policy=policy,
            proposal_nonce_store_path=(
                signer_runtime
                / "architect_proposal_nonce_store.json"
            ).resolve(),
            proposal_replay_high_water_store_id=HIGH_WATER_STORE_ID,
            proposal_replay_high_water_durability_receipt_id=(
                HIGH_WATER_DURABILITY_RECEIPT_ID
            ),
        )
    )
    values: dict[str, object] = {
        "repo_root": repo,
        "runtime_root": runtime,
        "signer_runtime_root": signer_runtime,
        "authority_profile": profile,
        "output_path": runtime / "signer-service.json",
        "socket_path": runtime / "reddog-signer.sock",
        "principal_signing_key_ref": "op://prod/principal/private",
        "principal_audit_mac_key_ref": "op://prod/principal/audit",
        "reddog_signing_key_ref": "op://prod/reddog/private",
        "reddog_audit_mac_key_ref": "op://prod/reddog/audit",
        "peer_uid_to_principal": {1001: "github:mjtrout"},
        "proposal_authority_policy": policy,
        "proposal_replay_high_water_store_id": HIGH_WATER_STORE_ID,
        "proposal_replay_high_water_durability_receipt_id": (
            HIGH_WATER_DURABILITY_RECEIPT_ID
        ),
        "proposal_policy_authorization": _policy_authorization(
            policy,
            principal_private=principal_private,
            public_key=public_key,
            signer_runtime_root=signer_runtime,
            security_context_digest=security_context_digest,
            profile=profile,
        ),
        "principal_key_resolver": _PrincipalKeyResolver(
            _public_text(principal_private)
        ),
        "now_epoch": NOW,
        "max_requests": 2,
    }
    values.update(overrides)
    return values


def _runtime_proposal_config(
    *,
    repo: Path,
    runtime: Path,
    signer_runtime: Path,
    policy: ArchitectProposalSignerPolicy,
    principal_private,
    reddog_private,
) -> SignerSocketServiceRuntimeWiringConfig:
    profiles = _provider_profiles(reddog_private=reddog_private)
    provisional = SignerSocketServiceRuntimeWiringConfig(
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
        control_loop_anchor_path=(
            signer_runtime / "signer_control_loop_anchor.json"
        ),
        proposal_authority_policy=policy,
        proposal_nonce_store_path=(
            signer_runtime / "architect_proposal_nonce_store.json"
        ),
        proposal_replay_high_water_store_id=HIGH_WATER_STORE_ID,
        proposal_replay_high_water_durability_receipt_id=(
            HIGH_WATER_DURABILITY_RECEIPT_ID
        ),
    )
    security_digest = architect_proposal_security_context_digest(
        provisional
    )
    authorization = _policy_authorization(
        policy,
        principal_private=principal_private,
        public_key=_public_text(reddog_private),
        signer_runtime_root=signer_runtime,
        security_context_digest=security_digest,
    )
    return dataclasses.replace(
        provisional,
        proposal_policy_authorization=authorization,
        proposal_security_context_digest=security_digest,
    )


def test_atomic_nonce_store_survives_restart_and_rejects_replay(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    runtime = tmp_path / "signer-state"
    repo.mkdir()
    store_path = runtime / "proposal-nonces.json"
    first = AtomicProposalAuthenticityNonceStore(
        store_path,
        **_nonce_store_kwargs(repo, runtime),
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
        **_nonce_store_kwargs(repo, runtime),
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
        **_nonce_store_kwargs(repo, runtime),
    )
    second = AtomicProposalAuthenticityNonceStore(
        store_path,
        **_nonce_store_kwargs(repo, runtime),
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
            allowed_root=runtime,
            repo_root=repo,
            integrity_key=INTEGRITY_KEY,
            replay_store_binding_digest="sha256:" + "b" * 64,
            high_water_store=InMemoryProposalReplayHighWaterStore(
                HIGH_WATER_STORE_ID
            ),
        )

    store_path = runtime / "proposal-nonces.json"
    store_path.parent.mkdir()
    store_path.write_text('{"schema_version":"wrong"}', encoding="utf-8")
    store = AtomicProposalAuthenticityNonceStore(
        store_path,
        **_nonce_store_kwargs(repo, runtime),
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
        **_nonce_store_kwargs(repo, runtime),
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
        **_nonce_store_kwargs(repo, runtime),
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
        **_nonce_store_kwargs(repo, runtime, clock=lambda: now[0]),
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
    high_water_path = tmp_path / "proposal-high-water.sqlite3"
    jobs = [
        (
            str(repo),
            str(runtime),
            str(high_water_path),
            "process-race",
            NOW + 60,
        ),
        (
            str(repo),
            str(runtime),
            str(high_water_path),
            "process-race",
            NOW + 60,
        ),
    ]
    with ProcessPoolExecutor(
        max_workers=2,
        mp_context=multiprocessing.get_context("spawn"),
    ) as executor:
        results = list(executor.map(_reserve_nonce_process, jobs))
    assert sum(results) == 1
    assert not (runtime / "proposal-nonces.json.lock").exists()


def test_atomic_nonce_store_rejects_state_rollback_and_deletion(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    runtime = tmp_path / "signer-state"
    repo.mkdir()
    store_path = runtime / "proposal-nonces.json"
    high_water = InMemoryProposalReplayHighWaterStore(
        HIGH_WATER_STORE_ID
    )
    store = AtomicProposalAuthenticityNonceStore(
        store_path,
        **_nonce_store_kwargs(
            repo,
            runtime,
            high_water_store=high_water,
        ),
    )
    first = store.reserve(
        "nonce-1",
        expires_at=NOW + 60,
        subject="github:mjtrout",
    )
    assert first
    store.commit(first)
    old_state = store_path.read_bytes()

    second = store.reserve(
        "nonce-2",
        expires_at=NOW + 60,
        subject="github:mjtrout",
    )
    assert second
    store.commit(second)
    current_state = store_path.read_bytes()

    store_path.write_bytes(old_state)
    with pytest.raises(ValueError, match="rollback_detected"):
        store.reserve(
            "nonce-3",
            expires_at=NOW + 60,
            subject="github:mjtrout",
        )

    store_path.write_bytes(current_state)
    store_path.unlink()
    with pytest.raises(ValueError, match="rollback_detected"):
        store.reserve(
            "nonce-4",
            expires_at=NOW + 60,
            subject="github:mjtrout",
        )

    store_path.write_bytes(current_state)


def test_atomic_nonce_store_recovers_state_commit_before_high_water_advance(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    runtime = tmp_path / "signer-state"
    repo.mkdir()
    high_water = _FailOnceProposalReplayHighWaterStore(
        HIGH_WATER_STORE_ID
    )
    store_path = runtime / "proposal-nonces.json"
    store = AtomicProposalAuthenticityNonceStore(
        store_path,
        **_nonce_store_kwargs(
            repo,
            runtime,
            high_water_store=high_water,
        ),
    )

    with pytest.raises(OSError, match="simulated_high_water_outage"):
        store.reserve(
            "crash-window-nonce",
            expires_at=NOW + 60,
            subject="github:mjtrout",
        )

    restarted = AtomicProposalAuthenticityNonceStore(
        store_path,
        **_nonce_store_kwargs(
            repo,
            runtime,
            high_water_store=high_water,
        ),
    )
    assert (
        restarted.reserve(
            "crash-window-nonce",
            expires_at=NOW + 60,
            subject="github:mjtrout",
        )
        is None
    )
    recovered = high_water.load("sha256:" + "b" * 64)
    assert recovered is not None
    assert recovered.sequence == 1


def test_atomic_nonce_store_rechecks_expiry_at_reserve_and_commit(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    runtime = tmp_path / "signer-state"
    repo.mkdir()
    now = [NOW]
    store = AtomicProposalAuthenticityNonceStore(
        runtime / "proposal-nonces.json",
        **_nonce_store_kwargs(repo, runtime, clock=lambda: now[0]),
    )

    assert (
        store.reserve(
            "already-expired",
            expires_at=NOW,
            subject="github:mjtrout",
        )
        is None
    )
    reservation = store.reserve(
        "expires-before-commit",
        expires_at=NOW + 1,
        subject="github:mjtrout",
    )
    assert reservation
    now[0] = NOW + 1
    with pytest.raises(ValueError, match="reservation_expired"):
        store.commit(reservation)


def test_ed25519_signature_decoder_rejects_noncanonical_suffix() -> None:
    canonical = encode_ed25519_signature(b"s" * 64)
    assert decode_ed25519_signature(canonical) == b"s" * 64
    assert decode_ed25519_signature(canonical + "A") is None
    assert decode_ed25519_signature(canonical + "=") is None


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

    kwargs = _config_kwargs(
        repo,
        runtime,
        public_key,
        policy,
        principal_private,
    )
    authorization = kwargs["proposal_policy_authorization"]
    assert isinstance(
        authorization,
        ArchitectProposalPolicyAuthorization,
    )
    result = run_reddog_signer_socket_service_config_supply(**kwargs)

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
    assert result.profile_count == 1
    assert [
        item["signer_profile_id"]
        for item in config["key_provider_profiles"]
    ] == ["reddog-work-authority"]
    assert "principal/private" not in json.dumps(config, sort_keys=True)
    assert "control_loop_authority_policy" not in config
    assert (
        config["proposal_policy_authorization"][
            "proposal_policy_digest"
        ]
        == authorization.proposal_policy_digest
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
    assert (
        rehydrated.proposal_replay_high_water_store_id
        == HIGH_WATER_STORE_ID
    )
    assert hmac.compare_digest(
        architect_proposal_security_context_digest(rehydrated),
        str(rehydrated.proposal_security_context_digest),
    )
    rejected_in_memory = (
        run_reddog_signer_socket_service_runtime_bootstrap(
            repo_root=repo,
            config_path=runtime / "signer-service.json",
            resolver=_Resolver(private_key),
            serve_bounded=lambda **kwargs: pytest.fail(
                "production signer accepted volatile replay authority"
            ),
            expected_config_digest=result.config_digest,
            principal_key_resolver=_PrincipalKeyResolver(
                _public_text(principal_private)
            ),
            proposal_replay_high_water_store=(
                InMemoryProposalReplayHighWaterStore(
                    HIGH_WATER_STORE_ID
                )
            ),
        )
    )
    assert rejected_in_memory.accepted is False
    assert (
        FAIL_SIGNER_RUNTIME_PROPOSAL_NONCE_STORE_INVALID
        in rejected_in_memory.rejection_reasons
    )

    bootstrap = run_reddog_signer_socket_service_runtime_bootstrap(
        repo_root=repo,
        config_path=runtime / "signer-service.json",
        resolver=_Resolver(private_key),
        serve_bounded=lambda **kwargs: (
            IsolatedSignerSocketResidentServiceResult(
                accepted=True,
                status=SIGNER_SOCKET_RESIDENT_SERVICE_SERVED,
                rejection_reasons=(),
                socket_path=str(kwargs["socket_path"]),
                requests_handled=0,
                response_digests=(),
                socket_removed=True,
            )
        ),
        expected_config_digest=result.config_digest,
        principal_key_resolver=_PrincipalKeyResolver(
            _public_text(principal_private)
        ),
        proposal_replay_high_water_store=(
            _SqliteProposalReplayHighWaterStore(
                tmp_path / "production-high-water.sqlite3"
            )
        ),
    )
    assert bootstrap.rejection_reasons == ()
    assert bootstrap.accepted is True


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
            signer_runtime_root=(
                tmp_path / "expired" / ".." / "signer-state"
            ).resolve(),
            security_context_digest=str(
                expired_kwargs[
                    "proposal_policy_authorization"
                ].security_context_digest
            ),
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


def test_config_supply_rejects_self_asserted_principal_and_config_substitution(
    tmp_path: Path,
) -> None:
    reddog_private = _private_key()
    attacker_private = _private_key()
    trusted_private = _private_key()
    public_key = _public_text(reddog_private)
    policy = ArchitectProposalSignerPolicy(_payload(public_key))
    repo = tmp_path / "repo"
    repo.mkdir()

    self_asserted = _config_kwargs(
        repo,
        tmp_path / "self-asserted",
        public_key,
        policy,
        attacker_private,
    )
    self_asserted["principal_key_resolver"] = _PrincipalKeyResolver(
        _public_text(trusted_private)
    )
    rejected = run_reddog_signer_socket_service_config_supply(
        **self_asserted
    )
    assert rejected.accepted is False
    assert rejected.rejection_reasons == (
        FAIL_SIGNER_CONFIG_PROPOSAL_POLICY_AUTHORIZATION_INVALID,
    )

    missing_resolver = _config_kwargs(
        repo,
        tmp_path / "missing-resolver",
        public_key,
        policy,
        trusted_private,
    )
    missing_resolver.pop("principal_key_resolver")
    rejected = run_reddog_signer_socket_service_config_supply(
        **missing_resolver
    )
    assert rejected.accepted is False
    assert rejected.rejection_reasons == (
        FAIL_SIGNER_CONFIG_PROPOSAL_POLICY_AUTHORIZATION_INVALID,
    )

    for field, replacement in (
        ("max_requests", 3),
        ("reddog_signing_key_ref", "op://prod/reddog/other-private"),
        ("signer_runtime_root", tmp_path / "other-signer-state"),
    ):
        substituted = _config_kwargs(
            repo,
            tmp_path / ("substituted-" + field),
            public_key,
            policy,
            trusted_private,
        )
        substituted[field] = replacement
        result = run_reddog_signer_socket_service_config_supply(
            **substituted
        )
        assert result.accepted is False
        assert (
            FAIL_SIGNER_CONFIG_PROPOSAL_POLICY_AUTHORIZATION_INVALID
            in result.rejection_reasons
            or FAIL_SIGNER_CONFIG_PROPOSAL_NONCE_PATH_INVALID
            in result.rejection_reasons
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
            "op://prod/reddog/private": _private_key_secret(private_key),
            "op://test/reddog/audit": (
                AUDIT_KEY_PREFIX
                + base64.b64encode(b"a" * 32).decode("ascii")
            ),
            "op://prod/reddog/audit": (
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
                    "op://prod/principal/private": (
                        _private_key_secret(principal_private)
                    ),
                    "op://test/principal/audit": (
                        AUDIT_KEY_PREFIX
                        + base64.b64encode(b"p" * 32).decode("ascii")
                    ),
                    "op://prod/principal/audit": (
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
    proposal_high_water_store = InMemoryProposalReplayHighWaterStore(
        HIGH_WATER_STORE_ID
    )

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

    config = _runtime_proposal_config(
        repo=repo,
        runtime=runtime,
        signer_runtime=signer_runtime,
        policy=policy,
        principal_private=principal_private,
        reddog_private=private_key,
    )

    result = run_reddog_signer_socket_service_runtime_wiring(
        config,
        _Resolver(private_key),
        serve_bounded=serve,
        principal_key_resolver=_PrincipalKeyResolver(
            _public_text(principal_private)
        ),
        proposal_replay_high_water_store=proposal_high_water_store,
    )

    assert result.accepted is True
    assert result.no_file_io_performed is False
    assert result.no_repo_file_io_performed is True
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
            signer_runtime / "architect_proposal_nonce_store.json",
            allowed_root=signer_runtime,
            repo_root=repo,
            integrity_key=b"a" * 32,
            high_water_store=proposal_high_water_store,
            replay_store_binding_digest=(
                architect_proposal_replay_store_binding_digest(
                    architect_proposal_signer_instance_id(
                        signer_runtime,
                        public_key,
                        "epoch-1",
                    ),
                    signer_runtime
                    / "architect_proposal_nonce_store.json",
                    HIGH_WATER_STORE_ID,
                )
            ),
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


def test_runtime_consumes_policy_authorization_nonce_once(
    tmp_path: Path,
) -> None:
    reddog_private = _private_key()
    principal_private = _private_key()
    public_key = _public_text(reddog_private)
    policy = ArchitectProposalSignerPolicy(_payload(public_key))
    repo = tmp_path / "repo"
    runtime = tmp_path / "runtime"
    signer_runtime = tmp_path / "signer-state"
    repo.mkdir()
    config = _runtime_proposal_config(
        repo=repo,
        runtime=runtime,
        signer_runtime=signer_runtime,
        policy=policy,
        principal_private=principal_private,
        reddog_private=reddog_private,
    )

    def serve(**kwargs):
        return IsolatedSignerSocketResidentServiceResult(
            accepted=True,
            status=SIGNER_SOCKET_RESIDENT_SERVICE_SERVED,
            rejection_reasons=(),
            socket_path=str(kwargs["socket_path"]),
            requests_handled=0,
            response_digests=(),
            socket_removed=True,
        )

    principal_resolver = _PrincipalKeyResolver(
        _public_text(principal_private)
    )
    high_water_store = InMemoryProposalReplayHighWaterStore(
        HIGH_WATER_STORE_ID
    )
    first = run_reddog_signer_socket_service_runtime_wiring(
        config,
        _Resolver(reddog_private),
        serve_bounded=serve,
        principal_key_resolver=principal_resolver,
        proposal_replay_high_water_store=high_water_store,
    )
    second = run_reddog_signer_socket_service_runtime_wiring(
        config,
        _Resolver(reddog_private),
        serve_bounded=serve,
        principal_key_resolver=principal_resolver,
        proposal_replay_high_water_store=high_water_store,
    )

    assert first.accepted is True
    assert second.accepted is False
    assert second.rejection_reasons == (
        FAIL_SIGNER_RUNTIME_PROPOSAL_POLICY_AUTHORIZATION_INVALID,
    )
    assert second.no_file_io_performed is False
    assert second.no_repo_file_io_performed is True


def test_runtime_requires_matching_independent_high_water_authority(
    tmp_path: Path,
) -> None:
    reddog_private = _private_key()
    principal_private = _private_key()
    policy = ArchitectProposalSignerPolicy(
        _payload(_public_text(reddog_private))
    )
    repo = tmp_path / "repo"
    runtime = tmp_path / "runtime"
    signer_runtime = tmp_path / "signer-state"
    repo.mkdir()
    config = _runtime_proposal_config(
        repo=repo,
        runtime=runtime,
        signer_runtime=signer_runtime,
        policy=policy,
        principal_private=principal_private,
        reddog_private=reddog_private,
    )
    common = {
        "serve_bounded": lambda **kwargs: pytest.fail(
            "signer service reached without matching high-water authority"
        ),
        "principal_key_resolver": _PrincipalKeyResolver(
            _public_text(principal_private)
        ),
    }

    missing = run_reddog_signer_socket_service_runtime_wiring(
        config,
        _Resolver(reddog_private),
        **common,
    )
    mismatched = run_reddog_signer_socket_service_runtime_wiring(
        config,
        _Resolver(reddog_private),
        proposal_replay_high_water_store=(
            InMemoryProposalReplayHighWaterStore("wrong-authority")
        ),
        **common,
    )

    assert missing.accepted is False
    assert mismatched.accepted is False
    assert missing.rejection_reasons == (
        FAIL_SIGNER_RUNTIME_PROPOSAL_NONCE_STORE_INVALID,
    )
    assert mismatched.rejection_reasons == (
        FAIL_SIGNER_RUNTIME_PROPOSAL_NONCE_STORE_INVALID,
    )
    assert missing.no_file_io_performed is False
    assert mismatched.no_file_io_performed is False
    assert missing.no_repo_file_io_performed is True
    assert mismatched.no_repo_file_io_performed is True


def test_runtime_never_reuses_authorization_after_service_signs_then_raises(
    tmp_path: Path,
) -> None:
    reddog_private = _private_key()
    principal_private = _private_key()
    public_key = _public_text(reddog_private)
    policy = ArchitectProposalSignerPolicy(_payload(public_key))
    repo = tmp_path / "repo"
    runtime = tmp_path / "runtime"
    signer_runtime = tmp_path / "signer-state"
    repo.mkdir()
    config = _runtime_proposal_config(
        repo=repo,
        runtime=runtime,
        signer_runtime=signer_runtime,
        policy=policy,
        principal_private=principal_private,
        reddog_private=reddog_private,
    )
    high_water = InMemoryProposalReplayHighWaterStore(
        HIGH_WATER_STORE_ID
    )
    service_calls = 0
    signed = []

    def sign_then_raise(**kwargs):
        nonlocal service_calls
        service_calls += 1
        signed.append(
            kwargs["backend"].sign(
                _signing_request(policy.expected_payload),
                _peer(),
            )
        )
        raise RuntimeError("service_failed_after_signing")

    principal_resolver = _PrincipalKeyResolver(
        _public_text(principal_private)
    )
    first = run_reddog_signer_socket_service_runtime_wiring(
        config,
        _Resolver(reddog_private),
        serve_bounded=sign_then_raise,
        principal_key_resolver=principal_resolver,
        proposal_replay_high_water_store=high_water,
    )
    second = run_reddog_signer_socket_service_runtime_wiring(
        config,
        _Resolver(reddog_private),
        serve_bounded=sign_then_raise,
        principal_key_resolver=principal_resolver,
        proposal_replay_high_water_store=high_water,
    )

    assert signed and signed[0].accepted is True
    assert first.accepted is False
    assert first.no_file_io_performed is False
    assert second.accepted is False
    assert service_calls == 1
    assert second.rejection_reasons == (
        FAIL_SIGNER_RUNTIME_PROPOSAL_POLICY_AUTHORIZATION_INVALID,
    )


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
    malformed_digest = run_reddog_signer_socket_service_runtime_bootstrap(
        repo_root=repo,
        config_path=config_path,
        resolver=_Resolver(private_key),
        serve_bounded=lambda **kwargs: pytest.fail(
            "malformed digest reached signer service"
        ),
        expected_config_digest=123,  # type: ignore[arg-type]
    )
    assert malformed_digest.accepted is False
    assert malformed_digest.rejection_reasons == (
        FAIL_SIGNER_BOOTSTRAP_CONFIG_DIGEST_MISMATCH,
    )
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
    policy = ArchitectProposalSignerPolicy(_payload(public_key))
    valid = _runtime_proposal_config(
        repo=repo,
        runtime=runtime,
        signer_runtime=signer_runtime,
        policy=policy,
        principal_private=principal_private,
        reddog_private=private_key,
    )
    missing_store = dataclasses.replace(
        valid,
        proposal_nonce_store_path=None,
    )
    mismatched_key = dataclasses.replace(
        valid,
        proposal_authority_policy=ArchitectProposalSignerPolicy(
            _payload(other_key)
        ),
    )
    substituted_profile = dataclasses.replace(
        valid,
        key_provider_profiles=(
            dataclasses.replace(
                valid.key_provider_profiles[0],
                signer_profile_id="principal-identity",
            ),
        ),
    )
    excessive_ttl = dataclasses.replace(
        valid,
        proposal_authority_policy=ArchitectProposalSignerPolicy(
            _payload(public_key),
            max_ttl_seconds=301,
        ),
    )

    assert validate_signer_socket_service_runtime_config(missing_store) == (
        FAIL_SIGNER_RUNTIME_PROPOSAL_POLICY_AUTHORIZATION_INVALID,
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
