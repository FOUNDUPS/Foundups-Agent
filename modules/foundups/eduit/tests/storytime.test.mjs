import test from 'node:test';
import assert from 'node:assert/strict';
import {initial,advance} from '../../../../public/eduit/storytime/engine.mjs';
import {movie,scene,EARTH} from '../../../../public/eduit/storytime/scene.mjs';
const tick=(s,n)=>{for(let i=0;i<n;i++)s=advance(s,'tick',.1);return s;};
test('no input still runs collapse and footprint through game over',()=>{let s=advance(initial(),'start');s=tick(s,100);assert.equal(s.phase,'playing');assert.ok(s.actors.every(a=>a.status==='lost'));s=tick(s,51);assert.equal(s.phase,'over');assert.equal(s.elapsed,15);const svg=scene({...movie(s.elapsed),actors:s.actors,showWords:false});assert.ok(svg.includes('data-event="footprint"'));assert.ok(!svg.includes('data-character="hero"'));assert.ok(!svg.includes('data-actor='));});
test('one selected shrew at a time; root required; moving shrew locks selection',()=>{let s=advance(initial(),'start');s=advance(s,'root');assert.equal(s.selected,null);s=advance(s,'select:baby-1');s=advance(s,'select:baby-2');assert.equal(s.selected,'baby-1');assert.equal(s.actors[3].status,'sleeping');s=advance(s,'root');s=advance(s,'root');s=tick(s,10);assert.equal(s.actors[2].status,'safe');assert.equal(s.selected,null);});
test('all five can be saved; parents require more travel time',()=>{let s=advance(initial(),'start');for(const id of ['baby-1','baby-2','baby-3','parent-1','parent-2']){s=advance(s,'select:'+id);s=advance(s,'root');s=tick(s,id.startsWith('parent')?27:10);}assert.ok(s.actors.every(a=>a.status==='safe'));s=tick(s,151);assert.equal(s.phase,'over');assert.ok(s.actors.every(a=>a.status==='safe'));assert.deepEqual(advance(s,'retry'),advance(initial(),'start'));});
test('late movement cannot rescue after deadline and invalid dt is bounded',()=>{let s=tick(advance(initial(),'start'),91);s=advance(s,'select:parent-1');s=advance(s,'root');s=tick(s,10);assert.equal(s.actors[0].status,'lost');assert.equal(advance(s,'select:baby-1').selected,null);assert.equal(advance(initial(),'select:baby-1').phase,'ready');assert.equal(advance(advance(initial(),'start'),'tick',100).elapsed,.1);});
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

test('moving actors paint over pocket background, under falling roof',()=>{let s=advance(initial(),'start');s=advance(s,'select:baby-3');s=advance(s,'root');s=tick(s,6);const svg=scene({...movie(s.elapsed),actors:s.actors});assert.ok(svg.indexOf('data-place="root-pocket"')<svg.indexOf('data-actor="baby-3"'));});

import {events,locales,localizeEvent,normalizeLocale} from '../../../../public/eduit/storytime/learning-events.mjs';
test('locale words preserve stable IDs and world timing',()=>{for(const locale of Object.keys(locales))for(const event of events){const cue=localizeEvent(event,locale);assert.equal(cue.id,event.id);assert.equal(cue.start,event.start);assert.equal(cue.end,event.end);assert.ok(cue.word);}assert.equal(normalizeLocale('unknown'),'en');assert.ok(events.some(e=>e.kind==='crunch'));});

test('educational typography cannot change tremor physics',()=>{
 for(const t of [.9,2.3,7,9.9]){
  const world=movie(t),base=scene(world),enlarged=scene({...world,cue:{...world.cue,size:world.cue.size*2}});
  assert.equal(base.match(/<g transform="translate\(([^)]*)\)"/)[1],enlarged.match(/<g transform="translate\(([^)]*)\)"/)[1]);
 }
});
