"""Adversarial tests for signer generation high-water persistence."""

from __future__ import annotations

import hashlib
import hmac
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.reddog_atomic_signer_runtime_generation_high_water import (
    AtomicSignerRuntimeGenerationHighWaterStore,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_anchor import (
    DurableSignerRuntimeGenerationAnchor,
    SignerRuntimeGenerationBinding,
    SignerRuntimeGenerationHighWater,
    VerifiedSignerRuntimeGenerationHighWater,
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


class HighWaterBoundary:
    def __init__(
        self, store: AtomicSignerRuntimeGenerationHighWaterStore
    ) -> None:
        self.capability = object()
        self._verified = VerifiedSignerRuntimeGenerationHighWater(
            store=store,
            store_id=store.store_id,
            durability_receipt_id=store.durability_receipt_id,
            rollback_domain_root=store.rollback_domain_root,
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
        verifier=signing_capability,
    )


def _value(generation: int, char: str) -> SignerRuntimeGenerationHighWater:
    return SignerRuntimeGenerationHighWater(
        generation=generation,
        revision=char * 64,
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
        verifier=HmacAuthenticator(),
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
            verifier=HmacAuthenticator(),
        )


def test_anchor_restart_rolls_forward_exactly_one_generation(roots) -> None:
    failing = _store(roots, store_type=FailCommitOnceStore)
    anchor = _anchor(roots, failing)

    with pytest.raises(RuntimeError, match="high_water_interrupted"):
        anchor.activate(_binding(), expected_revision=None)

    recovered_store = _store(roots)
    recovered = _anchor(roots, recovered_store).recover()
    assert recovered is not None
    assert recovered.generation == 1
    assert recovered_store.load(ANCHOR_ID) == SignerRuntimeGenerationHighWater(
        generation=1,
        revision=recovered.revision,
    )


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
            verifier=HmacAuthenticator(),
        )
    with pytest.raises(ValueError, match="outside_runtime_root"):
        AtomicSignerRuntimeGenerationHighWaterStore(
            authority.parent / "outside.json",
            allowed_root=authority,
            repo_root=repo,
            store_id="signer-high-water:production",
            durability_receipt_id=DURABILITY_RECEIPT_ID,
            signer=HmacAuthenticator(),
            verifier=HmacAuthenticator(),
        )


def _canonical(value: dict) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
