from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from holo_index.repository_state import repository_root_digest
from modules.infrastructure.shared_utilities.runtime_artifact_confined_byte_reader import (
    secure_digest_confined_file_impl,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_replica_plan import (
    QueryReplicaPlanError,
    _PlanDependencies,
    _build_query_replica_activation_plan_for_test,
    build_query_replica_activation_plan,
)


HEAD = "a" * 40
DIGEST_A = "sha256:" + "1" * 64
DIGEST_B = "sha256:" + "2" * 64


def _tree(tmp_path: Path) -> tuple[Path, Path, Path]:
    repo = tmp_path / "repo"
    canonical = tmp_path / "holo"
    model = canonical / "models" / "all-MiniLM-L6-v2"
    snapshots = canonical / "vectors" / "query_snapshots"
    repo.mkdir()
    model.mkdir(parents=True)
    snapshots.mkdir(parents=True)
    (model / "model.bin").write_bytes(b"model")
    (snapshots / "set.bin").write_bytes(b"snapshots")
    return repo, canonical, model


def _binding(repo: Path, *, generation: str = DIGEST_A) -> dict[str, str]:
    return {
        "freshness_generation_id": generation,
        "freshness_receipt_digest": DIGEST_B,
        "repo_head_sha": HEAD,
        "repo_root_digest": repository_root_digest(repo),
    }


def _dependencies(
    repo: Path,
    model: Path,
    *,
    state: object | None = None,
    admissions: list[object] | None = None,
    model_resolver=None,
    digester=secure_digest_confined_file_impl,
) -> _PlanDependencies:
    values = admissions or [
        SimpleNamespace(allowed=True, freshness="CURRENT", binding=_binding(repo)),
        SimpleNamespace(allowed=True, freshness="CURRENT", binding=_binding(repo)),
    ]
    calls = iter(values)
    return _PlanDependencies(
        state_reader=lambda _root: state
        or SimpleNamespace(proven_clean=True, head_sha=HEAD),
        admission=lambda **_kwargs: next(calls),
        model_resolver=model_resolver or (lambda _root, _name, **_kwargs: model),
        digester=digester,
        binding_validator=lambda *_args, **_kwargs: None,
        manifest_validator=lambda *_args, **_kwargs: None,
    )


def _plan(repo: Path, canonical: Path, dependencies: _PlanDependencies):
    return _build_query_replica_activation_plan_for_test(
        canonical_repo_root=repo,
        canonical_store=canonical,
        expected_repo_head_sha=HEAD,
        dependencies=dependencies,
    )


def test_builds_exact_sorted_model_and_snapshot_plan(tmp_path: Path) -> None:
    repo, canonical, model = _tree(tmp_path)
    plan = _plan(repo, canonical, _dependencies(repo, model))

    assert plan.binding.repo_root == repo.resolve()
    assert plan.binding.repo_head_sha == HEAD
    assert plan.binding.generation_id == DIGEST_A
    assert tuple(item.logical_name for item in plan.manifests) == ("model", "snapshots")
    assert plan.manifests[0].replica_relative_root == "models/all-MiniLM-L6-v2"
    assert plan.manifests[1].replica_relative_root == "vectors/query_snapshots"
    assert plan.manifests[0].files[0].relative_path == "model.bin"
    assert plan.manifests[1].files[0].relative_path == "set.bin"
    assert all(item.sha256.startswith("sha256:") for tree in plan.manifests for item in tree.files)


@pytest.mark.parametrize(
    ("state", "code"),
    [
        (SimpleNamespace(proven_clean=False, head_sha=HEAD), "QUERY_REPLICA_PLAN_REPOSITORY_DIRTY"),
        (SimpleNamespace(proven_clean=True, head_sha="b" * 40), "QUERY_REPLICA_PLAN_REPOSITORY_HEAD_MISMATCH"),
    ],
)
def test_rejects_unproven_repository(tmp_path: Path, state: object, code: str) -> None:
    repo, canonical, model = _tree(tmp_path)
    with pytest.raises(QueryReplicaPlanError, match=code):
        _plan(repo, canonical, _dependencies(repo, model, state=state))


def test_rejects_noncurrent_freshness(tmp_path: Path) -> None:
    repo, canonical, model = _tree(tmp_path)
    admissions = [SimpleNamespace(allowed=False, freshness="STALE", binding={})]
    with pytest.raises(QueryReplicaPlanError, match="QUERY_REPLICA_PLAN_FRESHNESS_NOT_CURRENT"):
        _plan(repo, canonical, _dependencies(repo, model, admissions=admissions))


def test_rejects_wrong_freshness_root_binding(tmp_path: Path) -> None:
    repo, canonical, model = _tree(tmp_path)
    value = _binding(repo)
    value["repo_root_digest"] = DIGEST_A
    admissions = [SimpleNamespace(allowed=True, freshness="CURRENT", binding=value)]
    with pytest.raises(QueryReplicaPlanError, match="QUERY_REPLICA_PLAN_FRESHNESS_BINDING_MISMATCH"):
        _plan(repo, canonical, _dependencies(repo, model, admissions=admissions))


def test_rejects_missing_or_outside_model(tmp_path: Path) -> None:
    repo, canonical, model = _tree(tmp_path)
    with pytest.raises(QueryReplicaPlanError, match="QUERY_REPLICA_PLAN_MODEL_UNAVAILABLE"):
        _plan(
            repo,
            canonical,
            _dependencies(repo, model, model_resolver=lambda *_args, **_kwargs: None),
        )
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "model.bin").write_bytes(b"outside")
    with pytest.raises(QueryReplicaPlanError, match="QUERY_REPLICA_PLAN_SOURCE_OUTSIDE_CANONICAL"):
        _plan(
            repo,
            canonical,
            _dependencies(
                repo,
                model,
                model_resolver=lambda *_args, **_kwargs: outside,
            ),
        )


def test_rejects_source_change_during_hashing(tmp_path: Path) -> None:
    repo, canonical, model = _tree(tmp_path)

    def changing_digest(path: Path, **kwargs):
        proof = secure_digest_confined_file_impl(path, **kwargs)
        path.write_bytes(path.read_bytes() + b"changed")
        return proof

    with pytest.raises(QueryReplicaPlanError, match="QUERY_REPLICA_PLAN_SOURCE_CHANGED"):
        _plan(repo, canonical, _dependencies(repo, model, digester=changing_digest))


def test_rejects_same_size_source_change_with_restored_mtime(tmp_path: Path) -> None:
    repo, canonical, model = _tree(tmp_path)

    def changing_digest(path: Path, **kwargs):
        proof = secure_digest_confined_file_impl(path, **kwargs)
        original = path.read_bytes()
        path.write_bytes(b"x" * len(original))
        os.utime(path, ns=(proof.identity.modified_ns, proof.identity.modified_ns))
        return proof

    with pytest.raises(QueryReplicaPlanError, match="QUERY_REPLICA_PLAN_SOURCE_CHANGED"):
        _plan(repo, canonical, _dependencies(repo, model, digester=changing_digest))


def test_rejects_directory_identity_swap_during_hashing(tmp_path: Path) -> None:
    repo, canonical, model = _tree(tmp_path)
    changed = False

    def changing_digest(path: Path, **kwargs):
        nonlocal changed
        proof = secure_digest_confined_file_impl(path, **kwargs)
        if not changed and path.parent == model:
            changed = True
            content = path.read_bytes()
            preserved = model.with_name("preserved-model")
            model.rename(preserved)
            model.mkdir()
            (model / path.name).write_bytes(content)
        return proof

    with pytest.raises(QueryReplicaPlanError, match="QUERY_REPLICA_PLAN_SOURCE_CHANGED"):
        _plan(repo, canonical, _dependencies(repo, model, digester=changing_digest))


def test_rejects_directory_swap_after_second_pass_digest(tmp_path: Path) -> None:
    repo, canonical, model = _tree(tmp_path)
    model_digest_calls = 0

    def changing_digest(path: Path, **kwargs):
        nonlocal model_digest_calls
        proof = secure_digest_confined_file_impl(path, **kwargs)
        if path.parent == model:
            model_digest_calls += 1
            if model_digest_calls == 2:
                preserved = model.with_name("preserved-model")
                model.rename(preserved)
                model.mkdir()
        return proof

    with pytest.raises(QueryReplicaPlanError, match="QUERY_REPLICA_PLAN_SOURCE_CHANGED"):
        _plan(repo, canonical, _dependencies(repo, model, digester=changing_digest))


def test_rejects_duck_typed_limits_before_plan_work(tmp_path: Path) -> None:
    repo, canonical, model = _tree(tmp_path)
    duck_limits = SimpleNamespace(
        max_files=1,
        max_file_bytes=1,
        max_total_bytes=1,
        validate=lambda: None,
    )
    with pytest.raises(QueryReplicaPlanError, match="QUERY_REPLICA_PLAN_LIMITS_INVALID"):
        _build_query_replica_activation_plan_for_test(
            canonical_repo_root=repo,
            canonical_store=canonical,
            expected_repo_head_sha=HEAD,
            limits=duck_limits,
            dependencies=_dependencies(repo, model),
        )


def test_rejects_freshness_change_after_manifest_hashing(tmp_path: Path) -> None:
    repo, canonical, model = _tree(tmp_path)
    admissions = [
        SimpleNamespace(allowed=True, freshness="CURRENT", binding=_binding(repo)),
        SimpleNamespace(
            allowed=True,
            freshness="CURRENT",
            binding=_binding(repo, generation=DIGEST_B),
        ),
    ]
    with pytest.raises(QueryReplicaPlanError, match="QUERY_REPLICA_PLAN_FRESHNESS_CHANGED"):
        _plan(repo, canonical, _dependencies(repo, model, admissions=admissions))


def test_rejects_noncanonical_expected_head(tmp_path: Path) -> None:
    repo, canonical, model = _tree(tmp_path)
    with pytest.raises(QueryReplicaPlanError, match="QUERY_REPLICA_PLAN_HEAD_INVALID"):
        _build_query_replica_activation_plan_for_test(
            canonical_repo_root=repo,
            canonical_store=canonical,
            expected_repo_head_sha="A" * 40,
            dependencies=_dependencies(repo, model),
        )


def _directory_alias(alias: Path, target: Path) -> None:
    try:
        os.symlink(target, alias, target_is_directory=True)
        return
    except OSError:
        pass
    if os.name == "nt":
        result = subprocess.run(
            ["cmd", "/d", "/c", "mklink", "/J", str(alias), str(target)],
            capture_output=True,
            check=False,
        )
        if result.returncode == 0:
            return
    pytest.skip("directory link/junction unavailable on this host")


def test_rejects_model_link_or_junction_provenance(tmp_path: Path) -> None:
    repo, canonical, model = _tree(tmp_path)
    target = canonical / "models" / "target-model"
    model.rename(target)
    _directory_alias(model, target)

    with pytest.raises(Exception, match="PATH_LINK_OR_REPARSE_REJECTED"):
        _plan(repo, canonical, _dependencies(repo, model))


def test_rejects_snapshot_link_or_junction_provenance(tmp_path: Path) -> None:
    repo, canonical, model = _tree(tmp_path)
    snapshots = canonical / "vectors" / "query_snapshots"
    target = snapshots.with_name("target-snapshots")
    snapshots.rename(target)
    _directory_alias(snapshots, target)

    with pytest.raises(Exception, match="PATH_LINK_OR_REPARSE_REJECTED"):
        _plan(repo, canonical, _dependencies(repo, model))


@pytest.mark.parametrize("binding", [3, [], {"freshness_generation_id": True}])
def test_rejects_hostile_freshness_binding_shapes(
    tmp_path: Path, binding: object,
) -> None:
    repo, canonical, model = _tree(tmp_path)
    admissions = [
        SimpleNamespace(allowed=True, freshness="CURRENT", binding=binding)
    ]
    with pytest.raises(QueryReplicaPlanError, match="QUERY_REPLICA_PLAN_FRESHNESS"):
        _plan(repo, canonical, _dependencies(repo, model, admissions=admissions))


def test_public_builder_normalizes_delegated_failures(monkeypatch) -> None:
    import modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_replica_plan as module

    monkeypatch.setattr(
        module,
        "_build_query_replica_activation_plan_for_test",
        lambda **_kwargs: (_ for _ in ()).throw(ValueError("untrusted detail")),
    )
    with pytest.raises(QueryReplicaPlanError, match="QUERY_REPLICA_PLAN_BUILD_FAILED"):
        build_query_replica_activation_plan(
            canonical_repo_root=Path("C:/repo"),
            canonical_store=Path("C:/holo"),
            expected_repo_head_sha=HEAD,
        )


def _full_dependencies(repo: Path, model: Path) -> _PlanDependencies:
    admissions = iter(
        [
            SimpleNamespace(
                allowed=True,
                freshness="CURRENT",
                binding={
                    "freshness_generation_id": "sha256:" + "b" * 64,
                    "freshness_receipt_digest": "sha256:" + "c" * 64,
                    "repo_head_sha": "a" * 40,
                    "repo_root_digest": repository_root_digest(repo),
                },
            )
            for _ in range(2)
        ]
    )
    return _PlanDependencies(
        state_reader=lambda _root: SimpleNamespace(proven_clean=True, head_sha="a" * 40),
        admission=lambda **_kwargs: next(admissions),
        model_resolver=lambda _root, _name, **_kwargs: model,
    )


def test_plan_boundary_runs_real_exact_closure_validators(tmp_path: Path) -> None:
    from modules.infrastructure.foundups_mcp_bridge.tests.test_reddog_holoindex_query_replica import (
        _canonical_fixture_paths,
    )

    canonical, repo, snapshots, model, _relative, _receipt = (
        _canonical_fixture_paths(tmp_path)
    )
    plan = _plan(repo, canonical, _full_dependencies(repo, model))

    assert len(plan.manifests[1].files) == 22
    assert {item.relative_path for item in plan.manifests[1].files} == {
        item.name for item in snapshots.iterdir()
    }


@pytest.mark.parametrize("mutation", ["extra", "missing", "wrong_generation"])
def test_plan_boundary_rejects_invalid_snapshot_closure(
    tmp_path: Path, mutation: str,
) -> None:
    from modules.infrastructure.foundups_mcp_bridge.tests.test_reddog_holoindex_query_replica import (
        _canonical_fixture_paths,
    )

    canonical, repo, snapshots, model, _relative, _receipt = (
        _canonical_fixture_paths(tmp_path)
    )
    if mutation == "extra":
        (snapshots / "extra.bin").write_bytes(b"extra")
    elif mutation == "missing":
        next(path for path in snapshots.iterdir() if path.name.endswith(".rows.jsonl")).unlink()
    else:
        manifest = snapshots / "snapshot_set.json"
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        payload["generation_id"] = "sha256:" + "d" * 64
        manifest.write_text(
            json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
    with pytest.raises(Exception):
        _plan(repo, canonical, _full_dependencies(repo, model))
