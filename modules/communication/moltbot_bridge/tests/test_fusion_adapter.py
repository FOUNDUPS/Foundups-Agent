#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for the FusionAdapter contract (HERMES_FUSION_ADAPTER_CONTRACT_PHASE1).

Contract-only: these tests exercise the typed contract + mock/dry-run path and PROVE the slice is
incapable of a live OpenRouter call (no network, no key read), including a NON-VACUOUS AST guard with
a negative control. No skip / no xfail.
"""

from __future__ import annotations

import ast
import json
import socket
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.fusion_adapter import (
    EXECUTABLE_MODES,
    FUTURE_BLOCKED_MODES,
    MAX_PANEL_MODELS,
    MIN_PANEL_MODELS,
    NOT_EVALUATED,
    REDACTION_BLOCKED,
    FusionAdapter,
    FusionAnalysis,
    FusionMode,
    FusionProvider,
    FusionRequest,
    ModelContributionReceipt,
    MockFusionAdapter,
    RedactionGateBlocked,
    DIGEST_HEX_LEN,
    digest,
    is_valid_digest,
)

ADAPTER_SRC = (
    Path(__file__).resolve().parents[1] / "src" / "fusion_adapter.py"
)
MANIFEST_PATH = (
    Path(__file__).resolve().parents[1] / "config" / "openclaw_integration_manifest.json"
)

# The manifest schema enforces status in {landed, planned, parked, removed}
# (test_openclaw_integration_manifest.test_status_is_known). The honest non-landed values are
# planned/parked/removed; the precise contract_pending / BLOCKED_PENDING_REDACTION_GATE wording
# is carried in the entry "notes" field.
HONEST_NON_LANDED_STATUSES = {"planned", "parked", "removed"}


# ---------------------------------------------------------------------------
# Non-vacuous AST guard
# ---------------------------------------------------------------------------

_FORBIDDEN_IMPORT_ROOTS = {
    "requests",
    "httpx",
    "aiohttp",
    "openai",
    "openrouter",
    "subprocess",
    "socket",
    "urllib",
    "urllib3",
    "http",
    "ftplib",
    "smtplib",
    "telnetlib",
}
_FORBIDDEN_NAMES = {"CABR_READY", "gate_passed", "source_authority", "pull_request_merge"}
_WRITE_MODES = ("w", "a", "x", "+")


def _scan_source(src: str) -> list:
    """Return a list of live-call/key-read/write/authority violations found in source.

    Targets AST imports/calls/names -- NOT string literals or comments (so an enum value
    "openrouter" or a docstring mention does not trip the guard).
    """
    tree = ast.parse(src)
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in _FORBIDDEN_IMPORT_ROOTS:
                    violations.append(f"import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            if (node.module or "").split(".")[0] in _FORBIDDEN_IMPORT_ROOTS:
                violations.append(f"from {node.module} import ...")
        elif isinstance(node, ast.Call):
            func = node.func
            # ANY getenv -- this module must never read any env var/key (not just OPENROUTER)
            if isinstance(func, ast.Attribute) and func.attr == "getenv":
                arg = (
                    node.args[0].value
                    if node.args and isinstance(node.args[0], ast.Constant)
                    else "<var>"
                )
                violations.append(f"getenv({arg!r})")
            elif isinstance(func, ast.Name) and func.id == "getenv":
                violations.append("getenv(...)")
            # open(path, "w"/"a"/"x"/"+")
            if isinstance(func, ast.Name) and func.id == "open" and len(node.args) > 1:
                mode = node.args[1]
                if (
                    isinstance(mode, ast.Constant)
                    and isinstance(mode.value, str)
                    and any(m in mode.value for m in _WRITE_MODES)
                ):
                    violations.append(f"open(..., {mode.value!r})")
            # Path.write_text / write_bytes
            if isinstance(func, ast.Attribute) and func.attr in ("write_text", "write_bytes"):
                violations.append(f".{func.attr}(...)")
            # subprocess.run/Popen/call/check_output
            if (
                isinstance(func, ast.Attribute)
                and isinstance(func.value, ast.Name)
                and func.value.id == "subprocess"
            ):
                violations.append(f"subprocess.{func.attr}(...)")
        elif isinstance(node, ast.Name) and node.id in _FORBIDDEN_NAMES:
            violations.append(f"name {node.id}")
        elif isinstance(node, ast.Subscript):
            # os.environ[...] / environ[...] -- env access without getenv
            val = node.value
            if isinstance(val, ast.Attribute) and val.attr == "environ":
                violations.append("os.environ[...]")
            elif isinstance(val, ast.Name) and val.id == "environ":
                violations.append("environ[...]")
    return violations


def test_ast_guard_real_module_clean():
    """The real adapter module has ZERO live-call/key-read/write/authority symbols."""
    violations = _scan_source(ADAPTER_SRC.read_text(encoding="utf-8"))
    assert violations == [], f"adapter module must be clean, found: {violations}"


def test_ast_guard_is_non_vacuous_negative_control():
    """Negative control: the guard MUST fail on forbidden imports/calls (proves it is not vacuous)."""
    bad_src = (
        "import requests\n"
        "import os\n"
        "import http.client\n"
        "import subprocess\n"
        "from pathlib import Path\n"
        "def f(p):\n"
        "    requests.get('http://x')\n"
        "    os.getenv('OPENROUTER_API_KEY')\n"
        "    os.environ['OPENROUTER_API_KEY']\n"
        "    subprocess.run(['ls'])\n"
        "    open('x.txt', 'w')\n"
        "    Path('y').write_text('z')\n"
        "    return source_authority\n"
    )
    violations = _scan_source(bad_src)
    assert any("import requests" in v for v in violations)
    assert any("import http.client" in v for v in violations)
    assert any("getenv('OPENROUTER_API_KEY')" in v for v in violations)
    assert any("os.environ" in v for v in violations)
    assert any("subprocess.run" in v for v in violations)
    assert any("open(..., 'w')" in v for v in violations)
    assert any("write_text" in v for v in violations)
    assert any("source_authority" in v for v in violations)
    assert len(violations) >= 8


def test_module_does_not_import_os():
    """No os import at all -> the module structurally cannot read any env var/key."""
    tree = ast.parse(ADAPTER_SRC.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add((node.module or "").split(".")[0])
    assert "os" not in imported, f"adapter must not import os; imported={sorted(imported)}"


# ---------------------------------------------------------------------------
# Contract shape
# ---------------------------------------------------------------------------


def _mock_request(panel=None, mode=FusionMode.MOCK):
    return FusionRequest(
        task_id="task-1",
        prompt_digest=digest("hello"),
        panel_models=panel if panel is not None else ["m1", "m2", "m3"],
        slice_id="HERMES_FUSION_ADAPTER_CONTRACT_PHASE1",
        mode=mode,
    )


def test_contract_dataclasses_typed_fields():
    req = _mock_request()
    assert req.panel_models == ["m1", "m2", "m3"]
    assert req.mode is FusionMode.MOCK
    analysis = FusionAnalysis(consensus="c")
    assert analysis.contradictions == [] and analysis.blind_spots == []
    # MockFusionAdapter satisfies the runtime-checkable Protocol
    assert isinstance(MockFusionAdapter(), FusionAdapter)


def test_protocol_provider_is_mock():
    assert MockFusionAdapter().provider is FusionProvider.MOCK


# ---------------------------------------------------------------------------
# Mock dry-run advisory behaviour
# ---------------------------------------------------------------------------


def test_mock_run_returns_advisory_receipt():
    receipt = MockFusionAdapter().run(_mock_request())
    assert receipt.advisory_not_canonical is True
    assert receipt.redaction_status == REDACTION_BLOCKED
    assert receipt.later_verified_outcome == NOT_EVALUATED
    assert receipt.wsp97_status == NOT_EVALUATED
    assert receipt.failed_models == []
    assert receipt.provider == FusionProvider.MOCK.value
    assert receipt.consensus.startswith("[MOCK advisory]")
    # receipt round-trips and never claims a gate pass
    d = receipt.to_dict()
    assert d["advisory_not_canonical"] is True
    assert "gate_passed" not in d and "cabr_ready" not in d


def test_dry_run_mode_executes():
    receipt = MockFusionAdapter().run(_mock_request(mode=FusionMode.DRY_RUN))
    assert receipt.mode == FusionMode.DRY_RUN.value
    assert receipt.advisory_not_canonical is True


def test_mock_is_deterministic():
    r1 = MockFusionAdapter().run(_mock_request())
    r2 = MockFusionAdapter().run(_mock_request())
    assert r1.receipt_id == r2.receipt_id
    assert r1.consensus == r2.consensus
    assert r1.response_digest == r2.response_digest


# ---------------------------------------------------------------------------
# Receipt truth boundary
# ---------------------------------------------------------------------------


def test_receipt_cannot_be_non_canonical():
    with pytest.raises(ValueError):
        ModelContributionReceipt(
            receipt_id="r",
            task_id="t",
            provider="mock",
            mode="mock",
            outer_model="o",
            panel_models=["m"],
            judge_model="j",
            prompt_digest="d",
            response_digest="d2",
            consensus="c",
            advisory_not_canonical=False,
        )


def test_receipt_to_dict_reasserts_truth_boundary():
    # dataclass fields are mutable; a post-construction flip must not serialize as canonical
    receipt = MockFusionAdapter().run(_mock_request())
    receipt.advisory_not_canonical = False
    with pytest.raises(ValueError):
        receipt.to_dict()


def test_receipt_defaults_do_not_imply_verified_or_gate_pass():
    receipt = ModelContributionReceipt(
        receipt_id="r",
        task_id="t",
        provider="mock",
        mode="mock",
        outer_model="o",
        panel_models=["m"],
        judge_model="j",
        prompt_digest="d",
        response_digest="d2",
        consensus="c",
    )
    assert receipt.later_verified_outcome == NOT_EVALUATED
    assert receipt.wsp97_status == NOT_EVALUATED
    assert receipt.redaction_status == REDACTION_BLOCKED
    assert receipt.accepted_by_judge is False
    assert receipt.advisory_not_canonical is True


def test_receipt_stores_digests_not_raw_context():
    # FusionRequest has no raw context/prompt field; for_mock digests inputs.
    req = FusionRequest.for_mock(
        "task-x", "secret prompt body", ["a", "b"], raw_context="secret context body"
    )
    assert not hasattr(req, "context_text")
    assert not hasattr(req, "raw_prompt")
    assert req.prompt_digest.startswith("sha256:")
    assert req.context_digest and req.context_digest.startswith("sha256:")
    assert "secret prompt body" not in req.prompt_digest
    assert "secret context body" not in (req.context_digest or "")
    receipt = MockFusionAdapter().run(req)
    blob = json.dumps(receipt.to_dict())
    assert "secret prompt body" not in blob
    assert "secret context body" not in blob


# ---------------------------------------------------------------------------
# Future live modes are declared but UNREACHABLE
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "mode", [FusionMode.ALIAS, FusionMode.SERVER_TOOL, FusionMode.LOCAL_FALLBACK]
)
def test_future_live_modes_raise(mode):
    with pytest.raises(RedactionGateBlocked):
        MockFusionAdapter().run(_mock_request(mode=mode))


def test_executable_vs_future_mode_partition():
    assert EXECUTABLE_MODES == frozenset({FusionMode.MOCK, FusionMode.DRY_RUN})
    assert FusionMode.ALIAS in FUTURE_BLOCKED_MODES
    assert FusionMode.SERVER_TOOL in FUTURE_BLOCKED_MODES
    assert FusionMode.LOCAL_FALLBACK in FUTURE_BLOCKED_MODES
    assert EXECUTABLE_MODES.isdisjoint(FUTURE_BLOCKED_MODES)


# ---------------------------------------------------------------------------
# Panel bounds
# ---------------------------------------------------------------------------


def test_panel_bounds_reject_zero():
    with pytest.raises(ValueError):
        _mock_request(panel=[])


def test_panel_bounds_reject_over_eight():
    with pytest.raises(ValueError):
        _mock_request(panel=[f"m{i}" for i in range(MAX_PANEL_MODELS + 1)])


def test_panel_bounds_accept_one_and_eight():
    assert MockFusionAdapter().run(_mock_request(panel=["m1"])).panel_models == ["m1"]
    eight = [f"m{i}" for i in range(MAX_PANEL_MODELS)]
    assert len(MockFusionAdapter().run(_mock_request(panel=eight)).panel_models) == MAX_PANEL_MODELS
    assert MIN_PANEL_MODELS == 1 and MAX_PANEL_MODELS == 8


# ---------------------------------------------------------------------------
# No-live proof: zero network even if a socket is attempted
# ---------------------------------------------------------------------------


def test_mock_run_performs_zero_network(monkeypatch):
    def _boom(*args, **kwargs):
        raise AssertionError("network access attempted by FusionAdapter mock path")

    monkeypatch.setattr(socket, "socket", _boom)
    receipt = MockFusionAdapter().run(_mock_request())
    assert receipt.advisory_not_canonical is True


# ---------------------------------------------------------------------------
# Manifest honesty
# ---------------------------------------------------------------------------


def test_manifest_openrouter_no_longer_claims_landed():
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    integrations = data.get("integrations", data if isinstance(data, list) else [])
    entry = next(e for e in integrations if e.get("name") == "OpenRouter")
    assert entry["status"] != "landed"
    assert entry["status"] in HONEST_NON_LANDED_STATUSES
    # the precise contract-pending / redaction-gate semantics are carried in notes
    assert "BLOCKED_PENDING_REDACTION_GATE" in entry.get("notes", "")


# ---------------------------------------------------------------------------
# Digest format guard (sha256:<64 hex>) -- raw prompt/context must fail early
# ---------------------------------------------------------------------------


def test_digest_produces_valid_sha256_64hex():
    d = digest("anything")
    assert d.startswith("sha256:")
    assert len(d) == len("sha256:") + DIGEST_HEX_LEN
    assert is_valid_digest(d) is True


@pytest.mark.parametrize(
    "bad",
    [
        "raw prompt text",        # raw text
        "",                       # empty
        "sha256:",                # prefix only
        "deadbeef" * 8,           # 64 hex but no prefix
        "sha256:" + "g" * 64,     # non-hex body
        "sha256:" + "a" * 63,     # too short
        "sha256:" + "a" * 65,     # too long
        "SHA256:" + "a" * 64,     # wrong-case prefix
        "md5:" + "a" * 64,        # wrong algo prefix
        None,                     # not a string
        123,                      # not a string
    ],
)
def test_is_valid_digest_rejects_bad(bad):
    assert is_valid_digest(bad) is False


def test_is_valid_digest_accepts_real_digest():
    assert is_valid_digest(digest("x")) is True


def test_raw_prompt_in_prompt_digest_rejected():
    with pytest.raises(ValueError):
        FusionRequest(task_id="t", prompt_digest="raw prompt text", panel_models=["m"])


def test_empty_prompt_digest_rejected():
    with pytest.raises(ValueError):
        FusionRequest(task_id="t", prompt_digest="", panel_models=["m"])


def test_raw_context_in_context_digest_rejected():
    with pytest.raises(ValueError):
        FusionRequest(
            task_id="t",
            prompt_digest=digest("p"),
            panel_models=["m"],
            context_digest="raw context body",
        )


def test_valid_digests_accepted():
    req = FusionRequest(
        task_id="t",
        prompt_digest=digest("p"),
        panel_models=["m"],
        context_digest=digest("c"),
    )
    assert is_valid_digest(req.prompt_digest)
    assert is_valid_digest(req.context_digest)


def test_none_context_digest_accepted():
    req = FusionRequest(task_id="t", prompt_digest=digest("p"), panel_models=["m"])
    assert req.context_digest is None


def test_for_mock_produces_valid_digests_and_no_raw_in_receipt():
    req = FusionRequest.for_mock(
        "t", "secret prompt body", ["a", "b"], raw_context="secret context body"
    )
    assert is_valid_digest(req.prompt_digest)
    assert is_valid_digest(req.context_digest)
    receipt = MockFusionAdapter().run(req)
    assert is_valid_digest(receipt.prompt_digest)
    blob = json.dumps(receipt.to_dict())
    assert "secret prompt body" not in blob
    assert "secret context body" not in blob
