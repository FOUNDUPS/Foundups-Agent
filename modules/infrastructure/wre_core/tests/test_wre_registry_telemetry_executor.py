"""Registry-bound telemetry connection; real producer coverage uses owned Git fixtures."""
import copy
from types import SimpleNamespace

import pytest

from modules.infrastructure.wre_core.src import wre_test_registry_differential_plan_runtime as producer
from modules.infrastructure.wre_core.src.registered_skill_executor import (
    dispatch_registered_skill_executor, skill_bundle_fingerprint,
)
from modules.infrastructure.wre_core.tests.test_wre_execution_truth import _write_executor_bundle
from modules.infrastructure.wre_core.tests.test_wre_test_registry_differential_plan_runtime import (
    REGISTRY_PATH, _commit, _request, repository,
)
from modules.infrastructure.wre_core.tests.wre_registry_telemetry_test_support import (
    FALSE_FLAGS, SKILL, _api, _assert_telemetry, _case, _executor, _json,
)


def _dispatch(target, request, *, skill=SKILL, context=None, fingerprint=None):
    return dispatch_registered_skill_executor(executor_path=target, skill_name=skill,
        input_context=context if context is not None else {"operation": "project_scope", "request": request},
        agent="qwen", admission_fingerprint=fingerprint or skill_bundle_fingerprint(target.parent))


@pytest.mark.parametrize("continuity", [False, True], ids=["plain", "reserved_continuity"])
def test_executor_uses_own_root_once_and_retains_report(monkeypatch, tmp_path, continuity):
    request, report = _case()
    calls = []
    def project(value, **kwargs):
        calls.append((value, kwargs))
        return SimpleNamespace(to_dict=lambda: copy.deepcopy(report))
    monkeypatch.setattr(producer, "produce_registry_scope_projection", project)
    target, namespace = _executor(tmp_path)
    elsewhere = tmp_path / "unrelated_cwd"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    task = {"operation": "project_scope", "request": request, "skill_name": SKILL, "agent": "qwen"}
    if continuity: task["parent_continuity_context"] = object()
    result = namespace["execute"](task)
    assert len(calls) == 1 and calls[0][0] == request
    assert calls[0][1] == {"worktree_path": tmp_path, "repo_root": tmp_path}
    assert _json(result) == _json(report)
    assert target.is_file()


BAD_TASKS = ["root", "command", "receipt", "telemetry_flag", "wrong_operation",
             "missing_operation", "missing_request", "skill_name", "agent"]


@pytest.mark.parametrize("case", BAD_TASKS, ids=BAD_TASKS)
def test_named_dispatch_rejects_caller_extras_without_projection(monkeypatch, tmp_path, case):
    request, report = _case()
    calls = []
    monkeypatch.setattr(producer, "produce_registry_scope_projection",
        lambda *args, **kwargs: calls.append(True) or SimpleNamespace(to_dict=lambda: report))
    target, _ = _executor(tmp_path)
    context = {"operation": "project_scope", "request": request}
    if case == "wrong_operation": context["operation"] = "regenerate"
    elif case == "missing_operation": context.pop("operation")
    elif case == "missing_request": context.pop("request")
    else: context[case] = {"skill_name": SKILL, "agent": "qwen"}.get(case, "caller controlled")
    result = _dispatch(target, request, context=context)
    assert result["success"] is False and result["_effect_evidence"] is False
    assert result.get("telemetry_completed") is not True and calls == []


@pytest.mark.parametrize("projected", [True, False], ids=["projected", "rejected"])
def test_named_manifest_bound_dispatch_normalizes_without_effect_success(monkeypatch, tmp_path, projected):
    request, report = _case(projected)
    calls = []
    monkeypatch.setattr(producer, "produce_registry_scope_projection",
        lambda *args, **kwargs: calls.append(True) or SimpleNamespace(to_dict=lambda: report))
    target, _ = _executor(tmp_path)
    result = _dispatch(target, request)
    _assert_telemetry(result, projected)
    assert _json(result["projection"]) == _json(report) and calls == [True]


def test_named_dispatch_keeps_bundle_binding_and_rejects_unrelated_layout(monkeypatch, tmp_path):
    request, report = _case()
    calls = []
    monkeypatch.setattr(producer, "produce_registry_scope_projection",
        lambda *args, **kwargs: calls.append(True) or SimpleNamespace(to_dict=lambda: report))
    target, _ = _executor(tmp_path)
    admitted = skill_bundle_fingerprint(target.parent)
    source = target.read_text(encoding="utf-8")
    target.write_text(source + "\n# changed after admission\n", encoding="utf-8")
    result = _dispatch(target, request, fingerprint=admitted)
    assert result["success"] is False and calls == []
    unrelated = _write_executor_bundle(tmp_path / "other", source)
    result = _dispatch(unrelated, request)
    assert result["success"] is False and calls == []


def test_other_skill_cannot_opt_into_named_telemetry(tmp_path):
    request, report = _case()
    target = _write_executor_bundle(tmp_path, "def execute(task):\n    return " + repr(report) + "\n")
    result = _dispatch(target, request, skill="other_skill",
        context={"operation": "project_scope", "request": request, "telemetry": True})
    assert result["success"] is False and result["_effect_evidence"] is False
    assert result.get("telemetry_completed") is not True


@pytest.mark.parametrize("fresh", [True, False], ids=["fresh", "stale_systemic"])
def test_real_projection_connection_preserves_flags_registry_and_freshness(repository, fresh):
    _api()
    repo, base = repository
    changed = "modules/example/demo/src/api.py"
    (repo / changed).write_text("VALUE = 2\n", encoding="ascii")
    head = _commit(repo, "candidate source")
    request = _request(base, head, [changed], impact="MODULAR", holoindex_evidence_fresh=fresh)
    registry_before = (repo / REGISTRY_PATH).read_bytes()
    target, _ = _executor(repo)
    result = _dispatch(target, request)
    _assert_telemetry(result, True)
    evidence = result["projection"]["evidence"]
    assert all(evidence[name] is False for name in FALSE_FLAGS)
    assert evidence["planning_only"] is True
    assert request["projection_input"]["holoindex_evidence_fresh"] is fresh
    assert evidence["impact_class"] == ("MODULAR" if fresh else "SYSTEMIC")
    assert evidence["systemic_batched"] is (not fresh)
    if not fresh: assert evidence["required_suite_kind"] == "FULL_REPOSITORY"
    assert (repo / REGISTRY_PATH).read_bytes() == registry_before
