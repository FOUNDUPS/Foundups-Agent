"""Adversarial tests for the durable signer runtime generation anchor."""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_anchor import (
    DurableSignerRuntimeGenerationAnchor,
    SignerRuntimeGenerationActivation,
    SignerRuntimeGenerationBinding,
    VerifiedSignerRuntimeGenerationHighWater,
)
from modules.communication.moltbot_bridge.tests.reddog_signer_generation_anchor_test_support import (
    DurableHighWaterStore,
    FailingHighWaterStore,
    LegacyHighWaterStore,
    NoOpHighWaterStore,
)

class HmacAuthenticator:
    def __init__(self, key: bytes = b"k" * 32, identity: str = "test-hmac:v1") -> None:
        self.key = key
        self.authenticator_id = identity

    def authenticate(self, payload: bytes) -> str:
        return "hmac-sha256:" + hmac.new(
            self.key, payload, hashlib.sha256
        ).hexdigest()

    def verify(self, payload: bytes, authentication_tag: str) -> bool:
        return hmac.compare_digest(
            self.authenticate(payload),
            authentication_tag,
        )

class RejectingVerifier:
    authenticator_id = "test-hmac:v1"
    def verify(self, payload: bytes, authentication_tag: str) -> bool:
        del payload, authentication_tag
        return False


class SignerOnly:
    authenticator_id = "test-hmac:v1"
    def authenticate(self, payload: bytes) -> str:
        return HmacAuthenticator().authenticate(payload)


class VerifierOnly:
    authenticator_id = "test-hmac:v1"
    def verify(self, payload: bytes, authentication_tag: str) -> bool:
        return HmacAuthenticator().verify(payload, authentication_tag)


class HighWaterAuthorityBoundary:
    def __init__(
        self, store: DurableHighWaterStore, rollback_domain_root: Path
    ) -> None:
        rollback_domain_root.mkdir(exist_ok=True)
        store.rollback_domain_root = rollback_domain_root
        store.witness_rollback_domain_root = (
            rollback_domain_root.parent / "generation-witness-authority"
        )
        store.witness_rollback_domain_root.mkdir(exist_ok=True)
        store.store_id = "test-high-water:durable"
        store.durability_receipt_id = "sha256:" + "e" * 64
        self.capability = object()
        self.verified = VerifiedSignerRuntimeGenerationHighWater(
            store=store,
            store_id=store.store_id,
            durability_receipt_id=store.durability_receipt_id,
        )

    def require(self, value: object) -> VerifiedSignerRuntimeGenerationHighWater:
        if value is not self.capability:
            raise ValueError("test_high_water_authority_unverified")
        return self.verified


def _sha(char: str) -> str:
    return "sha256:" + char * 64


def _binding(generation: int = 1, char: str = "1") -> SignerRuntimeGenerationBinding:
    values = [str((int(char) + offset) % 10) for offset in range(5)]
    return SignerRuntimeGenerationBinding(
        generation=generation,
        manifest_id=_sha(values[0]),
        artifact_generation_digest=_sha(values[1]),
        config_digest=_sha(values[2]),
        config_raw_digest=_sha(values[3]),
        run_packet_digest=_sha(values[4]),
    )


@pytest.fixture()
def roots(tmp_path: Path) -> tuple[Path, Path, Path]:
    repo = tmp_path / "repo"
    runtime = tmp_path / "runtime"
    repo.mkdir()
    runtime.mkdir()
    return repo, runtime, runtime / "signer-generation-anchor.json"


def _anchor(
    roots: tuple[Path, Path, Path],
    *,
    authenticator: HmacAuthenticator | None = None,
    verifier: object | None = None,
    high_water_store: DurableHighWaterStore | None = None,
    path: Path | None = None,
    anchor_id: str = "reddog-signer:production",
) -> DurableSignerRuntimeGenerationAnchor:
    repo, runtime, default_path = roots
    signing_capability = authenticator or HmacAuthenticator()
    boundary = HighWaterAuthorityBoundary(
        high_water_store or DurableHighWaterStore(),
        runtime.parent / "high-water-authority",
    )
    return DurableSignerRuntimeGenerationAnchor(
        path or default_path,
        allowed_root=runtime,
        repo_root=repo,
        anchor_id=anchor_id,
        signer=signing_capability,
        verifier=verifier or VerifierOnly(),
        high_water_authority=boundary.capability,
        high_water_authority_boundary=boundary,
    )


def _bytes(path: Path) -> bytes:
    return path.read_bytes() if path.exists() else b""


def test_round_trip_is_immutable_and_monotonic(roots) -> None:
    anchor = _anchor(roots)
    first = anchor.activate(_binding(), expected_revision=None)
    second = anchor.activate(
        _binding(2, "6"),
        expected_revision=first.revision,
    )

    assert isinstance(first, SignerRuntimeGenerationActivation)
    assert second.generation == 2
    assert second.previous_revision == first.revision
    assert anchor.load() == second
    with pytest.raises(FrozenInstanceError):
        second.generation = 3  # type: ignore[misc]


@pytest.mark.parametrize(
    "field,value",
    [
        ("generation", 0),
        ("generation", True),
        ("manifest_id", "wrong"),
        ("artifact_generation_digest", _sha("A")),
        ("config_digest", "sha256:" + "1" * 63),
        ("config_raw_digest", ""),
        ("run_packet_digest", _sha("z")),
    ],
)
def test_invalid_generation_or_digest_rejects_without_mutation(
    roots, field: str, value: object
) -> None:
    anchor = _anchor(roots)
    before = _bytes(anchor.path)
    candidate = replace(_binding(), **{field: value})

    with pytest.raises((TypeError, ValueError)):
        anchor.activate(candidate, expected_revision=None)

    assert _bytes(anchor.path) == before


def test_stale_expected_revision_rejects_without_mutation(roots) -> None:
    anchor = _anchor(roots)
    first = anchor.activate(_binding(), expected_revision=None)
    before = _bytes(anchor.path)

    with pytest.raises(RuntimeError, match="revision_conflict"):
        anchor.activate(_binding(2, "6"), expected_revision="0" * 64)

    assert anchor.load() == first
    assert _bytes(anchor.path) == before


@pytest.mark.parametrize("generation", [1, 0, 3])
def test_replay_rollback_and_generation_gap_reject(
    roots, generation: int
) -> None:
    anchor = _anchor(roots)
    first = anchor.activate(_binding(), expected_revision=None)
    before = _bytes(anchor.path)

    with pytest.raises(ValueError, match="generation_(?:invalid|not_monotonic)"):
        anchor.activate(
            replace(_binding(generation, "6"), generation=generation),
            expected_revision=first.revision,
        )

    assert _bytes(anchor.path) == before


@pytest.mark.parametrize("field", ["manifest_id", "artifact_generation_digest"])
def test_current_manifest_or_artifact_generation_cannot_be_replayed(
    roots, field: str
) -> None:
    anchor = _anchor(roots)
    first = anchor.activate(_binding(), expected_revision=None)
    before = _bytes(anchor.path)
    second = _binding(2, "6")
    second = replace(second, **{field: getattr(first, field)})

    with pytest.raises(ValueError, match="generation_replay"):
        anchor.activate(second, expected_revision=first.revision)

    assert _bytes(anchor.path) == before


def test_tampered_state_rejects_even_with_recomputed_self_hash(roots) -> None:
    anchor = _anchor(roots)
    anchor.activate(_binding(), expected_revision=None)
    payload = json.loads(anchor.path.read_text(encoding="utf-8"))
    payload["run_packet_digest"] = _sha("9")
    unsigned = dict(payload)
    unsigned.pop("revision")
    payload["revision"] = hashlib.sha256(
        json.dumps(
            unsigned,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()
    anchor.path.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    tampered = _bytes(anchor.path)

    with pytest.raises(ValueError, match="authentication_invalid"):
        anchor.load()

    assert _bytes(anchor.path) == tampered


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: {**value, "unexpected": True},
        lambda value: {**value, "schema_version": "wrong.v1"},
        lambda value: {**value, "anchor_id": "other"},
        lambda value: {**value, "authenticator_id": "other"},
        lambda value: {**value, "high_water_store_id": "other"},
        lambda value: {
            **value,
            "high_water_durability_receipt_id": _sha("f"),
        },
    ],
)
def test_state_shape_and_identity_tampering_reject_without_rewrite(
    roots, mutation
) -> None:
    anchor = _anchor(roots)
    anchor.activate(_binding(), expected_revision=None)
    payload = mutation(json.loads(anchor.path.read_text(encoding="utf-8")))
    anchor.path.write_text(json.dumps(payload), encoding="utf-8")
    tampered = _bytes(anchor.path)

    with pytest.raises(ValueError):
        anchor.load()

    assert _bytes(anchor.path) == tampered


def test_rejected_authenticator_never_creates_state(roots) -> None:
    anchor = _anchor(roots, verifier=RejectingVerifier())

    with pytest.raises(ValueError, match="authentication_rejected"):
        anchor.activate(_binding(), expected_revision=None)

    assert not anchor.path.exists()


def test_signer_and_verifier_are_separate_capabilities(roots) -> None:
    repo, runtime, path = roots
    boundary = HighWaterAuthorityBoundary(
        DurableHighWaterStore(), runtime.parent / "high-water-authority"
    )
    anchor = DurableSignerRuntimeGenerationAnchor(
        path,
        allowed_root=runtime,
        repo_root=repo,
        anchor_id="reddog-signer:production",
        signer=SignerOnly(),
        verifier=VerifierOnly(),
        high_water_authority=boundary.capability,
        high_water_authority_boundary=boundary,
    )

    assert anchor.activate(_binding(), expected_revision=None).generation == 1
    assert not hasattr(anchor._verifier, "authenticate")


def test_mismatched_signer_and_verifier_reject_before_write(roots) -> None:
    repo, runtime, path = roots
    boundary = HighWaterAuthorityBoundary(
        DurableHighWaterStore(), runtime.parent / "high-water-authority"
    )
    verifier = VerifierOnly()
    verifier.authenticator_id = "other-hmac:v1"

    with pytest.raises(ValueError, match="signer_verifier_mismatch"):
        DurableSignerRuntimeGenerationAnchor(
            path,
            allowed_root=runtime,
            repo_root=repo,
            anchor_id="reddog-signer:production",
            signer=SignerOnly(),
            verifier=verifier,
            high_water_authority=boundary.capability,
            high_water_authority_boundary=boundary,
        )
    assert not path.exists()


def test_verifier_cannot_expose_signing_capability(roots) -> None:
    repo, runtime, path = roots
    boundary = HighWaterAuthorityBoundary(
        DurableHighWaterStore(), runtime.parent / "high-water-authority"
    )
    combined = HmacAuthenticator()

    with pytest.raises(ValueError, match="verifier_invalid"):
        DurableSignerRuntimeGenerationAnchor(
            path,
            allowed_root=runtime,
            repo_root=repo,
            anchor_id="reddog-signer:production",
            signer=combined,
            verifier=combined,
            high_water_authority=boundary.capability,
            high_water_authority_boundary=boundary,
        )

    assert not path.exists()


def test_high_water_rollback_domain_must_be_disjoint(roots) -> None:
    repo, runtime, path = roots
    boundary = HighWaterAuthorityBoundary(DurableHighWaterStore(), runtime)

    with pytest.raises(ValueError, match="high_water_domain_overlap"):
        DurableSignerRuntimeGenerationAnchor(
            path,
            allowed_root=runtime,
            repo_root=repo,
            anchor_id="reddog-signer:production",
            signer=SignerOnly(),
            verifier=VerifierOnly(),
            high_water_authority=boundary.capability,
            high_water_authority_boundary=boundary,
        )

    assert not path.exists()


def test_witness_rollback_domain_must_be_disjoint(roots) -> None:
    repo, runtime, path = roots
    store = DurableHighWaterStore()
    boundary = HighWaterAuthorityBoundary(
        store, runtime.parent / "high-water-authority"
    )
    store.witness_rollback_domain_root = runtime

    with pytest.raises(ValueError, match="high_water_domain_overlap"):
        DurableSignerRuntimeGenerationAnchor(
            path,
            allowed_root=runtime,
            repo_root=repo,
            anchor_id="reddog-signer:production",
            signer=SignerOnly(),
            verifier=VerifierOnly(),
            high_water_authority=boundary.capability,
            high_water_authority_boundary=boundary,
        )
    assert not path.exists()


@pytest.mark.parametrize(
    ("field_name", "field_value"),
    [
        ("store_id", "other-high-water:durable"),
        ("durability_receipt_id", "sha256:" + "f" * 64),
    ],
)
def test_high_water_authority_metadata_must_match_store(
    roots, field_name: str, field_value: str
) -> None:
    repo, runtime, path = roots
    boundary = HighWaterAuthorityBoundary(
        DurableHighWaterStore(), runtime.parent / "high-water-authority"
    )
    object.__setattr__(
        boundary.verified,
        field_name,
        field_value,
    )

    with pytest.raises(ValueError, match="authority_mismatch"):
        DurableSignerRuntimeGenerationAnchor(
            path,
            allowed_root=runtime,
            repo_root=repo,
            anchor_id="reddog-signer:production",
            signer=SignerOnly(),
            verifier=VerifierOnly(),
            high_water_authority=boundary.capability,
            high_water_authority_boundary=boundary,
        )

    assert not path.exists()


def test_out_of_root_and_repository_paths_reject(roots, tmp_path: Path) -> None:
    repo, runtime, _ = roots
    authenticator = HmacAuthenticator()
    for path in (repo / "anchor.json", tmp_path / "outside" / "anchor.json"):
        boundary = HighWaterAuthorityBoundary(
            DurableHighWaterStore(), tmp_path / "high-water-authority"
        )
        with pytest.raises(ValueError):
            DurableSignerRuntimeGenerationAnchor(
                path,
                allowed_root=runtime,
                repo_root=repo,
                anchor_id="reddog-signer:production",
                signer=authenticator,
                verifier=VerifierOnly(),
                high_water_authority=boundary.capability,
                high_water_authority_boundary=boundary,
            )


def test_symlink_component_rejects(roots, tmp_path: Path) -> None:
    repo, runtime, _ = roots
    destination = tmp_path / "destination"
    destination.mkdir()
    linked = runtime / "linked"
    try:
        linked.symlink_to(destination, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation unavailable")

    with pytest.raises(ValueError, match="link"):
        _anchor(roots, path=linked / "anchor.json")


def test_two_writers_cannot_both_activate_same_generation(roots) -> None:
    barrier = threading.Barrier(2)
    authenticator = HmacAuthenticator()
    high_water = DurableHighWaterStore()
    first = _anchor(
        roots,
        authenticator=authenticator,
        high_water_store=high_water,
    )
    second = _anchor(
        roots,
        authenticator=authenticator,
        high_water_store=high_water,
    )

    def activate(anchor):
        try:
            barrier.wait(timeout=5)
            return anchor.activate(_binding(), expected_revision=None)
        except Exception as exc:
            return exc

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(activate, (first, second)))

    successes = [item for item in results if isinstance(item, SignerRuntimeGenerationActivation)]
    failures = [item for item in results if isinstance(item, Exception)]
    assert len(successes) == 1
    assert len(failures) == 1
    assert isinstance(failures[0], RuntimeError)
    assert first.load() == successes[0]


def test_older_valid_authenticated_state_is_rejected_after_restart(roots) -> None:
    high_water = DurableHighWaterStore()
    anchor = _anchor(roots, high_water_store=high_water)
    first = anchor.activate(_binding(), expected_revision=None)
    first_bytes = _bytes(anchor.path)
    anchor.activate(_binding(2, "6"), expected_revision=first.revision)
    anchor.path.write_bytes(first_bytes)
    restored_old_state = _bytes(anchor.path)
    restarted = _anchor(roots, high_water_store=high_water)

    with pytest.raises(ValueError, match="rollback_detected"):
        restarted.load()

    assert _bytes(anchor.path) == restored_old_state


def test_deleted_high_water_never_reauthorizes_old_generation_one(roots) -> None:
    high_water = DurableHighWaterStore()
    anchor = _anchor(roots, high_water_store=high_water)
    first = anchor.activate(_binding(), expected_revision=None)
    first_bytes = _bytes(anchor.path)
    anchor.activate(_binding(2, "6"), expected_revision=first.revision)
    high_water._values.clear()
    anchor.path.write_bytes(first_bytes)

    with pytest.raises(ValueError, match="rollback_detected"):
        _anchor(roots, high_water_store=high_water).load()


def test_high_water_prepare_failure_leaves_no_anchor_state(
    roots,
) -> None:
    high_water = FailingHighWaterStore()
    anchor = _anchor(roots, high_water_store=high_water)

    with pytest.raises(RuntimeError, match="high_water_unavailable"):
        anchor.activate(_binding(), expected_revision=None)

    assert not anchor.path.exists()
    assert _anchor(roots, high_water_store=high_water).load() is None


def test_noop_high_water_cannot_return_false_success(roots) -> None:
    high_water = NoOpHighWaterStore()
    anchor = _anchor(roots, high_water_store=high_water)

    with pytest.raises(RuntimeError, match="high_water_unverified"):
        anchor.activate(_binding(), expected_revision=None)
    with pytest.raises(RuntimeError, match="high_water_unverified"):
        _anchor(roots, high_water_store=high_water).recover(
            commit_guard=lambda _candidate: None
        )


def test_nontransactional_high_water_rejects_before_write(roots) -> None:
    repo, runtime, path = roots
    boundary = HighWaterAuthorityBoundary(
        LegacyHighWaterStore(),
        runtime.parent / "legacy-high-water",
    )

    with pytest.raises(ValueError, match="transactional_high_water_required"):
        DurableSignerRuntimeGenerationAnchor(
            path,
            allowed_root=runtime,
            repo_root=repo,
            anchor_id="reddog-signer:production",
            signer=SignerOnly(),
            verifier=VerifierOnly(),
            high_water_authority=boundary.capability,
            high_water_authority_boundary=boundary,
        )

    assert not path.exists()


def test_forged_high_water_authority_rejects(roots) -> None:
    repo, runtime, path = roots
    boundary = HighWaterAuthorityBoundary(
        DurableHighWaterStore(), runtime.parent / "high-water-authority"
    )
    with pytest.raises(ValueError, match="authority_unverified"):
        DurableSignerRuntimeGenerationAnchor(
            path,
            allowed_root=runtime,
            repo_root=repo,
            anchor_id="reddog-signer:production",
            signer=HmacAuthenticator(),
            verifier=VerifierOnly(),
            high_water_authority=object(),
            high_water_authority_boundary=boundary,
        )
