"""Use-time authority reconstruction for the governed RedDog execution valve.

The resolver re-reads caller-owned runtime artifacts, re-verifies the signed
delegated work authority, and reconstructs canonical valve bindings immediately
before evaluation. The immutable manifest producer exists, but execution remains
closed until selection, replay, current-generation, and peer-handshake controls
are independently verified.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Optional

from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    runtime_operation_lock,
    secure_read_confined_bytes,
)

from modules.communication.moltbot_bridge.src.reddog_execution_valve_environment_supply import (
    resolve_reddog_execution_valve_expected_bindings,
)
from modules.communication.moltbot_bridge.src.reddog_authority_profile_rehydration import (
    rehydrate_authority_profile_runtime,
)
from modules.communication.moltbot_bridge.src.reddog_authoritative_use_lease import (
    AuthoritativeUseLease,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    AUTHORITY_ISSUED,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    WorkAuthorityVerificationPhase,
    verify_delegated_work_authority,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_binding import (
    canonical_full_work_order_digest,
    canonical_work_order_base_ref,
)
from modules.communication.moltbot_bridge.src.reddog_work_authority_digest import (
    work_authority_digest_matches,
)
from modules.communication.moltbot_bridge.src.reddog_wre_execution_valve import (
    GovernedExecutionValveEnvironment,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authority_runtime_invoke import (
    QUEUE_AUTHORITY_RUNTIME_INVOKE_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authority_verification_invoke import (
    QUEUE_AUTHORITY_VERIFICATION_INVOKE_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_consumer_dryrun import (
    plan_reddog_wre_queue_consumer_dry_run,
)
from modules.communication.moltbot_bridge.src.reddog_signer_current_generation_use_time_gate import (
    collect_signer_current_generation_use_time_evidence,
)


AUTHENTICATED_RUNTIME_ARTIFACT_MANIFEST_SELECTION_MISSING = (
    "canonical_signed_runtime_artifact_manifest_selection_verifier_missing"
)
DURABLE_RUNTIME_ARTIFACT_MANIFEST_REPLAY_STATE_MISSING = (
    "canonical_runtime_artifact_manifest_replay_high_water_missing"
)
CURRENT_RUNTIME_ARTIFACT_GENERATION_VERIFIER_MISSING = (
    "canonical_runtime_artifact_manifest_current_generation_verifier_missing"
)
CURRENT_GENERATION_TRUST_ANCHOR_REASONS = (
    AUTHENTICATED_RUNTIME_ARTIFACT_MANIFEST_SELECTION_MISSING,
    DURABLE_RUNTIME_ARTIFACT_MANIFEST_REPLAY_STATE_MISSING,
    CURRENT_RUNTIME_ARTIFACT_GENERATION_VERIFIER_MISSING,
)
AUTHORITY_RUNTIME_STAGE_KEY = "authority_runtime"
AUTHORITY_VERIFICATION_STAGE_KEY = "authority_verification"
INCOMPLETE_TRUST_ANCHOR_REASONS = (
    AUTHENTICATED_RUNTIME_ARTIFACT_MANIFEST_SELECTION_MISSING,
    DURABLE_RUNTIME_ARTIFACT_MANIFEST_REPLAY_STATE_MISSING,
    CURRENT_RUNTIME_ARTIFACT_GENERATION_VERIFIER_MISSING,
    "canonical_consensus_receipt_verifier_missing",
    "canonical_sovereign_authorization_verifier_missing",
    "canonical_principal_subject_key_attestation_missing",
    "canonical_model_signed_evidence_trust_anchor_incomplete",
    "canonical_model_selection_signed_evidence_verifier_missing",
    "canonical_memex_supply_signed_evidence_verifier_missing",
    "canonical_signer_client_peer_handshake_verifier_missing",
)


@dataclass(frozen=True)
class GovernedValveUseTimeResolution:
    environment: Optional[GovernedExecutionValveEnvironment]
    expected_bindings: Mapping[str, Any]
    permission_ttl_seconds: int
    permission_expires_at: str
    rejection_reasons: tuple[str, ...]
    signed_authority_reverified: bool
    authoritative_use_lease: Optional["AuthoritativeUseLease"] = None
    signer_generation_binding_receipt_id: Optional[str] = None


@dataclass(frozen=True)
class GovernedValveUseTimeAuthorityResolver:
    repo_root: Path
    work_state_path: Optional[Path]
    authority_profile_path: Optional[Path]
    permission_snapshots_path: Optional[Path]
    principal_authority_records_path: Optional[Path]
    valve_environment_path: Optional[Path]
    runtime_allowed_root: Path
    signature_verifier: Any
    principal_key_resolver: Any
    nonce_store: Any
    snapshot_resolver: Any
    revocation_oracle: Any
    now_epoch: int
    required_valve_state: str
    trusted_now_epoch: Callable[[], int]
    forbidden_operations: tuple[str, ...] = ()
    revoked_key_epochs: tuple[str, ...] = ()
    leeway_s: int = 60

    def resolve(
        self,
        *,
        chain_state: Mapping[str, Any],
        work_order: Mapping[str, Any],
        queue_item_id: Optional[str],
        selected_slice: Optional[str],
    ) -> GovernedValveUseTimeResolution:
        reasons: list[str] = []
        if not _chain_snapshot_is_canonical(chain_state):
            reasons.append("canonical_chain_results_revision_invalid")

        artifacts, read_reasons = _read_runtime_artifacts(self)
        reasons.extend(read_reasons)
        environment = _governed_environment(artifacts.get("valve_environment"), reasons)
        expected = self._resolve_expected(artifacts, queue_item_id, reasons)
        queue_receipt = self._validate_queue(artifacts, queue_item_id, reasons)
        identity, work_authority = _recorded_authority(chain_state, reasons)
        reverified = self._reverify_and_bind(
            identity=identity,
            work_authority=work_authority,
            work_order=work_order,
            expected=expected,
            queue_receipt=queue_receipt,
            selected_slice=selected_slice,
            reasons=reasons,
        )

        generation_evidence = collect_signer_current_generation_use_time_evidence(
            reverified,
            self.repo_root,
            self.runtime_allowed_root,
            self.trusted_now_epoch,
        )
        generation_binding_receipt_id = generation_evidence.receipt_id
        reasons.extend(
            generation_evidence.remaining_reasons(
                INCOMPLETE_TRUST_ANCHOR_REASONS,
                CURRENT_GENERATION_TRUST_ANCHOR_REASONS,
            )
        )

        # Current-generation evidence is not effect authority. The external
        # signer peer remains the only future issuer for a live use lease.
        authoritative_use_lease = None

        expiry_epoch = _integer(work_authority.get("expires_at")) or self.now_epoch
        ttl = max(1, min(3600, expiry_epoch - self.now_epoch))
        expires = (
            datetime.fromtimestamp(expiry_epoch, tz=timezone.utc)
            .replace(microsecond=0)
            .isoformat()
        )
        return GovernedValveUseTimeResolution(
            environment=environment,
            expected_bindings=expected,
            permission_ttl_seconds=ttl,
            permission_expires_at=expires,
            rejection_reasons=tuple(_dedupe(reasons)),
            signed_authority_reverified=reverified,
            authoritative_use_lease=authoritative_use_lease,
            signer_generation_binding_receipt_id=generation_binding_receipt_id,
        )

    def _reverify_and_bind(
        self,
        *,
        identity: Mapping[str, Any],
        work_authority: Mapping[str, Any],
        work_order: Mapping[str, Any],
        expected: Mapping[str, Any],
        queue_receipt: Mapping[str, Any],
        selected_slice: Optional[str],
        reasons: list[str],
    ) -> bool:
        if not identity or not work_authority:
            reasons.append("canonical_signed_work_authority_missing")
            return False
        checked = self._verify_authority(
            identity=identity,
            work_authority=work_authority,
            phase=WorkAuthorityVerificationPhase.PREFLIGHT_NON_CONSUMING,
        )
        if checked.accepted is not True:
            reasons.extend(
                f"canonical_use_time_authority:{code}" for code in checked.reason_codes
            )
        reasons.extend(_signed_binding_reasons(work_authority, work_order, expected))
        reasons.extend(
            _queue_receipt_binding_reasons(
                queue_receipt, work_authority, work_order, selected_slice
            )
        )
        return checked.accepted is True

    def _consume_authoritative_nonce(
        self,
        *,
        identity: Mapping[str, Any],
        work_authority: Mapping[str, Any],
    ) -> bool:
        try:
            fresh_now_epoch = int(self.trusted_now_epoch())
        except Exception:
            return False
        checked = self._verify_authority(
            identity=identity,
            work_authority=work_authority,
            phase=WorkAuthorityVerificationPhase.AUTHORITATIVE_USE,
            now_epoch=fresh_now_epoch,
        )
        return checked.accepted is True

    def _verify_authority(
        self,
        *,
        identity: Mapping[str, Any],
        work_authority: Mapping[str, Any],
        phase: WorkAuthorityVerificationPhase,
        now_epoch: Optional[int] = None,
    ):
        return verify_delegated_work_authority(
            work_authority=work_authority,
            identity=identity,
            signature_verifier=self.signature_verifier,
            principal_key_resolver=self.principal_key_resolver,
            nonce_store=self.nonce_store,
            snapshot_resolver=self.snapshot_resolver,
            revocation_oracle=self.revocation_oracle,
            now=self.now_epoch if now_epoch is None else int(now_epoch),
            required_valve_state=self.required_valve_state,
            forbidden_operations=self.forbidden_operations,
            revoked_key_epochs=self.revoked_key_epochs,
            leeway_s=self.leeway_s,
            verification_phase=phase,
        )

    def _validate_queue(
        self,
        artifacts: Mapping[str, Mapping[str, Any]],
        queue_item_id: Optional[str],
        reasons: list[str],
    ) -> Mapping[str, Any]:
        work_state = artifacts.get("work_state")
        if work_state is None:
            reasons.append("canonical_queue_claim_state_missing")
            return {}
        now_iso = datetime.fromtimestamp(self.now_epoch, tz=timezone.utc).isoformat()
        result = plan_reddog_wre_queue_consumer_dry_run(
            work_state,
            now_iso=now_iso,
            requested_queue_item_id=queue_item_id,
            require_governed_lineage=True,
        )
        if result.accepted is not True or result.receipt is None:
            reasons.extend(
                f"canonical_queue_consumer:{reason}"
                for reason in result.rejection_reasons
            )
            return {}
        return result.receipt.to_dict()

    @staticmethod
    def _resolve_expected(
        artifacts: Mapping[str, Mapping[str, Any]],
        queue_item_id: Optional[str],
        reasons: list[str],
    ) -> Mapping[str, Any]:
        required = (
            "work_state",
            "authority_profile",
            "permission_snapshots",
            "principal_authority_records",
        )
        if any(name not in artifacts for name in required) or not queue_item_id:
            reasons.append("canonical_expected_bindings_unavailable")
            return {}
        expected, binding_reasons = resolve_reddog_execution_valve_expected_bindings(
            work_state=artifacts["work_state"],
            authority_profile=artifacts["authority_profile"],
            permission_snapshots=artifacts["permission_snapshots"],
            principal_authority_records=artifacts["principal_authority_records"],
            queue_item_id=str(queue_item_id),
        )
        reasons.extend(
            f"canonical_use_time_binding:{reason}" for reason in binding_reasons
        )
        return expected or {}


def _read_runtime_artifacts(
    resolver: GovernedValveUseTimeAuthorityResolver,
) -> tuple[dict[str, Mapping[str, Any]], list[str]]:
    paths = {
        "work_state": resolver.work_state_path,
        "authority_profile": resolver.authority_profile_path,
        "permission_snapshots": resolver.permission_snapshots_path,
        "principal_authority_records": resolver.principal_authority_records_path,
        "valve_environment": resolver.valve_environment_path,
    }
    payloads, reasons = _read_runtime_artifact_pass(resolver, paths)
    if reasons:
        return {}, reasons
    verified_payloads, verify_reasons = _read_runtime_artifact_pass(resolver, paths)
    if verify_reasons:
        return {}, verify_reasons
    changed = [
        name for name in paths if payloads.get(name) != verified_payloads.get(name)
    ]
    if changed:
        return {}, [
            f"canonical_use_time_artifact_snapshot_changed:{name}" for name in changed
        ]
    try:
        payloads["authority_profile"] = rehydrate_authority_profile_runtime(
            payloads["authority_profile"]
        )
    except (KeyError, TypeError, ValueError):
        return {}, ["canonical_use_time_authority_profile_invalid"]
    return payloads, []


def _read_runtime_artifact_pass(
    resolver: GovernedValveUseTimeAuthorityResolver,
    paths: Mapping[str, Optional[Path]],
) -> tuple[dict[str, Mapping[str, Any]], list[str]]:
    payloads: dict[str, Mapping[str, Any]] = {}
    reasons: list[str] = []
    for name, path in paths.items():
        if path is None:
            reasons.append(f"canonical_use_time_artifact_path_missing:{name}")
            continue
        payload, reason = _read_json_no_follow(
            resolver.repo_root, path, resolver.runtime_allowed_root
        )
        if reason:
            reasons.append(f"canonical_use_time_artifact_invalid:{name}:{reason}")
        elif payload is not None:
            payloads[name] = payload
    return payloads, reasons


def _read_json_no_follow(
    repo_root: Path,
    path: Path,
    allowed_root: Path,
) -> tuple[Optional[Mapping[str, Any]], Optional[str]]:
    root = repo_root.resolve()
    candidate = Path(os.path.abspath(Path(path).expanduser()))
    try:
        with runtime_operation_lock(str(candidate) + ".operation"):
            resolved_for_repo_check = candidate.resolve(strict=True)
            if (
                resolved_for_repo_check == root
                or root in resolved_for_repo_check.parents
            ):
                return None, "inside_repo"
            raw, _ = secure_read_confined_bytes(
                candidate,
                allowed_root=allowed_root,
                max_bytes=1024 * 1024,
            )
        if len(raw) >= 1024 * 1024:
            return None, "not_bounded_regular_file"
        payload = json.loads(raw.decode("utf-8"))
        return (
            (payload, None) if isinstance(payload, Mapping) else (None, "not_mapping")
        )
    except (OSError, ValueError, UnicodeError, json.JSONDecodeError):
        return None, "unreadable"


def _recorded_authority(
    chain_state: Mapping[str, Any], reasons: list[str]
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    stages = _stage_results(chain_state)
    runtime = _mapping(stages.get(AUTHORITY_RUNTIME_STAGE_KEY))
    verification = _mapping(stages.get(AUTHORITY_VERIFICATION_STAGE_KEY))
    authority_result = _mapping(runtime.get("authority_result"))
    identity = _mapping(authority_result.get("identity"))
    work_authority = _mapping(authority_result.get("work_authority"))
    reasons.extend(
        _validate_recorded_authority(
            runtime, verification, authority_result, identity, work_authority
        )
    )
    return identity, work_authority


def _validate_recorded_authority(
    runtime: Mapping[str, Any],
    verification: Mapping[str, Any],
    authority_result: Mapping[str, Any],
    identity: Mapping[str, Any],
    work_authority: Mapping[str, Any],
) -> list[str]:
    reasons: list[str] = []
    receipt = _mapping(authority_result.get("receipt"))
    checked = _mapping(verification.get("verification_result"))
    if (
        runtime.get("decision") != QUEUE_AUTHORITY_RUNTIME_INVOKE_ACCEPT
        or authority_result.get("accepted") is not True
        or receipt.get("status") != AUTHORITY_ISSUED
    ):
        reasons.append("canonical_recorded_authority_runtime_not_accepted")
    if (
        verification.get("decision") != QUEUE_AUTHORITY_VERIFICATION_INVOKE_ACCEPT
        or checked.get("accepted") is not True
    ):
        reasons.append("canonical_recorded_authority_verification_not_accepted")
    if checked.get("work_order_id") != _mapping(
        authority_result.get("work_authority")
    ).get("work_order_id"):
        reasons.append("canonical_recorded_authority_work_order_mismatch")
    required_receipt_fields = {
        "receipt_id",
        "status",
        "work_order_id",
        "identity_digest",
        "work_authority_digest",
        "generated_at",
    }
    if not required_receipt_fields.issubset(receipt) or any(
        receipt.get(field) in (None, "") for field in required_receipt_fields
    ):
        reasons.append("canonical_authority_receipt_lineage_incomplete")
    if receipt.get("work_order_id") != work_authority.get("work_order_id"):
        reasons.append("canonical_authority_receipt_work_order_mismatch")
    if identity and receipt.get("identity_digest") != _digest(identity):
        reasons.append("canonical_identity_receipt_digest_mismatch")
    if work_authority and not work_authority_digest_matches(
        work_authority, receipt.get("work_authority_digest")
    ):
        reasons.append("canonical_work_authority_receipt_digest_mismatch")
    identity_bindings = {
        "principal_id": identity.get("principal_id"),
        "reddog_id": identity.get("reddog_id"),
        "signer_public_key": identity.get("reddog_public_key"),
    }
    for field, identity_value in identity_bindings.items():
        if identity and work_authority.get(field) != identity_value:
            reasons.append(f"canonical_identity_work_authority_mismatch:{field}")
    if identity and work_authority.get("repo_full_name") not in set(
        identity.get("repo_scope") or ()
    ):
        reasons.append("canonical_identity_work_authority_mismatch:repo_scope")
    if identity and work_authority.get("foundup_id") not in set(
        identity.get("foundup_scope") or ()
    ):
        reasons.append("canonical_identity_work_authority_mismatch:foundup_scope")
    return reasons


def _signed_binding_reasons(
    authority: Mapping[str, Any],
    work_order: Mapping[str, Any],
    expected: Mapping[str, Any],
) -> list[str]:
    try:
        work_order_digest = canonical_full_work_order_digest(work_order)
        base_ref = canonical_work_order_base_ref(work_order)
    except (TypeError, ValueError):
        return ["canonical_work_order_binding_invalid"]
    snapshot = _mapping(work_order.get("repo_permission_snapshot"))
    allocation = _mapping(work_order.get("wsp15_allocation_receipt"))
    work_order_values = {
        "work_order_id": work_order.get("work_order_id"),
        "work_order_digest": work_order_digest,
        "base_ref": base_ref,
        "requested_operation": work_order.get("requested_operation"),
        "repo_full_name": work_order.get("repo_full_name"),
        "foundup_id": work_order.get("foundup_id"),
        "valve_state_required": work_order.get("valve_state_required"),
        "allowed_paths": work_order.get("allowed_paths"),
        "denied_paths": work_order.get("denied_paths"),
        "permission_snapshot_digest": snapshot.get("digest"),
        "wsp15_allocation_receipt_id": allocation.get("receipt_id"),
        "wsp15_allocation_digest": work_order.get("wsp15_allocation_digest"),
        "wsp15_priority": work_order.get("wsp15_priority"),
        "wsp15_mps_total": work_order.get("wsp15_mps_total"),
        "wsp15_reasoning_tier": work_order.get("wsp15_reasoning_tier"),
        "model_selection_receipt_id": work_order.get("model_selection_receipt_id"),
        "model_selection_digest": work_order.get("model_selection_digest"),
        "model_runtime_binding_receipt_id": work_order.get(
            "model_runtime_binding_receipt_id"
        ),
        "model_runtime_binding_digest": work_order.get("model_runtime_binding_digest"),
        "memex_supply_receipt_id": work_order.get("memex_supply_receipt_id"),
        "memex_supply_digest": work_order.get("memex_supply_digest"),
    }
    reasons = [
        f"canonical_signed_work_order_binding_mismatch:{field}"
        for field, value in work_order_values.items()
        if authority.get(field) != value
    ]
    for field in (
        "work_order_id",
        "requested_operation",
        "valve_state_required",
        "repo_full_name",
        "foundup_id",
        "principal_id",
        "reddog_id",
        "key_epoch",
        "permission_snapshot_digest",
        "wsp15_allocation_receipt_id",
        "wsp15_allocation_digest",
        "model_selection_receipt_id",
        "model_selection_digest",
        "model_runtime_binding_receipt_id",
        "model_runtime_binding_digest",
        "memex_supply_receipt_id",
        "memex_supply_digest",
        "consensus_receipt_digest",
        "sovereign_authorization_digest",
    ):
        if field not in expected or authority.get(field) != expected.get(field):
            reasons.append(f"canonical_signed_expected_binding_mismatch:{field}")
    return reasons


def _queue_current_truth_checks(
    receipt: Mapping[str, Any],
    authority: Mapping[str, Any],
    work_order: Mapping[str, Any],
    selected_slice: Optional[str],
) -> dict[str, tuple[Any, Any]]:
    return {
        "queue_consumer_receipt_digest": (
            _canonical_queue_receipt_digest(receipt),
            authority.get("queue_consumer_receipt_digest"),
        ),
        "work_order_id": (
            authority.get("work_order_id"),
            work_order.get("work_order_id"),
        ),
        "slice_id": (receipt.get("slice_id"), authority.get("selected_slice")),
        "selected_slice": (selected_slice, authority.get("selected_slice")),
        "progressive_policy_stage_receipt_id": (
            receipt.get("progressive_policy_stage_receipt_id"),
            authority.get("progressive_policy_stage_receipt_id"),
        ),
        "progressive_policy_stage_digest": (
            receipt.get("progressive_policy_stage_digest"),
            authority.get("progressive_policy_stage_digest"),
        ),
    }


def _queue_optional_binding_checks(
    receipt: Mapping[str, Any], authority: Mapping[str, Any]
) -> dict[str, tuple[Any, Any]]:
    return {
        "wsp15_allocation_receipt_id": (
            receipt.get("wsp15_allocation_receipt_id"),
            authority.get("wsp15_allocation_receipt_id"),
        ),
        "wsp15_allocation_digest": (
            receipt.get("wsp15_allocation_digest"),
            authority.get("wsp15_allocation_digest"),
        ),
        "wsp15_priority": (
            receipt.get("wsp15_priority"),
            authority.get("wsp15_priority"),
        ),
        "wsp15_mps_total": (
            receipt.get("wsp15_mps_total"),
            authority.get("wsp15_mps_total"),
        ),
        "wsp15_reasoning_tier": (
            receipt.get("reasoning_tier"),
            authority.get("wsp15_reasoning_tier"),
        ),
        "model_runtime_binding_receipt_id": (
            receipt.get("model_runtime_binding_receipt_id"),
            authority.get("model_runtime_binding_receipt_id"),
        ),
        "model_runtime_binding_digest": (
            receipt.get("model_runtime_binding_digest"),
            authority.get("model_runtime_binding_digest"),
        ),
        "model_selection_receipt_id": (
            receipt.get("model_selection_receipt_id"),
            authority.get("model_selection_receipt_id"),
        ),
        "model_selection_digest": (
            receipt.get("model_selection_digest"),
            authority.get("model_selection_digest"),
        ),
        "memex_supply_receipt_id": (
            receipt.get("memex_supply_receipt_id"),
            authority.get("memex_supply_receipt_id"),
        ),
        "memex_supply_digest": (
            receipt.get("memex_supply_digest"),
            authority.get("memex_supply_digest"),
        ),
    }


def _queue_receipt_binding_reasons(
    receipt: Mapping[str, Any],
    authority: Mapping[str, Any],
    work_order: Mapping[str, Any],
    selected_slice: Optional[str],
) -> list[str]:
    if not receipt:
        return ["canonical_queue_consumer_receipt_missing"]
    checks = _queue_current_truth_checks(receipt, authority, work_order, selected_slice)
    checks.update(_queue_optional_binding_checks(receipt, authority))
    return [
        f"canonical_queue_authority_binding_mismatch:{field}"
        for field, (left, right) in checks.items()
        if left != right
    ]


def _canonical_queue_receipt_digest(receipt: Mapping[str, Any]) -> Optional[str]:
    try:
        return canonical_full_work_order_digest(receipt)
    except (TypeError, ValueError):
        return None


def _stage_results(state: Mapping[str, Any]) -> Mapping[str, Mapping[str, Any]]:
    raw = state.get("stage_results")
    return raw if isinstance(raw, Mapping) else {}


def _governed_environment(
    payload: Optional[Mapping[str, Any]], reasons: list[str]
) -> Optional[GovernedExecutionValveEnvironment]:
    if payload is None:
        return None
    try:
        return GovernedExecutionValveEnvironment.from_mapping(payload)
    except ValueError as exc:
        reasons.append(str(exc))
        return None


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _select(values: Any, field: str, expected: Any) -> Mapping[str, Any]:
    if not isinstance(values, list):
        return {}
    return next(
        (
            item
            for item in values
            if isinstance(item, Mapping) and item.get(field) == expected
        ),
        {},
    )


def _digest(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _chain_snapshot_is_canonical(snapshot: Mapping[str, Any]) -> bool:
    revision = str(snapshot.get("revision") or "")
    receipts = snapshot.get("receipts")
    if not revision or not isinstance(receipts, list) or not receipts:
        return False
    payload = json.loads(json.dumps(snapshot, sort_keys=True))
    payload.pop("revision", None)
    if isinstance(payload.get("receipts", [None])[-1], Mapping):
        payload["receipts"][-1] = {**payload["receipts"][-1], "store_revision": None}
    newest = _mapping(receipts[-1])
    return newest.get("store_revision") == revision and _digest(payload) == revision


def _integer(value: Any) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


__all__ = [
    "AUTHENTICATED_RUNTIME_ARTIFACT_MANIFEST_SELECTION_MISSING",
    "AuthoritativeUseLease",
    "CURRENT_RUNTIME_ARTIFACT_GENERATION_VERIFIER_MISSING",
    "DURABLE_RUNTIME_ARTIFACT_MANIFEST_REPLAY_STATE_MISSING",
    "GovernedValveUseTimeAuthorityResolver",
    "GovernedValveUseTimeResolution",
]
