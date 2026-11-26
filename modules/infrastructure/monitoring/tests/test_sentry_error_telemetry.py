"""Offline manual-error privacy checks; no Sentry SDK, credentials or egress."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parents[4]
SPEC = importlib.util.spec_from_file_location("bounded_sentry_test", ROOT / "modules/infrastructure/monitoring/src/sentry_error_telemetry.py")
adapter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(adapter)
DSN = "https://" + "a" * 32 + "@o123.ingest.us.sentry.io/456"
EVENT_ID = "b" * 32
CANARY = "never-export-private-source-or-secret"
ENV = {"FOUNDUPS_SENTRY_ENABLED": "1", "SENTRY_DSN": DSN}


def report(**kwargs):
    return adapter.report_application_error(component="telemetry_probe", reason="synthetic_probe",
                                            transport_factory=lambda: object(), **kwargs)


def event(**extra):
    return {"event_id": EVENT_ID, "tags": {"foundups.telemetry": "bounded.v1", "foundups.component": "telemetry_probe", "foundups.reason": "synthetic_probe"}, **extra}


def test_disabled_before_dsn_access_or_sdk_import():
    class Guard(dict):
        def get(self, name, default=None):
            assert name == "FOUNDUPS_SENTRY_ENABLED"
            return "0"
    assert report(environ=Guard(), sdk_loader=lambda: pytest.fail("SDK loaded"))["status"] == "DISABLED"


def test_missing_dsn_does_not_load_sdk():
    assert report(environ={"FOUNDUPS_SENTRY_ENABLED": "1"}, sdk_loader=lambda: pytest.fail("SDK loaded"))["status"] == "MISSING_DSN"


@pytest.mark.parametrize("dsn", ["http://" + "a" * 32 + "@o123.ingest.us.sentry.io/456",
    DSN + "?private=" + CANARY, DSN.replace(".io/", ".io.evil.example/"),
    DSN.replace("@", ":private@"), DSN.replace("/456", "/456/other"), "file:///private", [], DSN + "#frag"])
def test_bad_dsn_static_no_import_or_leak(dsn):
    result = report(environ={**ENV, "SENTRY_DSN": dsn}, sdk_loader=lambda: pytest.fail("SDK loaded"))
    assert result["status"] in {"INVALID_DSN", "MISSING_DSN"}
    assert CANARY not in json.dumps(result)


@pytest.mark.parametrize("region", ["ingest", "ingest.us", "ingest.de"])
def test_official_ingest_regions_accepted(region):
    assert adapter._dsn_valid(DSN.replace("ingest.us", region))


def test_reprojection_discards_every_ambient_payload_field():
    raw = event(message=CANARY, logentry={"message": CANARY}, user={"email": CANARY},
        request={"data": CANARY, "headers": {"Authorization": CANARY}},
        exception={"values": [{"value": CANARY, "stacktrace": {"frames": [{"vars": {"secret": CANARY}, "filename": CANARY}]}}]},
        contexts={"trace": {"data": CANARY}}, breadcrumbs={"values": [{"message": CANARY}]},
        extra={"private": CANARY}, threads={"values": [CANARY]}, modules={CANARY: CANARY},
        server_name=CANARY, environment=CANARY, release=CANARY, attachments=[CANARY])
    clean = adapter.bounded_event(raw, {"exc_info": CANARY})
    assert CANARY not in json.dumps(clean)
    assert clean is not raw and raw["message"] == CANARY
    assert clean["exception"]["values"][0]["value"] == "synthetic_probe"
    assert "stacktrace" not in clean["exception"]["values"][0]


@pytest.mark.parametrize("bad", [None, [], {}, {"tags": []}, event(event_id=CANARY),
    event(tags={"foundups.telemetry": "bounded.v1", "foundups.component": [], "foundups.reason": "synthetic_probe"}),
    event(tags={"foundups.telemetry": "bounded.v1", "foundups.component": "telemetry_probe", "foundups.reason": CANARY})])
def test_unapproved_events_drop(bad):
    assert adapter.bounded_event(bad) is None


def test_dedicated_client_options_scope_and_close_no_global_init():
    calls = {}
    class Client:
        def __init__(self, **options):
            calls["options"] = options
        def capture_event(self, payload, scope):
            calls["scope"] = scope
            assert CANARY not in json.dumps(payload)
            assert adapter.bounded_event({**payload, "event_id": EVENT_ID})
            return EVENT_ID
        def close(self, timeout):
            calls["closed"] = timeout
    scope = object()
    sdk = SimpleNamespace(Client=Client, Scope=lambda: scope)
    result = report(environ=ENV, sdk_loader=lambda: sdk)
    assert result == {"status": "SUBMITTED", "event_id": EVENT_ID, "delivery_verified": False}
    options = calls["options"]
    for key in ("default_integrations", "auto_enabling_integrations", "send_default_pii", "include_local_variables", "include_source_context", "attach_stacktrace", "enable_logs", "auto_session_tracking", "send_client_reports", "spotlight", "enable_backpressure_handling"):
        assert options[key] is False
    assert options["integrations"] == [] and options["trace_propagation_targets"] == []
    assert options["traces_sample_rate"] == options["profiles_sample_rate"] == 0
    assert options["before_breadcrumb"]({"message": CANARY}, None) is None
    assert options["max_breadcrumbs"] == 0 and options["max_request_body_size"] == "never"
    assert calls["scope"] is scope and calls["closed"] == 2


def test_sdk_import_and_exception_failures_are_static():
    for error, expected in [(ImportError(CANARY), "SDK_UNAVAILABLE"), (RuntimeError(CANARY), "SDK_FAILED")]:
        def fail():
            raise error
        result = report(environ=ENV, sdk_loader=fail)
        assert result["status"] == expected and CANARY not in json.dumps(result)


def test_drop_and_close_failure_do_not_become_verified_delivery():
    client = mock.Mock()
    client.capture_event.return_value = None
    client.close.side_effect = RuntimeError(CANARY)
    result = report(environ=ENV, sdk_loader=lambda: SimpleNamespace(Client=lambda **kwargs: client, Scope=object))
    assert result == {"status": "DROPPED", "delivery_verified": False}
    client.close.assert_called_once_with(timeout=2)


def test_langfuse_error_hook_is_optional_and_only_receives_fixed_reason(monkeypatch, capsys):
    source = ROOT / "scripts/reddog_langfuse_review.py"
    spec = importlib.util.spec_from_file_location("langfuse_sentry_hook_test", source)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    with mock.patch.object(cli, "credential_pair", side_effect=cli.CredentialError("credentials_incomplete")), mock.patch.object(cli, "_report_error") as observed:
        assert cli.main(["--from-time", "2026-11-01T00:00:00Z", "--to-time", "2026-11-02T00:00:00Z"]) == 2
    observed.assert_called_once_with("credentials_incomplete")
    assert json.loads(capsys.readouterr().out) == {"ok": False, "reason": "credentials_incomplete"}
    monkeypatch.delenv("FOUNDUPS_SENTRY_ENABLED", raising=False)
    with mock.patch.object(cli.importlib.util, "spec_from_file_location", side_effect=AssertionError("adapter imported")):
        cli._report_error("credentials_incomplete")


@pytest.mark.parametrize("arguments,code", [(["--help"], 0), ([CANARY], 2)])
def test_probe_help_and_invalid_arguments_do_not_initialize_adapter(arguments, code, capsys):
    spec = importlib.util.spec_from_file_location("sentry_probe_help_test", ROOT / "scripts/reddog_sentry_probe.py")
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    with mock.patch.object(probe.importlib.util, "spec_from_file_location", side_effect=AssertionError("adapter imported")):
        with pytest.raises(SystemExit) as stopped:
            probe.main(arguments)
    assert stopped.value.code == code
    assert CANARY not in capsys.readouterr().err
