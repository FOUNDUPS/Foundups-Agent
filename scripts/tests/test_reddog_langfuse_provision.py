"""Synthetic loopback HTTP tests; no actual vault or credential access."""
import http.client
import importlib.util
import json
from pathlib import Path
import socket
import threading
import time
from urllib.parse import urlencode

import pytest

PATH = Path(__file__).resolve().parents[1] / "reddog_langfuse_provision.py"
SPEC = importlib.util.spec_from_file_location("loopback_provision_subject", PATH)
subject = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(subject)


@pytest.fixture
def server():
    calls = []
    with subject.ProvisionServer(store=lambda kind, values: calls.append((kind, dict(values)))) as value:
        value.calls = calls
        yield value


def request(server, method="GET", path=None, body=None, headers=None):
    worker = threading.Thread(target=server.handle_request, daemon=True)
    worker.start()
    connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    try:
        connection.request(method, server.entry_path if path is None else path, body=body, headers=headers or {})
        response = connection.getresponse()
        result = response.status, dict(response.getheaders()), response.read()
    finally:
        connection.close()
        worker.join(timeout=2)
        assert not worker.is_alive()
    return result


def post_headers(server):
    return {"Content-Type": "application/x-www-form-urlencoded", "Origin": server.origin}


def test_form_only_on_unpredictable_exact_loopback_path_and_private_headers(server):
    assert server.server_address[0] == "127.0.0.1" and len(server.entry_path) > 40
    status, headers, body = request(server)
    assert status == 200 and body.count(b'type="password"') == 2
    assert b'<script' not in body and b'autocomplete="off"' in body
    assert headers["Cache-Control"] == "no-store"
    assert headers["Referrer-Policy"] == "same-origin"
    assert "default-src 'none'" in headers["Content-Security-Policy"]
    assert "form-action 'self'" in headers["Content-Security-Policy"]
    assert "frame-ancestors 'none'" in headers["Content-Security-Policy"]


@pytest.mark.parametrize("path", ["/", "/wrong-nonce", "/wrong?PRIVATE"])
def test_nonce_rejection_never_echoes_requested_path(server, path):
    status, _, body = request(server, path=path)
    assert status == 404 and body == b"Request rejected." and not server.calls


@pytest.mark.parametrize("headers", [{"Host": "attacker.example"}, {"Host": "localhost"},
                                    {"Origin": "https://attacker.example"}, {"Origin": "null"}])
def test_foreign_host_or_origin_blocks_before_store(server, headers):
    status, _, body = request(server, headers=headers)
    assert status == 404 and body == b"Request rejected." and not server.calls


def test_success_uses_only_fixed_viewer_target_then_refuses_replay(server, capsys):
    fields = {"public_key": "SYNTHETIC_PUBLIC", "secret_key": "SYNTHETIC_SECRET"}
    status, _, body = request(server, "POST", body=urlencode(fields), headers=post_headers(server))
    assert status == 200 and b"stored" in body and b"SYNTHETIC" not in body
    assert server.calls == [("langfuse-viewer", fields)] and server.stored
    assert request(server)[0] == 404
    captured = capsys.readouterr()
    assert "SYNTHETIC" not in captured.out + captured.err


@pytest.mark.parametrize("body", ["secret_key=PRIVATE", "public_key=x&secret_key=PRIVATE&other=y",
                                 "public_key=x&secret_key=PRIVATE&secret_key=y", "bad%ff=PRIVATE",
                                 "x" * 4097])
def test_invalid_shape_or_oversized_body_no_echo_or_vault_call(server, body):
    status, _, response = request(server, "POST", body=body, headers=post_headers(server))
    assert status == 400 and json.loads(response)["status"] == "rejected" and not server.calls
    assert b"PRIVATE" not in response
    assert not server.stored


def test_vault_exception_never_echoes_values_or_exception(server):
    def broken(kind, values):
        raise RuntimeError("PRIVATE_FAILURE")
    server.store = broken
    status, _, response = request(server, "POST", body="public_key=x&secret_key=PRIVATE", headers=post_headers(server))
    assert status == 400 and json.loads(response) == {"status": "rejected", "stage": "storage", "code": "operation_failed"}
    assert not server.stored


def test_ttl_is_at_most_five_minutes_and_expired_server_refuses(server):
    assert subject.TTL_SECONDS <= 300
    server.deadline = time.monotonic() - 1
    try:
        assert request(server)[0] == 404
    except (ConnectionAbortedError, ConnectionResetError, http.client.RemoteDisconnected):
        pass  # An expired socket may close before its static response on Windows.
    assert not server.calls and not server.stored


def test_transfer_encoding_is_rejected_even_with_length(server):
    headers = {**post_headers(server), "Transfer-Encoding": "chunked", "Content-Length": "1"}
    assert request(server, "POST", body="x", headers=headers)[0] == 400
    assert not server.calls


def test_expiry_closes_loopback_listener(server):
    server.expire()
    assert server.socket.fileno() == -1 and server.deadline == 0


@pytest.mark.parametrize("duplicate", ["Host", "Origin", "Content-Length", "Content-Type"])
def test_duplicate_sensitive_headers_rejected_before_vault(server, duplicate):
    headers = {"Host": server.host, **post_headers(server), "Content-Length": "37"}
    lines = ["POST " + server.entry_path + " HTTP/1.1"]
    for key, value in headers.items():
        lines.append(key + ": " + value)
        if key == duplicate:
            lines.append(key + ": " + value)
    worker = threading.Thread(target=server.handle_request, daemon=True)
    worker.start()
    with socket.create_connection(server.server_address, timeout=2) as connection:
        connection.sendall(("\r\n".join(lines) + "\r\n\r\n").encode())
        response = http.client.HTTPResponse(connection)
        response.begin()
        assert response.status in (400, 404)
        assert json.loads(response.read())["status"] == "rejected"
    worker.join(timeout=2)
    assert not worker.is_alive() and not server.calls


def test_expiry_interrupts_incomplete_body_without_vault_call(server, monkeypatch, capsys):
    admitted = threading.Event()
    original = subject.ProvisionHandler._admitted
    def observed(handler):
        result = original(handler)
        if result:
            admitted.set()
        return result
    monkeypatch.setattr(subject.ProvisionHandler, "_admitted", observed)
    worker = threading.Thread(target=server.handle_request, daemon=True)
    worker.start()
    with socket.create_connection(server.server_address, timeout=2) as connection:
        connection.sendall(("POST " + server.entry_path + " HTTP/1.1\r\nHost: " + server.host
                            + "\r\nContent-Type: application/x-www-form-urlencoded\r\n"
                            + "Content-Length: 100\r\n\r\nsecret_key=SYNTHETIC").encode())
        assert admitted.wait(timeout=1)
        server.expire()
        worker.join(timeout=2)
    assert not worker.is_alive() and not server.calls and not server.stored
    captured = capsys.readouterr()
    assert not captured.out and not captured.err


@pytest.mark.parametrize("failure,status", [(RuntimeError("PRIVATE_PATH_OR_SECRET"), "setup_failed"),
                                           (KeyboardInterrupt(), "cancelled")])
def test_top_level_failure_is_static_status(monkeypatch, capsys, failure, status):
    def broken(*args):
        raise failure
    monkeypatch.setattr(subject, "_serve", broken)
    assert subject.main([]) == 2
    assert capsys.readouterr().out == '{"status":"' + status + '"}\n'


def test_actual_adapter_import_ready_and_invalid_values_stop_before_vault():
    with pytest.raises(Exception) as caught:
        subject._store("langfuse-viewer", {"public_key": "invalid", "secret_key": "invalid"})
    assert type(caught.value).__name__ == "PilotCredentialError"
    assert caught.value.args == ("invalid_credential_shape",)


def test_safe_storage_failure_code_is_preserved_without_raw_exception(server):
    def broken(kind, values):
        raise RuntimeError("credential_store_failed")
    server.store = broken
    status, _, response = request(server, "POST", body="public_key=x&secret_key=PRIVATE", headers=post_headers(server))
    assert status == 400 and json.loads(response)["code"] == "credential_store_failed"
    assert b"PRIVATE" not in response


def test_extreme_content_length_is_static_framing_failure(server):
    headers = {**post_headers(server), "Content-Length": "9" * 5000}
    status, _, response = request(server, "POST", body="", headers=headers)
    assert status == 400 and json.loads(response)["stage"] == "framing" and not server.calls


@pytest.mark.parametrize("headers,expected", [({"Origin": "null"}, "origin_null"),
                                             ({"Origin": "https://PRIVATE.invalid"}, "origin_mismatch"),
                                             ({"Host": "PRIVATE.invalid"}, "host_mismatch")])
def test_admission_diagnostic_flags_contain_no_header_values(server, headers, expected):
    status, _, response = request(server, "POST", body="public_key=x&secret_key=PRIVATE",
                                   headers={**post_headers(server), **headers})
    result = json.loads(response)
    assert status == 404 and result["stage"] == "admission"
    assert result["checks"][expected] is True
    assert all(type(value) is bool for value in result["checks"].values())
    assert b"PRIVATE" not in response and server.entry_path.encode() not in response


def test_sentry_form_accepts_only_one_fixed_dsn_field_and_target():
    calls = []
    with subject.ProvisionServer(store=lambda kind, values: calls.append((kind, dict(values))), credential_type="sentry-errors") as server:
        status, _, form = request(server)
        assert status == 200 and form.count(b'type="password"') == 1 and b'name="dsn"' in form
        assert b'name="secret_key"' not in form
        assert request(server, "POST", body="public_key=x&secret_key=PRIVATE", headers=post_headers(server))[0] == 400
        assert not calls
        status, _, body = request(server, "POST", body="dsn=SYNTHETIC_DSN", headers=post_headers(server))
        assert status == 200 and b"SYNTHETIC_DSN" not in body
        assert calls == [("sentry-errors", {"dsn": "SYNTHETIC_DSN"})]
        assert request(server)[0] == 404


def test_provision_rejects_other_targets_and_unknown_arguments(capsys):
    with pytest.raises(ValueError, match="unsupported_provision_type"):
        subject.ProvisionServer(credential_type="openrouter-pilot")
    assert subject.main(["--PRIVATE", "PRIVATE_VALUE"]) == 2
    assert capsys.readouterr().out == '{"status":"setup_failed"}\n'
