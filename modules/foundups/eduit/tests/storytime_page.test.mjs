import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';

test('episode puts playable video before the idle game and keeps iteration links', async () => {
  const html = await readFile(new URL('../../../../public/eduit/storytime/index.html', import.meta.url), 'utf8');
  assert.ok(html.indexOf('id="episode-video"') < html.indexOf('id="game-panel"'));
  assert.match(html, /id="episode-video" controls playsinline preload="metadata"/);
  assert.doesNotMatch(html, /\bautoplay\b/);
  assert.match(html, /href="\/review\/"/);
  assert.match(html, /More stories coming/);
  assert.match(html, /id="revision">__STORYTIME_REVISION__/);
});

test('page coordinates video, game, hidden pages, expansion, audio and disposal', async () => {
  const original = new Map();
  const globals = value => {
    for (const [key, entry] of Object.entries(value)) {
      original.set(key, Object.getOwnPropertyDescriptor(globalThis, key));
      Object.defineProperty(globalThis, key, {value: entry, configurable: true, writable: true});
    }
  };
  const document = new EventTarget(), window = new EventTarget();
  let frame, frameNumber = 0, now = 1000, audio, cancelled = false;
  class Element extends EventTarget {
    constructor(id) {
      super(); this.id = id; this.textContent = ''; this.innerHTML = ''; this.hidden = false;
      this.checked = false; this.disabled = false; this.paused = true; this.currentTime = 0;
      this.attributes = new Map(); const classes = new Set();
      this.classList = {add: name => classes.add(name), remove: name => classes.delete(name), contains: name => classes.has(name)};
    }
    setAttribute(name, value) { this.attributes.set(name, value); }
    focus() { document.activeElement = this; }
    pause() { this.paused = true; }
    play() { this.paused = false; this.dispatchEvent(new Event('play')); return Promise.resolve(); }
    querySelector() { return source; }
    querySelectorAll() { return []; }
    getClientRects() { return [{}]; }
  }
  const elements = new Map(), source = new Element('source');
  const get = id => { if (!elements.has(id)) elements.set(id, new Element(id)); return elements.get(id); };
  document.getElementById = get; document.hidden = false;
  document.body = {style: {overflow: ''}}; document.activeElement = get('start');
  get('revision').textContent = '__STORYTIME_REVISION__';
  class Audio {
    constructor() { audio = this; this.state = 'suspended'; this.currentTime = 0; this.suspensions = 0; this.stops = 0; }
    resume() { this.state = 'running'; return Promise.resolve(); }
    suspend() { this.state = 'suspended'; this.suspensions++; return Promise.resolve(); }
    close() { this.state = 'closed'; return Promise.resolve(); }
    createOscillator() { return {frequency: {}, connect: gain => gain, start() {}, stop: () => this.stops++, disconnect() {}}; }
    createGain() { return {gain: {setValueAtTime() {}, exponentialRampToValueAtTime() {}}, connect() {}, disconnect() {}}; }
  }
  globals({document, window, AudioContext: Audio, matchMedia: () => ({matches: false}),
    requestAnimationFrame: callback => { frame = callback; return ++frameNumber; },
    cancelAnimationFrame: () => { cancelled = true; },
  });
  const click = id => get(id).dispatchEvent(new Event('click'));
  const frames = count => { for (let i = 0; i < count; i++) { now += 100; frame(now); } };
  try {
    const {storyTimeActivity: game, episodeContext} = await import('../../../../public/eduit/storytime/game.js?page-test');
    const video = get('episode-video');
    assert.equal(episodeContext.revision, 'source-preview');
    await video.play(); frames(60);
    assert.equal(game.snapshot().phase, 'ready');
    assert.equal(game.snapshot().elapsed, 0);
    get('sound').checked = true;
    click('start'); frames(5);
    assert.equal(video.paused, true);
    assert.equal(game.snapshot().phase, 'wake');
    click('pause');
    const remaining = game.snapshot().elapsed;
    frames(60); click('wake');
    assert.equal(game.snapshot().phase, 'wake');
    assert.equal(game.snapshot().elapsed, remaining);
    assert.ok(audio.suspensions > 0); assert.ok(audio.stops > 0);
    click('pause');
    await video.play();
    assert.equal(game.snapshot().paused, true, 'playing video pauses active game');
    click('pause');
    assert.equal(video.paused, true, 'resuming game pauses video');
    document.hidden = true; document.dispatchEvent(new Event('visibilitychange'));
    document.hidden = false; document.dispatchEvent(new Event('visibilitychange')); frames(60);
    assert.equal(game.snapshot().elapsed, remaining);
    assert.equal(game.snapshot().paused, true, 'returning from hidden waits for Resume');
    click('pause'); click('expand-game');
    assert.equal(game.snapshot().paused, true, 'view transitions pause cue timer');
    assert.equal(get('back-game').hidden, false);
    assert.equal(document.body.style.overflow, 'hidden');
    click('back-game');
    assert.equal(document.body.style.overflow, '');
    assert.equal(get('expand-game').hidden, false);
    click('pause');
    let completions = 0;
    get('game-panel').addEventListener('storytime:complete', event => {
      completions++; assert.equal(event.detail.status, 'completed');
      assert.equal(event.detail.episodeId, 'little_shrew_poc_001');
      assert.equal(event.bubbles, false);
    });
    click('wake'); click('root'); frames(70);
    assert.equal(game.snapshot().phase, 'success');
    assert.equal(completions, 1);
    assert.match(get('retry').textContent, /Replay/);
    click('retry');
    get('practice').checked = true; frames(100);
    assert.equal(game.snapshot().phase, 'wake');
    game.reset();
    assert.equal(game.snapshot().phase, 'ready');
    const pagehide = new Event('pagehide'); pagehide.persisted = false;
    window.dispatchEvent(pagehide);
    assert.equal(game.snapshot().disposed, true);
    assert.equal(audio.state, 'closed'); assert.equal(cancelled, true);
    click('start');
    assert.equal(game.snapshot().phase, 'ready');
  } finally {
    for (const [key, descriptor] of original) {
      if (descriptor) Object.defineProperty(globalThis, key, descriptor); else delete globalThis[key];
    }
  }
});
