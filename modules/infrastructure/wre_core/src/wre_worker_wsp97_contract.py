"""Pure-evaluation WSP_00 0.2A and WSP_97 worker contract helpers for WRE.

Provides fail-closed worker identity/role/origin envelope validation,
canonical WSP_97 prompt contract construction, and repository-bound receipt
validation delegating to ``tools.wsp97_execution_validator`` (no shell/Git/IO).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

from tools.wsp97_execution_validator import (
    DEFAULT_CONTRACT_PATH,
    RECEIPT_SCHEMA_VERSION,
    WSP97ValidationResult,
    load_contract,
    validate_execution_receipt,
)
from tools.wsp97_repository_evidence import WSP_ID_PATTERN

ALLOWED_WORKER_SELF = "0102"
ALLOWED_WORKER_ROLES = frozenset({"architect", "worker", "verifier", "coordinator", "validator"})
ALLOWED_ORIGINS = frozenset({"external_principal", "internal_handoff", "autonomous_trigger"})

WSP00_ENVELOPE_VALID = "WSP00_ENVELOPE_VALID"
FAIL_ENVELOPE_TYPE = "FAIL_ENVELOPE_TYPE"
FAIL_SELF_IS_012 = "FAIL_SELF_IS_012"
FAIL_INVALID_SELF = "FAIL_INVALID_SELF"
FAIL_INVALID_ROLE = "FAIL_INVALID_ROLE"
FAIL_ROLE_ESCALATION = "FAIL_ROLE_ESCALATION"
FAIL_IMPLICIT_ROLE_ESCALATION = "FAIL_IMPLICIT_ROLE_ESCALATION"
FAIL_INVALID_ORIGIN = "FAIL_INVALID_ORIGIN"
FAIL_MISSING_PRINCIPAL_REF = "FAIL_MISSING_PRINCIPAL_REF"
FAIL_SELF_VERIFICATION_PROHIBITED = "FAIL_SELF_VERIFICATION_PROHIBITED"

WSP97_RECEIPT_VALID = "WSP97_RECEIPT_VALID"
FAIL_RECEIPT_INVALID_TYPE = "FAIL_RECEIPT_INVALID_TYPE"
FAIL_REPO_ROOT_REQUIRED = "FAIL_REPO_ROOT_REQUIRED"
FAIL_RECEIPT_VALIDATION_ERROR = "FAIL_RECEIPT_VALIDATION_ERROR"
FAIL_RECEIPT_NON_COMPLIANT = "FAIL_RECEIPT_NON_COMPLIANT"


@dataclass(frozen=True)
class WorkerWSP00EnvelopeResult:
    """Fail-closed WSP_00 Section 0.2A envelope evaluation result."""
    ok: bool
    code: str
    reason: str
    locked_self: str
    locked_role: str
    origin: str
    principal_ref: str
    worker_id: str
    verifier_id: str
    no_repo_mutation_performed: bool = True
    no_authority_granted: bool = True
    self_issued_receipt_not_independent_verification: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class WorkerWSP97PromptContract:
    """Canonical WSP_97 CoT/CoR prompt contract for a bounded worker role."""
    schema_version: str
    role: str
    system_prompt: str
    cot_gate: str
    cor_gate: str
    required_actions: tuple[str, ...]
    mantra_stages: tuple[str, ...]
    receipt_schema_version: str
    no_repo_mutation_performed: bool = True
    no_authority_granted: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class WorkerWSP97ReceiptResult:
    """Fail-closed wrapper over repository-bound WSP_97 receipt validation."""
    ok: bool
    code: str
    reason: str
    is_compliant: bool
    structurally_complete: bool
    validation_mode: str
    execution_id: str
    validated_base_commit: str
    repository_head_commit: str
    violations: tuple[str, ...]
    worker_id: str
    verifier_id: str
    no_repo_mutation_performed: bool = True
    no_authority_granted: bool = True
    self_issued_receipt_not_independent_verification: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _env_fail(code: str, reason: str, **kw: str) -> WorkerWSP00EnvelopeResult:
    return WorkerWSP00EnvelopeResult(
        ok=False, code=code, reason=reason,
        locked_self=kw.get("locked_self", ""), locked_role=kw.get("locked_role", ""),
        origin=kw.get("origin", ""), principal_ref=kw.get("principal_ref", ""),
        worker_id=kw.get("worker_id", ""), verifier_id=kw.get("verifier_id", ""),
    )


def _validate_verifier_pair(raw_worker: Any, raw_verifier: Any, *, require_separation: bool) -> tuple[bool, str, str]:
    if (raw_worker is not None and not isinstance(raw_worker, str)) or (raw_verifier is not None and not isinstance(raw_verifier, str)):
        return False, "", ""
    w_id = raw_worker.strip() if isinstance(raw_worker, str) else ""
    v_id = raw_verifier.strip() if isinstance(raw_verifier, str) else ""
    if (w_id and v_id and w_id == v_id) or (require_separation and (not w_id or not v_id)):
        return False, w_id, v_id
    return True, w_id, v_id


def validate_worker_wsp00_envelope(
    envelope: Mapping[str, Any],
    *,
    expected_role: str | None = None,
    require_verifier_separation: bool = False,
) -> WorkerWSP00EnvelopeResult:
    """Validate WSP_00 Section 0.2A self/role/origin/verifier lock fail-closed."""
    if not isinstance(envelope, Mapping):
        return _env_fail(FAIL_ENVELOPE_TYPE, "envelope must be a mapping")
    self_val = envelope.get("self").strip() if isinstance(envelope.get("self"), str) else ""
    if self_val == "012":
        return _env_fail(FAIL_SELF_IS_012, "machine self must be 0102, never 012")
    if self_val != ALLOWED_WORKER_SELF:
        return _env_fail(FAIL_INVALID_SELF, "machine self must be 0102")

    role_val = envelope.get("role").strip() if isinstance(envelope.get("role"), str) else ""
    if role_val not in ALLOWED_WORKER_ROLES:
        return _env_fail(FAIL_INVALID_ROLE, "role is missing or unsupported", locked_self=self_val)
    if expected_role is not None and (not isinstance(expected_role, str) or role_val != expected_role.strip()):
        return _env_fail(FAIL_ROLE_ESCALATION, "role does not match expected_role", locked_self=self_val, locked_role=role_val)
    for key in ("claimed_role", "requested_role"):
        claimed = envelope.get(key)
        if key in envelope and claimed is not None and (not isinstance(claimed, str) or claimed.strip() != role_val):
            return _env_fail(FAIL_IMPLICIT_ROLE_ESCALATION, f"{key} must not differ from role", locked_self=self_val, locked_role=role_val)

    origin_val = envelope.get("origin").strip() if isinstance(envelope.get("origin"), str) else ""
    if origin_val not in ALLOWED_ORIGINS:
        return _env_fail(FAIL_INVALID_ORIGIN, "origin is missing or unsupported", locked_self=self_val, locked_role=role_val)
    principal_val = envelope.get("principal_ref").strip() if isinstance(envelope.get("principal_ref"), str) else ""
    if not principal_val:
        return _env_fail(FAIL_MISSING_PRINCIPAL_REF, "principal_ref must be a non-empty string", locked_self=self_val, locked_role=role_val, origin=origin_val)

    pair_ok, w_id, v_id = _validate_verifier_pair(envelope.get("worker_id"), envelope.get("verifier_id"), require_separation=require_verifier_separation)
    if not pair_ok:
        return _env_fail(FAIL_SELF_VERIFICATION_PROHIBITED, "worker_id and verifier_id must be distinct non-empty identities", locked_self=self_val, locked_role=role_val, origin=origin_val, principal_ref=principal_val, worker_id=w_id, verifier_id=v_id)
    return WorkerWSP00EnvelopeResult(
        ok=True, code=WSP00_ENVELOPE_VALID, reason="WSP_00 0.2A envelope valid",
        locked_self=self_val, locked_role=role_val, origin=origin_val,
        principal_ref=principal_val, worker_id=w_id, verifier_id=v_id,
    )


def build_worker_wsp97_prompt_contract(
    *, role: str = "worker", agent_profile: str = "0102", contract_path: Path | str | None = None,
) -> WorkerWSP97PromptContract:
    """Build a canonical WSP_97 CoT/CoR prompt contract from the protocol JSON."""
    if not isinstance(role, str) or role.strip() not in ALLOWED_WORKER_ROLES:
        raise ValueError(f"unsupported worker role: {role!r}")
    locked_role = role.strip()
    contract = load_contract(contract_path)
    profiles = contract.get("agent_profiles")
    if not isinstance(profiles, Mapping) or agent_profile not in profiles:
        raise ValueError(f"unsupported agent_profile: {agent_profile!r}")
    profile, wsp97 = profiles[agent_profile], contract["wsp_97"]
    receipt_version = str(wsp97["validator"]["receipt_schema_version"])
    actions = tuple(item.strip().lower().replace(" ", "_") for item in wsp97["operator_actions"])
    stages = tuple(item.strip().lower().replace(" ", "_") for item in wsp97["mantra_stages"])
    cot_gate = "CoT: retrieve before stating (HoloIndex -> Research)"
    cor_gate = "CoR: dialectic sweep before committing (Hard Think -> Dialectic Sweep -> First Principles)"
    system_prompt = (
        f"{profile.get('system_prompt_reference', '').strip()} "
        f"WSP_00 0.2A Lock: self={ALLOWED_WORKER_SELF}, role={locked_role}. "
        f"Invariant: architect intent != worker truth. "
        f"Mantra emphasis: {profile.get('mantra_emphasis', '').strip()}. "
        f"{cot_gate}; {cor_gate}. Receipt schema: {receipt_version}."
    ).strip()
    return WorkerWSP97PromptContract(
        schema_version=str(wsp97.get("version", "")), role=locked_role,
        system_prompt=system_prompt, cot_gate=cot_gate, cor_gate=cor_gate,
        required_actions=actions, mantra_stages=stages, receipt_schema_version=receipt_version,
    )


def _receipt_fail(code: str, reason: str, *, execution_id: str = "", violations: tuple[str, ...] = (), worker_id: str = "", verifier_id: str = "") -> WorkerWSP97ReceiptResult:
    return WorkerWSP97ReceiptResult(
        ok=False, code=code, reason=reason, is_compliant=False,
        structurally_complete=False, validation_mode="error", execution_id=execution_id,
        validated_base_commit="", repository_head_commit="",
        violations=violations or (reason,), worker_id=worker_id, verifier_id=verifier_id,
    )


def validate_worker_wsp97_receipt(
    receipt: Mapping[str, Any], *, repo_root: Path | str | None = None,
    expected_base: str | None = None, worker_id: str = "", verifier_id: str = "",
    contract_path: Path | str | None = None,
) -> WorkerWSP97ReceiptResult:
    """Validate a worker execution receipt via tools.wsp97_execution_validator."""
    if not isinstance(worker_id, str) or not isinstance(verifier_id, str):
        return _receipt_fail(FAIL_SELF_VERIFICATION_PROHIBITED, "worker_id and verifier_id must be strings")
    w_id, v_id = worker_id.strip(), verifier_id.strip()
    if w_id and v_id and w_id == v_id:
        return _receipt_fail(FAIL_SELF_VERIFICATION_PROHIBITED, "self-verification is prohibited", worker_id=w_id, verifier_id=v_id)
    if not isinstance(receipt, Mapping):
        return _receipt_fail(FAIL_RECEIPT_INVALID_TYPE, "receipt must be a mapping", worker_id=w_id, verifier_id=v_id)
    exec_id = receipt.get("execution_id").strip() if isinstance(receipt.get("execution_id"), str) else ""
    if repo_root is None or (isinstance(repo_root, str) and not repo_root.strip()):
        return _receipt_fail(FAIL_REPO_ROOT_REQUIRED, "repo_root is required for receipt v1.1 validation", execution_id=exec_id, worker_id=w_id, verifier_id=v_id)
    try:
        contract = load_contract(contract_path)
        result: WSP97ValidationResult = validate_execution_receipt(receipt, contract, repo_root=repo_root, expected_base=expected_base)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        return _receipt_fail(FAIL_RECEIPT_VALIDATION_ERROR, str(exc), execution_id=exec_id, worker_id=w_id, verifier_id=v_id)
    code = WSP97_RECEIPT_VALID if result.is_compliant else FAIL_RECEIPT_NON_COMPLIANT
    reason = "WSP_97 receipt compliant" if result.is_compliant else "; ".join(result.violations)
    return WorkerWSP97ReceiptResult(
        ok=result.is_compliant, code=code, reason=reason, is_compliant=result.is_compliant,
        structurally_complete=result.structurally_complete, validation_mode=result.validation_mode,
        execution_id=result.execution_id, validated_base_commit=result.validated_base_commit,
        repository_head_commit=result.repository_head_commit, violations=result.violations,
        worker_id=w_id, verifier_id=v_id,
    )
