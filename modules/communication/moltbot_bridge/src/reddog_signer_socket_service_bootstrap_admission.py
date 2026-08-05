"""Bounded process-isolation admission for the signer service bootstrap."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional, Protocol

from modules.communication.moltbot_bridge.src.reddog_signer_process_isolation_gate import (
    SignerProcessIsolationReceipt,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_peer_credential_attestor import (
    PeerCredentialPolicy,
    rehydrate_peer_credential_policy,
)


SIGNER_SOCKET_RUNTIME_BOOTSTRAP_SERVED = "SIGNER_SOCKET_RUNTIME_BOOTSTRAP_SERVED"
SIGNER_SOCKET_RUNTIME_BOOTSTRAP_REJECT = "SIGNER_SOCKET_RUNTIME_BOOTSTRAP_REJECT"

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
    no_runtime_secret_file_loaded: bool = True
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
    "SIGNER_SOCKET_RUNTIME_BOOTSTRAP_REJECT",
    "SIGNER_SOCKET_RUNTIME_BOOTSTRAP_SERVED",
    "SignerSocketServiceRuntimeBootstrapResult",
    "bootstrap_runtime_result",
    "reject_bootstrap",
    "require_process_isolation",
]
