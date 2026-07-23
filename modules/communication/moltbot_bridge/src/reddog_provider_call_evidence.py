"""Content-free, durable evidence for governed provider call boundaries."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import threading
import time
from dataclasses import asdict, dataclass, replace
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol

from modules.communication.moltbot_bridge.src.reddog_runtime_json_read import (
    read_reddog_runtime_json_mapping,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    runtime_operation_lock,
)

SCHEMA_VERSION = "reddog_provider_call_evidence.v1"
STORE_SCHEMA_VERSION = "reddog_provider_call_evidence_store.v1"
ENV_STORE_PATH = "REDDOG_PROVIDER_CALL_EVIDENCE_STORE_PATH"
_CALL_DOMAIN = b"reddog-provider-call-id.v1\x00"
_RECEIPT_DOMAIN = b"reddog-provider-call-receipt-id.v1\x00"
_REQUEST_DOMAIN = b"reddog-provider-request-envelope.v1\x00"
_MAX_TEXT = 512
_MAX_USAGE = 10**12
_DIGEST_KEYS = {
    "redacted_input_digest",
    "request_envelope_digest",
    "response_content_digest",
    "model_runtime_binding_digest",
}
_RECEIPT_KEYS = {
    "schema_version",
    "receipt_id",
    "call_id",
    "surface",
    "task_id",
    "work_order_id",
    "queue_item_id",
    "run_id",
    "cycle_id",
    "requested_provider",
    "requested_model",
    "served_provider",
    "served_model",
    "redacted_input_digest",
    "request_envelope_digest",
    "response_content_digest",
    "response_byte_count",
    "model_runtime_binding_receipt_id",
    "model_runtime_binding_digest",
    "attempted",
    "outcome",
    "reason",
    "started_at_ms",
    "completed_at_ms",
    "usage",
}
_USAGE_KEYS = {"input_tokens", "output_tokens", "total_tokens"}


class ProviderCallOutcome(str, Enum):
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BLOCKED_PRECALL = "BLOCKED_PRECALL"
    INDETERMINATE = "INDETERMINATE"


class ProviderCallReason(str, Enum):
    PRECALL_INTENT = "PRECALL_INTENT"
    PROVIDER_RETURNED = "PROVIDER_RETURNED"
    PROVIDER_FAILED = "PROVIDER_FAILED"
    PROVIDER_TIMEOUT = "PROVIDER_TIMEOUT"
    RESPONSE_INVALID = "RESPONSE_INVALID"


@dataclass(frozen=True)
class ProviderCallUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None

    def to_dict(self) -> dict[str, int | None]:
        return asdict(self)


@dataclass(frozen=True)
class ProviderCallEvidence:
    schema_version: str
    receipt_id: str
    call_id: str
    surface: str
    task_id: str | None
    work_order_id: str | None
    queue_item_id: str | None
    run_id: str | None
    cycle_id: str | None
    requested_provider: str
    requested_model: str
    served_provider: str | None
    served_model: str | None
    redacted_input_digest: str
    request_envelope_digest: str
    response_content_digest: str | None
    response_byte_count: int | None
    model_runtime_binding_receipt_id: str
    model_runtime_binding_digest: str
    attempted: bool
    outcome: str
    reason: str
    started_at_ms: int
    completed_at_ms: int | None
    usage: ProviderCallUsage

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["usage"] = self.usage.to_dict()
        return payload


class ProviderCallEvidenceStore(Protocol):
    def load(self, call_id: str) -> ProviderCallEvidence | None: ...

    def start(self, receipt: ProviderCallEvidence) -> ProviderCallEvidence: ...

    def transition(self, receipt: ProviderCallEvidence) -> ProviderCallEvidence: ...


def canonical_digest(payload: Mapping[str, Any], *, domain: bytes = b"") -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(domain + encoded).hexdigest()


def response_digest(content: str) -> tuple[str, int]:
    raw = content.encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest(), len(raw)


def create_precall_evidence(
    *,
    surface: str,
    task_id: str | None,
    work_order_id: str | None,
    queue_item_id: str | None,
    run_id: str | None,
    cycle_id: str | None,
    requested_provider: str,
    requested_model: str,
    redacted_input_digest: str,
    model_runtime_binding_receipt_id: str,
    model_runtime_binding_digest: str,
    request_metadata: Mapping[str, Any],
    started_at_ms: int | None = None,
) -> ProviderCallEvidence:
    lineage = {
        "task_id": _optional_text(task_id),
        "work_order_id": _optional_text(work_order_id),
        "queue_item_id": _optional_text(queue_item_id),
        "run_id": _optional_text(run_id),
        "cycle_id": _optional_text(cycle_id),
    }
    envelope = {
        "surface": _text(surface),
        **lineage,
        "requested_provider": _text(requested_provider),
        "requested_model": _text(requested_model),
        "redacted_input_digest": redacted_input_digest,
        "model_runtime_binding_receipt_id": _text(model_runtime_binding_receipt_id),
        "model_runtime_binding_digest": model_runtime_binding_digest,
        "metadata": _bounded_metadata(request_metadata),
    }
    request_envelope_digest = canonical_digest(envelope, domain=_REQUEST_DOMAIN)
    call_id = _call_id(
        surface=envelope["surface"],
        lineage=lineage,
        request_envelope_digest=request_envelope_digest,
    )
    receipt = ProviderCallEvidence(
        schema_version=SCHEMA_VERSION,
        receipt_id="",
        call_id=call_id,
        surface=envelope["surface"],
        **lineage,
        requested_provider=envelope["requested_provider"],
        requested_model=envelope["requested_model"],
        served_provider=None,
        served_model=None,
        redacted_input_digest=redacted_input_digest,
        request_envelope_digest=request_envelope_digest,
        response_content_digest=None,
        response_byte_count=None,
        model_runtime_binding_receipt_id=envelope["model_runtime_binding_receipt_id"],
        model_runtime_binding_digest=model_runtime_binding_digest,
        attempted=False,
        outcome=ProviderCallOutcome.BLOCKED_PRECALL.value,
        reason=ProviderCallReason.PRECALL_INTENT.value,
        started_at_ms=int(
            started_at_ms if started_at_ms is not None else time.time() * 1000
        ),
        completed_at_ms=None,
        usage=ProviderCallUsage(),
    )
    return _with_receipt_id(receipt)


def arm_provider_call(receipt: ProviderCallEvidence) -> ProviderCallEvidence:
    armed = replace(
        receipt,
        receipt_id="",
        attempted=True,
        outcome=ProviderCallOutcome.INDETERMINATE.value,
        reason=ProviderCallReason.PRECALL_INTENT.value,
    )
    return _with_receipt_id(armed)


def terminalize_provider_call(
    receipt: ProviderCallEvidence,
    *,
    outcome: ProviderCallOutcome,
    reason: ProviderCallReason,
    completed_at_ms: int,
    content: str | None = None,
    served_metadata: Mapping[str, Any] | None = None,
) -> ProviderCallEvidence:
    if outcome not in {ProviderCallOutcome.COMPLETED, ProviderCallOutcome.FAILED}:
        raise ValueError("terminal_outcome_required")
    served_provider, served_model, usage = parse_served_metadata(served_metadata)
    digest, byte_count = (
        response_digest(content) if content is not None else (None, None)
    )
    terminal = replace(
        receipt,
        receipt_id="",
        served_provider=served_provider,
        served_model=served_model,
        response_content_digest=digest,
        response_byte_count=byte_count,
        attempted=True,
        outcome=outcome.value,
        reason=reason.value,
        completed_at_ms=int(completed_at_ms),
        usage=usage,
    )
    return _with_receipt_id(terminal)


def parse_served_metadata(
    value: Mapping[str, Any] | None,
) -> tuple[str | None, str | None, ProviderCallUsage]:
    if value is None:
        return None, None, ProviderCallUsage()
    if not isinstance(value, Mapping) or set(value) != {
        "served_provider",
        "served_model",
        "usage",
    }:
        raise ValueError("served_metadata_schema")
    provider = _optional_text(value["served_provider"])
    model = _optional_text(value["served_model"])
    if (provider is None) != (model is None):
        raise ValueError("served_identity_incomplete")
    usage_raw = value["usage"]
    if not isinstance(usage_raw, Mapping) or set(usage_raw) != _USAGE_KEYS:
        raise ValueError("usage_schema")
    usage = ProviderCallUsage(
        **{key: _usage(value) for key, value in usage_raw.items()}
    )
    return provider, model, usage


def validate_provider_call_evidence(
    value: ProviderCallEvidence | Mapping[str, Any],
) -> ProviderCallEvidence:
    if isinstance(value, ProviderCallEvidence):
        payload = value.to_dict()
    elif isinstance(value, Mapping):
        payload = dict(value)
    else:
        raise ValueError("receipt_not_mapping")
    if set(payload) != _RECEIPT_KEYS:
        raise ValueError("receipt_schema")
    usage_raw = payload["usage"]
    if not isinstance(usage_raw, Mapping) or set(usage_raw) != _USAGE_KEYS:
        raise ValueError("usage_schema")
    receipt = ProviderCallEvidence(
        **{key: payload[key] for key in _RECEIPT_KEYS - {"usage"}},
        usage=ProviderCallUsage(**{key: _usage(usage_raw[key]) for key in _USAGE_KEYS}),
    )
    if receipt.schema_version != SCHEMA_VERSION:
        raise ValueError("schema_version")
    for field in (
        "receipt_id",
        "call_id",
        "surface",
        "requested_provider",
        "requested_model",
        "model_runtime_binding_receipt_id",
    ):
        _text(getattr(receipt, field))
    for field in ("task_id", "work_order_id", "queue_item_id", "run_id", "cycle_id"):
        _optional_text(getattr(receipt, field))
    if not any(
        (
            receipt.task_id,
            receipt.work_order_id,
            receipt.queue_item_id,
            receipt.run_id,
            receipt.cycle_id,
        )
    ):
        raise ValueError("lineage_required")
    for field in _DIGEST_KEYS:
        current = getattr(receipt, field)
        if current is not None:
            _digest(current)
    if receipt.call_id != _call_id(
        surface=receipt.surface,
        lineage={
            "task_id": receipt.task_id,
            "work_order_id": receipt.work_order_id,
            "queue_item_id": receipt.queue_item_id,
            "run_id": receipt.run_id,
            "cycle_id": receipt.cycle_id,
        },
        request_envelope_digest=receipt.request_envelope_digest,
    ):
        raise ValueError("call_id_mismatch")
    if (receipt.served_provider is None) != (receipt.served_model is None):
        raise ValueError("served_identity_incomplete")
    _optional_text(receipt.served_provider)
    _optional_text(receipt.served_model)
    if not isinstance(receipt.attempted, bool):
        raise ValueError("attempted")
    if type(receipt.started_at_ms) is not int or receipt.started_at_ms < 0:
        raise ValueError("started_at_ms")
    if receipt.completed_at_ms is not None and (
        type(receipt.completed_at_ms) is not int
        or receipt.completed_at_ms < receipt.started_at_ms
    ):
        raise ValueError("completed_at_ms")
    if receipt.response_byte_count is not None and (
        type(receipt.response_byte_count) is not int
        or not 0 <= receipt.response_byte_count <= _MAX_USAGE
    ):
        raise ValueError("response_byte_count")
    if (receipt.response_content_digest is None) != (
        receipt.response_byte_count is None
    ):
        raise ValueError("response_evidence_incomplete")
    try:
        outcome = ProviderCallOutcome(receipt.outcome)
        reason = ProviderCallReason(receipt.reason)
    except ValueError as exc:
        raise ValueError("receipt_enum") from exc
    if outcome == ProviderCallOutcome.BLOCKED_PRECALL:
        if receipt.attempted or reason != ProviderCallReason.PRECALL_INTENT:
            raise ValueError("precall_state")
    elif outcome == ProviderCallOutcome.INDETERMINATE:
        if (
            not receipt.attempted
            or reason != ProviderCallReason.PRECALL_INTENT
            or receipt.completed_at_ms is not None
        ):
            raise ValueError("indeterminate_state")
    else:
        if not receipt.attempted or receipt.completed_at_ms is None:
            raise ValueError("terminal_state")
        if outcome == ProviderCallOutcome.COMPLETED and reason != ProviderCallReason.PROVIDER_RETURNED:
            raise ValueError("completed_reason")
        if outcome == ProviderCallOutcome.FAILED and reason not in {
            ProviderCallReason.PROVIDER_FAILED,
            ProviderCallReason.PROVIDER_TIMEOUT,
            ProviderCallReason.RESPONSE_INVALID,
        }:
            raise ValueError("failed_reason")
    if outcome in {
        ProviderCallOutcome.BLOCKED_PRECALL,
        ProviderCallOutcome.INDETERMINATE,
    } and any(
        value is not None
        for value in (
            receipt.served_provider,
            receipt.response_content_digest,
            receipt.response_byte_count,
            receipt.usage.input_tokens,
            receipt.usage.output_tokens,
            receipt.usage.total_tokens,
        )
    ):
        raise ValueError("preterminal_evidence")
    if receipt.receipt_id != _receipt_id(receipt):
        raise ValueError("receipt_id_mismatch")
    return receipt


def provider_call_store_from_env(
    env: Mapping[str, str] | None = None,
) -> ProviderCallEvidenceStore | None:
    raw = str((env or os.environ).get(ENV_STORE_PATH) or "").strip()
    if not raw:
        return None
    path = Path(raw).expanduser().resolve()
    repo_root = Path(__file__).resolve().parents[4]
    if path == repo_root or repo_root in path.parents:
        return None
    return AtomicJsonProviderCallEvidenceStore(path, allowed_root=path.parent)


class InMemoryProviderCallEvidenceStore:
    def __init__(self, *, fail_on_transition: int | None = None) -> None:
        self._history: dict[str, list[ProviderCallEvidence]] = {}
        self._lock = threading.Lock()
        self.fail_on_transition = fail_on_transition
        self.transition_count = 0

    def load(self, call_id: str) -> ProviderCallEvidence | None:
        with self._lock:
            items = self._history.get(call_id, ())
            return items[-1] if items else None

    def history(self, call_id: str) -> tuple[ProviderCallEvidence, ...]:
        with self._lock:
            return tuple(self._history.get(call_id, ()))

    def start(self, receipt: ProviderCallEvidence) -> ProviderCallEvidence:
        with self._lock:
            return self._commit(receipt, start=True)

    def transition(self, receipt: ProviderCallEvidence) -> ProviderCallEvidence:
        with self._lock:
            self.transition_count += 1
            if self.fail_on_transition == self.transition_count:
                raise RuntimeError("store_transition_failed")
            return self._commit(receipt, start=False)

    def _commit(
        self, receipt: ProviderCallEvidence, *, start: bool
    ) -> ProviderCallEvidence:
        receipt = validate_provider_call_evidence(receipt)
        history = self._history.setdefault(receipt.call_id, [])
        current = history[-1] if history else None
        if start:
            if any(item.receipt_id == receipt.receipt_id for item in history):
                return receipt
            if current is None:
                history.append(receipt)
                return receipt
            raise RuntimeError("divergent_replay")
        _validate_transition(current, receipt)
        if current and current.receipt_id == receipt.receipt_id:
            return current
        history.append(receipt)
        return receipt


class AtomicJsonProviderCallEvidenceStore:
    """Locked append-history snapshot with fsync plus atomic replace."""

    def __init__(self, path: str | Path, *, allowed_root: str | Path) -> None:
        self.path = Path(path).expanduser().resolve()
        self.allowed_root = Path(allowed_root).expanduser().resolve()
        if (
            self.path != self.allowed_root
            and self.allowed_root not in self.path.parents
        ):
            raise ValueError("store_path_outside_allowed_root")

    def load(self, call_id: str) -> ProviderCallEvidence | None:
        with runtime_operation_lock(str(self.path) + ".operation"):
            snapshot = self._load_unlocked()
            receipt_id = snapshot["heads"].get(call_id)
            return (
                validate_provider_call_evidence(snapshot["receipts"][receipt_id])
                if receipt_id
                else None
            )

    def start(self, receipt: ProviderCallEvidence) -> ProviderCallEvidence:
        return self._commit(receipt, start=True)

    def transition(self, receipt: ProviderCallEvidence) -> ProviderCallEvidence:
        return self._commit(receipt, start=False)

    def _commit(
        self, receipt: ProviderCallEvidence, *, start: bool
    ) -> ProviderCallEvidence:
        receipt = validate_provider_call_evidence(receipt)
        with runtime_operation_lock(str(self.path) + ".operation"):
            snapshot = self._load_unlocked()
            current_id = snapshot["heads"].get(receipt.call_id)
            current = (
                validate_provider_call_evidence(snapshot["receipts"][current_id])
                if current_id
                else None
            )
            if start:
                if receipt.receipt_id in snapshot["receipts"]:
                    return receipt
                if current is not None:
                    raise RuntimeError("divergent_replay")
            else:
                _validate_transition(current, receipt)
                if current and current.receipt_id == receipt.receipt_id:
                    return current
            snapshot["receipts"][receipt.receipt_id] = receipt.to_dict()
            snapshot["heads"][receipt.call_id] = receipt.receipt_id
            self._atomic_write(snapshot)
            return receipt

    def _load_unlocked(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"schema_version": STORE_SCHEMA_VERSION, "heads": {}, "receipts": {}}
        raw = read_reddog_runtime_json_mapping(
            self.path, allowed_root=self.allowed_root
        )
        if set(raw) != {"schema_version", "heads", "receipts"}:
            raise RuntimeError("store_schema")
        if raw["schema_version"] != STORE_SCHEMA_VERSION:
            raise RuntimeError("store_schema_version")
        if not isinstance(raw["heads"], Mapping) or not isinstance(
            raw["receipts"], Mapping
        ):
            raise RuntimeError("store_schema")
        snapshot = json.loads(json.dumps(raw, sort_keys=True))
        for receipt_id, payload in snapshot["receipts"].items():
            receipt = validate_provider_call_evidence(payload)
            if receipt.receipt_id != receipt_id:
                raise RuntimeError("store_receipt_key")
        for call_id, receipt_id in snapshot["heads"].items():
            if receipt_id not in snapshot["receipts"]:
                raise RuntimeError("store_head")
            if snapshot["receipts"][receipt_id]["call_id"] != call_id:
                raise RuntimeError("store_head")
        return snapshot

    def _atomic_write(self, snapshot: Mapping[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.", suffix=".tmp", dir=str(self.path.parent)
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(snapshot, handle, sort_keys=True, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_name, self.path)
            _fsync_parent(self.path.parent)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)


def execute_evidenced_provider_call(
    *,
    store: ProviderCallEvidenceStore,
    precall: ProviderCallEvidence,
    invoke: Callable[[], Any],
    content_from_result: Callable[[Any], str | None],
    metadata_from_result: Callable[[Any], Mapping[str, Any] | None],
    now_ms: Callable[[], int] = lambda: int(time.time() * 1000),
) -> tuple[Any | None, ProviderCallEvidence, bool]:
    """Run only after start+arm; return ``promotable=False`` on uncertain persistence."""

    store.start(precall)
    armed = arm_provider_call(precall)
    store.transition(armed)
    try:
        result = invoke()
    except TimeoutError:
        failed = terminalize_provider_call(
            armed,
            outcome=ProviderCallOutcome.FAILED,
            reason=ProviderCallReason.PROVIDER_TIMEOUT,
            completed_at_ms=now_ms(),
        )
        store.transition(failed)
        raise
    except Exception:
        failed = terminalize_provider_call(
            armed,
            outcome=ProviderCallOutcome.FAILED,
            reason=ProviderCallReason.PROVIDER_FAILED,
            completed_at_ms=now_ms(),
        )
        store.transition(failed)
        raise
    try:
        content = content_from_result(result)
        metadata = metadata_from_result(result)
        terminal = terminalize_provider_call(
            armed,
            outcome=(
                ProviderCallOutcome.COMPLETED
                if isinstance(result, Mapping) and result.get("ok") is True
                else ProviderCallOutcome.FAILED
            ),
            reason=(
                ProviderCallReason.PROVIDER_RETURNED
                if isinstance(result, Mapping) and result.get("ok") is True
                else ProviderCallReason.PROVIDER_FAILED
            ),
            completed_at_ms=now_ms(),
            content=content,
            served_metadata=metadata,
        )
    except (TypeError, ValueError):
        terminal = terminalize_provider_call(
            armed,
            outcome=ProviderCallOutcome.FAILED,
            reason=ProviderCallReason.RESPONSE_INVALID,
            completed_at_ms=now_ms(),
        )
        result = None
    try:
        store.transition(terminal)
    except Exception:
        return None, armed, False
    return result, terminal, True


def _validate_transition(
    current: ProviderCallEvidence | None, candidate: ProviderCallEvidence
) -> None:
    if current is None:
        raise RuntimeError("missing_precall")
    if current.receipt_id == candidate.receipt_id:
        return
    immutable = (
        "call_id",
        "surface",
        "task_id",
        "work_order_id",
        "queue_item_id",
        "run_id",
        "cycle_id",
        "requested_provider",
        "requested_model",
        "redacted_input_digest",
        "request_envelope_digest",
        "model_runtime_binding_receipt_id",
        "model_runtime_binding_digest",
        "started_at_ms",
    )
    if any(getattr(current, key) != getattr(candidate, key) for key in immutable):
        raise RuntimeError("divergent_replay")
    allowed = {
        ProviderCallOutcome.BLOCKED_PRECALL.value: {
            ProviderCallOutcome.INDETERMINATE.value
        },
        ProviderCallOutcome.INDETERMINATE.value: {
            ProviderCallOutcome.COMPLETED.value,
            ProviderCallOutcome.FAILED.value,
        },
    }
    if candidate.outcome not in allowed.get(current.outcome, set()):
        raise RuntimeError("invalid_transition")


def _with_receipt_id(receipt: ProviderCallEvidence) -> ProviderCallEvidence:
    candidate = replace(receipt, receipt_id=_receipt_id(receipt))
    return validate_provider_call_evidence(candidate)


def _call_id(
    *,
    surface: str,
    lineage: Mapping[str, str | None],
    request_envelope_digest: str,
) -> str:
    return "reddog_provider_call:" + canonical_digest(
        {
            "surface": surface,
            **lineage,
            "request_envelope_digest": request_envelope_digest,
        },
        domain=_CALL_DOMAIN,
    ).removeprefix("sha256:")


def _receipt_id(receipt: ProviderCallEvidence) -> str:
    payload = receipt.to_dict()
    payload.pop("receipt_id", None)
    return "reddog_provider_call_receipt:" + canonical_digest(
        payload, domain=_RECEIPT_DOMAIN
    ).removeprefix("sha256:")


def _bounded_metadata(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("request_metadata")
    normalized = json.loads(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    )
    if not isinstance(normalized, dict):
        raise ValueError("request_metadata")
    raw = json.dumps(
        normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    if len(raw) > 16_384:
        raise ValueError("request_metadata_too_large")
    return normalized


def _text(value: Any) -> str:
    if not isinstance(value, str) or not value or len(value) > _MAX_TEXT:
        raise ValueError("bounded_text")
    return value


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    return _text(value)


def _digest(value: Any) -> str:
    text = _text(value)
    if len(text) != 71 or not text.startswith("sha256:"):
        raise ValueError("digest")
    try:
        int(text[7:], 16)
    except ValueError as exc:
        raise ValueError("digest") from exc
    return text


def _usage(value: Any) -> int | None:
    if value is None:
        return None
    if type(value) is not int or not 0 <= value <= _MAX_USAGE:
        raise ValueError("usage_value")
    return value


def _fsync_parent(path: Path) -> None:
    if os.name == "nt":
        return
    descriptor = os.open(str(path), os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


__all__ = [
    "AtomicJsonProviderCallEvidenceStore",
    "ENV_STORE_PATH",
    "InMemoryProviderCallEvidenceStore",
    "ProviderCallEvidence",
    "ProviderCallEvidenceStore",
    "ProviderCallOutcome",
    "ProviderCallReason",
    "ProviderCallUsage",
    "SCHEMA_VERSION",
    "arm_provider_call",
    "canonical_digest",
    "create_precall_evidence",
    "execute_evidenced_provider_call",
    "parse_served_metadata",
    "provider_call_store_from_env",
    "response_digest",
    "terminalize_provider_call",
    "validate_provider_call_evidence",
]
