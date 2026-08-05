"""Read-only binding for the authenticated current signer generation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

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
    run_packet_digest: str | None = None
    selection_expires_at: int | None = None
    authority_granted: bool = False
    effect_capability_issued: bool = False
    no_repo_mutation_performed: bool = True
    no_holoindex_reindex_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def verify_signer_current_generation_runtime_binding(
    *,
    repo_root: Path | str,
    runtime_root: Path | str,
    now_epoch: int,
    run_packet_path: Path | str | None = None,
) -> SignerCurrentGenerationRuntimeBinding:
    """Verify root-owned current selection against trusted time and bytes."""

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
            owner_config_path=_required_absolute_path(
                packet.get("owner_authority_config_path")
            ),
            repo_root=repo,
            config_path=_required_absolute_path(packet.get("config_path")),
            run_packet_path=packet_path,
        )
        selection = dict(boundary.consume(capability))
        values = _validated_values(
            selection=selection,
            packet=packet,
            packet_path=packet_path,
            packet_raw=packet_raw,
            repo=repo,
            runtime=runtime,
            now_epoch=now_epoch,
        )
        return SignerCurrentGenerationRuntimeBinding(
            accepted=True,
            rejection_reasons=(),
            receipt_id=_digest(values),
            **values,
        )
    except Exception:
        return SignerCurrentGenerationRuntimeBinding(
            accepted=False,
            rejection_reasons=(SIGNER_CURRENT_GENERATION_BINDING_REJECTED,),
        )


def _validated_values(
    *,
    selection: Mapping[str, Any],
    packet: Mapping[str, Any],
    packet_path: Path,
    packet_raw: bytes,
    repo: Path,
    runtime: Path,
    now_epoch: int,
) -> dict[str, Any]:
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
    generation, revision, expires_at = _validated_selection_identity(
        selection, now_epoch=now_epoch
    )
    _validate_manifest_freshness(
        selection=selection,
        repo=repo,
        runtime=runtime,
        now_epoch=now_epoch,
    )
    return {
        "manifest_id": str(selection["manifest_id"]),
        "artifact_generation_digest": str(
            selection["artifact_generation_digest"]
        ),
        "generation": generation,
        "generation_revision": revision,
        "owner_config_id": str(selection["owner_config_id"]),
        "config_digest": str(selection["config_digest"]),
        "config_raw_digest": str(selection["config_raw_digest"]),
        "run_packet_digest": str(selection["run_packet_digest"]),
        "selection_expires_at": expires_at,
    }


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
    "verify_signer_current_generation_runtime_binding",
]
