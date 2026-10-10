"""Fail-closed secret gate: tracked tree plus all introduced commits.

Only scanner metadata is printed. No credentials or redacted raw report are
uploaded. Full retained history is scanned on scheduled/manual/new-branch runs.
"""
from pathlib import Path, PurePosixPath
import json
import hashlib
import os
import re
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[2]


def tracked_env_files(paths):
    # Templates remain scanned by Gitleaks; only exact template suffixes pass
    # the filename policy. Nested .env.local/.env.production are credentials too.
    return [p for p in paths if (PurePosixPath(p).name == '.env' or
            PurePosixPath(p).name.startswith('.env.')) and
            not PurePosixPath(p).name.endswith(('.example', '.sample', '.template'))]


def history_range(event, base, head):
    if not re.fullmatch(r'[0-9a-f]{40}', head):
        raise ValueError('Invalid security scan head')
    if event in {'pull_request', 'push'} and base and base != '0' * 40:
        if not re.fullmatch(r'[0-9a-f]{40}', base):
            raise ValueError('Invalid security scan base')
        return f'{base}..{head}'
    return '--all'


def finding_fingerprint(finding, source_root):
    path = Path(finding['File'])
    if path.is_absolute():
        path = path.relative_to(source_root)
    relative = path.as_posix()
    if '..' in path.parts:
        raise ValueError('Invalid report path')
    commit = finding.get('Commit')
    if commit:
        if not re.fullmatch(r'[0-9a-f]{40}', commit):
            raise ValueError('Invalid finding commit')
        content = subprocess.check_output(['git', 'show', f'{commit}:{relative}'], cwd=ROOT)
    else:
        content = (source_root / path).read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    identity = '\0'.join((relative, digest, finding['RuleID'], str(finding['StartLine'])))
    return hashlib.sha256(identity.encode()).hexdigest()


def reviewed_finding(finding, source_root):
    document = json.loads((ROOT / '.github/security/reviewed-findings.json').read_text())
    return finding_fingerprint(finding, source_root) in document['reviewed_findings']


def scan(arguments, report):
    # A scanner error, missing binary/report, or unreadable report is never clean.
    result = subprocess.run(['gitleaks', *arguments, '--redact=100',
        '--no-banner', '--ignore-gitleaks-allow', '--exit-code', '1',
        '--config', str(ROOT / '.github/security/gitleaks.toml'),
        '--gitleaks-ignore-path', str(report.parent / 'no-implicit-ignore'),
        '--timeout', '900', '--log-level', 'error', '--no-color',
        '--report-format', 'json', '--report-path', str(report)],
        cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=930)
    if result.stderr:
        print('ERROR: scanner reported an execution error; details withheld to protect secrets')
        return 1
    if report.exists():
        findings = json.loads(report.read_text(encoding='utf-8'))
        if not isinstance(findings, list):
            raise ValueError('Invalid scanner report')
        unreviewed = [finding for finding in findings
                      if not reviewed_finding(finding, Path(arguments[1]))]
        for finding in unreviewed:
            # Never print Secret, Match, commit message, or scanner stderr.
            print(json.dumps({k: finding.get(k) for k in
                              ('RuleID', 'File', 'StartLine', 'Commit')}))
        print(f'Secret scan: {len(unreviewed)} unreviewed, '
              f'{len(findings) - len(unreviewed)} exact reviewed fixture/metadata finding(s), '
              f'exit={result.returncode}')
        if unreviewed:
            return 1
    else:
        print('ERROR: scanner produced no report')
        return 1
    # Exit 1 means findings; only exact reviewed findings may clear it.
    return 0 if result.returncode == 0 or (result.returncode == 1 and findings) else 1


def main():
    paths = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    forbidden = tracked_env_files(filter(None, paths))
    for path in forbidden:
        print(f'ERROR: tracked environment file: {path}')
    log_options = history_range(os.environ.get('SECURITY_EVENT', 'workflow_dispatch'),
                               os.environ.get('SECURITY_BASE', ''),
                               os.environ.get('SECURITY_HEAD') or subprocess.check_output(
                                   ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip())
    with tempfile.TemporaryDirectory(prefix='foundups-secret-scan-') as directory:
        temporary = Path(directory)
        tree = temporary / 'tree'
        tree.mkdir()
        # git archive excludes .git, local credentials, and untracked artifacts.
        archive = temporary / 'tree.tar'
        subprocess.run(['git', 'archive', '--format=tar', '-o', str(archive), 'HEAD'],
                       cwd=ROOT, check=True)
        subprocess.run(['tar', '--no-same-owner', '-xf', str(archive), '-C', str(tree)], check=True)
        failed = bool(forbidden)
        failed |= bool(scan(['dir', str(tree)], temporary / 'tree.json'))
        failed |= bool(scan(['git', str(ROOT), '--log-opts=' + log_options], temporary / 'history.json'))
        return int(failed)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, subprocess.SubprocessError):
        print('ERROR: security scan incomplete; gate failed', file=sys.stderr)
        sys.exit(1)
