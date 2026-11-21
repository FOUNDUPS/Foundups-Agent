import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import { runInNewContext } from 'node:vm';
import { SKINS, createCallScript, resolveSkin } from '../web/contact-script.mjs';
import { appendOffice, parseContactRoster, phoneHref, selectOffices } from '../web/contact-queue.mjs';
import { suggestState } from '../oversight/public/states-location.mjs';

const roster = JSON.parse(await readFile(new URL('../web/contact-roster.json', import.meta.url), 'utf8'));
const boundaries = JSON.parse(await readFile(new URL('../oversight/public/states-boundaries.json', import.meta.url), 'utf8'));
const houseOffice = roster.offices.find((office) => office.id === 'J000294');
const senateOffice = roster.offices.find((office) => office.id === 'S000148');

test('every tone and regeneration preserves supplied identity, callback, request and reason', () => {
  const core = { intro: 'I am Alex.', callback: '555-0100', request: 'Please record my objection.', reason: 'Public accountability matters.' };
  const variants = new Set();
  for (let tone = 0; tone < 3; tone++) for (let variant = 0; variant < 3; variant++) {
    const script = createCallScript({ ...core, tone, variant });
    for (const value of Object.values(core)) assert.ok(script.includes(value));
    variants.add(script);
    assert.equal(createCallScript({ ...core, tone, variant: variant + 3 }), script);
  }
  assert.equal(variants.size, 9);
});

test('defaults never invent a director, coalition size, callback or election result', () => {
  const script = createCallScript(SKINS.hpc);
  assert.match(script, /Hakeem Jeffries/);
  assert.match(script, /Hasan Piker/);
  assert.doesNotMatch(script, /executive director|2,000|202-656|258|177/);
  assert.equal(createCallScript(SKINS.vote), '');
  for (const unknown of ['__proto__', 'constructor', '<script>', undefined]) assert.equal(resolveSkin(unknown), 'vote');
});

test('empty requests and malformed options fail safely; output remains bounded plain text', () => {
  assert.equal(createCallScript({ request: ' \n\t ' }), '');
  assert.equal(createCallScript({ request: false }), '');
  assert.equal(createCallScript({ request: 'Ask', tone: NaN, variant: -1 }), createCallScript({ request: 'Ask' }));
  const bounded = createCallScript({ intro: 'a'.repeat(1000), callback: 'b'.repeat(1000), request: 'c'.repeat(2000), reason: 'd'.repeat(2000) });
  assert.ok(bounded.length < 2400);
  assert.ok(!createCallScript({ request: 'Ask\u0000now' }).includes('\u0000'));
});

const scriptController = (await readFile(new URL('../web/contact-script.js', import.meta.url), 'utf8')).replace(/^import[^\n]+\n/, '');
function scriptPage(hash = '#hpc', clipboardFails = false) {
  const element = () => ({ value: '', checked: false, disabled: false, hidden: false, dataset: {}, attrs: {}, events: {},
    addEventListener(type, fn) { this.events[type] = fn; }, setAttribute(name, value) { this.attrs[name] = value; },
    focus() { this.focused = true; }, select() { this.selected = true; } });
  const ids = Object.fromEntries(['script-skin', 'script-intro', 'script-callback', 'script-request', 'script-reason', 'contact-notes', 'script-status', 'script-title', 'script-hpc-help', 'script-spokesperson', 'script-authorized', 'script-director', 'script-regenerate', 'script-copy', 'contact-clear'].map(id => [id, element()]));
  const tones = [0, 1, 2].map(index => Object.assign(element(), { dataset: { scriptTone: String(index) } }));
  const window = element();
  const location = { hash, pathname: '/contact', search: '' };
  let copied;
  runInNewContext(scriptController, { SKINS, createCallScript, resolveSkin, document: { getElementById: id => ids[id], querySelectorAll: () => tones, body: { dataset: {} } }, window, location, history: { replaceState() {} }, navigator: { clipboard: { async writeText(value) { if (clipboardFails) throw Error('Unavailable'); copied = value; } } } });
  return { ids, tones, window, location, copied: () => copied };
}

test('controller works without a directory and protects drafts from ordinary fragment navigation', async () => {
  const p = scriptPage();
  assert.match(p.ids['contact-notes'].value, /Hasan Piker/);
  p.ids['contact-notes'].value = 'My handwritten draft';
  p.location.hash = '#main'; p.window.events.hashchange();
  assert.equal(p.ids['contact-notes'].value, 'My handwritten draft');
  p.ids['script-request'].value = '<img src=x onerror=alert(1)> My core request';
  p.ids['script-request'].events.input();
  const first = p.ids['contact-notes'].value;
  p.tones[2].events.click();
  p.ids['script-regenerate'].events.click();
  assert.notEqual(p.ids['contact-notes'].value, first);
  assert.ok(p.ids['contact-notes'].value.includes(p.ids['script-request'].value));
  await p.ids['script-copy'].events.click();
  assert.equal(p.copied(), p.ids['contact-notes'].value);
  assert.ok(p.tones[2].attrs['aria-pressed'] === 'true');
});

test('director draft is explicit and skin changes and clear remove personal details', () => {
  const p = scriptPage();
  p.ids['script-director'].events.click();
  assert.doesNotMatch(p.ids['contact-notes'].value, /executive director/);
  p.ids['script-authorized'].checked = true; p.ids['script-authorized'].events.change();
  p.ids['script-director'].events.click();
  assert.match(p.ids['contact-notes'].value, /executive director.*2,000/);
  assert.match(p.ids['contact-notes'].value, /202-656-6012/);
  p.ids['script-skin'].value = 'vote'; p.ids['script-skin'].events.change();
  assert.equal(p.ids['contact-notes'].value, '');
  assert.equal(p.ids['script-callback'].value, '');
  assert.equal(p.ids['script-authorized'].checked, false);
  p.ids['script-skin'].value = 'hpc'; p.ids['script-skin'].events.change();
  p.ids['contact-clear'].events.click();
  for (const id of ['script-intro', 'script-callback', 'script-request', 'script-reason', 'contact-notes']) assert.equal(p.ids[id].value, '');
  assert.equal(p.ids['script-director'].disabled, true);
});

test('copy failure selects the draft and provides a manual fallback', async () => {
  const p = scriptPage('#hpc', true);
  await p.ids['script-copy'].events.click();
  assert.equal(p.ids['contact-notes'].selected, true);
  assert.match(p.ids['script-status'].textContent, /device’s copy command/);
});

test('the reviewed directory snapshot includes both chambers and reports omitted source rows', () => {
  assert.equal(parseContactRoster(roster), roster);
  for (const source of roster.sources) {
    assert.ok(source.sourceRows >= roster.offices.filter((office) => office.chamber === source.chamber).length);
  }
  assert.equal(houseOffice.state, 'NY');
  assert.equal(houseOffice.district, '8th');
  assert.equal(senateOffice.state, 'NY');
  assert.equal(senateOffice.chamber, 'Senate');
});

test('unsafe directory data fails closed before becoming a phone link', () => {
  const unsafe = structuredClone(roster);
  unsafe.offices[0].phone = 'tel:+12022243121;ext=1';
  assert.throws(() => parseContactRoster(unsafe), /Invalid contact snapshot row/);
  unsafe.offices[0].phone = null;
  assert.equal(parseContactRoster(unsafe), unsafe);
  unsafe.offices[1].id = unsafe.offices[0].id;
  assert.throws(() => parseContactRoster(unsafe), /Invalid contact snapshot row/);
  const badSource = structuredClone(roster);
  badSource.sources[0].url = 'https://example.com/';
  assert.throws(() => parseContactRoster(badSource), /Invalid contact snapshot source/);
});

test('dial links accept only a Washington office number and no dialing suffix', () => {
  assert.equal(phoneHref('2022243121'), 'tel:+12022243121');
  for (const value of ['+12022243121', '2022243121#', '2022243121\n', '2022243121,5', '2122243121', '', null, 2022243121]) {
    assert.equal(phoneHref(value), null, String(value));
  }
});

test('only an explicit state selection reveals offices, and chamber is a neutral filter', () => {
  assert.deepEqual(selectOffices(roster.offices, '', ''), []);
  assert.ok(selectOffices(roster.offices, 'NY', 'House').includes(houseOffice));
  assert.ok(selectOffices(roster.offices, 'NY', 'Senate').includes(senateOffice));
  assert.ok(!selectOffices(roster.offices, 'NY', 'House').includes(senateOffice));
  assert.deepEqual(selectOffices(roster.offices, 'GU', 'Senate'), []);
});

test('list starts empty and only manual additions fill the selected limit', () => {
  const empty = [];
  assert.equal(appendOffice(empty, null, 1), empty);
  assert.equal(appendOffice(empty, houseOffice, 2), empty);
  const one = appendOffice(empty, houseOffice, 1);
  assert.deepEqual(empty, []);
  assert.deepEqual(one, [houseOffice]);
  assert.equal(appendOffice(one, senateOffice, 1), one);
  assert.equal(appendOffice(one, houseOffice, 3), one);
  assert.equal(appendOffice(one, { ...senateOffice, phone: houseOffice.phone }, 3), one);
  const three = appendOffice(one, senateOffice, 3);
  assert.deepEqual(three, [houseOffice, senateOffice]);
  assert.equal(appendOffice(three, { ...senateOffice, id: 'X000001', phone: null }, 5), three);
});

test('Oversight location data covers Senate states and retains Census source provenance', () => {
  const senateStates = new Set(roster.offices.filter((office) => office.chamber === 'Senate').map((office) => office.state));
  assert.deepEqual(new Set(Object.keys(boundaries.states)), senateStates);
  assert.equal(boundaries.schemaVersion, 1);
  assert.equal(boundaries.source.url, 'https://www2.census.gov/geo/tiger/GENZ2025/kml/cb_2025_us_state_20m.zip');
  assert.match(boundaries.source.sha256, /^[a-f0-9]{64}$/);
  for (const rings of Object.values(boundaries.states)) {
    assert.ok(rings.length);
    for (const ring of rings) {
      assert.ok(ring.length >= 4);
      assert.deepEqual(ring[0], ring.at(-1));
      assert.ok(ring.every(([longitude, latitude]) => Number.isFinite(longitude)
        && Math.abs(longitude) <= 180 && Number.isFinite(latitude) && Math.abs(latitude) <= 90));
    }
  }
});

test('Oversight suggests inland locations and defers uncertain or unsupported locations', () => {
  const locate = (latitude, longitude, accuracy = 20) => suggestState({ latitude, longitude, accuracy }, boundaries);
  assert.equal(locate(39.7392, -104.9903), 'CO'); // Denver
  assert.equal(locate(30.2672, -97.7431), 'TX'); // Austin
  assert.equal(locate(64.8378, -147.7164), 'AK'); // Fairbanks
  assert.equal(locate(21.5028, -158.0228), 'HI'); // Wahiawa
  assert.equal(locate(33.4251, -94.0431), null); // Texarkana, on the state line
  assert.equal(locate(38.9072, -77.0369), null); // Washington, DC
  assert.equal(locate(35.6762, 139.6503), null); // Tokyo
  assert.equal(locate(39.7392, -104.9903, 26_000), null);
  assert.equal(locate(39.7392, -104.9903, -1), null);
  assert.equal(locate(Number.NaN, -104.9903), null);
});

test('Oversight handles rings spanning the antimeridian and defers an ambiguous match', () => {
  const ring = [[179, 50], [-179, 50], [-179, 52], [179, 52], [179, 50]];
  const geometry = { schemaVersion: 1, states: { AK: [ring] } };
  const locate = (longitude, source = geometry) => suggestState({ latitude: 51, longitude, accuracy: 20 }, source);
  assert.equal(locate(179.5), 'AK');
  assert.equal(locate(-179.5), 'AK');
  assert.equal(locate(0), null);
  assert.equal(locate(179.5, { schemaVersion: 1, states: { AK: [ring], HI: [ring] } }), null);
});
