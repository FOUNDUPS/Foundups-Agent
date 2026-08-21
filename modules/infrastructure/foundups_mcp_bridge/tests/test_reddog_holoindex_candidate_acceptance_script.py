"""CLI contracts for the isolated HoloIndex acceptance adapter."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace


SCRIPT = Path(__file__).resolve().parents[4] / "scripts" / "reddog_holoindex_candidate_acceptance.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("reddog_acceptance_script", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _argv(tmp_path: Path) -> list[str]:
    return [
        "--candidate-root",
        str(tmp_path / "candidate"),
        "--authority-root",
        str(tmp_path / "authority"),
        "--runtime-root",
        str(tmp_path / "runtime"),
        "--canonical-store",
        str(tmp_path / "canonical"),
        "--isolated-store",
        str(tmp_path / "isolated"),
        "--receipt-path",
        str(tmp_path / "receipts" / "acceptance.json"),
        "--expected-sha",
        "a" * 40,
    ]


def _run_with_import_bomb(tmp_path: Path, argv: list[str]) -> subprocess.CompletedProcess[str]:
    bomb_root = tmp_path / "import-bomb"
    bomb_root.mkdir()
    (bomb_root / "sitecustomize.py").write_text(
        "import builtins\n"
        "_real_import = builtins.__import__\n"
        "_blocked = (\n"
        " 'modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_candidate_acceptance',\n"
        " 'modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_maintenance_handshake',\n"
        " 'modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_owner_bootstrap',\n"
        " 'modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_acceptance_model_copy',\n"
        " 'modules.communication.moltbot_bridge.src.reddog_holoindex_owner_query_client',\n"
        ")\n"
        "def _guarded_import(name, globals=None, locals=None, fromlist=(), level=0):\n"
        " if any(name == item or name.startswith(item + '.') for item in _blocked):\n"
        "  raise RuntimeError('FORBIDDEN_ACCEPTANCE_IMPORT')\n"
        " return _real_import(name, globals, locals, fromlist, level)\n"
        "builtins.__import__ = _guarded_import\n",
        encoding="utf-8",
    )
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(bomb_root)
    environment["PYTHONNOUSERSITE"] = "1"
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, str(SCRIPT), *argv],
        cwd=str(SCRIPT.parents[1]),
        env=environment,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )


def test_cli_without_real_uses_stdlib_only_and_emits_stable_not_run(
    tmp_path: Path,
) -> None:
    completed = _run_with_import_bomb(tmp_path, _argv(tmp_path))
    assert completed.returncode == 2
    assert completed.stderr == ""
    assert json.loads(completed.stdout) == {
        "error": "",
        "freshness_receipt_digest": "",
        "generation_id": "",
        "receipt_published": False,
        "status": "REAL_MODE_REQUIRED",
        "verdict": "NOT_RUN",
    }


def test_cli_malformed_input_never_crosses_acceptance_import_boundary(
    tmp_path: Path,
) -> None:
    completed = _run_with_import_bomb(tmp_path, ["--candidate-root", "relative"])
    assert completed.returncode == 2
    assert "FORBIDDEN_ACCEPTANCE_IMPORT" not in completed.stderr


def test_cli_requires_runtime_root_before_acceptance_import(tmp_path: Path) -> None:
    argv = _argv(tmp_path)
    runtime_index = argv.index("--runtime-root")
    del argv[runtime_index : runtime_index + 2]

    completed = _run_with_import_bomb(tmp_path, argv)

    assert completed.returncode == 2
    assert "--runtime-root" in completed.stderr
    assert "FORBIDDEN_ACCEPTANCE_IMPORT" not in completed.stderr


def test_cli_default_is_inert_and_emits_stable_json(
    tmp_path: Path, capsys, monkeypatch
) -> None:
    module = _load_script()
    loads = []
    monkeypatch.setattr(
        module,
        "_load_candidate_acceptance",
        lambda: loads.append(True),
    )
    assert module.main(_argv(tmp_path)) == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload == {
        "error": "",
        "freshness_receipt_digest": "",
        "generation_id": "",
        "receipt_published": False,
        "status": "REAL_MODE_REQUIRED",
        "verdict": "NOT_RUN",
    }
    assert loads == []


def test_cli_real_flag_is_the_only_real_mode_activation(
    tmp_path: Path, capsys, monkeypatch
) -> None:
    module = _load_script()
    loads = []
    calls = []

    def load_contract():
        loads.append(True)
        return (
            SimpleNamespace,
            SimpleNamespace,
            lambda config: calls.append(config)
            or SimpleNamespace(
                verdict="PASS",
                status="COMPLETED",
                error="",
                receipt_published=True,
                generation_id="sha256:" + "b" * 64,
                freshness_receipt_digest="sha256:" + "c" * 64,
            ),
        )

    monkeypatch.setattr(
        module,
        "_load_candidate_acceptance",
        load_contract,
    )
    assert module.main([*_argv(tmp_path), "--real"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["verdict"] == "PASS"
    assert loads == [True]
    assert len(calls) == 1
    assert calls[0].real_mode is True
    assert calls[0].port == 8127
    assert calls[0].candidate_root == tmp_path / "candidate"
    assert calls[0].authority_root == tmp_path / "authority"
    assert calls[0].owner_runtime_root == tmp_path / "runtime"
    assert calls[0].canonical_store == tmp_path / "canonical"
    assert calls[0].isolated_store == tmp_path / "isolated"
    assert calls[0].receipt_path == tmp_path / "receipts" / "acceptance.json"
    assert calls[0].expected_sha == "a" * 40


def test_cli_fail_result_has_nonzero_exit_without_raw_exception(
    tmp_path: Path, capsys, monkeypatch
) -> None:
    module = _load_script()
    calls = []
    monkeypatch.setattr(
        module,
        "_load_candidate_acceptance",
        lambda: (
            SimpleNamespace,
            SimpleNamespace,
            lambda config: calls.append(config)
            or SimpleNamespace(
                verdict="FAIL",
                status="COMPLETED",
                error="DIRECT_QUERY_PROOF_INVALID",
                receipt_published=True,
                generation_id="sha256:" + "b" * 64,
                freshness_receipt_digest="sha256:" + "c" * 64,
            ),
        ),
    )
    assert module.main([*_argv(tmp_path), "--real"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"] == "DIRECT_QUERY_PROOF_INVALID"
    assert len(calls) == 1
