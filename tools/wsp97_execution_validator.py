#!/usr/bin/env python3
"""Validate WSP 97 execution evidence receipts.

This validator checks structural completeness only. Evidence references are
treated as opaque pointers: passing validation does not prove reasoning quality,
file existence, external effects, or successful execution.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT_PATH = (
    PROJECT_ROOT
    / "WSP_framework"
    / "src"
    / "WSP_97_System_Execution_Prompting_Protocol.json"
)
VALID_OUTCOMES = frozenset({"completed", "blocked", "failed"})
TRUTH_BOUNDARY = (
    "Structural receipt completeness only; evidence references are not resolved "
    "and no reasoning quality or runtime side effect is proven."
)


def _slug(value: str) -> str:
    """Convert a display label to the receipt's snake-case key."""
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def _string_tuple(value: Any) -> tuple[str, ...]:
    """Return normalized non-empty strings from a list/tuple, else empty."""
    if not isinstance(value, (list, tuple)):
        return ()
    normalized = tuple(item.strip() for item in value if isinstance(item, str) and item.strip())
    return normalized if len(normalized) == len(value) else ()


def load_contract(path: Path | str | None = None) -> dict[str, Any]:
    """Load and validate the canonical WSP 97 machine contract."""
    contract_path = Path(path) if path is not None else DEFAULT_CONTRACT_PATH
    data = json.loads(contract_path.read_text(encoding="utf-8"))
    wsp97 = data.get("wsp_97")
    if not isinstance(wsp97, dict):
        raise ValueError("contract missing wsp_97 object")

    mantra_stages = wsp97.get("mantra_stages")
    operator_actions = wsp97.get("operator_actions")
    if not isinstance(mantra_stages, list) or not all(
        isinstance(item, str) and item.strip() for item in mantra_stages
    ):
        raise ValueError("contract mantra_stages must be a non-empty string list")
    if not isinstance(operator_actions, list) or not all(
        isinstance(item, str) and item.strip() for item in operator_actions
    ):
        raise ValueError("contract operator_actions must be a non-empty string list")
    if wsp97.get("mantra_stage_count") != len(mantra_stages):
        raise ValueError("contract mantra_stage_count does not match mantra_stages")
    if wsp97.get("operator_action_count") != len(operator_actions):
        raise ValueError("contract operator_action_count does not match operator_actions")
    if len({_slug(item) for item in mantra_stages}) != len(mantra_stages):
        raise ValueError("contract mantra_stages contain duplicate normalized keys")
    if len({_slug(item) for item in operator_actions}) != len(operator_actions):
        raise ValueError("contract operator_actions contain duplicate normalized keys")
    return data


@dataclass(frozen=True)
class WSP97ValidationResult:
    """Deterministic structural validation result for one receipt."""

    is_compliant: bool
    execution_id: str
    required_actions: tuple[str, ...]
    derived_mantra_stages: tuple[str, ...]
    missing_actions: tuple[str, ...]
    invalid_evidence_actions: tuple[str, ...]
    unexpected_actions: tuple[str, ...]
    violations: tuple[str, ...]
    truth_boundary: str = TRUTH_BOUNDARY

    def to_dict(self) -> dict[str, Any]:
        """Serialize the result for CLI and machine consumers."""
        return asdict(self)


def validate_execution_receipt(
    receipt: Mapping[str, Any],
    contract: Mapping[str, Any] | None = None,
) -> WSP97ValidationResult:
    """Validate a WSP 97 evidence receipt against the canonical contract."""
    active_contract = dict(contract) if contract is not None else load_contract()
    wsp97 = active_contract.get("wsp_97", {})
    required_actions = tuple(_slug(item) for item in wsp97.get("operator_actions", ()))
    required_stages = tuple(_slug(item) for item in wsp97.get("mantra_stages", ()))
    if not required_actions or not required_stages:
        raise ValueError("contract must define mantra_stages and operator_actions")
    if wsp97.get("operator_action_count") != len(required_actions):
        raise ValueError("contract operator_action_count does not match operator_actions")
    if wsp97.get("mantra_stage_count") != len(required_stages):
        raise ValueError("contract mantra_stage_count does not match mantra_stages")

    violations: list[str] = []
    execution_id = receipt.get("execution_id")
    if not isinstance(execution_id, str) or not execution_id.strip():
        violations.append("missing_execution_id")
        execution_id = ""
    else:
        execution_id = execution_id.strip()

    execution_plane = receipt.get("execution_plane")
    if not isinstance(execution_plane, str) or not execution_plane.strip():
        violations.append("missing_execution_plane")

    outcome = receipt.get("outcome")
    if outcome not in VALID_OUTCOMES:
        violations.append("invalid_outcome")

    raw_evidence = receipt.get("action_evidence")
    if not isinstance(raw_evidence, Mapping):
        raw_evidence = {}
        violations.append("invalid_action_evidence")

    action_keys = {key for key in raw_evidence if isinstance(key, str)}
    missing_actions = tuple(action for action in required_actions if action not in action_keys)
    invalid_evidence_actions = tuple(
        action
        for action in required_actions
        if action in action_keys and not _string_tuple(raw_evidence.get(action))
    )
    unexpected_actions = tuple(sorted(action_keys.difference(required_actions)))
    violations.extend(f"missing_action:{action}" for action in missing_actions)
    violations.extend(
        f"invalid_action_evidence:{action}" for action in invalid_evidence_actions
    )
    violations.extend(f"unexpected_action:{action}" for action in unexpected_actions)

    wsps_applied = _string_tuple(receipt.get("wsps_applied"))
    normalized_wsps = {_slug(item) for item in wsps_applied}
    if not wsps_applied:
        violations.append("missing_wsps_applied")
    elif "wsp_97" not in normalized_wsps:
        violations.append("wsp_97_not_declared")

    compliance_evidence = _string_tuple(receipt.get("compliance_evidence"))
    if not compliance_evidence:
        violations.append("missing_compliance_evidence")

    valid_actions = {
        action
        for action in required_actions
        if action in action_keys and action not in invalid_evidence_actions
    }
    stage_sources: dict[str, tuple[str, ...]] = {
        "holoindex": ("retrieve_wsps", "retrieve_evidence"),
        "research": ("research", "micro_pass", "macro_pass"),
        "hard_think": ("hard_think",),
        "dialectic_sweep": ("dialectic_sweep",),
        "first_principles": ("first_principles",),
        "build": ("execute",),
    }
    derived: list[str] = []
    for stage in required_stages:
        if stage == "follow_wsp":
            if "wsp_97" in normalized_wsps and compliance_evidence:
                derived.append(stage)
            continue
        sources = stage_sources.get(stage)
        if sources and all(source in valid_actions for source in sources):
            derived.append(stage)

    if tuple(derived) != required_stages:
        missing_stages = tuple(stage for stage in required_stages if stage not in derived)
        violations.extend(f"underived_mantra_stage:{stage}" for stage in missing_stages)

    return WSP97ValidationResult(
        is_compliant=not violations,
        execution_id=execution_id,
        required_actions=required_actions,
        derived_mantra_stages=tuple(derived),
        missing_actions=missing_actions,
        invalid_evidence_actions=invalid_evidence_actions,
        unexpected_actions=unexpected_actions,
        violations=tuple(violations),
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt", type=Path, help="Path to a JSON execution receipt")
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT_PATH)
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
        if not isinstance(receipt, dict):
            raise ValueError("receipt root must be a JSON object")
        result = validate_execution_receipt(receipt, load_contract(args.contract))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2

    print(json.dumps(result.to_dict(), indent=2 if args.pretty else None, sort_keys=True))
    return 0 if result.is_compliant else 1


if __name__ == "__main__":
    raise SystemExit(main())
