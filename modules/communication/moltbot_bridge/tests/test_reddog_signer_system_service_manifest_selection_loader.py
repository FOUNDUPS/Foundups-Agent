"""Tests for the root-owned signer system-service selection loader."""

from __future__ import annotations

import json
import sys
from contextlib import contextmanager, nullcontext
from pathlib import Path
from typing import Any

import pytest

from modules.communication.moltbot_bridge.src import (
    reddog_current_generation_manifest_launch_selection as selection_module,
    reddog_signer_current_principal_authority_resolver as current_resolver_module,
    reddog_signer_system_service_manifest_selection_loader as loader_module,
)
from modules.communication.moltbot_bridge.src.reddog_atomic_signer_runtime_generation_high_water import (
    AtomicSignerRuntimeGenerationHighWaterStore,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    RuntimeArtifactManifestError,
    digest,
    raw_digest,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_launch_selection import (
    create_runtime_artifact_manifest_launch_selection_boundary,
)
from modules.communication.moltbot_bridge.src.reddog_signed_runtime_artifact_manifest import (
    produce_signed_runtime_artifact_manifest,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    Ed25519SignatureVerifier,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_anchor import (
    DurableSignerRuntimeGenerationAnchor,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_contract import (
    SignerRuntimeGenerationBinding,
)
from modules.communication.moltbot_bridge.src.reddog_signer_system_service_manifest_selection_loader import (
    SCHEMA_VERSION,
    load_system_service_manifest_selection,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_run_packet_supply import (
    run_reddog_signer_socket_service_run_packet_supply,
)
from modules.communication.moltbot_bridge.src.reddog_sqlite_monotonic_authority_store import (
    SqliteMonotonicAuthorityStore,
)
from modules.communication.moltbot_bridge.tests.reddog_signer_generation_test_support import (
    GenerationSigner,
    HighWaterBoundary,
    generation_witness_binding,
)
from modules.communication.moltbot_bridge.tests.test_reddog_current_generation_manifest_launch_selection import (
    _legacy_values,
)
from modules.communication.moltbot_bridge.tests.test_reddog_signer_socket_service_runtime_cli import (
    _config,
    _write_json,
)
from modules.communication.moltbot_bridge.tests.test_reddog_signed_runtime_artifact_manifest import (
    CONSENSUS_DIGEST,
    KEY_EPOCH,
    NOW,
    PRINCIPAL_ID,
    SOURCE_RECEIPT_ID,
    _boundary,
    _build_harness,
    _manifest_signing_context,
)


@pytest.fixture(autouse=True)
def _trusted_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(selection_module, "_now_epoch", lambda: NOW)


def _fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Any, Path, dict[str, Any]]:
    harness = _build_harness(tmp_path)
    assert harness.produce().accepted is True
    values = _legacy_values(harness)
    owner = _generation_owner_config(harness, values)
    owner_root = tmp_path / "signer-owner"
    owner_root.mkdir()
    owner_path = owner_root / "owner.json"
    owner_path.write_text(
        json.dumps(owner, sort_keys=True, separators=(",", ":")),
        encoding="ascii",
    )
    owner_path.chmod(0o400)
    monkeypatch.setattr(
        loader_module,
        "_read_root_owned_bytes",
        lambda target, _root: target.read_bytes(),
    )
    return harness, owner_path, owner


def _generation_owner_config(harness: Any, values: dict[str, Any]) -> dict[str, Any]:
    runtime = harness.runtime_root
    authority_root = runtime.parent / "signer-authority"
    witness_root = runtime.parent / "signer-generation-witness"
    authority_root.mkdir()
    witness_root.mkdir()
    signing = GenerationSigner()
    witness = SqliteMonotonicAuthorityStore(
        witness_root / "generation.sqlite3",
        allowed_root=witness_root,
        repo_root=harness.repo_root,
        store_id="signer-generation-witness:v1",
        durability_receipt_id="sha256:" + "7" * 64,
    )
    binding = generation_witness_binding(
        authenticator_id=signing.authenticator_id,
        runtime_root=runtime,
        high_water_store_id="signer-high-water:v1",
        high_water_durability_receipt_id="sha256:" + "8" * 64,
        witness_store_id=witness.store_id,
        witness_durability_receipt_id=witness.durability_receipt_id,
    )
    high_water = AtomicSignerRuntimeGenerationHighWaterStore(
        authority_root / "high-water.json",
        allowed_root=authority_root,
        repo_root=harness.repo_root,
        store_id="signer-high-water:v1",
        durability_receipt_id="sha256:" + "8" * 64,
        signer=signing,
        verifier=signing.verifier,
        generation_witness_store=witness,
        generation_witness_binding=binding,
    )
    high_boundary = HighWaterBoundary(high_water)
    writer = DurableSignerRuntimeGenerationAnchor(
        runtime / "generation-anchor.json",
        allowed_root=runtime,
        repo_root=harness.repo_root,
        anchor_id="reddog-signer:production",
        signer=signing,
        verifier=signing.verifier,
        high_water_authority=high_boundary.capability,
        high_water_authority_boundary=high_boundary,
    )
    writer.activate(_generation_binding(values), expected_revision=None)
    return _owner_mapping(
        harness,
        signing=signing,
        binding=binding,
        authority_root=authority_root,
        witness_root=witness_root,
    )


def _generation_binding(values: dict[str, Any]):
    return SignerRuntimeGenerationBinding(
        generation=1,
        manifest_id=str(values["manifest_id"]),
        artifact_generation_digest=str(values["artifact_generation_digest"]),
        config_digest=str(values["config_digest"]),
        config_raw_digest=str(values["config_raw_digest"]),
        run_packet_digest=str(values["run_packet_digest"]),
    )


def _owner_mapping(
    harness: Any,
    *,
    signing: GenerationSigner,
    binding: Any,
    authority_root: Path,
    witness_root: Path,
) -> dict[str, Any]:
    runtime = harness.runtime_root.resolve()
    value = {
        "schema_version": SCHEMA_VERSION,
        "config_id": "",
        "repo_root_digest": raw_digest(
            str(harness.repo_root.resolve()).encode("utf-8")
        ),
        "runtime_root": str(runtime),
        "anchor_path": str(runtime / "generation-anchor.json"),
        "anchor_id": "reddog-signer:production",
        "generation_public_key": signing.public_key,
        "generation_authenticator_id": signing.authenticator_id,
        "generation_key_epoch": binding.key_epoch,
        "generation_signer_public_key_fingerprint": (
            binding.signer_public_key_fingerprint
        ),
        "high_water_root": str(authority_root.resolve()),
        "high_water_path": str(authority_root.resolve() / "high-water.json"),
        "high_water_store_id": "signer-high-water:v1",
        "high_water_durability_receipt_id": "sha256:" + "8" * 64,
        "witness_root": str(witness_root.resolve()),
        "witness_path": str(witness_root.resolve() / "generation.sqlite3"),
        "witness_store_id": "signer-generation-witness:v1",
        "witness_durability_receipt_id": "sha256:" + "7" * 64,
    }
    value["config_id"] = digest(
        {key: item for key, item in value.items() if key != "config_id"}
    )
    return value


def test_root_owned_config_reconstructs_current_selection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    harness, owner_path, owner = _fixture(tmp_path, monkeypatch)

    capability, boundary = load_system_service_manifest_selection(
        owner_config_path=owner_path,
        repo_root=harness.repo_root,
        config_path=harness.runtime_root / "signer_service_config.json",
        run_packet_path=(harness.runtime_root / "signer_service_run_packet.json"),
    )
    selected = boundary.consume(capability)

    assert selected["owner_config_id"] == owner["config_id"]
    assert selected["generation"] == 1
    assert selected["config_path"].endswith("signer_service_config.json")


def test_tampered_owner_config_rejects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    harness, owner_path, owner = _fixture(tmp_path, monkeypatch)
    owner["anchor_id"] = "attacker-anchor"
    owner_path.chmod(0o600)
    owner_path.write_text(json.dumps(owner), encoding="ascii")
    owner_path.chmod(0o400)

    with pytest.raises(
        RuntimeArtifactManifestError, match="signer_owner_config_id_invalid"
    ):
        load_system_service_manifest_selection(
            owner_config_path=owner_path,
            repo_root=harness.repo_root,
            config_path=harness.runtime_root / "signer_service_config.json",
            run_packet_path=(harness.runtime_root / "signer_service_run_packet.json"),
        )


def test_caller_paths_must_match_current_runtime(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    harness, owner_path, _owner = _fixture(tmp_path, monkeypatch)

    with pytest.raises(
        RuntimeArtifactManifestError, match="signer_owner_cli_path_mismatch"
    ):
        load_system_service_manifest_selection(
            owner_config_path=owner_path,
            repo_root=harness.repo_root,
            config_path=tmp_path / "attacker.json",
            run_packet_path=(harness.runtime_root / "signer_service_run_packet.json"),
        )


def test_owner_config_root_cannot_overlap_runtime_roots(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    harness, owner_path, owner = _fixture(tmp_path, monkeypatch)
    owner["runtime_root"] = str(owner_path.parent.resolve())
    owner["anchor_path"] = str(owner_path.parent.resolve() / "generation-anchor.json")
    owner["config_id"] = digest(
        {key: item for key, item in owner.items() if key != "config_id"}
    )
    owner_path.chmod(0o600)
    owner_path.write_text(
        json.dumps(owner, sort_keys=True, separators=(",", ":")),
        encoding="ascii",
    )
    owner_path.chmod(0o400)

    with pytest.raises(RuntimeArtifactManifestError, match="signer_owner_root_overlap"):
        load_system_service_manifest_selection(
            owner_config_path=owner_path,
            repo_root=harness.repo_root,
            config_path=harness.runtime_root / "signer_service_config.json",
            run_packet_path=(harness.runtime_root / "signer_service_run_packet.json"),
        )


def test_system_service_loader_uses_root_owned_owner_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    harness, owner_path, owner = _fixture(tmp_path, monkeypatch)
    capability, boundary = load_system_service_manifest_selection(
        owner_config_path=owner_path,
        repo_root=harness.repo_root,
        config_path=harness.runtime_root / "signer_service_config.json",
        run_packet_path=(harness.runtime_root / "signer_service_run_packet.json"),
    )

    assert boundary.consume(capability)["owner_config_id"] == owner["config_id"]


def test_non_posix_owner_policy_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "owner.json"
    target.write_text("{}", encoding="ascii")
    monkeypatch.setattr(loader_module.sys, "platform", "win32")

    with pytest.raises(
        RuntimeArtifactManifestError,
        match="signer_owner_linux_service_required",
    ):
        loader_module._read_root_owned_bytes(target, tmp_path)


def test_conversation_principal_resolver_rereads_current_generation_per_use(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    selections = iter(({"generation": 1}, {"generation": 2}))
    loaded: list[int] = []
    lease_active = False
    class Boundary:
        def select(self, _request: object, *, now_epoch: int):
            assert now_epoch == NOW
            return next(selections)

        def _lease_current(self, capability: object):
            @contextmanager
            def lease():
                nonlocal lease_active
                assert lease_active is False
                lease_active = True
                try:
                    yield capability
                finally:
                    lease_active = False

            return lease()
    class Resolver:
        def __init__(self, generation: int) -> None:
            self.generation = generation

        def resolve(self, principal_id: str, principal_provider: str):
            assert lease_active is True
            assert (principal_id, principal_provider) == (
                "principal_012", "principal-signature"
            )
            return "current" if self.generation == 1 else None

        def resolve_unique(self, principal_id: str):
            assert lease_active is True
            assert principal_id == "principal_012"
            return "current" if self.generation == 1 else None

    def load(*, repo_root: Path, selection: object):
        assert repo_root == tmp_path.resolve()
        generation = int(selection["generation"])
        loaded.append(generation)
        return Resolver(generation)

    monkeypatch.setattr(
        current_resolver_module,
        "load_current_generation_principal_authority_resolver",
        load,
    )
    resolver = (
        current_resolver_module.ManifestBoundCurrentPrincipalAuthorityResolver(
            tmp_path, Boundary(), clock=lambda: NOW
        )
    )

    assert resolver.resolve("principal_012", "principal-signature") == "current"
    assert resolver.resolve("principal_012", "principal-signature") is None
    assert loaded == [1, 2]
    assert lease_active is False


@pytest.mark.skipif(
    not sys.platform.startswith("linux"),
    reason="Linux ownership policy",
)
def test_world_writable_owner_ancestor_fails_closed(tmp_path: Path) -> None:
    owner_root = tmp_path / "unsafe-owner"
    owner_root.mkdir()
    owner_root.chmod(0o777)
    target = owner_root / "owner.json"
    target.write_text("{}", encoding="ascii")
    target.chmod(0o400)

    with pytest.raises(
        RuntimeArtifactManifestError,
        match="signer_owner_config_permissions_invalid",
    ):
        loader_module._require_secure_ancestry(owner_root)


def test_owner_read_is_descriptor_bound_and_bounded() -> None:
    source = Path(loader_module.__file__).read_text(encoding="utf-8")
    start = source.index("def _read_root_owned_linux_bytes")
    end = source.index("\ndef _require_secure_ancestry", start)
    function_source = source[start:end]

    assert "dir_fd=directory_fd" in function_source
    assert "O_NOFOLLOW" in function_source
    assert "_require_root_file_fd(file_fd)" in function_source
    assert "_read_bounded_fd(file_fd)" in function_source
    assert "read_bytes" not in function_source


def _prepare_real_cli_owner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch | None,
    *,
    include_outcome_policy: bool = False,
) -> dict[str, Any]:
    harness = _build_harness(tmp_path)
    config_path = _write_json(
        harness.runtime_root / "signer_service_config.json",
        _runtime_config(harness, include_outcome_policy=include_outcome_policy),
    )
    owner_path = tmp_path / "signer-owner" / "owner.json"
    packet_path, supplied = _runtime_packet(harness, config_path, owner_path)
    authority, boundary = _fresh_manifest_authority(harness)
    _sign_and_publish_manifest(harness, authority, boundary)
    selector = create_runtime_artifact_manifest_launch_selection_boundary(
        authority=authority,
        authority_boundary=boundary,
        signature_verifier=Ed25519SignatureVerifier(),
    )
    values = dict(
        selector.consume(selector.select(harness.read_manifest(), now_epoch=NOW))
    )
    owner = _generation_owner_config(harness, values)
    if monkeypatch is not None:
        monkeypatch.setattr(
            loader_module,
            "_read_root_owned_bytes",
            lambda target, _root: target.read_bytes(),
        )
    return {
        "harness": harness,
        "config_path": config_path,
        "packet_path": packet_path,
        "owner_path": _write_owner_config(tmp_path, owner),
        "supplied": supplied,
        "selection": values,
    }


def _runtime_config(
    harness: Any, *, include_outcome_policy: bool = False
) -> dict[str, Any]:
    value = _config(
        harness.reddog_public_key,
        socket_path=harness.runtime_root / "signer.sock",
    )
    value["control_loop_authority_policy"].update(
        {
            "issuer_principal_id": PRINCIPAL_ID,
            "key_epoch": KEY_EPOCH,
            "consensus_receipt_digest": CONSENSUS_DIGEST,
            "authority_profile_digest": digest(harness.authority_profile),
            "authority_profile_source_receipt_id": SOURCE_RECEIPT_ID,
        }
    )
    value["key_provider_profiles"] = [value.pop("key_provider_profile")]
    if include_outcome_policy:
        value["verified_outcome_signer_policy"] = {
            "issuer_principal_id": PRINCIPAL_ID,
            "reddog_id": "reddog-0102",
            "signer_public_key": harness.reddog_public_key,
            "key_epoch": KEY_EPOCH,
            "authority_tier": "HIGH",
            "consensus_receipt_digest": CONSENSUS_DIGEST,
        }
    return value


def _runtime_packet(harness: Any, config_path: Path, owner_path: Path):
    packet_path = harness.runtime_root / "signer_service_run_packet.json"
    supplied = run_reddog_signer_socket_service_run_packet_supply(
        repo_root=harness.repo_root,
        config_path=config_path,
        output_path=packet_path,
        owner_authority_config_path=owner_path,
        op_executable="C:/Program Files/1Password/op.exe",
        op_timeout_s=7,
        ttl_seconds=61,
        session_id="session-prod",
        python_executable=sys.executable,
    )
    assert supplied.accepted is True
    return packet_path, supplied


def _fresh_manifest_authority(harness: Any):
    boundary = _boundary(
        harness.repo_root,
        harness.runtime_root,
        harness.work_state_store,
        harness.principal_public_key,
    )
    queue_id = next(
        item["queue_item_id"] for item in harness.work_state["wre_queue_items"]
    )
    authority = boundary.issue(
        identity=harness.identity,
        work_authority=harness.work_authority,
        queue_item_id=queue_id,
        now_epoch=NOW,
    )
    return authority, boundary


def _sign_and_publish_manifest(harness: Any, authority: Any, boundary: Any) -> None:
    _signer, context = _manifest_signing_context(
        authority,
        boundary,
        harness.reddog_private_key,
        harness.reddog_public_key,
    )
    result = produce_signed_runtime_artifact_manifest(
        manifest_directory=harness.manifest_directory,
        nonce="owner-cli-manifest",
        issued_at=NOW,
        expires_at=NOW + 120,
        context=context,
    )
    assert result.accepted is True


def _write_owner_config(tmp_path: Path, owner: dict[str, Any]) -> Path:
    owner_root = tmp_path / "signer-owner"
    owner_root.mkdir()
    owner_path = owner_root / "owner.json"
    owner_path.write_text(
        json.dumps(owner, sort_keys=True, separators=(",", ":")),
        encoding="ascii",
    )
    return owner_path
