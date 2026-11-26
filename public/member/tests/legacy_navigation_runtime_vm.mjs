/** Actual entry/recommendation owners with controlled DOM/navigation only.
 * No network, authentication, provider, browser-layout or device qualification.
 */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import vm from 'node:vm';

const member = dirname(dirname(fileURLToPath(import.meta.url)));
const source = path => readFileSync(join(member, path), 'utf8').replace(/\r\n/g, '\n');
const entry = source('foundup.html');
const player = source('js/mall-video-player.js');
const projection = source('js/mall-video-projection.js');
function owner(source, start, end, limit) {
  const at = source.indexOf(start);
  assert.ok(at >= 0 && at === source.lastIndexOf(start), 'unique actual owner: ' + start);
  const stop = source.indexOf(end, at + start.length);
  assert.ok(stop > at && stop - at < limit, 'bounded actual owner: ' + start);
  return source.slice(at, stop);
}
const cta = owner(entry, '    const SOURCE_TYPE_CTA = {', '    const NON_VIDEO_SOURCE_TYPES', 1000);
const sourceAction = owner(entry, '    function sourceAction(item) {', '    function renderSourceTypeCTA(item)', 1800);
const recommendations = owner(entry, '    function renderRecommendations() {', '    // -- Gather entry context', 2400);
const entryIdentity = owner(player, '  function currentEntryId() {', '  function syncTopBarButtons()', 1600);
const enterCase = owner(player, "      case 'enter':\n", "      case 'save':\n", 1800);
let recommendationsPassed = 0;
let enterPassed = 0;
function check(kind, name, fn) {
  fn();
  if (kind === 'recommendations') recommendationsPassed++;
  else enterPassed++;
  console.log('PASS ' + name);
}
function recommendation(item) {
  const calls = [];
  let click;
  const body = { innerHTML: '', addEventListener(type, fn) { assert.equal(type, 'click'); click = fn; } };
  const context = vm.createContext({
    URL,
    document: { getElementById(id) { assert.equal(id, 'entryRecsBody'); return body; } },
    window: { location: new URL('https://play.foundups.com/member/foundup.html?id=fixture'),
      open(...args) { calls.push(args); } },
    currentItem: item,
    ENTRY_RECOMMENDATIONS: [],
    // Labels are fixed fixture strings; HTML sanitization is not this fixture's claim.
    esc: String,
  });
  vm.runInContext(cta + sourceAction + recommendations + '\nrenderRecommendations();', context);
  assert.deepEqual(calls, [], 'render must not navigate without a selected action');
  return { body, calls, activate() {
    click({ target: { closest(selector) {
      assert.equal(selector, '.entry-rec-action');
      return { getAttribute(name) { assert.equal(name, 'data-rec-id'); return 'source_type_action'; } };
    } } });
  } };
}
function navigation(href, id, records, scoped = false) {
  const calls = [];
  let page = new URL(href);
  let catalog = records;
  const location = {
    get href() { return page.href; },
    set href(value) { page = new URL(value, page); calls.push(['navigate', page.href]); },
    get origin() { return page.origin; }, get hostname() { return page.hostname; },
    get pathname() { return page.pathname; }, get search() { return page.search; },
    assign(value) { this.href = value; },
  };
  const context = vm.createContext({ URL, URLSearchParams,
    document: {
      documentElement: { dataset: {} },
      querySelector(selector) {
        assert.ok(['link[rel="manifest"]', 'link[rel="apple-touch-icon"]', 'link[rel="icon"]'].includes(selector));
        return { href: '', setAttribute() {} };
      },
      createElement(tag) { assert.equal(tag, 'meta'); return {}; },
      head: { append() {} },
    },
    window: { location, mallTileField: { getCatalog: () => catalog },
      mallStateRestore: { save() { calls.push(['save']); } } },
    currentFoundUpId: id, currentEntryIdentity: undefined, scopedPlayer: scoped,
    close() { calls.push(['close']); context.currentFoundUpId = null; },
  });
  vm.runInContext(projection, context, { filename: 'actual-mall-video-projection.js' });
  vm.runInContext(entryIdentity + '\nfunction activateEnter() { switch ("enter") {\n' + enterCase + '\n} }', context);
  return { calls, identity: () => vm.runInContext('currentEntryId()', context),
    activate: () => vm.runInContext('activateEnter()', context), setCatalog(value) { catalog = value; } };
}
const mode = process.argv[2];
assert.ok(['recommendations', 'enter', undefined].includes(mode), 'known bounded fixture mode');
if (!mode || mode === 'recommendations') {
  check('recommendations', 'actual ready source recommendation preserves external destination and opener protection', () => {
    for (const type of ['github_repo', 'external_app']) {
      const h = recommendation({ source_type: type, launch_readiness: 'ready', external_url: 'https://example.invalid/ready' });
      assert.match(h.body.innerHTML, /source_type_action/);
      h.activate();
      assert.deepEqual(h.calls, [['https://example.invalid/ready', '_blank', 'noopener']]);
    }
  });
  check('recommendations', 'actual candidate and unfinished actions prefer truthful validated project information', () => {
    for (const item of [
      { source_type: 'external_app', discovery_kind: 'candidate' },
      { source_type: 'internal_app', launch_readiness: 'discoverable_only' },
      { source_type: 'internal_service', launch_readiness: 'planning_only' },
    ]) {
      const h = recommendation({ ...item, external_url: 'https://example.invalid/unfinished', public_plan_url: 'https://example.invalid/plan' });
      assert.match(h.body.innerHTML, /View project information/);
      assert.doesNotMatch(h.body.innerHTML, /Open App/);
      h.activate();
      assert.deepEqual(h.calls, [['https://example.invalid/plan', '_blank', 'noopener']]);
    }
  });
  check('recommendations', 'actual information-only recommendation rejects unsafe plan URLs', () => {
    for (const url of ['javascript:void(0)', 'http://example.invalid/plan', 'https://fixture:fixture@example.invalid/plan', 'https://[invalid']) {
      const h = recommendation({ source_type: 'external_app', discovery_kind: 'candidate', external_url: 'https://example.invalid/unfinished', public_plan_url: url });
      assert.doesNotMatch(h.body.innerHTML, /source_type_action/);
      h.activate();
      assert.deepEqual(h.calls, []);
    }
  });
  check('recommendations', 'actual missing or unsupported source never fabricates a recommendation action', () => {
    for (const item of [{ source_type: 'github_repo' }, { source_type: 'youtube', external_url: 'https://example.invalid/video' }]) {
      const h = recommendation(item);
      assert.doesNotMatch(h.body.innerHTML, /source_type_action/);
      h.activate();
      assert.deepEqual(h.calls, []);
    }
  });
  assert.equal(recommendationsPassed, 4);
  console.log('Legacy navigation source VM: 4 recommendations checks passed.');
}
if (!mode || mode === 'enter') {
  check('enter', 'actual admitted Enter keeps canonical route and resolves before close resets player state', () => {
    for (const [id, record, target] of [
      ['move2japan', { foundup_id: 'move2japan' }, 'move2japan'],
      ['antifafm', { foundup_id: 'antifafm', canonical_foundup_id: 'antifafm_001' }, 'antifafm_001'],
    ]) {
      const h = navigation('https://foundups.com/member/', id, [record]);
      h.activate();
      assert.deepEqual(h.calls, [['close'], ['navigate', 'https://foundups.com/f/' + target]]);
    }
  });
  check('enter', 'actual public Play and preview Enter save then close and preserve shared same-origin entry', () => {
    for (const origin of ['https://play.foundups.com', 'https://foundupscom--play-v26-iphone-review.web.app']) {
      const h = navigation(origin + '/member/', 'antifafm', [{ foundup_id: 'antifafm', canonical_foundup_id: 'antifafm_001' }]);
      h.activate();
      assert.deepEqual(h.calls, [['save'], ['close'], ['navigate', origin + '/member/foundup.html?id=antifafm_001']]);
    }
  });
  check('enter', 'actual filtered lane retains canonical alias and explicit null without guessing an entity', () => {
    const h = navigation('https://play.foundups.com/member/', 'antifafm', [{ foundup_id: 'antifafm', canonical_foundup_id: 'antifafm_001' }]);
    assert.equal(h.identity(), 'antifafm_001');
    h.setCatalog([]); h.activate();
    assert.deepEqual(h.calls, [['save'], ['close'], ['navigate', 'https://play.foundups.com/member/foundup.html?id=antifafm_001']]);
    const missing = navigation('https://play.foundups.com/member/', 'undaodu', [{ foundup_id: 'undaodu', canonical_foundup_id: null }]);
    assert.equal(missing.identity(), null);
    missing.setCatalog([]); missing.activate(); assert.deepEqual(missing.calls, []);
  });
  check('enter', 'actual candidate invalid unknown and scoped player guards prevent Enter navigation', () => {
    for (const [href, id, records, scoped] of [
      ['https://play.foundups.com/member/', 'candidate', [{ foundup_id: 'candidate', canonical_foundup_id: null }], false],
      ['https://play.foundups.com/member/', 'bad', [{ foundup_id: 'bad', canonical_foundup_id: '../evil' }], false],
      ['https://play.foundups.com/member/', 'unknown', [], false],
      ['https://hpc.foundups.com/member/', 'hpc', [{ foundup_id: 'hpc' }], true],
    ]) {
      const h = navigation(href, id, records, scoped); h.activate(); assert.deepEqual(h.calls, []);
    }
  });
  assert.equal(enterPassed, 4);
  console.log('Legacy navigation source VM: 4 enter checks passed.');
}
