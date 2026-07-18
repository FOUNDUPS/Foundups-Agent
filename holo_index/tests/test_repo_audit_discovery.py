"""Focused contracts for RedDog repository-audit grounding."""

from __future__ import annotations

import ast
import inspect
import os
from pathlib import Path

import pytest

from holo_index.cli import repo_audit_discovery as discovery


@pytest.mark.parametrize("alias", ["pfmall", "p.fMALL", "p-fmall", "PFMALL"])
def test_pfmall_aliases_resolve_to_one_safe_entity(alias):
    receipt = discovery.detect_repo_audit_intent(f"Audit the {alias} codebase")
    assert receipt["audit_intent"] is True
    assert receipt["entity"] == "pfmall"


@pytest.mark.parametrize(
    "prompt",
    ["audit ../../pfmall codebase", "audit C:/pfmall codebase", "audit pfmall/other module", "audit \x00pfmall module"],
)
def test_path_syntax_cannot_become_entity(prompt):
    result = discovery.detect_repo_audit_intent(prompt)
    assert result["entity"] != "pfmall" or result["audit_intent"] is False


def _seed_pfmall(root: Path) -> None:
    module = root / "modules" / "foundups" / "pfmall"
    (module / "tests").mkdir(parents=True)
    (module / "api.py").write_text("def list_items():\n    return []\n", encoding="utf-8")
    (module / "tests" / "test_api.py").write_text("def test_list_items():\n    assert True\n", encoding="utf-8")
    (module / "__init__.py").write_text("\"\"\"PFMall module.\"\"\"\n", encoding="utf-8")
    (root / "docs").mkdir()
    (root / "docs" / "PFMALL_README.md").write_text("PFMall public contract.\n", encoding="utf-8")


def test_weak_holo_uses_deterministic_fallback_and_selects_source_plus_test(tmp_path):
    _seed_pfmall(tmp_path)
    weak_holo = {"code_hits": [{"location": "docs/PFMALL_README.md", "summary": "adjacent documentation"}]}
    result = discovery.build_repo_audit_grounding(tmp_path, "audit pfmall codebase", weak_holo)
    receipt = result["receipt"]
    assert receipt["holo_first"] is True
    assert receipt["holo_evidence_sufficient"] is False
    assert receipt["search_mode"] == "holo_then_deterministic"
    assert receipt["coverage"] == {"verdict": "PASS", "reasons": []}
    categories = {item["category"] for item in receipt["selected"]}
    assert "implementation_source" in categories
    assert "test" in categories
    assert any(item["path"] == "modules/foundups/pfmall/api.py" for item in receipt["selected"])
    assert all(hit["direct_read"] is True and hit["content"] for hit in result["hits"])


def test_strong_holo_avoids_deterministic_walk(tmp_path, monkeypatch):
    _seed_pfmall(tmp_path)
    strong = {"code_hits": [
        {"location": "modules/foundups/pfmall/api.py", "content": "source"},
        {"location": "modules/foundups/pfmall/tests/test_api.py", "content": "test"},
    ]}
    monkeypatch.setattr(discovery, "_discover", lambda *_args, **_kwargs: pytest.fail("fallback must not run"))
    receipt = discovery.build_repo_audit_grounding(tmp_path, "critically review pfmall module", strong)["receipt"]
    assert receipt["search_mode"] == "holo_evidence_only"
    assert receipt["holo_evidence_sufficient"] is True
    assert receipt["coverage"]["verdict"] == "PASS"


def test_receipt_and_digests_are_stable(tmp_path):
    _seed_pfmall(tmp_path)
    first = discovery.build_repo_audit_grounding(tmp_path, "audit p.fMALL codebase", {})["receipt"]
    second = discovery.build_repo_audit_grounding(tmp_path, "audit p.fMALL codebase", {})["receipt"]
    assert first == second
    assert first["selected"]
    assert all(item["digest"].startswith("sha256:") for item in first["selected"])


def test_selected_evidence_obeys_count_and_byte_budgets(tmp_path):
    _seed_pfmall(tmp_path)
    module = tmp_path / "modules" / "foundups" / "pfmall"
    for index in range(20):
        (module / f"pfmall_component_{index}.py").write_bytes(b"x" * 13_000)
    result = discovery.build_repo_audit_grounding(tmp_path, "audit pfmall codebase", {})
    selected = result["receipt"]["selected"]
    assert len(selected) <= discovery.MAX_SELECTED_PATHS
    assert all(item["bytes"] <= discovery.PER_FILE_READ_BYTES for item in selected)
    assert sum(item["bytes"] for item in selected) <= discovery.TOTAL_READ_BUDGET_BYTES


@pytest.mark.parametrize(
    ("path", "reason"),
    [
        ("../outside.py", "traversal"),
        ("/etc/passwd", "absolute_path"),
        ("C:/Windows/system.ini", "absolute_path"),
        ("bad\x00.py", "nul_path"),
        ("config/client_secret.py", "secret_like_path"),
        ("vendor/library.py", "pruned_path"),
        ("generated/client.py", "pruned_path"),
    ],
)
def test_secure_reader_rejects_unsafe_path_classes(tmp_path, path, reason):
    result = discovery.secure_read_repo_file(tmp_path, path)
    assert result == {"ok": False, "path": path.replace("\\", "/"), "reason": reason}


def test_secure_reader_rejects_binary_oversize_and_budget(tmp_path, monkeypatch):
    (tmp_path / "binary.py").write_bytes(b"safe\x00binary")
    assert discovery.secure_read_repo_file(tmp_path, "binary.py")["reason"] == "binary"

    (tmp_path / "large.py").write_bytes(b"x" * 32)
    monkeypatch.setattr(discovery, "MAX_FILE_SIZE_BYTES", 16)
    assert discovery.secure_read_repo_file(tmp_path, "large.py")["reason"] == "oversize"
    assert discovery.secure_read_repo_file(tmp_path, "large.py", remaining_budget=0)["reason"] == "oversize"

    monkeypatch.setattr(discovery, "MAX_FILE_SIZE_BYTES", 1024)
    assert discovery.secure_read_repo_file(tmp_path, "large.py", remaining_budget=0)["reason"] == "budget_exhausted"


def test_secure_reader_respects_per_file_and_total_budget(tmp_path):
    (tmp_path / "source.py").write_bytes(b"x" * 64)
    result = discovery.secure_read_repo_file(tmp_path, "source.py", byte_cap=12, remaining_budget=7)
    assert result["ok"] is True
    assert result["bytes"] == 7
    assert result["truncated"] is True


def test_secure_reader_rejects_symlink_component(tmp_path):
    target = tmp_path / "target.py"
    target.write_text("safe", encoding="utf-8")
    link = tmp_path / "linked.py"
    try:
        os.symlink(target, link)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation unavailable")
    assert discovery.secure_read_repo_file(tmp_path, "linked.py")["reason"] == "reparse_component"


def test_secure_reader_rejects_reparse_or_junction_component(tmp_path, monkeypatch):
    nested = tmp_path / "module"
    nested.mkdir()
    (nested / "source.py").write_text("safe", encoding="utf-8")
    real_check = discovery._is_reparse_or_link

    def fake_check(path):
        if os.path.basename(os.fspath(path)) == "module":
            return True
        return real_check(path)

    monkeypatch.setattr(discovery, "_is_reparse_or_link", fake_check)
    assert discovery.secure_read_repo_file(tmp_path, "module/source.py")["reason"] == "reparse_component"


def test_secure_reader_detects_identity_race_after_open(tmp_path):
    original = tmp_path / "source.py"
    original.write_text("original", encoding="utf-8")

    def replace_path():
        original.rename(tmp_path / "old.py")
        original.write_text("replacement", encoding="utf-8")

    result = discovery.secure_read_repo_file(tmp_path, "source.py", post_open_hook=replace_path)
    assert result["reason"] == "identity_changed"


def test_secure_reader_fails_closed_when_final_handle_path_is_unavailable(tmp_path, monkeypatch):
    (tmp_path / "source.py").write_text("safe", encoding="utf-8")
    monkeypatch.setattr(discovery, "_fd_final_path", lambda _fd: None)
    result = discovery.secure_read_repo_file(tmp_path, "source.py")
    assert result["reason"] == "final_path_unavailable"


def test_discovery_prunes_secret_vendor_generated_and_reparse(tmp_path):
    _seed_pfmall(tmp_path)
    for folder in ("vendor", "generated"):
        path = tmp_path / folder
        path.mkdir()
        (path / "pfmall.py").write_text("pfmall", encoding="utf-8")
    (tmp_path / "pfmall_secret.py").write_text("pfmall", encoding="utf-8")
    receipt = discovery.build_repo_audit_grounding(tmp_path, "audit pfmall codebase", {})["receipt"]
    selected = {item["path"] for item in receipt["selected"]}
    assert not any(path.startswith(("vendor/", "generated/")) for path in selected)
    assert "pfmall_secret.py" not in selected
    assert receipt["exclusion_counts"]["pruned"] >= 2


def test_non_audit_zero_target_behavior_is_unchanged(tmp_path):
    result = discovery.build_repo_audit_grounding(tmp_path, "explain current architecture", {})
    assert result["receipt"]["applied"] is False
    assert result["hits"] == []
    assert result["telemetry"] is None


def test_module_contains_no_subprocess_or_shell_execution():
    source = inspect.getsource(discovery)
    assert "subprocess" not in source
    assert "shell=True" not in source
    assert "os.system" not in source
    tree = ast.parse(source)
    assert all(
        node.end_lineno - node.lineno + 1 <= 50
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    )
