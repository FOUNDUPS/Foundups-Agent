"""Adversarial tests for signer generation high-water persistence."""

from __future__ import annotations

import hashlib
import hmac
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.reddog_atomic_signer_runtime_generation_high_water import (
    AtomicSignerRuntimeGenerationHighWaterReader,
    AtomicSignerRuntimeGenerationHighWaterStore,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_anchor import (
    DurableSignerRuntimeGenerationAnchor,
    SignerRuntimeGenerationBinding,
    SignerRuntimeGenerationHighWater,
    VerifiedSignerRuntimeGenerationHighWater,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_pending_codec import (
    decode_pending,
)
from modules.communication.moltbot_bridge.src.reddog_sqlite_monotonic_authority_store import (
    SqliteMonotonicAuthorityStore,
)
from modules.communication.moltbot_bridge.tests.reddog_signer_generation_test_support import (
    generation_witness_binding,
)


ANCHOR_ID = "reddog-signer:production"
DURABILITY_RECEIPT_ID = "sha256:" + "e" * 64


class HmacAuthenticator:
    def __init__(
        self, key: bytes = b"h" * 32, identity: str = "test-hmac:v1"
    ) -> None:
        self.key = key
        self.authenticator_id = identity

    def authenticate(self, payload: bytes) -> str:
        return "hmac-sha256:" + hmac.new(
            self.key, payload, hashlib.sha256
        ).hexdigest()

    def verify(self, payload: bytes, authentication_tag: str) -> bool:
        return hmac.compare_digest(
            self.authenticate(payload), authentication_tag
        )


class VerifierOnly:
    def __init__(
        self, key: bytes = b"h" * 32, identity: str = "test-hmac:v1"
    ) -> None:
        self.key = key
        self.authenticator_id = identity

    def verify(self, payload: bytes, authentication_tag: str) -> bool:
        expected = "hmac-sha256:" + hmac.new(
            self.key, payload, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, authentication_tag)


class HighWaterBoundary:
    def __init__(
        self, store: AtomicSignerRuntimeGenerationHighWaterStore
    ) -> None:
        self.capability = object()
        self._verified = VerifiedSignerRuntimeGenerationHighWater(
            store=store,
            store_id=store.store_id,
            durability_receipt_id=store.durability_receipt_id,
        )

    def require(
        self, value: object
    ) -> VerifiedSignerRuntimeGenerationHighWater:
        if value is not self.capability:
            raise ValueError("test_high_water_authority_unverified")
        return self._verified


class FailCommitOnceStore(AtomicSignerRuntimeGenerationHighWaterStore):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fail_commit = True

    def commit_prepared(self, anchor_id: str, transaction_id: str) -> None:
        if self.fail_commit:
            self.fail_commit = False
            raise RuntimeError("test_high_water_interrupted")
        super().commit_prepared(anchor_id, transaction_id)


class RaiseAfterCommitStore(AtomicSignerRuntimeGenerationHighWaterStore):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fail_commit = True

    def commit_prepared(self, anchor_id: str, transaction_id: str) -> None:
        super().commit_prepared(anchor_id, transaction_id)
        if self.fail_commit:
            self.fail_commit = False
            raise RuntimeError("test_high_water_post_commit_interrupted")


class RaiseAfterAnchorCommit:
    def __init__(self, store) -> None:
        self._store = store
        self.failed = False

    def load(self):
        return self._store.load()

    @property
    def path(self):
        return self._store.path

    def remove(self, *, expected_revision):
        return self._store.remove(expected_revision=expected_revision)

    def commit(self, snapshot, *, expected_revision):
        revision = self._store.commit(
            snapshot, expected_revision=expected_revision
        )
        if not self.failed:
            self.failed = True
            raise RuntimeError("test_anchor_post_commit_interrupted")
        return revision


class RaiseBeforeAnchorCommit:
    def __init__(self, store) -> None:
        self._store = store

    def load(self):
        return self._store.load()

    def commit(self, snapshot, *, expected_revision):
        del snapshot, expected_revision
        raise RuntimeError("test_anchor_pre_commit_interrupted")


@pytest.fixture()
def roots(tmp_path: Path) -> tuple[Path, Path, Path]:
    repo = tmp_path / "repo"
    runtime = tmp_path / "signer-runtime"
    authority = tmp_path / "signer-authority"
    repo.mkdir()
    runtime.mkdir()
    authority.mkdir()
    return repo, runtime, authority


def _store(
    roots: tuple[Path, Path, Path],
    *,
    authenticator: HmacAuthenticator | None = None,
    store_type=AtomicSignerRuntimeGenerationHighWaterStore,
    witness_binding=None,
):
    repo, _, authority = roots
    signing_capability = authenticator or HmacAuthenticator()
    return store_type(
        authority / "generation-high-water.json",
        allowed_root=authority,
        repo_root=repo,
        store_id="signer-high-water:production",
        durability_receipt_id=DURABILITY_RECEIPT_ID,
        signer=signing_capability,
        verifier=VerifierOnly(
            key=signing_capability.key,
            identity=signing_capability.authenticator_id,
        ),
        generation_witness_store=_witness(roots),
        generation_witness_binding=(
            witness_binding
            or _witness_binding(roots, signing_capability.authenticator_id)
        ),
    )


def _witness(roots):
    repo, _, authority = roots
    root = authority.parent / "signer-generation-witness"
    root.mkdir(exist_ok=True)
    return SqliteMonotonicAuthorityStore(
        root / "generation-witness.sqlite3",
        allowed_root=root,
        repo_root=repo,
        store_id="signer-generation-witness:production",
        durability_receipt_id="sha256:" + "d" * 64,
    )


def _witness_binding(roots, authenticator_id="test-hmac:v1"):
    _, runtime, _ = roots
    return generation_witness_binding(
        authenticator_id=authenticator_id,
        runtime_root=runtime,
        high_water_store_id="signer-high-water:production",
        high_water_durability_receipt_id=DURABILITY_RECEIPT_ID,
        witness_store_id="signer-generation-witness:production",
        witness_durability_receipt_id="sha256:" + "d" * 64,
    )


def _value(generation: int, char: str) -> SignerRuntimeGenerationHighWater:
    return SignerRuntimeGenerationHighWater(
        generation=generation,
        revision=char * 64,
    )


def test_reader_rejects_noncanonical_verifier_boundary(roots) -> None:
    repo, _, authority = roots

    with pytest.raises(ValueError, match="boundary_invalid"):
        AtomicSignerRuntimeGenerationHighWaterReader(
            authority / "generation-high-water.json",
            allowed_root=authority,
            repo_root=repo,
            store_id="signer-high-water:production",
            durability_receipt_id=DURABILITY_RECEIPT_ID,
            verifier_authority=object(),
            verifier_authority_boundary=HmacAuthenticator(),
            generation_witness_reader=_witness(roots).reader(),
            generation_witness_binding=_witness_binding(roots),
        )


def _binding(generation: int = 1) -> SignerRuntimeGenerationBinding:
    return SignerRuntimeGenerationBinding(
        generation=generation,
        manifest_id="sha256:" + str(generation) * 64,
        artifact_generation_digest="sha256:" + str(generation + 1) * 64,
        config_digest="sha256:" + str(generation + 2) * 64,
        config_raw_digest="sha256:" + str(generation + 3) * 64,
        run_packet_digest="sha256:" + str(generation + 4) * 64,
    )


def _anchor(
    roots: tuple[Path, Path, Path],
    store: AtomicSignerRuntimeGenerationHighWaterStore,
) -> DurableSignerRuntimeGenerationAnchor:
    repo, runtime, _ = roots
    boundary = HighWaterBoundary(store)
    return DurableSignerRuntimeGenerationAnchor(
        runtime / "generation-anchor.json",
        allowed_root=runtime,
        repo_root=repo,
        anchor_id=ANCHOR_ID,
        signer=HmacAuthenticator(),
        verifier=VerifierOnly(),
        high_water_authority=boundary.capability,
        high_water_authority_boundary=boundary,
    )


def test_advance_survives_restart_and_is_monotonic(roots) -> None:
    store = _store(roots)
    store.advance(
        ANCHOR_ID,
        expected=None,
        next_value=_value(1, "1"),
    )

    restarted = _store(roots)
    assert restarted.load(ANCHOR_ID) == _value(1, "1")
    with pytest.raises(RuntimeError, match="conflict"):
        restarted.advance(
            ANCHOR_ID,
            expected=None,
            next_value=_value(1, "2"),
        )
    with pytest.raises(ValueError, match="not_monotonic"):
        restarted.advance(
            ANCHOR_ID,
            expected=_value(1, "1"),
            next_value=_value(3, "3"),
        )


def test_prepare_and_abort_are_authenticated_and_restart_safe(roots) -> None:
    store = _store(roots)
    pending = store.prepare(
        ANCHOR_ID,
        expected=None,
        next_value=_value(1, "1"),
    )

    restarted = _store(roots)
    assert restarted.load(ANCHOR_ID) is None
    assert restarted.pending(ANCHOR_ID) == pending
    restarted.abort_prepared(ANCHOR_ID, pending.transaction_id)
    assert restarted.load(ANCHOR_ID) is None
    assert restarted.pending(ANCHOR_ID) is None


def test_concurrent_advance_has_exactly_one_winner(roots) -> None:
    store = _store(roots)

    def advance() -> str:
        try:
            store.advance(
                ANCHOR_ID,
                expected=None,
                next_value=_value(1, "1"),
            )
            return "accepted"
        except RuntimeError:
            return "rejected"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: advance(), range(2)))

    assert results.count("accepted") == 1
    assert results.count("rejected") == 1


def test_recomputed_revision_cannot_authenticate_tampered_state(
    roots,
) -> None:
    store = _store(roots)
    store.advance(
        ANCHOR_ID,
        expected=None,
        next_value=_value(1, "1"),
    )
    path = roots[2] / "generation-high-water.json"
    state = json.loads(path.read_text(encoding="utf-8"))
    state["entries"][ANCHOR_ID]["current"]["generation"] = 9
    body = dict(state)
    body.pop("revision")
    state["revision"] = hashlib.sha256(_canonical(body)).hexdigest()
    path.write_text(json.dumps(state, sort_keys=True), encoding="utf-8")

    with pytest.raises(
        ValueError, match="generation_high_water_authentication_invalid"
    ):
        _store(roots).load(ANCHOR_ID)


def test_recomputed_revision_cannot_forge_pending_rollback_snapshot(
    roots,
) -> None:
    store = _store(roots)
    store.prepare(
        ANCHOR_ID,
        expected=None,
        next_value=_value(1, "1"),
        previous_anchor_state_json="{}",
    )
    path = roots[2] / "generation-high-water.json"
    state = json.loads(path.read_text(encoding="utf-8"))
    state["entries"][ANCHOR_ID]["pending"][
        "previous_anchor_state_json"
    ] = '{"attacker":"selected"}'
    body = dict(state)
    body.pop("revision")
    state["revision"] = hashlib.sha256(_canonical(body)).hexdigest()
    path.write_text(json.dumps(state, sort_keys=True), encoding="utf-8")

    with pytest.raises(
        ValueError, match="generation_high_water_authentication_invalid"
    ):
        _store(roots).pending(ANCHOR_ID)


def test_legacy_pending_without_rollback_snapshot_rejects() -> None:
    with pytest.raises(
        ValueError, match="generation_high_water_pending_invalid"
    ):
        decode_pending(
            {
                "transaction_id": "sha256:" + "a" * 64,
                "expected": None,
                "next_value": {
                    "generation": 1,
                    "revision": "1" * 64,
                },
            }
        )


def test_wrong_authenticator_and_placeholder_receipt_reject(roots) -> None:
    store = _store(roots)
    store.advance(
        ANCHOR_ID,
        expected=None,
        next_value=_value(1, "1"),
    )
    with pytest.raises(
        ValueError, match="generation_high_water_authentication_invalid"
    ):
        _store(
            roots,
            authenticator=HmacAuthenticator(key=b"x" * 32),
        ).load(ANCHOR_ID)

    repo, runtime, authority = roots
    with pytest.raises(ValueError, match="durability_receipt_id_invalid"):
        AtomicSignerRuntimeGenerationHighWaterStore(
            authority / "other.json",
            allowed_root=authority,
            repo_root=repo,
            store_id="signer-high-water:production",
            durability_receipt_id="sha256:" + "0" * 64,
            signer=HmacAuthenticator(),
            verifier=VerifierOnly(),
            generation_witness_store=_witness(roots),
            generation_witness_binding=_witness_binding(roots),
        )


def test_anchor_restart_rolls_forward_exactly_one_generation(roots) -> None:
    failing = _store(roots, store_type=FailCommitOnceStore)
    anchor = _anchor(roots, failing)

    with pytest.raises(RuntimeError, match="high_water_interrupted"):
        anchor.activate(_binding(), expected_revision=None)

    recovered_store = _store(roots)
    recovered = _anchor(roots, recovered_store).recover(
        commit_guard=lambda _candidate: None
    )
    assert recovered is not None
    assert recovered_store.pending(ANCHOR_ID) is None
    assert recovered_store.load(ANCHOR_ID) == SignerRuntimeGenerationHighWater(
        generation=1,
        revision=recovered.revision,
    )
    assert recovered.generation == 1


def test_committed_witness_recovery_uses_structural_guard(roots) -> None:
    failing = _store(roots, store_type=FailCommitOnceStore)
    anchor = _anchor(roots, failing)
    with pytest.raises(RuntimeError, match="high_water_interrupted"):
        anchor.activate(_binding(), expected_revision=None)

    calls: list[str] = []
    def reject_freshness(_candidate) -> None:
        raise RuntimeError("freshness_guard_must_not_run")

    recovered = _anchor(roots, _store(roots)).recover(
        commit_guard=reject_freshness,
        committed_witness_guard=lambda _candidate: calls.append(
            "structural"
        ),
    )

    assert recovered is not None
    assert calls == ["structural"]
    assert _anchor(roots, _store(roots)).recover(
        commit_guard=lambda _candidate: None,
    ) == recovered


def test_uncommitted_witness_recovery_uses_strict_guard(roots) -> None:
    store = _store(roots)
    anchor = _anchor(roots, store)
    calls: list[str] = []
    anchor._store = RaiseAfterAnchorCommit(anchor._store)

    def reject_freshness(_candidate) -> None:
        calls.append("strict")
        raise RuntimeError("manifest_expired")

    with pytest.raises(RuntimeError, match="manifest_expired"):
        anchor.activate(
            _binding(),
            expected_revision=None,
            commit_guard=reject_freshness,
        )

    assert calls == ["strict"]
    assert anchor.path.exists() is False
    assert store.pending(ANCHOR_ID) is None
    assert store.load(ANCHOR_ID) is None
    assert store.witness_load(ANCHOR_ID) is None


def test_recovery_accepts_verified_post_high_water_commit_exception(
    roots,
) -> None:
    failing = _store(roots, store_type=FailCommitOnceStore)
    with pytest.raises(RuntimeError, match="high_water_interrupted"):
        _anchor(roots, failing).activate(
            _binding(),
            expected_revision=None,
        )

    recovered_store = _store(roots, store_type=RaiseAfterCommitStore)
    recovered = _anchor(roots, recovered_store).recover(
        commit_guard=lambda _candidate: None
    )
    assert recovered is not None
    assert recovered_store.pending(ANCHOR_ID) is None
    assert recovered_store.load(ANCHOR_ID) == SignerRuntimeGenerationHighWater(
        generation=1,
        revision=recovered.revision,
    )


def test_caller_cannot_reset_witness_namespace_after_commit(roots) -> None:
    authenticator = HmacAuthenticator()
    store = _store(roots, authenticator=authenticator)
    store.advance(ANCHOR_ID, expected=None, next_value=_value(1, "1"))
    changed = replace(
        _witness_binding(roots, authenticator.authenticator_id),
        key_epoch="attacker-selected-key-epoch",
    )

    with pytest.raises(ValueError, match="state_invalid"):
        _store(
            roots,
            authenticator=authenticator,
            witness_binding=changed,
        ).load(ANCHOR_ID)


def test_witness_domain_must_not_overlap_local_high_water(roots) -> None:
    repo, _, authority = roots
    witness = SqliteMonotonicAuthorityStore(
        authority / "generation.sqlite3",
        allowed_root=authority,
        repo_root=repo,
        store_id="signer-generation-witness:production",
        durability_receipt_id="sha256:" + "d" * 64,
    )
    with pytest.raises(ValueError, match="witness_domain_overlap"):
        AtomicSignerRuntimeGenerationHighWaterStore(
            authority / "generation-high-water.json",
            allowed_root=authority,
            repo_root=repo,
            store_id="signer-high-water:production",
            durability_receipt_id=DURABILITY_RECEIPT_ID,
            signer=HmacAuthenticator(),
            verifier=VerifierOnly(),
            generation_witness_store=witness,
            generation_witness_binding=_witness_binding(roots),
        )

def test_anchor_post_commit_exception_rolls_forward(roots) -> None:
    store = _store(roots)
    anchor = _anchor(roots, store)
    anchor._store = RaiseAfterAnchorCommit(anchor._store)

    activation = anchor.activate(_binding(), expected_revision=None)

    assert activation.generation == 1
    assert _anchor(roots, _store(roots)).load() == activation


def test_replayed_anchor_and_local_high_water_fail_external_witness(roots) -> None:
    store = _store(roots)
    anchor = _anchor(roots, store)
    first = anchor.activate(_binding(), expected_revision=None)
    anchor_bytes = anchor.path.read_bytes()
    high_water_path = roots[2] / "generation-high-water.json"
    high_water_bytes = high_water_path.read_bytes()
    anchor.activate(_binding(2), expected_revision=first.revision)

    anchor.path.write_bytes(anchor_bytes)
    high_water_path.write_bytes(high_water_bytes)

    with pytest.raises(ValueError, match="rollback_detected"):
        _anchor(roots, _store(roots)).load()


def test_anchor_pre_commit_exception_aborts_pending(roots) -> None:
    store = _store(roots)
    anchor = _anchor(roots, store)
    anchor_path = anchor.path
    anchor._store = RaiseBeforeAnchorCommit(anchor._store)

    with pytest.raises(RuntimeError, match="pre_commit_interrupted"):
        anchor.activate(_binding(), expected_revision=None)

    assert store.load(ANCHOR_ID) is None
    assert store.pending(ANCHOR_ID) is None
    assert not anchor_path.exists()


def test_high_water_post_commit_exception_is_verified_success(roots) -> None:
    store = _store(roots, store_type=RaiseAfterCommitStore)
    activation = _anchor(roots, store).activate(
        _binding(), expected_revision=None
    )

    assert activation.generation == 1
    assert _anchor(roots, _store(roots)).load() == activation


def test_store_path_is_confined_outside_repository(roots) -> None:
    repo, _, authority = roots
    with pytest.raises(ValueError, match="inside_repo"):
        AtomicSignerRuntimeGenerationHighWaterStore(
            repo / "high-water.json",
            allowed_root=repo,
            repo_root=repo,
            store_id="signer-high-water:production",
            durability_receipt_id=DURABILITY_RECEIPT_ID,
            signer=HmacAuthenticator(),
            verifier=VerifierOnly(),
            generation_witness_store=_witness(roots),
            generation_witness_binding=_witness_binding(roots),
        )
    with pytest.raises(ValueError, match="outside_runtime_root"):
        AtomicSignerRuntimeGenerationHighWaterStore(
            authority.parent / "outside.json",
            allowed_root=authority,
            repo_root=repo,
            store_id="signer-high-water:production",
            durability_receipt_id=DURABILITY_RECEIPT_ID,
            signer=HmacAuthenticator(),
            verifier=VerifierOnly(),
            generation_witness_store=_witness(roots),
            generation_witness_binding=_witness_binding(roots),
        )


def _canonical(value: dict) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
