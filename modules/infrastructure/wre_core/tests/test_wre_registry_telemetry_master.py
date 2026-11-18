"""Public named WRE telemetry truth and durable observation, never SkillOutcome."""
from types import SimpleNamespace

import pytest

from modules.infrastructure.wre_core.src.pattern_memory import PatternMemory
from modules.infrastructure.wre_core.tests.wre_registry_telemetry_test_support import (
    SKILL, _assert_no_learning, _assert_telemetry, _json, _run, _setup, admission,
)


def _assert_event(event, result, request, projected):
    assert event["event_type"] == "telemetry_projection" and event["skill_name"] == SKILL
    assert all(event.get(name) is None for name in ("before_fidelity", "after_fidelity", "variation_id"))
    description = event["description"]
    assert type(description) is str and len(description) <= 16384
    assert result["execution_id"] in description
    assert request["base_sha"] in description and request["head_sha"] in description
    assert ("projected" if projected else "rejected") in description
    if projected:
        assert result["projection"]["evidence"]["projection_id"] in description
    else:
        assert all(reason in description for reason in result["projection"]["rejection_reasons"])
    assert "test_impact_plan" not in description and "candidate" not in description


@pytest.mark.parametrize("projected,react", [(True, False), (False, False), (True, True), (False, True)],
                         ids=["projected_once", "rejected_once", "projected_react", "rejected_react"])
def test_public_named_telemetry_is_one_observation_not_success(monkeypatch, tmp_path, projected, react):
    state = _setup(monkeypatch, tmp_path, projected)
    result = _run(state, react)
    _assert_telemetry(result, projected)
    assert result["execution_success"] is False and result["observation_persisted"] is True
    assert _json(result["projection"]) == _json(state.report)
    assert len(state.calls) == len(state.scans) == len(state.events) == 1
    assert state.memory.counters == {"wre_skill_scan_checks": 1}
    _assert_event(state.events[0], result, state.request, projected)
    _assert_no_learning(state)
    if react:
        metadata = result["_react_metadata"]
        assert metadata["iterations"] == 1 and metadata["early_success"] is False
        assert len(metadata["all_attempts"]) == 1
        assert metadata["all_attempts"][0]["success"] is False
        assert metadata["all_attempts"][0].get("fidelity") is None


GATES = ["scanner", "intent", "version", "load", "active_ab", "missing_executor"]


@pytest.mark.parametrize("gate", GATES, ids=GATES)
def test_named_admission_failures_stop_react_without_fallback(monkeypatch, tmp_path, gate):
    state = _setup(monkeypatch, tmp_path)
    if gate == "scanner":
        def denied(**kwargs):
            state.scans.append(kwargs)
            return SimpleNamespace(available=True, passed=False, manifest_passed=True)
        monkeypatch.setattr(admission, "run_skill_scan", denied)
    elif gate == "intent": state.master.skills_loader.registry["skills"][SKILL]["intent_type"] = "DECISION"
    elif gate == "version":
        state.master.skills_loader.get_skill_metadata = lambda _: {
            "name": SKILL, "version": "2.2", "intent_type": "TELEMETRY", "promotion_state": "production"}
    elif gate == "load":
        def fail_load(*args): raise RuntimeError("private-load-detail")
        state.master.skills_loader.load_skill = fail_load
    elif gate == "active_ab": state.memory.get_active_ab_test = lambda _: {"variation_id": "unbound"}
    else: state.target.unlink()
    result = _run(state, True)
    assert result["success"] is False and result.get("telemetry_completed") is not True
    assert state.calls == [] and state.events == [] and len(state.scans) <= 1
    assert result["_react_metadata"]["iterations"] == 1
    assert result["_react_metadata"]["early_success"] is False
    assert "private-load-detail" not in _json(result)
    _assert_no_learning(state)


@pytest.mark.parametrize("mode", ["failure", "unavailable"], ids=["failure", "unavailable"])
def test_observation_storage_failure_preserves_projection_without_retry(monkeypatch, tmp_path, mode):
    state = _setup(monkeypatch, tmp_path)
    writes = []
    def fail(**kwargs):
        writes.append(kwargs)
        raise RuntimeError("private-store-detail")
    if mode == "failure": state.memory.record_learning_event = fail
    else: state.master.sqlite_memory = None
    result = _run(state, True)
    _assert_telemetry(result, True)
    assert result["observation_persisted"] is False
    assert type(result["observation_error"]) is str and result["observation_error"]
    assert "private-store-detail" not in _json(result)
    assert _json(result["projection"]) == _json(state.report)
    assert len(state.calls) == 1 and len(writes) == (1 if mode == "failure" else 0)
    assert result["_react_metadata"]["iterations"] == 1
    _assert_no_learning(state)


@pytest.mark.parametrize("projected", [True, False], ids=["projected", "rejected"])
def test_real_pattern_memory_reopen_has_only_telemetry_event(monkeypatch, tmp_path, projected):
    state = _setup(monkeypatch, tmp_path, projected)
    path = tmp_path / "telemetry.sqlite3"
    memory = PatternMemory(db_path=path)
    state.master.sqlite_memory = memory
    try:
        before = (memory.recall_successful_patterns(SKILL), memory.recall_failure_patterns(SKILL))
        result = _run(state, True)
        _assert_telemetry(result, projected)
        assert result["observation_persisted"] is True and len(state.calls) == 1
        assert (memory.recall_successful_patterns(SKILL), memory.recall_failure_patterns(SKILL)) == before
        assert state.forbidden == []
    finally:
        memory.close()
    reopened = PatternMemory(db_path=path)
    try:
        events = [dict(row) for row in reopened.conn.execute("SELECT * FROM learning_events")]
        assert len(events) == 1
        _assert_event(events[0], result, state.request, projected)
        for table in ("skill_outcomes", "skill_variations"):
            assert reopened.conn.execute("SELECT COUNT(*) FROM " + table).fetchone()[0] == 0
        counters = dict(reopened.conn.execute("SELECT counter_name, counter_value FROM telemetry_counters"))
        assert counters == {"wre_skill_scan_checks": 1}
    finally:
        reopened.close()
