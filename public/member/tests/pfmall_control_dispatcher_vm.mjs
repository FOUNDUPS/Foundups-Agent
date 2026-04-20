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
 *   - contract surface stable (all 7 commands registered)
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

  // 8) All 7 commands in the contract are implemented (Layer 4 complete).
  //    No command returns `not_implemented` anymore. This test still guards the
  //    stable contract surface — all commands reject with a structured error
  //    other than `not_implemented` when prerequisites aren't met.
  {
    const sb = createSandbox();  // no tileField, no videoPlayer
    loadDispatcher(sb);
    const commands = ['inspect_state', 'set_layout', 'load_videos', 'play_tile',
                      'expand_tile', 'collapse_tile', 'reset_session'];
    for (const cmd of commands) {
      const res = sb.pfmallControlDispatcher.dispatch(cmd, {});
      // Every response must be a well-formed envelope (status + result|error).
      assert(typeof res.status === 'string', cmd + ' has status');
      if (res.status === 'error') {
        assert(res.error && res.error.code !== 'not_implemented',
               cmd + ' must not be not_implemented (Layer 4 is done)');
      }
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
    // load_videos is implemented (Layer 4): with no mallTileField it returns
    // api_unavailable, not not_implemented. (invalid_payload is checked first —
    // give a valid payload so we exercise the API-check path.)
    const lv = sb.pfmallControlDispatcher.dispatch('load_videos', {
      videos: [{ video_id: 'vid_x' }]
    });
    assert(lv.status === 'error' && lv.error.code === 'api_unavailable',
           'load_videos without API -> api_unavailable (not not_implemented)');
    // set_layout is implemented (Layer 2)
    const impl = sb.pfmallControlDispatcher.dispatch('set_layout', { preset: '3x5' });
    assert(impl.status === 'ok' && impl.error === undefined, 'set_layout still implemented');
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

  // ==========================================================================
  // Layer 3: play_tile / expand_tile / collapse_tile (direct tile control)
  // ==========================================================================

  // Shared helpers for Layer 3: tile field + video player stubs with real state.

  function makeL3TileField(catalog) {
    let expanded = null;
    const expandCalls = [];
    const collapseCalls = [];
    return {
      _expandCalls: expandCalls,
      _collapseCalls: collapseCalls,
      getCatalog: function() { return catalog.slice(); },
      isExpanded: function() { return expanded !== null; },
      getExpandedIndex: function() { return expanded; },
      expandFoundUp: function(idx) {
        expandCalls.push(idx);
        const item = catalog[idx];
        if (!item || !item.videos || !item.videos.length) return;  // mirrors real early return
        expanded = idx;
      },
      collapseFoundUp: function() {
        collapseCalls.push(true);
        expanded = null;
      }
    };
  }

  function makeL3VideoPlayer() {
    let open = false;
    let fid = null;
    let idx = -1;
    let qlen = 0;
    const openCalls = [];
    return {
      _openCalls: openCalls,
      open: function(foundupId, queue, startIndex) {
        openCalls.push({ foundupId: foundupId, queueLen: (queue || []).length, startIndex: startIndex });
        open = true;
        fid = foundupId;
        idx = startIndex || 0;
        qlen = (queue || []).length;
      },
      close: function() { open = false; fid = null; idx = -1; qlen = 0; },
      isOpen: function() { return open; },
      getFoundUpId: function() { return fid; },
      getCurrentIndex: function() { return idx; },
      getQueueLength: function() { return qlen; }
    };
  }

  const L3_CATALOG = [
    {
      foundup_id: 'move2japan',
      videos: [
        { video_id: 'vid_aaa', title: 'A' },
        { video_id: 'vid_bbb', title: 'B' },
        { video_id: 'vid_ccc', title: 'C' }
      ]
    },
    {
      foundup_id: 'kosei',
      videos: [{ video_id: 'vid_k1', title: 'K1' }]
    },
    {
      foundup_id: 'empty_foundup',
      videos: []
    }
  ];

  // 22) play_tile success path — valid foundup_id, API present -> status ok + video_loaded event.
  {
    const vp = makeL3VideoPlayer();
    const tf = makeL3TileField(L3_CATALOG);
    const sb = createSandbox({ tileField: tf, videoPlayer: vp });
    loadDispatcher(sb);
    const events = [];
    sb.pfmallControlDispatcher.registerEventListener({ postMessage(msg) { events.push(msg); } }, { origin: '*' });

    const res = sb.pfmallControlDispatcher.dispatch('play_tile', { foundup_id: 'move2japan' });
    assert(res.status === 'ok', 'play_tile ok');
    assert(res.result.applied === true, 'applied true (not "playing")');
    assert(res.result.foundup_id === 'move2japan', 'foundup_id echoed');
    assert(res.result.video_id === null, 'no specific video requested -> null');
    assert(res.result.start_index === 0, 'default start_index 0');
    assert(res.result.queue_length === 3, 'queue_length from catalog');
    assert(vp._openCalls.length === 1, 'mallVideoPlayer.open called once');
    assert(vp._openCalls[0].foundupId === 'move2japan', 'open got correct foundup_id');
    assert(vp._openCalls[0].queueLen === 3, 'open got full queue');
    assert(vp._openCalls[0].startIndex === 0, 'open got startIndex 0');

    const loaded = events.filter(e => e.event === 'video_loaded');
    assert(loaded.length === 1, 'one video_loaded event');
    assert(loaded[0].payload.foundup_id === 'move2japan', 'event foundup_id');
    assert(loaded[0].payload.start_index === 0, 'event start_index');
    assert(events.filter(e => e.event === 'video_failed').length === 0, 'no video_failed on success');
  }

  // 23) play_tile with specific video_id resolves to the correct queue index.
  {
    const vp = makeL3VideoPlayer();
    const sb = createSandbox({ tileField: makeL3TileField(L3_CATALOG), videoPlayer: vp });
    loadDispatcher(sb);

    const res = sb.pfmallControlDispatcher.dispatch('play_tile', {
      foundup_id: 'move2japan',
      video_id: 'vid_ccc'
    });
    assert(res.status === 'ok', 'play_tile with video_id -> ok');
    assert(res.result.start_index === 2, 'vid_ccc resolved to index 2');
    assert(res.result.video_id === 'vid_ccc', 'video_id echoed');
    assert(vp._openCalls[0].startIndex === 2, 'open got correct startIndex');
  }

  // 24) play_tile with missing mallVideoPlayer API -> status error, code api_unavailable.
  {
    const sb = createSandbox({ tileField: makeL3TileField(L3_CATALOG) });  // no videoPlayer
    loadDispatcher(sb);
    const res = sb.pfmallControlDispatcher.dispatch('play_tile', { foundup_id: 'move2japan' });
    assert(res.status === 'error', 'missing API -> error (not denied)');
    assert(res.error.code === 'api_unavailable', 'code api_unavailable');
  }

  // 25) play_tile with unknown foundup_id -> tile_not_found + video_failed event.
  {
    const vp = makeL3VideoPlayer();
    const sb = createSandbox({ tileField: makeL3TileField(L3_CATALOG), videoPlayer: vp });
    loadDispatcher(sb);
    const events = [];
    sb.pfmallControlDispatcher.registerEventListener({ postMessage(msg) { events.push(msg); } }, { origin: '*' });

    const res = sb.pfmallControlDispatcher.dispatch('play_tile', { foundup_id: 'does_not_exist' });
    assert(res.status === 'error', 'unknown foundup -> error');
    assert(res.error.code === 'tile_not_found', 'code tile_not_found');
    assert(vp._openCalls.length === 0, 'open never called for missing tile');

    const failed = events.filter(e => e.event === 'video_failed');
    assert(failed.length === 1, 'one video_failed event');
    assert(failed[0].payload.reason === 'tile_not_found', 'failure reason recorded');
    assert(events.filter(e => e.event === 'video_loaded').length === 0, 'no video_loaded on failure');
  }

  // 26) play_tile with unknown video_id within valid foundup -> video_id_not_found error.
  {
    const vp = makeL3VideoPlayer();
    const sb = createSandbox({ tileField: makeL3TileField(L3_CATALOG), videoPlayer: vp });
    loadDispatcher(sb);
    const events = [];
    sb.pfmallControlDispatcher.registerEventListener({ postMessage(msg) { events.push(msg); } }, { origin: '*' });

    const res = sb.pfmallControlDispatcher.dispatch('play_tile', {
      foundup_id: 'move2japan',
      video_id: 'vid_NOPE'
    });
    assert(res.status === 'error', 'unknown video_id -> error');
    assert(res.error.code === 'video_id_not_found', 'code video_id_not_found');
    assert(vp._openCalls.length === 0, 'open not called when video_id missing');

    const failed = events.filter(e => e.event === 'video_failed');
    assert(failed.length === 1, 'video_failed emitted for video_id_not_found');
    assert(failed[0].payload.reason === 'video_id_not_found', 'failure reason correct');
  }

  // 27) play_tile on FoundUp with empty queue -> no_videos error + video_failed event.
  {
    const vp = makeL3VideoPlayer();
    const sb = createSandbox({ tileField: makeL3TileField(L3_CATALOG), videoPlayer: vp });
    loadDispatcher(sb);
    const events = [];
    sb.pfmallControlDispatcher.registerEventListener({ postMessage(msg) { events.push(msg); } }, { origin: '*' });

    const res = sb.pfmallControlDispatcher.dispatch('play_tile', { foundup_id: 'empty_foundup' });
    assert(res.status === 'error', 'empty queue -> error');
    assert(res.error.code === 'no_videos', 'code no_videos');
    assert(vp._openCalls.length === 0, 'open not called when queue empty');
    assert(events.filter(e => e.event === 'video_failed').length === 1, 'video_failed on empty queue');
  }

  // 28) play_tile runtime_failure: open() is a no-op -> isOpen() stays false.
  {
    const stubVp = {
      open: function() { /* silently fails to update state */ },
      isOpen: function() { return false; },
      getFoundUpId: function() { return null; },
      getCurrentIndex: function() { return -1; },
      getQueueLength: function() { return 0; }
    };
    const sb = createSandbox({ tileField: makeL3TileField(L3_CATALOG), videoPlayer: stubVp });
    loadDispatcher(sb);
    const events = [];
    sb.pfmallControlDispatcher.registerEventListener({ postMessage(msg) { events.push(msg); } }, { origin: '*' });

    const res = sb.pfmallControlDispatcher.dispatch('play_tile', { foundup_id: 'move2japan' });
    assert(res.status === 'error', 'open no-op -> error');
    assert(res.error.code === 'runtime_failure', 'code runtime_failure');
    assert(events.filter(e => e.event === 'video_failed').length === 1, 'video_failed on runtime_failure');
    assert(events.filter(e => e.event === 'video_loaded').length === 0, 'no video_loaded when not confirmed');
  }

  // 29) play_tile missing foundup_id -> invalid_payload error, no event.
  {
    const sb = createSandbox({ tileField: makeL3TileField(L3_CATALOG), videoPlayer: makeL3VideoPlayer() });
    loadDispatcher(sb);
    const events = [];
    sb.pfmallControlDispatcher.registerEventListener({ postMessage(msg) { events.push(msg); } }, { origin: '*' });

    const res = sb.pfmallControlDispatcher.dispatch('play_tile', {});
    assert(res.status === 'error', 'missing foundup_id -> error');
    assert(res.error.code === 'invalid_payload', 'code invalid_payload');
    assert(events.length === 0, 'no event fired on invalid_payload (not a failure of playback)');
  }

  // 30) expand_tile success path -> status ok + state_changed event.
  {
    const tf = makeL3TileField(L3_CATALOG);
    const sb = createSandbox({ tileField: tf });
    loadDispatcher(sb);
    const events = [];
    sb.pfmallControlDispatcher.registerEventListener({ postMessage(msg) { events.push(msg); } }, { origin: '*' });

    const res = sb.pfmallControlDispatcher.dispatch('expand_tile', { foundup_id: 'kosei' });
    assert(res.status === 'ok', 'expand_tile ok');
    assert(res.result.applied === true, 'applied true');
    assert(res.result.foundup_id === 'kosei', 'foundup_id echoed');
    assert(res.result.expanded_index === 1, 'expanded_index returned (kosei = index 1)');
    assert(tf._expandCalls.length === 1, 'expandFoundUp called once');
    assert(tf._expandCalls[0] === 1, 'expand called with correct index');
    assert(tf.getExpandedIndex() === 1, 'tile field state mutated');

    const sc = events.filter(e => e.event === 'state_changed');
    assert(sc.length === 1, 'one state_changed event');
    assert(sc[0].payload.change === 'expanded', 'change=expanded');
    assert(sc[0].payload.foundup_id === 'kosei', 'event foundup_id');
    assert(sc[0].payload.expanded_index === 1, 'event expanded_index');
  }

  // 31) expand_tile with unknown foundup_id -> tile_not_found error.
  {
    const tf = makeL3TileField(L3_CATALOG);
    const sb = createSandbox({ tileField: tf });
    loadDispatcher(sb);
    const res = sb.pfmallControlDispatcher.dispatch('expand_tile', { foundup_id: 'ghost' });
    assert(res.status === 'error', 'unknown -> error');
    assert(res.error.code === 'tile_not_found', 'code tile_not_found');
    assert(tf._expandCalls.length === 0, 'expandFoundUp not called');
  }

  // 32) expand_tile with missing API -> api_unavailable error.
  {
    const sb = createSandbox({ tileField: { getCatalog: function() { return L3_CATALOG.slice(); } } });
    loadDispatcher(sb);
    const res = sb.pfmallControlDispatcher.dispatch('expand_tile', { foundup_id: 'kosei' });
    assert(res.status === 'error', 'no expandFoundUp -> error');
    assert(res.error.code === 'api_unavailable', 'code api_unavailable');
  }

  // 33) expand_tile where API silently refuses (e.g. empty videos) -> expand_failed.
  {
    const tf = makeL3TileField(L3_CATALOG);  // empty_foundup has no videos
    const sb = createSandbox({ tileField: tf });
    loadDispatcher(sb);
    const events = [];
    sb.pfmallControlDispatcher.registerEventListener({ postMessage(msg) { events.push(msg); } }, { origin: '*' });

    const res = sb.pfmallControlDispatcher.dispatch('expand_tile', { foundup_id: 'empty_foundup' });
    assert(res.status === 'error', 'silent expand refusal -> error');
    assert(res.error.code === 'expand_failed', 'code expand_failed (not runtime_failure)');
    assert(events.filter(e => e.event === 'state_changed').length === 0, 'no state_changed on expand_failed');
  }

  // 34) collapse_tile success path (tile currently expanded) -> ok + state_changed.
  {
    const tf = makeL3TileField(L3_CATALOG);
    const sb = createSandbox({ tileField: tf });
    loadDispatcher(sb);
    // expand first
    sb.pfmallControlDispatcher.dispatch('expand_tile', { foundup_id: 'move2japan' });
    assert(tf.getExpandedIndex() === 0, 'precondition: expanded');

    const events = [];
    sb.pfmallControlDispatcher.registerEventListener({ postMessage(msg) { events.push(msg); } }, { origin: '*' });

    const res = sb.pfmallControlDispatcher.dispatch('collapse_tile', { foundup_id: 'move2japan' });
    assert(res.status === 'ok', 'collapse ok');
    assert(res.result.applied === true, 'applied true');
    assert(res.result.foundup_id === 'move2japan', 'foundup_id echoed');
    assert(res.result.foundup_id_matched_prior === true, 'matched prior expanded index');
    assert(res.result.prior_expanded_index === 0, 'reports prior index');
    assert(tf._collapseCalls.length === 1, 'collapseFoundUp called once');
    assert(tf.getExpandedIndex() === null, 'state cleared');

    const sc = events.filter(e => e.event === 'state_changed');
    assert(sc.length === 1, 'one state_changed');
    assert(sc[0].payload.change === 'collapsed', 'change=collapsed');
    assert(sc[0].payload.foundup_id === 'move2japan', 'event foundup_id');
    assert(sc[0].payload.foundup_id_matched_prior === true, 'event reports id match');
  }

  // 35) collapse_tile when nothing expanded -> ok but foundup_id_matched_prior false.
  //     Truth-signal: dispatcher doesn't lie about whether the id was actually expanded;
  //     it still collapses (global API) but reports the mismatch.
  {
    const tf = makeL3TileField(L3_CATALOG);
    const sb = createSandbox({ tileField: tf });
    loadDispatcher(sb);
    assert(tf.getExpandedIndex() === null, 'precondition: nothing expanded');

    const res = sb.pfmallControlDispatcher.dispatch('collapse_tile', { foundup_id: 'move2japan' });
    assert(res.status === 'ok', 'collapse still ok (global API succeeds)');
    assert(res.result.foundup_id_matched_prior === false, 'not matched (nothing was expanded)');
    assert(res.result.prior_expanded_index === null, 'prior was null');
  }

  // 36) collapse_tile with missing API -> api_unavailable error.
  {
    const sb = createSandbox({ tileField: { getCatalog: function() { return L3_CATALOG.slice(); } } });
    loadDispatcher(sb);
    const res = sb.pfmallControlDispatcher.dispatch('collapse_tile', { foundup_id: 'move2japan' });
    assert(res.status === 'error', 'no collapseFoundUp -> error');
    assert(res.error.code === 'api_unavailable', 'code api_unavailable');
  }

  // 37) collapse_tile runtime_failure: collapse no-op leaves expanded state -> collapse_failed.
  {
    const stubTf = {
      getCatalog: function() { return L3_CATALOG.slice(); },
      getExpandedIndex: function() { return 0; },  // stays expanded after collapse
      isExpanded: function() { return true; },
      collapseFoundUp: function() { /* no-op */ }
    };
    const sb = createSandbox({ tileField: stubTf });
    loadDispatcher(sb);
    const res = sb.pfmallControlDispatcher.dispatch('collapse_tile', { foundup_id: 'move2japan' });
    assert(res.status === 'error', 'collapse no-op -> error');
    assert(res.error.code === 'collapse_failed', 'code collapse_failed');
  }

  // 38) play/expand/collapse missing or empty foundup_id -> invalid_payload.
  {
    const sb = createSandbox({
      tileField: makeL3TileField(L3_CATALOG),
      videoPlayer: makeL3VideoPlayer()
    });
    loadDispatcher(sb);
    const cmds = ['play_tile', 'expand_tile', 'collapse_tile'];
    for (const cmd of cmds) {
      const r1 = sb.pfmallControlDispatcher.dispatch(cmd, {});
      assert(r1.status === 'error' && r1.error.code === 'invalid_payload', cmd + ' missing -> invalid_payload');
      const r2 = sb.pfmallControlDispatcher.dispatch(cmd, { foundup_id: '' });
      assert(r2.status === 'error' && r2.error.code === 'invalid_payload', cmd + ' empty -> invalid_payload');
      const r3 = sb.pfmallControlDispatcher.dispatch(cmd, { foundup_id: 123 });
      assert(r3.status === 'error' && r3.error.code === 'invalid_payload', cmd + ' non-string -> invalid_payload');
    }
  }

  // 39) Layer 1/2 regressions still pass after Layer 3 lands.
  {
    const tf = makeTileFieldWithPolicy('desktop');
    const sb = createSandbox({ tileField: tf });
    loadDispatcher(sb);
    // inspect_state unchanged
    const ins = sb.pfmallControlDispatcher.dispatch('inspect_state', {});
    assert(ins.status === 'ok', 'Layer 1: inspect_state still ok');
    // set_layout Layer 2 accept path unchanged
    const sl = sb.pfmallControlDispatcher.dispatch('set_layout', { preset: '6x3', source: 'test' });
    assert(sl.status === 'ok' && sl.result.applied === true, 'Layer 2: set_layout accept unchanged');
    // set_layout Layer 2 deny path unchanged
    const sb2 = createSandbox({ tileField: makeTileFieldWithPolicy('phone') });
    loadDispatcher(sb2);
    const sl2 = sb2.pfmallControlDispatcher.dispatch('set_layout', { preset: '6x3' });
    assert(sl2.status === 'denied', 'Layer 2: set_layout deny unchanged');
    // Unknown commands still rejected
    const unk = sb.pfmallControlDispatcher.dispatch('nonsense', {});
    assert(unk.status === 'error' && unk.error.code === 'unknown_command', 'unknown still rejected');
  }

  // 40) postMessage routing works for Layer 3 commands with envelope shape preserved.
  {
    const vp = makeL3VideoPlayer();
    const tf = makeL3TileField(L3_CATALOG);
    const sb = createSandbox({ tileField: tf, videoPlayer: vp });
    loadDispatcher(sb);
    let replied;
    const source = { postMessage(msg) { replied = msg; } };
    sb._messageHandler({
      origin: 'http://127.0.0.1:5500',
      source,
      data: {
        type: 'pfmall_command',
        source: 'red_dog',
        command: 'play_tile',
        request_id: 'req-play-1',
        payload: { foundup_id: 'kosei' }
      }
    });
    assert(replied && replied.type === 'pfmall_response', 'play_tile postMessage response');
    assert(replied.status === 'ok', 'play_tile via postMessage ok');
    assert(replied.request_id === 'req-play-1', 'request_id echoed');
    assert(replied.target === 'red_dog', 'target echoed');
    assert(replied.result.foundup_id === 'kosei', 'result foundup_id');
    assert(replied.error === undefined, 'no error field on success');
  }

  // ==========================================================================
  // Layer 4: load_videos / reset_session (session commands)
  // ==========================================================================

  // makeL4TileField: composable tile field stub with optional session APIs.
  // session_mode controls how loadSessionVideos responds:
  //   'accept'    → {applied:true, session_mode:true, video_count:N}
  //   'refuse'    → {applied:false, reason:'policy'}
  //   'catalog'   → {applied:true, session_mode:false}  (dispatcher must reject)
  //   'malformed' → {}  (no applied field; dispatcher must return runtime_failure)
  //   'throw'     → throws (dispatcher must return runtime_failure)
  //   'missing'   → no method at all (dispatcher must return api_unavailable)
  function makeL4TileField(opts) {
    opts = opts || {};
    const sessionMode = opts.sessionMode || 'accept';
    const withResetApi = opts.withResetApi !== false;  // default true
    const resetCalls = [];
    const loadCalls = [];
    const tf = Object.assign({}, makeTileFieldStub({
      getCatalog: function() { return []; }
    }));
    if (sessionMode !== 'missing') {
      tf.loadSessionVideos = function(videos, options) {
        loadCalls.push({ count: videos.length, source: (options && options.source) || null });
        if (sessionMode === 'accept') {
          return { applied: true, session_mode: true, video_count: videos.length };
        }
        if (sessionMode === 'refuse') {
          return { applied: false, reason: 'test policy refusal' };
        }
        if (sessionMode === 'catalog') {
          return { applied: true, session_mode: false, video_count: videos.length };
        }
        if (sessionMode === 'malformed') {
          return {};
        }
        if (sessionMode === 'throw') {
          throw new Error('simulated runtime failure');
        }
        return null;
      };
    }
    if (withResetApi) {
      tf.resetSession = function(options) {
        resetCalls.push({ source: (options && options.source) || null });
        return { applied: true };
      };
    }
    tf._loadCalls = loadCalls;
    tf._resetCalls = resetCalls;
    return tf;
  }

  const L4_VIDEOS = [
    { video_id: 'sv_1', source_url: 'https://x.test/1' },
    { video_id: 'sv_2', source_url: 'https://x.test/2' }
  ];

  // 41) load_videos accepts a valid session list, updates session state, emits state_changed.
  {
    const tf = makeL4TileField({ sessionMode: 'accept' });
    const sb = createSandbox({ tileField: tf });
    loadDispatcher(sb);
    const events = [];
    sb.pfmallControlDispatcher.registerEventListener({ postMessage(msg) { events.push(msg); } }, { origin: '*' });

    const res = sb.pfmallControlDispatcher.dispatch('load_videos', { videos: L4_VIDEOS, source: 'red_dog' });
    assert(res.status === 'ok', 'load_videos ok');
    assert(res.result.applied === true, 'applied true');
    assert(res.result.session_mode === true, 'session_mode confirmed');
    assert(res.result.video_count === 2, 'video_count echoed');
    assert(res.result.source === 'red_dog', 'source echoed');
    assert(tf._loadCalls.length === 1, 'loadSessionVideos called once');
    assert(tf._loadCalls[0].count === 2, 'API received all videos');
    assert(tf._loadCalls[0].source === 'red_dog', 'API received source');

    // Session state reflected in inspect_state (dispatcher truth)
    const ins = sb.pfmallControlDispatcher.dispatch('inspect_state', {});
    assert(ins.result.session.override_active === true, 'session override now active');
    assert(ins.result.session.override_video_count === 2, 'inspect reports video count');
    assert(typeof ins.result.session.override_applied_at === 'string', 'applied_at timestamp set');

    // state_changed event emitted with session_loaded change
    const sc = events.filter(e => e.event === 'state_changed');
    assert(sc.length === 1, 'one state_changed event');
    assert(sc[0].payload.change === 'session_loaded', 'change=session_loaded');
    assert(sc[0].payload.video_count === 2, 'event has video_count');
    assert(events.filter(e => e.event === 'video_failed').length === 0, 'no video_failed on success');
  }

  // 42) load_videos rejects invalid payload with invalid_payload (no state mutation, no event).
  {
    const tf = makeL4TileField({ sessionMode: 'accept' });
    const sb = createSandbox({ tileField: tf });
    loadDispatcher(sb);
    const events = [];
    sb.pfmallControlDispatcher.registerEventListener({ postMessage(msg) { events.push(msg); } }, { origin: '*' });

    const cases = [
      [{}, 'missing videos'],
      [{ videos: null }, 'null videos'],
      [{ videos: [] }, 'empty videos'],
      [{ videos: 'not-an-array' }, 'non-array videos'],
      [{ videos: [{ /* no video_id */ }] }, 'item missing video_id'],
      [{ videos: [{ video_id: '' }] }, 'empty video_id'],
      [{ videos: [{ video_id: 123 }] }, 'non-string video_id']
    ];
    for (const [payload, label] of cases) {
      const res = sb.pfmallControlDispatcher.dispatch('load_videos', payload);
      assert(res.status === 'error', label + ' -> error');
      assert(res.error.code === 'invalid_payload', label + ' -> invalid_payload');
    }
    // No runtime call, no event, no session state change on invalid payloads.
    assert(tf._loadCalls.length === 0, 'loadSessionVideos never called on invalid payloads');
    assert(events.length === 0, 'no events emitted on invalid_payload');
    const ins = sb.pfmallControlDispatcher.dispatch('inspect_state', {});
    assert(ins.result.session.override_active === false, 'session still inactive after invalid_payload');
  }

  // 43) load_videos returns api_unavailable if required mall API is absent.
  //     Validates BOTH: no mallTileField at all, and mallTileField missing loadSessionVideos.
  {
    // no mallTileField
    const sb1 = createSandbox();
    loadDispatcher(sb1);
    const r1 = sb1.pfmallControlDispatcher.dispatch('load_videos', { videos: L4_VIDEOS });
    assert(r1.status === 'error', 'no tileField -> error');
    assert(r1.error.code === 'api_unavailable', 'no tileField -> api_unavailable');

    // tileField without loadSessionVideos
    const sb2 = createSandbox({ tileField: makeL4TileField({ sessionMode: 'missing' }) });
    loadDispatcher(sb2);
    const r2 = sb2.pfmallControlDispatcher.dispatch('load_videos', { videos: L4_VIDEOS });
    assert(r2.status === 'error', 'partial tileField -> error');
    assert(r2.error.code === 'api_unavailable', 'partial tileField -> api_unavailable');
  }

  // 44) load_videos does NOT set dispatcher session override unless API confirms session_mode:true.
  //     If the API says applied:true but session_mode:false (or missing), dispatcher rejects with
  //     session_mode_required — this prevents silent canonical-catalog mutation.
  {
    const tf = makeL4TileField({ sessionMode: 'catalog' });  // applied:true, session_mode:false
    const sb = createSandbox({ tileField: tf });
    loadDispatcher(sb);
    const events = [];
    sb.pfmallControlDispatcher.registerEventListener({ postMessage(msg) { events.push(msg); } }, { origin: '*' });

    const res = sb.pfmallControlDispatcher.dispatch('load_videos', { videos: L4_VIDEOS });
    assert(res.status === 'error', 'non-session mode applied -> error');
    assert(res.error.code === 'session_mode_required', 'code session_mode_required');
    assert(tf._loadCalls.length === 1, 'API was called — the refusal is dispatcher-side');

    // dispatcher session state MUST NOT flip to active
    const ins = sb.pfmallControlDispatcher.dispatch('inspect_state', {});
    assert(ins.result.session.override_active === false, 'session still inactive after session_mode_required');
    assert(ins.result.session.override_video_count === 0, 'video_count still 0');

    // Emits video_failed with session_mode_required reason (truth-signal)
    const failed = events.filter(e => e.event === 'video_failed');
    assert(failed.length === 1, 'one video_failed event');
    assert(failed[0].payload.reason === 'session_mode_required', 'failure reason recorded');
    assert(events.filter(e => e.event === 'state_changed').length === 0, 'no state_changed on session_mode_required');
  }

  // 45) load_videos with API refusing (applied:false) → load_refused + video_failed.
  {
    const tf = makeL4TileField({ sessionMode: 'refuse' });
    const sb = createSandbox({ tileField: tf });
    loadDispatcher(sb);
    const events = [];
    sb.pfmallControlDispatcher.registerEventListener({ postMessage(msg) { events.push(msg); } }, { origin: '*' });

    const res = sb.pfmallControlDispatcher.dispatch('load_videos', { videos: L4_VIDEOS });
    assert(res.status === 'error', 'refused load -> error');
    assert(res.error.code === 'load_refused', 'code load_refused');

    const ins = sb.pfmallControlDispatcher.dispatch('inspect_state', {});
    assert(ins.result.session.override_active === false, 'session inactive after refusal');
    assert(events.filter(e => e.event === 'video_failed').length === 1, 'video_failed emitted');
  }

  // 46) load_videos with malformed / throwing API outcome → runtime_failure.
  {
    const sb1 = createSandbox({ tileField: makeL4TileField({ sessionMode: 'malformed' }) });
    loadDispatcher(sb1);
    const r1 = sb1.pfmallControlDispatcher.dispatch('load_videos', { videos: L4_VIDEOS });
    assert(r1.status === 'error', 'malformed outcome -> error');
    assert(r1.error.code === 'runtime_failure', 'code runtime_failure');

    const sb2 = createSandbox({ tileField: makeL4TileField({ sessionMode: 'throw' }) });
    loadDispatcher(sb2);
    const r2 = sb2.pfmallControlDispatcher.dispatch('load_videos', { videos: L4_VIDEOS });
    assert(r2.status === 'error', 'thrown API -> error');
    assert(r2.error.code === 'runtime_failure', 'code runtime_failure on throw');
  }

  // 47) reset_session clears active override and emits session_reset + state_changed.
  {
    const tf = makeL4TileField({ sessionMode: 'accept' });
    const sb = createSandbox({ tileField: tf });
    loadDispatcher(sb);
    // precondition: load a session
    sb.pfmallControlDispatcher.dispatch('load_videos', { videos: L4_VIDEOS, source: 'red_dog' });
    const ins1 = sb.pfmallControlDispatcher.dispatch('inspect_state', {});
    assert(ins1.result.session.override_active === true, 'precondition: session active');

    const events = [];
    sb.pfmallControlDispatcher.registerEventListener({ postMessage(msg) { events.push(msg); } }, { origin: '*' });

    const res = sb.pfmallControlDispatcher.dispatch('reset_session', { source: 'red_dog' });
    assert(res.status === 'ok', 'reset_session ok');
    assert(res.result.applied === true, 'applied true');
    assert(res.result.changed === true, 'changed: true (session was active)');
    assert(res.result.api_called === true, 'runtime API was called');
    assert(res.result.api_acknowledged === true, 'runtime acknowledged reset');

    // Session state cleared
    const ins2 = sb.pfmallControlDispatcher.dispatch('inspect_state', {});
    assert(ins2.result.session.override_active === false, 'session cleared');
    assert(ins2.result.session.override_video_count === 0, 'video_count cleared');
    assert(ins2.result.session.override_applied_at === null, 'applied_at cleared');

    // Runtime API called
    assert(tf._resetCalls.length === 1, 'mallTileField.resetSession called once');
    assert(tf._resetCalls[0].source === 'red_dog', 'source passed through');

    // Both session_reset and state_changed fired
    const sr = events.filter(e => e.event === 'session_reset');
    const sc = events.filter(e => e.event === 'state_changed');
    assert(sr.length === 1, 'one session_reset event');
    assert(sc.length === 1, 'one state_changed event');
    assert(sc[0].payload.change === 'session_reset', 'change=session_reset');
  }

  // 48) reset_session when no session active → ok with changed:false, no events.
  //     (Truthful no-op: we don't emit session_reset if there was no session.)
  {
    const tf = makeL4TileField({ sessionMode: 'accept' });
    const sb = createSandbox({ tileField: tf });
    loadDispatcher(sb);
    // precondition: nothing active
    const ins0 = sb.pfmallControlDispatcher.dispatch('inspect_state', {});
    assert(ins0.result.session.override_active === false, 'precondition: no session');

    const events = [];
    sb.pfmallControlDispatcher.registerEventListener({ postMessage(msg) { events.push(msg); } }, { origin: '*' });

    const res = sb.pfmallControlDispatcher.dispatch('reset_session', {});
    assert(res.status === 'ok', 'no-op reset still ok');
    assert(res.result.changed === false, 'changed: false (nothing to reset)');
    assert(events.length === 0, 'no events fired on truthful no-op');
  }

  // 49) reset_session works even if mallTileField.resetSession is absent
  //     (dispatcher session state is local — still resettable), reporting
  //     api_called:false / api_acknowledged:false truthfully.
  {
    const tf = makeL4TileField({ sessionMode: 'accept', withResetApi: false });
    const sb = createSandbox({ tileField: tf });
    loadDispatcher(sb);
    // activate a session
    sb.pfmallControlDispatcher.dispatch('load_videos', { videos: L4_VIDEOS });
    assert(sb.pfmallControlDispatcher.dispatch('inspect_state', {}).result.session.override_active === true,
           'precondition: session active');

    const res = sb.pfmallControlDispatcher.dispatch('reset_session', {});
    assert(res.status === 'ok', 'reset still ok without runtime API');
    assert(res.result.changed === true, 'changed true');
    assert(res.result.api_called === false, 'api_called false when API absent');
    assert(res.result.api_acknowledged === false, 'api_acknowledged false when API absent');
    assert(sb.pfmallControlDispatcher.dispatch('inspect_state', {}).result.session.override_active === false,
           'session cleared locally');
  }

  // 50) postMessage routing for Layer 4 preserves envelope shape and request_id.
  {
    const tf = makeL4TileField({ sessionMode: 'accept' });
    const sb = createSandbox({ tileField: tf });
    loadDispatcher(sb);
    let replied;
    const source = { postMessage(msg) { replied = msg; } };
    sb._messageHandler({
      origin: 'http://127.0.0.1:5500',
      source,
      data: {
        type: 'pfmall_command',
        source: 'red_dog',
        command: 'load_videos',
        request_id: 'req-load-1',
        payload: { videos: L4_VIDEOS, source: 'red_dog' }
      }
    });
    assert(replied && replied.type === 'pfmall_response', 'response envelope');
    assert(replied.status === 'ok', 'postMessage load_videos ok');
    assert(replied.request_id === 'req-load-1', 'request_id echoed');
    assert(replied.result && replied.result.video_count === 2, 'result carries video_count');

    // reset over postMessage
    let replied2;
    const source2 = { postMessage(msg) { replied2 = msg; } };
    sb._messageHandler({
      origin: 'http://127.0.0.1:5500',
      source: source2,
      data: {
        type: 'pfmall_command',
        source: 'red_dog',
        command: 'reset_session',
        request_id: 'req-reset-1',
        payload: {}
      }
    });
    assert(replied2 && replied2.status === 'ok', 'reset_session over postMessage ok');
    assert(replied2.result.changed === true, 'reset reported changed via postMessage');
  }

  // 51) Layer 1/2/3 regressions still pass after Layer 4 lands.
  {
    // Layer 1: inspect_state with no APIs
    const sb1 = createSandbox();
    loadDispatcher(sb1);
    assert(sb1.pfmallControlDispatcher.dispatch('inspect_state', {}).status === 'ok',
           'Layer 1: inspect_state still ok');

    // Layer 2: set_layout accept on desktop
    const sb2 = createSandbox({ tileField: makeTileFieldWithPolicy('desktop') });
    loadDispatcher(sb2);
    const sl = sb2.pfmallControlDispatcher.dispatch('set_layout', { preset: '6x3', source: 'test' });
    assert(sl.status === 'ok' && sl.result.applied === true, 'Layer 2: set_layout accept unchanged');

    // Layer 2: set_layout deny on phone
    const sb3 = createSandbox({ tileField: makeTileFieldWithPolicy('phone') });
    loadDispatcher(sb3);
    const sl2 = sb3.pfmallControlDispatcher.dispatch('set_layout', { preset: '6x3' });
    assert(sl2.status === 'denied', 'Layer 2: set_layout deny unchanged');

    // Layer 3: play_tile + expand_tile + collapse_tile still work
    const vp = makeL3VideoPlayer();
    const l3tf = makeL3TileField(L3_CATALOG);
    const sb4 = createSandbox({ tileField: l3tf, videoPlayer: vp });
    loadDispatcher(sb4);
    const pt = sb4.pfmallControlDispatcher.dispatch('play_tile', { foundup_id: 'move2japan' });
    assert(pt.status === 'ok', 'Layer 3: play_tile unchanged');
    const et = sb4.pfmallControlDispatcher.dispatch('expand_tile', { foundup_id: 'kosei' });
    assert(et.status === 'ok', 'Layer 3: expand_tile unchanged');
    const ct = sb4.pfmallControlDispatcher.dispatch('collapse_tile', { foundup_id: 'kosei' });
    assert(ct.status === 'ok', 'Layer 3: collapse_tile unchanged');
  }

  console.log('pfmall_control_dispatcher_vm.mjs: all checks passed (Layer 1 + Layer 2 + Layer 3 + Layer 4)');
}

run().catch((e) => {
  console.error(e);
  process.exit(1);
});
