"""One-use loopback form delivering selected telemetry credentials to Windows vault.

Run explicitly with the vetted Python. The only output is the local entry URL
and a static terminal status. The listener ends after one stored pair or300s.
Default: Langfuse Viewer pair. --type sentry-errors selects one Sentry DSN.
No request logs, plaintext files, external resources or generic targets exist.
"""
from __future__ import annotations

import importlib.util
import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import secrets
import socket
import threading
import time
from urllib.parse import parse_qs

MAX_BODY = 4096
TTL_SECONDS = 299  # Reserve a shutdown margin below the five-minute limit.
SOCKET_TIMEOUT = 0.25
_SAFE_STORAGE_CODES = {"invalid_credential_shape", "credential_too_large", "windows_required",
                       "credential_vault_unavailable", "credential_store_failed"}
FORM = b'''<!doctype html><html><head><meta charset="utf-8"><title>FOUNDUPS Viewer setup</title></head>
<body><h1>Store Langfuse Viewer credentials</h1><p>One-use local setup. Values go only to this Windows account's Credential Manager.</p>
<form method="post" autocomplete="off"><label>Public key <input name="public_key" type="password" autocomplete="off" required maxlength="300"></label>
<label>Secret key <input name="secret_key" type="password" autocomplete="off" required maxlength="300"></label>
<button type="submit">Store Viewer credentials</button></form></body></html>'''
SENTRY_FORM = b'''<!doctype html><html><head><meta charset="utf-8"><title>FOUNDUPS Sentry setup</title></head>
<body><h1>Store Sentry error DSN</h1><p>One-use local setup. The DSN goes only to this Windows account's Credential Manager.</p>
<form method="post" autocomplete="off"><label>Sentry DSN <input name="dsn" type="password" autocomplete="off" required maxlength="512"></label>
<button type="submit">Store Sentry DSN</button></form></body></html>'''


def _store(kind, values):
    source = Path(__file__).resolve().parents[1] / "modules/infrastructure/secrets_mcp/src/windows_pilot_credentials.py"
    spec = importlib.util.spec_from_file_location("foundups_viewer_vault", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.store_credentials(kind, values)


class ProvisionServer(HTTPServer):
    def __init__(self, store=None, credential_type="langfuse-viewer"):
        if credential_type not in {"langfuse-viewer", "sentry-errors"}:
            raise ValueError("unsupported_provision_type")
        super().__init__(("127.0.0.1", 0), ProvisionHandler)
        self.credential_type = credential_type
        self.fields = {"dsn"} if credential_type == "sentry-errors" else {"public_key", "secret_key"}
        self.form = SENTRY_FORM if credential_type == "sentry-errors" else FORM
        self.store = _store if store is None else store
        self.host = "127.0.0.1:" + str(self.server_port)
        self.origin = "http://" + self.host
        self.entry_path = "/" + secrets.token_hex(32)
        self.deadline = time.monotonic() + TTL_SECONDS
        self.stored = False
        self.active_connection = None
        self.timeout = 1

    def get_request(self):
        connection, address = super().get_request()
        self.active_connection = connection
        connection.settimeout(max(0.001, min(SOCKET_TIMEOUT, self.deadline - time.monotonic())))
        return connection, address

    def handle_error(self, request, client_address):
        pass  # No request, credential or exception logging.

    def expire(self):
        self.deadline = 0
        for connection in (self.active_connection, self.socket):
            if connection is not None:
                try:
                    connection.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                connection.close()


class ProvisionHandler(BaseHTTPRequestHandler):
    server_version = "FOUNDUPS"
    sys_version = ""

    def log_message(self, *args):
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", "default-src 'none'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Connection", "close")
        self.close_connection = True
        super().end_headers()

    def _reply(self, status, body=b"Request rejected."):
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_error(self, code, message=None, explain=None):
        self._reply(code)

    def _reject(self, status, stage, code="request_rejected"):
        result = {"status": "rejected", "stage": stage, "code": code}
        if stage == "admission":
            hosts = self.headers.get_all("Host", [])
            origins = self.headers.get_all("Origin", [])
            result["checks"] = {
                "used": self.server.stored,
                "expired": time.monotonic() >= self.server.deadline,
                "path_mismatch": self.path != self.server.entry_path,
                "host_mismatch": hosts != [self.server.host],
                "host_missing": not hosts,
                "host_duplicate": len(hosts) > 1,
                "origin_mismatch": origins not in ([], [self.server.origin]),
                "origin_missing": not origins,
                "origin_duplicate": len(origins) > 1,
                "origin_null": origins == ["null"],
            }
        self._reply(status, json.dumps(result).encode("ascii"))

    def _admitted(self):
        return (not self.server.stored and time.monotonic() < self.server.deadline
                and self.path == self.server.entry_path
                and self.headers.get_all("Host", []) == [self.server.host]
                and self.headers.get_all("Origin", []) in ([], [self.server.origin]))

    def do_GET(self):
        self._reply(200, self.server.form) if self._admitted() else self._reply(404)

    def do_POST(self):
        if not self._admitted():
            self._reject(404, "admission")
            return
        lengths = self.headers.get_all("Content-Length", [])
        types = self.headers.get_all("Content-Type", [])
        if (len(lengths) != 1 or not 1 <= len(lengths[0]) <= 4
                or not lengths[0].isascii() or not lengths[0].isdigit()
                or not 0 < int(lengths[0]) <= MAX_BODY
                or self.headers.get("Transfer-Encoding") is not None or len(types) != 1
                or types[0].split(";", 1)[0].strip() != "application/x-www-form-urlencoded"):
            self._reject(400, "framing")
            return
        values = {}
        stage = "encoding"
        try:
            body = self.rfile.read(int(lengths[0]))
            if len(body) != int(lengths[0]):
                raise ValueError
            fields = parse_qs(body.decode("ascii"), keep_blank_values=True,
                              strict_parsing=True, errors="strict", max_num_fields=3)
            stage = "shape"
            if set(fields) != self.server.fields or any(len(v) != 1 for v in fields.values()):
                raise ValueError
            values = {key: value[0] for key, value in fields.items()}
            stage = "admission"
            if not self._admitted():
                raise ValueError
            stage = "storage"
            self.server.store(self.server.credential_type, values)
            self.server.stored = True
        except Exception as exc:
            args = exc.args
            code = args[0] if (stage == "storage" and len(args) == 1
                               and type(args[0]) is str and args[0] in _SAFE_STORAGE_CODES) else "operation_failed"
            self._reject(400, stage, code)
            return
        finally:
            values.clear()
        self._reply(200, b"<!doctype html><title>Setup complete</title><h1>Credentials stored.</h1><p>The local setup listener is closing.</p>")


def _serve(credential_type="langfuse-viewer"):
    with ProvisionServer(credential_type=credential_type) as server:
        expiry = threading.Timer(TTL_SECONDS, server.expire)
        expiry.daemon = True
        expiry.start()
        print(json.dumps({"status": "ready", "url": server.origin + server.entry_path}), flush=True)
        try:
            while not server.stored and time.monotonic() < server.deadline:
                server.handle_request()
        except (OSError, ValueError):
            pass
        finally:
            expiry.cancel()
        print(json.dumps({"status": "stored" if server.stored else "expired"}), flush=True)
        return 0 if server.stored else 2


class _SafeParser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError("invalid_arguments")


def main(argv=None):
    try:
        parser = _SafeParser(description=__doc__)
        parser.add_argument("--type", choices=("langfuse-viewer", "sentry-errors"), default="langfuse-viewer")
        return _serve(parser.parse_args(argv).type)
    except KeyboardInterrupt:
        print('{"status":"cancelled"}', flush=True)
    except Exception:
        print('{"status":"setup_failed"}', flush=True)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
