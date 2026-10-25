import test from 'node:test';
import assert from 'node:assert/strict';
import {initial,advance} from '../../../../public/eduit/storytime/engine.mjs';
import {movie,scene,EARTH} from '../../../../public/eduit/storytime/scene.mjs';
const tick=(s,n,practice=false)=>{for(let i=0;i<n;i++)s=advance(s,'tick',.1,practice);return s;};
test('two ordered taps lead to shelter; wrong target does not advance',()=>{let s=advance(initial(),'start');assert.equal(advance(s,'root').phase,'wake');s=advance(s,'shrew');assert.equal(s.phase,'root');s=advance(s,'root');s=tick(s,25);assert.equal(s.phase,'stomp');s=tick(s,31);assert.equal(s.phase,'success');});
test('both missed cues allow a clean retry',()=>{for(const cue of ['wake','root']){const s=tick({phase:cue,elapsed:0},41);assert.equal(s.phase,'retry');assert.deepEqual(advance(s,'retry'),{phase:'wake',elapsed:0});}});
test('practice waits indefinitely and large clock jumps cannot skip a cue',()=>{assert.equal(tick({phase:'wake',elapsed:0},200,true).phase,'wake');assert.equal(advance({phase:'wake',elapsed:0},'tick',100).elapsed,.1);});
test('collapse preserves soil and removes the entire chamber and family',()=>{
 const early=scene(movie(0)),late=scene(movie(14));
 assert.equal((early.match(/href="#sleepy"/g)||[]).length,5);
 for(const t of [0,1.4,9.5,10.2,10.7,14])assert.ok(scene(movie(t)).includes(`data-material="earth" width="960" height="540" fill="${EARTH}"`));
 assert.equal((late.match(/data-character="family-/g)||[]).length,0);
 assert.ok(!late.includes('M30 430'));
 assert.ok(late.includes('href="#front"'));
 assert.ok(late.includes('data-place="root-pocket"'));
 assert.ok(late.includes('data-event="footprint"'));
});
test('sound word precedes cracks; family reacts before the descending roof occludes it',()=>{
 assert.ok(scene(movie(1.4)).includes('THUMP!'));
 assert.ok(!scene({...movie(1.4),showWords:false}).includes('THUMP!'));
 assert.equal((scene(movie(1.4)).match(/href="#sleepy"/g)||[]).length,4);
 assert.ok(scene(movie(3)).includes('data-event="cracks"'));
 assert.equal((scene(movie(9.5)).match(/href="#surprised"/g)||[]).length,4);
 assert.ok(movie(9.5).collapse===0 && movie(10.2).collapse>0 && movie(10.2).collapse<1);
 const falling=scene(movie(10.2));
 assert.ok(falling.indexOf('data-character="family-0"')<falling.indexOf('data-event="falling-roof"'));
 assert.ok(falling.indexOf('data-event="falling-roof"')<falling.indexOf('data-place="root-pocket"'));
});
