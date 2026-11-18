"""Execute the real supervisor startup method without services or model effects."""
import ast
import logging
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict
from unittest.mock import Mock
import time

import pytest


def test_supervisor_advisory_startup_does_not_acquire_models(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[4]
    path = root / 'modules/communication/moltbot_bridge/src/openclaw_supervisor.py'
    tree = ast.parse(path.read_text(encoding='utf-8'))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'OpenClawSupervisor')
    method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == '_init_unified_components')
    namespace = {'logger': logging.getLogger(__name__)}
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), namespace)
    observed = []

    def overseer(*, repo_root, initialize_models=True):
        observed.append((repo_root, initialize_models))
        assert initialize_models is False, 'advisory startup must not initialize native model engines'
        return 'lightweight-overseer'

    monkeypatch.setitem(__import__('sys').modules, 'modules.ai_intelligence.ai_overseer.src.ai_overseer',
                        SimpleNamespace(AIIntelligenceOverseer=overseer))
    monkeypatch.setitem(__import__('sys').modules, 'modules.infrastructure.wre_core.src.pattern_memory',
                        SimpleNamespace(PatternMemory=Mock(return_value='memory')))
    monkeypatch.setitem(__import__('sys').modules, 'modules.infrastructure.wre_core.src.libido_monitor',
                        SimpleNamespace(GemmaLibidoMonitor=Mock(return_value='monitor')))
    owner = SimpleNamespace(repo_root=tmp_path)
    namespace['_init_unified_components'](owner)
    assert observed == [(tmp_path, False)]
    assert (owner._ai_overseer, owner._pattern_memory, owner._libido_monitor) == (
        'lightweight-overseer', 'memory', 'monitor')


@pytest.mark.parametrize('action', [
    'idle', 'execute_self_audit_fix', 'execute_maintenance_task',
    'claim_signed_worker_tasks_until_idle',
])
def test_lightweight_analysis_preserves_triage_plan(action):
    root = Path(__file__).resolve().parents[4]
    supervisor_path = root / 'modules/communication/moltbot_bridge/src/openclaw_supervisor.py'
    tree = ast.parse(supervisor_path.read_text(encoding='utf-8'))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'OpenClawSupervisor')
    method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == '_plan')
    normalizer = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_normalize_ai_analysis')
    namespace = dict(Dict=Dict, Any=Any, logger=logging.getLogger(__name__))
    exec(compile(ast.Module(body=[normalizer, method], type_ignores=[]), str(supervisor_path), 'exec'), namespace)

    # Execute the existing analysis fallback itself, without importing model owners.
    overseer_path = root / 'modules/ai_intelligence/ai_overseer/src/ai_overseer.py'
    overseer_tree = ast.parse(overseer_path.read_text(encoding='utf-8'))
    overseer_cls = next(n for n in overseer_tree.body if isinstance(n, ast.ClassDef) and n.name == 'AIIntelligenceOverseer')
    analysis = next(n for n in overseer_cls.body if isinstance(n, ast.FunctionDef) and n.name == 'analyze_mission_requirements')
    analysis_namespace = dict(Dict=Dict, Any=Any, time=time, HOLO_AVAILABLE=True,
                              logger=logging.getLogger(__name__),
                              MissionType=SimpleNamespace(CUSTOM=SimpleNamespace(value='custom')))
    exec(compile(ast.Module(body=[analysis], type_ignores=[]), str(overseer_path), 'exec'), analysis_namespace)
    lightweight = SimpleNamespace(orchestrator=None)
    lightweight.analyze_mission_requirements = lambda description: analysis_namespace['analyze_mission_requirements'](lightweight, description)
    triage = dict(action=action, reason='fixture', task={'id': 'task'},
                  event_signature='event', recommended_fix='fix',
                  maintenance_selection={'id': 'maintenance'}, max_claims=2)
    observation = dict(git={'dirty_files': ['preserved.py']}, restart_budget={'allowed': False})
    owner = SimpleNamespace(_attempts_in_window=lambda: 3, _ai_overseer=None)
    baseline = namespace['_plan'](owner, triage, observation)
    owner._ai_overseer = lightweight
    actual = namespace['_plan'](owner, triage, observation)
    assert actual.pop('ai_analysis') == dict(complexity=3, patterns=[], recommended_team={},
                                           method='fallback', requires_coordination=True)
    assert actual == baseline
