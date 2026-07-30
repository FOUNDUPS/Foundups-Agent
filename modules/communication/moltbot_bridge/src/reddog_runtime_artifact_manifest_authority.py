"""Closure-confined authority for RedDog runtime-artifact manifests."""

from __future__ import annotations

from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Protocol, Sequence
from weakref import WeakKeyDictionary

from modules.communication.moltbot_bridge.src.reddog_architect_fix_publication_effect_binding import (
    committed_publication_effect_binding,
)
from modules.communication.moltbot_bridge.src.reddog_authoritative_work_state_store import (
    AuthoritativeWorkStateStore,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    DEFAULT_MAX_TTL_SECONDS,
    digest,
    is_revision,
    is_sha256,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_json_read import (
    read_reddog_runtime_json_mapping,
)
from modules.communication.moltbot_bridge.src.reddog_work_authority_digest import (
    canonical_work_authority_digest,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    WorkAuthorityVerificationPhase,
    verify_delegated_work_authority,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    validate_runtime_root_path,
)


class RuntimeArtifactManifestAuthority(Protocol):
    """Opaque capability shape; only its issuing boundary may consume it."""


class RuntimeArtifactManifestAuthorityBoundary(Protocol):
    def issue(
        self,
        *,
        identity: Mapping[str, Any],
        work_authority: Mapping[str, Any],
        queue_item_id: str,
        now_epoch: int,
    ) -> RuntimeArtifactManifestAuthority: ...

    def require(
        self, value: object
    ) -> Mapping[str, Any]: ...


class _ClosureBoundary:
    __slots__ = ("_issue", "_require")

    def __init__(self, issue: Any, require: Any) -> None:
        self._issue = issue
        self._require = require

    def issue(
        self,
        *,
        identity: Mapping[str, Any],
        work_authority: Mapping[str, Any],
        queue_item_id: str,
        now_epoch: int,
    ) -> RuntimeArtifactManifestAuthority:
        return self._issue(
            identity=identity,
            work_authority=work_authority,
            queue_item_id=queue_item_id,
            now_epoch=now_epoch,
        )

    def require(self, value: object) -> Mapping[str, Any]:
        return self._require(value)


def create_runtime_artifact_manifest_authority_boundary(
    *,
    repo_root: Path | str,
    runtime_root: Path | str,
    work_state_store: AuthoritativeWorkStateStore,
    signature_verifier: Any, principal_key_resolver: Any,
    nonce_store: Any, snapshot_resolver: Any, revocation_oracle: Any,
    required_valve_state: str,
    forbidden_operations: Sequence[str] = (),
    revoked_key_epochs: Sequence[str] = (),
    leeway_s: int = 60,
) -> RuntimeArtifactManifestAuthorityBoundary:
    """Build one authority boundary pinned to durable state and trust inputs."""

    root = Path(repo_root).resolve()
    runtime = validate_runtime_root_path(runtime_root, repo_root=root)
    settings = {
        "root": root, "runtime": runtime, "store": work_state_store,
        "signature_verifier": signature_verifier,
        "principal_key_resolver": principal_key_resolver,
        "nonce_store": nonce_store, "snapshot_resolver": snapshot_resolver,
        "revocation_oracle": revocation_oracle,
        "required_valve_state": required_valve_state,
        "forbidden_operations": tuple(forbidden_operations),
        "revoked_key_epochs": tuple(revoked_key_epochs), "leeway_s": leeway_s,
    }
    return _make_capability_boundary(settings)


def _make_capability_boundary(
    settings: Mapping[str, Any],
) -> RuntimeArtifactManifestAuthorityBoundary:
    seal = object()
    issued: WeakKeyDictionary[object, str] = WeakKeyDictionary()
    capability_type = _capability_type(seal)
    require = _capability_require(capability_type, seal, issued)
    issue = _capability_issue(settings, capability_type, issued)
    return _ClosureBoundary(issue, require)


def _capability_type(seal: object) -> type:
    class Capability:
        __slots__ = ("_values", "_seal", "__weakref__")

        def __init__(self, values: Mapping[str, Any]) -> None:
            object.__setattr__(
                self, "_values", MappingProxyType(dict(values))
            )
            object.__setattr__(self, "_seal", seal)

        def __getattr__(self, name: str) -> Any:
            values = object.__getattribute__(self, "_values")
            if name not in values:
                raise AttributeError(name)
            return values[name]

        def __setattr__(self, name: str, value: Any) -> None:
            del name, value
            raise AttributeError("manifest_authority_immutable")

        def __copy__(self):
            raise TypeError("manifest_authority_not_copyable")

        def __deepcopy__(self, memo: Any):
            del memo
            raise TypeError("manifest_authority_not_copyable")

        def __reduce__(self):
            raise TypeError("manifest_authority_not_serializable")

    return Capability


def _capability_require(
    capability_type: type,
    seal: object,
    issued: WeakKeyDictionary[object, str],
) -> Any:
    def require(value: object) -> Mapping[str, Any]:
        if not isinstance(value, capability_type):
            raise ValueError("manifest_authority_unverified")
        values = object.__getattribute__(value, "_values")
        expected = issued.get(value)
        if (
            object.__getattribute__(value, "_seal") is not seal
            or expected is None
            or expected != _fingerprint(values)
        ):
            raise ValueError("manifest_authority_unverified")
        return values

    return require


def _capability_issue(
    settings: Mapping[str, Any],
    capability_type: type,
    issued: WeakKeyDictionary[object, str],
) -> Any:
    def issue(
        *,
        identity: Mapping[str, Any],
        work_authority: Mapping[str, Any],
        queue_item_id: str,
        now_epoch: int,
    ) -> RuntimeArtifactManifestAuthority:
        state = settings["store"].load()
        runtime = settings["runtime"]
        profile = _read_runtime(runtime, "authority_profile.json")
        config = _read_runtime(runtime, "signer_service_config.json")
        identity = _mapping(identity)
        work = _mapping(work_authority)
        queue_id = str(queue_item_id)
        _verify_work_authority(
            work=work, identity=identity, now_epoch=now_epoch,
            signature_verifier=settings["signature_verifier"],
            principal_key_resolver=settings["principal_key_resolver"],
            nonce_store=settings["nonce_store"],
            snapshot_resolver=settings["snapshot_resolver"],
            revocation_oracle=settings["revocation_oracle"],
            required_valve_state=settings["required_valve_state"],
            forbidden_operations=settings["forbidden_operations"],
            revoked_key_epochs=settings["revoked_key_epochs"],
            leeway_s=settings["leeway_s"],
        )
        values = _verified_values(
            root=settings["root"], runtime=runtime, state=state, profile=profile,
            config=config, identity=identity, work=work,
            queue_item_id=queue_id,
        )
        capability = capability_type(values)
        issued[capability] = _fingerprint(values)
        return capability

    return issue


def _verified_values(**values: Any) -> Mapping[str, Any]:
    state = _mapping(values["state"])
    profile = _mapping(values["profile"])
    config = _mapping(values["config"])
    identity = _mapping(values["identity"])
    work = _mapping(values["work"])
    queue_id = str(values["queue_item_id"])
    _validate_signed_bindings(profile, identity, work)
    revision = _validate_work_state(state, profile, queue_id)
    _validate_signer_config(config, profile)
    publication = _verified_publication(state, profile, work, queue_id)
    return {
        "repo_root": values["root"], "runtime_root": values["runtime"],
        "issuer_principal_id": identity["principal_id"],
        "signer_public_key": identity["reddog_public_key"],
        "key_epoch": work["key_epoch"],
        "consensus_receipt_digest": work["consensus_receipt_digest"],
        "authority_profile_digest": digest(profile),
        "authority_profile_source_receipt_id": profile[
            "authority_profile_source_receipt_id"
        ],
        "signer_service_config_digest": digest(config),
        "queue_item_id": queue_id, "work_state_revision": revision,
        "work_authority_digest": canonical_work_authority_digest(work),
        "publication_receipt_id": publication["publication_id"],
        "publication_binding_digest": publication["binding_digest"],
        "max_ttl_seconds": DEFAULT_MAX_TTL_SECONDS,
    }


def _verify_work_authority(**values: Any) -> None:
    result = verify_delegated_work_authority(
        work_authority=values["work"], identity=values["identity"],
        signature_verifier=values["signature_verifier"],
        principal_key_resolver=values["principal_key_resolver"],
        nonce_store=values["nonce_store"],
        snapshot_resolver=values["snapshot_resolver"],
        revocation_oracle=values["revocation_oracle"],
        now=int(values["now_epoch"]),
        required_valve_state=values["required_valve_state"],
        forbidden_operations=tuple(values["forbidden_operations"]),
        revoked_key_epochs=tuple(values["revoked_key_epochs"]),
        leeway_s=int(values["leeway_s"]),
        verification_phase=WorkAuthorityVerificationPhase.PREFLIGHT_NON_CONSUMING,
    )
    if result.accepted is not True:
        raise ValueError("manifest_authority_rejected")


def _verified_publication(
    state: Mapping[str, Any], profile: Mapping[str, Any],
    work: Mapping[str, Any], queue_item_id: str,
) -> Mapping[str, Any]:
    binding = _mapping(profile.get("operational_context_binding"))
    claim_id = str(binding.get("claim_id") or "")
    effect = committed_publication_effect_binding(
        state, profile, queue_item_id=queue_item_id, claim_id=claim_id
    )
    if (
        not effect
        or work.get("architect_fix_publication_receipt_id")
        != effect.get("publication_id")
        or work.get("architect_fix_publication_binding_digest")
        != effect.get("binding_digest")
    ):
        raise ValueError("manifest_publication_binding_invalid")
    return effect


def _validate_signed_bindings(
    profile: Mapping[str, Any], identity: Mapping[str, Any],
    work: Mapping[str, Any],
) -> None:
    expected = {
        "principal_id": identity.get("principal_id"),
        "reddog_id": identity.get("reddog_id"),
        "reddog_public_key": identity.get("reddog_public_key"),
        "key_epoch": work.get("key_epoch"),
        "consensus_receipt_digest": work.get("consensus_receipt_digest"),
        "work_order_id": work.get("work_order_id"),
        "repo_full_name": work.get("repo_full_name"),
        "foundup_id": work.get("foundup_id"),
        "requested_operation": work.get("requested_operation"),
        "permission_snapshot_digest": work.get(
            "permission_snapshot_digest"
        ),
        "valve_state_required": work.get("valve_state_required"),
        "allowed_paths": work.get("allowed_paths"),
        "denied_paths": work.get("denied_paths"),
    }
    if any(profile.get(name) != value for name, value in expected.items()):
        raise ValueError("manifest_authority_profile_binding_mismatch")
    if (
        identity.get("principal_id") != work.get("principal_id")
        or identity.get("reddog_id") != work.get("reddog_id")
        or identity.get("reddog_public_key")
        != work.get("signer_public_key")
        or not is_sha256(work.get("consensus_receipt_digest"))
        or not is_sha256(profile.get("authority_profile_source_receipt_id"))
    ):
        raise ValueError("manifest_authority_identity_binding_mismatch")


def _validate_work_state(
    state: Mapping[str, Any], profile: Mapping[str, Any], queue_item_id: str,
) -> str:
    revision = str(state.get("revision") or "")
    body = dict(state)
    body.pop("revision", None)
    binding = _mapping(profile.get("operational_context_binding"))
    matches = [
        item for item in state.get("wre_queue_items") or ()
        if isinstance(item, Mapping)
        and item.get("queue_item_id") == queue_item_id
    ]
    if (
        not is_revision(revision)
        or revision != digest(body)[7:]
        or len(matches) != 1
        or binding.get("queue_item_id") != queue_item_id
    ):
        raise ValueError("manifest_work_state_binding_invalid")
    return revision


def _validate_signer_config(
    config: Mapping[str, Any], profile: Mapping[str, Any],
) -> None:
    policy = _mapping(config.get("control_loop_authority_policy"))
    expected = {
        "issuer_principal_id": profile.get("principal_id"),
        "signer_public_key": profile.get("reddog_public_key"),
        "key_epoch": profile.get("key_epoch"),
        "consensus_receipt_digest": profile.get(
            "consensus_receipt_digest"
        ),
        "authority_profile_digest": digest(profile),
        "authority_profile_source_receipt_id": profile.get(
            "authority_profile_source_receipt_id"
        ),
    }
    if any(policy.get(name) != value for name, value in expected.items()):
        raise ValueError("manifest_signer_policy_mismatch")


def _read_runtime(runtime: Path, filename: str) -> Mapping[str, Any]:
    return read_reddog_runtime_json_mapping(
        runtime / filename, allowed_root=runtime
    )


def _fingerprint(values: Mapping[str, Any]) -> str:
    body = {
        key: str(value) if isinstance(value, Path) else value
        for key, value in values.items()
    }
    return digest(body)


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = [
    "RuntimeArtifactManifestAuthority",
    "RuntimeArtifactManifestAuthorityBoundary",
    "create_runtime_artifact_manifest_authority_boundary",
]
