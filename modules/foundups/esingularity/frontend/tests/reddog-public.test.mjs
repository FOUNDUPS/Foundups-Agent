import {test,after} from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync,writeFileSync,mkdtempSync,rmSync,copyFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import ts from 'typescript';
const root=fileURLToPath(new URL('../',import.meta.url));
const temp=mkdtempSync(path.join(root,'node_modules/.reddog-tests-'));
after(()=>rmSync(temp,{recursive:true,force:true}));
for (const name of ['reddog-policy','reddog-store','reddog-knowledge','reddog-openrouter','reddog-http','project-data']) {
  let text=readFileSync(path.join(root,`lib/${name}.ts`),'utf8').replace('../content/reddog-public-sources.json','./reddog-public-sources.json');
  writeFileSync(path.join(temp,`${name}.js`),ts.transpileModule(text,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,esModuleInterop:true}}).outputText);
}
copyFileSync(path.join(root,'content/reddog-public-sources.json'),path.join(temp,'reddog-public-sources.json'));
writeFileSync(path.join(temp,'package.json'),'{"type":"commonjs"}');
const require=createRequire(import.meta.url);
const {RedDogStore}=require(path.join(temp,'reddog-store.js'));
const {handlePublicRequest}=require(path.join(temp,'reddog-http.js'));
const {publicReply}=require(path.join(temp,'reddog-openrouter.js'));
const {publicKnowledge}=require(path.join(temp,'reddog-knowledge.js'));
const {readBoundedJson}=require(path.join(temp,'reddog-policy.js'));
const migration=readFileSync(path.join(root,'drizzle/0000_reddog_public_accounting.sql'),'utf8');

// Real SQLite transactions, matching documented D1 atomic batch semantics.
function database() {
  const raw=new DatabaseSync(':memory:'); raw.exec(migration);
  const wrap=(sql,values=[])=>({bind(...args){return wrap(sql,args)},
    first(){return Promise.resolve(raw.prepare(sql).get(...values)??null)},
    run(){const r=raw.prepare(sql).run(...values);return Promise.resolve({success:true,meta:{changes:Number(r.changes)}})},sql,values});
  return {raw,prepare:sql=>wrap(sql),async batch(statements){raw.exec('BEGIN IMMEDIATE');try{
    const results=statements.map(s=>{const r=raw.prepare(s.sql).run(...s.values);return {success:true,meta:{changes:Number(r.changes)}}});
    raw.exec('COMMIT');return results;
  }catch(e){raw.exec('ROLLBACK');throw e}}};
}
const identity=(subject='subject-a',surface='esingularity')=>({subject,surface,origin:surface==='esingularity'?'https://esingularity.ai':'https://foundups.com'});
const now=1788950000;
const errorCode=code=>error=>error.code===code;

test('persistent shared subject/session budgets span both sites and rollback atomically',async()=>{
  const db=database(),a=new RedDogStore(db),b=new RedDogStore(db);
  await a.open(identity(),now);await b.open(identity('subject-a','foundups'),now);await a.open(identity(),now);
  await assert.rejects(b.open(identity('subject-a','foundups'),now),errorCode('public_limit_or_conflict'));
  assert.equal(db.raw.prepare("SELECT used FROM reddog_web_budget_v1 WHERE bucket='sessions:global'").get().used,3);
  assert.equal(db.raw.prepare('SELECT count(*) AS n FROM reddog_web_session_v1').get().n,3);
});
test('one-use nonces, compare-and-swap and concurrent provider caps survive store replacement',async()=>{
  const db=database(),a=new RedDogStore(db),active=[];
  for(let i=0;i<5;i++){
    const id=identity('subject-'+i),opened=await a.open(id,now),row=await a.session(opened.token,id,now);
    if(i<4)active.push({row,turn:await a.reserve(row,opened.nonce,0,now)});
    else {
      await assert.rejects(new RedDogStore(db).reserve(row,opened.nonce,0,now),errorCode('public_limit_or_conflict'));
      assert.equal((await a.session(opened.token,id,now)).revision,0);
    }
  }
  await assert.rejects(a.reserve(active[0].row,active[0].row.nonce,0,now),errorCode('public_limit_or_conflict'));
  assert.equal(db.raw.prepare("SELECT used FROM reddog_web_budget_v1 WHERE bucket='turns:global'").get().used,4);
  await a.finish(active[0].row.token_hash,active[0].turn.reservation);
  await a.finish(active[0].row.token_hash,active[0].turn.reservation);
  assert.equal(db.raw.prepare("SELECT used FROM reddog_web_budget_v1 WHERE bucket='in_flight'").get().used,3);
});
test('ten-turn ceiling, shared daily turn caps, expiry, denial and clock rollback',async()=>{
  const db=database(),store=new RedDogStore(db),id=identity();
  let opened;
  for(let session=0;session<2;session++){
    opened=await store.open(identity('subject-a',session?'foundups':'esingularity'),now);
    const ident=identity('subject-a',session?'foundups':'esingularity');
    for(let i=0;i<10;i++) {const row=await store.session(opened.token,ident,now); const t=await store.reserve(row,row.nonce,row.revision,now);await store.finish(row.token_hash,t.reservation);}
    const row=await store.session(opened.token,ident,now);
    await assert.rejects(store.reserve(row,row.nonce,row.revision,now),errorCode('public_session_exhausted'));
  }
  opened=await store.open(id,now); const row=await store.session(opened.token,id,now);
  await assert.rejects(store.reserve(row,row.nonce,0,now),errorCode('public_limit_or_conflict'));
  await assert.rejects(store.session(opened.token,identity('other'),now),errorCode('public_session_denied'));
  await assert.rejects(store.session(opened.token,id,now+120),errorCode('public_session_expired'));
  await assert.rejects(store.open(identity('new'),now-1),errorCode('public_limit_or_conflict'));
});
test('withdrawal denies future access and retains busy reservation until completion',async()=>{
  const db=database(),store=new RedDogStore(db),id=identity(),opened=await store.open(id,now);
  const row=await store.session(opened.token,id,now),t=await store.reserve(row,row.nonce,0,now);
  await store.withdraw(row);
  await assert.rejects(store.session(opened.token,id,now),errorCode('public_session_denied'));
  assert.equal(db.raw.prepare("SELECT used FROM reddog_web_budget_v1 WHERE bucket='in_flight'").get().used,1);
  await store.finish(row.token_hash,t.reservation);
  assert.equal(db.raw.prepare("SELECT used FROM reddog_web_budget_v1 WHERE bucket='in_flight'").get().used,0);
  assert.deepEqual(db.raw.prepare('PRAGMA table_info(reddog_web_session_v1)').all().map(x=>x.name),
    ['token_hash','surface','origin','subject','created','last_seen','revision','nonce','busy','closed']);
});
test('withdrawal cleanup between read and reservation does not leak global slots or budget',async()=>{
  const db=database(),store=new RedDogStore(db),id=identity(),opened=await store.open(id,now);
  const stale=await store.session(opened.token,id,now);
  await store.withdraw(stale);await store.open(id,now);
  await assert.rejects(store.reserve(stale,stale.nonce,0,now),errorCode('public_limit_or_conflict'));
  assert.equal(db.raw.prepare("SELECT count(*) AS n FROM reddog_web_budget_v1 WHERE bucket IN ('in_flight','turns:global')").get().n,0);
});
const config=db=>({DB:db,OPENROUTER_API_KEY:'synthetic-key',OPENROUTER_MODEL:'synthetic/model',
  REDDOG_SUBJECT_KEY:'synthetic-test-secret-at-least-32-characters',REDDOG_ENABLED:'true',REDDOG_INGRESS_VERIFIED:'cloudflare-connecting-ip-v1'});
const req=(body,token='',origin='https://esingularity.ai')=>new Request('https://esingularity.ai/api/reddog/public/esingularity/turn',{
  method:'POST',headers:{Origin:origin,'Content-Type':'application/json','CF-Connecting-IP':'192.0.2.1',...(token?{Authorization:'Bearer '+token}:{})},body:JSON.stringify(body)});
const consent={consent:true,consent_version:'reddog.public-guest.v1',actor_claim:'unspecified'};

test('transient post-admission reads cannot exhaust provider slots before inference',async()=>{
  const db=database(),prepare=db.prepare;let failures=4,calls=0;
  db.prepare=sql=>{
    const statement=prepare(sql);
    return {...statement,bind(...values){
      const bound=statement.bind(...values);
      if(sql==='SELECT * FROM reddog_web_session_v1 WHERE token_hash=? AND busy=?' && failures>0)
        bound.first=async()=>{failures--;throw Error('SYNTHETIC_PRIVATE_STORAGE_DIAGNOSTIC')};
      return bound;
    }};
  };
  const cfg=config(db),responder=async()=>{calls++;return {reply:'公開情報です。'}};
  for(let i=1;i<=5;i++){
    const request=(body,token='')=>{const r=req(body,token);r.headers.set('CF-Connecting-IP',`192.0.2.${i}`);return r};
    const opened=await (await handlePublicRequest(request(consent),'esingularity','encounter',cfg,responder,()=>now)).json();
    const result=await handlePublicRequest(request({nonce:opened.nonce,revision:0,message:'計画は？'},opened.token),'esingularity','turn',cfg,responder,()=>now);
    assert.equal(result.status,i<=4?503:200);
    assert.ok(!(await result.text()).includes('SYNTHETIC_PRIVATE_STORAGE_DIAGNOSTIC'));
    assert.equal(db.raw.prepare("SELECT used FROM reddog_web_budget_v1 WHERE bucket='in_flight'").get().used,0);
    assert.equal(db.raw.prepare('SELECT count(*) AS n FROM reddog_web_session_v1 WHERE busy IS NOT NULL').get().n,0);
    assert.equal(db.raw.prepare("SELECT used FROM reddog_web_budget_v1 WHERE bucket='turns:global'").get().used,i);
  }
  assert.equal(calls,1);
});

test('HTTP denies configuration/origin/extra fields before inference; errors never expose secrets',async()=>{
  const cfg=config(database());let calls=0;const never=async()=>{calls++;throw Error('SECRET_SENTINEL')};
  assert.equal((await handlePublicRequest(req(consent),'esingularity','encounter',{...cfg,OPENROUTER_API_KEY:undefined},never,()=>now)).status,503);
  assert.equal((await handlePublicRequest(req(consent,'','https://evil.invalid'),'esingularity','encounter',cfg,never,()=>now)).status,403);
  assert.equal((await handlePublicRequest(req({...consent,role:'owner'}),'esingularity','encounter',cfg,never,()=>now)).status,400);
  assert.equal((await handlePublicRequest(req({...consent,actor_claim:['human']}),'esingularity','encounter',cfg,never,()=>now)).status,403);
  const open=await (await handlePublicRequest(req(consent),'esingularity','encounter',cfg,never,()=>now)).json();
  const turn={nonce:open.nonce,revision:0,message:'温泉を守るには？'};
  assert.equal((await handlePublicRequest(req({...turn,model:'bad'},open.token),'esingularity','turn',cfg,never,()=>now)).status,400);
  const failed=await handlePublicRequest(req(turn,open.token),'esingularity','turn',cfg,never,()=>now);
  assert.equal(failed.status,502);assert.ok(!(await failed.text()).includes('SECRET_SENTINEL'));assert.equal(calls,1);
  const status=await (await handlePublicRequest(req({},open.token),'esingularity','status',cfg,never,()=>now)).json();
  assert.equal(status.revision,1);assert.equal(status.in_flight,false);assert.equal(status.remaining_turns,9);
});
test('bounded JSON rejects oversize, duplicate escaped keys and non-JSON',async()=>{
  await assert.rejects(readBoundedJson(new Response('x'.repeat(100)),10));
  for(const text of ['{"message":"a","message":"b"}','{"message":"a","mess\\u0061ge":"b"}','not json'])
    await assert.rejects(readBoundedJson(new Response(text),100));
  assert.deepEqual(await readBoundedJson(new Response('{"message":"a\\\"b"}'),100),{message:'a"b'});
});
test('aborting an errored response catches stream cancellation rejection',async()=>{
  const abort=new AbortController();let controller;
  const pending=readBoundedJson(new Response(new ReadableStream({start(c){controller=c}})),100,abort.signal);
  controller.error(new Error('SYNTHETIC_TRANSPORT_FAILURE'));
  abort.abort();
  await assert.rejects(pending);
  // node:test fails on an unhandled rejection, including a detached cancel().
  await new Promise(resolve=>setImmediate(resolve));
});
test('OpenRouter receives only bounded public context with server model, no tools or identities',async()=>{
  let calls=0;
  const answer=await publicReply('60日間の検証は？','esingularity',config(database()),Math.floor(Date.now()/1000)+15,async(url,options)=>{
    calls++;assert.equal(url,'https://openrouter.ai/api/v1/chat/completions');assert.equal(options.redirect,'error');assert.ok(options.signal);
    const body=JSON.parse(options.body);assert.equal(body.model,'synthetic/model');assert.equal(body.max_tokens,256);
    assert.equal(body.tools,undefined);assert.equal(body.provider.data_collection,'deny');assert.equal(body.provider.allow_fallbacks,false);
    assert.ok(!options.body.includes('synthetic-test-secret'));assert.ok(options.body.includes('約60日間'));
    return Response.json({choices:[{message:{content:'約60日間、再利用案を検証する提案です。'}}]});
  });
  assert.equal(calls,1);assert.ok(answer.reply.includes('60'));assert.ok(answer.sources.length);
  await assert.rejects(publicReply('question','foundups',{},Math.floor(Date.now()/1000)+15),errorCode('public_provider_unavailable'));
  await assert.rejects(publicReply('question','foundups',config(database()),0),errorCode('public_reply_timeout'));
});
test('knowledge preserves date, draft and public-only Mosh Pit boundaries',()=>{
  const k=publicKnowledge('採決 最新 モッシュピット 投資 確約','esingularity',new Date('2026-09-26T00:00:00Z'));
  assert.ok(k.system.includes('2026-09-26'));assert.ok(k.system.includes('採決予定だった日'));
  assert.ok(k.system.includes('curated_snapshot'));assert.ok(k.system.includes('正式参加は未確定'));
  assert.ok(k.system.includes('登録完了と答えず'));
  const sources=JSON.parse(readFileSync(path.join(root,'content/reddog-public-sources.json'),'utf8'));
  assert.deepEqual(sources.sources.map(x=>x.id),['01','03','master']);
  assert.ok(!JSON.stringify(sources).includes('1Le5foHxTHWa8QMAfqTJ0PZFUULw3oNgJTgghlXaHEYM'));
});
