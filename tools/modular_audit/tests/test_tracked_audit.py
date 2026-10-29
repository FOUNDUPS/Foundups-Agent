"""Synthetic metadata/INI boundaries only; never runs Bandit."""
from pathlib import Path
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.modular_audit import external_audit as plan_module
from tools.modular_audit import modular_audit as audit
from tools.modular_audit import tracked_audit as tracked
import subprocess


def put(root, relative, data=b'# fixture\n'):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def test_only_explicit_tracked_python_is_admitted_without_source_reads(tmp_path):
    one = 'modules/infrastructure/example/src/service.py'
    two = 'modules/infrastructure/example/tests/test_service.py'
    for relative in (one, two, 'modules/vendor/foreign/src/trap.py'):
        put(tmp_path, relative)
    with patch.object(Path, 'open', side_effect=AssertionError('source read')):
        plan = plan_module.prepare_bandit_plan(tmp_path, [two, one])
    assert plan.paths == (one, two) and not plan.incomplete


def test_environment_parent_and_filename_are_excluded_without_metadata_reads(tmp_path):
    with patch.object(Path, 'lstat', side_effect=AssertionError('environment read')):
        plan = plan_module.prepare_bandit_plan(tmp_path, ['modules/.env/sample.py', 'modules/demo/.env.py'])
    assert plan.excluded_environment == 2 and not plan.paths


@pytest.mark.parametrize('relative', ['../outside.py', '/absolute.py', 'modules/../outside.py', 'modules/a,b.py', 'modules/a%b.py', 'modules/a\nb.py', 'modules/file.py.'])
def test_unrepresentable_or_uncontained_python_path_is_explicit(tmp_path, relative):
    plan = plan_module.prepare_bandit_plan(tmp_path, [relative])
    if relative.endswith('.py'):
        assert plan.incomplete
    assert not plan.paths


def test_missing_or_oversized_source_is_incomplete(tmp_path):
    path = 'modules/infrastructure/example/src/large.py'
    put(tmp_path, path, b' ' * (plan_module.MAX_FILE_BYTES + 1))
    plan = plan_module.prepare_bandit_plan(tmp_path, [path, 'modules/missing.py'])
    assert plan.incomplete == 2 and not plan.paths


def test_temporary_ini_is_explicit_and_removed_without_changing_cwd(tmp_path):
    relative = 'modules/infrastructure/example/src/service.py'
    put(tmp_path, relative)
    plan = plan_module.prepare_bandit_plan(tmp_path, [relative])
    before = Path.cwd()
    with plan_module.bandit_target_file(plan) as path:
        assert path.read_text() == '[bandit]\ntargets = ' + relative + '\n'
        assert path.parent != tmp_path
    assert not path.exists() and Path.cwd() == before


def tracked_repo(root, paths):
    subprocess.run(['git', 'init', '-q', str(root)], check=True)
    for relative in paths:
        put(root, relative)
    subprocess.run(['git', '-C', str(root), 'add', '.'], check=True)
    return root


def test_mode1_scans_once_with_explicit_root_and_never_changes_process_cwd(tmp_path, monkeypatch):
    root = tracked_repo(tmp_path / 'repo', ['requirements.txt', 'package.json', 'package-lock.json',
        'modules/infrastructure/one/requirements.txt', 'modules/infrastructure/one/src/service.py',
        'modules/infrastructure/two/requirements.txt', 'modules/infrastructure/two/src/service.py'])
    monkeypatch.chdir(tmp_path)
    with patch.object(audit, 'run_pip_audit', return_value=[]) as pip:
        with patch.object(audit, 'run_bandit', return_value=[]) as bandit:
            with patch.object(audit, 'run_npm_audit', return_value=[]) as npm:
                with patch.object(audit, 'inspect_tracked_source', return_value=[]):
                    findings, count = audit.audit_all_modules(root)
    assert count == 2 and Path.cwd() == tmp_path
    pip.assert_called_once_with(root)
    npm.assert_called_once_with(root)
    bandit.assert_called_once_with(root, ['modules/infrastructure/one/src/service.py',
                                        'modules/infrastructure/two/src/service.py'])
    assert any('installed interpreter' in x for x in findings)
    assert any('nested locks are not audited' in x for x in findings)


def test_untracked_files_cannot_create_modules_or_satisfy_documentation(tmp_path):
    root = tracked_repo(tmp_path / 'repo', ['modules/monitoring/one/src/service.py'])
    put(root, 'modules/monitoring/one/requirements.txt')
    put(root, 'modules/monitoring/one/tests/README.md')
    put(root, 'modules/untracked/two/src/trap.py')
    with patch.object(Path, 'glob', side_effect=AssertionError('traversal')):
        with patch.object(Path, 'iterdir', side_effect=AssertionError('traversal')):
            inventory = tracked.read_tracked_inventory(root)
            findings, count = tracked.structural_findings(inventory, audit.ENTERPRISE_DOMAINS, audit.ARCHITECTURAL_EXCEPTIONS)
    assert count == 1 and any('missing a tracked dependency' in x for x in findings)
    assert any('missing tracked tests/README' in x for x in findings)
    assert not any('Unknown' in x or 'untracked' in x for x in findings)


def test_non_git_root_fails_before_any_external_audit(tmp_path):
    put(tmp_path, 'modules/infrastructure/one/src/service.py')
    with patch.object(audit, 'perform_security_scan', side_effect=AssertionError('launched')):
        findings, count = audit.audit_all_modules(tmp_path)
    assert count == 0 and findings == ['ERROR: Git-tracked inventory unavailable or invalid']


def test_missing_tracked_source_is_incomplete(tmp_path):
    relative = 'modules/infrastructure/one/src/service.py'
    root = tracked_repo(tmp_path / 'repo', [relative])
    (root / relative).unlink()
    inventory = tracked.read_tracked_inventory(root)
    assert inventory.incomplete == 1 and not inventory.files


def test_environment_parent_never_reaches_metadata_or_source_read(tmp_path):
    relative = 'modules/.env.private/trap.py'
    root = tracked_repo(tmp_path / 'repo', [relative])
    with patch.object(tracked, 'source_metadata', side_effect=AssertionError('read')):
        inventory = tracked.read_tracked_inventory(root)
    assert inventory.excluded_environment == 1 and not inventory.files


@pytest.mark.parametrize('raw', ['100644 abc 0\tmodules/x.py',
    '100644 abc 1\tmodules/x.py\0', '100644 abc 0\t../outside.py\0',
    '100644 abc 0\tmodules/x.py\0' * 2])
def test_malformed_inventory_fails_closed(tmp_path, raw):
    with patch.object(tracked, '_git', side_effect=[str(tmp_path), raw]):
        with pytest.raises(ValueError):
            tracked.read_tracked_inventory(tmp_path)


def test_tracked_submodule_is_incomplete_not_traversed(tmp_path):
    with patch.object(tracked, '_git', side_effect=[str(tmp_path), '160000 abc 0\tmodules/vendor\0']):
        with patch.object(tracked, 'source_metadata', side_effect=AssertionError('traversed')):
            inventory = tracked.read_tracked_inventory(tmp_path)
    assert inventory.incomplete == 1 and not inventory.files


def test_missing_root_npm_lock_never_launches_npm(tmp_path):
    root = tracked_repo(tmp_path / 'repo', ['package.json'])
    with patch.object(audit, 'run_npm_audit', side_effect=AssertionError('launched')):
        findings = audit.perform_security_scan(root)
    assert any(x.startswith('SECURITY_ERROR:') and 'lockfile unavailable' in x for x in findings)


def test_documented_medium_severity_remains_warning_after_wrapping():
    finding = 'SECURITY_VULNERABILITY_MEDIUM: fixture'
    assert audit._finding_severity(finding) == 'WARNING'
    assert audit._finding_severity(audit._wrap_security_findings('repository', [finding])[0]) == 'WARNING'


def test_bandit_uses_only_explicit_targets_and_failed_empty_output_is_error(tmp_path):
    relative = 'modules/infrastructure/one/tests/test_service.py'
    put(tmp_path, relative)
    configs = []
    def runner(command, **kwargs):
        assert '-r' not in command and command[:5] == (sys.executable, '-I', '-B', '-m', 'bandit')
        config = Path(command[command.index('--ini') + 1])
        configs.append(config)
        assert config.read_text() == '[bandit]\ntargets = ' + relative + '\n'
        assert kwargs['cwd'] == tmp_path
        raise subprocess.CalledProcessError(2, command)
    with patch.object(plan_module, 'run_bounded_process', side_effect=runner):
        findings = plan_module.run_bandit(tmp_path, [relative])
    assert findings[0].startswith('SECURITY_SCAN_ERROR:') and not configs[0].exists()


def test_root_manifest_byte_limit_is_explicit(tmp_path, monkeypatch):
    root = tracked_repo(tmp_path / 'repo', ['package.json'])
    monkeypatch.setattr(tracked, 'MAX_MANIFEST_BYTES', 1)
    inventory = tracked.read_tracked_inventory(root)
    assert inventory.incomplete == 1 and not inventory.files


def test_bandit_total_source_and_target_limits_are_explicit(tmp_path, monkeypatch):
    relative = 'modules/infrastructure/one/src/service.py'
    put(tmp_path, relative)
    monkeypatch.setattr(plan_module, 'MAX_TOTAL_BYTES', 1)
    assert plan_module.prepare_bandit_plan(tmp_path, [relative]).incomplete == 1
    monkeypatch.setattr(plan_module, 'MAX_TOTAL_BYTES', 100)
    monkeypatch.setattr(plan_module, 'MAX_TARGET_BYTES', 1)
    assert plan_module.prepare_bandit_plan(tmp_path, [relative]).incomplete == 1


def test_redirected_source_cannot_be_admitted(tmp_path):
    from types import SimpleNamespace
    import stat
    metadata = SimpleNamespace(st_mode=stat.S_IFREG, st_file_attributes=0x400)
    with patch.object(Path, 'lstat', return_value=metadata):
        with pytest.raises(ValueError, match='redirected_path'):
            tracked.source_metadata(tmp_path, 'modules/infrastructure/one/src/service.py')


def test_git_output_uses_existing_bounded_io_and_sanitized_environment(tmp_path, monkeypatch):
    monkeypatch.setenv('GIT_DIR', 'unrelated-authority')
    with patch.object(tracked, 'run_bounded_stdout', return_value=b'') as read:
        assert tracked._git(tmp_path, 'ls-files', '--stage', '-z') == ''
    kwargs = read.call_args.kwargs
    assert kwargs['max_bytes'] == 4 * 1024 * 1024 and kwargs['timeout_s'] == 30
    assert 'GIT_DIR' not in kwargs['environment']
    assert kwargs['environment']['GIT_CONFIG_NOSYSTEM'] == '1'


def test_git_root_mismatch_rejects_before_inventory(tmp_path):
    with patch.object(tracked, '_git', return_value=str(tmp_path / 'other')) as read:
        with pytest.raises(ValueError, match='repository_root_mismatch'):
            tracked.read_tracked_inventory(tmp_path)
    assert read.call_count == 1


def test_empty_git_repository_is_not_a_clean_structural_audit(tmp_path):
    root = tracked_repo(tmp_path / 'repo', [])
    findings, count = audit.audit_all_modules(root)
    assert count == 0 and any(x.startswith('ERROR: No tracked module files') for x in findings)
