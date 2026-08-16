"""Focused contracts for RedDog repository-audit grounding."""

from __future__ import annotations

import ast
import inspect
import os
from pathlib import Path
import subprocess
import sys

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
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "test@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "Test"], check=True)
    subprocess.run(["git", "-C", str(root), "add", "modules", "docs"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "fixture"], check=True)


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


@pytest.mark.parametrize("unreadable", ["source", "test"])
def test_holo_sufficiency_requires_readable_source_and_test(tmp_path, monkeypatch, unreadable):
    _seed_pfmall(tmp_path)
    strong = {"code_hits": [
        {"location": "modules/foundups/pfmall/api.py", "content": "stale cached source"},
        {"location": "modules/foundups/pfmall/tests/test_api.py", "content": "stale cached test"},
    ]}
    blocked = strong["code_hits"][0 if unreadable == "source" else 1]["location"]
    real_read = discovery.secure_read_repo_head_file
    calls = {blocked: 0}

    def deny_holo_read(repo_root, raw_path, **kwargs):
        if raw_path == blocked and calls[blocked] == 0:
            calls[blocked] += 1
            return {"ok": False, "path": raw_path, "reason": "read_error"}
        return real_read(repo_root, raw_path, **kwargs)

    monkeypatch.setattr(discovery, "secure_read_repo_head_file", deny_holo_read)
    receipt = discovery.build_repo_audit_grounding(tmp_path, "audit pfmall codebase", strong)["receipt"]
    assert receipt["holo_evidence_sufficient"] is False
    assert receipt["search_mode"] == "holo_then_deterministic"
    assert receipt["coverage"]["verdict"] == "PASS"
    assert receipt["deterministic_candidates"]


def test_stale_holo_paths_trigger_fallback(tmp_path):
    _seed_pfmall(tmp_path)
    stale = {"code_hits": [
        {"location": "modules/foundups/pfmall/missing.py", "content": "stale source"},
        {"location": "modules/foundups/pfmall/tests/missing_test.py", "content": "stale test"},
    ]}
    receipt = discovery.build_repo_audit_grounding(tmp_path, "audit pfmall codebase", stale)["receipt"]
    assert receipt["holo_evidence_sufficient"] is False
    assert receipt["search_mode"] == "holo_then_deterministic"
    assert receipt["coverage"]["verdict"] == "PASS"
    assert {item["path"] for item in receipt["selected"]}.issuperset({
        "modules/foundups/pfmall/api.py",
        "modules/foundups/pfmall/tests/test_api.py",
    })


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


def test_secure_reader_rejects_hardlink(tmp_path):
    outside = tmp_path / "outside.py"
    outside.write_text("outside", encoding="utf-8")
    linked = tmp_path / "linked.py"
    try:
        os.link(outside, linked)
    except OSError:
        pytest.skip("hardlink creation unavailable")
    assert discovery.secure_read_repo_file(tmp_path, "linked.py")["reason"] == "hardlink_rejected"


def test_head_reader_ignores_dirty_overlay_and_untracked_file(tmp_path):
    _seed_pfmall(tmp_path)
    source = tmp_path / "modules" / "foundups" / "pfmall" / "api.py"
    source.write_text("ATTACKER_OVERLAY = True\n", encoding="utf-8")
    untracked = source.with_name("pfmall_untracked.py")
    untracked.write_text("ATTACKER_UNTRACKED = True\n", encoding="utf-8")

    committed = discovery.secure_read_repo_head_file(
        tmp_path, "modules/foundups/pfmall/api.py"
    )
    rejected = discovery.secure_read_repo_head_file(
        tmp_path, "modules/foundups/pfmall/pfmall_untracked.py"
    )

    assert committed["ok"] is True
    assert "list_items" in committed["content"]
    assert "ATTACKER_OVERLAY" not in committed["content"]
    assert rejected["reason"] == "not_committed"


def test_head_reader_ignores_attacker_git_replacement_object(tmp_path):
    _seed_pfmall(tmp_path)
    path = "modules/foundups/pfmall/api.py"
    original_oid = subprocess.run(
        ["git", "-C", str(tmp_path), "rev-parse", f"HEAD:{path}"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    attacker_oid = subprocess.run(
        ["git", "-C", str(tmp_path), "hash-object", "-w", "--stdin"],
        input=b"ATTACKER_REPLACEMENT = True\n", check=True, capture_output=True,
    ).stdout.decode("ascii").strip()
    subprocess.run(
        ["git", "-C", str(tmp_path), "replace", original_oid, attacker_oid], check=True
    )
    ordinary = subprocess.run(
        ["git", "-C", str(tmp_path), "cat-file", "blob", original_oid],
        check=True, capture_output=True, text=True,
    ).stdout

    result = discovery.secure_read_repo_head_file(tmp_path, path)

    assert "ATTACKER_REPLACEMENT" in ordinary
    assert result["ok"] is True
    assert "list_items" in result["content"]
    assert result["blob_oid"] == original_oid


def test_head_reader_rejects_committed_symlink_mode(tmp_path):
    _seed_pfmall(tmp_path)
    linked_path = "modules/foundups/pfmall/linked.py"
    blob_oid = subprocess.run(
        ["git", "-C", str(tmp_path), "hash-object", "-w", "--stdin"],
        input=b"api.py\n", check=True, capture_output=True,
    ).stdout.decode("ascii").strip()
    subprocess.run(
        [
            "git", "-C", str(tmp_path), "update-index", "--add", "--cacheinfo",
            "120000", blob_oid, linked_path,
        ],
        check=True,
    )
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-qm", "symlink"], check=True)

    result = discovery.secure_read_repo_head_file(tmp_path, linked_path)

    assert result["reason"] == "git_mode_rejected"


def test_head_reader_sanitizes_inherited_git_control_environment(tmp_path, monkeypatch):
    _seed_pfmall(tmp_path)
    monkeypatch.setenv("GIT_DIR", str(tmp_path / "attacker.git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(tmp_path / "attacker-tree"))
    monkeypatch.setenv("GIT_OBJECT_DIRECTORY", str(tmp_path / "attacker-objects"))
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "core.useReplaceRefs")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "true")

    result = discovery.secure_read_repo_head_file(
        tmp_path, "modules/foundups/pfmall/api.py"
    )

    assert result["ok"] is True
    assert "list_items" in result["content"]


def test_head_reader_uses_exact_command_scoped_ownership_and_read_guards(
    tmp_path, monkeypatch
):
    trusted_git = str(tmp_path / "trusted-git")
    monkeypatch.setattr(discovery, "_trusted_git_path", lambda: trusted_git)

    command = discovery._git_command(tmp_path, ("cat-file", "blob", "a" * 40))

    assert command[0] == trusted_git
    assert "--no-replace-objects" in command
    assert "--no-optional-locks" in command
    assert f"safe.directory={tmp_path}" in command
    null_path = "NUL" if sys.platform == "win32" else os.devnull
    assert f"core.hooksPath={null_path}" in command
    assert f"core.attributesFile={null_path}" in command
    assert f"core.excludesFile={null_path}" in command
    assert "diff.external=" in command


def test_head_reader_ignores_attacker_git_on_path(tmp_path, monkeypatch):
    _seed_pfmall(tmp_path)
    fake_bin = tmp_path / "attacker-bin"
    fake_bin.mkdir()
    (fake_bin / "git.exe").write_bytes(b"attacker controlled executable")
    monkeypatch.setenv("PATH", str(fake_bin))

    result = discovery.secure_read_repo_head_file(
        tmp_path, "modules/foundups/pfmall/api.py"
    )

    assert result["ok"] is True
    assert "list_items" in result["content"]


def test_head_reader_fails_closed_without_trusted_git(tmp_path, monkeypatch):
    _seed_pfmall(tmp_path)
    monkeypatch.setattr(discovery, "_trusted_git_path", lambda: None)

    result = discovery.secure_read_repo_head_file(
        tmp_path, "modules/foundups/pfmall/api.py"
    )

    assert result["ok"] is False


def test_head_reader_rejects_blob_bytes_that_do_not_match_tree_oid(tmp_path, monkeypatch):
    _seed_pfmall(tmp_path)
    real_read = discovery._read_git_blob_prefix

    def alter_blob(root, blob_oid, limit, deadline_monotonic):
        raw, complete = real_read(
            root, blob_oid, limit=limit, deadline_monotonic=deadline_monotonic
        )
        return b"X" + raw[1:], complete

    monkeypatch.setattr(discovery, "_read_git_blob_prefix", alter_blob)
    result = discovery.secure_read_repo_head_file(
        tmp_path, "modules/foundups/pfmall/api.py"
    )
    assert result["reason"] == "blob_oid_mismatch"


def test_blob_size_and_prefix_reads_share_one_absolute_deadline(tmp_path, monkeypatch):
    _seed_pfmall(tmp_path)
    captured = {}
    real_prepare = discovery._prepare_head_read
    real_blob = discovery._read_git_blob
    real_prefix = discovery._read_git_blob_prefix

    def capture_prepare(repo_root, rel_path, timeout_seconds):
        prepared = real_prepare(repo_root, rel_path, timeout_seconds)
        if not isinstance(prepared, dict):
            captured["prepared"] = prepared[2]
        return prepared

    def capture_blob(root, blob_oid, *, byte_cap, deadline_monotonic):
        captured["blob"] = deadline_monotonic
        return real_blob(
            root, blob_oid, byte_cap=byte_cap,
            deadline_monotonic=deadline_monotonic,
        )

    def capture_prefix(root, blob_oid, limit, deadline_monotonic):
        captured["prefix"] = deadline_monotonic
        return real_prefix(root, blob_oid, limit, deadline_monotonic)

    monkeypatch.setattr(discovery, "_prepare_head_read", capture_prepare)
    monkeypatch.setattr(discovery, "_read_git_blob", capture_blob)
    monkeypatch.setattr(discovery, "_read_git_blob_prefix", capture_prefix)
    result = discovery.secure_read_repo_head_file(
        tmp_path, "modules/foundups/pfmall/api.py", timeout_seconds=2.0
    )
    assert result["ok"] is True
    assert captured["prepared"] == captured["blob"] == captured["prefix"]


def test_head_reader_streams_only_the_bounded_prefix_of_large_blob(tmp_path):
    _seed_pfmall(tmp_path)
    target = tmp_path / "modules" / "foundups" / "pfmall" / "large.py"
    target.write_text("x" * 200_000, encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-qm", "large"], check=True)

    result = discovery.secure_read_repo_head_file(
        tmp_path, "modules/foundups/pfmall/large.py", byte_cap=1024,
        remaining_budget=1024,
    )

    assert result["ok"] is True
    assert result["bytes"] == 1024
    assert result["attempted_bytes"] == 1024
    assert result["truncated"] is True


def test_binary_blob_rejection_reports_attempted_bytes(tmp_path):
    _seed_pfmall(tmp_path)
    target = tmp_path / "modules" / "foundups" / "pfmall" / "binary.py"
    target.write_bytes(b"safe-prefix\x00binary-tail")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-qm", "binary"], check=True)

    result = discovery.secure_read_repo_head_file(
        tmp_path, "modules/foundups/pfmall/binary.py", byte_cap=1024,
        remaining_budget=1024,
    )

    assert result["ok"] is False
    assert result["reason"] == "blob_read_rejected"
    assert result["attempted_bytes"] == len(b"safe-prefix\x00binary-tail")


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
    for folder in ("vendor", "generated", ".worktrees"):
        path = tmp_path / folder
        path.mkdir()
        (path / "pfmall.py").write_text("pfmall", encoding="utf-8")
    (tmp_path / "pfmall_secret.py").write_text("pfmall", encoding="utf-8")
    receipt = discovery.build_repo_audit_grounding(tmp_path, "audit pfmall codebase", {})["receipt"]
    selected = {item["path"] for item in receipt["selected"]}
    assert not any(path.startswith(("vendor/", "generated/", ".worktrees/")) for path in selected)
    assert "pfmall_secret.py" not in selected
    assert receipt["exclusion_counts"]["pruned"] >= 3


def test_discovery_skips_windows_device_path_without_aborting(tmp_path, monkeypatch):
    _seed_pfmall(tmp_path)
    device_entry = tmp_path / "device.py"
    device_entry.write_text("pfmall", encoding="utf-8")
    real_relpath = discovery.os.path.relpath

    def reject_device_path(path, start):
        if os.fspath(path) == os.fspath(device_entry):
            raise ValueError("path is on mount '\\\\.\\nul'")
        return real_relpath(path, start)

    monkeypatch.setattr(discovery.os.path, "relpath", reject_device_path)
    receipt = discovery.build_repo_audit_grounding(
        tmp_path, "audit pfmall codebase", {}
    )["receipt"]
    assert receipt["coverage"]["verdict"] == "PASS"
    assert receipt["exclusion_counts"]["invalid_entry_path"] == 1
    assert all(item["path"] != "device.py" for item in receipt["selected"])


def test_discovery_never_enters_reads_or_selects_private_tool_state_roots(tmp_path, monkeypatch):
    _seed_pfmall(tmp_path)
    private_roots = sorted(discovery._PRIVATE_TOOL_STATE_SEGMENTS)
    for folder in private_roots:
        path = tmp_path / folder
        path.mkdir(exist_ok=True)
        (path / "pfmall_tool_state.py").write_text("pfmall private tool state", encoding="utf-8")

    scanned = []
    read_paths = []
    real_scandir = os.scandir
    real_read = discovery.secure_read_repo_head_file

    def track_scandir(path):
        scanned.append(os.path.relpath(os.fspath(path), os.fspath(tmp_path)).replace("\\", "/"))
        return real_scandir(path)

    def track_read(repo_root, raw_path, **kwargs):
        read_paths.append(str(raw_path).replace("\\", "/"))
        return real_read(repo_root, raw_path, **kwargs)

    monkeypatch.setattr(discovery.os, "scandir", track_scandir)
    monkeypatch.setattr(discovery, "secure_read_repo_head_file", track_read)
    private_holo = {"code_hits": [
        {"location": f"{private_roots[0]}/pfmall_tool_state.py", "content": "source"},
        {"location": f"{private_roots[-1]}/pfmall_tool_state.py", "content": "test"},
    ]}
    receipt = discovery.build_repo_audit_grounding(
        tmp_path, "audit pfmall codebase", private_holo
    )["receipt"]
    selected = [item["path"] for item in receipt["selected"]]
    for folder in private_roots:
        prefix = folder.casefold() + "/"
        assert not any(path.casefold() == folder.casefold() or path.casefold().startswith(prefix) for path in scanned)
        assert not any(path.casefold().startswith(prefix) for path in read_paths)
        assert not any(path.casefold().startswith(prefix) for path in selected)
        assert not any(path.casefold().startswith(prefix) for path in receipt["holo_evidence_refs"])


def test_non_audit_zero_target_behavior_is_unchanged(tmp_path):
    result = discovery.build_repo_audit_grounding(tmp_path, "explain current architecture", {})
    assert result["receipt"]["applied"] is False
    assert result["hits"] == []
    assert result["telemetry"] is None


def test_module_uses_only_fixed_argv_git_without_shell_execution():
    source = inspect.getsource(discovery)
    assert "shell=True" not in source
    assert "os.system" not in source
    tree = ast.parse(source)
    subprocess_calls = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "subprocess"
        and node.func.attr == "run"
    ]
    assert subprocess_calls
    assert all(
        any(keyword.arg == "shell" and keyword.value.value is False for keyword in node.keywords)
        for node in subprocess_calls
    )
    assert all(
        node.end_lineno - node.lineno + 1 <= 50
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    )
