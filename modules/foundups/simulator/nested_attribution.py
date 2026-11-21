"""Opt-in synthetic-only nested FoundUp measurement, not an economic ledger."""

from collections import defaultdict
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Iterable, Mapping


OUTCOME_POINTS = "verified_outcome_point"
_SIGNAL_KINDS = ("seen", "qualified")


@dataclass(frozen=True)
class Outcome:
    origin: str
    element_id: str
    credited_foundup_id: str
    unit: str
    points: int


@dataclass(frozen=True)
class Observation:
    actor: str
    foundup_id: str
    kind: str


def summarize(
    parents: Mapping[str, str | None],
    elements: Mapping[str, str],
    outcomes: Iterable[Outcome],
    observations: Iterable[Observation],
) -> dict:
    """Project one synthetic window under declared primary ancestry.

    Child reports overlap their ancestor's inclusive report. Only the disjoint
    direct points are additive ecosystem-wide. Observations do not award points.
    """
    ancestors = {}
    for foundup_id, parent in parents.items():
        tail = []
        visited = {foundup_id}
        while parent is not None:
            if parent not in parents or parent in visited:
                raise ValueError("unknown parent or containment cycle")
            visited.add(parent)
            tail.append(parent)
            parent = parents[parent]
        ancestors[foundup_id] = tail
    if any(owner not in parents for owner in elements.values()):
        raise ValueError("unregistered element owner")

    direct = dict.fromkeys(parents, 0)
    by_origin = {}
    for row in outcomes:
        if (
            not row.origin
            or row.unit != OUTCOME_POINTS
            or type(row.points) is not int
            or row.points < 0
            or row.credited_foundup_id not in parents
            or elements.get(row.element_id) != row.credited_foundup_id
        ):
            raise ValueError("invalid outcome or credit owner")
        if row.origin in by_origin:
            if by_origin[row.origin] != row:
                raise ValueError("contradictory immutable outcome")
            continue
        by_origin[row.origin] = row
        direct[row.credited_foundup_id] += row.points

    inclusive = direct.copy()
    for foundup_id, own_points in direct.items():
        for ancestor in ancestors[foundup_id]:
            inclusive[ancestor] += own_points

    actor_sets = defaultdict(set)
    ecosystem_actors = defaultdict(set)
    for observation in observations:
        if (
            not observation.actor
            or observation.foundup_id not in parents
            or observation.kind not in _SIGNAL_KINDS
        ):
            raise ValueError("invalid observation")
        actor_sets[observation.foundup_id, observation.kind].add(observation.actor)
        ecosystem_actors[observation.kind].add(observation.actor)

    return {
        "point_unit": OUTCOME_POINTS,
        "direct_points": direct,
        "inclusive_points": inclusive,
        "ecosystem_points": sum(direct.values()),
        "observations": {
            foundup_id: {kind: len(actor_sets[foundup_id, kind]) for kind in _SIGNAL_KINDS}
            for foundup_id in parents
        },
        "ecosystem_observations": {
            kind: len(ecosystem_actors[kind]) for kind in _SIGNAL_KINDS
        },
    }


def fixture_report() -> dict:
    """Reuse the existing static ancestry; all actors, outcomes and tool data are fake."""
    registry = Path(__file__).resolve().parents[1] / "foundup_registry.json"
    entities = json.loads(registry.read_text(encoding="utf-8"))["entities"]
    parents = {item["foundup_id"]: item.get("parent_foundup_id") for item in entities}
    if len(parents) != len(entities) or "voteballots" not in parents or parents.get("hpc") != "voteballots":
        raise ValueError("registry fixture ancestry changed; review its source")
    if parents["voteballots"] is not None or "synthetic_caption_tool" in parents:
        raise ValueError("registry fixture ancestry or synthetic ID changed; review its source")
    tool = "synthetic_caption_tool"
    scenario_parents = {"voteballots": None, "hpc": parents["hpc"], tool: "hpc"}
    elements = {"example-parent-work": "voteballots", "example-clip": "hpc",
                "example-tool-work": tool}
    tool_outcome = Outcome("fixture:3", "example-tool-work", tool, OUTCOME_POINTS, 20)
    outcomes = (
        Outcome("fixture:1", "example-parent-work", "voteballots", OUTCOME_POINTS, 30),
        Outcome("fixture:2", "example-clip", "hpc", OUTCOME_POINTS, 50),
        tool_outcome,
        tool_outcome,
    )
    observations = (
        Observation("fixture:viewer", "hpc", "seen"),
        Observation("fixture:member", "hpc", "seen"),
        Observation("fixture:member", "hpc", "qualified"),
        Observation("fixture:member", tool, "seen"),
        Observation("fixture:member", tool, "qualified"),
    )
    return {
        "scenario": "nested_attribution_audit",
        "scenario_version": 1,
        "fixture_only": True,
        "settlement_authority": "none",
        "registry_edge": {"hpc": parents["hpc"]},
        "synthetic_registered_tool": tool,
        **summarize(scenario_parents, elements, outcomes, observations),
    }
