"""Bounded progress and OpenRouter usage receipts for RedDog Fusion calls.

The receipt records orchestrator-owned stage transitions and provider metadata.
It never records prompts, model output, reasoning text, response bodies, secrets,
or authority-bearing decisions.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import threading
import time
from typing import Any, Callable, Mapping


PROGRESS_SCHEMA = "reddog_fusion_progress_receipt.v1"
EVENT_SCHEMA = "reddog_fusion_progress_event.v1"
CALL_SCHEMA = "reddog_openrouter_call_receipt.v1"
MAX_EVENTS = 96
MAX_CALLS = 16
MAX_TEXT = 160
_ROUTE_TEXT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@ +()-]*$")
_GENERATION_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
_RUN_ID = re.compile(r"^reddog_bridge_run:[0-9a-f]{32}$|^run-[A-Za-z0-9._:-]{1,96}$")
_SECRET_LIKE = re.compile(
    r"(?:sk-or-v1-[A-Za-z0-9_-]{8,}|sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|"
    r"AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{20,}|xox[baprs]-[0-9A-Za-z-]{10,}|"
    r"eyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}|Bearer\s+[A-Za-z0-9._~-]{8,})",
    re.IGNORECASE,
)

_STAGE_STATUS = {
    "bridge_start": "STARTED", "env_check": "OBSERVED",
    "redaction_start": "STARTED", "redaction_pass": "COMPLETED", "redaction_blocked": "BLOCKED",
    "fusion_alias_start": "STARTED", "fusion_alias_done": "COMPLETED",
    "lead_start": "STARTED", "lead_done": "COMPLETED",
    "panel_start": "STARTED", "panel_done": "COMPLETED", "panel_blocked": "BLOCKED",
    "synthesis_start": "STARTED", "synthesis_done": "COMPLETED",
    "single_start": "STARTED", "single_done": "COMPLETED",
}


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def _digest(prefix: str, value: Any) -> str:
    body = f"{prefix}." + _canonical(value)
    return "sha256:" + hashlib.sha256(body.encode("utf-8")).hexdigest()


def _text(value: Any, *, limit: int = MAX_TEXT) -> str:
    cleaned = str(value or "").strip()
    if not cleaned or any(ord(char) < 32 for char in cleaned) or _SECRET_LIKE.search(cleaned):
        return ""
    return cleaned[:limit]


def _route_text(value: Any, *, limit: int = MAX_TEXT) -> str:
    cleaned = _text(value, limit=limit)
    return cleaned if cleaned and _ROUTE_TEXT.fullmatch(cleaned) else ""


def _generation_id(value: Any) -> str:
    cleaned = _text(value, limit=256)
    return cleaned if cleaned and not _SECRET_LIKE.search(cleaned) and _GENERATION_ID.fullmatch(cleaned) else ""


def _nonnegative_int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    try:
        return min(10**15, max(0, int(value)))
    except (TypeError, ValueError, OverflowError):
        return 0


def _cost_microcredits(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    try:
        return min(10**15, max(0, round(float(value) * 1_000_000)))
    except (TypeError, ValueError, OverflowError):
        return 0


def _provider_usage_verified(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return False
    for key in ("prompt_tokens", "completion_tokens", "total_tokens", "cost"):
        item = value.get(key)
        if isinstance(item, bool) or not isinstance(item, (int, float)) or not math.isfinite(float(item)) or item < 0:
            return False
    return int(value["total_tokens"]) == int(value["prompt_tokens"]) + int(value["completion_tokens"])


def sanitize_openrouter_usage(value: Any) -> dict[str, int]:
    """Return numeric accounting only; never retain content-bearing fields."""

    source = value if isinstance(value, Mapping) else {}
    completion = source.get("completion_tokens_details")
    completion_details = completion if isinstance(completion, Mapping) else {}
    prompt = source.get("prompt_tokens_details")
    prompt_details = prompt if isinstance(prompt, Mapping) else {}
    return {
        "prompt_tokens": _nonnegative_int(source.get("prompt_tokens")),
        "completion_tokens": _nonnegative_int(source.get("completion_tokens")),
        "total_tokens": _nonnegative_int(source.get("total_tokens")),
        "reasoning_tokens": _nonnegative_int(completion_details.get("reasoning_tokens")),
        "cached_tokens": _nonnegative_int(prompt_details.get("cached_tokens")),
        "cost_microcredits": _cost_microcredits(source.get("cost")),
    }


def sanitize_openrouter_metadata(value: Any) -> dict[str, Any]:
    """Keep routing facts while dropping free-form/plugin/provider payload data."""

    source = value if isinstance(value, Mapping) else {}
    endpoints = source.get("endpoints")
    endpoint_map = endpoints if isinstance(endpoints, Mapping) else {}
    available = endpoint_map.get("available")
    selected: list[dict[str, str]] = []
    if isinstance(available, list):
        for item in available[:8]:
            if not isinstance(item, Mapping) or item.get("selected") is not True:
                continue
            selected.append({
                "provider": _route_text(item.get("provider")),
                "model": _route_text(item.get("model")),
            })
    pipeline = source.get("pipeline")
    stages: list[dict[str, str]] = []
    if isinstance(pipeline, list):
        for item in pipeline[:12]:
            if isinstance(item, Mapping):
                stages.append({
                    "type": _route_text(item.get("type")),
                    "name": _route_text(item.get("name")),
                })
    attempt_value = source.get("attempt")
    attempt_present = not isinstance(attempt_value, bool) and isinstance(attempt_value, int) and attempt_value >= 0
    return {
        "requested": _route_text(source.get("requested")),
        "strategy": _route_text(source.get("strategy")),
        "region": _route_text(source.get("region")),
        "attempt": _nonnegative_int(source.get("attempt")),
        "attempt_present": attempt_present,
        "is_byok": source.get("is_byok") is True,
        "response_provider": _route_text(source.get("response_provider")),
        "response_model": _route_text(source.get("response_model")),
        "selected_endpoints": selected,
        "pipeline_stages": stages,
    }


class FusionProgressRecorder:
    """Thread-safe, process-local recorder for one RedDog bridge invocation."""

    def __init__(
        self,
        run_id: str,
        *,
        wall_clock_ms: Callable[[], int] | None = None,
        monotonic_ns: Callable[[], int] | None = None,
    ) -> None:
        value = _text(run_id, limit=128)
        if not value or not _RUN_ID.fullmatch(value):
            raise ValueError("missing_bridge_run_id")
        self.run_id = value
        self._wall_clock_ms = wall_clock_ms or (lambda: int(time.time() * 1000))
        self._monotonic_ns = monotonic_ns or time.monotonic_ns
        self._started_ns = self._monotonic_ns()
        self._lock = threading.Lock()
        self._events: list[dict[str, Any]] = []
        self._calls: dict[str, dict[str, Any]] = {}
        self._call_sequence = 0

    def emit(self, stage: str, *, role: str = "", model: str = "") -> dict[str, Any] | None:
        normalized_stage = _text(stage, limit=64)
        if normalized_stage not in _STAGE_STATUS:
            return None
        with self._lock:
            if len(self._events) >= MAX_EVENTS:
                return None
            sequence = len(self._events) + 1
            previous_event_digest = self._events[-1]["event_digest"] if self._events else "GENESIS"
            body = {
                "schema_version": EVENT_SCHEMA,
                "run_id": self.run_id,
                "sequence": sequence,
                "stage": normalized_stage,
                "status": _STAGE_STATUS[normalized_stage],
                "role": _route_text(role, limit=64),
                "model": _route_text(model),
                "recorded_at_ms": self._wall_clock_ms(),
                "elapsed_ms": max(0, (self._monotonic_ns() - self._started_ns) // 1_000_000),
                "previous_event_digest": previous_event_digest,
            }
            event_digest = _digest("reddog_fusion_progress_event", body)
            event = {**body, "event_id": event_digest, "event_digest": event_digest}
            self._events.append(event)
            return dict(event)

    def begin_call(self, *, role: str, model: str, requested_max_tokens: int) -> str:
        with self._lock:
            if len(self._calls) >= MAX_CALLS:
                raise ValueError("openrouter_call_receipt_limit_exceeded")
            self._call_sequence += 1
            seed = {
                "run_id": self.run_id,
                "sequence": self._call_sequence,
                "role": _route_text(role, limit=64),
                "model": _route_text(model),
            }
            call_id = _digest("reddog_openrouter_call", seed)
            self._calls[call_id] = {
                "sequence": self._call_sequence,
                "role": seed["role"],
                "model": seed["model"],
                "requested_max_tokens": _nonnegative_int(requested_max_tokens),
                "started_at_ms": self._wall_clock_ms(),
                "started_ns": self._monotonic_ns(),
            }
            return call_id

    def finish_call(
        self,
        call_id: str,
        *,
        status: str,
        retry_count: int = 0,
        generation_id: str = "",
        usage: Any = None,
        router_metadata: Any = None,
        failure_reason: str = "",
    ) -> dict[str, Any]:
        with self._lock:
            pending = self._calls.get(call_id)
            if not pending or "receipt_id" in pending:
                raise ValueError("unknown_or_finished_openrouter_call")
            usage_verified = status == "COMPLETED" and _provider_usage_verified(usage)
            safe_metadata = sanitize_openrouter_metadata(router_metadata)
            retry_total = _nonnegative_int(retry_count)
            body = {
                "schema_version": CALL_SCHEMA,
                "call_id": call_id,
                "run_id": self.run_id,
                "sequence": pending["sequence"],
                "role": pending["role"],
                "model": pending["model"],
                "status": _text(status, limit=32),
                "requested_max_tokens": pending["requested_max_tokens"],
                "started_at_ms": pending["started_at_ms"],
                "completed_at_ms": self._wall_clock_ms(),
                "duration_ms": max(0, (self._monotonic_ns() - pending["started_ns"]) // 1_000_000),
                "retry_count": retry_total,
                "generation_id": _generation_id(generation_id),
                "usage": sanitize_openrouter_usage(usage),
                "usage_verified": usage_verified,
                "cost_accounting_complete": (
                    usage_verified and retry_total == 0
                    and safe_metadata["attempt_present"] is True and safe_metadata["attempt"] == 1
                ),
                "router_metadata": safe_metadata,
                "failure_reason": _text(failure_reason, limit=96),
            }
            receipt = {**body, "receipt_id": _digest("reddog_openrouter_call_receipt", body)}
            self._calls[call_id] = receipt
            return dict(receipt)

    def receipt(self) -> dict[str, Any]:
        with self._lock:
            events = [dict(item) for item in self._events]
            calls = [
                dict(item)
                for item in sorted(self._calls.values(), key=lambda value: int(value["sequence"]))
                if "receipt_id" in item
            ]
        body = {
            "schema_version": PROGRESS_SCHEMA,
            "run_id": self.run_id,
            "events": events,
            "openrouter_calls": calls,
            "event_count": len(events),
            "openrouter_call_count": len(calls),
            "events_digest": _digest("reddog_fusion_progress_events", events),
            "openrouter_calls_digest": _digest("reddog_openrouter_calls", calls),
            "contains_prompt_or_response_content": False,
            "contains_reasoning_content": False,
        }
        return {**body, "receipt_id": _digest("reddog_fusion_progress_receipt", body)}


def validate_fusion_progress_receipt(value: Any) -> tuple[bool, tuple[str, ...]]:
    from .reddog_fusion_progress_validation import validate_fusion_progress_receipt as validate

    return validate(value)


__all__ = ["CALL_SCHEMA", "EVENT_SCHEMA", "PROGRESS_SCHEMA", "FusionProgressRecorder",
           "sanitize_openrouter_metadata", "sanitize_openrouter_usage", "validate_fusion_progress_receipt"]
