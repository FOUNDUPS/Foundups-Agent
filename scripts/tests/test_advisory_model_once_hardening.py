"""Bridge hardening tests for advisory_model_once (Addendum B)."""

from __future__ import annotations

import io
import json
import sys
import unittest
from pathlib import Path
from unittest import mock
from urllib.error import HTTPError

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import scripts.advisory_model_once as bridge  # noqa: E402


class AdvisoryBridgeHardeningTests(unittest.TestCase):
    def test_panel_models_capped_at_six(self) -> None:
        models = bridge._panel_models(["m" + str(i) for i in range(12)])
        self.assertLessEqual(len(models), bridge.MAX_PANEL_MODELS)

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
        self.assertEqual(meta["retry_count"], 1)
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


if __name__ == "__main__":
    unittest.main()
