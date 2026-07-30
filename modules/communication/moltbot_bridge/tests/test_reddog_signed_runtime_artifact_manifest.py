"""Security tests for the signed RedDog runtime-artifact manifest."""

from __future__ import annotations

import ast
import copy
import json
import pickle
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

import pytest

from modules.communication.moltbot_bridge.src.reddog_architect_fix_publication_effect_binding import (
    committed_publication_effect_binding,
)
from modules.communication.moltbot_bridge.src.reddog_architect_proposal_authenticity import (
    InMemoryProposalAuthenticityNonceStore,
)
from modules.communication.moltbot_bridge.src.reddog_authoritative_work_state_store import (
    InMemoryAuthoritativeWorkStateStore,
)
from modules.communication.moltbot_bridge.src.reddog_authority_runtime_store import (
    atomic_create_confined_mapping,
    atomic_replace_confined_mapping,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    Ed25519SignatureVerifier,
    encode_ed25519_public_key,
    encode_ed25519_signature,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signer_backend import (
    REJECT_ED25519_SIGNER_MANIFEST_NONCE_REPLAY,
    REJECT_ED25519_SIGNER_PROPOSAL_DOMAIN_ONLY,
    Ed25519SignerBackend,
)
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_protocol import (
    SignerPeerAttestation,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_authority import (
    RuntimeArtifactManifestAuthority,
    RuntimeArtifactManifestAuthorityBoundary,
    create_runtime_artifact_manifest_authority_boundary,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    REQUIRED_RUNTIME_ARTIFACTS,
    RuntimeArtifactManifestError,
    canonical_signing_input as canonical_manifest_signing_input,
    digest,
    manifest_id_for,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_io import (
    MANIFEST_DIRECTORY_NAME,
)
from modules.communication.moltbot_bridge.src import (
    reddog_runtime_artifact_manifest_io as manifest_io,
)
from modules.communication.moltbot_bridge.src.reddog_signed_runtime_artifact_manifest import (
    RuntimeArtifactManifestSigningContext,
    _unsigned_manifest,
    produce_signed_runtime_artifact_manifest,
    verify_signed_runtime_artifact_manifest,
)
from modules.communication.moltbot_bridge.src.reddog_signer_audit_attestation import (
    CONTROL_LOOP_AUDIT_ATTESTATION_PREFIX,
    RUNTIME_ARTIFACT_MANIFEST_AUDIT_ATTESTATION_PREFIX,
    canonical_signer_audit_attestation_input,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    SigningRequest,
    SigningResponse,
    public_key_fingerprint,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    InMemoryNonceStore,
    PREFIX_IDENTITY,
    PREFIX_WORKAUTH,
    PermissionSnapshot,
    canonical_signing_input,
)
from modules.communication.moltbot_bridge.tests.reddog_resident_queue_test_helpers import (
    with_architect_fix_publication,
)
from modules.infrastructure.shared_utilities.reddog_runtime_artifact_generation import (
    CANONICAL_REDDOG_RUNTIME_ARTIFACTS,
)


pytest.importorskip("cryptography")

NOW = 1_800_000_000
REPO = "FOUNDUPS/Foundups-Agent"
FOUNDUP = "paccess_001"
PRINCIPAL_ID = "github:mjtrout"
REDDOG_ID = "reddog:runtime-manifest"
VALVE = "VALVE_OPEN_WORKTREE_CREATE"
KEY_EPOCH = "epoch-runtime-manifest-1"
SNAPSHOT_DIGEST = "sha256:" + "1" * 64
CONSENSUS_DIGEST = "sha256:" + "2" * 64
SOURCE_RECEIPT_ID = "sha256:" + "3" * 64


class AuditMacBuilder:
    def build(
        self,
        request: SigningRequest,
        signature: str,
        peer: SignerPeerAttestation,
    ) -> str:
        return digest(
            {
                "nonce": request.nonce,
                "peer": peer.peer_principal_id,
                "signature": signature,
            }
        )


class DirectSignerClient:
    def __init__(
        self,
        backend: Ed25519SignerBackend,
        before_sign: Callable[[], None] | None = None,
    ) -> None:
        self.backend = backend
        self.before_sign = before_sign
        self.requests: list[SigningRequest] = []
        self.responses: list[SigningResponse] = []

    def sign(self, request: SigningRequest) -> SigningResponse:
        self.requests.append(request)
        if self.before_sign is not None:
            self.before_sign()
        response = self.backend.sign(request, _peer())
        self.responses.append(response)
        return response


class PrincipalKeyResolver:
    def __init__(self, public_key: str) -> None:
        self.public_key = public_key

    def resolve(
        self, principal_id: str, principal_provider: str
    ) -> str | None:
        if principal_id == PRINCIPAL_ID and principal_provider == "github":
            return self.public_key
        return None


class SnapshotResolver:
    def resolve(self, snapshot_digest: str) -> PermissionSnapshot | None:
        if snapshot_digest != SNAPSHOT_DIGEST:
            return None
        return PermissionSnapshot(
            evidence_digest=SNAPSHOT_DIGEST,
            expires_at=NOW + 600,
            can_write=True,
            repo_full_name=REPO,
        )


class NoRevocation:
    def is_revoked(self, **_kwargs: Any) -> bool:
        return False


class CommitFailNonceStore(InMemoryProposalAuthenticityNonceStore):
    def commit(self, reservation_id: str) -> None:
        raise RuntimeError(f"commit failed: {reservation_id}")


class FailingPrivateKey:
    def __init__(self, real_key: Any) -> None:
        self.real_key = real_key

    def public_key(self) -> Any:
        return self.real_key.public_key()

    def sign(self, _value: bytes) -> bytes:
        raise RuntimeError("sign failed")


@dataclass
class ManifestHarness:
    repo_root: Path
    runtime_root: Path
    manifest_directory: Path
    principal_private_key: Any
    reddog_private_key: Any
    principal_public_key: str
    reddog_public_key: str
    identity: dict[str, Any]
    work_authority: dict[str, Any]
    work_state: dict[str, Any]
    authority_profile: dict[str, Any]
    signer_service_config: dict[str, Any]
    work_state_store: InMemoryAuthoritativeWorkStateStore
    authority_boundary: RuntimeArtifactManifestAuthorityBoundary
    authority: RuntimeArtifactManifestAuthority
    signer: DirectSignerClient
    context: RuntimeArtifactManifestSigningContext

    def produce(
        self,
        *,
        nonce: str = "manifest-nonce-1",
        issued_at: int = NOW,
        expires_at: int = NOW + 120,
        context: RuntimeArtifactManifestSigningContext | None = None,
    ):
        return produce_signed_runtime_artifact_manifest(
            manifest_directory=self.manifest_directory,
            nonce=nonce,
            issued_at=issued_at,
            expires_at=expires_at,
            context=context or self.context,
        )

    def read_manifest(self, path: Path | None = None) -> dict[str, Any]:
        target = path or next(self.manifest_directory.glob("*.json"))
        return json.loads(target.read_text(encoding="utf-8"))

    def verify(
        self,
        value: Mapping[str, Any] | None = None,
        *,
        now_epoch: int = NOW,
    ) -> dict[str, Any]:
        return verify_signed_runtime_artifact_manifest(
            value or self.read_manifest(),
            authority=self.authority,
            authority_boundary=self.authority_boundary,
            now_epoch=now_epoch,
            signature_verifier=Ed25519SignatureVerifier(),
        )

    def fresh_context(
        self,
        *,
        before_sign: Callable[[], None] | None = None,
        nonce_store: Any | None = None,
        private_key: Any | None = None,
    ) -> RuntimeArtifactManifestSigningContext:
        backend = Ed25519SignerBackend(
            private_key=private_key or self.reddog_private_key,
            public_key=self.reddog_public_key,
            key_epoch=KEY_EPOCH,
            audit_mac_builder=AuditMacBuilder(),
            proposal_clock=lambda: float(NOW),
            runtime_artifact_manifest_authority=self.authority,
            runtime_artifact_manifest_authority_boundary=(
                self.authority_boundary
            ),
            runtime_artifact_manifest_nonce_store=(
                nonce_store
                if nonce_store is not None
                else InMemoryProposalAuthenticityNonceStore()
            ),
        )
        return RuntimeArtifactManifestSigningContext(
            signer=DirectSignerClient(backend, before_sign=before_sign),
            signature_verifier=Ed25519SignatureVerifier(),
            authority=self.authority,
            authority_boundary=self.authority_boundary,
            authority_tier="HIGH",
        )


@pytest.fixture
def harness(tmp_path: Path) -> ManifestHarness:
    return _build_harness(tmp_path)


def _build_harness(tmp_path: Path) -> ManifestHarness:
    (
        repo_root,
        runtime_root,
        principal_private,
        reddog_private,
        principal_public,
        reddog_public,
    ) = _harness_roots_and_keys(tmp_path)
    identity = _identity(principal_private, principal_public, reddog_public)
    profile = _authority_profile(reddog_public)
    state, profile, queue_id, claim_id = with_architect_fix_publication(
        _work_state(), profile
    )
    state["revision"] = _revision(state)
    effect = committed_publication_effect_binding(
        state, profile, queue_item_id=queue_id, claim_id=claim_id
    )
    assert effect is not None
    work_authority = _work_authority(
        reddog_private,
        reddog_public,
        publication_receipt_id=str(effect["publication_id"]),
        publication_binding_digest=str(effect["binding_digest"]),
    )
    signer_config = _signer_config(profile, reddog_public)
    _write_artifacts(runtime_root, state, profile, signer_config, queue_id)
    store, boundary, authority = _issue_harness_authority(
        repo_root, runtime_root, state, principal_public, identity, work_authority, queue_id
    )
    signer, context = _manifest_signing_context(
        authority,
        boundary,
        reddog_private,
        reddog_public,
    )
    return ManifestHarness(
        repo_root=repo_root,
        runtime_root=runtime_root,
        manifest_directory=runtime_root / MANIFEST_DIRECTORY_NAME,
        principal_private_key=principal_private,
        reddog_private_key=reddog_private,
        principal_public_key=principal_public,
        reddog_public_key=reddog_public,
        identity=identity,
        work_authority=work_authority,
        work_state=state,
        authority_profile=profile,
        signer_service_config=signer_config,
        work_state_store=store,
        authority_boundary=boundary,
        authority=authority,
        signer=signer,
        context=context,
    )


def _issue_harness_authority(
    repo_root: Path,
    runtime_root: Path,
    state: Mapping[str, Any],
    principal_public: str,
    identity: Mapping[str, Any],
    work_authority: Mapping[str, Any],
    queue_id: str,
) -> tuple[Any, Any, Any]:
    store = InMemoryAuthoritativeWorkStateStore(state)
    boundary = _boundary(repo_root, runtime_root, store, principal_public)
    authority = boundary.issue(
        identity=identity,
        work_authority=work_authority,
        queue_item_id=queue_id,
        now_epoch=NOW,
    )
    return store, boundary, authority


def _harness_roots_and_keys(
    tmp_path: Path,
) -> tuple[Path, Path, Any, Any, str, str]:
    repo_root = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"
    repo_root.mkdir()
    runtime_root.mkdir()
    principal_private = _private_key()
    reddog_private = _private_key()
    return (
        repo_root,
        runtime_root,
        principal_private,
        reddog_private,
        _public_text(principal_private),
        _public_text(reddog_private),
    )


def test_valid_manifest_is_created_and_verifies(
    harness: ManifestHarness,
) -> None:
    result = harness.produce()

    assert result.accepted is True
    target = Path(str(result.output_path))
    assert target == (
        harness.manifest_directory / f"{result.manifest_id[7:]}.json"
    )
    assert target.is_file() and not target.is_symlink()
    assert harness.repo_root not in target.parents
    verified = harness.verify()
    assert verified["manifest_id"] == result.manifest_id
    assert verified["revision"] == result.manifest_id[7:]
    assert verified["artifact_count"] == len(REQUIRED_RUNTIME_ARTIFACTS)


def test_preseeded_manifest_is_never_overwritten(
    harness: ManifestHarness,
) -> None:
    values = harness.authority_boundary.require(harness.authority)
    unsigned = _unsigned_manifest(
        harness.authority,
        harness.authority_boundary,
        values,
        nonce="preseeded-manifest",
        issued_at=NOW,
        expires_at=NOW + 120,
    )
    target = harness.manifest_directory / (
        f"{unsigned['manifest_id'][7:]}.json"
    )
    target.parent.mkdir()
    target.write_text('{"attacker":true}\n', encoding="utf-8")
    original = target.read_bytes()

    result = harness.produce(nonce="preseeded-manifest")

    assert result.accepted is False
    assert result.rejection_reasons == ("manifest_already_exists",)
    assert target.read_bytes() == original


def test_existing_valid_manifest_is_never_overwritten(
    harness: ManifestHarness,
) -> None:
    first = harness.produce()
    target = Path(str(first.output_path))
    original = target.read_bytes()

    second = harness.produce(context=harness.fresh_context())

    assert second.accepted is False
    assert second.rejection_reasons == ("manifest_already_exists",)
    assert target.read_bytes() == original


def test_atomic_create_concurrency_has_exactly_one_winner(
    harness: ManifestHarness,
) -> None:
    target = harness.runtime_root / "concurrent-create.json"
    barrier = threading.Barrier(12)

    def create(index: int) -> tuple[int, bool]:
        barrier.wait(timeout=5)
        try:
            atomic_create_confined_mapping(
                target,
                {"revision": f"{index:064x}", "writer": index},
                allowed_root=harness.runtime_root,
                repo_root=harness.repo_root,
            )
            return index, True
        except RuntimeError as exc:
            assert str(exc) == "revision_conflict"
            return index, False

    with ThreadPoolExecutor(max_workers=12) as pool:
        results = tuple(pool.map(create, range(12)))
    winners = [index for index, accepted in results if accepted]
    stored = json.loads(target.read_text(encoding="utf-8"))

    assert len(winners) == 1
    assert stored["writer"] == winners[0]


def test_publication_holds_generation_fence_against_writer(
    harness: ManifestHarness,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_create = manifest_io.atomic_create_confined_mapping
    started = threading.Event()
    finished = threading.Event()
    writer_threads: list[threading.Thread] = []
    changed = {**harness.authority_profile, "foundup_id": "attacker"}

    def race_writer() -> None:
        started.set()
        atomic_replace_confined_mapping(
            harness.runtime_root / "authority_profile.json",
            changed,
            allowed_root=harness.runtime_root,
            repo_root=harness.repo_root,
        )
        finished.set()

    def create_while_writer_waits(*args: Any, **kwargs: Any) -> Path:
        thread = threading.Thread(target=race_writer)
        writer_threads.append(thread)
        thread.start()
        assert started.wait(timeout=2)
        time.sleep(0.05)
        assert finished.is_set() is False
        return original_create(*args, **kwargs)

    monkeypatch.setattr(
        manifest_io,
        "atomic_create_confined_mapping",
        create_while_writer_waits,
    )
    result = harness.produce(nonce="generation-fence")
    for thread in writer_threads:
        thread.join(timeout=2)

    assert result.accepted is True
    assert finished.is_set() is True
    with pytest.raises(RuntimeArtifactManifestError, match="profile_changed"):
        harness.verify()


def test_manifest_nonce_replay_is_rejected_by_signer(
    harness: ManifestHarness,
) -> None:
    assert harness.produce(nonce="manifest-replay-1").accepted is True

    replay = harness.produce(nonce="manifest-replay-1")

    assert replay.accepted is False
    assert harness.signer.responses[-1].rejection_code == (
        REJECT_ED25519_SIGNER_MANIFEST_NONCE_REPLAY
    )


def test_sign_failure_rolls_back_nonce_reservation(
    harness: ManifestHarness,
) -> None:
    store = InMemoryProposalAuthenticityNonceStore()
    failed = harness.produce(
        nonce="rollback-after-sign-failure",
        context=harness.fresh_context(
            nonce_store=store,
            private_key=FailingPrivateKey(harness.reddog_private_key),
        ),
    )
    retried = harness.produce(
        nonce="rollback-after-sign-failure",
        context=harness.fresh_context(nonce_store=store),
    )

    assert failed.accepted is False
    assert retried.accepted is True


def test_nonce_commit_failure_rejects_publication(
    harness: ManifestHarness,
) -> None:
    result = harness.produce(
        nonce="manifest-commit-failure",
        context=harness.fresh_context(nonce_store=CommitFailNonceStore()),
    )

    assert result.accepted is False
    assert not harness.manifest_directory.exists()


def test_changed_artifact_bytes_invalidate_manifest(
    harness: ManifestHarness,
) -> None:
    result = harness.produce()
    manifest = harness.read_manifest(Path(str(result.output_path)))
    _write_json(
        harness.runtime_root / "execution_valve_env.json",
        {"valve_state": "attacker-changed"},
    )

    with pytest.raises(RuntimeArtifactManifestError, match="artifacts_changed"):
        harness.verify(manifest)


def test_recomputed_manifest_id_cannot_reuse_signature(
    harness: ManifestHarness,
) -> None:
    result = harness.produce()
    manifest = harness.read_manifest(Path(str(result.output_path)))
    manifest["nonce"] = "attacker-recomputed-id"
    manifest["manifest_id"] = manifest_id_for(manifest)
    manifest["revision"] = manifest["manifest_id"][7:]

    with pytest.raises(RuntimeArtifactManifestError, match="signature_invalid"):
        harness.verify(manifest)


def test_current_state_change_rejects_before_signing(
    harness: ManifestHarness,
) -> None:
    state = copy.deepcopy(harness.work_state)
    state["wre_queue_items"][0]["status"] = "attacker-changed"
    state["revision"] = _revision(state)
    _write_json(
        harness.runtime_root / "authoritative_work_state.json", state
    )

    result = harness.produce()

    assert result.accepted is False
    assert result.rejection_reasons == ("manifest_state_changed",)
    assert harness.signer.requests == []


def test_signer_rereads_artifacts_inside_boundary(
    harness: ManifestHarness,
) -> None:
    artifact = harness.runtime_root / "execution_valve_env.json"
    context = harness.fresh_context(
        before_sign=lambda: _write_json(
            artifact,
            {"valve_state": "changed-inside-signer-boundary"},
        )
    )

    result = harness.produce(context=context)

    assert result.accepted is False
    assert not harness.manifest_directory.exists()


def test_unverified_authority_is_rejected_and_cannot_be_copied(
    harness: ManifestHarness,
) -> None:
    with pytest.raises(ValueError, match="unverified"):
        harness.authority_boundary.require(object())
    with pytest.raises(TypeError, match="not_copyable"):
        copy.copy(harness.authority)
    with pytest.raises(TypeError, match="not_copyable"):
        copy.deepcopy(harness.authority)
    with pytest.raises(TypeError, match="not_serializable"):
        pickle.dumps(harness.authority)


def test_authority_tamper_invalidates_closure_proof(
    harness: ManifestHarness,
) -> None:
    values = object.__getattribute__(harness.authority, "_values")
    changed = dict(values)
    changed["queue_item_id"] = "queue-attacker"
    object.__setattr__(harness.authority, "_values", changed)

    with pytest.raises(ValueError, match="unverified"):
        harness.authority_boundary.require(harness.authority)
    result = harness.produce()
    assert result.accepted is False
    assert result.rejection_reasons == ("manifest_authority_unverified",)


def test_authority_module_exposes_no_capability_registry() -> None:
    import modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_authority as module

    assert not hasattr(module, "_CAPABILITY_TOKEN")
    assert not hasattr(module, "_CAPABILITY_REGISTRY")
    assert "Capability" not in module.__dict__


def test_boundary_does_not_accept_caller_work_state(
    harness: ManifestHarness,
) -> None:
    with pytest.raises(TypeError):
        harness.authority_boundary.issue(
            identity=harness.identity,
            work_authority=harness.work_authority,
            queue_item_id=harness.authority_boundary.require(
                harness.authority
            )["queue_item_id"],
            now_epoch=NOW,
            work_state={"revision": "attacker"},
        )


def test_prepared_publication_cannot_issue_authority(
    harness: ManifestHarness,
) -> None:
    state = copy.deepcopy(harness.work_state)
    state["architect_fix_publications"][0]["state"] = "STATE_PREPARED"
    state["architect_fix_publications"][0]["base_work_state_digest"] = (
        "sha256:" + "a" * 64
    )
    state["revision"] = _revision(state)
    store = InMemoryAuthoritativeWorkStateStore(state)
    boundary = _boundary(
        harness.repo_root,
        harness.runtime_root,
        store,
        harness.principal_public_key,
    )

    with pytest.raises(RuntimeError):
        boundary.issue(
            identity=harness.identity,
            work_authority=harness.work_authority,
            queue_item_id=harness.authority_boundary.require(
                harness.authority
            )["queue_item_id"],
            now_epoch=NOW,
        )


def test_attacker_self_signed_authority_is_rejected(
    harness: ManifestHarness,
) -> None:
    attacker_principal = _private_key()
    attacker_reddog = _private_key()
    identity = _identity(
        attacker_principal,
        _public_text(attacker_principal),
        _public_text(attacker_reddog),
    )
    work = _work_authority(
        attacker_reddog,
        _public_text(attacker_reddog),
        publication_receipt_id=harness.work_authority[
            "architect_fix_publication_receipt_id"
        ],
        publication_binding_digest=harness.work_authority[
            "architect_fix_publication_binding_digest"
        ],
    )

    with pytest.raises(ValueError, match="authority_rejected"):
        harness.authority_boundary.issue(
            identity=identity,
            work_authority=work,
            queue_item_id=harness.authority_boundary.require(
                harness.authority
            )["queue_item_id"],
            now_epoch=NOW,
        )


def test_attacker_self_signed_manifest_is_rejected(
    harness: ManifestHarness,
) -> None:
    result = harness.produce()
    manifest = harness.read_manifest(Path(str(result.output_path)))
    attacker = _private_key()
    attacker_public = _public_text(attacker)
    manifest["signer_public_key"] = attacker_public
    manifest["signer_key_fingerprint"] = public_key_fingerprint(
        attacker_public
    )
    manifest["manifest_id"] = manifest_id_for(manifest)
    manifest["revision"] = manifest["manifest_id"][7:]
    _self_sign_manifest(manifest, attacker)

    with pytest.raises(RuntimeArtifactManifestError, match="binding_mismatch"):
        harness.verify(manifest)


def test_manifest_audit_attestation_has_distinct_domain(
    harness: ManifestHarness,
) -> None:
    result = harness.produce()
    manifest = harness.read_manifest(Path(str(result.output_path)))
    signing_input = canonical_manifest_signing_input(manifest)
    control_input = canonical_signer_audit_attestation_input(
        signing_input=signing_input,
        signature=manifest["signature"],
        audit_mac=manifest["signer_audit_mac"],
        signer_public_key=harness.reddog_public_key,
        key_epoch=KEY_EPOCH,
        requester_principal_id=PRINCIPAL_ID,
        domain_prefix=CONTROL_LOOP_AUDIT_ATTESTATION_PREFIX,
    )

    assert control_input.startswith(CONTROL_LOOP_AUDIT_ATTESTATION_PREFIX)
    manifest_input = canonical_signer_audit_attestation_input(
        signing_input=signing_input,
        signature=manifest["signature"],
        audit_mac=manifest["signer_audit_mac"],
        signer_public_key=harness.reddog_public_key,
        key_epoch=KEY_EPOCH,
        requester_principal_id=PRINCIPAL_ID,
        domain_prefix=RUNTIME_ARTIFACT_MANIFEST_AUDIT_ATTESTATION_PREFIX,
    )
    assert manifest_input != control_input


def test_manifest_configured_signer_rejects_arbitrary_domain(
    harness: ManifestHarness,
) -> None:
    request = SigningRequest(
        signing_input="attacker.v1.payload",
        payload_digest=digest({"signing_input": "attacker.v1.payload"}),
        signer_role="attacker",
        signer_public_key=harness.reddog_public_key,
        requester_principal_id=PRINCIPAL_ID,
        nonce="attacker-nonce",
        key_epoch=KEY_EPOCH,
        requested_operation="attacker_operation",
        authority_tier="HIGH",
        consensus_receipt_digest=CONSENSUS_DIGEST,
    )

    response = harness.signer.backend.sign(request, _peer())

    assert response.accepted is False
    assert response.rejection_code == (
        REJECT_ED25519_SIGNER_PROPOSAL_DOMAIN_ONLY
    )


def test_manifest_signing_requires_boundary_and_nonce_store(
    harness: ManifestHarness,
) -> None:
    backend = Ed25519SignerBackend(
        private_key=harness.reddog_private_key,
        public_key=harness.reddog_public_key,
        key_epoch=KEY_EPOCH,
        audit_mac_builder=AuditMacBuilder(),
        proposal_clock=lambda: float(NOW),
        runtime_artifact_manifest_authority=harness.authority,
    )
    context = RuntimeArtifactManifestSigningContext(
        signer=DirectSignerClient(backend),
        signature_verifier=Ed25519SignatureVerifier(),
        authority=harness.authority,
        authority_boundary=harness.authority_boundary,
        authority_tier="HIGH",
    )

    result = harness.produce(context=context)

    assert result.accepted is False
    assert not harness.manifest_directory.exists()


@pytest.mark.parametrize(
    ("issued_at", "expires_at"),
    [(NOW + 1, NOW + 120), (NOW, NOW), (NOW, NOW + 301)],
)
def test_manifest_freshness_fails_closed(
    harness: ManifestHarness,
    issued_at: int,
    expires_at: int,
) -> None:
    result = harness.produce(
        issued_at=issued_at,
        expires_at=expires_at,
    )

    assert result.accepted is False
    assert not harness.manifest_directory.exists()


def test_manifest_directory_must_be_canonical(
    harness: ManifestHarness,
) -> None:
    result = produce_signed_runtime_artifact_manifest(
        manifest_directory=harness.runtime_root / "attacker-location",
        nonce="manifest-nonce-wrong-directory",
        issued_at=NOW,
        expires_at=NOW + 120,
        context=harness.context,
    )

    assert result.accepted is False
    assert not (harness.runtime_root / "attacker-location").exists()


def test_manifest_modules_follow_wsp62_function_bounds() -> None:
    source_root = Path(__file__).parents[1] / "src"
    names = (
        "reddog_runtime_artifact_manifest_authority.py",
        "reddog_runtime_artifact_manifest_contract.py",
        "reddog_runtime_artifact_manifest_io.py",
        "reddog_signed_runtime_artifact_manifest.py",
        "reddog_signer_audit_attestation.py",
    )
    for name in names:
        lines = (source_root / name).read_text(
            encoding="utf-8"
        ).splitlines()
        assert len(lines) < 1200
        tree = ast.parse("\n".join(lines))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert node.end_lineno is not None
                assert node.end_lineno - node.lineno + 1 <= 50


def test_modified_platform_writer_functions_follow_wsp62_bounds() -> None:
    source_root = Path(__file__).parents[1] / "src"
    expected = {
        "reddog_authority_runtime_store_posix.py": {
            "posix_atomic_replace",
            "_replace_posix_descriptor",
            "_prepare_posix_temp",
            "_install_posix_temp",
            "_verify_posix_install",
            "_cleanup_posix_replace",
            "_replace_entry",
            "_require_replace_precondition",
            "_install_absent_entry",
            "_rename_entry",
        },
        "reddog_authority_runtime_store_windows.py": {
            "windows_atomic_replace",
            "_replace_windows_handle",
            "_cleanup_windows_replace",
            "_rename_handle",
            "_require_windows_replace_precondition",
            "_windows_rename_info",
            "_set_windows_rename",
        },
    }
    for name, function_names in expected.items():
        tree = ast.parse(
            (source_root / name).read_text(encoding="utf-8")
        )
        functions = {
            node.name: node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        assert function_names <= functions.keys()
        for function_name in function_names:
            node = functions[function_name]
            assert node.end_lineno is not None
            assert node.end_lineno - node.lineno + 1 <= 50


def test_all_canonical_custom_writers_use_generation_fence() -> None:
    assert CANONICAL_REDDOG_RUNTIME_ARTIFACTS == frozenset(
        REQUIRED_RUNTIME_ARTIFACTS
    )
    source_root = Path(__file__).parents[1] / "src"
    names = (
        "reddog_authority_profile_seed_supply.py",
        "reddog_authority_profile_source_artifact_supply.py",
        "reddog_execution_valve_environment_supply.py",
        "reddog_github_principal_permission_snapshot_supply.py",
        "reddog_authority_runtime_resolver_artifact_supply.py",
        "reddog_signer_socket_service_run_packet_supply.py",
    )
    for name in names:
        source = (source_root / name).read_text(encoding="utf-8")
        assert "reddog_runtime_artifact_generation_lock" in source


def _boundary(
    repo_root: Path,
    runtime_root: Path,
    store: InMemoryAuthoritativeWorkStateStore,
    principal_public_key: str,
) -> RuntimeArtifactManifestAuthorityBoundary:
    return create_runtime_artifact_manifest_authority_boundary(
        repo_root=repo_root,
        runtime_root=runtime_root,
        work_state_store=store,
        signature_verifier=Ed25519SignatureVerifier(),
        principal_key_resolver=PrincipalKeyResolver(principal_public_key),
        nonce_store=InMemoryNonceStore(),
        snapshot_resolver=SnapshotResolver(),
        revocation_oracle=NoRevocation(),
        required_valve_state=VALVE,
    )


def _manifest_signing_context(
    authority: RuntimeArtifactManifestAuthority,
    boundary: RuntimeArtifactManifestAuthorityBoundary,
    reddog_private: Any,
    reddog_public: str,
) -> tuple[DirectSignerClient, RuntimeArtifactManifestSigningContext]:
    backend = Ed25519SignerBackend(
        private_key=reddog_private,
        public_key=reddog_public,
        key_epoch=KEY_EPOCH,
        audit_mac_builder=AuditMacBuilder(),
        proposal_clock=lambda: float(NOW),
        runtime_artifact_manifest_authority=authority,
        runtime_artifact_manifest_authority_boundary=boundary,
        runtime_artifact_manifest_nonce_store=(
            InMemoryProposalAuthenticityNonceStore()
        ),
    )
    signer = DirectSignerClient(backend)
    context = RuntimeArtifactManifestSigningContext(
        signer=signer,
        signature_verifier=Ed25519SignatureVerifier(),
        authority=authority,
        authority_boundary=boundary,
        authority_tier="HIGH",
    )
    return signer, context


def _identity(
    principal_private_key: Any,
    principal_public_key: str,
    reddog_public_key: str,
) -> dict[str, Any]:
    value = {
        "principal_id": PRINCIPAL_ID,
        "principal_provider": "github",
        "principal_public_key": principal_public_key,
        "principal_key_fingerprint": public_key_fingerprint(
            principal_public_key
        ),
        "reddog_id": REDDOG_ID,
        "reddog_public_key": reddog_public_key,
        "reddog_key_fingerprint": public_key_fingerprint(reddog_public_key),
        "repo_scope": [REPO],
        "foundup_scope": [FOUNDUP],
        "issued_at": NOW - 60,
        "expires_at": NOW + 3600,
    }
    value["signature"] = _sign(
        principal_private_key,
        canonical_signing_input(value, PREFIX_IDENTITY),
    )
    return value


def _work_authority(
    reddog_private_key: Any,
    reddog_public_key: str,
    *,
    publication_receipt_id: str,
    publication_binding_digest: str,
) -> dict[str, Any]:
    value = {
        "work_order_id": "work-order-runtime-manifest-1",
        "work_order_digest": "sha256:" + "6" * 64,
        "base_ref": "main",
        "principal_id": PRINCIPAL_ID,
        "reddog_id": REDDOG_ID,
        "repo_full_name": REPO,
        "foundup_id": FOUNDUP,
        "allowed_paths": [f"modules/foundups/{FOUNDUP}/**"],
        "denied_paths": [],
        "requested_operation": "create_foundup",
        "permission_snapshot_digest": SNAPSHOT_DIGEST,
        "queue_consumer_receipt_digest": "sha256:" + "7" * 64,
        "wsp15_allocation_receipt_id": "sha256:" + "8" * 64,
        "wsp15_allocation_digest": "sha256:" + "9" * 64,
        "wsp15_priority": "P0",
        "wsp15_mps_total": 20,
        "wsp15_reasoning_tier": "ULTRA",
        "nonce": "work-authority-nonce-1",
        "issued_at": NOW - 30,
        "expires_at": NOW + 300,
        "valve_state_required": VALVE,
        "key_epoch": KEY_EPOCH,
        "signer_public_key": reddog_public_key,
        "consensus_receipt_digest": CONSENSUS_DIGEST,
        "architect_fix_publication_receipt_id": publication_receipt_id,
        "architect_fix_publication_binding_digest": (
            publication_binding_digest
        ),
    }
    value["signature"] = _sign(
        reddog_private_key,
        canonical_signing_input(value, PREFIX_WORKAUTH),
    )
    return value


def _authority_profile(reddog_public_key: str) -> dict[str, Any]:
    return {
        "principal_id": PRINCIPAL_ID,
        "reddog_id": REDDOG_ID,
        "reddog_public_key": reddog_public_key,
        "key_epoch": KEY_EPOCH,
        "consensus_receipt_digest": CONSENSUS_DIGEST,
        "work_order_id": "work-order-runtime-manifest-1",
        "repo_full_name": REPO,
        "foundup_id": FOUNDUP,
        "requested_operation": "create_foundup",
        "permission_snapshot_digest": SNAPSHOT_DIGEST,
        "valve_state_required": VALVE,
        "allowed_paths": [f"modules/foundups/{FOUNDUP}/**"],
        "denied_paths": [],
        "authority_profile_source_receipt_id": SOURCE_RECEIPT_ID,
        "queue_consumer_receipt_digest": "sha256:" + "7" * 64,
        "wsp15_allocation_receipt_id": "sha256:" + "8" * 64,
        "wsp15_allocation_digest": "sha256:" + "9" * 64,
        "wsp15_priority": "P0",
        "wsp15_mps_total": 20,
        "wsp15_reasoning_tier": "ULTRA",
    }


def _signer_config(
    authority_profile: Mapping[str, Any],
    reddog_public_key: str,
) -> dict[str, Any]:
    return {
        "service_id": "reddog-isolated-signer-1",
        "control_loop_authority_policy": {
            "issuer_principal_id": PRINCIPAL_ID,
            "signer_public_key": reddog_public_key,
            "key_epoch": KEY_EPOCH,
            "consensus_receipt_digest": CONSENSUS_DIGEST,
            "authority_profile_digest": digest(authority_profile),
            "authority_profile_source_receipt_id": SOURCE_RECEIPT_ID,
        },
    }


def _work_state() -> dict[str, Any]:
    value = {
        "schema_version": "reddog_authoritative_work_state.v1",
        "worker_claims": [
            {
                "claim_id": "sha256:" + "b" * 64,
                "worker_id": "reddog-worker-1",
            }
        ],
        "wre_queue_items": [
            {
                "queue_item_id": "sha256:" + "c" * 64,
                "claim_id": "sha256:" + "b" * 64,
                "status": "AUTHORIZED",
                "work_order_id": "work-order-runtime-manifest-1",
                "evidence_refs": [],
            }
        ],
    }
    value["revision"] = _revision(value)
    return value


def _write_artifacts(
    runtime_root: Path,
    work_state: Mapping[str, Any],
    profile: Mapping[str, Any],
    signer_config: Mapping[str, Any],
    queue_item_id: str,
) -> None:
    values = {
        "authoritative_work_state.json": work_state,
        "authority_profile.json": profile,
        "execution_valve_env.json": {
            "valve_state": VALVE,
            "queue_item_id": queue_item_id,
        },
        "permission_snapshots.json": {
            "snapshots": [
                {
                    "evidence_digest": SNAPSHOT_DIGEST,
                    "expires_at": NOW + 600,
                }
            ]
        },
        "principal_authority_records.json": {
            "principal_id": PRINCIPAL_ID,
            "reddog_id": REDDOG_ID,
        },
        "signer_service_config.json": signer_config,
        "signer_service_run_packet.json": {
            "packet_id": "signer-run-packet-1",
            "key_epoch": KEY_EPOCH,
        },
    }
    for filename in REQUIRED_RUNTIME_ARTIFACTS:
        _write_json(runtime_root / filename, values[filename])


def _revision(value: Mapping[str, Any]) -> str:
    body = copy.deepcopy(dict(value))
    body.pop("revision", None)
    return digest(body)[7:]


def _private_key():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
    )

    return Ed25519PrivateKey.generate()


def _public_text(private_key: Any) -> str:
    from cryptography.hazmat.primitives import serialization

    raw = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return encode_ed25519_public_key(raw)


def _sign(private_key: Any, signing_input: str) -> str:
    return encode_ed25519_signature(
        private_key.sign(signing_input.encode("utf-8"))
    )


def _self_sign_manifest(manifest: dict[str, Any], private_key: Any) -> None:
    signing_input = canonical_manifest_signing_input(manifest)
    signature = _sign(private_key, signing_input)
    audit_mac = digest({"attacker": True, "signature": signature})
    manifest["signature"] = signature
    manifest["signer_audit_mac"] = audit_mac
    manifest["signer_audit_attestation_signature"] = _sign(
        private_key,
        canonical_signer_audit_attestation_input(
            signing_input=signing_input,
            signature=signature,
            audit_mac=audit_mac,
            signer_public_key=str(manifest["signer_public_key"]),
            key_epoch=str(manifest["key_epoch"]),
            requester_principal_id=str(manifest["issuer_principal_id"]),
            domain_prefix=(
                RUNTIME_ARTIFACT_MANIFEST_AUDIT_ATTESTATION_PREFIX
            ),
        ),
    )


def _peer() -> SignerPeerAttestation:
    return SignerPeerAttestation(
        peer_principal_id=PRINCIPAL_ID,
        transport="unix_socket",
        credential_source="kernel_peer_credential",
        boundary_attested=True,
    )


def _write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
