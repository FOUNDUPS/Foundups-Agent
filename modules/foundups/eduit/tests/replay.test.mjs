import test from 'node:test';
import assert from 'node:assert/strict';
import {initial,advance,actorPose} from '../../../../public/eduit/storytime/engine.mjs';
import {gameWorld} from '../../../../public/eduit/storytime/game-world.mjs';
import {scene} from '../../../../public/eduit/storytime/scene.mjs';
import {replay,replayWorld} from '../storytime_replay.mjs';

test('film states exactly reproduce legal engine inputs without accelerated mechanics',()=>{
 const recording=replay();let state=initial();
 for(let frame=0;frame<recording.frameCount;frame++){
  for(const action of recording.actions.filter(a=>a.frame===frame))state=advance(state,action.event);
  assert.deepEqual(recording.states[frame],state,`frame ${frame}`);
  assert.equal(scene(replayWorld(state)),scene(gameWorld(state,state.actors.map(a=>actorPose(a,state.elapsed)))));
  state=advance(state,'tick',1/30);
 }
 const final=recording.states.at(-1);
 assert.equal(final.phase,'over');assert.equal(final.outcome,'rescued');assert.equal(final.awards.length,5);
 assert.ok(final.actors.every(a=>a.status==='safe'));assert.equal(new Set(final.awards.map(a=>a.id)).size,5);
 assert.equal(recording.duration,25);assert.equal(recording.frameCount,750);
 assert.ok(recording.completedFrame/30>final.victoryAt+3.5);
});

test('repeated film exports preserve full state/action/event identity and actual cue appearances',()=>{
 const a=replay(),b=replay();assert.deepEqual(a,b);
 const hit=a.events.find(e=>e.id==='victory-thump');assert.ok(hit);
 const index=Math.round(hit.start*30);
 assert.equal(replayWorld(a.states[index]).cue.id,'victory-thump');
 assert.ok(scene(replayWorld(a.states[index])).includes('data-event="foot"'));
 assert.ok(a.events.every((e,i)=>e.start<e.end&&e.end<=a.duration&&(i===0||a.events[i-1].end<=e.start)));
 for(const event of a.events){
  for(let frame=Math.round(event.start*30);frame<Math.round(event.end*30);frame++)
   assert.equal(replayWorld(a.states[frame]).cue?.id,event.id,`observed event ${event.id}, frame ${frame}`);
  if(event.end<a.duration)assert.notEqual(replayWorld(a.states[Math.round(event.end*30)]).cue?.id,event.id);
 }
 assert.equal(scene(replayWorld(a.states.at(-1))).match(/data-survivor=/g).length,5);
});
test('safe film retains five longer sniffs and progressive impacts without mammal squish',()=>{
 const film=replay(),sniffs=film.events.filter(e=>e.kind==='sniff'),thumps=film.events.filter(e=>e.kind==='thump');
 assert.equal(sniffs.length,5);for(const cue of sniffs)assert.ok(cue.end-cue.start>=.69);
 assert.equal(thumps.length,3);assert.ok(thumps[0].gain<thumps[1].gain&&thumps[1].gain<thumps[2].gain);
 assert.ok(!film.events.some(e=>e.kind==='squish'));
 for(const state of film.states)assert.notEqual(replayWorld(state).cue?.kind,'squish');
 assert.equal(film.duration,25);assert.equal(film.revision,'same-engine-rescue-3');
});
