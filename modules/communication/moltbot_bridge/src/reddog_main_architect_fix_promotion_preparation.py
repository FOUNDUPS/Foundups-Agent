"""Bounded input preparation for architect FIX promotion bootstrap."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional

from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_verified_admission import (
    VerifiedRuntimeBindingCapability,
)
from modules.communication.moltbot_bridge.src.reddog_main_architect_fix_promotion_execution import (
    run_locked_promotion,
)
from modules.communication.moltbot_bridge.src.reddog_model_runtime_verifier_bootstrap import (
    ModelRuntimeVerifierConfig,
    build_model_runtime_verifier,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    validate_runtime_root_path,
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


def run_promotion_bootstrap_request(arguments: Mapping[str, Any]):
    """Validate all immutable inputs before entering the promotion lock."""

    from modules.communication.moltbot_bridge.src.reddog_main_architect_fix_promotion_bootstrap import (
        _not_ready,
    )

    root = Path(arguments["repo_root"]).resolve()
    try:
        runtime_root = validate_runtime_root_path(
            arguments["runtime_root"], repo_root=root
        )
    except Exception:
        return _not_ready(("resident_runtime_root_invalid",))
    artifacts, reasons = _load_artifacts(root, runtime_root, arguments)
    if reasons:
        return _not_ready(reasons)
    capability, found = _resolve_runtime_capability(
        root,
        runtime_root,
        artifacts["model_runtime_binding"],
        artifacts["model_selection"],
        arguments["model_runtime_binding_verification_capability"],
        arguments["model_runtime_verifier_config"],
        arguments["now_iso"],
    )
    if found:
        return _not_ready(found)
    output_reasons = _probe_atomic_output(artifacts["output_path"])
    if output_reasons:
        return _not_ready(output_reasons)
    return run_locked_promotion(
        _build_inputs(root, runtime_root, artifacts, capability, arguments)
    )


def _load_artifacts(root: Path, runtime_root: Path, args: Mapping[str, Any]):
    artifacts, reasons = _load_receipts(root, runtime_root, args)
    paths, path_reasons = _load_profile_paths(root, args)
    artifacts.update(paths)
    reasons.extend(path_reasons)
    reasons.extend(
        _bootstrap_path_reasons(
            root,
            runtime_root,
            artifacts.get("work_state_file"),
            artifacts.get("output_path"),
            args,
        )
    )
    return artifacts, list(dict.fromkeys(reasons))


def _load_receipts(root: Path, runtime_root: Path, args: Mapping[str, Any]):
    work_state, reasons = _resolve_existing_file_outside_repo(
        root,
        args["work_state_path"],
        missing_reason="missing_authoritative_work_state_path",
        inside_reason="work_state_path_inside_repo",
    )
    determination, found = _read_json_outside_repo(
        root,
        args["architect_determination_path"],
        missing_reason="missing_architect_determination_path",
        inside_reason="architect_determination_path_inside_repo",
        unreadable_reason="malformed_architect_determination",
    )
    reasons.extend(found)
    selection, binding, capability, found = _promotion_model_runtime_inputs(
        root,
        runtime_root,
        args["model_selection_receipt_path"],
        args["model_runtime_binding_receipt_path"],
        args["model_runtime_verifier_config"],
        args["model_runtime_binding_verification_capability"],
        args["now_iso"],
    )
    reasons.extend(found)
    supply, found = _read_json_outside_repo(
        root,
        args["memex_supply_receipt_path"],
        missing_reason="missing_memex_supply_receipt_path",
        inside_reason="memex_supply_receipt_path_inside_repo",
        unreadable_reason="malformed_memex_supply_receipt",
    )
    reasons.extend(found)
    return {
        "work_state_file": work_state,
        "determination": determination,
        "model_selection": selection,
        "model_runtime_binding": binding,
        "runtime_capability": capability,
        "memex_supply": supply,
    }, reasons


def _load_profile_paths(root: Path, args: Mapping[str, Any]):
    profile, reasons = _read_json_outside_repo(
        root,
        args["authority_profile_source_path"],
        missing_reason="missing_authority_profile_source_path",
        inside_reason="authority_profile_source_path_inside_repo",
        unreadable_reason="malformed_authority_profile_source",
    )
    holoindex, found = _resolve_existing_file_outside_repo(
        root,
        args["holoindex_receipt_path"],
        missing_reason="missing_holoindex_freshness_receipt_path",
        inside_reason="holoindex_freshness_receipt_path_inside_repo",
    )
    reasons.extend(found)
    output, found = _resolve_output_outside_repo(
        root,
        args["authority_profile_output_path"],
        missing_reason="missing_authority_profile_output_path",
        inside_reason="authority_profile_output_path_inside_repo",
    )
    reasons.extend(found)
    return {
        "authority_profile": profile,
        "holoindex_file": holoindex,
        "output_path": output,
    }, reasons


def _build_inputs(root, runtime_root, artifacts, capability, args):
    from modules.communication.moltbot_bridge.src.reddog_main_architect_fix_promotion_bootstrap import (
        _PromotionBootstrapInputs,
    )

    required = (
        "work_state_file",
        "output_path",
        "determination",
        "model_selection",
        "memex_supply",
        "authority_profile",
        "holoindex_file",
    )
    assert all(artifacts[key] is not None for key in required)
    return _PromotionBootstrapInputs(
        root=root,
        runtime_root=runtime_root,
        work_state_file=artifacts["work_state_file"],
        output_path=artifacts["output_path"],
        determination=artifacts["determination"],
        model_selection=artifacts["model_selection"],
        model_runtime_binding=artifacts["model_runtime_binding"],
        model_runtime_binding_verification_capability=capability,
        memex_supply=artifacts["memex_supply"],
        authority_profile=artifacts["authority_profile"],
        holoindex_file=artifacts["holoindex_file"],
        proposal_attestation=args["proposal_authenticity_attestation"] or {},
        signer_runtime_config=args["signer_runtime_config"],
        principal_key_resolver=args["principal_key_resolver"],
        revoked_key_epochs=frozenset(args["current_proposal_revoked_key_epochs"]),
        worker_id=args["worker_id"],
        now_iso=args["now_iso"] or datetime.now(timezone.utc).isoformat(),
        promotion_claim_fence_executor=args["promotion_claim_fence_executor"],
        environment=dict(
            os.environ if args["environment"] is None else args["environment"]
        ),
    )


def _promotion_model_runtime_inputs(
    root: Path,
    runtime_root: Path,
    selection_path,
    binding_path,
    config,
    injected,
    now_iso,
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
        return None, tuple(
            dict.fromkeys(reasons + ["model_runtime_binding_signed_evidence_invalid"])
        )
    try:
        capability = verifier.verify(binding=binding, selection=selection)
    except Exception:
        reasons.append("model_runtime_binding_signed_evidence_invalid")
        capability = None
    return capability, tuple(dict.fromkeys(reasons))


def _read_json_outside_repo(
    repo_root: Path,
    value,
    *,
    missing_reason: str,
    inside_reason: str,
    unreadable_reason: str,
) -> tuple[Optional[Mapping[str, Any]], list[str]]:
    path, reasons = _resolve_existing_file_outside_repo(
        repo_root, value, missing_reason=missing_reason, inside_reason=inside_reason
    )
    if reasons:
        return None, reasons
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None, [unreadable_reason]
    return (
        (payload, []) if isinstance(payload, Mapping) else (None, [unreadable_reason])
    )


def _read_optional_json_outside_repo(
    repo_root: Path,
    value,
    *,
    inside_reason: str,
    unreadable_reason: str,
) -> tuple[Optional[Mapping[str, Any]], list[str]]:
    if not value:
        return None, []
    return _read_json_outside_repo(
        repo_root,
        value,
        missing_reason=unreadable_reason,
        inside_reason=inside_reason,
        unreadable_reason=unreadable_reason,
    )


def _resolve_existing_file_outside_repo(
    repo_root: Path,
    value,
    *,
    missing_reason: str,
    inside_reason: str,
) -> tuple[Optional[Path], list[str]]:
    if not value:
        return None, [missing_reason]
    path = Path(value)
    path = ((repo_root / path) if not path.is_absolute() else path).resolve()
    if _is_inside(path, repo_root):
        return None, [inside_reason]
    return (path, []) if path.exists() and path.is_file() else (None, [missing_reason])


def _resolve_output_outside_repo(
    repo_root: Path,
    value,
    *,
    missing_reason: str,
    inside_reason: str,
) -> tuple[Optional[Path], list[str]]:
    if not value:
        return None, [missing_reason]
    path = Path(value)
    path = ((repo_root / path) if not path.is_absolute() else path).resolve()
    return (None, [inside_reason]) if _is_inside(path, repo_root) else (path, [])


def _output_alias_reasons(
    repo_root: Path, output_path: Path | None, consumed_paths
) -> list[str]:
    if output_path is None:
        return []
    for value in consumed_paths:
        if value:
            path = Path(value)
            resolved = (
                (repo_root / path) if not path.is_absolute() else path
            ).resolve()
            if resolved == output_path:
                return ["authority_profile_output_aliases_consumed_artifact"]
    return []


def _bootstrap_path_reasons(
    repo_root, runtime_root, work_state_path, output_path, arguments
):
    consumed = tuple(arguments.get(name) for name in _CONSUMED_ARTIFACT_PATH_ARGUMENTS)
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
        fd, tmp_name = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".probe", dir=str(path.parent)
        )
        os.close(fd)
        os.replace(tmp_name, tmp_name)
        os.unlink(tmp_name)
    except Exception:
        return ["authority_profile_output_not_writable"]
    return []


def _is_inside(child: Path, parent: Path) -> bool:
    child_r, parent_r = child.resolve(), parent.resolve()
    return child_r == parent_r or parent_r in child_r.parents


__all__ = ["run_promotion_bootstrap_request"]
