"""One-shot verified runtime-topology resolution for RedDog model consumers.

The canonical evidence verifier remains the only authority that can mint the
input capability. This module consumes that capability exactly once, checks an
explicit consumer provider allowlist, and returns an opaque one-shot topology
capability. It does not call a model, probe or launch a server, read secrets,
fall back to another provider, or mutate runtime/repository state.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
import threading
from dataclasses import asdict, dataclass
from typing import Any, Callable, Mapping, Sequence

from .model_runtime_binding import ModelRuntimeBindingDecision
from .model_runtime_binding_digest import canonical_digest
from .model_runtime_binding_evidence_verifier import (
    VerifiedRuntimeBindingArtifact,
    consume_verified_runtime_binding_capability,
    discard_verified_runtime_binding_capability,
)


SCHEMA_VERSION = "verified_model_runtime_topology_resolution.v1"
KNOWN_RUNTIME_PROVIDERS = frozenset(
    {"anthropic", "gemini", "grok", "lm_studio_local", "openai", "openrouter"}
)
MAX_RUNTIME_PROVIDERS = 8
MAX_RUNTIME_ROLES = 8
MAX_RESOLUTION_TTL_SECONDS = 60
TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/-]{0,255}$")


@dataclass(frozen=True)
class RuntimeTopologyEndpoint:
    """Exact provider/model endpoint for one verified RedDog role."""

    role: str
    provider: str
    model_id: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


class RuntimeTopologyCapability:
    """Opaque process-local handle for consuming one resolved topology."""

    __slots__ = ("__token",)

    def __init__(self, token: str) -> None:
        object.__setattr__(self, "_RuntimeTopologyCapability__token", token)

    def __setattr__(self, _name: str, _value: Any) -> None:
        raise TypeError("runtime_topology_capability_is_immutable")

    def __copy__(self) -> "RuntimeTopologyCapability":
        raise TypeError("runtime_topology_capability_copy_forbidden")

    def __deepcopy__(self, _memo: dict[int, Any]) -> "RuntimeTopologyCapability":
        raise TypeError("runtime_topology_capability_copy_forbidden")

    def __reduce_ex__(self, _protocol: int) -> Any:
        raise TypeError("runtime_topology_capability_pickle_forbidden")


@dataclass(frozen=True)
class ResolvedRuntimeTopology:
    """Digest-bound routing metadata plus a non-serializable one-shot handle."""

    receipt_id: str
    runtime_binding_receipt_id: str
    verification_receipt_id: str
    selection_receipt_id: str
    runtime_surface: str
    resolved_at: int
    valid_until: int
    endpoints: tuple[RuntimeTopologyEndpoint, ...]
    capability: RuntimeTopologyCapability
    no_model_call_performed: bool = True
    no_provider_fallback_performed: bool = True
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "receipt_id": self.receipt_id,
            "runtime_binding_receipt_id": self.runtime_binding_receipt_id,
            "verification_receipt_id": self.verification_receipt_id,
            "selection_receipt_id": self.selection_receipt_id,
            "runtime_surface": self.runtime_surface,
            "resolved_at": self.resolved_at,
            "valid_until": self.valid_until,
            "endpoints": [item.to_dict() for item in self.endpoints],
            "no_model_call_performed": True,
            "no_provider_fallback_performed": True,
        }


@dataclass(frozen=True)
class _TopologyAdmission:
    resolution: ResolvedRuntimeTopology
    receipt_digest: str


_CAPABILITY_LOCK = threading.Lock()
_CAPABILITIES: dict[str, tuple[RuntimeTopologyCapability, _TopologyAdmission]] = {}


def resolve_verified_runtime_topology(
    *,
    verified: VerifiedRuntimeBindingArtifact,
    selection: Mapping[str, Any],
    available_providers: Sequence[str],
    now: int,
    expected_runtime_surface: str | None = None,
) -> ResolvedRuntimeTopology:
    """Consume verified binding authority and mint one exact routing topology."""

    if type(verified) is not VerifiedRuntimeBindingArtifact:
        raise ValueError("verified_runtime_binding_artifact_required")
    try:
        endpoints = _admit_verified_binding(
            verified=verified,
            selection=selection,
            providers=_available_provider_set(available_providers),
            now=int(now),
            expected_runtime_surface=expected_runtime_surface,
        )
    except Exception:
        discard_verified_runtime_binding_capability(verified.capability)
        raise
    return _mint_resolution(verified, endpoints, int(now))


def _admit_verified_binding(
    *,
    verified: VerifiedRuntimeBindingArtifact,
    selection: Mapping[str, Any],
    providers: frozenset[str],
    now: int,
    expected_runtime_surface: str | None,
) -> tuple[RuntimeTopologyEndpoint, ...]:
    binding = verified.binding
    verification = verified.verification
    if binding.decision != ModelRuntimeBindingDecision.BOUND:
        raise ValueError("runtime_topology_binding_not_bound")
    if expected_runtime_surface is not None and binding.runtime_surface != _token(
        "expected_runtime_surface", expected_runtime_surface
    ):
        raise ValueError("runtime_topology_surface_mismatch")
    if not verification.verified_at <= now <= verification.valid_until:
        raise ValueError("runtime_topology_verification_expired")
    endpoints = _endpoints(binding.role_bindings, providers)
    if set(verification.model_ids) != {item.model_id for item in endpoints}:
        raise ValueError("runtime_topology_verified_model_set_mismatch")
    accepted = consume_verified_runtime_binding_capability(
        verified.capability,
        binding=verified.to_artifact(),
        selection=selection,
        receipt=verification,
    )
    if accepted is None:
        raise ValueError("runtime_topology_binding_capability_rejected")
    return endpoints


def _mint_resolution(
    verified: VerifiedRuntimeBindingArtifact,
    endpoints: tuple[RuntimeTopologyEndpoint, ...],
    now: int,
) -> ResolvedRuntimeTopology:
    binding = verified.binding
    verification = verified.verification
    valid_until = min(verification.valid_until, now + MAX_RESOLUTION_TTL_SECONDS)
    body = {
        "schema_version": SCHEMA_VERSION,
        "runtime_binding_receipt_id": binding.receipt_id,
        "verification_receipt_id": verification.receipt_id,
        "selection_receipt_id": binding.selection_receipt_id,
        "runtime_surface": binding.runtime_surface,
        "resolved_at": now,
        "valid_until": valid_until,
        "endpoints": [item.to_dict() for item in endpoints],
        "no_model_call_performed": True,
        "no_provider_fallback_performed": True,
    }
    receipt_id = _digest("verified_model_runtime_topology", body)
    capability = RuntimeTopologyCapability(secrets.token_urlsafe(32))
    resolution = ResolvedRuntimeTopology(
        receipt_id=receipt_id,
        runtime_binding_receipt_id=binding.receipt_id,
        verification_receipt_id=verification.receipt_id,
        selection_receipt_id=binding.selection_receipt_id,
        runtime_surface=binding.runtime_surface,
        resolved_at=now,
        valid_until=valid_until,
        endpoints=endpoints,
        capability=capability,
    )
    token = object.__getattribute__(capability, "_RuntimeTopologyCapability__token")
    with _CAPABILITY_LOCK:
        _CAPABILITIES[token] = (
            capability,
            _TopologyAdmission(resolution, canonical_digest(resolution.to_dict())),
        )
    return resolution


def consume_resolved_runtime_topology(
    resolution: ResolvedRuntimeTopology,
    *,
    trusted_now_epoch: Callable[[], int],
) -> tuple[RuntimeTopologyEndpoint, ...] | None:
    """Consume a resolver-minted topology once and return its exact endpoints."""

    if type(resolution) is not ResolvedRuntimeTopology:
        return None
    capability = resolution.capability
    if type(capability) is not RuntimeTopologyCapability:
        return None
    token = object.__getattribute__(capability, "_RuntimeTopologyCapability__token")
    with _CAPABILITY_LOCK:
        record = _CAPABILITIES.get(token)
        if record is None or record[0] is not capability:
            return None
        _CAPABILITIES.pop(token, None)
    admission = record[1]
    actual = canonical_digest(resolution.to_dict())
    if admission.resolution is not resolution or not hmac.compare_digest(
        actual, admission.receipt_digest
    ):
        return None
    try:
        now = int(trusted_now_epoch())
    except Exception:
        return None
    if not resolution.resolved_at <= now <= resolution.valid_until:
        return None
    return resolution.endpoints


def discard_resolved_runtime_topology(resolution: Any) -> None:
    """Invalidate a topology that a consumer elects not to execute."""

    if type(resolution) is not ResolvedRuntimeTopology:
        return
    capability = resolution.capability
    if type(capability) is not RuntimeTopologyCapability:
        return
    token = object.__getattribute__(capability, "_RuntimeTopologyCapability__token")
    with _CAPABILITY_LOCK:
        record = _CAPABILITIES.get(token)
        if record is not None and record[0] is capability:
            _CAPABILITIES.pop(token, None)


def _available_provider_set(values: Sequence[str]) -> frozenset[str]:
    if isinstance(values, (str, bytes)) or not 1 <= len(values) <= MAX_RUNTIME_PROVIDERS:
        raise ValueError("runtime_topology_available_providers_invalid")
    providers = tuple(_token("provider", value) for value in values)
    if len(providers) != len(set(providers)):
        raise ValueError("runtime_topology_available_providers_invalid")
    if any(provider not in KNOWN_RUNTIME_PROVIDERS for provider in providers):
        raise ValueError("runtime_topology_unknown_provider")
    return frozenset(providers)


def _endpoints(bindings: Sequence[Any], providers: frozenset[str]) -> tuple[RuntimeTopologyEndpoint, ...]:
    if not 1 <= len(bindings) <= MAX_RUNTIME_ROLES:
        raise ValueError("runtime_topology_role_count_invalid")
    endpoints = tuple(
        RuntimeTopologyEndpoint(
            role=_token("role", item.role),
            provider=_token("provider", item.provider),
            model_id=_token("model_id", item.model_id),
        )
        for item in bindings
    )
    if len({item.role for item in endpoints}) != len(endpoints):
        raise ValueError("runtime_topology_duplicate_role")
    for item in endpoints:
        if item.provider not in KNOWN_RUNTIME_PROVIDERS:
            raise ValueError("runtime_topology_unknown_provider")
        if item.provider not in providers:
            raise ValueError("runtime_topology_provider_unavailable")
    return endpoints


def _token(name: str, value: Any) -> str:
    token = str(value or "").strip()
    if not TOKEN_RE.fullmatch(token):
        raise ValueError(f"runtime_topology_{name}_invalid")
    return token


def _digest(prefix: str, value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"{prefix}:{hashlib.sha256(encoded).hexdigest()}"


__all__ = [
    "KNOWN_RUNTIME_PROVIDERS",
    "ResolvedRuntimeTopology",
    "RuntimeTopologyCapability",
    "RuntimeTopologyEndpoint",
    "consume_resolved_runtime_topology",
    "discard_resolved_runtime_topology",
    "resolve_verified_runtime_topology",
]
