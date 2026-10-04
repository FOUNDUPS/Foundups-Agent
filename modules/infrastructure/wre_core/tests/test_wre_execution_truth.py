"""Fail-closed execution-truth contracts for the legacy WRE skill path."""

import logging
from pathlib import Path
from types import SimpleNamespace

import pytest

from modules.infrastructure.wre_core.src import skill_runtime_admission as admission
from modules.infrastructure.wre_core.tests.test_wre_runtime_admission_truth import (
    _runtime_admission_loader, _Libido, _Memory,
)
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
        lambda _skill_name, force=False: (True, "test pass", "f" * 64),
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


def _admission_orchestrator(monkeypatch, tmp_path):
    source = "def execute(task): return {'success': True, 'output': 'original', 'effect_receipts': [{'receipt_id': 'test', 'effect_type': 'test'}]}\n"
    executor = _write_executor_bundle(tmp_path, source)
    orchestrator = _minimal_orchestrator(monkeypatch, tmp_path)
    orchestrator.repo_root = tmp_path
    orchestrator.skills_loader = _runtime_admission_loader(executor.parent / "SKILLz.md")
    orchestrator.wre_skill_scan_required = orchestrator.wre_skill_scan_enforced = True
    orchestrator.wre_skill_scan_always = False
    orchestrator.wre_skill_scan_ttl_sec = 900
    orchestrator.wre_skill_scan_max_severity = "medium"
    monkeypatch.setattr(orchestrator, "_ensure_wre_skill_safety", WREMasterOrchestrator._ensure_wre_skill_safety.__get__(orchestrator))
    monkeypatch.setattr(admission, "run_skill_scan", lambda **_: SimpleNamespace(available=True, passed=True, manifest_passed=True))
    return orchestrator, executor


@pytest.mark.parametrize("change_bundle", [False, True])
def test_reentrant_execution_keeps_its_admitted_bundle(monkeypatch, tmp_path, change_bundle):
    orchestrator, executor = _admission_orchestrator(monkeypatch, tmp_path)
    nested = []

    def load(*_args):
        if not nested:
            nested.append(None)
            if change_bundle:
                executor.write_text(executor.read_text(encoding="utf-8").replace("original", "replacement"), encoding="utf-8")
                generate_skill_manifest(executor.parent, manifest_path=executor.parent / "SKILL_MANIFEST.json")
            nested[0] = orchestrator._execute_skill_once("skill", "qwen", {}, evolve_on_low_fidelity=False)
        return "# Skill"

    orchestrator.skills_loader.load_skill = load
    result = orchestrator._execute_skill_once("skill", "qwen", {}, evolve_on_low_fidelity=False)
    assert nested[0]["success"] is True
    assert result["success"] is (not change_bundle)
    assert result["execution_id"] != nested[0]["execution_id"]
    assert orchestrator.sqlite_memory.outcomes[-1].success is (not change_bundle)


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


@pytest.mark.parametrize("explicit", [False, True])
def test_orchestrator_dispatches_only_with_stored_admission_fingerprint(tmp_path, explicit):
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

    kwargs = {"admission_fingerprint": skill_bundle_fingerprint(executor.parent)} if explicit else {}
    result = orchestrator._try_executor_dispatch("bound_skill", {}, "qwen", **kwargs)

    assert result["success"] is explicit
    if explicit:
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

        def close(self):
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
        close=lambda: None,
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


# Portable caller wiring only: this fake factory is not a native formatter proof.
_NATIVE_PROFILE_TEMPLATE = "synthetic qualified chat template"
_NATIVE_SKILL = "# Skill\nReturn a proposal."
_NATIVE_CONTEXT = {"x": 1, "proposal_mode": "native_chat"}
_NATIVE_SYSTEM = "You are drafting a WRE proposal. Do not claim effects."
_NATIVE_PROMPT = (
    "Execute this skill step-by-step:\n\n# Skill\nReturn a proposal.\n\n"
    'Input Context:\n{\n  "x": 1,\n  "proposal_mode": "native_chat"\n}\n\n'
    "Draft a structured proposal. Do not claim that repository, shell, Git, "
    "network, or external effects occurred."
)


def _native_profile():
    import hashlib
    return {"runtime_version": "0.3.20", "template_sha256": hashlib.sha256(
        _NATIVE_PROFILE_TEMPLATE.encode("utf-8")).hexdigest()}


@pytest.fixture
def native_contract_collaborators(monkeypatch):
    import sys
    module = sys.modules[WREMasterOrchestrator.__module__]
    calls = []
    def collaborator(name):
        def construct(*args, **kwargs):
            calls.append(name)
            return SimpleNamespace(set_thresholds=lambda *a, **k: calls.append("thresholds"))
        return construct
    for name in ("PatternMemory", "WSPValidator", "GemmaLibidoMonitor",
                 "SQLitePatternMemory", "WRESkillsLoader", "SkillSelector"):
        monkeypatch.setattr(module, name, collaborator(name), raising=False)
    monkeypatch.setattr(module, "WRE_SKILLS_AVAILABLE", True)
    monkeypatch.setattr(module, "SPRINT3_AVAILABLE", True)
    monkeypatch.setattr(WREMasterOrchestrator, "_register_optional_workers",
                        lambda self: calls.append("workers"))
    for key, value in {"WRE_REACT_MODE": "0", "WRE_REACT_MAX_ITER": "3",
                       "WRE_REACT_FIDELITY": "0.9", "WRE_TOT_SELECTION": "1",
                       "WRE_TOT_MAX_BRANCHES": "5", "WRE_SKILL_SCAN_REQUIRED": "1",
                       "WRE_SKILL_SCAN_ENFORCED": "1", "WRE_SKILL_SCAN_ALWAYS": "0",
                       "WRE_SKILL_SCAN_TTL_SEC": "900", "WRE_SKILL_SCAN_MAX_SEVERITY": "medium",
                       "WRE_PATTERN_MEMORY_DB": "must-not-open-synthetic.db"}.items():
        monkeypatch.setenv(key, value)
    return calls


class _NativeContractModel:
    def __init__(self):
        self.metadata = {"tokenizer.chat_template": _NATIVE_PROFILE_TEMPLATE}
        self.chat_handler, self.chat_format = object(), "unchanged-format"
        self.raw, self.tokens, self.completions, self.selection_seen = [], [], [], []
        self.count, self.capacity, self.outcome = 1536, 2048, "text"
        self.close_calls = 0
    def close(self):
        self.close_calls += 1
    def __call__(self, prompt, **kwargs):
        self.raw.append((prompt, kwargs))
        return {"choices": [{"text": "  raw proposal  "}]}
    def n_ctx(self):
        return self.capacity
    def token_bos(self):
        return 1
    def token_eos(self):
        return 2
    def detokenize(self, tokens, special=False):
        assert special is True
        return b"<eos>" if tokens == [2] else b"<bos>"
    def tokenize(self, text, add_bos=True, special=False):
        self.tokens.append((text, add_bos, special))
        return list(range(self.count))
    def create_completion(self, **kwargs):
        self.completions.append(kwargs)
        self.selection_seen.append((self.chat_handler, self.chat_format,
                                    "create_completion" in self.__dict__))
        if self.outcome == "raises":
            raise RuntimeError("SYNTHETIC_NATIVE_SECRET")
        if self.outcome == "malformed":
            return {}
        return {"choices": [{"text": "" if self.outcome == "empty" else "  chat proposal  "}]}


def _install_native_contract_factory(monkeypatch, state):
    import sys
    from types import ModuleType
    native = ModuleType("llama_cpp")
    native.__path__, native.__version__ = [], "0.3.20"
    def forbidden(*args, **kwargs):
        state.forbidden.append("native-constructor")
        raise AssertionError("native constructor forbidden")
    native.Llama = forbidden
    formats = ModuleType("llama_cpp.llama_chat_format")
    class Formatter:
        def __init__(self, **kwargs):
            state.formatter_init.append(kwargs)
        def __call__(self, **kwargs):
            state.renders.append(kwargs)
            return SimpleNamespace(prompt="fixed synthetic rendered prompt", added_special=True,
                                   stop="<eos>", stopping_criteria=None)
    def factory(formatter):
        state.factories.append(formatter)
        def handler(*, llama, messages, **kwargs):
            state.handlers.append((messages, dict(kwargs)))
            rendered = formatter(messages=messages)
            tokens = llama.tokenize(rendered.prompt.encode(), add_bos=not rendered.added_special,
                                    special=True)
            completion = llama.create_completion(prompt=tokens, **{
                **kwargs, "stop": list(kwargs["stop"]) + [rendered.stop]})
            return {"choices": [{"message": {"content": completion["choices"][0]["text"]}}]}
        return handler
    formats.Jinja2ChatFormatter = Formatter
    formats.chat_formatter_to_chat_completion_handler = factory
    monkeypatch.setitem(sys.modules, "llama_cpp", native)
    monkeypatch.setitem(sys.modules, "llama_cpp.llama_chat_format", formats)
    return native, formats


@pytest.fixture
def native_contract_boundary(monkeypatch, native_contract_collaborators):
    from holo_index.qwen_advisor import llm_engine
    from modules.infrastructure.shared_utilities import local_model_selection
    state = SimpleNamespace(model=_NativeContractModel(), init=[], resolved=[], forbidden=[],
                            formatter_init=[], renders=[], factories=[], handlers=[], init_ok=True)
    def initialize(engine):
        state.init.append(engine)
        engine.llm, engine._initialized = state.model, state.init_ok
        return state.init_ok
    def resolve():
        state.resolved.append(True)
        return Path("synthetic-code.gguf")
    monkeypatch.setattr(llm_engine.QwenInferenceEngine, "initialize", initialize)
    monkeypatch.setattr(local_model_selection, "resolve_code_model_path", resolve)
    state.native, state.formats = _install_native_contract_factory(monkeypatch, state)
    yield state
    assert state.forbidden == []


def _native_contract_call(master):
    return master._execute_skill_with_qwen(_NATIVE_SKILL, dict(_NATIVE_CONTEXT), "qwen")


@pytest.mark.parametrize("selection", ["omitted", "explicit", "legacy"])
def test_native_contract_raw_recording(selection, native_contract_boundary):
    state = native_contract_boundary
    if selection == "legacy":
        master = object.__new__(WREMasterOrchestrator)
    else:
        master = WREMasterOrchestrator(**({} if selection == "omitted" else
                                         {"local_proposal_mode": "raw"}))
    result = _native_contract_call(master)
    assert state.model.raw == [(_NATIVE_SYSTEM + "\n\n" + _NATIVE_PROMPT,
                               {"max_tokens": 512, "temperature": 0.2,
                                "stop": ["\n\n", "###"], "echo": False})]
    assert len(state.init) == 2 and len(state.resolved) == 1
    assert state.handlers == [] and state.model.completions == []
    assert result["proposal"] == "raw proposal"
    assert result["success"] is False and result["_effect_evidence"] is False


_NATIVE_INVALID_CONFIGS = [
    ("mode-unknown", "unknown", None), ("mode-bool", True, None),
    ("mode-list", [], None), ("raw-profile", "raw", {}),
    ("profile-missing", "native_chat", None), ("profile-list", "native_chat", []),
    ("runtime-missing", "native_chat", {"template_sha256": "a" * 64}),
    ("digest-missing", "native_chat", {"runtime_version": "0.3.20"}),
    ("extra-field", "native_chat", {"runtime_version": "0.3.20", "template_sha256": "a" * 64, "x": 1}),
    ("runtime-type", "native_chat", {"runtime_version": 3, "template_sha256": "a" * 64}),
    ("runtime-unqualified", "native_chat", {"runtime_version": "0.2.72", "template_sha256": "a" * 64}),
    ("digest-type", "native_chat", {"runtime_version": "0.3.20", "template_sha256": 1}),
    ("digest-short", "native_chat", {"runtime_version": "0.3.20", "template_sha256": "a" * 63}),
    ("digest-uppercase", "native_chat", {"runtime_version": "0.3.20", "template_sha256": "A" * 64}),
    ("digest-nonhex", "native_chat", {"runtime_version": "0.3.20", "template_sha256": "g" * 64}),
]


@pytest.mark.parametrize("case,mode,profile", _NATIVE_INVALID_CONFIGS,
                         ids=[row[0] for row in _NATIVE_INVALID_CONFIGS])
def test_native_contract_invalid_config_before_effects(
        case, mode, profile, native_contract_boundary, native_contract_collaborators):
    from modules.infrastructure.wre_core.src import local_skill_inference as adapter
    state = native_contract_boundary
    with pytest.raises(ValueError):
        adapter.validate_local_proposal_config(mode, profile)
    with pytest.raises(ValueError):
        WREMasterOrchestrator(local_proposal_mode=mode, local_native_chat_profile=profile)
    result = adapter.execute_local_skill_inference(
        skill_content=_NATIVE_SKILL, input_context={}, agent="qwen",
        proposal_mode=mode, native_chat_profile=profile)
    assert result["error_code"] == "local_model_unavailable" and result["proposal"] == ""
    assert result["success"] is False and result["_effect_evidence"] is False
    assert native_contract_collaborators == []
    assert state.resolved == [] and state.init == [] and state.model.completions == []


def test_native_contract_profile_copy_and_trusted_forwarding(native_contract_boundary):
    from modules.infrastructure.wre_core.src import local_skill_inference as adapter
    profile = _native_profile()
    copied = adapter.validate_local_proposal_config("native_chat", profile)
    assert copied == profile and copied is not profile
    assert adapter.validate_local_proposal_config("raw", None) is None
    master = WREMasterOrchestrator(local_proposal_mode="native_chat", local_native_chat_profile=profile)
    profile["template_sha256"] = "0" * 64
    context = {**_NATIVE_CONTEXT, "native_chat_profile": profile}
    result = master._execute_skill_with_qwen(_NATIVE_SKILL, context, "qwen")
    assert result["proposal"] == "chat proposal"
    assert len(native_contract_boundary.handlers) == 1
    assert native_contract_boundary.model.raw == []


_NATIVE_BRANCHES = [
    ("fit", 1, 1), ("overflow", 1, 0), ("actual-context-smaller", 1, 0),
    ("runtime-old", 0, 0), ("runtime-missing", 0, 0), ("capability-missing", 0, 0),
    ("template-missing", 1, 0), ("template-mismatch", 1, 0), ("init-false", 1, 0),
    ("completion-raises", 1, 1), ("response-empty", 1, 1), ("response-malformed", 1, 1),
]


def _configure_native_contract_branch(case, state, monkeypatch):
    if case == "overflow": state.model.count = 1537
    if case == "actual-context-smaller": state.model.capacity = 2047
    if case == "runtime-old": state.native.__version__ = "0.2.72"
    if case == "runtime-missing": monkeypatch.delattr(state.native, "__version__")
    if case == "capability-missing":
        monkeypatch.delattr(state.formats, "chat_formatter_to_chat_completion_handler")
    if case == "template-missing": state.model.metadata = {}
    if case == "template-mismatch": state.model.metadata["tokenizer.chat_template"] = "different"
    if case == "init-false": state.init_ok = False
    if case == "completion-raises": state.model.outcome = "raises"
    if case == "response-empty": state.model.outcome = "empty"
    if case == "response-malformed": state.model.outcome = "malformed"


@pytest.mark.parametrize("case,init_count,completion_count", _NATIVE_BRANCHES,
                         ids=[row[0] for row in _NATIVE_BRANCHES])
def test_native_contract_branch_wiring(
        case, init_count, completion_count, native_contract_boundary, monkeypatch, caplog):
    state = native_contract_boundary
    _configure_native_contract_branch(case, state, monkeypatch)
    master = WREMasterOrchestrator(local_proposal_mode="native_chat",
                                   local_native_chat_profile=_native_profile())
    before = (state.model.chat_handler, state.model.chat_format,
              state.model.create_completion.__func__, set(state.model.__dict__))
    result = _native_contract_call(master)
    assert len(state.init) == init_count and len(state.model.completions) == completion_count
    assert state.model.raw == [] and len(state.resolved) == 1
    assert state.model.selection_seen == [(before[0], before[1], False)] * completion_count
    assert before == (state.model.chat_handler, state.model.chat_format,
                      state.model.create_completion.__func__, set(state.model.__dict__))
    assert result["success"] is False and result["_effect_evidence"] is False
    assert "SYNTHETIC_NATIVE_SECRET" not in str(result) + caplog.text
    if case != "fit":
        assert result["error_code"] == "local_model_unavailable" and result["proposal"] == ""
    else:
        assert result["proposal"] == "chat proposal" and result["steps_completed"] == 0
        assert result["error_code"] == "unverified_model_proposal"
        assert state.renders == [{"messages": [{"role": "system", "content": _NATIVE_SYSTEM},
                                {"role": "user", "content": _NATIVE_PROMPT}], "enable_thinking": False}]
        assert state.model.tokens == [(b"fixed synthetic rendered prompt", False, True)] * 2
        assert state.model.completions[0]["prompt"] == list(range(1536))
        assert state.model.completions[0]["stop"] == ["###", "<eos>"]
        assert state.handlers[0][1] == {"max_tokens": 512, "temperature": 0.2,
                                         "stream": False, "stop": ["###"]}
        assert state.formatter_init == [{"template": _NATIVE_PROFILE_TEMPLATE,
                                        "eos_token": "<eos>", "bos_token": "<bos>",
                                        "stop_token_ids": [2], "add_generation_prompt": True}]


def test_native_contract_sequential_state_is_unchanged(native_contract_boundary):
    state = native_contract_boundary
    master = WREMasterOrchestrator(local_proposal_mode="native_chat",
                                   local_native_chat_profile=_native_profile())
    before = (state.model.chat_handler, state.model.chat_format,
              state.model.create_completion.__func__, set(state.model.__dict__))
    first, second = _native_contract_call(master), _native_contract_call(master)
    assert first == second and first["proposal"] == "chat proposal"
    assert len(state.model.completions) == 2 and len(state.init) == 2
    assert state.model.selection_seen == [(before[0], before[1], False)] * 2
    assert state.handlers[0] == state.handlers[1] and state.renders[0] == state.renders[1]
    assert before == (state.model.chat_handler, state.model.chat_format,
                      state.model.create_completion.__func__, set(state.model.__dict__))


def test_native_contract_engine_failure_is_redacted(native_contract_boundary, caplog):
    from holo_index.qwen_advisor.llm_engine import QwenInferenceEngine
    state = native_contract_boundary
    state.model.outcome = "raises"
    engine = QwenInferenceEngine(Path("synthetic-code.gguf"))
    response = engine.generate_chat_response(_NATIVE_PROMPT, _NATIVE_SYSTEM, **_native_profile())
    assert isinstance(response, str) and response.startswith("Error:")
    assert "SYNTHETIC_NATIVE_SECRET" not in response + caplog.text
    assert len(state.init) == 1 and len(state.model.completions) == 1
    assert state.model.raw == []


# Portable lifecycle ownership: fake handles never allocate native resources.
@pytest.mark.parametrize("initialized", [False, True], ids=["fresh", "flag-only"])
def test_qwen_lifecycle_close_without_model(initialized):
    from holo_index.qwen_advisor.llm_engine import QwenInferenceEngine

    engine = QwenInferenceEngine(Path("synthetic-code.gguf"))
    engine._initialized = initialized
    assert engine.close() is None
    assert engine.close() is None
    assert engine.llm is None and engine._initialized is False


@pytest.mark.parametrize("initialized,falsey", [(True, False), (False, False), (True, True)],
                         ids=["initialized", "owned-before-init", "falsey-owned"])
def test_qwen_lifecycle_close_detaches_before_callback(initialized, falsey):
    from holo_index.qwen_advisor.llm_engine import QwenInferenceEngine

    engine = QwenInferenceEngine(Path("synthetic-code.gguf"))
    events = []

    class OwnedHandle:
        def __bool__(self):
            return not falsey

        def close(self):
            events.append((engine.llm, engine._initialized))
            # Reentrant cleanup must not hand the same handle out twice.
            assert engine.close() is None

    engine.llm, engine._initialized = OwnedHandle(), initialized
    assert engine.close() is None
    assert engine.close() is None
    assert events == [(None, False)]
    assert engine.llm is None and engine._initialized is False


def test_qwen_lifecycle_close_error_is_redacted_and_not_retried(caplog):
    from holo_index.qwen_advisor.llm_engine import QwenInferenceEngine

    engine = QwenInferenceEngine(Path("synthetic-code.gguf"))
    events = []

    class FailingHandle:
        def close(self):
            events.append((engine.llm, engine._initialized))
            raise ValueError("SYNTHETIC_CLEANUP_SECRET")

    engine.llm, engine._initialized = FailingHandle(), True
    with caplog.at_level(logging.ERROR), pytest.raises(RuntimeError) as caught:
        engine.close()
    assert str(caught.value) == "Qwen model cleanup failed"
    assert caught.value.__cause__ is None and caught.value.__suppress_context__ is True
    assert "error_type=ValueError" in caplog.text
    assert "SYNTHETIC_CLEANUP_SECRET" not in caplog.text + str(caught.value)
    assert events == [(None, False)]
    assert engine.llm is None and engine._initialized is False
    assert engine.close() is None
    assert events == [(None, False)]


@pytest.fixture
def lifecycle_boundary(native_contract_boundary, monkeypatch):
    """Observe real engine ownership without replacing its candidate close body."""
    from holo_index.qwen_advisor import llm_engine

    state = native_contract_boundary
    state.constructed, state.engine_closes, state.native_closes = [], [], []
    state.cleanup_raises = False
    engine_type = llm_engine.QwenInferenceEngine
    original_init = engine_type.__init__
    original_close = getattr(engine_type, "close", None)

    def construct(engine, *args, **kwargs):
        original_init(engine, *args, **kwargs)
        state.constructed.append(engine)

    def close(engine):
        state.engine_closes.append(engine)
        # Baseline has no close API, but also never calls this observer.  Missing
        # adapter ownership is asserted after the call, not fabricated here.
        assert callable(original_close)
        return original_close(engine)

    def close_native():
        engine = state.engine_closes[-1]
        state.native_closes.append((engine.llm, engine._initialized))
        if state.cleanup_raises:
            raise ValueError("SYNTHETIC_CLEANUP_SECRET")

    monkeypatch.setattr(engine_type, "__init__", construct)
    monkeypatch.setattr(engine_type, "close", close, raising=False)
    monkeypatch.setattr(state.model, "close", close_native)
    return state


def _lifecycle_master(mode):
    return WREMasterOrchestrator(
        local_proposal_mode=mode,
        local_native_chat_profile=_native_profile() if mode == "native_chat" else None,
    )


def _lifecycle_outcome(state, outcome, monkeypatch):
    if outcome == "init-false":
        state.init_ok = False
    elif outcome == "runtime-old":
        state.native.__version__ = "0.2.72"
    elif outcome == "template-mismatch":
        state.model.metadata["tokenizer.chat_template"] = "not the qualified template"
    elif outcome in ("raises", "empty"):
        state.model.outcome = outcome
        original_raw = _NativeContractModel.__call__

        def raw(model, *args, **kwargs):
            response = original_raw(model, *args, **kwargs)
            if outcome == "raises":
                raise RuntimeError("SYNTHETIC_INFERENCE_SECRET")
            response["choices"][0]["text"] = ""
            return response

        monkeypatch.setattr(_NativeContractModel, "__call__", raw)


_LIFECYCLE_PATHS = [
    ("raw", "text"), ("native_chat", "text"),
    ("raw", "init-false"), ("native_chat", "init-false"),
    ("raw", "raises"), ("native_chat", "raises"),
    ("raw", "empty"), ("native_chat", "empty"),
    ("native_chat", "runtime-old"), ("native_chat", "template-mismatch"),
]


@pytest.mark.parametrize("mode,outcome", _LIFECYCLE_PATHS,
                         ids=[mode + "-" + outcome for mode, outcome in _LIFECYCLE_PATHS])
def test_local_lifecycle_closes_before_return(mode, outcome, lifecycle_boundary, monkeypatch, caplog):
    state = lifecycle_boundary
    _lifecycle_outcome(state, outcome, monkeypatch)
    result = _native_contract_call(_lifecycle_master(mode))

    assert len(state.constructed) == 1
    assert state.engine_closes == state.constructed
    assert state.native_closes == ([] if outcome == "runtime-old" else [(None, False)])
    assert state.constructed[0].llm is None and state.constructed[0]._initialized is False
    assert result["success"] is False and result["_effect_evidence"] is False
    assert result["output"] == "" and result["steps_completed"] == 0
    if outcome == "text":
        assert result["error_code"] == "unverified_model_proposal"
        assert result["proposal"] == ("raw proposal" if mode == "raw" else "chat proposal")
    else:
        assert result["error_code"] == "local_model_unavailable" and result["proposal"] == ""
    assert "SYNTHETIC_INFERENCE_SECRET" not in str(result) + caplog.text
    assert "SYNTHETIC_NATIVE_SECRET" not in str(result) + caplog.text


@pytest.mark.parametrize("mode,outcome", [("raw", "text"), ("native_chat", "text"),
                                         ("raw", "raises"), ("native_chat", "raises")],
                         ids=["raw-proposal", "native-proposal", "raw-primary-error", "native-primary-error"])
def test_local_lifecycle_cleanup_error_fails_closed(mode, outcome, lifecycle_boundary, monkeypatch, caplog):
    state = lifecycle_boundary
    state.cleanup_raises = True
    _lifecycle_outcome(state, outcome, monkeypatch)
    with caplog.at_level(logging.ERROR):
        result = _native_contract_call(_lifecycle_master(mode))

    assert state.engine_closes == state.constructed and len(state.constructed) == 1
    assert state.native_closes == [(None, False)]
    assert state.constructed[0].llm is None and state.constructed[0]._initialized is False
    assert result["error_code"] == "local_model_unavailable" and result["proposal"] == ""
    assert result["success"] is False and result["_effect_evidence"] is False and result["output"] == ""
    assert "SYNTHETIC_CLEANUP_SECRET" not in str(result) + caplog.text
    assert "SYNTHETIC_INFERENCE_SECRET" not in str(result) + caplog.text
    assert "SYNTHETIC_NATIVE_SECRET" not in str(result) + caplog.text


@pytest.mark.parametrize("case", ["unsupported-agent", "invalid-config", "resolver-error"])
def test_local_lifecycle_preconstruction_failure_owns_nothing(case, lifecycle_boundary, monkeypatch):
    from modules.infrastructure.shared_utilities import local_model_selection

    state = lifecycle_boundary
    options = {"skill_content": _NATIVE_SKILL, "input_context": dict(_NATIVE_CONTEXT), "agent": "qwen"}
    if case == "unsupported-agent":
        options["agent"] = "gemma"
    elif case == "invalid-config":
        options.update(proposal_mode="native_chat", native_chat_profile=None)
    else:
        def missing_model():
            raise FileNotFoundError("SYNTHETIC_RESOLVER_SECRET")
        monkeypatch.setattr(local_model_selection, "resolve_code_model_path", missing_model)
    result = execute_local_skill_inference(**options)
    assert state.constructed == state.engine_closes == state.native_closes == []
    assert state.init == state.model.raw == state.model.completions == []
    assert result["success"] is False and result["_effect_evidence"] is False and result["proposal"] == ""
    assert result["error_code"] == ("unsupported_local_agent" if case == "unsupported-agent" else "local_model_unavailable")
    assert "SYNTHETIC_RESOLVER_SECRET" not in str(result)


@pytest.mark.parametrize("mode", ["raw", "native_chat"])
def test_qwen_lifecycle_direct_generation_retains_owner(mode, native_contract_boundary):
    from holo_index.qwen_advisor.llm_engine import QwenInferenceEngine

    state = native_contract_boundary
    engine = QwenInferenceEngine(Path("synthetic-code.gguf"))
    if mode == "raw":
        responses = [engine.generate_response(_NATIVE_PROMPT, _NATIVE_SYSTEM) for _ in range(2)]
        assert responses == ["raw proposal", "raw proposal"]
        assert len(state.model.raw) == 2
    else:
        responses = [engine.generate_chat_response(_NATIVE_PROMPT, _NATIVE_SYSTEM, **_native_profile())
                     for _ in range(2)]
        assert responses == ["chat proposal", "chat proposal"]
        assert len(state.model.completions) == 2
    assert engine.llm is state.model and engine._initialized is True
    assert state.model.close_calls == 0


@pytest.mark.parametrize("mode", ["raw", "native_chat"])
def test_local_lifecycle_interruption_preserves_primary(mode, lifecycle_boundary, monkeypatch):
    from holo_index.qwen_advisor import llm_engine

    state = lifecycle_boundary
    def interrupted(engine, *args, **kwargs):
        engine.llm, engine._initialized = state.model, True
        raise KeyboardInterrupt("synthetic cancellation")
    method = "generate_response" if mode == "raw" else "generate_chat_response"
    monkeypatch.setattr(llm_engine.QwenInferenceEngine, method, interrupted)
    with pytest.raises(KeyboardInterrupt, match="synthetic cancellation"):
        _native_contract_call(_lifecycle_master(mode))
    assert state.engine_closes == state.constructed and len(state.constructed) == 1
    assert state.native_closes == [(None, False)]
    assert state.constructed[0].llm is None and state.constructed[0]._initialized is False


# Transport lineage is consumed by the master, not serialized into model input.
_CONTINUITY_REFLECTION = (
    '# Skill Evolution Reflection\n\n## Current Skill\n# Skill\nReturn a proposal.\n\n'
    '## Last Execution (fidelity=0.50)\n'
    'Input: {"x": 1, "proposal_mode": "native_chat"}\n'
    'Output: {"success": false}\n\n## Past Failures\nNone recorded yet.\n\n'
    '## Past Successes\nNone recorded yet.\n\n## Task\n'
    'Analyze why fidelity is 0.50 (below 0.90 target).\n'
    'Generate IMPROVED skill instructions that address the failure patterns.\n'
    'Output the improved SKILL.md content (YAML frontmatter + instructions).\n'
    'Keep the same name: continuity_skill\n'
)


@pytest.fixture
def continuity_proposal_parent():
    from modules.communication.moltbot_bridge.src.continuity_context import (
        ContinuityContext, RuntimeSurface,
    )
    return ContinuityContext(
        continuity_id="synthetic-parent", surface=RuntimeSurface.OPENCLAW,
        session_id="synthetic-session", sender="synthetic-sender", channel="test",
        created_at="2026-10-04T00:00:00Z", last_activity_at="2026-10-04T00:00:00Z",
        surface_metadata={"internal": "SYNTHETIC_CONTINUITY_ONLY"},
    )


def _continuity_reflection(context):
    return WREMasterOrchestrator._build_reflection_prompt(
        None, skill_name="continuity_skill", skill_content=_NATIVE_SKILL,
        failed_output={"success": False}, input_context=context, current_fidelity=0.5,
        failure_patterns=[], success_patterns=[],
    )


def test_continuity_proposal_ordinary_prompt_unchanged():
    from modules.infrastructure.wre_core.src.local_skill_inference import _build_prompt
    context = dict(_NATIVE_CONTEXT)
    assert _build_prompt(_NATIVE_SKILL, context) == _NATIVE_PROMPT
    assert context == _NATIVE_CONTEXT


@pytest.mark.parametrize("kind", ["context", "none", "mapping"])
def test_continuity_proposal_prompt_omits_reserved_field(kind, continuity_proposal_parent):
    from modules.infrastructure.wre_core.src.local_skill_inference import _build_prompt
    parent = continuity_proposal_parent
    value = {"context": parent, "none": None, "mapping": parent.to_dict()}[kind]
    context = {**_NATIVE_CONTEXT, "parent_continuity_context": value}
    before, parent_before = dict(context), parent.to_dict()
    assert _build_prompt(_NATIVE_SKILL, context) == _NATIVE_PROMPT
    assert context == before and context["parent_continuity_context"] is value
    assert parent.to_dict() == parent_before


def test_continuity_proposal_prompt_rejects_unrelated_object():
    from modules.infrastructure.wre_core.src.local_skill_inference import _build_prompt
    unrelated = object()
    context = {**_NATIVE_CONTEXT, "business_value": unrelated}
    with pytest.raises(TypeError):
        _build_prompt(_NATIVE_SKILL, context)
    assert context["business_value"] is unrelated


@pytest.mark.parametrize("mode", ["raw", "native_chat"])
def test_continuity_proposal_route_keeps_lineage_and_truth(
        mode, continuity_proposal_parent, lifecycle_boundary):
    state, parent = lifecycle_boundary, continuity_proposal_parent
    context = {**_NATIVE_CONTEXT, "parent_continuity_context": parent}
    before, parent_before = dict(context), parent.to_dict()
    result = _lifecycle_master(mode)._execute_skill_with_qwen(_NATIVE_SKILL, context, "qwen")
    assert result["error_code"] == "unverified_model_proposal"
    assert result["proposal"] == ("raw proposal" if mode == "raw" else "chat proposal")
    assert result["success"] is False and result["_effect_evidence"] is False
    assert result["output"] == "" and result["steps_completed"] == 0
    if mode == "raw":
        assert len(state.model.raw) == 1
        assert state.model.raw[0][0] == _NATIVE_SYSTEM + "\n\n" + _NATIVE_PROMPT
        assert state.handlers == []
    else:
        assert len(state.handlers) == len(state.model.completions) == 1
        assert state.handlers[0][0] == [
            {"role": "system", "content": _NATIVE_SYSTEM},
            {"role": "user", "content": _NATIVE_PROMPT},
        ]
        assert state.model.raw == []
    assert state.engine_closes == state.constructed and len(state.constructed) == 1
    assert state.native_closes == [(None, False)]
    assert state.constructed[0].llm is None and state.constructed[0]._initialized is False
    assert context == before and context["parent_continuity_context"] is parent
    assert parent.to_dict() == parent_before


@pytest.mark.parametrize("mode", ["raw", "native_chat"])
def test_continuity_proposal_route_rejects_unrelated_object(mode, lifecycle_boundary):
    state = lifecycle_boundary
    unrelated = object()
    context = {**_NATIVE_CONTEXT, "business_value": unrelated}
    result = _lifecycle_master(mode)._execute_skill_with_qwen(_NATIVE_SKILL, context, "qwen")
    assert result["error_code"] == "local_model_unavailable" and result["proposal"] == ""
    assert result["success"] is False and result["_effect_evidence"] is False
    assert state.model.raw == state.handlers == state.model.completions == []
    assert state.engine_closes == state.constructed and len(state.constructed) == 1
    assert context["business_value"] is unrelated


def test_continuity_proposal_ordinary_reflection_unchanged():
    context = dict(_NATIVE_CONTEXT)
    assert _continuity_reflection(context) == _CONTINUITY_REFLECTION
    assert context == _NATIVE_CONTEXT


@pytest.mark.parametrize("kind", ["context", "none", "mapping"])
def test_continuity_proposal_reflection_omits_reserved_field(kind, continuity_proposal_parent):
    parent = continuity_proposal_parent
    value = {"context": parent, "none": None, "mapping": parent.to_dict()}[kind]
    context = {**_NATIVE_CONTEXT, "parent_continuity_context": value}
    before, parent_before = dict(context), parent.to_dict()
    assert _continuity_reflection(context) == _CONTINUITY_REFLECTION
    assert context == before and context["parent_continuity_context"] is value
    assert parent.to_dict() == parent_before


def test_continuity_proposal_reflection_rejects_unrelated_object():
    unrelated = object()
    context = {**_NATIVE_CONTEXT, "business_value": unrelated}
    with pytest.raises(TypeError):
        _continuity_reflection(context)
    assert context["business_value"] is unrelated
