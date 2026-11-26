// Shared current-tab projection of observed UI events. No persistence, polling,
// network, microphone, model, backend worker or security-audit authority.
const owners = new WeakMap();
const eventLabels = Object.freeze({
  mallVideoPlayback: 'Playback', videoPlayerOpen: 'Video opened',
  videoPlayerClose: 'Video closed', videoPlayerModeChange: 'View changed',
  videoPlayerTuck: 'Player tucked', videoPlayerSave: 'Save changed',
  videoPlayerDismiss: 'Video dismissed'
});
const states = new Set(['loading', 'ready', 'starting', 'playing', 'paused', 'ended',
  'unavailable', 'embedding-disabled', 'configuration', 'playback-error',
  'client-identification', 'autoplay-blocked', 'timeout', 'continuity-unavailable',
  'provider-state', 'provider-unknown', 'manual-play', 'unsupported']);

function field(value, key) {
  if (!value || typeof value !== 'object') return undefined;
  const descriptor = Object.getOwnPropertyDescriptor(value, key);
  return descriptor && Object.prototype.hasOwnProperty.call(descriptor, 'value') ? descriptor.value : undefined;
}

export function createLocalActivityMonitor(view) {
  if (owners.has(view)) return owners.get(view);
  let enabled = false, sequence = 0, entries = [], lastPlayback = '';
  const subscribers = new Set();
  const read = () => ({ enabled, entries: entries.map(entry => ({ ...entry })) });
  const notify = () => subscribers.forEach(callback => { try { callback(read()); } catch { /* Isolate consumers. */ } });
  function append(type, detail) {
    const entry = { sequence: ++sequence, time: Date.now(), action: eventLabels[type] };
    const videoId = field(detail, 'videoId');
    if (typeof videoId === 'string' && /^[A-Za-z0-9_-]{11}$/.test(videoId)) entry.videoId = videoId;
    const state = field(detail, 'state');
    if (states.has(state)) entry.state = state;
    const mode = field(detail, 'mode');
    if (['floating', 'wikitube', 'full-video', 'theater', 'inline', 'mall', 'closed'].includes(mode)) entry.mode = mode;
    const tucked = field(detail, 'tucked');
    if (typeof tucked === 'boolean') entry.tucked = tucked;
    const code = field(detail, 'code');
    if ([2, 5, 100, 101, 150, 153].includes(code)) entry.code = code;
    const saved = field(detail, 'saved');
    if (typeof saved === 'boolean') entry.saved = saved;
    if (type === 'mallVideoPlayback') {
      const identity = [entry.videoId, entry.state, entry.mode, entry.tucked, entry.code].join(':');
      if (identity === lastPlayback) { sequence--; return; }
      lastPlayback = identity;
    }
    entries.push(entry);
    if (entries.length > 100) entries.shift();
    notify();
  }
  const receive = event => {
    if (!enabled || !Object.prototype.hasOwnProperty.call(eventLabels, event.type)) return;
    try { append(event.type, event.detail); } catch { /* Do not serialize arbitrary event data. */ }
  };
  function setEnabled(next) {
    next = next === true;
    if (next === enabled) return;
    enabled = next;
    Object.keys(eventLabels).forEach(name => view[enabled ? 'addEventListener' : 'removeEventListener'](name, receive));
    if (enabled) {
      lastPlayback = '';
      try {
        const snapshot = view.mallVideoPlayer?.getPlaybackSnapshot?.();
        if (snapshot) append('mallVideoPlayback', snapshot);
      } catch { /* A missing provider is not an execution result. */ }
    }
    notify();
  }
  const api = {
    getSnapshot: read, setEnabled,
    clear() { entries = []; lastPlayback = ''; notify(); },
    subscribe(callback) { subscribers.add(callback); callback(read()); return () => subscribers.delete(callback); }
  };
  view.addEventListener('pagehide', () => setEnabled(false));
  owners.set(view, api);
  return api;
}

export function mountLocalActivityView(container, monitor) {
  const doc = container.ownerDocument;
  const status = doc.createElement('p');
  status.textContent = 'Activity in this tab. History is kept only for this visit.';
  const list = doc.createElement('ol');
  list.className = 'mall-daemon-entries';
  list.setAttribute('aria-label', 'Observed tab activity');
  const empty = doc.createElement('p');
  const clear = doc.createElement('button');
  clear.type = 'button'; clear.textContent = 'Clear activity';
  clear.addEventListener('click', () => monitor.clear());
  container.append(status, empty, list, clear);
  const render = snapshot => {
    if (!container.isConnected) return;
    const dialog = container.closest('dialog');
    if (dialog && !dialog.open) return;
    status.textContent = snapshot.enabled ? 'Monitoring activity in this tab. History is kept only for this visit.' : 'Monitoring is off. History is kept only for this visit.';
    empty.textContent = snapshot.entries.length ? '' : snapshot.enabled ? 'Waiting for activity.' : 'Monitoring is off.';
    list.replaceChildren();
    snapshot.entries.slice().reverse().forEach(entry => {
      const row = doc.createElement('li');
      row.textContent = [new Date(entry.time).toLocaleTimeString(), entry.action,
        entry.state, entry.mode, entry.videoId, entry.code === undefined ? '' : 'Error ' + entry.code,
        entry.tucked === undefined ? '' : entry.tucked ? 'Hidden' : 'Visible',
        entry.saved === undefined ? '' : entry.saved ? 'Saved' : 'Unsaved'].filter(Boolean).join(' · ');
      list.append(row);
    });
  };
  const unsubscribe = monitor.subscribe(render);
  return { refresh() { render(monitor.getSnapshot()); }, destroy: unsubscribe };
}
