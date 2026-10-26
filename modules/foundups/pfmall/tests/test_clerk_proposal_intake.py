"""Real RSA/HTTP draft-intake contracts; no live Clerk identity or deployment."""

import asyncio
import hashlib
import http.client
import importlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
import jwt
import pytest

from modules.foundups.pfmall.http_api import app

ISSUER = "https://identity.example.com"
ORIGIN = "https://foundups.example.com"
OWNER = "modules.ai_intelligence.ai_overseer.src.foundup_genesis.clerk_intake"
HOST = "modules.foundups.pfmall.intake_host"
PROPOSAL = {"proposed_name": "Garden Share", "reference_urls": ["https://example.com/garden"]}
PATH = "/pfmall/proposals"


@pytest.fixture(scope="module")
def key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def owner():
    return importlib.import_module(OWNER)


@pytest.fixture
def policy(owner, key):
    pem = key.public_key().public_bytes(serialization.Encoding.PEM,
                                        serialization.PublicFormat.SubjectPublicKeyInfo)
    return owner.ClerkIntakePolicy(issuer=ISSUER, authorized_parties=(ORIGIN,),
                                   public_key_pem=pem.decode("ascii"))


@pytest.fixture
def client(policy, monkeypatch):
    monkeypatch.setattr(app.state, "clerk_intake_policy", policy, raising=False)
    with TestClient(app) as current:
        yield current


def claims(**changes):
    now = int(time.time())
    result = {"iss": ISSUER, "azp": ORIGIN, "sub": "user_CaseSensitive",
              "sid": "sess_example", "v": 2, "iat": now, "nbf": now - 5,
              "exp": now + 60}
    result.update(changes)
    return result


def headers(key, payload=None, **changes):
    token = jwt.encode(payload or claims(), key, algorithm="RS256")
    result = {"Authorization": "Bearer " + token, "Origin": ORIGIN,
              "Content-Type": "application/json"}
    result.update(changes)
    return result


def post(client, key, payload=None, body=None, **changes):
    return client.post(PATH, headers=headers(key, payload, **changes),
                       content=json.dumps(PROPOSAL if body is None else body))


def assert_rejected(response, status=401):
    assert response.status_code == status
    assert response.json() == {"detail": "not_authorized" if status == 401 else "invalid_request"}
    assert response.headers["cache-control"] == "no-store"


def test_default_unavailable(monkeypatch):
    monkeypatch.delattr(app.state, "clerk_intake_policy", raising=False)
    with TestClient(app) as current:
        response = current.post(PATH, json=PROPOSAL)
    assert response.status_code == 503
    assert response.json() == {"detail": "intake_unavailable"}


def test_arbitrary_configuration_cannot_enable_route(monkeypatch):
    monkeypatch.setattr(app.state, "clerk_intake_policy", {"authenticated": True}, raising=False)
    with TestClient(app) as current:
        response = current.post(PATH, json=PROPOSAL)
    assert response.status_code == 503


def test_real_signed_bearer_reaches_existing_draft_mapper(client, key):
    response = post(client, key)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "DRAFT_ONLY"
    envelope = data["genesis_envelope"]
    assert envelope["name"] == "Garden Share"
    assert envelope["lifecycle_stage"] == "idea"
    assert envelope["binding_state"] == "unbound"
    assert envelope["external_repo_requested"] is False
    expected = "clerk_" + hashlib.sha256((ISSUER + "\0user_CaseSensitive").encode()).hexdigest()
    assert envelope["requested_by"] == expected
    assert response.headers["cache-control"] == "no-store"


def test_subject_binding_is_case_sensitive_and_session_independent(client, key):
    first = post(client, key).json()["genesis_envelope"]["requested_by"]
    second = post(client, key, claims(sid="sess_second")).json()["genesis_envelope"]["requested_by"]
    third = post(client, key, claims(sub="user_casesensitive")).json()["genesis_envelope"]["requested_by"]
    assert first == second and first != third


def test_requester_handle_is_never_body_identity(client, key):
    response = post(client, key, body={**PROPOSAL, "requester_handle": "repository_owner"})
    assert response.status_code == 201
    assert response.json()["genesis_envelope"]["requested_by"] != "repository_owner"


@pytest.mark.parametrize("field,value", [
    ("iss", "https://other.example.com"), ("azp", "https://other.example.com"),
    ("v", 1), ("v", True), ("v", "2"), ("sub", "org_example"),
    ("sub", "user_bad space"), ("sid", "machine_example"), ("sid", ""),
    ("aud", "other-service"), ("aud", []), ("aud", None),
    ("sts", "pending"), ("sts", "active"), ("sts", None),
    ("act", {"sub": "user_actor"}), ("act", None),
    ("exp", True), ("iat", "123"), ("nbf", 1.5),
])
def test_signed_but_ineligible_claims_are_generic(client, key, field, value):
    assert_rejected(post(client, key, claims(**{field: value})))


@pytest.mark.parametrize("field", ["iss", "azp", "v", "sub", "sid", "iat", "nbf", "exp"])
def test_required_claims(client, key, field):
    payload = claims()
    del payload[field]
    assert_rejected(post(client, key, payload))


@pytest.mark.parametrize("change", ["expired", "boundary", "future_iat", "future_nbf", "long_ttl"])
def test_time_boundaries(client, key, change):
    now = int(time.time())
    changes = {"expired": {"iat": now - 120, "exp": now - 1},
               "boundary": {"exp": now}, "future_iat": {"iat": now + 20},
               "future_nbf": {"nbf": now + 20}, "long_ttl": {"exp": now + 121}}
    assert_rejected(post(client, key, claims(**changes[change])))


def test_ttl_cap_is_valid(client, key):
    now = int(time.time())
    assert post(client, key, claims(iat=now, exp=now + 120)).status_code == 201


def test_exact_body_byte_cap_is_valid(client, key):
    raw = json.dumps(PROPOSAL).encode()
    response = client.post(PATH, content=raw + b" " * (16384 - len(raw)), headers=headers(key))
    assert response.status_code == 201


def test_other_private_key_rejected(client):
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    assert_rejected(post(client, other))


@pytest.mark.parametrize("algorithm", ["none", "HS256"])
def test_algorithm_confusion_rejected(client, algorithm):
    token = jwt.encode(claims(), "synthetic-test-secret-for-algorithm-confusion" if algorithm == "HS256" else None,
                       algorithm=algorithm)
    response = client.post(PATH, json=PROPOSAL,
                           headers={"Authorization": "Bearer " + token, "Origin": ORIGIN})
    assert_rejected(response)


@pytest.mark.parametrize("extra", [{"crit": []}, {"jku": "https://untrusted.example/jwks"},
                                   {"typ": "other"}])
def test_unrequested_header_features_rejected(client, key, extra):
    token = jwt.encode(claims(), key, algorithm="RS256", headers=extra)
    response = client.post(PATH, json=PROPOSAL,
                           headers={"Authorization": "Bearer " + token, "Origin": ORIGIN})
    assert_rejected(response)


@pytest.mark.parametrize("origin", ["", "null", "https://other.example.com"])
def test_request_origin_bound_to_verified_party(client, key, origin):
    assert_rejected(post(client, key, Origin=origin))


@pytest.mark.parametrize("auth", ["", "Bearer junk", "Basic junk", "Bearer  a.b.c", "Bearer " + "a" * 8193])
def test_absent_malformed_and_oversize_bearer(client, key, auth):
    assert_rejected(post(client, key, Authorization=auth))


def test_cookie_and_invite_cannot_authenticate(client, key):
    token = jwt.encode(claims(), key, algorithm="RS256")
    response = client.post(PATH, json=PROPOSAL, headers={"Origin": ORIGIN,
        "Cookie": "__session=" + token + "; foundup_session=" + token,
        "X-Foundup-Invite": "invite.v1.synthetic"})
    assert_rejected(response)


@pytest.mark.parametrize("body", [[], {}, {"proposed_name": ""},
    {**PROPOSAL, "authenticated": True}, {**PROPOSAL, "uid": "user_other"},
    {**PROPOSAL, "source_authority": "trusted"}, {**PROPOSAL, "inviteValidated": True}])
def test_body_preflight_precedes_verifier(client, key, owner, monkeypatch, body):
    calls = []
    monkeypatch.setattr(owner, "_verify_session", lambda *args: calls.append(1))
    assert_rejected(post(client, key, body=body), 400)
    assert calls == []


@pytest.mark.parametrize("raw", [b"{", b"\xff", b"x" * 16385, b"null"])
def test_raw_invalid_body_never_verifies(client, key, owner, monkeypatch, raw):
    calls = []
    monkeypatch.setattr(owner, "_verify_session", lambda *args: calls.append(1))
    response = client.post(PATH, content=raw, headers=headers(key))
    assert_rejected(response, 400)
    assert calls == []


@pytest.mark.parametrize("name,value", [("Content-Type", "text/plain"),
    ("Content-Type", "application/json; charset=latin1"), ("Content-Encoding", "gzip"),
    ("Content-Length", "16385"), ("Content-Length", "garbage")])
def test_wire_policy(client, key, name, value):
    assert_rejected(post(client, key, **{name: value}), 400)


@pytest.mark.parametrize("name", ["Authorization", "Origin", "Content-Type", "Content-Encoding", "Content-Length"])
def test_duplicate_security_headers_rejected(client, key, name):
    current = list(headers(key).items())
    current.extend([(name, "identity" if name == "Content-Encoding" else "0"), (name.lower(), "0")])
    response = client.post(PATH, content=json.dumps(PROPOSAL), headers=current)
    assert_rejected(response, 400)


async def asgi_request(chunks, current_headers, delayed=False):
    messages = []
    index = 0

    async def receive():
        nonlocal index
        if delayed:
            await asyncio.sleep(10)
        chunk = chunks[index]
        index += 1
        return {"type": "http.request", "body": chunk, "more_body": index < len(chunks)}

    async def send(message):
        messages.append(message)

    scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
             "method": "POST", "scheme": "https", "path": PATH, "raw_path": PATH.encode(),
             "query_string": b"", "root_path": "", "server": ("testserver", 443),
             "client": ("127.0.0.1", 1), "headers": [
                 (k.lower().encode(), v.encode()) for k, v in current_headers.items()]}
    await app(scope, receive, send)
    status = next(message["status"] for message in messages if message["type"] == "http.response.start")
    return status, b"".join(message.get("body", b"") for message in messages)


def test_actual_stream_cap_ignores_false_content_length(client, key, owner, monkeypatch):
    calls = []
    monkeypatch.setattr(owner, "_verify_session", lambda *args: calls.append(1))
    current = headers(key, **{"Content-Length": "1"})
    status, _ = asyncio.run(asgi_request([b" " * 8192, b" " * 8192, b"x"], current))
    assert status == 400 and calls == []


def test_body_read_timeout(client, key, monkeypatch):
    import modules.foundups.pfmall.http_api as http
    monkeypatch.setattr(http, "_PROPOSAL_READ_SECONDS", 0.01)
    status, _ = asyncio.run(asgi_request([b"{}"], headers(key), delayed=True))
    assert status == 400


def test_response_and_policy_repr_do_not_expose_identity_or_key(client, key, policy):
    token = jwt.encode(claims(), key, algorithm="RS256")
    response = client.post(PATH, json=PROPOSAL,
                           headers={"Authorization": "Bearer " + token, "Origin": ORIGIN})
    text = response.text + repr(policy)
    values = [token, policy.public_key_pem, "user_CaseSensitive", "sess_example"]
    assert not any(value in text for value in values)


@pytest.mark.parametrize("change", [{"issuer": "http://identity.example.com"},
    {"issuer": ISSUER + "/path"},
    {"authorized_parties": ()}, {"authorized_parties": ("*",)},
    {"authorized_parties": [ORIGIN]},
    {"public_key_pem": "not-a-key"}])
def test_invalid_server_policy_fails_closed(owner, policy, change):
    values = {"issuer": policy.issuer, "authorized_parties": policy.authorized_parties,
              "public_key_pem": policy.public_key_pem, **change}
    with pytest.raises(ValueError, match="^invalid_clerk_intake_policy$"):
        owner.ClerkIntakePolicy(**values)


@pytest.mark.parametrize("private,weak", [(True, False), (False, True)])
def test_private_or_weak_server_key_rejected(owner, key, private, weak):
    selected = rsa.generate_private_key(public_exponent=65537, key_size=1024) if weak else key
    if private:
        pem = selected.private_bytes(serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    else:
        pem = selected.public_key().public_bytes(serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo)
    with pytest.raises(ValueError, match="^invalid_clerk_intake_policy$"):
        owner.ClerkIntakePolicy(issuer=ISSUER, authorized_parties=(ORIGIN,),
                                public_key_pem=pem.decode("ascii"))


@pytest.mark.parametrize("suffix", ["private", "public", "junk"])
def test_public_policy_accepts_exactly_one_public_document(owner, policy, key, suffix):
    private = key.private_bytes(serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode("ascii")
    extra = {"private": private, "public": policy.public_key_pem, "junk": "ignored-trailer"}
    with pytest.raises(ValueError, match="^invalid_clerk_intake_policy$"):
        owner.ClerkIntakePolicy(issuer=ISSUER, authorized_parties=(ORIGIN,),
                                public_key_pem=policy.public_key_pem + extra[suffix])


def test_crlf_public_document_is_supported(owner, policy):
    current = owner.ClerkIntakePolicy(issuer=ISSUER, authorized_parties=(ORIGIN,),
        public_key_pem=policy.public_key_pem.replace("\n", "\r\n"))
    assert current.issuer == policy.issuer


def host_config(tmp_path, policy):
    path = tmp_path / "policy.json"
    path.write_text(json.dumps({"issuer": policy.issuer,
        "authorized_parties": list(policy.authorized_parties),
        "public_key_pem": policy.public_key_pem}), encoding="utf-8")
    return path


def test_isolated_host_reuses_handler_with_its_own_policy(tmp_path, policy, key, monkeypatch):
    monkeypatch.setenv("PFMALL_CLERK_POLICY_FILE", str(host_config(tmp_path, policy)))
    monkeypatch.setattr(app.state, "clerk_intake_policy", None, raising=False)
    current = importlib.import_module(HOST).create_app()
    route = next(route for route in current.routes if route.path == PATH)
    assert route.endpoint is importlib.import_module("modules.foundups.pfmall.http_api").foundup_proposal
    with TestClient(current) as client:
        response = post(client, key)
        assert response.status_code == 201 and response.json()["status"] == "DRAFT_ONLY"
        assert response.headers["cache-control"] == "no-store"
        assert_rejected(post(client, key, Origin="https://other.example.com"))
    assert app.state.clerk_intake_policy is None


def test_host_instances_keep_independent_signing_policies(tmp_path, policy, key, owner, monkeypatch):
    path = host_config(tmp_path, policy)
    monkeypatch.setenv("PFMALL_CLERK_POLICY_FILE", str(path))
    first = importlib.import_module(HOST).create_app()
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = other.public_key().public_bytes(serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo).decode("ascii")
    host_config(tmp_path, owner.ClerkIntakePolicy(ISSUER, (ORIGIN,), pem))
    second = importlib.import_module(HOST).create_app()
    with TestClient(first) as a, TestClient(second) as b:
        assert post(a, key).status_code == post(b, other).status_code == 201
        assert_rejected(post(a, other))
        assert_rejected(post(b, key))


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json", "/pfmall/catalog",
                                  "/pfmall/ui/", "/pfmall/static/", "/f/example"])
def test_host_does_not_publish_unrelated_routes(tmp_path, policy, monkeypatch, path):
    monkeypatch.setenv("PFMALL_CLERK_POLICY_FILE", str(host_config(tmp_path, policy)))
    with TestClient(importlib.import_module(HOST).create_app()) as current:
        assert current.get(path).status_code == 404


def test_host_health_exposes_no_policy_or_catalog(tmp_path, policy, monkeypatch):
    monkeypatch.setenv("PFMALL_CLERK_POLICY_FILE", str(host_config(tmp_path, policy)))
    with TestClient(importlib.import_module(HOST).create_app()) as current:
        response = current.get("/healthz")
    assert response.status_code == 200 and response.json() == {"status": "ready"}
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("kind", ["missing_env", "relative", "missing_file", "directory",
    "oversize", "utf8", "malformed", "array", "null", "duplicate", "unknown", "deep",
    "missing_issuer", "missing_parties", "missing_key", "parties_string", "private_key"])
def test_host_rejects_invalid_server_config_generically(tmp_path, policy, key, monkeypatch, kind):
    path = host_config(tmp_path, policy)
    values = json.loads(path.read_text(encoding="utf-8"))
    missing = {"missing_issuer": "issuer", "missing_parties": "authorized_parties",
               "missing_key": "public_key_pem"}
    if kind in missing:
        del values[missing[kind]]
    elif kind == "unknown":
        values["authenticated"] = True
    elif kind == "parties_string":
        values["authorized_parties"] = ORIGIN
    elif kind == "private_key":
        values["public_key_pem"] = key.private_bytes(serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode("ascii")
    raw = json.dumps(values).encode("utf-8")
    special = {"oversize": raw + b" " * (16385 - len(raw)), "utf8": b"\xff",
        "malformed": b"{", "array": b"[]", "null": b"null", "deep": b"[" * 1100 + b"]" * 1100,
        "duplicate": b'{"issuer":"https://other.example.com",' + raw[1:]}
    path.write_bytes(special.get(kind, raw))
    selected = {"relative": "policy.json", "missing_file": str(path) + ".missing",
                "directory": str(tmp_path)}.get(kind, str(path))
    monkeypatch.setenv("PFMALL_CLERK_POLICY_FILE", selected)
    if kind == "missing_env":
        monkeypatch.delenv("PFMALL_CLERK_POLICY_FILE")
    with pytest.raises(RuntimeError, match="^intake_configuration_invalid$"):
        importlib.import_module(HOST).create_app()


def test_host_accepts_exact_config_byte_cap(tmp_path, policy, key, monkeypatch):
    path = host_config(tmp_path, policy)
    raw = path.read_bytes()
    path.write_bytes(raw + b" " * (16384 - len(raw)))
    monkeypatch.setenv("PFMALL_CLERK_POLICY_FILE", str(path))
    with TestClient(importlib.import_module(HOST).create_app()) as current:
        assert post(current, key).status_code == 201


@pytest.fixture
def wire_server(tmp_path):
    """Real child/loopback profile; no OS isolation or graceful-stop claim."""
    children = []

    def start(config):
        log = tmp_path / (str(len(children)) + "-server.log")
        env = {k: os.environ[k] for k in ("SystemRoot", "WINDIR", "COMSPEC") if k in os.environ}
        env.update(PYTHONDONTWRITEBYTECODE="1", PYTHON_DOTENV_DISABLED="1",
                   PFMALL_CLERK_POLICY_FILE=str(config), HOME=str(tmp_path),
                   USERPROFILE=str(tmp_path), TEMP=str(tmp_path), TMP=str(tmp_path))
        root = str(Path(__file__).resolve().parents[4])
        args = [sys.executable, "-I", "-B", "-m", "uvicorn", HOST + ":create_app",
            "--factory", "--app-dir", root, "--host", "127.0.0.1", "--port", "0",
            "--workers", "1", "--loop", "asyncio", "--http", "h11", "--interface", "asgi3",
            "--ws", "none", "--lifespan", "on", "--no-proxy-headers", "--no-access-log",
            "--no-server-header", "--limit-concurrency", "16", "--backlog", "32",
            "--timeout-keep-alive", "5", "--timeout-graceful-shutdown", "10",
            "--h11-max-incomplete-event-size", "16384", "--log-level", "info"]
        with log.open("wb") as stream:
            child = subprocess.Popen(args, cwd=root, env=env, stdout=stream, stderr=stream)
        children.append(child)
        deadline, port = time.monotonic() + 10, None
        while time.monotonic() < deadline:
            text = log.read_text(encoding="utf-8")
            match = re.search(r"Uvicorn running on http://127\.0\.0\.1:(\d+)", text)
            if match:
                server_pid = int(re.search(r"Started server process \[(\d+)\]", text).group(1))
                if os.name == "nt":
                    powershell = Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
                    command = f"(Get-CimInstance Win32_Process -Filter 'ProcessId = {server_pid}').ParentProcessId"
                    parent = subprocess.check_output([str(powershell), "-NoProfile", "-Command", command], timeout=4)
                    assert int(parent) == child.pid
                else:
                    assert server_pid == child.pid
                port = int(match.group(1))
                break
            if child.poll() is not None:
                break
            time.sleep(0.025)
        return child, port, log

    try:
        yield start
    finally:
        for child in children:
            if child.poll() is None:
                if os.name == "nt":
                    killer = Path(os.environ["SystemRoot"]) / "System32/taskkill.exe"
                    subprocess.run([str(killer), "/PID", str(child.pid), "/T", "/F"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=4, check=True)
                else:
                    child.terminate()
            try:
                child.wait(timeout=3)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=3)
            assert child.poll() is not None


def test_real_server_delivers_only_bounded_drafts(tmp_path, policy, key, wire_server):
    child, port, log = wire_server(host_config(tmp_path, policy))
    assert port is not None and child.poll() is None

    def request(method, path, body=None, selected=None, chunked=False):
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
        try:
            connection.request(method, path, body=body, headers=selected or {},
                               encode_chunked=chunked)
            response = connection.getresponse()
            raw = response.read(32768)
            assert len(raw) < 32768 and response.getheader("server") is None
            return response, json.loads(raw)
        finally:
            connection.close()

    response, data = request("GET", "/healthz")
    assert response.status == 200 and data == {"status": "ready"}
    assert response.getheader("cache-control") == "no-store"
    response, data = request("POST", PATH, json.dumps(PROPOSAL),
                             {"Content-Type": "application/json", "Origin": ORIGIN})
    assert response.status == 401 and data == {"detail": "not_authorized"}
    response, data = request("POST", PATH, json.dumps(PROPOSAL), headers(key))
    assert response.status == 201 and data["status"] == "DRAFT_ONLY"
    assert response.getheader("cache-control") == "no-store"
    response, _ = request("GET", "/pfmall/catalog")
    assert response.status == 404
    raw = json.dumps(PROPOSAL).encode("utf-8")
    chunks = iter([raw + b" " * (16384 - len(raw)), b" "])
    response, data = request("POST", PATH, chunks, headers(key), chunked=True)
    assert response.status == 400 and data == {"detail": "invalid_request"}
    assert response.getheader("cache-control") == "no-store"
    assert child.poll() is None and '"GET ' not in log.read_text(encoding="utf-8")
    assert '"POST ' not in log.read_text(encoding="utf-8")


@pytest.mark.parametrize("kind", ["missing", "malformed"])
def test_real_server_invalid_policy_never_listens(tmp_path, wire_server, kind):
    config = tmp_path / "policy.json"
    if kind == "malformed":
        config.write_text("{", encoding="utf-8")
    child, port, log = wire_server(config)
    assert port is None and child.poll() is not None and child.returncode != 0
    text = log.read_text(encoding="utf-8")
    assert "intake_configuration_invalid" in text and str(config) not in text
