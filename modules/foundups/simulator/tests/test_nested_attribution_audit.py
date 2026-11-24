"""Frozen, synthetic-only attribution acceptance under the scenario CLI."""
from itertools import permutations
import json
import sys

import pytest

from modules.foundups.simulator import scenario_runner
from modules.foundups.simulator.nested_attribution import (
    OUTCOME_POINTS, Observation, Outcome, summarize,
)


PARENTS = {"root": None, "hpc": "root", "sim_tool": "hpc", "lab": "root"}
ELEMENTS = {"root-work": "root", "clip": "hpc", "tool-work": "sim_tool"}
ROWS = (
    Outcome("origin-1", "root-work", "root", OUTCOME_POINTS, 30),
    Outcome("origin-2", "clip", "hpc", OUTCOME_POINTS, 50),
    Outcome("origin-3", "tool-work", "sim_tool", OUTCOME_POINTS, 20),
)


def test_rollup_is_not_additional_credit_and_replay_is_idempotent():
    expected = summarize(PARENTS, ELEMENTS, ROWS, ())
    assert expected["direct_points"] == {"root": 30, "hpc": 50, "sim_tool": 20, "lab": 0}
    assert expected["inclusive_points"] == {"root": 100, "hpc": 70, "sim_tool": 20, "lab": 0}
    assert expected["ecosystem_points"] == 100
    for arrangement in permutations((*ROWS, ROWS[-1])):
        assert summarize(PARENTS, ELEMENTS, arrangement, ()) == expected


def test_exposure_and_qualified_use_remain_distinct_and_union_actors():
    exposure = (Observation("a", "hpc", "seen"), Observation("b", "hpc", "seen"),
                Observation("b", "lab", "seen"))
    report = summarize(PARENTS, ELEMENTS, (), (*exposure, *exposure))
    assert report["observations"]["hpc"] == {"seen": 2, "qualified": 0}
    assert report["ecosystem_observations"] == {"seen": 2, "qualified": 0}
    assert report["ecosystem_points"] == 0
    qualified = (Observation("b", "hpc", "qualified"), Observation("b", "lab", "qualified"))
    report = summarize(PARENTS, ELEMENTS, (), (*exposure, *qualified))
    assert report["observations"]["hpc"] == {"seen": 2, "qualified": 1}
    assert report["observations"]["lab"] == {"seen": 1, "qualified": 1}
    assert report["observations"]["root"] == {"seen": 0, "qualified": 0}
    assert report["ecosystem_observations"] == {"seen": 2, "qualified": 1}
    assert report["ecosystem_points"] == 0


def test_same_origin_with_conflicting_owner_and_element_fails_closed():
    conflict = Outcome(ROWS[1].origin, "tool-work", "sim_tool", OUTCOME_POINTS, 50)
    with pytest.raises(ValueError, match="contradictory"):
        summarize(PARENTS, ELEMENTS, (*ROWS, conflict), ())


@pytest.mark.parametrize("unit,value", [("FUC", 1), ("LAB", 1), ("UPS", 1),
                                        (OUTCOME_POINTS, True), (OUTCOME_POINTS, 1.5),
                                        (OUTCOME_POINTS, -1)])
def test_no_financial_or_untyped_units(unit, value):
    with pytest.raises(ValueError, match="invalid outcome"):
        summarize(PARENTS, ELEMENTS, (Outcome("x", "clip", "hpc", unit, value),), ())


def test_content_item_cannot_claim_registered_project_credit():
    with pytest.raises(ValueError, match="invalid outcome"):
        summarize(PARENTS, ELEMENTS, (Outcome("x", "clip", "clip", OUTCOME_POINTS, 2),), ())
    with pytest.raises(ValueError, match="unregistered"):
        summarize(PARENTS, {"feature": "undeclared_tool"}, (), ())
    with pytest.raises(ValueError, match="invalid observation"):
        summarize(PARENTS, ELEMENTS, (), (Observation("x", "clip", "qualified"),))


@pytest.mark.parametrize("parents", [{"a": "b", "b": "a"}, {"a": "not_registered"}])
def test_primary_graph_is_acyclic_and_referentially_closed(parents):
    with pytest.raises(ValueError, match="unknown parent or containment cycle"):
        summarize(parents, {}, (), ())


def test_opt_in_cli_uses_existing_registry_but_never_runs_model_or_writes(monkeypatch, tmp_path, capsys):
    def unexpected(*args, **kwargs):
        pytest.fail("the diagnostic must not start the simulation/model")

    absent_output = tmp_path / "never-created"
    monkeypatch.setattr(scenario_runner, "_run_once", unexpected)
    monkeypatch.setattr(scenario_runner, "_run_monte_carlo", unexpected)
    monkeypatch.setattr(sys, "argv", ["scenario_runner", "--nested-attribution-audit",
                                     "--out", str(absent_output)])
    assert scenario_runner.main() == 0
    report = json.loads(capsys.readouterr().out)
    assert report["fixture_only"] is True and report["settlement_authority"] == "none"
    assert report["registry_edge"] == {"hpc": "voteballots"}
    assert report["direct_points"]["hpc"] == 50
    assert report["inclusive_points"] == {"voteballots": 100, "hpc": 70,
                                           "synthetic_caption_tool": 20}
    assert report["ecosystem_points"] == 100
    assert not absent_output.exists()
