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

  // 8) Layer 3+ commands return not_implemented (stable contract, not crash).
  //    set_layout moved out of this list in Layer 2 — it is now implemented.
  {
    const sb = createSandbox();
    loadDispatcher(sb);
    const notYet = ['load_videos', 'play_tile', 'expand_tile', 'collapse_tile', 'reset_session'];
    for (const cmd of notYet) {
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

  // ==========================================================================
  // Layer 2: set_layout + device policy denial + layout_denied / layout_applied
  // ==========================================================================

  // L2 test helper: tile field that mirrors mall-tile-field.js requestDensity
  // contract — phone denies desktop presets, desktop accepts.
  function makeTileFieldWithPolicy(deviceClass) {
    const allowedByClass = {
      phone: ['3x4', '3x5'],
      tablet: ['3x4', '3x5', '4x6', '5x8'],
      desktop: ['3x4', '3x5', '4x6', '5x8', '6x3', '8x2', '8x5', '10x6', '12x3', '12x8', '15x4']
    };
    const allowed = allowedByClass[deviceClass] || allowedByClass.phone;
    let currentDensity = allowed[0];
    const calls = [];
    return {
      _calls: calls,
      getDensity: function() { return currentDensity; },
      getDevicePolicy: function() {
        return { allowed: allowed.slice(), deviceClass: deviceClass, reason: deviceClass + ' (test)' };
      },
      requestDensity: function(preset, options) {
        calls.push({ preset: preset, source: (options && options.source) || 'unknown' });
        if (allowed.indexOf(preset) === -1) {
          return {
            applied: false,
            preset: preset,
            reason: 'Density ' + preset + ' not allowed for ' + deviceClass + '. Allowed: ' + allowed.join(', ')
          };
        }
        currentDensity = preset;
        return { applied: true, preset: preset, deviceClass: deviceClass, source: (options && options.source) };
      }
    };
  }

  // 13) set_layout denies a phone requesting a desktop preset and emits layout_denied.
  {
    const sb = createSandbox({ tileField: makeTileFieldWithPolicy('phone') });
    loadDispatcher(sb);
    const events = [];
    sb.pfmallControlDispatcher.registerEventListener({ postMessage(msg) { events.push(msg); } }, { origin: '*' });

    const res = sb.pfmallControlDispatcher.dispatch('set_layout', { preset: '6x3', source: 'rogue_agent' });
    assert(res.status === 'denied', 'phone + 6x3 -> status denied');
    assert(res.result.applied === false, 'applied false on denial');
    assert(res.result.preset === '6x3', 'denial echoes requested preset');
    assert(res.result.device_class === 'phone', 'denial names device class');
    assert(Array.isArray(res.result.allowed), 'denial lists allowed presets');
    assert(res.result.allowed.indexOf('6x3') === -1, 'denied preset not in allowed list');
    assert(typeof res.result.reason === 'string' && res.result.reason.length > 0, 'denial has reason string');

    // layout_denied event emitted with same detail
    const denied = events.filter(e => e.event === 'layout_denied');
    assert(denied.length === 1, 'one layout_denied event emitted');
    assert(denied[0].payload.preset === '6x3', 'event preset matches');
    assert(denied[0].payload.source === 'rogue_agent', 'event preserves source');
    assert(denied[0].payload.device_class === 'phone', 'event has device_class');
    assert(Array.isArray(denied[0].payload.allowed), 'event lists allowed');

    // no layout_applied or state_changed fired on denial
    assert(events.filter(e => e.event === 'layout_applied').length === 0, 'no layout_applied on denial');
    assert(events.filter(e => e.event === 'state_changed').length === 0, 'no state_changed on denial');
  }

  // 14) set_layout applies a desktop preset on a desktop, emits layout_applied + state_changed.
  {
    const tf = makeTileFieldWithPolicy('desktop');
    const sb = createSandbox({ tileField: tf });
    loadDispatcher(sb);
    const events = [];
    sb.pfmallControlDispatcher.registerEventListener({ postMessage(msg) { events.push(msg); } }, { origin: '*' });

    const res = sb.pfmallControlDispatcher.dispatch('set_layout', { preset: '6x3', source: 'red_dog' });
    assert(res.status === 'ok', 'desktop + 6x3 -> status ok');
    assert(res.result.applied === true, 'applied true');
    assert(res.result.preset === '6x3', 'preset echoed');
    assert(res.result.source === 'red_dog', 'source echoed');
    assert(res.result.device_class === 'desktop', 'device_class reported');

    // requestDensity was called once with the correct payload
    assert(tf._calls.length === 1, 'requestDensity called once');
    assert(tf._calls[0].preset === '6x3', 'requestDensity got preset');
    assert(tf._calls[0].source === 'red_dog', 'requestDensity got source');

    // Both layout_applied and state_changed emitted on success
    const applied = events.filter(e => e.event === 'layout_applied');
    const stateCh = events.filter(e => e.event === 'state_changed');
    assert(applied.length === 1, 'one layout_applied');
    assert(applied[0].payload.preset === '6x3', 'applied event preset');
    assert(applied[0].payload.source === 'red_dog', 'applied event source');
    assert(applied[0].payload.device_class === 'desktop', 'applied event device_class');
    assert(stateCh.length === 1, 'one state_changed');
    assert(stateCh[0].payload.change === 'layout', 'state_changed change=layout');
    assert(stateCh[0].payload.preset === '6x3', 'state_changed preset');

    // No layout_denied on success
    assert(events.filter(e => e.event === 'layout_denied').length === 0, 'no layout_denied on success');

    // Underlying state reflects change
    assert(tf.getDensity() === '6x3', 'density mutated by requestDensity');
  }

  // 15) set_layout with missing / non-string preset returns invalid_payload error.
  {
    const sb = createSandbox({ tileField: makeTileFieldWithPolicy('desktop') });
    loadDispatcher(sb);
    const cases = [
      [{ source: 'x' }, 'missing preset'],
      [{ preset: '', source: 'x' }, 'empty preset'],
      [{ preset: null }, 'null preset'],
      [{ preset: 123 }, 'numeric preset']
    ];
    for (const [payload, label] of cases) {
      const res = sb.pfmallControlDispatcher.dispatch('set_layout', payload);
      assert(res.status === 'error', label + ' -> error');
      assert(res.error.code === 'invalid_payload', label + ' -> invalid_payload code');
    }
  }

  // 16) set_layout with no mallTileField returns api_unavailable error.
  {
    const sb = createSandbox();  // no tileField
    loadDispatcher(sb);
    const res = sb.pfmallControlDispatcher.dispatch('set_layout', { preset: '3x5' });
    assert(res.status === 'error', 'no tileField -> error');
    assert(res.error.code === 'api_unavailable', 'error code api_unavailable');
  }

  // 17) set_layout with mallTileField missing requestDensity returns api_unavailable.
  {
    const sb = createSandbox({
      tileField: { getDensity: function() { return '3x5'; } }  // lacks requestDensity
    });
    loadDispatcher(sb);
    const res = sb.pfmallControlDispatcher.dispatch('set_layout', { preset: '3x5' });
    assert(res.status === 'error', 'partial tileField -> error');
    assert(res.error.code === 'api_unavailable', 'code api_unavailable for partial API');
  }

  // 18) set_layout with requestDensity returning malformed outcome -> runtime_failure.
  {
    const sb = createSandbox({
      tileField: {
        getDevicePolicy: function() { return { allowed: ['3x5'], deviceClass: 'phone', reason: 't' }; },
        requestDensity: function() { return { /* no applied field */ }; }
      }
    });
    loadDispatcher(sb);
    const res = sb.pfmallControlDispatcher.dispatch('set_layout', { preset: '3x5' });
    assert(res.status === 'error', 'malformed outcome -> error');
    assert(res.error.code === 'runtime_failure', 'code runtime_failure');
  }

  // 19) set_layout via postMessage routes denial correctly with request_id.
  {
    const sb = createSandbox({ tileField: makeTileFieldWithPolicy('phone') });
    loadDispatcher(sb);
    let replied;
    const source = { postMessage(msg) { replied = msg; } };
    sb._messageHandler({
      origin: 'http://127.0.0.1:5500',
      source,
      data: {
        type: 'pfmall_command',
        source: 'native_phone_agent',
        command: 'set_layout',
        request_id: 'req-deny-1',
        payload: { preset: '6x3', source: 'native_phone_agent' }
      }
    });
    assert(replied && replied.type === 'pfmall_response', 'response envelope');
    assert(replied.status === 'denied', 'postMessage routes denial status');
    assert(replied.request_id === 'req-deny-1', 'request_id echoed');
    assert(replied.target === 'native_phone_agent', 'target echoed');
    assert(replied.result.preset === '6x3', 'result preset');
    assert(replied.error === undefined, 'denied status has no error field');
  }

  // 20) Layer 1 contracts still intact after Layer 2 lands.
  {
    const sb = createSandbox({ tileField: makeTileFieldWithPolicy('desktop') });
    loadDispatcher(sb);
    // inspect_state unchanged
    const ins = sb.pfmallControlDispatcher.dispatch('inspect_state', {});
    assert(ins.status === 'ok', 'inspect_state still ok');
    assert(ins.result.tile_field.device_policy.deviceClass === 'desktop', 'inspect reads desktop policy');
    // unknown command unchanged
    const unk = sb.pfmallControlDispatcher.dispatch('not_a_command', {});
    assert(unk.status === 'error' && unk.error.code === 'unknown_command', 'unknown still error');
    // Layer 3+ still not_implemented (unchanged)
    const ni = sb.pfmallControlDispatcher.dispatch('play_tile', {});
    assert(ni.status === 'error' && ni.error.code === 'not_implemented', 'play_tile still not_implemented');
    // set_layout is now registered as implemented (not not_implemented)
    const impl = sb.pfmallControlDispatcher.dispatch('set_layout', { preset: '3x5' });
    assert(impl.status === 'ok' && impl.error === undefined, 'set_layout no longer not_implemented');
  }

  // 21) Denial event does not fire on invalid_payload / api_unavailable — only on policy denial.
  //     (truth-signal: "policy said no" is different from "you sent garbage or there was no runtime").
  {
    const sb = createSandbox({ tileField: makeTileFieldWithPolicy('phone') });
    loadDispatcher(sb);
    const events = [];
    sb.pfmallControlDispatcher.registerEventListener({ postMessage(msg) { events.push(msg); } }, { origin: '*' });

    sb.pfmallControlDispatcher.dispatch('set_layout', {});  // invalid payload
    sb.pfmallControlDispatcher.dispatch('set_layout', { preset: 'bogus_preset' });  // policy denial

    const denied = events.filter(e => e.event === 'layout_denied');
    assert(denied.length === 1, 'exactly one layout_denied (not fired on invalid_payload)');
    assert(denied[0].payload.preset === 'bogus_preset', 'the one denial is the policy one');
  }

  console.log('pfmall_control_dispatcher_vm.mjs: all checks passed (Layer 1 + Layer 2)');
}

run().catch((e) => {
  console.error(e);
  process.exit(1);
});
