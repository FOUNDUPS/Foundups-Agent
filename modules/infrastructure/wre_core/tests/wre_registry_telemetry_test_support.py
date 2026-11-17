"""Independent telemetry fixtures; scanner verdicts are explicitly substituted."""
import copy
import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

from modules.infrastructure.wre_core.src import skill_execution_truth as truth
from modules.infrastructure.wre_core.src import skill_runtime_admission as admission
from modules.infrastructure.wre_core.src import wre_test_registry_differential_plan_runtime as producer
from modules.infrastructure.wre_core.src.skill_manifest_guard import generate_skill_manifest
from modules.infrastructure.wre_core.src.wre_test_registry_impact_binding import bound_test_impact_plan
from modules.infrastructure.wre_core.tests.test_wre_execution_truth import _minimal_orchestrator
from modules.infrastructure.wre_core.tests.test_wre_runtime_admission_truth import _runtime_admission_loader
from modules.infrastructure.wre_core.tests.test_wre_test_registry_differential_plan_runtime import _request
from modules.infrastructure.wre_core.wre_master_orchestrator.src import wre_master_orchestrator as master

SKILL = "auto_test_registry_audit"
RELATIVE = Path("modules/infrastructure/wre_core/skillz") / SKILL / "executor.py"
ROOT = Path(__file__).resolve().parents[4]
FALSE_FLAGS = (
    "repository_authority_verified", "test_execution_performed", "pytest_invoked",
    "candidate_code_executed", "signed_authority_verified", "execution_authority_verified",
    "collector_integrity_verified", "os_isolation_verified", "verification_capability_issued",
)


def _api():
    fn = getattr(truth, "normalize_registry_scope_projection", None)
    assert callable(fn), "registry_scope_normalizer_api_missing"
    return fn


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(value):
    return "sha256:" + hashlib.sha256(_json(value).encode("ascii")).hexdigest()


def _seal(report):
    evidence = report["evidence"]
    evidence.pop("projection_id", None)
    evidence["projection_id"] = "wre_registry_scope_" + _digest(evidence)[7:]
    return report


def _case(projected=True):
    _api()
    request = _request("1" * 40, "2" * 40, ["modules/demo/pkg/src/a.py"], impact="MODULAR")
    if not projected:
        return request, {"projected": False, "rejection_reasons": ("FAIL_TEST_REGISTRY_BOUNDS",), "evidence": {}}
    digest = "sha256:" + "a" * 64
    plan = bound_test_impact_plan(request["projection_input"], base_sha=request["base_sha"],
        head_sha=request["head_sha"], changed_paths=request["expected_changed_paths"],
        suite_scope_digest=digest, dependency_lock_digest=digest, selection_args_digest=digest)
    assert plan is not None, "existing_impact_plan_fixture_invalid"
    side = {"registry_digest": digest, "shard_ids": ["demo-unit"],
        "paths": ["modules/demo/pkg/tests/test_a.py"], "batches": [["demo-unit"]], "plan_digest": digest}
    evidence = {"schema_version": "wre_test_registry_scope_projection.v1",
        "base_sha": request["base_sha"], "head_sha": request["head_sha"],
        "changed_paths": request["expected_changed_paths"].copy(),
        "changed_paths_digest": _digest(request["expected_changed_paths"]),
        "lineage_digest": _digest({"base": request["base_sha"], "head": request["head_sha"]}),
        "worktree_path_digest": digest, "repository_common_dir_digest": digest,
        "recognized_dependency_digest": digest, "recognized_dependency_parity_verified": True,
        "impact_class": "MODULAR", "required_suite_kind": plan["required_suite_kind"],
        "logical_scope_digest": digest, "test_impact_plan": dict(plan),
        "base": copy.deepcopy(side), "candidate": copy.deepcopy(side), "systemic_batched": False,
        "planning_only": True, "execution_status": "BLOCKED_BY_OS_ISOLATED_RUNNER",
        **{name: False for name in FALSE_FLAGS}}
    return request, _seal({"projected": True, "rejection_reasons": (), "evidence": evidence})


def _assert_telemetry(result, projected):
    assert result["success"] is False and result["_effect_evidence"] is False
    assert result["telemetry_completed"] is projected
    assert result["telemetry_status"] == ("projected" if projected else "rejected")
    for key in ("effect_receipts", "steps_completed", "pattern_fidelity", "fidelity_score"):
        assert key not in result


def _executor(root):
    source = ROOT / RELATIVE
    assert source.is_file(), "registry_scope_executor_api_missing"
    target = root / RELATIVE
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(source.read_bytes())
    (target.parent / "SKILLz.md").write_text("# Disposable telemetry skill\n", encoding="utf-8")
    generate_skill_manifest(target.parent, manifest_path=target.parent / "SKILL_MANIFEST.json")
    namespace = {"__file__": str(target), "__name__": "inert_registry_scope_executor"}
    exec(compile(target.read_bytes(), str(target), "exec"), namespace)
    assert callable(namespace.get("execute")), "registry_scope_executor_entry_missing"
    return target, namespace


def _setup(monkeypatch, tmp_path, projected=True):
    request, report = _case(projected)
    target, _ = _executor(tmp_path)
    orchestrator = _minimal_orchestrator(monkeypatch, tmp_path)
    orchestrator.repo_root = tmp_path
    orchestrator.react_mode, orchestrator.react_max_iterations = False, 3
    loader = _runtime_admission_loader(target.parent / "SKILLz.md")
    loader.registry["skills"] = {SKILL: {"promotion_state": "production", "version": "2.3", "intent_type": "TELEMETRY"}}
    loader.get_skill_metadata = lambda _: {"name": SKILL, **loader.registry["skills"][SKILL]}
    loader.load_skill = lambda *_: "# Disposable telemetry skill"
    orchestrator.skills_loader = loader
    orchestrator.wre_skill_scan_required = orchestrator.wre_skill_scan_enforced = True
    orchestrator.wre_skill_scan_always, orchestrator.wre_skill_scan_ttl_sec = False, 900
    orchestrator.wre_skill_scan_max_severity = "medium"
    monkeypatch.setattr(orchestrator, "_ensure_wre_skill_safety", master.WREMasterOrchestrator._ensure_wre_skill_safety.__get__(orchestrator))
    state = SimpleNamespace(master=orchestrator, request=request, report=report, target=target,
        calls=[], scans=[], events=[], forbidden=[], memory=orchestrator.sqlite_memory)
    def scan(**kwargs):
        state.scans.append(kwargs)
        return SimpleNamespace(available=True, passed=True, manifest_passed=True)
    def project(*args, **kwargs):
        state.calls.append((args, kwargs))
        return SimpleNamespace(to_dict=lambda: copy.deepcopy(state.report))
    monkeypatch.setattr(admission, "SKILL_SCANNER_AVAILABLE", True)
    monkeypatch.setattr(admission, "run_skill_scan", scan)
    monkeypatch.setattr(producer, "produce_registry_scope_projection", project)
    state.memory.record_learning_event = lambda **kwargs: state.events.append(kwargs)
    _install_traps(monkeypatch, state)
    return state


def _install_traps(monkeypatch, state):
    def forbidden(*args, **kwargs):
        state.forbidden.append(True)
        raise AssertionError("unexpected downstream execution or learning")
    for name in ("_execute_skill_with_qwen", "evolve_skill"):
        monkeypatch.setattr(state.master, name, forbidden)
    for name in ("validate_step_fidelity", "record_execution"):
        monkeypatch.setattr(state.master.libido_monitor, name, forbidden)
    monkeypatch.setattr(master, "structural_step_output", forbidden)
    monkeypatch.setattr(master, "SkillOutcome", forbidden)
    monkeypatch.setitem(sys.modules, "modules.infrastructure.database.src.agent_db", SimpleNamespace(AgentDB=forbidden))


def _run(state, react=False):
    state.master.react_mode = react
    return state.master.execute_skill(SKILL, "qwen", {"operation": "project_scope", "request": state.request})


def _assert_no_learning(state):
    assert state.forbidden == [] and state.memory.outcomes == []
    assert not {"total_executions", "react_retry_count"}.intersection(state.memory.counters)
