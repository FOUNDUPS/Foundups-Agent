"""Offline regression: no credential, network or production service required."""
import asyncio
import pytest
from fastapi import FastAPI, Depends, HTTPException
from fastapi.testclient import TestClient
from modules.foundups.gotjunk.backend import security


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv('FIREBASE_PROJECT_ID', 'demo-gotjunk-security')
    security.firebase_project.cache_clear()
    monkeypatch.setattr(security, 'write_limiter', security.WriteLimiter())
    app = FastAPI()
    app.add_middleware(security.BodyLimitMiddleware, max_bytes=128)
    @app.post('/write')
    def write(uid=Depends(security.require_writer)):
        return {'uid': uid}
    yield TestClient(app)
    security.firebase_project.cache_clear()


def test_missing_configuration_and_credential_fail_closed(client, monkeypatch):
    assert client.post('/write').status_code == 401
    monkeypatch.delenv('FIREBASE_PROJECT_ID')
    monkeypatch.delenv('GOOGLE_CLOUD_PROJECT', raising=False)
    security.firebase_project.cache_clear()
    assert client.post('/write').status_code == 503


def test_verified_identity_and_wrong_issuer(client, monkeypatch):
    seen = {}
    def verify(token, transport, audience):
        seen['audience'] = audience
        return {'sub': 'alice', 'iss': 'https://securetoken.google.com/demo-gotjunk-security'}
    monkeypatch.setattr(security.id_token, 'verify_firebase_token', verify)
    response = client.post('/write', headers={'Authorization': 'Bearer offline-test'})
    assert response.status_code == 200 and response.json()['uid'] == 'alice'
    assert seen['audience'] == 'demo-gotjunk-security'
    monkeypatch.setattr(security.id_token, 'verify_firebase_token', lambda *a, **k: {'sub': 'alice', 'iss': 'wrong-project'})
    assert client.post('/write', headers={'Authorization': 'Bearer offline-test'}).status_code == 401


def test_invalid_signature_rejected(client, monkeypatch):
    def verify(*args, **kwargs):
        raise ValueError('invalid signature')
    monkeypatch.setattr(security.id_token, 'verify_firebase_token', verify)
    assert client.post('/write', headers={'Authorization': 'Bearer offline-test'}).status_code == 401


def test_invalid_attempts_rate_limited_and_forwarded_header_not_trusted(client):
    for i in range(10):
        assert client.post('/write', headers={'X-Forwarded-For': f'192.0.2.{i}'}).status_code == 401
    response = client.post('/write')
    assert response.status_code == 429 and response.headers['retry-after'] == '60'


def test_limiter_capacity_and_expiry():
    now = [0]
    limiter = security.WriteLimiter(limit=1, capacity=1, clock=lambda: now[0])
    limiter.admit('alice')
    with pytest.raises(HTTPException) as failure:
        limiter.admit('bob')
    assert failure.value.status_code == 503
    now[0] = 61
    limiter.admit('bob')
    with pytest.raises(HTTPException) as failure:
        limiter.admit('bob')
    assert failure.value.status_code == 429


def test_body_limit_before_authentication(client):
    assert client.post('/write', content=b'x' * 129).status_code == 413


def test_chunked_body_limit():
    called = []
    async def app(*args):
        called.append(True)
    events = iter([{'type':'http.request','body':b'12345','more_body':True},
                   {'type':'http.request','body':b'67890','more_body':False}])
    sent = []
    async def receive(): return next(events)
    async def send(event): sent.append(event)
    asyncio.run(security.BodyLimitMiddleware(app, max_bytes=8)({'type':'http','method':'POST'}, receive, send))
    assert not called and sent[0]['status'] == 413
