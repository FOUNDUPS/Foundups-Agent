"""HoloIndex-first external research grounding adapter for RedDog.

Slice: REDDOG_HOLOINDEX_FIRST_EXTERNAL_RESEARCH_GROUNDING_ADAPTER_PHASE1

This module grounds typed external/semantic research targets without giving
external content instruction authority. It queries injected HoloIndex memory
first, then uses an injected approved external retriever only for unresolved or
freshness-sensitive external targets. It never re-indexes HoloIndex, promotes
findings, writes PatternMemory, runs commands, or performs direct network I/O.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Protocol, Sequence
from urllib.parse import urlparse

RESEARCH_GROUNDING_ACCEPT = "RESEARCH_GROUNDING_ACCEPT"
RESEARCH_GROUNDING_REJECT = "RESEARCH_GROUNDING_REJECT"

FAIL_HOLOINDEX_FIRST_MISSING = "FAIL_HOLOINDEX_FIRST_MISSING"
FAIL_HOLOINDEX_INDEX_GAP = "FAIL_HOLOINDEX_INDEX_GAP"
FAIL_EXTERNAL_RETRIEVER_REQUIRED = "FAIL_EXTERNAL_RETRIEVER_REQUIRED"
FAIL_UNAPPROVED_SOURCE = "FAIL_UNAPPROVED_SOURCE"
FAIL_EXTERNAL_SNAPSHOT_INVALID = "FAIL_EXTERNAL_SNAPSHOT_INVALID"
FAIL_EXTERNAL_SNAPSHOT_STALE = "FAIL_EXTERNAL_SNAPSHOT_STALE"
FAIL_TARGET_UNGROUNDED = "FAIL_TARGET_UNGROUNDED"

DEFAULT_APPROVED_DOMAINS = (
    "arxiv.org",
    "github.com",
    "doi.org",
    "openreview.net",
    "nber.org",
)
DEFAULT_MAX_SNAPSHOT_AGE_S = 7 * 24 * 60 * 60
MAX_EXTERNAL_CONTENT_EXCERPT_CHARS = 2_400

PROMPT_INJECTION_MARKERS = (
    "ignore previous instructions",
    "system prompt",
    "developer message",
    "run this command",
    "execute this command",
    "exfiltrate",
)


class HoloIndexResearchMemory(Protocol):
    def search(self, query: str) -> Mapping[str, Any]:
        ...


class ExternalResearchRetriever(Protocol):
    def fetch(self, target: Mapping[str, Any]) -> Mapping[str, Any]:
        ...


@dataclass(frozen=True)
class GroundedResearchTarget:
    target: str
    target_type: str
    target_digest: str
    grounded: bool
    grounding_channel: str
    holoindex_status: str
    holoindex_refs: List[str]
    external_snapshot_digest: Optional[str]
    source_url: Optional[str]
    source_domain: Optional[str]
    source_type: Optional[str]
    content_digest: Optional[str]
    freshness_receipt_digest: Optional[str]
    provenance_refs: List[str]
    content_excerpt: str
    finding_status: str
    prompt_injection_markers_detected: bool
    untrusted_data_only: bool
    rejection_reasons: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ResearchGroundingReceipt:
    receipt_id: str
    request_digest: str
    targets_total: int
    targets_grounded: int
    targets_missing: List[str]
    internal_holoindex_first_performed: bool
    external_retrieval_attempted: bool
    external_snapshots_count: int
    verified_research_receipt_required: bool
    rejected_negative_results_indexable: bool
    promoted_to_holoindex: bool
    no_holoindex_reindex_performed: bool
    no_pattern_memory_write_performed: bool
    no_command_execution_performed: bool
    no_model_instruction_from_external_content: bool
    rejection_reasons: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ResearchGroundingResult:
    decision: str
    accepted: bool
    receipt: ResearchGroundingReceipt
    grounded_targets: List[GroundedResearchTarget]
    rejection_reasons: List[str]

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["receipt"] = self.receipt.to_dict()
        payload["grounded_targets"] = [target.to_dict() for target in self.grounded_targets]
        return payload


def _digest(payload: Any) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    )
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _as_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if value in (None, ""):
        return []
    return [value]


def _dedupe(values: Iterable[str]) -> List[str]:
    seen = set()
    ordered: List[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            seen.add(text)
            ordered.append(text)
    return ordered


def _target_text(raw: Any) -> str:
    if isinstance(raw, Mapping):
        return str(raw.get("url") or raw.get("query") or raw.get("target") or "").strip()
    return str(raw or "").strip()


def _target_url(raw: Any) -> str:
    if isinstance(raw, Mapping):
        return str(raw.get("url") or "").strip()
    text = _target_text(raw)
    return text if text.lower().startswith("https://") else ""


def _domain_for_url(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().removeprefix("www.")
    except Exception:
        return ""


def _domain_allowed(domain: str, allowed_domains: Sequence[str]) -> bool:
    if not domain:
        return False
    for allowed in allowed_domains:
        norm = str(allowed or "").lower().removeprefix("www.")
        if domain == norm or domain.endswith("." + norm):
            return True
    return False


def _holo_refs(result: Mapping[str, Any]) -> List[str]:
    refs: List[str] = []
    for key in ("hits", "code_hits", "wsp_hits", "docs", "knowledge", "results"):
        hits = result.get(key)
        if not isinstance(hits, Sequence) or isinstance(hits, (str, bytes)):
            continue
        for hit in hits:
            if isinstance(hit, Mapping):
                ref = (
                    hit.get("path")
                    or hit.get("location")
                    or hit.get("url")
                    or hit.get("title")
                    or hit.get("id")
                )
            else:
                ref = hit
            if ref:
                refs.append(str(ref))
    return _dedupe(refs)


def _holo_status(result: Mapping[str, Any]) -> str:
    return str(result.get("status") or result.get("holoindex_status") or "unknown")


def _holo_index_gap(result: Mapping[str, Any]) -> bool:
    status = _holo_status(result).upper()
    return (
        result.get("index_gap_detected") is True
        or str(result.get("retrieval_quality") or "").upper() == "INDEX_GAP"
        or status == "INDEX_GAP"
    )


def _content_digest(snapshot: Mapping[str, Any]) -> str:
    explicit = snapshot.get("content_sha256") or snapshot.get("content_digest")
    if explicit:
        text = str(explicit)
        return text if text.startswith("sha256:") else "sha256:" + text
    body = str(snapshot.get("content_text") or snapshot.get("content") or "")
    return _digest({"external_content": body}) if body else ""


def _snapshot_digest(snapshot: Mapping[str, Any]) -> str:
    safe = {
        "source_url": snapshot.get("source_url") or snapshot.get("url") or "",
        "source_type": snapshot.get("source_type") or "",
        "fetched_at": snapshot.get("fetched_at") or 0,
        "content_digest": _content_digest(snapshot),
        "provenance": snapshot.get("provenance") or snapshot.get("provenance_refs") or [],
        "finding_status": snapshot.get("finding_status") or "unverified",
    }
    return _digest(safe)


def _provenance_refs(snapshot: Mapping[str, Any]) -> List[str]:
    refs = snapshot.get("provenance_refs") or snapshot.get("provenance") or []
    if isinstance(refs, (str, bytes)):
        refs = [refs]
    if not isinstance(refs, Sequence):
        return []
    return _dedupe(str(ref) for ref in refs)


def _prompt_injection_detected(snapshot: Mapping[str, Any]) -> bool:
    body = str(snapshot.get("content_text") or snapshot.get("content") or "").lower()
    return any(marker in body for marker in PROMPT_INJECTION_MARKERS)


def _content_excerpt(snapshot: Mapping[str, Any]) -> str:
    body = str(snapshot.get("content_text") or snapshot.get("content") or "")
    if not body:
        return ""
    sanitized = body
    for marker in PROMPT_INJECTION_MARKERS:
        sanitized = re.sub(
            re.escape(marker),
            "[external_prompt_injection_marker_removed]",
            sanitized,
            flags=re.IGNORECASE,
        )
    return sanitized[:MAX_EXTERNAL_CONTENT_EXCERPT_CHARS]


def _snapshot_valid(
    snapshot: Mapping[str, Any],
    *,
    now_s: int,
    max_age_s: int,
    freshness_required: bool,
) -> List[str]:
    reasons: List[str] = []
    if not _content_digest(snapshot):
        reasons.append(FAIL_EXTERNAL_SNAPSHOT_INVALID)
    if not _provenance_refs(snapshot):
        reasons.append(FAIL_EXTERNAL_SNAPSHOT_INVALID)
    if not str(snapshot.get("source_url") or snapshot.get("url") or ""):
        reasons.append(FAIL_EXTERNAL_SNAPSHOT_INVALID)
    fetched_at = int(snapshot.get("fetched_at") or 0)
    if freshness_required and (fetched_at <= 0 or now_s - fetched_at > max_age_s):
        reasons.append(FAIL_EXTERNAL_SNAPSHOT_STALE)
    return _dedupe(reasons)


def _normalize_targets(request: Mapping[str, Any]) -> List[Dict[str, Any]]:
    targets: List[Dict[str, Any]] = []
    for raw in _as_list(request.get("semantic_targets")):
        text = _target_text(raw)
        if text:
            targets.append(
                {
                    "target": text,
                    "target_type": "semantic",
                    "url": "",
                    "freshness_required": bool(
                        isinstance(raw, Mapping) and raw.get("freshness_required") is True
                    ),
                }
            )
    for raw in _as_list(request.get("external_research_targets")):
        text = _target_text(raw)
        url = _target_url(raw)
        if text:
            targets.append(
                {
                    "target": text,
                    "target_type": "external_research",
                    "url": url,
                    "freshness_required": True
                    if not isinstance(raw, Mapping)
                    else raw.get("freshness_required", True) is True,
                }
            )
    return targets


def ground_reddog_holoindex_first_external_research(
    request: Mapping[str, Any],
    *,
    holoindex: HoloIndexResearchMemory,
    external_retriever: Optional[ExternalResearchRetriever] = None,
    approved_domains: Sequence[str] = DEFAULT_APPROVED_DOMAINS,
    now_s: int = 0,
    max_snapshot_age_s: int = DEFAULT_MAX_SNAPSHOT_AGE_S,
) -> ResearchGroundingResult:
    """Ground research targets with HoloIndex first and approved external snapshots."""

    req = dict(request or {})
    targets = _normalize_targets(req)
    grounded_targets: List[GroundedResearchTarget] = []
    reasons: List[str] = []
    external_attempted = False
    external_count = 0

    for target in targets:
        query = str(target["target"])
        holo_result = dict(holoindex.search(query) or {})
        refs = _holo_refs(holo_result)
        status = _holo_status(holo_result)
        target_reasons: List[str] = []

        if not holo_result:
            target_reasons.append(FAIL_HOLOINDEX_FIRST_MISSING)
        if _holo_index_gap(holo_result):
            target_reasons.append(FAIL_HOLOINDEX_INDEX_GAP)

        requires_external = (
            target["target_type"] == "external_research"
            or target["freshness_required"] is True
        )
        source_url: Optional[str] = None
        source_domain: Optional[str] = None
        source_type: Optional[str] = None
        snapshot_digest: Optional[str] = None
        content_digest: Optional[str] = None
        freshness_digest: Optional[str] = None
        provenance: List[str] = []
        content_excerpt = ""
        finding_status = "internal_memory"
        grounding_channel = "holoindex"
        prompt_injection = False

        if requires_external:
            url = str(target.get("url") or "")
            domain = _domain_for_url(url)
            if url and not _domain_allowed(domain, approved_domains):
                target_reasons.append(FAIL_UNAPPROVED_SOURCE)
            elif external_retriever is None:
                target_reasons.append(FAIL_EXTERNAL_RETRIEVER_REQUIRED)
            else:
                external_attempted = True
                snapshot = dict(external_retriever.fetch(target) or {})
                source_url = str(snapshot.get("source_url") or snapshot.get("url") or url)
                source_domain = _domain_for_url(source_url)
                source_type = str(snapshot.get("source_type") or "external")
                if not _domain_allowed(source_domain, approved_domains):
                    target_reasons.append(FAIL_UNAPPROVED_SOURCE)
                target_reasons.extend(
                    _snapshot_valid(
                        snapshot,
                        now_s=now_s,
                        max_age_s=max_snapshot_age_s,
                        freshness_required=target["freshness_required"],
                    )
                )
                snapshot_digest = _snapshot_digest(snapshot)
                content_digest = _content_digest(snapshot)
                freshness_digest = str(
                    snapshot.get("freshness_receipt_digest") or snapshot_digest
                )
                provenance = _provenance_refs(snapshot)
                content_excerpt = _content_excerpt(snapshot)
                finding_status = str(snapshot.get("finding_status") or "unverified")
                prompt_injection = _prompt_injection_detected(snapshot)
                grounding_channel = "external_snapshot"
                external_count += 1

        grounded = not target_reasons and (bool(refs) or requires_external)
        if not grounded:
            target_reasons.append(FAIL_TARGET_UNGROUNDED)
        target_reasons = _dedupe(target_reasons)
        reasons.extend(target_reasons)
        grounded_targets.append(
            GroundedResearchTarget(
                target=query,
                target_type=str(target["target_type"]),
                target_digest=_digest({"target": query, "type": target["target_type"]}),
                grounded=grounded,
                grounding_channel=grounding_channel,
                holoindex_status=status,
                holoindex_refs=refs,
                external_snapshot_digest=snapshot_digest,
                source_url=source_url,
                source_domain=source_domain,
                source_type=source_type,
                content_digest=content_digest,
                freshness_receipt_digest=freshness_digest,
                provenance_refs=provenance,
                content_excerpt=content_excerpt,
                finding_status=finding_status,
                prompt_injection_markers_detected=prompt_injection,
                untrusted_data_only=True,
                rejection_reasons=target_reasons,
            )
        )

    missing = [item.target for item in grounded_targets if not item.grounded]
    reasons = _dedupe(reasons)
    receipt_seed = {
        "request": req,
        "grounded_targets": [target.to_dict() for target in grounded_targets],
        "rejection_reasons": reasons,
    }
    receipt = ResearchGroundingReceipt(
        receipt_id="research_grounding_" + _digest(receipt_seed).removeprefix("sha256:")[:16],
        request_digest=_digest(req),
        targets_total=len(grounded_targets),
        targets_grounded=len([item for item in grounded_targets if item.grounded]),
        targets_missing=missing,
        internal_holoindex_first_performed=True,
        external_retrieval_attempted=external_attempted,
        external_snapshots_count=external_count,
        verified_research_receipt_required=True,
        rejected_negative_results_indexable=True,
        promoted_to_holoindex=False,
        no_holoindex_reindex_performed=True,
        no_pattern_memory_write_performed=True,
        no_command_execution_performed=True,
        no_model_instruction_from_external_content=True,
        rejection_reasons=reasons,
    )
    accepted = not reasons and bool(grounded_targets)
    return ResearchGroundingResult(
        decision=RESEARCH_GROUNDING_ACCEPT if accepted else RESEARCH_GROUNDING_REJECT,
        accepted=accepted,
        receipt=receipt,
        grounded_targets=grounded_targets,
        rejection_reasons=reasons,
    )


__all__ = [
    "DEFAULT_APPROVED_DOMAINS",
    "FAIL_EXTERNAL_RETRIEVER_REQUIRED",
    "FAIL_EXTERNAL_SNAPSHOT_INVALID",
    "FAIL_EXTERNAL_SNAPSHOT_STALE",
    "FAIL_HOLOINDEX_FIRST_MISSING",
    "FAIL_HOLOINDEX_INDEX_GAP",
    "FAIL_TARGET_UNGROUNDED",
    "FAIL_UNAPPROVED_SOURCE",
    "GroundedResearchTarget",
    "HoloIndexResearchMemory",
    "ExternalResearchRetriever",
    "ResearchGroundingReceipt",
    "ResearchGroundingResult",
    "RESEARCH_GROUNDING_ACCEPT",
    "RESEARCH_GROUNDING_REJECT",
    "ground_reddog_holoindex_first_external_research",
]
