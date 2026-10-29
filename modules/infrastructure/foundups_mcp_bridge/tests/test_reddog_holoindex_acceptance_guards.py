"""Adversarial contracts for isolated RedDog HoloIndex acceptance guards."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from holo_index.repository_state import RepositoryState


EXPECTED_SHA = "a" * 40


def _state(*, sha: str = EXPECTED_SHA, clean: bool = True) -> RepositoryState:
    return RepositoryState(
        head_sha=sha,
        clean=clean,
        state_digest="sha256:" + "b" * 64,
        error="" if clean else "HOLOINDEX_REPOSITORY_DIRTY",
    )


def _model(root: Path, payload: bytes = b"model") -> Path:
    root.mkdir(parents=True)
    for name, value in {
        "config.json": b"{}",
        "model.safetensors": payload,
        "modules.json": b"[]",
        "tokenizer.json": b"{}",
    }.items():
        (root / name).write_bytes(value)
    return root


def test_worktree_guard_requires_clean_same_sha_same_common_dir_and_detached_authority(
    tmp_path: Path,
    ) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_acceptance_guards import (
        validate_acceptance_worktrees,
    )

    candidate = tmp_path / "candidate"
    authority = tmp_path / "authority"
    candidate.mkdir()
    authority.mkdir()
    selection = SimpleNamespace(
        accepted=True,
        selected_root=authority.resolve(),
        workspace_head_sha=EXPECTED_SHA,
        authority_head_sha=EXPECTED_SHA,
        authority_root_digest="sha256:" + "c" * 64,
        workspace_overlay_present=False,
        error="",
    )
    proof = validate_acceptance_worktrees(
        candidate,
        authority,
        expected_sha=EXPECTED_SHA,
        state_reader=lambda _path: _state(),
        selection_resolver=lambda *_args, **_kwargs: selection,
        detached_reader=lambda _path: True,
    )
    assert proof.expected_sha == EXPECTED_SHA
    assert proof.candidate_root_digest.startswith("sha256:")
    assert proof.authority_root_digest == selection.authority_root_digest


def test_runtime_root_guard_accepts_clean_related_checkout_without_head_coupling(
    tmp_path: Path,
) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_acceptance_guards import (
        validate_acceptance_runtime_root,
    )

    candidate = tmp_path / "candidate"
    authority = tmp_path / "authority"
    runtime = tmp_path / "runtime"
    for root in (candidate, authority, runtime):
        root.mkdir()
    common = tmp_path / "common.git"
    runtime_state = _state(sha="d" * 40)
    site_packages = runtime / ".venv" / "Lib" / "site-packages"
    site_packages.mkdir(parents=True)
    executable = SimpleNamespace(path=tmp_path / "python.exe")
    observed: dict[str, object] = {}
    proof = validate_acceptance_runtime_root(
        candidate,
        authority,
        runtime,
        state_reader=lambda _path: runtime_state,
        common_dir_reader=lambda _path: common,
        site_packages_resolver=lambda _path, **kwargs: (
            observed.update(kwargs) or (str(site_packages),)
        ),
        reparse_reader=lambda _path: False,
        process_image_prover=lambda: executable,
    )
    assert proof.runtime_root_digest.startswith("sha256:")
    assert proof.runtime_state_digest == runtime_state.state_digest
    assert proof.site_packages == (str(site_packages),)
    assert proof.base_executable_proof.path == tmp_path / "python.exe"
    assert observed == {"base_executable": executable.path}


@pytest.mark.parametrize(
    "defect",
    ["candidate", "authority", "dirty", "unrelated", "reparse", "missing", "ambiguous", "executable"],
)
def test_runtime_root_guard_rejects_untrusted_dependency_checkout(
    tmp_path: Path, defect: str
) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_acceptance_guards import (
        AcceptanceGuardError,
        validate_acceptance_runtime_root,
    )

    candidate = tmp_path / "candidate"
    authority = tmp_path / "authority"
    runtime = tmp_path / "runtime"
    for root in (candidate, authority, runtime):
        root.mkdir()
    selected = {"candidate": candidate, "authority": authority}.get(defect, runtime)
    common = tmp_path / "common.git"
    unrelated = tmp_path / "unrelated.git"
    site_packages = runtime / ".venv" / "Lib" / "site-packages"
    site_packages.mkdir(parents=True)
    entries = {
        "missing": (),
        "ambiguous": (str(site_packages), str(runtime / "other")),
    }.get(defect, (str(site_packages),))

    with pytest.raises(AcceptanceGuardError):
        validate_acceptance_runtime_root(
            candidate,
            authority,
            selected,
            state_reader=lambda _path: _state(clean=defect != "dirty"),
            common_dir_reader=lambda path: (
                unrelated if defect == "unrelated" and path == selected else common
            ),
            site_packages_resolver=lambda _path, **_kwargs: entries,
            reparse_reader=lambda _path: defect == "reparse",
            process_image_prover=lambda: (
                (_ for _ in ()).throw(ValueError("unproven"))
                if defect == "executable"
                else SimpleNamespace(path=tmp_path / "python.exe")
            ),
        )


@pytest.mark.parametrize("defect", ["dirty", "mismatch", "unrelated", "branch"])
def test_worktree_guard_fails_closed_for_invalid_authority(
    tmp_path: Path, defect: str
) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_acceptance_guards import (
        AcceptanceGuardError,
        validate_acceptance_worktrees,
    )

    candidate = tmp_path / "candidate"
    authority = tmp_path / "authority"
    candidate.mkdir()
    authority.mkdir()
    authority_state = _state(
        sha="d" * 40 if defect == "mismatch" else EXPECTED_SHA,
        clean=defect != "dirty",
    )
    selection = SimpleNamespace(
        accepted=defect != "unrelated",
        selected_root=authority.resolve(),
        workspace_head_sha=EXPECTED_SHA,
        authority_head_sha=authority_state.head_sha,
        authority_root_digest="sha256:" + "c" * 64,
        workspace_overlay_present=False,
        error="AUTHORITY_ROOT_UNRELATED" if defect == "unrelated" else "",
    )
    states = {candidate.resolve(): _state(), authority.resolve(): authority_state}
    with pytest.raises(AcceptanceGuardError):
        validate_acceptance_worktrees(
            candidate,
            authority,
            expected_sha=EXPECTED_SHA,
            state_reader=lambda path: states[path.resolve()],
            selection_resolver=lambda *_args, **_kwargs: selection,
            detached_reader=lambda _path: defect != "branch",
        )


@pytest.mark.parametrize("relation", ["equal", "child", "parent"])
def test_store_guard_rejects_canonical_overlap(tmp_path: Path, relation: str) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_acceptance_guards import (
        AcceptanceGuardError,
        validate_isolated_store_target,
    )

    canonical = tmp_path / "canonical"
    canonical.mkdir()
    target = {
        "equal": canonical,
        "child": canonical / "candidate",
        "parent": tmp_path,
    }[relation]
    with pytest.raises(AcceptanceGuardError):
        validate_isolated_store_target(
            target,
            canonical_store=canonical,
            repo_roots=(tmp_path / "repo",),
        )


def test_store_guard_rejects_existing_and_link_components(tmp_path: Path) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src import (
        reddog_holoindex_acceptance_guards as guards,
    )

    canonical = tmp_path / "canonical"
    canonical.mkdir()
    existing = tmp_path / "existing"
    existing.mkdir()
    with pytest.raises(guards.AcceptanceGuardError):
        guards.validate_isolated_store_target(
            existing, canonical_store=canonical, repo_roots=()
        )
    target = tmp_path / "safe-parent" / "candidate"
    target.parent.mkdir()
    monkey_value = target.parent.resolve()
    real = guards._is_link_or_reparse
    guards._is_link_or_reparse = lambda path, metadata=None: (
        path.resolve(strict=False) == monkey_value or real(path, metadata)
    )
    try:
        with pytest.raises(guards.AcceptanceGuardError):
            guards.validate_isolated_store_target(
                target, canonical_store=canonical, repo_roots=()
            )
    finally:
        guards._is_link_or_reparse = real


def test_store_proof_detects_replacement_after_creation(tmp_path: Path) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_acceptance_guards import (
        AcceptanceGuardError,
        create_isolated_store,
        verify_store_proof,
    )

    canonical = tmp_path / "canonical"
    canonical.mkdir()
    target = tmp_path / "isolated"
    proof = create_isolated_store(target, canonical_store=canonical, repo_roots=())
    target.rmdir()
    target.mkdir()
    with pytest.raises(AcceptanceGuardError):
        verify_store_proof(proof, canonical_store=canonical, repo_roots=())


def test_model_copy_is_sorted_bounded_and_digest_equal(tmp_path: Path) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_acceptance_guards import (
        ModelCopyLimits,
        copy_model_snapshot,
        create_isolated_store,
    )

    canonical = tmp_path / "canonical"
    canonical.mkdir()
    source = _model(tmp_path / "source")
    store = tmp_path / "isolated"
    proof = create_isolated_store(store, canonical_store=canonical, repo_roots=())
    result = copy_model_snapshot(
        source,
        store / "models" / "all-MiniLM-L6-v2",
        store_proof=proof,
        canonical_store=canonical,
        repo_roots=(),
        limits=ModelCopyLimits(max_files=8, max_file_bytes=1024, max_total_bytes=4096),
    )
    assert result.source_digest == result.destination_digest
    assert result.file_count == 4
    assert result.relative_files == tuple(sorted(result.relative_files))


def test_model_copy_rejects_links_special_files_and_bounds(tmp_path: Path) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_acceptance_guards import (
        AcceptanceGuardError,
        ModelCopyLimits,
        copy_model_snapshot,
        create_isolated_store,
    )

    canonical = tmp_path / "canonical"
    canonical.mkdir()
    source = _model(tmp_path / "source", payload=b"x" * 32)
    store = tmp_path / "isolated"
    proof = create_isolated_store(store, canonical_store=canonical, repo_roots=())
    with pytest.raises(AcceptanceGuardError):
        copy_model_snapshot(
            source,
            store / "models" / "all-MiniLM-L6-v2",
            store_proof=proof,
            canonical_store=canonical,
            repo_roots=(),
            limits=ModelCopyLimits(max_files=8, max_file_bytes=8, max_total_bytes=4096),
        )


def test_bounded_digest_rejects_oversize_and_detects_change(tmp_path: Path) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_acceptance_guards import (
        AcceptanceGuardError,
        read_bounded_digest,
    )

    receipt = tmp_path / "receipt.json"
    receipt.write_bytes(b"0123456789")
    with pytest.raises(AcceptanceGuardError):
        read_bounded_digest(receipt, allowed_root=tmp_path, max_bytes=4)
    first = read_bounded_digest(receipt, allowed_root=tmp_path, max_bytes=16)
    receipt.write_bytes(b"changed")
    second = read_bounded_digest(receipt, allowed_root=tmp_path, max_bytes=16)
    assert first.digest != second.digest


def test_atomic_publication_is_bounded_secret_free_and_never_overwrites(
    tmp_path: Path,
) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_acceptance_guards import (
        AcceptanceGuardError,
        atomic_publish_acceptance_receipt,
    )

    target = tmp_path / "acceptance.json"
    payload = {"schema_version": "reddog_holoindex_candidate_acceptance.v1", "verdict": "PASS"}
    atomic_publish_acceptance_receipt(
        target,
        payload,
        allowed_root=tmp_path,
        canonical_store=tmp_path / "canonical",
        repo_roots=(),
        max_bytes=4096,
    )
    assert json.loads(target.read_text(encoding="utf-8")) == payload
    with pytest.raises(AcceptanceGuardError):
        atomic_publish_acceptance_receipt(
            target,
            payload,
            allowed_root=tmp_path,
            canonical_store=tmp_path / "canonical",
            repo_roots=(),
            max_bytes=4096,
        )
    with pytest.raises(AcceptanceGuardError):
        atomic_publish_acceptance_receipt(
            tmp_path / "secret.json",
            {"schema_version": payload["schema_version"], "password": "not-a-real-secret"},
            allowed_root=tmp_path,
            canonical_store=tmp_path / "canonical",
            repo_roots=(),
            max_bytes=4096,
        )


def test_atomic_publication_quarantines_false_pass_when_parent_fsync_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src import (
        reddog_holoindex_acceptance_guards as guards,
        reddog_private_json_publication as publication,
    )

    target = tmp_path / "acceptance.json"
    monkeypatch.setattr(publication, "_fsync_directory", lambda _path: (_ for _ in ()).throw(OSError("boom")))
    with pytest.raises(guards.AcceptanceGuardError) as raised:
        guards.atomic_publish_acceptance_receipt(
            target,
            {"schema_version": guards.ACCEPTANCE_SCHEMA_VERSION, "verdict": "PASS"},
            allowed_root=tmp_path,
            canonical_store=tmp_path / "canonical",
            repo_roots=(),
            max_bytes=4096,
        )
    assert not target.exists()
    orphans = list((tmp_path / ".private-json-orphans").iterdir())
    assert len(orphans) == 1
    assert raised.value.orphan_relative_paths == (
        orphans[0].relative_to(tmp_path).as_posix(),
    )


def test_atomic_publication_never_overwrites_foreign_target_raced_at_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src import (
        reddog_holoindex_acceptance_guards as guards,
        reddog_private_json_publication as publication,
    )

    target = tmp_path / "acceptance.json"
    foreign = b"foreign-receipt\n"
    original_publish = publication._publish_temp_no_replace

    def race_then_publish(temporary, destination, proof):
        Path(destination).write_bytes(foreign)
        return original_publish(temporary, destination, proof)

    monkeypatch.setattr(publication, "_publish_temp_no_replace", race_then_publish)
    with pytest.raises(guards.AcceptanceGuardError) as raised:
        guards.atomic_publish_acceptance_receipt(
            target,
            {"schema_version": guards.ACCEPTANCE_SCHEMA_VERSION, "verdict": "PASS"},
            allowed_root=tmp_path,
            canonical_store=tmp_path / "canonical",
            repo_roots=(),
            max_bytes=4096,
        )
    assert target.read_bytes() == foreign
    assert list(tmp_path.glob(".acceptance.json.*.tmp")) == []
    orphan = tmp_path / raised.value.orphan_relative_paths[0]
    assert json.loads(orphan.read_text(encoding="utf-8"))["verdict"] == "PASS"


def test_publication_failure_quarantines_foreign_target_swapped_after_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src import (
        reddog_holoindex_acceptance_guards as guards,
        reddog_private_json_publication as publication,
    )

    target = tmp_path / "acceptance.json"
    foreign = b"foreign-after-publication\n"

    def swap_then_fail(_parent: Path) -> None:
        target.unlink()
        target.write_bytes(foreign)
        raise OSError("directory flush failed")

    monkeypatch.setattr(publication, "_fsync_directory", swap_then_fail)
    with pytest.raises(guards.AcceptanceGuardError) as raised:
        guards.atomic_publish_acceptance_receipt(
            target,
            {"schema_version": guards.ACCEPTANCE_SCHEMA_VERSION, "verdict": "PASS"},
            allowed_root=tmp_path,
            canonical_store=tmp_path / "canonical",
            repo_roots=(),
            max_bytes=4096,
        )
    assert not target.exists()
    assert (tmp_path / raised.value.orphan_relative_paths[0]).read_bytes() == foreign
    assert list(tmp_path.glob(".acceptance.json.*.tmp")) == []


def test_atomic_publication_primitive_failure_quarantines_owned_temp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src import (
        reddog_holoindex_acceptance_guards as guards,
        reddog_private_json_publication as publication,
    )

    target = tmp_path / "acceptance.json"
    monkeypatch.setattr(
        publication,
        "_publish_temp_no_replace",
        lambda *_args: (_ for _ in ()).throw(OSError("rename/link failed")),
    )
    with pytest.raises(guards.AcceptanceGuardError) as raised:
        guards.atomic_publish_acceptance_receipt(
            target,
            {"schema_version": guards.ACCEPTANCE_SCHEMA_VERSION, "verdict": "PASS"},
            allowed_root=tmp_path,
            canonical_store=tmp_path / "canonical",
            repo_roots=(),
            max_bytes=4096,
        )
    assert not target.exists()
    assert list(tmp_path.glob(".acceptance.json.*.tmp")) == []
    assert (tmp_path / raised.value.orphan_relative_paths[0]).is_file()


def test_atomic_publication_file_fsync_failure_quarantines_owned_temp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src import (
        reddog_holoindex_acceptance_guards as guards,
        reddog_private_json_publication as publication,
    )

    target = tmp_path / "acceptance.json"
    monkeypatch.setattr(
        publication,
        "_write_receipt_temp",
        lambda *_args: (_ for _ in ()).throw(OSError("file flush failed")),
    )
    with pytest.raises(guards.AcceptanceGuardError) as raised:
        guards.atomic_publish_acceptance_receipt(
            target,
            {"schema_version": guards.ACCEPTANCE_SCHEMA_VERSION, "verdict": "PASS"},
            allowed_root=tmp_path,
            canonical_store=tmp_path / "canonical",
            repo_roots=(),
            max_bytes=4096,
        )
    assert not target.exists()
    assert list(tmp_path.glob(".acceptance.json.*.tmp")) == []
    assert (tmp_path / raised.value.orphan_relative_paths[0]).is_file()


def test_atomic_publication_preserves_preexisting_target_bytes(tmp_path: Path) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src import (
        reddog_holoindex_acceptance_guards as guards,
    )

    target = tmp_path / "acceptance.json"
    prior = b"prior-foreign-receipt\n"
    target.write_bytes(prior)
    with pytest.raises(guards.AcceptanceGuardError):
        guards.atomic_publish_acceptance_receipt(
            target,
            {"schema_version": guards.ACCEPTANCE_SCHEMA_VERSION, "verdict": "PASS"},
            allowed_root=tmp_path,
            canonical_store=tmp_path / "canonical",
            repo_roots=(),
            max_bytes=4096,
        )
    assert target.read_bytes() == prior


def test_atomic_publication_pass_occurs_after_file_and_directory_durability(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src import (
        reddog_holoindex_acceptance_guards as guards,
        reddog_private_json_publication as publication,
    )

    events: list[str] = []
    original_write = publication._write_receipt_temp
    original_publish = publication._publish_temp_no_replace
    original_fsync_directory = publication._fsync_directory

    def write_then_record(descriptor, encoded):
        proof = original_write(descriptor, encoded)
        events.append("file_durable")
        return proof

    def publish_then_record(temporary, target, proof):
        original_publish(temporary, target, proof)
        events.append("published_no_replace")

    def fsync_then_record(parent):
        original_fsync_directory(parent)
        events.append("directory_durable")

    monkeypatch.setattr(publication, "_write_receipt_temp", write_then_record)
    monkeypatch.setattr(publication, "_publish_temp_no_replace", publish_then_record)
    monkeypatch.setattr(publication, "_fsync_directory", fsync_then_record)
    target = tmp_path / "acceptance.json"
    returned = guards.atomic_publish_acceptance_receipt(
        target,
        {"schema_version": guards.ACCEPTANCE_SCHEMA_VERSION, "verdict": "PASS"},
        allowed_root=tmp_path,
        canonical_store=tmp_path / "canonical",
        repo_roots=(),
        max_bytes=4096,
    )
    assert returned == target
    assert events == [
        "file_durable",
        "published_no_replace",
        "directory_durable",
    ]


def test_quarantine_collision_preserves_source_and_existing_orphan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src import (
        reddog_private_json_publication as publication,
    )

    source = tmp_path / "active.json"
    source.write_bytes(b"source")
    orphans = tmp_path / "orphans"
    orphans.mkdir()
    collision = orphans / "active-fixed-active.json"
    collision.write_bytes(b"existing")

    with pytest.raises(Exception):
        publication.quarantine_owned_path_no_replace(
            source, allowed_root=tmp_path, orphan_root=orphans,
            label="active", token="fixed", max_bytes=4096,
        )
    assert source.read_bytes() == b"source"
    assert collision.read_bytes() == b"existing"


def test_quarantine_rename_failure_leaves_active_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src import (
        reddog_private_json_publication as publication,
    )

    source = tmp_path / "active.json"
    source.write_bytes(b"source")
    monkeypatch.setattr(
        publication, "_rename_path_no_replace",
        lambda *_args: (_ for _ in ()).throw(OSError("rename denied")),
    )
    with pytest.raises(OSError, match="rename denied"):
        publication.quarantine_owned_path_no_replace(
            source, allowed_root=tmp_path, orphan_root=tmp_path / "orphans",
            label="active", token="fixed", max_bytes=4096,
        )
    assert source.read_bytes() == b"source"


def test_quarantine_fails_closed_on_unsupported_platform(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src import (
        reddog_private_json_publication as publication,
    )

    source = tmp_path / "active.json"
    source.write_bytes(b"source")
    monkeypatch.setattr(publication.os, "name", "posix")
    monkeypatch.setattr(publication.platform, "system", lambda: "Darwin")
    with pytest.raises(Exception, match="ATOMIC_RENAME_UNAVAILABLE"):
        publication._rename_path_no_replace(source, tmp_path / "orphan.json")
    assert source.read_bytes() == b"source"
