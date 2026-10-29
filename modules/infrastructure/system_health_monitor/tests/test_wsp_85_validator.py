from pathlib import Path

import pytest

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


@pytest.mark.parametrize('name', ['tmp_probe.txt', '.prompt_reddog_example.md'])
def test_temporary_root_artifact_is_reported_without_mutation(tmp_path, name):
    path = tmp_path / name
    path.write_bytes(b'preserve this authored content\n')
    result = WSP85Validator(str(tmp_path)).scan_root_directory()
    assert str(path) in result['prohibited_files']
    assert path.read_bytes() == b'preserve this authored content\n'


def test_foundational_root_contracts_are_not_unknown(tmp_path):
    names = ['AGENTS.md', 'MEMORY.md', 'requirements-trust-bootstrap.txt',
             '.gitmodules', '.gitattributes', 'wsp_62_exemptions.yaml']
    for name in names:
        (tmp_path / name).write_bytes(b'fixture\n')
    result = WSP85Validator(str(tmp_path)).scan_root_directory()
    assert result == {'prohibited_files': [], 'prohibited_dirs': [], 'unknown_files': []}
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted(names)


def test_escaped_drive_directory_is_reported_without_removal(tmp_path):
    path = tmp_path / 'C\uf03aUsersfixture'
    path.mkdir()
    (path / 'keep.txt').write_bytes(b'preserved\n')
    result = WSP85Validator(str(tmp_path)).scan_root_directory()
    assert str(path) in result['prohibited_dirs']
    assert (path / 'keep.txt').read_bytes() == b'preserved\n'
