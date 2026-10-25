"""Real RSA/HTTP draft-intake contracts; no live Clerk identity or deployment."""

import asyncio
import hashlib
import importlib
import json
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
    token = jwt.encode(claims(), "synthetic-test-secret" if algorithm == "HS256" else None,
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
