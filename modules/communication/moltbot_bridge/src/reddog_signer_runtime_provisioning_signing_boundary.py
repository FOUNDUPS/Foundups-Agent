"""Opaque signer binding for atomic RedDog runtime provisioning."""

from __future__ import annotations

import hashlib
import json
from types import MappingProxyType
from typing import Any, Mapping, Protocol
from weakref import WeakKeyDictionary

from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    Ed25519SignatureVerifier,
    decode_ed25519_public_key,
)
from modules.communication.moltbot_bridge.src.reddog_signed_runtime_artifact_manifest import (
    RuntimeArtifactManifestSigningContext,
)


VERIFIER_BACKEND_ID = "reddog-ed25519-verifier.v1"


class SignerRuntimeProvisioningSigningBoundary(Protocol):
    """Marker protocol for the closure-confined signing boundary."""


class _Boundary:
    __slots__ = ("__weakref__",)


class _Capability:
    __slots__ = ("__weakref__",)

    def __copy__(self):
        raise TypeError("signer_runtime_signing_capability_not_copyable")

    def __deepcopy__(self, memo: Any):
        del memo
        raise TypeError("signer_runtime_signing_capability_not_copyable")

    def __reduce__(self):
        raise TypeError("signer_runtime_signing_capability_not_serializable")


def _binding(
    context: RuntimeArtifactManifestSigningContext,
) -> Mapping[str, Any]:
    authority = context.authority_boundary.require(context.authority)
    signer_type = type(context.signer)
    values = {
        "verifier_backend_id": VERIFIER_BACKEND_ID,
        "signer_public_key": authority["signer_public_key"],
        "key_epoch": authority["key_epoch"],
        "authority_tier": context.authority_tier,
        "signer_client_type": (
            f"{signer_type.__module__}.{signer_type.__qualname__}"
        ),
    }
    raw = json.dumps(
        values, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return MappingProxyType(
        {
            **values,
            "binding_digest": (
                "sha256:" + hashlib.sha256(raw.encode("ascii")).hexdigest()
            ),
        }
    )


def _build_tools(verifier_type: type, binding_builder: Any):
    records: WeakKeyDictionary[
        object, tuple[object, Mapping[str, Any]]
    ] = WeakKeyDictionary()
    contexts: WeakKeyDictionary[
        object, RuntimeArtifactManifestSigningContext
    ] = WeakKeyDictionary()

    def create(
        context: RuntimeArtifactManifestSigningContext,
    ) -> tuple[SignerRuntimeProvisioningSigningBoundary, object]:
        if not isinstance(context, RuntimeArtifactManifestSigningContext):
            raise ValueError("signer_runtime_signing_context_invalid")
        authority = context.authority_boundary.require(context.authority)
        if (
            not callable(getattr(context.signer, "sign", None))
            or decode_ed25519_public_key(
                str(authority.get("signer_public_key") or "")
            )
            is None
            or not str(authority.get("key_epoch") or "")
        ):
            raise ValueError("signer_runtime_signing_identity_invalid")
        canonical = RuntimeArtifactManifestSigningContext(
            signer=context.signer,
            signature_verifier=verifier_type(),
            authority=context.authority,
            authority_boundary=context.authority_boundary,
            authority_tier=context.authority_tier,
        )
        boundary = _Boundary()
        capability = _Capability()
        binding = binding_builder(canonical)
        records[capability] = (boundary, binding)
        contexts[capability] = canonical
        return boundary, capability

    def require(
        boundary: object,
        capability: object,
    ) -> RuntimeArtifactManifestSigningContext:
        if type(boundary) is not _Boundary or type(capability) is not _Capability:
            raise ValueError("signer_runtime_signing_capability_unverified")
        record = records.get(capability)
        context = contexts.get(capability)
        if (
            record is None
            or context is None
            or record[0] is not boundary
            or record[1] != binding_builder(context)
        ):
            raise ValueError("signer_runtime_signing_capability_unverified")
        return context

    return create, require


(
    create_signer_runtime_provisioning_signing_boundary,
    require_signer_runtime_provisioning_signing_context,
) = _build_tools(Ed25519SignatureVerifier, _binding)
del _build_tools, Ed25519SignatureVerifier, _binding


__all__ = [
    "SignerRuntimeProvisioningSigningBoundary",
    "VERIFIER_BACKEND_ID",
    "create_signer_runtime_provisioning_signing_boundary",
    "require_signer_runtime_provisioning_signing_context",
]
