"""Bridge hardening tests for advisory_model_once (Addendum B + C)."""

from __future__ import annotations

import io
import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock
from urllib.error import HTTPError

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import scripts.advisory_model_once as bridge  # noqa: E402
from modules.communication.moltbot_bridge.src.fusion_redaction_gate import (  # noqa: E402
    REDACTION_GATE_PASSED,
    RedactionReport,
)


def _passed_gate(*, prompt: str = "redacted-prompt", context: str | None = None):
    # Attach a REAL RedactionReport so the per-target-isolation telemetry fields
    # (blocked_paths / blocked_reasons) are iterable tuples, not Mock attributes.
    return mock.Mock(
        status=REDACTION_GATE_PASSED,
        redacted_prompt=prompt,
        redacted_context=context,
        reason="ok",
        report=RedactionReport(),
    )


def _invoke_bridge_main(payload: dict, *, api_key: str = "test-key") -> tuple[int, dict]:
    stdin_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    stdin_buffer = io.BytesIO(stdin_bytes)
    stdout = io.StringIO()
    fake_stdin = mock.Mock()
    fake_stdin.buffer = stdin_buffer
    with mock.patch("sys.stdin", fake_stdin), mock.patch("sys.stdout", stdout), mock.patch.dict(
        os.environ, {bridge.ENV_API_KEY: api_key}, clear=False
    ):
        rc = bridge.main()
    return rc, json.loads(stdout.getvalue())


class AdvisoryBridgeHardeningTests(unittest.TestCase):
    def _invoke_main(self, payload: dict, *, api_key: str = "test-key") -> tuple[int, dict]:
        return _invoke_bridge_main(payload, api_key=api_key)

    def test_panel_models_capped_at_six(self) -> None:
        models = bridge._panel_models(["m" + str(i) for i in range(12)])
        self.assertLessEqual(len(models), bridge.MAX_PANEL_MODELS)
        self.assertEqual(len(models), 6)

    def test_panel_models_truncated_metadata(self) -> None:
        models, truncated = bridge._panel_models_with_meta(["m" + str(i) for i in range(12)])
        self.assertTrue(truncated)
        self.assertEqual(len(models), bridge.MAX_PANEL_MODELS)

    def test_default_panel_keeps_kimi_code_and_adds_kimi_k3(self) -> None:
        self.assertIn("moonshotai/kimi-k2.7-code", bridge.DEFAULT_PANEL_MODELS)
        self.assertIn("moonshotai/kimi-k3", bridge.DEFAULT_PANEL_MODELS)
        self.assertEqual(bridge.KIMI_K3_PANEL_MAX_TOKENS, 4096)

    def test_kimi_k3_completion_uses_mandatory_max_reasoning_without_temperature(self) -> None:
        post = mock.Mock(
            return_value=(
                {"choices": [{"message": {"content": "ok"}}]},
                {"retry_count": 0, "final_retry_reason": None},
            )
        )
        with mock.patch.object(bridge, "_post_openrouter", post):
            content, _meta = bridge._chat_completion(
                "key",
                "moonshotai/kimi-k3",
                [{"role": "user", "content": "test"}],
                max_tokens=256,
                temperature=0.2,
                timeout=30,
            )

        self.assertEqual(content, "ok")
        body = post.call_args.args[1]
        self.assertEqual(body["reasoning"], {"effort": "max"})
        self.assertNotIn("temperature", body)

    def test_retry_429_then_success(self) -> None:
        calls: list[dict] = []
        responses = [
            HTTPError("https://x", 429, "rate", {}, io.BytesIO(b'{"error":{"message":"rate"}}')),
            json.dumps({"choices": [{"message": {"content": "ok"}}]}).encode("utf-8"),
        ]

        def fake_urlopen(request, timeout=0):  # noqa: ARG001
            calls.append({"body": request.data.decode("utf-8")})
            item = responses.pop(0)
            if isinstance(item, HTTPError):
                raise item
            return io.BytesIO(item)

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            data, meta = bridge._post_openrouter("key", {"model": "x", "messages": []}, 30)

        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0]["body"], calls[1]["body"])
        self.assertGreater(meta["retry_count"], 0)
        self.assertEqual(meta["final_retry_reason"], "http_429")
        self.assertIn("choices", data)

    def test_no_retry_on_400(self) -> None:
        calls: list[dict] = []

        def fake_urlopen(request, timeout=0):  # noqa: ARG001
            calls.append({"body": request.data.decode("utf-8")})
            raise HTTPError("https://x", 400, "bad", {}, io.BytesIO(b'{"error":{"message":"bad"}}'))

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            with self.assertRaises(HTTPError) as ctx:
                bridge._post_openrouter("key", {"model": "x", "messages": []}, 30)

        self.assertEqual(len(calls), 1)
        meta = getattr(ctx.exception, "retry_meta", {"retry_count": 0})
        self.assertEqual(meta.get("retry_count", 0), 0)

    def test_main_429_success_redaction_once_same_body(self) -> None:
        gate_mock = mock.Mock(return_value=_passed_gate())
        bodies: list[str] = []
        responses = [
            HTTPError("https://x", 429, "rate", {}, io.BytesIO(b'{"error":{"message":"rate"}}')),
            json.dumps({"choices": [{"message": {"content": "ok"}}]}).encode("utf-8"),
        ]

        def fake_urlopen(request, timeout=0):  # noqa: ARG001
            bodies.append(request.data.decode("utf-8"))
            item = responses.pop(0)
            if isinstance(item, HTTPError):
                raise item
            return io.BytesIO(item)

        with mock.patch.object(bridge, "evaluate_redaction_gate", gate_mock), mock.patch(
            "urllib.request.urlopen", side_effect=fake_urlopen
        ):
            _rc, out = self._invoke_main(
                {
                    "mode": "openrouter_single",
                    "prompt": "012 work focus",
                    "lead_model": "z-ai/glm-5.2",
                }
            )

        gate_mock.assert_called_once()
        self.assertEqual(len(bodies), 2)
        self.assertEqual(bodies[0], bodies[1])
        self.assertTrue(out.get("ok"))
        self.assertGreater(out.get("retry_count", 0), 0)
        self.assertEqual(out.get("final_retry_reason"), "http_429")
        packet = out.get("review_packet") or {}
        self.assertGreater(packet.get("retry_count", 0), 0)
        self.assertEqual(packet.get("final_retry_reason"), "http_429")

    def test_main_400_single_attempt_no_retry_exhausted(self) -> None:
        gate_mock = mock.Mock(return_value=_passed_gate())
        call_count = {"n": 0}

        def fake_urlopen(request, timeout=0):  # noqa: ARG001
            call_count["n"] += 1
            raise HTTPError("https://x", 400, "bad", {}, io.BytesIO(b'{"error":{"message":"bad"}}'))

        with mock.patch.object(bridge, "evaluate_redaction_gate", gate_mock), mock.patch(
            "urllib.request.urlopen", side_effect=fake_urlopen
        ):
            _rc, out = self._invoke_main(
                {
                    "mode": "openrouter_single",
                    "prompt": "012 work focus",
                    "lead_model": "z-ai/glm-5.2",
                }
            )

        gate_mock.assert_called_once()
        self.assertEqual(call_count["n"], 1)
        self.assertFalse(out.get("ok"))
        self.assertEqual(out.get("reason"), "http_error")
        self.assertNotEqual(out.get("reason"), "retry_exhausted")
        self.assertEqual(out.get("retry_count", 0), 0)

    def test_redaction_blocked_zero_network_calls(self) -> None:
        gate_mock = mock.Mock(
            return_value=mock.Mock(
                status="BLOCKED",
                redacted_prompt="",
                redacted_context=None,
                reason="blocked",
                report=RedactionReport(),
            )
        )
        post_mock = mock.Mock()

        with mock.patch.object(bridge, "evaluate_redaction_gate", gate_mock), mock.patch.object(
            bridge, "_post_openrouter", post_mock
        ):
            _rc, out = self._invoke_main(
                {
                    "mode": "openrouter_single",
                    "prompt": "secret material",
                    "lead_model": "z-ai/glm-5.2",
                }
            )

        post_mock.assert_not_called()
        # Non-audit legacy path: required_target_paths collapses to None (byte-identical to pre-hardening).
        gate_mock.assert_called_once_with(
            "secret material", None, audit_mode=False, required_target_paths=None
        )
        self.assertFalse(out.get("ok"))
        self.assertEqual(out.get("reason"), "redaction_blocked")
        self.assertEqual(out.get("retry_count"), 0)

    def test_main_panel_models_truncated_in_review_packet(self) -> None:
        gate_mock = mock.Mock(return_value=_passed_gate())
        fusion_result = {
            "ok": True,
            "reason": "ok",
            "mode": "foundups_fusion",
            "content": "panel output",
            "review_packet": {
                "mode": "foundups_fusion",
                "panel_models": ["m0", "m1", "m2", "m3", "m4", "m5"],
                "panel_models_truncated": True,
            },
        }

        with mock.patch.object(bridge, "evaluate_redaction_gate", gate_mock), mock.patch.object(
            bridge, "_run_foundups_fusion", return_value=fusion_result
        ):
            _rc, out = self._invoke_main(
                {
                    "mode": "foundups_fusion",
                    "prompt": "012 work focus",
                    "panel_models": ["m" + str(i) for i in range(10)],
                    "bridge_meta": {"python_interpreter_source": "system"},
                }
            )

        gate_mock.assert_called_once()
        self.assertTrue(out.get("ok"))
        packet = out.get("review_packet") or {}
        self.assertTrue(packet.get("panel_models_truncated"))
        self.assertEqual(packet.get("python_interpreter_source"), "system")
        self.assertLessEqual(len(packet.get("panel_models") or []), bridge.MAX_PANEL_MODELS)

    def test_fusion_quorum_blocks_missing_required_evidence_before_network(self) -> None:
        chat_mock = mock.Mock()
        with mock.patch.object(bridge, "_chat_completion", chat_mock):
            result = bridge._run_foundups_fusion(
                "key",
                "prompt that names docs/missing.md but has no evidence context",
                [],
                {
                    "lead_model": "lead-model",
                    "panel_models": ["critic-a"],
                    "required_target_paths": ["docs/missing.md"],
                    "_redacted_evidence_context": "### Required direct-read target: docs/present.md\ncontent",
                },
            )
        chat_mock.assert_not_called()
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "fusion_quorum_missing_required_evidence")
        quorum = result["review_packet"]["fusion_panel_quorum"]
        self.assertEqual(quorum["missing_required_evidence"], ["docs/missing.md"])

    def test_fusion_quorum_blocks_none_lead_before_panel(self) -> None:
        calls: list[str] = []

        def fake_chat(api_key, model, messages, **kwargs):  # noqa: ANN001, ARG001
            calls.append(str(messages[0]["content"]))
            return "None", {"retry_count": 0}

        with mock.patch.object(bridge, "_chat_completion", side_effect=fake_chat):
            result = bridge._run_foundups_fusion(
                "key",
                "prompt\n\n### Required direct-read target: docs/present.md\ncontent",
                [],
                {
                    "lead_model": "lead-model",
                    "panel_models": ["critic-a"],
                    "required_target_paths": ["docs/present.md"],
                    "_redacted_evidence_context": "### Required direct-read target: docs/present.md\ncontent",
                },
            )
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "fusion_quorum_lead_missing")
        self.assertEqual(len(calls), 2)
        self.assertEqual(
            result["review_packet"]["fusion_panel_quorum"]["lead_semantic_retry_count"],
            1,
        )

    def test_fusion_quorum_semantic_retry_recovers_none_lead(self) -> None:
        lead_calls = 0

        def fake_chat(api_key, model, messages, **kwargs):  # noqa: ANN001, ARG001
            nonlocal lead_calls
            system = str(messages[0]["content"])
            if "Lead pass" in system:
                lead_calls += 1
                if lead_calls == 1:
                    return "None", {"retry_count": 0}
                return "## Decision\nProceed\n\nEvidence docs/present.md:1", {"retry_count": 0}
            if "Panel critic pass" in system:
                return (
                    "Challenge: the evidence claim is unsupported and the WSP_15 "
                    "priority order needs verification.",
                    {"retry_count": 0},
                )
            return "## Decision\nProceed\n\n## WSP_15 Priority\nP1", {"retry_count": 0}

        with mock.patch.object(bridge, "_chat_completion", side_effect=fake_chat):
            result = bridge._run_foundups_fusion(
                "key",
                "prompt\n\n### Required direct-read target: docs/present.md\ncontent",
                [],
                {
                    "lead_model": "lead-model",
                    "panel_models": ["critic-a"],
                    "required_target_paths": ["docs/present.md"],
                    "_redacted_evidence_context": "### Required direct-read target: docs/present.md\ncontent",
                },
            )
        self.assertTrue(result["ok"])
        self.assertEqual(lead_calls, 2)
        self.assertEqual(
            result["review_packet"]["fusion_panel_quorum"]["lead_semantic_retry_count"],
            1,
        )

    def test_fusion_quorum_requires_critic_challenge_to_framing_and_priority(self) -> None:
        retry_models: list[str] = []

        def fake_chat(api_key, model, messages, **kwargs):  # noqa: ANN001, ARG001
            system = str(messages[0]["content"])
            if "Lead pass" in system:
                return "## Decision\nProceed\n\nEvidence docs/present.md:1", {"retry_count": 0}
            if "Independent defensive evidence review" in system:
                retry_models.append(model)
                return "Looks generally reasonable.", {"retry_count": 0}
            if "Panel critic pass" in system:
                return "Looks generally reasonable.", {"retry_count": 0}
            return "Synthesis should not run", {"retry_count": 0}

        with mock.patch.object(bridge, "_chat_completion", side_effect=fake_chat):
            result = bridge._run_foundups_fusion(
                "key",
                "prompt\n\n### Required direct-read target: docs/present.md\ncontent",
                [],
                {
                    "lead_model": "lead-model",
                    "panel_models": ["critic-a", "critic-b"],
                    "required_target_paths": ["docs/present.md"],
                    "_redacted_evidence_context": "### Required direct-read target: docs/present.md\ncontent",
                },
            )
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "fusion_quorum_challenging_critic_missing")
        quorum = result["review_packet"]["fusion_panel_quorum"]
        self.assertEqual(quorum["challenging_critics"], [])
        self.assertEqual(retry_models, ["critic-a", "critic-b"])
        self.assertEqual(quorum["critic_challenge_retry_models"], ["critic-a", "critic-b"])

    def test_fusion_quorum_targeted_critic_retry_can_recover(self) -> None:
        def fake_chat(api_key, model, messages, **kwargs):  # noqa: ANN001, ARG001
            system = str(messages[0]["content"])
            if "Lead pass" in system:
                return "## Decision\nProceed\n\nEvidence docs/present.md:1", {"retry_count": 0}
            if "Independent defensive evidence review" in system:
                return (
                    "Challenge: the framing assumes complete evidence and the WSP_15 "
                    "priority order should defer execution pending verification.",
                    {"retry_count": 0},
                )
            if "Panel critic pass" in system:
                return "No material challenge: framing and priority appear sound.", {"retry_count": 0}
            return "## Decision\nProceed\n\n## WSP_15 Priority\nP1", {"retry_count": 0}

        with mock.patch.object(bridge, "_chat_completion", side_effect=fake_chat):
            result = bridge._run_foundups_fusion(
                "key",
                "prompt\n\n### Required direct-read target: docs/present.md\ncontent",
                [],
                {
                    "lead_model": "lead-model",
                    "panel_models": ["critic-a"],
                    "required_target_paths": ["docs/present.md"],
                    "_redacted_evidence_context": "### Required direct-read target: docs/present.md\ncontent",
                },
            )
        self.assertTrue(result["ok"])
        quorum = result["review_packet"]["fusion_panel_quorum"]
        self.assertEqual(quorum["challenging_critics"], ["critic-a"])
        self.assertEqual(quorum["critic_challenge_retry_models"], ["critic-a"])

    def test_fusion_quorum_preserves_retry_challenge_after_long_initial_response(self) -> None:
        synthesis_prompts: list[str] = []
        accepted_challenge = (
            "Challenge: the evidence framing lacks an exact receipt, so the WSP_15 "
            "priority order must verify it before implementation."
        )

        def fake_chat(api_key, model, messages, **kwargs):  # noqa: ANN001, ARG001
            system = str(messages[0]["content"])
            if "Lead pass" in system:
                return "## Decision\nProceed\n\nEvidence docs/present.md:1", {"retry_count": 0}
            if "Independent defensive evidence review" in system:
                return accepted_challenge, {"retry_count": 0}
            if "Panel critic pass" in system:
                return "No material challenge: " + ("x" * 9000), {"retry_count": 0}
            synthesis_prompts.append(str(messages[1]["content"]))
            return "## Decision\nProceed\n\n## WSP_15 Priority\nP1", {"retry_count": 0}

        with mock.patch.object(bridge, "_chat_completion", side_effect=fake_chat):
            result = bridge._run_foundups_fusion(
                "key",
                "prompt\n\n### Required direct-read target: docs/present.md\ncontent",
                [],
                {
                    "lead_model": "lead-model",
                    "panel_models": ["critic-a"],
                    "required_target_paths": ["docs/present.md"],
                    "_redacted_evidence_context": "### Required direct-read target: docs/present.md\ncontent",
                },
            )

        self.assertTrue(result["ok"])
        self.assertEqual(len(synthesis_prompts), 1)
        self.assertIn(accepted_challenge, synthesis_prompts[0])

    def test_challenge_outside_synthesis_bound_never_satisfies_quorum(self) -> None:
        hidden_challenge = (
            "Challenge: "
            + ("x" * bridge.SYNTHESIS_CRITIC_CHAR_LIMIT)
            + " evidence WSP_15 priority"
        )
        self.assertFalse(bridge._critic_challenges_framing_and_priority(hidden_challenge))

    def test_fusion_quorum_retry_prefers_critic_with_usable_initial_response(self) -> None:
        retry_models: list[str] = []

        def fake_chat(api_key, model, messages, **kwargs):  # noqa: ANN001, ARG001
            system = str(messages[0]["content"])
            if "Lead pass" in system:
                return "## Decision\nProceed\n\nEvidence docs/present.md:1", {"retry_count": 0}
            if "Independent defensive evidence review" in system:
                retry_models.append(model)
                return (
                    "Challenge: the evidence is incomplete and WSP_15 should defer "
                    "implementation until the missing runtime proof is verified.",
                    {"retry_count": 0},
                )
            if "Panel critic pass" in system and model == "critic-a":
                raise HTTPError("https://example.invalid", 503, "blocked", {}, None)
            if "Panel critic pass" in system:
                return "The proposal is generally reasonable.", {"retry_count": 0}
            return "## Decision\nProceed\n\n## WSP_15 Priority\nP1", {"retry_count": 0}

        with mock.patch.object(bridge, "_chat_completion", side_effect=fake_chat):
            result = bridge._run_foundups_fusion(
                "key",
                "prompt\n\n### Required direct-read target: docs/present.md\ncontent",
                [],
                {
                    "lead_model": "lead-model",
                    "panel_models": ["critic-a", "critic-b"],
                    "required_target_paths": ["docs/present.md"],
                    "_redacted_evidence_context": "### Required direct-read target: docs/present.md\ncontent",
                },
            )

        self.assertTrue(result["ok"])
        self.assertEqual(retry_models, ["critic-b"])
        quorum = result["review_packet"]["fusion_panel_quorum"]
        self.assertEqual(quorum["challenging_critics"], ["critic-b"])
        self.assertEqual(quorum["critic_challenge_retry_models"], ["critic-b"])

    def test_fusion_quorum_retry_fails_over_after_provider_abstention(self) -> None:
        retry_models: list[str] = []

        def fake_chat(api_key, model, messages, **kwargs):  # noqa: ANN001, ARG001
            system = str(messages[0]["content"])
            if "Lead pass" in system:
                return "## Decision\nProceed\n\nEvidence docs/present.md:1", {"retry_count": 0}
            if "Independent defensive evidence review" in system:
                retry_models.append(model)
                if model == "critic-a":
                    return "None", {"retry_count": 0}
                return (
                    "Challenge: the evidence framing lacks a runtime receipt, so the "
                    "WSP_15 priority order must verify that receipt before implementation.",
                    {"retry_count": 0},
                )
            if "Panel critic pass" in system:
                return "No material challenge: framing and priority appear sound.", {"retry_count": 0}
            return "## Decision\nProceed\n\n## WSP_15 Priority\nP1", {"retry_count": 0}

        with mock.patch.object(bridge, "_chat_completion", side_effect=fake_chat):
            result = bridge._run_foundups_fusion(
                "key",
                "prompt\n\n### Required direct-read target: docs/present.md\ncontent",
                [],
                {
                    "lead_model": "lead-model",
                    "panel_models": ["critic-a", "critic-b", "critic-c"],
                    "required_target_paths": ["docs/present.md"],
                    "_redacted_evidence_context": "### Required direct-read target: docs/present.md\ncontent",
                },
            )

        self.assertTrue(result["ok"])
        self.assertEqual(retry_models, ["critic-a", "critic-b"])
        quorum = result["review_packet"]["fusion_panel_quorum"]
        self.assertEqual(quorum["challenging_critics"], ["critic-b"])
        self.assertEqual(quorum["critic_challenge_retry_models"], ["critic-a", "critic-b"])
        self.assertEqual(quorum["abstaining_critics"], ["critic-a"])

    def test_no_material_challenge_prefix_never_satisfies_quorum(self) -> None:
        self.assertFalse(
            bridge._critic_challenges_framing_and_priority(
                "No material challenge: the framing, evidence, and WSP_15 priority are sound."
            )
        )
        self.assertFalse(
            bridge._critic_challenges_framing_and_priority(
                "The framing and WSP_15 priority are sound; I challenge nothing material."
            )
        )

    def test_fusion_quorum_passes_with_challenge_and_blocks_synthesis_failure(self) -> None:
        def fake_chat(api_key, model, messages, **kwargs):  # noqa: ANN001, ARG001
            system = str(messages[0]["content"])
            if "Lead pass" in system:
                return "## Decision\nProceed\n\nEvidence docs/present.md:1", {"retry_count": 0}
            if "Panel critic pass" in system:
                return (
                    "Challenge: the framing and the WSP_15 priority order are unsafe because the "
                    "scope may overclaim evidence.",
                    {"retry_count": 0},
                )
            raise TimeoutError("synthesis unavailable")

        with mock.patch.object(bridge, "_chat_completion", side_effect=fake_chat):
            result = bridge._run_foundups_fusion(
                "key",
                "prompt\n\n### Required direct-read target: docs/present.md\ncontent",
                [],
                {
                    "lead_model": "lead-model",
                    "panel_models": ["critic-a"],
                    "required_target_paths": ["docs/present.md"],
                    "_redacted_evidence_context": "### Required direct-read target: docs/present.md\ncontent",
                },
            )
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "fusion_quorum_synthesis_unavailable")
        quorum = result["review_packet"]["fusion_panel_quorum"]
        self.assertEqual(quorum["challenging_critics"], ["critic-a"])

    def test_fusion_quorum_accepts_evidence_priority_challenge_wording(self) -> None:
        def fake_chat(api_key, model, messages, **kwargs):  # noqa: ANN001, ARG001
            system = str(messages[0]["content"])
            if "Lead pass" in system:
                return "## Decision\nProceed\n\nEvidence docs/present.md:1", {"retry_count": 0}
            if "Panel critic pass" in system:
                return (
                    "Challenge: the evidence claim is unsupported and the WSP_15 "
                    "priority should be P0 because the runtime gate is missing.",
                    {"retry_count": 0},
                )
            return "## Decision\nProceed\n\n## WSP_15 Priority\nP0\n\n## Next safest step\nFix.", {
                "retry_count": 0
            }

        with mock.patch.object(bridge, "_chat_completion", side_effect=fake_chat):
            result = bridge._run_foundups_fusion(
                "key",
                "prompt\n\n### Required direct-read target: docs/present.md\ncontent",
                [],
                {
                    "lead_model": "lead-model",
                    "panel_models": ["critic-a"],
                    "required_target_paths": ["docs/present.md"],
                    "_redacted_evidence_context": "### Required direct-read target: docs/present.md\ncontent",
                },
            )
        self.assertTrue(result["ok"])
        quorum = result["review_packet"]["fusion_panel_quorum"]
        self.assertEqual(quorum["challenging_critics"], ["critic-a"])

    def test_fusion_quorum_success_records_challenging_critic(self) -> None:
        def fake_chat(api_key, model, messages, **kwargs):  # noqa: ANN001, ARG001
            system = str(messages[0]["content"])
            if "Lead pass" in system:
                return "## Decision\nProceed\n\nEvidence docs/present.md:1", {"retry_count": 0}
            if "Panel critic pass" in system:
                return (
                    "Challenge: the framing and WSP_15 priority are unsafe because the sequence "
                    "could hide a missing gate.",
                    {"retry_count": 0},
                )
            return "## Decision\nProceed\n\n## WSP_15 Priority\nP1\n\n## Next safest step\nVerify.", {
                "retry_count": 0
            }

        with mock.patch.object(bridge, "_chat_completion", side_effect=fake_chat):
            result = bridge._run_foundups_fusion(
                "key",
                "prompt\n\n### Required direct-read target: docs/present.md\ncontent",
                [],
                {
                    "lead_model": "lead-model",
                    "panel_models": ["critic-a"],
                    "required_target_paths": ["docs/present.md"],
                    "_redacted_evidence_context": "### Required direct-read target: docs/present.md\ncontent",
                },
            )
        self.assertTrue(result["ok"])
        quorum = result["review_packet"]["fusion_panel_quorum"]
        self.assertTrue(quorum["passed"])
        self.assertEqual(quorum["challenging_critics"], ["critic-a"])

    def test_fusion_kimi_k3_uses_and_records_4096_token_critic_budget(self) -> None:
        calls: list[tuple[str, int]] = []

        def fake_chat(api_key, model, messages, **kwargs):  # noqa: ANN001, ARG001
            calls.append((model, kwargs["max_tokens"]))
            system = str(messages[0]["content"])
            if "Lead pass" in system:
                return "## Decision\nProceed\n\nEvidence docs/present.md:1", {"retry_count": 0}
            if "Panel critic pass" in system:
                return (
                    "Challenge: the evidence claim is unsupported and the WSP_15 "
                    "priority sequence needs verification.",
                    {"retry_count": 0},
                )
            return "## Decision\nProceed\n\n## WSP_15 Priority\nP1", {"retry_count": 0}

        with mock.patch.object(bridge, "_chat_completion", side_effect=fake_chat):
            result = bridge._run_foundups_fusion(
                "key",
                "prompt\n\n### Required direct-read target: docs/present.md\ncontent",
                [],
                {
                    "lead_model": "lead-model",
                    "panel_models": ["moonshotai/kimi-k3"],
                    "max_tokens": 1600,
                    "required_target_paths": ["docs/present.md"],
                    "_redacted_evidence_context": "### Required direct-read target: docs/present.md\ncontent",
                },
            )

        self.assertTrue(result["ok"])
        self.assertIn(("moonshotai/kimi-k3", 4096), calls)
        self.assertEqual(
            result["review_packet"]["panel_max_tokens"],
            {"moonshotai/kimi-k3": 4096},
        )

    def test_fusion_strict_json_contract_reaches_lead_and_synthesis_prompts(self) -> None:
        systems: list[str] = []

        def fake_chat(api_key, model, messages, **kwargs):  # noqa: ANN001, ARG001
            system = str(messages[0]["content"])
            systems.append(system)
            if "Lead pass" in system:
                return '{"summary":"lead","evidence_refs":["file:docs/present.md:sha256:x:lines:1"],"findings":[]}', {
                    "retry_count": 0
                }
            if "Panel critic pass" in system:
                return (
                    "Challenge: the evidence claim and WSP_15 priority need checking.",
                    {"retry_count": 0},
                )
            return '{"summary":"final","evidence_refs":["file:docs/present.md:sha256:x:lines:1"],"findings":[]}', {
                "retry_count": 0
            }

        with mock.patch.object(bridge, "_chat_completion", side_effect=fake_chat):
            result = bridge._run_foundups_fusion(
                "key",
                "prompt\n\n### Required direct-read target: docs/present.md\ncontent",
                [],
                {
                    "lead_model": "lead-model",
                    "panel_models": ["critic-a"],
                    "response_contract": "strict_json_repo_code_audit.v1",
                    "required_target_paths": ["docs/present.md"],
                    "_redacted_evidence_context": "### Required direct-read target: docs/present.md\ncontent",
                },
            )
        self.assertTrue(result["ok"])
        self.assertTrue(any("Return only a JSON object" in system for system in systems))
        self.assertTrue(any("return only the final strict JSON object" in system for system in systems))

    def test_read_stdin_json_em_dash(self) -> None:
        payload = {"prompt": "safe", "context": "PR #718 \u2014 `WSP_109_FOUNDUP_ONBOARDI"}
        stdin_buffer = io.BytesIO(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
        fake_stdin = mock.Mock()
        fake_stdin.buffer = stdin_buffer
        with mock.patch("sys.stdin", fake_stdin):
            parsed = bridge._read_stdin_json()
        self.assertIn("\u2014", parsed["context"])

    def test_main_em_dash_utf8_stdin_not_redactor_error(self) -> None:
        context = "PR #718 \u2014 `WSP_109_FOUNDUP_ONBOARDI"
        responses = [
            json.dumps({"choices": [{"message": {"content": "ok"}}]}).encode("utf-8"),
        ]

        def fake_urlopen(request, timeout=0):  # noqa: ARG001
            item = responses.pop(0)
            return io.BytesIO(item)

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            _rc, out = self._invoke_main(
                {
                    "mode": "openrouter_single",
                    "prompt": "Operate as RedDog Architect. Review the supplied repo context.",
                    "context": context,
                    "lead_model": "z-ai/glm-5.2",
                }
            )

        self.assertNotEqual(out.get("reason"), "redaction_blocked")
        self.assertNotEqual(out.get("redaction_reason"), "redactor_error")
        self.assertTrue(out.get("ok"))

    def test_audit_context_false_strict_blocks_governance_sample(self) -> None:
        from modules.communication.moltbot_bridge.tests.test_fusion_redaction_gate import (  # noqa: WPS433
            _AUDIT_STRUCTURE_SAMPLE,
        )

        _rc, out = self._invoke_main(
            {
                "mode": "openrouter_single",
                "prompt": "012 work focus",
                "context": _AUDIT_STRUCTURE_SAMPLE,
                "lead_model": "z-ai/glm-5.2",
                "audit_context": False,
            }
        )

        self.assertFalse(out.get("ok"))
        self.assertEqual(out.get("reason"), "redaction_blocked")
        self.assertFalse(out.get("audit_context_requested"))
        self.assertFalse(out.get("audit_context_applied"))

    def test_audit_context_true_preserves_governance_structure(self) -> None:
        from modules.communication.moltbot_bridge.tests.test_fusion_redaction_gate import (  # noqa: WPS433
            _AUDIT_STRUCTURE_SAMPLE,
        )

        responses = [
            json.dumps({"choices": [{"message": {"content": "ok"}}]}).encode("utf-8"),
        ]

        def fake_urlopen(request, timeout=0):  # noqa: ARG001
            return io.BytesIO(responses.pop(0))

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            _rc, out = self._invoke_main(
                {
                    "mode": "openrouter_single",
                    "prompt": "012 work focus",
                    "context": _AUDIT_STRUCTURE_SAMPLE,
                    "lead_model": "z-ai/glm-5.2",
                    "audit_context": True,
                }
            )

        self.assertTrue(out.get("ok"))
        self.assertTrue(out.get("audit_context_requested"))
        self.assertTrue(out.get("audit_context_applied"))
        self.assertIn("SourceAuthority", out.get("redacted_prompt") or "")

    def test_audit_context_true_still_redacts_fake_secret(self) -> None:
        secret = ("s" + "k-") + "FAKE" + ("Z" * 44)
        context = (
            "class SourceAuthority(str, enum.Enum):\n"
            '    MONOREPO_POC = "monorepo_poc"\n'
            f'api_key = "{secret}"\n'
        )
        responses = [
            json.dumps({"choices": [{"message": {"content": "ok"}}]}).encode("utf-8"),
        ]

        def fake_urlopen(request, timeout=0):  # noqa: ARG001
            return io.BytesIO(responses.pop(0))

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            _rc, out = self._invoke_main(
                {
                    "mode": "openrouter_single",
                    "prompt": "012 work focus",
                    "context": context,
                    "lead_model": "z-ai/glm-5.2",
                    "audit_context": True,
                }
            )

        self.assertTrue(out.get("ok"))
        redacted = out.get("redacted_prompt") or ""
        self.assertIn("SourceAuthority", redacted)
        self.assertNotIn(secret, redacted)
        self.assertIn("[REDACTED", redacted)

    # ------------------------------------------------------------------
    # REDDOG_REQUIRED_TARGET_MARKER_FORGERY_HARDENING_PHASE1 -- VECTOR B closure
    # (legacy None path under audit_mode). When audit_context is requested but the JS
    # packer emits NO authoritative packed paths (audit_context true because direct-read
    # code_hits are present, but direct_read_fallback_used is false so packProtected is
    # false -> authoritativePacked=[]), the bridge MUST forward an EXPLICIT EMPTY tuple
    # sentinel -- NOT None -- so the gate builds an EMPTY authoritative_set (every marker
    # folds back as ordinary content, checked==0) instead of the legacy no-filter path
    # (authoritative_set=None -> every marker is a required-target section).
    # ------------------------------------------------------------------

    def test_vectorb_audit_mode_empty_required_targets_forwards_empty_tuple_not_none(self) -> None:
        # audit_context=true + required_target_paths ABSENT -> gate receives () (empty set sentinel).
        gate_mock = mock.Mock(return_value=_passed_gate(context="ctx"))
        responses = [json.dumps({"choices": [{"message": {"content": "ok"}}]}).encode("utf-8")]

        def fake_urlopen(request, timeout=0):  # noqa: ARG001
            return io.BytesIO(responses.pop(0))

        with mock.patch.object(bridge, "evaluate_redaction_gate", gate_mock), mock.patch(
            "urllib.request.urlopen", side_effect=fake_urlopen
        ):
            self._invoke_main(
                {
                    "mode": "openrouter_single",
                    "prompt": "012 audit focus",
                    "context": "audit body",
                    "lead_model": "z-ai/glm-5.2",
                    "audit_context": True,
                }
            )

        gate_mock.assert_called_once()
        kwargs = gate_mock.call_args.kwargs
        self.assertTrue(kwargs["audit_mode"])
        self.assertEqual(
            kwargs["required_target_paths"],
            (),
            "audit_mode with no packed paths MUST forward an explicit empty tuple, not None",
        )
        self.assertIsNotNone(kwargs["required_target_paths"])

    def test_vectorb_audit_mode_empty_list_forwards_empty_tuple_not_none(self) -> None:
        # audit_context=true + required_target_paths=[] (empty list, the JS authoritativePacked=[]
        # value) -> gate receives () (never None).
        gate_mock = mock.Mock(return_value=_passed_gate(context="ctx"))
        responses = [json.dumps({"choices": [{"message": {"content": "ok"}}]}).encode("utf-8")]

        def fake_urlopen(request, timeout=0):  # noqa: ARG001
            return io.BytesIO(responses.pop(0))

        with mock.patch.object(bridge, "evaluate_redaction_gate", gate_mock), mock.patch(
            "urllib.request.urlopen", side_effect=fake_urlopen
        ):
            self._invoke_main(
                {
                    "mode": "openrouter_single",
                    "prompt": "012 audit focus",
                    "context": "audit body",
                    "lead_model": "z-ai/glm-5.2",
                    "audit_context": True,
                    "required_target_paths": [],
                }
            )

        kwargs = gate_mock.call_args.kwargs
        self.assertEqual(kwargs["required_target_paths"], ())

    def test_vectorb_non_audit_empty_required_targets_stays_none_byte_identical(self) -> None:
        # NON-AUDIT legacy path preserved byte-identical: no packed paths -> None (unchanged).
        gate_mock = mock.Mock(return_value=_passed_gate(context="ctx"))
        responses = [json.dumps({"choices": [{"message": {"content": "ok"}}]}).encode("utf-8")]

        def fake_urlopen(request, timeout=0):  # noqa: ARG001
            return io.BytesIO(responses.pop(0))

        with mock.patch.object(bridge, "evaluate_redaction_gate", gate_mock), mock.patch(
            "urllib.request.urlopen", side_effect=fake_urlopen
        ):
            self._invoke_main(
                {
                    "mode": "openrouter_single",
                    "prompt": "012 work focus",
                    "context": "ordinary body",
                    "lead_model": "z-ai/glm-5.2",
                }
            )

        kwargs = gate_mock.call_args.kwargs
        self.assertFalse(kwargs["audit_mode"])
        self.assertIsNone(
            kwargs["required_target_paths"],
            "non-audit path must keep legacy None (byte-identical to pre-hardening)",
        )

    def test_vectorb_audit_mode_real_paths_still_forwarded(self) -> None:
        # A real authoritative list is still forwarded verbatim (unchanged behavior).
        gate_mock = mock.Mock(return_value=_passed_gate(context="ctx"))
        responses = [json.dumps({"choices": [{"message": {"content": "ok"}}]}).encode("utf-8")]

        def fake_urlopen(request, timeout=0):  # noqa: ARG001
            return io.BytesIO(responses.pop(0))

        with mock.patch.object(bridge, "evaluate_redaction_gate", gate_mock), mock.patch(
            "urllib.request.urlopen", side_effect=fake_urlopen
        ):
            self._invoke_main(
                {
                    "mode": "openrouter_single",
                    "prompt": "012 audit focus",
                    "context": "audit body",
                    "lead_model": "z-ai/glm-5.2",
                    "audit_context": True,
                    "required_target_paths": ["real/a.py", "real/b.py"],
                }
            )

        kwargs = gate_mock.call_args.kwargs
        self.assertEqual(kwargs["required_target_paths"], ("real/a.py", "real/b.py"))


class KimiK3RuntimeBudgetTests(unittest.TestCase):
    """Focused coverage for K3 provider budgets and truthful role receipts."""

    def _invoke_main(self, payload: dict) -> tuple[int, dict]:
        stdin_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        fake_stdin = mock.Mock()
        fake_stdin.buffer = io.BytesIO(stdin_bytes)
        stdout = io.StringIO()
        with mock.patch("sys.stdin", fake_stdin), mock.patch("sys.stdout", stdout), mock.patch.dict(
            os.environ, {bridge.ENV_API_KEY: "test-key"}, clear=False
        ):
            rc = bridge.main()
        return rc, json.loads(stdout.getvalue())

    def test_kimi_k3_completion_applies_4096_floor(self) -> None:
        post = mock.Mock(
            return_value=(
                {"choices": [{"message": {"content": "ok"}}]},
                {"retry_count": 0, "final_retry_reason": None},
            )
        )
        with mock.patch.object(bridge, "_post_openrouter", post):
            bridge._chat_completion(
                "key",
                "moonshotai/kimi-k3",
                [{"role": "user", "content": "test"}],
                max_tokens=256,
                temperature=0.2,
                timeout=30,
            )

        body = post.call_args.args[1]
        self.assertEqual(body["max_tokens"], 4096)
        self.assertEqual(body["reasoning"], {"effort": "max"})
        self.assertNotIn("temperature", body)

    def test_fusion_kimi_k3_principal_uses_and_records_4096_for_both_passes(self) -> None:
        calls: list[tuple[str, int]] = []

        def fake_chat(api_key, model, messages, **kwargs):  # noqa: ANN001, ARG001
            calls.append((model, kwargs["max_tokens"]))
            system = str(messages[0]["content"])
            if "Panel critic pass" in system:
                return (
                    "Challenge: the evidence framing is unsupported and the WSP_15 "
                    "priority needs verification.",
                    {"retry_count": 0},
                )
            return "Evidence-backed result with WSP_15 priority.", {"retry_count": 0}

        with mock.patch.object(bridge, "_chat_completion", side_effect=fake_chat):
            result = bridge._run_foundups_fusion(
                "key",
                "prompt",
                [],
                {
                    "lead_model": "moonshotai/kimi-k3",
                    "panel_models": ["critic-a"],
                    "max_tokens": 1200,
                },
            )

        self.assertTrue(result["ok"])
        self.assertEqual(calls.count(("moonshotai/kimi-k3", 4096)), 2)
        self.assertIn(("critic-a", 1200), calls)
        packet = result["review_packet"]
        self.assertEqual(packet["requested_max_tokens"], 1200)
        self.assertEqual(
            packet["role_max_tokens"],
            {"lead": 4096, "panel": {"critic-a": 1200}, "synthesis": 4096},
        )

    def test_single_kimi_k3_receipt_records_requested_and_effective_budget(self) -> None:
        chat = mock.Mock(return_value=("ok", {"retry_count": 0, "final_retry_reason": None}))
        with mock.patch.object(bridge, "evaluate_redaction_gate", return_value=_passed_gate()), mock.patch.object(
            bridge, "_chat_completion", chat
        ):
            rc, result = self._invoke_main(
                {
                    "mode": "openrouter_single",
                    "prompt": "test",
                    "lead_model": "moonshotai/kimi-k3",
                    "max_tokens": 256,
                }
            )

        self.assertEqual(rc, 0)
        self.assertTrue(result["ok"])
        self.assertEqual(chat.call_args.kwargs["max_tokens"], 256)
        packet = result["review_packet"]
        self.assertEqual(packet["requested_max_tokens"], 256)
        self.assertEqual(packet["effective_max_tokens"], 4096)

    def test_single_non_kimi_receipt_preserves_requested_budget(self) -> None:
        chat = mock.Mock(return_value=("ok", {"retry_count": 0, "final_retry_reason": None}))
        with mock.patch.object(bridge, "evaluate_redaction_gate", return_value=_passed_gate()), mock.patch.object(
            bridge, "_chat_completion", chat
        ):
            rc, result = self._invoke_main(
                {
                    "mode": "openrouter_single",
                    "prompt": "test",
                    "lead_model": "z-ai/glm-5.2",
                    "max_tokens": 777,
                }
            )

        self.assertEqual(rc, 0)
        self.assertTrue(result["ok"])
        self.assertEqual(chat.call_args.kwargs["max_tokens"], 777)
        packet = result["review_packet"]
        self.assertEqual(packet["requested_max_tokens"], 777)
        self.assertEqual(packet["effective_max_tokens"], 777)


if __name__ == "__main__":
    unittest.main()
