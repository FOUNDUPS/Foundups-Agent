from pathlib import Path

from modules.infrastructure.system_health_monitor.src.wsp_85_validator import (
    WSP85Validator,
)


def _write(path: Path, content: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_validator_allows_repo_level_root_configs_and_scripts_dir(tmp_path):
    (tmp_path / "scripts").mkdir()
    _write(tmp_path / "firebase.json")
    _write(tmp_path / "firestore.rules")
    _write(tmp_path / "pyrightconfig.json")

    validator = WSP85Validator(project_root=str(tmp_path))
    violations = validator.scan_root_directory()

    assert violations["prohibited_dirs"] == []
    assert violations["prohibited_files"] == []
    assert violations["unknown_files"] == []


def test_validator_flags_root_check_and_fix_scripts(tmp_path):
    _write(tmp_path / "check_port_sentinel.py", "print('probe')\n")
    _write(tmp_path / "fix_openclaw_auth.py", "print('fix')\n")

    validator = WSP85Validator(project_root=str(tmp_path))
    violations = validator.scan_root_directory()
    prohibited = {Path(path).name for path in violations["prohibited_files"]}

    assert "check_port_sentinel.py" in prohibited
    assert "fix_openclaw_auth.py" in prohibited
