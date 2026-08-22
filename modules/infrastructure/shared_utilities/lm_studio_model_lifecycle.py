"""Exact LM Studio leases; never launch, download, discover, or fall back."""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Callable, Generic, Mapping, TypeVar

from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    runtime_operation_lock,
)
from modules.infrastructure.shared_utilities.lm_studio_lifecycle_intent import (
    LMStudioLifecycleIntent,
    LMStudioLifecycleIntentJournal,
)
from modules.infrastructure.shared_utilities.lm_studio_native_transport import (
    DEFAULT_LM_STUDIO_BASE_URL,
    MAX_CONFIG_BYTES,
    MAX_CONTROL_RESPONSE_BYTES,
    LMStudioAuthenticationError,
    LMStudioLoadedInstance,
    LMStudioModelState,
    LMStudioResidencyState,
    bounded_timeout,
    canonical_mapping,
    inspect_lm_studio_model,
    json_bytes,
    lm_studio_node_identity,
    normalize_lm_studio_base_url,
    request_lm_studio_json,
    required_text,
    validate_api_token,
)


LIFECYCLE_SCHEMA_VERSION = "lm_studio_model_lifecycle.v1"
MAX_LOCK_WAIT_SECONDS = 60.0
_T = TypeVar("_T")


class LMStudioLeaseMode(str, Enum):
    BORROW_ONLY = "borrow_only"
    MANAGED_LOAD = "managed_load"


@dataclass(frozen=True)
class LMStudioModelLease:
    model_key: str
    instance_id: str
    base_url: str


@dataclass(frozen=True)
class LMStudioModelLifecycleReceipt:
    receipt_id: str
    model_key: str
    instance_id: str
    lease_mode: str
    residency_origin: str
    base_url_digest: str
    lock_scope_digest: str
    requested_config_digest: str
    observed_config_digest: str
    load_confirmed: bool
    unload_confirmed: bool
    no_server_launch_performed: bool
    no_model_download_performed: bool
    no_provider_fallback_performed: bool
    schema_version: str = LIFECYCLE_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LMStudioModelTransactionResult(Generic[_T]):
    value: _T
    lifecycle_receipt: LMStudioModelLifecycleReceipt


@dataclass(frozen=True)
class _AcquiredLease:
    lease: LMStudioModelLease
    mode: LMStudioLeaseMode
    origin: str
    requested_config: Mapping[str, Any]
    observed_config: Mapping[str, Any]
    api_token: str | None = field(repr=False, compare=False)

    @property
    def owned(self) -> bool:
        return self.origin == "explicit_load"


def execute_lm_studio_model_transaction(
    *,
    model_key: str,
    operation: Callable[[LMStudioModelLease], _T],
    mode: LMStudioLeaseMode = LMStudioLeaseMode.MANAGED_LOAD,
    base_url: str = DEFAULT_LM_STUDIO_BASE_URL,
    api_token: str | None = None,
    load_config: Mapping[str, Any] | None = None,
    timeout: float = 300.0,
) -> LMStudioModelTransactionResult[_T]:
    """Borrow or explicitly load one model for one serialized operation."""

    key = required_text("model_key", model_key)
    root = normalize_lm_studio_base_url(base_url)
    lease_mode = LMStudioLeaseMode(mode)
    config = _validate_load_config(load_config or {})
    lock_digest = _digest(lm_studio_node_identity(root))
    lock_wait = min(_bounded_timeout(timeout), MAX_LOCK_WAIT_SECONDS)
    with runtime_operation_lock(
        f"lm-studio-node:{lock_digest}", timeout_seconds=lock_wait
    ):
        acquired = _acquire_lease(
            key, root, api_token, lease_mode, config, _bounded_timeout(timeout), lock_digest
        )
        value, error = _run_operation(operation, acquired.lease)
        try:
            receipt = _release_lease(acquired, lock_digest, timeout)
        except BaseException as cleanup_error:
            if error is not None:
                raise cleanup_error from error
            raise
        if error is not None:
            raise error.with_traceback(error.__traceback__)
    return LMStudioModelTransactionResult(value=value, lifecycle_receipt=receipt)


def rehydrate_lm_studio_model_lifecycle_receipt(
    payload: Mapping[str, Any],
) -> LMStudioModelLifecycleReceipt:
    """Validate deterministic, content-free lifecycle evidence."""

    body = _receipt_body_from_payload(payload)
    receipt_id = str(payload.get("receipt_id") or "")
    expected = f"lm_studio_model_lifecycle:{_digest(body)}"
    if not hmac.compare_digest(receipt_id, expected):
        raise ValueError("lm_studio_lifecycle_receipt_id_invalid")
    return LMStudioModelLifecycleReceipt(receipt_id=receipt_id, **body)


def _acquire_lease(
    key: str,
    root: str,
    token: str | None,
    mode: LMStudioLeaseMode,
    config: Mapping[str, Any],
    timeout: float,
    lock_digest: str,
) -> _AcquiredLease:
    state = inspect_lm_studio_model(
        key, base_url=root, api_token=token, timeout=min(timeout, 10.0)
    )
    if state.state is LMStudioResidencyState.SERVER_UNREACHABLE:
        raise RuntimeError("lm_studio_server_unreachable")
    if state.state is LMStudioResidencyState.NOT_INSTALLED:
        raise ValueError("lm_studio_model_not_installed")
    journal = None
    if mode is LMStudioLeaseMode.MANAGED_LOAD:
        journal = LMStudioLifecycleIntentJournal(lock_digest)
        state = _recover_prior_intent(journal, state, root, token, timeout)
    if state.state is LMStudioResidencyState.RESIDENT:
        instance = _require_single_instance(state)
        _require_config_match(config, instance.config)
        return _acquired(key, root, token, mode, "preexisting", config, instance)
    if mode is LMStudioLeaseMode.BORROW_ONLY:
        raise ValueError("lm_studio_model_not_resident")
    if journal is None:
        raise AssertionError("lm_studio_lifecycle_journal_missing")
    _require_managed_capacity(state, config)
    intent = journal.prepare(key, _digest(config))
    instance = _load_exact_model(key, root, token, config, timeout, journal, intent)
    return _acquired(key, root, token, mode, "explicit_load", config, instance)


def _acquired(
    key: str,
    root: str,
    token: str | None,
    mode: LMStudioLeaseMode,
    origin: str,
    config: Mapping[str, Any],
    instance: LMStudioLoadedInstance,
) -> _AcquiredLease:
    lease = LMStudioModelLease(key, instance.instance_id, root)
    return _AcquiredLease(
        lease, mode, origin, config, instance.config, validate_api_token(token)
    )


def _load_exact_model(
    key: str,
    root: str,
    token: str | None,
    config: Mapping[str, Any],
    timeout: float,
    journal: LMStudioLifecycleIntentJournal,
    intent: LMStudioLifecycleIntent,
) -> LMStudioLoadedInstance:
    body = {"model": key, **config, "echo_load_config": True}
    intent = journal.transition(intent, "load_requested")
    try:
        response = request_lm_studio_json(
            f"{root}/api/v1/models/load",
            method="POST",
            payload=body,
            api_token=token,
            timeout=timeout,
            max_response_bytes=MAX_CONTROL_RESPONSE_BYTES,
        )
    except LMStudioAuthenticationError:
        raise
    except BaseException as exc:
        journal.transition(intent, "quarantined")
        inspect_lm_studio_model(key, base_url=root, api_token=token, timeout=10.0)
        raise RuntimeError("lm_studio_load_outcome_indeterminate") from exc
    instance_id = _validate_load_response(response)
    intent = _record_confirmed_load(
        journal, intent, key, instance_id, root, token, timeout
    )
    try:
        state = inspect_lm_studio_model(
            key, base_url=root, api_token=token, timeout=10.0
        )
        instance = _require_single_instance(state)
        if state.total_resident_instances != 1:
            raise RuntimeError("lm_studio_managed_capacity_changed")
        if instance.instance_id != instance_id:
            raise RuntimeError("lm_studio_loaded_instance_mismatch")
        _require_config_match(config, instance.config)
        return instance
    except BaseException as verification_error:
        lease = LMStudioModelLease(key, instance_id, root)
        try:
            _unload_exact_instance(lease, token, timeout)
            journal.transition(intent, "unload_confirmed")
        except BaseException as cleanup_error:
            raise cleanup_error from verification_error
        raise


def _record_confirmed_load(
    journal: LMStudioLifecycleIntentJournal,
    intent: LMStudioLifecycleIntent,
    key: str,
    instance_id: str,
    root: str,
    token: str | None,
    timeout: float,
) -> LMStudioLifecycleIntent:
    """Never leave a known instance resident if durable ownership cannot seal."""

    try:
        return journal.transition(intent, "load_confirmed", instance_id=instance_id)
    except BaseException as journal_error:
        lease = LMStudioModelLease(key, instance_id, root)
        try:
            _unload_exact_instance(lease, token, timeout)
        except BaseException as cleanup_error:
            raise cleanup_error from journal_error
        raise


def _validate_load_response(payload: Mapping[str, Any]) -> str:
    if payload.get("status") != "loaded" or payload.get("type") != "llm":
        raise RuntimeError("lm_studio_load_response_invalid")
    return required_text("instance_id", payload.get("instance_id"))


def _require_single_instance(state: LMStudioModelState) -> LMStudioLoadedInstance:
    if state.state is not LMStudioResidencyState.RESIDENT:
        raise RuntimeError("lm_studio_model_residency_not_confirmed")
    if len(state.loaded_instances) != 1:
        raise RuntimeError("lm_studio_model_residency_ambiguous")
    return state.loaded_instances[0]


def _require_config_match(
    requested: Mapping[str, Any], observed: Mapping[str, Any]
) -> None:
    if any(observed.get(name) != value for name, value in requested.items()):
        raise RuntimeError("lm_studio_load_config_mismatch")


def _require_managed_capacity(
    state: LMStudioModelState, config: Mapping[str, Any]
) -> None:
    """Admit no additive load while any instance already occupies the node."""

    if state.total_resident_instances != 0:
        raise RuntimeError("lm_studio_managed_capacity_occupied")
    requested_context = config.get("context_length")
    if requested_context is not None:
        if state.max_context_length is None:
            raise RuntimeError("lm_studio_max_context_length_unavailable")
        if requested_context > state.max_context_length:
            raise ValueError("lm_studio_context_length_exceeds_model_maximum")


def _recover_prior_intent(
    journal: LMStudioLifecycleIntentJournal,
    state: LMStudioModelState,
    root: str,
    token: str | None,
    timeout: float,
) -> LMStudioModelState:
    """Recover proven ownership, or quarantine ambiguous interrupted loads."""

    intent = journal.read()
    if intent is None or intent.terminal:
        return state
    prior_state = inspect_lm_studio_model(
        intent.model_key,
        base_url=root,
        api_token=token,
        timeout=min(timeout, 10.0),
    )
    if prior_state.state is LMStudioResidencyState.SERVER_UNREACHABLE:
        raise RuntimeError("lm_studio_lifecycle_recovery_unavailable")
    if prior_state.total_resident_instances == 0:
        journal.transition(intent, "recovered_absent")
        return inspect_lm_studio_model(
            state.model_key,
            base_url=root,
            api_token=token,
            timeout=min(timeout, 10.0),
        )
    # Native inventory exposes no documented server boot/generation identity.
    # A matching ID after restart may be a reused foreign instance, so it is
    # never sufficient for automatic destructive recovery.
    journal.transition(intent, "quarantined")
    raise RuntimeError("lm_studio_lifecycle_recovery_required")


def _run_operation(
    operation: Callable[[LMStudioModelLease], _T], lease: LMStudioModelLease
) -> tuple[_T | None, BaseException | None]:
    try:
        return operation(lease), None
    except BaseException as exc:
        return None, exc


def _release_lease(
    acquired: _AcquiredLease, lock_digest: str, timeout: float
) -> LMStudioModelLifecycleReceipt:
    unloaded = False
    if acquired.owned:
        _unload_exact_instance(
            acquired.lease, acquired.api_token, _bounded_timeout(timeout)
        )
        journal = LMStudioLifecycleIntentJournal(lock_digest)
        intent = journal.read()
        if intent is None or intent.instance_id != acquired.lease.instance_id:
            raise RuntimeError("lm_studio_lifecycle_intent_binding_missing")
        journal.transition(intent, "unload_confirmed")
        unloaded = True
    return _lifecycle_receipt(acquired, lock_digest, unloaded)


def _unload_exact_instance(
    lease: LMStudioModelLease, api_token: str | None, timeout: float
) -> None:
    response = request_lm_studio_json(
        f"{lease.base_url}/api/v1/models/unload",
        method="POST",
        payload={"instance_id": lease.instance_id},
        api_token=api_token,
        timeout=timeout,
        max_response_bytes=MAX_CONTROL_RESPONSE_BYTES,
    )
    if response.get("instance_id") != lease.instance_id:
        raise RuntimeError("lm_studio_unload_response_invalid")
    state = inspect_lm_studio_model(
        lease.model_key,
        base_url=lease.base_url,
        api_token=api_token,
        timeout=min(timeout, 10.0),
    )
    if state.state is LMStudioResidencyState.SERVER_UNREACHABLE:
        raise RuntimeError("lm_studio_unload_confirmation_unavailable")
    if any(item.instance_id == lease.instance_id for item in state.loaded_instances):
        raise RuntimeError("lm_studio_unload_not_confirmed")


def _lifecycle_receipt(
    acquired: _AcquiredLease, lock_digest: str, unloaded: bool
) -> LMStudioModelLifecycleReceipt:
    body = {
        "schema_version": LIFECYCLE_SCHEMA_VERSION,
        "model_key": acquired.lease.model_key,
        "instance_id": acquired.lease.instance_id,
        "lease_mode": acquired.mode.value,
        "residency_origin": acquired.origin,
        "base_url_digest": _digest(acquired.lease.base_url),
        "lock_scope_digest": lock_digest,
        "requested_config_digest": _digest(acquired.requested_config),
        "observed_config_digest": _digest(acquired.observed_config),
        "load_confirmed": acquired.owned,
        "unload_confirmed": unloaded,
        "no_server_launch_performed": True,
        "no_model_download_performed": True,
        "no_provider_fallback_performed": True,
    }
    receipt_id = f"lm_studio_model_lifecycle:{_digest(body)}"
    return LMStudioModelLifecycleReceipt(receipt_id=receipt_id, **body)


def _receipt_body_from_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    origin = str(payload.get("residency_origin") or "")
    load_expected = origin == "explicit_load"
    if origin not in {"preexisting", "explicit_load"}:
        raise ValueError("lm_studio_lifecycle_origin_invalid")
    if payload.get("load_confirmed") is not load_expected:
        raise ValueError("lm_studio_lifecycle_load_flag_invalid")
    if payload.get("unload_confirmed") is not load_expected:
        raise ValueError("lm_studio_lifecycle_unload_flag_invalid")
    body = _receipt_scalar_fields(payload)
    body.update(_receipt_flag_fields(payload, load_expected))
    return body


def _receipt_scalar_fields(payload: Mapping[str, Any]) -> dict[str, Any]:
    if payload.get("schema_version") != LIFECYCLE_SCHEMA_VERSION:
        raise ValueError("lm_studio_lifecycle_schema_invalid")
    mode = str(payload.get("lease_mode") or "")
    if mode not in {item.value for item in LMStudioLeaseMode}:
        raise ValueError("lm_studio_lifecycle_mode_invalid")
    return {
        "schema_version": LIFECYCLE_SCHEMA_VERSION,
        "model_key": required_text("model_key", payload.get("model_key")),
        "instance_id": required_text("instance_id", payload.get("instance_id")),
        "lease_mode": mode,
        "residency_origin": str(payload.get("residency_origin")),
        "base_url_digest": _required_digest(payload.get("base_url_digest")),
        "lock_scope_digest": _required_digest(payload.get("lock_scope_digest")),
        "requested_config_digest": _required_digest(payload.get("requested_config_digest")),
        "observed_config_digest": _required_digest(payload.get("observed_config_digest")),
    }


def _receipt_flag_fields(
    payload: Mapping[str, Any], load_expected: bool
) -> dict[str, bool]:
    required_true = (
        "no_server_launch_performed",
        "no_model_download_performed",
        "no_provider_fallback_performed",
    )
    if any(payload.get(name) is not True for name in required_true):
        raise ValueError("lm_studio_lifecycle_boundary_flag_invalid")
    return {
        "load_confirmed": load_expected,
        "unload_confirmed": load_expected,
        **{name: True for name in required_true},
    }


def _validate_load_config(value: Mapping[str, Any]) -> Mapping[str, Any]:
    config = canonical_mapping(value, "load_config")
    allowed = {
        "context_length",
        "eval_batch_size",
        "flash_attention",
        "num_experts",
        "offload_kv_cache_to_gpu",
    }
    if set(config) - allowed:
        raise ValueError("lm_studio_load_config_field_invalid")
    _bounded_integer(config, "context_length", 512, 131_072)
    _bounded_integer(config, "eval_batch_size", 1, 4_096)
    _bounded_integer(config, "num_experts", 1, 256)
    for name in ("flash_attention", "offload_kv_cache_to_gpu"):
        if name in config and type(config[name]) is not bool:
            raise ValueError(f"lm_studio_{name}_invalid")
    return config


def _bounded_integer(
    config: Mapping[str, Any], name: str, minimum: int, maximum: int
) -> None:
    if name not in config:
        return
    value = config[name]
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f"lm_studio_{name}_invalid")


def _required_digest(value: Any) -> str:
    text = str(value or "")
    if len(text) != 64 or any(character not in "0123456789abcdef" for character in text):
        raise ValueError("lm_studio_lifecycle_digest_invalid")
    return text


def _bounded_timeout(value: float) -> float:
    return bounded_timeout(value)


def _digest(value: Any) -> str:
    return hashlib.sha256(json_bytes(value, MAX_CONFIG_BYTES)).hexdigest()
__all__ = [
    "DEFAULT_LM_STUDIO_BASE_URL", "LMStudioAuthenticationError",
    "LMStudioLeaseMode", "LMStudioLoadedInstance", "LMStudioModelLease",
    "LMStudioModelLifecycleReceipt", "LMStudioModelState",
    "LMStudioModelTransactionResult", "LMStudioResidencyState",
    "execute_lm_studio_model_transaction", "inspect_lm_studio_model",
    "normalize_lm_studio_base_url", "rehydrate_lm_studio_model_lifecycle_receipt",
]
