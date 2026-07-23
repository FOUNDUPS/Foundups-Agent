"""Exact-schema validator for content-free RedDog Fusion progress receipts."""

from __future__ import annotations

from typing import Any, Mapping

from . import reddog_fusion_progress_receipt as receipt
from .reddog_provider_call_evidence import validate_provider_call_evidence


_CALL_STATUSES = frozenset({"COMPLETED", "FAILED"})
_EVENT_KEYS = frozenset({"schema_version", "run_id", "sequence", "stage", "status", "role", "model",
                         "recorded_at_ms", "elapsed_ms", "previous_event_digest", "event_id", "event_digest"})
_USAGE_KEYS = frozenset({"prompt_tokens", "completion_tokens", "total_tokens", "reasoning_tokens",
                         "cached_tokens", "cost_microcredits"})
_ROUTER_KEYS = frozenset({"requested", "strategy", "region", "attempt", "is_byok", "response_provider",
                          "attempt_present", "response_model", "selected_endpoints", "pipeline_stages"})
_ENDPOINT_KEYS = frozenset({"provider", "model"})
_PIPELINE_STAGE_KEYS = frozenset({"type", "name"})
_CALL_KEYS = frozenset({
    "schema_version", "call_id", "run_id", "sequence", "role", "model", "status", "requested_max_tokens",
    "started_at_ms", "completed_at_ms", "duration_ms", "retry_count", "generation_id", "usage",
    "usage_verified", "cost_accounting_complete", "router_metadata", "failure_reason", "receipt_id",
})
_RECEIPT_KEYS = frozenset({
    "schema_version", "run_id", "events", "openrouter_calls", "event_count", "openrouter_call_count",
    "events_digest", "openrouter_calls_digest", "contains_prompt_or_response_content",
    "contains_reasoning_content", "provider_call_evidence", "provider_call_evidence_count",
    "provider_call_evidence_digest", "receipt_id",
})
_REQUIRED_START = {
    "lead_done": "lead_start", "synthesis_done": "synthesis_start", "single_done": "single_start",
    "fusion_alias_done": "fusion_alias_start", "redaction_pass": "redaction_start",
    "redaction_blocked": "redaction_start", "panel_done": "panel_start", "panel_blocked": "panel_start",
}
_START_STAGES = frozenset(_REQUIRED_START.values())


def _valid_counter(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, int) and 0 <= value <= 10**15


def _valid_route_value(value: Any, *, limit: int = receipt.MAX_TEXT) -> bool:
    if not isinstance(value, str) or len(value) > limit:
        return False
    return value == "" or (
        receipt._SECRET_LIKE.search(value) is None and receipt._ROUTE_TEXT.fullmatch(value) is not None
    )


def _validate_router_metadata(metadata: Mapping[str, Any], reasons: list[str]) -> None:
    if not all(_valid_route_value(metadata.get(key)) for key in (
        "requested", "strategy", "region", "response_provider", "response_model"
    )):
        reasons.append("openrouter_router_metadata_value_invalid")
    if (
        not _valid_counter(metadata.get("attempt"))
        or not isinstance(metadata.get("attempt_present"), bool)
        or not isinstance(metadata.get("is_byok"), bool)
    ):
        reasons.append("openrouter_router_metadata_value_invalid")
    if metadata.get("attempt_present") is False and metadata.get("attempt") != 0:
        reasons.append("openrouter_router_metadata_attempt_invalid")

    endpoints = metadata.get("selected_endpoints")
    if not isinstance(endpoints, list) or len(endpoints) > 8:
        reasons.append("openrouter_selected_endpoints_invalid")
    else:
        for endpoint in endpoints:
            if not isinstance(endpoint, Mapping) or set(endpoint) != _ENDPOINT_KEYS:
                reasons.append("openrouter_selected_endpoint_fields_invalid")
                continue
            if not all(_valid_route_value(endpoint.get(key)) for key in _ENDPOINT_KEYS):
                reasons.append("openrouter_selected_endpoint_value_invalid")

    stages = metadata.get("pipeline_stages")
    if not isinstance(stages, list) or len(stages) > 12:
        reasons.append("openrouter_pipeline_stages_invalid")
    else:
        for stage in stages:
            if not isinstance(stage, Mapping) or set(stage) != _PIPELINE_STAGE_KEYS:
                reasons.append("openrouter_pipeline_stage_fields_invalid")
                continue
            if not all(_valid_route_value(stage.get(key)) for key in _PIPELINE_STAGE_KEYS):
                reasons.append("openrouter_pipeline_stage_value_invalid")


def _validate_events(events: list[Any], run_id: Any, reasons: list[str]) -> None:
    previous = "GENESIS"
    started: set[tuple[str, str, str]] = set()
    for index, event in enumerate(events, start=1):
        if not isinstance(event, Mapping) or event.get("schema_version") != receipt.EVENT_SCHEMA:
            reasons.append("progress_event_invalid")
            continue
        if set(event) != _EVENT_KEYS:
            reasons.append("progress_event_fields_invalid")
        event_body = {key: item for key, item in event.items() if key not in {"event_id", "event_digest"}}
        if event.get("run_id") != run_id or event.get("sequence") != index:
            reasons.append("progress_event_binding_invalid")
        if not all(_valid_counter(event.get(key)) for key in ("sequence", "recorded_at_ms", "elapsed_ms")):
            reasons.append("progress_event_numeric_invalid")
        if not _valid_route_value(event.get("role"), limit=64) or not _valid_route_value(event.get("model")):
            reasons.append("progress_event_route_value_invalid")
        if event.get("previous_event_digest") != previous:
            reasons.append("progress_event_chain_invalid")
        stage = event.get("stage")
        if stage not in receipt._STAGE_STATUS or event.get("status") != receipt._STAGE_STATUS.get(stage):
            reasons.append("progress_event_status_invalid")
        key = (str(stage), str(event.get("role") or ""), str(event.get("model") or ""))
        if stage in _START_STAGES:
            started.add(key)
        required = _REQUIRED_START.get(str(stage))
        if required:
            found = any(item[0] == "panel_start" for item in started) if required == "panel_start" else (required, key[1], key[2]) in started
            if not found:
                reasons.append("progress_event_transition_invalid")
        expected = receipt._digest("reddog_fusion_progress_event", event_body)
        if event.get("event_id") != expected or event.get("event_digest") != expected:
            reasons.append("progress_event_id_mismatch")
        previous = str(event.get("event_digest") or "")


def _validate_calls(calls: list[Any], run_id: Any, reasons: list[str]) -> None:
    for index, call in enumerate(calls, start=1):
        if not isinstance(call, Mapping) or call.get("schema_version") != receipt.CALL_SCHEMA:
            reasons.append("openrouter_call_invalid")
            continue
        if set(call) != _CALL_KEYS:
            reasons.append("openrouter_call_fields_invalid")
        call_body = {key: item for key, item in call.items() if key != "receipt_id"}
        if call.get("run_id") != run_id or call.get("sequence") != index:
            reasons.append("openrouter_call_binding_invalid")
        expected_call_id = receipt._digest("reddog_openrouter_call", {
            "run_id": run_id, "sequence": index, "role": call.get("role"), "model": call.get("model"),
        })
        if call.get("call_id") != expected_call_id:
            reasons.append("openrouter_call_id_mismatch")
        numeric_keys = ("sequence", "requested_max_tokens", "started_at_ms", "completed_at_ms", "duration_ms", "retry_count")
        if not all(_valid_counter(call.get(key)) for key in numeric_keys):
            reasons.append("openrouter_call_numeric_invalid")
        if _valid_counter(call.get("started_at_ms")) and _valid_counter(call.get("completed_at_ms")):
            if call["completed_at_ms"] < call["started_at_ms"]:
                reasons.append("openrouter_call_time_invalid")
        if not _valid_route_value(call.get("role"), limit=64) or not _valid_route_value(call.get("model")):
            reasons.append("openrouter_call_route_value_invalid")
        generation_id = call.get("generation_id")
        if not isinstance(generation_id, str) or (
            generation_id != "" and receipt._GENERATION_ID.fullmatch(generation_id) is None
        ):
            reasons.append("openrouter_generation_id_invalid")
        if not _valid_route_value(call.get("failure_reason"), limit=96):
            reasons.append("openrouter_failure_reason_invalid")
        if call.get("status") not in _CALL_STATUSES:
            reasons.append("openrouter_call_status_invalid")
        usage, metadata = call.get("usage"), call.get("router_metadata")
        if not isinstance(usage, Mapping) or set(usage) != _USAGE_KEYS:
            reasons.append("openrouter_usage_fields_invalid")
        elif not all(_valid_counter(usage.get(key)) for key in _USAGE_KEYS):
            reasons.append("openrouter_usage_value_invalid")
        elif call.get("usage_verified") is True and usage.get("total_tokens") != (
            usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)
        ):
            reasons.append("openrouter_usage_total_invalid")
        if not isinstance(metadata, Mapping) or set(metadata) != _ROUTER_KEYS:
            reasons.append("openrouter_router_metadata_fields_invalid")
        else:
            _validate_router_metadata(metadata, reasons)
        if not isinstance(call.get("usage_verified"), bool) or not isinstance(call.get("cost_accounting_complete"), bool):
            reasons.append("openrouter_usage_verification_invalid")
        elif call.get("cost_accounting_complete") is not (
            call.get("usage_verified") is True
            and call.get("retry_count") == 0
            and isinstance(metadata, Mapping)
            and metadata.get("attempt_present") is True
            and metadata.get("attempt") == 1
        ):
            reasons.append("openrouter_cost_accounting_consistency_invalid")
        if call.get("status") == "FAILED" and (call.get("usage_verified") or call.get("cost_accounting_complete")):
            reasons.append("openrouter_failed_call_accounting_invalid")
        if call.get("status") == "FAILED" and isinstance(usage, Mapping) and any(usage.get(key) != 0 for key in _USAGE_KEYS):
            reasons.append("openrouter_failed_call_usage_invalid")
        if call.get("status") == "FAILED" and not call.get("failure_reason"):
            reasons.append("openrouter_failure_reason_missing")
        if call.get("status") == "COMPLETED" and call.get("failure_reason"):
            reasons.append("openrouter_completed_call_failure_reason_invalid")
        if call.get("receipt_id") != receipt._digest("reddog_openrouter_call_receipt", call_body):
            reasons.append("openrouter_call_receipt_id_mismatch")


def _validate_event_call_correlation(events: list[Any], calls: list[Any], reasons: list[str]) -> None:
    event_rows = [item for item in events if isinstance(item, Mapping)]
    call_rows = [item for item in calls if isinstance(item, Mapping)]

    def has_event(stage: str, *, model: Any = None) -> bool:
        return any(
            item.get("stage") == stage and (model is None or item.get("model") == model)
            for item in event_rows
        )

    def has_call(role: str, *, model: Any = None, status: str | None = None) -> bool:
        return any(
            item.get("role") == role
            and (model is None or item.get("model") == model)
            and (status is None or item.get("status") == status)
            for item in call_rows
        )

    start_for_role = {
        "lead": "lead_start", "synthesis": "synthesis_start", "single": "single_start",
        "critic": "panel_start", "fusion_alias": "fusion_alias_start",
    }
    for call in call_rows:
        role = call.get("role")
        start = start_for_role.get(role)
        if start is None:
            reasons.append("openrouter_call_role_invalid")
            continue
        model = call.get("model") if role in {"lead", "synthesis", "single"} else None
        if not has_event(start, model=model):
            reasons.append("openrouter_call_progress_start_missing")

    terminal_bindings = {
        "lead_done": ("lead", "COMPLETED"),
        "synthesis_done": ("synthesis", "COMPLETED"),
        "single_done": ("single", "COMPLETED"),
        "fusion_alias_done": ("fusion_alias", "COMPLETED"),
        "panel_done": ("critic", "COMPLETED"),
        "panel_blocked": ("critic", None),
    }
    for event in event_rows:
        binding = terminal_bindings.get(event.get("stage"))
        if binding is None:
            continue
        role, status = binding
        model = event.get("model") if role in {"lead", "synthesis", "single", "critic"} else None
        if not has_call(role, model=model, status=status):
            reasons.append("progress_terminal_call_missing")


def validate_fusion_progress_receipt(value: Any) -> tuple[bool, tuple[str, ...]]:
    if not isinstance(value, Mapping) or value.get("schema_version") != receipt.PROGRESS_SCHEMA:
        return False, ("progress_receipt_schema_invalid",)
    if set(value) != _RECEIPT_KEYS:
        return False, ("progress_receipt_fields_invalid",)
    body = {key: item for key, item in value.items() if key != "receipt_id"}
    reasons: list[str] = []
    run_id = body.get("run_id")
    if not isinstance(run_id, str) or receipt._RUN_ID.fullmatch(run_id) is None:
        reasons.append("progress_run_id_invalid")
    events, calls = body.get("events"), body.get("openrouter_calls")
    if not isinstance(events, list) or len(events) > receipt.MAX_EVENTS:
        reasons.append("progress_events_invalid")
    else:
        if body.get("event_count") != len(events):
            reasons.append("progress_event_count_mismatch")
        if body.get("events_digest") != receipt._digest("reddog_fusion_progress_events", events):
            reasons.append("progress_events_digest_mismatch")
        _validate_events(events, body.get("run_id"), reasons)
    if not isinstance(calls, list) or len(calls) > receipt.MAX_CALLS:
        reasons.append("openrouter_calls_invalid")
    else:
        if body.get("openrouter_call_count") != len(calls):
            reasons.append("openrouter_call_count_mismatch")
        if body.get("openrouter_calls_digest") != receipt._digest("reddog_openrouter_calls", calls):
            reasons.append("openrouter_calls_digest_mismatch")
        _validate_calls(calls, body.get("run_id"), reasons)
    if isinstance(events, list) and isinstance(calls, list):
        _validate_event_call_correlation(events, calls, reasons)
    provider_evidence = body.get("provider_call_evidence")
    if not isinstance(provider_evidence, list) or len(provider_evidence) > receipt.MAX_CALLS:
        reasons.append("provider_call_evidence_invalid")
    else:
        if body.get("provider_call_evidence_count") != len(provider_evidence):
            reasons.append("provider_call_evidence_count_mismatch")
        if body.get("provider_call_evidence_digest") != receipt._digest(
            "reddog_provider_call_evidence", provider_evidence
        ):
            reasons.append("provider_call_evidence_digest_mismatch")
        for item in provider_evidence:
            try:
                evidence = validate_provider_call_evidence(item)
            except (TypeError, ValueError):
                reasons.append("provider_call_evidence_receipt_invalid")
                continue
            if evidence.run_id is not None and evidence.run_id != run_id:
                reasons.append("provider_call_evidence_binding_invalid")
    if value.get("receipt_id") != receipt._digest("reddog_fusion_progress_receipt", body):
        reasons.append("progress_receipt_id_mismatch")
    if body.get("contains_prompt_or_response_content") is not False:
        reasons.append("progress_content_boundary_invalid")
    if body.get("contains_reasoning_content") is not False:
        reasons.append("progress_reasoning_boundary_invalid")
    return not reasons, tuple(dict.fromkeys(reasons))


__all__ = ["validate_fusion_progress_receipt"]
