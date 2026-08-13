"""WRE autonomous slice verifier runtime.

Slice: WRE_AUTONOMOUS_SLICE_VERIFIER_RUNTIME_PHASE1

This module verifies author-output evidence for one bounded coding slice. It
does not run commands, call GitHub, publish PRs, merge, write PatternMemory, or
settle rewards. It consumes machine-derived evidence and returns an ACCEPT or
fail-closed REJECT decision for downstream draft-PR publishing.
"""

from __future__ import annotations
import fnmatch
import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence
from modules.infrastructure.wre_core.src.wre_test_differential_verification import verify_test_differential_evidence
from modules.communication.moltbot_bridge.src.reddog_signer_optional_authority_bindings import (
    optional_authority_binding_values_valid,
)
from modules.communication.moltbot_bridge.src.reddog_work_authority_digest import (
    signed_authority_envelope_digest_matches,
)
AUTONOMOUS_SLICE_VERIFIER_ACCEPT = "AUTONOMOUS_SLICE_VERIFIER_ACCEPT"
AUTONOMOUS_SLICE_VERIFIER_REJECT = "AUTONOMOUS_SLICE_VERIFIER_REJECT"
FAIL_REQUIRED_FIELD = "FAIL_REQUIRED_FIELD"
FAIL_SELF_VERIFICATION = "FAIL_SELF_VERIFICATION"
FAIL_HEAD_SHA = "FAIL_HEAD_SHA"
FAIL_DIFF_EVIDENCE = "FAIL_DIFF_EVIDENCE"
FAIL_SCOPE_VIOLATION = "FAIL_SCOPE_VIOLATION"
FAIL_PROTECTED_SURFACE = "FAIL_PROTECTED_SURFACE"
FAIL_SECRET_IN_DIFF = "FAIL_SECRET_IN_DIFF"
FAIL_TEST_EVIDENCE = "FAIL_TEST_EVIDENCE"
FAIL_SIGNED_AUTHORITY = "FAIL_SIGNED_AUTHORITY"
FAIL_RECEIPT_CHAIN = "FAIL_RECEIPT_CHAIN"
FAIL_WORKTREE_RECEIPT = "FAIL_WORKTREE_RECEIPT"
FAIL_HOLOINDEX_EVIDENCE = "FAIL_HOLOINDEX_EVIDENCE"
FAIL_MODEL_RUNTIME_BINDING = "FAIL_MODEL_RUNTIME_BINDING"
FAIL_MEMEX_SUPPLY_BINDING = "FAIL_MEMEX_SUPPLY_BINDING"
FAIL_PATTERN_MEMORY_WRITE = "FAIL_PATTERN_MEMORY_WRITE"
FAIL_PR_OR_MERGE_ALREADY_PERFORMED = "FAIL_PR_OR_MERGE_ALREADY_PERFORMED"

HEAD_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
PROTECTED_PATH_PREFIXES = (
    ".github/workflows/",
    "WSP_framework/",
    "holo_index/",
    "modules/infrastructure/wre_core/src/wre_autonomous_slice_verifier_runtime.py",
    "modules/communication/moltbot_bridge/src/reddog_wre_execution_valve.py",
    "modules/communication/moltbot_bridge/src/reddog_work_order_signature_verifier.py",
    "modules/communication/moltbot_bridge/src/reddog_signed_receipt_chain.py",
    "docs/contracts/REDDOG_PRINCIPAL_IDENTITY_AND_DELEGATION_CONTRACT_PHASE1.md",
)

DENIED_PATH_FRAGMENTS = (
    "/secrets/",
    "/wallet/",
    "/private_key",
    "/nonce/",
    "/permission/",
)

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
FAIL_ASSURANCE_RESERVATION = "FAIL_ASSURANCE_RESERVATION"


@dataclass(frozen=True)
class AutonomousSliceVerifierReceipt:
    receipt_id: str
    work_order_id: str
    slice_name: str
    verifier_id: str
    worker_id: str
    assurance_reservation_id: str
    assurance_reservation_digest: str
    verifier_task_id: str
    base_sha: str
    head_sha: str
    changed_paths: List[str]
    diff_digest: str
    test_evidence_digest: str
    signed_authority_digest: str
    receipt_chain_terminal_hash: str
    worktree_receipt_digest: str
    holoindex_freshness_receipt_digest: str
    model_runtime_binding_receipt_id: Optional[str]
    model_runtime_binding_digest: str
    memex_supply_receipt_id: Optional[str]
    memex_supply_digest: str
    rejection_reasons: List[str]
    accepted: bool
    no_command_execution_performed: bool = True
    no_pr_publish_performed: bool = True
    no_merge_performed: bool = True
    no_pattern_memory_write_performed: bool = True
    no_reward_settlement_performed: bool = True
    no_holoindex_reindex_performed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AutonomousSliceVerifierResult:
    decision: str
    accepted: bool
    receipt: AutonomousSliceVerifierReceipt
    rejection_reasons: List[str] = field(default_factory=list)
    no_execution_performed: bool = True
    no_command_execution_performed: bool = True
    no_github_call_performed: bool = True
    no_pr_publish_performed: bool = True
    no_merge_performed: bool = True
    no_pattern_memory_write_performed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["receipt"] = self.receipt.to_dict()
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


def _dedupe(values: Iterable[str]) -> List[str]:
    seen = set()
    ordered: List[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            seen.add(text)
            ordered.append(text)
    return ordered


def _mapping(value: Any) -> Mapping[str, Any]:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, Mapping):
        return value
    return {}


def _list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _is_head_sha(value: Any) -> bool:
    return isinstance(value, str) and HEAD_SHA_RE.fullmatch(value) is not None


def _is_digest(value: Any) -> bool:
    return isinstance(value, str) and SHA256_RE.fullmatch(value) is not None


def _normalize_path(path: Any) -> str:
    text = str(path or "").replace("\\", "/").strip()
    while text.startswith("./"):
        text = text[2:]
    return text.strip("/")


def _safe_repo_path(path: str) -> bool:
    if not path or path.startswith("/") or ":" in path:
        return False
    parts = [part for part in path.split("/") if part]
    return bool(parts) and ".." not in parts


def _matches_any(path: str, patterns: Sequence[str]) -> bool:
    lowered = path.lower()
    for pattern in patterns:
        pat = str(pattern or "").replace("\\", "/").strip().lower()
        if pat and fnmatch.fnmatch(lowered, pat):
            return True
    return False


def _protected_path(path: str) -> bool:
    lowered = path.lower()
    basename = lowered.rsplit("/", 1)[-1]
    if basename.startswith(".env"):
        return True
    if any(fragment in lowered for fragment in DENIED_PATH_FRAGMENTS):
        return True
    return any(lowered.startswith(prefix.lower()) for prefix in PROTECTED_PATH_PREFIXES)


def _changed_paths(diff_evidence: Mapping[str, Any]) -> List[str]:
    raw_paths = _list(diff_evidence.get("changed_paths"))
    normalized = [_normalize_path(path) for path in raw_paths]
    return [path for path in normalized if path]


def _diff_contains_secret(diff_evidence: Mapping[str, Any]) -> bool:
    candidates: List[str] = []
    for key in ("diff_text_sample", "added_lines", "removed_lines"):
        value = diff_evidence.get(key)
        if isinstance(value, list):
            candidates.extend(str(item) for item in value)
        elif value is not None:
            candidates.append(str(value))
    combined = "\n".join(candidates).lower()
    return any(marker in combined for marker in SECRET_MARKERS)


def _diff_evidence_ok(
    *,
    diff_evidence: Mapping[str, Any],
    base_sha: str,
    head_sha: str,
) -> bool:
    if diff_evidence.get("source") != "machine_derived":
        return False
    if diff_evidence.get("red_dog_prose_source") is True:
        return False
    if diff_evidence.get("base_sha") != base_sha:
        return False
    if diff_evidence.get("head_sha") != head_sha:
        return False
    if not _is_digest(diff_evidence.get("diff_digest")):
        return False
    return bool(_changed_paths(diff_evidence))


def _test_evidence_ok(test_evidence: Mapping[str, Any], head_sha: str, request: Mapping[str, Any]) -> bool:
    if test_evidence.get("head_sha") != head_sha:
        return False
    if not _is_digest(test_evidence.get("test_evidence_digest")):
        return False
    checks = _list(test_evidence.get("required_checks"))
    for check in checks:
        if not isinstance(check, Mapping):
            return False
        if check.get("head_sha") != head_sha:
            return False
        if check.get("conclusion") not in ("success", "pass"):
            return False
    differential = _mapping(test_evidence.get("differential_evidence"))
    if not differential:
        return bool(checks)
    if differential.get("execution_authority_verified") is not True:
        return False
    expected_digest = _digest({"required_checks": checks, "differential_evidence": differential})
    verified, _, _ = verify_test_differential_evidence(differential, request=request)
    return verified and test_evidence.get("test_evidence_digest") == expected_digest

def _receipt_chain_ok(receipt_chain: Mapping[str, Any]) -> bool:
    if receipt_chain.get("accepted") is not True:
        return False
    terminal_hash = receipt_chain.get("terminal_receipt_hash") or receipt_chain.get(
        "signed_receipt_chain_terminal_hash"
    )
    return _is_digest(terminal_hash)


def _worktree_receipt_ok(worktree_receipt: Mapping[str, Any]) -> bool:
    if worktree_receipt.get("accepted") is False:
        return False
    if worktree_receipt.get("decision") in {"REJECT", "WORKTREE_CREATE_REJECT"}:
        return False
    return bool(_worktree_receipt_digest(worktree_receipt))


def _worktree_receipt_digest(worktree_receipt: Mapping[str, Any]) -> str:
    explicit = worktree_receipt.get("receipt_digest") or worktree_receipt.get(
        "worktree_write_receipt_digest"
    )
    if explicit:
        return str(explicit) if _is_digest(explicit) else ""
    return _digest(worktree_receipt) if worktree_receipt.get("receipt_id") else ""


def _holoindex_evidence_ok(holoindex_evidence: Mapping[str, Any]) -> bool:
    if holoindex_evidence.get("index_gap_detected") is True:
        return False
    if str(holoindex_evidence.get("retrieval_quality") or "").upper() == "INDEX_GAP":
        return False
    return _is_digest(holoindex_evidence.get("holoindex_freshness_receipt_digest"))


def _runtime_binding_pair(value: Mapping[str, Any]) -> tuple[str, str]:
    receipt_id = str(
        value.get("model_runtime_binding_receipt_id")
        or value.get("runtime_binding_receipt_id")
        or ""
    )
    digest = str(value.get("model_runtime_binding_digest") or "")
    return receipt_id, digest


def _runtime_binding_sources(req: Mapping[str, Any]) -> List[tuple[str, str]]:
    sources: List[tuple[str, str]] = []
    signed_authority = _mapping(req.get("signed_authority"))
    candidates = [
        req,
        signed_authority,
        _mapping(signed_authority.get("work_authority")),
        _mapping(signed_authority.get("authority")),
        _mapping(signed_authority.get("payload")),
        _mapping(req.get("artifact_generation_receipt")),
        _mapping(_mapping(req.get("artifact_generation_result")).get("receipt")),
        _mapping(req.get("bounded_worker_pilot_receipt")),
    ]
    for candidate in candidates:
        pair = _runtime_binding_pair(candidate)
        if pair[0] or pair[1]:
            sources.append(pair)
    return sources


def _runtime_binding_ok(req: Mapping[str, Any]) -> tuple[bool, Optional[str], str]:
    pairs = _runtime_binding_sources(req)
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


def _memex_binding_pair(value: Mapping[str, Any]) -> tuple[Any, Any]:
    return (
        value.get("memex_supply_receipt_id"),
        value.get("memex_supply_digest"),
    )


def _memex_binding_ok(req: Mapping[str, Any]) -> tuple[bool, Optional[str], str]:
    signed_authority = _mapping(req.get("signed_authority"))
    candidates = (
        req,
        signed_authority,
        _mapping(signed_authority.get("work_authority")),
        _mapping(signed_authority.get("authority")),
        _mapping(signed_authority.get("payload")),
        _mapping(req.get("artifact_generation_receipt")),
        _mapping(_mapping(req.get("artifact_generation_result")).get("receipt")),
        _mapping(req.get("bounded_worker_pilot_receipt")),
    )
    raw_pairs = tuple(
        pair
        for pair in (_memex_binding_pair(candidate) for candidate in candidates)
        if pair[0] not in (None, "") or pair[1] not in (None, "")
    )
    if not raw_pairs:
        return True, None, ""
    if any(
        not optional_authority_binding_values_valid(receipt_id, digest)
        for receipt_id, digest in raw_pairs
    ):
        return False, None, ""
    pairs = tuple(
        (str(receipt_id), str(digest))
        for receipt_id, digest in raw_pairs
    )
    first = pairs[0]
    if any(pair != first for pair in pairs[1:]):
        return False, first[0], first[1]
    return True, first[0], first[1]


def _all_paths_in_scope(paths: Sequence[str], req: Mapping[str, Any]) -> bool:
    allowed_patterns = [str(item) for item in _list(req.get("allowed_path_patterns"))]
    forbidden_patterns = [str(item) for item in _list(req.get("forbidden_path_patterns"))]
    expected_paths = {_normalize_path(path) for path in _list(req.get("expected_changed_paths"))}
    if expected_paths and set(paths) != expected_paths:
        return False
    for path in paths:
        if not _safe_repo_path(path):
            return False
        if forbidden_patterns and _matches_any(path, forbidden_patterns):
            return False
        if allowed_patterns and not _matches_any(path, allowed_patterns):
            return False
    return True


def verify_autonomous_slice_runtime(request: Mapping[str, Any], *, trusted_work_authority_digest: Any) -> AutonomousSliceVerifierResult:
    """Verify one autonomous coding-slice evidence packet.
    The verifier is intentionally independent from the authoring worker. It
    checks evidence shape, exact-head binding, scope, tests, signatures, receipt
    chain, HoloIndex freshness, and non-self verification. It never executes the
    work or publishes the result.
    """
    req = _mapping(request)
    diff_evidence = _mapping(req.get("diff_evidence"))
    test_evidence = _mapping(req.get("test_evidence"))
    signed_authority = _mapping(req.get("signed_authority"))
    receipt_chain = _mapping(req.get("signed_receipt_chain"))
    worktree_receipt = _mapping(req.get("worktree_receipt"))
    pilot_receipt = _mapping(req.get("bounded_worker_pilot_receipt"))
    holoindex_evidence = _mapping(req.get("holoindex_evidence"))
    runtime_binding_ok, runtime_binding_id, runtime_binding_digest = _runtime_binding_ok(req)
    memex_binding_ok, memex_supply_id, memex_supply_digest = _memex_binding_ok(req)
    work_order_id = str(req.get("work_order_id") or "")
    slice_name = str(req.get("slice_name") or "")
    worker_id = str(req.get("worker_id") or "")
    verifier_id = str(req.get("verifier_id") or "")
    base_sha = str(req.get("base_sha") or "")
    head_sha = str(req.get("head_sha") or "")
    assurance_reservation_id = str(
        req.get("assurance_reservation_id") or ""
    )
    assurance_reservation_digest = str(
        req.get("assurance_reservation_digest") or ""
    )
    verifier_task_id = str(req.get("verifier_task_id") or "")
    reasons: List[str] = []
    if not all([work_order_id, slice_name, worker_id, verifier_id]):
        reasons.append(FAIL_REQUIRED_FIELD)
    if worker_id and verifier_id and worker_id == verifier_id:
        reasons.append(FAIL_SELF_VERIFICATION)
    if (
        not assurance_reservation_id.startswith("assurance-reservation-")
        or not _is_digest(assurance_reservation_digest)
        or not verifier_task_id.startswith("reddog-worker-dispatch-")
    ):
        reasons.append(FAIL_ASSURANCE_RESERVATION)
    if not _is_head_sha(base_sha) or not _is_head_sha(head_sha) or base_sha == head_sha:
        reasons.append(FAIL_HEAD_SHA)
    if not _diff_evidence_ok(
        diff_evidence=diff_evidence,
        base_sha=base_sha,
        head_sha=head_sha,
    ):
        reasons.append(FAIL_DIFF_EVIDENCE)
    changed_paths = _changed_paths(diff_evidence)
    if changed_paths and not _all_paths_in_scope(changed_paths, req):
        reasons.append(FAIL_SCOPE_VIOLATION)
    protected_paths = [path for path in changed_paths if _protected_path(path)]
    protected_digest = req.get("protected_surface_authorization_digest")
    consensus_digest = req.get("consensus_receipt_digest")
    if protected_paths and not (_is_digest(protected_digest) and _is_digest(consensus_digest)):
        reasons.append(FAIL_PROTECTED_SURFACE)
    if _diff_contains_secret(diff_evidence):
        reasons.append(FAIL_SECRET_IN_DIFF)
    if not _test_evidence_ok(test_evidence, head_sha, req):
        reasons.append(FAIL_TEST_EVIDENCE)
    if not signed_authority_envelope_digest_matches(signed_authority, trusted_work_authority_digest):
        reasons.append(FAIL_SIGNED_AUTHORITY)
    if not _receipt_chain_ok(receipt_chain):
        reasons.append(FAIL_RECEIPT_CHAIN)
    if not _worktree_receipt_ok(worktree_receipt):
        reasons.append(FAIL_WORKTREE_RECEIPT)
    if pilot_receipt and pilot_receipt.get("accepted") is not True:
        reasons.append(FAIL_WORKTREE_RECEIPT)
    if not _holoindex_evidence_ok(holoindex_evidence):
        reasons.append(FAIL_HOLOINDEX_EVIDENCE)
    if not runtime_binding_ok:
        reasons.append(FAIL_MODEL_RUNTIME_BINDING)
    if not memex_binding_ok:
        reasons.append(FAIL_MEMEX_SUPPLY_BINDING)
    if req.get("pattern_memory_write_performed") is True:
        reasons.append(FAIL_PATTERN_MEMORY_WRITE)
    if req.get("draft_pr_published") is True or req.get("merge_performed") is True:
        reasons.append(FAIL_PR_OR_MERGE_ALREADY_PERFORMED)
    deduped = _dedupe(reasons)
    accepted = not deduped
    receipt_chain_hash = (
        receipt_chain.get("terminal_receipt_hash")
        or receipt_chain.get("signed_receipt_chain_terminal_hash")
        or ""
    )
    worktree_digest = _worktree_receipt_digest(worktree_receipt)
    signed_digest = signed_authority.get("signature_gate_digest") or signed_authority.get(
        "signed_work_authority_digest"
    )
    receipt_seed = {
        "work_order_id": work_order_id,
        "slice_name": slice_name,
        "verifier_id": verifier_id,
        "worker_id": worker_id,
        "assurance_reservation_id": assurance_reservation_id,
        "assurance_reservation_digest": assurance_reservation_digest,
        "verifier_task_id": verifier_task_id,
        "base_sha": base_sha,
        "head_sha": head_sha,
        "changed_paths": sorted(changed_paths),
        "diff_digest": str(diff_evidence.get("diff_digest") or ""),
        "test_evidence_digest": str(test_evidence.get("test_evidence_digest") or ""),
        "signed_authority_digest": str(signed_digest or ""),
        "receipt_chain_terminal_hash": str(receipt_chain_hash or ""),
        "worktree_receipt_digest": str(worktree_digest or ""),
        "holoindex_freshness_receipt_digest": str(
            holoindex_evidence.get("holoindex_freshness_receipt_digest") or ""
        ),
        "model_runtime_binding_receipt_id": runtime_binding_id or "",
        "model_runtime_binding_digest": runtime_binding_digest,
        "memex_supply_receipt_id": memex_supply_id or "",
        "memex_supply_digest": memex_supply_digest,
        "rejection_reasons": deduped,
    }
    receipt = AutonomousSliceVerifierReceipt(
        receipt_id="wre_slice_verify_" + _digest(receipt_seed).removeprefix("sha256:")[:16],
        work_order_id=work_order_id,
        slice_name=slice_name,
        verifier_id=verifier_id,
        worker_id=worker_id,
        assurance_reservation_id=assurance_reservation_id,
        assurance_reservation_digest=assurance_reservation_digest,
        verifier_task_id=verifier_task_id,
        base_sha=base_sha,
        head_sha=head_sha,
        changed_paths=sorted(changed_paths),
        diff_digest=str(diff_evidence.get("diff_digest") or ""),
        test_evidence_digest=str(test_evidence.get("test_evidence_digest") or ""),
        signed_authority_digest=str(signed_digest or ""),
        receipt_chain_terminal_hash=str(receipt_chain_hash or ""),
        worktree_receipt_digest=str(worktree_digest or ""),
        holoindex_freshness_receipt_digest=str(
            holoindex_evidence.get("holoindex_freshness_receipt_digest") or ""
        ),
        model_runtime_binding_receipt_id=runtime_binding_id,
        model_runtime_binding_digest=runtime_binding_digest,
        memex_supply_receipt_id=memex_supply_id,
        memex_supply_digest=memex_supply_digest,
        rejection_reasons=deduped,
        accepted=accepted,
    )
    return AutonomousSliceVerifierResult(
        decision=(
            AUTONOMOUS_SLICE_VERIFIER_ACCEPT
            if accepted
            else AUTONOMOUS_SLICE_VERIFIER_REJECT
        ),
        accepted=accepted,
        receipt=receipt,
        rejection_reasons=deduped,
    )


__all__ = [
    "AUTONOMOUS_SLICE_VERIFIER_ACCEPT",
    "AUTONOMOUS_SLICE_VERIFIER_REJECT",
    "AutonomousSliceVerifierReceipt",
    "AutonomousSliceVerifierResult",
    "FAIL_ASSURANCE_RESERVATION",
    "FAIL_DIFF_EVIDENCE",
    "FAIL_HEAD_SHA",
    "FAIL_HOLOINDEX_EVIDENCE",
    "FAIL_MEMEX_SUPPLY_BINDING",
    "FAIL_MODEL_RUNTIME_BINDING",
    "FAIL_PATTERN_MEMORY_WRITE",
    "FAIL_PR_OR_MERGE_ALREADY_PERFORMED",
    "FAIL_PROTECTED_SURFACE",
    "FAIL_RECEIPT_CHAIN",
    "FAIL_REQUIRED_FIELD",
    "FAIL_SCOPE_VIOLATION",
    "FAIL_SECRET_IN_DIFF",
    "FAIL_SELF_VERIFICATION",
    "FAIL_SIGNED_AUTHORITY",
    "FAIL_TEST_EVIDENCE",
    "FAIL_WORKTREE_RECEIPT",
    "verify_autonomous_slice_runtime",
]
