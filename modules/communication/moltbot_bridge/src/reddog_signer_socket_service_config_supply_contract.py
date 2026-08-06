"""Typed contract for signer socket service config materialization."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from modules.communication.moltbot_bridge.src.reddog_architect_proposal_authenticity import (
    ArchitectProposalPolicyAuthorization,
    ArchitectProposalSignerPolicy,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    PrincipalKeyResolver,
)


SIGNER_SERVICE_CONFIG_SUPPLY_ACCEPT = "SIGNER_SERVICE_CONFIG_SUPPLY_ACCEPT"
SIGNER_SERVICE_CONFIG_SUPPLY_REJECT = "SIGNER_SERVICE_CONFIG_SUPPLY_REJECT"
SIGNER_SERVICE_CONFIG_SCHEMA_VERSION = "reddog_signer_service_config.v3"

FAIL_SIGNER_CONFIG_AUTHORITY_PROFILE_INVALID = (
    "signer_config_authority_profile_invalid"
)
FAIL_SIGNER_CONFIG_ARCHITECT_PUBLICATION_INVALID = (
    "signer_config_architect_publication_invalid"
)
FAIL_SIGNER_CONFIG_OUTPUT_PATH_INVALID = "signer_config_output_path_invalid"
FAIL_SIGNER_CONFIG_SOCKET_PATH_INVALID = "signer_config_socket_path_invalid"
FAIL_SIGNER_CONFIG_CONTROL_ANCHOR_PATH_INVALID = (
    "signer_config_control_anchor_path_invalid"
)
FAIL_SIGNER_CONFIG_OP_REF_INVALID = "signer_config_op_ref_invalid"
FAIL_SIGNER_CONFIG_OP_REF_REUSED = "signer_config_op_ref_reused"
FAIL_SIGNER_CONFIG_PEER_POLICY_INVALID = "signer_config_peer_policy_invalid"
FAIL_SIGNER_CONFIG_LIMITS_INVALID = "signer_config_limits_invalid"
FAIL_SIGNER_CONFIG_PROPOSAL_POLICY_INVALID = (
    "signer_config_proposal_policy_invalid"
)
FAIL_SIGNER_CONFIG_PROPOSAL_POLICY_AUTHORIZATION_INVALID = (
    "signer_config_proposal_policy_authorization_invalid"
)
FAIL_SIGNER_CONFIG_PROPOSAL_NONCE_PATH_INVALID = (
    "signer_config_proposal_nonce_path_invalid"
)
FAIL_SIGNER_CONFIG_WRITE_FAILED = "signer_config_write_failed"


@dataclass(frozen=True)
class SignerServiceConfigSupplyRequest:
    repo_root: Path | str
    runtime_root: Path | str
    signer_runtime_root: Path | str
    authority_profile: Mapping[str, Any] | None
    authoritative_work_state_path: Path | str | None
    output_path: Path | str | None
    socket_path: Path | str | None
    principal_signing_key_ref: str
    principal_audit_mac_key_ref: str
    reddog_signing_key_ref: str
    reddog_audit_mac_key_ref: str
    peer_uid_to_principal: Mapping[int | str, str]
    allowed_gids: Sequence[int | str]
    max_requests: int
    timeout_s: float
    max_request_bytes: int
    max_response_bytes: int
    principal_signer_agent_id: str
    reddog_signer_agent_id: str
    control_loop_anchor_path: Path | str | None
    proposal_authority_policy: ArchitectProposalSignerPolicy | None
    proposal_policy_authorization: (
        ArchitectProposalPolicyAuthorization | Mapping[str, Any] | None
    )
    proposal_nonce_store_path: Path | str | None
    proposal_replay_high_water_store_id: str | None
    proposal_replay_high_water_durability_receipt_id: str | None
    now_epoch: int | None
    principal_key_resolver: PrincipalKeyResolver | None
    authoritative_work_state: Mapping[str, Any] | None


@dataclass(frozen=True)
class SignerServiceConfigSupplyResult:
    """Audit-safe result for signer service config materialization."""

    accepted: bool
    status: str
    config_supply_receipt_id: str | None
    config_path: str | None
    config_digest: str | None
    socket_path: str | None
    principal_id: str | None
    reddog_id: str | None
    profile_count: int
    rejection_reasons: tuple[str, ...]
    proposal_policy_configured: bool = False
    proposal_attestation_id: str | None = None
    proposal_nonce_store_path: str | None = None
    no_secret_values_written: bool = True
    no_secret_values_resolved: bool = True
    no_signer_started: bool = True
    no_socket_bound: bool = True
    no_process_spawned: bool = True
    no_shell_command_executed: bool = True
    no_repo_mutation_performed: bool = True
    no_openclaw_enqueue_performed: bool = True
    no_hermes_dispatch_performed: bool = True
    no_pr_created: bool = True
    no_reward_settlement_performed: bool = True
    no_holoindex_reindex_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def reject_supply(reasons: Sequence[str]) -> SignerServiceConfigSupplyResult:
    return SignerServiceConfigSupplyResult(
        accepted=False,
        status=SIGNER_SERVICE_CONFIG_SUPPLY_REJECT,
        config_supply_receipt_id=None,
        config_path=None,
        config_digest=None,
        socket_path=None,
        principal_id=None,
        reddog_id=None,
        profile_count=0,
        rejection_reasons=dedupe_reasons(reasons),
    )


def canonical_config_digest(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def dedupe_reasons(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(value) for value in values if str(value)))


__all__ = [name for name in globals() if name.startswith("FAIL_SIGNER_CONFIG_")] + [
    "SIGNER_SERVICE_CONFIG_SCHEMA_VERSION",
    "SIGNER_SERVICE_CONFIG_SUPPLY_ACCEPT",
    "SIGNER_SERVICE_CONFIG_SUPPLY_REJECT",
    "SignerServiceConfigSupplyRequest",
    "SignerServiceConfigSupplyResult",
    "canonical_config_digest",
    "dedupe_reasons",
    "reject_supply",
]
