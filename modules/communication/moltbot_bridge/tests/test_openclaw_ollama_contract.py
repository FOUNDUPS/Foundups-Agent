"""Frozen timeout/default contract; real helper code with fake daemon and transport.

Load the helper package without executing the production src/__init__ daemon
imports. No live model, provider, network or process startup is acceptance here.
"""
import importlib
import os
from pathlib import Path
import socket
import subprocess
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock

import pytest

ROOT=Path(os.environ.get('PC_OLLAMA_TEST_ROOT',str(Path(__file__).resolve().parents[4])))
MAIN=Path(os.environ.get('PC_OLLAMA_TEST_FALLBACK',str(ROOT)))
REL='modules/communication/moltbot_bridge/src'


@pytest.fixture
def helpers(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('Live network/process operation forbidden')
    monkeypatch.setattr(socket.socket,'connect',forbidden)
    monkeypatch.setattr(socket,'create_connection',forbidden)
    monkeypatch.setattr(subprocess,'Popen',forbidden)
    package=ModuleType('_pc_ollama_contract_owner')
    package.__path__=[str(ROOT/REL),str(MAIN/REL)]
    monkeypatch.setitem(sys.modules,package.__name__,package)
    for name in list(sys.modules):
        if name.startswith(package.__name__+'.'):
            monkeypatch.delitem(sys.modules,name)
    bootstrap=importlib.import_module(package.__name__+'.openclaw_bootstrap_config')
    engine=importlib.import_module(package.__name__+'.openclaw_conversation_engine')
    return bootstrap,engine


def bootstrap_daemon():
    return SimpleNamespace(
        _normalize_genus_label=lambda value,default:value or default,
        _normalize_lower_label=lambda value,default:value or default,
        _resolve_local_target_for_role=lambda role:'local/qwen-coder-7b',
        _no_api_keys=True,
    )


@pytest.mark.parametrize('raw,expected',[
    (None,120.0),('',120.0),('invalid',120.0),('nan',120.0),
    ('inf',120.0),('-inf',120.0),('0',15.0),('-10',15.0),
    ('15',15.0),('125.5',125.5),('300',300.0),('301',300.0),
])
def test_bootstrap_timeout_is_finite_and_bounded(helpers,monkeypatch,raw,expected):
    monkeypatch.delenv('OPENCLAW_OLLAMA_TIMEOUT_SEC',raising=False)
    if raw is not None: monkeypatch.setenv('OPENCLAW_OLLAMA_TIMEOUT_SEC',raw)
    dae=bootstrap_daemon()
    helpers[0].initialize_control_plane_state(dae,backend='openclaw',allow_external_requested=False)
    assert dae._ollama_timeout_sec==expected


@pytest.mark.parametrize('raw,expected',[
    (None,'qwen-overseer:latest'),('custom-model:tag','custom-model:tag'),('', ''),
])
def test_model_default_override_and_explicit_disable(helpers,monkeypatch,raw,expected):
    monkeypatch.delenv('OPENCLAW_OLLAMA_MODEL',raising=False)
    if raw is not None: monkeypatch.setenv('OPENCLAW_OLLAMA_MODEL',raw)
    dae=bootstrap_daemon()
    helpers[0].initialize_control_plane_state(dae,backend='openclaw',allow_external_requested=False)
    assert dae._ollama_model==expected


def conversation_daemon():
    dae=SimpleNamespace(
        _conversation_backend='openclaw', _preferred_external_provider='',
        _preferred_external_model='', overseer=None, _ollama_model='custom-model:tag',
        _ollama_timeout_sec=125.5, _allow_external_llm=False,
        _build_conversation_system_prompt=Mock(return_value='test prompt'),
        _maybe_apply_agentic_conversation_model=Mock(),
        _try_preferred_external_conversation=Mock(return_value=None),
        _mark_conversation_engine=Mock(), _record_token_usage=Mock(),
        _trim_self_dialogue=lambda value:value,
        _ensure_conversation_identity=lambda value:'0102: '+value,
        _safe_int=lambda value:value if type(value) is int else None,
        _turn_cancelled_response=Mock(return_value='cancelled'),
    )
    for name in ('_is_turn_cancelled','_is_connect_wre_request','_is_model_switch_request',
                 '_is_token_usage_query','_is_identity_query'):
        setattr(dae,name,Mock(return_value=False))
    return dae


@pytest.mark.parametrize('cancel_at',[None,'pre_ollama','post_ollama'])
def test_transport_budget_model_and_cancellation(helpers,monkeypatch,cancel_at):
    monkeypatch.setenv('OPENCLAW_ALLOW_IRONCLAW_FALLBACK','0')
    response=SimpleNamespace(ok=True,json=lambda:{'message':{'content':'runtime ready'},
                                                'prompt_eval_count':4,'eval_count':2})
    request=Mock(return_value=response)
    monkeypatch.setitem(sys.modules,'requests',SimpleNamespace(post=request))
    dae=conversation_daemon()
    dae._is_turn_cancelled.side_effect=lambda phase:phase==cancel_at
    intent=SimpleNamespace(raw_message='hello',is_authorized_commander=True)
    result=helpers[1].execute_conversation(dae,intent)
    if cancel_at:
        assert result=='cancelled'
        dae._record_token_usage.assert_not_called()
    else:
        assert result=='0102: runtime ready'
        dae._record_token_usage.assert_called_once()
    if cancel_at=='pre_ollama': request.assert_not_called()
    else:
        request.assert_called_once()
        assert request.call_args.args==('http://localhost:11434/api/chat',)
        assert request.call_args.kwargs['timeout']==125.5
        assert request.call_args.kwargs['json']['model']=='custom-model:tag'
        assert request.call_args.kwargs['json']['stream'] is False


def test_transport_failure_stays_local_when_external_disabled(helpers,monkeypatch):
    monkeypatch.setenv('OPENCLAW_ALLOW_IRONCLAW_FALLBACK','0')
    request=Mock(side_effect=TimeoutError('synthetic timeout'))
    monkeypatch.setitem(sys.modules,'requests',SimpleNamespace(post=request))
    dae=conversation_daemon()
    result=helpers[1].execute_conversation(dae,SimpleNamespace(raw_message='hello',is_authorized_commander=True))
    request.assert_called_once()
    assert result=="0102: I'm here. Local conversation models are unavailable right now."
    dae._record_token_usage.assert_not_called()
