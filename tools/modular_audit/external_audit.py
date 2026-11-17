"""One bounded external audit per repository scope; no install/fix operations."""
from contextlib import contextmanager
from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from modules.infrastructure.wre_core.src.wre_git_process_io import run_bounded_process

if __package__:
    from .external_audit_results import AuditSummary, MAX_OUTPUT_BYTES, summarize_external_audit, summary_findings
    from .tracked_audit import MAX_PATHS, environment_path, source_metadata
else:
    from external_audit_results import AuditSummary, MAX_OUTPUT_BYTES, summarize_external_audit, summary_findings
    from tracked_audit import MAX_PATHS, environment_path, source_metadata

MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_TOTAL_BYTES = 128 * 1024 * 1024
MAX_TARGET_BYTES = 4 * 1024 * 1024


def run_json_audit(tool, command, root, *, runner=None):
    """Retain exit-1 JSON; discard raw failures, stdout and stderr from findings."""
    if tool not in {'pip-audit', 'bandit', 'npm'}:
        raise ValueError('unknown_audit_tool')
    runner = run_bounded_process if runner is None else runner
    chunks, code = [], 0
    environment = {k: v for k, v in os.environ.items()
                   if not k.upper().startswith('PIP_AUDIT_') and k.upper() != 'NODE_OPTIONS'}
    try:
        runner(tuple(command), cwd=Path(root), max_bytes=MAX_OUTPUT_BYTES,
               timeout_s=120, chunks=chunks, output_path=None,
               environment=environment, stdin_bytes=None)
    except subprocess.CalledProcessError as failure:
        code = failure.returncode
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired):
        return AuditSummary(tool, incomplete=1)
    return summarize_external_audit(tool, code, b''.join(chunks))


@dataclass(frozen=True)
class BanditPlan:
    paths: tuple[str, ...]
    incomplete: int
    excluded_environment: int


def prepare_bandit_plan(root, tracked_paths):
    selected, seen = [], set()
    incomplete = environments = total = target_bytes = 0
    for index, relative in enumerate(tracked_paths):
        if index >= MAX_PATHS:
            incomplete += 1
            break
        if type(relative) is not str or relative in seen:
            incomplete += 1
            continue
        seen.add(relative)
        if environment_path(relative):
            environments += 1
            continue
        if not relative.endswith('.py'):
            continue
        try:
            if not relative.startswith('modules/') or any(c in relative for c in ',%'):
                raise ValueError('unrepresentable_target')
            size = source_metadata(Path(root), relative).st_size
            target_bytes += len(relative.encode('utf-8')) + 1
            if size > MAX_FILE_BYTES or total + size > MAX_TOTAL_BYTES or target_bytes > MAX_TARGET_BYTES:
                raise ValueError('source_budget_exceeded')
            selected.append(relative)
            total += size
        except (OSError, ValueError, UnicodeError):
            incomplete += 1
    return BanditPlan(tuple(sorted(selected)), incomplete, environments)


@contextmanager
def bandit_target_file(plan):
    """Explicit INI targets avoid recursive traversal and argument-length limits."""
    path = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', prefix='foundups-bandit-',
                                         encoding='utf-8', newline='\n', delete=False) as handle:
            path = Path(handle.name)
            handle.write('[bandit]\ntargets = ' + ','.join(plan.paths) + '\n')
        yield path
    finally:
        if path is not None:
            path.unlink(missing_ok=True)


def run_pip_audit(root):
    """Audit this interpreter's installed environment, not each requirements file."""
    command = (sys.executable, '-I', '-B', '-m', 'pip_audit', '--format=json', '--progress-spinner=off')
    return summary_findings(run_json_audit('pip-audit', command, root))


def run_bandit(root, tracked_paths):
    plan = prepare_bandit_plan(root, tracked_paths)
    findings = []
    if plan.incomplete:
        findings.append(f'SECURITY_SCAN_ERROR: bandit source inspection incomplete ({plan.incomplete})')
    if plan.excluded_environment:
        findings.append(f'SECURITY_WARNING: bandit excluded environment paths ({plan.excluded_environment})')
    if not plan.paths:
        return findings
    try:
        with bandit_target_file(plan) as target:
            command = (sys.executable, '-I', '-B', '-m', 'bandit', '--ini', str(target), '-f', 'json')
            findings.extend(summary_findings(run_json_audit('bandit', command, root)))
    except (OSError, ValueError):
        findings.append('SECURITY_SCAN_ERROR: bandit target configuration unavailable')
    return findings


def _npm_command():
    """Invoke npm's JS entrypoint through Node, never a Windows command shell."""
    node, npm = shutil.which('node'), shutil.which('npm')
    if not node or not npm:
        raise ValueError('npm_runtime_unavailable')
    node_path, npm_path = Path(node).resolve(), Path(npm).resolve()
    entry = node_path.parent / 'node_modules/npm/bin/npm-cli.js' if os.name == 'nt' else npm_path
    if not entry.is_file() or entry.suffix != '.js':
        raise ValueError('npm_entrypoint_unavailable')
    return (str(node_path), str(entry), 'audit', '--json', '--ignore-scripts',
            '--no-fund', '--no-update-notifier', '--audit-level=low', '--package-lock-only',
            '--workspaces=false', '--include=dev', '--include=optional', '--include=peer')


def run_npm_audit(root):
    """Audit only the admitted root package/lock pair; never invoke audit fix."""
    try:
        command = _npm_command()
    except (OSError, ValueError):
        return ['SECURITY_SCAN_ERROR: npm runtime unavailable']
    return summary_findings(run_json_audit('npm', command, root))
