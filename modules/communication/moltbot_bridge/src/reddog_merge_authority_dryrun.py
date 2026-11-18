"""RedDog merge authority dry-run.

Slice: REDDOG_MERGE_AUTHORITY_DRYRUN_PHASE1
Contract: docs/audits/architecture/REDDOG_MERGE_AUTHORITY_CONTRACT_PHASE1.md

This module validates a future merge-promotion packet and emits a dry-run decision.
It never calls GitHub, `gh`, subprocesses, shell commands, HoloIndex re-indexing, or
any merge API. It only answers whether the evidence packet is complete enough for a
future merge authority implementation to consider.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Union

MERGE_AUTHORITY_ACCEPT = "MERGE_AUTHORITY_ACCEPT"
MERGE_AUTHORITY_REJECT = "MERGE_AUTHORITY_REJECT"

FAIL_REQUIRED_FIELD = "FAIL_REQUIRED_FIELD"
FAIL_PR_IDENTITY = "FAIL_PR_IDENTITY"
FAIL_HEAD_SHA = "FAIL_HEAD_SHA"
FAIL_MERGE_METHOD = "FAIL_MERGE_METHOD"
FAIL_POLICY_TIER = "FAIL_POLICY_TIER"
FAIL_SELF_PROMOTION = "FAIL_SELF_PROMOTION"
FAIL_SIGNING_KEY_REUSE = "FAIL_SIGNING_KEY_REUSE"
FAIL_SIGNED_AUTHORITY = "FAIL_SIGNED_AUTHORITY"
FAIL_RECEIPT_CHAIN = "FAIL_RECEIPT_CHAIN"
FAIL_WORKTREE_RECEIPT = "FAIL_WORKTREE_RECEIPT"
FAIL_SHELL_RECEIPTS = "FAIL_SHELL_RECEIPTS"
FAIL_CI_STATUS = "FAIL_CI_STATUS"
FAIL_DIFF_SUMMARY = "FAIL_DIFF_SUMMARY"
FAIL_REVIEW_OPINIONS = "FAIL_REVIEW_OPINIONS"
FAIL_CONSENSUS_REQUIRED = "FAIL_CONSENSUS_REQUIRED"
FAIL_PERMISSION_SNAPSHOT = "FAIL_PERMISSION_SNAPSHOT"
FAIL_HOLOINDEX_INDEX_GAP = "FAIL_HOLOINDEX_INDEX_GAP"
FAIL_HOLOINDEX_FRESHNESS_RECEIPT = "FAIL_HOLOINDEX_FRESHNESS_RECEIPT"
FAIL_PROTECTED_SURFACE = "FAIL_PROTECTED_SURFACE"
FAIL_EXPIRY = "FAIL_EXPIRY"
FAIL_NONCE = "FAIL_NONCE"
FAIL_SECRET_IN_REQUEST = "FAIL_SECRET_IN_REQUEST"

POLICY_TIERS = frozenset({"f0_sovereign", "foundup_repo", "docs_only", "external_foundup"})
MERGE_METHODS = frozenset({"squash", "merge", "rebase"})
HIGH_AUTHORITY_TIERS = frozenset({"f0_sovereign", "foundup_repo", "external_foundup"})
SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
HEAD_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SECRET_MARKERS = (
    "bearer ",
    "authorization:",
    "api_key",
    "apikey",
    "private_key",
    "begin private key",
    "token=",
    "secret=",
    "password=",
)
PROTECTED_PATH_PATTERNS = (
    ".github/workflows/",
    "WSP_framework/",
    "holo_index/",
    "modules/communication/moltbot_bridge/src/reddog_wre_execution_valve.py",
    "modules/communication/moltbot_bridge/src/reddog_work_order_signature_verifier.py",
    "modules/communication/moltbot_bridge/src/reddog_signed_receipt_chain.py",
    "modules/communication/moltbot_bridge/src/reddog_operator_loop_wardrobe_selection.py",
    "modules/communication/moltbot_bridge/src/reddog_merge_authority",
    "modules/**/secrets/",
    "modules/**/wallet/",
    "modules/**/nonce/",
    "modules/**/permission/",
)


@dataclass(frozen=True)
class RedDogMergeAuthorityRequest:
    merge_request_id: str
    work_order_id: str
    repo_full_name: str
    pr_number: int
    base_ref: str
    head_ref: str
    head_sha: str
    author_principal_id: str
    author_reddog_id: str
    promoter_principal_id: str
    promoter_reddog_id: Optional[str]
    signed_work_authority_digest: str
    signed_receipt_chain_terminal_hash: str
    worktree_write_receipt_digest: str
    shell_run_receipt_digests: List[str]
    ci_status: Mapping[str, Any]
    diff_summary: Mapping[str, Any]
    review_opinions: List[Mapping[str, Any]]
    consensus_receipt_digest: Optional[str]
    holoindex_evidence: Mapping[str, Any]
    permission_snapshot_digest: str
    policy_tier: str
    requested_merge_method: str
    expiry: str
    nonce: str
    author_lane_id: str = ""
    promoter_signature_digest: str = ""
    author_key_fingerprint: str = ""
    promoter_key_fingerprint: str = ""
    sovereign_override_digest: Optional[str] = None
    now: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RedDogMergeAuthorityDecision:
    decision: str
    merge_request_id: str
    work_order_id: str
    pr_number: int
    expected_head_sha: str
    merge_method: str
    promoter_signature_digest: str
    consensus_receipt_digest: Optional[str]
    ci_status_digest: str
    review_set_digest: str
    machine_diff_summary_digest: str
    holoindex_freshness_receipt_digest: str
    rejection_reasons: List[str]
    no_merge_performed: bool = True
    no_reward_settlement_performed: bool = True
    no_holoindex_reindex_performed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RedDogMergeAuthorityDryRunResult:
    accepted: bool
    decision: RedDogMergeAuthorityDecision
    no_execution_performed: bool = True
    no_github_call_performed: bool = True
    no_merge_performed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["decision"] = self.decision.to_dict()
        return payload


def _mapping(request: Union[RedDogMergeAuthorityRequest, Mapping[str, Any]]) -> Mapping[str, Any]:
    if isinstance(request, RedDogMergeAuthorityRequest):
        return request.to_dict()
    return request


def _digest(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _dedupe(values: Iterable[str]) -> List[str]:
    seen = set()
    ordered: List[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            seen.add(text)
            ordered.append(text)
    return ordered


def _is_digest(value: Any) -> bool:
    return isinstance(value, str) and SHA256_RE.fullmatch(value) is not None


def _digest_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if _is_digest(item)]


def _is_head_sha(value: Any) -> bool:
    return isinstance(value, str) and HEAD_SHA_RE.fullmatch(value) is not None


def _parse_time(value: str) -> Optional[datetime]:
    text = str(value or "").strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _expired(expiry: str, now: Optional[str]) -> bool:
    expiry_dt = _parse_time(expiry)
    if expiry_dt is None:
        return True
    now_dt = _parse_time(now or "") if now else datetime.now(timezone.utc)
    if now_dt is None:
        return True
    return now_dt > expiry_dt


def _contains_raw_secret(payload: Any) -> bool:
    if isinstance(payload, Mapping):
        return any(_contains_raw_secret(value) for value in payload.values())
    if isinstance(payload, (list, tuple)):
        return any(_contains_raw_secret(value) for value in payload)
    text = str(payload or "").lower()
    return any(marker in text for marker in SECRET_MARKERS)


def _path_normalized(path: str) -> str:
    return str(path or "").replace("\\", "/").lstrip("./").strip()


def _is_protected_path(path: str) -> bool:
    normalized = _path_normalized(path)
    lowered = normalized.lower()
    base = lowered.rsplit("/", 1)[-1]
    if base.startswith(".env"):
        return True
    for pattern in PROTECTED_PATH_PATTERNS:
        pat = pattern.lower()
        if "**" in pat:
            prefix, suffix = pat.split("**", 1)
            if lowered.startswith(prefix) and suffix.strip("/") in lowered:
                return True
            continue
        if lowered.startswith(pat):
            return True
    return False


def _changed_paths(diff_summary: Mapping[str, Any]) -> List[str]:
    paths = diff_summary.get("changed_paths")
    if not isinstance(paths, list):
        return []
    return [str(path) for path in paths if str(path or "").strip()]


def _ci_ok(ci_status: Mapping[str, Any], head_sha: str) -> bool:
    if ci_status.get("head_sha") != head_sha:
        return False
    if ci_status.get("status") not in ("success", "pass"):
        return False
    checks = ci_status.get("required_checks")
    if not isinstance(checks, list) or not checks:
        return False
    for check in checks:
        if not isinstance(check, Mapping):
            return False
        if check.get("head_sha") not in (None, head_sha):
            return False
        conclusion = str(check.get("conclusion") or check.get("status") or "").lower()
        if conclusion not in ("success", "pass", "skipped_report_only"):
            return False
    return _is_digest(ci_status.get("ci_status_digest"))


def _diff_summary_ok(diff_summary: Mapping[str, Any]) -> bool:
    if diff_summary.get("source") != "machine_derived":
        return False
    if diff_summary.get("red_dog_prose_source") is True:
        return False
    if not _is_digest(diff_summary.get("diff_summary_digest")):
        return False
    return bool(_changed_paths(diff_summary))


def _review_opinions_ok(reviews: Any, req: Mapping[str, Any]) -> bool:
    if not isinstance(reviews, list) or not reviews:
        return False
    author_reddog = str(req.get("author_reddog_id") or "")
    author_principal = str(req.get("author_principal_id") or "")
    author_lane = str(req.get("author_lane_id") or "")
    author_key = str(req.get("author_key_fingerprint") or "")
    for review in reviews:
        if not isinstance(review, Mapping):
            return False
        if review.get("accepted") is not True:
            return False
        if not _is_digest(review.get("review_opinion_digest")):
            return False
        if review.get("reviewer_reddog_id") in ("", None, author_reddog):
            return False
        if review.get("reviewer_principal_id") in ("", None, author_principal):
            return False
        if author_lane and review.get("lane_id") == author_lane:
            return False
        if author_key and review.get("reviewer_key_fingerprint") == author_key:
            return False
    return True


def _holoindex_freshness_digest(holoindex_evidence: Mapping[str, Any]) -> str:
    return str(
        holoindex_evidence.get("holoindex_freshness_receipt_digest")
        or holoindex_evidence.get("freshness_receipt_digest")
        or ""
    )


def _holoindex_gap(holoindex_evidence: Mapping[str, Any]) -> bool:
    return (
        holoindex_evidence.get("index_gap_detected") is True
        or str(holoindex_evidence.get("retrieval_quality") or "").upper() == "INDEX_GAP"
    )


def _required_strings_present(req: Mapping[str, Any], names: Sequence[str]) -> bool:
    return all(isinstance(req.get(name), str) and bool(str(req.get(name)).strip()) for name in names)


def plan_reddog_merge_authority_dry_run(
    request: Union[RedDogMergeAuthorityRequest, Mapping[str, Any]],
) -> RedDogMergeAuthorityDryRunResult:
    """Validate a future merge promotion and emit a dry-run decision only."""
    req = _mapping(request)
    reasons: List[str] = []

    string_fields = (
        "merge_request_id",
        "work_order_id",
        "repo_full_name",
        "base_ref",
        "head_ref",
        "head_sha",
        "author_principal_id",
        "author_reddog_id",
        "promoter_principal_id",
        "signed_work_authority_digest",
        "signed_receipt_chain_terminal_hash",
        "worktree_write_receipt_digest",
        "permission_snapshot_digest",
        "policy_tier",
        "requested_merge_method",
        "expiry",
        "nonce",
        "promoter_signature_digest",
    )
    if not _required_strings_present(req, string_fields):
        reasons.append(FAIL_REQUIRED_FIELD)

    pr_number = req.get("pr_number")
    if not isinstance(pr_number, int) or pr_number <= 0:
        reasons.append(FAIL_PR_IDENTITY)
    if str(req.get("base_ref") or "") == str(req.get("head_ref") or ""):
        reasons.append(FAIL_PR_IDENTITY)

    head_sha = str(req.get("head_sha") or "")
    if not _is_head_sha(head_sha):
        reasons.append(FAIL_HEAD_SHA)

    if req.get("requested_merge_method") not in MERGE_METHODS:
        reasons.append(FAIL_MERGE_METHOD)
    policy_tier = str(req.get("policy_tier") or "")
    if policy_tier not in POLICY_TIERS:
        reasons.append(FAIL_POLICY_TIER)

    same_principal = req.get("author_principal_id") == req.get("promoter_principal_id")
    if same_principal and policy_tier != "docs_only" and not req.get("sovereign_override_digest"):
        reasons.append(FAIL_SELF_PROMOTION)
    if req.get("author_reddog_id") and req.get("author_reddog_id") == req.get("promoter_reddog_id"):
        reasons.append(FAIL_SELF_PROMOTION)
    if req.get("author_key_fingerprint") and req.get("author_key_fingerprint") == req.get("promoter_key_fingerprint"):
        reasons.append(FAIL_SIGNING_KEY_REUSE)

    if not _is_digest(req.get("signed_work_authority_digest")):
        reasons.append(FAIL_SIGNED_AUTHORITY)
    if not _is_digest(req.get("signed_receipt_chain_terminal_hash")):
        reasons.append(FAIL_RECEIPT_CHAIN)
    if not _is_digest(req.get("worktree_write_receipt_digest")):
        reasons.append(FAIL_WORKTREE_RECEIPT)
    if not _digest_list(req.get("shell_run_receipt_digests")):
        reasons.append(FAIL_SHELL_RECEIPTS)
    if not _is_digest(req.get("permission_snapshot_digest")):
        reasons.append(FAIL_PERMISSION_SNAPSHOT)
    if not _is_digest(req.get("promoter_signature_digest")):
        reasons.append(FAIL_SIGNED_AUTHORITY)
    if not str(req.get("nonce") or "").strip():
        reasons.append(FAIL_NONCE)
    if _expired(str(req.get("expiry") or ""), None if req.get("now") is None else str(req.get("now"))):
        reasons.append(FAIL_EXPIRY)

    ci_status = dict(req.get("ci_status") or {})
    if not _ci_ok(ci_status, head_sha):
        reasons.append(FAIL_CI_STATUS)

    diff_summary = dict(req.get("diff_summary") or {})
    if not _diff_summary_ok(diff_summary):
        reasons.append(FAIL_DIFF_SUMMARY)
    changed_paths = _changed_paths(diff_summary)
    protected_surface = any(_is_protected_path(path) for path in changed_paths)

    reviews = req.get("review_opinions")
    if not _review_opinions_ok(reviews, req):
        reasons.append(FAIL_REVIEW_OPINIONS)

    consensus_required = policy_tier in HIGH_AUTHORITY_TIERS or protected_surface
    if consensus_required and not _is_digest(req.get("consensus_receipt_digest")):
        reasons.append(FAIL_CONSENSUS_REQUIRED)
    if protected_surface and policy_tier == "docs_only":
        reasons.append(FAIL_PROTECTED_SURFACE)

    holoindex_evidence = dict(req.get("holoindex_evidence") or {})
    if _holoindex_gap(holoindex_evidence):
        reasons.append(FAIL_HOLOINDEX_INDEX_GAP)
    holo_digest = _holoindex_freshness_digest(holoindex_evidence)
    if not _is_digest(holo_digest):
        reasons.append(FAIL_HOLOINDEX_FRESHNESS_RECEIPT)

    if _contains_raw_secret(
        {
            "repo_full_name": req.get("repo_full_name"),
            "head_ref": req.get("head_ref"),
            "diff_summary": diff_summary,
            "review_opinions": reviews,
        }
    ):
        reasons.append(FAIL_SECRET_IN_REQUEST)

    deduped = _dedupe(reasons)
    accepted = not deduped
    decision = RedDogMergeAuthorityDecision(
        decision=MERGE_AUTHORITY_ACCEPT if accepted else MERGE_AUTHORITY_REJECT,
        merge_request_id=str(req.get("merge_request_id") or ""),
        work_order_id=str(req.get("work_order_id") or ""),
        pr_number=int(pr_number) if isinstance(pr_number, int) else 0,
        expected_head_sha=head_sha,
        merge_method=str(req.get("requested_merge_method") or ""),
        promoter_signature_digest=str(req.get("promoter_signature_digest") or ""),
        consensus_receipt_digest=(
            None if req.get("consensus_receipt_digest") is None else str(req.get("consensus_receipt_digest"))
        ),
        ci_status_digest=str(ci_status.get("ci_status_digest") or ""),
        review_set_digest=_digest(reviews or []),
        machine_diff_summary_digest=str(diff_summary.get("diff_summary_digest") or ""),
        holoindex_freshness_receipt_digest=holo_digest,
        rejection_reasons=deduped,
    )
    return RedDogMergeAuthorityDryRunResult(
        accepted=accepted,
        decision=decision,
    )


__all__ = [
    "FAIL_CI_STATUS",
    "FAIL_CONSENSUS_REQUIRED",
    "FAIL_DIFF_SUMMARY",
    "FAIL_EXPIRY",
    "FAIL_HEAD_SHA",
    "FAIL_HOLOINDEX_FRESHNESS_RECEIPT",
    "FAIL_HOLOINDEX_INDEX_GAP",
    "FAIL_MERGE_METHOD",
    "FAIL_NONCE",
    "FAIL_PERMISSION_SNAPSHOT",
    "FAIL_POLICY_TIER",
    "FAIL_PR_IDENTITY",
    "FAIL_PROTECTED_SURFACE",
    "FAIL_RECEIPT_CHAIN",
    "FAIL_REQUIRED_FIELD",
    "FAIL_REVIEW_OPINIONS",
    "FAIL_SECRET_IN_REQUEST",
    "FAIL_SELF_PROMOTION",
    "FAIL_SHELL_RECEIPTS",
    "FAIL_SIGNED_AUTHORITY",
    "FAIL_SIGNING_KEY_REUSE",
    "FAIL_WORKTREE_RECEIPT",
    "MERGE_AUTHORITY_ACCEPT",
    "MERGE_AUTHORITY_REJECT",
    "RedDogMergeAuthorityDecision",
    "RedDogMergeAuthorityDryRunResult",
    "RedDogMergeAuthorityRequest",
    "plan_reddog_merge_authority_dry_run",
]
