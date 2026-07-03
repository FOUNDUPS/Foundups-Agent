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


class AdvisoryBridgeHardeningTests(unittest.TestCase):
    def _invoke_main(self, payload: dict, *, api_key: str = "test-key") -> tuple[int, dict]:
        stdin_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        stdin_buffer = io.BytesIO(stdin_bytes)
        stdout = io.StringIO()
        env = {bridge.ENV_API_KEY: api_key}
        fake_stdin = mock.Mock()
        fake_stdin.buffer = stdin_buffer
        with mock.patch("sys.stdin", fake_stdin), mock.patch("sys.stdout", stdout), mock.patch.dict(
            os.environ, env, clear=False
        ):
            rc = bridge.main()
        return rc, json.loads(stdout.getvalue())

    def test_panel_models_capped_at_six(self) -> None:
        models = bridge._panel_models(["m" + str(i) for i in range(12)])
        self.assertLessEqual(len(models), bridge.MAX_PANEL_MODELS)
        self.assertEqual(len(models), 6)

    def test_panel_models_truncated_metadata(self) -> None:
        models, truncated = bridge._panel_models_with_meta(["m" + str(i) for i in range(12)])
        self.assertTrue(truncated)
        self.assertEqual(len(models), bridge.MAX_PANEL_MODELS)

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


if __name__ == "__main__":
    unittest.main()
