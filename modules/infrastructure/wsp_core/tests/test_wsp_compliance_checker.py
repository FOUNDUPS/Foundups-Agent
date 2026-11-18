"""Offline tracked-inventory and no-write contracts for WSPComplianceChecker."""
import asyncio
import ast
import hashlib
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
from unittest.mock import patch
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from modules.infrastructure.wsp_core.src import wsp_compliance_checker as checker_module

Checker = checker_module.WSPComplianceChecker


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / 'repo'
    root.mkdir()
    subprocess.run(['git', 'init', '-q', str(root)], check=True)
    return root


def put(repo, path, text, tracked=True):
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding='utf-8')
    if tracked:
        subprocess.run(['git', '-C', str(repo), 'add', '--', path], check=True)
    return target


def scan(repo, **kwargs):
    return asyncio.run(Checker(repo, **kwargs).scan())


def rows_of(rows, kind):
    return [r for r in rows if r.violation_type.name == kind]


def test_constructor_never_opens_or_creates_pattern_database(repo):
    with patch.object(sqlite3, 'connect', side_effect=AssertionError('database open')) as connect:
        Checker(repo)
    connect.assert_not_called()


def test_scan_reads_only_tracked_source_and_never_executes_it(repo):
    put(repo, 'modules/infrastructure/example/src/service.py', 'raise AssertionError("must not import")\n')
    for prefix in ('.worktrees', 'agent-worktrees', 'vendor', 'chroma'):
        put(repo, f'modules/{prefix}/foreign/src/trap.py', '# not tracked\n' * 800, False)
    put(repo, 'local_root.py', '# local\n' * 800, False)
    opened = []
    original = Path.open
    def guarded(path, *a, **k):
        if path.is_relative_to(repo):
            opened.append(path.relative_to(repo).as_posix())
            assert path.name == 'service.py'
        return original(path, *a, **k)
    with patch.object(Path, 'open', guarded):
        rows = scan(repo)
    assert opened == ['modules/infrastructure/example/src/service.py']
    assert not rows_of(rows, 'SCAN_INCOMPLETE')
    assert all('foreign' not in str(r.affected_files) for r in rows)


def test_untracked_docs_do_not_satisfy_tracked_module_requirements(repo):
    put(repo, 'modules/infrastructure/example/src/service.py', 'value = 1\n')
    for path in ('ModLog.md', 'tests/README.md', 'requirements.txt'):
        put(repo, f'modules/infrastructure/example/{path}', 'local only\n', False)
    rows = scan(repo)
    assert len(rows_of(rows, 'DOCUMENTATION')) == 1
    assert len(rows_of(rows, 'TESTING')) == 1
    assert len(rows_of(rows, 'DEPENDENCY')) == 1
    assert all(not r.auto_fixable for r in rows)


def test_tracked_module_documents_are_recognized_without_reading_contents(repo):
    put(repo, 'modules/infrastructure/example/src/service.py', 'value = 1\n')
    for path in ('ModLog.md', 'tests/README.md', 'requirements.txt'):
        put(repo, f'modules/infrastructure/example/{path}', 'fixture\n')
    original = Path.open
    def guarded(path, *a, **k):
        assert path.suffix not in {'.md', '.txt'}
        return original(path, *a, **k)
    with patch.object(Path, 'open', guarded):
        assert scan(repo) == []


@pytest.mark.parametrize('relative', ['modules/infrastructure/example/.env.py', 'modules/.env.sample/data.py'])
def test_environment_content_is_never_opened(repo, relative):
    put(repo, relative, '# fixture only\n')
    with patch.object(Path, 'open', side_effect=AssertionError('environment read')):
        scan(repo)


def test_missing_git_inventory_is_an_explicit_failure(repo):
    with patch.object(Checker, '_git', side_effect=ValueError('unavailable')):
        rows = scan(repo)
    assert len(rows) == 1 and len(rows_of(rows, 'SCAN_INCOMPLETE')) == 1


def test_nested_project_directory_is_not_accepted_as_git_root(repo):
    nested = repo / 'nested'
    nested.mkdir()
    rows = scan(nested)
    assert len(rows) == 1 and len(rows_of(rows, 'SCAN_INCOMPLETE')) == 1


@pytest.mark.parametrize('record', [
    '100644 abc 0\t../outside.py\0', '100644 abc 0\t/absolute.py\0',
    '100644 abc 0\tC:/outside.py\0', '100644 abc 0\tbad\\path.py\0',
    '100644 abc 1\tconflicted.py\0', 'not a stage entry\0',
    '100644 abc 0\ttruncated.py',
    '100644 abc 0\tduplicate.py\0' * 2,
])
def test_invalid_git_inventory_never_reads_source(repo, record):
    with patch.object(Checker, '_git', side_effect=[str(repo), record]):
        with patch.object(Path, 'open', side_effect=AssertionError('unsafe read')):
            rows = scan(repo)
    assert len(rows) == 1 and rows_of(rows, 'SCAN_INCOMPLETE')


@pytest.mark.parametrize('mode', ['120000', '160000'])
def test_git_link_and_submodule_entries_are_not_followed(repo, mode):
    with patch.object(Checker, '_git', side_effect=[str(repo), f'{mode} abc 0\tforeign.py\0']):
        with patch.object(Path, 'open', side_effect=AssertionError('link read')):
            rows = scan(repo)
    assert rows_of(rows, 'SCAN_INCOMPLETE')


def test_missing_tracked_source_is_not_silently_ignored(repo):
    path = put(repo, 'modules/infrastructure/example/src/service.py', 'value = 1\n')
    path.unlink()
    rows = scan(repo)
    assert len(rows_of(rows, 'SCAN_INCOMPLETE')) == 1


def test_redirected_parent_is_never_opened(repo):
    put(repo, 'modules/infrastructure/example/src/service.py', 'value = 1\n')
    original = Path.lstat
    class Redirect:
        st_mode = 0o120777
        st_file_attributes = 0x400
    def metadata(path, *a, **k):
        return Redirect() if path.name == 'src' else original(path, *a, **k)
    with patch.object(Path, 'lstat', metadata):
        with patch.object(Path, 'open', side_effect=AssertionError('redirect read')):
            rows = scan(repo)
    assert rows_of(rows, 'SCAN_INCOMPLETE')


def test_oversized_source_is_reported(repo):
    put(repo, 'modules/infrastructure/example/src/service.py', '#' * (2 * 1024 * 1024 + 1))
    assert rows_of(scan(repo), 'SCAN_INCOMPLETE')


def test_total_source_budget_reports_uninspected_tail(repo, monkeypatch):
    for name in ('a.py', 'b.py'):
        put(repo, f'modules/infrastructure/example/src/{name}', '# fixture\n')
    first = repo / 'modules/infrastructure/example/src/a.py'
    monkeypatch.setattr(checker_module, 'MAX_TOTAL_BYTES', len(first.read_bytes()), raising=False)
    rows = rows_of(scan(repo), 'SCAN_INCOMPLETE')
    assert [row.affected_files for row in rows] == [['modules/infrastructure/example/src/b.py']]


def test_caller_git_environment_cannot_replace_the_inventory_root(repo, tmp_path, monkeypatch):
    put(repo, 'diagnostic.py', 'value = 1\n')
    foreign = tmp_path / 'foreign'
    subprocess.run(['git', 'init', '-q', str(foreign)], check=True)
    monkeypatch.setenv('GIT_DIR', str(foreign / '.git'))
    monkeypatch.setenv('GIT_WORK_TREE', str(foreign))
    rows = scan(repo)
    assert not rows_of(rows, 'SCAN_INCOMPLETE')
    assert any(row.affected_files == ['diagnostic.py'] for row in rows_of(rows, 'ARCHITECTURE'))


def test_component_counts_use_direct_children_not_repeated_ancestor_totals(repo):
    for i in range(21):
        put(repo, f'modules/infrastructure/example/src/group/component_{i}.py', 'value = 1\n')
    counts = rows_of(scan(repo), 'COMPONENT_COUNT')
    assert [r.affected_files for r in counts] == [['modules/infrastructure/example/src/group']]


def test_domain_src_and_tests_are_not_phantom_duplicate_modules(repo):
    for domain in ('infrastructure', 'communication'):
        for folder in ('src', 'tests'):
            put(repo, f'modules/{domain}/{folder}/example.py', 'value = 1\n')
    rows = scan(repo)
    assert not rows_of(rows, 'NAMING_COHERENCE')
    architecture = rows_of(rows, 'ARCHITECTURE')
    assert len(architecture) == 4


def test_real_duplicate_module_names_remain_findings(repo):
    for domain in ('infrastructure', 'communication'):
        put(repo, f'modules/{domain}/example/src/service.py', 'value = 1\n')
    assert len(rows_of(scan(repo), 'NAMING_COHERENCE')) == 1


def test_monitoring_and_documented_wre_exception_are_recognized(repo):
    put(repo, 'modules/monitoring/example/src/service.py', 'value = 1\n')
    put(repo, 'modules/wre_core/src/service.py', 'value = 1\n')
    assert not rows_of(scan(repo), 'ARCHITECTURE')


def test_noncanonical_domain_is_reported(repo):
    put(repo, 'modules/data_processing/example/src/service.py', 'value = 1\n')
    assert any(r.affected_files == ['modules/data_processing'] for r in rows_of(scan(repo), 'ARCHITECTURE'))


def test_tracked_test_file_and_name_containing_test_are_not_blanket_exempt(repo):
    for relative in ('modules/infrastructure/example/tests/test_large.py', 'modules/infrastructure/example/src/latest.py'):
        put(repo, relative, '# fixture\n' * 801)
    assert len(rows_of(scan(repo), 'FILE_SIZE')) == 2


@pytest.mark.parametrize('lines,severity', [(799, None), (800, 'low'), (1000, 'low'), (1001, 'medium'), (1500, 'high')])
def test_size_hints_use_current_wsp62_thresholds(repo, lines, severity):
    put(repo, 'modules/infrastructure/example/src/service.py', '# fixture\n' * lines)
    rows = rows_of(scan(repo), 'FILE_SIZE')
    assert [r.severity for r in rows] == ([] if severity is None else [severity])


def test_explicit_memory_snapshot_is_frozen_and_does_not_open_database(repo):
    put(repo, 'diagnostic.py', 'value = 1\n')
    selected = [('root_file', 'diagnostic.py')]
    checker = Checker(repo, known_false_positives=selected)
    selected.clear()
    with patch.object(sqlite3, 'connect', side_effect=AssertionError('database open')):
        assert not rows_of(asyncio.run(checker.scan()), 'ARCHITECTURE')


def test_scanner_preserves_tracked_untracked_and_git_index_bytes(repo):
    put(repo, 'modules/infrastructure/example/src/service.py', 'value = 1\n')
    put(repo, 'local-note.txt', 'untouched\n', False)
    def snapshot():
        return {p.relative_to(repo).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in repo.rglob('*') if p.is_file()}
    before = snapshot()
    scan(repo)
    assert snapshot() == before


def test_repeated_scan_refreshes_inventory(repo):
    checker = Checker(repo)
    assert asyncio.run(checker.scan()) == []
    put(repo, 'diagnostic.py', 'value = 1\n')
    assert rows_of(asyncio.run(checker.scan()), 'ARCHITECTURE')


@pytest.mark.parametrize('explicit', [False, True])
def test_github_consumer_binds_scanner_and_workflow_to_the_same_repository(repo, explicit):
    # Execute the real constructor body with inert dependencies, without
    # importing network clients or enabling any GitHub workflow.
    relative = 'modules/platform_integration/github_integration/src/wsp_automation.py'
    source_path = ROOT / relative
    tree = ast.parse(source_path.read_bytes())
    owner = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'WSPAutomationManager')
    constructor = next(n for n in owner.body if isinstance(n, ast.FunctionDef) and n.name == '__init__')
    constructor.returns = None
    for argument in constructor.args.args:
        argument.annotation = None
    isolated = ast.Module(body=[constructor], type_ignores=[])
    namespace = {
        '__file__': str(repo / relative), 'Path': Path,
        'logging': SimpleNamespace(getLogger=lambda _: None), '__name__': 'synthetic_constructor',
        'WSPComplianceChecker': lambda **kwargs: SimpleNamespace(**kwargs),
        'GitHubAutomation': lambda **kwargs: SimpleNamespace(**kwargs),
        'WREGitHubIntegration': lambda **kwargs: SimpleNamespace(**kwargs),
    }
    exec(compile(ast.fix_missing_locations(isolated), '<reviewed constructor>', 'exec'), namespace)
    manager = SimpleNamespace()
    selected = repo / 'selected' if explicit else repo
    namespace['__init__'](manager, project_root=selected if explicit else None)
    assert manager.project_root == selected
    assert manager.checker.project_root == selected
    assert manager.wre_integration.project_root == selected


def test_data_container_does_not_acquire_module_document_requirements(repo):
    put(repo, 'modules/telemetry/feedback/session.json', '{}\n')
    rows = scan(repo)
    for kind in ('DOCUMENTATION', 'TESTING', 'DEPENDENCY', 'NAMING_COHERENCE'):
        assert not rows_of(rows, kind)
    assert any(r.affected_files == ['modules/telemetry/feedback']
               and 'root-contract evidence' in r.description for r in rows)


def test_unqualified_container_remains_visible_under_module_suppression(repo):
    put(repo, 'modules/foundups/intake/docs/OUTCOME.md', 'intake evidence\n')
    rows = scan(repo, known_false_positives=[('module', 'intake')])
    assert len(rows) == 1 and rows[0].affected_files == ['modules/foundups/intake']
    assert rows[0].violation_type.name == 'ARCHITECTURE' and not rows[0].auto_fixable


def test_both_auditors_share_immutable_domain_and_exception_objects():
    from tools.modular_audit import modular_audit as audit
    from tools.modular_audit import tracked_audit as tracked
    assert audit.ENTERPRISE_DOMAINS is checker_module.CORE_DOMAINS
    assert audit.ARCHITECTURAL_EXCEPTIONS is checker_module.ARCHITECTURAL_EXCEPTIONS
    assert tracked.RESERVED is checker_module.RESERVED_BLOCK_NAMES
    for values in (audit.ENTERPRISE_DOMAINS, audit.ARCHITECTURAL_EXCEPTIONS, tracked.RESERVED):
        assert isinstance(values, frozenset)
        with pytest.raises(AttributeError):
            values.add('unreviewed_domain')


@pytest.mark.parametrize('owner', ['WSP_framework', 'WSP_knowledge'])
def test_shared_policy_matches_canonical_wsp3_mirrors(owner):
    from modules.infrastructure.wsp_core.src import wsp_domain_policy as policy
    text = (ROOT / owner / 'src/WSP_3_Enterprise_Domain_Organization.md').read_text(encoding='utf-8')
    section = text.split('## 3. Core Domains', 1)[1].split('### 3.1', 1)[0]
    assert frozenset(re.findall(r'^- \*\*([a-z_]+)/\*\*:', section, flags=re.M)) == policy.CORE_DOMAINS
    assert 'monitoring' in policy.CORE_DOMAINS and 'data_processing' not in policy.CORE_DOMAINS
    exception = text.split('### 5.1 WRE Core Engine', 1)[1].split('## 6.', 1)[0]
    assert '**Location**: `modules/wre_core/`' in exception


@pytest.mark.parametrize('evidence', ['src/service.py', 'tests/test_service.py', 'README.md', 'INTERFACE.md'])
def test_contract_evidence_promotes_container_without_changing_other_scope(evidence):
    from modules.infrastructure.wsp_core.src import wsp_domain_policy as policy
    paths = ['modules/foundups/intake/docs/OUTCOME.md',
             'modules/infrastructure/src/domain_service.py',
             'modules/communication/tests/test_domain.py',
             'modules/infrastructure/docs/README.md',
             'modules/infrastructure/.private/src/service.py',
             'modules/wre_core/README.md', f'modules/monitoring/health/{evidence}']
    assert policy.evidenced_module_roots(iter(paths)) == ('modules/monitoring/health', 'modules/wre_core')
    assert policy.unqualified_module_containers(iter(paths)) == ('modules/foundups/intake',)
    paths.append('modules/foundups/intake/INTERFACE.md')
    assert policy.unqualified_module_containers(iter(paths)) == ()
    assert 'modules/foundups/intake' in policy.evidenced_module_roots(iter(paths))


def test_pure_policy_preserves_explicit_exception_without_io():
    from modules.infrastructure.wsp_core.src import wsp_domain_policy as policy
    with patch.object(Path, 'open', side_effect=AssertionError('content read')):
        with patch.object(Path, 'lstat', side_effect=AssertionError('metadata read')):
            with patch.object(subprocess, 'run', side_effect=AssertionError('process')):
                paths = ['modules/legacy/notes.md', 'modules/data_processing/data/session.json']
                assert policy.evidenced_module_roots(paths, {'legacy'}) == ('modules/legacy',)
                assert policy.unqualified_module_containers(paths, {'legacy'}) == ('modules/data_processing/data',)
