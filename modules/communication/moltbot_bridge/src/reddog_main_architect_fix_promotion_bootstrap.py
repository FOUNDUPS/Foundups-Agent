"""Main-startup bridge for RedDog architect FIX promotion.

Slice: REDDOG_ARCHITECT_FIX_PROMOTION_MAIN_PREFLIGHT_PHASE1

This adapter consumes already-produced backend architect, model-selection,
Memex-supply, and authority-profile receipts from outside-repo runtime files.
It promotes one FIX determination into the authoritative work-state queue and
writes the promoted authority profile consumed by the resident serial loop.

It does not sign authority, spawn workers, create worktrees, run shell commands,
enqueue OpenClaw, dispatch Hermes, publish PRs, admit PatternMemory, settle
rewards, mutate source files, or re-index HoloIndex.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Optional

from holo_index.freshness_receipt import load_freshness_receipt, read_git_head_sha
from holo_index.query_receipt import generation_binding_from_receipt

from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_verified_admission import (
    VerifiedRuntimeBindingCapability,
)
from modules.communication.moltbot_bridge.src.reddog_model_runtime_verifier_bootstrap import (
    ModelRuntimeVerifierConfig,
    build_model_runtime_verifier,
)
from modules.communication.moltbot_bridge.src.reddog_architect_fix_signed_wsp15_work_order_promotion import (
    ARCHITECT_FIX_WSP15_PROMOTION_ACCEPT,
    promote_reddog_architect_fix_to_signed_wsp15_work_order,
)
from modules.communication.moltbot_bridge.src.reddog_architect_fix_promotion_publication import (
    AtomicArchitectFixPromotionPublisher,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_runtime_wiring import (
    SignerSocketServiceRuntimeWiringConfig,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    PrincipalKeyResolver,
)
from modules.communication.moltbot_bridge.src.reddog_authority_runtime_store import (
    AtomicJsonAuthorityRuntimeStore,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    runtime_operation_lock,
    validate_runtime_root_path,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_owner_bootstrap import (
    verify_reddog_holoindex_owner_binding,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_owner_replica_route import (
    resolve_query_replica_owner_route,
)


REDDOG_ARCHITECT_FIX_PROMOTION_BOOTSTRAP_APPLIED = (
    "REDDOG_ARCHITECT_FIX_PROMOTION_BOOTSTRAP_APPLIED"
)
_CONSUMED_ARTIFACT_PATH_ARGUMENTS = (
    "work_state_path",
    "architect_determination_path",
    "model_selection_receipt_path",
    "model_runtime_binding_receipt_path",
    "memex_supply_receipt_path",
    "authority_profile_source_path",
    "holoindex_receipt_path",
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
    model_runtime_verifier_config: ModelRuntimeVerifierConfig | Mapping[str, Any] | None = None,
    model_runtime_binding_verification_capability: VerifiedRuntimeBindingCapability | None = None,
    proposal_authenticity_attestation: Mapping[str, Any] | None = None,
    signer_runtime_config: SignerSocketServiceRuntimeWiringConfig | None = None,
    principal_key_resolver: PrincipalKeyResolver | None = None,
    current_proposal_revoked_key_epochs: frozenset[str] = frozenset(),
    promotion_claim_fence_executor: Callable | None = None,
    worker_id: str = "reddog-main-architect-fix-promotion",
    now_iso: str | None = None,
    environment: Mapping[str, str] | None = None,
) -> RedDogMainArchitectFixPromotionBootstrapResult:
    """Promote one backend architect FIX determination into the resident queue."""
    root = Path(repo_root).resolve()
    reasons: list[str] = []
    try:
        trusted_runtime_root = validate_runtime_root_path(
            runtime_root,
            repo_root=root,
        )
    except Exception:
        return _not_ready(("resident_runtime_root_invalid",))
    work_state_file, work_state_reasons = _resolve_existing_file_outside_repo(
        root,
        work_state_path,
        missing_reason="missing_authoritative_work_state_path",
        inside_reason="work_state_path_inside_repo",
    )
    reasons.extend(work_state_reasons)
    determination, determination_reasons = _read_json_outside_repo(
        root,
        architect_determination_path,
        missing_reason="missing_architect_determination_path",
        inside_reason="architect_determination_path_inside_repo",
        unreadable_reason="malformed_architect_determination",
    )
    reasons.extend(determination_reasons)
    model_selection, model_runtime_binding, runtime_capability, model_reasons = (
        _promotion_model_runtime_inputs(
            root, trusted_runtime_root, model_selection_receipt_path,
            model_runtime_binding_receipt_path, model_runtime_verifier_config,
            model_runtime_binding_verification_capability, now_iso,
        )
    )
    reasons.extend(model_reasons)
    memex_supply, memex_reasons = _read_json_outside_repo(
        root,
        memex_supply_receipt_path,
        missing_reason="missing_memex_supply_receipt_path",
        inside_reason="memex_supply_receipt_path_inside_repo",
        unreadable_reason="malformed_memex_supply_receipt",
    )
    reasons.extend(memex_reasons)
    authority_profile, profile_reasons = _read_json_outside_repo(
        root,
        authority_profile_source_path,
        missing_reason="missing_authority_profile_source_path",
        inside_reason="authority_profile_source_path_inside_repo",
        unreadable_reason="malformed_authority_profile_source",
    )
    reasons.extend(profile_reasons)
    holoindex_file, holoindex_reasons = _resolve_existing_file_outside_repo(
        root,
        holoindex_receipt_path,
        missing_reason="missing_holoindex_freshness_receipt_path",
        inside_reason="holoindex_freshness_receipt_path_inside_repo",
    )
    reasons.extend(holoindex_reasons)
    output_path, output_reasons = _resolve_output_outside_repo(
        root,
        authority_profile_output_path,
        missing_reason="missing_authority_profile_output_path",
        inside_reason="authority_profile_output_path_inside_repo",
    )
    reasons.extend(output_reasons)
    reasons.extend(_bootstrap_path_reasons(
        root, trusted_runtime_root, work_state_file, output_path, locals()
    ))
    if reasons:
        return _not_ready(reasons)
    runtime_capability, found = _resolve_runtime_capability(
        root, trusted_runtime_root, model_runtime_binding, model_selection,
        runtime_capability, model_runtime_verifier_config, now_iso,
    )
    if found:
        return _not_ready(found)
    assert work_state_file is not None
    assert output_path is not None
    assert determination is not None
    assert model_selection is not None
    assert memex_supply is not None
    assert authority_profile is not None
    assert holoindex_file is not None

    output_probe_reasons = _probe_atomic_output(output_path)
    if output_probe_reasons:
        return _not_ready(output_probe_reasons)
    return _run_locked_promotion(
        _PromotionBootstrapInputs(
            root=root,
            runtime_root=trusted_runtime_root,
            work_state_file=work_state_file,
            output_path=output_path,
            determination=determination,
            model_selection=model_selection,
            model_runtime_binding=model_runtime_binding,
            model_runtime_binding_verification_capability=runtime_capability,
            memex_supply=memex_supply,
            authority_profile=authority_profile,
            holoindex_file=holoindex_file,
            proposal_attestation=proposal_authenticity_attestation or {},
            signer_runtime_config=signer_runtime_config,
            principal_key_resolver=principal_key_resolver,
            revoked_key_epochs=frozenset(current_proposal_revoked_key_epochs),
            worker_id=worker_id,
            now_iso=now_iso or datetime.now(timezone.utc).isoformat(),
            promotion_claim_fence_executor=promotion_claim_fence_executor,
            environment=dict(os.environ if environment is None else environment),
        )
    )


def _run_locked_promotion(
    inputs: _PromotionBootstrapInputs,
) -> RedDogMainArchitectFixPromotionBootstrapResult:
    with runtime_operation_lock(str(inputs.root) + ".architect-fix-promotion"):
        try:
            receipt = load_freshness_receipt(inputs.holoindex_file)
        except Exception:
            return _not_ready(("malformed_holoindex_freshness_receipt",))
        repo_head = read_git_head_sha(inputs.root)
        owner = generation_binding_from_receipt(
            receipt, receipt_path=inputs.holoindex_file
        )
        try:
            route = resolve_query_replica_owner_route(
                canonical_repo_root=inputs.root,
                canonical_ssd_path=receipt.ssd_path,
                environment=inputs.environment,
            )
        except Exception:
            return _not_ready(("holoindex_query_replica_route_not_current",))
        if not verify_reddog_holoindex_owner_binding(
            repo_root=inputs.root,
            expected_repo_head_sha=repo_head,
            expected_generation_id=receipt.generation_id,
            expected_receipt_digest=str(
                owner.get("freshness_receipt_digest") or ""
            ),
            query_replica_route=route,
        ):
            return _not_ready(("holoindex_owner_binding_not_current",))
        return _run_profile_transaction(inputs, repo_head, receipt)


def _run_profile_transaction(inputs, repo_head, holoindex_receipt):
    store = AtomicJsonAuthorityRuntimeStore(
        inputs.work_state_file,
        allowed_root=inputs.runtime_root,
        repo_root=inputs.root,
    )
    publisher = AtomicArchitectFixPromotionPublisher(
        repo_root=inputs.root,
        runtime_root=inputs.runtime_root,
        authority_profile_path=inputs.output_path,
        work_state_store=store,
    )
    def operation(fence=None):
        return _recover_and_promote(
            inputs,
            store,
            publisher,
            repo_head,
            holoindex_receipt,
            fence,
        )
    try:
        result = (
            inputs.promotion_claim_fence_executor(operation)
            if inputs.promotion_claim_fence_executor
            else operation()
        )
    except Exception as exc:
        return _not_ready(
            ("architect_fix_promotion_claim_fence_rejected", exc.__class__.__name__)
        )
    if not result.accepted:
        return _not_ready(
            list(
                result.rejection_reasons
                or ("architect_fix_promotion_rejected",)
            )
        )
    return _applied_result(result, inputs.output_path)


def _recover_and_promote(inputs, store, publisher, repo_head, holo_receipt, fence):
    try:
        publisher.recover()
    except Exception as exc:
        return _not_ready(
            ("architect_fix_publication_recovery_failed", exc.__class__.__name__)
        )
    return _promote_with_fence(
        inputs,
        store,
        publisher,
        repo_head,
        holo_receipt,
        fence,
    )


def _promote_with_fence(inputs, store, publisher, repo_head, holo_receipt, fence):
    return promote_reddog_architect_fix_to_signed_wsp15_work_order(
        architect_determination=inputs.determination,
        work_state_store=store,
        authority_profile=inputs.authority_profile,
        model_selection_receipt=inputs.model_selection,
        model_runtime_binding_receipt=inputs.model_runtime_binding,
        model_runtime_binding_verification_capability=(
            inputs.model_runtime_binding_verification_capability
        ),
        memex_supply_receipt=inputs.memex_supply,
        proposal_authenticity_attestation=inputs.proposal_attestation,
        signer_runtime_config=inputs.signer_runtime_config,
        principal_key_resolver=inputs.principal_key_resolver,
        current_proposal_revoked_key_epochs=inputs.revoked_key_epochs,
        worker_id=inputs.worker_id,
        now_iso=inputs.now_iso,
        current_repo_head_sha=repo_head,
        current_holoindex_receipt=holo_receipt,
        authority_profile_publication_publisher=publisher.publish,
        agentdb_fix_promotion_claim_fence=fence,
    )


def _applied_result(result, output_path):
    if (
        result.status != ARCHITECT_FIX_WSP15_PROMOTION_ACCEPT
        or result.authority_profile is None
        or result.receipt is None
    ):
        return _not_ready(("architect_fix_promotion_missing_profile",))
    return RedDogMainArchitectFixPromotionBootstrapResult(
        accepted=True,
        status=REDDOG_ARCHITECT_FIX_PROMOTION_BOOTSTRAP_APPLIED,
        promotion_receipt_id=result.receipt.promotion_receipt_id,
        queue_item_id=result.receipt.queue_item_id,
        claim_id=result.receipt.claim_id,
        selected_slice=result.receipt.selected_slice,
        authority_profile_path=str(output_path),
        committed_revision=result.receipt.committed_revision,
        rejection_reasons=(),
    )


def _promotion_model_runtime_inputs(
    root: Path,
    runtime_root: Path,
    selection_path: Path | str | None,
    binding_path: Path | str | None,
    config: ModelRuntimeVerifierConfig | Mapping[str, Any] | None,
    injected: VerifiedRuntimeBindingCapability | None,
    now_iso: str | None,
) -> tuple[
    Mapping[str, Any] | None,
    Mapping[str, Any] | None,
    VerifiedRuntimeBindingCapability | None,
    list[str],
]:
    selection, reasons = _read_json_outside_repo(
        root,
        selection_path,
        missing_reason="missing_model_selection_receipt_path",
        inside_reason="model_selection_receipt_path_inside_repo",
        unreadable_reason="malformed_model_selection_receipt",
    )
    binding, found = _read_optional_json_outside_repo(
        root,
        binding_path,
        inside_reason="model_runtime_binding_receipt_path_inside_repo",
        unreadable_reason="malformed_model_runtime_binding_receipt",
    )
    reasons.extend(found)
    return selection, binding, injected, list(dict.fromkeys(reasons))


def _resolve_runtime_capability(
    root: Path,
    runtime_root: Path,
    binding: Mapping[str, Any] | None,
    selection: Mapping[str, Any] | None,
    injected: VerifiedRuntimeBindingCapability | None,
    config: ModelRuntimeVerifierConfig | Mapping[str, Any] | None,
    now_iso: str | None,
) -> tuple[VerifiedRuntimeBindingCapability | None, tuple[str, ...]]:
    if binding is None or injected is not None:
        return injected, ()
    verifier, found = build_model_runtime_verifier(
        repo_root=root,
        runtime_root=runtime_root,
        config=config,
        trusted_now=lambda: int(
            datetime.fromisoformat(
                (now_iso or datetime.now(timezone.utc).isoformat()).replace(
                    "Z", "+00:00"
                )
            ).timestamp()
        ),
        artifact_generator=True,
    )
    reasons = list(found)
    if verifier is None or selection is None:
        reasons.append("model_runtime_binding_signed_evidence_invalid")
        return None, tuple(dict.fromkeys(reasons))
    try:
        capability = verifier.verify(binding=binding, selection=selection)
    except Exception:
        reasons.append("model_runtime_binding_signed_evidence_invalid")
        capability = None
    return capability, tuple(dict.fromkeys(reasons))


def _read_json_outside_repo(
    repo_root: Path,
    value: Path | str | None,
    *,
    missing_reason: str,
    inside_reason: str,
    unreadable_reason: str,
) -> tuple[Optional[Mapping[str, Any]], list[str]]:
    path, reasons = _resolve_existing_file_outside_repo(
        repo_root,
        value,
        missing_reason=missing_reason,
        inside_reason=inside_reason,
    )
    if reasons:
        return None, reasons
    assert path is not None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None, [unreadable_reason]
    if not isinstance(payload, Mapping):
        return None, [unreadable_reason]
    return payload, []


def _read_optional_json_outside_repo(
    repo_root: Path,
    value: Path | str | None,
    *,
    inside_reason: str,
    unreadable_reason: str,
) -> tuple[Optional[Mapping[str, Any]], list[str]]:
    if not value:
        return None, []
    path, reasons = _resolve_existing_file_outside_repo(
        repo_root,
        value,
        missing_reason=unreadable_reason,
        inside_reason=inside_reason,
    )
    if reasons:
        return None, reasons
    assert path is not None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None, [unreadable_reason]
    if not isinstance(payload, Mapping):
        return None, [unreadable_reason]
    return payload, []


def _resolve_existing_file_outside_repo(
    repo_root: Path,
    value: Path | str | None,
    *,
    missing_reason: str,
    inside_reason: str,
) -> tuple[Optional[Path], list[str]]:
    if not value:
        return None, [missing_reason]
    path = Path(value)
    if not path.is_absolute():
        path = (repo_root / path).resolve()
    else:
        path = path.resolve()
    if _is_inside(path, repo_root):
        return None, [inside_reason]
    if not path.exists() or not path.is_file():
        return None, [missing_reason]
    return path, []


def _resolve_output_outside_repo(
    repo_root: Path,
    value: Path | str | None,
    *,
    missing_reason: str,
    inside_reason: str,
) -> tuple[Optional[Path], list[str]]:
    if not value:
        return None, [missing_reason]
    path = Path(value)
    if not path.is_absolute():
        path = (repo_root / path).resolve()
    else:
        path = path.resolve()
    if _is_inside(path, repo_root):
        return None, [inside_reason]
    return path, []


def _output_alias_reasons(
    repo_root: Path,
    output_path: Path | None,
    consumed_paths: tuple[Path | str | None, ...],
) -> list[str]:
    if output_path is None:
        return []
    for value in consumed_paths:
        if not value:
            continue
        path = Path(value)
        resolved = (
            (repo_root / path).resolve()
            if not path.is_absolute()
            else path.resolve()
        )
        if resolved == output_path:
            return ["authority_profile_output_aliases_consumed_artifact"]
    return []


def _bootstrap_path_reasons(
    repo_root: Path,
    runtime_root: Path,
    work_state_path: Path | None,
    output_path: Path | None,
    arguments: Mapping[str, Any],
) -> list[str]:
    consumed = tuple(
        arguments.get(name) for name in _CONSUMED_ARTIFACT_PATH_ARGUMENTS
    )
    reasons = _output_alias_reasons(repo_root, output_path, consumed)
    for label, path in (
        ("work_state", work_state_path),
        ("authority_profile_output", output_path),
    ):
        if path is not None and not _is_inside(path, runtime_root):
            reasons.append(f"{label}_path_outside_resident_runtime_root")
    return reasons


def _probe_atomic_output(path: Path) -> list[str]:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".probe", dir=str(path.parent))
        os.close(fd)
        os.replace(tmp_name, tmp_name)
        os.unlink(tmp_name)
    except Exception:
        return ["authority_profile_output_not_writable"]
    return []


def _not_ready(reasons: tuple[str, ...] | list[str]) -> RedDogMainArchitectFixPromotionBootstrapResult:
    return RedDogMainArchitectFixPromotionBootstrapResult(
        accepted=False,
        status=REDDOG_ARCHITECT_FIX_PROMOTION_BOOTSTRAP_NOT_READY,
        promotion_receipt_id=None,
        queue_item_id=None,
        claim_id=None,
        selected_slice=None,
        authority_profile_path=None,
        committed_revision=None,
        rejection_reasons=tuple(dict.fromkeys(str(reason) for reason in reasons if str(reason))),
    )


def _is_inside(child: Path, parent: Path) -> bool:
    child_r = child.resolve()
    parent_r = parent.resolve()
    return child_r == parent_r or parent_r in child_r.parents


__all__ = [
    "REDDOG_ARCHITECT_FIX_PROMOTION_BOOTSTRAP_APPLIED",
    "REDDOG_ARCHITECT_FIX_PROMOTION_BOOTSTRAP_NOT_READY",
    "RedDogMainArchitectFixPromotionBootstrapResult",
    "run_reddog_main_architect_fix_promotion_bootstrap",
]
