#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for the FoundUp LIVE scaffold writer.

Slice: FOUNDUP_SCAFFOLD_WRITER_LIVE_PHASE1
WSP:   49, 50, 97, 109

A FakeRunner is injected everywhere -- NO real git/gh/worktree/PR executes in CI.
pAccess (paccess_001) is used ONLY as the acceptance fixture.
"""

from __future__ import annotations

import ast
import json
import sys
import types
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.reddog_wre_execution_valve import (
    ExecutionValveEnvironment,
)
from modules.foundups.agent.src import foundup_scaffold_writer_live as live
from modules.foundups.agent.src.create_foundup_dryrun import plan_create_foundup_dry_run
from modules.foundups.agent.src.foundup_scaffold_writer_live import (
    _digest,
    run_foundup_scaffold_writer_live,
)

_TOKEN = "SOVEREIGN-DAO-TEST-TOKEN-abc123"


class FakeRunner:
    """Records calls; materializes the worktree dir so the real (hardened) dry-run
    writer can write into it. Never touches git/gh."""

    def __init__(self) -> None:
        self.calls: list = []

    def create_worktree(self, *, worktree_path, branch_name, base_branch):
        self.calls.append(("create_worktree", str(worktree_path), branch_name, base_branch))
        Path(worktree_path).mkdir(parents=True, exist_ok=True)
        return {"ok": True}

    def commit_all(self, *, worktree_path, add_paths, message):
        self.calls.append(("commit_all", str(worktree_path), tuple(add_paths)))
        return {"ok": True}

    def push_branch(self, *, worktree_path, branch_name):
        self.calls.append(("push_branch", str(worktree_path), branch_name))
        return {"ok": True}

    def create_draft_pr(self, *, branch_name, base_branch, title, body):
        self.calls.append(("create_draft_pr", branch_name, base_branch))
        return "https://github.com/FOUNDUPS/Foundups-Agent/pull/9999"

    def cleanup_worktree(self, *, worktree_path):
        self.calls.append(("cleanup_worktree", str(worktree_path)))
        return {"ok": True}


def _envelope(fid: str = "paccess_001") -> dict:
    return {
        "foundup_id": fid,
        "name": "pAccess",
        "tagline": "decentralized agent/crawler access rail",
        "description": "A decentralized agent/crawler access rail FoundUp.",
        "category": "tools",
        "acceptance_criteria": [
            {"observable": "renders", "method": "pytest", "oracle": "200", "pass_condition": "s==200"},
        ],
        "truth_state_map": [{"feature": fid, "marker": "IDEA_ONLY", "evidence": ""}],
    }


def _make_valid(tmp_path: Path, fid: str = "paccess_001"):
    reg = tmp_path / "reg.json"
    reg.write_text(
        '{"schema_version":"1.0.0","last_updated":"2026-07-23T00:00:00Z",'
        '"entities":[]}',
        encoding="utf-8",
    )
    contract = plan_create_foundup_dry_run(_envelope(fid), registry_path=reg).scaffold_contract
    assert contract is not None
    module_path = f"modules/foundups/{fid}"
    packet = {
        "foundup_id": fid,
        "foundup_name": "pAccess",
        "module_path": module_path + "/",
        "target_branch": f"feat/foundup-live-writer-{fid}",
        "requested_operation": "create_foundup",
        "requested_valve_state": "VALVE_OPEN_WORKTREE_CREATE",
        "scaffold_plan_digest": _digest(contract),
        "planned_artifacts": list(contract["scaffold_artifacts"]),
        "planned_artifacts_count": len(contract["scaffold_artifacts"]),
        "allowed_paths": list(contract["allowed_paths"]),
        "denied_paths": list(contract["denied_paths"]),
        "registry_write": False,
        "merge_authority": False,
        "draft_pr_only": True,
        "no_live_write_performed": True,
        "preauth_ready": True,
    }
    fake_main = tmp_path / "fakemain"
    fake_main.mkdir()
    kwargs = dict(
        preauth_packet=packet,
        scaffold_contract=contract,
        supplied_packet_digest=_digest(packet),
        sovereign_token=_TOKEN,
        valve_env=ExecutionValveEnvironment(
            valve_worktree_create_enabled=True, sovereign_worktree_token=_TOKEN,
        ),
        runner=FakeRunner(),
        worktree_path=tmp_path / "worktree",
        repo_root=fake_main,
    )
    return kwargs, packet, contract


def _resign(kwargs, packet):
    kwargs["supplied_packet_digest"] = _digest(packet)
    return kwargs


# 1 + 2 ---------------------------------------------------------------------- #
def test_valid_paccess_writes_only_planned_and_draft_pr(tmp_path: Path) -> None:
    kwargs, packet, contract = _make_valid(tmp_path)
    r = run_foundup_scaffold_writer_live(**kwargs)
    assert r.ok is True, r.rejection_reason
    assert r.written_artifacts_count == 14
    assert sorted(r.written_artifacts) == sorted(contract["scaffold_artifacts"])
    # Materialized on disk in the isolated worktree only.
    assert (tmp_path / "worktree" / "modules" / "foundups" / "paccess_001" / "foundup_manifest.json").exists()
    assert not (tmp_path / "fakemain" / "modules").exists()  # main untouched
    # Draft PR only.
    assert r.draft_pr_url and "pull/" in r.draft_pr_url
    assert r.merge_performed is False and r.main_mutated is False and r.registry_mutated is False
    pr = [x for x in r.receipts if x["step"] == "draft_pr_created"][0]
    assert pr["draft"] is True and pr["ready"] is False and pr["merged"] is False
    steps = {x["step"] for x in r.receipts}
    for req in ("preauth_verified", "valve_opened", "worktree_created", "write_completed",
                "validation_completed", "draft_pr_created", "cleanup_planned"):
        assert req in steps, f"missing receipt: {req}"


# 3 -------------------------------------------------------------------------- #
def test_missing_sovereign_token_rejects(tmp_path: Path) -> None:
    kwargs, packet, _ = _make_valid(tmp_path)
    kwargs["sovereign_token"] = ""
    r = run_foundup_scaffold_writer_live(**kwargs)
    assert r.ok is False and r.rejection_code == "FAIL_SOVEREIGN_TOKEN"


# 4 -------------------------------------------------------------------------- #
def test_closed_valve_rejects(tmp_path: Path) -> None:
    kwargs, packet, _ = _make_valid(tmp_path)
    kwargs["valve_env"] = ExecutionValveEnvironment(
        valve_worktree_create_enabled=False, sovereign_worktree_token=_TOKEN,
    )
    r = run_foundup_scaffold_writer_live(**kwargs)
    assert r.ok is False and r.rejection_code == "FAIL_VALVE_NOT_OPEN"


# 5 -------------------------------------------------------------------------- #
def test_wrong_preauth_digest_rejects(tmp_path: Path) -> None:
    kwargs, packet, _ = _make_valid(tmp_path)
    kwargs["supplied_packet_digest"] = "sha256:deadbeef"
    r = run_foundup_scaffold_writer_live(**kwargs)
    assert r.ok is False and r.rejection_code == "FAIL_PREAUTH_DIGEST_MISMATCH"


# 6 -------------------------------------------------------------------------- #
def test_existing_target_path_rejects(tmp_path: Path) -> None:
    kwargs, packet, _ = _make_valid(tmp_path)
    (kwargs["repo_root"] / "modules" / "foundups" / "paccess_001").mkdir(parents=True)
    r = run_foundup_scaffold_writer_live(**kwargs)
    assert r.ok is False and r.rejection_code == "FAIL_MODULE_EXISTS"


# 7 -------------------------------------------------------------------------- #
def test_path_traversal_rejects(tmp_path: Path) -> None:
    kwargs, packet, contract = _make_valid(tmp_path)
    contract["scaffold_artifacts"].append("modules/foundups/paccess_001/../../../etc/x")
    packet["scaffold_plan_digest"] = _digest(contract)
    packet["planned_artifacts"] = list(contract["scaffold_artifacts"])
    _resign(kwargs, packet)
    r = run_foundup_scaffold_writer_live(**kwargs)
    assert r.ok is False and r.rejection_code == "FAIL_PATH_TRAVERSAL"


# 8 + 10 --------------------------------------------------------------------- #
@pytest.mark.parametrize("bad", [
    "modules/foundups/paccess_001/.env",
    "modules/foundups/paccess_001/public/route.py",
    "modules/foundups/paccess_001/api/route.py",
])
def test_denied_and_route_paths_reject(tmp_path: Path, bad: str) -> None:
    kwargs, packet, contract = _make_valid(tmp_path)
    contract["scaffold_artifacts"].append(bad)
    packet["scaffold_plan_digest"] = _digest(contract)
    packet["planned_artifacts"] = list(contract["scaffold_artifacts"])
    _resign(kwargs, packet)
    r = run_foundup_scaffold_writer_live(**kwargs)
    assert r.ok is False and r.rejection_code == "FAIL_DENIED_PATH"


def test_out_of_scope_artifact_rejects(tmp_path: Path) -> None:
    kwargs, packet, contract = _make_valid(tmp_path)
    contract["scaffold_artifacts"].append("modules/foundups/other_foundup/x.py")
    packet["scaffold_plan_digest"] = _digest(contract)
    packet["planned_artifacts"] = list(contract["scaffold_artifacts"])
    _resign(kwargs, packet)
    r = run_foundup_scaffold_writer_live(**kwargs)
    assert r.ok is False and r.rejection_code == "FAIL_PATH_OUT_OF_SCOPE"


# 9 -------------------------------------------------------------------------- #
def test_registry_write_request_rejects(tmp_path: Path) -> None:
    kwargs, packet, _ = _make_valid(tmp_path)
    packet["registry_write"] = True
    _resign(kwargs, packet)
    r = run_foundup_scaffold_writer_live(**kwargs)
    assert r.ok is False and r.rejection_code == "FAIL_PREAUTH_ATTESTATION"


def test_merge_authority_request_rejects(tmp_path: Path) -> None:
    kwargs, packet, _ = _make_valid(tmp_path)
    packet["merge_authority"] = True
    _resign(kwargs, packet)
    r = run_foundup_scaffold_writer_live(**kwargs)
    assert r.ok is False and r.rejection_code == "FAIL_PREAUTH_ATTESTATION"


# 11 + 12 -------------------------------------------------------------------- #
def test_extra_artifact_rejects_and_cleans_up(tmp_path: Path) -> None:
    kwargs, packet, contract = _make_valid(tmp_path)
    contract["scaffold_artifacts"].append("modules/foundups/paccess_001/extra_unplanned.txt")
    packet["scaffold_plan_digest"] = _digest(contract)
    packet["planned_artifacts"] = list(contract["scaffold_artifacts"])
    _resign(kwargs, packet)
    r = run_foundup_scaffold_writer_live(**kwargs)
    assert r.ok is False
    assert r.rejection_code in ("FAIL_WRITE_REJECTED", "FAIL_PLAN_ARTIFACT_MISMATCH")
    # Guard 15: cleanup plan + cleanup receipt after a post-worktree failure.
    assert r.cleanup_plan
    assert any(x["step"] == "cleanup_planned" for x in r.receipts)
    assert any(c[0] == "cleanup_worktree" for c in kwargs["runner"].calls)


def test_missing_artifact_rejects(tmp_path: Path) -> None:
    kwargs, packet, contract = _make_valid(tmp_path)
    contract["scaffold_artifacts"] = list(contract["scaffold_artifacts"])[:-1]
    packet["scaffold_plan_digest"] = _digest(contract)
    packet["planned_artifacts"] = list(contract["scaffold_artifacts"])
    _resign(kwargs, packet)
    r = run_foundup_scaffold_writer_live(**kwargs)
    assert r.ok is False


# 13 + 14 -------------------------------------------------------------------- #
def test_worktree_equals_main_rejects(tmp_path: Path) -> None:
    kwargs, packet, _ = _make_valid(tmp_path)
    kwargs["worktree_path"] = kwargs["repo_root"]  # worktree == main checkout
    r = run_foundup_scaffold_writer_live(**kwargs)
    assert r.ok is False and r.rejection_code == "FAIL_WORKTREE_INSIDE_MAIN"


def test_worktree_inside_main_rejects(tmp_path: Path) -> None:
    kwargs, packet, _ = _make_valid(tmp_path)
    kwargs["worktree_path"] = kwargs["repo_root"] / "nested" / "wt"
    r = run_foundup_scaffold_writer_live(**kwargs)
    assert r.ok is False and r.rejection_code == "FAIL_WORKTREE_INSIDE_MAIN"


def test_mispointed_repo_root_cannot_place_worktree_in_true_main(tmp_path: Path) -> None:
    """A mis-pointed repo_root must NOT let a worktree land inside the TRUE repo:
    Guard 8 anchors on the union of the supplied repo AND the sentinel-checked root."""
    from modules.foundups.agent.src.foundup_scaffold_writer_live import _default_repo_root

    kwargs, packet, _ = _make_valid(tmp_path)  # repo_root is a decoy tmp dir
    true_wt = _default_repo_root() / "__pytest_live_writer_must_never_exist__"
    kwargs["worktree_path"] = true_wt
    r = run_foundup_scaffold_writer_live(**kwargs)
    assert r.ok is False and r.rejection_code == "FAIL_WORKTREE_INSIDE_MAIN"
    assert not true_wt.exists()  # rejected before any runner call
    assert not any(c[0] == "create_worktree" for c in kwargs["runner"].calls)


def test_relative_worktree_path_rejects(tmp_path: Path) -> None:
    """A relative worktree_path resolves differently at guard time (orchestration cwd)
    vs runner time (repo_root); must be refused before any runner call."""
    kwargs, packet, _ = _make_valid(tmp_path)
    kwargs["worktree_path"] = Path("escape_wt")  # relative
    r = run_foundup_scaffold_writer_live(**kwargs)
    assert r.ok is False and r.rejection_code == "FAIL_WORKTREE_NOT_ABSOLUTE"
    assert not any(c[0] == "create_worktree" for c in kwargs["runner"].calls)


def test_create_worktree_failure_triggers_cleanup(tmp_path: Path) -> None:
    """A create that fails (git may have partially created) must still attempt cleanup."""
    kwargs, packet, _ = _make_valid(tmp_path)

    class _FailingCreate(FakeRunner):
        def create_worktree(self, *, worktree_path, branch_name, base_branch):
            self.calls.append(("create_worktree", str(worktree_path)))
            return {"ok": False}  # git may have partially materialized before failing

    kwargs["runner"] = _FailingCreate()
    r = run_foundup_scaffold_writer_live(**kwargs)
    assert r.ok is False and r.rejection_code == "FAIL_WORKTREE_CREATE"
    assert any(c[0] == "cleanup_worktree" for c in kwargs["runner"].calls)


def test_protected_branch_target_rejects(tmp_path: Path) -> None:
    kwargs, packet, _ = _make_valid(tmp_path)
    packet["target_branch"] = "main"
    _resign(kwargs, packet)
    r = run_foundup_scaffold_writer_live(**kwargs)
    assert r.ok is False and r.rejection_code == "FAIL_PROTECTED_BRANCH_TARGET"


def test_exception_after_worktree_triggers_cleanup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """An exception during materialize (after worktree creation) must fail closed AND
    invoke cleanup + a rollback receipt -- never leave an orphaned worktree."""
    import modules.foundups.agent.src.scaffold_writer_dryrun as writer_mod

    def _boom(*a, **k):
        raise RuntimeError("simulated mid-write failure")

    monkeypatch.setattr(writer_mod, "materialize_scaffold_dry_run", _boom)
    kwargs, packet, _ = _make_valid(tmp_path)
    r = run_foundup_scaffold_writer_live(**kwargs)
    assert r.ok is False and r.rejection_code == "FAIL_LIVE_WRITE_EXCEPTION"
    assert r.cleanup_plan
    assert any(x["step"] == "cleanup_planned" for x in r.receipts)
    assert any(c[0] == "cleanup_worktree" for c in kwargs["runner"].calls)


# 16 ------------------------------------------------------------------------- #
def test_receipts_on_reject_path(tmp_path: Path) -> None:
    kwargs, packet, _ = _make_valid(tmp_path)
    kwargs["sovereign_token"] = ""
    r = run_foundup_scaffold_writer_live(**kwargs)
    assert any(x["step"] == "rejected" for x in r.receipts)
    assert any(x["step"] == "cleanup_planned" for x in r.receipts)  # even with no worktree


# 17 ------------------------------------------------------------------------- #
def test_orchestration_module_has_no_shell_git_calls() -> None:
    src = Path(live.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    imported: list = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            imported += [a.name for a in n.names]
        elif isinstance(n, ast.ImportFrom):
            imported.append(n.module or "")
    # Authoritative check: the orchestration imports NO execution/shell module, so it
    # cannot run git/gh/subprocess directly -- every side effect is delegated to the
    # injected runner (the approved helper worktree_pr_runner.py owns subprocess).
    forbidden = {"subprocess", "os", "pty", "sh", "importlib", "git", "shutil"}
    assert not (set(imported) & forbidden), f"orchestration must delegate side effects: {set(imported) & forbidden}"
    # Builtin dynamic-dispatch primitives (need no import) are denied by name.
    called = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
            called.add(n.func.id)
    assert not (called & {"__import__", "eval", "exec", "getattr", "compile"}), \
        f"orchestration uses a dynamic-dispatch primitive: {called & {'__import__','eval','exec','getattr','compile'}}"


# 18 ------------------------------------------------------------------------- #
def test_no_secrets_in_result_or_receipts(tmp_path: Path) -> None:
    kwargs, packet, _ = _make_valid(tmp_path)
    r = run_foundup_scaffold_writer_live(**kwargs)
    assert r.ok is True
    blob = json.dumps(r.to_dict(), default=str)
    assert _TOKEN not in blob, "sovereign token leaked into result/receipts"


def test_preseeded_worktree_out_of_scope_rejected(tmp_path: Path) -> None:
    """A pre-seeded worktree (out-of-scope content under the target module path) must
    be refused -- the writer validates the actual on-disk tree, never blindly commits."""
    kwargs, packet, _ = _make_valid(tmp_path)

    class _SeedingRunner(FakeRunner):
        def create_worktree(self, *, worktree_path, branch_name, base_branch):
            r = super().create_worktree(
                worktree_path=worktree_path, branch_name=branch_name, base_branch=base_branch,
            )
            junk = Path(worktree_path) / "modules" / "foundups" / "paccess_001" / "smuggled.txt"
            junk.parent.mkdir(parents=True, exist_ok=True)
            junk.write_text("out-of-scope", encoding="utf-8")
            return r

    kwargs["runner"] = _SeedingRunner()
    r = run_foundup_scaffold_writer_live(**kwargs)
    assert r.ok is False
    assert r.rejection_code in ("FAIL_WORKTREE_NOT_CLEAN", "FAIL_PLAN_ARTIFACT_MISMATCH")
    assert any(c[0] == "cleanup_worktree" for c in kwargs["runner"].calls)


def test_commit_scoped_to_module_path(tmp_path: Path) -> None:
    """The commit stages ONLY the module path (never `git add -A`)."""
    kwargs, packet, _ = _make_valid(tmp_path)
    r = run_foundup_scaffold_writer_live(**kwargs)
    assert r.ok is True
    commit_calls = [c for c in kwargs["runner"].calls if c[0] == "commit_all"]
    assert commit_calls and commit_calls[0][2] == ("modules/foundups/paccess_001",)


# real runner: draft-PR-only, no ready/merge (subprocess fully mocked -- no real git/gh)
def test_real_runner_create_draft_pr_only(monkeypatch: pytest.MonkeyPatch) -> None:
    import modules.foundups.agent.src.worktree_pr_runner as wr

    captured: list = []

    class _Proc:
        returncode = 0
        stdout = "https://github.com/FOUNDUPS/Foundups-Agent/pull/1"
        stderr = ""

    monkeypatch.setattr(wr.subprocess, "run", lambda argv, **kw: (captured.append(argv), _Proc())[1])
    runner = wr.RealWorktreeRunner(repo_root=Path("O:/Foundups-Agent"))
    url = runner.create_draft_pr(branch_name="feat/x", base_branch="main", title="t", body="b")

    assert "pull/" in url
    argv = captured[-1]
    assert argv[:3] == ["gh", "pr", "create"] and "--draft" in argv
    assert "ready" not in argv and "merge" not in argv
    # The runner exposes NO ready/merge capability at all.
    assert not any(hasattr(runner, m) for m in ("mark_ready", "ready", "merge", "merge_pr"))


def test_real_runner_mutating_git_uses_worktree_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import modules.foundups.agent.src.worktree_pr_runner as wr

    repo = tmp_path / "repo"
    worktree = tmp_path / "worker-wt"
    repo.mkdir()
    worktree.mkdir()
    captured: list = []

    class _Proc:
        returncode = 0
        stdout = ""
        stderr = ""

    def _run(argv, **kw):
        captured.append((argv, kw))
        return _Proc()

    monkeypatch.setattr(wr.subprocess, "run", _run)
    runner = wr.RealWorktreeRunner(repo_root=repo)

    result = runner.commit_all(
        worktree_path=worktree,
        add_paths=["modules/foundups/paccess_001"],
        message="test",
    )

    assert result["ok"] is True
    assert len(captured) == 2
    assert captured[0][0] == ["git", "add", "--", "modules/foundups/paccess_001"]
    assert captured[1][0] == ["git", "commit", "-m", "test"]
    assert Path(captured[0][1]["cwd"]).resolve() == worktree.resolve()
    assert Path(captured[1][1]["cwd"]).resolve() == worktree.resolve()


def test_real_runner_refuses_shared_repo_cwd_before_subprocess(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import modules.foundups.agent.src.worktree_pr_runner as wr

    repo = tmp_path / "repo"
    repo.mkdir()
    captured: list = []

    def _run(argv, **kw):
        captured.append((argv, kw))
        raise AssertionError("subprocess must not run when worktree path is repo root")

    monkeypatch.setattr(wr.subprocess, "run", _run)
    runner = wr.RealWorktreeRunner(repo_root=repo)

    result = runner.commit_all(
        worktree_path=repo,
        add_paths=["modules/foundups/paccess_001"],
        message="test",
    )

    assert result["ok"] is False
    assert "FAIL_WORKTREE_INSIDE_REPO_ROOT" in result["stderr"]
    assert captured == []


def test_real_runner_refuses_in_repo_worktree_create_before_subprocess(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import modules.foundups.agent.src.worktree_pr_runner as wr

    repo = tmp_path / "repo"
    nested = repo / ".reddog" / "worktrees" / "wo" / "nonce"
    repo.mkdir()
    captured: list = []

    def _run(argv, **kw):
        captured.append((argv, kw))
        raise AssertionError("subprocess must not create an in-repo worktree")

    monkeypatch.setattr(wr.subprocess, "run", _run)
    runner = wr.RealWorktreeRunner(repo_root=repo)

    result = runner.create_worktree(
        worktree_path=nested,
        branch_name="feat/demo",
        base_branch="main",
    )

    assert result["ok"] is False
    assert "FAIL_WORKTREE_INSIDE_REPO_ROOT" in result["stderr"]
    assert captured == []


def test_real_runner_refuses_nested_main_worktree_before_push(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import modules.foundups.agent.src.worktree_pr_runner as wr

    repo = tmp_path / "repo"
    nested = repo / ".reddog" / "worktrees" / "wo" / "nonce"
    nested.mkdir(parents=True)
    captured: list = []

    def _run(argv, **kw):
        captured.append((argv, kw))
        raise AssertionError("subprocess must not run for nested main worktree")

    monkeypatch.setattr(wr.subprocess, "run", _run)
    runner = wr.RealWorktreeRunner(repo_root=repo)

    result = runner.push_branch(worktree_path=nested, branch_name="feat/demo")

    assert result["ok"] is False
    assert "FAIL_WORKTREE_INSIDE_REPO_ROOT" in result["stderr"]
    assert captured == []


# schema-compat: the real preauth packet exposes every field the live writer reads
def test_real_preauth_packet_is_field_compatible(tmp_path: Path) -> None:
    from modules.foundups.agent.src.live_writer_preauth_packet import (
        build_live_writer_preauth_packet,
    )
    reg = tmp_path / "r.json"
    reg.write_text(
        '{"schema_version":"1.0.0","last_updated":"2026-07-23T00:00:00Z",'
        '"entities":[]}',
        encoding="utf-8",
    )
    p = build_live_writer_preauth_packet(
        idea="decentralized agent/crawler access rail",
        foundup_id="paccess_001", foundup_name="pAccess",
        module_path="modules/foundups/paccess_001/",
        target_branch="feat/foundup-live-writer-paccess_001",
        registry_path=reg, sandbox_root=tmp_path / "s",
    ).to_dict()
    for key in ("preauth_ready", "requested_operation", "requested_valve_state",
                "registry_write", "merge_authority", "draft_pr_only", "no_live_write_performed",
                "foundup_id", "module_path", "target_branch", "scaffold_plan_digest",
                "planned_artifacts", "planned_artifacts_count", "allowed_paths", "denied_paths"):
        assert key in p, f"preauth packet missing field the live writer reads: {key}"


# Round-5 regression: Windows device / extended-length prefix worktree escape ---- #
def test_device_prefixed_worktree_rejected_before_runner(tmp_path: Path) -> None:
    r"""A Windows extended-length / device prefix (\\?\, //?/) disables Win32 path
    normalization: is_absolute() is True and .resolve() keeps a distinct anchor, so a
    path physically INSIDE the repo would evade the _is_inside isolation checks. It must
    be refused (FAIL_WORKTREE_DEVICE_PREFIX) BEFORE any runner.create_worktree call."""
    from modules.foundups.agent.src.foundup_scaffold_writer_live import _default_repo_root

    kwargs, packet, _ = _make_valid(tmp_path)
    # Device-prefixed path that physically points INSIDE the true main checkout.
    inside = str(_default_repo_root()).replace("\\", "/")
    kwargs["worktree_path"] = Path("//?/" + inside + "/__pytest_device_prefix_escape__")
    r = run_foundup_scaffold_writer_live(**kwargs)
    assert r.ok is False and r.rejection_code == "FAIL_WORKTREE_DEVICE_PREFIX"
    assert not any(c[0] == "create_worktree" for c in kwargs["runner"].calls)


def test_materializer_device_prefix_output_root_rejected(tmp_path: Path) -> None:
    """Second isolation layer: the materializer itself refuses a device-prefixed
    output_root, so a direct call cannot escape into main via the prefix trick."""
    from modules.foundups.agent.src.scaffold_writer_dryrun import materialize_scaffold_dry_run

    _, _, contract = _make_valid(tmp_path)
    res = materialize_scaffold_dry_run(
        contract,
        output_root=Path("//?/" + str(tmp_path).replace("\\", "/") + "/wt"),
        real_repo_root=tmp_path / "fakemain",
    )
    assert res.ok is False and res.rejection_code == "FAIL_WRITE_TO_MAIN_REPO"


# Round-5 regression: deferred materializer import failure must fail closed pre-write - #
def test_materializer_import_failure_is_pre_side_effect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If the materializer import fails at import time, it must fail closed BEFORE the
    worktree is created -- never orphan a partial worktree. Simulated by replacing the
    cached module with one lacking the symbol so `from ... import ...` raises."""
    broken = types.ModuleType("modules.foundups.agent.src.scaffold_writer_dryrun")
    monkeypatch.setitem(
        sys.modules, "modules.foundups.agent.src.scaffold_writer_dryrun", broken
    )
    kwargs, packet, _ = _make_valid(tmp_path)
    r = run_foundup_scaffold_writer_live(**kwargs)
    assert r.ok is False and r.rejection_code == "FAIL_MATERIALIZER_IMPORT"
    # No side effect: the worktree was never created, so nothing to clean up.
    assert not any(c[0] == "create_worktree" for c in kwargs["runner"].calls)
    assert not any(c[0] == "cleanup_worktree" for c in kwargs["runner"].calls)
