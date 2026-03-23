import asyncio
from pathlib import Path

from holo_index.monitoring.root_violation_monitor.src.root_violation_monitor import (
    GemmaRootViolationMonitor,
)


def _write(path: Path, content: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_scan_root_violations_allows_repo_level_configs(tmp_path):
    _write(tmp_path / "firebase.json")
    _write(tmp_path / "firestore.rules")
    _write(tmp_path / "firestore.indexes.json")
    _write(tmp_path / ".firebaserc")
    _write(tmp_path / "pyrightconfig.json")
    _write(tmp_path / "check_port_sentinel.py", "print('probe')\n")

    monitor = GemmaRootViolationMonitor(repo_root=tmp_path)
    monitor.telemetry_logger = None

    result = asyncio.run(monitor.scan_root_violations())
    violations = {item["filename"]: item for item in result["violations"]}

    assert "firebase.json" not in violations
    assert "firestore.rules" not in violations
    assert "firestore.indexes.json" not in violations
    assert ".firebaserc" not in violations
    assert "pyrightconfig.json" not in violations
    assert violations["check_port_sentinel.py"]["violation_type"] == "script_in_root"


def test_target_location_routes_root_operator_scripts(tmp_path):
    monitor = GemmaRootViolationMonitor(repo_root=tmp_path)

    assert (
        monitor._determine_target_location_qwen("check_port_sentinel.py", {})
        == "scripts/verification/check_port_sentinel.py"
    )
    assert (
        monitor._determine_target_location_qwen("fix_openclaw_auth.py", {})
        == "scripts/fix_openclaw_auth.py"
    )
    assert (
        monitor._determine_target_location_qwen("check_discord_logs.sh", {})
        == "scripts/verification/check_discord_logs.sh"
    )
