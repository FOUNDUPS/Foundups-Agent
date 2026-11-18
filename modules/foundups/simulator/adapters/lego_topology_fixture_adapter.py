"""Opt-in Lego topology fixture adapter for FoundUps simulator contracts.

Evaluates deterministic tick-by-tick FoundUp composition readiness over frozen
Lego block dependency fixtures and projects stage caps onto `SimState` without
creating a parallel simulation engine or mutating simulator defaults.
"""

from __future__ import annotations

import hashlib
import heapq
import json
from dataclasses import dataclass
from typing import Any, Mapping, NamedTuple, NoReturn, Optional, Sequence

from ..config import SimulatorConfig
from ..parameter_registry import ParameterBundle, load_bundle, to_simulator_config
from ..state_contracts import STAGE_TO_INT, ActorState, FoundUpState, FrozenDict, PoolState, SimState
from ..step_pure import StepParams, step as pure_sim_step

TRACE_SCHEMA_VERSION = "lego_topology_sim_trace_v1"
SIMULATED_EVIDENCE_ORIGIN = "SIMULATED_TRANSITION_ONLY"
AGI_SCAFFOLDING_HYPOTHESIS_STATUS = "HYPOTHESIS_UNDER_TEST"
FORBIDDEN_RUNTIME_PROMOTION_ERROR = "simulated_transitions_never_create_runtime_verification_evidence"

BLOCKED_UPSTREAM_DEPENDENCY = "BLOCKED_UPSTREAM_DEPENDENCY"
BLOCKED_DEPENDENCY_CYCLE = "BLOCKED_DEPENDENCY_CYCLE"
BLOCKED_MISSING_BLOCK = "BLOCKED_MISSING_BLOCK"
BLOCKED_UNKNOWN_CONSUMER = "UNKNOWN_DYNAMIC_OR_EXTERNAL_CONSUMER"
BLOCKED_STALE_PROVENANCE = "STALE_PROVENANCE_MISMATCH"
_READY_INPUT_STATES = frozenset({"READY", "SIMULATED_READY", "VERIFIED_CAPABILITY", "VERIFIED_READY"})


def _require_exact_bool(value: Any, field_name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{field_name} must be an exact bool")
    return value


def _enforce_simulated_only_metadata(origin: Any, eligible: Any, status: Any) -> None:
    if origin != SIMULATED_EVIDENCE_ORIGIN or type(eligible) is not bool or eligible is not False or status != AGI_SCAFFOLDING_HYPOTHESIS_STATUS:
        raise ValueError(FORBIDDEN_RUNTIME_PROMOTION_ERROR)


def export_for_runtime_verification(artifact: Any, *, target_status: str = "VERIFIED_RUNTIME") -> NoReturn:
    """Hard barrier: simulated transitions never export as runtime verification."""
    del artifact, target_status
    raise ValueError(FORBIDDEN_RUNTIME_PROMOTION_ERROR)


def guard_no_simulated_runtime_promotion(
    artifact: Any, *, requested_origin: Optional[str] = None, requested_runtime_eligible: bool = False
) -> None:
    """Reject any attempt to relabel simulated transitions as runtime truth."""
    if _require_exact_bool(requested_runtime_eligible, "requested_runtime_eligible") or (
        requested_origin is not None and requested_origin != SIMULATED_EVIDENCE_ORIGIN
    ):
        raise ValueError(FORBIDDEN_RUNTIME_PROMOTION_ERROR)
    get = artifact.get if isinstance(artifact, Mapping) else lambda k: getattr(artifact, k, None)
    _enforce_simulated_only_metadata(get("evidence_origin"), get("runtime_verification_eligible"), get("agi_scaffolding_hypothesis_status"))


@dataclass(frozen=True)
class LegoTopologyAdapterConfig:
    enabled: bool = False
    scenario: str = "baseline"
    seed: int = 42

    def __post_init__(self) -> None:
        _require_exact_bool(self.enabled, "enabled")
        if not isinstance(self.scenario, str) or not self.scenario or type(self.seed) is not int:
            raise ValueError("invalid scenario or seed")


@dataclass(frozen=True, kw_only=True)
class _SimulatedArtifactBase:
    evidence_origin: str = SIMULATED_EVIDENCE_ORIGIN
    runtime_verification_eligible: bool = False
    agi_scaffolding_hypothesis_status: str = AGI_SCAFFOLDING_HYPOTHESIS_STATUS

    def __post_init__(self) -> None:
        _enforce_simulated_only_metadata(self.evidence_origin, self.runtime_verification_eligible, self.agi_scaffolding_hypothesis_status)


@dataclass(frozen=True)
class SimulatedTransitionRecord(_SimulatedArtifactBase):
    tick: int
    ticket_id: str
    target_id: str
    transition_kind: str
    detail: str

    def to_trace_dict(self) -> dict[str, Any]:
        return {"ticket_id": self.ticket_id, "target_id": self.target_id, "transition_kind": self.transition_kind, "detail": self.detail, "evidence_origin": self.evidence_origin, "runtime_verification_eligible": self.runtime_verification_eligible}


@dataclass(frozen=True)
class BlockSimulationState(_SimulatedArtifactBase):
    canonical_id: str
    depends_on_block_ids: tuple[str, ...]
    preserved_verified_capabilities: tuple[str, ...]
    preserved_input_provenance: FrozenDict[str, Any]
    simulated_only_capabilities: tuple[str, ...]
    simulated_satisfied_capabilities: tuple[str, ...]
    structurally_ready: bool
    effective_ready: bool
    blocking_reasons: tuple[str, ...]


@dataclass(frozen=True)
class FoundUpCompositionProjection(_SimulatedArtifactBase):
    foundup_id: str
    required_block_ids: tuple[str, ...]
    ready_block_ids: tuple[str, ...]
    required_capabilities: tuple[str, ...]
    simulated_satisfied_capabilities: tuple[str, ...]
    preserved_verified_capabilities: tuple[str, ...]
    blocking_reasons: tuple[str, ...]
    stage_cap_name: str
    stage_cap_int: int

    def to_trace_dict(self) -> dict[str, Any]:
        return {"stage_cap_name": self.stage_cap_name, "stage_cap_int": self.stage_cap_int, "ready_block_ids": list(self.ready_block_ids), "simulated_satisfied_capabilities": list(self.simulated_satisfied_capabilities), "preserved_verified_capabilities": list(self.preserved_verified_capabilities), "blocking_reasons": list(self.blocking_reasons)}


@dataclass(frozen=True)
class LegoTickSnapshot(_SimulatedArtifactBase):
    tick: int
    blocks: FrozenDict[str, BlockSimulationState]
    foundup_projections: FrozenDict[str, FoundUpCompositionProjection]
    transitions: tuple[SimulatedTransitionRecord, ...]
    sim_state: SimState


@dataclass(frozen=True)
class LegoTopologySimulationResult(_SimulatedArtifactBase):
    scenario: str
    seed: int
    snapshots: tuple[LegoTickSnapshot, ...]
    final_sim_state: SimState
    canonical_trace_json: str
    simulation_trace_sha256: str


_BlockSpec = NamedTuple("_BlockSpec", [("canonical_id", str), ("depends_on", tuple[str, ...]), ("preserved_verified_caps", tuple[str, ...]), ("initial_sim_caps", tuple[str, ...]), ("preserved_provenance", FrozenDict[str, Any]), ("initial_ready", bool), ("stale_provenance", bool), ("unknown_consumer", bool)])
_FoundUpSpec = NamedTuple("_FoundUpSpec", [("foundup_id", str), ("required_block_ids", tuple[str, ...]), ("required_capabilities", tuple[str, ...])])


def resolve_adapter_config(
    bundle: Optional[ParameterBundle] = None, *, simulator_config: Optional[SimulatorConfig] = None, enabled: Optional[bool] = None
) -> LegoTopologyAdapterConfig:
    """Resolve opt-in adapter config without altering simulator defaults."""
    resolved = bundle if bundle is not None else load_bundle("baseline")
    cfg = simulator_config if simulator_config is not None else to_simulator_config(resolved)
    raw_enabled = resolved.params.get("lego_topology_enabled", False) if enabled is None else enabled
    return LegoTopologyAdapterConfig(_require_exact_bool(raw_enabled, "enabled"), resolved.scenario, int(cfg.seed))


def _normalize_cap_list(raw_caps: Any, owner_block_id: Optional[str] = None) -> tuple[str, ...]:
    if raw_caps is None:
        return ()
    if isinstance(raw_caps, Mapping):
        return tuple(sorted({f"{b}:{c}" if ":" not in c else c for b, cs in raw_caps.items() for c in _normalize_cap_list(cs)}))
    if isinstance(raw_caps, (str, bytes)) or not isinstance(raw_caps, Sequence):
        raise ValueError("capabilities must be a sequence or mapping")
    result: set[str] = set()
    for item in raw_caps:
        if isinstance(item, str) and item:
            result.add(f"{owner_block_id}:{item}" if owner_block_id and ":" not in item else item)
        elif isinstance(item, Mapping):
            if item.get("evidence_origin") == SIMULATED_EVIDENCE_ORIGIN:
                raise ValueError(FORBIDDEN_RUNTIME_PROMOTION_ERROR)
            cap_id = str(item.get("capability_id") or "").strip()
            if cap_id and str(item.get("status") or "VERIFIED_CAPABILITY") != BLOCKED_STALE_PROVENANCE:
                result.add(cap_id)
        else:
            raise ValueError("invalid capability entry")
    return tuple(sorted(result))


def _normalize_topology_fixture(fixture: Mapping[str, Any]) -> tuple[dict[str, _BlockSpec], dict[str, _FoundUpSpec]]:
    if not isinstance(fixture, Mapping):
        raise ValueError("fixture must be a mapping")
    import_deps: dict[str, set[str]] = {}
    rel_fup_blocks: dict[str, set[str]] = {}
    rel_fup_caps: dict[str, set[str]] = {}
    for rel in fixture.get("relations") or fixture.get("catalog_relations") or ():
        if not isinstance(rel, Mapping):
            raise ValueError("relation entry must be a mapping")
        rtype = str(rel.get("relation_type") or rel.get("kind") or "")
        src = str(rel.get("source_id") or rel.get("foundup_id") or "").strip()
        tgt = str(rel.get("target_id") or rel.get("block_id") or "").strip()
        if rtype == "BLOCK_IMPORTS_BLOCK" and src and tgt:
            import_deps.setdefault(src, set()).add(tgt)
        elif rtype == "FOUNDUP_TO_MODULE" and src:
            req_blks = rel_fup_blocks.setdefault(src, set())
            if tgt:
                req_blks.add(tgt)
            req_blks.update(str(b_id) for b_id in (rel.get("required_block_ids") or ()))
            rel_fup_caps.setdefault(src, set()).update(_normalize_cap_list(rel.get("required_capabilities")))

    raw_blocks = fixture.get("blocks") or ()
    block_items = [{**v, "canonical_id": v.get("canonical_id", k)} for k, v in raw_blocks.items()] if isinstance(raw_blocks, Mapping) else list(raw_blocks)
    blocks: dict[str, _BlockSpec] = {}
    for raw in block_items:
        if not isinstance(raw, Mapping):
            raise ValueError("block entry must be a mapping")
        identity = raw.get("identity") if isinstance(raw.get("identity"), Mapping) else {}
        cid = str(raw.get("canonical_id") or identity.get("canonical_id") or "").strip()
        if not cid or cid in blocks:
            raise ValueError(f"invalid or duplicate block canonical_id: {cid!r}")
        deps = {str(d) for d in (raw.get("depends_on_block_ids") or ())} | import_deps.get(cid, set())
        verified_raw = raw.get("verified_capabilities") or ()
        cap_statuses = raw.get("capability_statuses")
        status_verified = [r for r in cap_statuses if isinstance(r, Mapping) and r.get("status") == "VERIFIED_CAPABILITY"] if isinstance(cap_statuses, Sequence) and not isinstance(cap_statuses, (str, bytes)) else []
        preserved_verified = tuple(sorted(set(_normalize_cap_list(verified_raw)) | set(_normalize_cap_list(status_verified))))
        has_stale_cap = (isinstance(cap_statuses, Mapping) and BLOCKED_STALE_PROVENANCE in cap_statuses.values()) or (isinstance(cap_statuses, Sequence) and not isinstance(cap_statuses, (str, bytes)) and any(isinstance(r, Mapping) and r.get("status") == BLOCKED_STALE_PROVENANCE for r in cap_statuses))
        has_stale_rcpt = isinstance(verified_raw, Sequence) and any(isinstance(r, Mapping) and r.get("status") == BLOCKED_STALE_PROVENANCE for r in verified_raw)
        readiness = str(raw.get("readiness_state") or "").strip()
        stale = raw.get("provenance_status") == BLOCKED_STALE_PROVENANCE or readiness == BLOCKED_STALE_PROVENANCE or has_stale_cap or has_stale_rcpt
        triage = raw.get("triage") if isinstance(raw.get("triage"), Mapping) else {}
        triage_cls = str(raw.get("triage_status") or triage.get("classification") or triage.get("status") or "")
        init_ready = _require_exact_bool(raw["initial_ready"], "initial_ready") if "initial_ready" in raw else (readiness in _READY_INPUT_STATES if readiness else (bool(preserved_verified) and not stale))
        prov_meta = raw.get("byte_provenance") or raw.get("provenance") or {}
        blocks[cid] = _BlockSpec(
            cid, tuple(sorted(deps)), preserved_verified, _normalize_cap_list(raw.get("initial_capabilities") or ()),
            FrozenDict(dict(prov_meta) if isinstance(prov_meta, Mapping) else {}), init_ready, stale, triage_cls == BLOCKED_UNKNOWN_CONSUMER,
        )

    raw_fups = fixture.get("foundups") or ()
    fup_entries = [{"foundup_id": k, **v} for k, v in raw_fups.items()] if isinstance(raw_fups, Mapping) else list(raw_fups)
    fup_by_id = {str(e.get("foundup_id") or "").strip(): e for e in fup_entries if isinstance(e, Mapping)}
    foundups: dict[str, _FoundUpSpec] = {}
    for fid in sorted(f for f in (set(rel_fup_blocks) | set(fup_by_id)) if f):
        entry = fup_by_id.get(fid, {})
        req_blocks = {str(b) for b in (entry.get("required_block_ids") or ())} | rel_fup_blocks.get(fid, set())
        req_caps = set(_normalize_cap_list(entry.get("required_capabilities"))) | rel_fup_caps.get(fid, set())
        foundups[fid] = _FoundUpSpec(fid, tuple(sorted(req_blocks)), tuple(sorted(req_caps)))
    return blocks, foundups


def _kahn_topological_order(blocks: Mapping[str, _BlockSpec]) -> tuple[list[str], set[str]]:
    in_degree = {bid: 0 for bid in blocks}
    dependents: dict[str, list[str]] = {bid: [] for bid in blocks}
    for bid, spec in blocks.items():
        for dep in spec.depends_on:
            if dep in blocks:
                in_degree[bid] += 1
                dependents[dep].append(bid)
    heap = [bid for bid, deg in in_degree.items() if deg == 0]
    heapq.heapify(heap)
    order: list[str] = []
    while heap:
        curr = heapq.heappop(heap)
        order.append(curr)
        for nxt in sorted(dependents[curr]):
            in_degree[nxt] -= 1
            if in_degree[nxt] == 0:
                heapq.heappush(heap, nxt)
    return order, set(order)


def _cap_satisfied(req_cap: str, req_blocks: Sequence[str], bstates: Mapping[str, BlockSimulationState]) -> bool:
    if ":" in req_cap:
        blk_id, local_cap = req_cap.split(":", 1)
        bs = bstates.get(blk_id)
        return bool(bs and bs.effective_ready and (local_cap in bs.simulated_satisfied_capabilities or req_cap in bs.simulated_satisfied_capabilities))
    return any(req_cap in bstates[b].simulated_satisfied_capabilities for b in req_blocks if b in bstates and bstates[b].effective_ready)


def _evaluate_tick_state(
    blocks: Mapping[str, _BlockSpec], foundups: Mapping[str, _FoundUpSpec], ready_flags: Mapping[str, bool],
    stale_flags: Mapping[str, bool], unknown_flags: Mapping[str, bool], sim_caps: Mapping[str, set[str]],
    topo_order: Sequence[str], acyclic_ids: set[str],
) -> tuple[dict[str, BlockSimulationState], dict[str, FoundUpCompositionProjection]]:
    bstates: dict[str, BlockSimulationState] = {}
    for bid in list(topo_order) + sorted(b for b in blocks if b not in acyclic_ids):
        spec = blocks[bid]
        reasons = {
            r for r, flag in (
                (BLOCKED_MISSING_BLOCK, any(dep not in blocks for dep in spec.depends_on)),
                (BLOCKED_DEPENDENCY_CYCLE, bid not in acyclic_ids),
                (BLOCKED_STALE_PROVENANCE, stale_flags[bid]),
                (BLOCKED_UNKNOWN_CONSUMER, unknown_flags[bid]),
            ) if flag
        }
        if bid in acyclic_ids:
            for dep in spec.depends_on:
                if dep in bstates and not bstates[dep].effective_ready:
                    reasons.add(BLOCKED_UPSTREAM_DEPENDENCY)
                    reasons.update(r for r in bstates[dep].blocking_reasons if r != BLOCKED_UPSTREAM_DEPENDENCY)
        eff_ready = ready_flags[bid] and not reasons
        satisfied = tuple(sorted(set(spec.preserved_verified_caps) | set(spec.initial_sim_caps) | sim_caps[bid])) if eff_ready else ()
        bstates[bid] = BlockSimulationState(bid, spec.depends_on, spec.preserved_verified_caps, spec.preserved_provenance, tuple(sorted(sim_caps[bid])), satisfied, ready_flags[bid], eff_ready, tuple(sorted(reasons)))

    projs: dict[str, FoundUpCompositionProjection] = {}
    for fid, fspec in sorted(foundups.items()):
        f_reasons: set[str] = {BLOCKED_MISSING_BLOCK} if any(b not in bstates for b in fspec.required_block_ids) else set()
        present_bs = [bstates[b] for b in fspec.required_block_ids if b in bstates]
        for bs in present_bs:
            f_reasons.update(bs.blocking_reasons)
        preserved_caps = {f"{bs.canonical_id}:{c}" if ":" not in c else c for bs in present_bs for c in bs.preserved_verified_capabilities}
        ready_blks = tuple(bs.canonical_id for bs in present_bs if bs.effective_ready)
        sat_caps = tuple(c for c in fspec.required_capabilities if _cap_satisfied(c, fspec.required_block_ids, bstates))
        if not fspec.required_block_ids or BLOCKED_DEPENDENCY_CYCLE in f_reasons or BLOCKED_MISSING_BLOCK in f_reasons or not ready_blks:
            stage = "Idea"
        elif len(ready_blks) < len(fspec.required_block_ids) or f_reasons:
            stage = "PoC"
        else:
            stage = "Proto" if len(sat_caps) < len(fspec.required_capabilities) else "MVP"
        projs[fid] = FoundUpCompositionProjection(fid, fspec.required_block_ids, ready_blks, fspec.required_capabilities, sat_caps, tuple(sorted(preserved_caps)), tuple(sorted(f_reasons)), stage, STAGE_TO_INT[stage])
    return bstates, projs


def apply_stage_caps_to_sim_state(
    sim_state: SimState, projections: Mapping[str, FoundUpCompositionProjection], *, enabled: bool = False
) -> Optional[SimState]:
    """Project Lego readiness stage caps onto an immutable `SimState`."""
    if not _require_exact_bool(enabled, "enabled"):
        return None
    next_fups = dict(sim_state.foundups.items())
    for fid, proj in sorted(projections.items()):
        ex = next_fups.get(fid)
        next_fups[fid] = FoundUpState(fid, proj.stage_cap_int, 0.0, 0.0, sim_state.btc_reserve_total) if ex is None else FoundUpState(ex.id, min(ex.stage, proj.stage_cap_int), ex.total_tokens, ex.cabr_score, ex.btc_reserve)
    return SimState(sim_state.tick, FrozenDict(dict(sim_state.actors.items())), FrozenDict(next_fups), sim_state.pools, sim_state.btc_reserve_total, sim_state.fi_released_total)


def run_lego_topology_simulation(
    fixture: Mapping[str, Any], *, enabled: bool = False, ticks: int = 1,
    completed_tickets_by_tick: Optional[Mapping[int, Sequence[Mapping[str, Any]]]] = None,
    base_sim_state: Optional[SimState] = None, step_params: Optional[StepParams] = None, bundle: Optional[ParameterBundle] = None,
) -> Optional[LegoTopologySimulationResult]:
    """Run opt-in deterministic tick-by-tick Lego composition simulation."""
    cfg = resolve_adapter_config(bundle, enabled=enabled)
    if not cfg.enabled:
        return None
    if type(ticks) is not int or ticks < 0:
        raise ValueError("ticks must be a non-negative integer")
    blocks, foundups = _normalize_topology_fixture(fixture)
    topo_order, acyclic_ids = _kahn_topological_order(blocks)
    ready_flags = {bid: spec.initial_ready for bid, spec in blocks.items()}
    stale_flags = {bid: spec.stale_provenance for bid, spec in blocks.items()}
    unknown_flags = {bid: spec.unknown_consumer for bid, spec in blocks.items()}
    sim_caps: dict[str, set[str]] = {bid: set() for bid in blocks}
    schedule: dict[int, list[Mapping[str, Any]]] = {}
    for raw_t in fixture.get("simulated_tickets") or ():
        if not isinstance(raw_t, Mapping) or type(raw_t.get("tick")) is not int or raw_t["tick"] < 0:
            raise ValueError("invalid simulated ticket")
        schedule.setdefault(raw_t["tick"], []).append(raw_t)
    for t_idx, items in (completed_tickets_by_tick or {}).items():
        if type(t_idx) is not int or t_idx < 0:
            raise ValueError("ticket tick must be a non-negative integer")
        schedule.setdefault(t_idx, []).extend(items)

    curr_sim = base_sim_state or SimState(0, FrozenDict[str, ActorState]({}), FrozenDict({fid: FoundUpState(fid, STAGE_TO_INT["Launch"], 0.0, 0.0, 0.0) for fid in sorted(foundups)}), PoolState(0.0, 0.0, 0.0, 0.0, 0.0), 0.0, 0.0)
    sparams = step_params or StepParams()
    snapshots: list[LegoTickSnapshot] = []
    prev_stages: dict[str, int] = {}
    for step_idx in range(ticks + 1):
        if step_idx > 0:
            curr_sim = pure_sim_step(curr_sim, sparams)
        tnum = curr_sim.tick
        transitions: list[SimulatedTransitionRecord] = []
        for ticket in sorted(schedule.get(tnum, ()), key=lambda item: str(item.get("ticket_id", ""))):
            tid, bid = str(ticket.get("ticket_id") or f"sim_ticket_{tnum}"), str(ticket.get("block_id") or "").strip()
            if bid not in blocks:
                continue
            if ticket.get("clears_stale_provenance") and stale_flags[bid]:
                stale_flags[bid] = False
                transitions.append(SimulatedTransitionRecord(tnum, tid, bid, "PROVENANCE_SIMULATED_REFRESH", "cleared_stale_provenance"))
            if ticket.get("clears_unknown_consumer") and unknown_flags[bid]:
                unknown_flags[bid] = False
                transitions.append(SimulatedTransitionRecord(tnum, tid, bid, "CONSUMER_TRIAGE_SIMULATED_CLEAR", "cleared_unknown_consumer"))
            if ticket.get("sets_block_ready", True) and not ready_flags[bid]:
                ready_flags[bid] = True
                transitions.append(SimulatedTransitionRecord(tnum, tid, bid, "BLOCK_SIMULATED_READY", "marked_structurally_ready"))
            for cap in _normalize_cap_list(ticket.get("satisfies_capabilities")):
                if cap not in sim_caps[bid]:
                    sim_caps[bid].add(cap)
                    transitions.append(SimulatedTransitionRecord(tnum, tid, bid, "CAPABILITY_SIMULATED", cap))
        bstates, projs = _evaluate_tick_state(blocks, foundups, ready_flags, stale_flags, unknown_flags, sim_caps, topo_order, acyclic_ids)
        for fid, proj in sorted(projs.items()):
            if prev_stages.get(fid) != proj.stage_cap_int:
                transitions.append(SimulatedTransitionRecord(tnum, f"stage_eval_{tnum}", fid, "FOUNDUP_STAGE_CAP_CHANGED", proj.stage_cap_name))
                prev_stages[fid] = proj.stage_cap_int
        projected_sim = apply_stage_caps_to_sim_state(curr_sim, projs, enabled=True)
        assert projected_sim is not None
        snapshots.append(LegoTickSnapshot(tnum, FrozenDict(bstates), FrozenDict(projs), tuple(transitions), projected_sim))

    ticks_trace = [
        {"tick": s.tick, "evidence_origin": s.evidence_origin, "runtime_verification_eligible": s.runtime_verification_eligible, "foundups": {fid: p.to_trace_dict() for fid, p in sorted(s.foundup_projections.items())}, "sim_state_stages": {fid: f.stage for fid, f in sorted(s.sim_state.foundups.items())}, "transitions": [tr.to_trace_dict() for tr in s.transitions]}
        for s in snapshots
    ]
    trace_obj = {"schema_version": TRACE_SCHEMA_VERSION, "scenario": cfg.scenario, "seed": cfg.seed, "evidence_origin": SIMULATED_EVIDENCE_ORIGIN, "runtime_verification_eligible": False, "agi_scaffolding_hypothesis_status": AGI_SCAFFOLDING_HYPOTHESIS_STATUS, "ticks": ticks_trace}
    canonical_json = json.dumps(trace_obj, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return LegoTopologySimulationResult(cfg.scenario, cfg.seed, tuple(snapshots), snapshots[-1].sim_state, canonical_json, hashlib.sha256(canonical_json.encode("utf-8")).hexdigest())
