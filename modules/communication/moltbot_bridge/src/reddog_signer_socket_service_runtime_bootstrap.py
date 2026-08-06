"""Outside-repo config bootstrap for the RedDog signer socket service.

Slice: REDDOG_SIGNER_SOCKET_SERVICE_RUNTIME_BOOTSTRAP_PHASE1

This signer-owned bootstrap reads one outside-repo JSON config, builds the
existing signer socket service runtime wiring config, and invokes that wiring
with an injected resolver. It does not parse environment variables, spawn a
process, load secret files, mutate the repository, enqueue OpenClaw, dispatch
Hermes, publish PRs, settle rewards, or re-index HoloIndex.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Callable, Mapping, Optional

from modules.communication.moltbot_bridge.src.reddog_signer_key_provider_dryrun import (
    PROVIDER_MODE_WSP71_PERMISSIONED,
    SignerKeyResolver,
)
from modules.communication.moltbot_bridge.src.reddog_proposal_authenticity_nonce_store import (
    ProposalReplayHighWaterStore,
)
from modules.communication.moltbot_bridge.src.reddog_signer_process_isolation_gate import (
    enforce_signer_process_isolation,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_bootstrap_admission import (
    ProcessIsolationGate,
    SIGNER_SOCKET_RUNTIME_BOOTSTRAP_REJECT,
    SIGNER_SOCKET_RUNTIME_BOOTSTRAP_SERVED,
    SignerSocketServiceRuntimeBootstrapResult,
    bootstrap_runtime_result as _bootstrap_runtime_result,
    reject_bootstrap as _reject,
    require_process_isolation as _process_isolation_receipt,
)
from modules.communication.moltbot_bridge.src.foundup_memex_verified_outcome_signing import (
    VerifiedOutcomeSigningAuthority,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_config_rehydration import (
    rehydrate_signer_socket_service_runtime_config as _rehydrate_runtime_config,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_runtime_wiring import (
    ServeSignerSocketBounded,
    SignerSocketServiceRuntimeWiringConfig,
    run_reddog_signer_socket_service_runtime_wiring,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    PrincipalKeyResolver,
)
from modules.communication.moltbot_bridge.src.reddog_authority_runtime_store import (
    PrincipalAuthorityResolver,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_launch_selection import (
    RuntimeArtifactManifestLaunchSelectionBoundary,
)
from modules.communication.moltbot_bridge.src.reddog_signer_mutual_peer_handshake import (
    SignerPeerProfileBinding,
    load_signer_peer_instance_binding,
)
from modules.communication.moltbot_bridge.src.reddog_signer_peer_instance_packet_validator import (
    signer_generation_bound_selection_valid,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    secure_read_confined_text,
    validate_runtime_artifact_path,
    validate_runtime_root_path,
)
from modules.communication.moltbot_bridge.src.reddog_verified_outcome_authority_admission import admit_verified_outcome_authority


FAIL_SIGNER_BOOTSTRAP_CONFIG_PATH_MISSING = "FAIL_SIGNER_BOOTSTRAP_CONFIG_PATH_MISSING"
FAIL_SIGNER_BOOTSTRAP_CONFIG_PATH_RELATIVE = "FAIL_SIGNER_BOOTSTRAP_CONFIG_PATH_RELATIVE"
FAIL_SIGNER_BOOTSTRAP_CONFIG_PATH_INSIDE_REPO = "FAIL_SIGNER_BOOTSTRAP_CONFIG_PATH_INSIDE_REPO"
FAIL_SIGNER_BOOTSTRAP_CONFIG_UNREADABLE = "FAIL_SIGNER_BOOTSTRAP_CONFIG_UNREADABLE"
FAIL_SIGNER_BOOTSTRAP_CONFIG_MALFORMED = "FAIL_SIGNER_BOOTSTRAP_CONFIG_MALFORMED"
FAIL_SIGNER_BOOTSTRAP_CONFIG_DIGEST_MISMATCH = (
    "FAIL_SIGNER_BOOTSTRAP_CONFIG_DIGEST_MISMATCH"
)
FAIL_SIGNER_BOOTSTRAP_RUNTIME_REJECTED = "FAIL_SIGNER_BOOTSTRAP_RUNTIME_REJECTED"
FAIL_SIGNER_BOOTSTRAP_PROCESS_ISOLATION = "FAIL_SIGNER_BOOTSTRAP_PROCESS_ISOLATION"
FAIL_SIGNER_BOOTSTRAP_MANIFEST_SELECTION = (
    "FAIL_SIGNER_BOOTSTRAP_MANIFEST_SELECTION"
)

ResolverAfterAdmission = Callable[[], SignerKeyResolver]
ConversationResolverAfterAdmission = Callable[[], PrincipalAuthorityResolver]
BootstrapLoadResult = tuple[Any | None, Path | None, str | None, "SignerSocketServiceRuntimeBootstrapResult | None"]


@dataclass(frozen=True)
class RuntimeBootstrapRequest:
    repo_root: Path | str
    config_path: Path | str | None
    resolver: SignerKeyResolver | None
    resolver_factory: ResolverAfterAdmission | None
    serve_bounded: ServeSignerSocketBounded
    ready_callback: Optional[Callable[[], None]]
    expected_config_digest: str | None
    run_packet_path: Path | str | None
    expected_session_id: str | None
    expected_owner_authority_config_path: Path | str | None
    manifest_selection: object | None
    manifest_selection_boundary: RuntimeArtifactManifestLaunchSelectionBoundary | None
    principal_key_resolver: PrincipalKeyResolver | None
    conversation_scope_principal_resolver: PrincipalAuthorityResolver | None
    conversation_scope_principal_resolver_supplier: ConversationResolverAfterAdmission | None
    proposal_replay_high_water_store: ProposalReplayHighWaterStore | None
    verified_outcome_signing_authority: VerifiedOutcomeSigningAuthority | None
    verified_outcome_signing_authority_supplier: Callable[[], VerifiedOutcomeSigningAuthority] | None
    process_isolation_required: bool
    process_isolation_gate: ProcessIsolationGate
    expected_signer_uid: int | None
    expected_signer_gid: int | None


def run_reddog_signer_socket_service_runtime_bootstrap(
    *,
    repo_root: Path | str,
    config_path: Path | str | None,
    resolver: SignerKeyResolver | None = None,
    resolver_factory: ResolverAfterAdmission | None = None,
    serve_bounded: ServeSignerSocketBounded,
    ready_callback: Optional[Callable[[], None]] = None,
    expected_config_digest: str | None = None,
    run_packet_path: Path | str | None = None,
    expected_session_id: str | None = None,
    expected_owner_authority_config_path: Path | str | None = None,
    manifest_selection: object | None = None,
    manifest_selection_boundary: RuntimeArtifactManifestLaunchSelectionBoundary | None = None,
    principal_key_resolver: PrincipalKeyResolver | None = None,
    conversation_scope_principal_resolver: PrincipalAuthorityResolver | None = None,
    conversation_scope_principal_resolver_supplier: (
        ConversationResolverAfterAdmission | None
    ) = None,
    proposal_replay_high_water_store: ProposalReplayHighWaterStore | None = None,
    verified_outcome_signing_authority: VerifiedOutcomeSigningAuthority | None = None,
    verified_outcome_signing_authority_supplier: Callable[[], VerifiedOutcomeSigningAuthority] | None = None,
    process_isolation_required: bool = False,
    process_isolation_gate: ProcessIsolationGate = enforce_signer_process_isolation,
    expected_signer_uid: int | None = None, expected_signer_gid: int | None = None,
) -> SignerSocketServiceRuntimeBootstrapResult:
    """Read a signer-owned outside-repo config and run signer service wiring."""

    return _run_runtime_bootstrap(RuntimeBootstrapRequest(**locals()))


def _run_runtime_bootstrap(
    request: RuntimeBootstrapRequest,
) -> SignerSocketServiceRuntimeBootstrapResult:
    root = Path(request.repo_root).resolve()
    config, path, digest, rejected = _load_bound_runtime_config(
        root, request.config_path, request.expected_config_digest,
        request.run_packet_path, request.expected_session_id,
        request.expected_owner_authority_config_path,
        request.manifest_selection, request.manifest_selection_boundary,
    )
    if rejected is not None:
        return rejected
    assert config is not None and path is not None and digest is not None
    isolation = _process_isolation_receipt(
        config, required=request.process_isolation_required,
        gate=request.process_isolation_gate,
        expected_signer_uid=request.expected_signer_uid,
        expected_signer_gid=request.expected_signer_gid,
    )
    if request.process_isolation_required and (isolation is None or not isolation.accepted):
        return _reject(
            FAIL_SIGNER_BOOTSTRAP_PROCESS_ISOLATION,
            config_path=str(path),
            config_digest=digest,
            process_isolation_receipt=(isolation.to_dict() if isolation else None),
        )
    dependencies, rejected = _admitted_runtime_dependencies(
        request, config, path, digest
    )
    if rejected is not None:
        return rejected
    admitted_resolver, outcome_authority, conversation_resolver = dependencies
    runtime = run_reddog_signer_socket_service_runtime_wiring(
        config, admitted_resolver,
        serve_bounded=request.serve_bounded,
        ready_callback=request.ready_callback,
        principal_key_resolver=request.principal_key_resolver,
        conversation_scope_principal_resolver=conversation_resolver,
        proposal_replay_high_water_store=request.proposal_replay_high_water_store,
        verified_outcome_signing_authority=outcome_authority,
    )
    return _bootstrap_runtime_result(
        runtime, path=path, digest=digest,
        process_isolation_receipt=(isolation.to_dict() if isolation else None),
    )


def _consume_manifest_selection(
    root: Path,
    value: object | None,
    boundary: RuntimeArtifactManifestLaunchSelectionBoundary | None,
) -> Mapping[str, Any] | None:
    if value is None or boundary is None:
        return None
    try:
        selected = boundary.consume(value)
        runtime_root = validate_runtime_root_path(
            selected["runtime_root"],
            repo_root=root,
        )
        config_path = Path(str(selected["config_path"])).resolve()
        packet_path = Path(str(selected["run_packet_path"])).resolve()
    except Exception:
        return None
    if Path(str(selected.get("repo_root") or "")).resolve() != root:
        return None
    if config_path.parent != runtime_root or packet_path.parent != runtime_root:
        return None
    return selected


def _caller_paths_match_selection(
    config_path: Path | str | None,
    run_packet_path: Path | str | None,
    selected_config: Path,
    selected_packet: Path,
) -> bool:
    if config_path is None and run_packet_path is None:
        return True
    if config_path is None or run_packet_path is None:
        return False
    return bool(
        config_path
        and run_packet_path
        and Path(config_path).resolve() == selected_config.resolve()
        and Path(run_packet_path).resolve() == selected_packet.resolve()
    )


def _resolver_after_admission(
    resolver: SignerKeyResolver | None,
    factory: ResolverAfterAdmission | None,
) -> SignerKeyResolver | None:
    if resolver is not None:
        return resolver
    if factory is None:
        return None
    try:
        return factory()
    except Exception:
        return None


def _conversation_resolver_after_admission(
    config: SignerSocketServiceRuntimeWiringConfig,
    resolver: PrincipalAuthorityResolver | None,
    supplier: ConversationResolverAfterAdmission | None,
) -> PrincipalAuthorityResolver | None:
    if config.conversation_scope_signer_policy is None:
        return None
    if resolver is not None:
        return resolver
    if supplier is None:
        return None
    try:
        return supplier()
    except Exception:
        return None


def _load_bound_runtime_config(
    root: Path, config_path: Path | str | None,
    expected_digest: str | None, run_packet_path: Path | str | None,
    session_id: str | None,
    owner_authority_config_path: Path | str | None,
    manifest_selection: object | None,
    manifest_selection_boundary: RuntimeArtifactManifestLaunchSelectionBoundary | None,
) -> BootstrapLoadResult:
    launch = _selected_launch_paths(
        root,
        config_path,
        run_packet_path,
        manifest_selection,
        manifest_selection_boundary,
    )
    if launch is None:
        return None, None, None, _reject(
            FAIL_SIGNER_BOOTSTRAP_MANIFEST_SELECTION
        )
    selection, selected_config, selected_packet = launch
    path, reasons = _resolve_config_path(root, selected_config)
    if reasons:
        return None, None, None, _reject(*reasons)
    assert path is not None
    payload, digest, raw_digest, reasons = _read_config(path, path.parent)
    if reasons:
        return None, path, None, _reject(*reasons, config_path=str(path))
    assert payload is not None and digest is not None and raw_digest is not None
    selected_digest = str(selection["config_digest"])
    if (
        expected_digest is not None
        and expected_digest != selected_digest
    ) or _config_digest_rejected(
        payload, digest, selected_digest
    ):
        rejected = _reject(
            FAIL_SIGNER_BOOTSTRAP_CONFIG_DIGEST_MISMATCH,
            config_path=str(path),
            config_digest=digest,
        )
        return None, path, digest, rejected
    config = _rehydrate_selected_config(
        root,
        path,
        payload,
        raw_digest,
        selected_digest,
        selected_packet,
        session_id,
        owner_authority_config_path,
        selection,
    )
    if config is None:
        return None, path, digest, _malformed_config(path, digest)
    return config, path, digest, None


def _selected_launch_paths(
    root: Path,
    config_path: Path | str | None,
    run_packet_path: Path | str | None,
    manifest_selection: object | None,
    boundary: RuntimeArtifactManifestLaunchSelectionBoundary | None,
) -> tuple[Mapping[str, Any], Path, Path] | None:
    selection = _consume_manifest_selection(
        root,
        manifest_selection,
        boundary,
    )
    if selection is None:
        return None
    selected_config = Path(str(selection["config_path"]))
    selected_packet = Path(str(selection["run_packet_path"]))
    if not _caller_paths_match_selection(
        config_path,
        run_packet_path,
        selected_config,
        selected_packet,
    ):
        return None
    return selection, selected_config, selected_packet


def _rehydrate_selected_config(
    root: Path,
    path: Path,
    payload: dict[str, Any],
    raw_digest: str,
    selected_digest: str,
    selected_packet: Path,
    session_id: str | None,
    owner_authority_config_path: Path | str | None,
    selection: Mapping[str, Any],
) -> Any | None:
    config = rehydrate_signer_socket_service_runtime_config(
        root,
        path.parent,
        payload,
        expected_config_digest=selected_digest,
    )
    if config is None:
        return None
    return _attach_peer_binding(
        config,
        root,
        path,
        selected_digest,
        selected_packet,
        session_id,
        owner_authority_config_path,
        selection,
        raw_digest,
    )


def _config_digest_rejected(
    payload: Mapping[str, Any],
    actual: str,
    expected: str | None,
) -> bool:
    if expected is not None and not _is_sha256_digest(expected):
        return True
    matches = expected is not None and hmac.compare_digest(expected, actual)
    return (expected is not None and not matches) or (
        payload.get("proposal_authority_policy") is not None and not matches
    )


def _attach_peer_binding(
    config: Any,
    root: Path,
    config_path: Path,
    expected_digest: str | None,
    run_packet_path: Path | str | None,
    session_id: str | None,
    owner_authority_config_path: Path | str | None,
    manifest_selection: Mapping[str, Any],
    config_raw_digest: str,
) -> Any | None:
    if config.provider_mode != PROVIDER_MODE_WSP71_PERMISSIONED:
        return None
    if (
        expected_digest is None
        or not run_packet_path
        or not owner_authority_config_path
    ):
        return None
    profiles = tuple(config.key_provider_profiles) or (
        (config.key_provider_profile,) if config.key_provider_profile else ()
    )
    if not _selection_config_binding_valid(
        manifest_selection,
        root=root,
        config_path=config_path,
        config_digest=expected_digest,
        config_raw_digest=config_raw_digest,
    ):
        return None
    binding = load_signer_peer_instance_binding(
        repo_root=root,
        config_path=config_path,
        expected_config_digest=expected_digest,
        run_packet_path=run_packet_path,
        expected_session_id=session_id,
        expected_socket_path=config.socket_path,
        signer_profiles=tuple(_profile_peer_binding(item) for item in profiles),
        manifest_selection=manifest_selection,
        python_executable=sys.executable,
        owner_authority_config_path=owner_authority_config_path,
    )
    return (
        replace(
            config,
            signer_peer_instance_binding=binding,
            system_service_owner_config_id=str(
                manifest_selection.get("owner_config_id") or ""
            ),
        )
        if binding
        else None
    )


def _profile_peer_binding(value: Any) -> SignerPeerProfileBinding:
    return SignerPeerProfileBinding(
        signer_profile_id=_profile_id(value),
        signer_public_key=_profile_value(value, "expected_public_key"),
        key_epoch=_profile_value(value, "expected_key_epoch"),
    )


def _selection_config_binding_valid(
    value: object,
    *,
    root: Path,
    config_path: Path,
    config_digest: str,
    config_raw_digest: str,
) -> bool:
    return signer_generation_bound_selection_valid(value) and all(
        (
            Path(str(value.get("repo_root") or "")).resolve() == root,
            Path(str(value.get("config_path") or "")).resolve() == config_path,
            value.get("config_digest") == config_digest,
            value.get("config_raw_digest") == config_raw_digest,
        )
    )


def _profile_value(value: Any, name: str) -> str:
    candidate = (
        value.get(name)
        if isinstance(value, Mapping)
        else getattr(value, name, "")
    )
    return str(candidate or "")


def _malformed_config(
    path: Path,
    digest: str,
) -> SignerSocketServiceRuntimeBootstrapResult:
    return _reject(
        FAIL_SIGNER_BOOTSTRAP_CONFIG_MALFORMED,
        config_path=str(path),
        config_digest=digest,
    )


def _resolve_config_path(
    repo_root: Path,
    value: Path | str | None,
) -> tuple[Optional[Path], tuple[str, ...]]:
    if not value:
        return None, (FAIL_SIGNER_BOOTSTRAP_CONFIG_PATH_MISSING,)
    path = Path(value)
    if not path.is_absolute():
        return None, (FAIL_SIGNER_BOOTSTRAP_CONFIG_PATH_RELATIVE,)
    if _is_inside(path, repo_root):
        return None, (FAIL_SIGNER_BOOTSTRAP_CONFIG_PATH_INSIDE_REPO,)
    try:
        runtime_root = validate_runtime_root_path(path.parent, repo_root=repo_root)
        resolved = validate_runtime_artifact_path(
            path,
            repo_root=repo_root,
            allowed_root=runtime_root,
        )
    except (OSError, ValueError):
        return None, (FAIL_SIGNER_BOOTSTRAP_CONFIG_UNREADABLE,)
    if not resolved.exists() or not resolved.is_file():
        return None, (FAIL_SIGNER_BOOTSTRAP_CONFIG_PATH_MISSING,)
    return resolved, ()


def _profile_id(value: object) -> str:
    if hasattr(value, "signer_profile_id"):
        return str(getattr(value, "signer_profile_id"))
    if isinstance(value, dict):
        return str(value.get("signer_profile_id") or "")
    return ""


def _read_config(
    path: Path,
    runtime_root: Path,
) -> tuple[
    Optional[dict[str, Any]],
    Optional[str],
    Optional[str],
    tuple[str, ...],
]:
    try:
        text = secure_read_confined_text(
            path,
            allowed_root=runtime_root,
            max_bytes=256 * 1024,
        )
        payload = json.loads(text, parse_constant=_reject_json_constant)
    except Exception:
        return None, None, None, (FAIL_SIGNER_BOOTSTRAP_CONFIG_UNREADABLE,)
    if not isinstance(payload, dict):
        return None, None, None, (FAIL_SIGNER_BOOTSTRAP_CONFIG_MALFORMED,)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    digest = "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    raw_digest = "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()
    return payload, digest, raw_digest, ()


def rehydrate_signer_socket_service_runtime_config(
    repo_root: Path,
    expected_runtime_root: Path,
    payload: dict[str, Any],
    *,
    expected_config_digest: str | None = None,
) -> SignerSocketServiceRuntimeWiringConfig | None:
    """Compatibility seam for the extracted strict config rehydrator."""

    return _rehydrate_runtime_config(
        repo_root,
        expected_runtime_root,
        payload,
        expected_config_digest=expected_config_digest,
    )


def _admitted_runtime_dependencies(
    request: RuntimeBootstrapRequest,
    config: SignerSocketServiceRuntimeWiringConfig,
    path: Path,
    digest: str,
) -> tuple[tuple[Any, Any, Any] | None, SignerSocketServiceRuntimeBootstrapResult | None]:
    resolver = _resolver_after_admission(
        request.resolver, request.resolver_factory
    )
    outcome = admit_verified_outcome_authority(
        config.verified_outcome_signer_policy,
        request.verified_outcome_signing_authority,
        request.verified_outcome_signing_authority_supplier,
    )
    conversation = _conversation_resolver_after_admission(
        config, request.conversation_scope_principal_resolver,
        request.conversation_scope_principal_resolver_supplier,
    )
    invalid = resolver is None or (
        config.conversation_scope_signer_policy is not None
        and conversation is None
    )
    if invalid:
        return None, _reject(
            FAIL_SIGNER_BOOTSTRAP_RUNTIME_REJECTED,
            config_path=str(path), config_digest=digest,
        )
    return (resolver, outcome, conversation), None


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non_finite_json_constant:{value}")


def _is_sha256_digest(value: object) -> bool:
    text = value if isinstance(value, str) else ""
    return (
        len(text) == 71
        and text.startswith("sha256:")
        and all(char in "0123456789abcdef" for char in text[7:])
    )


def _is_inside(child: Path, parent: Path) -> bool:
    child_r = child.resolve()
    parent_r = parent.resolve()
    return child_r == parent_r or parent_r in child_r.parents


__all__ = [
    "FAIL_SIGNER_BOOTSTRAP_CONFIG_DIGEST_MISMATCH",
    "FAIL_SIGNER_BOOTSTRAP_CONFIG_MALFORMED",
    "FAIL_SIGNER_BOOTSTRAP_CONFIG_PATH_INSIDE_REPO",
    "FAIL_SIGNER_BOOTSTRAP_CONFIG_PATH_MISSING",
    "FAIL_SIGNER_BOOTSTRAP_CONFIG_PATH_RELATIVE",
    "FAIL_SIGNER_BOOTSTRAP_CONFIG_UNREADABLE",
    "FAIL_SIGNER_BOOTSTRAP_RUNTIME_REJECTED",
    "FAIL_SIGNER_BOOTSTRAP_PROCESS_ISOLATION",
    "SIGNER_SOCKET_RUNTIME_BOOTSTRAP_REJECT",
    "SIGNER_SOCKET_RUNTIME_BOOTSTRAP_SERVED",
    "SignerSocketServiceRuntimeBootstrapResult",
    "rehydrate_signer_socket_service_runtime_config",
    "run_reddog_signer_socket_service_runtime_bootstrap",
]
