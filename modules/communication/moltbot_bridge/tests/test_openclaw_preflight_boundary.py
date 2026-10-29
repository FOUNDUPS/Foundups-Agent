"""Frozen denial boundary on the real process helper with synthetic collaborators."""
import asyncio
from enum import Enum
import importlib
import os
from pathlib import Path
import socket
import subprocess
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest


class Category(Enum):
    COMMAND='command'
    SYSTEM='system'
    SCHEDULE='schedule'
    SOCIAL='social'
    AUTOMATION='automation'
    FOUNDUP='foundup'
    RESEARCH='research'
    QUERY='query'
    MONITOR='monitor'
    CONVERSATION='conversation'


@pytest.fixture
def process(monkeypatch):
    # Windows initializes its loopback self-pipe during loop construction.
    # Complete that test-runner setup before denying application connections.
    loop=asyncio.new_event_loop()
    def forbidden(*args,**kwargs):
        raise AssertionError('Live network/process operation forbidden')
    monkeypatch.setattr(socket.socket,'connect',forbidden)
    monkeypatch.setattr(socket,'create_connection',forbidden)
    monkeypatch.setattr(subprocess,'Popen',forbidden)
    root=Path(os.environ.get('PC_PREFLIGHT_TEST_ROOT',str(Path(__file__).resolve().parents[4])))
    fallback=Path(os.environ.get('PC_PREFLIGHT_TEST_FALLBACK',str(root)))
    relative='modules/communication/moltbot_bridge/src'
    package=ModuleType('_pc_preflight_contract_owner')
    package.__path__=[str(root/relative),str(fallback/relative)]
    monkeypatch.setitem(sys.modules,package.__name__,package)
    for name in list(sys.modules):
        if name.startswith(package.__name__+'.'):monkeypatch.delitem(sys.modules,name)
    helper=importlib.import_module(package.__name__+'.openclaw_process_loop').process_message
    planner=importlib.import_module(package.__name__+'.openclaw_intent_planner').wsp_preflight
    def run(*args,**kwargs):
        return loop.run_until_complete(helper(*args,**kwargs))
    run.preflight=planner
    try:
        yield run
    finally:
        loop.close()


def fake_daemon(category,allowed):
    intent=SimpleNamespace(category=category,confidence=0.95,sender='synthetic',
                           is_authorized_commander=True,target_domain='original',extracted_task='bounded task')
    tier=SimpleNamespace(value='advisory')
    plan=SimpleNamespace(route='original',permission_level=tier,steps=[],
                         wsp_preflight_passed=True,estimated_tokens=0,intent=intent)
    validated=SimpleNamespace(response_text='ok',success=True,pattern_fidelity=1,
                               learning_stored=False,wsp_violations=[])
    dae=SimpleNamespace(
        IntentCategory=Category,AutonomyTier=SimpleNamespace(ADVISORY=tier),
        HoneypotDefense=SimpleNamespace(is_secret_seeking=Mock(return_value=False)),
        clear_turn_cancel=Mock(),_check_containment=Mock(return_value=None),
        _is_turn_cancelled=Mock(return_value=False),classify_intent=Mock(return_value=intent),
        _apply_runtime_profile_policy=Mock(),_central_adapter=None,
        _report_daemon_action=Mock(),_ensure_skill_safety=Mock(return_value=(True,'current')),
        _wsp_preflight=Mock(return_value=allowed),_resolve_autonomy_tier=Mock(return_value=tier),
        _check_permission_gate=Mock(return_value=True),_plan_execution=Mock(return_value=plan),
        _execute_plan=AsyncMock(return_value='ok'),_validate_and_remember=Mock(return_value=validated),
    )
    return dae,intent


@pytest.mark.parametrize('category',list(Category))
@pytest.mark.parametrize('allowed',[False,True])
def test_failed_preflight_stops_before_permission_plan_execution_and_memory(process,category,allowed):
    dae,intent=fake_daemon(category,allowed)
    response=process(dae,'bounded task','synthetic','local_repl')
    event=[c.kwargs for c in dae._report_daemon_action.call_args_list if c.args==('wsp_preflight',)]
    assert len(event)==1
    if allowed:
        assert response=='ok'
        assert event[0]['result']=='passed'
        dae._execute_plan.assert_awaited_once()
        dae._validate_and_remember.assert_called_once()
    else:
        assert response.startswith('[SECURITY BLOCK]')
        assert event[0]['result']=='blocked'
        assert intent.category is category and intent.target_domain=='original'
        for name in ('_resolve_autonomy_tier','_check_permission_gate','_plan_execution','_validate_and_remember'):
            getattr(dae,name).assert_not_called()
        dae._execute_plan.assert_not_awaited()


def test_newer_skill_verdict_contract_remains_enforced(process):
    dae,_=fake_daemon(Category.COMMAND,True)
    dae._ensure_skill_safety.return_value=(1,'invalid boolean')
    with pytest.raises(ValueError,match='invalid skill safety result'):
        process(dae,'bounded task','synthetic','local_repl')
    dae._ensure_skill_safety.assert_called_once_with(details=True)
    dae._wsp_preflight.assert_not_called()
    dae._execute_plan.assert_not_awaited()


@pytest.mark.parametrize('category,commander,blocked',[
    (Category.COMMAND,False,True),(Category.SYSTEM,False,True),
    (Category.SCHEDULE,True,True),(Category.CONVERSATION,False,False),
    (Category.COMMAND,True,False),
])
def test_actual_planner_authority_and_missing_runtime_reach_the_boundary(process,category,commander,blocked):
    dae,intent=fake_daemon(category,True)
    intent.is_authorized_commander=commander
    intent.raw_message='bounded task'
    dae.wre=None
    dae._wsp_preflight=Mock(side_effect=lambda incoming:process.preflight(dae,incoming))
    response=process(dae,'bounded task','synthetic','local_repl')
    if blocked:
        assert response.startswith('[SECURITY BLOCK]')
        dae._execute_plan.assert_not_awaited()
        dae._validate_and_remember.assert_not_called()
    else:
        assert response=='ok'
        dae._execute_plan.assert_awaited_once()
