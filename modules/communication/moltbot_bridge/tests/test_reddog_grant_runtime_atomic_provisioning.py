"""Grant-profile integration for the existing atomic provisioner."""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from threading import Event, Thread

import pytest

from modules.communication.moltbot_bridge.src.reddog_atomic_signer_runtime_generation_high_water import (
    AtomicSignerRuntimeGenerationHighWaterStore,
)
from modules.communication.moltbot_bridge.src.reddog_grant_authority_service_artifact_contract import (
    CONFIG_SCHEMA,
    CONFIG_SCHEMA_V2,
)
from modules.communication.moltbot_bridge.src.reddog_grant_authority_service_git_archive_builder import (
    build_grant_service_archive_from_git,
)
from modules.communication.moltbot_bridge.src.reddog_grant_authority_service_git_source_policy import (
    SOURCE_POLICY_SCHEMA,
    grant_service_git_source_policy_digest,
)
from modules.communication.moltbot_bridge.src.reddog_grant_authority_service_owner_binding import (
    grant_authority_owner_operation_fence,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    GRANT_AUTHORITY_SERVICE_ARCHIVE,
    GRANT_AUTHORITY_SERVICE_CONFIG,
    GRANT_AUTHORITY_SERVICE_RUN_PACKET,
    RUNTIME_PROFILE_GRANT_AUTHORITY_SERVICE_GIT_PROVENANCE,
    SCHEMA_VERSION_V3,
    canonical_json,
    digest,
    raw_digest,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_atomic_provisioning import (
    provision_signer_runtime_generation,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_atomic_provisioning_contract import (
    SignerRuntimeAtomicProvisioningContext,
    create_grant_runtime_atomic_provisioning_context,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_anchor import (
    DurableSignerRuntimeGenerationAnchor,
)
from modules.communication.moltbot_bridge.src.reddog_sqlite_monotonic_authority_store import (
    SqliteMonotonicAuthorityStore,
)
from modules.communication.moltbot_bridge.tests.reddog_signer_generation_test_support import (
    GenerationSigner,
    HighWaterBoundary,
    generation_witness_binding,
)
from modules.communication.moltbot_bridge.tests.test_reddog_grant_authority_service_authenticated_manifest_binding import (
    _GIT_SOURCES,
    _config,
    _fixture_at,
    _initialize_grant_git_repository,
    _run_packet,
)
from modules.communication.moltbot_bridge.tests.test_reddog_signed_runtime_artifact_manifest import (
    NOW,
    _build_harness,
)
from modules.communication.moltbot_bridge.tests.test_reddog_signer_independent_grant_authority_client_supply import (
    _owner,
)


@pytest.fixture(autouse=True)
def _clock(monkeypatch: pytest.MonkeyPatch) -> None:
    import modules.communication.moltbot_bridge.src.reddog_signer_runtime_atomic_provisioning as target

    monkeypatch.setattr(target, "_trusted_now", lambda: NOW)


def test_v4_policy_provisions_exact_grant_v3_generation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    setup = _setup(tmp_path, monkeypatch)

    result = _provision(setup["context"])

    assert result.accepted is True, result.rejection_reasons
    manifest = json.loads(Path(str(result.manifest_path)).read_text("utf-8"))
    assert manifest["schema_version"] == SCHEMA_VERSION_V3
    assert manifest["runtime_profile"] == (
        RUNTIME_PROFILE_GRANT_AUTHORITY_SERVICE_GIT_PROVENANCE
    )
    assert tuple(item["filename"] for item in manifest["artifacts"]) == (
        GRANT_AUTHORITY_SERVICE_CONFIG,
        GRANT_AUTHORITY_SERVICE_RUN_PACKET,
        GRANT_AUTHORITY_SERVICE_ARCHIVE,
    )
    activation = setup["anchor"].load()
    assert activation is not None
    assert activation.config_raw_digest == raw_digest(setup["config_raw"])
    assert activation.run_packet_digest == raw_digest(setup["packet_raw"])


def test_grant_config_v1_cannot_enter_v3_provisioning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    setup = _setup(tmp_path, monkeypatch, create_context=False)
    config = dict(setup["config"])
    for key in tuple(config):
        if key.startswith("source_policy_"):
            del config[key]
    config["schema_version"] = CONFIG_SCHEMA
    _write_artifacts(setup, config)

    with pytest.raises(ValueError, match="source_policy_config_mismatch"):
        _context(setup)


def test_grant_context_has_no_caller_supplied_source_policy_boundary() -> None:
    parameters = inspect.signature(
        create_grant_runtime_atomic_provisioning_context
    ).parameters
    fields = SignerRuntimeAtomicProvisioningContext.__dataclass_fields__

    assert "source_policy_authority" not in parameters
    assert "source_policy_boundary" not in parameters
    assert "source_policy_authority" not in fields
    assert "source_policy_boundary" not in fields


def test_alternate_committed_source_map_rejects_before_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    setup = _setup(tmp_path, monkeypatch, create_context=False)
    alternate = {
        "reddog_grant_authority_service.py": (
            "service/attacker_selected_service.py"
        )
    }
    archive = build_grant_service_archive_from_git(
        repo_root=setup["harness"].repo_root,
        source_commit_sha=setup["commit"],
        sources=alternate,
    )
    setup["archive"] = archive
    _write_artifacts(setup, setup["config"])

    with pytest.raises(ValueError, match="source_policy_binding_mismatch"):
        _context(setup)
    assert not setup["harness"].manifest_directory.exists()


def test_owner_replacement_during_commit_guard_rolls_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    setup = _setup(tmp_path, monkeypatch, create_context=False)
    from modules.communication.moltbot_bridge.src import (
        reddog_signer_system_service_manifest_selection_loader as loader,
    )
    rotating_loader = _RotateAfterAnchorWrite(setup)
    monkeypatch.setattr(loader, "_load_owner_config", rotating_loader)
    context = _context(setup)

    result = _provision(context)

    assert result.accepted is False
    assert setup["anchor"].load() is None
    assert rotating_loader.rotated is True, result.rejection_reasons


def test_grant_committed_witness_interruption_recovers_same_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    setup = _setup(tmp_path, monkeypatch)
    store = setup["anchor"]._high_water_store
    original = store.commit_prepared
    interrupted = [False]

    def fail_once(anchor_id: str, transaction_id: str) -> None:
        if not interrupted[0]:
            interrupted[0] = True
            raise RuntimeError("high_water_interrupted")
        original(anchor_id, transaction_id)

    monkeypatch.setattr(store, "commit_prepared", fail_once)
    result = _provision(setup["context"])

    assert result.accepted is True, result.rejection_reasons
    assert result.recovered_existing_activation is True
    assert setup["anchor"].load() is not None
    assert store.pending(setup["anchor"]._anchor_id) is None


def test_owner_operation_fence_serializes_compliant_rotation(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    owner = tmp_path / "owner" / "owner.json"
    repo.mkdir()
    owner.parent.mkdir()
    entered = Event()

    def rotate() -> None:
        with grant_authority_owner_operation_fence(owner, repo_root=repo):
            entered.set()

    with grant_authority_owner_operation_fence(owner, repo_root=repo):
        worker = Thread(target=rotate)
        worker.start()
        assert entered.wait(0.1) is False
    worker.join(timeout=2)
    assert entered.is_set() and not worker.is_alive()


class _RotateAfterAnchorWrite:
    def __init__(self, setup) -> None:
        self.setup = setup
        self.rotated = False

    def __call__(self, *_args, **_kwargs):
        anchor = self.setup["anchor"]
        if anchor._decode(anchor._store.load()) is not None:
            self.setup["owner_ref"][0] = self.setup["owner_replacement"]
            self.rotated = True
        return self.setup["owner_ref"][0]


def _setup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    *, create_context: bool = True,
):
    repo = tmp_path / "repo"
    (tmp_path / "harness").mkdir()
    harness = _build_harness(
        tmp_path / "harness", repo_root=repo,
        repo_initializer=_initialize_grant_git_repository,
    )
    authority = harness.authority_boundary.require(harness.authority)
    commit = str(authority["authorized_base_sha"])
    archive = build_grant_service_archive_from_git(
        repo_root=repo, source_commit_sha=commit, sources=_GIT_SOURCES,
    )
    owner_path, owner, policy = _owner_policy_fixture(
        tmp_path, repo=repo, runtime_root=harness.runtime_root
    )
    owner_ref = [owner]
    from modules.communication.moltbot_bridge.src import (
        reddog_signer_system_service_manifest_selection_loader as loader,
    )

    monkeypatch.setattr(loader, "_load_owner_config", lambda *_a, **_k: owner_ref[0])
    e0 = _fixture_at(tmp_path / "e0")
    config = _config(e0, raw_digest(archive))
    config.update(
        {
            "schema_version": CONFIG_SCHEMA_V2,
            "source_policy_owner_config_id": owner["config_id"],
            "source_policy_repo_root_digest": policy["repo_root_digest"],
            "source_policy_digest": policy["source_policy_digest"],
        }
    )
    setup = {
        "archive": archive, "commit": commit, "config": config,
        "harness": harness, "owner_path": owner_path, "owner_ref": owner_ref,
    }
    _write_artifacts(setup, config)
    setup["anchor"] = _anchor(harness, tmp_path)
    replacement = json.loads(json.dumps(owner))
    replacement["config_id"] = digest({**owner, "rotation": "replacement"})
    setup["owner_replacement"] = replacement
    if create_context:
        setup["context"] = _context(setup)
    return setup


def _owner_policy_fixture(
    tmp_path: Path, *, repo: Path, runtime_root: Path
):
    owner_path = tmp_path / "owner" / "owner.json"
    owner_path.parent.mkdir()
    (tmp_path / "owner-fixture").mkdir()
    owner = _owner(tmp_path / "owner-fixture", config_id="pending")
    owner["schema_version"] = "reddog_signer_system_service_owner_config.v4"
    owner["independent_grant_authority"].update(
        {
            "authority_root": str(runtime_root.resolve()),
            "authority_socket_path": str(
                (runtime_root / "grant-authority.sock").resolve()
            ),
        }
    )
    policy = {
        "schema_version": SOURCE_POLICY_SCHEMA,
        "repo_root_digest": raw_digest(str(repo.resolve()).encode("utf-8")),
        "sources": dict(_GIT_SOURCES),
        "source_policy_digest": grant_service_git_source_policy_digest(
            _GIT_SOURCES
        ),
    }
    owner["grant_authority_source_policy"] = policy
    owner["config_id"] = digest(
        {key: value for key, value in owner.items() if key != "config_id"}
    )
    return owner_path, owner, policy


def _write_artifacts(setup, config) -> None:
    runtime = setup["harness"].runtime_root
    archive = setup["archive"]
    config["archive_digest"] = raw_digest(archive)
    config_raw = canonical_json(config).encode("ascii")
    packet = _run_packet(raw_digest(config_raw), raw_digest(archive))
    packet_raw = canonical_json(packet).encode("ascii")
    (runtime / GRANT_AUTHORITY_SERVICE_ARCHIVE).write_bytes(archive)
    (runtime / GRANT_AUTHORITY_SERVICE_CONFIG).write_bytes(config_raw)
    (runtime / GRANT_AUTHORITY_SERVICE_RUN_PACKET).write_bytes(packet_raw)
    setup.update(
        {"config": config, "config_raw": config_raw, "packet_raw": packet_raw}
    )


def _context(setup):
    return create_grant_runtime_atomic_provisioning_context(
        manifest_signing=setup["harness"].context,
        generation_anchor=setup["anchor"],
        owner_config_path=setup["owner_path"],
    )


def _anchor(harness, tmp_path: Path):
    authority_root = tmp_path / "generation-authority"
    anchor_root = tmp_path / "generation-anchor"
    witness_root = tmp_path / "generation-witness"
    for root in (authority_root, anchor_root, witness_root):
        root.mkdir()
    signing = GenerationSigner()
    witness = SqliteMonotonicAuthorityStore(
        witness_root / "generation.sqlite3", allowed_root=witness_root,
        repo_root=harness.repo_root, store_id="grant-generation-witness:v1",
        durability_receipt_id="sha256:" + "7" * 64,
    )
    high_water = AtomicSignerRuntimeGenerationHighWaterStore(
        authority_root / "high-water.json", allowed_root=authority_root,
        repo_root=harness.repo_root, store_id="grant-high-water:v1",
        durability_receipt_id="sha256:" + "8" * 64, signer=signing,
        verifier=signing.verifier, generation_witness_store=witness,
        generation_witness_binding=generation_witness_binding(
            authenticator_id=signing.authenticator_id,
            runtime_root=harness.runtime_root,
            high_water_store_id="grant-high-water:v1",
            high_water_durability_receipt_id="sha256:" + "8" * 64,
            witness_store_id=witness.store_id,
            witness_durability_receipt_id=witness.durability_receipt_id,
        ),
    )
    boundary = HighWaterBoundary(high_water)
    return DurableSignerRuntimeGenerationAnchor(
        anchor_root / "generation-anchor.json", allowed_root=anchor_root,
        repo_root=harness.repo_root, anchor_id="reddog-grant:production",
        signer=signing, verifier=signing.verifier,
        high_water_authority=boundary.capability,
        high_water_authority_boundary=boundary,
    )


def _provision(context):
    return provision_signer_runtime_generation(
        nonce="grant-provision-generation-1", ttl_seconds=120, context=context,
    )
