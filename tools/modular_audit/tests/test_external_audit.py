"""Synthetic JSON only; no external audit process or network request."""
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.modular_audit import external_audit_results as module
from tools.modular_audit import external_audit as external



def summarize(tool, code, data):
    return module.summarize_external_audit(tool, code, json.dumps(data).encode())


@pytest.mark.parametrize('wrapped', [False, True])
def test_pip_exit_one_preserves_unrated_vulnerabilities_without_provider_text(wrapped):
    dependencies = [{'name': 'fixture', 'version': '1', 'vulns': [{'id': 'fixture-id', 'description': 'PRIVATE_RESPONSE'}]}]
    result = summarize('pip-audit', 1, {'dependencies': dependencies} if wrapped else dependencies)
    assert result.unrated == 1 and result.high == result.incomplete == 0
    findings = module.summary_findings(result)
    assert findings[0].startswith('SECURITY_AUDIT_FAIL:')
    assert 'PRIVATE_RESPONSE' not in repr(result) + repr(findings)


def test_skipped_dependency_is_incomplete_even_when_other_packages_are_clean():
    result = summarize('pip-audit', 0, {'dependencies': [{'name': 'fixture', 'skip_reason': 'PRIVATE_REASON'}]})
    assert result.incomplete == 1
    assert 'PRIVATE_REASON' not in repr(module.summary_findings(result))


def test_bandit_retains_severity_and_coverage_failure_without_source_excerpt():
    result = summarize('bandit', 1, {'results': [{'issue_severity': 'HIGH', 'code': 'PRIVATE_CODE'}], 'errors': ['PRIVATE_ERROR']})
    assert result.high == result.incomplete == 1
    assert 'PRIVATE' not in repr(result) + repr(module.summary_findings(result))


@pytest.mark.parametrize('severity,field', [('critical', 'critical'), ('high', 'high'), ('moderate', 'medium'), ('low', 'low'), ('info', 'info')])
def test_npm_severity_is_not_silently_dropped(severity, field):
    result = summarize('npm', 1, {'vulnerabilities': {'fixture': {'severity': severity}}})
    assert getattr(result, field) == 1 and result.incomplete == 0


@pytest.mark.parametrize('tool,data', [('pip-audit', []), ('bandit', {'results': [], 'errors': []}), ('npm', {'vulnerabilities': {}})])
def test_clean_schema_requires_successful_process(tool, data):
    assert module.summary_findings(summarize(tool, 0, data)) == []
    assert summarize(tool, 1, data).incomplete == 1


@pytest.mark.parametrize('tool,data', [
    ('pip-audit', {'vulnerabilities': []}), ('pip-audit', {'dependencies': [None]}),
    ('pip-audit', [{'name': 'fixture'}]), ('pip-audit', [{'vulns': 'not a list'}]),
    ('bandit', {'results': []}), ('bandit', {'results': [{'issue_severity': 'unknown'}], 'errors': []}),
    ('npm', {'vulnerabilities': []}), ('npm', {'vulnerabilities': {'fixture': {'severity': 'unknown'}}}),
    ('npm', {'vulnerabilities': {}, 'error': {'detail': 'PRIVATE'}}),
])
def test_malformed_or_partial_schema_cannot_report_clean(tool, data):
    assert summarize(tool, 0, data).incomplete == 1


@pytest.mark.parametrize('code,body', [(2, b'{}'), (True, b'{}'), (0, b''), (0, b'broken'), (0, b'\xff'), (0, b' ' * (2 * 1024 * 1024 + 1))], ids=['bad-exit', 'boolean-exit', 'empty', 'malformed', 'bad-encoding', 'oversized'])
def test_process_or_byte_boundary_failure_is_explicit(code, body):
    result = module.summarize_external_audit('npm', code, body)
    assert result.incomplete == 1 and module.summary_findings(result)[0].startswith('SECURITY_SCAN_ERROR:')


def test_exit_one_retains_bounded_json_and_explicit_cwd(tmp_path, monkeypatch):
    monkeypatch.setenv('PIP_AUDIT_OUTPUT', 'must-not-write.json')
    def runner(command, **kwargs):
        assert command == ('synthetic-tool', '--json')
        assert kwargs['cwd'] == tmp_path
        assert kwargs['timeout_s'] == 120
        assert kwargs['max_bytes'] == 2 * 1024 * 1024
        assert kwargs['output_path'] is None and kwargs['stdin_bytes'] is None
        assert 'PIP_AUDIT_OUTPUT' not in kwargs['environment']
        kwargs['chunks'].append(b'{"dependencies":[{"vulns":[{"id":"fixture"}]}]}')
        raise subprocess.CalledProcessError(1, command)
    before = Path.cwd()
    result = external.run_json_audit('pip-audit', ['synthetic-tool', '--json'], tmp_path, runner=runner)
    assert result.unrated == 1 and result.incomplete == 0
    assert Path.cwd() == before and list(tmp_path.iterdir()) == []


@pytest.mark.parametrize('failure', [OSError('PRIVATE'), ValueError('PRIVATE'), RuntimeError('PRIVATE'), subprocess.TimeoutExpired('synthetic', 120)])
def test_process_boundary_errors_do_not_echo_details(tmp_path, failure):
    def runner(*args, **kwargs):
        raise failure
    result = external.run_json_audit('bandit', ['synthetic'], tmp_path, runner=runner)
    assert result.incomplete == 1 and 'PRIVATE' not in repr(result)


def test_nonzero_tool_failure_without_json_is_not_clean(tmp_path):
    def runner(command, **kwargs):
        raise subprocess.CalledProcessError(2, command)
    result = external.run_json_audit('npm', ['synthetic'], tmp_path, runner=runner)
    assert result.incomplete == 1


def test_duplicate_json_members_are_not_accepted_as_clean():
    result = module.summarize_external_audit('npm', 0, b'{"vulnerabilities":{"x":{"severity":"high"}},"vulnerabilities":{}}')
    assert result.incomplete == 1


def test_unknown_tool_rejects_before_process_start(tmp_path):
    with patch.object(external, 'run_bounded_process', side_effect=AssertionError('launched')):
        with pytest.raises(ValueError, match='unknown_audit_tool'):
            external.run_json_audit('unrecognized', ['synthetic'], tmp_path)


def test_actual_bounded_runner_retains_exit_one_json_without_echoing_stderr(tmp_path):
    command = (sys.executable, '-I', '-B', '-c',
               '''import sys; print('{"vulnerabilities":{"x":{"severity":"critical"}}}'); print("PRIVATE_STDERR", file=sys.stderr); sys.exit(1)''')
    result = external.run_json_audit('npm', command, tmp_path)
    assert result.critical == 1 and result.incomplete == 0
    assert 'PRIVATE' not in repr(module.summary_findings(result))


@pytest.mark.parametrize('tool,call,data', [
    ('pip-audit', external.run_pip_audit, {'dependencies':[{'vulns':[{'id':'fixture'}]}]}),
    ('npm', external.run_npm_audit, {'vulnerabilities':{'fixture':{'severity':'critical'}}}),
])
def test_public_adapters_keep_known_vulnerabilities(tmp_path, tool, call, data):
    def runner(command, **kwargs):
        assert kwargs['cwd'] == tmp_path
        kwargs['chunks'].append(json.dumps(data).encode())
        raise subprocess.CalledProcessError(1, command)
    with patch.object(external, 'run_bounded_process', side_effect=runner):
        with patch.object(external, '_npm_command', return_value=('synthetic',)):
            findings = call(tmp_path)
    assert any(x.startswith('SECURITY_AUDIT_FAIL:') for x in findings)


def test_npm_missing_runtime_is_explicit(tmp_path):
    with patch.object(external.shutil, 'which', return_value=None):
        assert external.run_npm_audit(tmp_path)[0].startswith('SECURITY_SCAN_ERROR:')


def test_pip_command_uses_isolated_interpreter_without_install_or_fix(tmp_path):
    def runner(command, **kwargs):
        assert command[:5] == (sys.executable, '-I', '-B', '-m', 'pip_audit')
        assert '--desc' not in command and '--fix' not in command
        kwargs['chunks'].append(b'[]')
    with patch.object(external, 'run_bounded_process', side_effect=runner):
        assert external.run_pip_audit(tmp_path) == []


def test_npm_command_is_read_only_and_includes_all_dependency_types(tmp_path):
    node, npm = tmp_path / 'node', tmp_path / 'npm-cli.js'
    node.write_text('fixture', encoding='utf-8')
    npm.write_text('fixture', encoding='utf-8')
    # Supply both layouts; the host-specific resolver selects its supported one.
    adjacent = tmp_path / 'node_modules/npm/bin/npm-cli.js'
    adjacent.parent.mkdir(parents=True)
    adjacent.write_text('fixture', encoding='utf-8')
    with patch.object(external.shutil, 'which', side_effect=[str(node), str(npm)]):
        command = external._npm_command()
    assert command[0] == str(node.resolve()) and command[2:4] == ('audit', '--json')
    assert not {'fix', 'install', 'update'} & set(command)
    assert {'--ignore-scripts', '--package-lock-only', '--workspaces=false',
            '--include=dev', '--include=optional', '--include=peer'} <= set(command)
