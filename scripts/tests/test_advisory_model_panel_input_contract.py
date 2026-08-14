"""Focused end-to-end contracts for RedDog Fusion panel input truth."""

from __future__ import annotations

import inspect
import io
import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import scripts.advisory_model_once as bridge  # noqa: E402
from modules.communication.moltbot_bridge.src.fusion_redaction_gate import (  # noqa: E402
    REDACTION_GATE_PASSED,
    RedactionReport,
)


def _passed_gate():
    return mock.Mock(
        status=REDACTION_GATE_PASSED,
        redacted_prompt="redacted-prompt",
        redacted_context=None,
        reason="ok",
        report=RedactionReport(),
    )


def _invoke_main(payload: dict) -> tuple[int, dict]:
    fake_stdin = mock.Mock()
    fake_stdin.buffer = io.BytesIO(json.dumps(payload).encode("utf-8"))
    stdout = io.StringIO()
    with mock.patch("sys.stdin", fake_stdin), mock.patch("sys.stdout", stdout), mock.patch.dict(
        os.environ, {bridge.ENV_API_KEY: "test-key"}, clear=False
    ):
        rc = bridge.main()
    return rc, json.loads(stdout.getvalue())


class FusionPanelInputHardeningTests(unittest.TestCase):
    _MISSING = object()

    def test_system_prompt_always_retains_one_terminal_evidence_rule(self) -> None:
        rule = bridge.UNTRUSTED_EVIDENCE_SYSTEM_RULE
        prompts = (
            "a" * 6001 + rule,
            "b" * (6000 - len(rule) // 2) + rule,
            rule + "\n" + ("c" * 6001) + rule,
        )
        for prompt in prompts:
            with self.subTest(length=len(prompt)):
                assembled = bridge._system_prompt({"system": prompt})
                self.assertLessEqual(len(assembled), 6000)
                self.assertTrue(assembled.endswith(rule))
                self.assertEqual(assembled.count(rule), 1)

    @staticmethod
    def _fusion_chat(api_key, model, messages, **kwargs):  # noqa: ANN001, ARG004
        system = str(messages[0]["content"])
        if "Lead pass" in system:
            return "## Decision\nProceed\n\nEvidence: observed.", {"retry_count": 0}
        if "Panel critic pass" in system:
            return (
                "Challenge: the evidence framing is unsupported and the WSP_15 priority must be P0.",
                {"retry_count": 0},
            )
        return "## Decision\nProceed\n\n## WSP_15 Priority\nP0", {"retry_count": 0}

    @classmethod
    def _panel_cases(cls) -> tuple[tuple[str, object, list[str], bool], ...]:
        above_legacy_cap = ["m" + str(index) for index in range(5)]
        overflow_sentinel = ["m" + str(index) for index in range(bridge.MAX_PANEL_MODELS + 1)]
        return (
            ("omitted", cls._MISSING, list(bridge.DEFAULT_PANEL_MODELS), False),
            ("non_list", "not-a-list", list(bridge.DEFAULT_PANEL_MODELS), False),
            ("empty", [], [], False),
            ("invalid_only", ["", None, 7], [], False),
            ("above_legacy_four", above_legacy_cap, above_legacy_cap, False),
            (
                "extension_overflow_sentinel",
                overflow_sentinel,
                overflow_sentinel[: bridge.MAX_PANEL_MODELS],
                True,
            ),
        )

    @staticmethod
    def _spoofed_bridge_meta() -> dict:
        return {
            "mode": "spoofed",
            "reason": "redaction_blocked",
            "made_network_call": True,
            "lead_model": "spoofed",
            "panel_models": ["spoofed"],
            "panel_models_truncated": False,
            "fusion_panel_quorum": {"passed": True},
            "retry_count": 999,
            "python_interpreter_source": "contract-test",
        }

    def _assert_core_packet(
        self,
        packet: dict,
        *,
        mode: str,
        panel_models: list[str],
        truncated: bool,
    ) -> None:
        self.assertEqual(packet["mode"], mode)
        self.assertEqual(packet["lead_model"], "lead-model")
        self.assertEqual(packet["panel_models"], panel_models)
        self.assertEqual(packet["panel_models_truncated"], truncated)
        self.assertEqual(packet["python_interpreter_source"], "contract-test")
        self.assertNotEqual(packet.get("retry_count"), 999)
        self.assertNotIn("reason", packet)
        self.assertNotIn("made_network_call", packet)

    def test_missing_or_non_list_panel_input_keeps_compatibility_defaults(self) -> None:
        for value in (None, "not-a-list", {"invalid": "container"}):
            with self.subTest(value=value):
                models, truncated = bridge._panel_models_with_meta(value)
                self.assertEqual(models, list(bridge.DEFAULT_PANEL_MODELS))
                self.assertFalse(truncated)

    def test_explicit_empty_or_invalid_panel_never_restores_defaults(self) -> None:
        empty_models, empty_truncated = bridge._panel_models_with_meta([])
        invalid_models, invalid_truncated = bridge._panel_models_with_meta(["", None, " " * 4])
        self.assertEqual((empty_models, empty_truncated), ([], False))
        self.assertEqual((invalid_models, invalid_truncated), ([], False))

    def test_manual_fusion_rejects_explicit_empty_panel_before_network(self) -> None:
        chat_mock = mock.Mock()
        with mock.patch.object(bridge, "_chat_completion", chat_mock):
            result = bridge._run_foundups_fusion(
                "key",
                "prompt",
                [],
                {"lead_model": "lead-model", "panel_models": []},
            )
        chat_mock.assert_not_called()
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "fusion_quorum_panel_missing")
        self.assertEqual(result["review_packet"]["panel_models"], [])

    def test_fusion_alias_rejects_explicit_empty_panel_before_network(self) -> None:
        post_mock = mock.Mock()
        with mock.patch.object(bridge, "_post_openrouter", post_mock):
            result = bridge._openrouter_fusion_alias(
                "key",
                "prompt",
                [],
                {"lead_model": "judge-model", "panel_models": []},
            )
        post_mock.assert_not_called()
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "fusion_alias_panel_missing")
        self.assertEqual(result["review_packet"]["panel_models"], [])

    def test_main_manual_fusion_panel_matrix_is_no_network_and_unspoofable(self) -> None:
        chat_mock = mock.Mock(side_effect=self._fusion_chat)
        with mock.patch.object(bridge, "evaluate_redaction_gate", return_value=_passed_gate()), mock.patch.object(
            bridge, "_chat_completion", chat_mock
        ), mock.patch.object(bridge, "_post_openrouter") as post_mock:
            for name, raw_panel, expected, truncated in self._panel_cases():
                with self.subTest(name=name):
                    payload = self._payload("foundups_fusion", raw_panel)
                    before = chat_mock.call_count
                    _rc, out = _invoke_main(payload)
                    expected_calls = len(expected) + 2 if expected else 0
                    self.assertEqual(chat_mock.call_count - before, expected_calls)
                    self._assert_core_packet(
                        out["review_packet"],
                        mode="foundups_fusion",
                        panel_models=expected,
                        truncated=truncated,
                    )
                    self.assertTrue(out["redacted_task_prompt_digest"].startswith("sha256:"))
                    if expected:
                        self.assertEqual(out["redacted_task_prompt"], "redacted-prompt")
                    else:
                        self.assertNotIn("redacted_task_prompt", out)
                    self.assertEqual(out["review_packet"]["fusion_panel_quorum"]["passed"], bool(expected))
        post_mock.assert_not_called()

    def test_main_fusion_alias_panel_matrix_is_no_network_and_unspoofable(self) -> None:
        post_mock = mock.Mock(
            return_value=(
                {"choices": [{"message": {"content": "alias synthesis"}}]},
                {"retry_count": 0, "final_retry_reason": None},
            )
        )
        with mock.patch.object(bridge, "evaluate_redaction_gate", return_value=_passed_gate()), mock.patch.object(
            bridge, "_post_openrouter", post_mock
        ), mock.patch.object(bridge, "_chat_completion") as chat_mock:
            for name, raw_panel, expected, truncated in self._panel_cases():
                with self.subTest(name=name):
                    before = post_mock.call_count
                    _rc, out = _invoke_main(self._payload("openrouter_fusion_alias", raw_panel))
                    self.assertEqual(post_mock.call_count - before, 1 if expected else 0)
                    self._assert_core_packet(
                        out["review_packet"],
                        mode="openrouter_fusion_alias",
                        panel_models=expected,
                        truncated=truncated,
                    )
                    self.assertTrue(out["redacted_task_prompt_digest"].startswith("sha256:"))
                    if expected:
                        self.assertEqual(out["redacted_task_prompt"], "redacted-prompt")
                    else:
                        self.assertNotIn("redacted_task_prompt", out)
                    self.assertNotIn("fusion_panel_quorum", out["review_packet"])
                    if expected:
                        self.assertEqual(post_mock.call_args.args[1]["plugins"][0]["analysis_models"], expected)
                        system = post_mock.call_args.args[1]["messages"][0]
                        self.assertEqual(system["role"], "system")
                        self.assertIn("untrusted evidence", system["content"])
                        self.assertEqual(
                            out["review_packet"]["evidence_boundary_scope"],
                            "outer_request_system_and_user_evidence_only",
                        )
                        self.assertFalse(
                            out["review_packet"]["internal_panel_role_prompts_observable"]
                        )
        chat_mock.assert_not_called()

    def test_extension_overflow_sentinel_yields_truthful_final_receipts(self) -> None:
        extension_source = (REPO_ROOT / "extensions" / "reddog" / "extension.js").read_text("utf-8")
        self.assertIn(
            "const FUSION_PANEL_RUNTIME_LIMIT = " + str(bridge.MAX_PANEL_MODELS) + ";",
            extension_source,
        )
        self.assertIn("FUSION_PANEL_FORWARD_LIMIT = FUSION_PANEL_RUNTIME_LIMIT + 1", extension_source)
        sentinel = ["m" + str(index) for index in range(bridge.MAX_PANEL_MODELS + 1)]
        for mode in ("foundups_fusion", "openrouter_fusion_alias"):
            with self.subTest(mode=mode), mock.patch.object(
                bridge, "evaluate_redaction_gate", return_value=_passed_gate()
            ), mock.patch.object(bridge, "_chat_completion", side_effect=self._fusion_chat), mock.patch.object(
                bridge,
                "_post_openrouter",
                return_value=(
                    {"choices": [{"message": {"content": "alias synthesis"}}]},
                    {"retry_count": 0, "final_retry_reason": None},
                ),
            ):
                _rc, out = _invoke_main(self._payload(mode, sentinel))
                packet = out["review_packet"]
                self.assertEqual(packet["panel_models"], sentinel[: bridge.MAX_PANEL_MODELS])
                self.assertTrue(packet["panel_models_truncated"])

    def test_exact_redacted_task_prompt_excludes_context_in_manual_fusion(self) -> None:
        gate = _passed_gate()
        gate.redacted_prompt = "task-only-sentinel"
        gate.redacted_context = "context-only-sentinel"
        with mock.patch.object(bridge, "evaluate_redaction_gate", return_value=gate), mock.patch.object(
            bridge, "_chat_completion", side_effect=self._fusion_chat
        ):
            _rc, out = _invoke_main(self._payload("foundups_fusion", ["critic-model"]))
        self.assertEqual(out["redacted_task_prompt"], "task-only-sentinel")
        self.assertTrue(out["redacted_task_prompt_digest"].startswith("sha256:"))
        self.assertNotIn("context-only-sentinel", out["redacted_task_prompt"])
        self.assertIn("context-only-sentinel", out["review_packet"]["redacted_prompt"])

    def test_fusion_alias_function_stays_within_fifty_lines(self) -> None:
        source_lines, _line = inspect.getsourcelines(bridge._openrouter_fusion_alias)
        self.assertLessEqual(len(source_lines), 50)

    def _payload(self, mode: str, raw_panel: object) -> dict:
        payload = {
            "mode": mode,
            "prompt": "panel contract",
            "lead_model": "lead-model",
            "bridge_meta": self._spoofed_bridge_meta(),
        }
        if raw_panel is not self._MISSING:
            payload["panel_models"] = raw_panel
        return payload


if __name__ == "__main__":
    unittest.main()
