"""Progressive RedDog authority policy for audit and bounded execution.

The operator-facing stage is a ceiling, never authority. Audit stays useful
without effects. Bounded execution requires the existing authenticated FIX and
WSP 15 chain and excludes work whose risk cannot be safely inferred as low.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence

from modules.communication.moltbot_bridge.src.reddog_wsp15_allocation_receipt import (
    canonical_reddog_wsp15_allocation_digest,
    validate_reddog_wsp15_allocation_receipt,
)


SCHEMA_VERSION = "reddog_progressive_execution_stage_receipt.v1"
STAGE_AUDIT = "AUDIT_NO_EFFECT"
STAGE_BOUNDED_EXECUTION = "BOUNDED_EXECUTION"
STAGE_PRODUCTION = "POLICY_STAGE_PRODUCTION"

DECISION_AUDIT_CONTINUES = "AUDIT_CONTINUES"
DECISION_BOUNDED_EXECUTION_ADMITTED = "BOUNDED_EXECUTION_ADMITTED"
DECISION_WOULD_BLOCK = "WOULD_BLOCK"
DECISION_REJECT = "REJECT"

REJECT_STAGE = "REJECT_PROGRESSIVE_STAGE_INVALID"
REJECT_PRODUCTION_CLOSED = "REJECT_PROGRESSIVE_PRODUCTION_CLOSED"
REJECT_WSP15 = "REJECT_PROGRESSIVE_WSP15_INVALID"
REJECT_COMPLEXITY = "REJECT_PROGRESSIVE_COMPLEXITY_ABOVE_TWO"
REJECT_NOT_FIX = "REJECT_PROGRESSIVE_DETERMINATION_NOT_FIX"
REJECT_HIGH_RISK = "REJECT_PROGRESSIVE_HIGH_RISK_WORK"
REJECT_CHANGED_PATH_BINDING = "REJECT_PROGRESSIVE_CHANGED_PATH_BINDING"
REJECT_EFFECT_PLANE = "REJECT_PROGRESSIVE_EFFECT_PLANE"
REJECT_CREATE_NEW = "REJECT_PROGRESSIVE_CREATE_NEW"

_HIGH_RISK_PATTERNS = {
    "AUTHORITY": re.compile(r"\b(authorit(?:y|ies)|permission|privilege|sovereign)\b", re.I),
    "SECURITY": re.compile(r"\b(security|secret|credential|token|password|oauth|auth(?:n|z)?)\b", re.I),
    "SIGNING": re.compile(r"\b(sign(?:er|ing|ature)?|crypt(?:o|ography)|key[_ -]?epoch)\b", re.I),
    "MERGE": re.compile(r"\b(merge|promot(?:e|ion)|publish|release|deploy)\b", re.I),
    "DEPENDENCY": re.compile(r"\b(dependenc(?:y|ies)|vendor|lockfile|package[- ]?lock|requirements)\b", re.I),
    "MIGRATION": re.compile(r"\b(schema|database|migration|backfill)\b", re.I),
    "RUNTIME_CONTROL": re.compile(r"\b(shell|subprocess|service|daemon|main\.py|extension\.js)\b", re.I),
}

_BOUNDED_OPERATION_CLASSES = frozenset(
    {
        "bounded_module_fix",
        "bounded_code_change",
        "bounded_docs_patch",
        "edit_foundup_module",
    }
)
_BOUNDED_FOUNDUP_SURFACES = frozenset({"src", "tests", "docs"})
_BOUNDED_FOUNDUP_DOCS = frozenset(
    {"readme.md", "interface.md", "roadmap.md", "modlog.md", "requirements.txt"}
)
_PROTECTED_PATH_SEGMENTS = frozenset(
    {
        "auth", "authority", "credential", "crypto", "deploy", "finance",
        "key", "merge", "oauth", "payment", "permission", "publish",
        "release", "security", "secret", "signer", "token", "trade", "wallet",
    }
)


@dataclass(frozen=True)
class ProgressiveExecutionStageReceipt:
    schema_version: str
    receipt_id: str
    stage: str
    decision: str
    determination_action: str
    selected_slice: str
    requested_operation: str
    changed_paths: tuple[str, ...]
    wsp15_allocation_receipt_id: str | None
    wsp15_allocation_digest: str | None
    complexity: int | None
    risk_classes: tuple[str, ...]
    would_block_reasons: tuple[str, ...]
    rejection_reasons: tuple[str, ...]
    no_effect_authority: bool
    independent_verifier_required: bool
    production_authority_granted: bool = False

    @property
    def accepted(self) -> bool:
        return self.decision != DECISION_REJECT

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_audit_stage(
    *, would_block_reasons: Sequence[str] = ()
) -> ProgressiveExecutionStageReceipt:
    """Keep review/dialogue available while proving that no effect is allowed."""

    reasons = _texts(would_block_reasons)
    return _receipt(
        stage=STAGE_AUDIT,
        decision=DECISION_AUDIT_CONTINUES,
        action="AUDIT",
        selected_slice="",
        requested_operation="",
        changed_paths=(),
        allocation=None,
        risk_classes=(),
        would_block_reasons=reasons,
        rejection_reasons=(),
        no_effect_authority=True,
        independent_verifier_required=False,
    )


def admit_bounded_execution(
    *,
    determination_action: str,
    allocation: Mapping[str, Any],
    selected_slice: str,
    requested_operation: str,
    changed_paths: Sequence[str],
) -> ProgressiveExecutionStageReceipt:
    """Admit only low-complexity, low-risk, authenticated FIX work."""

    rejection: list[str] = []
    validation = validate_reddog_wsp15_allocation_receipt(allocation)
    if not validation.accepted:
        rejection.append(REJECT_WSP15)
    action = str(determination_action or "").upper()
    if action != "FIX":
        rejection.append(REJECT_NOT_FIX)
    complexity = allocation.get("complexity")
    if type(complexity) is not int or complexity not in {1, 2}:
        rejection.append(REJECT_COMPLEXITY)
    normalized_paths = _normalize_paths(changed_paths)
    allocation_paths = _normalize_paths(allocation.get("changed_paths") or ())
    if normalized_paths != allocation_paths:
        rejection.append(REJECT_CHANGED_PATH_BINDING)
    risk_classes = classify_high_risk_work(
        selected_slice=selected_slice,
        requested_operation=requested_operation,
        changed_paths=changed_paths,
    )
    if risk_classes:
        rejection.append(REJECT_HIGH_RISK)
    hard_rejection = tuple(
        reason for reason in rejection
        if reason in {REJECT_WSP15, REJECT_CHANGED_PATH_BINDING}
    )
    soft_rejection = tuple(reason for reason in rejection if reason not in hard_rejection)
    return _receipt(
        stage=STAGE_BOUNDED_EXECUTION,
        decision=(
            DECISION_REJECT if hard_rejection
            else DECISION_WOULD_BLOCK if soft_rejection
            else DECISION_BOUNDED_EXECUTION_ADMITTED
        ),
        action=action,
        selected_slice=str(selected_slice or ""),
        requested_operation=str(requested_operation or ""),
        changed_paths=tuple(map(str, changed_paths)),
        allocation=allocation,
        risk_classes=risk_classes,
        would_block_reasons=_texts(soft_rejection),
        rejection_reasons=hard_rejection,
        no_effect_authority=bool(rejection),
        independent_verifier_required=True,
    )


def evaluate_proposal_stage(
    *, action: str, reuse_decision: str, effect_plane: str,
    allocation: Mapping[str, Any], selected_slice: str,
    requested_operation: str, changed_paths: Sequence[str],
    would_block_reasons: Sequence[str] = (),
) -> ProgressiveExecutionStageReceipt:
    """Project a valid proposal onto the progressive effect ceiling."""

    normalized_action = str(action or "").upper()
    normalized_effect = str(effect_plane or "").upper()
    if normalized_action != "FIX" or normalized_effect in {"NONE", "READ_ONLY_AUDIT"}:
        return _audit_proposal_receipt(
            action=normalized_action,
            allocation=allocation,
            selected_slice=selected_slice,
            requested_operation=requested_operation,
            changed_paths=changed_paths,
            would_block_reasons=would_block_reasons,
        )
    receipt = admit_bounded_execution(
        determination_action=normalized_action,
        allocation=allocation,
        selected_slice=selected_slice,
        requested_operation=requested_operation,
        changed_paths=changed_paths,
    )
    extra: list[str] = []
    if str(reuse_decision or "").upper() == "CREATE_NEW":
        extra.append(REJECT_CREATE_NEW)
    if normalized_effect != "REPOSITORY_CODE_CHANGE":
        extra.append(REJECT_EFFECT_PLANE)
    if not extra:
        return receipt
    return _receipt(
        stage=STAGE_BOUNDED_EXECUTION,
        decision=DECISION_WOULD_BLOCK,
        action=normalized_action,
        selected_slice=str(selected_slice or ""),
        requested_operation=str(requested_operation or ""),
        changed_paths=tuple(map(str, changed_paths)),
        allocation=allocation,
        risk_classes=receipt.risk_classes,
        would_block_reasons=_texts((*receipt.would_block_reasons, *extra)),
        rejection_reasons=(),
        no_effect_authority=True,
        independent_verifier_required=True,
    )


def _audit_proposal_receipt(
    *, action: str, allocation: Mapping[str, Any], selected_slice: str,
    requested_operation: str, changed_paths: Sequence[str],
    would_block_reasons: Sequence[str],
) -> ProgressiveExecutionStageReceipt:
    return _receipt(
        stage=STAGE_AUDIT,
        decision=DECISION_AUDIT_CONTINUES,
        action=action,
        selected_slice=str(selected_slice or ""),
        requested_operation=str(requested_operation or ""),
        changed_paths=tuple(map(str, changed_paths)),
        allocation=allocation,
        risk_classes=classify_high_risk_work(
            selected_slice=selected_slice,
            requested_operation=requested_operation,
            changed_paths=changed_paths,
        ),
        would_block_reasons=_texts(would_block_reasons),
        rejection_reasons=(),
        no_effect_authority=True,
        independent_verifier_required=False,
    )


def reject_unavailable_stage(stage: str) -> ProgressiveExecutionStageReceipt:
    """Reject unknown stages and the deliberately closed production stage."""

    normalized = str(stage or "").upper()
    reason = REJECT_PRODUCTION_CLOSED if normalized == STAGE_PRODUCTION else REJECT_STAGE
    return _receipt(
        stage=normalized or "UNKNOWN",
        decision=DECISION_REJECT,
        action="",
        selected_slice="",
        requested_operation="",
        changed_paths=(),
        allocation=None,
        risk_classes=(),
        would_block_reasons=(),
        rejection_reasons=(reason,),
        no_effect_authority=True,
        independent_verifier_required=True,
    )


def validate_bounded_execution_receipt(
    receipt: Mapping[str, Any], allocation: Mapping[str, Any]
) -> bool:
    """Rehydrate a bounded receipt by recomputing policy and its receipt id."""

    if not isinstance(receipt, Mapping) or set(receipt) != set(
        ProgressiveExecutionStageReceipt.__dataclass_fields__
    ):
        return False
    if receipt.get("stage") != STAGE_BOUNDED_EXECUTION:
        return False
    rebuilt = admit_bounded_execution(
        determination_action=str(receipt.get("determination_action") or ""),
        allocation=allocation,
        selected_slice=str(receipt.get("selected_slice") or ""),
        requested_operation=str(receipt.get("requested_operation") or ""),
        changed_paths=tuple(receipt.get("changed_paths") or ()),
    )
    return bool(
        rebuilt.decision == DECISION_BOUNDED_EXECUTION_ADMITTED
        and receipt.get("decision") == DECISION_BOUNDED_EXECUTION_ADMITTED
        and receipt.get("wsp15_allocation_receipt_id") == allocation.get("receipt_id")
        and receipt.get("wsp15_allocation_digest")
        == canonical_reddog_wsp15_allocation_digest(allocation)
        and receipt.get("complexity") == allocation.get("complexity")
        and receipt.get("risk_classes") in ((), [])
        and receipt.get("would_block_reasons") in ((), [])
        and receipt.get("rejection_reasons") in ((), [])
        and receipt.get("no_effect_authority") is False
        and receipt.get("independent_verifier_required") is True
        and receipt.get("production_authority_granted") is False
        and receipt.get("receipt_id") == _digest(_unsigned(receipt))
    )


def validate_queue_bounded_stage_binding(
    queue_item: Mapping[str, Any], allocation: Mapping[str, Any]
) -> bool:
    """Validate the receipt plus the queue fields that bind it durably."""

    receipt = queue_item.get("progressive_policy_stage_receipt")
    if not isinstance(receipt, Mapping):
        return False
    return bool(
        validate_bounded_execution_receipt(receipt, allocation)
        and queue_item.get("progressive_policy_stage_receipt_id")
        == receipt.get("receipt_id")
        and queue_item.get("progressive_policy_stage_digest") == _digest(receipt)
        and queue_item.get("independent_verifier_required") is True
    )


def validate_proposal_stage_projection(proposal: Mapping[str, Any]) -> bool:
    """Verify an embedded stage receipt against its proposal receipt fields."""

    stage = proposal.get("progressive_policy_stage_receipt")
    if not isinstance(stage, Mapping) or set(stage) != set(
        ProgressiveExecutionStageReceipt.__dataclass_fields__
    ):
        return False
    if stage.get("receipt_id") != _digest(_unsigned(stage)):
        return False
    bindings = {
        "determination_action": str(proposal.get("action") or "").upper(),
        "selected_slice": str(proposal.get("slice_id") or ""),
        "requested_operation": str(proposal.get("requested_operation") or ""),
        "changed_paths": tuple(proposal.get("allowed_paths") or ()),
        "wsp15_allocation_receipt_id": proposal.get("wsp15_allocation_receipt_id"),
        "wsp15_allocation_digest": proposal.get("wsp15_allocation_digest"),
        "complexity": proposal.get("wsp15_complexity"),
    }
    for key, value in bindings.items():
        actual = stage.get(key)
        if key == "changed_paths":
            actual = tuple(actual or ())
        if actual != value:
            return False
    expected_risk = classify_high_risk_work(
        selected_slice=bindings["selected_slice"],
        requested_operation=bindings["requested_operation"],
        changed_paths=bindings["changed_paths"],
    )
    if tuple(stage.get("risk_classes") or ()) != expected_risk:
        return False
    if stage.get("production_authority_granted") is not False:
        return False
    return _valid_projected_stage_decision(proposal, stage, expected_risk)


def _valid_projected_stage_decision(
    proposal: Mapping[str, Any], stage: Mapping[str, Any], risk: tuple[str, ...]
) -> bool:
    action = str(proposal.get("action") or "").upper()
    effect = str(proposal.get("target_effect_plane") or "").upper()
    if action != "FIX" or effect in {"NONE", "READ_ONLY_AUDIT"}:
        return bool(
            stage.get("stage") == STAGE_AUDIT
            and stage.get("decision") == DECISION_AUDIT_CONTINUES
            and stage.get("no_effect_authority") is True
            and stage.get("independent_verifier_required") is False
        )
    if stage.get("decision") == DECISION_REJECT:
        return bool(
            stage.get("stage") == STAGE_BOUNDED_EXECUTION
            and stage.get("no_effect_authority") is True
            and stage.get("independent_verifier_required") is True
            and tuple(stage.get("rejection_reasons") or ())
        )
    blocked = bool(
        proposal.get("reuse_decision") == "CREATE_NEW"
        or effect != "REPOSITORY_CODE_CHANGE"
        or proposal.get("wsp15_complexity") not in {1, 2}
        or risk
    )
    return bool(
        stage.get("stage") == STAGE_BOUNDED_EXECUTION
        and stage.get("decision")
        == (DECISION_WOULD_BLOCK if blocked else DECISION_BOUNDED_EXECUTION_ADMITTED)
        and stage.get("no_effect_authority") is blocked
        and stage.get("independent_verifier_required") is True
    )


def classify_high_risk_work(
    *, selected_slice: str, requested_operation: str, changed_paths: Sequence[str]
) -> tuple[str, ...]:
    del selected_slice
    corpus = " ".join((str(requested_operation or ""), *map(str, changed_paths)))
    risks = [name for name, pattern in _HIGH_RISK_PATTERNS.items() if pattern.search(corpus)]
    operation = str(requested_operation or "").strip().lower()
    if operation not in _BOUNDED_OPERATION_CLASSES:
        risks.append("UNKNOWN_OPERATION_CLASS")
    for path in _normalize_paths(changed_paths):
        risks.extend(_bounded_path_risks(path))
    if not changed_paths:
        risks.append("MISSING_EFFECT_PATH")
    return tuple(dict.fromkeys(risks))


def _bounded_path_risks(path: str) -> tuple[str, ...]:
    parts = tuple(part.lower() for part in path.split("/") if part)
    if len(parts) < 4 or parts[:2] != ("modules", "foundups"):
        return ("PROTECTED_SURFACE",)
    if any(part in _PROTECTED_PATH_SEGMENTS for part in parts):
        return ("PROTECTED_SURFACE",)
    leaf = parts[-1]
    if parts[3] not in _BOUNDED_FOUNDUP_SURFACES and leaf not in _BOUNDED_FOUNDUP_DOCS:
        return ("UNKNOWN_FOUNDUP_SURFACE",)
    return ()


def _normalize_paths(values: Sequence[Any]) -> tuple[str, ...]:
    normalized: list[str] = []
    for value in values:
        path = str(value or "").replace("\\", "/").strip()
        while path.startswith("./"):
            path = path[2:]
        if path:
            normalized.append(path)
    return tuple(dict.fromkeys(normalized))


def _receipt(
    *, stage: str, decision: str, action: str, selected_slice: str,
    requested_operation: str, changed_paths: tuple[str, ...],
    allocation: Mapping[str, Any] | None, risk_classes: tuple[str, ...],
    would_block_reasons: tuple[str, ...], rejection_reasons: tuple[str, ...],
    no_effect_authority: bool, independent_verifier_required: bool,
) -> ProgressiveExecutionStageReceipt:
    values = {
        "schema_version": SCHEMA_VERSION,
        "stage": stage,
        "decision": decision,
        "determination_action": action,
        "selected_slice": selected_slice,
        "requested_operation": requested_operation,
        "changed_paths": changed_paths,
        "wsp15_allocation_receipt_id": (
            str(allocation.get("receipt_id")) if allocation else None
        ),
        "wsp15_allocation_digest": (
            canonical_reddog_wsp15_allocation_digest(allocation) if allocation else None
        ),
        "complexity": allocation.get("complexity") if allocation else None,
        "risk_classes": risk_classes,
        "would_block_reasons": would_block_reasons,
        "rejection_reasons": rejection_reasons,
        "no_effect_authority": no_effect_authority,
        "independent_verifier_required": independent_verifier_required,
        "production_authority_granted": False,
    }
    return ProgressiveExecutionStageReceipt(receipt_id=_digest(values), **values)


def _unsigned(receipt: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in receipt.items() if key != "receipt_id"}


def _digest(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _texts(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(value).strip() for value in values if str(value).strip()))


__all__ = [
    "DECISION_AUDIT_CONTINUES", "DECISION_BOUNDED_EXECUTION_ADMITTED",
    "DECISION_WOULD_BLOCK",
    "ProgressiveExecutionStageReceipt", "STAGE_AUDIT",
    "STAGE_BOUNDED_EXECUTION", "STAGE_PRODUCTION", "admit_bounded_execution",
    "classify_high_risk_work", "evaluate_audit_stage",
    "evaluate_proposal_stage",
    "reject_unavailable_stage", "validate_bounded_execution_receipt",
    "validate_proposal_stage_projection", "validate_queue_bounded_stage_binding",
]
