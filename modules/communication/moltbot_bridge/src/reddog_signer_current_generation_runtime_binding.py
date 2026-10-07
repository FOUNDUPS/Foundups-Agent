"""Read-only binding for the authenticated current signer generation."""

from __future__ import annotations

import hashlib
import json
from contextlib import ExitStack, contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterator, Mapping

from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    DEFAULT_MAX_TTL_SECONDS,
    is_sha256,
    validate_freshness,
    validate_signed_payload,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_io import (
    MANIFEST_DIRECTORY_NAME,
)
from modules.communication.moltbot_bridge.src.reddog_signer_system_service_manifest_selection_loader import (
    load_system_service_manifest_selection,
    load_system_service_signer_identity,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_config_rehydration import (
    rehydrate_signer_socket_service_runtime_config,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    secure_read_confined_bytes,
    validate_runtime_artifact_path,
    validate_runtime_root_path,
)


SIGNER_CURRENT_GENERATION_BINDING_SCHEMA_VERSION = (
    "reddog_signer_current_generation_runtime_binding.v1"
)
SIGNER_CURRENT_GENERATION_BINDING_REJECTED = (
    "signer_current_generation_runtime_binding_rejected"
)
MAX_RUNTIME_ARTIFACT_BYTES = 256 * 1024


@dataclass(frozen=True)
class SignerCurrentGenerationRuntimeBinding:
    """Audit evidence only; this result grants no effect authority."""

    accepted: bool
    rejection_reasons: tuple[str, ...]
    receipt_id: str | None = None
    manifest_id: str | None = None
    artifact_generation_digest: str | None = None
    generation: int | None = None
    generation_revision: str | None = None
    owner_config_id: str | None = None
    config_digest: str | None = None
    config_raw_digest: str | None = None
    run_packet_id: str | None = None
    run_packet_digest: str | None = None
    session_id: str | None = None
    socket_path_digest: str | None = None
    signer_profile_id: str | None = None
    signer_public_key: str | None = None
    key_epoch: str | None = None
    selection_expires_at: int | None = None
    authority_granted: bool = False
    effect_capability_issued: bool = False
    no_repo_mutation_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    principal_binding_digest: str | None = None
    signer_uid: int | None = None
    signer_gid: int | None = None
    manifest_expires_at: int | None = None
    model_work_order_digest: str | None = None
    model_artifact_pair_digest: str | None = None
    model_valid_until: int | None = None
    memex_work_order_digest: str | None = None
    memex_evidence_digest: str | None = None
    memex_valid_until: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SignerCurrentGenerationRuntimeAuthority:
    """Resolve current generation only from root-owned runtime artifacts."""

    repo_root: Path
    runtime_root: Path

    def lease(self, *, now_epoch: int, signer_profile_id: str):
        """Keep the current generation fenced through a local consumer commit."""
        return _lease_current_generation_runtime_binding(
            repo_root=self.repo_root, runtime_root=self.runtime_root,
            now_epoch=now_epoch, signer_profile_id=signer_profile_id,
        )

    def resolve(
        self, *, now_epoch: int, signer_profile_id: str
    ) -> SignerCurrentGenerationRuntimeBinding:
        return verify_signer_current_generation_runtime_binding(
            repo_root=self.repo_root,
            runtime_root=self.runtime_root,
            now_epoch=now_epoch,
            signer_profile_id=signer_profile_id,
        )


def verify_signer_current_generation_runtime_binding(
    *,
    repo_root: Path | str,
    runtime_root: Path | str,
    now_epoch: int,
    run_packet_path: Path | str | None = None,
    signer_profile_id: str | None = None,
    principal_identity: Mapping[str, Any] | None = None,
    principal_work_authority: Mapping[str, Any] | None = None,
    include_process_identity: bool = False,
    model_work_order: Mapping[str, Any] | None = None,
    trusted_now_epoch=None,
    retained_proposal_inputs=None, revoked_key_epochs=frozenset(),
) -> SignerCurrentGenerationRuntimeBinding:
    """Verify root-owned current selection against trusted time and bytes."""
    try:
        with _lease_current_generation_runtime_binding(
            repo_root=repo_root, runtime_root=runtime_root, now_epoch=now_epoch,
            run_packet_path=run_packet_path, signer_profile_id=signer_profile_id,
            principal_identity=principal_identity, principal_work_authority=principal_work_authority,
            include_process_identity=include_process_identity,
            model_work_order=model_work_order, trusted_now_epoch=trusted_now_epoch,
            retained_proposal_inputs=retained_proposal_inputs, revoked_key_epochs=revoked_key_epochs,
        ) as binding:
            return binding
    except Exception:
        return SignerCurrentGenerationRuntimeBinding(
            accepted=False,
            rejection_reasons=(SIGNER_CURRENT_GENERATION_BINDING_REJECTED,),
        )


@contextmanager
def _lease_current_generation_runtime_binding(
    *, repo_root: Path | str, runtime_root: Path | str, now_epoch: int,
    run_packet_path: Path | str | None = None,
    signer_profile_id: str | None = None,
    principal_identity: Mapping[str, Any] | None = None,
    principal_work_authority: Mapping[str, Any] | None = None,
    include_process_identity: bool = False,
    model_work_order: Mapping[str, Any] | None = None, trusted_now_epoch=None,
    retained_proposal_inputs=None, revoked_key_epochs=frozenset(),
) -> Iterator[SignerCurrentGenerationRuntimeBinding]:
    with ExitStack() as stack:
        try:
            if type(now_epoch) is not int or now_epoch <= 0:
                raise ValueError("trusted_time_invalid")
            repo = Path(repo_root).resolve()
            runtime = validate_runtime_root_path(runtime_root, repo_root=repo)
            packet_path = validate_runtime_artifact_path(
                run_packet_path or runtime / "signer_service_run_packet.json",
                repo_root=repo,
                allowed_root=runtime,
            )
            packet_raw, _ = secure_read_confined_bytes(
                packet_path,
                allowed_root=runtime,
                max_bytes=MAX_RUNTIME_ARTIFACT_BYTES,
            )
            packet = _mapping(packet_raw)
            capability, boundary = load_system_service_manifest_selection(
                owner_config_path=_required_absolute_path(packet.get("owner_authority_config_path")),
                repo_root=repo,
                config_path=_required_absolute_path(packet.get("config_path")),
                run_packet_path=packet_path,
            )
            selection = stack.enter_context(boundary._lease_current(capability))
            values = _validated_values(
                selection=selection, packet=packet, packet_path=packet_path,
                packet_raw=packet_raw, repo=repo, runtime=runtime, now_epoch=now_epoch,
                signer_profile_id=signer_profile_id or ("reddog-work-authority" if retained_proposal_inputs is not None else None),
            )
            if principal_identity is not None or principal_work_authority is not None:
                values["principal_binding_digest"] = _validated_principal_digest(
                    repo, selection, principal_identity, principal_work_authority)
            if include_process_identity is True:
                values.update(_process_identity_values(repo, packet, selection))
            trusted_now_epoch = _evidence_clock(trusted_now_epoch, now_epoch)
            if model_work_order is not None:
                values.update(_validated_model_values(repo, packet, selection, model_work_order,
                    principal_work_authority, trusted_now_epoch, now_epoch))
            if retained_proposal_inputs is not None:
                values.update(_validated_memex_values(repo, runtime, packet_path, packet_raw,
                    packet, selection, values, retained_proposal_inputs, model_work_order,
                    principal_work_authority, principal_identity, trusted_now_epoch, now_epoch, revoked_key_epochs))
            binding = _accepted_binding(values)
        except Exception:
            stack.close()
            binding = SignerCurrentGenerationRuntimeBinding(
                accepted=False,
                rejection_reasons=(SIGNER_CURRENT_GENERATION_BINDING_REJECTED,),
            )
        yield binding


def _evidence_clock(clock, started):
    last = [started]
    def read():
        now = clock()
        if type(now) is not int or now < last[0]:
            raise ValueError("current_evidence_clock_reversed")
        last[0] = now
        return now
    return read


def _validated_memex_values(repo, runtime, packet_path, packet_raw, packet, selected,
    signer, bundle, work, authority, identity, clock, started, revoked):
    from .reddog_architect_proposal_verified_authority import (
        snapshot_retained_architect_proposal_inputs, verify_retained_proposal_work_binding,
    )
    from .reddog_signer_owner_e0_principal_authority import load_current_generation_principal_key_resolver
    from .reddog_work_order_binding import canonical_full_work_order_digest
    try:
        inputs = snapshot_retained_architect_proposal_inputs(bundle)
        authority_digest = _digest({"identity": identity, "authority": authority})
        args = dict(selection=selected, packet=packet, packet_path=packet_path,
                    packet_raw=packet_raw, repo=repo, runtime=runtime)
        raw = _read_bound_config(**args)
        config = rehydrate_signer_socket_service_runtime_config(repo, runtime,
            dict(_mapping(raw)), expected_config_digest=selected["config_digest"])
        resolver = load_current_generation_principal_key_resolver(repo_root=repo, selection=selected)
        checked_at = clock()
        if type(checked_at) is not int or checked_at < started:
            raise ValueError("memex_trusted_clock_invalid")
        result = verify_retained_proposal_work_binding(inputs, work_order=work,
            work_authority=authority, principal_identity=identity, signer_identity=signer, signer_runtime_config=config,
            principal_key_resolver=resolver, now_epoch=checked_at, revoked_key_epochs=revoked)
        # Re-read manifest-bound artifacts; checked input cannot survive replacement.
        _read_bound_config(**args)
        load_current_generation_principal_key_resolver(repo_root=repo, selection=selected)
        final = clock()
        if (type(final) is not int or final < checked_at
                or final >= min(result["memex_valid_until"], selected["selection_expires_at"], selected["manifest_expires_at"])
                or canonical_full_work_order_digest(work) != result["memex_work_order_digest"]
                or _digest(snapshot_retained_architect_proposal_inputs(bundle)) != result["memex_evidence_digest"]
                or _digest({"identity": identity, "authority": authority}) != authority_digest):
            raise ValueError("memex_evidence_no_longer_current")
        return result
    except Exception:
        return {}


def _validated_model_values(repo, packet, selected, work, authority, clock, started):
    from . import reddog_signer_system_service_manifest_selection_loader as owner_loader
    from .reddog_work_order_binding import canonical_full_work_order_digest
    from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_verified_admission import (
        consume_verified_runtime_binding_capability, discard_verified_runtime_binding_capability,
        verified_runtime_binding_receipt,
    )
    capability, last_time = None, [started]
    def monotonic_clock():
        value = clock()
        if type(value) is not int or value < last_time[0]:
            raise ValueError("model_trusted_clock_reversed")
        last_time[0] = value
        return value
    try:
        work_digest, pair = _model_work_snapshot(work, authority)
        model_selection, model_binding = pair.values()
        owner_path = _required_absolute_path(packet["owner_authority_config_path"])
        owner = owner_loader._load_owner_config(owner_path, repo=repo)
        if owner["config_id"] != selected["owner_config_id"]:
            raise ValueError("model_selected_owner_mismatch")
        verifier = owner_loader.load_system_service_model_runtime_verifier(
            owner_config_path=owner_path, repo_root=repo,
            expected_owner_config_id=selected["owner_config_id"], trusted_now_epoch=monotonic_clock)
        args = dict(selection=model_selection, binding=model_binding)
        capability = verifier.verify(**args)
        receipt = verified_runtime_binding_receipt(model_binding)
        if consume_verified_runtime_binding_capability(capability, receipt=receipt, **args) != receipt or receipt is None:
            raise ValueError("model_capability_not_consumed")
        checked_at = verifier.trusted_now_epoch()
        deadline = min(receipt.valid_until, owner["model_verifier_authority"]["expires_at"])
        if (type(checked_at) is not int or checked_at < receipt.verified_at or checked_at >= deadline
                or checked_at >= selected["selection_expires_at"] or checked_at >= selected["manifest_expires_at"]
                or canonical_full_work_order_digest(work) != work_digest):
            raise ValueError("model_evidence_no_longer_current")
        return dict(model_work_order_digest=work_digest, model_artifact_pair_digest=_digest(pair),
                    model_valid_until=deadline)
    except Exception:
        # Model rejection cannot certify either model gate or erase other evidence.
        return {}
    finally:
        discard_verified_runtime_binding_capability(capability)


def _model_work_snapshot(work, authority):
    from .reddog_work_order_binding import canonical_full_work_order_digest
    from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_digest import canonical_model_runtime_binding_digest
    snapshot = json.loads(json.dumps(work, allow_nan=False))
    work_digest = canonical_full_work_order_digest(snapshot)
    if authority.get("work_order_digest") != work_digest:
        raise ValueError("model_work_order_not_authorized")
    context = snapshot.get("operational_context_binding", {})
    pair = {}
    for name in ("model_selection_receipt", "model_runtime_binding_receipt"):
        candidates = [container[name] for container in (snapshot, context) if name in container]
        if not candidates or any(type(item) is not dict or item != candidates[0] for item in candidates):
            raise ValueError("model_artifact_pair_missing_or_ambiguous")
        pair[name] = candidates[0]
    model_selection, model_binding = pair.values()
    expected = dict(model_selection_receipt_id=model_selection["receipt_id"],
        model_selection_digest=_digest(model_selection),
        model_runtime_binding_receipt_id=model_binding["receipt_id"],
        model_runtime_binding_digest=canonical_model_runtime_binding_digest(model_binding))
    if any(snapshot.get(key) != value or authority.get(key) != value for key, value in expected.items()):
        raise ValueError("model_signed_work_binding_mismatch")
    return work_digest, pair


def _process_identity_values(repo, packet, selection):
    uid, gid = load_system_service_signer_identity(
        owner_config_path=_required_absolute_path(packet["owner_authority_config_path"]),
        repo_root=repo, expected_owner_config_id=selection["owner_config_id"])
    return {"signer_uid": uid, "signer_gid": gid}


def _validated_principal_digest(repo, selection, identity, work_authority):
    from .reddog_signer_owner_e0_principal_authority import verify_current_generation_principal_identity

    # Bind exactly the value checked, even when caller dictionaries mutate during IO.
    serialized = json.dumps({"identity": identity, "work_authority": work_authority},
                            sort_keys=True, allow_nan=False)
    snapshot = json.loads(serialized)
    verify_current_generation_principal_identity(
        repo_root=repo, selection=selection, identity=snapshot["identity"],
        work_authority=snapshot["work_authority"])
    if serialized != json.dumps({"identity": identity, "work_authority": work_authority},
                                sort_keys=True, allow_nan=False):
        raise ValueError("current_principal_binding_changed")
    return _digest(snapshot)


def _validated_values(
    *,
    selection: Mapping[str, Any],
    packet: Mapping[str, Any],
    packet_path: Path,
    packet_raw: bytes,
    repo: Path,
    runtime: Path,
    now_epoch: int,
    signer_profile_id: str | None,
) -> dict[str, Any]:
    config_raw = _read_bound_config(
        selection=selection,
        packet=packet,
        packet_path=packet_path,
        packet_raw=packet_raw,
        repo=repo,
        runtime=runtime,
    )
    generation, revision, expires_at = _validated_selection_identity(
        selection, now_epoch=now_epoch
    )
    _validate_manifest_freshness(
        selection=selection, repo=repo, runtime=runtime, now_epoch=now_epoch
    )
    signer_identity = _selected_signer_identity(
        config_raw=config_raw,
        config_digest=str(selection["config_digest"]),
        repo=repo,
        runtime=runtime,
        signer_profile_id=signer_profile_id,
    )
    return _binding_values(
        selection=selection,
        packet=packet,
        generation=generation,
        revision=revision,
        expires_at=expires_at,
        signer_identity=signer_identity,
    )


def _read_bound_config(
    *,
    selection: Mapping[str, Any],
    packet: Mapping[str, Any],
    packet_path: Path,
    packet_raw: bytes,
    repo: Path,
    runtime: Path,
) -> bytes:
    config_path = validate_runtime_artifact_path(
        packet.get("config_path"),
        repo_root=repo,
        allowed_root=runtime,
    )
    config_raw, _ = secure_read_confined_bytes(
        config_path,
        allowed_root=runtime,
        max_bytes=MAX_RUNTIME_ARTIFACT_BYTES,
    )
    expected = {
        "repo_root": str(repo),
        "runtime_root": str(runtime),
        "config_path": str(config_path),
        "run_packet_path": str(packet_path),
        "config_digest": packet.get("config_digest"),
        "config_raw_digest": _bytes_digest(config_raw),
        "run_packet_digest": _bytes_digest(packet_raw),
    }
    if any(
        str(selection.get(key) or "") != str(value)
        for key, value in expected.items()
    ):
        raise ValueError("selection_artifact_binding_mismatch")
    return config_raw


def _accepted_binding(
    values: Mapping[str, Any],
) -> SignerCurrentGenerationRuntimeBinding:
    return SignerCurrentGenerationRuntimeBinding(
        accepted=True,
        rejection_reasons=(),
        receipt_id=_digest(values),
        **dict(values),
    )


def _binding_values(
    *,
    selection: Mapping[str, Any],
    packet: Mapping[str, Any],
    generation: int,
    revision: str,
    expires_at: int,
    signer_identity: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "manifest_id": str(selection["manifest_id"]),
        "artifact_generation_digest": str(selection["artifact_generation_digest"]),
        "generation": generation,
        "generation_revision": revision,
        "owner_config_id": str(selection["owner_config_id"]),
        "config_digest": str(selection["config_digest"]),
        "config_raw_digest": str(selection["config_raw_digest"]),
        "run_packet_digest": str(selection["run_packet_digest"]),
        **_runtime_identity(packet),
        **signer_identity,
        "selection_expires_at": expires_at,
        "manifest_expires_at": selection["manifest_expires_at"],
    }


def _selected_signer_identity(
    *,
    config_raw: bytes,
    config_digest: str,
    repo: Path,
    runtime: Path,
    signer_profile_id: str | None,
) -> dict[str, str | None]:
    if signer_profile_id is None:
        return {
            "signer_profile_id": None,
            "signer_public_key": None,
            "key_epoch": None,
        }
    config = rehydrate_signer_socket_service_runtime_config(
        repo,
        runtime,
        dict(_mapping(config_raw)),
        expected_config_digest=config_digest,
    )
    if config is None:
        raise ValueError("signer_runtime_config_invalid")
    profiles = (
        config.key_provider_profiles
        if config.key_provider_profiles
        else (config.key_provider_profile,)
    )
    selected = next(
        (
            profile
            for profile in profiles
            if profile is not None
            and _profile_value(profile, "signer_profile_id") == signer_profile_id
        ),
        None,
    )
    if selected is None:
        raise ValueError("signer_profile_not_current")
    return {
        "signer_profile_id": signer_profile_id,
        "signer_public_key": _profile_value(selected, "expected_public_key"),
        "key_epoch": _profile_value(selected, "expected_key_epoch"),
    }


def _profile_value(profile: object, field: str) -> str:
    value = (
        profile.get(field)
        if isinstance(profile, Mapping)
        else getattr(profile, field, None)
    )
    if not isinstance(value, str) or not value or not value.isascii():
        raise ValueError("signer_profile_value_invalid")
    return value


def _validate_manifest_freshness(
    *,
    selection: Mapping[str, Any],
    repo: Path,
    runtime: Path,
    now_epoch: int,
) -> None:
    manifest_id = str(selection.get("manifest_id") or "")
    if not is_sha256(manifest_id):
        raise ValueError("selection_manifest_invalid")
    path = validate_runtime_artifact_path(
        runtime / MANIFEST_DIRECTORY_NAME / f"{manifest_id[7:]}.json",
        repo_root=repo,
        allowed_root=runtime,
    )
    raw, _ = secure_read_confined_bytes(
        path,
        allowed_root=runtime,
        max_bytes=MAX_RUNTIME_ARTIFACT_BYTES,
    )
    payload = validate_signed_payload(_mapping(raw))
    if payload["manifest_id"] != manifest_id:
        raise ValueError("selection_manifest_mismatch")
    validate_freshness(
        payload,
        now_epoch=now_epoch,
        max_ttl_seconds=DEFAULT_MAX_TTL_SECONDS,
    )


def _runtime_identity(packet: Mapping[str, Any]) -> dict[str, str]:
    return {
        "run_packet_id": str(packet["run_packet_id"]),
        "session_id": str(packet["session_id"]),
        "socket_path_digest": _text_digest(str(packet["socket_path"])),
    }


def _validated_selection_identity(
    selection: Mapping[str, Any], *, now_epoch: int
) -> tuple[int, str, int]:
    issued_at = selection.get("selection_issued_at")
    expires_at = selection.get("selection_expires_at")
    generation = selection.get("generation")
    if (
        type(issued_at) is not int
        or type(expires_at) is not int
        or type(generation) is not int
        or generation < 1
        or issued_at > now_epoch
        or now_epoch >= expires_at
    ):
        raise ValueError("selection_freshness_invalid")
    digest_fields = (
        "manifest_id",
        "artifact_generation_digest",
        "owner_config_id",
        "config_digest",
        "config_raw_digest",
        "run_packet_digest",
    )
    if any(not is_sha256(selection.get(field)) for field in digest_fields):
        raise ValueError("selection_digest_invalid")
    revision = str(selection.get("generation_revision") or "")
    if not revision or any(ord(char) >= 128 for char in revision):
        raise ValueError("selection_revision_invalid")
    return generation, revision, expires_at


def _mapping(raw: Any) -> Mapping[str, Any]:
    value = (
        json.loads(raw.decode("utf-8", errors="strict"))
        if isinstance(raw, bytes)
        else raw
    )
    if not isinstance(value, Mapping):
        raise ValueError("runtime_artifact_not_mapping")
    return value


def _required_absolute_path(value: Any) -> Path:
    path = Path(str(value or ""))
    if not path.is_absolute():
        raise ValueError("runtime_path_invalid")
    return path.resolve()


def _bytes_digest(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _text_digest(value: str) -> str:
    return _bytes_digest(value.encode("utf-8"))


def _digest(value: Mapping[str, Any]) -> str:
    raw = json.dumps(
        {
            "schema_version": SIGNER_CURRENT_GENERATION_BINDING_SCHEMA_VERSION,
            **dict(value),
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("ascii")
    return _bytes_digest(raw)


__all__ = [
    "SIGNER_CURRENT_GENERATION_BINDING_REJECTED",
    "SIGNER_CURRENT_GENERATION_BINDING_SCHEMA_VERSION",
    "SignerCurrentGenerationRuntimeBinding",
    "SignerCurrentGenerationRuntimeAuthority",
    "verify_signer_current_generation_runtime_binding",
]
