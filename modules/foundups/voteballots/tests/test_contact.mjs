import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import { appendOffice, parseContactRoster, phoneHref, selectOffices } from '../web/contact-queue.mjs';
import { suggestState } from '../oversight/public/states-location.mjs';

const roster = JSON.parse(await readFile(new URL('../web/contact-roster.json', import.meta.url), 'utf8'));
const boundaries = JSON.parse(await readFile(new URL('../oversight/public/states-boundaries.json', import.meta.url), 'utf8'));
const houseOffice = roster.offices.find((office) => office.id === 'J000294');
const senateOffice = roster.offices.find((office) => office.id === 'S000148');

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
