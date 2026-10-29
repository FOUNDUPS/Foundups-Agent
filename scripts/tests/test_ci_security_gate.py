"""Security gate regression tests; synthetic credential is assembled at runtime."""
import importlib.util
import json
from pathlib import Path
import re
import shlex
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


def _mentions_pip_install(text):
    # Conservative fallback for opaque wrappers/code, including global flags.
    return bool(re.search(r'\bpip(?:\d+(?:\.\d+)*)?(?:\.exe)?\b[^\n]*\binstall\b', text))


def _workflow_shell_commands(script):
    """Read literal command forms used here; never execute workflow contents.

    Preserve quoted bodies and keep offline filename inspection separate from
    installs. Installer syntax in opaque code or control flow requires review.
    This is a bounded source contract, not a general shell interpreter.
    """
    script = re.sub(r'(?:\\|`)\r?\n', ' ', script)
    pending, heredocs = '', []
    shell_blocks = brace_blocks = 0
    for line in script.splitlines():
        if heredocs:
            delimiter, strip_tabs = heredocs[0]
            if (line.lstrip('\t') if strip_tabs else line) == delimiter:
                heredocs.pop(0)
            elif not line.lstrip().startswith('#'):
                assert not _mentions_pip_install(line), 'Installer syntax in opaque heredoc requires review'
            continue
        pending += line + '\n'
        # Non-POSIX mode keeps quotation marks, distinguishing a quoted "<<"
        # from a real heredoc operator; normalize literal words only afterward.
        lexer = shlex.shlex(pending, posix=False, punctuation_chars=';&|<>')
        lexer.whitespace_split = True
        try:
            tokens = list(lexer)
        except ValueError as error:
            if str(error) == 'No closing quotation':
                continue
            raise
        pending = ''
        installer_text = _mentions_pip_install(' '.join(tokens))
        expanding = ' '.join(token for token in tokens if not token.startswith("'"))
        if installer_text:
            assert '$(' not in expanding and '`' not in expanding, 'Installer command substitution requires review'
            assert not any(token in ('&&', '||', '|') for token in tokens), 'Conditional or piped installer requires review'
        for index, token in enumerate(tokens):
            if token == '<<':
                assert index + 1 < len(tokens), 'Missing heredoc delimiter'
                delimiter = tokens[index + 1]
                strip_tabs = delimiter.startswith('-')
                delimiter = _literal_shell_word(delimiter[1:] if strip_tabs else delimiter)
                assert re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*', delimiter), 'Unqualified heredoc form'
                heredocs.append((delimiter, strip_tabs))
        command = []
        for token in tokens:
            if token in (';', '&&', '||', '|') or (token == '&' and command):
                if token == '&' and installer_text:
                    raise AssertionError('Background installer requires review')
                if command:
                    shell_blocks, brace_blocks = _check_installer_control_context(
                        command, shell_blocks, brace_blocks)
                    yield [_literal_shell_word(word) for word in command]
                command = []
            else:
                command.append(token)
        if command:
            shell_blocks, brace_blocks = _check_installer_control_context(
                command, shell_blocks, brace_blocks)
            yield [_literal_shell_word(word) for word in command]
    assert not pending and not heredocs, 'Unterminated workflow quotation or heredoc'


def _check_installer_control_context(command, shell_blocks, brace_blocks):
    # Track only block boundaries to reject installs inside opaque control flow.
    # No condition, function, shell payload or PowerShell expression is evaluated.
    first = command[0]
    if first in ('if', 'for', 'while', 'until', 'case', 'select', 'function') and '{' not in command:
        shell_blocks += 1
    brace_blocks += command.count('{')
    if _mentions_pip_install(' '.join(command)):
        assert shell_blocks == 0 and brace_blocks == 0, 'Installer inside control block requires review'
    if first in ('fi', 'done', 'esac'):
        shell_blocks = max(0, shell_blocks - 1)
    brace_blocks = max(0, brace_blocks - command.count('}'))
    return shell_blocks, brace_blocks


def _literal_shell_word(word):
    if len(word) >= 2 and word[0] in ('\"', "'") and word[-1] == word[0]:
        return word[1:-1]
    return word


def _pip_install_arguments(command):
    if command and command[0] == '&':  # PowerShell call operator.
        command = command[1:]
    if not command:
        return None
    executable = command[0].replace('\\', '/').rsplit('/', 1)[-1]
    if re.fullmatch(r'pip(?:\d+(?:\.\d+)*)?(?:\.exe)?', executable):
        arguments = command[1:]
    elif re.fullmatch(r'python(?:\d+(?:\.\d+)*)?(?:\.exe)?', executable):
        arguments = command[1:]
        while arguments and arguments[0] in ('-I', '-B', '-u', '-s', '-E'):
            arguments = arguments[1:]
        if arguments[:2] != ['-m', 'pip']:
            assert not _mentions_pip_install(' '.join(command)), 'Installer syntax in opaque Python command requires review'
            return None
        arguments = arguments[2:]
    else:
        assert not _mentions_pip_install(' '.join(command)), 'Unsupported installer wrapper requires review'
        return None
    # These are the actual flag-only pip global options in the workflows.
    # Unknown prefixes with an install token require review, not silent omission.
    while arguments and arguments[0] in ('--isolated', '--disable-pip-version-check',
                                         '--no-input', '-v', '--verbose', '-q', '--quiet'):
        arguments = arguments[1:]
    if arguments and arguments[0] == 'install':
        return arguments[1:]
    assert 'install' not in arguments, 'Unqualified pip global option form'
    return None


def _assert_job_bootstraps_trust(job, label='fixture'):
    bootstrapped = False
    for step in job.get('steps', []):
        for command in _workflow_shell_commands(step.get('run', '')):
            arguments = _pip_install_arguments(command)
            if arguments is None:
                continue
            requirements = []
            for index, argument in enumerate(arguments):
                if argument in ('-r', '--requirement') and index + 1 < len(arguments):
                    requirements.append(arguments[index + 1])
                elif argument.startswith('--requirement='):
                    requirements.append(_literal_shell_word(argument.partition('=')[2]))
            bootstrap = any(path in ('requirements-trust-bootstrap.txt',
                                    './requirements-trust-bootstrap.txt') for path in requirements)
            if bootstrap:
                assert '--require-hashes' in arguments and '--no-deps' in arguments, (label, step.get('name'))
                bootstrapped = True
            else:
                assert bootstrapped, (label, step.get('name'))


def test_python_download_jobs_bootstrap_trust_before_dependencies():
    root = Path(__file__).resolve().parents[2]
    for path in (root / '.github/workflows').glob('*.yml'):
        workflow = yaml.load(path.read_text(), Loader=yaml.BaseLoader)
        for job in workflow.get('jobs', {}).values():
            _assert_job_bootstraps_trust(job, path.name)
    windows = yaml.load((root / '.github/workflows/ci.yml').read_text(),
                        Loader=yaml.BaseLoader)['jobs']['mcp-runtime-compatibility']
    prepare = next(s['run'] for s in windows['steps'] if s.get('name') == 'Prepare isolated MCP candidate')
    assert prepare.index('Candidate venv creation failed') < prepare.index('Candidate trust bootstrap failed') < prepare.index('Candidate dependency installation failed')


@pytest.mark.parametrize('script', [
    'python -m pip --isolated install --require-hashes --no-deps \\\n'
    '  -r requirements-trust-bootstrap.txt\npython -m pip install pytest',
    '& "$env:RUNNER_TEMP/venv/Scripts/python.exe" -m pip --isolated install `\n'
    '  --require-hashes --no-deps -r requirements-trust-bootstrap.txt\n'
    '& "$env:RUNNER_TEMP/venv/Scripts/python.exe" -m pip install pytest',
    'pip3 install --no-deps --require-hashes -r requirements-trust-bootstrap.txt\npip3 install pytest',
    'python -c "print(\'requirements-trust-bootstrap.txt\')"\npython -m pip check',
    'python - <<\'PY\'\nrequired = ("requirements-trust-bootstrap.txt",)\nPY\n'
    '# pip install -r requirements-trust-bootstrap.txt\n'
    'echo "requirements-trust-bootstrap.txt"',
    'printf "%s\\n" "requirements-trust-bootstrap.txt"',
])
def test_trust_reader_accepts_verified_commands_and_offline_inspection(script):
    _assert_job_bootstraps_trust({'steps': [{'run': script}]})


@pytest.mark.parametrize('script', [
    'python -m pip install pytest',
    'python -m pip --isolated --disable-pip-version-check install pytest',
    'pip install pytest; pip install --no-deps --require-hashes -r requirements-trust-bootstrap.txt',
    'pip install --no-deps -r requirements-trust-bootstrap.txt',
    'pip install --require-hashes -r requirements-trust-bootstrap.txt',
    'pip install -r requirements-trust-bootstrap.txt; echo "--require-hashes --no-deps"',
    'echo "pip install --require-hashes --no-deps -r requirements-trust-bootstrap.txt"\npip install pytest',
    'python -c "print(\'requirements-trust-bootstrap.txt\')"\npip install pytest',
    'python - <<\'PY\'\nprint("pip install --no-deps --require-hashes -r requirements-trust-bootstrap.txt")\nPY\npip install pytest',
    'pip install --no-deps -r requirements-trust-bootstrap.txt # --require-hashes',
    'env python -m pip install pytest',
    'sudo pip install pytest',
    'uv pip install pytest',
    'bash -c "pip install pytest"',
    'command python -m pip install pytest',
    'timeout 60 pip install pytest',
    'python -c "import os; os.system(\'pip install pytest\')"',
    'python - <<\'PY\'\nimport os\nos.system("pip install pytest")\nPY',
    'if true; then pip install pytest; fi',
    'echo $(pip install pytest)',
    'pip install --no-deps --require-hashes -r requirements-trust-bootstrap.txt & pip install pytest',
    'false && pip install --no-deps --require-hashes -r requirements-trust-bootstrap.txt || pip install pytest',
    'if false; then\npip install --no-deps --require-hashes -r requirements-trust-bootstrap.txt\nfi\npip install pytest',
    "echo '$(pip install pytest)'",
    "printf -v installer '%s' 'pip install pytest'; eval \"$installer\"",
    "echo 'pip install pytest' > installer.sh; sh installer.sh",
    "printf '%s\\n' 'pip install pytest' > installer.sh; sh installer.sh",
])
def test_trust_reader_rejects_unverified_or_late_bootstrap(script):
    with pytest.raises(AssertionError):
        _assert_job_bootstraps_trust({'steps': [{'run': script}]})


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


def test_module_container_bootstraps_match_reviewed_wheel_hashes():
    root = Path(__file__).resolve().parents[2]
    entries = [line for line in (root / 'requirements-trust-bootstrap.txt').read_text().splitlines()
               if line and not line.startswith('#')]
    urls = [line.split(' @ ')[1].replace(' --hash=sha256:', '#sha256=') for line in entries]
    for path in ['modules/foundups/simulator/Dockerfile',
                 'modules/communication/moltbot_bridge/Dockerfile.nanoclaw']:
        docker = (root / path).read_text()
        for url in urls:
            assert url in docker
            assert docker.index(url) < docker.index('&& python -m pip install')
        assert '--require-hashes' in docker and '--no-deps' in docker
    node = (root / 'modules/foundups/gotjunk/frontend/Dockerfile').read_text()
    assert 'FROM node:22.23.4-alpine AS builder' in node
    workflow = yaml.load((root / '.github/workflows/validate-esingularity.yml').read_text(), Loader=yaml.BaseLoader)
    versions = [s.get('with', {}).get('node-version') for j in workflow['jobs'].values()
                for s in j.get('steps', []) if 'actions/setup-node@' in s.get('uses', '')]
    assert versions == ['24.22.1']
