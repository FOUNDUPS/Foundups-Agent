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
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Optional

from modules.communication.moltbot_bridge.src.reddog_signer_key_provider_dryrun import (
    SignerKeyResolver,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_config_supply import (
    SIGNER_SERVICE_CONFIG_SCHEMA_VERSION,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_runtime_wiring import (
    ServeSignerSocketBounded,
    SignerSocketServiceRuntimeWiringConfig,
    run_reddog_signer_socket_service_runtime_wiring,
    validate_signer_socket_service_runtime_config,
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
FAIL_SIGNER_BOOTSTRAP_RUNTIME_REJECTED = "FAIL_SIGNER_BOOTSTRAP_RUNTIME_REJECTED"


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
    resolver: SignerKeyResolver,
    serve_bounded: ServeSignerSocketBounded,
    ready_callback: Optional[Callable[[], None]] = None,
) -> SignerSocketServiceRuntimeBootstrapResult:
    """Read a signer-owned outside-repo config and run signer service wiring."""

    root = Path(repo_root).resolve()
    path, path_reasons = _resolve_config_path(root, config_path)
    if path_reasons:
        return _reject(*path_reasons)
    assert path is not None

    payload, digest, read_reasons = _read_config(path, path.parent)
    if read_reasons:
        return _reject(*read_reasons, config_path=str(path))
    assert payload is not None
    assert digest is not None

    config = rehydrate_signer_socket_service_runtime_config(
        root,
        path.parent,
        payload,
    )
    if config is None:
        return _reject(
            FAIL_SIGNER_BOOTSTRAP_CONFIG_MALFORMED,
            config_path=str(path),
            config_digest=digest,
        )

    runtime = run_reddog_signer_socket_service_runtime_wiring(
        config,
        resolver,
        serve_bounded=serve_bounded,
        ready_callback=ready_callback,
    )
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


def _read_config(
    path: Path,
    runtime_root: Path,
) -> tuple[Optional[dict[str, Any]], Optional[str], tuple[str, ...]]:
    try:
        text = secure_read_confined_text(
            path,
            allowed_root=runtime_root,
            max_bytes=256 * 1024,
        )
        payload = json.loads(text, parse_constant=_reject_json_constant)
    except Exception:
        return None, None, (FAIL_SIGNER_BOOTSTRAP_CONFIG_UNREADABLE,)
    if not isinstance(payload, dict):
        return None, None, (FAIL_SIGNER_BOOTSTRAP_CONFIG_MALFORMED,)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    digest = "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return payload, digest, ()


def rehydrate_signer_socket_service_runtime_config(
    repo_root: Path,
    expected_runtime_root: Path,
    payload: dict[str, Any],
) -> Optional[SignerSocketServiceRuntimeWiringConfig]:
    """Validate and rehydrate the canonical schema-v2 signer config."""

    try:
        if payload.get("schema_version") != SIGNER_SERVICE_CONFIG_SCHEMA_VERSION:
            return None
        if not payload.get("control_loop_anchor_path") or not isinstance(
            payload.get("control_loop_authority_policy"),
            dict,
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
            control_loop_authority_policy=payload["control_loop_authority_policy"],
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


def _is_inside(child: Path, parent: Path) -> bool:
    child_r = child.resolve()
    parent_r = parent.resolve()
    return child_r == parent_r or parent_r in child_r.parents


__all__ = [
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
