import test from 'node:test';
import assert from 'node:assert/strict';
import {CueScheduler,storyCues} from '../../../../public/eduit/storytime/cue-scheduler.mjs';
function fixture(){let time=0;const calls=[],traces=[],ducks=[],views=[];const s=new CueScheduler({speak:(text,cb)=>calls.push({text,cb}),cancel:()=>{},view:(c,f)=>views.push([c?.id,f]),duck:v=>ducks.push(v),trace:r=>traces.push(r),now:()=>time});return {s,calls,traces,ducks,views,clock:t=>time=t};}
test('paused initialization does not consume first narration; resume replays interrupted phrase',()=>{const f=fixture();f.s.update(0);f.s.update(220,{running:true});assert.equal(f.calls[0].text,'long long ago');f.calls[0].cb.start();f.s.stop();f.s.update(500,{running:true});assert.equal(f.calls.length,2);});
test('speech callbacks are bound to generation; stale callbacks cannot unduck new speech',()=>{const f=fixture();f.s.update(220,{running:true});const old=f.calls[0].cb;f.s.reset();f.s.update(3620,{running:true});f.calls[1].cb.start();old.end();assert.equal(f.s.voice,'speaking');assert.equal(f.ducks.at(-1),true);});
test('silent/muted unavailable voice still displays and fades captions',()=>{const f=fixture();f.s.update(220,{running:true,audible:false});assert.equal(f.calls.length,0);f.s.update(3100,{running:true,audible:false});assert.deepEqual(f.views.at(-1),['long-ago',true]);f.s.update(3620,{running:true});f.calls[0].cb.error();assert.equal(f.s.voice,'done');});
test('seek backwards and repeat rearm cue without overlapping old voice',()=>{const f=fixture();f.s.update(3620,{running:true});f.s.update(220,{running:true});assert.equal(f.calls.length,2);assert.equal(f.calls[1].text,'long long ago');f.s.update(15000,{running:false});assert.equal(f.s.current,null);f.s.update(220,{running:true});assert.equal(f.calls.length,3);});
test('trace distinguishes intended media timestamp from browser callback time',()=>{const f=fixture();f.clock(1000);f.s.update(220,{running:true});f.clock(1400);f.calls[0].cb.start();const start=f.traces.find(r=>r.type==='speech_started');assert.equal(start.intended_ms,220);assert.equal(start.observed_ms,1400);assert.equal(start.media_ms,220);});
test('THUMP visible word follows original 9600ms effect; speech leaves transient clear',()=>{const c=storyCues.find(x=>x.id==='thump');assert.equal(c.start_ms,9680);assert.equal(c.speech_ms,10400);assert.ok(c.fade_ms<c.end_ms);});
test('pause after completed speech permits explicit same-cue replay; cues do not repeat every frame',()=>{const f=fixture();f.s.update(220,{running:true});f.calls[0].cb.end();f.s.update(600,{running:true});assert.equal(f.calls.length,1);f.s.stop();f.s.update(800,{running:true});assert.equal(f.calls.length,2);});

import {StorybookPlayback,storyPages,storyObjects} from '../../../../public/eduit/storytime/cue-scheduler.mjs';
function bookFixture(){let time=0;const spoken=[],views=[],traces=[];let cancels=0;
 const book=new StorybookPlayback({speak:(text,cb)=>spoken.push({text,cb}),cancel:()=>cancels++,view:(page,state)=>views.push({page,state}),trace:e=>traces.push(e),now:()=>time});
 return {book,spoken,views,traces,step:t=>{time=t;book.tick(t);},set:t=>{time=t;},cancels:()=>cancels};
}
test('storybook shares concept text while retaining independent movie/page clocks and spoken emoji-free forms',()=>{
 assert.equal(storyPages[0].text,storyObjects['long-ago'].text);
 assert.equal(storyPages[1].text,storyCues[1].text);
 assert.equal(storyPages[1].speech_offset_ms,220);assert.equal(storyCues[1].speech_ms,3620);
 assert.equal(storyPages[2].text,'a family of MAMMA 🥚s');assert.equal(storyPages[2].spoken_text,'a family of MAMMAs');
 assert.ok(storyPages.every(p=>!/[🥚]/u.test(p.spoken_text??p.text)));
});
test('storybook never speaks or advances until Play and waits for actual speech completion plus hold',()=>{
 const f=bookFixture();f.step(5000);assert.equal(f.spoken.length,0);assert.equal(f.book.index,0);
 f.set(0);f.book.play();f.step(219);assert.equal(f.spoken.length,0);f.step(220);assert.equal(f.spoken.length,1);
 f.spoken[0].cb.start();f.step(6000);assert.equal(f.book.index,0);
 f.spoken[0].cb.end();f.step(7199);assert.equal(f.book.index,0);f.step(7550);assert.equal(f.book.index,1);
});
test('navigation and pause invalidate previous-page callbacks without auto-advancing',()=>{
 const f=bookFixture();f.book.play();f.step(220);const stale=f.spoken[0].cb;
 f.book.select(2);stale.start();stale.end();f.step(10000);
 assert.equal(f.book.index,2);assert.equal(f.book.playing,false);assert.equal(f.book.completedAt,null);
 f.book.play();f.step(10220);assert.equal(f.spoken.at(-1).text,'a family of MAMMAs');
 const old=f.spoken.at(-1).cb;f.book.pause('hidden');old.end();f.step(20000);assert.equal(f.book.playing,false);assert.equal(f.book.index,2);
});
test('silent and unavailable narration use bounded holds; hung speech is not retried',()=>{
 const silent=bookFixture();silent.book.play({audible:false});silent.step(4200);assert.equal(silent.book.index,0);silent.step(4550);
 assert.equal(silent.book.index,1);assert.equal(silent.spoken.length,0);
 const failed=bookFixture();failed.book.play();failed.step(220);failed.spoken[0].cb.error();failed.step(4550);assert.equal(failed.book.index,1);
 const hung=bookFixture();hung.book.play();hung.step(220);hung.step(12000);assert.equal(hung.book.unavailable,true);
 hung.step(12500);hung.step(13000);assert.equal(hung.spoken.length,1);hung.step(13550);assert.equal(hung.book.index,1);
});
test('final story page stops; invalid selection and malformed clock cannot change progress',()=>{
 const f=bookFixture();f.book.select(storyPages.length-1);f.book.play({audible:false});f.step(4550);
 assert.equal(f.book.finished,true);assert.equal(f.book.playing,false);assert.equal(f.book.index,4);
 assert.equal(f.book.select(100),false);assert.equal(f.book.select(NaN),false);
 f.book.tick(Infinity);f.book.tick(-1);assert.equal(f.book.index,4);
 assert.throws(()=>new StorybookPlayback({pages:[],speak(){},cancel(){}}),TypeError);
});
