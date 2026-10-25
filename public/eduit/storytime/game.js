import {createStoryActivity} from './activity.mjs';
import {scene} from './scene.mjs';

const $ = id => document.getElementById(id);
const revision = $('revision');
if (!revision.textContent.trim() || revision.textContent.includes('__STORYTIME_')) revision.textContent = 'source-preview';
export const episodeContext = Object.freeze({
  foundupId: 'eduit', productionFoundupId: 'kids_episodes', publisherId: 'us_story_time',
  collectionId: 'storytime', storyId: 'little_shrew', episodeId: 'little_shrew_poc_001',
  revision: revision.textContent.trim(), locale: 'en',
});
const video = $('episode-video'), stage = $('scene'), wake = $('wake'), root = $('root');
let last = 0, frameId, audio, disposed = false, previousPhase = 'ready', expanded = null;
let originalOverflow = '', returnFocus = null;
const listeners = [];
const tones = new Set();
const listen = (target, event, handler) => {
  target.addEventListener(event, handler);
  listeners.push(() => target.removeEventListener(event, handler));
};
const activity = createStoryActivity({context: episodeContext, onComplete: detail => {
  $('game-panel').dispatchEvent(new CustomEvent('storytime:complete', {detail}));
}});

function suspendAudio() {
  for (const oscillator of tones) { try { oscillator.stop(); } catch { /* Already stopped. */ } oscillator.disconnect(); }
  tones.clear();
  if (audio?.state === 'running') void audio.suspend().catch(() => {});
}
function sound(freq) {
  if (!$('sound').checked || activity.snapshot().paused || document.hidden) return;
  try {
    audio ??= new AudioContext();
    void audio.resume().catch(() => {});
    const oscillator = audio.createOscillator(), gain = audio.createGain();
    tones.add(oscillator);
    oscillator.onended = () => { tones.delete(oscillator); oscillator.disconnect(); gain.disconnect(); };
    oscillator.type = 'sine'; oscillator.frequency.value = freq;
    gain.gain.setValueAtTime(.045, audio.currentTime);
    gain.gain.exponentialRampToValueAtTime(.001, audio.currentTime + .22);
    oscillator.connect(gain).connect(audio.destination);
    oscillator.start(); oscillator.stop(audio.currentTime + .23);
  } catch { /* Audio is optional. */ }
}
function render(focus = false) {
  const state = activity.snapshot(), p = state.phase, e = state.elapsed;
  const text = {ready: 'Press Play when you’re ready. First the shrew, then the root.',
    wake: 'The ground is shaking. Tap the little shrew!', root: 'Now tap the root to find the little pocket.',
    walk: 'Shuffle, shuffle… sniff, sniff!', stomp: 'A big foot presses down…',
    success: 'Safe in the little pocket! You noticed and acted.', retry: 'Try again. First the shrew, then the root.'};
  const message = state.paused ? 'Paused. Press Resume when you’re ready.' : text[p];
  if ($('message').textContent !== message) $('message').textContent = message;
  wake.hidden = p !== 'wake' || state.paused; root.hidden = p !== 'root' || state.paused;
  wake.disabled = state.paused; root.disabled = state.paused;
  $('start').hidden = p !== 'ready';
  $('retry').hidden = !['success', 'retry'].includes(p);
  $('retry').textContent = p === 'success' ? 'Replay game ↻' : 'Try again ↻';
  $('pause').hidden = ['ready', 'success', 'retry'].includes(p);
  $('pause').textContent = state.paused ? 'Resume' : 'Pause';
  $('pause').setAttribute('aria-pressed', String(state.paused));
  const cue = ['wake', 'root'].includes(p);
  $('time').textContent = state.paused ? 'Timer stopped' : p === 'ready' ? 'Timer starts with Play'
    : cue && !$('practice').checked ? Math.max(0, Math.ceil(4 - e)) + ' seconds'
    : $('practice').checked && !['success', 'retry'].includes(p) ? 'Practice · no timer' : '';
  const moving = ['walk', 'stomp', 'success'].includes(p);
  stage.innerHTML = scene({t: state.clock, awake: ['root', 'walk', 'stomp', 'success'].includes(p),
    progress: moving ? (p === 'walk' ? Math.min(e / 1.5, 1) : 1) : 0,
    impact: p === 'stomp' ? Math.min(e / .7, 1) : p === 'success' ? 1 : 0,
    lift: p === 'stomp' ? Math.max(0, (e - 1.5) / 1.3) : p === 'success' ? 1 : 0,
    shake: p === 'wake' && !state.paused && !matchMedia('(prefers-reduced-motion: reduce)').matches});
  if (focus && !state.paused) {
    if (p === 'wake') wake.focus({preventScroll: true});
    if (p === 'root') root.focus({preventScroll: true});
    if (['success', 'retry'].includes(p)) $('retry').focus({preventScroll: true});
  }
  previousPhase = p;
}
function pause() { if (disposed) return; activity.pause(); last = 0; suspendAudio(); render(); }
function resume() { if (document.hidden || disposed) return; video.pause(); activity.resume(); last = 0; render(true); }
function start(retry = false) {
  if (document.hidden || disposed) return;
  video.pause(); last = 0;
  if (retry) activity.retry(); else activity.start();
  sound(440); render(true);
}
listen($('start'), 'click', () => start());
listen($('retry'), 'click', () => start(true));
listen($('pause'), 'click', () => activity.snapshot().paused ? resume() : pause());
for (const [target, event] of [[wake, 'shrew'], [root, 'root']]) listen(target, 'click', () => {
  if (document.hidden || disposed || activity.snapshot().paused) return;
  const before = activity.snapshot().phase;
  activity.act(event);
  if (activity.snapshot().phase !== before) { sound(event === 'root' ? 660 : 440); render(true); }
});
listen($('practice'), 'change', () => render());
listen($('sound'), 'change', () => { if (!$('sound').checked) suspendAudio(); });
listen(video, 'play', pause);
listen(video, 'error', () => { $('video-status').hidden = false; });
listen(video.querySelector('source'), 'error', () => { $('video-status').hidden = false; });
listen($('replay-video'), 'click', () => {
  pause(); video.currentTime = 0;
  void video.play().catch(() => { $('video-status').hidden = false; });
});
listen(document, 'visibilitychange', () => {
  last = 0;
  if (document.hidden) { pause(); video.pause(); }
});

// Same presentation pattern as the Mall player: scoped overlay, explicit Back,
// body scroll lock and cleanup. No second shell or gesture engine is mounted.
function leaveExpanded() {
  if (!expanded) return;
  const name = expanded;
  expanded = null;
  $(name + '-panel').classList.remove('episode-expanded');
  $('expand-' + name).hidden = false;
  $('expand-' + name).setAttribute('aria-expanded', 'false');
  $('back-' + name).hidden = true;
  document.body.style.overflow = originalOverflow;
  if (name === 'game') pause(); else video.pause();
  returnFocus?.focus({preventScroll: true});
}
async function closeExpanded() {
  if (document.fullscreenElement) {
    try { await document.exitFullscreen(); } catch { /* CSS fallback still closes. */ }
  }
  leaveExpanded();
}
async function expand(name) {
  if (disposed || expanded) return;
  expanded = name; returnFocus = document.activeElement;
  originalOverflow = document.body.style.overflow;
  document.body.style.overflow = 'hidden';
  $(name + '-panel').classList.add('episode-expanded');
  $('expand-' + name).hidden = true;
  $('expand-' + name).setAttribute('aria-expanded', 'true');
  $('back-' + name).hidden = false;
  video.pause(); pause();
  $('back-' + name).focus({preventScroll: true});
  try { await $(name + '-panel').requestFullscreen?.(); } catch { /* Scoped overlay works without fullscreen permission. */ }
}
for (const name of ['video', 'game']) {
  listen($('expand-' + name), 'click', () => { void expand(name); });
  listen($('back-' + name), 'click', () => { void closeExpanded(); });
}
listen(document, 'fullscreenchange', () => { if (!document.fullscreenElement) leaveExpanded(); });
listen(document, 'keydown', event => {
  if (event.key === 'Escape' && expanded) { event.preventDefault(); void closeExpanded(); }
  if (event.key === 'Tab' && expanded && !document.fullscreenElement) {
    const controls = [...$(expanded + '-panel').querySelectorAll('button:not([hidden]), input, video')]
      .filter(control => !control.disabled && control.getClientRects().length);
    const first = controls[0], lastControl = controls.at(-1);
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); lastControl?.focus(); }
    else if (!event.shiftKey && document.activeElement === lastControl) { event.preventDefault(); first?.focus(); }
  }
});

function frame(now) {
  if (disposed) return;
  const dt = last ? (now - last) / 1000 : 0; last = now;
  if (!document.hidden) {
    const before = activity.snapshot();
    const after = activity.tick(dt, $('practice').checked);
    if (before.phase !== after.phase && after.phase === 'success') sound(784);
    if (after.clock !== before.clock || after.phase !== previousPhase) render(before.phase !== after.phase);
  }
  frameId = requestAnimationFrame(frame);
}
export const storyTimeActivity = Object.freeze({
  context: episodeContext,
  mount() { return activity.mount(); },
  start() { start(); return activity.snapshot(); },
  pause() { pause(); return activity.snapshot(); },
  resume() { resume(); return activity.snapshot(); },
  reset() {
    if (disposed) return activity.snapshot();
    video.pause(); suspendAudio(); last = 0; activity.reset(); render(); return activity.snapshot();
  },
  snapshot: activity.snapshot,
  dispose() {
    if (disposed) return;
    disposed = true; cancelAnimationFrame(frameId); video.pause();
    activity.dispose(); leaveExpanded(); listeners.splice(0).forEach(remove => remove());
    suspendAudio();
    if (audio) void audio.close().catch(() => {});
    wake.hidden = true; root.hidden = true;
  },
});
listen(window, 'pagehide', event => { if (event.persisted) { pause(); video.pause(); } else storyTimeActivity.dispose(); });
activity.mount(); render(); frameId = requestAnimationFrame(frame);
