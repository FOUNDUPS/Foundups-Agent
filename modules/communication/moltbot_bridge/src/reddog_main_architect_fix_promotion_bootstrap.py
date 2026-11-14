"""Main-startup bridge for bounded RedDog architect FIX promotion.

The public adapter preserves the startup API while preparation and locked
execution live in cohesive bounded modules. It performs no signing, worker
spawn, shell execution, repository mutation, PR publication, or re-indexing.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Optional

from holo_index.freshness_receipt import read_git_head_sha  # noqa: F401

from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_verified_admission import (
    VerifiedRuntimeBindingCapability,
)
from modules.communication.moltbot_bridge.src.reddog_model_runtime_verifier_bootstrap import (
    ModelRuntimeVerifierConfig,
)
from modules.communication.moltbot_bridge.src.reddog_architect_fix_signed_wsp15_work_order_promotion import (
    promote_reddog_architect_fix_to_signed_wsp15_work_order,  # noqa: F401
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_runtime_wiring import (
    SignerSocketServiceRuntimeWiringConfig,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    PrincipalKeyResolver,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_owner_bootstrap import (
    verify_reddog_holoindex_owner_binding,  # noqa: F401
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_owner_replica_route import (
    resolve_query_replica_owner_route,  # noqa: F401
)


REDDOG_ARCHITECT_FIX_PROMOTION_BOOTSTRAP_APPLIED = (
    "REDDOG_ARCHITECT_FIX_PROMOTION_BOOTSTRAP_APPLIED"
)
REDDOG_ARCHITECT_FIX_PROMOTION_BOOTSTRAP_NOT_READY = (
    "REDDOG_ARCHITECT_FIX_PROMOTION_BOOTSTRAP_NOT_READY"
)


@dataclass(frozen=True)
class RedDogMainArchitectFixPromotionBootstrapResult:
    """Result returned to ``main.py`` for startup reporting."""

    accepted: bool
    status: str
    promotion_receipt_id: Optional[str]
    queue_item_id: Optional[str]
    claim_id: Optional[str]
    selected_slice: Optional[str]
    authority_profile_path: Optional[str]
    committed_revision: Optional[str]
    rejection_reasons: tuple[str, ...]
    no_signing_performed: bool = True
    no_worker_spawn_performed: bool = True
    no_worktree_created: bool = True
    no_shell_command_executed: bool = True
    no_openclaw_enqueue_performed: bool = True
    no_hermes_dispatch_performed: bool = True
    no_repo_mutation_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_pr_created: bool = True
    no_pattern_memory_write_performed: bool = True
    no_reward_settlement_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class _PromotionBootstrapInputs:
    root: Path
    runtime_root: Path
    work_state_file: Path
    output_path: Path
    determination: Mapping[str, Any]
    model_selection: Mapping[str, Any]
    model_runtime_binding: Mapping[str, Any] | None
    model_runtime_binding_verification_capability: (
        VerifiedRuntimeBindingCapability | None
    )
    memex_supply: Mapping[str, Any]
    authority_profile: Mapping[str, Any]
    holoindex_file: Path
    proposal_attestation: Mapping[str, Any]
    signer_runtime_config: SignerSocketServiceRuntimeWiringConfig | None
    principal_key_resolver: PrincipalKeyResolver | None
    revoked_key_epochs: frozenset[str]
    worker_id: str
    now_iso: str
    promotion_claim_fence_executor: Callable | None
    environment: Mapping[str, str]


def run_reddog_main_architect_fix_promotion_bootstrap(
    *,
    repo_root: Path | str,
    runtime_root: Path | str | None,
    work_state_path: Path | str | None,
    architect_determination_path: Path | str | None,
    model_selection_receipt_path: Path | str | None,
    memex_supply_receipt_path: Path | str | None,
    authority_profile_source_path: Path | str | None,
    authority_profile_output_path: Path | str | None,
    holoindex_receipt_path: Path | str | None,
    model_runtime_binding_receipt_path: Path | str | None = None,
    model_runtime_verifier_config: ModelRuntimeVerifierConfig
    | Mapping[str, Any]
    | None = None,
    model_runtime_binding_verification_capability: VerifiedRuntimeBindingCapability
    | None = None,
    proposal_authenticity_attestation: Mapping[str, Any] | None = None,
    signer_runtime_config: SignerSocketServiceRuntimeWiringConfig | None = None,
    principal_key_resolver: PrincipalKeyResolver | None = None,
    current_proposal_revoked_key_epochs: frozenset[str] = frozenset(),
    promotion_claim_fence_executor: Callable | None = None,
    worker_id: str = "reddog-main-architect-fix-promotion",
    now_iso: str | None = None,
    environment: Mapping[str, str] | None = None,
) -> RedDogMainArchitectFixPromotionBootstrapResult:
    """Validate and promote one backend architect FIX determination."""

    from modules.communication.moltbot_bridge.src.reddog_main_architect_fix_promotion_preparation import (
        run_promotion_bootstrap_request,
    )

    return run_promotion_bootstrap_request(locals())


def _not_ready(reasons: tuple[str, ...] | list[str]):
    return RedDogMainArchitectFixPromotionBootstrapResult(
        accepted=False,
        status=REDDOG_ARCHITECT_FIX_PROMOTION_BOOTSTRAP_NOT_READY,
        promotion_receipt_id=None,
        queue_item_id=None,
        claim_id=None,
        selected_slice=None,
        authority_profile_path=None,
        committed_revision=None,
        rejection_reasons=tuple(
            dict.fromkeys(str(reason) for reason in reasons if str(reason))
        ),
    )


__all__ = [
    "REDDOG_ARCHITECT_FIX_PROMOTION_BOOTSTRAP_APPLIED",
    "REDDOG_ARCHITECT_FIX_PROMOTION_BOOTSTRAP_NOT_READY",
    "RedDogMainArchitectFixPromotionBootstrapResult",
    "run_reddog_main_architect_fix_promotion_bootstrap",
]
