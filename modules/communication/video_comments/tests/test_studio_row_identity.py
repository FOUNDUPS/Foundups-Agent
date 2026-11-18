"""Exact-source Studio identity scripts against one bounded, effect-free DOM.

This is synthetic selector/ownership qualification, not a browser or delivery
claim. Existing history/unknown-outcome and legacy fixture tests remain owners.
"""
import ast
import asyncio
import json
import logging
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
from types import ModuleType, SimpleNamespace
from uuid import uuid4

import pytest


STUDIO_DOM = r"""
const vm = require('node:vm');
let input=''; process.stdin.on('data', chunk => input+=chunk);
process.stdin.on('end', () => {
 const f=JSON.parse(input), target='UCRRRRRRRRRRRRRRRRRRRRRR', video='AbCdEfGhI_1';
 const location={origin:'https://studio.youtube.com',pathname:'/channel/'+target+'/comments',
   href:'https://studio.youtube.com/channel/'+target+'/comments'};
 let clicks=0;
 function split(text, separator) {
   let out=[], start=0, depth=0, quote='';
   for(let i=0;i<text.length;i++) {
     const c=text[i];
     if(quote) { if(c===quote && text[i-1]!=='\\') quote=''; continue; }
     if(c==='"'||c==="'") { quote=c; continue; }
     if(c==='['||c==='(') depth++;
     if(c===']'||c===')') depth--;
     if(!depth && separator(c)) { if(text.slice(start,i).trim()) out.push(text.slice(start,i).trim()); start=i+1; }
   }
   if(text.slice(start).trim()) out.push(text.slice(start).trim());
   return out;
 }
 function atom(el, selector) {
   let rest=selector;
   const tag=rest.match(/^(\*|[A-Za-z][\w-]*)/);
   if(tag) { if(tag[1]!=='*'&&el.tagName.toLowerCase()!==tag[1].toLowerCase()) return false; rest=rest.slice(tag[0].length); }
   while(rest) {
     let m;
     if((m=rest.match(/^#([\w-]+)/))) { if(el.getAttribute('id')!==m[1]) return false; }
     else if((m=rest.match(/^\.([\w-]+)/))) { if(!(el.getAttribute('class')||'').split(/\s+/).includes(m[1])) return false; }
     else if((m=rest.match(/^\[([\w-]+)(?:(\*=|\^=|\$=|=)["']?([^"'\]]*)["']?)?\]/))) {
       const value=el.getAttribute(m[1]);
       if(value===null) return false;
       if(m[2] && !(m[2]==='='?value===m[3]:m[2]==='*='?value.includes(m[3]):m[2]==='^='?value.startsWith(m[3]):value.endsWith(m[3]))) return false;
     } else if((m=rest.match(/^:not\(([^()]*)\)/))) { if(atom(el,m[1])) return false; }
     else if((m=rest.match(/^:disabled/))) { if(!el.disabled) return false; }
     else throw Error('unsupported fixed-fixture selector');
     rest=rest.slice(m[0].length);
   }
   return true;
 }
 function selectorMatches(el, selector) {
   const parts=split(selector,c=>/\s/.test(c)), last=parts.pop();
   if(!last||!atom(el,last)) return false;
   let current=el;
   while(parts.length) {
     let wanted=parts.pop(), direct=false;
     if(wanted==='>') { direct=true; wanted=parts.pop(); }
     current=current.parentElement;
     if(direct) { if(!current||!atom(current,wanted)) return false; }
     else { while(current&&!atom(current,wanted)) current=current.parentElement; if(!current) return false; }
   }
   return true;
 }
 class Element {
   constructor(tag,attrs={},text='') { this.tagName=tag.toUpperCase(); this.attrs={...attrs}; this.ownText=text; this.children=[]; this.parentElement=null; this.hidden=false; }
   append(...items) { for(const item of items) { item.parentElement=this; this.children.push(item); } return this; }
   remove() { if(this.parentElement) this.parentElement.children=this.parentElement.children.filter(x=>x!==this); this.parentElement=null; }
   getAttribute(name) { return Object.prototype.hasOwnProperty.call(this.attrs,name)?String(this.attrs[name]):null; }
   hasAttribute(name) { return this.getAttribute(name)!==null; }
   setAttribute(name,value) { this.attrs[name]=String(value); }
   removeAttribute(name) { delete this.attrs[name]; }
   get textContent() { return this.ownText+this.children.map(x=>x.textContent).join(''); }
   set textContent(value) { this.ownText=String(value); this.children=[]; }
   get innerText() { return this.textContent; }
   get id() { return this.getAttribute('id')||''; }
   get href() { const raw=this.getAttribute('href'); return raw===null?'':new URL(raw,location.href).href; }
   get src() { const raw=this.getAttribute('src'); return raw===null?'':new URL(raw,location.href).href; }
   get disabled() { return this.disabledOverride===undefined?this.hasAttribute('disabled'):this.disabledOverride; }
   get isConnected() { let n=this; while(n.parentElement) n=n.parentElement; return n===document; }
   get offsetParent() { return this.hidden?null:this.parentElement; }
   getClientRects() { return this.hidden?[]:[{}]; }
   contains(other) { for(let n=other;n;n=n.parentElement) if(n===this) return true; return false; }
   matches(selector) { return split(selector,c=>c===',').some(s=>selectorMatches(this,s)); }
   closest(selector) { for(let n=this;n;n=n.parentElement) if(n.matches(selector)) return n; return null; }
   querySelectorAll(selector) { const result=[]; const visit=n=>{ for(const child of n.children) { if(child.matches(selector)) result.push(child); visit(child); } }; visit(this); return result; }
   querySelector(selector) { return this.querySelectorAll(selector)[0]||null; }
   scrollIntoView() {}
   click() { clicks++; }
 }
 const node=(tag,attrs={},text='')=>new Element(tag,attrs,text);
 const document=node('document'), body=node('body'); document.append(body);
 const row=node('ytcp-comment-thread'), foreign=node('ytcp-comment-thread'); body.append(row,foreign);
 const original=node('ytcp-comment',{id:'comment',...(f.nestedCommentIdOnly?{}:{'comment-id':'UgxOriginal001'})}); row.append(original);
 const container=node('div',{id:'content'}); original.append(container);
 if(f.rowConflict) row.setAttribute('data-comment-id','UgxDifferent');
 const header=node('div',{id:'header'}); container.append(header);
 const author=node('a',{id:f.legacyAuthor?'author-text':'name',href:f.authorURL||(f.channelAuthor?'https://www.youtube.com/channel/UCAAAAAAAAAAAAAAAAAAAAAA':'http://www.youtube.com/@Aki')},'@Aki');
 if(!f.nestedAuthorOnly) header.append(author);
 const content=node('yt-formatted-string',{id:'content-text'},'Where can I watch the film?');
 if(!f.nestedTextOnly) container.append(content);
 const actions=node('ytcp-comment-action-buttons',{id:'action-buttons'}); container.append(node('div',{id:'comment-actions'}).append(actions));
 const editor=node('div',{contenteditable:'true'},'Thanks for asking.'); original.append(node('ytcp-comment-creator').append(editor,node('ytcp-button',{id:'submit-button'}).append(node('button',{},'Reply'))));
 const replies=f.classReplies ? node('div',{'class':'replies-renderer'}) : node('ytcp-comment-replies',{id:'replies'});
 function reply(data) {
   if(data.modern) {
     const attrs={'class':'expanded-replies','is-reply':''};
     if(data.id) attrs[data.rawIDMissing?'data-comment-id':'comment-id']=data.id;
     const r=node('ytcp-comment',attrs), meta=node('div',{id:'metadata'});
     const name=node('a',{id:'name',...(data.nameVisible?{}:{hidden:''}),href:data.nameURL||'http://www.youtube.com/@Creator'},data.nameText===undefined?'@Creator':data.nameText);
     const badge=node('ytcp-author-comment-badge',data.owner===false?{}:{'is-creator':''});
     badge.append(node('a',{id:'badge-name',href:data.badgeURL||'http://www.youtube.com/@Creator'}).append(node('yt-formatted-string',{},data.badgeText||'@Creator')));
     if(!data.nameMissing) meta.append(name);
     if(!data.badgeMissing) meta.append(badge);
     if(data.badgeDuplicate) meta.append(node('ytcp-author-comment-badge',{'is-creator':''}).append(node('a',{id:'badge-name',href:'http://www.youtube.com/@Creator'},'@Creator')));
     if(data.innerMetadata) r.append(node('ytcp-comment',{'comment-id':'UgxForeign001'}).append(meta));
     else r.append(meta);
     r.append(node('span',{id:'expander-container'}).append(node('yt-formatted-string',{id:'content-text','split-lines':''},data.text||'Thanks for asking.')));
     if(data.hidden) r.hidden=true;
     return r;
   }
   const r=node('ytcp-comment',data.id?{'data-comment-id':data.id}:{});
   r.append(node('ytcp-comment-author').append(node('a',{href:(data.host||'https://www.youtube.com')+'/channel/'+(data.channel||target)},'Creator')));
   r.append(node('yt-formatted-string',{id:'content-text'},data.text||'Thanks for asking.'));
   if(data.owner!==false) r.append(node('span',{'class':'creator-badge'}));
   return r;
 }
 if(f.nestedAuthorOnly||f.nestedTextOnly||f.nestedCommentIdOnly||f.extraNestedMetadata) {
   const nested=reply({id:'UgxNested',channel:'UCFFFFFFFFFFFFFFFFFFFFFF',text:'Nested text'});
   if(f.nestedAuthorOnly) nested.append(author);
   replies.append(nested);
 }
 for(const data of f.replies||[]) replies.append(reply(data));
 if(replies.children.length||f.nestedMetadata) (f.foreignReplies?foreign:f.innerReplies?container:row).append(replies);
 if(f.secondReplies) row.append(node('div',{'class':'replies-renderer'}).append(reply({id:'UgxOriginal001.OldCreator'})));
 if(f.replyLoading) replies.setAttribute('aria-busy','true');
 function metadata(parent, kind, url) {
   const info=node(kind==='legacy'?'ytcp-video-thumbnail-with-info':'ytcp-comment-video-thumbnail',{id:'video-thumbnail'});
   info.append(node('div',{id:'video-title'},'Observed film title'));
   if(kind==='legacy') info.append(node('a',{href:url}));
   else info.append(node('a',{id:'body'}).append(node('ytcp-img-with-fallback',{id:'video-thumbnail'}).append(node('img',{id:'img-with-fallback',src:url}))));
   parent.append(info); return info;
 }
 const metadataParent=f.foreignMetadata?foreign:f.nestedMetadata?replies:null;
 if(!f.noMetadata) {
   for(const url of f.imageURLs||['https://i.ytimg.com/vi/'+video+'/default.jpg']) if(!f.legacyOnly) metadata(metadataParent||container,'modern',url);
   for(const url of f.legacyURLs||(f.legacyOnly?['https://studio.youtube.com/video/'+video+'/comments']:[])) metadata(metadataParent||row,'legacy',url);
 }
 if(f.extraNestedMetadata) metadata(replies,'modern','https://i.ytimg.com/vi/OtherVideo2/default.jpg');
 if(f.innerNativeOnly) {
   const inner=node('ytcp-comment',{'comment-id':'UgxInner001'});
   for(const child of [...original.children]) { child.remove(); inner.append(child); }
   original.append(inner);
 }
 const zero=f.zero===undefined?'qualified':f.zero;
 let host, zeroButton;
 function expandControl() {
   row.setAttribute('show-replies','');
   host.removeAttribute('disabled'); zeroButton.removeAttribute('disabled');
   host.setAttribute('aria-disabled','false'); zeroButton.setAttribute('aria-disabled','false');
   host.setAttribute('icon','COLLAPSE'); zeroButton.setAttribute('aria-label','1 reply'); zeroButton.textContent='1 reply';
 }
 if(zero!=='absent') {
   host=node('ytcp-button',{id:'show-replies-button',disabled:'','aria-disabled':'true',icon:'EXPAND'});
   const button=node('button',{disabled:'','aria-disabled':'true','aria-label':'0 replies'},'0 replies');
   zeroButton=button;
   host.append(node('ytcp-button-shape').append(button));
   if(zero==='enabled') { host.removeAttribute('disabled'); button.removeAttribute('disabled'); }
   if(zero==='host_missing_disabled') host.removeAttribute('disabled');
   if(zero==='child_enabled') button.disabledOverride=false;
   if(zero==='host_aria_false') host.setAttribute('aria-disabled','false');
   if(zero==='child_aria_false') button.setAttribute('aria-disabled','false');
   if(zero==='nonzero') { button.textContent='2 replies'; button.setAttribute('aria-label','2 replies'); }
   if(zero==='collapsed') host.setAttribute('aria-expanded','false');
   const toolbar=node('div',{id:f.controlFault==='wrong_toolbar'?'other-toolbar':'toolbar','class':'style-scope ytcp-comment-action-buttons'});
   if(f.controlFault==='inner_toolbar') actions.append(node('ytcp-comment',{'comment-id':'UgxForeign001'}).append(toolbar));
   else actions.append(toolbar);
   (zero==='unassociated'?row:toolbar).append(host);
   if(zero==='expanded') expandControl();
   if(f.controlFault==='no_show') row.removeAttribute('show-replies');
   if(f.controlFault==='wrong_icon') host.setAttribute('icon','EXPAND');
   if(f.controlFault==='host_disabled') host.setAttribute('disabled','');
   if(f.controlFault==='child_disabled') button.setAttribute('disabled','');
   if(f.controlFault==='host_aria') host.setAttribute('aria-disabled','true');
   if(f.controlFault==='child_aria') button.setAttribute('aria-disabled','true');
 }
 if(f.progress) row.append(node('span',{role:'progressbar'}));
 if(f.collapsed) row.append(node('button',{'aria-expanded':'false'},'View 2 replies'));
 if(f.more) row.append(node('button',{},'SHOW MORE REPLIES'));
 if(f.connected===false) row.remove();
 let nativeOne=f.nativeOne===undefined?target:f.nativeOne, nativeTwo=f.nativeTwo===undefined?target:f.nativeTwo;
 const window={ytcfg:{get:()=>nativeOne},yt:{config_:{get CHANNEL_ID(){return nativeTwo;}}}};
 const context={document,location,window,URL,console:{log(){}}};
 function run(script,args) { return vm.runInNewContext('(function(){'+script+'\n}).apply(null,'+JSON.stringify(args)+')',context,{timeout:1000}); }
 function mutate(change) {
   if(change==='comment') original.setAttribute('comment-id','UgxOther');
   else if(change==='video') { for(const image of row.querySelectorAll('img')) image.setAttribute('src','https://i.ytimg.com/vi/OtherVideo2/default.jpg'); }
   else if(change==='text') content.textContent='Where  can I watch the film?';
   else if(change==='author') author.textContent='@Other';
   else if(change==='author_url') author.setAttribute('href','http://www.youtube.com/@Other');
   else if(change==='author_channel') author.setAttribute('href','https://www.youtube.com/channel/UCFFFFFFFFFFFFFFFFFFFFFF');
   else if(change==='origin') location.origin='https://studio.youtube.com.invalid';
   else if(change==='receiving') location.pathname='/channel/UCFFFFFFFFFFFFFFFFFFFFFF/comments';
   else if(change==='entered') editor.textContent='Changed draft';
   else if(change==='detached') row.remove();
   else if(change==='native_changed') { nativeOne='UCFFFFFFFFFFFFFFFFFFFFFF'; nativeTwo=nativeOne; }
   else if(change==='native_missing') { nativeOne=null; nativeTwo=null; }
   else if(change==='native_conflict') nativeTwo='UCFFFFFFFFFFFFFFFFFFFFFF';
   else if(change) throw Error('unknown fixed-fixture mutation');
 }
 let result;
 if(f.operation==='pipeline'||f.operation==='delivery') {
   const extracted=run(f.scripts.extract,[0]);
   const bound=run(f.scripts.bind,['ytcp-comment-thread',0,f.expected,'fixture-target']);
   const before=bound?run(f.scripts.snapshot,['[data-0102-reply-target="fixture-target"]',f.expected,f.draft]):null;
   mutate(f.change);
   const submission=bound&&before&&before.complete&&!before.matching_ids.length?
     run(f.scripts.submit,['[data-0102-reply-target="fixture-target"]',0,f.expected,f.draft]):null;
   result={extracted,bound,before,submission};
   if(f.operation==='delivery'&&submission&&submission.success) {
     replies.append(reply({modern:true,id:'UgxOriginal001.NewReply001'}));
     if(!replies.isConnected) row.append(replies);
     expandControl();
     result.after=run(f.scripts.snapshot,['[data-0102-reply-target="fixture-target"]',f.expected,f.draft]);
   }
 } else if(f.operation==='extract') result=run(f.scripts.extract,[0]);
 else if(f.operation==='snapshot') result=run(f.scripts.snapshot,['ytcp-comment-thread',f.expected,f.draft]);
 else throw Error('unknown fixed-fixture operation');
 process.stdout.write(JSON.stringify({result,click_count:clicks}));
});
"""


@pytest.fixture(scope='module')
def source_scripts():
    root = Path(__file__).resolve().parents[4]
    directory = root / 'modules/communication/video_comments/skillz/tars_like_heart_reply/src'
    row = ast.parse((directory / 'comment_row_context.py').read_text(encoding='utf-8'))
    values = {node.targets[0].id: ast.literal_eval(node.value) for node in row.body
              if isinstance(node, ast.Assign) and len(node.targets) == 1
              and isinstance(node.targets[0], ast.Name) and node.targets[0].id in
              {'COMMENT_IDENTITY_SCRIPT', 'COMMENT_ROW_SCRIPT'}}
    executor = ast.parse((directory / 'reply_executor.py').read_text(encoding='utf-8'))
    scripts = {'extract': values['COMMENT_IDENTITY_SCRIPT'] + values['COMMENT_ROW_SCRIPT']}
    for action, name in (('bind', '_bind_reply_target'), ('snapshot', '_reply_snapshot'),
                         ('submit', '_execute_reply_unverified')):
        method = next(node for node in ast.walk(executor) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name)
        operands = [node.args[0] for node in ast.walk(method) if isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute) and node.func.attr == 'execute_script'
                    and node.args and isinstance(node.args[0], ast.BinOp)
                    and isinstance(node.args[0].left, ast.Name) and node.args[0].left.id == 'COMMENT_IDENTITY_SCRIPT']
        assert len(operands) == 1
        scripts[action] = values['COMMENT_IDENTITY_SCRIPT'] + ast.literal_eval(operands[0].right)
    return scripts


def dom(source_scripts, operation='pipeline', **options):
    expected = dict(text='Where can I watch the film?', author_name='Aki', author_handle='@Aki',
                    channel_id=None, comment_id='UgxOriginal001', video_id='AbCdEfGhI_1',
                    author_url='http://www.youtube.com/@Aki', _target_channel_id='UCRRRRRRRRRRRRRRRRRRRRRR',
                    _target_channel_handle='@Creator')
    if 'targetHandle' in options:
        expected['_target_channel_handle'] = options.pop('targetHandle')
    if options.get('channelAuthor'):
        expected.update(channel_id='UCAAAAAAAAAAAAAAAAAAAAAA', author_url='https://www.youtube.com/channel/UCAAAAAAAAAAAAAAAAAAAAAA')
    payload = dict(scripts=source_scripts, operation=operation, expected=expected,
                   draft='Thanks for asking.', **options)
    node = os.environ.get('NODE_BINARY') or shutil.which('node')
    assert node, 'Node required for exact-source Studio DOM qualification'
    result = subprocess.run([node, '-e', STUDIO_DOM], input=json.dumps(payload), capture_output=True,
                            text=True, check=True, timeout=5,
                            env={'SystemRoot': r'C:\Windows', 'WINDIR': r'C:\Windows'})
    return json.loads(result.stdout)


def test_observed_modern_tree_extracts_binds_and_submits_once(source_scripts):
    output = dom(source_scripts)
    value = output['result']
    assert value['extracted']['video_id'] == 'AbCdEfGhI_1'
    assert value['extracted']['video_title'] == 'Observed film title'
    assert value['extracted']['video_url'] is None
    assert value['extracted']['channel_id'] is None
    assert value['extracted']['author_url'] == 'http://www.youtube.com/@Aki'
    assert value['extracted']['comment_id'] == 'UgxOriginal001'
    assert value['bound'] is True and value['before']['complete'] is True
    assert value['submission']['success'] is True and output['click_count'] == 1


@pytest.mark.parametrize('kind', ['legacy', 'mixed_same', 'repeated_modern', 'nested_foreign'])
def test_retained_or_repeated_owned_metadata_is_useful(source_scripts, kind):
    options = {'legacyOnly': True, 'legacyAuthor': True} if kind == 'legacy' else {}
    if kind == 'mixed_same': options['legacyURLs'] = ['https://studio.youtube.com/video/AbCdEfGhI_1/comments']
    if kind == 'repeated_modern': options['imageURLs'] = ['https://i.ytimg.com/vi/AbCdEfGhI_1/default.jpg'] * 2
    if kind == 'nested_foreign': options.update(extraNestedMetadata=True, zero='absent')
    value = dom(source_scripts, **options)
    assert value['result']['extracted']['video_id'] == 'AbCdEfGhI_1'
    assert value['result']['submission'] is not None
    assert value['result']['submission']['success'] is True and value['click_count'] == 1
    assert value['result']['extracted']['channel_id'] is None


@pytest.mark.parametrize('url', [
    'http://i.ytimg.com/vi/AbCdEfGhI_1/default.jpg', 'ftp://i.ytimg.com/vi/AbCdEfGhI_1/default.jpg',
    '//i.ytimg.com/vi/AbCdEfGhI_1/default.jpg', '/vi/AbCdEfGhI_1/default.jpg',
    'data:image/png,synthetic', 'blob:https://i.ytimg.com/synthetic',
    'https://i.ytimg.com.invalid/vi/AbCdEfGhI_1/default.jpg', 'https://sub.i.ytimg.com/vi/AbCdEfGhI_1/default.jpg',
    'https://user@i.ytimg.com/vi/AbCdEfGhI_1/default.jpg', 'https://user:pass@i.ytimg.com/vi/AbCdEfGhI_1/default.jpg',
    'https://i.ytimg.com:444/vi/AbCdEfGhI_1/default.jpg', 'https://i.ytimg.com/vi/AbCdEfGhI%5f1/default.jpg',
    'https://i.ytimg.com/vi/short/default.jpg', 'https://i.ytimg.com/vi/AbCdEfGhI_12/default.jpg',
    'https://i.ytimg.com/vi/AbCdEfGhI_1/hqdefault.jpg', 'https://i.ytimg.com/vi_webp/AbCdEfGhI_1/default.jpg',
    'https://i.ytimg.com/vi/AbCdEfGhI_1/default.jpg?x=1', 'https://i.ytimg.com/vi/AbCdEfGhI_1/default.jpg#x',
])
def test_unqualified_image_urls_never_supply_identity_or_click(source_scripts, url):
    value = dom(source_scripts, imageURLs=[url])
    assert value['result']['extracted']['video_id'] is None
    assert not value['result']['bound'] and value['click_count'] == 0


@pytest.mark.parametrize('problem', ['none', 'nested', 'foreign', 'legacy_conflict', 'modern_conflict'])
def test_missing_foreign_nested_and_conflicting_metadata_refuse(source_scripts, problem):
    options = {'noMetadata': problem == 'none', 'nestedMetadata': problem == 'nested',
               'foreignMetadata': problem == 'foreign'}
    if problem == 'legacy_conflict': options['legacyURLs'] = ['https://studio.youtube.com/video/OtherVideo2/comments']
    if problem == 'modern_conflict': options['imageURLs'] = ['https://i.ytimg.com/vi/AbCdEfGhI_1/default.jpg', 'https://i.ytimg.com/vi/OtherVideo2/default.jpg']
    value = dom(source_scripts, **options)
    assert value['result']['extracted']['video_id'] is None
    if 'conflict' in problem: assert value['result']['extracted']['video_title'] is None
    assert not value['result']['bound'] and value['click_count'] == 0


@pytest.mark.parametrize('problem', ['nestedAuthorOnly', 'nestedTextOnly', 'nestedCommentIdOnly', 'rowConflict'])
def test_nested_or_conflicting_original_identity_cannot_repair_owner(source_scripts, problem):
    value = dom(source_scripts, **{problem: True})
    assert not value['result']['bound'] and value['click_count'] == 0


def test_inner_native_comment_cannot_lend_outer_comment_identity(source_scripts):
    value = dom(source_scripts, innerNativeOnly=True)
    assert value['result']['extracted']['comment_id'] == 'UgxOriginal001'
    assert value['result']['extracted']['video_id'] is None
    assert value['result']['extracted']['channel_id'] is None
    assert not value['result']['bound'] and value['click_count'] == 0


@pytest.mark.parametrize('url', ['javascript:void(0)', 'data:text/plain,synthetic',
    'https://www.youtube.com.invalid/@Aki', 'https://example.invalid/@Aki',
    'http://user@www.youtube.com/@Aki', 'https://www.youtube.com:444/@Aki',
    'https://www.youtube.com/watch?v=AbCdEfGhI_1', 'https://www.youtube.com/@'])
def test_unqualified_author_url_never_repairs_original_identity(source_scripts, url):
    value = dom(source_scripts, authorURL=url)
    assert not value['result']['bound'] and value['click_count'] == 0


@pytest.mark.parametrize('change', ['comment', 'video', 'text', 'author', 'author_url',
                                    'author_channel', 'origin', 'receiving', 'entered', 'detached'])
def test_actual_final_submit_rechecks_frozen_identity_and_entered_text(source_scripts, change):
    value = dom(source_scripts, change=change)
    assert value['result']['bound'] is True and value['result']['before']['complete'] is True
    assert not value['result']['submission']['success'] and value['click_count'] == 0


def test_selected_known_author_channel_is_still_rechecked(source_scripts):
    good = dom(source_scripts, channelAuthor=True)
    assert good['result']['extracted']['channel_id'] == 'UCAAAAAAAAAAAAAAAAAAAAAA'
    assert good['click_count'] == 1
    changed = dom(source_scripts, channelAuthor=True, change='author_channel')
    assert changed['result']['bound'] is True and changed['click_count'] == 0


@pytest.mark.parametrize('zero', ['enabled', 'host_missing_disabled', 'child_enabled',
                                  'host_aria_false', 'child_aria_false', 'nonzero', 'collapsed', 'unassociated'])
def test_only_exact_owned_disabled_zero_widget_qualifies_empty_baseline(source_scripts, zero):
    value = dom(source_scripts, zero=zero)
    assert value['result']['bound'] is True
    assert value['result']['before']['complete'] is False and value['click_count'] == 0


@pytest.mark.parametrize('problem', ['progress', 'collapsed', 'existing_reply'])
def test_zero_widget_never_overrides_other_incomplete_or_existing_reply_evidence(source_scripts, problem):
    options = {problem: True} if problem != 'existing_reply' else {'replies': [{'id': 'UgxOld'}]}
    value = dom(source_scripts, **options)
    assert value['result']['before'] is not None
    assert value['result']['before']['complete'] is False and value['click_count'] == 0


def test_zero_widget_refuses_supported_class_based_existing_replies(source_scripts):
    value = dom(source_scripts, classReplies=True, replies=[{'id': 'UgxOld'}])
    assert value['result']['bound'] is True
    assert value['result']['before']['complete'] is False and value['click_count'] == 0


@pytest.mark.parametrize('problem', ['good', 'wrong_channel', 'wrong_text', 'no_owner',
                                     'missing_id', 'duplicate_id'])
def test_existing_creator_readback_contract_is_not_widened(source_scripts, problem):
    reply = dict(id='UgxCreator', channel='UCRRRRRRRRRRRRRRRRRRRRRR', text='Thanks for asking.', owner=True)
    if problem == 'wrong_channel': reply['channel'] = 'UCFFFFFFFFFFFFFFFFFFFFFF'
    if problem == 'wrong_text': reply['text'] = 'Thanks for asking. Extra'
    if problem == 'no_owner': reply['owner'] = False
    if problem == 'missing_id': reply['id'] = None
    replies = [reply, reply] if problem == 'duplicate_id' else [reply]
    value = dom(source_scripts, operation='snapshot', zero='absent', replies=replies)
    assert value['result'] is not None
    if problem in ('missing_id', 'duplicate_id'): assert value['result']['complete'] is False
    else: assert value['result']['matching_ids'] == (['UgxCreator'] if problem == 'good' else [])
    assert value['click_count'] == 0


def test_row_disappearance_and_historical_matching_reply_never_establish_new_delivery(source_scripts):
    assert dom(source_scripts, operation='snapshot', connected=False)['result'] is None
    old = dict(id='UgxHistorical', channel='UCRRRRRRRRRRRRRRRRRRRRRR', text='Thanks for asking.', owner=True)
    value = dom(source_scripts, zero='absent', replies=[old])
    assert value['result']['before'] is not None
    assert value['result']['before']['matching_ids'] == ['UgxHistorical']
    assert value['result']['submission'] is None and value['click_count'] == 0


def test_modern_toolbar_zero_to_new_creator_readback_after_one_submit(source_scripts):
    value = dom(source_scripts, operation='delivery')
    assert value['result']['bound'] is True
    assert value['result']['before'] == {'complete': True, 'ids': [], 'matching_ids': []}
    assert value['result']['submission']['success'] is True and value['click_count'] == 1
    assert value['result']['after']['complete'] is True
    assert value['result']['after']['matching_ids'] == ['UgxOriginal001.NewReply001']


def test_expanded_label_one_is_not_the_four_reply_inventory_count(source_scripts):
    replies = [{'modern': True, 'id': 'UgxOriginal001.R' + str(i), 'text': 'Earlier answer ' + str(i)} for i in range(4)]
    value = dom(source_scripts, operation='snapshot', zero='expanded', replies=replies)
    assert value['result']['complete'] is True
    assert len(value['result']['ids']) == 4 and value['result']['matching_ids'] == []


def test_multiple_supported_reply_inventories_cannot_hide_an_old_creator_id(source_scripts):
    value = dom(source_scripts, zero='expanded', secondReplies=True,
                replies=[{'modern': True, 'id': 'UgxOriginal001.Past', 'text': 'Earlier answer'}])
    assert value['result']['bound'] is True
    assert value['result']['before']['complete'] is False and value['click_count'] == 0


@pytest.mark.parametrize('problem', ['no_show', 'wrong_icon', 'host_disabled', 'child_disabled',
                                    'host_aria', 'child_aria', 'wrong_toolbar', 'inner_toolbar'])
def test_expanded_control_requires_exact_observed_state_and_toolbar(source_scripts, problem):
    value = dom(source_scripts, zero='expanded', controlFault=problem,
                replies=[{'modern': True, 'id': 'UgxOriginal001.Past', 'text': 'Earlier answer'}])
    assert value['result']['bound'] is True
    assert value['result']['before']['complete'] is False and value['click_count'] == 0


@pytest.mark.parametrize('problem', ['empty', 'duplicate', 'raw_id_missing', 'wrong_parent',
                                    'hidden', 'loading', 'more', 'progress', 'foreign', 'inner'])
def test_expanded_control_cannot_replace_settled_owned_inventory(source_scripts, problem):
    item = {'modern': True, 'id': 'UgxOriginal001.Past', 'text': 'Earlier answer'}
    if problem == 'raw_id_missing': item['rawIDMissing'] = True
    if problem == 'wrong_parent': item['id'] = 'UgxOther.Past'
    if problem == 'hidden': item['hidden'] = True
    replies = [] if problem == 'empty' else [item, item] if problem == 'duplicate' else [item]
    options = {'replyLoading': problem == 'loading', 'more': problem == 'more',
               'progress': problem == 'progress', 'foreignReplies': problem == 'foreign',
               'innerReplies': problem == 'inner'}
    value = dom(source_scripts, zero='expanded', replies=replies, **options)
    assert value['result']['bound'] is True
    assert value['result']['before']['complete'] is False and value['click_count'] == 0


@pytest.mark.parametrize('problem', ['name_missing', 'badge_missing', 'no_creator', 'wrong_name',
                                    'wrong_badge', 'badge_text', 'inner_metadata', 'duplicate_badge'])
def test_modern_creator_proof_requires_owned_agreeing_native_badge_and_anchors(source_scripts, problem):
    reply = {'modern': True, 'id': 'UgxOriginal001.New'}
    if problem == 'name_missing': reply['nameMissing'] = True
    if problem == 'badge_missing': reply['badgeMissing'] = True
    if problem == 'no_creator': reply['owner'] = False
    if problem == 'wrong_name': reply['nameURL'] = 'http://www.youtube.com/@Other'
    if problem == 'wrong_badge': reply['badgeURL'] = 'http://www.youtube.com/@Other'
    if problem == 'badge_text': reply['badgeText'] = '@Other'
    if problem == 'inner_metadata': reply['innerMetadata'] = True
    if problem == 'duplicate_badge': reply['badgeDuplicate'] = True
    value = dom(source_scripts, operation='snapshot', zero='absent', replies=[reply])
    assert value['result'] is not None
    assert not value['result'].get('matching_ids') and value['click_count'] == 0


@pytest.mark.parametrize('native', [None, '', 123, 'UCFFFFFFFFFFFFFFFFFFFFFF'])
def test_modern_target_refuses_missing_malformed_or_conflicting_native_receiving_id(source_scripts, native):
    value = dom(source_scripts, nativeTwo=native)
    if native is None:
        value = dom(source_scripts, nativeOne=None, nativeTwo=None)
    assert value['result']['bound'] is False and value['click_count'] == 0


@pytest.mark.parametrize('missing', ['nativeOne', 'nativeTwo'])
def test_one_available_native_receiving_owner_is_useful_without_conflict(source_scripts, missing):
    value = dom(source_scripts, **{missing: None})
    assert value['result']['bound'] is True and value['result']['before']['complete'] is True
    assert value['result']['submission']['success'] is True and value['click_count'] == 1


@pytest.mark.parametrize('change', ['native_changed', 'native_missing', 'native_conflict'])
def test_actual_submit_rechecks_native_receiving_identity_after_good_baseline(source_scripts, change):
    value = dom(source_scripts, change=change)
    assert value['result']['bound'] is True and value['result']['before']['complete'] is True
    assert value['result']['submission']['success'] is False and value['click_count'] == 0


@pytest.mark.parametrize('handle', [None, '', 'Creator', 123])
def test_modern_zero_baseline_requires_frozen_canonical_registry_context(source_scripts, handle):
    value = dom(source_scripts, targetHandle=handle)
    assert value['result']['bound'] is False and value['click_count'] == 0


def test_old_modern_creator_id_cannot_establish_new_delivery(source_scripts):
    value = dom(source_scripts, zero='expanded', replies=[{'modern': True, 'id': 'UgxOriginal001.Past'}])
    assert value['result']['before']['complete'] is True
    assert value['result']['before']['matching_ids'] == ['UgxOriginal001.Past']
    assert value['result']['submission'] is None and value['click_count'] == 0


def _bare_actual_executor():
    path = Path(__file__).resolve().parents[4] / 'modules/communication/video_comments/skillz/tars_like_heart_reply/src/reply_executor.py'
    tree = ast.parse(path.read_text(encoding='utf-8'))
    definition = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'BrowserReplyExecutor')
    namespace = dict(asyncio=asyncio, os=os, random=random, logger=logging.getLogger('studio-fixture'),
                     uuid4=uuid4, Any=object, Dict=dict, List=list, HUMAN_BEHAVIOR_AVAILABLE=False)
    exec(compile(ast.Module(body=[definition], type_ignores=[]), str(path), 'exec'), namespace)
    executor = object.__new__(namespace['BrowserReplyExecutor'])
    executor._reply_actions_allowed = lambda: True
    executor.history_store = SimpleNamespace(reply_target_key=lambda _: 'synthetic-target')
    return executor


@pytest.mark.parametrize('entry', ['valid', 'missing', 'wrong_id', 'bad_handle'])
def test_actual_executor_freezes_registry_once_and_discards_forged_caller_handle(monkeypatch, entry):
    executor, calls, captured = _bare_actual_executor(), [], []
    expected = {'_target_channel_id': 'UCRRRRRRRRRRRRRRRRRRRRRR', '_target_channel_handle': '@Forged'}
    registry = ModuleType('modules.infrastructure.shared_utilities.youtube_channel_registry')
    def get_channel_by_id(channel_id):
        calls.append(channel_id)
        if entry == 'missing': return None
        return {'id': 'UCFFFFFFFFFFFFFFFFFFFFFF' if entry == 'wrong_id' else channel_id,
                'handle': 'Creator' if entry == 'bad_handle' else '@Creator'}
    registry.get_channel_by_id = get_channel_by_id
    monkeypatch.setitem(sys.modules, registry.__name__, registry)
    executor._bind_reply_target = lambda index, target, marker: captured.append(target) or False
    assert asyncio.run(executor.execute_reply(1, 'Thanks for asking.', expected_comment=expected)) is False
    assert calls == ['UCRRRRRRRRRRRRRRRRRRRRRR']
    assert captured[0] is not expected and expected['_target_channel_handle'] == '@Forged'
    assert captured[0].get('_target_channel_handle') == ('@Creator' if entry == 'valid' else None)
