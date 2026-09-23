"""Characterize instruction consumption, without claiming prompt provenance."""

import hashlib
import json
from pathlib import Path

import pytest

from modules.infrastructure.wre_core.src import wre_auto_researcher as subject
from modules.infrastructure.wre_core.tests.test_wre_auto_researcher import (
    temp_research_env,  # noqa: F401 - reuse the pre-construction model-disable fixture
)


INITIAL = "PROGRAM_INITIAL"
CHANGED = "PROGRAM_CHANGED"
CANDIDATE = ("AGENT_ALLOCATION = {'basic_search': 1.0}\n"
             "AGENT_PREMIUM_MULTIPLIERS = {'basic_search': 1.0}")


def _metrics():
    return {"fitness": 1.0, "roc_ratio": 1.0,
            "is_roi_sustainable": True, "monthly_margin_usd": 1.0}


class RecordingBackend:
    def __init__(self, researcher, scenario):
        self.researcher = researcher
        self.scenario = scenario
        self.calls = []

    def generate_response(self, prompt, max_tokens):
        self.calls.append((prompt, max_tokens))
        if self.scenario == "between_attempts" and len(self.calls) == 1:
            self.researcher.program_instructions = CHANGED
        if self.scenario == "backend_error":
            raise RuntimeError("synthetic backend failure")
        return CANDIDATE


def _observe_evaluations(monkeypatch, researcher, scenario):
    calls = []

    def evaluate(path, *, cost_catalog=None):
        calls.append(path.read_text(encoding="utf-8"))
        if scenario == "baseline_edit" and len(calls) == 1:
            researcher.program_instructions = CHANGED
        return _metrics()

    monkeypatch.setattr(subject, "evaluate_target", evaluate)
    return calls


def _assert_terminal_state(researcher, report, attempts, proposal_count):
    assert report["status"] == "completed"
    assert report["attempts_requested"] == report["attempts_started"] == attempts
    assert report["attempts_finished"] == attempts
    assert report["baseline_evaluations"] == 1
    assert report["candidate_evaluations"] == proposal_count
    assert report["outcome_counts"] == {
        "no_proposal": attempts - proposal_count, "accepted": 0,
        "rejected": proposal_count, "failed_validation": 0, "crashed": 0,
    }
    assert report["cleanup"] == "restored"
    assert researcher.working_target_path.read_text(encoding="utf-8") == researcher.original_code
    assert json.loads(Path(report["report_path"]).read_text()) == report
    assert report["independently_verified"] is None
    assert report["retained_improvements"] is None


@pytest.mark.parametrize("scenario,attempts,expected", [
    pytest.param("file_edit", 1, [INITIAL], id="constructor-file-captured"),
    pytest.param("attribute_edit", 1, [CHANGED], id="pre-run-attribute-consumed"),
    pytest.param("baseline_edit", 1, [CHANGED], id="baseline-callback-consumed"),
    pytest.param("between_attempts", 2, [INITIAL, CHANGED], id="next-call-observes-mutation"),
    pytest.param("backend_error", 1, [INITIAL], id="failed-backend-still-observed"),
    pytest.param("heuristic", 1, [], id="heuristic-no-backend-consumption"),
    pytest.param("zero", 0, [], id="zero-attempts-no-backend-consumption"),
])
def test_program_consumption_boundary(temp_research_env, tmp_path, monkeypatch,
                                      scenario, attempts, expected):
    target, program = temp_research_env
    target_before = target.read_bytes()
    program.write_text(INITIAL, encoding="utf-8")
    researcher = subject.WREAutoResearcher(
        target, program, max_iterations=attempts, results_dir=tmp_path / "results")
    backend = RecordingBackend(researcher, scenario)
    researcher.llm = None if scenario == "heuristic" else backend
    heuristic_calls = []
    monkeypatch.setattr(researcher, "_propose_via_heuristic",
                        lambda code: heuristic_calls.append(code))
    evaluations = _observe_evaluations(monkeypatch, researcher, scenario)
    if scenario == "file_edit":
        program.write_text(CHANGED, encoding="utf-8")
    if scenario == "attribute_edit":
        researcher.program_instructions = CHANGED
    report = researcher.run()
    prompts = [prompt for prompt, _ in backend.calls]
    assert [p.partition("\n\n### CURRENT CONFIGURATION CODE:")[0] for p in prompts] == expected
    assert all("\n\n### CURRENT CONFIGURATION CODE:" in p for p in prompts)
    assert all(researcher.original_code in p for p in prompts)
    assert [limit for _, limit in backend.calls] == [1024] * len(expected)
    assert heuristic_calls == ([researcher.original_code] if scenario == "heuristic" else [])
    proposals = 0 if scenario in {"backend_error", "heuristic", "zero"} else attempts
    assert evaluations == [researcher.original_code] + [CANDIDATE] * proposals
    _assert_terminal_state(researcher, report, attempts, proposals)
    assert target.read_bytes() == target_before
    assert program.read_text(encoding="utf-8") == (CHANGED if scenario == "file_edit" else INITIAL)
    assert report["program_inputs"] == [
        _identity(text, iteration=i, ordinal=i) for i, text in enumerate(expected, 1)]
    assert not hasattr(researcher, "_program_input_context")


def _identity(text, iteration=1, ordinal=1):
    try:
        digest = hashlib.sha256(str.encode(text, "utf-8")).hexdigest()
    except UnicodeEncodeError:
        return {"iteration": iteration, "call_ordinal": ordinal,
                "program_input_sha256": None, "identity_error": "UnicodeEncodeError"}
    return {"iteration": iteration, "call_ordinal": ordinal,
            "program_input_sha256": digest, "identity_error": None}


def _researcher(temp_research_env, tmp_path, monkeypatch):
    target, program = temp_research_env
    program.write_text(INITIAL, encoding="utf-8")
    researcher = subject.WREAutoResearcher(
        target, program, max_iterations=1, results_dir=tmp_path / "results")
    researcher.llm = RecordingBackend(researcher, "normal")
    _observe_evaluations(monkeypatch, researcher, "normal")
    return researcher


@pytest.mark.parametrize("kind", ["unicode-newlines", "custom-format", "unencodable", "format-result-subclass"])
def test_program_rendered_identity(temp_research_env, tmp_path, monkeypatch, kind):
    researcher = _researcher(temp_research_env, tmp_path, monkeypatch)
    rendered = "research \u03bb\r\nnext\n" if kind != "unencodable" else "research\ud800"
    formats = []

    class Rendered(str):
        def __format__(self, spec):
            raise AssertionError("Do not format the rendered result again")

        def __str__(self):
            raise AssertionError("Do not invoke a rendered-result override")

    class Instructions:
        def __format__(self, spec):
            formats.append(spec)
            return Rendered(rendered) if kind == "format-result-subclass" else rendered

        def __str__(self):
            raise AssertionError("Preserve original format semantics")

    custom = kind in {"custom-format", "format-result-subclass"}
    researcher.program_instructions = Instructions() if custom else rendered
    report = researcher.run()
    assert researcher.llm.calls[0][0].startswith(rendered + "\n\n### CURRENT")
    assert len(researcher.llm.calls) == 1
    assert formats == ([""] if custom else [])
    assert report["program_inputs"] == [_identity(rendered)]
    _assert_terminal_state(researcher, report, 1, 1)


@pytest.mark.parametrize("prior", [False, True], ids=["absent", "prior"])
@pytest.mark.parametrize("exit_kind", ["normal", "format", "lookup", "interrupt", "mode"])
def test_program_context_exit(temp_research_env, tmp_path, monkeypatch, prior, exit_kind):
    researcher = _researcher(temp_research_env, tmp_path, monkeypatch)
    previous = ([], 99)
    if prior:
        researcher._program_input_context = previous
    calls = []

    class Instructions:
        def __format__(self, spec):
            raise ValueError("synthetic formatting failure")

    class Backend:
        @property
        def generate_response(self):
            if exit_kind == "lookup":
                raise RuntimeError("synthetic lookup failure")
            return self.call

        def call(self, prompt, max_tokens):
            calls.append(prompt)
            if exit_kind == "interrupt":
                raise KeyboardInterrupt("synthetic interruption")
            if exit_kind == "mode":
                researcher.dry_run = False
            return CANDIDATE

    researcher.llm = Backend()
    if exit_kind == "format":
        researcher.program_instructions = Instructions()
    errors = {"format": ValueError, "interrupt": KeyboardInterrupt, "mode": NotImplementedError}
    if exit_kind in errors:
        with pytest.raises(errors[exit_kind]):
            researcher.run()
        paths = list(researcher.results_dir.glob("invocation-*/report.json"))
        assert len(paths) == 1
        report = json.loads(paths[0].read_text())
        assert report["status"] == "aborted"
        assert report["failure"]["type"] == errors[exit_kind].__name__
    else:
        report = researcher.run()
        _assert_terminal_state(researcher, report, 1, int(exit_kind == "normal"))
    called = exit_kind not in {"format", "lookup"}
    assert len(calls) == int(called)
    assert report["program_inputs"] == ([_identity(INITIAL)] if called else [])
    assert report["cleanup"] == "restored"
    assert researcher.working_target_path.read_text(encoding="utf-8") == researcher.original_code
    assert previous == ([], 99)
    assert ("_program_input_context" in vars(researcher)) == prior
    if prior:
        assert researcher._program_input_context is previous


def test_program_override_bypass(temp_research_env, tmp_path, monkeypatch):
    researcher = _researcher(temp_research_env, tmp_path, monkeypatch)
    monkeypatch.setattr(researcher, "_propose_change", lambda code, metrics, history: CANDIDATE)
    report = researcher.run()
    assert report["program_inputs"] == []
    assert researcher.llm.calls == []
    _assert_terminal_state(researcher, report, 1, 1)


def test_program_sequential_call_ordinals(temp_research_env, tmp_path, monkeypatch):
    researcher = _researcher(temp_research_env, tmp_path, monkeypatch)

    def twice(code, metrics, history):
        researcher._propose_via_llm(code, metrics, history)
        return researcher._propose_via_llm(code, metrics, history)

    monkeypatch.setattr(researcher, "_propose_change", twice)
    first = researcher.run()
    saved = Path(first["report_path"]).read_bytes()
    researcher.program_instructions = CHANGED
    second = researcher.run()
    assert first["program_inputs"] == [_identity(INITIAL, ordinal=i) for i in (1, 2)]
    assert second["program_inputs"] == [_identity(CHANGED, ordinal=i) for i in (1, 2)]
    assert first["invocation_id"] != second["invocation_id"]
    assert Path(first["report_path"]).read_bytes() == saved
    assert len(researcher.llm.calls) == 4
    assert not hasattr(researcher, "_program_input_context")


def test_program_direct_call_compatibility(temp_research_env, tmp_path, monkeypatch):
    researcher = _researcher(temp_research_env, tmp_path, monkeypatch)
    assert researcher._propose_via_llm(researcher.original_code, _metrics(), []) == CANDIDATE
    assert len(researcher.llm.calls) == 1
    assert not hasattr(researcher, "_program_input_context")
    assert list(researcher.results_dir.glob("invocation-*")) == []
