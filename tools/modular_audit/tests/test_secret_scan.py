"""Synthetic-only acceptance tests for FMAS scan scope and honest summaries."""

import argparse
import importlib.util
from pathlib import Path
import re
import subprocess
import sys
from unittest.mock import patch

import pytest


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/modular_audit'))
spec = importlib.util.spec_from_file_location('secret_scan_fmas', ROOT / 'tools/modular_audit/modular_audit.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / 'repo'
    root.mkdir()
    subprocess.run(['git', 'init', '-q', str(root)], check=True)
    (root / 'modules/infrastructure/example/src').mkdir(parents=True)
    return root


def add_source(root, relative, text):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')
    subprocess.run(['git', '-C', str(root), 'add', '--', relative], check=True)
    return path


@pytest.mark.parametrize('line', [
    'stage_token = _reddog_startup_blocker_token(context)',
    'access_key = provider.get_current_access_key()',
    'secret = configuration.compute_secret_reference()',
    'password = derive_password_from_profile()',
    'api_key = os.environ.get("API_KEY")',
    'token = object.attribute_value',
    'monkey = "synthetic-fixture-placeholder"',
    'tokenized = "synthetic-fixture-placeholder"',
])
def test_expressions_are_not_literal_secret_findings(line):
    assert not any(re.search(pattern, line) for pattern in audit.SECRET_PATTERNS)


@pytest.mark.parametrize('name', ['password', 'passwd', 'api_key', 'service_token', 'access_key', 'secret'])
def test_quoted_credential_literals_remain_candidates(name):
    line = f'{name} = "synthetic-fixture-placeholder"'
    assert any(re.search(pattern, line) for pattern in audit.SECRET_PATTERNS)


def test_tracked_test_fixture_is_scanned_and_only_metadata_returned(repo):
    add_source(repo, 'modules/infrastructure/example/tests/test_fixture.py',
               'service_token = "synthetic-fixture-placeholder"\n')
    findings = audit.scan_for_secrets(repo / 'modules')
    assert len(findings) == 1 and findings[0].startswith('SECRET_DETECTED:')
    assert findings[0].endswith('test_fixture.py:1')
    assert 'synthetic-fixture-placeholder' not in str(findings)


def test_inspection_boundary_returns_only_location_metadata(repo):
    relative = 'modules/infrastructure/example/src/source.py'
    add_source(repo, relative, 'service_token = "synthetic-fixture-placeholder"\n')
    hints = audit.inspect_tracked_source(repo / 'modules', [relative])
    assert [hint._asdict() for hint in hints] == [
        {'category': 'literal', 'path': relative, 'line': 1},
    ]
    assert 'synthetic-fixture-placeholder' not in repr(hints)


def test_untracked_worktrees_and_environment_files_are_never_opened(repo):
    add_source(repo, 'modules/infrastructure/example/src/normal.py', 'value = 1\n')
    for relative in ('modules/.worktrees/foreign.py', 'modules/vendor/local.py', 'modules/.env'):
        p = repo / relative
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('password = "synthetic-fixture-placeholder"\n', encoding='utf-8')
    real_open = Path.open
    def guarded(path, *args, **kwargs):
        assert path.name == 'normal.py', f'untracked path read: {path.name}'
        return real_open(path, *args, **kwargs)
    with patch.object(Path, 'open', guarded):
        assert audit.scan_for_secrets(repo / 'modules') == []


def test_tracked_environment_filename_is_reported_without_read(repo):
    add_source(repo, 'modules/infrastructure/example/.env.sample', 'fixture only\n')
    with patch.object(Path, 'open', side_effect=AssertionError('environment content read')):
        findings = audit.scan_for_secrets(repo / 'modules')
    assert len(findings) == 1 and findings[0].startswith('SECRET_SCAN_SKIPPED:')
    assert audit._finding_severity(findings[0]) == 'WARNING'


def test_unavailable_git_inventory_does_not_fall_back_to_walk(repo):
    add_source(repo, 'modules/infrastructure/example/src/normal.py', 'value = 1\n')
    with patch.object(audit, '_git_value', return_value=None):
        with patch.object(Path, 'open', side_effect=AssertionError('fallback read')):
            findings = audit.scan_for_secrets(repo / 'modules')
    assert findings and all(x.startswith('SECRET_SCAN_ERROR:') for x in findings)


def test_missing_tracked_source_is_a_scan_error(repo):
    path = add_source(repo, 'modules/infrastructure/example/src/missing.py', 'value = 1\n')
    path.unlink()
    findings = audit.scan_for_secrets(repo / 'modules')
    assert findings and findings[0].startswith('SECRET_SCAN_ERROR:')


def test_invalid_encoding_is_not_silently_ignored(repo):
    path = add_source(repo, 'modules/infrastructure/example/src/bad.py', 'value = 1\n')
    path.write_bytes(b'\xff\xfe\x00')
    findings = audit.scan_for_secrets(repo / 'modules')
    assert findings and findings[0].startswith('SECRET_SCAN_ERROR:')


def test_symlink_or_reparse_parent_is_never_read(repo):
    add_source(repo, 'modules/infrastructure/example/src/normal.py', 'value = 1\n')
    original = Path.lstat
    class Redirect:
        st_mode = 0o120777
        st_file_attributes = 0x400
    def metadata(path, *args, **kwargs):
        return Redirect() if path.name == 'src' else original(path, *args, **kwargs)
    with patch.object(Path, 'lstat', metadata):
        with patch.object(Path, 'open', side_effect=AssertionError('redirect read')):
            findings = audit.scan_for_secrets(repo / 'modules')
    assert findings and findings[0].startswith('SECRET_SCAN_ERROR:')


def test_oversized_source_is_reported_as_incomplete(repo):
    path = add_source(repo, 'modules/infrastructure/example/src/large.py', 'value = 1\n')
    with path.open('wb') as handle:
        handle.write(b'#' * (2 * 1024 * 1024 + 1))
    findings = audit.scan_for_secrets(repo / 'modules')
    assert findings and findings[0].startswith('SECRET_SCAN_ERROR:')


def test_invalid_inventory_path_is_rejected_before_read(repo):
    with patch.object(audit, '_git_value', side_effect=[str(repo), 'modules/../outside.py\0']):
        with patch.object(Path, 'open', side_effect=AssertionError('invalid path read')):
            findings = audit.scan_for_secrets(repo / 'modules')
    assert findings and findings[0].startswith('SECRET_SCAN_ERROR:')


def test_scan_does_not_modify_tracked_or_untracked_files(repo):
    add_source(repo, 'modules/infrastructure/example/src/source.py', 'value = 1\n')
    (repo / 'modules/local.txt').write_text('untouched\n', encoding='utf-8')
    before = {p.relative_to(repo): p.read_bytes() for p in (repo / 'modules').rglob('*') if p.is_file()}
    audit.scan_for_secrets(repo / 'modules')
    after = {p.relative_to(repo): p.read_bytes() for p in (repo / 'modules').rglob('*') if p.is_file()}
    assert after == before


@pytest.mark.parametrize('finding', ['SECRET_DETECTED: fixture.py:1', 'SECRET_SCAN_SKIPPED: fixture.env'])
def test_secret_hints_and_unread_environment_files_are_visible_warnings(finding):
    assert audit._finding_severity(finding) == 'WARNING'


@pytest.mark.parametrize('finding,expected', [
    ('WSP 62 WARNING: inherited debt', 'warnings'),
    ('WSP 62: informational debt', 'advisories'),
])
def test_mode2_does_not_claim_no_findings(finding, expected):
    args = argparse.Namespace(wsp_62_size_check=True)
    with patch.object(audit, '_validated_mode2_baseline', return_value=Path('.')):
        with patch.object(audit, 'audit_with_baseline_comparison', return_value={'status':'success'}):
            with patch.object(audit, 'audit_file_sizes', return_value=[finding]):
                with patch.object(audit.logging, 'info') as info, patch.object(audit.logging, 'warning') as warn:
                    audit._run_mode2(args, Path('.'))
    messages = [str(call.args[0]) for call in (*info.call_args_list, *warn.call_args_list)]
    assert not any('no findings' in x for x in messages)
    assert any(f'completed with {expected}' in x for x in messages)


def test_mode1_advisories_are_not_a_clean_scan():
    args = argparse.Namespace(wsp_62_size_check=False)
    with patch.object(audit, 'audit_all_modules', return_value=(['WSP 62: informational debt'], 1)):
        with patch.object(audit.logging, 'info') as info:
            audit._run_mode1(args, Path('.'))
    assert not any('no findings' in str(call) for call in info.call_args_list)


def test_mode2_baseline_differences_remain_visible():
    args = argparse.Namespace(wsp_62_size_check=False)
    with patch.object(audit, '_validated_mode2_baseline', return_value=Path('.')):
        with patch.object(audit, 'audit_with_baseline_comparison', return_value={'status':'success', 'has_changes':True}):
            with patch.object(audit.logging, 'info') as info:
                audit._run_mode2(args, Path('.'))
    assert any('completed with baseline differences' in str(call) for call in info.call_args_list)
    assert not any('no findings' in str(call) for call in info.call_args_list)
