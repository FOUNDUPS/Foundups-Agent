#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Adversarial tests for the Fusion redaction gate (HERMES_FUSION_REDACTION_GATE_PHASE1).

SECURITY-CRITICAL. Every "secret" below is SYNTHETIC -- a fake, pattern-shaped string assembled from
SPLIT fragments at runtime (e.g. "s" "k-"), so this source file contains NO literal provider-secret
pattern (proven by test_no_literal_secret_pattern_in_source). No real secret. No skip / no xfail.

Sentinel lanes covered: secret-leak, authority-block, private-reasoning, source-literal, live-mode,
non-vacuity.
"""

from __future__ import annotations

import ast
import json
import re
import socket
from dataclasses import asdict
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.fusion_redaction_gate import (
    ALLOWED_REASONS,
    AUDIT_STRUCTURAL_CATEGORIES,
    BLOCK_CATEGORIES,
    REASON_BLOCKED_POLICY,
    REASON_CLEAN,
    REASON_REDACTED,
    REASON_REDACTOR_ERROR,
    REASON_RESIDUAL,
    REDACT_CATEGORIES,
    REDACTION_BLOCKED,
    REDACTION_GATE_PASSED,
    REDACTION_POLICY_VERSION,
    RedactionReport,
    evaluate_redaction_gate,
    redact_text,
    redaction_status_for,
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
import modules.communication.moltbot_bridge.src.fusion_redaction_gate as gate_mod

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
GATE_SRC = SRC_DIR / "fusion_redaction_gate.py"
TEST_SRC = Path(__file__).resolve()

# --- synthetic, pattern-shaped secrets (split prefixes -> no literal token in source) -----------
_SK = "s" "k-"
_AI = "AI" "za"
_GHP = "gh" "p_"
_AK = "AK" "IA"
_XOX = "xox" "b-"
_PK_BEGIN = "-----BEGIN RSA PRIVATE " "KEY-----"
_PK_END = "-----END RSA PRIVATE " "KEY-----"

# REDACT class -> these PASS the gate (value removed, clean output)
REDACTABLE_CORPUS = [
    ("openai_key", _SK + "A" * 48),
    ("anthropic_key", _SK + "ant-api" + "B" * 45),
    ("openrouter_key", _SK + "or-" + "C" * 40),
    ("grok_key", "x" "ai-" + "D" * 42),
    ("google_api_key", _AI + "E" * 35),
    ("google_oauth_access", "ya29." + "F" * 40),
    ("google_oauth_refresh", "1//" + "G" * 30),
    ("aws_akia", _AK + "1234567890ABCDEF"),
    ("github_ghp", _GHP + "h" * 36),
    ("github_pat", "github" "_pat_" + "i" * 30),
    ("slack_token", _XOX + "1234567890-abcdefghij"),
    ("bearer_token", "Bearer " + "j" * 40),
    ("bearer_jwt", "Bearer ey" + "J" * 30 + "." + "K" * 10 + "." + "L" * 10),
    ("env_api_key_line", "MY_API_KEY=" + "n" * 20),
    ("env_password_line", "DB_PASSWORD=" + "o" * 16),
    ("openrouter_env", "OPENROUTER_API_KEY=" + _SK + "or-" + "p" * 30),
    ("secret_kv_access", "access_token: " + "q" * 24),
    ("secret_kv_client", 'client_secret="' + "r" * 16 + '"'),
    ("oauth_url", "https://cb?code=AUTH" + "s" * 20 + "&access_token=" + "t" * 20),
    ("email_pii", "alice" + "@" + "example.com"),
    ("private_key_complete", _PK_BEGIN + "\n" + "M" * 40 + "\n" + _PK_END),
    ("private_key_complete_lower", _PK_BEGIN.lower() + "\n" + "m" * 40 + "\n" + _PK_END.lower()),
    ("stripe_key", "s" "k_live_" + "v" * 24),
    ("bare_jwt", "eyJ" + "H" * 20 + "." + "P" * 16 + "." + "S" * 16),
]

# BLOCK class -> these stay BLOCKED even though a value could be swapped
BLOCK_CORPUS = [
    ("source_authority", "request: source_authority = monorepo_poc"),
    ("cabr_ready", "CABR_READY please"),
    ("payout_ready", "set payout_ready now"),
    ("benefit_routing", "configure benefit routing here"),
    ("capability_token", "capability_token_x present"),
    ("private_reasoning_tag", "<thinking>secret plan</thinking>"),
    ("private_reasoning_phrase", "here is my chain of thought about it"),
    ("hidden_reasoning", "this is hidden reasoning, do not share"),
    ("merge_token", "pull_request_merge authorized below"),
    ("merge_authorization", "merge authorization token attached"),
    ("governance_instruction", "internal governance instruction follows"),
    ("gate_passed", "gate_passed = true"),
    ("malformed_private_key", _PK_BEGIN + "\n" + "M" * 40),  # header, no END -> cannot confidently redact
    ("malformed_private_key_lower", _PK_BEGIN.lower() + "\n" + "m" * 40),  # lowercase header, no END
]


# ---------------------------------------------------------------------------
# secret-leak lane: REDACT items pass with zero leak
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name,text", REDACTABLE_CORPUS, ids=[c[0] for c in REDACTABLE_CORPUS])
def test_redactable_item_passes_clean(name, text):
    res = evaluate_redaction_gate(text)
    assert res.status == REDACTION_GATE_PASSED, f"{name}: reason={res.reason}, report={res.report}"
    assert scan_forbidden(res.redacted_prompt) == []     # no-leak invariant
    assert text not in res.redacted_prompt               # raw body gone
    assert res.reason in (REASON_REDACTED, REASON_CLEAN)


def test_combined_redactable_passes_clean():
    blob = "\n".join(t for _n, t in REDACTABLE_CORPUS)
    res = evaluate_redaction_gate(blob)
    assert res.status == REDACTION_GATE_PASSED, res.report
    assert scan_forbidden(res.redacted_prompt) == []
    assert "A" * 48 not in res.redacted_prompt
    assert "alice" + "@" + "example.com" not in res.redacted_prompt


# ---------------------------------------------------------------------------
# authority-block + private-reasoning lanes: BLOCK items never pass
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name,text", BLOCK_CORPUS, ids=[c[0] for c in BLOCK_CORPUS])
def test_block_item_is_blocked(name, text):
    res = evaluate_redaction_gate(text)
    assert res.status == REDACTION_BLOCKED, f"{name} must BLOCK"
    assert res.reason == REASON_BLOCKED_POLICY
    assert res.redacted_prompt is None          # nothing safe to send
    assert res.report.blocked_categories         # at least one block category named


def test_block_categories_never_pass_even_when_mixed_with_redactable():
    # a payload mixing a redactable secret AND a block marker must BLOCK
    text = (_SK + "A" * 48) + "  and  source_authority = x"
    res = evaluate_redaction_gate(text)
    assert res.status == REDACTION_BLOCKED
    assert res.reason == REASON_BLOCKED_POLICY


def test_private_reasoning_is_blocked_not_merely_redacted():
    res = evaluate_redaction_gate("prefix <thinking> hidden </thinking> suffix")
    assert res.status == REDACTION_BLOCKED
    assert "private_reasoning" in res.report.blocked_categories


def test_redact_and_block_categories_disjoint_and_populated():
    assert set(REDACT_CATEGORIES) and set(BLOCK_CATEGORIES)
    assert set(REDACT_CATEGORIES).isdisjoint(set(BLOCK_CATEGORIES))


# ---------------------------------------------------------------------------
# fail-closed
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad", [None, 123, b"bytes", 4.5, ["x"], {"k": "v"}])
def test_non_text_prompt_fails_closed(bad):
    res = evaluate_redaction_gate(bad)
    assert res.status == REDACTION_BLOCKED
    assert res.reason == REASON_REDACTOR_ERROR


def test_non_text_context_fails_closed():
    res = evaluate_redaction_gate("clean", context=123)
    assert res.status == REDACTION_BLOCKED
    assert res.reason == REASON_REDACTOR_ERROR


def test_exception_fails_closed_no_raw_echo(monkeypatch):
    raw = _SK + "SECRETVALUE" + "Z" * 30

    def _boom(_text):
        raise RuntimeError("redactor exploded: " + raw)  # message contains raw -> must NOT surface

    monkeypatch.setattr(gate_mod, "redact_text", _boom)
    res = gate_mod.evaluate_redaction_gate(raw)
    assert res.status == REDACTION_BLOCKED
    assert res.reason == REASON_REDACTOR_ERROR
    blob = json.dumps(asdict(res.report)) + res.reason + res.status
    assert raw not in blob and "SECRETVALUE" not in blob


def test_residual_forbidden_fails_closed(monkeypatch):
    def _dirty(_text):
        return (_SK + "RESIDUAL" + "Z" * 30, RedactionReport(residual_forbidden_count=1))

    monkeypatch.setattr(gate_mod, "redact_text", _dirty)
    res = gate_mod.evaluate_redaction_gate("anything")
    assert res.status == REDACTION_BLOCKED
    assert res.reason == REASON_RESIDUAL


def test_clean_prompt_passes_clean_reason():
    res = evaluate_redaction_gate("ordinary prompt about ramen shops in tokyo")
    assert res.status == REDACTION_GATE_PASSED
    assert res.reason == REASON_CLEAN
    assert res.redacted_prompt == "ordinary prompt about ramen shops in tokyo"


def test_all_reasons_in_allowed_vocabulary():
    samples = ["clean text", _SK + "A" * 48, "source_authority = x", None]
    for s in samples:
        assert evaluate_redaction_gate(s).reason in ALLOWED_REASONS


# ---------------------------------------------------------------------------
# digests from redacted output only; report has counts not snippets
# ---------------------------------------------------------------------------


def test_digests_are_from_redacted_output_not_raw():
    secret = _SK + "A" * 48
    res = evaluate_redaction_gate(secret, context="clean context")
    assert res.status == REDACTION_GATE_PASSED
    assert is_valid_digest(res.prompt_digest) and is_valid_digest(res.context_digest)
    # digest matches the REDACTED output, and differs from a digest of the raw secret
    assert res.prompt_digest == digest(res.redacted_prompt)
    assert res.prompt_digest != digest(secret)


def test_report_has_counts_not_snippets():
    secret = _SK + "A" * 48
    res = evaluate_redaction_gate(secret)
    rep = res.report
    assert rep.policy_version == REDACTION_POLICY_VERSION
    assert isinstance(rep.categories_hit, dict)
    assert all(isinstance(k, str) and isinstance(v, int) for k, v in rep.categories_hit.items())
    assert rep.categories_hit.get("openai_anthropic_key", 0) >= 1
    # no raw secret material anywhere in the serialized report
    blob = json.dumps(asdict(rep))
    assert secret not in blob and "A" * 48 not in blob


# ---------------------------------------------------------------------------
# determinism
# ---------------------------------------------------------------------------


def test_deterministic():
    blob = "\n".join(t for _n, t in REDACTABLE_CORPUS)
    r1 = evaluate_redaction_gate(blob)
    r2 = evaluate_redaction_gate(blob)
    assert (r1.status, r1.reason, r1.redacted_prompt, r1.prompt_digest) == (
        r2.status, r2.reason, r2.redacted_prompt, r2.prompt_digest
    )


# ---------------------------------------------------------------------------
# live-mode lane: live Fusion modes STILL raise after this slice
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("mode", [FusionMode.ALIAS, FusionMode.SERVER_TOOL, FusionMode.LOCAL_FALLBACK])
def test_live_modes_remain_blocked(mode):
    req = FusionRequest(task_id="t", prompt_digest=digest("p"), panel_models=["m"], mode=mode)
    with pytest.raises(RedactionGateBlocked):
        MockFusionAdapter().run(req)


# ---------------------------------------------------------------------------
# no network / no env
# ---------------------------------------------------------------------------


def test_gate_makes_zero_network(monkeypatch):
    def _boom(*a, **k):
        raise AssertionError("network attempted by redaction gate")

    monkeypatch.setattr(socket, "socket", _boom)
    for _n, t in REDACTABLE_CORPUS + BLOCK_CORPUS:
        evaluate_redaction_gate(t)
    assert evaluate_redaction_gate("clean").status == REDACTION_GATE_PASSED


def test_gate_module_imports_no_os_no_network():
    tree = ast.parse(GATE_SRC.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add((node.module or "").split(".")[0])
    forbidden = {"os", "socket", "requests", "httpx", "aiohttp", "openai", "openrouter", "urllib", "http", "subprocess"}
    assert not (forbidden & imported), f"gate module must not import {forbidden & imported}"


# ---------------------------------------------------------------------------
# source-literal lane: no literal provider-secret pattern committed in source/tests
# ---------------------------------------------------------------------------

_REAL_SECRET_SCANS = [
    re.compile(r"sk-[A-Za-z0-9]{24,}"),
    re.compile(r"AIza[A-Za-z0-9_\-]{30,}"),
    re.compile(r"gh[posru]_[A-Za-z0-9]{30,}"),
    re.compile(r"AKIA[A-Z0-9]{16}"),
    re.compile(r"xai-[A-Za-z0-9]{30,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9\-]{20,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----\s+[A-Za-z0-9+/=]{40,}"),
    re.compile(r"Bearer [A-Za-z0-9._\-]{30,}"),
]


@pytest.mark.parametrize("path", [GATE_SRC, TEST_SRC], ids=["gate_src", "test_src"])
def test_no_literal_secret_pattern_in_source(path):
    text = path.read_text(encoding="utf-8")
    hits = [rx.pattern for rx in _REAL_SECRET_SCANS if rx.search(text)]
    assert hits == [], f"literal secret pattern committed in {path.name}: {hits}"


# ---------------------------------------------------------------------------
# non-vacuity lane: prove the no-leak assertion is meaningful
# ---------------------------------------------------------------------------


def test_no_leak_assertion_is_non_vacuous():
    raw = _SK + "L" * 48
    # an intentionally UNredacted secret is detected (so the no-leak assert can fail when it should)
    assert scan_forbidden(raw) != []
    # the redacted placeholder is genuinely clean
    redacted, _rep = redact_text(raw)
    assert scan_forbidden(redacted) == []
    assert raw not in redacted


def test_scan_forbidden_non_text_is_forbidden():
    assert scan_forbidden(123) == ["non_text_input"]
    assert scan_forbidden(None) == ["non_text_input"]


# ---------------------------------------------------------------------------
# AUDIT MODE lane (REDDOG_AUDIT_MODE_REDACTION_PHASE1, slice 3/3)
#
# audit_mode preserves STRUCTURAL governance identifiers (enum members, field
# names, gate/action constants, WSP refs) while STILL redacting every secret
# VALUE / payout AMOUNT / authorization TOKEN. Secret redaction is NEVER weakened.
# All fixtures are SYNTHETIC (split-prefix) fakes -- no real secret.
# ---------------------------------------------------------------------------

# A realistic FoundUp governance snippet: enum, field list, action constants, WSP ref.
_AUDIT_STRUCTURE_SAMPLE = (
    "class SourceAuthority(str, enum.Enum):\n"
    '    MONOREPO_POC = "monorepo_poc"\n'
    '    EXTERNAL_PROTO = "external_proto"\n'
    "requested_action: str = \"build_foundup\"\n"
    "CANONICAL_ACTIONS = (\"build_foundup\", \"extract_foundup\")\n"
    "# See WSP 109 onboarding intake. source_authority resolve convention; "
    "merge_authorization gate ordering; cabr_payout_authority routing; "
    "governance_instruction gate name.\n"
    "FoundUpJob fields: requested_action, module_path, source_authority.\n"
)


def test_audit_mode_preserves_governance_structure():
    res = evaluate_redaction_gate(_AUDIT_STRUCTURE_SAMPLE, audit_mode=True)
    assert res.status == REDACTION_GATE_PASSED, res.report
    out = res.redacted_prompt or ""
    # enum + member identifiers preserved
    assert "SourceAuthority" in out
    assert "source_authority" in out
    assert "MONOREPO_POC" in out
    assert "EXTERNAL_PROTO" in out
    # action-name constants + field names preserved
    assert "build_foundup" in out
    assert "extract_foundup" in out
    assert "CANONICAL_ACTIONS" in out
    assert "requested_action" in out
    assert "module_path" in out
    # structural governance gate names preserved (not value)
    assert "merge_authorization" in out
    assert "cabr_payout_authority" in out
    assert "governance_instruction" in out
    # WSP ref preserved
    assert "WSP 109" in out


def test_audit_mode_same_structure_blocks_in_default_mode():
    # The identical content BLOCKS on the default (non-audit) path -- proves audit
    # mode is what unblocks the structure, not a general weakening.
    res = evaluate_redaction_gate(_AUDIT_STRUCTURE_SAMPLE, audit_mode=False)
    assert res.status == REDACTION_BLOCKED
    assert res.reason == REASON_BLOCKED_POLICY
    assert "source_authority" in res.report.blocked_categories


def test_audit_mode_still_redacts_fake_api_key():
    # CRITICAL SAFETY TEST: a synthetic API key must STILL be redacted in audit mode.
    secret = _SK + "FAKE" + "A" * 40
    res = evaluate_redaction_gate("here is a loose key " + secret, audit_mode=True)
    assert res.status == REDACTION_GATE_PASSED
    out = res.redacted_prompt or ""
    assert "[REDACTED" in out
    assert secret not in out
    assert scan_forbidden(out, audit_mode=True) == []


def test_audit_mode_still_redacts_fake_oauth_token():
    # Synthetic OAuth access token (ya29.*) -- STILL redacted in audit mode.
    token = "ya29." + "F" * 44
    res = evaluate_redaction_gate("token=" + token, audit_mode=True)
    assert res.status == REDACTION_GATE_PASSED
    out = res.redacted_prompt or ""
    assert token not in out
    assert "F" * 44 not in out


def test_audit_mode_redacts_cabr_payout_amount_keeps_identifier():
    res = evaluate_redaction_gate("cabr_payout = 12500.50 approved", audit_mode=True)
    assert res.status == REDACTION_GATE_PASSED
    out = res.redacted_prompt or ""
    # identifier kept, numeric AMOUNT gone
    assert "cabr_payout" in out
    assert "12500.50" not in out
    assert "[REDACTED" in out


def test_audit_mode_redacts_merge_authorization_token_keeps_gate_name():
    # Preserve that a merge gate EXISTS + its name; redact any authorization token value.
    grant = "gh" "p_" + "T" * 36
    res = evaluate_redaction_gate("merge_authorization = " + grant, audit_mode=True)
    assert res.status == REDACTION_GATE_PASSED
    out = res.redacted_prompt or ""
    assert "merge_authorization" in out   # gate name kept (structure)
    assert grant not in out               # token value gone
    assert "T" * 36 not in out


def test_audit_mode_private_reasoning_still_blocks():
    # private_reasoning free-text is NEVER relaxed by audit mode.
    res = evaluate_redaction_gate("prefix <thinking> hidden plan </thinking> suffix", audit_mode=True)
    assert res.status == REDACTION_BLOCKED
    assert "private_reasoning" in res.report.blocked_categories


def test_audit_mode_malformed_private_key_still_blocks():
    # Ambiguous (header, no END) -> cannot confidently redact -> still BLOCKS in audit mode.
    res = evaluate_redaction_gate(_PK_BEGIN + "\n" + "M" * 40, audit_mode=True)
    assert res.status == REDACTION_BLOCKED
    assert "private_key_residual" in res.report.blocked_categories


def test_audit_mode_mixed_line_keeps_key_redacts_value():
    # ACCEPTANCE fixture: `api_key = "sk-FAKE123"` -> key name kept, value redacted.
    secret = _SK + "FAKE123" + "B" * 30
    res = evaluate_redaction_gate('api_key = "' + secret + '"', audit_mode=True)
    assert res.status == REDACTION_GATE_PASSED
    out = res.redacted_prompt or ""
    assert "api_key" in out               # key/identifier kept (structure)
    assert secret not in out              # value redacted
    assert "FAKE123" not in out
    assert "[REDACTED" in out


def test_audit_mode_generic_secret_kv_value_still_removed():
    # A non-provider-shaped value only caught by the secret_kv shape must still be
    # removed by the key-preserving audit variant (safety net preserved).
    res = evaluate_redaction_gate("password = hunter2topsecretvalue", audit_mode=True)
    assert res.status == REDACTION_GATE_PASSED
    out = res.redacted_prompt or ""
    assert "password" in out
    assert "hunter2topsecretvalue" not in out


def test_audit_mode_combined_structure_and_secret():
    # A payload with BOTH governance structure AND a fake secret: structure survives,
    # secret is redacted, gate PASSES (this is the slice-3 acceptance shape).
    secret = _SK + "MIXED" + "C" * 40
    payload = _AUDIT_STRUCTURE_SAMPLE + '\napi_key = "' + secret + '"\n'
    res = evaluate_redaction_gate(payload, audit_mode=True)
    assert res.status == REDACTION_GATE_PASSED, res.report
    out = res.redacted_prompt or ""
    assert "SourceAuthority" in out and "build_foundup" in out
    assert secret not in out
    assert scan_forbidden(out, audit_mode=True) == []


def test_audit_mode_off_is_byte_identical_default():
    # Backward-compat: audit_mode=False (default) must equal an explicit False AND the
    # no-kwarg call, for structure (blocks), secrets (redact), and clean text.
    samples = [
        _AUDIT_STRUCTURE_SAMPLE,
        _SK + "A" * 48,
        "password = hunter2topsecretvalue",
        "ordinary prompt about ramen shops in tokyo",
        "source_authority = x",
    ]
    for s in samples:
        default = evaluate_redaction_gate(s)
        explicit_false = evaluate_redaction_gate(s, audit_mode=False)
        assert default.status == explicit_false.status
        assert default.reason == explicit_false.reason
        assert default.redacted_prompt == explicit_false.redacted_prompt
        assert default.report.blocked_categories == explicit_false.report.blocked_categories


def test_audit_structural_categories_are_subset_of_block():
    # The audit-visible structural set must be a strict subset of BLOCK categories and
    # must NOT include private_reasoning or private_key_residual (never relaxed).
    assert AUDIT_STRUCTURAL_CATEGORIES.issubset(set(BLOCK_CATEGORIES))
    assert "private_reasoning" not in AUDIT_STRUCTURAL_CATEGORIES
    assert "private_key_residual" not in AUDIT_STRUCTURAL_CATEGORIES


def test_audit_mode_makes_zero_network(monkeypatch):
    def _boom(*a, **k):
        raise AssertionError("network attempted by redaction gate in audit mode")

    monkeypatch.setattr(socket, "socket", _boom)
    evaluate_redaction_gate(_AUDIT_STRUCTURE_SAMPLE, audit_mode=True)
    evaluate_redaction_gate(_SK + "A" * 48, audit_mode=True)
