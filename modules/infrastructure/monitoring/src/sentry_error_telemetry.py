"""Opt-in manual Sentry error codes; never export exceptions or ambient content."""
from __future__ import annotations

import importlib
import os
import re
from urllib.parse import urlsplit

_COMPONENTS = frozenset({"langfuse_review", "telemetry_probe"})
_REASONS = frozenset({"synthetic_probe", "env_file_unavailable", "credentials_incomplete",
    "invalid_utc_time", "invalid_time_window", "invalid_lookup_bounds", "invalid_trace_id",
    "missing_or_invalid_credentials", "response_too_large", "lookup_failed",
    "invalid_response_schema", "invalid_pagination_cursor"})
_HEX_ID = re.compile(r"^[0-9a-f]{32}$")
_MARKER = "bounded.v1"


def _dsn_valid(value):
    if not isinstance(value, str) or len(value) > 512 or any(ord(character) < 33 or ord(character) > 126 for character in value):
        return False
    try:
        parsed = urlsplit(value)
        return (parsed.scheme == "https" and parsed.password is None and parsed.port is None
                and bool(re.fullmatch(r"[0-9a-f]{32}", parsed.username or ""))
                and bool(re.fullmatch(r"o[0-9]+\.ingest(?:\.(?:us|de))?\.sentry\.io", parsed.hostname or ""))
                and bool(re.fullmatch(r"/[0-9]+", parsed.path))
                and not parsed.query and not parsed.fragment)
    except (TypeError, ValueError):
        return False


def bounded_event(event, hint=None):
    """Rebuild approved manual events after SDK processing; discard all raw fields."""
    if not isinstance(event, dict) or not isinstance(event.get("tags"), dict):
        return None
    tags = event["tags"]
    component, reason = tags.get("foundups.component"), tags.get("foundups.reason")
    if (tags.get("foundups.telemetry") != _MARKER or not isinstance(component, str)
            or component not in _COMPONENTS or not isinstance(reason, str) or reason not in _REASONS):
        return None
    event_id = event.get("event_id")
    if not isinstance(event_id, str) or not _HEX_ID.fullmatch(event_id):
        return None
    return {"event_id": event_id, "level": "error", "platform": "python",
            "message": "FOUNDUPS bounded application error", "logger": "foundups.bounded_errors",
            "server_name": "foundups", "environment": "pilot", "release": "foundups-telemetry-pilot",
            "fingerprint": ["foundups.bounded.v1", component, reason],
            "tags": {"foundups.telemetry": _MARKER, "foundups.component": component, "foundups.reason": reason},
            "exception": {"values": [{"type": "FoundupsBoundedError", "value": reason,
                          "mechanism": {"type": "generic", "handled": True}}]}}


def make_bounded_transport():
    """SDK 2.73 transport with fixed trust and no secondary receivers or body logs."""
    import certifi
    import ssl
    import urllib3
    from sentry_sdk.consts import VERSION
    if VERSION != "2.73.0":
        raise ValueError("unsupported_sentry_sdk")
    from sentry_sdk.transport import HttpTransport

    class BoundedHttpTransport(HttpTransport):
        def _make_pool(self):
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.load_verify_locations(certifi.where())
            return urllib3.PoolManager(num_pools=1, maxsize=1, ssl_context=context,
                cert_reqs="CERT_REQUIRED", timeout=urllib3.Timeout(connect=5, read=5), retries=False)

        def _request(self, method, endpoint_type, body, headers):
            return self._pool.request(method, self._auth.get_api_url(endpoint_type), body=body,
                headers=headers, redirect=False, retries=False, preload_content=False)

        def _send_request(self, body, headers, endpoint_type, envelope=None):
            response = None
            try:
                self._update_headers(headers)
                response = self._request("POST", endpoint_type, body, headers)
                if not 200 <= response.status < 300:
                    self._handle_request_error(envelope=envelope, loss_reason="status_error", record_reason="send_error")
            except Exception:
                self._handle_request_error(envelope=envelope, loss_reason="network", record_reason="network_error")
            finally:
                if response is not None:
                    try:
                        response.close()
                    except Exception:
                        pass

    return BoundedHttpTransport


def report_application_error(*, component, reason, environ=None, sdk_loader=None, transport_factory=None):
    """Submit a content-free event. SUBMITTED never means verified server delivery."""
    env = os.environ if environ is None else environ
    if env.get("FOUNDUPS_SENTRY_ENABLED") != "1":
        return {"status": "DISABLED", "delivery_verified": False}
    if not isinstance(component, str) or component not in _COMPONENTS or not isinstance(reason, str) or reason not in _REASONS:
        return {"status": "INVALID_EVENT", "delivery_verified": False}
    dsn = env.get("SENTRY_DSN")
    if not dsn:
        return {"status": "MISSING_DSN", "delivery_verified": False}
    if not _dsn_valid(dsn):
        return {"status": "INVALID_DSN", "delivery_verified": False}
    client = None
    try:
        sdk = (sdk_loader or (lambda: importlib.import_module("sentry_sdk")))()
        client = sdk.Client(dsn=dsn, transport=(transport_factory or make_bounded_transport)(),
            default_integrations=False, auto_enabling_integrations=False,
            integrations=[], send_default_pii=False, include_local_variables=False,
            include_source_context=False, attach_stacktrace=False, max_breadcrumbs=0,
            before_breadcrumb=lambda breadcrumb, hint: None, before_send=bounded_event,
            traces_sample_rate=0.0, profiles_sample_rate=0.0, enable_logs=False,
            auto_session_tracking=False, send_client_reports=False, spotlight=False, debug=False,
            enable_backpressure_handling=False, trace_propagation_targets=[],
            max_request_body_size="never", server_name="foundups", environment="pilot",
            release="foundups-telemetry-pilot", transport_queue_size=10, shutdown_timeout=2)
        event_id = client.capture_event({"level": "error", "message": "FOUNDUPS bounded application error",
            "tags": {"foundups.telemetry": _MARKER, "foundups.component": component, "foundups.reason": reason}},
            scope=sdk.Scope())
        if not isinstance(event_id, str) or not _HEX_ID.fullmatch(event_id):
            return {"status": "DROPPED", "delivery_verified": False}
        return {"status": "SUBMITTED", "event_id": event_id, "delivery_verified": False}
    except ImportError:
        return {"status": "SDK_UNAVAILABLE", "delivery_verified": False}
    except Exception:
        return {"status": "SDK_FAILED", "delivery_verified": False}
    finally:
        if client is not None:
            try:
                client.close(timeout=2)
            except Exception:
                pass
