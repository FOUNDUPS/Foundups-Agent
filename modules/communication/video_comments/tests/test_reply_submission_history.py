"""Offline durable SQLite and exact-source browser-script contracts.

No Selenium package startup, credentials, model, browser or network is used.
JavaScript runs in Node against an explicit synthetic DOM; it is not live proof.
"""
import ast
import asyncio
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import json
import logging
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[4]
EXECUTOR_PATH = ROOT / 'modules/communication/video_comments/skillz/tars_like_heart_reply/src/reply_executor.py'
ROW_MODULE = 'modules.communication.video_comments.skillz.tars_like_heart_reply.src.comment_row_context'


def source_module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


HISTORY = source_module('_submission_history', 'modules/communication/video_comments/src/commenter_history_store.py')
ROW = source_module('_submission_row', 'modules/communication/video_comments/skillz/tars_like_heart_reply/src/comment_row_context.py')
tree = ast.parse(EXECUTOR_PATH.read_text(encoding='utf-8'))
definitions = ast.Module(body=[node for node in tree.body if isinstance(node, ast.ClassDef)], type_ignores=[])
namespace = dict(asyncio=asyncio, os=os, random=random, uuid4=uuid4, Any=object, Dict=dict, List=list,
                 logger=logging.getLogger(__name__), HUMAN_BEHAVIOR_AVAILABLE=False)
exec(compile(definitions, str(EXECUTOR_PATH), 'exec'), namespace)
Executor = namespace['BrowserReplyExecutor']
CONTEXT = dict(_target_channel_id='RECEIVING', video_id='VIDEO', comment_id='UgxOriginal',
               text='Where is the film?', author_name='Aki', author_handle='@Aki', channel_id='AUTHOR')


NODE_DOM = r"""
const vm = require('node:vm');
let input = ''; process.stdin.on('data', x => input += x); process.stdin.on('end', () => {
 const f = JSON.parse(input), v = Object.assign({id:'UgxOriginal', video:'VIDEO', text:'Where is the film?',
   author:'@Aki', authorChannel:'AUTHOR', target:'RECEIVING', replies:[]}, f.row || {});
 function author(name, channel, host='www.youtube.com') { const link={href:'https://'+host+'/channel/'+channel,
   matches:()=>true, querySelector:()=>null};
   return {textContent:name, matches:()=>false, querySelector:()=>link}; }
 function reply(r) { const e={getAttribute:k=>k==='data-comment-id'?r.id:null,
   querySelector:s=>s.includes('ytcp-comment-author')?author('Creator',r.channel,r.host):
     s.includes('creator-badge')?(r.owner?{}:null):null,
   querySelectorAll:()=>[]};
   const text={textContent:r.text, closest:()=>e}; return {e,text}; }
 const replyRows=v.replies.map(reply);
 const replies={querySelectorAll:()=>replyRows.map(x=>x.text), contains:e=>replyRows.some(x=>x.e===e)};
 const info={querySelectorAll:()=>[{href:'https://studio.youtube.com/video/'+v.video+'/comments'}]};
 const control={textContent:'View 2 replies', getAttribute:k=>k==='aria-expanded'?'false':null,
   getClientRects:()=>[{}], offsetParent:true};
 let clicks=0;
 const button={disabled:false, scrollIntoView:()=>{}, click:()=>clicks++};
 const row={isConnected:v.connected!==false, getAttribute:k=>k==='data-comment-id'?v.id:null,
   setAttribute:()=>{}, querySelector:s=>s.includes('ytcp-comment-view')?null:
     s.includes('ytcp-video-thumbnail-with-info')?info:
     s.includes('contenteditable')?{textContent:v.entered===undefined?'Draft':v.entered}:
     s.includes('submit-button')?button:
     s.includes('content-text')?{textContent:v.text}:
     s.includes('author')?author(v.author,v.authorChannel):
     s.includes('replies')?(v.replies.length?replies:null):null,
   querySelectorAll:s=>s==='a[href]'?[]:v.collapsed?[control]:[]};
 const document={querySelector:()=>v.disappeared?null:row, querySelectorAll:()=>[row]};
 const program='(function(){'+f.script+'\n}).apply(null,'+JSON.stringify(f.args)+')';
 const result=vm.runInNewContext(program,{document,location:{origin:v.origin || 'https://studio.youtube.com',pathname:'/channel/'+v.target+'/comments',
   href:'https://studio.youtube.com/channel/'+v.target+'/comments'},URL},{timeout:1000});
 if (result && typeof result==='object') result.click_count=clicks;
 process.stdout.write(JSON.stringify(result));
});
"""


class SubmissionHistoryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'history.db'
        self.store = HISTORY.CommenterHistoryStore(self.path)

    def executor(self):
        executor = object.__new__(Executor)
        executor.history_store = self.store
        executor.driver = SimpleNamespace(execute_script=lambda *args: None)
        executor._bind_reply_target = lambda *a, **kw: True
        executor._reply_snapshot = lambda *a: dict(complete=True, ids=[], matching_ids=[])
        return executor

    def test_unknown_claim_survives_reopen_and_new_draft(self):
        attempt = self.store.begin_reply_attempt(CONTEXT, 'First draft')
        reopened = HISTORY.CommenterHistoryStore(self.path)
        self.assertIsNone(reopened.begin_reply_attempt(CONTEXT, 'Completely different draft'))
        self.assertEqual(reopened.get_reply_attempts(CONTEXT)[0]['attempt_id'], attempt)
        self.assertEqual(reopened.get_reply_attempts(CONTEXT)[0]['status'], 'unknown')

    def test_only_one_concurrent_claim_wins(self):
        stores = [HISTORY.CommenterHistoryStore(self.path) for _ in range(8)]
        with ThreadPoolExecutor(max_workers=8) as pool:
            claims = list(pool.map(lambda store: store.begin_reply_attempt(CONTEXT, 'Draft'), stores))
        self.assertEqual(sum(claim is not None for claim in claims), 1)
        self.assertEqual(len(self.store.get_reply_attempts(CONTEXT)), 1)

    def test_identity_is_required_and_independent_of_row_or_edited_text(self):
        for field in ('comment_id', 'video_id', '_target_channel_id', 'text'):
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.store.begin_reply_attempt({**CONTEXT, field:None}, 'Draft')
        self.store.begin_reply_attempt(CONTEXT, 'Draft')
        self.assertIsNone(self.store.begin_reply_attempt({**CONTEXT, 'text':'Edited comment', 'row':99}, 'New'))

    def test_verified_receipt_is_not_retried(self):
        attempt = self.store.begin_reply_attempt(CONTEXT, 'Draft')
        self.store.finish_reply_attempt(attempt, 'verified', {'creator_reply_ids':['reply-1']})
        self.assertIsNone(HISTORY.CommenterHistoryStore(self.path).begin_reply_attempt(CONTEXT, 'New'))

    def test_inspection_evidence_preserves_verified_and_unknown_reservations(self):
        for status in ('unknown', 'verified'):
            context = {**CONTEXT, 'comment_id':CONTEXT['comment_id'] + '-' + status}
            attempt = self.store.begin_reply_attempt(context, 'Draft')
            if status == 'verified':
                self.store.finish_reply_attempt(attempt, status, {'creator_reply_ids':['new']})
            self.store.append_reply_evidence(attempt, {'screenshot_path':'private.png', 'sha256':'digest', 'vision':False})
            record, = self.store.get_reply_attempts(context)
            self.assertEqual(record['status'], status)
            self.assertEqual(record['evidence']['post_inspection']['screenshot_path'], 'private.png')
            self.assertIsNone(HISTORY.CommenterHistoryStore(self.path).begin_reply_attempt(context, 'Other draft'))
            if status == 'verified':
                self.assertEqual(record['evidence']['creator_reply_ids'], ['new'])
        with self.assertRaises(ValueError):
            self.store.append_reply_evidence(attempt, {'too_large':'x'*16385})

    def test_proven_no_submit_can_retry_without_removing_history(self):
        attempt = self.store.begin_reply_attempt(CONTEXT, 'Draft')
        self.store.finish_reply_attempt(attempt, 'not_submitted', {'submit_invoked':False})
        self.assertIsNotNone(self.store.begin_reply_attempt(CONTEXT, 'Revised draft'))
        self.assertEqual([x['status'] for x in self.store.get_reply_attempts(CONTEXT)], ['not_submitted','unknown'])

    def test_shared_history_override(self):
        shared = Path(self.directory.name) / 'shared' / 'history.db'
        with patch.dict(os.environ, {'YT_COMMENT_HISTORY_DB':str(shared)}):
            self.assertEqual(HISTORY.CommenterHistoryStore().db_path, shared.resolve())

    def test_verified_new_creator_reply_completes_durable_attempt(self):
        executor = self.executor()
        snapshots = iter([dict(complete=True, ids=['old'], matching_ids=[]),
                          dict(complete=True, ids=['old','new'], matching_ids=['new'])])
        executor._reply_snapshot = lambda *a: next(snapshots)
        async def submit(*args, **kwargs):
            executor._submit_invoked = True
            return True
        executor._execute_reply_unverified = submit
        self.assertTrue(asyncio.run(executor.execute_reply(1, 'Draft', expected_comment=CONTEXT)))
        receipt, = self.store.get_reply_attempts(CONTEXT)
        self.assertEqual(receipt['status'], 'verified')
        self.assertEqual(receipt['evidence']['creator_reply_ids'], ['new'])
        interaction, = self.store.get_recent_interactions(commenter_key='AUTHOR')
        self.assertTrue(interaction.replied)
        self.assertEqual(interaction.comment_text, CONTEXT['text'])
        self.assertEqual(interaction.reply_text, 'Draft')

    def test_unknown_delivery_blocks_after_executor_restart(self):
        executor = self.executor()
        async def submit(*args, **kwargs):
            executor._submit_invoked = True
            raise ConnectionError('browser disappeared after click')
        executor._execute_reply_unverified = submit
        self.assertFalse(asyncio.run(executor.execute_reply(1, 'Draft', expected_comment=CONTEXT)))
        restarted = self.executor()
        restarted._execute_reply_unverified = lambda *a, **k: self.fail('must not retry unknown')
        self.assertFalse(asyncio.run(restarted.execute_reply(1, 'New draft', expected_comment=CONTEXT)))
        self.assertEqual(restarted.last_submission_status, 'unknown')

    def test_incomplete_baseline_blocks_before_attempt(self):
        executor = self.executor()
        executor._reply_snapshot = lambda *a: {'complete':False}
        self.assertFalse(asyncio.run(executor.execute_reply(1, 'Draft', expected_comment=CONTEXT)))
        self.assertEqual(self.store.get_reply_attempts(CONTEXT), [])

    def test_old_reply_revealed_after_submit_does_not_prove_delivery(self):
        executor = self.executor()
        snapshots = iter([dict(complete=True, ids=['old'], matching_ids=[])] +
                         [dict(complete=True, ids=['old'], matching_ids=['old'])] * 10)
        executor._reply_snapshot = lambda *a: next(snapshots)
        async def submit(*a, **k):
            executor._submit_invoked = True
            return True
        executor._execute_reply_unverified = submit
        async def no_wait(*a): pass
        with patch.object(asyncio, 'sleep', no_wait):
            self.assertFalse(asyncio.run(executor.execute_reply(1, 'Draft', expected_comment=CONTEXT)))
        self.assertEqual(self.store.get_reply_attempts(CONTEXT)[0]['status'], 'unknown')

    def capture_script(self, method, *args):
        captured = []
        executor = object.__new__(Executor)
        executor.driver = SimpleNamespace(execute_script=lambda script,*a:captured.append((script,a)))
        executor.selectors = {'comment_thread':'ytcp-comment-thread'}
        with patch.dict(sys.modules, {ROW_MODULE:ROW}):
            getattr(executor, method)(*args)
        return captured[0]

    def dom(self, script, args, row):
        node = os.environ.get('NODE_BINARY') or shutil.which('node')
        self.assertTrue(node, 'Node required for exact-script offline DOM contract')
        result = subprocess.run([node, '-e', NODE_DOM], input=json.dumps(dict(script=script,args=args,row=row)),
            capture_output=True, text=True, check=True, timeout=5,
            env={key:os.environ[key] for key in ('SystemRoot','WINDIR') if key in os.environ})
        return json.loads(result.stdout)

    def test_actual_bind_script_accepts_exact_target_and_rejects_identity_changes(self):
        script,args = self.capture_script('_bind_reply_target', 1, CONTEXT, 'marker')
        self.assertTrue(self.dom(script,args,{}))
        for change in ({'id':'another'}, {'video':'another'}, {'target':'another'}, {'author':'Other'},
                       {'authorChannel':'OTHER'}, {'text':'Where  is the film?'}, {'connected':False},
                       {'origin':'https://other.invalid'}):
            with self.subTest(change=change):
                self.assertFalse(self.dom(script,args,change))

    def test_actual_readback_requires_owner_channel_exact_text_and_real_reply_id(self):
        script,args = self.capture_script('_reply_snapshot', 'marked', CONTEXT, 'Draft')
        good = dict(id='UgxReply',channel='RECEIVING',owner=True,text='Draft')
        self.assertEqual(self.dom(script,args,{'replies':[good]})['matching_ids'], ['UgxReply'])
        for bad in ({**good,'channel':'OTHER'}, {**good,'owner':False}, {**good,'text':'Draft extra'},
                    {**good,'host':'other.invalid'}):
            self.assertEqual(self.dom(script,args,{'replies':[bad]})['matching_ids'], [])
        self.assertFalse(self.dom(script,args,{'replies':[{**good,'id':None}]})['complete'])
        self.assertFalse(self.dom(script,args,{'collapsed':True})['complete'])
        self.assertIsNone(self.dom(script,args,{'disappeared':True}))

    def test_factory_carries_real_vision_bridge(self):
        names = ('driver','human','stats','reply_executor','SELECTORS','VISION_DESCRIPTIONS','use_vision',
                 'check_moderators','mod_lookup','reply_debug_tags','video_title','channel_id','session_id','ui_tars_bridge')
        dae = SimpleNamespace(**{key:object() for key in names})
        self.assertIs(ROW.create_comment_processor(dae, lambda **kwargs:kwargs)['ui_tars_bridge'], dae.ui_tars_bridge)

    def test_final_submit_script_rechecks_target_and_text_then_clicks_once(self):
        method = next(node for node in ast.walk(tree) if isinstance(node, ast.AsyncFunctionDef)
                      and node.name == '_execute_reply_unverified')
        argument = next(node.args[0] for node in ast.walk(method) if isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Attribute) and node.func.attr == 'execute_script'
                        and node.args and isinstance(node.args[0], ast.BinOp))
        script = ROW.COMMENT_IDENTITY_SCRIPT + ast.literal_eval(argument.right)
        args = ['marked', 0, CONTEXT, 'Draft']
        good = self.dom(script, args, {})
        self.assertTrue(good['success'])
        self.assertEqual(good['click_count'], 1)
        for changed in ({'id':'other'}, {'video':'other'}, {'text':'other'}, {'entered':'Draft extra'}):
            result = self.dom(script, args, changed)
            self.assertFalse(result['success'])
            self.assertEqual(result['click_count'], 0)

    def test_changed_theme_guard_is_checked_after_typing_before_submit(self):
        executor = self.executor()
        executor.human, executor.delay_multiplier = None, 0
        executor.selectors = {'comment_thread':'ytcp-comment-thread'}
        executor._submit_invoked = False
        editor = SimpleNamespace(textContent='')
        submitted, guarded = [], []
        def script(source, *args):
            if 'Reply button not found (Deep Shadow Search)' in source:
                return {'success':True}
            if 'return textarea;' in source:
                return editor
            if "arguments[0].textContent = '';" in source:
                editor.textContent = ''
            elif 'const chunk = arguments[1]' in source:
                editor.textContent += args[1]
            elif source == 'return arguments[0].textContent' or source.startswith('const row=document.querySelector'):
                return editor.textContent
            elif 'Submit button not found/disabled' in source:
                submitted.append(True)
                return {'success':True}
            return None
        executor.driver = SimpleNamespace(execute_script=script)
        def guard():
            guarded.append(editor.textContent)
            return False  # Theme changed during typing.
        executor._pre_submit_guard = guard
        async def no_wait(*args): pass
        behavior = SimpleNamespace(get_0102_behavior_interface=lambda **kwargs:'0102')
        with patch.object(asyncio, 'sleep', no_wait), patch.dict(sys.modules, {
            'modules.infrastructure.foundups_selenium.src.human_behavior':behavior, ROW_MODULE:ROW}):
            self.assertFalse(asyncio.run(executor._execute_reply_unverified(1, 'Draft',
                thread_selector='marked', expected_comment=CONTEXT)))
        self.assertEqual(guarded, ['Draft'])
        self.assertEqual(submitted, [])
        self.assertFalse(executor._submit_invoked)


if __name__ == '__main__':
    unittest.main()
