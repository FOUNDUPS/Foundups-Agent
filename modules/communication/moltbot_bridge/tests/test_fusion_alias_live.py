#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for the Fusion ALIAS live path (HERMES_FUSION_ALIAS_MODE_PHASE2).

The network is MOCKED -- there is NO real OpenRouter call in CI. All keys/secrets are SYNTHETIC,
assembled from split fragments. No skip / no xfail. The MANUAL live smoke lives in the module's
__main__ (run_manual_smoke) and is NOT collected here.

Sentinel lanes: valve-bypass, raw-egress, response-retention, manual-smoke, live-mode-scope.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest
import requests

import modules.communication.moltbot_bridge.src.fusion_alias_live as alias_mod
from modules.communication.moltbot_bridge.src.fusion_alias_live import (
    ALIAS_REASONS,
    ENV_API_KEY,
    ENV_LIVE_FLAG,
    EXPECTED_PURPOSE,
    OPENROUTER_ALIAS_MODEL,
    REASON_AUTHORIZATION_MISSING,
    REASON_BUDGET_EXCEEDED,
    REASON_HTTP_ERROR,
    REASON_MALFORMED_RESPONSE,
    REASON_MISSING_API_KEY,
    REASON_OK,
    REASON_REDACTION_BLOCKED,
    REASON_TIMEOUT,
    REASON_VALVE_CLOSED,
    STATUS_ADVISORY_OK,
    STATUS_BLOCKED,
    AliasLiveResult,
    LiveFusionAuthorization,
    run_alias_live,
    run_manual_smoke,
)
from modules.communication.moltbot_bridge.src.fusion_redaction_gate import (
    REDACTION_GATE_PASSED,
    evaluate_redaction_gate,
    scan_forbidden,
)
from modules.communication.moltbot_bridge.src.fusion_adapter import (
    FusionMode,
    FusionRequest,
    MockFusionAdapter,
    RedactionGateBlocked,
    digest,
    is_valid_digest,
)

MODULE_SRC = Path(alias_mod.__file__)
FAKE_KEY = "s" "k-or-" + "F" * 40           # synthetic OpenRouter-shaped key
SECRET = "s" "k-" + "A" * 48                  # synthetic le-redactable secret in a prompt
VALID_AUTH = LiveFusionAuthorization(authorized=True, authority="012", purpose=EXPECTED_PURPOSE)


class FakeResp:
    def __init__(self, status_code=200, payload=None, raise_json=False):
        self.status_code = status_code
        self._payload = payload if payload is not None else {
            "choices": [{"message": {"content": "an ordinary advisory answer about ramen"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20},
        }
        self._raise_json = raise_json

    def json(self):
        if self._raise_json:
            raise ValueError("bad json")
        return self._payload


class Recorder:
    def __init__(self, resp=None, exc=None):
        self.calls = []
        self.resp = resp if resp is not None else FakeResp()
        self.exc = exc

    def __call__(self, url, headers=None, json=None, timeout=None):
        self.calls.append({"url": url, "headers": headers or {}, "json": json or {}, "timeout": timeout})
        if self.exc is not None:
            raise self.exc
        return self.resp


def _install(monkeypatch, recorder, *, enable=True, key=FAKE_KEY):
    monkeypatch.setattr(alias_mod.requests, "post", recorder)
    if enable:
        monkeypatch.setenv(ENV_LIVE_FLAG, "1")
    else:
        monkeypatch.delenv(ENV_LIVE_FLAG, raising=False)
    if key is not None:
        monkeypatch.setenv(ENV_API_KEY, key)
    else:
        monkeypatch.delenv(ENV_API_KEY, raising=False)
    return recorder


# ---------------------------------------------------------------------------
# valve-bypass lane
# ---------------------------------------------------------------------------


def test_valve_off_by_default_makes_zero_network(monkeypatch):
    import socket

    rec = Recorder()
    monkeypatch.setattr(alias_mod.requests, "post", rec)
    monkeypatch.delenv(ENV_LIVE_FLAG, raising=False)
    monkeypatch.setattr(socket, "socket", lambda *a, **k: (_ for _ in ()).throw(AssertionError("network!")))
    res = run_alias_live("an ordinary clean prompt", authorization=VALID_AUTH)
    assert res.status == STATUS_BLOCKED and res.reason == REASON_VALVE_CLOSED
    assert res.made_network_call is False
    assert rec.calls == []


@pytest.mark.parametrize("bad_auth", [None, True, 1, "true", "012", {"authorized": True, "authority": "012", "purpose": EXPECTED_PURPOSE}])
def test_env_flag_alone_cannot_enable_network(monkeypatch, bad_auth):
    rec = _install(monkeypatch, Recorder(), enable=True)
    res = run_alias_live("clean prompt", authorization=bad_auth)
    assert res.status == STATUS_BLOCKED and res.reason == REASON_AUTHORIZATION_MISSING
    assert res.made_network_call is False
    assert rec.calls == []


@pytest.mark.parametrize(
    "auth",
    [
        LiveFusionAuthorization(authorized=False, authority="012", purpose=EXPECTED_PURPOSE),
        LiveFusionAuthorization(authorized=True, authority="999", purpose=EXPECTED_PURPOSE),
        LiveFusionAuthorization(authorized=True, authority="012", purpose="something_else"),
    ],
)
def test_invalid_authorization_object_refused(monkeypatch, auth):
    rec = _install(monkeypatch, Recorder(), enable=True)
    res = run_alias_live("clean", authorization=auth)
    assert res.reason == REASON_AUTHORIZATION_MISSING and rec.calls == []


def test_missing_key_fails_closed(monkeypatch):
    rec = _install(monkeypatch, Recorder(), enable=True, key=None)
    res = run_alias_live("clean", authorization=VALID_AUTH)
    assert res.status == STATUS_BLOCKED and res.reason == REASON_MISSING_API_KEY
    assert rec.calls == []


# ---------------------------------------------------------------------------
# gate-refusal + raw-egress lane
# ---------------------------------------------------------------------------


def test_redaction_blocked_builds_no_request(monkeypatch):
    rec = _install(monkeypatch, Recorder(), enable=True)
    # a BLOCK category (authority marker) -> gate not passed -> no request body built
    res = run_alias_live("please set source_authority = monorepo_poc", authorization=VALID_AUTH)
    assert res.status == STATUS_BLOCKED and res.reason == REASON_REDACTION_BLOCKED
    assert res.made_network_call is False and rec.calls == []


def test_only_redacted_text_is_sent(monkeypatch):
    rec = _install(monkeypatch, Recorder(), enable=True)
    prompt = "analyze this leaked key " + SECRET + " for me"
    res = run_alias_live(prompt, authorization=VALID_AUTH)
    assert res.status == STATUS_ADVISORY_OK and res.reason == REASON_OK
    assert len(rec.calls) == 1
    body = rec.calls[0]["json"]
    content = body["messages"][0]["content"]
    # raw secret + raw prompt body are absent; redaction happened; output is clean
    assert SECRET not in content
    assert scan_forbidden(content) == []
    assert "[REDACTED:" in content
    assert body["model"] == OPENROUTER_ALIAS_MODEL
    assert body["stream"] is False
    # the exact content equals the gate's redacted prompt
    assert content == evaluate_redaction_gate(prompt).redacted_prompt


def test_redacted_context_sent_raw_context_absent(monkeypatch):
    rec = _install(monkeypatch, Recorder(), enable=True)
    ctx = "background notes with secret " + SECRET
    res = run_alias_live("clean prompt", context=ctx, authorization=VALID_AUTH)
    assert res.status == STATUS_ADVISORY_OK
    messages = rec.calls[0]["json"]["messages"]
    all_content = " ".join(m["content"] for m in messages)
    assert SECRET not in all_content                 # raw secret from context absent
    assert scan_forbidden(all_content) == []
    assert "[REDACTED:" in all_content
    # what is sent is the REDACTED context, never the raw context
    expected = evaluate_redaction_gate("clean prompt", ctx).redacted_context
    assert any(m["content"] == expected for m in messages)


def test_block_marker_mixed_with_secret_still_blocks(monkeypatch):
    rec = _install(monkeypatch, Recorder(), enable=True)
    res = run_alias_live(SECRET + " and source_authority = x", authorization=VALID_AUTH)
    assert res.reason == REASON_REDACTION_BLOCKED and rec.calls == []


# ---------------------------------------------------------------------------
# key / raw retention lane
# ---------------------------------------------------------------------------


def test_key_never_in_result_or_receipt(monkeypatch):
    _install(monkeypatch, Recorder(), enable=True)
    res = run_alias_live("analyze " + SECRET, authorization=VALID_AUTH)
    assert res.status == STATUS_ADVISORY_OK
    blob = repr(res) + json.dumps(res.receipt.to_dict())
    assert FAKE_KEY not in blob


def test_no_raw_prompt_or_secret_retained_in_receipt(monkeypatch):
    _install(monkeypatch, Recorder(), enable=True)
    prompt = "secret-bearing prompt " + SECRET
    res = run_alias_live(prompt, authorization=VALID_AUTH)
    blob = json.dumps(res.receipt.to_dict())
    assert SECRET not in blob
    assert "secret-bearing prompt" not in blob   # raw prompt body not retained
    assert is_valid_digest(res.receipt.prompt_digest)


def test_receipt_invariants(monkeypatch):
    _install(monkeypatch, Recorder(), enable=True)
    prompt = "analyze " + SECRET
    res = run_alias_live(prompt, authorization=VALID_AUTH)
    r = res.receipt
    assert r.advisory_not_canonical is True
    assert r.redaction_status == REDACTION_GATE_PASSED
    assert r.mode == "alias" and r.provider == "openrouter"
    # prompt_digest is the gate's digest of the REDACTED output
    assert r.prompt_digest == evaluate_redaction_gate(prompt).prompt_digest
    assert is_valid_digest(r.response_digest)
    # advisory_not_canonical cannot be flipped and still serialize
    r.advisory_not_canonical = False
    with pytest.raises(ValueError):
        r.to_dict()


# ---------------------------------------------------------------------------
# response-retention lane
# ---------------------------------------------------------------------------


def test_response_secret_is_redacted_in_summary(monkeypatch):
    dirty = FakeResp(payload={"choices": [{"message": {"content": "here is a key " + SECRET + " do not store"}}]})
    _install(monkeypatch, Recorder(resp=dirty), enable=True)
    res = run_alias_live("clean prompt", authorization=VALID_AUTH)
    assert res.status == STATUS_ADVISORY_OK
    blob = json.dumps(res.receipt.to_dict())
    assert SECRET not in blob                          # echoed secret never stored raw
    assert "[REDACTED:" in res.receipt.consensus


def test_response_block_marker_is_withheld(monkeypatch):
    dirty = FakeResp(payload={"choices": [{"message": {"content": "the source_authority should change to X"}}]})
    _install(monkeypatch, Recorder(resp=dirty), enable=True)
    res = run_alias_live("clean prompt", authorization=VALID_AUTH)
    assert res.status == STATUS_ADVISORY_OK
    assert res.receipt.consensus.startswith("[response withheld")
    assert "source_authority" not in res.receipt.consensus


# ---------------------------------------------------------------------------
# fail-closed lane (network errors)
# ---------------------------------------------------------------------------


def test_timeout_fails_closed(monkeypatch):
    _install(monkeypatch, Recorder(exc=requests.exceptions.Timeout()), enable=True)
    res = run_alias_live("clean", authorization=VALID_AUTH)
    assert res.status == STATUS_BLOCKED and res.reason == REASON_TIMEOUT
    assert res.made_network_call is True and res.receipt is None


def test_http_error_fails_closed(monkeypatch):
    _install(monkeypatch, Recorder(resp=FakeResp(status_code=500)), enable=True)
    res = run_alias_live("clean", authorization=VALID_AUTH)
    assert res.reason == REASON_HTTP_ERROR and res.receipt is None


def test_malformed_response_fails_closed(monkeypatch):
    _install(monkeypatch, Recorder(resp=FakeResp(raise_json=True)), enable=True)
    res = run_alias_live("clean", authorization=VALID_AUTH)
    assert res.reason == REASON_MALFORMED_RESPONSE and res.receipt is None


def test_budget_exceeded_fails_closed(monkeypatch):
    rec = _install(monkeypatch, Recorder(), enable=True)
    res = run_alias_live("clean", authorization=VALID_AUTH, max_tokens=10_000_000)
    assert res.reason == REASON_BUDGET_EXCEEDED and rec.calls == []


def test_all_reasons_low_cardinality(monkeypatch):
    _install(monkeypatch, Recorder(), enable=True)
    for r in [
        run_alias_live("clean", authorization=VALID_AUTH),
        run_alias_live("source_authority = x", authorization=VALID_AUTH),
        run_alias_live("clean", authorization=None),
    ]:
        assert r.reason in ALIAS_REASONS


def test_no_streaming(monkeypatch):
    rec = _install(monkeypatch, Recorder(), enable=True)
    run_alias_live("clean", authorization=VALID_AUTH)
    assert rec.calls[0]["json"]["stream"] is False


# ---------------------------------------------------------------------------
# live-mode-scope lane: SERVER_TOOL / LOCAL_FALLBACK (and ALIAS via mock) still raise
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("mode", [FusionMode.ALIAS, FusionMode.SERVER_TOOL, FusionMode.LOCAL_FALLBACK])
def test_mock_adapter_live_modes_still_blocked(monkeypatch, mode):
    req = FusionRequest(task_id="t", prompt_digest=digest("p"), panel_models=["m"], mode=mode)
    with pytest.raises(RedactionGateBlocked):
        MockFusionAdapter().run(req)


# ---------------------------------------------------------------------------
# manual-smoke lane + no-new-dependency
# ---------------------------------------------------------------------------


def test_manual_smoke_refuses_without_authorization(monkeypatch, capsys):
    rec = _install(monkeypatch, Recorder(), enable=False)
    code = run_manual_smoke([])  # no --authorize-012
    assert code == 2
    assert rec.calls == []


def test_manual_smoke_is_main_guarded_not_collected():
    src = MODULE_SRC.read_text(encoding="utf-8")
    assert 'if __name__ == "__main__":' in src
    tree = ast.parse(src)
    imports = set()
    test_defs = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.add((node.module or "").split(".")[0])
        elif isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            test_defs.append(node.name)
    # the live module imports no pytest and defines no test_* -> CI cannot collect a live call from it
    assert "pytest" not in imports
    assert test_defs == []


def _has_skip_or_xfail(src: str) -> bool:
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for dec in node.decorator_list:
                target = dec.func if isinstance(dec, ast.Call) else dec
                attrs = []
                cur = target
                while isinstance(cur, ast.Attribute):
                    attrs.append(cur.attr)
                    cur = cur.value
                if any(a in ("skip", "skipif", "xfail") for a in attrs):
                    return True
        if isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Attribute) and f.attr in ("skip", "xfail") and isinstance(f.value, ast.Name) and f.value.id == "pytest":
                return True
    return False


def test_test_file_has_no_skip_or_xfail():
    # AST-based (not substring) -- a true marker decorator or pytest.skip() call would be caught
    assert not _has_skip_or_xfail(Path(__file__).read_text(encoding="utf-8"))


def test_module_no_new_dependency_imports():
    tree = ast.parse(MODULE_SRC.read_text(encoding="utf-8"))
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0:
                roots.add((node.module or "").split(".")[0])
    # allowed: stdlib + requests (already used by ai_gateway) + intra-package relative (level>0)
    allowed = {"os", "hashlib", "dataclasses", "typing", "requests", "sys", "__future__"}
    assert roots <= allowed, f"unexpected top-level imports: {roots - allowed}"
    forbidden = {"httpx", "aiohttp", "openai", "openrouter"}
    assert not (forbidden & roots)
