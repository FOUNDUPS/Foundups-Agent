#!/usr/bin/env python3
"""Validate repository-bound WSP 97 execution evidence receipts."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

try:
    from tools.wsp97_repository_evidence import (
        COMMIT_PATTERN,
        GIT_TIMEOUT_SECONDS,
        MAX_ACCEPTED_GIT_OUTPUT_BYTES,
        MAX_GIT_CALLS,
        WSP_ID_PATTERN,
        lexical_wsp_id,
        validate_repository_evidence,
    )
except ModuleNotFoundError:  # Direct ``python tools/...`` execution.
    from wsp97_repository_evidence import (
        COMMIT_PATTERN,
        GIT_TIMEOUT_SECONDS,
        MAX_ACCEPTED_GIT_OUTPUT_BYTES,
        MAX_GIT_CALLS,
        WSP_ID_PATTERN,
        lexical_wsp_id,
        validate_repository_evidence,
    )


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT_PATH = (
    PROJECT_ROOT
    / "WSP_framework"
    / "src"
    / "WSP_97_System_Execution_Prompting_Protocol.json"
)
RECEIPT_SCHEMA_VERSION = "wsp97_execution_receipt.v1.1"
MAX_RECEIPT_BYTES = 262_144
MAX_RECEIPT_MAPPING_ITEMS = 32
MAX_REPOSITORY_CONTEXT_ITEMS = 8
MAX_ACTION_EVIDENCE_MAPPING_ITEMS = 32
MAX_EVIDENCE_LIST_ITEMS = 128
MAX_EVIDENCE_ITEM_BYTES = 4_096
MAX_RETRIEVE_WSP_PATH_BYTES = 512
MAX_RETRIEVE_WSPS = 64
MAX_AGGREGATE_EVIDENCE_BYTES = 131_072
EXPECTED_RESOURCE_LIMITS = {
    "receipt_bytes": MAX_RECEIPT_BYTES,
    "receipt_mapping_items": MAX_RECEIPT_MAPPING_ITEMS,
    "repository_context_mapping_items": MAX_REPOSITORY_CONTEXT_ITEMS,
    "action_evidence_mapping_items": MAX_ACTION_EVIDENCE_MAPPING_ITEMS,
    "evidence_list_items": MAX_EVIDENCE_LIST_ITEMS,
    "evidence_item_bytes": MAX_EVIDENCE_ITEM_BYTES,
    "retrieve_wsp_path_bytes": MAX_RETRIEVE_WSP_PATH_BYTES,
    "retrieve_wsps_items": MAX_RETRIEVE_WSPS,
    "aggregate_evidence_bytes": MAX_AGGREGATE_EVIDENCE_BYTES,
    "git_calls": MAX_GIT_CALLS,
    "git_timeout_seconds": GIT_TIMEOUT_SECONDS,
    "git_accepted_output_bytes_per_stream": MAX_ACCEPTED_GIT_OUTPUT_BYTES,
}
VALID_OUTCOMES = frozenset({"completed", "blocked", "failed"})
TRUTH_BOUNDARY = (
    "WSP 97 receipt v1.1 validates structural completeness plus repository-bound "
    "Retrieve WSPs evidence; all other evidence references remain opaque and no "
    "reasoning quality or runtime side effect is proven."
)


def _slug(value: str) -> str:
    """Convert a display label to the receipt's snake-case key."""
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def _string_tuple(value: Any) -> tuple[str, ...]:
    """Return non-empty strings from a list/tuple without rewriting evidence."""
    if not isinstance(value, (list, tuple)) or len(value) > MAX_EVIDENCE_LIST_ITEMS:
        return ()
    normalized = tuple(
        item
        for item in value
        if isinstance(item, str)
        and len(item) <= MAX_EVIDENCE_ITEM_BYTES
        and item.strip()
    )
    return normalized if len(normalized) == len(value) else ()


def load_receipt(path: Path | str) -> dict[str, Any]:
    """Load one receipt after enforcing its byte cap before JSON parsing."""
    receipt_path = Path(path)
    with receipt_path.open("rb") as stream:
        payload = stream.read(MAX_RECEIPT_BYTES + 1)
    if len(payload) > MAX_RECEIPT_BYTES:
        raise ValueError("receipt byte limit exceeded")
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise ValueError("receipt root must be a JSON object")
    return data


def load_contract(path: Path | str | None = None) -> dict[str, Any]:
    """Load and validate the canonical WSP 97 machine contract."""
    contract_path = Path(path) if path is not None else DEFAULT_CONTRACT_PATH
    data = json.loads(contract_path.read_text(encoding="utf-8"))
    wsp97 = data.get("wsp_97")
    if not isinstance(wsp97, dict):
        raise ValueError("contract missing wsp_97 object")
    stages = wsp97.get("mantra_stages")
    actions = wsp97.get("operator_actions")
    _validate_contract_list(stages, "mantra_stages")
    _validate_contract_list(actions, "operator_actions")
    if wsp97.get("mantra_stage_count") != len(stages):
        raise ValueError("contract mantra_stage_count does not match mantra_stages")
    if wsp97.get("operator_action_count") != len(actions):
        raise ValueError("contract operator_action_count does not match operator_actions")
    validator = wsp97.get("validator")
    if not isinstance(validator, Mapping):
        raise ValueError("contract missing validator object")
    if validator.get("receipt_schema_version") != RECEIPT_SCHEMA_VERSION:
        raise ValueError("contract receipt_schema_version is unsupported")
    if validator.get("resource_limits") != EXPECTED_RESOURCE_LIMITS:
        raise ValueError("contract resource_limits do not match validator limits")
    return data


def _validate_contract_list(value: Any, name: str) -> None:
    """Validate one ordered contract label list."""
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        raise ValueError(f"contract {name} must be a non-empty string list")
    if len({_slug(item) for item in value}) != len(value):
        raise ValueError(f"contract {name} contain duplicate normalized keys")


@dataclass(frozen=True)
class WSP97ValidationResult:
    """Deterministic validation result for one execution receipt."""

    is_compliant: bool
    structurally_complete: bool
    validation_mode: str
    execution_id: str
    required_actions: tuple[str, ...]
    derived_mantra_stages: tuple[str, ...]
    missing_actions: tuple[str, ...]
    invalid_evidence_actions: tuple[str, ...]
    unexpected_actions: tuple[str, ...]
    violations: tuple[str, ...]
    validated_base_commit: str = ""
    repository_head_commit: str = ""
    truth_boundary: str = TRUTH_BOUNDARY

    def to_dict(self) -> dict[str, Any]:
        """Serialize the result for CLI and machine consumers."""
        return asdict(self)


def _contract_requirements(
    contract: Mapping[str, Any],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    wsp97 = contract.get("wsp_97", {})
    actions = tuple(_slug(item) for item in wsp97.get("operator_actions", ()))
    stages = tuple(_slug(item) for item in wsp97.get("mantra_stages", ()))
    if not actions or not stages:
        raise ValueError("contract must define mantra_stages and operator_actions")
    if wsp97.get("operator_action_count") != len(actions):
        raise ValueError("contract operator_action_count does not match operator_actions")
    if wsp97.get("mantra_stage_count") != len(stages):
        raise ValueError("contract mantra_stage_count does not match mantra_stages")
    return actions, stages


def _validate_envelope(receipt: Mapping[str, Any]) -> tuple[list[str], str]:
    violations: list[str] = []
    execution_id = receipt.get("execution_id")
    if not isinstance(execution_id, str) or not execution_id.strip():
        violations.append("missing_execution_id")
        execution_id = ""
    else:
        execution_id = execution_id.strip()
    plane = receipt.get("execution_plane")
    if not isinstance(plane, str) or not plane.strip():
        violations.append("missing_execution_plane")
    if receipt.get("outcome") not in VALID_OUTCOMES:
        violations.append("invalid_outcome")
    return violations, execution_id


def _validate_actions(
    receipt: Mapping[str, Any],
    required: tuple[str, ...],
) -> tuple[Mapping[str, Any], tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    raw = receipt.get("action_evidence")
    if not isinstance(raw, Mapping):
        return {}, required, (), ()
    if len(raw) > MAX_ACTION_EVIDENCE_MAPPING_ITEMS:
        return {}, required, (), ()
    keys = {key for key in raw if isinstance(key, str)}
    missing = tuple(action for action in required if action not in keys)
    invalid = tuple(
        action for action in required if action in keys and not _string_tuple(raw.get(action))
    )
    unexpected = tuple(sorted(keys.difference(required)))
    return raw, missing, invalid, unexpected


def _action_violations(
    raw: Mapping[str, Any],
    missing: tuple[str, ...],
    invalid: tuple[str, ...],
    unexpected: tuple[str, ...],
) -> list[str]:
    violations: list[str] = []
    if not raw:
        violations.append("invalid_action_evidence")
    violations.extend(f"missing_action:{action}" for action in missing)
    violations.extend(f"invalid_action_evidence:{action}" for action in invalid)
    violations.extend(f"unexpected_action:{action}" for action in unexpected)
    if any(not isinstance(key, str) for key in raw):
        violations.append("invalid_action_evidence")
    return violations


def _validate_wsp_declarations(
    receipt: Mapping[str, Any],
) -> tuple[tuple[str, ...], tuple[str, ...], list[str]]:
    wsps = _string_tuple(receipt.get("wsps_applied"))
    compliance = _string_tuple(receipt.get("compliance_evidence"))
    violations: list[str] = []
    if not wsps:
        violations.append("missing_wsps_applied")
    elif "WSP_97" not in wsps:
        violations.append("wsp_97_not_declared")
    if len(set(wsps)) != len(wsps):
        violations.append("duplicate_wsps_applied")
    if not compliance:
        violations.append("missing_compliance_evidence")
    return wsps, compliance, violations


def _derive_stages(
    required_stages: tuple[str, ...],
    valid_actions: set[str],
    wsps: tuple[str, ...],
    compliance: tuple[str, ...],
) -> tuple[tuple[str, ...], list[str]]:
    sources = {
        "holoindex": ("retrieve_wsps", "retrieve_evidence"),
        "research": ("research", "micro_pass", "macro_pass"),
        "hard_think": ("hard_think",),
        "dialectic_sweep": ("dialectic_sweep",),
        "first_principles": ("first_principles",),
        "build": ("execute",),
    }
    derived = [
        stage
        for stage in required_stages
        if (stage == "follow_wsp" and "WSP_97" in wsps and compliance)
        or (stage != "follow_wsp" and all(item in valid_actions for item in sources[stage]))
    ]
    missing = [f"underived_mantra_stage:{stage}" for stage in required_stages if stage not in derived]
    return tuple(derived), missing


def _schema_violations(receipt: Mapping[str, Any]) -> list[str]:
    version = receipt.get("schema_version")
    if version is None:
        return ["missing_schema_version"]
    if version != RECEIPT_SCHEMA_VERSION:
        return [f"unsupported_schema_version:{version}"]
    return []


def _bounded_string_size(value: str, limit: int) -> int:
    """Return a bounded UTF-8 size sentinel without encoding huge strings."""
    if len(value) > limit:
        return limit + 1
    return len(value.encode("utf-8"))


def _bounded_evidence_list(
    value: Any,
    label: str,
    *,
    item_limit: int = MAX_EVIDENCE_ITEM_BYTES,
    count_limit: int = MAX_EVIDENCE_LIST_ITEMS,
) -> tuple[list[str], int]:
    """Validate one evidence list without iterating beyond its declared cap."""
    if not isinstance(value, (list, tuple)):
        return [f"invalid_evidence_list:{label}"], 0
    if len(value) > count_limit:
        return [f"evidence_list_limit_exceeded:{label}"], 0
    violations: list[str] = []
    total = 0
    for index, item in enumerate(value):
        if not isinstance(item, str):
            violations.append(f"invalid_evidence_item:{label}:{index}")
            continue
        size = _bounded_string_size(item, item_limit)
        if size > item_limit:
            violations.append(f"evidence_item_string_limit_exceeded:{label}:{index}")
        else:
            total += size
    return violations, total


def _retrieve_wsp_bounds(value: Any) -> tuple[list[str], int]:
    """Apply the narrower count and path limits to retrieved WSP evidence."""
    if not isinstance(value, (list, tuple)):
        return ["invalid_evidence_list:retrieve_wsps"], 0
    if len(value) > MAX_RETRIEVE_WSPS:
        return ["retrieve_wsps_count_limit_exceeded"], 0
    violations, total = _bounded_evidence_list(value, "retrieve_wsps")
    for index, item in enumerate(value):
        if isinstance(item, str) and _bounded_string_size(
            item, MAX_RETRIEVE_WSP_PATH_BYTES
        ) > MAX_RETRIEVE_WSP_PATH_BYTES:
            violations.append(f"retrieve_wsp_path_limit_exceeded:{index}")
    return violations, total


def _evidence_bound_violations(receipt: Mapping[str, Any]) -> list[str]:
    """Validate all bounded receipt containers before repository subprocesses."""
    if len(receipt) > MAX_RECEIPT_MAPPING_ITEMS:
        return ["receipt_mapping_limit_exceeded"]
    context = receipt.get("repository_context")
    if isinstance(context, Mapping) and len(context) > MAX_REPOSITORY_CONTEXT_ITEMS:
        return ["repository_context_mapping_limit_exceeded"]
    evidence = receipt.get("action_evidence")
    if not isinstance(evidence, Mapping):
        return ["invalid_action_evidence_shape"]
    if len(evidence) > MAX_ACTION_EVIDENCE_MAPPING_ITEMS:
        return ["action_evidence_mapping_limit_exceeded"]
    violations: list[str] = []
    aggregate = 0
    for action, value in evidence.items():
        label = action if isinstance(action, str) else "non_string_action"
        bounded = (
            _retrieve_wsp_bounds(value)
            if action == "retrieve_wsps"
            else _bounded_evidence_list(value, label)
        )
        violations.extend(bounded[0])
        aggregate += bounded[1]
    for field in ("wsps_applied", "compliance_evidence"):
        bounded = _bounded_evidence_list(receipt.get(field), field)
        violations.extend(bounded[0])
        aggregate += bounded[1]
    if aggregate > MAX_AGGREGATE_EVIDENCE_BYTES:
        violations.append("aggregate_evidence_limit_exceeded")
    return violations


def _repository_context_preflight(
    receipt: Mapping[str, Any],
    expected_base: str | None,
) -> tuple[list[str], str]:
    """Validate exact receipt/caller base syntax before filesystem operations."""
    if expected_base is not None and not COMMIT_PATTERN.fullmatch(expected_base):
        raise ValueError("expected_base must be an exact lowercase 40-character commit")
    context = receipt.get("repository_context")
    if not isinstance(context, Mapping) or set(context) != {"base_commit"}:
        return ["invalid_repository_context"], ""
    base = context.get("base_commit")
    if not isinstance(base, str) or not COMMIT_PATTERN.fullmatch(base):
        return ["invalid_repository_context"], ""
    if expected_base is not None and base != expected_base:
        return ["expected_base_mismatch"], base
    return [], base


def _repository_reference_preflight(
    evidence: Mapping[str, Any],
    wsps: tuple[str, ...],
) -> list[str]:
    """Validate lexical WSP paths, identifiers, and coverage before Git."""
    violations: list[str] = []
    retrieved_ids: set[str] = set()
    seen: set[str] = set()
    for index, reference in enumerate(_string_tuple(evidence.get("retrieve_wsps"))):
        wsp_id, reason = lexical_wsp_id(reference)
        if reason is not None:
            violations.append(f"invalid_retrieve_wsp_syntax:{index}")
        elif reference in seen:
            violations.append(f"invalid_retrieve_wsp_syntax:{index}:duplicate")
        elif wsp_id is not None:
            retrieved_ids.add(wsp_id)
        seen.add(reference)
    for wsp_id in wsps:
        if not WSP_ID_PATTERN.fullmatch(wsp_id):
            violations.append(f"invalid_wsp_identifier:{wsp_id}")
        elif wsp_id not in retrieved_ids:
            violations.append(f"wsp_not_retrieved:{wsp_id}")
    return violations


def _repository_receipt_preflight(
    receipt: Mapping[str, Any],
    evidence: Mapping[str, Any],
    wsps: tuple[str, ...],
    expected_base: str | None,
) -> list[str]:
    """Run cheapest repository admission checks before root resolution."""
    context_violations, _base = _repository_context_preflight(
        receipt, expected_base
    )
    if context_violations:
        return context_violations
    return _repository_reference_preflight(evidence, wsps)


def _finalize_repository_mode(
    receipt: Mapping[str, Any],
    evidence: Mapping[str, Any],
    wsps: tuple[str, ...],
    repo_root: Path | str | None,
    expected_base: str | None,
    legacy_structural: bool,
    structurally_complete: bool,
    violations: list[str],
) -> tuple[str, str, str]:
    """Apply schema/mode semantics and resolve the repository only when eligible."""
    if legacy_structural:
        violations.append("legacy_structural_non_admitting")
        return "legacy_structural_non_admitting", "", ""
    violations.extend(_schema_violations(receipt))
    if not structurally_complete:
        return "repository_evidence_v1.1", "", ""
    base, head = _resolve_repository_slice(
        receipt, evidence, wsps, repo_root, expected_base, violations
    )
    return "repository_evidence_v1.1", base, head


def validate_execution_receipt(
    receipt: Mapping[str, Any],
    contract: Mapping[str, Any] | None = None,
    *,
    repo_root: Path | str | None = None,
    expected_base: str | None = None,
    legacy_structural: bool = False,
) -> WSP97ValidationResult:
    """Validate a receipt, resolving only its ``retrieve_wsps`` evidence."""
    active = dict(contract) if contract is not None else load_contract()
    required_actions, required_stages = _contract_requirements(active)
    violations, execution_id = _validate_envelope(receipt)
    bound_violations = _evidence_bound_violations(receipt)
    violations.extend(bound_violations)
    raw, missing, invalid, unexpected = _validate_actions(receipt, required_actions)
    violations.extend(_action_violations(raw, missing, invalid, unexpected))
    wsps, compliance, wsp_violations = _validate_wsp_declarations(receipt)
    violations.extend(wsp_violations)
    if (
        not legacy_structural
        and receipt.get("schema_version") == RECEIPT_SCHEMA_VERSION
        and not bound_violations
    ):
        violations.extend(
            _repository_receipt_preflight(receipt, raw, wsps, expected_base)
        )
    valid_actions = set(required_actions).difference(missing, invalid)
    derived, stage_violations = _derive_stages(
        required_stages, valid_actions, wsps, compliance
    )
    violations.extend(stage_violations)
    structurally_complete = not violations
    mode, base, head = _finalize_repository_mode(
        receipt, raw, wsps, repo_root, expected_base, legacy_structural,
        structurally_complete, violations
    )
    return WSP97ValidationResult(
        is_compliant=not violations and not legacy_structural,
        structurally_complete=structurally_complete,
        validation_mode=mode,
        execution_id=execution_id,
        required_actions=required_actions,
        derived_mantra_stages=derived,
        missing_actions=missing,
        invalid_evidence_actions=invalid,
        unexpected_actions=unexpected,
        violations=tuple(violations),
        validated_base_commit=base,
        repository_head_commit=head,
    )


def _resolve_repository_slice(
    receipt: Mapping[str, Any],
    evidence: Mapping[str, Any],
    wsps: tuple[str, ...],
    repo_root: Path | str | None,
    expected_base: str | None,
    violations: list[str],
) -> tuple[str, str]:
    if receipt.get("schema_version") != RECEIPT_SCHEMA_VERSION:
        return "", ""
    if repo_root is None:
        raise ValueError("repo_root is required for receipt v1.1 validation")
    repository = validate_repository_evidence(
        receipt,
        repo_root=repo_root,
        retrieve_wsps=_string_tuple(evidence.get("retrieve_wsps")),
        wsps_applied=wsps,
        expected_base=expected_base,
    )
    violations.extend(repository.violations)
    return repository.base_commit, repository.head_commit


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt", type=Path, help="Path to a JSON execution receipt")
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT_PATH)
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--expected-base")
    parser.add_argument("--legacy-structural", action="store_true")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        receipt = load_receipt(args.receipt)
        result = validate_execution_receipt(
            receipt,
            load_contract(args.contract),
            repo_root=args.repo_root,
            expected_base=args.expected_base,
            legacy_structural=args.legacy_structural,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps(result.to_dict(), indent=2 if args.pretty else None, sort_keys=True))
    return 0 if result.is_compliant else 1


if __name__ == "__main__":
    raise SystemExit(main())
