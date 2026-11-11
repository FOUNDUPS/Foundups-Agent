"""Actual entry-script behavior for native textarea and contenteditable inputs.

The textarea fixture deliberately separates dirty value from default text, as
observed in Studio's current native reply form. No real browser or posting.
"""
import ast
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest


EDITOR_DOM = r"""
const vm = require('node:vm');
let input=''; process.stdin.on('data', chunk => input+=chunk);
process.stdin.on('end', () => {
 const f=JSON.parse(input), events=[];
 const el={tagName:f.native?'TEXTAREA':'DIV',isContentEditable:!f.native,
   textContent:f.native?'stale default text':f.initial,
   dispatchEvent:event=>{events.push({type:event.type,bubbles:event.bubbles});return true;}};
 // A dirty textarea's default text does not change its current value.
 if(f.native) el.value=f.initial;
 const context=vm.createContext({el,Event:class Event{
   constructor(type,options){this.type=type;this.bubbles=options&&options.bubbles;}
 }});
 const results=[];
 for(const step of f.steps) {
   context.chunk=step.chunk;
   const result=vm.runInContext('(function(){'+step.script+'\n}).apply(null,[el,chunk])',context,{timeout:1000});
   results.push(result===undefined?null:result);
 }
 process.stdout.write(JSON.stringify({value:el.value===undefined?null:el.value,
   text:el.textContent,results,events}));
});
"""


def _entry_method():
    path = Path(__file__).resolve().parents[1] / 'skillz/tars_like_heart_reply/src/reply_executor.py'
    tree = ast.parse(path.read_text(encoding='utf-8'))
    owner = next(node for node in tree.body if isinstance(node, ast.ClassDef)
                 and node.name == 'BrowserReplyExecutor')
    return next(node for node in owner.body if isinstance(node, ast.AsyncFunctionDef)
                and node.name == '_execute_reply_unverified')


def _literal(call):
    assert isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
    assert call.func.attr == 'execute_script' and call.args
    return ast.literal_eval(call.args[0])


def _script(stage):
    """Select complete existing scripts by their call site, not replacement logic."""
    method = _entry_method()
    if stage in {'read_current', 'read_entered'}:
        target = 'current' if stage == 'read_current' else 'entered_text'
        rows = sorted((node for node in ast.walk(method) if isinstance(node, ast.Assign)
                       and any(isinstance(t, ast.Name) and t.id == target for t in node.targets)
                       and isinstance(node.value, ast.Call)
                       and isinstance(node.value.func, ast.Attribute)
                       and node.value.func.attr == 'execute_script'), key=lambda node: node.lineno)
        assert rows, 'Actual entry read site must exist'
        return _literal(rows[0].value)
    markers = {
        'clear': "arguments[0].textContent = ''",
        'append': 'const chunk = arguments[1]',
        'micro_edit': 'const t =',
    }
    scripts = []
    for node in ast.walk(method):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == 'execute_script' and node.args
                and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str)
                and markers[stage] in node.args[0].value):
            scripts.append(_literal(node))
    assert len(scripts) == 1, 'Entry operation must have one qualified script'
    return scripts[0]


def _run(native, initial, steps):
    binary = os.getenv('NODE_BINARY') or shutil.which('node')
    assert binary, 'The qualified Node fixture runner is required'
    result = subprocess.run([binary, '-e', EDITOR_DOM], input=json.dumps({
        'native': native, 'initial': initial,
        'steps': [{'script': _script(stage), 'chunk': chunk} for stage, chunk in steps],
    }), capture_output=True, text=True, timeout=5, check=True)
    return json.loads(result.stdout)


def _current(result, native):
    return result['value'] if native else result['text']


@pytest.mark.parametrize('native', [True, False], ids=['textarea', 'contenteditable'])
def test_clear_removes_the_current_input(native):
    result = _run(native, 'an old unfinished draft', [('clear', None)])
    assert _current(result, native) == ''


@pytest.mark.parametrize('native', [True, False], ids=['textarea', 'contenteditable'])
def test_append_uses_current_input_and_not_default_text(native):
    result = _run(native, 'Thanks ', [('append', 'for explaining.\nありがとう')])
    assert _current(result, native) == 'Thanks for explaining.\nありがとう'
    assert result['events'] == [{'type': 'input', 'bubbles': True}]


@pytest.mark.parametrize('native', [True, False], ids=['textarea', 'contenteditable'])
@pytest.mark.parametrize('stage', ['read_current', 'read_entered'])
def test_recovery_and_first_verification_read_the_actual_input(native, stage):
    result = _run(native, 'Actual input\nwith a second line.', [(stage, None)])
    assert result['results'] == ['Actual input\nwith a second line.']


@pytest.mark.parametrize('native', [True, False], ids=['textarea', 'contenteditable'])
def test_existing_micro_edit_changes_current_input(native):
    result = _run(native, 'wordx', [('micro_edit', None)])
    assert _current(result, native) == 'word'
    assert result['events'] == [{'type': 'input', 'bubbles': True}]


@pytest.mark.parametrize('native', [True, False], ids=['textarea', 'contenteditable'])
@pytest.mark.parametrize('text', ['', 'abc'], ids=['empty', 'short'])
def test_short_input_is_not_changed_by_micro_edit(native, text):
    result = _run(native, text, [('micro_edit', None)])
    assert _current(result, native) == text
    assert result['events'] == []


@pytest.mark.parametrize('native', [True, False], ids=['textarea', 'contenteditable'])
def test_complete_entry_sequence_preserves_exact_multiline_draft(native):
    draft = 'I understand your concern.\nWhich use of AI do you mean?'
    result = _run(native, 'old input', [
        ('clear', None), ('append', draft[:17]), ('append', draft[17:]),
        ('read_current', None), ('read_entered', None),
    ])
    assert _current(result, native) == draft
    assert result['results'][-2:] == [draft, draft]
    assert result['events'] == [{'type': 'input', 'bubbles': True}] * 2


def _typing_loop_fixture(monkeypatch, *, micro=False, stale=None):
    """Reuse the admitted complete-definition owner; JavaScript is a collaborator."""
    import asyncio
    import importlib.util
    import sys
    from types import ModuleType, SimpleNamespace
    path = Path(__file__).with_name('test_chat_manifest_inspection.py')
    spec = importlib.util.spec_from_file_location('_editor_loop_definitions', path)
    owners = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(owners)
    module = owners.EXECUTOR
    class StaleElementReferenceException(Exception):
        pass
    module.StaleElementReferenceException = StaleElementReferenceException
    gates = ModuleType('offline_editor_gates')
    gates.gate_snapshot = lambda: dict(stop_active=False, yt_automation=True,
                                      comment_engagement=True, comment_reply=True)
    monkeypatch.setitem(sys.modules, 'modules.communication.livechat.src.automation_gates', gates)
    monkeypatch.setitem(sys.modules,
        'modules.communication.video_comments.skillz.tars_like_heart_reply.src.comment_row_context',
        owners.definitions('_editor_loop_row', 'modules/communication/video_comments/skillz/tars_like_heart_reply/src/comment_row_context.py'))
    behavior = ModuleType('offline_editor_behavior')
    behavior.get_0102_behavior_interface = lambda **_: '0102'
    monkeypatch.setitem(sys.modules, 'modules.infrastructure.foundups_selenium.src.human_behavior', behavior)
    state = dict(text='', clicks=0, micro_edits=0, stale_seen=False, after_foreign_appends=0,
                 random_calls=0, micro_selected=False)
    textarea = object()
    def script(code, *args):
        if 'submitBtn.click()' in code:
            state['clicks'] += 1
            return {'success': True}
        if 'replyBtn.click()' in code: return {'success': True}
        if 'return textarea;' in code or 'return ta;' in code: return textarea
        if "arguments[0].textContent = ''" in code: state['text'] = ''; return None
        if 'const chunk = arguments[1]' in code:
            if stale and not state['stale_seen'] and len(state['text']) >= 4:
                state['stale_seen'] = True
                if stale == 'foreign': state['text'] = 'Other'
                raise StaleElementReferenceException('synthetic stale input')
            if state['stale_seen'] and stale == 'foreign': state['after_foreign_appends'] += 1
            state['text'] += args[1]
            return None
        if 'const t =' in code:
            if len(state['text']) > 3:
                state['text'] = state['text'][:-1]
                state['micro_edits'] += 1
            return state['text']
        if ('return arguments[0].textContent' in code or 'return el ?' in code
                or 'return el.value === undefined' in code):
            return state['text']
        return None
    def random_value():
        index = state['random_calls']
        state['random_calls'] += 1
        if index > 0 and index % 2 == 0 and micro and len(state['text']) >= 5 and not state['micro_selected']:
            state['micro_selected'] = True
            return 0.0
        return 1.0
    async def settled(*_args, **_kwargs):
        return None
    monkeypatch.setattr(module.random, 'random', random_value)
    monkeypatch.setattr(module.random, 'uniform', lambda lower, upper: lower)
    monkeypatch.setattr(module.asyncio, 'sleep', settled)
    item = object.__new__(module.BrowserReplyExecutor)
    item.driver = SimpleNamespace(execute_script=script)
    item.selectors = {'comment_thread': 'ytcp-comment-thread'}
    item.human, item.delay_multiplier = None, 1.0
    item._bind_reply_target = lambda *_a, **_k: True
    item._pre_submit_guard = lambda: True
    item._submit_invoked = False
    return item, state, asyncio


def test_actual_typing_loop_retypes_the_micro_edited_character(monkeypatch):
    item, state, asyncio = _typing_loop_fixture(monkeypatch, micro=True)
    draft = 'Useful answer with detail'
    result = asyncio.run(item._execute_reply_unverified(1, draft, expected_comment={'comment_id': 'c1'}))
    assert state['micro_edits'] == 1
    assert state['text'] == draft
    assert result is True and state['clicks'] == 1 and item._submit_invoked is True


@pytest.mark.parametrize('recovery', ['prefix', 'foreign'])
def test_actual_stale_recovery_continues_only_our_exact_prefix(monkeypatch, recovery):
    item, state, asyncio = _typing_loop_fixture(monkeypatch, stale=recovery)
    draft = 'Useful answer with detail'
    result = asyncio.run(item._execute_reply_unverified(1, draft, expected_comment={'comment_id': 'c1'}))
    assert state['stale_seen'] is True
    if recovery == 'prefix':
        assert state['text'] == draft and result is True and state['clicks'] == 1
    else:
        assert state['after_foreign_appends'] == 0
        assert state['text'] == 'Other' and result is False and state['clicks'] == 0
        assert item._submit_invoked is False
