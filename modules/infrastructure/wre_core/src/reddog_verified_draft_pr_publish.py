"""Verified draft PR publish gate for RedDog/WRE coding slices.

Slice: REDDOG_VERIFIED_DRAFT_PR_PUBLISH_PHASE1

This module publishes a draft PR only after the independent autonomous-slice
verifier has accepted the exact branch head. It delegates side effects to an
injected runner with the same draft-PR interface used by the existing
`worktree_pr_runner.py` helper. It never marks ready, merges, settles rewards,
writes PatternMemory, executes tests, or mutates HoloIndex.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Protocol

from modules.infrastructure.wre_core.src.wre_autonomous_slice_verifier_runtime import (
    AUTONOMOUS_SLICE_VERIFIER_ACCEPT,
)

VERIFIED_DRAFT_PR_PUBLISH_ACCEPT = "VERIFIED_DRAFT_PR_PUBLISH_ACCEPT"
VERIFIED_DRAFT_PR_PUBLISH_REJECT = "VERIFIED_DRAFT_PR_PUBLISH_REJECT"

FAIL_VERIFIER_NOT_ACCEPTED = "FAIL_VERIFIER_NOT_ACCEPTED"
FAIL_HEAD_MISMATCH = "FAIL_HEAD_MISMATCH"
FAIL_BRANCH_POLICY = "FAIL_BRANCH_POLICY"
FAIL_DRAFT_ONLY = "FAIL_DRAFT_ONLY"
FAIL_PR_METADATA = "FAIL_PR_METADATA"
FAIL_SECRET_IN_PR_METADATA = "FAIL_SECRET_IN_PR_METADATA"
FAIL_MODEL_RUNTIME_BINDING = "FAIL_MODEL_RUNTIME_BINDING"
FAIL_PUSH_BRANCH = "FAIL_PUSH_BRANCH"
FAIL_CREATE_DRAFT_PR = "FAIL_CREATE_DRAFT_PR"
FAIL_PR_URL = "FAIL_PR_URL"

ALLOWED_BRANCH_PREFIXES = ("feat/", "fix/", "docs/", "test/", "chore/")
SECRET_MARKERS = (
    "authorization:",
    "bearer ",
    "api_key",
    "apikey",
    "private_key",
    "begin private key",
    "secret=",
    "token=",
    "password=",
)


class DraftPrRunner(Protocol):
    def push_branch(self, *, worktree_path: Path, branch_name: str) -> Mapping[str, Any]:
        ...

    def create_draft_pr(
        self,
        *,
        branch_name: str,
        base_branch: str,
        title: str,
        body: str,
    ) -> str:
        ...


@dataclass(frozen=True)
class VerifiedDraftPrPublishReceipt:
    receipt_id: str
    work_order_id: str
    slice_name: str
    verifier_receipt_id: str
    branch_name: str
    base_branch: str
    verified_head_sha: str
    draft_pr_url: str
    changed_paths: List[str]
    model_runtime_binding_receipt_id: Optional[str]
    model_runtime_binding_digest: str
    rejection_reasons: List[str]
    accepted: bool
    no_ready_performed: bool = True
    no_merge_performed: bool = True
    no_pattern_memory_write_performed: bool = True
    no_reward_settlement_performed: bool = True
    no_holoindex_reindex_performed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class VerifiedDraftPrPublishResult:
    decision: str
    accepted: bool
    receipt: VerifiedDraftPrPublishReceipt
    rejection_reasons: List[str] = field(default_factory=list)
    push_result: Mapping[str, Any] = field(default_factory=dict)
    no_ready_performed: bool = True
    no_merge_performed: bool = True
    no_pattern_memory_write_performed: bool = True
    no_reward_settlement_performed: bool = True
    no_holoindex_reindex_performed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["receipt"] = self.receipt.to_dict()
        payload["push_result"] = dict(self.push_result)
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


def _mapping(value: Any) -> Mapping[str, Any]:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, Mapping):
        return value
    return {}


def _list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _dedupe(values: List[str]) -> List[str]:
    seen = set()
    ordered: List[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            seen.add(text)
            ordered.append(text)
    return ordered


def _contains_secret(value: Any) -> bool:
    text = json.dumps(value, sort_keys=True, default=str).lower()
    return any(marker in text for marker in SECRET_MARKERS)


def _draft_url_ok(url: str) -> bool:
    return url.startswith("https://github.com/") and "/pull/" in url


def _is_digest(value: Any) -> bool:
    text = str(value or "")
    return (
        text.startswith("sha256:")
        and len(text) == 71
        and all(ch in "0123456789abcdef" for ch in text.removeprefix("sha256:"))
    )


def _runtime_binding_pair(value: Mapping[str, Any]) -> tuple[str, str]:
    receipt_id = str(
        value.get("model_runtime_binding_receipt_id")
        or value.get("runtime_binding_receipt_id")
        or ""
    )
    digest = str(value.get("model_runtime_binding_digest") or "")
    return receipt_id, digest


def _runtime_binding_ok(
    verifier_receipt: Mapping[str, Any],
    request: Mapping[str, Any],
) -> tuple[bool, Optional[str], str]:
    pairs = [
        pair
        for pair in (
            _runtime_binding_pair(verifier_receipt),
            _runtime_binding_pair(request),
        )
        if pair[0] or pair[1]
    ]
    if not pairs:
        return True, None, ""
    normalized: List[tuple[str, str]] = []
    for receipt_id, digest in pairs:
        if not receipt_id or not digest:
            return False, receipt_id or None, digest
        if not receipt_id.startswith("reddog_model_runtime_binding:") or not _is_digest(digest):
            return False, receipt_id, digest
        normalized.append((receipt_id, digest))
    first = normalized[0]
    if any(pair != first for pair in normalized[1:]):
        return False, first[0], first[1]
    return True, first[0], first[1]


def _receipt_seed(
    *,
    work_order_id: str,
    slice_name: str,
    verifier_receipt_id: str,
    branch_name: str,
    base_branch: str,
    verified_head_sha: str,
    draft_pr_url: str,
    changed_paths: List[str],
    model_runtime_binding_receipt_id: str,
    model_runtime_binding_digest: str,
    rejection_reasons: List[str],
) -> Dict[str, Any]:
    return {
        "work_order_id": work_order_id,
        "slice_name": slice_name,
        "verifier_receipt_id": verifier_receipt_id,
        "branch_name": branch_name,
        "base_branch": base_branch,
        "verified_head_sha": verified_head_sha,
        "draft_pr_url": draft_pr_url,
        "changed_paths": changed_paths,
        "model_runtime_binding_receipt_id": model_runtime_binding_receipt_id,
        "model_runtime_binding_digest": model_runtime_binding_digest,
        "rejection_reasons": rejection_reasons,
    }


def _result(
    *,
    accepted: bool,
    reasons: List[str],
    work_order_id: str,
    slice_name: str,
    verifier_receipt_id: str,
    branch_name: str,
    base_branch: str,
    verified_head_sha: str,
    draft_pr_url: str,
    changed_paths: List[str],
    model_runtime_binding_receipt_id: Optional[str] = None,
    model_runtime_binding_digest: str = "",
    push_result: Mapping[str, Any] | None = None,
) -> VerifiedDraftPrPublishResult:
    deduped = _dedupe(reasons)
    seed = _receipt_seed(
        work_order_id=work_order_id,
        slice_name=slice_name,
        verifier_receipt_id=verifier_receipt_id,
        branch_name=branch_name,
        base_branch=base_branch,
        verified_head_sha=verified_head_sha,
        draft_pr_url=draft_pr_url,
        changed_paths=changed_paths,
        model_runtime_binding_receipt_id=model_runtime_binding_receipt_id or "",
        model_runtime_binding_digest=model_runtime_binding_digest,
        rejection_reasons=deduped,
    )
    receipt = VerifiedDraftPrPublishReceipt(
        receipt_id="verified_draft_pr_" + _digest(seed).removeprefix("sha256:")[:16],
        work_order_id=work_order_id,
        slice_name=slice_name,
        verifier_receipt_id=verifier_receipt_id,
        branch_name=branch_name,
        base_branch=base_branch,
        verified_head_sha=verified_head_sha,
        draft_pr_url=draft_pr_url,
        changed_paths=changed_paths,
        model_runtime_binding_receipt_id=model_runtime_binding_receipt_id,
        model_runtime_binding_digest=model_runtime_binding_digest,
        rejection_reasons=deduped,
        accepted=accepted,
    )
    return VerifiedDraftPrPublishResult(
        decision=(
            VERIFIED_DRAFT_PR_PUBLISH_ACCEPT
            if accepted
            else VERIFIED_DRAFT_PR_PUBLISH_REJECT
        ),
        accepted=accepted,
        receipt=receipt,
        rejection_reasons=deduped,
        push_result=dict(push_result or {}),
    )


def publish_verified_draft_pr(
    request: Mapping[str, Any],
    *,
    runner: DraftPrRunner,
) -> VerifiedDraftPrPublishResult:
    """Push a verified branch and create a draft PR only.

    The caller must provide an accepted autonomous-slice verifier result. This
    function refuses to publish if the pre-publish branch head does not match the
    verifier receipt's head SHA.
    """
    req = _mapping(request)
    verifier_result = _mapping(req.get("verifier_result"))
    verifier_receipt = _mapping(verifier_result.get("receipt"))
    work_order_id = str(verifier_receipt.get("work_order_id") or req.get("work_order_id") or "")
    slice_name = str(verifier_receipt.get("slice_name") or req.get("slice_name") or "")
    verifier_receipt_id = str(verifier_receipt.get("receipt_id") or "")
    verified_head_sha = str(verifier_receipt.get("head_sha") or "")
    changed_paths = [str(path) for path in _list(verifier_receipt.get("changed_paths"))]
    branch_name = str(req.get("branch_name") or "")
    base_branch = str(req.get("base_branch") or "main")
    title = str(req.get("pr_title") or "")
    body = str(req.get("pr_body") or "")
    worktree_path = Path(str(req.get("worktree_path") or ""))
    reasons: List[str] = []
    runtime_binding_ok, runtime_binding_id, runtime_binding_digest = _runtime_binding_ok(
        verifier_receipt,
        req,
    )

    if (
        verifier_result.get("accepted") is not True
        or verifier_result.get("decision") != AUTONOMOUS_SLICE_VERIFIER_ACCEPT
        or not verifier_receipt_id
    ):
        reasons.append(FAIL_VERIFIER_NOT_ACCEPTED)
    if str(req.get("pre_publish_branch_head_sha") or "") != verified_head_sha:
        reasons.append(FAIL_HEAD_MISMATCH)
    if base_branch != "main" or not branch_name.startswith(ALLOWED_BRANCH_PREFIXES):
        reasons.append(FAIL_BRANCH_POLICY)
    if (
        req.get("draft_pr_only") is not True
        or req.get("mark_ready") is True
        or req.get("merge") is True
    ):
        reasons.append(FAIL_DRAFT_ONLY)
    if not title.strip() or not body.strip() or not changed_paths:
        reasons.append(FAIL_PR_METADATA)
    if _contains_secret({"title": title, "body": body}):
        reasons.append(FAIL_SECRET_IN_PR_METADATA)
    if not runtime_binding_ok:
        reasons.append(FAIL_MODEL_RUNTIME_BINDING)

    if reasons:
        return _result(
            accepted=False,
            reasons=reasons,
            work_order_id=work_order_id,
            slice_name=slice_name,
            verifier_receipt_id=verifier_receipt_id,
            branch_name=branch_name,
            base_branch=base_branch,
            verified_head_sha=verified_head_sha,
            draft_pr_url="",
            changed_paths=changed_paths,
            model_runtime_binding_receipt_id=runtime_binding_id,
            model_runtime_binding_digest=runtime_binding_digest,
        )

    push_result = dict(runner.push_branch(worktree_path=worktree_path, branch_name=branch_name))
    if push_result.get("ok") is not True:
        return _result(
            accepted=False,
            reasons=[FAIL_PUSH_BRANCH],
            work_order_id=work_order_id,
            slice_name=slice_name,
            verifier_receipt_id=verifier_receipt_id,
            branch_name=branch_name,
            base_branch=base_branch,
            verified_head_sha=verified_head_sha,
            draft_pr_url="",
            changed_paths=changed_paths,
            model_runtime_binding_receipt_id=runtime_binding_id,
            model_runtime_binding_digest=runtime_binding_digest,
            push_result=push_result,
        )

    try:
        draft_pr_url = runner.create_draft_pr(
            branch_name=branch_name,
            base_branch=base_branch,
            title=title,
            body=body,
        )
    except Exception:
        return _result(
            accepted=False,
            reasons=[FAIL_CREATE_DRAFT_PR],
            work_order_id=work_order_id,
            slice_name=slice_name,
            verifier_receipt_id=verifier_receipt_id,
            branch_name=branch_name,
            base_branch=base_branch,
            verified_head_sha=verified_head_sha,
            draft_pr_url="",
            changed_paths=changed_paths,
            model_runtime_binding_receipt_id=runtime_binding_id,
            model_runtime_binding_digest=runtime_binding_digest,
            push_result=push_result,
        )

    if not _draft_url_ok(str(draft_pr_url)):
        return _result(
            accepted=False,
            reasons=[FAIL_PR_URL],
            work_order_id=work_order_id,
            slice_name=slice_name,
            verifier_receipt_id=verifier_receipt_id,
            branch_name=branch_name,
            base_branch=base_branch,
            verified_head_sha=verified_head_sha,
            draft_pr_url=str(draft_pr_url or ""),
            changed_paths=changed_paths,
            model_runtime_binding_receipt_id=runtime_binding_id,
            model_runtime_binding_digest=runtime_binding_digest,
            push_result=push_result,
        )

    return _result(
        accepted=True,
        reasons=[],
        work_order_id=work_order_id,
        slice_name=slice_name,
        verifier_receipt_id=verifier_receipt_id,
        branch_name=branch_name,
        base_branch=base_branch,
        verified_head_sha=verified_head_sha,
        draft_pr_url=str(draft_pr_url),
        changed_paths=changed_paths,
        model_runtime_binding_receipt_id=runtime_binding_id,
        model_runtime_binding_digest=runtime_binding_digest,
        push_result=push_result,
    )


__all__ = [
    "FAIL_BRANCH_POLICY",
    "FAIL_CREATE_DRAFT_PR",
    "FAIL_DRAFT_ONLY",
    "FAIL_HEAD_MISMATCH",
    "FAIL_MODEL_RUNTIME_BINDING",
    "FAIL_PR_METADATA",
    "FAIL_PR_URL",
    "FAIL_PUSH_BRANCH",
    "FAIL_SECRET_IN_PR_METADATA",
    "FAIL_VERIFIER_NOT_ACCEPTED",
    "VERIFIED_DRAFT_PR_PUBLISH_ACCEPT",
    "VERIFIED_DRAFT_PR_PUBLISH_REJECT",
    "VerifiedDraftPrPublishReceipt",
    "VerifiedDraftPrPublishResult",
    "publish_verified_draft_pr",
]
