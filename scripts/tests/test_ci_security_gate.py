"""Security gate regression tests; synthetic credential is assembled at runtime."""
import importlib.util
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest
import yaml

SPEC = importlib.util.spec_from_file_location('ci_security_gate',
    Path(__file__).resolve().parents[2] / '.github/scripts/security_gate.py')
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


def test_security_checks_cover_stacked_and_retargeted_pull_requests():
    root = Path(__file__).resolve().parents[2]
    # BaseLoader preserves YAML's `on` key (SafeLoader treats it as bool).
    workflow = yaml.load((root / '.github/workflows/ci.yml').read_text(),
                         Loader=yaml.BaseLoader)
    trigger = workflow['on']['pull_request']
    for filter_name in ('branches', 'branches-ignore', 'paths', 'paths-ignore'):
        assert filter_name not in trigger
    assert {'opened', 'synchronize', 'reopened', 'edited', 'ready_for_review'} <= set(trigger['types'])
    assert 'pull_request_target' not in workflow['on']
    security = workflow['jobs']['security']
    assert security['uses'] == './.github/workflows/security-scan.yml'
    assert 'if' not in security  # Draft/stacked PRs must not skip the gate.
    assert security['permissions'] == {'contents': 'read'}


def test_nested_environment_files_and_exact_templates():
    paths = ['.env', 'web/.env.local', 'web/.env.production', '.env.example',
             'web/.env.sample', 'web/.env.template', 'web/.env.example.backup']
    assert gate.tracked_env_files(paths) == paths[:3] + paths[-1:]


@pytest.mark.parametrize('shallow', [True, False])
def test_history_gate_rejects_real_shallow_checkout(tmp_path, monkeypatch, capsys, shallow):
    origin = tmp_path / 'origin'
    origin.mkdir()
    def git(*args, cwd=origin):
        return subprocess.run(['git', *args], cwd=cwd, check=True, capture_output=True)
    git('init', '-q')
    source = origin / 'fixture.txt'
    for content in ('historical synthetic canary', 'current harmless content'):
        source.write_text(content)
        git('add', 'fixture.txt')
        git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
            'commit', '-qm', 'fixture')
    checkout = tmp_path / 'checkout'
    git('clone', '-q', *(['--depth=1'] if shallow else []),
        origin.as_uri(), str(checkout))
    monkeypatch.setattr(gate, 'ROOT', checkout)
    for name in ('SECURITY_EVENT', 'SECURITY_BASE', 'SECURITY_HEAD'):
        monkeypatch.delenv(name, raising=False)
    scans = []
    monkeypatch.setattr(gate, 'scan', lambda args, report: scans.append(args) or 0)
    assert gate.main() == int(shallow)
    assert len(scans) == (0 if shallow else 2)
    assert ('coverage incomplete' in capsys.readouterr().out) == shallow


def test_commit_range_includes_intermediate_commits():
    base, head = 'a' * 40, 'b' * 40
    assert gate.history_range('pull_request', base, head) == base + '..' + head
    assert gate.history_range('push', base, head) == base + '..' + head
    assert gate.history_range('schedule', base, head) == '--all'
    assert gate.history_range('push', '0' * 40, head) == '--all'
    with pytest.raises(ValueError):
        gate.history_range('push', '--all --skip=1', head)


@pytest.mark.parametrize('status,exists,findings,expected', [
    (0, True, [], 0), (1, True, [], 1), (2, True, [], 1),
    (0, False, [], 1), (0, True, [{'Secret': 'sensitive', 'Match': 'sensitive',
        'RuleID': 'synthetic', 'File': 'fixture', 'StartLine': 1}], 1)])
def test_scan_fails_closed_and_never_logs_values(tmp_path, monkeypatch, capsys,
                                                status, exists, findings, expected):
    report = tmp_path / 'report.json'
    def fake_run(command, **kwargs):
        assert '--redact=100' in command
        assert '--ignore-gitleaks-allow' in command
        if exists:
            report.write_text(json.dumps(findings))
        return SimpleNamespace(returncode=status, stdout=b'sensitive', stderr=b'')
    monkeypatch.setattr(gate.subprocess, 'run', fake_run)
    monkeypatch.setattr(gate, 'reviewed_finding', lambda *args: False)
    assert gate.scan(['dir', str(tmp_path)], report) == expected
    output = capsys.readouterr()
    assert 'sensitive' not in output.out + output.err


def test_missing_scanner_is_error(tmp_path, monkeypatch):
    def missing(*args, **kwargs):
        raise FileNotFoundError('scanner unavailable')
    monkeypatch.setattr(gate.subprocess, 'run', missing)
    with pytest.raises(FileNotFoundError):
        gate.scan(['dir', str(tmp_path)], tmp_path / 'report.json')


def test_gotjunk_missing_headers_and_http_error_fail(tmp_path):
    # Execute the actual post-deployment shell check against a bounded curl stub.
    workflow = (Path(__file__).resolve().parents[2] /
                '.github/workflows/deploy-gotjunk.yml').read_text()
    # Backend-only repairs must not roll out unrelated frontend/rule state.
    from fnmatch import fnmatchcase
    push_paths = yaml.load(workflow, Loader=yaml.BaseLoader)['on']['push']['paths']
    for path, should_deploy in [
        ('modules/foundups/gotjunk/backend/requirements.txt', False),
        ('modules/foundups/gotjunk/tests/test_backend_security.py', False),
        ('modules/foundups/gotjunk/frontend/App.tsx', True),
        ('modules/foundups/gotjunk/firestore.rules', True),
        ('modules/foundups/gotjunk/storage.rules', True),
    ]:
        assert any(fnmatchcase(path, pattern) for pattern in push_paths) == should_deploy
    command = workflow.split('          set -euo pipefail\n', 1)[1]
    command = 'set -euo pipefail\n' + '\n'.join(line[10:] for line in command.splitlines())
    for headers, status, expected in [
        ('HTTP/2 200', 0, 1),
        ('Content-Security-Policy: frame-ancestors https://foundups.com\n'
         'X-Content-Type-Options: nosniff', 0, 0),
        ('Content-Security-Policy: frame-ancestors https://foundups.com', 0, 1),
        ('', 22, 1),
    ]:
        stub = 'curl() { printf "%s\\n" "$FAKE_HEADERS"; return "$FAKE_STATUS"; };\n'
        result = subprocess.run(['bash', '-c', stub + command],
                                env={'FAKE_HEADERS': headers, 'FAKE_STATUS': str(status)},
                                capture_output=True)
        assert (result.returncode != 0) == bool(expected)


def test_reviewed_exception_is_bound_to_whole_file_rule_and_location(tmp_path):
    source = tmp_path / 'fixture.py'
    source.write_text('synthetic fixture')
    finding = {'File': 'fixture.py', 'RuleID': 'synthetic', 'StartLine': 1}
    original = gate.finding_fingerprint(finding, tmp_path)
    source.write_text('different credential at the same location')
    assert gate.finding_fingerprint(finding, tmp_path) != original
    source.write_text('synthetic fixture')
    assert gate.finding_fingerprint(dict(finding, StartLine=2), tmp_path) != original
    assert gate.finding_fingerprint(dict(finding, RuleID='different'), tmp_path) != original


def test_history_exception_uses_historical_content(tmp_path, monkeypatch):
    (tmp_path / 'fixture.py').write_text('synthetic fixture')
    finding = {'File': 'fixture.py', 'RuleID': 'synthetic', 'StartLine': 1}
    original = gate.finding_fingerprint(finding, tmp_path)
    def historical(command, **kwargs):
        assert command == ['git', 'show', 'a' * 40 + ':fixture.py']
        return b'prior real credential'
    monkeypatch.setattr(gate.subprocess, 'check_output', historical)
    assert gate.finding_fingerprint(dict(finding, Commit='a' * 40), tmp_path) != original


@pytest.mark.parametrize('status,expected', [(1, 0), (2, 1)])
def test_reviewed_findings_do_not_mask_scanner_errors(tmp_path, monkeypatch, status, expected):
    report = tmp_path / 'report.json'
    report.write_text('[{"RuleID":"synthetic","File":"fixture.py","StartLine":1}]')
    monkeypatch.setattr(gate.subprocess, 'run', lambda *a, **k: SimpleNamespace(returncode=status, stderr=b''))
    monkeypatch.setattr(gate, 'reviewed_finding', lambda *args: True)
    assert gate.scan(['dir', str(tmp_path)], report) == expected


def test_partial_reviewed_report_cannot_mask_scanner_error(tmp_path, monkeypatch, capsys):
    report = tmp_path / 'report.json'
    report.write_text('[]')
    monkeypatch.setattr(gate.subprocess, 'run', lambda *a, **k:
                        SimpleNamespace(returncode=1, stderr=b'error: sensitive diagnostic'))
    assert gate.scan(['dir', str(tmp_path)], report) == 1
    assert 'sensitive diagnostic' not in capsys.readouterr().out


def test_python_download_jobs_bootstrap_trust_before_dependencies():
    root = Path(__file__).resolve().parents[2]
    for path in (root / '.github/workflows').glob('*.yml'):
        workflow = yaml.load(path.read_text(), Loader=yaml.BaseLoader)
        for job in workflow.get('jobs', {}).values():
            bootstrapped = False
            for step in job.get('steps', []):
                command = step.get('run', '')
                if 'requirements-trust-bootstrap.txt' in command:
                    assert '--require-hashes' in command and '--no-deps' in command
                    bootstrapped = True
                if 'pip install' in command or 'pip3 install' in command:
                    assert bootstrapped, (path.name, step.get('name'))
    windows = yaml.load((root / '.github/workflows/ci.yml').read_text(),
                        Loader=yaml.BaseLoader)['jobs']['mcp-runtime-compatibility']
    prepare = next(s['run'] for s in windows['steps'] if s.get('name') == 'Prepare isolated MCP candidate')
    assert prepare.index('Candidate venv creation failed') < prepare.index('Candidate trust bootstrap failed') < prepare.index('Candidate dependency installation failed')


def test_trust_bootstrap_is_hash_bound_and_precedes_docker_downloads():
    root = Path(__file__).resolve().parents[2]
    entries = [line for line in (root / 'requirements-trust-bootstrap.txt').read_text().splitlines()
               if line and not line.startswith('#')]
    assert len(entries) == 2
    assert {line.split(' @ ')[0] for line in entries} == {'pip', 'certifi'}
    for line in entries:
        url, digest = line.split(' @ ')[1].split(' --hash=sha256:')
        assert url.startswith('https://files.pythonhosted.org/packages/')
        assert url.endswith('.whl') and len(digest) == 64
        assert all(c in '0123456789abcdef' for c in digest)
    assert 'pip-26.2.2-' in entries[0]
    assert 'certifi-2026.10.19-' in entries[1]
    assert 'certifi==2026.10.19' in (root / 'requirements.txt').read_text()
    docker = (root / 'Dockerfile').read_text()
    assert docker.index('--require-hashes -r requirements-trust-bootstrap.txt') < docker.index('-r requirements.txt')
