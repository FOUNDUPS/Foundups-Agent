"""Exercise real startup/constructor bodies with all runtime effects replaced.

AST loading follows the existing preflight test boundary: importing main itself
loads environment files and CLI services unrelated to these deterministic gates.
"""
import ast
from contextlib import ExitStack
import json
import logging
import runpy
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, Optional
from unittest.mock import Mock, patch

import pytest


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = 'modules.ai_intelligence.ai_overseer.src'


def source_functions(path, names, namespace, class_name=None):
    tree = ast.parse(path.read_text(encoding='utf-8'))
    if class_name:
        tree = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name)
    body = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    assert {node.name for node in body} == set(names)
    exec(compile(ast.Module(body=body, type_ignores=[]), str(path), 'exec'), namespace)


def constructor_fixture(tmp_path, stack):
    namespace = dict(Path=Path, Any=Any, Optional=Optional, Dict=Dict, json=json,
                     os=__import__('os'), logging=logging, logger=logging.getLogger(__name__),
                     __package__=PACKAGE, HOLO_AVAILABLE=True, MCP_AVAILABLE=False,
                     PATTERN_MEMORY_AVAILABLE=False, AUTOGATE_AVAILABLE=True,
                     WSP_FRAMEWORK_SENTINEL_AVAILABLE=False, CORRELATOR_AVAILABLE=False,
                     AutonomousRefactoringOrchestrator=Mock(), AutoGate=Mock(),
                     DaemonLogger=Mock(), MetricsAppender=Mock(), PatchAllowlist=Mock(),
                     PatchExecutor=Mock(), _env_int_with_fallback=lambda *args: args[-1])
    sentinel = SimpleNamespace(check=Mock(return_value={'available': True, 'passed': False, 'message': 'rejected'}))
    imports = {
        PACKAGE + '.holo_adapter': SimpleNamespace(HoloAdapter=Mock()),
        PACKAGE + '.ii_agent_adapter': SimpleNamespace(IIAgentAdapter=Mock()),
        PACKAGE + '.openclaw_security_sentinel': SimpleNamespace(OpenClawSecuritySentinel=Mock(return_value=sentinel)),
    }
    stack.enter_context(patch.dict('sys.modules', imports))
    stack.enter_context(patch.dict('os.environ', {}, clear=True))
    source_functions(ROOT / 'modules/ai_intelligence/ai_overseer/src/ai_overseer.py',
                     {'__init__', '_load_patterns', 'monitor_openclaw_security'}, namespace,
                     'AIIntelligenceOverseer')
    owner = type('OwnerUnderTest', (), {name: namespace[name] for name in ('__init__', '_load_patterns', 'monitor_openclaw_security')})
    return owner, namespace, sentinel


def test_preflight_constructor_does_not_acquire_models_and_preserves_rejection(tmp_path):
    with ExitStack() as stack:
        owner, namespace, sentinel = constructor_fixture(tmp_path, stack)
        instance = owner(tmp_path, initialize_models=False)
        namespace['AutonomousRefactoringOrchestrator'].assert_not_called()
        namespace['AutoGate'].assert_not_called()
        assert instance.orchestrator is None and instance.auto_gate is None
        result = instance.monitor_openclaw_security(force=True)
        sentinel.check.assert_called_once_with(force=True)
        assert result['passed'] is False and result['success'] is False


def test_operational_constructor_retains_explicit_model_clients(tmp_path):
    with ExitStack() as stack:
        owner, namespace, _ = constructor_fixture(tmp_path, stack)
        instance = owner(tmp_path)
        namespace['AutonomousRefactoringOrchestrator'].assert_called_once_with(tmp_path)
        namespace['AutoGate'].assert_called_once_with(tmp_path, instance.holo_adapter)


def test_main_factory_requests_model_free_preflight_and_restores_logging(tmp_path):
    factory = Mock()
    namespace = dict(Path=Path, Any=Any, logging=logging)
    source_functions(ROOT / 'main.py', {'_create_ai_overseer_for_preflight'}, namespace)
    before = logging.root.level
    with patch.dict('sys.modules', {PACKAGE + '.ai_overseer': SimpleNamespace(AIIntelligenceOverseer=factory)}):
        assert namespace['_create_ai_overseer_for_preflight'](tmp_path) is factory.return_value
    factory.assert_called_once_with(tmp_path, initialize_models=False)
    assert logging.root.level == before


def test_main_factory_failure_restores_logging(tmp_path):
    factory = Mock(side_effect=RuntimeError('fixture failure'))
    namespace = dict(Path=Path, Any=Any, logging=logging)
    source_functions(ROOT / 'main.py', {'_create_ai_overseer_for_preflight'}, namespace)
    before = logging.root.level
    with patch.dict('sys.modules', {PACKAGE + '.ai_overseer': SimpleNamespace(AIIntelligenceOverseer=factory)}):
        try:
            namespace['_create_ai_overseer_for_preflight'](tmp_path)
        except RuntimeError:
            pass
        else:
            raise AssertionError('Constructor failure must not masquerade as success')
    assert logging.root.level == before


def proposal_function():
    namespace = dict(Path=Path, Any=Any, Optional=Optional, Dict=Dict,
                     PreflightFailureEvent=object, logger=logging.getLogger(__name__))
    source_functions(ROOT / 'modules/ai_intelligence/ai_overseer/src/preflight_resolution.py',
                     {'_try_ai_proposal'}, namespace)
    return namespace['_try_ai_proposal']


def test_missing_proposal_capability_never_constructs_model_orchestrator():
    class Unimplemented:
        def __init__(self, *args):
            raise AssertionError('Unavailable capability must not acquire models')
    module = 'holo_index.qwen_advisor.orchestration.autonomous_refactoring'
    with patch.dict('sys.modules', {module: SimpleNamespace(AutonomousRefactoringOrchestrator=Unimplemented)}):
        result = proposal_function()(SimpleNamespace(to_dict=lambda: {}))
    assert result is not None and result['available'] is False


def test_noncallable_proposal_capability_never_constructs_model_orchestrator():
    class Unimplemented:
        propose_preflight_fix = None
        def __init__(self, *args):
            raise AssertionError('Unavailable capability must not acquire models')
    module = 'holo_index.qwen_advisor.orchestration.autonomous_refactoring'
    with patch.dict('sys.modules', {module: SimpleNamespace(AutonomousRefactoringOrchestrator=Unimplemented)}):
        result = proposal_function()(SimpleNamespace(to_dict=lambda: {}))
    assert result is not None and result['available'] is False


def test_implemented_proposal_capability_retains_existing_dispatch():
    class Implemented:
        def __init__(self, root):
            assert root == Path('.')
        def propose_preflight_fix(self, payload):
            return {'available': True, 'component': payload['component']}
    module = 'holo_index.qwen_advisor.orchestration.autonomous_refactoring'
    with patch.dict('sys.modules', {module: SimpleNamespace(AutonomousRefactoringOrchestrator=Implemented)}):
        result = proposal_function()(SimpleNamespace(to_dict=lambda: {'component': 'fixture'}))
    assert result == {'available': True, 'component': 'fixture'}


def test_proposal_failure_does_not_log_exception_payload(caplog):
    class Failing:
        def __init__(self, root):
            raise ValueError('private-diagnostic-fixture')
        def propose_preflight_fix(self, payload):
            raise AssertionError('must not reach proposal')
    module = 'holo_index.qwen_advisor.orchestration.autonomous_refactoring'
    with caplog.at_level(logging.DEBUG), patch.dict('sys.modules', {module: SimpleNamespace(AutonomousRefactoringOrchestrator=Failing)}):
        assert proposal_function()(SimpleNamespace(to_dict=lambda: {})) is None
    assert 'private-diagnostic-fixture' not in caplog.text
    assert 'ValueError' in caplog.text


@pytest.mark.parametrize('relative,skipped', [
    ('modules/infrastructure/shared_utilities/tests/test_local_llm_backends.py', False),
    ('modules/ai_intelligence/ai_overseer/tests/test_preflight_model_boundary.py', False),
    ('modules/ai_intelligence/ai_overseer/tests/test_legacy_heavy.py', True),
    ('modules/ai_intelligence/ai_overseer/tests/nested/test_legacy_heavy.py', True),
])
def test_overseer_collection_guard_is_scoped_to_its_owner(relative, skipped):
    path = ROOT / relative
    item = SimpleNamespace(path=path, fspath=SimpleNamespace(basename=path.name), add_marker=Mock())
    with patch.dict('os.environ', {}, clear=True):
        owner = runpy.run_path(str(ROOT / 'modules/ai_intelligence/ai_overseer/tests/conftest.py'))
        owner['pytest_collection_modifyitems'](None, [item])
    assert item.add_marker.called is skipped


def test_overseer_collection_guard_retains_explicit_heavy_opt_in():
    path = ROOT / 'modules/ai_intelligence/ai_overseer/tests/test_legacy_heavy.py'
    item = SimpleNamespace(path=path, fspath=SimpleNamespace(basename=path.name), add_marker=Mock())
    with patch.dict('os.environ', {'AI_OVERSEER_HEAVY_TESTS': '1'}, clear=True):
        owner = runpy.run_path(str(ROOT / 'modules/ai_intelligence/ai_overseer/tests/conftest.py'))
        owner['pytest_collection_modifyitems'](None, [item])
    item.add_marker.assert_not_called()
