"""Authority-profile source artifact supplier for RedDog FIX promotion.

Slice: REDDOG_AUTHORITY_PROFILE_SOURCE_ARTIFACT_SUPPLY_PHASE1

This module materializes the source authority profile consumed by the existing
architect FIX promotion bridge. It validates an explicit authority seed against
token-verified principal evidence and a fresh permission snapshot, then writes
one JSON artifact outside the source repository.

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
    HIGH_AUTHORITY_VALVE_STATES,
    PrincipalAuthorityRecord,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    PermissionSnapshot,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    runtime_operation_lock,
)


AUTHORITY_PROFILE_SOURCE_SUPPLY_ACCEPT = "AUTHORITY_PROFILE_SOURCE_SUPPLY_ACCEPT"
AUTHORITY_PROFILE_SOURCE_SUPPLY_REJECT = "AUTHORITY_PROFILE_SOURCE_SUPPLY_REJECT"
AUTHORITY_PROFILE_SOURCE_SCHEMA_VERSION = "reddog_authority_profile_source.v1"

_FOUNDUP_PATH_PREFIX = "modules/foundups/"

_REQUIRED_SEED_FIELDS = (
    "principal_id",
    "principal_provider",
    "reddog_id",
    "reddog_public_key",
    "repo_full_name",
    "foundup_id",
    "allowed_paths",
    "denied_paths",
    "requested_operation",
    "permission_snapshot_digest",
    "identity_nonce",
    "work_authority_nonce",
    "issued_at",
    "identity_expires_at",
    "work_authority_expires_at",
    "valve_state_required",
    "key_epoch",
    "required_tests",
    "required_policy_gates",
    "holoindex_evidence",
)


class AuthorityProfileSourceSupplyReason:
    SEED_MISSING = "authority_profile_seed_missing"
    SEED_NON_ASCII = "authority_profile_seed_non_ascii"
    REQUIRED_FIELD_MISSING = "authority_profile_seed_required_field_missing"
    PRINCIPAL_INVALID = "principal_authority_record_invalid"
    PRINCIPAL_MISMATCH = "principal_authority_record_mismatch"
    REPO_OUT_OF_SCOPE = "principal_repo_scope_missing"
    FOUNDUP_OUT_OF_SCOPE = "principal_foundup_scope_missing"
    PERMISSION_SNAPSHOT_INVALID = "permission_snapshot_invalid"
    PERMISSION_SNAPSHOT_MISMATCH = "permission_snapshot_digest_mismatch"
    PERMISSION_SNAPSHOT_STALE = "permission_snapshot_stale"
    PERMISSION_DENIED = "permission_snapshot_denies_operation"
    PATH_SCOPE = "authority_profile_path_scope_invalid"
    UNSUPPORTED_REPO_WIDE = "authority_profile_repo_wide_not_supported"
    HIGH_AUTHORITY_COSIGN = "authority_profile_high_authority_cosign_missing"
    HOLOINDEX_EVIDENCE_INVALID = "authority_profile_holoindex_evidence_invalid"
    TIME_BOUNDS_INVALID = "authority_profile_time_bounds_invalid"
    KEY_REUSE = "authority_profile_principal_reddog_key_reuse"
    OUTPUT_PATH_INVALID = "authority_profile_source_output_path_invalid"
    OUTPUT_WRITE_FAILED = "authority_profile_source_output_write_failed"


@dataclass(frozen=True)
class AuthorityProfileSourceSupplyResult:
    accepted: bool
    status: str
    authority_profile_source_receipt_id: str | None
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


def run_reddog_authority_profile_source_artifact_supply(
    *,
    repo_root: Path | str,
    authority_seed: Mapping[str, Any] | None,
    principal_authority_record: Mapping[str, Any] | PrincipalAuthorityRecord | None,
    permission_snapshot: Mapping[str, Any] | PermissionSnapshot | None,
    output_path: Path | str | None,
    now_epoch: int,
    leeway_s: int = 60,
) -> AuthorityProfileSourceSupplyResult:
    """Validate and materialize one authority-profile source artifact."""

    root = Path(repo_root).resolve()
    seed = _mapping(authority_seed)
    reasons: list[str] = []
    if not seed:
        reasons.append(AuthorityProfileSourceSupplyReason.SEED_MISSING)
    elif not _ascii_deep(seed):
        reasons.append(AuthorityProfileSourceSupplyReason.SEED_NON_ASCII)
    missing = [field for field in _REQUIRED_SEED_FIELDS if field not in seed or seed.get(field) in (None, "", (), [])]
    if missing:
        reasons.extend(
            f"{AuthorityProfileSourceSupplyReason.REQUIRED_FIELD_MISSING}:{field}" for field in missing
        )

    principal = _principal(principal_authority_record)
    if principal is None:
        reasons.append(AuthorityProfileSourceSupplyReason.PRINCIPAL_INVALID)
    snapshot = _snapshot(permission_snapshot)
    if snapshot is None:
        reasons.append(AuthorityProfileSourceSupplyReason.PERMISSION_SNAPSHOT_INVALID)

    output, output_reasons = _runtime_output_path(output_path, root)
    reasons.extend(output_reasons)
    if seed and principal is not None:
        reasons.extend(_principal_reasons(seed, principal))
    if seed and snapshot is not None:
        reasons.extend(_snapshot_reasons(seed, snapshot, now_epoch=now_epoch, leeway_s=leeway_s))
    if seed:
        reasons.extend(_seed_policy_reasons(seed, now_epoch=now_epoch, leeway_s=leeway_s))

    deduped = _dedupe(reasons)
    if deduped:
        return _reject(deduped)

    assert principal is not None
    assert snapshot is not None
    assert output is not None
    profile = _profile(seed, principal, snapshot)
    try:
        _write_json_atomic(output, profile)
    except Exception:
        return _reject((AuthorityProfileSourceSupplyReason.OUTPUT_WRITE_FAILED,))
    return AuthorityProfileSourceSupplyResult(
        accepted=True,
        status=AUTHORITY_PROFILE_SOURCE_SUPPLY_ACCEPT,
        authority_profile_source_receipt_id=str(profile["authority_profile_source_receipt_id"]),
        output_path=str(output),
        principal_id=str(profile["principal_id"]),
        reddog_id=str(profile["reddog_id"]),
        foundup_id=str(profile["foundup_id"]),
        requested_operation=str(profile["requested_operation"]),
        rejection_reasons=(),
    )


def _principal_reasons(seed: Mapping[str, Any], principal: PrincipalAuthorityRecord) -> list[str]:
    reasons: list[str] = []
    if (
        str(seed.get("principal_id") or "") != principal.principal_id
        or str(seed.get("principal_provider") or "") != principal.principal_provider
    ):
        reasons.append(AuthorityProfileSourceSupplyReason.PRINCIPAL_MISMATCH)
    if str(seed.get("repo_full_name") or "") not in set(principal.repo_scope):
        reasons.append(AuthorityProfileSourceSupplyReason.REPO_OUT_OF_SCOPE)
    if str(seed.get("foundup_id") or "") not in set(principal.foundup_scope):
        reasons.append(AuthorityProfileSourceSupplyReason.FOUNDUP_OUT_OF_SCOPE)
    if str(seed.get("reddog_public_key") or "") == principal.principal_public_key:
        reasons.append(AuthorityProfileSourceSupplyReason.KEY_REUSE)
    return reasons


def _snapshot_reasons(
    seed: Mapping[str, Any],
    snapshot: PermissionSnapshot,
    *,
    now_epoch: int,
    leeway_s: int,
) -> list[str]:
    reasons: list[str] = []
    if snapshot.evidence_digest != str(seed.get("permission_snapshot_digest") or ""):
        reasons.append(AuthorityProfileSourceSupplyReason.PERMISSION_SNAPSHOT_MISMATCH)
    if not snapshot.is_fresh(now_epoch, leeway_s):
        reasons.append(AuthorityProfileSourceSupplyReason.PERMISSION_SNAPSHOT_STALE)
    if not snapshot.grants(str(seed.get("requested_operation") or ""), str(seed.get("repo_full_name") or "")):
        reasons.append(AuthorityProfileSourceSupplyReason.PERMISSION_DENIED)
    return reasons


def _seed_policy_reasons(seed: Mapping[str, Any], *, now_epoch: int, leeway_s: int) -> list[str]:
    reasons: list[str] = []
    foundup_id = str(seed.get("foundup_id") or "")
    if not foundup_id or foundup_id in {"*", "repo", "root", "all"}:
        reasons.append(AuthorityProfileSourceSupplyReason.UNSUPPORTED_REPO_WIDE)
    allowed_paths = _strings(seed.get("allowed_paths"))
    denied_paths = _strings(seed.get("denied_paths"))
    if not allowed_paths or not all(_path_within_foundup(path, foundup_id) for path in allowed_paths):
        reasons.append(AuthorityProfileSourceSupplyReason.PATH_SCOPE)
    if not denied_paths or not all(_path_within_foundup(path, foundup_id) for path in denied_paths):
        reasons.append(AuthorityProfileSourceSupplyReason.PATH_SCOPE)
    operation = str(seed.get("requested_operation") or "")
    high_authority = (
        operation in HIGH_AUTHORITY_OPERATIONS
        or str(seed.get("valve_state_required") or "") in HIGH_AUTHORITY_VALVE_STATES
    )
    if high_authority and not (
        seed.get("consensus_receipt_digest") and seed.get("sovereign_authorization_digest")
    ):
        reasons.append(AuthorityProfileSourceSupplyReason.HIGH_AUTHORITY_COSIGN)
    if not _valid_holoindex_evidence(_mapping(seed.get("holoindex_evidence"))):
        reasons.append(AuthorityProfileSourceSupplyReason.HOLOINDEX_EVIDENCE_INVALID)
    try:
        issued_at = int(seed.get("issued_at"))
        identity_expires_at = int(seed.get("identity_expires_at"))
        work_expires_at = int(seed.get("work_authority_expires_at"))
    except Exception:
        reasons.append(AuthorityProfileSourceSupplyReason.TIME_BOUNDS_INVALID)
        return reasons
    if issued_at > now_epoch + int(leeway_s) or identity_expires_at <= now_epoch or work_expires_at <= now_epoch:
        reasons.append(AuthorityProfileSourceSupplyReason.TIME_BOUNDS_INVALID)
    if not _strings(seed.get("required_tests")) or not _strings(seed.get("required_policy_gates")):
        reasons.append(AuthorityProfileSourceSupplyReason.REQUIRED_FIELD_MISSING + ":required_execution_gates")
    return reasons


def _profile(
    seed: Mapping[str, Any],
    principal: PrincipalAuthorityRecord,
    snapshot: PermissionSnapshot,
) -> dict[str, Any]:
    body = dict(seed)
    body.update(
        {
            "schema_version": AUTHORITY_PROFILE_SOURCE_SCHEMA_VERSION,
            "principal_public_key": principal.principal_public_key,
            "permission_snapshot_digest": snapshot.evidence_digest,
            "allowed_paths": list(_strings(seed.get("allowed_paths"))),
            "denied_paths": list(_strings(seed.get("denied_paths"))),
            "required_tests": list(_strings(seed.get("required_tests"))),
            "required_policy_gates": list(_strings(seed.get("required_policy_gates"))),
            "source_authority_basis": {
                "principal_verified_subject_digest": principal.verified_subject_digest,
                "principal_repo_scope": list(principal.repo_scope),
                "principal_foundup_scope": list(principal.foundup_scope),
                "permission_snapshot_digest": snapshot.evidence_digest,
                "permission_snapshot_expires_at": snapshot.expires_at,
                "permission_snapshot_can_write": snapshot.can_write,
                "permission_snapshot_can_admin": snapshot.can_admin,
            },
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
    )
    if principal.reward_account:
        body["reward_account"] = principal.reward_account
    if principal.owner_dae:
        body["owner_dae"] = principal.owner_dae
    if principal.principal_wallet:
        body["principal_wallet"] = principal.principal_wallet
    body["authority_profile_source_receipt_id"] = _digest(body)
    return body


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
            repo_scope=tuple(str(item) for item in _strings(data.get("repo_scope"))),
            foundup_scope=tuple(str(item) for item in _strings(data.get("foundup_scope"))),
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
        return None, [AuthorityProfileSourceSupplyReason.OUTPUT_PATH_INVALID]
    path = Path(value)
    if not path.is_absolute():
        path = repo_root.parent / path
    resolved = path.resolve()
    try:
        resolved.relative_to(repo_root)
        return None, [AuthorityProfileSourceSupplyReason.OUTPUT_PATH_INVALID]
    except ValueError:
        return resolved, []


def _write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    with runtime_operation_lock(str(path) + ".operation"):
        _write_json_atomic_unlocked(path, payload)


def _write_json_atomic_unlocked(path: Path, payload: Mapping[str, Any]) -> None:
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


def _valid_holoindex_evidence(evidence: Mapping[str, Any]) -> bool:
    if not evidence:
        return False
    if evidence.get("index_gap_detected") is True:
        return False
    if str(evidence.get("retrieval_quality") or "").upper() == "INDEX_GAP":
        return False
    refs = evidence.get("evidence_refs")
    return bool(_strings(refs))


def _mapping(value: Any) -> Mapping[str, Any]:
    if hasattr(value, "to_dict"):
        try:
            return value.to_dict()
        except Exception:
            return {}
    return value if isinstance(value, Mapping) else {}


def _strings(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    if isinstance(value, (list, tuple)):
        return tuple(str(item) for item in value if str(item).strip())
    return ()


def _ascii_deep(value: Any) -> bool:
    if isinstance(value, str):
        return all(ord(char) < 128 for char in value)
    if isinstance(value, Mapping):
        return all(isinstance(key, str) and _ascii_deep(key) and _ascii_deep(item) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return all(_ascii_deep(item) for item in value)
    return True


def _digest(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _reject(reasons: Sequence[str]) -> AuthorityProfileSourceSupplyResult:
    return AuthorityProfileSourceSupplyResult(
        accepted=False,
        status=AUTHORITY_PROFILE_SOURCE_SUPPLY_REJECT,
        authority_profile_source_receipt_id=None,
        output_path=None,
        principal_id=None,
        reddog_id=None,
        foundup_id=None,
        requested_operation=None,
        rejection_reasons=_dedupe(reasons),
    )


def _dedupe(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(value) for value in values if str(value).strip()))


__all__ = [
    "AUTHORITY_PROFILE_SOURCE_SCHEMA_VERSION",
    "AUTHORITY_PROFILE_SOURCE_SUPPLY_ACCEPT",
    "AUTHORITY_PROFILE_SOURCE_SUPPLY_REJECT",
    "AuthorityProfileSourceSupplyReason",
    "AuthorityProfileSourceSupplyResult",
    "run_reddog_authority_profile_source_artifact_supply",
]
