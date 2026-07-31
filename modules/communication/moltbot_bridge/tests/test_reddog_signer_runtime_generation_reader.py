"""Security tests for the verifier-only signer-generation reader."""

from __future__ import annotations

import inspect
from collections.abc import Mapping
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from modules.communication.moltbot_bridge.src import (
    reddog_signer_runtime_generation_reader as reader_module,
)
from modules.communication.moltbot_bridge.src import (
    reddog_signer_runtime_generation_verifier_authority as verifier_module,
)
from modules.communication.moltbot_bridge.src.reddog_atomic_signer_runtime_generation_high_water import (
    AtomicSignerRuntimeGenerationHighWaterReader,
    AtomicSignerRuntimeGenerationHighWaterStore,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    encode_ed25519_public_key,
    encode_ed25519_signature,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_anchor import (
    DurableSignerRuntimeGenerationAnchor,
    SignerRuntimeGenerationBinding,
    SignerRuntimeGenerationHighWater,
    VerifiedSignerRuntimeGenerationHighWater,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_reader import (
    DurableSignerRuntimeGenerationReader,
    VerifiedSignerRuntimeGenerationHighWaterReader,
    create_signer_runtime_generation_high_water_reader_authority,
    create_signer_runtime_generation_reader_authority,
    require_signer_runtime_generation_high_water_reader_authority,
    require_signer_runtime_generation_reader_authority,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_verifier_authority import (
    create_signer_runtime_generation_verifier_authority,
    require_signer_runtime_generation_verifier_authority,
)


class Ed25519GenerationSigner:
    def __init__(self) -> None:
        self.private_key = Ed25519PrivateKey.generate()
        public = self.private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        self.public_key = encode_ed25519_public_key(public)
        authority, boundary = (
            create_signer_runtime_generation_verifier_authority(
                self.public_key
            )
        )
        self.verifier_authority = authority
        self.verifier_boundary = boundary
        self.authenticator_id = boundary.require(authority).authenticator_id

    def authenticate(self, payload: bytes) -> str:
        return encode_ed25519_signature(self.private_key.sign(payload))


class Boundary:
    def __init__(self, store) -> None:
        self.capability = object()
        self.verified = VerifiedSignerRuntimeGenerationHighWater(
            store=store,
            store_id=store.store_id,
            durability_receipt_id=store.durability_receipt_id,
        )

    def require(self, value: object):
        if value is not self.capability:
            raise ValueError("test_authority_invalid")
        return self.verified


def _sha(char: str) -> str:
    return "sha256:" + char * 64


def _roots(tmp_path: Path) -> tuple[Path, Path, Path]:
    repo = tmp_path / "repo"
    runtime = tmp_path / "runtime"
    authority = tmp_path / "authority"
    repo.mkdir()
    runtime.mkdir()
    authority.mkdir()
    return repo, runtime, authority


def _high_water(repo: Path, authority: Path):
    signing = Ed25519GenerationSigner()
    high_water = AtomicSignerRuntimeGenerationHighWaterStore(
        authority / "high-water.json",
        allowed_root=authority,
        repo_root=repo,
        store_id="high-water:production",
        durability_receipt_id=_sha("e"),
        signer=signing,
        verifier=signing.verifier_boundary.require(
            signing.verifier_authority
        ),
    )
    return signing, high_water


def _reader(
    repo: Path,
    runtime: Path,
    authority: Path,
    signing: Ed25519GenerationSigner | None = None,
):
    verifier = signing or Ed25519GenerationSigner()
    high_water_reader = AtomicSignerRuntimeGenerationHighWaterReader(
        authority / "high-water.json",
        allowed_root=authority,
        repo_root=repo,
        store_id="high-water:production",
        durability_receipt_id=_sha("e"),
        verifier_authority=verifier.verifier_authority,
        verifier_authority_boundary=verifier.verifier_boundary,
    )
    high_water_authority, reader_boundary = (
        create_signer_runtime_generation_high_water_reader_authority(
            high_water_reader
        )
    )
    return DurableSignerRuntimeGenerationReader(
        runtime / "anchor.json",
        allowed_root=runtime,
        repo_root=repo,
        anchor_id="reddog-signer:production",
        verifier_authority=verifier.verifier_authority,
        verifier_authority_boundary=verifier.verifier_boundary,
        high_water_authority=high_water_authority,
        high_water_authority_boundary=reader_boundary,
    )


def test_reader_holds_no_signing_capability_and_reads_active_generation(
    tmp_path: Path,
) -> None:
    repo, runtime, authority = _roots(tmp_path)
    signing, high_water = _high_water(repo, authority)
    boundary = Boundary(high_water)
    anchor_path = runtime / "anchor.json"
    writer = DurableSignerRuntimeGenerationAnchor(
        anchor_path,
        allowed_root=runtime,
        repo_root=repo,
        anchor_id="reddog-signer:production",
        signer=signing,
        verifier=signing.verifier_boundary.require(
            signing.verifier_authority
        ),
        high_water_authority=boundary.capability,
        high_water_authority_boundary=boundary,
    )
    writer.activate(
        SignerRuntimeGenerationBinding(
            generation=1,
            manifest_id=_sha("1"),
            artifact_generation_digest=_sha("2"),
            config_digest=_sha("3"),
            config_raw_digest=_sha("4"),
            run_packet_digest=_sha("5"),
        ),
        expected_revision=None,
    )
    reader = _reader(repo, runtime, authority, signing)

    assert reader.load().generation == 1
    assert not hasattr(reader, "__dict__")
    assert not hasattr(reader, "_verifier")
    assert not hasattr(reader, "_high_water")
    assert not hasattr(reader, "_store")

    reader_authority, reader_boundary = (
        create_signer_runtime_generation_reader_authority(reader)
    )
    accepted = require_signer_runtime_generation_reader_authority(
        reader_authority, reader_boundary
    )
    anchor_path.unlink()
    with pytest.raises(ValueError, match="rollback_detected"):
        accepted.load()


def test_lifecycle_reader_authority_object_graph_has_no_effect_capability(
    tmp_path: Path,
) -> None:
    repo, runtime, authority = _roots(tmp_path)
    signing, _ = _high_water(repo, authority)
    reader = _reader(repo, runtime, authority, signing)
    _, boundary = create_signer_runtime_generation_reader_authority(reader)
    forbidden = {
        "activate",
        "advance",
        "authenticate",
        "commit",
        "commit_prepared",
        "prepare",
        "private_key",
        "sign",
    }

    for value in _reachable_runtime_values(boundary):
        assert not any(
            callable(getattr(value, name, None))
            or getattr(value, name, None) is not None
            for name in forbidden
        )


def test_factory_authority_payloads_cannot_be_replaced_after_mint(
    tmp_path: Path,
) -> None:
    repo, runtime, authority = _roots(tmp_path)
    signing = Ed25519GenerationSigner()
    reader = _reader(repo, runtime, authority, signing)
    reader_authority, reader_boundary = (
        create_signer_runtime_generation_reader_authority(reader)
    )
    high_water = AtomicSignerRuntimeGenerationHighWaterReader(
        authority / "high-water.json",
        allowed_root=authority,
        repo_root=repo,
        store_id="high-water:production",
        durability_receipt_id=_sha("e"),
        verifier_authority=signing.verifier_authority,
        verifier_authority_boundary=signing.verifier_boundary,
    )
    high_authority, high_boundary = (
        create_signer_runtime_generation_high_water_reader_authority(
            high_water
        )
    )

    for boundary, field in (
        (reader_boundary, "_reader"),
        (high_boundary, "_reader"),
        (signing.verifier_boundary, "_verifier"),
    ):
        with pytest.raises(AttributeError):
            setattr(boundary, field, object())
        with pytest.raises(AttributeError):
            object.__setattr__(boundary, field, object())

    accepted_reader = require_signer_runtime_generation_reader_authority(
        reader_authority, reader_boundary
    )
    accepted_high = (
        require_signer_runtime_generation_high_water_reader_authority(
            high_authority, high_boundary
        ).reader
    )
    accepted_verifier = require_signer_runtime_generation_verifier_authority(
        signing.verifier_authority, signing.verifier_boundary
    )
    with pytest.raises(AttributeError):
        object.__setattr__(accepted_verifier, "_verifier", signing)
    with pytest.raises(AttributeError):
        object.__setattr__(accepted_verifier, "_hidden_signer", signing)
    assert accepted_reader.load() is None
    assert accepted_high.load("reddog-signer:production") is None
    assert not hasattr(accepted_verifier, "sign")


def test_generation_authority_registries_are_not_module_mutation_surfaces() -> None:
    for module, names in (
        (
            reader_module,
            (
                "_READER_TARGETS",
                "_READER_AUTHORITIES",
                "_HIGH_WATER_READER_TARGETS",
                "_HIGH_WATER_READER_AUTHORITIES",
                "_DURABLE_READER_STATES",
                "_issue_reader_target",
                "_lookup_reader_target",
                "_issue_high_water_target",
                "_lookup_high_water_target",
            ),
        ),
        (
            verifier_module,
            (
                "_VERIFIER_TARGETS",
                "_VERIFIER_AUTHORITIES",
                "_issue_verifier_target",
                "_lookup_verifier_target",
                "_issue_verifier_authority",
                "_lookup_verifier_authority",
            ),
        ),
    ):
        for name in names:
            assert not hasattr(module, name)


def test_generation_authority_public_apis_reject_registry_injection(
    tmp_path: Path,
) -> None:
    repo, runtime, authority = _roots(tmp_path)
    signing = Ed25519GenerationSigner()
    reader = _reader(repo, runtime, authority, signing)
    reader_authority, reader_boundary = (
        create_signer_runtime_generation_reader_authority(reader)
    )
    accepted_reader = require_signer_runtime_generation_reader_authority(
        reader_authority, reader_boundary
    )
    verifier = require_signer_runtime_generation_verifier_authority(
        signing.verifier_authority, signing.verifier_boundary
    )

    for callable_value in (
        create_signer_runtime_generation_verifier_authority,
        create_signer_runtime_generation_reader_authority,
        accepted_reader.load,
        verifier.verify,
    ):
        parameters = inspect.signature(callable_value).parameters
        assert "_issue" not in parameters
        assert "_lookup" not in parameters

    with pytest.raises(TypeError):
        accepted_reader.load(_lookup=lambda _value: object())
    with pytest.raises(TypeError):
        verifier.verify(b"payload", "not-a-signature", _lookup=lambda _value: True)


def test_reader_sources_cannot_be_retargeted_after_authority_mint(
    tmp_path: Path,
) -> None:
    repo, runtime, authority = _roots(tmp_path)
    signing = Ed25519GenerationSigner()
    reader = _reader(repo, runtime, authority, signing)
    reader_authority, reader_boundary = (
        create_signer_runtime_generation_reader_authority(reader)
    )
    accepted = require_signer_runtime_generation_reader_authority(
        reader_authority, reader_boundary
    )

    for target in (reader, accepted):
        with pytest.raises(AttributeError):
            object.__setattr__(target, "_hidden_signer", signing)
        with pytest.raises(AttributeError):
            object.__setattr__(target, "_verifier", signing)
    assert accepted.load() is None
    for value in _reachable_runtime_values(reader_boundary):
        assert not hasattr(value, "private_key")
        assert not callable(getattr(value, "authenticate", None))


def test_high_water_reader_cannot_be_retargeted_after_authority_mint(
    tmp_path: Path,
) -> None:
    repo, _, authority = _roots(tmp_path)
    signing = Ed25519GenerationSigner()
    reader = AtomicSignerRuntimeGenerationHighWaterReader(
        authority / "high-water.json",
        allowed_root=authority,
        repo_root=repo,
        store_id="high-water:production",
        durability_receipt_id=_sha("e"),
        verifier_authority=signing.verifier_authority,
        verifier_authority_boundary=signing.verifier_boundary,
    )
    high_authority, boundary = (
        create_signer_runtime_generation_high_water_reader_authority(reader)
    )
    accepted = require_signer_runtime_generation_high_water_reader_authority(
        high_authority, boundary
    ).reader

    for target in (reader, accepted):
        with pytest.raises(AttributeError):
            object.__setattr__(target, "_hidden_signer", signing)
        with pytest.raises(AttributeError):
            object.__setattr__(target, "_verifier", signing)
    assert accepted.load("reddog-signer:production") is None


def _reachable_runtime_values(root: object) -> list[object]:
    """Traverse retained runtime state without following module globals."""

    values: list[object] = []
    pending = [root]
    seen: set[int] = set()
    while pending:
        value = pending.pop()
        if id(value) in seen:
            continue
        seen.add(id(value))
        values.append(value)
        if isinstance(value, (str, bytes, int, float, bool, type(None), Path)):
            continue
        if isinstance(value, Mapping):
            pending.extend(value.values())
        elif isinstance(value, (tuple, list, set, frozenset)):
            pending.extend(value)
        if inspect.isfunction(value) and value.__closure__:
            pending.extend(cell.cell_contents for cell in value.__closure__)
        attributes = getattr(value, "__dict__", None)
        if isinstance(attributes, dict):
            pending.extend(attributes.values())
        for item_type in type(value).__mro__:
            slots = getattr(item_type, "__slots__", ())
            slots = (slots,) if isinstance(slots, str) else slots
            for slot in slots:
                if slot in {"__dict__", "__weakref__"}:
                    continue
                try:
                    pending.append(getattr(value, slot))
                except AttributeError:
                    pass
    return values


def test_reader_rejects_authenticated_pending_generation(tmp_path: Path) -> None:
    repo, runtime, authority = _roots(tmp_path)
    signing, high_water = _high_water(repo, authority)
    high_water.prepare(
        "reddog-signer:production",
        expected=None,
        next_value=SignerRuntimeGenerationHighWater(
            generation=1, revision="1" * 64
        ),
    )

    with pytest.raises(ValueError, match="pending_transaction"):
        _reader(repo, runtime, authority, signing).load()


def test_reader_rejects_same_rollback_domain(tmp_path: Path) -> None:
    repo, runtime, _ = _roots(tmp_path)
    signing = Ed25519GenerationSigner()
    high_water_reader = AtomicSignerRuntimeGenerationHighWaterReader(
        runtime / "high-water.json",
        allowed_root=runtime,
        repo_root=repo,
        store_id="high-water:production",
        durability_receipt_id=_sha("e"),
        verifier_authority=signing.verifier_authority,
        verifier_authority_boundary=signing.verifier_boundary,
    )
    high_water_authority, boundary = (
        create_signer_runtime_generation_high_water_reader_authority(
            high_water_reader
        )
    )

    with pytest.raises(ValueError, match="high_water_domain_overlap"):
        DurableSignerRuntimeGenerationReader(
            runtime / "anchor.json",
            allowed_root=runtime,
            repo_root=repo,
            anchor_id="reddog-signer:production",
            verifier_authority=signing.verifier_authority,
            verifier_authority_boundary=signing.verifier_boundary,
            high_water_authority=high_water_authority,
            high_water_authority_boundary=boundary,
        )


def test_reader_rejects_write_capable_high_water(tmp_path: Path) -> None:
    repo, runtime, authority = _roots(tmp_path)
    signing, high_water = _high_water(repo, authority)
    with pytest.raises(ValueError, match="high_water_reader_invalid"):
        create_signer_runtime_generation_high_water_reader_authority(
            high_water  # type: ignore[arg-type]
        )


def test_reader_rejects_forged_high_water_authority_boundary(
    tmp_path: Path,
) -> None:
    repo, runtime, authority = _roots(tmp_path)
    signing = Ed25519GenerationSigner()
    high_reader = AtomicSignerRuntimeGenerationHighWaterReader(
        authority / "high-water.json",
        allowed_root=authority,
        repo_root=repo,
        store_id="high-water:production",
        durability_receipt_id=_sha("e"),
        verifier_authority=signing.verifier_authority,
        verifier_authority_boundary=signing.verifier_boundary,
    )

    class ForgedBoundary:
        def require(self, value):
            del value
            return VerifiedSignerRuntimeGenerationHighWaterReader(
                reader=high_reader,
                store_id=high_reader.store_id,
                durability_receipt_id=high_reader.durability_receipt_id,
            )

    with pytest.raises(ValueError, match="reader_boundary_invalid"):
        DurableSignerRuntimeGenerationReader(
            runtime / "anchor.json",
            allowed_root=runtime,
            repo_root=repo,
            anchor_id="reddog-signer:production",
            verifier_authority=signing.verifier_authority,
            verifier_authority_boundary=signing.verifier_boundary,
            high_water_authority=object(),
            high_water_authority_boundary=ForgedBoundary(),
        )


def test_reader_rejects_verifier_with_signing_method(tmp_path: Path) -> None:
    repo, runtime, authority = _roots(tmp_path)
    signing = Ed25519GenerationSigner()
    high_water_reader = AtomicSignerRuntimeGenerationHighWaterReader(
        authority / "high-water.json",
        allowed_root=authority,
        repo_root=repo,
        store_id="high-water:production",
        durability_receipt_id=_sha("e"),
        verifier_authority=signing.verifier_authority,
        verifier_authority_boundary=signing.verifier_boundary,
    )
    high_water_authority, boundary = (
        create_signer_runtime_generation_high_water_reader_authority(
            high_water_reader
        )
    )

    with pytest.raises(ValueError, match="authority_unverified"):
        DurableSignerRuntimeGenerationReader(
            runtime / "anchor.json",
            allowed_root=runtime,
            repo_root=repo,
            anchor_id="reddog-signer:production",
            verifier_authority=object(),
            verifier_authority_boundary=signing.verifier_boundary,
            high_water_authority=high_water_authority,
            high_water_authority_boundary=boundary,
        )
