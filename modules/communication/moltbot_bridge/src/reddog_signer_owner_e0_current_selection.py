"""Root-owned current-generation selection for signer E0 admission."""

from __future__ import annotations

import time
import math
import os
import threading
from weakref import WeakKeyDictionary
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Mapping

from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    Ed25519SignatureVerifier,
)

from modules.communication.moltbot_bridge.src.reddog_signer_system_service_manifest_selection_loader import (
    load_system_service_manifest_selection,
)

from .reddog_signer_owner_e0_admission_contract import (
    OwnerControlledE0ConsumptionReceipt,
)
from .reddog_signer_owner_e0_admission_validation import (
    load_selected_signer_config,
    require_policy_authorities,
    require_policy_config_binding,
    require_policy_runtime_paths,
    require_policy_selection_binding,
)
from .reddog_signer_owner_e0_capability_state import (
    freeze_owner_e0_policy,
    thaw_owner_e0_policy,
)
from .reddog_signer_owner_e0_policy_contract import (
    signer_owner_e0_authority_binding_digest,
    validated_signer_owner_e0_policy,
)
from .reddog_signer_owner_e0_principal_authority import (
    load_current_generation_principal_key_resolver,
)
from .reddog_signer_secret_grant_revocation_authority_binding import (
    SignerGrantRevocationAuthorityBinding,
    revocation_authority_binding_from_policy,
)


@dataclass(frozen=True)
class ValidatedOwnerE0Lease:
    receipt: OwnerControlledE0ConsumptionReceipt
    policy: Mapping[str, Any]
    selection: Mapping[str, Any]
    config: Any
    resolver: Any
    revocation_binding: SignerGrantRevocationAuthorityBinding


def load_owner_e0_current_selection(
    *, owner_config_path: Path | str, repo_root: Path
) -> Mapping[str, Any]:
    capability, boundary = load_system_service_manifest_selection(
        owner_config_path=owner_config_path,
        repo_root=repo_root,
    )
    selected = boundary.consume(capability)
    if Path(str(selected.get("repo_root") or "")).resolve() != repo_root.resolve():
        raise ValueError("e0_selection_repo_root_mismatch")
    return selected


@contextmanager
def lease_owner_e0_current_selection(
    *, owner_config_path: Path | str, repo_root: Path
) -> Iterator[Mapping[str, Any]]:
    """Hold the authenticated generation fence through use-time admission."""

    capability, boundary = load_system_service_manifest_selection(
        owner_config_path=owner_config_path,
        repo_root=repo_root,
    )
    with boundary._lease_current(capability) as selected:
        if Path(str(selected.get("repo_root") or "")).resolve() != repo_root.resolve():
            raise ValueError("e0_selection_repo_root_mismatch")
        yield selected


def validate_owner_e0_current_admission(
    *,
    owner_config_path: Path | str,
    repo_root: Path,
    policy: Mapping[str, Any],
) -> tuple[OwnerControlledE0ConsumptionReceipt, Mapping[str, Any]]:
    """Validate E0 inputs under the private current-generation lease."""

    capability, boundary = load_system_service_manifest_selection(
        owner_config_path=owner_config_path,
        repo_root=repo_root,
    )
    with boundary._lease_current(capability) as selected:
        if Path(str(selected.get("repo_root") or "")).resolve() != repo_root.resolve():
            raise ValueError("e0_selection_repo_root_mismatch")
        return _validate_selected(repo_root.resolve(), selected, policy)


@contextmanager
def lease_validated_owner_e0_current_admission(
    *, owner_config_path: Path | str, repo_root: Path,
    policy: Mapping[str, Any],
) -> Iterator[ValidatedOwnerE0Lease]:
    """Hold the current-generation fence through one privileged use."""

    capability, boundary = load_system_service_manifest_selection(
        owner_config_path=owner_config_path, repo_root=repo_root,
    )
    with boundary._lease_current(capability) as selected:
        if Path(str(selected.get("repo_root") or "")).resolve() != repo_root.resolve():
            raise ValueError("e0_selection_repo_root_mismatch")
        yield _validated_selected_lease(repo_root.resolve(), selected, policy)


def _validate_selected(
    repo_root: Path,
    selection: Mapping[str, Any],
    policy: Mapping[str, Any],
) -> tuple[OwnerControlledE0ConsumptionReceipt, Mapping[str, Any]]:
    lease = _validated_selected_lease(repo_root, selection, policy)
    return lease.receipt, lease.policy


def _validated_selected_lease(
    repo_root: Path,
    selection: Mapping[str, Any],
    policy: Mapping[str, Any],
) -> ValidatedOwnerE0Lease:
    checked = validated_signer_owner_e0_policy(
        thaw_owner_e0_policy(policy), now_epoch=int(time.time())
    )
    require_policy_selection_binding(checked, selection)
    config = load_selected_signer_config(
        repo_root=repo_root,
        selection=selection,
        expected_authority_binding_digest=(
            signer_owner_e0_authority_binding_digest(checked)
        ),
    )
    profile = require_policy_config_binding(checked, config)
    resolver = load_current_generation_principal_key_resolver(
        repo_root=repo_root, selection=selection
    )
    require_policy_authorities(
        checked,
        principal_key_resolver=resolver,
        signature_verifier=Ed25519SignatureVerifier(),
    )
    require_policy_runtime_paths(
        checked,
        repo_root=repo_root,
        signer_runtime_root=Path(config.signer_runtime_root).resolve(),
        initial_config=config,
    )
    _require_consensus_policy(checked)
    binding = revocation_authority_binding_from_policy(
        checked, repo_root=repo_root,
        signer_runtime_root=Path(config.signer_runtime_root).resolve(),
    )
    return ValidatedOwnerE0Lease(
        receipt=_receipt(checked, selection, profile),
        policy=freeze_owner_e0_policy(checked),
        selection=dict(selection), config=config, resolver=resolver,
        revocation_binding=binding,
    )


def _receipt(
    policy: Mapping[str, Any], selection: Mapping[str, Any], profile: Any
) -> OwnerControlledE0ConsumptionReceipt:
    return OwnerControlledE0ConsumptionReceipt(
        policy_id=str(policy["policy_id"]),
        manifest_id=str(selection["manifest_id"]),
        artifact_generation_digest=str(selection["artifact_generation_digest"]),
        config_digest=str(selection["config_digest"]),
        target_signer_agent_id=profile.signer_agent_id,
        target_signer_profile_id=profile.signer_profile_id,
    )


def _require_consensus_policy(policy: Mapping[str, Any]) -> None:
    tiers = set(policy["allowed_authority_tiers"])
    consensus = set(policy["consensus_required_tiers"])
    if tiers - {"LOW"} - consensus:
        raise ValueError("signer_owner_e0_consensus_policy_invalid")


__all__ = [
    "ValidatedOwnerE0Lease",
    "lease_owner_e0_current_selection",
    "lease_validated_owner_e0_current_admission",
    "load_owner_e0_current_selection",
    "validate_owner_e0_current_admission",
]


class _CurrentOwnerUseScope:
    """Opaque, thread/process-local lifetime of one real authenticated lease."""
    __slots__ = ("__weakref__",)

    def __new__(cls, *args, **kwargs):
        raise TypeError("current_owner_scope_construction_forbidden")

    def __copy__(self):
        raise TypeError("current_owner_scope_copy_forbidden")

    def __deepcopy__(self, memo):
        raise TypeError("current_owner_scope_copy_forbidden")

    def __reduce__(self):
        raise TypeError("current_owner_scope_pickle_forbidden")


_SCOPE_LOCK = threading.Lock()
_LIVE_SCOPES = WeakKeyDictionary()


def _scope_clock(record):
    wall, mono = time.time(), time.monotonic()
    if (type(wall) not in (int, float) or type(mono) not in (int, float)
            or not math.isfinite(wall) or not math.isfinite(mono)
            or min(wall, mono) < 0 or wall < record['wall'] or mono < record['mono']):
        raise ValueError("current_owner_scope_clock_invalid")
    record['wall'], record['mono'] = wall, mono
    return wall


def _scope_admission(scope, *, owner_config_path, repo_root):
    from . import reddog_signer_system_service_manifest_selection_loader as loader
    from .reddog_runtime_artifact_manifest_contract import canonical_json
    with _SCOPE_LOCK:
        record = _LIVE_SCOPES.get(scope) if type(scope) is _CurrentOwnerUseScope else None
    if (record is None or record['thread'] != threading.get_ident() or record['pid'] != os.getpid()
            or record['path'] != Path(owner_config_path).resolve() or record['repo'] != Path(repo_root).resolve()):
        raise ValueError("current_owner_scope_not_live")
    _scope_clock(record)
    owner = loader._load_owner_config(record['path'], repo=record['repo'])
    if canonical_json(owner) != record['owner']:
        raise ValueError("current_owner_scope_owner_changed")
    record['boundary']._recheck_current_locked(record['selected'])
    current = _validated_selected_lease(record['repo'], record['selected'], record['policy'])
    if (canonical_json(dict(current.selection)) != record['selection']
            or canonical_json(thaw_owner_e0_policy(current.policy)) != record['policy_bytes']):
        raise ValueError("current_owner_scope_binding_changed")
    now = _scope_clock(record)
    if not current.selection['selection_issued_at'] <= now < current.selection['selection_expires_at']:
        raise ValueError("current_owner_scope_expired")
    if not current.policy['issued_at'] <= now < current.policy['expires_at']:
        raise ValueError("current_owner_scope_expired")
    return owner, current


@contextmanager
def _lease_validated_owner_e0_current_scope(*, owner_config_path, repo_root, policy):
    from . import reddog_signer_system_service_manifest_selection_loader as loader
    from .reddog_runtime_artifact_manifest_contract import canonical_json
    repo, path = Path(repo_root).resolve(), Path(owner_config_path).resolve()
    capability, boundary = load_system_service_manifest_selection(owner_config_path=path, repo_root=repo)
    scope = object.__new__(_CurrentOwnerUseScope)
    with boundary._lease_current(capability) as selected:
        owner = loader._load_owner_config(path, repo=repo)
        if owner['schema_version'] != loader.SCHEMA_VERSION_V13:
            raise ValueError("current_owner_scope_owner_version")
        current = _validated_selected_lease(repo, selected, policy)
        from .reddog_consensus_nonce_custody import current_consensus_nonce_custody
        current_consensus_nonce_custody(owner, thaw_owner_e0_policy(current.policy), repo, time.time())
        record = dict(path=path, repo=repo, owner=canonical_json(owner), boundary=boundary,
            selected=dict(selected), selection=canonical_json(dict(selected)),
            policy=freeze_owner_e0_policy(thaw_owner_e0_policy(current.policy)),
            policy_bytes=canonical_json(thaw_owner_e0_policy(current.policy)),
            thread=threading.get_ident(), pid=os.getpid(), wall=0, mono=0)
        with _SCOPE_LOCK:
            _LIVE_SCOPES[scope] = record
        try:
            _scope_admission(scope, owner_config_path=path, repo_root=repo)
            yield scope
            _scope_admission(scope, owner_config_path=path, repo_root=repo)
        finally:
            with _SCOPE_LOCK:
                _LIVE_SCOPES.pop(scope, None)
