"""Public facade for signer socket service config materialization.

The bounded implementation lives in the adjacent contract, composition, and
materialization modules. This facade preserves the established import and
call surface while keeping secret resolution, signer startup, command
execution, and repository mutation outside the supplier.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from modules.communication.moltbot_bridge.src.reddog_architect_proposal_authenticity import (
    ArchitectProposalPolicyAuthorization,
    ArchitectProposalSignerPolicy,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_config_composition import (
    config_mapping,
    peer_policy,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_config_materialization import (
    materialize_signer_service_config,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_config_supply_contract import (
    FAIL_SIGNER_CONFIG_ARCHITECT_PUBLICATION_INVALID as FAIL_SIGNER_CONFIG_ARCHITECT_PUBLICATION_INVALID,
    FAIL_SIGNER_CONFIG_AUTHORITY_PROFILE_INVALID as FAIL_SIGNER_CONFIG_AUTHORITY_PROFILE_INVALID,
    FAIL_SIGNER_CONFIG_CONTROL_ANCHOR_PATH_INVALID as FAIL_SIGNER_CONFIG_CONTROL_ANCHOR_PATH_INVALID,
    FAIL_SIGNER_CONFIG_LIMITS_INVALID as FAIL_SIGNER_CONFIG_LIMITS_INVALID,
    FAIL_SIGNER_CONFIG_OP_REF_INVALID as FAIL_SIGNER_CONFIG_OP_REF_INVALID,
    FAIL_SIGNER_CONFIG_OP_REF_REUSED as FAIL_SIGNER_CONFIG_OP_REF_REUSED,
    FAIL_SIGNER_CONFIG_OUTPUT_PATH_INVALID as FAIL_SIGNER_CONFIG_OUTPUT_PATH_INVALID,
    FAIL_SIGNER_CONFIG_PEER_POLICY_INVALID as FAIL_SIGNER_CONFIG_PEER_POLICY_INVALID,
    FAIL_SIGNER_CONFIG_PROPOSAL_NONCE_PATH_INVALID as FAIL_SIGNER_CONFIG_PROPOSAL_NONCE_PATH_INVALID,
    FAIL_SIGNER_CONFIG_PROPOSAL_POLICY_AUTHORIZATION_INVALID as FAIL_SIGNER_CONFIG_PROPOSAL_POLICY_AUTHORIZATION_INVALID,
    FAIL_SIGNER_CONFIG_PROPOSAL_POLICY_INVALID as FAIL_SIGNER_CONFIG_PROPOSAL_POLICY_INVALID,
    FAIL_SIGNER_CONFIG_SOCKET_PATH_INVALID as FAIL_SIGNER_CONFIG_SOCKET_PATH_INVALID,
    FAIL_SIGNER_CONFIG_WRITE_FAILED as FAIL_SIGNER_CONFIG_WRITE_FAILED,
    SIGNER_SERVICE_CONFIG_SCHEMA_VERSION as SIGNER_SERVICE_CONFIG_SCHEMA_VERSION,
    SIGNER_SERVICE_CONFIG_SUPPLY_ACCEPT as SIGNER_SERVICE_CONFIG_SUPPLY_ACCEPT,
    SIGNER_SERVICE_CONFIG_SUPPLY_REJECT as SIGNER_SERVICE_CONFIG_SUPPLY_REJECT,
    SignerServiceConfigSupplyRequest,
    SignerServiceConfigSupplyResult as SignerServiceConfigSupplyResult,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    PrincipalKeyResolver,
)


_config = config_mapping
_peer_policy = peer_policy


def run_reddog_signer_socket_service_config_supply(
    *,
    repo_root: Path | str,
    runtime_root: Path | str,
    signer_runtime_root: Path | str,
    authority_profile: Mapping[str, Any] | None,
    authoritative_work_state_path: Path | str | None,
    output_path: Path | str | None,
    socket_path: Path | str | None,
    principal_signing_key_ref: str,
    principal_audit_mac_key_ref: str,
    reddog_signing_key_ref: str,
    reddog_audit_mac_key_ref: str,
    peer_uid_to_principal: Mapping[int | str, str],
    allowed_gids: Sequence[int | str] = (),
    max_requests: int = 16,
    timeout_s: float = 5.0,
    max_request_bytes: int | None = None,
    max_response_bytes: int = 16384,
    principal_signer_agent_id: str = "signer:principal",
    reddog_signer_agent_id: str = "signer:reddog",
    control_loop_anchor_path: Path | str | None = None,
    proposal_authority_policy: ArchitectProposalSignerPolicy | None = None,
    proposal_policy_authorization: (
        ArchitectProposalPolicyAuthorization | Mapping[str, Any] | None
    ) = None,
    proposal_nonce_store_path: Path | str | None = None,
    proposal_replay_high_water_store_id: str | None = None,
    proposal_replay_high_water_durability_receipt_id: str | None = None,
    now_epoch: int | None = None,
    principal_key_resolver: PrincipalKeyResolver | None = None,
    authoritative_work_state: Mapping[str, Any] | None = None,
) -> SignerServiceConfigSupplyResult:
    """Write one signer CLI config from existing authority artifacts."""

    values = locals()
    if max_request_bytes is None:
        values["max_request_bytes"] = (
            16384 if proposal_authority_policy is not None else 163840
        )
    return materialize_signer_service_config(SignerServiceConfigSupplyRequest(**values))


__all__ = [name for name in globals() if name.startswith("FAIL_SIGNER_CONFIG_")] + [
    "SIGNER_SERVICE_CONFIG_SCHEMA_VERSION",
    "SIGNER_SERVICE_CONFIG_SUPPLY_ACCEPT",
    "SIGNER_SERVICE_CONFIG_SUPPLY_REJECT",
    "SignerServiceConfigSupplyResult",
    "run_reddog_signer_socket_service_config_supply",
]
