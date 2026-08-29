from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import threading

import pytest

from modules.infrastructure.wre_core.scripts.generate_test_registry import (
    build_registry,
    canonical_bytes,
)
from modules.infrastructure.wre_core.src.wre_test_registry import REGISTRY_PATH
from modules.infrastructure.wre_core.src.wre_test_registry_differential_plan_runtime import (
    FAIL_CHANGED_PATHS,
    FAIL_DEPENDENCIES,
    FAIL_LINEAGE,
    FAIL_REPOSITORY,
    FAIL_REQUEST,
    produce_registry_scope_projection,
)
from modules.infrastructure.wre_core.src import wre_git_bounded_io
from modules.infrastructure.wre_core.src import wre_git_process_io
from modules.infrastructure.wre_core.src import wre_test_registry_git_binding
from modules.infrastructure.wre_core.src import wre_test_registry_scope_plan

def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True,
        check=True, timeout=30,
    )
    return result.stdout.strip()


def _write_registry(repo: Path) -> None:
    paths = tuple(sorted(
        path.relative_to(repo).as_posix() for path in repo.rglob("test_*.py")
        if path.is_file()
    ))
    target = repo / REGISTRY_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(canonical_bytes(build_registry(repo, test_paths=paths)))


def _commit(repo: Path, message: str) -> str:
    _write_registry(repo)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


@pytest.fixture
def repository(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "tests@example.invalid")
    _git(repo, "config", "user.name", "WRE Tests")
    (repo / ".gitattributes").write_text(
        f"/{REGISTRY_PATH} text eol=lf\n", encoding="ascii"
    )
    (repo / "requirements-dev.txt").write_text("pytest==9.0.2\n", encoding="ascii")
    test = repo / "modules/example/demo/tests/test_existing.py"
    test.parent.mkdir(parents=True)
    test.write_text("def test_existing(): assert True\n", encoding="ascii")
    source = repo / "modules/example/demo/src/api.py"
    source.parent.mkdir()
    source.write_text("VALUE = 1\n", encoding="ascii")
    return repo, _commit(repo, "base")


def _projection_input(
    impact: str = "ISOLATED", **overrides: object,
) -> dict[str, object]:
    value: dict[str, object] = {
        "impact_class": impact, "max_shards_per_batch": 32,
        "max_total_shards": 512, "max_files": 4096,
        "omitted_scope_rationale": "planning only",
        "wsp15_allocation_receipt_id": "wsp15-test",
        "wsp15_allocation_receipt_digest": "sha256:" + "a" * 64,
        "runner_digest": "sha256:" + "b" * 64,
        "environment_digest": "sha256:" + "c" * 64,
        "base_lineage_receipt_digest": "sha256:" + "f" * 64,
        "dependency_evidence_fresh": True,
        "holoindex_evidence_fresh": True,
        "protected_authority_surface": False,
        "release_candidate": False,
        "periodic_health_audit": False,
        "security_closure_required": False,
        "held_out_closure_required": False,
    }
    value.update(overrides)
    return value


def _request(base: str, head: str, changed: list[str], **policy: object) -> dict:
    paths = list(changed)
    if any(Path(path).name.startswith("test_") for path in paths):
        paths.append(REGISTRY_PATH)
    return {
        "base_sha": base, "head_sha": head,
        "expected_changed_paths": sorted(paths),
        "projection_input": _projection_input(**policy),
    }


def _plan(repo: Path, request: dict):
    return produce_registry_scope_projection(
        request, worktree_path=repo, repo_root=repo,
    )


def test_added_test_produces_non_executing_scope_projection(repository) -> None:
    repo, base = repository
    changed = "modules/example/demo/tests/test_added.py"
    (repo / changed).write_text("def test_added(): assert True\n", encoding="ascii")
    head = _commit(repo, "candidate")
    result = _plan(repo, _request(base, head, [changed]))
    assert result.projected is True
    assert changed in result.evidence["candidate"]["paths"]
    assert result.evidence["test_execution_performed"] is False
    assert result.evidence["candidate_code_executed"] is False
    assert result.evidence["verification_capability_issued"] is False
    assert result.evidence["execution_status"] == "BLOCKED_BY_OS_ISOLATED_RUNNER"
    impact_plan = result.evidence["test_impact_plan"]
    assert impact_plan["schema_version"] == "wre_test_impact_plan.v1"
    assert impact_plan["runner_digest"] == "sha256:" + "b" * 64
    assert impact_plan["environment_digest"] == "sha256:" + "c" * 64
    assert impact_plan["dependency_lock_digest"] == (
        result.evidence["recognized_dependency_digest"]
    )
    assert impact_plan["selection_args_digest"].startswith("sha256:")


def test_planner_never_executes_candidate_module_scope_code(repository) -> None:
    repo, base = repository
    marker = repo.parent / "host-marker.txt"
    changed = "modules/example/demo/tests/test_host_write.py"
    (repo / changed).write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).write_text('bad')\n",
        encoding="utf-8",
    )
    head = _commit(repo, "host write source")
    result = _plan(repo, _request(base, head, [changed]))
    assert result.projected is False
    assert marker.exists() is False
    assert result.rejection_reasons == ("FAIL_QUARANTINED_CHANGED_TEST",)


def test_quarantined_to_collectable_transition_still_rejects(repository) -> None:
    repo, _initial = repository
    changed = "modules/example/demo/tests/test_transition.py"
    target = repo / changed
    target.write_text(
        "from pathlib import Path\nPath('outside').write_text('bad')\n",
        encoding="ascii",
    )
    base = _commit(repo, "quarantined base")
    target.write_text("def test_transition(): assert True\n", encoding="ascii")
    head = _commit(repo, "collectable candidate")
    result = _plan(repo, _request(base, head, [changed]))
    assert result.rejection_reasons == ("FAIL_QUARANTINED_CHANGED_TEST",)


def test_forged_registry_projection_is_rejected(repository) -> None:
    repo, base = repository
    changed = "modules/example/demo/tests/test_added.py"
    (repo / changed).write_text("def test_added(): assert True\n", encoding="ascii")
    _commit(repo, "candidate")
    registry = repo / REGISTRY_PATH
    registry.write_bytes((repo / REGISTRY_PATH).read_bytes().replace(b"test_added", b"test_forged"))
    _git(repo, "add", REGISTRY_PATH)
    _git(repo, "commit", "-m", "forge registry")
    forged = _git(repo, "rev-parse", "HEAD")
    result = _plan(repo, _request(base, forged, [changed]))
    assert result.projected is False
    assert result.rejection_reasons == ("FAIL_TEST_REGISTRY_PROJECTION",)


def test_changed_path_substitution_is_rejected(repository) -> None:
    repo, base = repository
    changed = "modules/example/demo/tests/test_added.py"
    (repo / changed).write_text("def test_added(): assert True\n", encoding="ascii")
    head = _commit(repo, "candidate")
    request = _request(base, head, ["modules/example/demo/tests/test_other.py"])
    assert _plan(repo, request).rejection_reasons == (FAIL_CHANGED_PATHS,)


def test_non_string_changed_path_is_rejected(repository) -> None:
    repo, base = repository
    changed = "modules/example/demo/src/api.py"
    (repo / changed).write_text("VALUE = 2\n", encoding="ascii")
    head = _commit(repo, "candidate")
    request = _request(base, head, [changed])
    request["expected_changed_paths"] = [1]
    assert _plan(repo, request).rejection_reasons == (FAIL_CHANGED_PATHS,)


def test_recognized_dependency_change_is_rejected(repository) -> None:
    repo, base = repository
    (repo / "requirements-dev.txt").write_text("pytest==9.0.3\n", encoding="ascii")
    head = _commit(repo, "dependency change")
    request = _request(base, head, ["requirements-dev.txt"], impact="SYSTEMIC")
    assert _plan(repo, request).rejection_reasons == (FAIL_DEPENDENCIES,)


def test_systemic_plan_batches_every_shard_once(repository) -> None:
    repo, base = repository
    changed_tests = []
    for name in ("one", "two", "three"):
        relative = f"modules/example/{name}/tests/test_{name}.py"
        changed_tests.append(relative)
        target = repo / relative
        target.parent.mkdir(parents=True)
        target.write_text(f"def test_{name}(): assert True\n", encoding="ascii")
    marker = repo / "scripts/change.py"
    marker.parent.mkdir()
    marker.write_text("VALUE = 1\n", encoding="ascii")
    head = _commit(repo, "systemic candidate")
    result = _plan(repo, _request(
        base, head, ["scripts/change.py", *changed_tests], impact="SYSTEMIC",
        max_shards_per_batch=2,
    ))
    assert result.projected is True
    shards = result.evidence["candidate"]["shard_ids"]
    batches = result.evidence["candidate"]["batches"]
    assert len(batches) > 1
    assert tuple(item for batch in batches for item in batch) == shards
    assert "." not in result.evidence["candidate"]["paths"]


def test_bounds_and_invalid_policy_reject(repository) -> None:
    repo, base = repository
    changed = "modules/example/demo/tests/test_added.py"
    (repo / changed).write_text("def test_added(): assert True\n", encoding="ascii")
    head = _commit(repo, "candidate")
    bounded = _plan(repo, _request(base, head, [changed], max_files=1))
    invalid = _plan(repo, _request(base, head, [changed], max_shards_per_batch=0))
    assert bounded.rejection_reasons == ("FAIL_TEST_REGISTRY_BOUNDS",)
    assert invalid.rejection_reasons == ("FAIL_TEST_REGISTRY_PROJECTION_INPUT",)


def test_missing_wsp15_and_stale_evidence_fail_or_escalate(repository) -> None:
    repo, base = repository
    changed = "modules/example/demo/tests/test_added.py"
    (repo / changed).write_text("def test_added(): assert True\n", encoding="ascii")
    head = _commit(repo, "candidate")
    missing = _request(base, head, [changed])
    del missing["projection_input"]["wsp15_allocation_receipt_id"]
    stale = _request(base, head, [changed], dependency_evidence_fresh=False)
    assert _plan(repo, missing).rejection_reasons == (
        "FAIL_TEST_REGISTRY_PROJECTION_INPUT",
    )
    result = _plan(repo, stale)
    assert result.projected is True
    assert result.evidence["impact_class"] == "SYSTEMIC"
    assert result.evidence["required_suite_kind"] == "FULL_REPOSITORY"


def test_cross_owner_rename_cannot_be_planned_as_one_module(repository) -> None:
    repo, base = repository
    old = "modules/example/demo/src/api.py"
    new = "modules/example/other/src/api.py"
    (repo / new).parent.mkdir(parents=True)
    _git(repo, "mv", old, new)
    head = _commit(repo, "cross owner rename")
    modular = _plan(repo, _request(base, head, [old, new], impact="MODULAR"))
    systemic = _plan(repo, _request(base, head, [old, new], impact="SYSTEMIC"))
    assert modular.projected is False
    assert systemic.projected is True
    assert systemic.evidence["impact_class"] == "SYSTEMIC"


def test_result_is_immutable_and_request_subclasses_reject(repository) -> None:
    repo, base = repository
    changed = "modules/example/demo/tests/test_added.py"
    (repo / changed).write_text("def test_added(): assert True\n", encoding="ascii")
    head = _commit(repo, "candidate")
    request = _request(base, head, [changed])
    result = _plan(repo, request)
    with pytest.raises(TypeError):
        result.evidence["verification_capability_issued"] = True
    detached = result.to_dict()
    detached["evidence"]["verification_capability_issued"] = True
    assert result.evidence["verification_capability_issued"] is False
    class CustomRequest(dict):
        pass
    custom = produce_registry_scope_projection(
        CustomRequest(request), worktree_path=repo, repo_root=repo,
    )
    assert custom.rejection_reasons == (FAIL_REQUEST,)
    with pytest.raises(TypeError):
        custom.evidence["attacker"] = True


def test_invalid_sha_rejects_before_any_git_process(
    repository, monkeypatch,
) -> None:
    repo, base = repository
    request = _request(base, "--help", ["modules/example/demo/src/api.py"])
    monkeypatch.setattr(
        wre_git_process_io.subprocess, "Popen",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("Git started before SHA validation")
        ),
    )
    assert _plan(repo, request).rejection_reasons == (FAIL_LINEAGE,)


def test_bounded_git_stdout_terminates_at_ceiling(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="bounded_git_output_exceeded"):
        wre_git_bounded_io.run_bounded_stdout(
            (sys.executable, "-c", "import sys;sys.stdout.write('x'*10000)"),
            cwd=tmp_path, max_bytes=100, timeout_s=10,
        )


def test_bounded_git_stdout_supports_bounded_binary_stdin() -> None:
    runtime_root = Path("O:/tmp")
    runtime_root.mkdir(parents=True, exist_ok=True)
    observed = wre_git_bounded_io.run_bounded_stdout(
        (
            sys.executable, "-c",
            "import sys;data=sys.stdin.buffer.read();sys.stdout.buffer.write(data[::-1])",
        ),
        cwd=runtime_root, max_bytes=16, timeout_s=10, stdin_bytes=b"builder",
    )
    assert observed == b"redliub"


def test_bounded_git_stdin_ceiling_rejects_before_process(monkeypatch) -> None:
    runtime_root = Path("O:/tmp")
    runtime_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(
        wre_git_process_io.subprocess, "Popen",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("process started before stdin ceiling validation")
        ),
    )
    with pytest.raises(ValueError, match="bounded_git_output_configuration_invalid"):
        wre_git_bounded_io.run_bounded_stdout(
            (sys.executable, "-c", "pass"), cwd=runtime_root,
            max_bytes=1, timeout_s=1, stdin_bytes=b"x" * (8 * 1024 * 1024 + 1),
        )


def test_bounded_git_stdin_tolerates_early_child_exit() -> None:
    runtime_root = Path("O:/tmp")
    runtime_root.mkdir(parents=True, exist_ok=True)
    observed = wre_git_bounded_io.run_bounded_stdout(
        (sys.executable, "-c", "pass"), cwd=runtime_root,
        max_bytes=1, timeout_s=10, stdin_bytes=b"x" * (1024 * 1024),
    )
    assert observed == b""


def test_bounded_git_stdin_timeout_leaves_no_io_threads() -> None:
    runtime_root = Path("O:/tmp")
    runtime_root.mkdir(parents=True, exist_ok=True)
    with pytest.raises(subprocess.TimeoutExpired):
        wre_git_bounded_io.run_bounded_stdout(
            (sys.executable, "-c", "import time;time.sleep(30)"),
            cwd=runtime_root, max_bytes=1, timeout_s=1,
            stdin_bytes=b"x" * (8 * 1024 * 1024),
        )
    assert not any(
        thread.name in {"wre-git-stdin", "wre-git-stdout"}
        for thread in threading.enumerate()
    )


def test_bounded_git_output_ceiling_terminates_concurrent_stdin() -> None:
    runtime_root = Path("O:/tmp")
    runtime_root.mkdir(parents=True, exist_ok=True)
    with pytest.raises(ValueError, match="bounded_git_output_exceeded"):
        wre_git_bounded_io.run_bounded_stdout(
            (
                sys.executable, "-c",
                "import sys;sys.stdout.buffer.write(b'x'*10000);sys.stdout.flush()",
            ),
            cwd=runtime_root, max_bytes=100, timeout_s=10,
            stdin_bytes=b"y" * (8 * 1024 * 1024),
        )


def test_repository_mismatch_and_git_failure_reject(
    repository, tmp_path: Path, monkeypatch,
) -> None:
    repo, base = repository
    changed = "modules/example/demo/tests/test_added.py"
    (repo / changed).write_text("def test_added(): assert True\n", encoding="ascii")
    head = _commit(repo, "candidate")
    request = _request(base, head, [changed])
    other = tmp_path / "other"
    other.mkdir()
    _git(other, "init")
    mismatch = produce_registry_scope_projection(
        request, worktree_path=repo, repo_root=other,
    )
    assert mismatch.rejection_reasons == (FAIL_REPOSITORY,)
    monkeypatch.setattr(
        wre_test_registry_git_binding.subprocess, "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            subprocess.TimeoutExpired("git", 1)
        ),
    )
    assert _plan(repo, request).rejection_reasons == (FAIL_LINEAGE,)


def test_registry_size_rejects_before_read(repository, monkeypatch) -> None:
    repo, _base = repository
    monkeypatch.setattr(wre_test_registry_scope_plan, "MAX_REGISTRY_BYTES", 1)
    original = Path.read_bytes
    def guarded(path: Path) -> bytes:
        if path.as_posix().endswith(REGISTRY_PATH):
            raise AssertionError("registry read before size check")
        return original(path)
    monkeypatch.setattr(Path, "read_bytes", guarded)
    with pytest.raises(ValueError, match="test_registry_size_exceeded"):
        wre_test_registry_scope_plan._verified_registry(repo)


def test_first_test_for_new_owner_is_plannable(repository) -> None:
    repo, base = repository
    changed = "modules/example/new_owner/tests/test_first.py"
    target = repo / changed
    target.parent.mkdir(parents=True)
    target.write_text("def test_first(): assert True\n", encoding="ascii")
    head = _commit(repo, "new owner")
    result = _plan(repo, _request(base, head, [changed]))
    assert result.projected is True
    assert result.evidence["base"]["shard_ids"] == ()
    assert result.evidence["candidate"]["paths"] == (changed,)
