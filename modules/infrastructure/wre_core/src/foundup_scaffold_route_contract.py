# -*- coding: utf-8 -*-
"""Immutable create_foundup routing and scaffold-plan validation contract."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional


CREATE_ACTION = "create_foundup"
CREATE_MODE = "new_scaffold"
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_FOUNDUP_ID_RE = re.compile(r"^[a-z][a-z0-9_]{2,49}$")


class CanonicalizationError(ValueError):
    """Raised when evidence cannot cross the canonical JSON boundary."""


def canonical_json(value: Any) -> str:
    """Serialize JSON-compatible evidence deterministically and fail closed."""
    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as exc:
        raise CanonicalizationError("value is not canonical JSON") from exc


def canonical_json_copy(value: Any) -> Any:
    """Return a detached canonical-JSON copy with no nested aliases."""
    return json.loads(canonical_json(value))


def digest_scaffold_contract(contract: Mapping[str, Any]) -> str:
    """Return the planner-compatible canonical scaffold-contract digest."""
    raw = json.dumps(
        contract,
        ensure_ascii=True,
        sort_keys=True,
        default=str,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class CreateScaffoldRequest:
    """Frozen request snapshot shared identically by router and planner."""

    job_id: str
    tenant_id: str
    foundup_id: str
    creation_mode: str
    genesis_envelope_digest: str
    scaffold_contract_digest: str
    genesis_envelope_json: str
    request_digest: str

    @property
    def genesis_envelope(self) -> Dict[str, Any]:
        """Return a new detached genesis-envelope mapping."""
        value = json.loads(self.genesis_envelope_json)
        if not isinstance(value, dict):
            raise CanonicalizationError("genesis envelope snapshot is not a mapping")
        return value

    def to_dict(self) -> Dict[str, Any]:
        """Return a detached JSON-safe request receipt."""
        return {
            "job_id": self.job_id,
            "tenant_id": self.tenant_id,
            "foundup_id": self.foundup_id,
            "requested_action": CREATE_ACTION,
            "creation_mode": self.creation_mode,
            "genesis_envelope_digest": self.genesis_envelope_digest,
            "scaffold_contract_digest": self.scaffold_contract_digest,
            "genesis_envelope": self.genesis_envelope,
            "request_digest": self.request_digest,
        }


@dataclass(frozen=True)
class CreateScaffoldRequestDecision:
    """Fail-closed result from freezing an untrusted mutable job."""

    request: Optional[CreateScaffoldRequest]
    error_human: Optional[str]

    @property
    def ok(self) -> bool:
        return self.request is not None and self.error_human is None


def _reject(reason: str) -> CreateScaffoldRequestDecision:
    return CreateScaffoldRequestDecision(request=None, error_human=reason)


def _is_safe_identifier(value: Any) -> bool:
    """Reject path traversal and control characters without narrowing tenant syntax."""
    return (
        isinstance(value, str)
        and bool(value.strip())
        and value == value.strip()
        and ".." not in value
        and "/" not in value
        and "\\" not in value
        and all(ord(character) >= 32 and ord(character) != 127 for character in value)
    )


def freeze_create_scaffold_request(
    job: Any,
    policy_summary: Mapping[str, bool],
) -> CreateScaffoldRequestDecision:
    """Read a mutable job once and freeze its canonical create request."""
    try:
        if policy_summary.get("dry_run_mode") is not True:
            return _reject("create_foundup requires explicit dry_run_mode=True")

        job_id = getattr(job, "job_id", None)
        tenant_id = getattr(job, "tenant_id", None)
        foundup_id = getattr(job, "foundup_id", None)
        creation_mode = getattr(job, "creation_mode", None)
        genesis_digest = getattr(job, "genesis_envelope_digest", None)
        scaffold_digest = getattr(job, "scaffold_contract_digest", None)
        payload = getattr(job, "payload", None)

        if not _is_safe_identifier(job_id):
            return _reject("create_foundup requires safe job_id")
        if not _is_safe_identifier(tenant_id):
            return _reject("create_foundup requires safe tenant_id")
        if (
            not isinstance(foundup_id, str)
            or _FOUNDUP_ID_RE.fullmatch(foundup_id) is None
        ):
            return _reject("create_foundup requires canonical foundup_id")
        if creation_mode != CREATE_MODE:
            return _reject("create_foundup requires creation_mode='new_scaffold'")
        if (
            not isinstance(genesis_digest, str)
            or _SHA256_RE.fullmatch(genesis_digest) is None
        ):
            return _reject(
                "create_foundup requires canonical genesis_envelope_digest"
            )
        if (
            not isinstance(scaffold_digest, str)
            or _SHA256_RE.fullmatch(scaffold_digest) is None
        ):
            return _reject(
                "create_foundup requires canonical scaffold_contract_digest"
            )
        if not isinstance(payload, dict):
            return _reject("create_foundup requires a payload mapping")
        genesis_envelope = payload.get("genesis_envelope")
        if not isinstance(genesis_envelope, dict):
            return _reject("create_foundup requires payload.genesis_envelope")
        if genesis_envelope.get("foundup_id") != foundup_id:
            return _reject(
                "create_foundup foundup_id must match genesis envelope"
            )

        genesis_json = canonical_json(genesis_envelope)
        request_body = {
            "job_id": job_id,
            "tenant_id": tenant_id,
            "foundup_id": foundup_id,
            "requested_action": CREATE_ACTION,
            "creation_mode": creation_mode,
            "genesis_envelope_digest": genesis_digest,
            "scaffold_contract_digest": scaffold_digest,
            "genesis_envelope": json.loads(genesis_json),
        }
        request_digest = "sha256:" + hashlib.sha256(
            canonical_json(request_body).encode("utf-8")
        ).hexdigest()
        return CreateScaffoldRequestDecision(
            request=CreateScaffoldRequest(
                job_id=job_id,
                tenant_id=tenant_id,
                foundup_id=foundup_id,
                creation_mode=creation_mode,
                genesis_envelope_digest=genesis_digest,
                scaffold_contract_digest=scaffold_digest,
                genesis_envelope_json=genesis_json,
                request_digest=request_digest,
            ),
            error_human=None,
        )
    except (AttributeError, CanonicalizationError, TypeError, ValueError):
        return _reject("create_foundup request could not be canonicalized")


@dataclass(frozen=True)
class ScaffoldPlanValidation:
    """Detached scaffold plan or a stable fail-closed reason."""

    plan: Optional[Dict[str, Any]]
    reason_code: str

    @property
    def ok(self) -> bool:
        return self.plan is not None and self.reason_code == "OK_SCAFFOLD_PLAN"


def validate_scaffold_plan(
    plan: Any,
    request: CreateScaffoldRequest,
) -> ScaffoldPlanValidation:
    """Validate returned planner identity, lineage, and no-effect evidence."""
    try:
        detached = canonical_json_copy(plan)
    except CanonicalizationError:
        return ScaffoldPlanValidation(None, "FAIL_SCAFFOLD_PLAN_NOT_CANONICAL")
    if not isinstance(detached, dict):
        return ScaffoldPlanValidation(None, "FAIL_SCAFFOLD_PLAN_INVALID")
    if (
        detached.get("action") != CREATE_ACTION
        or detached.get("ok") is not True
        or detached.get("dry_run") is not True
        or detached.get("files_written") != []
        or detached.get("fam_called") is not False
        or detached.get("hermes_called") is not False
        or detached.get("registry_mutated") is not False
        or detached.get("worktree_created") is not False
    ):
        return ScaffoldPlanValidation(None, "FAIL_SCAFFOLD_PLAN_BOUNDARY")

    contract = detached.get("scaffold_contract")
    if not isinstance(contract, dict):
        return ScaffoldPlanValidation(None, "FAIL_MISSING_SCAFFOLD_CONTRACT")
    if contract.get("foundup_id") != request.foundup_id:
        return ScaffoldPlanValidation(None, "FAIL_SCAFFOLD_FOUNDUP_MISMATCH")
    if (
        contract.get("genesis_envelope_digest")
        != request.genesis_envelope_digest
    ):
        return ScaffoldPlanValidation(None, "FAIL_GENESIS_LINEAGE_MISMATCH")
    if digest_scaffold_contract(contract) != request.scaffold_contract_digest:
        return ScaffoldPlanValidation(None, "FAIL_SCAFFOLD_LINEAGE_MISMATCH")
    return ScaffoldPlanValidation(detached, "OK_SCAFFOLD_PLAN")
