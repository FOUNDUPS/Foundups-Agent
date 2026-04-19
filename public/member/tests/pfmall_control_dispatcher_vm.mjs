/**
 * Runtime checks for pfmall-control-dispatcher.js (Node vm).
 * Run: node public/member/tests/pfmall_control_dispatcher_vm.mjs
 *
 * Layer 1 coverage:
 *   - dispatcher loads and exposes window.pfmallControlDispatcher
 *   - inspect_state returns truthful state (reads only what APIs expose)
 *   - inspect_state reports null for missing APIs (no fabrication)
 *   - invalid / unknown commands rejected with error shape
 *   - pfmall_command routed via postMessage produces pfmall_response
 *   - disallowed origin ignored
 *   - not_implemented layer 2+ commands return error (stable contract surface)
 *   - emitEvent broadcasts pfmall_event to registered listeners
 *
 * @see test_pfmall_control_dispatcher.py (optional pytest wrapper)
 */
import { readFileSync } from 'fs';
import { runInNewContext } from 'vm';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = dirname(__dirname);
const JS = readFileSync(join(ROOT, 'js', 'pfmall-control-dispatcher.js'), 'utf8');

function createSandbox(opts) {
  opts = opts || {};
  const sandbox = {
    console,
    location: { origin: 'http://127.0.0.1:5500', search: '' },
    document: { readyState: 'complete', addEventListener() {} },
    CustomEvent: function(name, init) {
      this.type = name;
      this.detail = (init && init.detail) || null;
    }
  };
  sandbox.addEventListener = function(evt, handler) {
    if (evt === 'message') sandbox._messageHandler = handler;
  };
  sandbox.dispatchEvent = function(ev) {
    sandbox._lastCustomEvent = ev;
    return true;
  };
  sandbox.window = sandbox;

  if (opts.tileField) sandbox.mallTileField = opts.tileField;
  if (opts.planes) sandbox.mallPlanes = opts.planes;
  if (opts.videoPlayer) sandbox.mallVideoPlayer = opts.videoPlayer;

  return sandbox;
}

function loadDispatcher(sandbox) {
  runInNewContext(JS, sandbox, { filename: 'pfmall-control-dispatcher.js' });
  if (!sandbox.pfmallControlDispatcher) {
    throw new Error('pfmallControlDispatcher not exposed');
  }
}

function assert(cond, msg) {
  if (!cond) throw new Error(msg || 'assert failed');
}

function makeTileFieldStub(overrides) {
  overrides = overrides || {};
  return Object.assign({
    getDensity: function() { return '3x5'; },
    getDevicePolicy: function() {
      return { allowed: ['3x4', '3x5'], deviceClass: 'phone', reason: 'Phone (test)' };
    },
    isExpanded: function() { return false; },
    getExpandedIndex: function() { return null; },
    getPlayingIndex: function() { return null; },
    getMotionMode: function() { return 'snap'; },
    getProjection: function() { return 'default'; },
    getFieldScope: function() { return { type: null, query: null }; },
    getCatalog: function() { return [{ foundup_id: 'a' }, { foundup_id: 'b' }]; }
  }, overrides);
}

async function run() {
  // 1) Dispatcher loads and exposes stable API surface.
  {
    const sb = createSandbox();
    loadDispatcher(sb);
    const d = sb.pfmallControlDispatcher;
    assert(typeof d.dispatch === 'function', 'dispatch is function');
    assert(typeof d.emitEvent === 'function', 'emitEvent is function');
    assert(typeof d.registerEventListener === 'function', 'registerEventListener is function');
    const cfg = d.getConfig();
    // Stable contract surface — all 7 commands present even before full impl.
    const expected = ['inspect_state', 'set_layout', 'load_videos', 'play_tile',
                      'expand_tile', 'collapse_tile', 'reset_session'];
    for (const cmd of expected) {
      assert(cfg.commands.indexOf(cmd) !== -1, 'command registered: ' + cmd);
    }
    // Known events surfaced.
    assert(cfg.knownEvents.indexOf('layout_denied') !== -1, 'layout_denied known');
    assert(cfg.knownEvents.indexOf('video_loaded') !== -1, 'video_loaded known');
    assert(cfg.knownEvents.indexOf('state_changed') !== -1, 'state_changed known');
  }

  // 2) inspect_state returns truthful state from underlying APIs.
  {
    const sb = createSandbox({
      tileField: makeTileFieldStub({
        getDensity: function() { return '6x3'; },
        getDevicePolicy: function() {
          return { allowed: ['3x4', '3x5', '4x6', '5x8', '6x3'], deviceClass: 'desktop', reason: 'Desktop' };
        },
        isExpanded: function() { return true; },
        getExpandedIndex: function() { return 2; }
      }),
      planes: { isOpen: function() { return true; }, getActiveIndex: function() { return 2; } },
      videoPlayer: {
        isOpen: function() { return false; },
        getFoundUpId: function() { return null; },
        getCurrentIndex: function() { return -1; },
        getQueueLength: function() { return 0; }
      }
    });
    loadDispatcher(sb);
    const res = sb.pfmallControlDispatcher.dispatch('inspect_state', {});
    assert(res.status === 'ok', 'inspect_state ok');
    assert(res.result.tile_field.density === '6x3', 'density read truthfully');
    assert(res.result.tile_field.device_policy.deviceClass === 'desktop', 'device policy read');
    assert(res.result.tile_field.expanded === true, 'expanded read');
    assert(res.result.tile_field.expanded_index === 2, 'expanded index read');
    assert(res.result.tile_field.catalog_length === 2, 'catalog length read from getCatalog()');
    assert(res.result.planes.open === true, 'planes.open read');
    assert(res.result.video_player.open === false, 'video_player.open read');
    assert(res.result.session.override_active === false, 'session override defaults false');
  }

  // 3) inspect_state reports null for missing APIs — no fabrication.
  {
    const sb = createSandbox();  // no tileField, no planes, no videoPlayer
    loadDispatcher(sb);
    const res = sb.pfmallControlDispatcher.dispatch('inspect_state', {});
    assert(res.status === 'ok', 'inspect_state still ok with no APIs');
    assert(res.result.tile_field === null, 'tile_field null when API missing');
    assert(res.result.planes === null, 'planes null when API missing');
    assert(res.result.video_player === null, 'video_player null when API missing');
    // truth-signal: session block is always present, since it is dispatcher-local.
    assert(res.result.session && typeof res.result.session === 'object', 'session always present');
  }

  // 4) inspect_state returns null for individual missing methods on a present API.
  {
    const sb = createSandbox({
      tileField: { getDensity: function() { return '3x5'; } }  // only one method
    });
    loadDispatcher(sb);
    const res = sb.pfmallControlDispatcher.dispatch('inspect_state', {});
    assert(res.result.tile_field.density === '3x5', 'partial API density read');
    assert(res.result.tile_field.device_policy === null, 'missing method reported null');
    assert(res.result.tile_field.expanded === null, 'missing isExpanded reported null');
  }

  // 5) inspect_state swallows handler exceptions into null (no leak, no crash).
  {
    const sb = createSandbox({
      tileField: makeTileFieldStub({
        getDensity: function() { throw new Error('boom'); }
      })
    });
    loadDispatcher(sb);
    const res = sb.pfmallControlDispatcher.dispatch('inspect_state', {});
    assert(res.status === 'ok', 'inspect_state ok even when a reader throws');
    assert(res.result.tile_field.density === null, 'thrown reader -> null');
    // other readers unaffected
    assert(res.result.tile_field.motion_mode === 'snap', 'other readers still work');
  }

  // 6) Unknown command rejected with structured error.
  {
    const sb = createSandbox();
    loadDispatcher(sb);
    const res = sb.pfmallControlDispatcher.dispatch('nonsense_command', {});
    assert(res.status === 'error', 'unknown command is error');
    assert(res.error.code === 'unknown_command', 'error code is unknown_command');
    assert(res.error.message.indexOf('nonsense_command') !== -1, 'error names the command');
  }

  // 7) Invalid command shape rejected.
  {
    const sb = createSandbox();
    loadDispatcher(sb);
    const res1 = sb.pfmallControlDispatcher.dispatch('', {});
    assert(res1.status === 'error' && res1.error.code === 'invalid_command', 'empty command rejected');
    const res2 = sb.pfmallControlDispatcher.dispatch(null, {});
    assert(res2.status === 'error' && res2.error.code === 'invalid_command', 'null command rejected');
  }

  // 8) Layer 2+ commands return not_implemented (stable contract, not crash).
  {
    const sb = createSandbox();
    loadDispatcher(sb);
    const layer2 = ['set_layout', 'load_videos', 'play_tile', 'expand_tile', 'collapse_tile', 'reset_session'];
    for (const cmd of layer2) {
      const res = sb.pfmallControlDispatcher.dispatch(cmd, {});
      assert(res.status === 'error', cmd + ' returns error');
      assert(res.error.code === 'not_implemented', cmd + ' error code is not_implemented');
    }
  }

  // 9) postMessage routing: pfmall_command -> pfmall_response with same request_id.
  {
    const sb = createSandbox({ tileField: makeTileFieldStub() });
    loadDispatcher(sb);
    let replied;
    const source = { postMessage(msg, _origin) { replied = msg; } };
    sb._messageHandler({
      origin: 'http://127.0.0.1:5500',
      source,
      data: {
        type: 'pfmall_command',
        source: 'test_agent',
        target: 'pfmall_control_dispatcher',
        command: 'inspect_state',
        request_id: 'req-42',
        payload: {}
      }
    });
    assert(replied, 'response posted');
    assert(replied.type === 'pfmall_response', 'response type is pfmall_response');
    assert(replied.request_id === 'req-42', 'request_id echoed');
    assert(replied.target === 'test_agent', 'target echoed as original source');
    assert(replied.source === 'pfmall_control_dispatcher', 'source is dispatcher');
    assert(replied.status === 'ok', 'inspect_state over postMessage is ok');
    assert(replied.result && replied.result.tile_field, 'result present');
  }

  // 10) Disallowed origin ignored — no response posted.
  {
    const sb = createSandbox();
    loadDispatcher(sb);
    let replied;
    const source = { postMessage(msg) { replied = msg; } };
    sb._messageHandler({
      origin: 'https://evil.example',
      source,
      data: {
        type: 'pfmall_command',
        command: 'inspect_state',
        request_id: 'req-evil'
      }
    });
    assert(replied === undefined, 'disallowed origin produces no response');
  }

  // 11) Non-pfmall_command messages ignored.
  {
    const sb = createSandbox();
    loadDispatcher(sb);
    let replied;
    const source = { postMessage(msg) { replied = msg; } };
    sb._messageHandler({
      origin: 'http://127.0.0.1:5500',
      source,
      data: { type: 'agent_request', command: 'inspect_state' }  // wrong envelope type
    });
    assert(replied === undefined, 'non-pfmall_command ignored');
  }

  // 12) emitEvent broadcasts to registered listeners and dispatches CustomEvent.
  {
    const sb = createSandbox();
    loadDispatcher(sb);
    const received = [];
    sb.pfmallControlDispatcher.registerEventListener({
      postMessage(msg) { received.push(msg); }
    }, { origin: '*' });
    const envelope = sb.pfmallControlDispatcher.emitEvent('state_changed', { foo: 'bar' });
    assert(envelope.type === 'pfmall_event', 'envelope type');
    assert(envelope.event === 'state_changed', 'event name');
    assert(envelope.payload.foo === 'bar', 'payload passed through');
    assert(received.length === 1, 'listener received one event');
    assert(received[0].event === 'state_changed', 'listener got state_changed');
    assert(sb._lastCustomEvent && sb._lastCustomEvent.type === 'pfmall:state_changed',
           'CustomEvent dispatched on window');
  }

  console.log('pfmall_control_dispatcher_vm.mjs: all checks passed');
}

run().catch((e) => {
  console.error(e);
  process.exit(1);
});
