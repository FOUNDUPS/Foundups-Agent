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
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Callable, Mapping, Optional

from modules.communication.moltbot_bridge.src.reddog_signer_key_provider_dryrun import (
    PROVIDER_MODE_WSP71_PERMISSIONED,
    SignerKeyResolver,
)
from modules.communication.moltbot_bridge.src.reddog_proposal_authenticity_nonce_store import (
    ProposalReplayHighWaterStore,
)
from modules.communication.moltbot_bridge.src.foundup_memex_verified_outcome_signing import (
    VerifiedOutcomeSigningAuthority,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_config_supply import (
    SIGNER_SERVICE_CONFIG_SCHEMA_VERSION,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_runtime_wiring import (
    ServeSignerSocketBounded,
    SignerSocketServiceRuntimeWiringConfig,
    architect_proposal_security_context_digest,
    run_reddog_signer_socket_service_runtime_wiring,
    validate_signer_socket_service_runtime_config,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    PrincipalKeyResolver,
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


SIGNER_SOCKET_RUNTIME_BOOTSTRAP_SERVED = "SIGNER_SOCKET_RUNTIME_BOOTSTRAP_SERVED"
SIGNER_SOCKET_RUNTIME_BOOTSTRAP_REJECT = "SIGNER_SOCKET_RUNTIME_BOOTSTRAP_REJECT"

FAIL_SIGNER_BOOTSTRAP_CONFIG_PATH_MISSING = "FAIL_SIGNER_BOOTSTRAP_CONFIG_PATH_MISSING"
FAIL_SIGNER_BOOTSTRAP_CONFIG_PATH_RELATIVE = "FAIL_SIGNER_BOOTSTRAP_CONFIG_PATH_RELATIVE"
FAIL_SIGNER_BOOTSTRAP_CONFIG_PATH_INSIDE_REPO = "FAIL_SIGNER_BOOTSTRAP_CONFIG_PATH_INSIDE_REPO"
FAIL_SIGNER_BOOTSTRAP_CONFIG_UNREADABLE = "FAIL_SIGNER_BOOTSTRAP_CONFIG_UNREADABLE"
FAIL_SIGNER_BOOTSTRAP_CONFIG_MALFORMED = "FAIL_SIGNER_BOOTSTRAP_CONFIG_MALFORMED"
FAIL_SIGNER_BOOTSTRAP_CONFIG_DIGEST_MISMATCH = (
    "FAIL_SIGNER_BOOTSTRAP_CONFIG_DIGEST_MISMATCH"
)
FAIL_SIGNER_BOOTSTRAP_RUNTIME_REJECTED = "FAIL_SIGNER_BOOTSTRAP_RUNTIME_REJECTED"
FAIL_SIGNER_BOOTSTRAP_MANIFEST_SELECTION = (
    "FAIL_SIGNER_BOOTSTRAP_MANIFEST_SELECTION"
)

ResolverAfterAdmission = Callable[[], SignerKeyResolver]
BootstrapLoadResult = tuple[
    Any | None,
    Path | None,
    str | None,
    "SignerSocketServiceRuntimeBootstrapResult | None",
]


@dataclass(frozen=True)
class SignerSocketServiceRuntimeBootstrapResult:
    """Audit-safe result for signer socket service runtime bootstrap."""

    accepted: bool
    status: str
    rejection_reasons: tuple[str, ...]
    config_path: Optional[str] = None
    config_digest: Optional[str] = None
    runtime_result: Optional[dict[str, Any]] = None
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
    proposal_replay_high_water_store: ProposalReplayHighWaterStore | None = None,
    verified_outcome_signing_authority: VerifiedOutcomeSigningAuthority | None = None,
) -> SignerSocketServiceRuntimeBootstrapResult:
    """Read a signer-owned outside-repo config and run signer service wiring."""

    root = Path(repo_root).resolve()
    config, path, digest, rejected = _load_bound_runtime_config(
        root,
        config_path,
        expected_config_digest,
        run_packet_path,
        expected_session_id,
        expected_owner_authority_config_path,
        manifest_selection,
        manifest_selection_boundary,
    )
    if rejected is not None:
        return rejected
    assert config is not None and path is not None and digest is not None
    admitted_resolver = _resolver_after_admission(resolver, resolver_factory)
    if admitted_resolver is None:
        return _reject(
            FAIL_SIGNER_BOOTSTRAP_RUNTIME_REJECTED,
            config_path=str(path),
            config_digest=digest,
        )

    runtime = run_reddog_signer_socket_service_runtime_wiring(
        config,
        admitted_resolver,
        serve_bounded=serve_bounded,
        ready_callback=ready_callback,
        principal_key_resolver=principal_key_resolver,
        proposal_replay_high_water_store=proposal_replay_high_water_store,
        verified_outcome_signing_authority=verified_outcome_signing_authority,
    )
    return _bootstrap_runtime_result(runtime, path=path, digest=digest)


def _bootstrap_runtime_result(
    runtime: Any,
    *,
    path: Path,
    digest: str,
) -> SignerSocketServiceRuntimeBootstrapResult:
    runtime_receipt = runtime.to_dict()
    if runtime.accepted is not True:
        return _reject(
            FAIL_SIGNER_BOOTSTRAP_RUNTIME_REJECTED,
            *runtime.rejection_reasons,
            config_path=str(path),
            config_digest=digest,
            runtime_result=runtime_receipt,
        )

    return SignerSocketServiceRuntimeBootstrapResult(
        accepted=True,
        status=SIGNER_SOCKET_RUNTIME_BOOTSTRAP_SERVED,
        rejection_reasons=(),
        config_path=str(path),
        config_digest=digest,
        runtime_result=runtime_receipt,
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
) -> Optional[SignerSocketServiceRuntimeWiringConfig]:
    """Validate and rehydrate the canonical schema-v2 signer config."""

    try:
        canonical = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        actual_digest = (
            "sha256:"
            + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        )
        if payload.get("proposal_authority_policy") is not None and (
            expected_config_digest is None
            or not hmac.compare_digest(
                expected_config_digest,
                actual_digest,
            )
        ):
            return None
        if payload.get("schema_version") != SIGNER_SERVICE_CONFIG_SCHEMA_VERSION:
            return None
        if not payload.get("control_loop_anchor_path"):
            return None
        if (
            not isinstance(
                payload.get("control_loop_authority_policy"),
                dict,
            )
            and payload.get("proposal_authority_policy") is None
        ):
            return None
        runtime_root = validate_runtime_root_path(
            payload["runtime_root"],
            repo_root=repo_root,
        )
        if runtime_root != expected_runtime_root.resolve():
            return None
        signer_runtime_root = validate_runtime_root_path(
            payload["signer_runtime_root"],
            repo_root=repo_root,
        )
        if (
            signer_runtime_root == runtime_root
            or runtime_root in signer_runtime_root.parents
            or signer_runtime_root in runtime_root.parents
        ):
            return None
        socket_path = validate_runtime_artifact_path(
            payload["socket_path"],
            repo_root=repo_root,
            allowed_root=runtime_root,
        )
        anchor_path = validate_runtime_artifact_path(
            payload["control_loop_anchor_path"],
            repo_root=repo_root,
            allowed_root=signer_runtime_root,
        )
        if socket_path.parent != runtime_root or anchor_path.parent != signer_runtime_root:
            return None
        proposal_policy = payload.get("proposal_authority_policy")
        proposal_policy_authorization = payload.get(
            "proposal_policy_authorization"
        )
        proposal_nonce_path_value = payload.get("proposal_nonce_store_path")
        proposal_high_water_store_id = payload.get(
            "proposal_replay_high_water_store_id"
        )
        proposal_high_water_durability_receipt_id = payload.get(
            "proposal_replay_high_water_durability_receipt_id"
        )
        if not (
            (proposal_policy is None)
            == (proposal_policy_authorization is None)
            == (proposal_nonce_path_value is None)
            == (proposal_high_water_store_id is None)
            == (
                proposal_high_water_durability_receipt_id is None
            )
        ):
            return None
        proposal_nonce_path = None
        if proposal_policy is not None:
            if not isinstance(proposal_policy, dict) or not isinstance(
                proposal_policy_authorization,
                dict,
            ):
                return None
            proposal_nonce_path = validate_runtime_artifact_path(
                proposal_nonce_path_value,
                repo_root=repo_root,
                allowed_root=signer_runtime_root,
            )
            if proposal_nonce_path.parent != signer_runtime_root:
                return None
            if (
                not isinstance(proposal_high_water_store_id, str)
                or not proposal_high_water_store_id.strip()
                or not proposal_high_water_store_id.isascii()
                or not _is_sha256_digest(
                    proposal_high_water_durability_receipt_id
                )
            ):
                return None
        else:
            proposal_high_water_store_id = None
            proposal_high_water_durability_receipt_id = None
        peer_policy = payload["peer_policy"]
        key_profile = payload.get("key_provider_profile")
        key_profiles = payload.get("key_provider_profiles") or ()
        if not isinstance(peer_policy, dict):
            return None
        if key_profile is not None and key_profiles:
            return None
        if key_profile is not None and not isinstance(key_profile, dict):
            return None
        if key_profiles:
            if not isinstance(key_profiles, list) or not all(
                isinstance(item, dict) for item in key_profiles
            ):
                return None
            key_profiles = tuple(key_profiles)
        if key_profile is None and not key_profiles:
            return None
        config = SignerSocketServiceRuntimeWiringConfig(
            repo_root=repo_root,
            runtime_root=runtime_root,
            signer_runtime_root=signer_runtime_root,
            socket_path=socket_path,
            peer_policy=peer_policy,
            key_provider_profile=key_profile,
            provider_mode=str(payload.get("provider_mode") or ""),
            allow_test_only_key_material=payload.get("allow_test_only_key_material") is True,
            permission_snapshot_fresh=payload.get("permission_snapshot_fresh") is True,
            max_requests=payload.get("max_requests"),
            timeout_s=payload.get("timeout_s"),
            max_request_bytes=payload.get("max_request_bytes"),
            max_response_bytes=payload.get("max_response_bytes"),
            key_provider_profiles=key_profiles,
            control_loop_anchor_path=anchor_path,
            control_loop_authority_policy=payload.get(
                "control_loop_authority_policy"
            ),
            verified_outcome_signer_policy=payload.get(
                "verified_outcome_signer_policy"
            ),
            proposal_authority_policy=proposal_policy,
            proposal_policy_authorization=proposal_policy_authorization,
            proposal_nonce_store_path=proposal_nonce_path,
            proposal_replay_high_water_store_id=(
                proposal_high_water_store_id
            ),
            proposal_replay_high_water_durability_receipt_id=(
                proposal_high_water_durability_receipt_id
            ),
        )
        if proposal_policy is not None:
            config = replace(
                config,
                proposal_security_context_digest=(
                    architect_proposal_security_context_digest(config)
                ),
            )
    except Exception:
        return None
    if validate_signer_socket_service_runtime_config(config):
        return None
    return config


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non_finite_json_constant:{value}")


def _reject(
    *reasons: str,
    config_path: Optional[str] = None,
    config_digest: Optional[str] = None,
    runtime_result: Optional[dict[str, Any]] = None,
) -> SignerSocketServiceRuntimeBootstrapResult:
    return SignerSocketServiceRuntimeBootstrapResult(
        accepted=False,
        status=SIGNER_SOCKET_RUNTIME_BOOTSTRAP_REJECT,
        rejection_reasons=tuple(dict.fromkeys(reason for reason in reasons if reason)),
        config_path=config_path,
        config_digest=config_digest,
        runtime_result=runtime_result,
    )


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
    "SIGNER_SOCKET_RUNTIME_BOOTSTRAP_REJECT",
    "SIGNER_SOCKET_RUNTIME_BOOTSTRAP_SERVED",
    "SignerSocketServiceRuntimeBootstrapResult",
    "rehydrate_signer_socket_service_runtime_config",
    "run_reddog_signer_socket_service_runtime_bootstrap",
]
