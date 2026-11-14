"""Scope-kind policy for authenticated RedDog conversation state."""

from __future__ import annotations

from typing import Any, Mapping, Sequence


SCOPE_KIND_FOUNDUP = "foundup"
SCOPE_KIND_PRINCIPAL = "principal"
SCOPE_KIND_COMPARISON = "comparison"
SCOPE_KINDS = frozenset(
    {SCOPE_KIND_FOUNDUP, SCOPE_KIND_PRINCIPAL, SCOPE_KIND_COMPARISON}
)

_OPERATIONAL_BINDINGS = (
    "source_snapshot_id",
    "source_snapshot_digest",
    "last_grounded_head_sha",
    "holoindex_generation_id",
    "holoindex_freshness_receipt_id",
    "grounding_receipt_id",
    "pending_work_proposal_id",
    "pending_work_proposal_digest",
)


def scope_request_authorized(
    *,
    scope_kind: str,
    active_foundup_id: str,
    discussion_foundup_ids: Sequence[str],
    allowed_foundup_ids: Sequence[str],
) -> bool:
    if (
        type(active_foundup_id) is not str
        or any(type(item) is not str for item in discussion_foundup_ids)
        or any(type(item) is not str for item in allowed_foundup_ids)
    ):
        return False
    raw_discussions = tuple(discussion_foundup_ids)
    discussions = tuple(dict.fromkeys(raw_discussions))
    if discussions != raw_discussions:
        return False
    allowed = set(allowed_foundup_ids)
    if scope_kind == SCOPE_KIND_FOUNDUP:
        return bool(
            active_foundup_id
            and discussions == (active_foundup_id,)
            and set(discussions).issubset(allowed)
        )
    if scope_kind == SCOPE_KIND_PRINCIPAL:
        return not active_foundup_id and not discussions
    if scope_kind == SCOPE_KIND_COMPARISON:
        return bool(
            not active_foundup_id
            and len(discussions) >= 2
            and set(discussions).issubset(allowed)
        )
    return False


def scope_record_reasons(record: Mapping[str, Any]) -> tuple[str, ...]:
    kind = str(record.get("scope_kind") or "")
    active = str(record.get("authorized_foundup_id") or "")
    discussions = record.get("discussion_foundup_ids")
    if kind not in SCOPE_KINDS or not isinstance(discussions, list):
        return ("conversation_scope_kind_invalid",)
    reasons: list[str] = []
    if kind == SCOPE_KIND_FOUNDUP:
        if not active or discussions != [active]:
            reasons.append("conversation_scope_foundup_set_invalid")
    elif kind == SCOPE_KIND_PRINCIPAL:
        if active or discussions:
            reasons.append("conversation_scope_principal_binding_invalid")
    elif active or len(discussions) < 2 or len(discussions) != len(set(discussions)):
        reasons.append("conversation_scope_comparison_binding_invalid")
    if kind != SCOPE_KIND_FOUNDUP and any(record.get(name) for name in _OPERATIONAL_BINDINGS):
        reasons.append("conversation_scope_nonfoundup_operational_binding")
    return tuple(reasons)


def scope_allows_work(scope_kind: object) -> bool:
    return scope_kind == SCOPE_KIND_FOUNDUP


__all__ = [
    "SCOPE_KIND_COMPARISON",
    "SCOPE_KIND_FOUNDUP",
    "SCOPE_KIND_PRINCIPAL",
    "SCOPE_KINDS",
    "scope_allows_work",
    "scope_record_reasons",
    "scope_request_authorized",
]
