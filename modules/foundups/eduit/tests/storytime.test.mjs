import test from 'node:test';
import assert from 'node:assert/strict';
import {initial,advance} from '../../../../public/eduit/storytime/engine.mjs';
import {movie,scene} from '../../../../public/eduit/storytime/scene.mjs';
const tick=(s,n,practice=false)=>{for(let i=0;i<n;i++)s=advance(s,'tick',.1,practice);return s;};
test('two ordered taps lead to shelter; wrong target does not advance',()=>{let s=advance(initial(),'start');assert.equal(advance(s,'root').phase,'wake');s=advance(s,'shrew');assert.equal(s.phase,'root');s=advance(s,'root');s=tick(s,25);assert.equal(s.phase,'stomp');s=tick(s,31);assert.equal(s.phase,'success');});
test('both missed cues allow a clean retry',()=>{for(const cue of ['wake','root']){const s=tick({phase:cue,elapsed:0},41);assert.equal(s.phase,'retry');assert.deepEqual(advance(s,'retry'),{phase:'wake',elapsed:0});}});
test('practice waits indefinitely and large clock jumps cannot skip a cue',()=>{assert.equal(tick({phase:'wake',elapsed:0},200,true).phase,'wake');assert.equal(advance({phase:'wake',elapsed:0},'tick',100).elapsed,.1);});
test('movie and game share five rigs, an intact pocket and no floor after stomp',()=>{const early=scene(movie(0)),late=scene(movie(14));assert.equal((early.match(/href="#sleepy"/g)||[]).length,5);assert.ok(late.includes('opacity="0"'));assert.ok(late.includes('href="#surprised"'));assert.ok(late.includes('M740 430'));assert.ok(late.includes('<rect width="960" height="540" fill="#9C724F" opacity="1"/>')); });
