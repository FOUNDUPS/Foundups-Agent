"""Characterize instruction consumption, without claiming prompt provenance."""

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

    def evaluate(path):
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
