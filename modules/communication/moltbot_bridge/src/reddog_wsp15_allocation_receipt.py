"""Deterministic RedDog WSP 15 allocation receipts.

This module converts a work focus into a WSP 15 MPS allocation receipt that
downstream RedDog/OpenClaw planning can bind to without relying on hand-written
priority fields. It performs no model calls, worker dispatch, queue mutation,
shell execution, or HoloIndex indexing.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence


SCHEMA_VERSION = "reddog_wsp15_allocation_receipt.v1"

PRIORITY_P0 = "P0"
PRIORITY_P1 = "P1"
PRIORITY_P2 = "P2"
PRIORITY_P3 = "P3"
PRIORITY_P4 = "P4"

REASONING_REGULAR = "REGULAR"
REASONING_HIGH = "HIGH"
REASONING_ULTRA = "ULTRA"

_ULTRA_KEYWORDS = (
    "authority",
    "auth",
    "credential",
    "hermes",
    "live",
    "main.py",
    "merge",
    "openclaw",
    "redaction",
    "reddog",
    "security",
    "signature",
    "sovereign",
    "token",
    "valve",
    "worktree",
    "wre",
)

_URGENCY_KEYWORDS = (
    "block",
    "blocked",
    "critical",
    "fail",
    "fix",
    "main startup",
    "operational",
    "runtime",
    "startup",
)

_SYSTEM_KEYWORDS = (
    "agentdb",
    "brain",
    "breadcrumb",
    "fusion",
    "holoindex",
    "main",
    "queue",
    "wsp",
)


@dataclass(frozen=True)
class RedDogWSP15AllocationReceipt:
    """WSP 15 allocation receipt for one RedDog work focus."""

    schema_version: str
    receipt_id: str
    input_digest: str
    requested_operation: str
    prompt_digest: str
    changed_paths: tuple[str, ...]
    allowed_read_targets: tuple[str, ...]
    complexity: int
    importance: int
    deferability: int
    impact: int
    mps_total: int
    priority: str
    reasoning_tier: str
    worker_plan: Mapping[str, Any]
    scoring_rationale: Mapping[str, str]
    wsp_refs: tuple[str, ...] = ("WSP_15", "WSP_97")
    wsp97_label: str = "INFERRED"
    scoring_method: str = "deterministic_wsp15_runtime_heuristic"
    no_model_call_performed: bool = True
    no_worker_spawn_performed: bool = True
    no_queue_mutation_performed: bool = True
    no_repo_mutation_performed: bool = True
    no_holoindex_reindex_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def allocate_reddog_wsp15_receipt(
    *,
    requested_operation: str,
    prompt_text: str,
    changed_paths: Sequence[str] = (),
    allowed_read_targets: Sequence[str] = (),
) -> RedDogWSP15AllocationReceipt:
    """Allocate a deterministic WSP 15 receipt for a RedDog work focus."""

    paths = _normalize_paths(changed_paths)
    targets = _normalize_paths(allowed_read_targets)
    corpus = _corpus(
        requested_operation=requested_operation,
        prompt_text=prompt_text,
        changed_paths=paths,
        allowed_read_targets=targets,
    )
    path_count = len(tuple(dict.fromkeys((*paths, *targets))))
    ultra_hit = _contains_any(corpus, _ULTRA_KEYWORDS)
    urgency_hit = _contains_any(corpus, _URGENCY_KEYWORDS)
    system_hit = _contains_any(corpus, _SYSTEM_KEYWORDS)

    complexity = _score_complexity(path_count=path_count, corpus=corpus, ultra_hit=ultra_hit)
    importance = _score_importance(ultra_hit=ultra_hit, system_hit=system_hit, path_count=path_count)
    deferability = _score_deferability(ultra_hit=ultra_hit, urgency_hit=urgency_hit)
    impact = _score_impact(ultra_hit=ultra_hit, system_hit=system_hit, urgency_hit=urgency_hit)
    mps_total = complexity + importance + deferability + impact
    priority = _priority_for_total(mps_total)
    reasoning_tier = _reasoning_tier(priority=priority, ultra_hit=ultra_hit, path_count=path_count)
    worker_plan = _worker_plan(priority=priority, reasoning_tier=reasoning_tier, ultra_hit=ultra_hit)
    scoring_rationale = {
        "complexity": _complexity_rationale(path_count=path_count, ultra_hit=ultra_hit),
        "importance": _importance_rationale(ultra_hit=ultra_hit, system_hit=system_hit),
        "deferability": _deferability_rationale(ultra_hit=ultra_hit, urgency_hit=urgency_hit),
        "impact": _impact_rationale(ultra_hit=ultra_hit, system_hit=system_hit, urgency_hit=urgency_hit),
    }
    input_payload = {
        "schema_version": SCHEMA_VERSION,
        "requested_operation": str(requested_operation or ""),
        "prompt_digest": _digest(str(prompt_text or "")),
        "changed_paths": paths,
        "allowed_read_targets": targets,
        "complexity": complexity,
        "importance": importance,
        "deferability": deferability,
        "impact": impact,
        "mps_total": mps_total,
        "priority": priority,
        "reasoning_tier": reasoning_tier,
        "worker_plan": worker_plan,
        "scoring_method": "deterministic_wsp15_runtime_heuristic",
    }
    input_digest = _digest(input_payload)
    return RedDogWSP15AllocationReceipt(
        schema_version=SCHEMA_VERSION,
        receipt_id=_digest({"receipt": input_digest, "type": SCHEMA_VERSION}),
        input_digest=input_digest,
        requested_operation=str(requested_operation or ""),
        prompt_digest=_digest(str(prompt_text or "")),
        changed_paths=paths,
        allowed_read_targets=targets,
        complexity=complexity,
        importance=importance,
        deferability=deferability,
        impact=impact,
        mps_total=mps_total,
        priority=priority,
        reasoning_tier=reasoning_tier,
        worker_plan=worker_plan,
        scoring_rationale=scoring_rationale,
    )


def _score_complexity(*, path_count: int, corpus: str, ultra_hit: bool) -> int:
    if ultra_hit or "runtime" in corpus or "integration" in corpus:
        return 5
    if path_count >= 6:
        return 4
    if path_count >= 3:
        return 3
    if path_count >= 1:
        return 2
    return 1


def _score_importance(*, ultra_hit: bool, system_hit: bool, path_count: int) -> int:
    if ultra_hit:
        return 5
    if system_hit:
        return 4
    if path_count >= 1:
        return 3
    return 2


def _score_deferability(*, ultra_hit: bool, urgency_hit: bool) -> int:
    if ultra_hit and urgency_hit:
        return 5
    if ultra_hit or urgency_hit:
        return 4
    return 3


def _score_impact(*, ultra_hit: bool, system_hit: bool, urgency_hit: bool) -> int:
    if ultra_hit and (system_hit or urgency_hit):
        return 5
    if ultra_hit or system_hit:
        return 4
    return 3


def _priority_for_total(total: int) -> str:
    if total >= 16:
        return PRIORITY_P0
    if total >= 13:
        return PRIORITY_P1
    if total >= 10:
        return PRIORITY_P2
    if total >= 7:
        return PRIORITY_P3
    return PRIORITY_P4


def _reasoning_tier(*, priority: str, ultra_hit: bool, path_count: int) -> str:
    if priority == PRIORITY_P0 or ultra_hit:
        return REASONING_ULTRA
    if priority in {PRIORITY_P1, PRIORITY_P2} or path_count >= 3:
        return REASONING_HIGH
    return REASONING_REGULAR


def _worker_plan(*, priority: str, reasoning_tier: str, ultra_hit: bool) -> Mapping[str, Any]:
    critic_count = 0
    if reasoning_tier == REASONING_ULTRA:
        critic_count = 2
    elif reasoning_tier == REASONING_HIGH:
        critic_count = 1
    return {
        "schema_version": "reddog_wsp15_worker_plan.v1",
        "fusion_required": reasoning_tier in {REASONING_HIGH, REASONING_ULTRA},
        "reasoning_tier": reasoning_tier,
        "critic_count": critic_count,
        "coding_worker_count": 2 if priority == PRIORITY_P0 else (1 if priority in {PRIORITY_P1, PRIORITY_P2} else 0),
        "independent_verifier_required": priority in {PRIORITY_P0, PRIORITY_P1} or ultra_hit,
        "openclaw_candidate": priority in {PRIORITY_P0, PRIORITY_P1},
        "hermes_execution_allowed": False,
        "queue_mutation_allowed": False,
        "mode_selection_source": SCHEMA_VERSION,
    }


def _complexity_rationale(*, path_count: int, ultra_hit: bool) -> str:
    if ultra_hit:
        return "Very high because the work focus touches RedDog/WRE/security/runtime authority terms."
    return f"Derived from {path_count} unique repo targets and no authority-sensitive keyword hit."


def _importance_rationale(*, ultra_hit: bool, system_hit: bool) -> str:
    if ultra_hit:
        return "Essential because authority-sensitive RedDog/WRE terms are present."
    if system_hit:
        return "Critical because system governance or memory terms are present."
    return "Important but not core-authority-sensitive."


def _deferability_rationale(*, ultra_hit: bool, urgency_hit: bool) -> str:
    if ultra_hit and urgency_hit:
        return "Cannot defer because authority-sensitive and blocking/operational terms are present."
    if ultra_hit or urgency_hit:
        return "Difficult to defer because either authority or urgency terms are present."
    return "Moderate deferability."


def _impact_rationale(*, ultra_hit: bool, system_hit: bool, urgency_hit: bool) -> str:
    if ultra_hit and (system_hit or urgency_hit):
        return "Transformative operational impact for RedDog/WRE governance."
    if ultra_hit or system_hit:
        return "Major system impact."
    return "Moderate impact."


def _contains_any(text: str, needles: Sequence[str]) -> bool:
    return any(needle in text for needle in needles)


def _corpus(
    *,
    requested_operation: str,
    prompt_text: str,
    changed_paths: Sequence[str],
    allowed_read_targets: Sequence[str],
) -> str:
    return " ".join(
        (
            str(requested_operation or ""),
            str(prompt_text or ""),
            " ".join(str(path) for path in changed_paths),
            " ".join(str(path) for path in allowed_read_targets),
        )
    ).lower()


def _normalize_paths(paths: Sequence[str]) -> tuple[str, ...]:
    normalized: list[str] = []
    for value in paths:
        text = str(value or "").replace("\\", "/").strip()
        while text.startswith("./"):
            text = text[2:]
        if text and not text.startswith("/") and not text.startswith("../") and "/../" not in text:
            normalized.append(text)
    return tuple(dict.fromkeys(normalized))


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def _digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


__all__ = [
    "PRIORITY_P0",
    "PRIORITY_P1",
    "PRIORITY_P2",
    "PRIORITY_P3",
    "PRIORITY_P4",
    "REASONING_HIGH",
    "REASONING_REGULAR",
    "REASONING_ULTRA",
    "RedDogWSP15AllocationReceipt",
    "allocate_reddog_wsp15_receipt",
]
