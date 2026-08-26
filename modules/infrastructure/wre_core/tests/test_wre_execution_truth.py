"""Fail-closed execution-truth contracts for the legacy WRE skill path."""

import logging
from pathlib import Path
from types import SimpleNamespace

import pytest

from modules.infrastructure.wre_core.src.libido_monitor import LibidoSignal
from modules.infrastructure.wre_core.src.local_skill_inference import (
    execute_local_skill_inference,
)
from modules.infrastructure.wre_core.src.registered_skill_executor import (
    _has_link_or_reparse_component,
    dispatch_registered_skill_executor,
    skill_bundle_fingerprint,
)
from modules.infrastructure.wre_core.src.skill_execution_truth import (
    stable_json_record,
    structural_step_output,
)
from modules.infrastructure.wre_core.src.skill_manifest_guard import (
    generate_skill_manifest,
)
from modules.infrastructure.wre_core.wre_master_orchestrator.src.wre_master_orchestrator import (
    WREMasterOrchestrator,
)


class _Libido:
    def should_execute(self, **_kwargs):
        return LibidoSignal.ESCALATE

    def validate_step_fidelity(self, **_kwargs):
        return 1.0

    def record_execution(self, **_kwargs):
        return None


class _Memory:
    def __init__(self):
        self.outcomes = []
        self.counters = {}

    def get_active_ab_test(self, _skill_name):
        return None

    def store_outcome(self, outcome):
        self.outcomes.append(outcome)

    def increment_counter(self, name, delta=1):
        self.counters[name] = self.counters.get(name, 0) + delta


def _minimal_orchestrator(monkeypatch, tmp_path):
    orchestrator = object.__new__(WREMasterOrchestrator)
    orchestrator.repo_root = Path(__file__).resolve().parents[4]
    orchestrator.libido_monitor = _Libido()
    orchestrator.sqlite_memory = _Memory()
    orchestrator.react_fidelity_threshold = 0.90
    orchestrator._wre_skill_scan_cache = {}
    monkeypatch.setattr(
        orchestrator,
        "_ensure_wre_skill_safety",
        lambda _skill_name, force=False: (True, "test pass"),
    )
    monkeypatch.setenv("WRE_AGENTIC_RAG", "0")
    monkeypatch.setenv("FOUNDUPS_DB_PATH", str(tmp_path / "foundups.db"))
    return orchestrator


def test_skill_load_failure_stops_before_execution(monkeypatch, tmp_path):
    orchestrator = _minimal_orchestrator(monkeypatch, tmp_path)
    orchestrator.skills_loader = SimpleNamespace(
        load_skill=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            ValueError("unhealthy skill")
        )
    )
    monkeypatch.setattr(
        orchestrator,
        "_try_executor_dispatch",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("executor must not run")
        ),
    )

    result = orchestrator._execute_skill_once(
        "unsafe_skill",
        "qwen",
        {},
        evolve_on_low_fidelity=False,
    )

    assert result["success"] is False
    assert result["blocked"] is True
    assert result["blocked_by"] == "skill_load"
    assert orchestrator.sqlite_memory.outcomes == []


def test_failed_executor_cannot_become_successful_learning_evidence(monkeypatch, tmp_path):
    orchestrator = _minimal_orchestrator(monkeypatch, tmp_path)
    orchestrator.skills_loader = SimpleNamespace(load_skill=lambda *_args: "# Skill")
    monkeypatch.setattr(
        orchestrator,
        "_try_executor_dispatch",
        lambda *_args, **_kwargs: {
            "success": False,
            "output": "failed",
            "steps_completed": 0,
            "failed_at_step": 1,
        },
    )

    result = orchestrator._execute_skill_once(
        "broken_executor",
        "qwen",
        {},
        evolve_on_low_fidelity=False,
    )

    assert result["success"] is False
    assert len(orchestrator.sqlite_memory.outcomes) == 1
    outcome = orchestrator.sqlite_memory.outcomes[0]
    assert outcome.success is False
    assert outcome.outcome_quality == 0.0
    assert outcome.step_count == 0
    assert outcome.failed_at_step == 1


def test_empty_shape_is_not_structural_fidelity_evidence():
    """Synthesized empty keys cannot manufacture structural fidelity."""
    assert structural_step_output({"output": "", "steps_completed": 0}) == {}
    assert structural_step_output({"output": "done", "steps_completed": 1}) == {
        "output": "done",
        "steps_completed": 1,
    }
    assert "record_unavailable" in stable_json_record({"bad": object()})


def test_evolution_does_not_auto_schedule_unbound_ab_runtime(monkeypatch):
    """A generated variation remains stored evidence until governed scheduling."""
    memory = SimpleNamespace(
        recall_failure_patterns=lambda *_args, **_kwargs: [],
        recall_successful_patterns=lambda *_args, **_kwargs: [],
        store_variation=lambda **kwargs: setattr(memory, "variation", kwargs),
        record_learning_event=lambda **kwargs: setattr(memory, "event", kwargs),
    )
    orchestrator = object.__new__(WREMasterOrchestrator)
    orchestrator.sqlite_memory = memory
    monkeypatch.setattr(orchestrator, "_generate_variation_with_qwen", lambda *_args: "# candidate")

    created = orchestrator.evolve_skill(
        skill_name="skill",
        agent="qwen",
        skill_content="# original",
        failed_output={"success": False},
        input_context={},
        current_fidelity=0.2,
    )

    assert memory.variation["skill_name"] == "skill"
    assert memory.event["event_type"] == "variation_created"
    assert not hasattr(memory, "active_ab_test")
    assert created is True


def test_successful_effect_keeps_outcome_quality_unknown(monkeypatch, tmp_path):
    orchestrator = _minimal_orchestrator(monkeypatch, tmp_path)
    orchestrator.skills_loader = SimpleNamespace(load_skill=lambda *_args: "# Skill")
    monkeypatch.setattr(
        orchestrator,
        "_try_executor_dispatch",
        lambda *_args, **_kwargs: {
            "success": True,
            "output": "effect completed",
            "steps_completed": 1,
            "failed_at_step": None,
            "effect_receipts": [{"receipt_id": "effect-1", "effect_type": "test"}],
            "_effect_evidence": True,
        },
    )

    result = orchestrator._execute_skill_once(
        "effect_skill", "qwen", {}, evolve_on_low_fidelity=False
    )

    assert result["success"] is True
    assert orchestrator.sqlite_memory.outcomes[0].outcome_quality == 0.0


def test_executor_resolution_is_adjacent_to_registered_skill(monkeypatch, tmp_path):
    registered = tmp_path / "registered" / "skill"
    registered.mkdir(parents=True)
    skill_file = registered / "SKILLz.md"
    skill_file.write_text("# Bound skill\n", encoding="utf-8")
    executor = registered / "executor.py"
    executor.write_text("def execute(task): return {'success': True}\n", encoding="utf-8")

    decoy = tmp_path / "modules" / "x" / "y" / "skillz" / "bound_skill"
    decoy.mkdir(parents=True)
    (decoy / "executor.py").write_text("raise RuntimeError\n", encoding="utf-8")

    orchestrator = object.__new__(WREMasterOrchestrator)
    orchestrator.repo_root = tmp_path.resolve()
    orchestrator.skills_loader = SimpleNamespace(
        resolve_skill_file=lambda _skill_name: skill_file.resolve()
    )

    assert orchestrator._find_skill_executor("bound_skill") == str(executor.resolve())


def test_executor_resolution_rejects_registered_skill_without_executor(tmp_path):
    registered = tmp_path / "registered" / "skill"
    registered.mkdir(parents=True)
    skill_file = registered / "SKILLz.md"
    skill_file.write_text("# No executor\n", encoding="utf-8")

    decoy = tmp_path / "modules" / "x" / "y" / "skillz" / "bound_skill"
    decoy.mkdir(parents=True)
    (decoy / "executor.py").write_text("raise RuntimeError\n", encoding="utf-8")

    orchestrator = object.__new__(WREMasterOrchestrator)
    orchestrator.repo_root = tmp_path.resolve()
    orchestrator.skills_loader = SimpleNamespace(
        resolve_skill_file=lambda _skill_name: skill_file.resolve()
    )

    assert orchestrator._find_skill_executor("bound_skill") is None


def _write_executor_bundle(tmp_path, source):
    skill_dir = tmp_path / "registered" / "skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILLz.md").write_text("# Bound skill\n", encoding="utf-8")
    executor = skill_dir / "executor.py"
    executor.write_text(source, encoding="utf-8")
    generate_skill_manifest(skill_dir, manifest_path=skill_dir / "SKILL_MANIFEST.json")
    return executor


def test_executor_rejects_truthy_string_success(tmp_path):
    executor = _write_executor_bundle(
        tmp_path,
        "def execute(task): return {'success': 'false', 'effect_receipts': [{'receipt_id': 'x', 'effect_type': 'test'}]}\n",
    )

    result = dispatch_registered_skill_executor(
        executor_path=executor,
        skill_name="bound_skill",
        input_context={},
        agent="qwen",
        admission_fingerprint=skill_bundle_fingerprint(executor.parent),
    )

    assert result["success"] is False
    assert result["error_code"] == "invalid_executor_result"


def test_executor_success_requires_typed_effect_receipt(tmp_path):
    executor = _write_executor_bundle(
        tmp_path,
        "def execute(task): return {'success': True, 'output': 'shape only'}\n",
    )

    result = dispatch_registered_skill_executor(
        executor_path=executor,
        skill_name="bound_skill",
        input_context={},
        agent="qwen",
        admission_fingerprint=skill_bundle_fingerprint(executor.parent),
    )

    assert result["success"] is False
    assert result["error_code"] == "missing_effect_receipt"


def test_executor_exception_does_not_expose_exception_text(tmp_path, caplog):
    executor = _write_executor_bundle(
        tmp_path,
        "def execute(task): raise RuntimeError('SYNTHETIC_SECRET')\n",
    )

    with caplog.at_level(logging.ERROR):
        result = dispatch_registered_skill_executor(
            executor_path=executor,
            skill_name="bound_skill",
            input_context={},
            agent="qwen",
            admission_fingerprint=skill_bundle_fingerprint(executor.parent),
        )

    assert result["success"] is False
    assert "SYNTHETIC_SECRET" not in str(result)
    assert "SYNTHETIC_SECRET" not in caplog.text


def test_executor_accepts_exact_boolean_and_typed_effect_receipt(tmp_path):
    executor = _write_executor_bundle(
        tmp_path,
        "def execute(task): return {'success': True, 'output': 'done', 'effect_receipts': [{'receipt_id': 'effect-1', 'effect_type': 'test'}]}\n",
    )

    result = dispatch_registered_skill_executor(
        executor_path=executor,
        skill_name="bound_skill",
        input_context={},
        agent="qwen",
        admission_fingerprint=skill_bundle_fingerprint(executor.parent),
    )

    assert result["success"] is True
    assert result["_effect_evidence"] is True


def test_executor_rejects_bundle_replaced_after_scanner_admission(tmp_path):
    executor = _write_executor_bundle(
        tmp_path,
        "def execute(task): return {'success': True, 'output': 'v1', 'effect_receipts': [{'receipt_id': 'v1', 'effect_type': 'test'}]}\n",
    )
    admitted = skill_bundle_fingerprint(executor.parent)
    executor.write_text(
        "def execute(task): return {'success': True, 'output': 'v2', 'effect_receipts': [{'receipt_id': 'v2', 'effect_type': 'test'}]}\n",
        encoding="utf-8",
    )
    generate_skill_manifest(
        executor.parent,
        manifest_path=executor.parent / "SKILL_MANIFEST.json",
    )

    result = dispatch_registered_skill_executor(
        executor_path=executor,
        skill_name="bound_skill",
        input_context={},
        agent="qwen",
        admission_fingerprint=admitted,
    )

    assert result["success"] is False
    assert "v2" not in str(result)


def test_bundle_fingerprint_frames_file_presence_names_and_content(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    manifest = b"{}"
    prefix = b"prefix"
    legacy = b"legacy"
    (first / "SKILLz.md").write_bytes(prefix)
    (first / "SKILL.md").write_bytes(legacy)
    (first / "SKILL_MANIFEST.json").write_bytes(manifest)
    (second / "SKILLz.md").write_bytes(prefix + b"SKILL.md" + legacy)
    (second / "SKILL_MANIFEST.json").write_bytes(manifest)

    assert skill_bundle_fingerprint(first) != skill_bundle_fingerprint(second)


def test_orchestrator_dispatches_only_with_stored_admission_fingerprint(tmp_path):
    executor = _write_executor_bundle(
        tmp_path,
        "def execute(task): return {'success': True, 'output': 'bound', 'effect_receipts': [{'receipt_id': 'bound', 'effect_type': 'test'}]}\n",
    )
    orchestrator = object.__new__(WREMasterOrchestrator)
    orchestrator.repo_root = tmp_path.resolve()
    orchestrator.skills_loader = SimpleNamespace(
        resolve_skill_file=lambda _name: executor.parent / "SKILLz.md"
    )
    orchestrator._wre_skill_admission_fingerprints = {
        "bound_skill": skill_bundle_fingerprint(executor.parent)
    }

    result = orchestrator._try_executor_dispatch("bound_skill", {}, "qwen")

    assert result["success"] is True
    assert result["output"] == "bound"


def test_executor_reparse_attribute_is_rejected_before_resolution(
    tmp_path, monkeypatch
):
    import os
    from types import SimpleNamespace
    from modules.infrastructure.wre_core.src import skill_path_security

    candidate = tmp_path / "executor.py"
    candidate.write_text("", encoding="utf-8")
    original_lstat = os.lstat

    def _lstat(path):
        metadata = original_lstat(path)
        if Path(path) == candidate:
            return SimpleNamespace(
                st_mode=metadata.st_mode,
                st_file_attributes=0x400,
            )
        return metadata

    monkeypatch.setattr(skill_path_security.os, "lstat", _lstat)
    assert _has_link_or_reparse_component(tmp_path.resolve(), candidate) is True


def test_local_inference_model_path_failure_returns_stable_failure(monkeypatch):
    from modules.infrastructure.shared_utilities import local_model_selection

    monkeypatch.setattr(
        local_model_selection,
        "resolve_code_model_path",
        lambda: (_ for _ in ()).throw(FileNotFoundError("SYNTHETIC_SECRET")),
    )

    result = execute_local_skill_inference(
        skill_content="# Skill", input_context={}, agent="qwen"
    )

    assert result["success"] is False
    assert result["error_code"] == "local_model_unavailable"
    assert "SYNTHETIC_SECRET" not in str(result)


def test_local_inference_text_is_proposal_not_effect_success(monkeypatch):
    from holo_index.qwen_advisor import llm_engine
    from modules.infrastructure.shared_utilities import local_model_selection

    class _FakeEngine:
        def __init__(self, **_kwargs):
            pass

        def initialize(self):
            return True

        def generate_response(self, **_kwargs):
            return "I cannot perform the requested action."

    monkeypatch.setattr(llm_engine, "QwenInferenceEngine", _FakeEngine)
    monkeypatch.setattr(local_model_selection, "resolve_code_model_path", lambda: "model.gguf")

    result = execute_local_skill_inference(
        skill_content="# Skill", input_context={}, agent="qwen"
    )

    assert result["success"] is False
    assert result["proposal"] == "I cannot perform the requested action."
    assert result["error_code"] == "unverified_model_proposal"


def test_local_inference_rejects_engine_error_text(monkeypatch):
    from holo_index.qwen_advisor import llm_engine
    from modules.infrastructure.shared_utilities import local_model_selection

    engine = SimpleNamespace(
        initialize=lambda: True,
        generate_response=lambda **_kwargs: "Error: failed - SYNTHETIC_SECRET",
    )
    monkeypatch.setattr(llm_engine, "QwenInferenceEngine", lambda **_kwargs: engine)
    monkeypatch.setattr(local_model_selection, "resolve_code_model_path", lambda: "model.gguf")

    result = execute_local_skill_inference(
        skill_content="# Skill", input_context={}, agent="qwen"
    )

    assert result["error_code"] == "local_model_unavailable"
    assert "SYNTHETIC_SECRET" not in str(result)


def test_qwen_engine_generation_exception_is_redacted(monkeypatch, caplog):
    from holo_index.qwen_advisor.llm_engine import QwenInferenceEngine

    engine = object.__new__(QwenInferenceEngine)
    engine.max_tokens = 32
    engine.temperature = 0.2
    engine.llm = lambda *_args, **_kwargs: (_ for _ in ()).throw(
        RuntimeError("SYNTHETIC_SECRET")
    )
    monkeypatch.setattr(engine, "initialize", lambda: True)

    with caplog.at_level(logging.ERROR):
        response = engine.generate_response("proposal")

    assert response == "Error: Qwen response generation failed"
    assert "SYNTHETIC_SECRET" not in caplog.text


def test_react_never_treats_failed_high_fidelity_shape_as_success(monkeypatch):
    orchestrator = object.__new__(WREMasterOrchestrator)
    orchestrator.react_fidelity_threshold = 0.90
    orchestrator.sqlite_memory = None
    attempts = []

    def _failed_attempt(**_kwargs):
        attempts.append(1)
        return {
            "success": False,
            "pattern_fidelity": 1.0,
            "result": {"error": "effect failed", "failed_at_step": 1},
        }

    monkeypatch.setattr(orchestrator, "_execute_skill_once", _failed_attempt)

    result = orchestrator.execute_skill_with_reasoning(
        "broken_skill",
        "qwen",
        {},
        max_iterations=3,
    )

    assert len(attempts) == 3
    assert result["success"] is False
    assert result["_react_metadata"]["early_success"] is False
    assert all(
        attempt["success"] is False
        for attempt in result["_react_metadata"]["all_attempts"]
    )


def test_react_exhaustion_rejects_successful_low_fidelity_attempts(monkeypatch):
    orchestrator = object.__new__(WREMasterOrchestrator)
    orchestrator.react_fidelity_threshold = 0.90
    orchestrator.sqlite_memory = None
    monkeypatch.setattr(
        orchestrator,
        "_execute_skill_once",
        lambda **_kwargs: {
            "success": True,
            "pattern_fidelity": 0.20,
            "result": {"failed_at_step": None},
        },
    )

    result = orchestrator.execute_skill_with_reasoning(
        "low_fidelity_skill", "qwen", {}, max_iterations=2
    )

    assert result["success"] is False
    assert result["execution_success"] is True
    assert result["_react_metadata"]["early_success"] is False


def test_react_clamps_untrusted_iteration_and_fidelity_inputs(monkeypatch):
    orchestrator = object.__new__(WREMasterOrchestrator)
    orchestrator.react_fidelity_threshold = 0.90
    orchestrator.sqlite_memory = None
    attempts = []

    def _attempt(**_kwargs):
        attempts.append(1)
        return {"success": True, "pattern_fidelity": 0.20, "result": {}}

    monkeypatch.setattr(orchestrator, "_execute_skill_once", _attempt)
    result = orchestrator.execute_skill_with_reasoning(
        "bounded_skill", "qwen", {}, max_iterations=1000, fidelity_threshold=-1
    )

    assert len(attempts) == 10
    assert result["success"] is False
    assert result["_react_metadata"]["max_iterations"] == 10
