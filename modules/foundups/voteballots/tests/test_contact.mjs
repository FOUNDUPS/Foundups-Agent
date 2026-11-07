import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import { appendOffice, parseContactRoster, phoneHref, selectOffices } from '../web/contact-queue.mjs';

const roster = JSON.parse(await readFile(new URL('../web/contact-roster.json', import.meta.url), 'utf8'));
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
