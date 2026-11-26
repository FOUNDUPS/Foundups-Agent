"""Pinned real-SDK serialization/transport tests with synthetic pools only.

Run with the isolated sentry-pilot Python; no real DSN or network is used.
"""
from __future__ import annotations

import gzip
import importlib.metadata
import importlib.util
import io
import json
import logging
import os
import ssl
from pathlib import Path
import unittest
from unittest.mock import patch

try:
    import sentry_sdk
    import urllib3
except ImportError:
    sentry_sdk = None
    urllib3 = None

ROOT = Path(__file__).resolve().parents[4]
SPEC = importlib.util.spec_from_file_location("real_sentry_qualification_subject",
    ROOT / "modules/infrastructure/monitoring/src/sentry_error_telemetry.py")
subject = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(subject)
SYNTHETIC_DSN = "https://" + "a" * 32 + "@o1.ingest.us.sentry.io/1"
SENTINEL = "PRIVATE_SYNTHETIC_AMBIENT_DATA"


@unittest.skipUnless(sentry_sdk is not None, "isolated sentry-sdk runtime required")
class SentryRealSdkQualification(unittest.TestCase):
    def _capture(self, status=200):
        pools, calls = [], []
        class Response:
            headers = {"Location": "https://PRIVATE_SYNTHETIC_REDIRECT.invalid"}
            @property
            def data(self):
                calls.append(("BODY_READ", "", {}))
                return SENTINEL.encode()
            def close(self):
                pass
        response = Response()
        response.status = status
        class Pool:
            def request(self, method, url, **kwargs):
                calls.append((method, url, dict(kwargs)))
                return response
        def make_pool(**kwargs):
            pools.append(dict(kwargs))
            return Pool()
        ambient = {"SENTRY_SPOTLIGHT": "http://localhost:8969", "SENTRY_DEBUG": "true",
            "SENTRY_RELEASE": SENTINEL, "SENTRY_ENVIRONMENT": SENTINEL,
            "HTTP_PROXY": "http://" + SENTINEL + ":pass@127.0.0.1:9",
            "HTTPS_PROXY": "http://" + SENTINEL + ":pass@127.0.0.1:9",
            "SSL_CERT_FILE": SENTINEL, "REQUESTS_CA_BUNDLE": SENTINEL,
            "CLIENT_CERT_FILE": SENTINEL, "CLIENT_KEY_FILE": SENTINEL}
        ambient.update({"SSLKEYLOGFILE": SENTINEL, "SENTRY_AUTH_TOKEN": SENTINEL,
                        "OPENROUTER_API_KEY": SENTINEL, "LANGFUSE_SECRET_KEY": SENTINEL})
        logs = io.StringIO()
        handler = logging.StreamHandler(logs)
        logger = logging.getLogger("sentry_sdk.errors")
        logger.addHandler(handler)
        try:
            with patch.dict(os.environ, ambient), patch.object(urllib3, "PoolManager", make_pool), \
                 patch.object(urllib3, "ProxyManager", make_pool), \
                 patch("socket.socket.connect", side_effect=AssertionError("outbound_denied")), \
                 patch("socket.socket.connect_ex", side_effect=AssertionError("outbound_denied")):
                with sentry_sdk.new_scope() as scope:
                    scope.set_user({"email": SENTINEL})
                    scope.set_extra("private", SENTINEL)
                    scope.set_context("private", {"content": SENTINEL})
                    scope.set_context("trace", {"dynamic_sampling_context": {"user_segment": SENTINEL}})
                    scope.add_breadcrumb({"message": SENTINEL})
                    result = subject.report_application_error(component="telemetry_probe", reason="synthetic_probe",
                        environ={"FOUNDUPS_SENTRY_ENABLED": "1", "SENTRY_DSN": SYNTHETIC_DSN},
                        sdk_loader=lambda: sentry_sdk)
        finally:
            logger.removeHandler(handler)
        return result, pools, calls, logs.getvalue()

    def test_pinned_version_and_content_free_real_envelope(self):
        self.assertEqual(importlib.metadata.version("sentry-sdk"), "2.73.0")
        result, pools, calls, logs = self._capture()
        self.assertEqual(result["status"], "SUBMITTED")
        self.assertFalse(result["delivery_verified"])
        self.assertEqual(len(calls), 1)  # Spotlight remains explicitly disabled.
        method, url, request = calls[0]
        self.assertEqual(method, "POST")
        self.assertEqual(url, "https://o1.ingest.us.sentry.io/api/1/envelope/")
        self.assertEqual(set(request["headers"]), {"Content-Type", "Content-Encoding", "User-Agent", "X-Sentry-Auth"})
        raw = request["body"]
        if request["headers"].get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
        lines = raw.splitlines()
        envelope, item, event = map(json.loads, lines)
        self.assertEqual(set(envelope), {"event_id", "sent_at"})
        self.assertEqual(item["type"], "event")
        self.assertEqual(event, subject.bounded_event(event))
        self.assertNotIn(SENTINEL.encode(), raw)
        self.assertNotIn(SENTINEL, json.dumps(request["headers"]) + logs)

    def test_no_ambient_proxy_client_certificate_or_trust_paths(self):
        result, pools, calls, logs = self._capture()
        self.assertEqual(result["status"], "SUBMITTED")
        self.assertEqual(len(pools), 1)
        self.assertNotIn(SENTINEL, repr(pools))
        self.assertNotIn("proxy_url", pools[0])
        self.assertFalse(pools[0].get("cert_file"))
        self.assertFalse(pools[0].get("key_file"))
        self.assertTrue(pools[0]["ssl_context"].check_hostname)
        self.assertEqual(pools[0]["ssl_context"].verify_mode, ssl.CERT_REQUIRED)

    def test_real_transport_disables_redirects_and_retries(self):
        result, pools, calls, logs = self._capture(status=302)
        self.assertEqual(result["status"], "SUBMITTED")
        self.assertEqual(len(calls), 1)
        self.assertIs(calls[0][2].get("redirect"), False)
        self.assertIs(calls[0][2].get("retries"), False)
        self.assertNotIn(SENTINEL, logs)

    def test_upstream_error_body_never_reaches_sdk_logs(self):
        result, pools, calls, logs = self._capture(status=413)
        self.assertEqual(result["status"], "SUBMITTED")
        self.assertEqual(len(calls), 1)
        self.assertNotIn(SENTINEL, logs)


if __name__ == "__main__":
    unittest.main()
