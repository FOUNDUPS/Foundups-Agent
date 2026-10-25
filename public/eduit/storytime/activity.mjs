import {initial, advance} from './engine.mjs';

const active = phase => ['wake', 'root', 'walk', 'stomp'].includes(phase);

// A local adapter around the existing engine. No storage, transport or permissions.
export function createStoryActivity({context = {}, onComplete = () => {}} = {}) {
  const references = Object.freeze({...context});
  let state = initial(), mounted = false, paused = false, disposed = false;
  let clock = 0, completed = false;
  const snapshot = () => Object.freeze({
    ...state, mounted, paused, disposed, clock, context: references,
  });
  const enabled = () => mounted && !disposed;

  function transition(event, dt = 0, practice = false) {
    state = advance(state, event, dt, practice);
    if (state.phase === 'success' && !completed) {
      completed = true;
      // One bounded completion per attempt, with references only; no tap history.
      onComplete(Object.freeze({...references, status: 'completed'}));
    }
    return snapshot();
  }

  return Object.freeze({
    mount() { if (!disposed) mounted = true; return snapshot(); },
    start() {
      if (enabled() && state.phase === 'ready') {
        paused = false;
        return transition('start');
      }
      return snapshot();
    },
    retry() {
      if (enabled() && ['retry', 'success'].includes(state.phase)) {
        paused = false; clock = 0; completed = false;
        return transition('retry');
      }
      return snapshot();
    },
    pause() { if (enabled() && active(state.phase)) paused = true; return snapshot(); },
    resume() { if (enabled()) paused = false; return snapshot(); },
    reset() {
      if (enabled()) { state = initial(); clock = 0; paused = false; completed = false; }
      return snapshot();
    },
    act(event) {
      return enabled() && !paused && ['shrew', 'root'].includes(event)
        ? transition(event) : snapshot();
    },
    tick(dt, practice = false) {
      if (enabled() && !paused && active(state.phase) && Number.isFinite(dt)) {
        const step = Math.max(0, Math.min(dt, .1));
        clock += step;
        return transition('tick', step, practice);
      }
      return snapshot();
    },
    dispose() { mounted = false; disposed = true; paused = true; return snapshot(); },
    snapshot,
  });
}
