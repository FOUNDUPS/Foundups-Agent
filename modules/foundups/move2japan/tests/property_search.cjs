'use strict';
// Executable public-catalog contract; no browser or live source service required.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '../../../..');
const { normalizeCatalog, searchProperties } = require(path.join(root, 'public/move2japan/property-search.js'));
const raw = JSON.parse(fs.readFileSync(path.join(root, 'public/move2japan/properties.json'), 'utf8'));
const catalog = normalizeCatalog(raw);
const rows = catalog.properties;
let passed = 0;
function check(name, fn) { fn(); passed += 1; process.stdout.write('PASS ' + name + '\n'); }
function changedRow(changes) { const copy = structuredClone(raw); Object.assign(copy.properties[0], changes); return copy; }

check('five distinct houses retain a single Move2Japan context', () => {
  assert.equal(rows.length, 5);
  assert.equal(new Set(rows.map(x => x.listing_id)).size, 5);
  assert.ok(rows.every(x => x.foundup_id === 'move2japan'));
});
check('lowest-price sort and budget include boundary price', () => {
  assert.deepEqual(searchProperties(rows, {max_price_jpy: 2800000}).map(x => x.listing_id), ['fukui-87', 'fukui-77']);
  assert.deepEqual(searchProperties(rows, {max_price_jpy: 0}), []);
});
check('English town and original Japanese address are searchable', () => {
  assert.equal(searchProperties(rows, {query: 'EIHEIJI'})[0].listing_id, 'fukui-76');
  assert.equal(searchProperties(rows, {query: '松岡志比堺'})[0].listing_id, 'fukui-76');
  assert.equal(searchProperties(rows, {area: 'Wakasa'})[0].listing_id, 'fukui-87');
});
check('compound search and area filters intersect', () => {
  assert.equal(searchProperties(rows, {query: 'house storehouse', area: 'Sakai'}).length, 1);
  assert.equal(searchProperties(rows, {query: 'storehouse', area: 'Wakasa'}).length, 0);
});
check('large plots and source tours filter actual fields', () => {
  assert.equal(searchProperties(rows, {large_plots: true}).length, 4);
  assert.equal(searchProperties(rows, {virtual_tours: true}).length, 4);
  assert.equal(searchProperties(rows, {virtual_tours: true, max_price_jpy: 1000000}).length, 0);
});
check('largest-plot sort preserves original data order', () => {
  const before = rows.map(x => x.listing_id);
  assert.equal(searchProperties(rows, {sort: 'land_desc'})[0].listing_id, 'fukui-83');
  assert.equal(searchProperties(rows, {sort: 'price_desc'})[0].listing_id, 'fukui-83');
  assert.deepEqual(rows.map(x => x.listing_id), before);
});
check('missing condition and construction remain unknown', () => {
  const row = rows.find(x => x.listing_id === 'fukui-85');
  assert.equal(row.repair_level, 'unknown');
  assert.equal(row.construction_date, null);
  assert.equal(row.building_area_label_ja, '建築面積');
  assert.equal(row.building_area_m2, 298.94);
});
check('unsafe or unrelated sources reject the catalog', () => {
  ['javascript:alert(1)', 'http://akiya.pref.fukui.lg.jp/webroot/public/estate/detail/87',
   'https://evil.example/webroot/public/estate/detail/87',
   'https://user:secret@akiya.pref.fukui.lg.jp/webroot/public/estate/detail/87',
   'https://akiya.pref.fukui.lg.jp/webroot/public/estate/detail/85',
   'https://akiya.pref.fukui.lg.jp/webroot/public/estate/detail/87?private=1'].forEach(source_url => {
    assert.throws(() => normalizeCatalog(changedRow({source_url})), /provenance/);
  });
});
check('foreign tenant, duplicate ID and unreleased state reject', () => {
  assert.throws(() => normalizeCatalog(changedRow({foundup_id: 'gotjunk_001'})), /identity/);
  assert.throws(() => normalizeCatalog(changedRow({availability: 'members_only'})), /identity/);
  const duplicate = structuredClone(raw); duplicate.properties.push(duplicate.properties[0]);
  assert.throws(() => normalizeCatalog(duplicate), /identity/);
});
check('dates and nonnumeric prices are not silently fabricated', () => {
  assert.throws(() => normalizeCatalog(changedRow({last_checked: '2026-02-30'})), /provenance/);
  assert.throws(() => normalizeCatalog(changedRow({price_jpy: '600000'})), /provenance/);
  assert.throws(() => normalizeCatalog(changedRow({price_jpy: -1})), /provenance/);
});
check('render projection drops all private or economic metadata', () => {
  const row = normalizeCatalog(changedRow({owner_email:'private@example.invalid',token_symbol:'FAKE',
    poster_url:'https://example.invalid/unlicensed.jpg',member_release_at:'future',private_notes:'private'})).properties[0];
  ['owner_email','token_symbol','poster_url','member_release_at','private_notes'].forEach(key => assert.equal(key in row, false));
});
check('shipped snapshot has no paid or private inventory fields', () => {
  raw.properties.forEach(row => {
    assert.equal(row.availability, 'source_listed');
    ['owner_email','member_release_at','private_notes','token_symbol','poster_url'].forEach(key => assert.equal(key in row, false));
    assert.equal(row.broker_availability_confirmed, false);
  });
});
process.stdout.write(passed + ' property-search checks passed\n');
