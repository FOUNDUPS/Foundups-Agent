"""Bounded scaffold-generator regressions; no production module import."""
import ast
import importlib.util
import logging
from pathlib import Path
import sys
from unittest.mock import patch

import pytest

SOURCE = Path(__file__).resolve().parents[1] / 'tools/wsp_compliance_guardian.py'


@pytest.fixture
def guardian_module():
    name = '_scaffold_guardian_under_test'
    spec = importlib.util.spec_from_file_location(name, SOURCE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        with patch('logging.FileHandler', return_value=logging.NullHandler()):
            spec.loader.exec_module(module)
        yield module
    finally:
        sys.modules.pop(name, None)


def make_source(root, package='example'):
    source = root / f'modules/infrastructure/{package}/src/worker.py'
    source.parent.mkdir(parents=True)
    source.write_text("raise RuntimeError('production source must not be imported')\n", encoding='utf-8')
    return source


@pytest.mark.parametrize('package', ['example', '0102_orchestrator'])
def test_generated_scaffold_parses_without_importing_production(tmp_path, guardian_module, package):
    source = make_source(tmp_path, package)
    target = source.parent.parent / 'tests/test_worker.py'
    guardian_module.WSPComplianceGuardian(tmp_path)._create_test_skeleton(target, str(source))
    text = target.read_text(encoding='utf-8')
    tree = ast.parse(text)
    assert 'WSP 5 compliant test coverage' not in text
    assert 'SPECIFIED_NOT_IMPLEMENTED' in text
    assert not any(isinstance(node, ast.ImportFrom) and node.module and node.module.startswith('modules') for node in ast.walk(tree))
    namespace = {'__name__': '_generated_scaffold', '__file__': str(target)}
    exec(compile(tree, str(target), 'exec'), namespace)
    assert namespace['WRE_TEST_MODE'] == 'scaffold'
    assert namespace['SOURCE_MODULE'] == f'modules.infrastructure.{package}.src.worker'
    assert not any(isinstance(node, ast.Assert) and isinstance(node.test, ast.Constant) and node.test.value is True for node in ast.walk(tree))


@pytest.mark.parametrize('outside', ['source', 'destination'])
def test_generator_rejects_outside_project_before_writing(tmp_path, guardian_module, outside):
    root = tmp_path / 'project'
    source = make_source(root)
    target = root / 'modules/infrastructure/example/tests/test_worker.py'
    if outside == 'source':
        source = tmp_path / 'outside.py'
        source.write_text('value = 1\n', encoding='utf-8')
    else:
        target = tmp_path / 'outside_tests/test_worker.py'
    with pytest.raises(ValueError):
        guardian_module.WSPComplianceGuardian(root)._create_test_skeleton(target, str(source))
    assert not target.exists()
    assert not target.parent.exists()


def test_generator_preserves_existing_authored_test(tmp_path, guardian_module):
    source = make_source(tmp_path)
    target = source.parent.parent / 'tests/test_worker.py'
    target.parent.mkdir()
    authored = 'def test_authored():\n    assert 2 + 2 == 4\n'
    target.write_text(authored, encoding='utf-8')
    with pytest.raises(FileExistsError):
        guardian_module.WSPComplianceGuardian(tmp_path)._create_test_skeleton(target, str(source))
    assert target.read_text(encoding='utf-8') == authored


def test_generator_rejects_missing_source_before_writing(tmp_path, guardian_module):
    target = tmp_path / 'tests/test_missing.py'
    with pytest.raises((ValueError, FileNotFoundError)):
        guardian_module.WSPComplianceGuardian(tmp_path)._create_test_skeleton(target, str(tmp_path / 'missing.py'))
    assert not target.exists()


def test_scaffold_creation_does_not_claim_coverage_fixed(tmp_path, guardian_module):
    source = make_source(tmp_path)
    module_root = source.parent.parent
    target = module_root / 'tests/test_worker.py'
    guardian = guardian_module.WSPComplianceGuardian(tmp_path)
    violation = guardian_module.Violation(
        standard=guardian_module.WSPStandard.WSP_5,
        level=guardian_module.ComplianceLevel.WARNING,
        file_path=str(source), description='No corresponding test file for worker.py',
        remediation=f'Create test file: {target}')
    assert guardian._auto_fix_violation(module_root, violation) is False
    assert target.is_file()
    report = guardian_module.ComplianceReport(str(module_root), '2026-10-29')
    guardian._validate_test_coverage(module_root, report)
    assert any(item.standard == guardian_module.WSPStandard.WSP_5 for item in report.violations)


def test_nested_source_generates_discoverable_test_filename(tmp_path, guardian_module):
    source = tmp_path / 'modules/infrastructure/example/src/adapters/worker.py'
    source.parent.mkdir(parents=True)
    source.write_text('value = 1\n', encoding='utf-8')
    module_root = source.parents[2]
    (module_root / 'tests').mkdir()
    guardian = guardian_module.WSPComplianceGuardian(tmp_path)
    report = guardian_module.ComplianceReport(str(module_root), '2026-10-29')
    guardian._validate_test_coverage(module_root, report)
    violation = next(item for item in report.violations if item.file_path == str(source))
    target = module_root / 'tests/adapters/test_worker.py'
    assert violation.remediation == f'Create test file: {target}'
    assert guardian._auto_fix_violation(module_root, violation) is False
    assert target.is_file()
    assert not (module_root / 'tests/test_adapters/worker.py').exists()
