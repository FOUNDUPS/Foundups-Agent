import test from 'node:test';
import assert from 'node:assert/strict';
import {initial,advance} from '../../../../public/eduit/storytime/engine.mjs';
import {movie,scene} from '../../../../public/eduit/storytime/scene.mjs';
import {createStoryActivity} from '../../../../public/eduit/storytime/activity.mjs';
const tick=(s,n,practice=false)=>{for(let i=0;i<n;i++)s=advance(s,'tick',.1,practice);return s;};
test('two ordered taps lead to shelter; wrong target does not advance',()=>{let s=advance(initial(),'start');assert.equal(advance(s,'root').phase,'wake');s=advance(s,'shrew');assert.equal(s.phase,'root');s=advance(s,'root');s=tick(s,25);assert.equal(s.phase,'stomp');s=tick(s,31);assert.equal(s.phase,'success');});
test('both missed cues allow a clean retry',()=>{for(const cue of ['wake','root']){const s=tick({phase:cue,elapsed:0},41);assert.equal(s.phase,'retry');assert.deepEqual(advance(s,'retry'),{phase:'wake',elapsed:0});}});
test('practice waits indefinitely and large clock jumps cannot skip a cue',()=>{assert.equal(tick({phase:'wake',elapsed:0},200,true).phase,'wake');assert.equal(advance({phase:'wake',elapsed:0},'tick',100).elapsed,.1);});
test('movie and game share five rigs, an intact pocket and no floor after stomp',()=>{const early=scene(movie(0)),late=scene(movie(14));assert.equal((early.match(/href="#sleepy"/g)||[]).length,5);assert.ok(late.includes('opacity="0"'));assert.ok(late.includes('href="#surprised"'));assert.ok(late.includes('M740 430'));assert.ok(late.includes('<rect width="960" height="540" fill="#9C724F" opacity="1"/>')); });

test('mounted game remains idle for an entire movie until explicit Play', () => {
  const game = createStoryActivity();
  assert.equal(game.start().phase, 'ready', 'unmounted activity does not start');
  game.mount();
  for (let i = 0; i < 200; i++) game.tick(.1);
  assert.equal(game.snapshot().phase, 'ready');
  assert.equal(game.snapshot().clock, 0);
  assert.equal(game.snapshot().elapsed, 0);
  assert.equal(game.start().phase, 'wake');
});

test('pause blocks both timer and cue actions; resume preserves remaining cue time', () => {
  const game = createStoryActivity();
  game.mount(); game.start();
  for (let i = 0; i < 12; i++) game.tick(.1);
  const elapsed = game.pause().elapsed;
  for (let i = 0; i < 100; i++) game.tick(.1);
  assert.equal(game.act('shrew').phase, 'wake');
  assert.equal(game.snapshot().elapsed, elapsed);
  game.resume();
  assert.equal(game.act('shrew').phase, 'root');
  game.pause();
  assert.equal(game.act('root').phase, 'root');
  game.resume();
  assert.equal(game.act('root').phase, 'walk');
});

test('untimed practice, retry and reset retain the existing two-cue engine', () => {
  const game = createStoryActivity();
  game.mount(); game.start();
  for (let i = 0; i < 90; i++) game.tick(.1, true);
  assert.equal(game.snapshot().phase, 'wake');
  game.tick(.1, false);
  assert.equal(game.snapshot().phase, 'retry');
  assert.equal(game.retry().phase, 'wake');
  assert.equal(game.snapshot().clock, 0);
  game.pause(); game.reset();
  assert.equal(game.snapshot().paused, false);
  assert.equal(game.snapshot().phase, 'ready');
  assert.equal(game.snapshot().elapsed, 0);
});

test('completion is bounded to one reference-only result per successful attempt', () => {
  const completions = [], context = {episodeId: 'little_shrew_poc_001', revision: 'test', locale: 'en'};
  const game = createStoryActivity({context, onComplete: result => completions.push(result)});
  context.episodeId = 'changed-outside';
  game.mount();
  const win = () => {
    game.start(); game.act('shrew'); game.act('root');
    for (let i = 0; i < 70; i++) game.tick(.1);
  };
  win();
  assert.equal(game.snapshot().phase, 'success');
  assert.deepEqual(completions, [{episodeId: 'little_shrew_poc_001', revision: 'test', locale: 'en', status: 'completed'}]);
  assert.ok(Object.isFrozen(completions[0]));
  for (let i = 0; i < 100; i++) game.tick(.1);
  game.start(); game.act('root');
  assert.equal(completions.length, 1);
  game.reset(); win();
  assert.equal(completions.length, 2);
});

test('disposed activity releases its mount and cannot restart or complete', () => {
  let completions = 0;
  const game = createStoryActivity({onComplete: () => completions++});
  game.mount(); game.start();
  const disposed = game.dispose();
  assert.equal(disposed.mounted, false);
  assert.equal(disposed.disposed, true);
  game.mount(); game.reset(); game.start(); game.resume(); game.act('shrew');
  assert.deepEqual(game.tick(.1), disposed);
  assert.equal(completions, 0);
});

test('invalid or suspended clock increments cannot bypass cue windows', () => {
  const game = createStoryActivity();
  game.mount(); game.start();
  game.tick(Number.NaN); game.tick(Infinity); game.tick(-1);
  assert.equal(game.snapshot().elapsed, 0);
  assert.equal(game.tick(100).elapsed, .1);
});
