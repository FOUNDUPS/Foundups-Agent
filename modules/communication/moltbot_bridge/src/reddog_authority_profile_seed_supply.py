"""Authority-profile seed supplier for resident RedDog FIX promotion.

Slice: REDDOG_AUTHORITY_PROFILE_SEED_SUPPLY_PHASE1

This module materializes the authority seed consumed by
``reddog_authority_profile_source_artifact_supply`` from already-supplied
runtime receipts. It removes the last hand-placed seed file from the resident
FIX-promotion path while preserving the existing authority-profile source
validator as the enforcement point.

It does not sign, verify signatures, mutate signer state, mutate work state,
spawn workers, create worktrees, execute shell commands, enqueue OpenClaw,
dispatch Hermes, create PRs, settle rewards, write PatternMemory, or re-index
HoloIndex.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    HIGH_AUTHORITY_OPERATIONS,
    PrincipalAuthorityRecord,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    PermissionSnapshot,
)
from modules.communication.moltbot_bridge.src.reddog_wre_execution_valve import (
    VALVE_OPEN_WORKTREE_CREATE,
)
from modules.communication.moltbot_bridge.src.reddog_wsp15_allocation_receipt import (
    canonical_reddog_wsp15_allocation_digest,
    validate_reddog_wsp15_allocation_receipt,
)


AUTHORITY_PROFILE_SEED_SUPPLY_ACCEPT = "AUTHORITY_PROFILE_SEED_SUPPLY_ACCEPT"
AUTHORITY_PROFILE_SEED_SUPPLY_REJECT = "AUTHORITY_PROFILE_SEED_SUPPLY_REJECT"
AUTHORITY_PROFILE_SEED_SCHEMA_VERSION = "reddog_authority_profile_seed.v1"

_FOUNDUP_PATH_PREFIX = "modules/foundups/"
_DEFAULT_REQUIRED_TESTS = ("pytest modules/foundups/tests",)
_DEFAULT_REQUIRED_POLICY_GATES = (
    "signed_work_order_authority",
    "execution_valve",
    "independent_worker_output_verifier",
)


class AuthorityProfileSeedSupplyReason:
    DETERMINATION_INVALID = "architect_determination_invalid"
    DETERMINATION_NOT_FIX = "architect_determination_not_fix"
    QUEUE_CANDIDATE_INVALID = "queue_candidate_invalid"
    WSP15_ALLOCATION_INVALID = "wsp15_allocation_invalid"
    WSP15_ALLOCATION_MISMATCH = "wsp15_allocation_mismatch"
    MODEL_SELECTION_INVALID = "model_selection_invalid"
    MEMEX_SUPPLY_INVALID = "memex_supply_invalid"
    PRINCIPAL_INVALID = "principal_authority_record_invalid"
    PERMISSION_SNAPSHOT_INVALID = "permission_snapshot_invalid"
    MISSING_REDDOG_ID = "missing_reddog_id"
    MISSING_REDDOG_PUBLIC_KEY = "missing_reddog_public_key"
    PRINCIPAL_REDDOG_KEY_REUSE = "principal_reddog_key_reuse"
    FOUNDUP_SCOPE_INVALID = "foundup_scope_invalid"
    REPO_SCOPE_INVALID = "repo_scope_invalid"
    PATH_SCOPE_INVALID = "authority_seed_path_scope_invalid"
    HIGH_AUTHORITY_COSIGN_MISSING = "authority_seed_high_authority_cosign_missing"
    HOLOINDEX_EVIDENCE_INVALID = "authority_seed_holoindex_evidence_invalid"
    TIME_BOUNDS_INVALID = "authority_seed_time_bounds_invalid"
    NON_ASCII_INPUT = "authority_seed_non_ascii_input"
    OUTPUT_PATH_INVALID = "authority_seed_output_path_invalid"
    OUTPUT_WRITE_FAILED = "authority_seed_output_write_failed"


@dataclass(frozen=True)
class AuthorityProfileSeedSupplyResult:
    accepted: bool
    status: str
    seed_supply_receipt_id: str | None
    output_path: str | None
    principal_id: str | None
    reddog_id: str | None
    foundup_id: str | None
    requested_operation: str | None
    rejection_reasons: tuple[str, ...]
    no_signing_performed: bool = True
    no_signature_verification_performed: bool = True
    no_signer_state_mutation_performed: bool = True
    no_worker_spawn_performed: bool = True
    no_worktree_created: bool = True
    no_shell_command_executed: bool = True
    no_openclaw_enqueue_performed: bool = True
    no_hermes_dispatch_performed: bool = True
    no_work_state_mutation_performed: bool = True
    no_repo_mutation_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_pattern_memory_write_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_reddog_authority_profile_seed_supply(
    *,
    repo_root: Path | str,
    architect_determination: Mapping[str, Any] | None,
    model_selection_receipt: Mapping[str, Any] | None,
    memex_supply_receipt: Mapping[str, Any] | None,
    principal_authority_record: Mapping[str, Any] | PrincipalAuthorityRecord | None,
    permission_snapshot: Mapping[str, Any] | PermissionSnapshot | None,
    output_path: Path | str | None,
    reddog_id: str,
    reddog_public_key: str,
    now_epoch: int,
    foundup_id: str | None = None,
    requested_operation: str = "feature_slice",
    allowed_paths: Sequence[str] = (),
    denied_paths: Sequence[str] = (),
    valve_state_required: str = VALVE_OPEN_WORKTREE_CREATE,
    key_epoch: str = "epoch-1",
    required_tests: Sequence[str] = (),
    required_policy_gates: Sequence[str] = (),
    consensus_receipt_digest: str | None = None,
    sovereign_authorization_digest: str | None = None,
    identity_ttl_seconds: int = 3600,
    work_authority_ttl_seconds: int = 900,
) -> AuthorityProfileSeedSupplyResult:
    """Materialize one authority-profile seed from resident runtime receipts."""

    root = Path(repo_root).resolve()
    determination = _mapping(architect_determination)
    model_selection = _mapping(model_selection_receipt)
    memex_supply = _mapping(memex_supply_receipt)
    principal = _principal(principal_authority_record)
    snapshot = _snapshot(permission_snapshot)
    output, output_reasons = _runtime_output_path(output_path, root)

    reasons: list[str] = []
    reasons.extend(output_reasons)
    reasons.extend(_determination_reasons(determination))
    allocation = _allocation(determination)
    if allocation:
        allocation_validation = validate_reddog_wsp15_allocation_receipt(allocation)
        if not allocation_validation.accepted:
            reasons.extend(
                f"{AuthorityProfileSeedSupplyReason.WSP15_ALLOCATION_INVALID}:{reason}"
                for reason in allocation_validation.rejection_reasons
            )
        elif _allocation_mismatches_determination(determination, allocation):
            reasons.append(AuthorityProfileSeedSupplyReason.WSP15_ALLOCATION_MISMATCH)
    else:
        reasons.append(AuthorityProfileSeedSupplyReason.WSP15_ALLOCATION_INVALID)
    reasons.extend(_model_selection_reasons(model_selection))
    reasons.extend(_memex_supply_reasons(memex_supply, determination))
    if principal is None:
        reasons.append(AuthorityProfileSeedSupplyReason.PRINCIPAL_INVALID)
    if snapshot is None:
        reasons.append(AuthorityProfileSeedSupplyReason.PERMISSION_SNAPSHOT_INVALID)

    rid = str(reddog_id or "").strip()
    rkey = str(reddog_public_key or "").strip()
    if not rid:
        reasons.append(AuthorityProfileSeedSupplyReason.MISSING_REDDOG_ID)
    if not rkey:
        reasons.append(AuthorityProfileSeedSupplyReason.MISSING_REDDOG_PUBLIC_KEY)
    if principal is not None and rkey and rkey == principal.principal_public_key:
        reasons.append(AuthorityProfileSeedSupplyReason.PRINCIPAL_REDDOG_KEY_REUSE)

    fid = _selected_foundup_id(foundup_id, principal)
    if not fid:
        reasons.append(AuthorityProfileSeedSupplyReason.FOUNDUP_SCOPE_INVALID)
    repo_full_name = _selected_repo_full_name(snapshot, principal)
    if not repo_full_name:
        reasons.append(AuthorityProfileSeedSupplyReason.REPO_SCOPE_INVALID)
    if snapshot is not None and repo_full_name and not snapshot.grants(str(requested_operation or ""), repo_full_name):
        reasons.append(AuthorityProfileSeedSupplyReason.PERMISSION_SNAPSHOT_INVALID)
    if memex_supply and fid and str(memex_supply.get("foundup_id") or "") not in {"", fid}:
        reasons.append(AuthorityProfileSeedSupplyReason.FOUNDUP_SCOPE_INVALID)

    allow = _paths_or_default(allowed_paths, fid, denied=False)
    deny = _paths_or_default(denied_paths, fid, denied=True)
    if not fid or not allow or not deny or not all(_path_within_foundup(path, fid) for path in (*allow, *deny)):
        reasons.append(AuthorityProfileSeedSupplyReason.PATH_SCOPE_INVALID)
    operation = str(requested_operation or "").strip()
    if operation in HIGH_AUTHORITY_OPERATIONS and not (
        consensus_receipt_digest and sovereign_authorization_digest
    ):
        reasons.append(AuthorityProfileSeedSupplyReason.HIGH_AUTHORITY_COSIGN_MISSING)
    if identity_ttl_seconds <= 0 or work_authority_ttl_seconds <= 0:
        reasons.append(AuthorityProfileSeedSupplyReason.TIME_BOUNDS_INVALID)

    evidence = _holoindex_evidence(determination, model_selection, memex_supply)
    if not _valid_holoindex_evidence(evidence):
        reasons.append(AuthorityProfileSeedSupplyReason.HOLOINDEX_EVIDENCE_INVALID)

    if reasons:
        return _reject(reasons)

    assert principal is not None
    assert snapshot is not None
    assert allocation is not None
    assert output is not None
    assert fid is not None
    assert repo_full_name is not None
    seed = _seed(
        determination=determination,
        allocation=allocation,
        model_selection=model_selection,
        memex_supply=memex_supply,
        principal=principal,
        snapshot=snapshot,
        reddog_id=rid,
        reddog_public_key=rkey,
        repo_full_name=repo_full_name,
        foundup_id=fid,
        requested_operation=operation,
        allowed_paths=allow,
        denied_paths=deny,
        valve_state_required=str(valve_state_required or VALVE_OPEN_WORKTREE_CREATE),
        key_epoch=str(key_epoch or "epoch-1"),
        required_tests=tuple(_strings(required_tests)) or _DEFAULT_REQUIRED_TESTS,
        required_policy_gates=tuple(_strings(required_policy_gates)) or _DEFAULT_REQUIRED_POLICY_GATES,
        consensus_receipt_digest=consensus_receipt_digest,
        sovereign_authorization_digest=sovereign_authorization_digest,
        holoindex_evidence=evidence,
        now_epoch=now_epoch,
        identity_ttl_seconds=identity_ttl_seconds,
        work_authority_ttl_seconds=work_authority_ttl_seconds,
    )
    if not _ascii_deep(seed):
        return _reject((AuthorityProfileSeedSupplyReason.NON_ASCII_INPUT,))
    try:
        _write_json_atomic(output, seed)
    except Exception:
        return _reject((AuthorityProfileSeedSupplyReason.OUTPUT_WRITE_FAILED,))
    return AuthorityProfileSeedSupplyResult(
        accepted=True,
        status=AUTHORITY_PROFILE_SEED_SUPPLY_ACCEPT,
        seed_supply_receipt_id=str(seed["seed_supply_receipt_id"]),
        output_path=str(output),
        principal_id=principal.principal_id,
        reddog_id=rid,
        foundup_id=fid,
        requested_operation=operation,
        rejection_reasons=(),
    )


def _determination_reasons(determination: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    if not determination or determination.get("schema_version") != "reddog_architect_determination_receipt.v1":
        return [AuthorityProfileSeedSupplyReason.DETERMINATION_INVALID]
    status = str(determination.get("status") or "")
    if determination.get("accepted") is not True or status not in {"ACCEPT", "ARCHITECT_DETERMINATION_ACCEPT"}:
        reasons.append(AuthorityProfileSeedSupplyReason.DETERMINATION_INVALID)
    if str(determination.get("action") or "") != "FIX":
        reasons.append(AuthorityProfileSeedSupplyReason.DETERMINATION_NOT_FIX)
    if determination.get("fusion_quorum_passed") is not True:
        reasons.append(AuthorityProfileSeedSupplyReason.DETERMINATION_INVALID)
    candidate = _mapping(determination.get("queue_candidate"))
    if not candidate or candidate.get("no_execution_performed") is not True:
        reasons.append(AuthorityProfileSeedSupplyReason.QUEUE_CANDIDATE_INVALID)
    return reasons


def _allocation(determination: Mapping[str, Any]) -> Mapping[str, Any]:
    return _mapping(_mapping(determination.get("queue_candidate")).get("wsp15_allocation_receipt"))


def _allocation_mismatches_determination(
    determination: Mapping[str, Any],
    allocation: Mapping[str, Any],
) -> bool:
    return (
        str(determination.get("wsp15_allocation_receipt_id") or "") != str(allocation.get("receipt_id") or "")
        or str(determination.get("wsp15_allocation_digest") or "")
        != canonical_reddog_wsp15_allocation_digest(allocation)
    )


def _model_selection_reasons(model_selection: Mapping[str, Any]) -> list[str]:
    if not model_selection:
        return [AuthorityProfileSeedSupplyReason.MODEL_SELECTION_INVALID]
    if not str(model_selection.get("receipt_id") or "").startswith("model_selection_receipt:"):
        return [AuthorityProfileSeedSupplyReason.MODEL_SELECTION_INVALID]
    if not str(model_selection.get("catalog_snapshot_id") or ""):
        return [AuthorityProfileSeedSupplyReason.MODEL_SELECTION_INVALID]
    requirements = _mapping(model_selection.get("requirements"))
    if str(requirements.get("purpose") or model_selection.get("purpose") or "").lower() != "production":
        return [AuthorityProfileSeedSupplyReason.MODEL_SELECTION_INVALID]
    return []


def _memex_supply_reasons(memex_supply: Mapping[str, Any], determination: Mapping[str, Any]) -> list[str]:
    if not memex_supply:
        return [AuthorityProfileSeedSupplyReason.MEMEX_SUPPLY_INVALID]
    if memex_supply.get("schema_version") != "reddog_operational_memex_snapshot_supply_receipt.v1":
        return [AuthorityProfileSeedSupplyReason.MEMEX_SUPPLY_INVALID]
    if not str(memex_supply.get("receipt_id") or "").startswith("sha256:"):
        return [AuthorityProfileSeedSupplyReason.MEMEX_SUPPLY_INVALID]
    if str(memex_supply.get("snapshot_receipt_id") or "") != str(determination.get("snapshot_receipt_id") or ""):
        return [AuthorityProfileSeedSupplyReason.MEMEX_SUPPLY_INVALID]
    if memex_supply.get("no_holoindex_reindex_performed") is not True:
        return [AuthorityProfileSeedSupplyReason.MEMEX_SUPPLY_INVALID]
    return []


def _selected_foundup_id(value: str | None, principal: PrincipalAuthorityRecord | None) -> str | None:
    explicit = str(value or "").strip()
    if explicit:
        return explicit
    if principal is None:
        return None
    scopes = tuple(item for item in principal.foundup_scope if item)
    return scopes[0] if len(scopes) == 1 else None


def _selected_repo_full_name(
    snapshot: PermissionSnapshot | None,
    principal: PrincipalAuthorityRecord | None,
) -> str | None:
    if snapshot is not None and snapshot.repo_full_name:
        return snapshot.repo_full_name
    if principal is None:
        return None
    scopes = tuple(item for item in principal.repo_scope if item)
    return scopes[0] if len(scopes) == 1 else None


def _paths_or_default(paths: Sequence[str], foundup_id: str | None, *, denied: bool) -> tuple[str, ...]:
    provided = tuple(_strings(paths))
    if provided:
        return provided
    if not foundup_id:
        return ()
    suffix = "secrets/**" if denied else "**"
    return (f"{_FOUNDUP_PATH_PREFIX}{foundup_id}/{suffix}",)


def _holoindex_evidence(
    determination: Mapping[str, Any],
    model_selection: Mapping[str, Any],
    memex_supply: Mapping[str, Any],
) -> dict[str, Any]:
    candidate = _mapping(determination.get("queue_candidate"))
    refs = tuple(_strings(candidate.get("evidence_refs")))
    return {
        "holoindex_query": str(determination.get("next_slice_name") or "RedDog architect FIX promotion"),
        "holoindex_status": "receipt_bound_runtime_evidence",
        "index_gap_detected": False,
        "retrieval_quality": "HIGH",
        "applicable_wsps": ["WSP_15", "WSP_97"],
        "evidence_refs": list(refs),
        "model_selection_receipt_id": str(model_selection.get("receipt_id") or ""),
        "memex_supply_receipt_id": str(memex_supply.get("receipt_id") or ""),
    }


def _valid_holoindex_evidence(evidence: Mapping[str, Any]) -> bool:
    if not evidence:
        return False
    if evidence.get("index_gap_detected") is True:
        return False
    if str(evidence.get("retrieval_quality") or "").upper() == "INDEX_GAP":
        return False
    return bool(_strings(evidence.get("evidence_refs")))


def _seed(
    *,
    determination: Mapping[str, Any],
    allocation: Mapping[str, Any],
    model_selection: Mapping[str, Any],
    memex_supply: Mapping[str, Any],
    principal: PrincipalAuthorityRecord,
    snapshot: PermissionSnapshot,
    reddog_id: str,
    reddog_public_key: str,
    repo_full_name: str,
    foundup_id: str,
    requested_operation: str,
    allowed_paths: Sequence[str],
    denied_paths: Sequence[str],
    valve_state_required: str,
    key_epoch: str,
    required_tests: Sequence[str],
    required_policy_gates: Sequence[str],
    consensus_receipt_digest: str | None,
    sovereign_authorization_digest: str | None,
    holoindex_evidence: Mapping[str, Any],
    now_epoch: int,
    identity_ttl_seconds: int,
    work_authority_ttl_seconds: int,
) -> dict[str, Any]:
    basis = {
        "determination_id": str(determination.get("determination_receipt_id") or ""),
        "queue_candidate_id": str(_mapping(determination.get("queue_candidate")).get("queue_candidate_id") or ""),
        "wsp15_allocation_receipt_id": str(allocation.get("receipt_id") or ""),
        "model_selection_receipt_id": str(model_selection.get("receipt_id") or ""),
        "memex_supply_receipt_id": str(memex_supply.get("receipt_id") or ""),
        "principal_id": principal.principal_id,
        "permission_snapshot_digest": snapshot.evidence_digest,
        "foundup_id": foundup_id,
        "requested_operation": requested_operation,
        "issued_at": now_epoch,
    }
    seed = {
        "schema_version": AUTHORITY_PROFILE_SEED_SCHEMA_VERSION,
        "principal_id": principal.principal_id,
        "principal_provider": principal.principal_provider,
        "reddog_id": reddog_id,
        "reddog_public_key": reddog_public_key,
        "repo_full_name": repo_full_name,
        "foundup_id": foundup_id,
        "allowed_paths": list(allowed_paths),
        "denied_paths": list(denied_paths),
        "requested_operation": requested_operation,
        "permission_snapshot_digest": snapshot.evidence_digest,
        "identity_nonce": "identity-" + _digest({"identity_nonce": basis}).removeprefix("sha256:")[:24],
        "work_authority_nonce": "workauth-" + _digest({"work_authority_nonce": basis}).removeprefix("sha256:")[:24],
        "issued_at": int(now_epoch),
        "identity_expires_at": int(now_epoch) + int(identity_ttl_seconds),
        "work_authority_expires_at": int(now_epoch) + int(work_authority_ttl_seconds),
        "valve_state_required": valve_state_required,
        "key_epoch": key_epoch,
        "required_tests": list(required_tests),
        "required_policy_gates": list(required_policy_gates),
        "holoindex_evidence": dict(holoindex_evidence),
        "source_determination_receipt_id": basis["determination_id"],
        "queue_candidate_id": basis["queue_candidate_id"],
        "wsp15_allocation_receipt_id": basis["wsp15_allocation_receipt_id"],
        "wsp15_allocation_digest": canonical_reddog_wsp15_allocation_digest(allocation),
        "model_selection_receipt_id": basis["model_selection_receipt_id"],
        "model_catalog_snapshot_id": str(model_selection.get("catalog_snapshot_id") or ""),
        "memex_supply_receipt_id": basis["memex_supply_receipt_id"],
        "memex_snapshot_receipt_id": str(memex_supply.get("snapshot_receipt_id") or ""),
        "no_signing_performed": True,
        "no_signature_verification_performed": True,
        "no_signer_state_mutation_performed": True,
        "no_worker_spawn_performed": True,
        "no_worktree_created": True,
        "no_shell_command_executed": True,
        "no_openclaw_enqueue_performed": True,
        "no_hermes_dispatch_performed": True,
        "no_work_state_mutation_performed": True,
        "no_repo_mutation_performed": True,
        "no_holoindex_reindex_performed": True,
        "no_pattern_memory_write_performed": True,
    }
    if consensus_receipt_digest:
        seed["consensus_receipt_digest"] = str(consensus_receipt_digest)
    if sovereign_authorization_digest:
        seed["sovereign_authorization_digest"] = str(sovereign_authorization_digest)
    seed["seed_supply_receipt_id"] = _digest(seed)
    return seed


def _principal(value: Mapping[str, Any] | PrincipalAuthorityRecord | None) -> PrincipalAuthorityRecord | None:
    if isinstance(value, PrincipalAuthorityRecord):
        return value
    data = _mapping(value)
    if not data:
        return None
    try:
        return PrincipalAuthorityRecord(
            principal_id=str(data["principal_id"]),
            principal_provider=str(data["principal_provider"]),
            principal_public_key=str(data["principal_public_key"]),
            repo_scope=tuple(_strings(data.get("repo_scope"))),
            foundup_scope=tuple(_strings(data.get("foundup_scope"))),
            verified_subject_digest=str(data["verified_subject_digest"]),
            reward_account=(str(data["reward_account"]) if data.get("reward_account") else None),
            owner_dae=(str(data["owner_dae"]) if data.get("owner_dae") else None),
            principal_wallet=(str(data["principal_wallet"]) if data.get("principal_wallet") else None),
        )
    except Exception:
        return None


def _snapshot(value: Mapping[str, Any] | PermissionSnapshot | None) -> PermissionSnapshot | None:
    if isinstance(value, PermissionSnapshot):
        return value
    data = _mapping(value)
    if not data:
        return None
    try:
        return PermissionSnapshot(
            evidence_digest=str(data["evidence_digest"]),
            expires_at=int(data["expires_at"]),
            can_write=bool(data.get("can_write", False)),
            can_admin=bool(data.get("can_admin", False)),
            repo_full_name=str(data.get("repo_full_name") or ""),
        )
    except Exception:
        return None


def _runtime_output_path(value: Path | str | None, repo_root: Path) -> tuple[Path | None, list[str]]:
    if not value:
        return None, [AuthorityProfileSeedSupplyReason.OUTPUT_PATH_INVALID]
    path = Path(value)
    if not path.is_absolute():
        path = repo_root.parent / path
    resolved = path.resolve()
    if _is_inside(resolved, repo_root):
        return None, [AuthorityProfileSeedSupplyReason.OUTPUT_PATH_INVALID]
    return resolved, []


def _write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, sort_keys=True, indent=2)
            handle.write("\n")
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def _path_within_foundup(path: str, foundup_id: str) -> bool:
    if not isinstance(path, str) or not path or "\\" in path or ":" in path or path.startswith("/") or "\x00" in path:
        return False
    if path.startswith("//?/") or path.startswith("//./"):
        return False
    prefix = f"{_FOUNDUP_PATH_PREFIX}{foundup_id}/"
    if not path.startswith(prefix):
        return False
    for segment in path.split("/"):
        if segment.strip(" \t") == ".." or segment.strip(" .\t") == "":
            return False
    return True


def _is_inside(child: Path, parent: Path) -> bool:
    child_r = child.resolve()
    parent_r = parent.resolve()
    return child_r == parent_r or parent_r in child_r.parents


def _mapping(value: Any) -> Mapping[str, Any]:
    if hasattr(value, "to_dict"):
        try:
            return value.to_dict()
        except Exception:
            return {}
    return value if isinstance(value, Mapping) else {}


def _strings(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,) if value.strip() else ()
    if isinstance(value, (list, tuple)):
        return tuple(str(item).strip() for item in value if str(item).strip())
    return ()


def _ascii_deep(value: Any) -> bool:
    if isinstance(value, str):
        return all(ord(char) < 128 for char in value)
    if isinstance(value, Mapping):
        return all(isinstance(key, str) and _ascii_deep(key) and _ascii_deep(item) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return all(_ascii_deep(item) for item in value)
    return True


def _digest(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _reject(reasons: Sequence[str]) -> AuthorityProfileSeedSupplyResult:
    return AuthorityProfileSeedSupplyResult(
        accepted=False,
        status=AUTHORITY_PROFILE_SEED_SUPPLY_REJECT,
        seed_supply_receipt_id=None,
        output_path=None,
        principal_id=None,
        reddog_id=None,
        foundup_id=None,
        requested_operation=None,
        rejection_reasons=tuple(dict.fromkeys(str(reason) for reason in reasons if str(reason).strip())),
    )


__all__ = [
    "AUTHORITY_PROFILE_SEED_SCHEMA_VERSION",
    "AUTHORITY_PROFILE_SEED_SUPPLY_ACCEPT",
    "AUTHORITY_PROFILE_SEED_SUPPLY_REJECT",
    "AuthorityProfileSeedSupplyReason",
    "AuthorityProfileSeedSupplyResult",
    "run_reddog_authority_profile_seed_supply",
]
