from __future__ import annotations

from modules.communication.moltbot_bridge.src.reddog_fusion_progress_receipt import (
    FusionProgressRecorder,
    validate_fusion_progress_receipt,
)


def _completed_call(recorder: FusionProgressRecorder, role: str, model: str) -> None:
    call_id = recorder.begin_call(role=role, model=model, requested_max_tokens=400)
    recorder.finish_call(
        call_id,
        status="COMPLETED",
        generation_id=f"gen-{role}",
        usage={"prompt_tokens": 2, "completion_tokens": 1, "total_tokens": 3, "cost": 0.001},
        router_metadata={"requested": model, "attempt": 1},
    )


def test_bounded_semantic_retries_remain_valid_progress() -> None:
    recorder = FusionProgressRecorder("run-semantic-retry")
    recorder.emit("lead_start", role="lead", model="model-a")
    _completed_call(recorder, "lead", "model-a")
    recorder.emit("lead_retry", role="lead", model="model-a")
    recorder.emit("lead_start", role="lead", model="model-a")
    _completed_call(recorder, "lead", "model-a")
    recorder.emit("lead_done", role="lead", model="model-a")
    recorder.emit("panel_start", role="panel", model="model-b")
    _completed_call(recorder, "critic", "model-b")
    recorder.emit("panel_done", role="critic", model="model-b")
    recorder.emit("panel_retry", role="critic", model="model-b")
    recorder.emit("panel_start", role="panel", model="model-b")
    _completed_call(recorder, "critic", "model-b")
    recorder.emit("panel_done", role="critic", model="model-b")
    assert validate_fusion_progress_receipt(recorder.receipt()) == (True, ())
