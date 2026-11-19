"""Bounded process-isolation admission for the signer service bootstrap."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass, replace
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional, Protocol

from modules.communication.moltbot_bridge.src.reddog_signer_process_isolation_gate import (
    SignerProcessIsolationReceipt,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_peer_credential_attestor import (
    PeerCredentialPolicy,
    rehydrate_peer_credential_policy,
)


if TYPE_CHECKING:
    from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_runtime_bootstrap import RuntimeBootstrapRequest


SIGNER_SOCKET_RUNTIME_BOOTSTRAP_SERVED = "SIGNER_SOCKET_RUNTIME_BOOTSTRAP_SERVED"
SIGNER_SOCKET_RUNTIME_BOOTSTRAP_REJECT = "SIGNER_SOCKET_RUNTIME_BOOTSTRAP_REJECT"

@dataclass(frozen=True)
class SignerSocketServiceGrantAdmission:
    """Dependencies to verify against current owner state, never authority alone."""
    owner_config_path: Path | str
    owner_policy: Any
    replay_store: Any
    revocation_oracle: Any


@dataclass(frozen=True)
class SignerSocketServiceRuntimeDependencies:
    """Deferred dependencies, not authority; existing use-time gates still apply."""

    resolver: Any
    principal_key_resolver: Any
    proposal_replay_high_water_store: Any
    secret_grant_admission: SignerSocketServiceGrantAdmission


def _supply_isolated_dependencies(request: RuntimeBootstrapRequest) -> RuntimeBootstrapRequest:
    """Consume one supply only after config/isolation checks; never infer grants."""
    if request.process_isolation_required is not True or any(
        item is not None for item in (
            request.resolver, request.resolver_factory, request.principal_key_resolver,
            request.proposal_replay_high_water_store, request.secret_grant_admission,
        )
    ):
        raise ValueError("signer_runtime_dependency_supply_conflict")
    supplied = request.runtime_dependencies_supplier()
    if (
        type(supplied) is not SignerSocketServiceRuntimeDependencies
        or not callable(getattr(supplied.resolver, "resolve", None))
        or not callable(getattr(supplied.principal_key_resolver, "resolve", None))
        or type(supplied.secret_grant_admission) is not SignerSocketServiceGrantAdmission
    ):
        raise ValueError("signer_runtime_dependency_supply_invalid")
    return replace(
        request, resolver=supplied.resolver,
        principal_key_resolver=supplied.principal_key_resolver,
        proposal_replay_high_water_store=supplied.proposal_replay_high_water_store,
        secret_grant_admission=supplied.secret_grant_admission,
        runtime_dependencies_supplier=None,
    )


@contextmanager
def lease_signer_socket_service_grant_admission(config: Any, admission: Any):
    """Fence assembly or one protected callback; never enclose a root RPC."""
    from modules.communication.moltbot_bridge.src import reddog_signer_owner_e0_current_selection as owner_source
    from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_runtime_bootstrap import _attach_peer_binding
    from modules.communication.moltbot_bridge.src.reddog_current_generation_manifest_launch_selection import _legacy_launch_values

    if type(admission) is not SignerSocketServiceGrantAdmission:
        raise ValueError("signer_grant_admission_invalid")
    with owner_source.lease_validated_owner_e0_current_admission(
        owner_config_path=admission.owner_config_path,
        repo_root=Path(config.repo_root).resolve(), policy=admission.owner_policy,
    ) as owner:
        selected = owner.selection
        attached = _attach_peer_binding(
            owner.config, Path(config.repo_root).resolve(),
            Path(selected["config_path"]), selected["config_digest"],
            selected["run_packet_path"], None, admission.owner_config_path,
            _legacy_launch_values(selected), selected["config_raw_digest"],
        )
        if attached is None or json.dumps(
            asdict(config), sort_keys=True, default=str, allow_nan=False,
        ) != json.dumps(
            asdict(attached), sort_keys=True, default=str, allow_nan=False,
        ):
            raise ValueError("signer_grant_selected_config_mismatch")
        yield attached, owner

class ProcessIsolationGate(Protocol):
    def __call__(
        self,
        policy: PeerCredentialPolicy,
        *,
        expected_signer_uid: int,
        expected_signer_gid: int,
    ) -> SignerProcessIsolationReceipt: ...


@dataclass(frozen=True)
class SignerSocketServiceRuntimeBootstrapResult:
    accepted: bool
    status: str
    rejection_reasons: tuple[str, ...]
    config_path: Optional[str] = None
    config_digest: Optional[str] = None
    runtime_result: Optional[dict[str, Any]] = None
    process_isolation_receipt: Optional[dict[str, Any]] = None
    no_env_parsed: bool = True
    no_process_spawned: bool = True
    no_runtime_secret_file_loaded: bool | None = True
    no_repo_mutation_performed: bool = True
    no_openclaw_enqueue_performed: bool = True
    no_hermes_dispatch_performed: bool = True
    no_pr_created: bool = True
    no_reward_settlement_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_secret_values_returned: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def require_process_isolation(
    config: Any,
    *,
    required: bool,
    gate: ProcessIsolationGate,
    expected_signer_uid: int | None,
    expected_signer_gid: int | None,
) -> SignerProcessIsolationReceipt | None:
    if not required:
        return None
    policy = rehydrate_peer_credential_policy(config.peer_policy)
    if (
        policy is None
        or type(expected_signer_uid) is not int
        or type(expected_signer_gid) is not int
    ):
        return None
    try:
        result = gate(
            policy,
            expected_signer_uid=expected_signer_uid,
            expected_signer_gid=expected_signer_gid,
        )
    except Exception:
        return None
    return result if isinstance(result, SignerProcessIsolationReceipt) else None


def bootstrap_runtime_result(
    runtime: Any,
    *,
    path: Path,
    digest: str,
    process_isolation_receipt: dict[str, Any] | None,
) -> SignerSocketServiceRuntimeBootstrapResult:
    runtime_receipt = runtime.to_dict()
    if runtime.accepted is not True:
        return reject_bootstrap(
            "FAIL_SIGNER_BOOTSTRAP_RUNTIME_REJECTED",
            *runtime.rejection_reasons,
            config_path=str(path),
            config_digest=digest,
            runtime_result=runtime_receipt,
            process_isolation_receipt=process_isolation_receipt,
        )
    return SignerSocketServiceRuntimeBootstrapResult(
        accepted=True,
        status=SIGNER_SOCKET_RUNTIME_BOOTSTRAP_SERVED,
        rejection_reasons=(),
        config_path=str(path),
        config_digest=digest,
        runtime_result=runtime_receipt,
        process_isolation_receipt=process_isolation_receipt,
    )


def reject_bootstrap(
    *reasons: str,
    config_path: Optional[str] = None,
    config_digest: Optional[str] = None,
    runtime_result: Optional[dict[str, Any]] = None,
    process_isolation_receipt: Optional[dict[str, Any]] = None,
) -> SignerSocketServiceRuntimeBootstrapResult:
    return SignerSocketServiceRuntimeBootstrapResult(
        accepted=False,
        status=SIGNER_SOCKET_RUNTIME_BOOTSTRAP_REJECT,
        rejection_reasons=tuple(dict.fromkeys(reason for reason in reasons if reason)),
        config_path=config_path,
        config_digest=config_digest,
        runtime_result=runtime_result,
        process_isolation_receipt=process_isolation_receipt,
    )


__all__ = [
    "ProcessIsolationGate",
    "SignerSocketServiceGrantAdmission",
    "SignerSocketServiceRuntimeDependencies",
    "SIGNER_SOCKET_RUNTIME_BOOTSTRAP_REJECT",
    "SIGNER_SOCKET_RUNTIME_BOOTSTRAP_SERVED",
    "SignerSocketServiceRuntimeBootstrapResult",
    "bootstrap_runtime_result",
    "reject_bootstrap",
    "require_process_isolation",
]
