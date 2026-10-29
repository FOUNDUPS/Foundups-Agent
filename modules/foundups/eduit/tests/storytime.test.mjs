import test from 'node:test';
import assert from 'node:assert/strict';
import {initial,advance,actorPose,DEADLINE,DURATION,rescuePoints,worldTime} from '../../../../public/eduit/storytime/engine.mjs';
import {movie,scene,EARTH} from '../../../../public/eduit/storytime/scene.mjs';
const tick=(s,n)=>{for(let i=0;i<n;i++)s=advance(s,'tick',.1);return s;};
const wake=(s,id)=>{const actor=s.actors.find(a=>a.id===id);for(let i=0;i<actor.wakeTaps;i++)s=advance(s,'select:'+id);return s;};
test('no input still runs collapse and footprint after a slow round',()=>{let s=advance(initial(),'start');s=tick(s,481);assert.equal(s.phase,'playing');assert.ok(s.actors.every(a=>a.status==='lost'));s=tick(s,120);assert.equal(s.phase,'over');assert.equal(s.elapsed,DURATION);const svg=scene({...gameWorld(s,s.actors),showWords:false});assert.ok(svg.includes('data-event="footprint"'));assert.ok(!svg.includes('data-actor='));});
test('partial parent wake stays selectable, full wake and travel lock selection',()=>{let s=advance(initial(),'start');s=advance(s,'select:parent-1');assert.equal(s.selected,null);assert.equal(s.actors[0].taps,1);s=advance(s,'select:parent-1');s=advance(s,'select:parent-1');assert.equal(s.selected,'parent-1');s=advance(s,'select:baby-2');assert.equal(s.actors[3].status,'sleeping');s=advance(s,'root');s=advance(s,'root');s=tick(s,41);assert.equal(s.actors[0].status,'safe');assert.equal(s.selected,null);});
test('all five can be saved with slow deliberate input; awards exactly once',()=>{let s=advance(initial(),'start');for(const id of ['baby-1','baby-2','baby-3','parent-1','parent-2']){s=tick(s,20);const actor=s.actors.find(a=>a.id===id);for(let i=0;i<actor.wakeTaps;i++){s=advance(s,'select:'+id);s=tick(s,8);}s=tick(s,15);s=advance(s,'root');s=tick(s,Math.ceil(actor.duration*10)+1);}assert.ok(s.actors.every(a=>a.status==='safe'));assert.equal(s.phase,'celebrating');assert.equal(s.outcome,'rescued');s=tick(s,36);assert.equal(s.phase,'over');assert.equal(s.awards.length,5);assert.ok(s.score>=50&&s.score<=100);assert.equal(tick(s,600).score,s.score);assert.equal(advance(s,'retry').score,0);assert.equal(advance(s,'retry').awards.length,0);});
test('late movement cannot rescue; invalid delta remains bounded',()=>{let s=tick(advance(initial(),'start'),460);s=wake(s,'parent-1');s=advance(s,'root');s=tick(s,30);assert.equal(s.actors[0].status,'lost');assert.equal(actorPose(s.actors[0],49).x,actorPose(s.actors[0],54).x);assert.ok(actorPose(s.actors[0],54).x<s.actors[0].destX);assert.equal(s.score,0);assert.equal(advance(s,'select:baby-1').selected,null);assert.equal(advance(advance(initial(),'start'),'tick',100).elapsed,.1);});
test('sleepers investigate and doze; selected actor can be rewoken',()=>{let s=tick(advance(initial(),'start'),61);assert.equal(s.actors[2].status,'wandering');assert.ok(actorPose(s.actors[2],s.elapsed+2).x>s.actors[2].x);s=tick(s,51);assert.equal(s.actors[2].status,'sleeping');s=wake(s,'baby-2');s=tick(s,101);assert.equal(s.selected,null);assert.equal(s.actors[3].status,'sleeping');s=wake(s,'baby-2');assert.equal(s.selected,'baby-2');});
test('practice holds danger, no time bonus, and resets preserve selected mode',()=>{let s=advance(initial({practice:true}),'start');s=tick(s,1200);assert.equal(s.phase,'playing');assert.equal(worldTime(s),30);for(const a of s.actors){s=wake(s,a.id);s=advance(s,'root');s=tick(s,Math.ceil(a.duration*10)+1);}assert.equal(s.score,50);assert.equal(s.outcome,'rescued');assert.equal(advance(s,'retry').practice,true);assert.equal(rescuePoints(0),20);assert.equal(rescuePoints(48),10);assert.equal(rescuePoints(100),10);});
test('collapse preserves soil and removes the entire chamber and family',()=>{
 const early=scene(movie(0)),late=scene(movie(14));
 assert.equal((early.match(/href="#sleepy"/g)||[]).length,5);
 for(const t of [0,1.4,9.5,10.2,10.7,14])assert.ok(scene(movie(t)).includes(`data-material="earth" width="960" height="540" fill="${EARTH}"`));
 assert.equal((late.match(/data-character="family-/g)||[]).length,0);
 assert.ok(!late.includes('M30 430'));
 assert.ok(late.includes('data-character="hero"'));
 assert.ok(!late.includes('href="#front"'));
 assert.ok(late.includes('data-place="root-pocket"'));
 assert.ok(late.includes('data-event="footprint"'));
});
test('approach, sniff, cracks and compression use visible event-local words',()=>{
 assert.equal(movie(.8).awake,false); assert.equal(movie(2.3).awake,true);
 assert.ok(movie(.8).cue.size<movie(2.3).cue.size);
 assert.ok(movie(2.3).cue.size<movie(6.9).cue.size);
 for(const t of [3.2,4.1,5.9]){
  assert.equal(movie(t).cue.kind,'sniff');assert.ok(scene(movie(t)).includes('>SNIFF</text>'));
 }
 assert.ok(!scene({...movie(3.2),showWords:false}).includes('>SNIFF</text>'));
 assert.ok(scene(movie(7.9)).includes('data-event="cracks"'));
 assert.ok(scene(movie(10.8)).includes('>SQUISH</text>'));
 assert.ok(movie(9.5).collapse===0 && movie(10.2).collapse>0 && movie(10.2).collapse<1);
 const falling=scene(movie(10.2));
 assert.ok(falling.indexOf('data-character="family-0"')<falling.indexOf('data-event="falling-roof"'));
 assert.ok(falling.indexOf('data-place="root-pocket"')<falling.indexOf('data-event="falling-roof"'));
 assert.ok(movie(12.8).turn>0 && movie(12.8).turn<1);
});

test('moving actors paint over pocket background, under falling roof',()=>{let s=advance(initial(),'start');s=wake(s,'baby-3');s=advance(s,'root');s=tick(s,6);assert.equal(s.actors[4].status,'moving');const poses=s.actors.map(a=>actorPose(a,s.elapsed));assert.ok(poses[4].x>s.actors[4].x);const svg=scene({...gameWorld(s,poses)});assert.ok(svg.indexOf('data-place="root-pocket"')<svg.indexOf('data-actor="baby-3"'));});

import {events,locales,localizeEvent,normalizeLocale} from '../../../../public/eduit/storytime/learning-events.mjs';
test('locale words preserve stable IDs and world timing',()=>{for(const locale of Object.keys(locales))for(const event of events){const cue=localizeEvent(event,locale);assert.equal(cue.id,event.id);assert.equal(cue.start,event.start);assert.equal(cue.end,event.end);assert.ok(cue.word);}assert.equal(normalizeLocale('unknown'),'en');assert.ok(events.some(e=>e.kind==='crunch'));});

test('educational typography cannot change tremor physics',()=>{
 for(const t of [.9,2.3,7,9.9]){
  const world=movie(t),base=scene(world),enlarged=scene({...world,cue:{...world.cue,size:world.cue.size*2}});
  assert.equal(base.match(/<g transform="translate\(([^)]*)\)"/)[1],enlarged.match(/<g transform="translate\(([^)]*)\)"/)[1]);
 }
});

import {gameWorld,gameEvents} from '../../../../public/eduit/storytime/game-world.mjs';
test('game cues have valid source foley and progressive world hazards',()=>{for(const e of gameEvents){assert.ok(e.sourceTime>=0&&e.sourceTime+e.sourceDuration<=15);assert.ok(e.start<e.end&&e.end<=DURATION);}const s={...initial(),elapsed:24};const early=gameWorld(s,s.actors),late=gameWorld({...s,elapsed:40},s.actors);assert.ok(late.warning>early.warning);assert.ok(scene(early).includes('falling-dirt'));assert.ok(scene(late).includes('new-cracks'));assert.equal(gameWorld({...s,outcome:'rescued'},s.actors).collapse,0);});

// Appearance is presentation only; these fixed render oracles come from main 8b345ec.
import {createHash} from 'node:crypto';
import {appearances,appearanceFor} from '../../../../public/eduit/storytime/rig.mjs';
import {learningWordLayout} from '../../../../public/eduit/storytime/scene.mjs';
test('default appearance retains the original rendered art and invalid IDs fall back',()=>{
 const golden={0:'5dbade47fbf60c95dd4dc0674d084500d08e3aa9633516154ef90d580178feb6',
  '3.2':'5a7f43866bdc4495ba9ae91a19b4ff683e186d2a4a5a4152a4190609d3fd2ce4',
  '10.8':'4e439f09eeee58e5d17066e923ce10847e5ab6dd529f0785ff09680c49824a22',
  14:'8be4af1aac002f441c6c307dfd8dfdb058e01a8aa8f8bfa68f904be1008e33e7'};
 for(const [t,hash]of Object.entries(golden)){
  const world={...movie(Number(t)),showWords:false};
  assert.equal(createHash('sha256').update(scene(world)).digest('hex'),hash);
  for(const invalid of [null,{},'__proto__','constructor','missing','https://example.invalid/a.svg']){
   assert.equal(appearanceFor(invalid).id,'mamma');assert.equal(scene({...world,appearance:invalid}),scene(world));
  }
 }
 assert.ok(Object.isFrozen(appearances));assert.ok(Object.isFrozen(appearances.mermaid));
});
test('mermaid artwork changes every pose but never mutates simulated input or physical events',()=>{
 for(const phase of ['sleeping','awake','moving','safe']){
  const state=initial();state.actors=state.actors.map(a=>({...a,status:phase,awake:phase!=='sleeping'}));
  const before=structuredClone(state),world={...gameWorld(state,state.actors),turn:1};
  const original=scene(world),mermaid=scene({...world,appearance:'mermaid'});
  assert.notEqual(mermaid,original);assert.ok(mermaid.includes('#164D68'));assert.deepEqual(state,before);
  assert.equal((mermaid.match(/data-(?:actor|survivor)=/g)||[]).length,5);
  assert.equal((original.match(/data-(?:actor|survivor)=/g)||[]).length,5);
 }
 for(const t of [0,2,9.9,10.8,14]){
  const world=movie(t),before=structuredClone(world);
  const a=scene({...world,appearance:'mamma'}),b=scene({...world,appearance:'mermaid'});
  assert.deepEqual([...a.matchAll(/data-event="([^"]+)"/g)].map(m=>m[1]),[...b.matchAll(/data-event="([^"]+)"/g)].map(m=>m[1]));
  assert.deepEqual(world,before);
 }
});
test('rendering either appearance between inputs preserves identical rescue histories',()=>{
 for(const practice of [false,true]){
  const results=[];
  for(const appearance of Object.keys(appearances)){
   let s=advance(initial({practice}),'start');const history=[];
   for(const id of ['baby-1','baby-2','baby-3','parent-1','parent-2']){
    s=wake(s,id);s=advance(s,'root');
    for(let i=0;i<50;i++){s=advance(s,'tick',.1);scene({...gameWorld(s,s.actors.map(a=>actorPose(a,s.elapsed))),appearance});}
    history.push(structuredClone(s));
   }
   results.push(history);
  }
  assert.deepEqual(results[0],results[1]);assert.equal(results[0].at(-1).awards.length,5);
 }
});
test('preschool sniff label avoids the five actor envelopes and the rescue destination',()=>{
 for(const locale of Object.keys(locales)){
  const s=initial();const a=s.actors[2];const cue={id:'test-sniff',kind:'sniff',actorId:a.id,size:58,x:a.x+180,y:a.y+28};
  const label=localizeEvent(cue,locale).word,p=learningWordLayout(label,cue,s.actors);
  assert.equal(p.overlap,0);assert.ok(p.size>=72);assert.ok(p.box.left>=0&&p.box.right<=960);
  assert.ok(p.box.top>=0&&p.box.bottom<=540);
 }
});
