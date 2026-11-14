from __future__ import annotations

from copy import deepcopy

from modules.communication.moltbot_bridge.src.reddog_fusion_progress_receipt import (
    FusionProgressRecorder,
    sanitize_openrouter_metadata,
    sanitize_openrouter_usage,
    validate_fusion_progress_receipt,
)

LEGACY_V1_EMPTY_RECEIPT = {
    "contains_prompt_or_response_content": False,
    "contains_reasoning_content": False,
    "event_count": 0,
    "events": [],
    "events_digest": (
        "sha256:fdc918a2ba66d9f5c2a72c7f31a06659ef2c688382005a1dd19ada7235bcd6f1"
    ),
    "openrouter_call_count": 0,
    "openrouter_calls": [],
    "openrouter_calls_digest": (
        "sha256:b3ca0b3604b87e8a7be45d46a519058bbdbb922fc8092e62c1ed1bf0931389ab"
    ),
    "receipt_id": (
        "sha256:07c50c30914d62645da8e0c287dc9f2a0cfe17708854f54fba7b1993ccd83fec"
    ),
    "run_id": "run-legacy-v1",
    "schema_version": "reddog_fusion_progress_receipt.v1",
}


class _Clock:
    def __init__(self) -> None:
        self.wall = 1_000
        self.mono = 5_000_000_000

    def wall_ms(self) -> int:
        self.wall += 10
        return self.wall

    def monotonic_ns(self) -> int:
        self.mono += 1_000_000
        return self.mono


def _recorder() -> FusionProgressRecorder:
    clock = _Clock()
    return FusionProgressRecorder(
        "run-1",
        wall_clock_ms=clock.wall_ms,
        monotonic_ns=clock.monotonic_ns,
    )


def test_frozen_legacy_v1_receipt_remains_valid() -> None:
    assert validate_fusion_progress_receipt(LEGACY_V1_EMPTY_RECEIPT) == (True, ())


def test_progress_receipt_round_trip_and_tamper_rejection() -> None:
    recorder = _recorder()
    recorder.emit("lead_start", role="lead", model="model-a")
    recorder.emit("lead_done", role="lead", model="model-a")
    call_id = recorder.begin_call(role="lead", model="model-a", requested_max_tokens=400)
    recorder.finish_call(
        call_id,
        status="COMPLETED",
        generation_id="gen-1",
        usage={"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30, "cost": 0.001},
        router_metadata={"requested": "model-a", "strategy": "direct", "attempt": 1},
    )
    receipt = recorder.receipt()

    assert validate_fusion_progress_receipt(receipt) == (True, ())
    tampered = deepcopy(receipt)
    tampered["events"][0]["model"] = "model-b"
    valid, reasons = validate_fusion_progress_receipt(tampered)
    assert valid is False
    assert "progress_events_digest_mismatch" in reasons
    assert "progress_receipt_id_mismatch" in reasons

    rehashed = deepcopy(receipt)
    rehashed["events"][0]["model"] = "model-b"
    from modules.communication.moltbot_bridge.src import reddog_fusion_progress_receipt as receipts

    rehashed["events_digest"] = receipts._digest("reddog_fusion_progress_events", rehashed["events"])
    outer = {key: item for key, item in rehashed.items() if key != "receipt_id"}
    rehashed["receipt_id"] = receipts._digest("reddog_fusion_progress_receipt", outer)
    valid, reasons = validate_fusion_progress_receipt(rehashed)
    assert valid is False
    assert "progress_event_id_mismatch" in reasons

    smuggled = deepcopy(receipt)
    smuggled["openrouter_calls"][0]["prompt"] = "must-not-cross"
    smuggled["openrouter_calls_digest"] = receipts._digest("reddog_openrouter_calls", smuggled["openrouter_calls"])
    outer = {key: item for key, item in smuggled.items() if key != "receipt_id"}
    smuggled["receipt_id"] = receipts._digest("reddog_fusion_progress_receipt", outer)
    valid, reasons = validate_fusion_progress_receipt(smuggled)
    assert valid is False
    assert "openrouter_call_fields_invalid" in reasons

    nested_smuggled = deepcopy(receipt)
    nested_smuggled["openrouter_calls"][0]["router_metadata"]["selected_endpoints"] = [
        {"provider": "Provider A", "model": "model-a", "prompt": "must-not-cross"}
    ]
    call = nested_smuggled["openrouter_calls"][0]
    call_body = {key: item for key, item in call.items() if key != "receipt_id"}
    call["receipt_id"] = receipts._digest("reddog_openrouter_call_receipt", call_body)
    nested_smuggled["openrouter_calls_digest"] = receipts._digest(
        "reddog_openrouter_calls", nested_smuggled["openrouter_calls"]
    )
    outer = {key: item for key, item in nested_smuggled.items() if key != "receipt_id"}
    nested_smuggled["receipt_id"] = receipts._digest("reddog_fusion_progress_receipt", outer)
    valid, reasons = validate_fusion_progress_receipt(nested_smuggled)
    assert valid is False
    assert "openrouter_selected_endpoint_fields_invalid" in reasons


def test_unknown_stage_is_not_recorded() -> None:
    recorder = _recorder()
    assert recorder.emit("model_private_thought", role="lead") is None
    assert recorder.receipt()["event_count"] == 0


def test_run_id_cannot_carry_free_form_content() -> None:
    try:
        FusionProgressRecorder("operator prompt text")
    except ValueError as exc:
        assert str(exc) == "missing_bridge_run_id"
    else:
        raise AssertionError("expected run ID rejection")


def test_usage_sanitizer_keeps_only_numeric_accounting() -> None:
    usage = sanitize_openrouter_usage(
        {
            "prompt_tokens": 12,
            "completion_tokens": 8,
            "total_tokens": 20,
            "cost": 0.000123,
            "prompt": "secret prompt",
            "completion_tokens_details": {"reasoning_tokens": 4, "reasoning": "private"},
            "prompt_tokens_details": {"cached_tokens": 3, "raw": "private"},
        }
    )
    assert usage == {
        "prompt_tokens": 12,
        "completion_tokens": 8,
        "total_tokens": 20,
        "reasoning_tokens": 4,
        "cached_tokens": 3,
        "cost_microcredits": 123,
    }
    assert "prompt" not in usage
    assert "reasoning" not in usage


def test_router_metadata_drops_free_form_pipeline_data() -> None:
    metadata = sanitize_openrouter_metadata(
        {
            "requested": "model-a",
            "strategy": "fusion",
            "region": "iad",
            "attempt": 2,
            "is_byok": True,
            "summary": "may contain provider prose",
            "endpoints": {
                "available": [
                    {"provider": "Provider A", "model": "model-a", "selected": True, "token": "secret"},
                    {"provider": "Provider B", "model": "model-a", "selected": False},
                ]
            },
            "pipeline": [{"type": "guardrail", "name": "content-filter", "data": {"raw": "secret"}}],
        }
    )
    assert metadata["selected_endpoints"] == [{"provider": "Provider A", "model": "model-a"}]
    assert metadata["pipeline_stages"] == [{"type": "guardrail", "name": "content-filter"}]
    assert metadata["response_provider"] == ""
    assert metadata["response_model"] == ""
    assert "summary" not in metadata
    assert "data" not in metadata["pipeline_stages"][0]


def test_failed_call_is_receipted_without_usage_or_content() -> None:
    recorder = _recorder()
    call_id = recorder.begin_call(role="critic", model="model-b", requested_max_tokens=900)
    call = recorder.finish_call(call_id, status="FAILED", retry_count=2, failure_reason="timeout")
    assert call["status"] == "FAILED"
    assert call["failure_reason"] == "timeout"
    assert call["usage"]["total_tokens"] == 0
    assert call["usage_verified"] is False
    assert call["cost_accounting_complete"] is False
    assert "content" not in call
    assert "messages" not in call
    assert "secret" not in str(call).lower()


def test_secret_like_route_and_failure_values_are_removed() -> None:
    recorder = _recorder()
    secret = "sk-or-v1-THIS-IS-A-SECRET-TOKEN"
    call_id = recorder.begin_call(role="lead", model=secret, requested_max_tokens=1)
    call = recorder.finish_call(
        call_id,
        status="FAILED",
        failure_reason=secret,
        router_metadata={"requested": secret, "response_provider": secret},
    )
    assert call["model"] == ""
    assert call["failure_reason"] == ""
    assert call["router_metadata"]["requested"] == ""
    assert call["router_metadata"]["response_provider"] == ""
    assert secret not in str(recorder.receipt())


def test_completed_call_with_malformed_usage_is_not_verified() -> None:
    recorder = _recorder()
    call_id = recorder.begin_call(role="lead", model="model-a", requested_max_tokens=10)
    call = recorder.finish_call(
        call_id,
        status="COMPLETED",
        usage={"prompt_tokens": -1, "completion_tokens": 2, "total_tokens": 1},
    )
    assert call["usage_verified"] is False
    assert call["cost_accounting_complete"] is False


def test_completed_call_with_inconsistent_usage_total_is_not_verified() -> None:
    recorder = _recorder()
    call_id = recorder.begin_call(role="lead", model="model-a", requested_max_tokens=10)
    call = recorder.finish_call(
        call_id,
        status="COMPLETED",
        usage={"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 9, "cost": 0.001},
    )
    assert call["usage_verified"] is False
    assert call["cost_accounting_complete"] is False


def test_retry_success_keeps_cost_accounting_incomplete() -> None:
    recorder = _recorder()
    recorder.emit("lead_start", role="lead", model="model-a")
    call_id = recorder.begin_call(role="lead", model="model-a", requested_max_tokens=10)
    call = recorder.finish_call(
        call_id,
        status="COMPLETED",
        retry_count=2,
        usage={"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 5, "cost": 0.001},
    )
    assert call["usage_verified"] is True
    assert call["cost_accounting_complete"] is False
    assert validate_fusion_progress_receipt(recorder.receipt()) == (True, ())

    recorder = _recorder()
    recorder.emit("lead_start", role="lead", model="model-a")
    call_id = recorder.begin_call(role="lead", model="model-a", requested_max_tokens=10)
    call = recorder.finish_call(
        call_id,
        status="COMPLETED",
        usage={"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 5, "cost": 0.001},
    )
    assert call["usage_verified"] is True
    assert call["router_metadata"]["attempt_present"] is False
    assert call["cost_accounting_complete"] is False
    assert validate_fusion_progress_receipt(recorder.receipt()) == (True, ())

    recorder = _recorder()
    recorder.emit("lead_start", role="lead", model="model-a")
    call_id = recorder.begin_call(role="lead", model="model-a", requested_max_tokens=10)
    call = recorder.finish_call(
        call_id,
        status="COMPLETED",
        usage={"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 5, "cost": 0.001},
        router_metadata={"attempt": 2},
    )
    assert call["cost_accounting_complete"] is False
    assert validate_fusion_progress_receipt(recorder.receipt()) == (True, ())


def test_progress_and_call_correlation_fails_closed() -> None:
    recorder = _recorder()
    recorder.emit("lead_start", role="lead", model="model-a")
    recorder.emit("lead_done", role="lead", model="model-a")
    valid, reasons = validate_fusion_progress_receipt(recorder.receipt())
    assert valid is False
    assert "progress_terminal_call_missing" in reasons

    recorder = _recorder()
    call_id = recorder.begin_call(role="lead", model="model-a", requested_max_tokens=1)
    recorder.finish_call(
        call_id,
        status="COMPLETED",
        usage={"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2, "cost": 0.001},
    )
    valid, reasons = validate_fusion_progress_receipt(recorder.receipt())
    assert valid is False
    assert "openrouter_call_progress_start_missing" in reasons


def test_receipt_declares_content_and_reasoning_boundaries() -> None:
    receipt = _recorder().receipt()
    assert receipt["contains_prompt_or_response_content"] is False
    assert receipt["contains_reasoning_content"] is False


def test_call_limit_fails_closed() -> None:
    recorder = _recorder()
    for index in range(16):
        recorder.begin_call(role="critic", model=f"model-{index}", requested_max_tokens=1)
    try:
        recorder.begin_call(role="critic", model="overflow", requested_max_tokens=1)
    except ValueError as exc:
        assert str(exc) == "openrouter_call_receipt_limit_exceeded"
    else:
        raise AssertionError("expected call limit rejection")
