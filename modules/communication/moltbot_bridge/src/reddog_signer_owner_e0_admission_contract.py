"""Types and statuses for owner-controlled signer E0 admission."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

ADMISSION_ACCEPT = "SIGNER_OWNER_E0_ADMISSION_ACCEPT"
ADMISSION_REJECT = "SIGNER_OWNER_E0_ADMISSION_REJECT"
FAIL_ADMISSION_INPUT = "signer_owner_e0_admission_input_invalid"
FAIL_ADMISSION_POLICY = "signer_owner_e0_policy_invalid"


@dataclass(frozen=True)
class OwnerControlledE0ConsumptionReceipt:
    policy_id: str
    manifest_id: str
    artifact_generation_digest: str
    config_digest: str
    target_signer_agent_id: str
    target_signer_profile_id: str
    generation_fenced_during_validation: bool = True
    no_composition_authority_released: bool = True


@dataclass(frozen=True)
class OwnerControlledE0AdmissionResult:
    accepted: bool
    status: str
    rejection_reasons: tuple[str, ...]
    policy_id: str = ""
    capability: object | None = None
    no_secret_resolution_performed: bool = True
    no_socket_bound: bool = True
    no_signer_started: bool = True
    no_repo_mutation_performed: bool = True


@dataclass(frozen=True)
class IssuedAdmission:
    owner_config_path: Path
    policy: Mapping[str, Any]


__all__ = [
    "ADMISSION_ACCEPT",
    "ADMISSION_REJECT",
    "FAIL_ADMISSION_INPUT",
    "FAIL_ADMISSION_POLICY",
    "IssuedAdmission",
    "OwnerControlledE0AdmissionResult",
    "OwnerControlledE0ConsumptionReceipt",
]
