"""Focused defensive critic and abstention contracts."""

from __future__ import annotations

import inspect
from unittest import mock

import scripts.advisory_model_once as bridge


def test_kimi_k3_none_is_recorded_as_abstention_and_quorum_fails_closed():
    def fake_completion(_key, model, _messages, **_kwargs):
        if model == "moonshotai/kimi-k3":
            return "None", {"retry_count": 0, "final_retry_reason": None}
        return "Lead evidence with WSP_15 priority and next safest step.", {
            "retry_count": 0,
            "final_retry_reason": None,
        }

    payload = {
        "lead_model": "z-ai/glm-5.2",
        "panel_models": ["moonshotai/kimi-k3"],
        "system": "RedDog Architect defensive review.",
    }
    with mock.patch.object(bridge, "_chat_completion", side_effect=fake_completion):
        result = bridge._run_foundups_fusion("key", "Audit pfmall defensively", [], payload)

    assert result["ok"] is False
    assert result["reason"] == "fusion_quorum_challenging_critic_missing"
    quorum = result["review_packet"]["fusion_panel_quorum"]
    assert quorum["passed"] is False
    assert quorum["challenging_critics"] == []
    assert quorum["abstaining_critics"] == ["moonshotai/kimi-k3"]


def test_critic_prompt_uses_defensive_critical_review_wording():
    source = inspect.getsource(bridge._run_foundups_fusion_core)
    assert "critically review the lead answer" in source
    assert "identifying, preventing, or remediating" in source
    assert "omit exploit details" in source
    assert "attack the lead answer" not in source


def test_critic_retry_uses_defensive_provider_safe_wording():
    source = inspect.getsource(bridge._defensive_critic_retry_messages)
    assert "Independent defensive evidence review" in source
    assert "never fabricate a defect" in source
    assert "adversarial" not in source.lower()
