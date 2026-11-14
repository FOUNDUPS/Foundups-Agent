"""Typed evidence citation policy for RedDog read-only audit outputs.

Repository file evidence can support current implementation claims. External
research evidence can support current external-source/freshness claims only
when the runtime supplied an explicit external evidence ref. Memex evidence is
historical memory context and can only supplement a finding that also cites
current repository or verified external evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


SOURCE_CLASS_REPO_FILE = "repo_file"
SOURCE_CLASS_MEMEX = "memex"
SOURCE_CLASS_EXTERNAL_RESEARCH = "external_research"
SOURCE_CLASS_UNKNOWN = "unknown"

TYPED_CITATION_ACCEPTED = "TYPED_EVIDENCE_CITATIONS_ACCEPTED"
TYPED_CITATION_REJECTED = "TYPED_EVIDENCE_CITATIONS_REJECTED"


@dataclass(frozen=True)
class TypedCitationPolicyResult:
    accepted: bool
    status: str
    rejection_reasons: tuple[str, ...]


def classify_evidence_ref(ref: str) -> str:
    text = str(ref or "").strip()
    if text.startswith("file:"):
        return SOURCE_CLASS_REPO_FILE
    if text.startswith("external:"):
        return SOURCE_CLASS_EXTERNAL_RESEARCH
    if text.startswith("memex:"):
        return SOURCE_CLASS_MEMEX
    return SOURCE_CLASS_UNKNOWN


def validate_typed_evidence_citations(
    *,
    refs: Sequence[str],
    allowed_file_refs: Sequence[str],
    allowed_memex_refs: Sequence[str] = (),
    allowed_external_refs: Sequence[str] = (),
    require_file_evidence: bool = True,
) -> TypedCitationPolicyResult:
    """Validate that cited evidence refs match their typed authority boundary."""

    normalized_refs = tuple(dict.fromkeys(str(ref).strip() for ref in refs if str(ref).strip()))
    file_allowed = set(str(ref).strip() for ref in allowed_file_refs if str(ref).strip())
    memex_allowed = set(str(ref).strip() for ref in allowed_memex_refs if str(ref).strip())
    external_allowed = set(str(ref).strip() for ref in allowed_external_refs if str(ref).strip())
    reasons: list[str] = []

    if not normalized_refs:
        reasons.append("missing_evidence_refs")

    saw_file = False
    saw_external = False
    for ref in normalized_refs:
        source_class = classify_evidence_ref(ref)
        if source_class == SOURCE_CLASS_REPO_FILE:
            saw_file = True
            if ref not in file_allowed:
                reasons.append("unknown_file_evidence_ref")
        elif source_class == SOURCE_CLASS_EXTERNAL_RESEARCH:
            saw_external = True
            if ref not in external_allowed:
                reasons.append("unknown_external_evidence_ref")
        elif source_class == SOURCE_CLASS_MEMEX:
            if ref not in memex_allowed:
                reasons.append("unknown_memex_evidence_ref")
        else:
            reasons.append("unknown_evidence_ref_type")

    if require_file_evidence and normalized_refs and not saw_file:
        reasons.append("memex_cannot_replace_repo_file_evidence")
    if not require_file_evidence and normalized_refs and not saw_file and not saw_external:
        reasons.append("memex_cannot_replace_primary_evidence")

    if reasons:
        return TypedCitationPolicyResult(
            accepted=False,
            status=TYPED_CITATION_REJECTED,
            rejection_reasons=tuple(dict.fromkeys(reasons)),
        )
    return TypedCitationPolicyResult(
        accepted=True,
        status=TYPED_CITATION_ACCEPTED,
        rejection_reasons=(),
    )


__all__ = [
    "SOURCE_CLASS_EXTERNAL_RESEARCH",
    "SOURCE_CLASS_MEMEX",
    "SOURCE_CLASS_REPO_FILE",
    "SOURCE_CLASS_UNKNOWN",
    "TYPED_CITATION_ACCEPTED",
    "TYPED_CITATION_REJECTED",
    "TypedCitationPolicyResult",
    "classify_evidence_ref",
    "validate_typed_evidence_citations",
]
