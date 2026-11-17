"""Synthetic provider and real Streamable HTTP transport contract tests."""

from dataclasses import replace
from hashlib import sha256
from threading import Thread
from time import time

from cryptography.fernet import Fernet
from mcp.server.auth.provider import AccessToken
import pytest
from starlette.testclient import TestClient

from modules.infrastructure.foundups_mcp_bridge.src.draft_auth import (
    DRAFT_READ_SCOPE, DRAFT_WRITE_SCOPE,
)
from modules.infrastructure.foundups_mcp_bridge.src.draft_correction import (
    DraftCorrection, DraftJournal, DraftPolicy,
)
from modules.infrastructure.foundups_mcp_bridge.src.draft_gmail import GmailDraft, GmailError
from modules.infrastructure.foundups_mcp_bridge.src.draft_mime import rewrite_from
from modules.infrastructure.foundups_mcp_bridge.src.draft_server import build_app

ACCOUNT = "owner@example.test"
OLD = "prior@example.test"
ISSUER = "https://issuer.example.test"
RESOURCE = "https://resource.example.test/v1/mcp/private-test"
ORIGIN = "http://127.0.0.1:8178"
RAW = (
    f"From: {OLD}\r\nTo: other@example.test\r\nSubject: Review\r\n"
    "Message-ID: <test@example.test>\r\nContent-Type: text/plain; charset=utf-8\r\n\r\n"
    "Private synthetic marker: 讀懆ｨｼ逕ｨ\r\n"
).encode("utf-8")
DIGEST = sha256(RAW).hexdigest()
ARGS = dict(draft_id="d1", expected_digest=DIGEST, approved_sender=ACCOUNT, request_id="req1")
ACCEPT = {"Accept": "application/json, text/event-stream"}


class FakeGmail:
    def __init__(self):
        self.drafts = {"d1": GmailDraft("d1", "m1", "t1", RAW)}
        self.account = ACCOUNT
        self.calls = 0
        self.update_mode = "normal"

    def get_account(self):
        return self.account

    def list_send_as(self):
        return frozenset({ACCOUNT})

    def list_draft_ids(self):
        return tuple(self.drafts)

    def get_draft(self, draft_id):
        return self.drafts[draft_id]

    def update_draft(self, draft_id, raw, thread_id, *, expected):
        if self.update_mode == "conflict":
            self.drafts[draft_id] = replace(expected, message_id="changed")
        if self.drafts[draft_id] != expected:
            raise GmailError("concurrent_edit")
        self.calls += 1
        if self.update_mode == "timeout_before":
            raise GmailError("mutation_uncertain")
        self.drafts[draft_id] = GmailDraft(
            draft_id, "m2", "changed" if self.update_mode == "bad_thread" else thread_id, raw,
        )
        if self.update_mode == "timeout_after":
            raise GmailError("mutation_uncertain")
        return "m2"


class Verifier:
    def __init__(self):
        self.count = 0
        self.revoke_at = None

    async def verify_token(self, token):
        self.count += 1
        if self.count == self.revoke_at or token not in {"read", "write"}:
            return None
        scopes = [DRAFT_READ_SCOPE]
        if token == "write":
            scopes.append(DRAFT_WRITE_SCOPE)
        return AccessToken(token=token, client_id="synthetic", scopes=scopes,
                           expires_at=int(time()) + 60, resource=RESOURCE)


@pytest.fixture
def setup(tmp_path):
    cipher = Fernet(Fernet.generate_key())
    path = tmp_path / "journal.sqlite3"
    journal = DraftJournal(path, cipher)
    gmail = FakeGmail()
    service = DraftCorrection(DraftPolicy(ACCOUNT, ACCOUNT, DIGEST, "req1", 100, 300),
                              gmail, journal, clock=lambda: 200)
    return service, gmail, path, cipher


def apply(service, **overrides):
    return service.set_draft_sender(**{**ARGS, **overrides}, dry_run=False,
                                    allow_write=True, confirm_write=lambda: True)


@pytest.mark.parametrize("case,reason", [
    ("wrong_account", "wrong_account"), ("missing", "target_missing_or_changed"),
    ("duplicate", "ambiguous_target"), ("stale", "stale_digest"),
    ("sender", "unapproved_sender"), ("grant", "private_approval_required"),
    ("future", "private_approval_required"), ("expired", "private_approval_required"),
    ("conflict", "concurrent_edit"),
])
def test_holds_before_provider_mutation(setup, case, reason):
    service, gmail, _, _ = setup
    args = {}
    if case == "wrong_account":
        gmail.account = "unknown@example.test"
    elif case == "missing":
        gmail.drafts.clear()
    elif case == "duplicate":
        gmail.drafts["d2"] = replace(gmail.drafts["d1"], draft_id="d2")
    elif case == "stale":
        args["expected_digest"] = "0" * 64
    elif case == "sender":
        args["approved_sender"] = OLD
    elif case == "grant":
        args["request_id"] = "different"
    elif case == "future":
        service.clock = lambda: 99
    elif case == "expired":
        service.clock = lambda: 300
    elif case == "conflict":
        gmail.update_mode = "conflict"
    assert apply(service, **args) == {"status": "hold", "reason": reason}
    assert gmail.calls == 0


@pytest.mark.parametrize("mode,status", [
    ("normal", "verified"), ("timeout_after", "reconciled"),
    ("timeout_before", "hold"), ("bad_thread", "hold"),
])
def test_single_put_exact_readback_and_restart(setup, mode, status):
    service, gmail, path, cipher = setup
    gmail.update_mode = mode
    preview = service.set_draft_sender(**ARGS)
    assert preview["status"] == "preview"
    assert gmail.calls == 0 and service.journal.get() is None
    result = apply(service)
    assert result["status"] == status
    assert gmail.calls == 1
    assert RAW not in path.read_bytes()
    restarted = DraftCorrection(service.policy, gmail, DraftJournal(path, cipher), clock=lambda: 500)
    second = apply(restarted)
    assert second["status"] == ("reconciled" if status != "hold" else "hold")
    assert gmail.calls == 1
    if status != "hold":
        assert gmail.drafts["d1"].raw == rewrite_from(RAW, ACCOUNT)
        assert result["verification_receipt"]["current_message_id"] == "m2"
        assert restarted.inspect_draft()["digest"] == preview["after_digest"]


def test_separate_service_instances_admit_only_one_write(setup):
    service, gmail, path, cipher = setup
    other = DraftCorrection(service.policy, gmail, DraftJournal(path, cipher), clock=lambda: 200)
    results = []
    workers = [Thread(target=lambda owner=owner: results.append(apply(owner))) for owner in (service, other)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(5)
        assert not worker.is_alive()
    assert len(results) == 2 and gmail.calls == 1


def rpc(client, method, params=None, token=None, **kwargs):
    headers = {**ACCEPT, **kwargs.pop("headers", {})}
    if token:
        headers["Authorization"] = "Bearer " + token
    return client.post("/mcp", headers=headers, json={
        "jsonrpc": "2.0", "id": 1, "method": method, "params": params or {},
    }, **kwargs)


def call(client, name, arguments, token="read"):
    response = rpc(client, "tools/call", {"name": name, "arguments": arguments}, token)
    assert response.status_code == 200
    return response.json()["result"]


def test_http_discovery_privacy_and_route_denial(setup):
    service, gmail, _, _ = setup
    verifier = Verifier()
    app = build_app(service, verifier, issuer=ISSUER, resource_url=RESOURCE, port=8178)
    with TestClient(app, base_url=ORIGIN) as client:
        assert client.get("/health").json() == {"status": "ok"}
        assert rpc(client, "tools/list").status_code == 401
        assert rpc(client, "tools/list", token="revoked").status_code == 401
        assert rpc(client, "tools/list", token="read", headers={"Origin": "https://other.test"}).status_code == 403
        assert rpc(client, "tools/list", token="read", headers={"Host": "other.test"}).status_code == 400
        assert client.post("/mcp/", follow_redirects=False).status_code == 404
        assert client.post("/mcp?private=1").status_code == 400
        for path in ("/send", "/drafts", "/settings", "/shell"):
            assert client.post(path, follow_redirects=False).status_code == 404
        metadata = client.get("/.well-known/oauth-protected-resource/mcp").json()
        assert metadata["authorization_servers"] == [ISSUER]
        assert metadata["resource"] == RESOURCE
        assert client.get("/.well-known/oauth-protected-resource/v1/mcp/private-test").json() == metadata
        assert set(metadata["scopes_supported"]) == {DRAFT_READ_SCOPE, DRAFT_WRITE_SCOPE}
        init = rpc(client, "initialize", {"protocolVersion": "2025-11-25", "capabilities": {},
                   "clientInfo": {"name": "test", "version": "1"}}, "read")
        assert init.status_code == 200 and "Mcp-Session-Id" not in init.headers
        listing = rpc(client, "tools/list", token="read")
        assert listing.headers["Cache-Control"] == "no-store"
        tools = {tool["name"]: tool for tool in listing.json()["result"]["tools"]}
        assert set(tools) == {"inspect_draft", "set_draft_sender"}
        assert tools["inspect_draft"]["annotations"]["readOnlyHint"]
        assert tools["set_draft_sender"]["inputSchema"]["additionalProperties"] is False
        inspected = call(client, "inspect_draft", {})
        assert inspected["structuredContent"]["digest"] == DIGEST
        assert "Private synthetic marker" not in str(inspected)
        assert call(client, "set_draft_sender", ARGS)["structuredContent"]["status"] == "preview"
        write = call(client, "set_draft_sender", {**ARGS, "dry_run": False})
        assert write["structuredContent"]["reason"] == "write_scope_required"
        for name in ("send_email", "delete_draft", "change_settings"):
            assert call(client, name, {})["isError"]
        for args in ({**ARGS, "dry_run": "private-sentinel"}, {**ARGS, "private-sentinel": True}):
            rejected = call(client, "set_draft_sender", args, token="write")
            assert rejected["isError"] and "private-sentinel" not in str(rejected)
        assert gmail.calls == 0


def test_http_rechecks_revocation_before_write(setup):
    service, gmail, _, _ = setup
    verifier = Verifier()
    verifier.revoke_at = 2
    app = build_app(service, verifier, issuer=ISSUER, resource_url=RESOURCE, port=8178)
    with TestClient(app, base_url=ORIGIN) as client:
        response = call(client, "set_draft_sender", {**ARGS, "dry_run": False}, token="write")
        assert response["structuredContent"]["reason"] == "write_authorization_expired"
        assert gmail.calls == 0 and service.journal.get() is None
        response = call(client, "set_draft_sender", {**ARGS, "dry_run": False}, token="write")
        assert response["structuredContent"]["status"] == "verified"
        assert gmail.calls == 1



def test_read_only_holo_surface_unchanged():
    from modules.infrastructure.foundups_mcp_bridge.src.mcp_server import REMOTE_READ_ONLY_ALLOWLIST

    assert REMOTE_READ_ONLY_ALLOWLIST == ("holo_query_bundle",)
