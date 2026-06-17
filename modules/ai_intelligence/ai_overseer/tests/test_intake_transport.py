#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the framework-agnostic intake ADAPTER (Phase 3 transport).

The adapter turns a transport-neutral request (headers + cookies + body) into a DRAFT
FoundUpGenesisEnvelope or a SAFE rejection. These tests prove, deterministically:

  - Token strings are extracted ONLY from transport metadata (headers/cookies), NEVER the
    body (a body session_token/invite_token/authenticated field can never authenticate).
  - The pipeline is STRICTLY ordered: size gate -> body parse/validate -> token extract ->
    build_intake_context EXACTLY ONCE -> validate_launch_request -> to_genesis_envelope.
  - An invalid / oversize / non-object / auth-field body is rejected PRE-PROVIDER with ZERO
    provider calls, so a single-use invite is NOT consumed (proven against a real nonce
    store: the nonce remains usable afterward).
  - Header/cookie precedence + ambiguity (Addendum A), body parsing/allowlist (B), generic
    non-oracle reasons (C), provider-exactly-once-after-gates (D), token values are NOT
    normalized (E).
  - The 5 independent SENTINEL lanes: transport-extraction, body-boundary, auth-oracle/
    leakage, pipeline-integrity, scope/architecture (AST: no web/network/subprocess; only
    sibling intake modules + stdlib).

Valid tokens are forged with the #821 TEST-ONLY signers (_make_session_token /
_make_invite_token) using an explicit secret injected via secret_provider= (no os.environ
mutation). No skip/xfail.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from modules.ai_intelligence.ai_overseer.src.foundup_genesis.intake_transport import (
    intake_request,
    IntakeResult,
    SURFACE_BINDING_SLICE,
    ENTITLEMENT_SLICE,
)
from modules.ai_intelligence.ai_overseer.src.foundup_genesis import (
    intake_transport as _mod,
)
from modules.ai_intelligence.ai_overseer.src.foundup_genesis.intake_auth_provider import (
    _make_session_token,
    _make_invite_token,
    build_intake_context,
    InMemoryNonceStore,
    SQLiteNonceStore,
)
from modules.ai_intelligence.ai_overseer.src.foundup_genesis import (
    intake_request as _intake_request_from_pkg,
    IntakeResult as _IntakeResult_from_pkg,
)

MODULE_SRC = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "foundup_genesis"
    / "intake_transport.py"
)

_SECRET = "test-transport-secret-AAAA"
_OTHER_SECRET = "unrelated-secret-ZZZZ"


def _provider(current=_SECRET, previous=None):
    """A secret_provider that never touches os.environ (Addendum E test seam)."""
    return lambda: (current, previous)


def _now() -> int:
    return 1_000_000


def _iat() -> int:
    return _now() - 10


def _future() -> int:
    return _now() + 1800  # within both #821 TTL caps


def _past() -> int:
    return _now() - 3600


def _session_token(secret=_SECRET, subject="alice", iat=None, exp=None) -> str:
    return _make_session_token(
        secret, subject, iat if iat is not None else _iat(), exp if exp is not None else _future()
    )


def _invite_token(secret=_SECRET, handle="bob", nonce="nonce-1", iat=None, exp=None) -> str:
    return _make_invite_token(
        secret, handle, nonce, iat if iat is not None else _iat(),
        exp if exp is not None else _future(),
    )


def _clean_body_dict() -> dict:
    return {
        "proposed_name": "Get Kei Truck Marketplace",
        "problem_statement": "Help people buy and sell used Kei trucks safely.",
        "intended_users": "scouts, buyers, sellers",
        "category": "marketplace",
        "reference_urls": ["https://example.com/kei-trucks"],
        "requested_type": "marketplace",
    }


def _clean_body_bytes() -> bytes:
    return json.dumps(_clean_body_dict()).encode("utf-8")


def _call(headers=None, body=None, **kw):
    """intake_request with sane defaults: clean body, injected test secret, fixed now."""
    if headers is None:
        headers = {}
    if body is None:
        body = _clean_body_bytes()
    kw.setdefault("secret_provider", _provider())
    kw.setdefault("now", _now())
    return intake_request(headers, body, **kw)


class SpyProvider:
    """Counts provider calls and records args, delegating to the real verifier (Addendum D)."""

    def __init__(self):
        self.calls = []

    def __call__(self, session_token, invite_token, **kw):
        self.calls.append((session_token, invite_token, kw))
        return build_intake_context(session_token, invite_token, **kw)


# ===========================================================================
# POSITIVES
# ===========================================================================


def test_header_session_creates_draft_envelope():
    r = _call(headers={"Authorization": f"Bearer {_session_token()}"})
    assert r.status == "created"
    assert r.reason == "created"
    assert r.http_status == 201
    assert isinstance(r.envelope, dict)
    # requested_by is the VERIFIED handle from the context, never a body field.
    assert r.envelope["requested_by"] == "alice"
    # Draft invariants from #810.
    assert r.envelope["external_repo_requested"] is False
    assert r.envelope["lifecycle_stage"] == "idea"


def test_header_invite_creates_draft_and_is_single_use():
    store = InMemoryNonceStore()
    tok = _invite_token(nonce="single-use-1")
    r1 = intake_request(
        {"X-FoundUp-Invite": tok}, _clean_body_bytes(),
        nonce_store=store, now=_now(), secret_provider=_provider(),
    )
    assert r1.status == "created"
    assert r1.envelope["requested_by"] == "bob"
    # Second identical request replays the SAME nonce -> rejected (single-use across requests).
    r2 = intake_request(
        {"X-FoundUp-Invite": tok}, _clean_body_bytes(),
        nonce_store=store, now=_now(), secret_provider=_provider(),
    )
    assert r2.status == "rejected"
    assert r2.reason == "not_authorized"


def test_both_session_and_invite_present_creates_draft():
    store = InMemoryNonceStore()
    r = intake_request(
        {
            "Authorization": f"Bearer {_session_token(subject='carol')}",
            "X-FoundUp-Invite": _invite_token(handle="dave", nonce="n-both"),
        },
        _clean_body_bytes(),
        nonce_store=store, now=_now(), secret_provider=_provider(),
    )
    assert r.status == "created"
    # Session handle is preferred when both verify (matches #821 handle precedence).
    assert r.envelope["requested_by"] == "carol"


def test_clean_body_maps_to_proposal_fields():
    r = _call(headers={"Authorization": f"Bearer {_session_token()}"})
    assert r.status == "created"
    env = r.envelope
    assert env["name"] == "Get Kei Truck Marketplace"
    assert env["category"] == "marketplace"
    assert "Kei trucks" in env["description"]


def test_envelope_requested_by_is_verified_handle_not_body_requester_handle():
    body = _clean_body_dict()
    body["requester_handle"] = "attacker_claimed_handle"
    r = _call(headers={"Authorization": f"Bearer {_session_token(subject='real_user')}"}, body=json.dumps(body).encode("utf-8"))
    assert r.status == "created"
    assert r.envelope["requested_by"] == "real_user"
    assert r.envelope["requested_by"] != "attacker_claimed_handle"


def test_str_body_accepted():
    r = _call(headers={"Authorization": f"Bearer {_session_token()}"}, body=json.dumps(_clean_body_dict()))
    assert r.status == "created"


def test_mapping_body_accepted_and_not_mutated():
    body = _clean_body_dict()
    snapshot = dict(body)
    r = _call(headers={"Authorization": f"Bearer {_session_token()}"}, body=body)
    assert r.status == "created"
    # Mapping body copied into a fresh dict -> no mutable side effects on caller (Addendum B).
    assert body == snapshot


# ===========================================================================
# ADDENDUM A -- HEADER/COOKIE PRECEDENCE + AMBIGUITY
# ===========================================================================


def test_authorization_value_used_when_no_session_cookie():
    # Authorization present, no session cookie -> the HEADER token's handle is used.
    r = _call(headers={"Authorization": f"Bearer {_session_token(subject='hdr_user')}"})
    assert r.status == "created"
    assert r.envelope["requested_by"] == "hdr_user"


def test_authorization_value_used_when_cookie_matches():
    # Header + identical cookie (not a mismatch) -> header value is used; cookie does not veto.
    tok = _session_token(subject="hdr_user")
    r = _call(
        headers={"Authorization": f"Bearer {tok}"},
        cookies={"foundup_session": tok},
    )
    assert r.status == "created"
    assert r.envelope["requested_by"] == "hdr_user"


def test_session_cookie_used_only_when_authorization_absent():
    r = _call(cookies={"foundup_session": _session_token(subject="cookie_user")})
    assert r.status == "created"
    assert r.envelope["requested_by"] == "cookie_user"


def test_malformed_authorization_does_not_fall_back_to_cookie():
    # Authorization present but malformed -> session mechanism rejected; cookie NOT used.
    r = _call(
        headers={"Authorization": "Basic abc123"},
        cookies={"foundup_session": _session_token(subject="cookie_user")},
    )
    assert r.status == "rejected"
    assert r.reason == "not_authorized"


def test_multiple_bearer_tokens_rejected():
    two = f"Bearer {_session_token()}, Bearer {_session_token(subject='second')}"
    r = _call(headers={"Authorization": two})
    assert r.status == "rejected"
    assert r.reason == "not_authorized"


def test_session_header_cookie_mismatch_rejected():
    r = _call(
        headers={"Authorization": f"Bearer {_session_token(subject='a')}"},
        cookies={"foundup_session": _session_token(subject="b")},
    )
    # Header + cookie both present and DIFFER -> session mechanism rejected.
    assert r.status == "rejected"
    assert r.reason == "not_authorized"


def test_invite_header_cookie_mismatch_rejected():
    store = InMemoryNonceStore()
    r = intake_request(
        {"X-FoundUp-Invite": _invite_token(nonce="hdr")},
        _clean_body_bytes(),
        cookies={"foundup_invite": _invite_token(nonce="cookie")},
        nonce_store=store, now=_now(), secret_provider=_provider(),
    )
    assert r.status == "rejected"
    assert r.reason == "not_authorized"


def test_invite_header_takes_precedence_over_cookie():
    store = InMemoryNonceStore()
    tok = _invite_token(nonce="hdr-precedence")
    r = intake_request(
        {"X-FoundUp-Invite": tok},
        _clean_body_bytes(),
        cookies={"foundup_invite": tok},  # same value -> not a mismatch
        nonce_store=store, now=_now(), secret_provider=_provider(),
    )
    assert r.status == "created"


def test_lowercase_and_uppercase_header_names_both_work():
    for name in ("authorization", "AUTHORIZATION", "Authorization", "AuThOrIzAtIoN"):
        r = _call(headers={name: f"Bearer {_session_token()}"})
        assert r.status == "created", name


def test_duplicate_case_colliding_headers_rejected():
    # Two keys folding to the same lowercased name -> collision -> invalid_request.
    headers = {"Authorization": f"Bearer {_session_token()}", "authorization": "Bearer x"}
    r = _call(headers=headers)
    assert r.status == "rejected"
    assert r.reason == "invalid_request"


def test_duplicate_case_colliding_cookies_rejected():
    cookies = {"foundup_session": _session_token(), "FOUNDUP_SESSION": "x"}
    r = _call(cookies=cookies)
    assert r.status == "rejected"
    assert r.reason == "invalid_request"


# ===========================================================================
# ADDENDUM B -- BODY PARSING / FIELD ALLOWLIST
# ===========================================================================


def test_array_body_rejected_pre_provider():
    spy = SpyProvider()
    r = _call(headers={"Authorization": f"Bearer {_session_token()}"}, body=b"[1,2,3]", _provider=spy)
    assert r.status == "rejected"
    assert r.reason == "invalid_request"
    assert spy.calls == []  # zero provider calls


@pytest.mark.parametrize("raw", [b'"a string"', b"123", b"true", b"null"])
def test_non_object_json_rejected(raw):
    r = _call(headers={"Authorization": f"Bearer {_session_token()}"}, body=raw)
    assert r.status == "rejected"
    assert r.reason == "invalid_request"


def test_unknown_field_rejected_not_dropped():
    body = _clean_body_dict()
    body["surprise_field"] = "value"
    r = _call(headers={"Authorization": f"Bearer {_session_token()}"}, body=json.dumps(body).encode("utf-8"))
    assert r.status == "rejected"
    assert r.reason == "invalid_request"


@pytest.mark.parametrize("field", ["authenticated", "invite_token_verified", "role", "authorized", "admin"])
def test_auth_ish_body_field_rejected(field):
    body = _clean_body_dict()
    body[field] = True
    r = _call(headers={"Authorization": f"Bearer {_session_token()}"}, body=json.dumps(body).encode("utf-8"))
    assert r.status == "rejected"
    assert r.reason == "invalid_request"


def test_invalid_utf8_body_rejected():
    r = _call(headers={"Authorization": f"Bearer {_session_token()}"}, body=b"\xff\xfe\x00bad")
    assert r.status == "rejected"
    assert r.reason == "invalid_request"


def test_oversize_body_rejected_before_parse():
    spy = SpyProvider()
    big = b"{" + b"x" * 50_000 + b"}"  # > default 16 KiB; also not valid JSON
    r = _call(headers={"Authorization": f"Bearer {_session_token()}"}, body=big, _provider=spy, max_body_bytes=16 * 1024)
    assert r.status == "rejected"
    assert r.reason == "invalid_request"
    assert spy.calls == []  # rejected BEFORE any parse AND before the provider


def test_missing_proposed_name_rejected():
    body = _clean_body_dict()
    del body["proposed_name"]
    r = _call(headers={"Authorization": f"Bearer {_session_token()}"}, body=json.dumps(body).encode("utf-8"))
    assert r.status == "rejected"
    assert r.reason == "invalid_request"


def test_malformed_json_rejected_pre_provider():
    spy = SpyProvider()
    r = _call(headers={"Authorization": f"Bearer {_session_token()}"}, body=b"{not json", _provider=spy)
    assert r.status == "rejected"
    assert r.reason == "invalid_request"
    assert spy.calls == []


# ===========================================================================
# ADDENDUM C -- RESULT IS NOT A SECRET SIDE CHANNEL (no auth oracle / no leak)
# ===========================================================================


def _auth_failure_cases():
    """A family of DIFFERENT auth failures that must ALL map to the same generic reason."""
    forged = _session_token(secret=_OTHER_SECRET)  # signed by wrong secret
    expired = _session_token(exp=_now() - 1, iat=_now() - 100)  # expired
    malformed = "sess.v1.not-a-real-token"
    return {
        "missing": {},
        "forged": {"Authorization": f"Bearer {forged}"},
        "expired": {"Authorization": f"Bearer {expired}"},
        "malformed": {"Authorization": f"Bearer {malformed}"},
    }


def test_all_auth_failures_share_one_generic_reason():
    reasons = set()
    for name, headers in _auth_failure_cases().items():
        r = _call(headers=headers)
        assert r.status == "rejected", name
        reasons.add(r.reason)
    # Forged / expired / malformed / missing are INDISTINGUISHABLE -> one reason.
    assert reasons == {"not_authorized"}


def test_replayed_invite_indistinguishable_from_other_auth_failures():
    store = InMemoryNonceStore()
    tok = _invite_token(nonce="replay-1")
    intake_request({"X-FoundUp-Invite": tok}, _clean_body_bytes(), nonce_store=store, now=_now(), secret_provider=_provider())
    r = intake_request({"X-FoundUp-Invite": tok}, _clean_body_bytes(), nonce_store=store, now=_now(), secret_provider=_provider())
    assert r.reason == "not_authorized"


def test_no_token_substring_in_result():
    tok = _session_token(secret=_OTHER_SECRET, subject="leaky_subject")
    r = _call(headers={"Authorization": f"Bearer {tok}"})
    blob = repr(r) + "|" + r.reason + "|" + json.dumps({"s": r.status, "r": r.reason, "h": r.http_status})
    assert tok not in blob
    assert "leaky_subject" not in blob
    assert "Bearer" not in r.reason


def test_reason_is_low_cardinality_enum():
    # Every reason the adapter can emit is one of exactly three strings.
    allowed = {"created", "invalid_request", "not_authorized"}
    samples = [
        _call(headers={"Authorization": f"Bearer {_session_token()}"}),          # created
        _call(headers={"Authorization": f"Bearer {_session_token()}"}, body=b"[]"),  # invalid_request
        _call(headers={}),                                                        # not_authorized
    ]
    assert {s.reason for s in samples} <= allowed


# ===========================================================================
# ADDENDUM D -- PROVIDER CALLED EXACTLY ONCE, ONLY AFTER BODY GATES
# ===========================================================================


def test_provider_called_exactly_once_on_valid_request():
    spy = SpyProvider()
    r = _call(headers={"Authorization": f"Bearer {_session_token()}"}, _provider=spy)
    assert r.status == "created"
    assert len(spy.calls) == 1


def test_provider_zero_calls_on_oversize_body():
    spy = SpyProvider()
    r = _call(headers={"Authorization": f"Bearer {_session_token()}"}, body=b"x" * 50_000, _provider=spy)
    assert r.status == "rejected"
    assert spy.calls == []


def test_provider_zero_calls_on_malformed_json():
    spy = SpyProvider()
    r = _call(headers={"Authorization": f"Bearer {_session_token()}"}, body=b"{bad", _provider=spy)
    assert spy.calls == []


def test_invalid_body_does_not_consume_invite_nonce():
    """An invalid body with a VALID invite token must NOT consume the single-use invite.

    Proven against a real nonce store: after the invalid-body request, the SAME nonce is
    still usable by a later valid request (so the provider was never called for it).
    """
    store = InMemoryNonceStore()
    tok = _invite_token(nonce="not-consumed-by-bad-body")
    spy = SpyProvider()

    # Invalid body (unknown field) + valid invite token.
    bad = _clean_body_dict()
    bad["surprise"] = 1
    r_bad = intake_request(
        {"X-FoundUp-Invite": tok}, json.dumps(bad).encode("utf-8"),
        nonce_store=store, now=_now(), secret_provider=_provider(), _provider=spy,
    )
    assert r_bad.status == "rejected"
    assert r_bad.reason == "invalid_request"
    assert spy.calls == []  # provider never called -> nonce never consumed

    # The nonce is STILL usable: a later valid request with the same token succeeds.
    r_good = intake_request(
        {"X-FoundUp-Invite": tok}, _clean_body_bytes(),
        nonce_store=store, now=_now(), secret_provider=_provider(),
    )
    assert r_good.status == "created"
    assert r_good.envelope["requested_by"] == "bob"


def test_provider_receives_clean_strings_never_body():
    spy = SpyProvider()
    body = _clean_body_dict()
    body["requester_handle"] = "body_handle"  # allowed field, but never a token source
    _call(headers={"Authorization": f"Bearer {_session_token()}"}, body=json.dumps(body).encode("utf-8"), _provider=spy)
    assert len(spy.calls) == 1
    session_arg, invite_arg, _kw = spy.calls[0]
    # The session arg is the extracted header token; invite is None; neither is from the body.
    assert isinstance(session_arg, str) and session_arg.startswith("sess.v1.")
    assert invite_arg is None
    assert "body_handle" not in (session_arg or "")


# ===========================================================================
# ADDENDUM E -- DO NOT NORMALIZE TOKEN VALUES
# ===========================================================================


@pytest.mark.parametrize("bad", [
    "sess.v1.abc\r\ndef",   # CR/LF
    "sess.v1.abc\ndef",      # LF
    "sess.v1.abc def",       # internal space
    "sess.v1.abc,def",       # comma
    "sess.v1.abc\tdef",      # tab (control)
])
def test_session_token_with_illegal_chars_rejected(bad):
    r = _call(headers={"Authorization": f"Bearer {bad}"})
    assert r.status == "rejected"
    assert r.reason == "not_authorized"


def test_fullwidth_prefix_not_normalized_into_valid_kindver():
    # A fullwidth-lookalike 'sess.v1' must NOT be NFKC-normalized into the real prefix.
    # Built from \\uXXXX escapes so this source file stays pure ASCII (byte-check clean).
    fake = "\uff53\uff45\uff53\uff53.v1.payload.sig"  # fullwidth s e s s lookalike
    r = _call(headers={"Authorization": f"Bearer {fake}"})
    assert r.status == "rejected"
    assert r.reason == "not_authorized"


def test_token_value_preserved_byte_for_byte_to_provider():
    """The exact token string (outer-trim only) is what reaches #821 -- not lowercased,
    not NFKC-normalized, not inner-stripped."""
    spy = SpyProvider()
    tok = _session_token(subject="MixedCaseSubject")
    # Surround with external whitespace; only that outer whitespace may be trimmed.
    _call(headers={"Authorization": f"Bearer  {tok}  "}, _provider=spy)
    assert len(spy.calls) == 1
    session_arg = spy.calls[0][0]
    assert session_arg == tok  # equal after boundary-trim only; value unchanged


def test_invite_token_with_comma_rejected():
    store = InMemoryNonceStore()
    r = intake_request(
        {"X-FoundUp-Invite": "invite.v1.abc,def"},
        _clean_body_bytes(), nonce_store=store, now=_now(), secret_provider=_provider(),
    )
    assert r.status == "rejected"
    assert r.reason == "not_authorized"


# ===========================================================================
# GENERAL SECURITY -- tokens never from body; confused deputy; fail closed
# ===========================================================================


def test_body_session_token_field_cannot_authenticate():
    # A body field literally named session_token must NOT authenticate (and is rejected as
    # a forbidden/unknown field pre-provider).
    body = _clean_body_dict()
    body["session_token"] = _session_token()
    r = _call(body=json.dumps(body).encode("utf-8"))  # no auth header
    assert r.status == "rejected"
    assert r.reason == "invalid_request"  # unknown field -> body gate, pre-provider


def test_relayed_already_authenticated_header_is_not_trusted():
    # A confused-deputy relayed assertion header must not authenticate; only sess.v1/invite.v1
    # tokens via the canonical headers/cookies do.
    r = _call(headers={"X-Authenticated": "true", "X-On-Behalf-Of": "admin"})
    assert r.status == "rejected"
    assert r.reason == "not_authorized"


def test_no_token_at_all_is_not_authorized():
    r = _call(headers={}, cookies={})
    assert r.status == "rejected"
    assert r.reason == "not_authorized"
    assert r.envelope is None


def test_no_secret_configured_fails_closed():
    # Empty current secret -> #821 fails closed -> not_authorized (no envelope).
    r = intake_request(
        {"Authorization": f"Bearer {_session_token()}"}, _clean_body_bytes(),
        now=_now(), secret_provider=lambda: ("", None),
    )
    assert r.status == "rejected"
    assert r.reason == "not_authorized"
    assert r.envelope is None


def test_package_reexports_public_surface():
    assert _intake_request_from_pkg is intake_request
    assert _IntakeResult_from_pkg is IntakeResult


def test_named_followup_slices_present():
    assert SURFACE_BINDING_SLICE == "FOUNDUP_LAUNCH_REQUEST_INTAKE_SURFACE_BINDING_PHASE3C"
    assert ENTITLEMENT_SLICE == "FOUNDUP_LAUNCH_REQUEST_ENTITLEMENT_PHASE3B"


# ===========================================================================
# SENTINEL LANE 4 -- PIPELINE INTEGRITY (ordering proven by spy timing)
# ===========================================================================


def test_pipeline_size_gate_precedes_everything():
    # Oversize + invalid-token body: size gate fires first -> invalid_request (NOT
    # not_authorized), proving the body gate runs before token/auth concerns.
    spy = SpyProvider()
    r = _call(headers={}, body=b"x" * 50_000, _provider=spy)
    assert r.reason == "invalid_request"
    assert spy.calls == []


def test_body_gate_precedes_auth_gate():
    # Invalid body + NO auth: body failure wins -> invalid_request, not not_authorized.
    spy = SpyProvider()
    r = _call(headers={}, body=b"[]", _provider=spy)
    assert r.reason == "invalid_request"
    assert spy.calls == []


def test_auth_gate_runs_only_after_valid_body():
    # Valid body + bad auth -> provider IS called once, result is not_authorized (post gate).
    spy = SpyProvider()
    r = _call(headers={}, _provider=spy)  # valid body, no token
    assert len(spy.calls) == 1
    assert r.reason == "not_authorized"


# ===========================================================================
# SENTINEL LANE 5 -- SCOPE / ARCHITECTURE (static AST sweep)
# ===========================================================================


def _module_ast():
    return ast.parse(MODULE_SRC.read_text(encoding="utf-8"))


def test_module_imports_no_web_framework_network_or_subprocess():
    tree = _module_ast()
    mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                mods.add(a.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                mods.add(node.module)
    banned_roots = {
        "fastapi", "flask", "starlette", "django", "aiohttp", "tornado",
        "uvicorn", "werkzeug", "sanic", "bottle",
        "socket", "ssl", "urllib", "requests", "httpx", "http",
        "subprocess", "multiprocessing", "ctypes", "sys",
        "pickle", "marshal", "shutil", "pathlib", "importlib", "dotenv",
    }
    bad = {m for m in mods if m.split(".")[0] in banned_roots}
    assert not bad, f"banned import: {bad}"


def test_module_imports_only_sibling_intake_modules_and_stdlib():
    tree = _module_ast()
    project_imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            # Relative imports (level>0) inside the package are the ONLY project imports
            # allowed, and only the two sibling intake modules.
            if node.level and node.level > 0:
                project_imports.append(mod)
            elif "modules." in mod or "holo_index" in mod:
                project_imports.append(mod)
        elif isinstance(node, ast.Import):
            for a in node.names:
                if a.name.startswith("modules.") or a.name.startswith("holo_index"):
                    project_imports.append(a.name)
    allowed_siblings = {"intake_auth_provider", "launch_request"}
    for mod in project_imports:
        assert mod in allowed_siblings, f"unexpected project import: {mod!r}"


def test_module_makes_no_exec_process_or_network_calls():
    tree = _module_ast()
    banned_names = {"eval", "exec", "compile", "__import__", "input", "open"}
    banned_attrs = {
        "system", "popen", "Popen", "run", "call", "check_call", "check_output",
        "urlopen", "connect", "spawn", "fork", "remove", "unlink",
        "write_text", "write_bytes", "load_dotenv", "print", "getenv",
    }
    name_bad, attr_bad = [], []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Name) and f.id in banned_names:
                name_bad.append(f.id)
            elif isinstance(f, ast.Attribute) and f.attr in banned_attrs:
                attr_bad.append(f.attr)
    assert not name_bad, f"banned builtin calls: {name_bad}"
    assert not attr_bad, f"banned attr calls: {attr_bad}"


def test_module_has_no_logging_or_print():
    tree = _module_ast()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id != "print"
        if isinstance(node, ast.Import):
            for a in node.names:
                assert a.name != "logging"
        if isinstance(node, ast.ImportFrom):
            assert node.module != "logging"


def test_public_surface_minimal():
    # Only the intended public names are exported (no internal extraction helpers).
    assert set(_mod.__all__) == {
        "intake_request", "IntakeResult", "SURFACE_BINDING_SLICE", "ENTITLEMENT_SLICE",
    }


# ===========================================================================
# SENTINEL FINDING 1 (HIGH) -- PRE-PROVIDER GATE IS A COMPLETE PAYLOAD SUPERSET:
# NO payload defect may reach the provider and burn a single-use invite. The pre-gate
# omitted reference_urls validation, so a bad reference_urls slipped past pre-provider, the
# provider was called once (nonce CONSUMED), and validate THEN rejected -> invite burned.
# Each test below asserts (a) rejected/invalid_request, (b) ZERO provider calls, and (c) the
# real invite nonce is STILL USABLE afterward. These FAIL on the old pre-gate (reference_urls
# class) and PASS after the fix.
# ===========================================================================


# Every payload-defect class: bad reference_urls (all 6 variants) + unknown field + auth-ish
# field + missing/empty name. \uXXXX escapes keep this source pure ASCII.
_PAYLOAD_DEFECTS = {
    # --- bad reference_urls, all 6 variants (the class the old pre-gate MISSED) ---
    "refurl_file_scheme": ("reference_urls", ["file:///etc/passwd"]),
    "refurl_local_path": ("reference_urls", ["/etc/passwd"]),
    "refurl_shell_metachar": ("reference_urls", ["https://x.com/$(rm -rf /)"]),
    "refurl_non_string": ("reference_urls", [123]),
    "refurl_empty": ("reference_urls", [""]),
    "refurl_non_ascii": ("reference_urls", ["https://x.com/caf\u00e9"]),
    # --- other payload-defect classes (already covered, re-asserted for the invariant) ---
    "unknown_field": ("surprise_field", "value"),
    "auth_ish_field": ("authenticated", True),
}


@pytest.mark.parametrize("label", sorted(_PAYLOAD_DEFECTS))
def test_payload_defect_rejected_pre_provider_and_invite_not_burned(label):
    field, value = _PAYLOAD_DEFECTS[label]
    store = InMemoryNonceStore()
    spy = SpyProvider()
    nonce = f"finding1-{label}"
    tok = _invite_token(nonce=nonce)

    bad = _clean_body_dict()
    bad[field] = value
    r_bad = intake_request(
        {"X-FoundUp-Invite": tok}, json.dumps(bad).encode("utf-8"),
        nonce_store=store, now=_now(), secret_provider=_provider(), _provider=spy,
    )
    # (a) rejected as a body-shape failure (NOT an auth oracle).
    assert r_bad.status == "rejected", label
    assert r_bad.reason == "invalid_request", label
    # (b) the provider was NEVER called -> the invite nonce was never even seen.
    assert spy.calls == [], label

    # (c) the SAME invite nonce is STILL usable -- a later VALID request with it succeeds.
    r_good = intake_request(
        {"X-FoundUp-Invite": tok}, _clean_body_bytes(),
        nonce_store=store, now=_now(), secret_provider=_provider(),
    )
    assert r_good.status == "created", label
    assert r_good.envelope["requested_by"] == "bob", label


def test_missing_name_payload_defect_does_not_burn_invite():
    # Missing proposed_name is a payload defect too -> pre-provider reject, nonce preserved.
    store = InMemoryNonceStore()
    spy = SpyProvider()
    tok = _invite_token(nonce="finding1-missing-name")
    bad = _clean_body_dict()
    del bad["proposed_name"]
    r_bad = intake_request(
        {"X-FoundUp-Invite": tok}, json.dumps(bad).encode("utf-8"),
        nonce_store=store, now=_now(), secret_provider=_provider(), _provider=spy,
    )
    assert r_bad.status == "rejected"
    assert r_bad.reason == "invalid_request"
    assert spy.calls == []
    r_good = intake_request(
        {"X-FoundUp-Invite": tok}, _clean_body_bytes(),
        nonce_store=store, now=_now(), secret_provider=_provider(),
    )
    assert r_good.status == "created"


def test_bad_reference_urls_is_the_high_finding_regression():
    """Focused HIGH-finding regression: a proposal whose ONLY defect is a bad reference_urls
    entry must be rejected PRE-provider with the invite intact. This is the exact case the old
    pre-gate missed (it ran reference_urls validation only POST-provider, after the nonce was
    consumed). FAILS on the old code; PASSES after the fix."""
    store = SQLiteNonceStore()  # a REAL durable nonce store
    try:
        spy = SpyProvider()
        tok = _invite_token(nonce="high-finding-refurl")
        bad = _clean_body_dict()
        bad["reference_urls"] = ["file:///etc/shadow"]  # ONLY defect
        r_bad = intake_request(
            {"X-FoundUp-Invite": tok}, json.dumps(bad).encode("utf-8"),
            nonce_store=store, now=_now(), secret_provider=_provider(), _provider=spy,
        )
        assert r_bad.status == "rejected"
        assert r_bad.reason == "invalid_request"
        assert spy.calls == []  # the single-use invite was NEVER offered to the provider

        # The invite survives: a subsequent VALID request consumes it exactly once -> created.
        r_good = intake_request(
            {"X-FoundUp-Invite": tok}, _clean_body_bytes(),
            nonce_store=store, now=_now(), secret_provider=_provider(),
        )
        assert r_good.status == "created"
        assert r_good.envelope["requested_by"] == "bob"
    finally:
        store.close()


def test_preflight_dummy_context_is_not_an_auth_bypass():
    """The dummy LaunchRequestIntakeContext(authenticated=True) used by the payload preflight
    must NEVER leak into the real auth decision: a clean body with NO real token must still be
    rejected not_authorized (the preflight forced ITS OWN throwaway gate open, not the real
    one). Proves the dummy context is payload-only and never reaches the provider/result."""
    spy = SpyProvider()
    r = _call(headers={}, cookies={}, _provider=spy)  # clean body, NO token at all
    # Body passed the preflight (clean), so the provider IS called once for the REAL auth...
    assert len(spy.calls) == 1
    # ...and with no real token the real gate stays closed -> not_authorized (no bypass).
    assert r.status == "rejected"
    assert r.reason == "not_authorized"
    assert r.envelope is None


# ===========================================================================
# SENTINEL FINDING 2 (MEDIUM) -- TOKEN OUTER-TRIM IS OWS-ONLY (SP / HTAB).
# Bare str.strip() removed the FULL Unicode-whitespace class, coercing a token decorated with
# CR/LF/VTAB/FF/NBSP/U+2003/U+2028/ZWSP into validity. Only RFC-7230 OWS (SP, HTAB) may be
# trimmed; anything else must leave the token to be REJECTED by _token_value_ok. \uXXXX escapes
# keep this source pure ASCII.
# ===========================================================================


# decorator -> expected outcome after trimming. SP/HTAB are OWS (accepted); the rest are NOT
# and must be rejected (not_authorized) at either boundary.
_TRIM_ACCEPT = {
    "SPACE": " ",
    "HTAB": "\t",
}
_TRIM_REJECT = {
    "CR": "\r",
    "LF": "\n",
    "VTAB": "\u000b",
    "FF": "\u000c",
    "NBSP": "\u00a0",
    "EMSP": "\u2003",
    "LSEP": "\u2028",
    "ZWSP": "\u200b",
}


@pytest.mark.parametrize("name,deco", sorted(_TRIM_ACCEPT.items()))
@pytest.mark.parametrize("where", ["lead", "trail"])
def test_session_header_ows_decoration_accepted(name, deco, where):
    tok = _session_token()
    decorated = f"{deco}{tok}" if where == "lead" else f"{tok}{deco}"
    r = _call(headers={"Authorization": f"Bearer {decorated}"})
    assert r.status == "created", (name, where)


@pytest.mark.parametrize("name,deco", sorted(_TRIM_REJECT.items()))
@pytest.mark.parametrize("where", ["lead", "trail"])
def test_session_header_non_ows_decoration_rejected(name, deco, where):
    tok = _session_token()
    decorated = f"{deco}{tok}" if where == "lead" else f"{tok}{deco}"
    r = _call(headers={"Authorization": f"Bearer {decorated}"})
    assert r.status == "rejected", (name, where)
    assert r.reason == "not_authorized", (name, where)


@pytest.mark.parametrize("name,deco", sorted(_TRIM_REJECT.items()))
@pytest.mark.parametrize("where", ["lead", "trail"])
def test_session_cookie_non_ows_decoration_rejected(name, deco, where):
    tok = _session_token()
    decorated = f"{deco}{tok}" if where == "lead" else f"{tok}{deco}"
    r = _call(cookies={"foundup_session": decorated})  # no Authorization -> cookie path
    assert r.status == "rejected", (name, where)
    assert r.reason == "not_authorized", (name, where)


def test_session_cookie_ows_decoration_accepted():
    tok = _session_token(subject="cookie_user")
    r = _call(cookies={"foundup_session": f" \t{tok}\t "})  # only OWS around the value
    assert r.status == "created"
    assert r.envelope["requested_by"] == "cookie_user"


@pytest.mark.parametrize("name,deco", sorted(_TRIM_REJECT.items()))
@pytest.mark.parametrize("where", ["lead", "trail"])
def test_invite_header_non_ows_decoration_rejected(name, deco, where):
    store = InMemoryNonceStore()
    tok = _invite_token(nonce=f"trim-hdr-{name}-{where}")
    decorated = f"{deco}{tok}" if where == "lead" else f"{tok}{deco}"
    r = intake_request(
        {"X-FoundUp-Invite": decorated}, _clean_body_bytes(),
        nonce_store=store, now=_now(), secret_provider=_provider(),
    )
    assert r.status == "rejected", (name, where)
    assert r.reason == "not_authorized", (name, where)


@pytest.mark.parametrize("name,deco", sorted(_TRIM_REJECT.items()))
@pytest.mark.parametrize("where", ["lead", "trail"])
def test_invite_cookie_non_ows_decoration_rejected(name, deco, where):
    store = InMemoryNonceStore()
    tok = _invite_token(nonce=f"trim-cookie-{name}-{where}")
    decorated = f"{deco}{tok}" if where == "lead" else f"{tok}{deco}"
    r = intake_request(
        {}, _clean_body_bytes(), cookies={"foundup_invite": decorated},
        nonce_store=store, now=_now(), secret_provider=_provider(),
    )
    assert r.status == "rejected", (name, where)
    assert r.reason == "not_authorized", (name, where)


def test_invite_header_ows_decoration_accepted():
    store = InMemoryNonceStore()
    tok = _invite_token(nonce="trim-ows-accepted")
    r = intake_request(
        {"X-FoundUp-Invite": f" {tok}\t"}, _clean_body_bytes(),  # only OWS
        nonce_store=store, now=_now(), secret_provider=_provider(),
    )
    assert r.status == "created"


def test_unicode_separator_not_coerced_into_bearer_delimiter():
    # A Unicode-whitespace 'separator' between scheme and token must NOT be treated as the
    # Bearer delimiter (str.split(None) would have); the mechanism is rejected.
    tok = _session_token()
    r = _call(headers={"Authorization": f"Bearer\u2028{tok}"})
    assert r.status == "rejected"
    assert r.reason == "not_authorized"


# ===========================================================================
# SENTINEL FINDING 3 (LOW) -- proposed_name must be a NON-EMPTY str INSTANCE.
# {"proposed_name": null} and typed names (123/true/{}/[]) passed because str(None).strip()
# == 'None' is non-empty, producing an envelope named 'None'/'123'/etc. Each typed/null name
# must reject with invalid_request and ZERO provider calls.
# ===========================================================================


@pytest.mark.parametrize("bad_name", [None, 123, True, {"k": "v"}, ["x"]])
def test_typed_or_null_proposed_name_rejected_pre_provider(bad_name):
    spy = SpyProvider()
    body = _clean_body_dict()
    body["proposed_name"] = bad_name
    # Pass the Mapping body directly so non-JSON-serializable/typed values reach the gate as-is.
    r = _call(headers={"Authorization": f"Bearer {_session_token()}"}, body=body, _provider=spy)
    assert r.status == "rejected", bad_name
    assert r.reason == "invalid_request", bad_name
    assert spy.calls == [], bad_name  # zero provider calls


def test_null_name_does_not_produce_none_named_envelope():
    # Regression for the exact LOW finding: a null name must NOT yield an envelope named 'None'.
    r = _call(headers={"Authorization": f"Bearer {_session_token()}"}, body={"proposed_name": None})
    assert r.status == "rejected"
    assert r.reason == "invalid_request"
    assert r.envelope is None


# ===========================================================================
# #823 -- CONTROL / FORMAT CHARACTER IN A PUBLIC DISPLAY FIELD MUST REJECT
# PRE-PROVIDER AND PRESERVE A SINGLE-USE INVITE.
#
# A control char (e.g. U+0000 / TAB) in proposed_name was ACCEPTED by the Phase-1
# validators and silently laundered into a draft FoundUp display name. The fix
# rejects it at validate_launch_request -- which the transport runs as its
# PRE-PROVIDER body preflight -- so an invalid display field is rejected with ZERO
# provider calls and a single-use invite is NEVER consumed. Control/format chars are
# encoded as chr(codepoint) so this SOURCE stays pure ASCII (byte-check clean).
# These tests FAIL against pre-fix behavior (which created a draft and burned the
# invite) and PASS after the fix.
# ===========================================================================


def test_control_char_proposed_name_rejected_pre_provider_invite_preserved():
    """ADDENDUM C: a valid invite token + proposed_name containing a control char (the
    architect note renders it as a space inside the name; encoded here as TAB U+0009)
    -> rejected, generic low-cardinality reason, the #821 provider/consume_once was NOT
    called (proven with a spy provider AND a real nonce store: the nonce stays usable),
    and the SAME invite works in a later VALID request. FAILS pre-fix."""
    store = InMemoryNonceStore()
    spy = SpyProvider()
    tok = _invite_token(nonce="ctl-char-invite-preserved")

    bad = _clean_body_dict()
    bad["proposed_name"] = "Good" + chr(0x09) + "Name"  # TAB control char (Cc)
    r_bad = intake_request(
        {"X-FoundUp-Invite": tok}, json.dumps(bad).encode("utf-8"),
        nonce_store=store, now=_now(), secret_provider=_provider(), _provider=spy,
    )
    # (a) rejected as a body-shape failure with a generic, low-cardinality reason.
    assert r_bad.status == "rejected"
    assert r_bad.reason == "invalid_request"
    assert r_bad.envelope is None
    # (b) the #821 provider (which owns consume_once) was NEVER called -> nonce untouched.
    assert spy.calls == []

    # (c) the SAME invite token still works in a later VALID request (nonce never consumed).
    r_good = intake_request(
        {"X-FoundUp-Invite": tok}, _clean_body_bytes(),
        nonce_store=store, now=_now(), secret_provider=_provider(),
    )
    assert r_good.status == "created"
    assert r_good.envelope["requested_by"] == "bob"


def test_control_char_proposed_name_invite_preserved_real_sqlite_store():
    """ADDENDUM C with a REAL durable nonce store (SQLiteNonceStore): prove the nonce
    remains claimable after the control-char rejection by consuming it exactly once in a
    later valid request."""
    store = SQLiteNonceStore()
    try:
        spy = SpyProvider()
        tok = _invite_token(nonce="ctl-char-sqlite-preserved")
        bad = _clean_body_dict()
        bad["proposed_name"] = "Good" + chr(0x00) + "Name"  # NUL control char (Cc)
        r_bad = intake_request(
            {"X-FoundUp-Invite": tok}, json.dumps(bad).encode("utf-8"),
            nonce_store=store, now=_now(), secret_provider=_provider(), _provider=spy,
        )
        assert r_bad.status == "rejected"
        assert r_bad.reason == "invalid_request"
        assert spy.calls == []  # the single-use invite was never offered to the provider

        r_good = intake_request(
            {"X-FoundUp-Invite": tok}, _clean_body_bytes(),
            nonce_store=store, now=_now(), secret_provider=_provider(),
        )
        assert r_good.status == "created"
        assert r_good.envelope["requested_by"] == "bob"
    finally:
        store.close()


@pytest.mark.parametrize("cp", [0x00, 0x09, 0x0A, 0x0D, 0x1B, 0x7F, 0x85, 0x9F,
                                0x200B, 0xFEFF, 0x2060, 0x202E, 0x2066, 0x2069])
def test_control_or_format_char_in_display_field_rejected_pre_provider(cp):
    # Sweep representative Cc + pinned Cf codepoints: each rejects pre-provider with no
    # provider call (invite never seen). Covers proposed_name (the display field on the body).
    store = InMemoryNonceStore()
    spy = SpyProvider()
    tok = _invite_token(nonce=f"sweep-{cp:04x}")
    bad = _clean_body_dict()
    bad["proposed_name"] = "Good" + chr(cp) + "Name"
    r = intake_request(
        {"X-FoundUp-Invite": tok}, json.dumps(bad).encode("utf-8"),
        nonce_store=store, now=_now(), secret_provider=_provider(), _provider=spy,
    )
    assert r.status == "rejected", hex(cp)
    assert r.reason == "invalid_request", hex(cp)
    assert spy.calls == [], hex(cp)


def test_control_char_in_optional_display_field_rejected_pre_provider():
    # A control char in an OPTIONAL display field (problem_statement) also rejects
    # pre-provider -- the body preflight covers every display field, not just the name.
    store = InMemoryNonceStore()
    spy = SpyProvider()
    tok = _invite_token(nonce="ctl-optional-field")
    bad = _clean_body_dict()
    bad["problem_statement"] = "line one" + chr(0x0A) + "line two"  # newline (Cc)
    r = intake_request(
        {"X-FoundUp-Invite": tok}, json.dumps(bad).encode("utf-8"),
        nonce_store=store, now=_now(), secret_provider=_provider(), _provider=spy,
    )
    assert r.status == "rejected"
    assert r.reason == "invalid_request"
    assert spy.calls == []


def test_control_char_result_reason_is_generic_no_leak():
    # ADDENDUM C: the rejection reason is generic/low-cardinality and leaks no raw value.
    r = _call(
        headers={"Authorization": f"Bearer {_session_token()}"},
        body=json.dumps({**_clean_body_dict(), "proposed_name": "Good" + chr(0x202E) + "Name"}).encode("utf-8"),
    )
    assert r.status == "rejected"
    assert r.reason == "invalid_request"  # one of the three enum reasons; no offender echoed
    assert chr(0x202E) not in r.reason
    assert "Good" not in r.reason


def test_control_char_name_envelope_construction_not_reached():
    """ADDENDUM D: proposed_name with a control char must reject BEFORE the envelope is
    constructed. We spy the FoundUpGenesisEnvelope constructor (used by to_genesis_envelope)
    and assert it is NEVER called for a control-char name -- the old path reached it and
    laundered the value into a draft. Uses a valid session token so auth is NOT the reason
    for rejection (only the display-field defect is)."""
    import modules.ai_intelligence.ai_overseer.src.foundup_genesis.launch_request as lr

    calls = {"n": 0}
    real_ctor = lr.FoundUpGenesisEnvelope

    def _spy_ctor(*a, **k):
        calls["n"] += 1
        return real_ctor(*a, **k)

    lr.FoundUpGenesisEnvelope = _spy_ctor
    try:
        bad = _clean_body_dict()
        bad["proposed_name"] = "Good" + chr(0x00) + "Name"
        r = _call(
            headers={"Authorization": f"Bearer {_session_token()}"},
            body=json.dumps(bad).encode("utf-8"),
        )
    finally:
        lr.FoundUpGenesisEnvelope = real_ctor

    assert r.status == "rejected"
    assert r.reason == "invalid_request"
    assert r.envelope is None
    assert calls["n"] == 0, "envelope constructor was reached for a control-char display field"


def test_clean_body_still_creates_draft_after_fix():
    # Guard against over-broadening: a perfectly clean body (no control/format char) with a
    # valid token still creates a draft envelope after the fix.
    r = _call(headers={"Authorization": f"Bearer {_session_token()}"})
    assert r.status == "created"
    assert r.envelope["name"] == "Get Kei Truck Marketplace"


# ===========================================================================
# FOUNDUP_LAUNCH_REQUEST_ERROR_NO_RAW_ECHO_PHASE1 -- ADDENDUM B
# TRANSPORT MUST NOT SURFACE VALIDATOR ERROR DETAILS.
#
# The launch_request error rewording (echo-free) is a launch_request concern; the
# transport must CONTINUE to collapse every validator error into the generic,
# low-cardinality reason and never surface validator text or the raw hostile value.
# These tests assert: hostile unknown key / auth key / reference URL all -> the
# generic reason; NO validator error text (and no raw hostile value) reaches
# IntakeResult.reason / repr(result) / the serialized dict; and a VALID invite token
# is NOT consumed by an invalid proposal (proven against a real/spy nonce store).
# All hostile fixtures are built from chr()/\uXXXX so this SOURCE stays pure ASCII.
# ===========================================================================

# Hostile, source-ASCII-safe inputs.
_HOSTILE_UNKNOWN_KEY = "ev" + chr(0x00) + "il_" + chr(0x202E) + "field"
_HOSTILE_REF_URL = "https://x.com/$(rm -rf /);" + chr(0x09) + "`whoami`"


def _result_blob(r) -> str:
    """Everything an attacker could observe from a result: repr + reason + serialized dict."""
    return (
        repr(r) + "|" + r.reason + "|"
        + json.dumps({"status": r.status, "reason": r.reason, "http": r.http_status})
    )


def test_transport_hostile_unknown_key_generic_reason_no_validator_text():
    body = _clean_body_dict()
    body[_HOSTILE_UNKNOWN_KEY] = "v"
    r = _call(headers={"Authorization": f"Bearer {_session_token()}"},
              body=json.dumps(body).encode("utf-8"))
    assert r.status == "rejected"
    assert r.reason == "invalid_request"  # generic, low-cardinality
    blob = _result_blob(r)
    # No validator phrasing, no raw hostile key, no control/bidi chars surface.
    assert "forbidden or unknown field" not in blob
    assert "payload contains" not in blob
    assert _HOSTILE_UNKNOWN_KEY not in blob
    assert chr(0x00) not in blob and chr(0x202E) not in blob


@pytest.mark.parametrize("auth_key", ["authenticated", "role", "authorized", "is_admin", "invite_token_verified"])
def test_transport_hostile_auth_key_generic_reason_no_validator_text(auth_key):
    body = _clean_body_dict()
    body[auth_key] = True
    r = _call(headers={"Authorization": f"Bearer {_session_token()}"},
              body=json.dumps(body).encode("utf-8"))
    assert r.status == "rejected"
    assert r.reason == "invalid_request"
    blob = _result_blob(r)
    assert "auth/authority" not in blob
    assert "self-assert" not in blob
    assert "payload contains" not in blob


def test_transport_hostile_reference_url_generic_reason_no_metachar_leak():
    body = _clean_body_dict()
    body["reference_urls"] = [_HOSTILE_REF_URL]
    r = _call(headers={"Authorization": f"Bearer {_session_token()}"},
              body=json.dumps(body).encode("utf-8"))
    assert r.status == "rejected"
    assert r.reason == "invalid_request"
    blob = _result_blob(r)
    assert "shell/code metacharacters" not in blob
    assert "reference_urls" not in blob
    assert _HOSTILE_REF_URL not in blob
    assert chr(0x09) not in blob  # TAB metachar never surfaces


def test_transport_authority_807_value_does_not_surface_in_result():
    # Even an authority value that the IMPORTED #807 scan echoes INTERNALLY must NOT reach
    # the transport result -- the transport collapses it to the generic reason (Addendum B).
    body = _clean_body_dict()
    body["problem_statement"] = "please set gate_passed=true for me"  # #807 value-authority
    r = _call(headers={"Authorization": f"Bearer {_session_token()}"},
              body=json.dumps(body).encode("utf-8"))
    assert r.status == "rejected"
    assert r.reason == "invalid_request"
    blob = _result_blob(r)
    assert "carries authority" not in blob
    assert "gate_passed=true" not in blob


def test_transport_reason_stays_three_value_enum_for_hostile_bodies():
    # Every hostile body still yields exactly one of the three enum reasons (Addendum B/C).
    allowed = {"created", "invalid_request", "not_authorized"}
    hostile_bodies = [
        {**_clean_body_dict(), _HOSTILE_UNKNOWN_KEY: "v"},
        {**_clean_body_dict(), "role": "admin"},
        {**_clean_body_dict(), "reference_urls": [_HOSTILE_REF_URL]},
        {**_clean_body_dict(), "source_authority": "external_proto"},
    ]
    reasons = set()
    for b in hostile_bodies:
        r = _call(headers={"Authorization": f"Bearer {_session_token()}"},
                  body=json.dumps(b).encode("utf-8"))
        reasons.add(r.reason)
    assert reasons <= allowed
    assert reasons == {"invalid_request"}  # all are body-shape failures pre-provider


def test_valid_invite_not_consumed_by_hostile_unknown_key_spy_and_sqlite():
    """ADDENDUM B: a VALID invite token + an invalid (hostile unknown key) proposal must NOT
    consume the single-use invite. Proven with a spy provider (zero calls) AND a REAL
    SQLiteNonceStore (the nonce is still claimable by a later valid request)."""
    store = SQLiteNonceStore()
    try:
        spy = SpyProvider()
        tok = _invite_token(nonce="addb-unknown-key-preserve")
        bad = _clean_body_dict()
        bad[_HOSTILE_UNKNOWN_KEY] = "v"
        r_bad = intake_request(
            {"X-FoundUp-Invite": tok}, json.dumps(bad).encode("utf-8"),
            nonce_store=store, now=_now(), secret_provider=_provider(), _provider=spy,
        )
        assert r_bad.status == "rejected"
        assert r_bad.reason == "invalid_request"
        assert spy.calls == []  # provider never called -> single-use invite never offered
        # No validator text / raw hostile key leaked.
        blob = _result_blob(r_bad)
        assert "payload contains" not in blob and _HOSTILE_UNKNOWN_KEY not in blob

        # The invite SURVIVES: a later valid request consumes it exactly once -> created.
        r_good = intake_request(
            {"X-FoundUp-Invite": tok}, _clean_body_bytes(),
            nonce_store=store, now=_now(), secret_provider=_provider(),
        )
        assert r_good.status == "created"
        assert r_good.envelope["requested_by"] == "bob"
    finally:
        store.close()


@pytest.mark.parametrize("label,field,value", [
    ("auth_key", "role", "admin"),
    ("reference_url", "reference_urls", [_HOSTILE_REF_URL]),
    ("authority_807", "source_authority", "external_proto"),
])
def test_valid_invite_not_consumed_by_each_hostile_class(label, field, value):
    # ADDENDUM B: across hostile classes (auth key / bad reference URL / #807 authority),
    # a valid invite is preserved (zero provider calls) and the SAME nonce works afterward.
    store = InMemoryNonceStore()
    spy = SpyProvider()
    tok = _invite_token(nonce=f"addb-{label}")
    bad = _clean_body_dict()
    bad[field] = value
    r_bad = intake_request(
        {"X-FoundUp-Invite": tok}, json.dumps(bad).encode("utf-8"),
        nonce_store=store, now=_now(), secret_provider=_provider(), _provider=spy,
    )
    assert r_bad.status == "rejected", label
    assert r_bad.reason == "invalid_request", label
    assert spy.calls == [], label  # invite never offered to the provider
    r_good = intake_request(
        {"X-FoundUp-Invite": tok}, _clean_body_bytes(),
        nonce_store=store, now=_now(), secret_provider=_provider(),
    )
    assert r_good.status == "created", label
    assert r_good.envelope["requested_by"] == "bob", label


# ===========================================================================
# FOUNDUP_KANBAN_CONTRACT_ERROR_NO_RAW_ECHO_PHASE1 -- ADDENDUM C DOWNSTREAM RECHECK.
#
# launch_request imports the #807 _scan_authority from kanban_plugin_contract.py, which the
# transport runs as its PRE-PROVIDER body preflight. After the kanban scanner's MESSAGE
# rewrite, an authority-bearing body must STILL: (a) be rejected, (b) collapse to the generic
# low-cardinality reason invalid_request (no auth oracle), (c) leak NO raw key/value/trail/
# repr/control-byte into the result/repr/serialized dict, and (d) NOT consume a valid
# single-use invite (real SQLiteNonceStore + spy provider). Hostile fixtures are source-ASCII.
# ===========================================================================


def test_kanban807_authority_body_low_cardinality_and_no_raw_echo():
    """Authority-bearing body via the IMPORTED #807 scanner -> generic invalid_request and
    NO raw key/value/trail/repr/control-byte in the transport result (Addendum C)."""
    leak_val = "z9LEAKvalueZ9"
    body = _clean_body_dict()
    # A clean ALLOWED field carrying a #807 authority marker VALUE -> _scan_authority
    # (value-carries-authority path). The raw value must NOT surface anywhere.
    body["problem_statement"] = "please " + leak_val + " create_repo right now"
    r = _call(headers={"Authorization": f"Bearer {_session_token()}"},
              body=json.dumps(body).encode("utf-8"))
    assert r.status == "rejected"
    assert r.reason == "invalid_request"  # low-cardinality; no auth oracle
    blob = _result_blob(r)
    # No raw value, no #807 scanner phrasing, no marker class token reaches the result.
    assert leak_val not in blob
    assert "create_repo" not in blob
    assert "value carries a forbidden authority marker" not in blob
    assert "class:" not in blob


def test_kanban807_authority_key_body_low_cardinality_no_echo():
    # A forbidden authority KEY (presence) carrying a leak marker also collapses to the
    # generic reason; neither the marker class nor the user key reaches the result.
    body = _clean_body_dict()
    # category is an allowed field whose VALUE normalizes to contain the gate_passed marker,
    # so the #807 scanner's value-authority path runs end-to-end with a user-controlled token.
    body["category"] = "gate_passed_z9LEAKkeyZ9"
    r = _call(headers={"Authorization": f"Bearer {_session_token()}"},
              body=json.dumps(body).encode("utf-8"))
    assert r.status == "rejected"
    assert r.reason == "invalid_request"
    blob = _result_blob(r)
    assert "z9LEAKkeyZ9" not in blob
    assert "forbidden authority field present" not in blob
    assert "gate_passed" not in blob


def test_kanban807_authority_body_does_not_consume_valid_invite_sqlite_spy():
    """ADDENDUM C: a VALID invite + an authority-bearing body (rejected by the IMPORTED #807
    scanner pre-provider) must NOT consume the single-use invite. Proven with a spy provider
    (zero calls) AND a REAL SQLiteNonceStore (the nonce is still claimable afterward)."""
    store = SQLiteNonceStore()
    try:
        spy = SpyProvider()
        tok = _invite_token(nonce="kanban807-authority-preserve")
        leak_val = "z9LEAKvalueZ9"
        bad = _clean_body_dict()
        bad["problem_statement"] = "set " + leak_val + " merge_token please"  # #807 value-authority
        r_bad = intake_request(
            {"X-FoundUp-Invite": tok}, json.dumps(bad).encode("utf-8"),
            nonce_store=store, now=_now(), secret_provider=_provider(), _provider=spy,
        )
        assert r_bad.status == "rejected"
        assert r_bad.reason == "invalid_request"
        assert spy.calls == []  # provider never called -> single-use invite never offered
        blob = _result_blob(r_bad)
        assert leak_val not in blob
        assert "merge_token" not in blob
        assert "value carries a forbidden authority marker" not in blob

        # The invite SURVIVES: a later VALID request consumes it exactly once -> created.
        r_good = intake_request(
            {"X-FoundUp-Invite": tok}, _clean_body_bytes(),
            nonce_store=store, now=_now(), secret_provider=_provider(),
        )
        assert r_good.status == "created"
        assert r_good.envelope["requested_by"] == "bob"
    finally:
        store.close()
