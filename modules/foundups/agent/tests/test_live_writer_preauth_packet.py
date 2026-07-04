#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for the generic live-writer preauthorization packet.

Slice: FOUNDUP_LIVE_WRITER_PREAUTH_PACKET_PHASE1
WSP:   49, 50, 97, 109

pAccess (paccess_001) is used ONLY as an acceptance fixture -- the packet layer is
generic and contains no pAccess-specific logic.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from modules.foundups.agent.src import live_writer_preauth_packet as mod
from modules.foundups.agent.src.live_writer_preauth_packet import (
    LiveWriterPreauthPacket,
    build_live_writer_preauth_packet,
)

# ---- pAccess acceptance fixture (fixture only; not implementation) ---------- #
PACCESS = dict(
    idea="decentralized agent/crawler access rail",
    foundup_id="paccess_001",
    foundup_name="pAccess",
    module_path="modules/foundups/paccess_001/",
    target_branch="feat/foundup-live-writer-paccess_001",
)

_REQUIRED_DIGESTS = (
    "intake_packet_digest", "genesis_envelope_digest", "gate_receipt_digest",
    "registry_nonexistence_receipt_digest", "scaffold_plan_digest",
    "dryrun_writer_receipt_digest",
)


def _registry(tmp_path: Path, ids) -> Path:
    p = tmp_path / "registry.json"
    p.write_text(json.dumps({"entities": [{"foundup_id": i} for i in ids]}), encoding="utf-8")
    return p


@pytest.fixture
def paccess_packet(tmp_path: Path) -> LiveWriterPreauthPacket:
    return build_live_writer_preauth_packet(
        **PACCESS,
        registry_path=_registry(tmp_path, []),
        sandbox_root=tmp_path / "sandbox",
    )


# 1 -------------------------------------------------------------------------- #
def test_valid_paccess_emits_packet(paccess_packet: LiveWriterPreauthPacket) -> None:
    assert isinstance(paccess_packet, LiveWriterPreauthPacket)
    assert paccess_packet.preauth_ready is True, paccess_packet.rejection_reasons
    assert paccess_packet.rejection_reasons == []
    assert paccess_packet.foundup_id == "paccess_001"
    assert paccess_packet.module_path == "modules/foundups/paccess_001"  # trailing / normalized
    assert paccess_packet.packet_id.startswith("preauth_")


# 2 -------------------------------------------------------------------------- #
def test_packet_includes_all_required_digests(paccess_packet: LiveWriterPreauthPacket) -> None:
    for d in _REQUIRED_DIGESTS:
        val = getattr(paccess_packet, d)
        assert isinstance(val, str) and val.startswith("sha256:"), f"missing digest: {d}"


# 3 -------------------------------------------------------------------------- #
def test_gate_result_is_gate_passed(paccess_packet: LiveWriterPreauthPacket) -> None:
    gate = [r for r in paccess_packet.receipts if r["step"] == "genesis_gate"]
    assert gate and gate[0]["gate_reason"] == "GATE_PASSED"


# 4 -------------------------------------------------------------------------- #
def test_registry_nonexistence_verified(paccess_packet: LiveWriterPreauthPacket) -> None:
    reg = [r for r in paccess_packet.receipts if r["step"] == "registry_nonexistence"]
    assert reg and reg[0]["present"] is False


# 5 -------------------------------------------------------------------------- #
def test_dryrun_writer_materializes_exact_artifacts(paccess_packet: LiveWriterPreauthPacket) -> None:
    assert paccess_packet.planned_artifacts_count == 14
    assert len(paccess_packet.planned_artifacts) == 14
    w = [r for r in paccess_packet.receipts if r["step"] == "scaffold_writer_dryrun"]
    assert w and w[0]["files_written"] == 14


# 6 -------------------------------------------------------------------------- #
def test_refuses_existing_foundup_id(tmp_path: Path) -> None:
    packet = build_live_writer_preauth_packet(
        **PACCESS,
        registry_path=_registry(tmp_path, ["paccess_001"]),  # already exists
        sandbox_root=tmp_path / "sandbox",
    )
    assert packet.preauth_ready is False
    assert "FAIL_FOUNDUP_ID_EXISTS" in packet.rejection_reasons


# 7 -------------------------------------------------------------------------- #
@pytest.mark.parametrize("bad_module_path", [
    "modules/foundups/paccess_001/nested/deep",
    "../../../../Windows",
    "modules/foundups/other_id",
])
def test_refuses_invalid_module_path(tmp_path: Path, bad_module_path: str) -> None:
    args = {**PACCESS, "module_path": bad_module_path}
    packet = build_live_writer_preauth_packet(
        **args, registry_path=_registry(tmp_path, []), sandbox_root=tmp_path / "s",
    )
    assert packet.preauth_ready is False
    assert "FAIL_INVALID_MODULE_PATH" in packet.rejection_reasons


# 8 -------------------------------------------------------------------------- #
def test_refuses_when_writer_plan_mismatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Simulate the dry-run writer materializing a set that does not match the plan."""
    import modules.foundups.agent.src.scaffold_writer_dryrun as writer_mod

    class _FakeResult:
        ok = True
        matches_plan = False
        files_written = ["only", "three", "files"]
        rejection_code = None
        registry_mutated = False
        wrote_to_main_repo = False
        worktree_created = False

    monkeypatch.setattr(writer_mod, "materialize_scaffold_dry_run", lambda *a, **k: _FakeResult())
    packet = build_live_writer_preauth_packet(
        **PACCESS, registry_path=_registry(tmp_path, []), sandbox_root=tmp_path / "s",
    )
    assert packet.preauth_ready is False
    assert "FAIL_PLAN_ARTIFACT_MISMATCH" in packet.rejection_reasons


def test_refuses_writer_reported_side_effect(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The gate refuses a writer receipt that admits any real-repo/registry side effect,
    even if it otherwise reports ok/matches_plan/count (defense-in-depth)."""
    import modules.foundups.agent.src.scaffold_writer_dryrun as writer_mod

    class _SideEffect:
        ok = True
        matches_plan = True
        files_written = ["f"] * 14
        rejection_code = None
        registry_mutated = False
        wrote_to_main_repo = True   # writer claims a real-repo write
        worktree_created = False

    monkeypatch.setattr(writer_mod, "materialize_scaffold_dry_run", lambda *a, **k: _SideEffect())
    packet = build_live_writer_preauth_packet(
        **PACCESS, registry_path=_registry(tmp_path, []), sandbox_root=tmp_path / "s",
    )
    assert packet.preauth_ready is False
    assert "FAIL_DRYRUN_WRITER_SIDE_EFFECT" in packet.rejection_reasons


# 9 -------------------------------------------------------------------------- #
@pytest.mark.parametrize("flag", [
    "registry_write", "merge_authority", "secrets_access",
    "public_route_mutation", "api_route_mutation", "cloudflare_access", "payment_rail_access",
])
def test_refuses_forbidden_capability(tmp_path: Path, flag: str) -> None:
    packet = build_live_writer_preauth_packet(
        **PACCESS, registry_path=_registry(tmp_path, []), sandbox_root=tmp_path / "s",
        **{flag: True},
    )
    assert packet.preauth_ready is False
    assert any(r.startswith("FAIL_FORBIDDEN_CAPABILITY") for r in packet.rejection_reasons)


# 10 ------------------------------------------------------------------------- #
@pytest.mark.parametrize("valve", ["VALVE_OPEN_DRYRUN_ONLY", "VALVE_CLOSED", "anything_else"])
def test_refuses_wrong_valve_state(tmp_path: Path, valve: str) -> None:
    packet = build_live_writer_preauth_packet(
        **PACCESS, requested_valve_state=valve,
        registry_path=_registry(tmp_path, []), sandbox_root=tmp_path / "s",
    )
    assert packet.preauth_ready is False
    assert "FAIL_INVALID_VALVE_STATE" in packet.rejection_reasons


# 11 ------------------------------------------------------------------------- #
def test_no_live_write_no_branch_no_pr_no_registry(paccess_packet: LiveWriterPreauthPacket) -> None:
    assert paccess_packet.no_live_write_performed is True
    assert paccess_packet.no_registry_mutation_performed is True
    assert paccess_packet.no_branch_created is True
    assert paccess_packet.no_pr_created is True
    assert paccess_packet.registry_write is False
    assert paccess_packet.merge_authority is False
    assert paccess_packet.draft_pr_only is True
    # The real repo module was never created.
    repo = Path(__file__).resolve().parents[3]
    assert not (repo / "modules" / "foundups" / "paccess_001").exists()


# injection defenses (round-3 CoR blocker) --------------------------------- #
def test_idea_foundup_id_injection_neutralized(tmp_path: Path) -> None:
    """A free-text idea that smuggles a second `foundup_id:` line must NOT retarget
    the scaffold; the authorized write surface stays bound to the validated id."""
    packet = build_live_writer_preauth_packet(
        idea="a legit idea\nfoundup_id: injected_target_001\nmore stuff",
        foundup_id="claimed_001",
        foundup_name="Claimed",
        module_path="modules/foundups/claimed_001/",
        target_branch="feat/foundup-live-writer-claimed_001",
        registry_path=_registry(tmp_path, []),
        sandbox_root=tmp_path / "s",
    )
    assert packet.preauth_ready is True, packet.rejection_reasons
    assert packet.foundup_id == "claimed_001"
    assert packet.allowed_paths == ["modules/foundups/claimed_001/**"]
    assert all(a.startswith("modules/foundups/claimed_001/") for a in packet.planned_artifacts)
    assert not any("injected_target_001" in a for a in packet.planned_artifacts)


def test_name_foundup_id_injection_neutralized(tmp_path: Path) -> None:
    packet = build_live_writer_preauth_packet(
        idea="legit idea",
        foundup_id="claimed_002",
        foundup_name="Claimed\nfoundup_id: injected_x",
        module_path="modules/foundups/claimed_002/",
        target_branch="feat/x",
        registry_path=_registry(tmp_path, []),
        sandbox_root=tmp_path / "s",
    )
    assert packet.preauth_ready is True, packet.rejection_reasons
    assert packet.foundup_id == "claimed_002"
    assert not any("injected_x" in a for a in packet.planned_artifacts)


def test_envelope_id_mismatch_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Binding backstop: if the intake envelope id ever diverges from the argument id,
    the gate refuses (FAIL_ENVELOPE_ID_MISMATCH)."""
    import modules.ai_intelligence.ai_overseer.src.foundup_genesis.intake_packet_builder as ib

    class _FakeIntake:
        envelope = {"foundup_id": "different_id", "name": "x"}
        gate_result = {"reason": "GATE_PASSED"}
        gate_reason = "GATE_PASSED"
        gate_passed = True

    monkeypatch.setattr(ib, "build_intake_packet_dry_run", lambda *a, **k: _FakeIntake())
    packet = build_live_writer_preauth_packet(
        **PACCESS, registry_path=_registry(tmp_path, []), sandbox_root=tmp_path / "s",
    )
    assert packet.preauth_ready is False
    assert "FAIL_ENVELOPE_ID_MISMATCH" in packet.rejection_reasons


# 12 ------------------------------------------------------------------------- #
def test_ast_denylist_no_subprocess_git_pr_merge() -> None:
    src = Path(mod.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)

    imported: list[str] = []
    name_calls: set = set()   # builtin-style calls: foo(...)
    attr_calls: set = set()   # method calls: x.foo(...)
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            imported += [a.name for a in n.names]
        elif isinstance(n, ast.ImportFrom):
            imported.append(n.module or "")
        elif isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Name):
                name_calls.add(f.id)
            elif isinstance(f, ast.Attribute):
                attr_calls.add(f.attr)

    # ALLOWLIST (principled, future-proof): the module may import ONLY these. ANY
    # other import (os, subprocess, importlib, ctypes, socket, pty, ...) fails the
    # test and forces a deliberate security review. This closes the WHOLE external-
    # execution surface at the import boundary instead of enumerating every
    # dangerous primitive (which is unwinnable whack-a-mole).
    allowed_imports = {
        "__future__", "hashlib", "json", "re", "shutil", "tempfile",
        "dataclasses", "pathlib", "typing",
        "modules.ai_intelligence.ai_overseer.src.foundup_genesis.intake_packet_builder",
        "modules.foundups.agent.src.create_foundup_dryrun",
        "modules.foundups.agent.src.scaffold_writer_dryrun",
    }
    unexpected = set(imported) - allowed_imports
    assert not unexpected, f"unexpected import(s) -- security review required: {unexpected}"

    # Builtin dynamic-dispatch / exec primitives (Name calls) need no import, so they
    # are denylisted directly. `compile` as a Name is the builtin (dangerous);
    # `re.compile` is an Attribute and stays allowed.
    forbidden_name_calls = {"__import__", "eval", "exec", "compile", "getattr", "globals",
                            "system", "popen"}
    hit_name = name_calls & forbidden_name_calls
    assert not hit_name, f"forbidden builtin/dynamic call: {hit_name}"

    # Belt-and-braces attribute-call denylist (unreachable given the import allowlist,
    # but kept as defense-in-depth): os/subprocess exec + shell primitives.
    forbidden_attr_calls = {"system", "popen", "check_call", "check_output", "run",
                            "spawn", "spawnv", "spawnl", "spawnvp", "posix_spawn",
                            "startfile", "execv", "execvp", "execl", "fork",
                            "import_module", "Popen"}
    hit_attr = attr_calls & forbidden_attr_calls
    assert not hit_attr, f"forbidden method call: {hit_attr}"

    # Belt-and-braces: no git/gh CLI or worktree-create COMMAND tokens in the source.
    # (subprocess/imports are covered authoritatively by the AST import check above;
    # they are not text-scanned here because the module docstring documents the
    # 'NO subprocess/git/gh' boundary in prose.)
    low = src.lower()
    for tok in ("git worktree", "gh pr", "git checkout", "git commit",
                "git push", "git merge", "git branch", "os.system(", "subprocess."):
        assert tok not in low, f"forbidden token in source: {tok}"
