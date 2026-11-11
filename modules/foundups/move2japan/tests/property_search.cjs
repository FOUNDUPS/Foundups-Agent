'use strict';
// Executable public-catalog contract; no browser or live source service required.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '../../../..');
const { normalizeCatalog, searchProperties, groupProperties, locationOptions, isShellProductRoute } = require(path.join(root, 'public/move2japan/property-search.js'));
const raw = JSON.parse(fs.readFileSync(path.join(root, 'public/move2japan/properties.json'), 'utf8'));
const catalog = normalizeCatalog(raw);
const rows = catalog.properties;
let passed = 0;
function check(name, fn) { fn(); passed += 1; process.stdout.write('PASS ' + name + '\n'); }
function changedRow(changes) { const copy = structuredClone(raw); Object.assign(copy.properties[0], changes); return copy; }

check('eight distinct houses retain a single Move2Japan context', () => {
  assert.equal(rows.length, 8);
  assert.equal(new Set(rows.map(x => x.listing_id)).size, 8);
  assert.ok(rows.every(x => x.foundup_id === 'move2japan'));
});
check('lowest-price sort and budget include boundary price', () => {
  assert.deepEqual(searchProperties(rows, {max_price_jpy: 2800000}).map(x => x.listing_id), ['fukui-87', 'fukui-25', 'fukui-77']);
  assert.deepEqual(searchProperties(rows, {max_price_jpy: 0}), []);
});
check('English town and original Japanese address are searchable', () => {
  assert.equal(searchProperties(rows, {query: 'EIHEIJI'})[0].listing_id, 'fukui-76');
  assert.equal(searchProperties(rows, {query: '松岡志比堺'})[0].listing_id, 'fukui-76');
  assert.equal(searchProperties(rows, {area: 'Wakasa'})[0].listing_id, 'fukui-87');
});
check('compound search and area filters intersect', () => {
  assert.equal(searchProperties(rows, {query: 'house storehouse', area: 'Sakai'}).length, 1);
  assert.equal(searchProperties(rows, {query: 'storehouse', area: 'Eiheiji'}).length, 0);
});
check('large plots and source tours filter actual fields', () => {
  assert.equal(searchProperties(rows, {large_plots: true}).length, 6);
  assert.equal(searchProperties(rows, {virtual_tours: true}).length, 5);
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
check('cities become five distinct geographic rows, each owning its houses', () => {
  const groups = groupProperties(rows, 'city');
  assert.equal(groups.length, 5);
  assert.deepEqual(groups.find(group => group.label === 'Wakasa').itemIds, ['fukui-87', 'fukui-88']);
  assert.equal(new Set(groups.flatMap(group => group.itemIds)).size, 8);
});
check('locality grouping keeps the complete geographic hierarchy', () => {
  const repeated = [{ ...rows[0], locality_ja: '同名' }, { ...rows[1], locality_ja: '同名' }];
  assert.equal(groupProperties(repeated, 'locality').length, 2);
  assert.equal(groupProperties(rows, 'locality').length, 8);
});
check('country, prefecture, city, locality and price combine', () => {
  const result = searchProperties(rows, { country: 'JP', prefecture: 'fukui', city: 'wakasa', locality: '安賀里', max_price_jpy: 600000 });
  assert.deepEqual(result.map(row => row.listing_id), ['fukui-87']);
});
check('unsupported geography stays empty instead of widening the result', () => {
  assert.equal(searchProperties(rows, { country: 'US' }).length, 0);
  assert.equal(searchProperties(rows, { prefecture: 'Tokyo' }).length, 0);
  assert.equal(searchProperties(rows, { city: 'Sakai', locality: '安賀里' }).length, 0);
});
check('unknown land is distinct from no land and recorded land', () => {
  assert.equal(searchProperties(rows, { land: 'with_land' }).length, 7);
  assert.equal(searchProperties(rows, { land: 'no_land' }).length, 0);
  assert.deepEqual(searchProperties(rows, { land: 'unknown' }).map(row => row.listing_id), ['fukui-25']);
});
check('land filtering never infers title or unknown plot size', () => {
  assert.equal(searchProperties(rows, { land: 'unknown', large_plots: true }).length, 0);
  assert.equal(searchProperties(rows, { land: 'with_land', city: 'Sakai' }).length, 1);
});
check('negotiable prices remain null and sort last in both price directions', () => {
  assert.equal(rows.find(row => row.listing_id === 'fukui-88').price_jpy, null);
  for (const sort of ['price_asc', 'price_desc']) assert.equal(searchProperties(rows, { sort }).at(-1).listing_id, 'fukui-88');
});
check('budgets exclude unknown or negotiable prices', () => {
  assert.equal(searchProperties(rows, { max_price_jpy: 1e12 }).length, 7);
  assert.equal(searchProperties(rows, { city: 'Wakasa', max_price_jpy: 1e12 }).length, 1);
});
check('cascading locations expose only the selected parent', () => {
  const options = locationOptions(rows, { country: 'JP', prefecture: 'Fukui', city: 'Wakasa' });
  assert.equal(options.city.length, 5);
  assert.deepEqual(options.locality.map(option => option.value).sort(), ['安賀里', '日笠'].sort());
  assert.equal(locationOptions(rows, { country: 'US' }).prefecture.length, 0);
});
check('localities are searchable in Japanese and checked Latin forms', () => {
  assert.equal(searchProperties(rows, { query: 'nakajima' })[0].listing_id, 'fukui-79');
  assert.equal(searchProperties(rows, { query: '日笠' })[0].listing_id, 'fukui-88');
});
check('unknown, no-land and recorded-land data are validated explicitly', () => {
  assert.throws(() => normalizeCatalog(changedRow({ land_status: 'unknown', land_area_m2: 5 })), /provenance/);
  assert.throws(() => normalizeCatalog(changedRow({ land_status: 'with_land', land_area_m2: null })), /provenance/);
  assert.throws(() => normalizeCatalog(changedRow({ land_status: 'no_land', land_area_m2: null })), /provenance/);
  assert.equal(normalizeCatalog(changedRow({ land_status: 'no_land', land_area_m2: 0 })).properties[0].land_status, 'no_land');
});
check('price status cannot turn missing facts into free houses', () => {
  assert.throws(() => normalizeCatalog(changedRow({ price_status: 'asking', price_jpy: null })), /provenance/);
  assert.throws(() => normalizeCatalog(changedRow({ price_status: 'negotiable', price_jpy: 0 })), /provenance/);
  assert.equal(normalizeCatalog(changedRow({ price_status: 'unknown', price_jpy: null })).properties[0].price_jpy, null);
});
check('catalog version and product identity stay explicit', () => {
  assert.throws(() => normalizeCatalog({ ...raw, schema_version: 'move2japan_property_catalog.v1' }), /Unsupported/);
  assert.throws(() => normalizeCatalog({ ...raw, foundup_id: 'other' }), /Unsupported/);
});
check('only the exact registered product selection enables public member boot', () => {
  for (const route of ['/member/?foundup=move2japan', '/member/index.html?foundup=move2japan&city=Wakasa']) {
    assert.equal(isShellProductRoute(new URL(route, 'https://foundups.com')), true);
  }
});
check('video routes, aliases and ambiguous selections do not grant public member boot', () => {
  for (const route of ['/member/', '/member/?creator=move2japan', '/move2japan/?foundup=move2japan',
    '/member/?foundup=Move2Japan', '/member/?foundup=other', '/member/?foundup=move2japan&foundup=other',
    '/member/?foundup=move2japan&foundup=move2japan']) {
    assert.equal(isShellProductRoute(new URL(route, 'https://foundups.com')), false, route);
  }
});
check('legacy entry redirects only to the existing member page with bounded filters', () => {
  const vm = require('node:vm');
  const alias = fs.readFileSync(path.join(root, 'public/move2japan/index.html'), 'utf8');
  // Extract this trusted local fixture's inline script, not untrusted HTML.
  const source = alias.match(/<script\b[^>]*>([\s\S]*?)<\/script\b[^>]*>/i)[1];
  let redirected;
  vm.runInNewContext(source, { URLSearchParams, window: { location: {
    search: '?area=Wakasa&q=house&return_to=https://evil.invalid&foundup=other', replace: value => { redirected = value; }
  } } });
  const selected = new URL(redirected, 'https://foundups.com');
  assert.equal(selected.pathname, '/member/');
  assert.equal(selected.searchParams.get('foundup'), 'move2japan');
  assert.equal(selected.searchParams.get('city'), 'Wakasa');
  assert.equal(selected.searchParams.has('return_to'), false);
  assert.equal(alias.includes('mall-tile-field.js'), false);
});
process.stdout.write(passed + ' property-search checks passed\n');
