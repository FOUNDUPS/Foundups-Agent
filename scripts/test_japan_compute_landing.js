/* Node-only regression checks; run from any directory. No external services. */
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const crypto = require('node:crypto');
const root = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'public/index.html'), 'utf8');
const script = fs.readFileSync(path.join(root, 'public/js/japan-compute.js'), 'utf8');
let passed = 0;
function test(name, fn) { fn(); passed += 1; console.log('PASS ' + name); }
function run(suffix = '', protocol = 'https:') {
  const url = new URL('https://foundups.com/' + suffix);
  const state = { redirected: null, updated: null, description: '' };
  const buttons = ['ja', 'en'].map(language => ({
    dataset: { language }, attributes: {}, handlers: {},
    setAttribute(key, value) { this.attributes[key] = value; },
    addEventListener(key, fn) { this.handlers[key] = fn; }
  }));
  const doc = {
    documentElement: { lang: 'ja', classList: { add() {} } },
    querySelector() { return { setAttribute(key, value) { state.description = value; } }; },
    querySelectorAll() { return buttons; }
  };
  vm.runInNewContext(script, {
    URL, URLSearchParams, document: doc,
    window: { location: {
      href: url.href, search: url.search, hash: url.hash, protocol,
      replace(value) { state.redirected = value; }
    }, history: { replaceState(a, b, value) { state.updated = value; } } }
  });
  return { state, doc, buttons };
}
test('Japanese default and invalid language fallback', () => {
  assert.equal(run().doc.documentElement.lang, 'ja');
  assert.equal(run('?lang=invalid').doc.documentElement.lang, 'ja');
});
test('English URL changes language and metadata', () => {
  const result = run('?lang=en');
  assert.equal(result.doc.documentElement.lang, 'en');
  assert.match(result.state.description, /feasibility/);
  assert.equal(result.buttons[1].attributes['aria-pressed'], 'true');
});
test('Language click preserves marketing parameters and section', () => {
  const result = run('?utm_source=partner#capital');
  result.buttons[1].handlers.click();
  assert.equal(result.doc.documentElement.lang, 'en');
  assert.equal(result.state.updated, '/?utm_source=partner&lang=en#capital');
});
test('Legacy query links preserve the complete suffix', () => {
  for (const suffix of ['?sse=1&sse_url=test#build', '?invite=FUP-EXAMPLE', '?__clerk_ticket=example']) {
    assert.equal(run(suffix).state.redirected, '/innovate.html' + suffix);
  }
});
test('Legacy product anchors route to Innovate', () => {
  for (const suffix of ['#how', '#roc', '#build', '#beta']) {
    assert.equal(run(suffix).state.redirected, '/innovate.html' + suffix);
  }
});
test('Compute anchors and untrusted redirect values do not redirect', () => {
  assert.equal(run('#capital').state.redirected, null);
  assert.equal(run('?redirect=https://example.invalid/').state.redirected, null);
});
test('Local-preview language change does not write HTTP history', () => {
  const result = run('', 'about:');
  result.buttons[1].handlers.click();
  assert.equal(result.doc.documentElement.lang, 'en');
  assert.equal(result.state.updated, null);
});
test('Unique ids and valid local section links', () => {
  const ids = [...html.matchAll(/\bid="([^"]+)"/g)].map(match => match[1]);
  assert.equal(ids.length, new Set(ids).size);
  for (const match of html.matchAll(/href="#([^"]+)"/g)) assert.ok(ids.includes(match[1]), match[1]);
  assert.equal((html.match(/<h1\b/g) || []).length, 1);
});
test('Separate investor enquiry route; no investment or authentication form', () => {
  assert.match(html, /mailto:info@foundups\.com\?subject=/);
  assert.doesNotMatch(html, /<form\b|<iframe\b|clerk\.browser|firebase-app\.js/);
  assert.match(html, /No payback period or yield is offered/);
  assert.match(html, /planned, not deployed/i);
});
test('Existing Innovate destination and qualified national figure', () => {
  assert.match(html, /href="\/innovate\.html"/);
  assert.match(html, /May 1, 2024/);
  assert.match(html, /1,951 unused schools/);
  assert.match(html, /FY2004–FY2023/);
});
test('Existing hosting owner and FoundUp routes are preserved', () => {
  const config = JSON.parse(fs.readFileSync(path.join(root, 'firebase.json'), 'utf8'));
  assert.equal(config.hosting.site, 'foundupscom');
  assert.equal(config.hosting.public, 'public');
  assert.equal(config.hosting.rewrites.find(route => route.source === '/f/**').destination, '/f/index.html');
  assert.equal(config.hosting.rewrites.find(route => route.source === '**').destination, '/innovate.html');
});
test('Investor questions and immediate readable brief replace vague copy', () => {
  assert.match(html, /Who owns<br>the compute\?/);
  assert.match(html, /Who uses—and pays for—it\?/);
  assert.match(html, /Is compute affordable\?/);
  assert.match(html, /href="#investment-brief"/);
  assert.match(html, /Read the investment brief/);
  assert.match(html, /id="investment-brief"/);
  assert.doesNotMatch(html, /Japan-wide possibility|Discuss a partnership/);
});
test('Scope, ownership and negative economics cannot disappear', () => {
  assert.match(html, /800-site case/);
  assert.match(html, /approximately 41%/);
  assert.match(html, /Revenue is not profit or investor distributions/);
  assert.match(html, /−64\.8/);
  assert.match(html, /base case also has a shortfall that year/);
  assert.match(html, /Investor IRR and payback are not established/);
  assert.match(html, /Proposed site SPVs/);
  assert.match(html, /not customers' data/);
});
test('Displayed scale arithmetic matches the cited reference inputs', () => {
  const gpus = Math.ceil(360000 / (8760 * 0.75 * 8)) * 8;
  const facilityKw = ((gpus / 8) * 10.2 + 6) * 1.35;
  assert.equal(gpus, 56);
  assert.ok(Math.abs(facilityKw - 104.49) < 1e-9);
  assert.equal(gpus * 195, 10920);
  assert.equal(gpus * 800, 44800);
  assert.equal(160000 * 550 * 800, 70400000000);
  for (const value of ['10,920','44,800','104.49 kW','¥70.40bn','¥454.0bn']) assert.ok(html.includes(value), value);
});
const originalPath = path.join(root, 'public/innovate.html');
if (fs.existsSync(originalPath)) {
  test('Innovate preserves the complete pre-change application blob', () => {
    const data = fs.readFileSync(originalPath);
    const digest = crypto.createHash('sha1').update('blob ' + data.length + '\0').update(data).digest('hex');
    assert.equal(digest, '0d0e9ef375458e37e8aec67f4d2211d639c2016a');
  });
} else {
  if (process.argv.includes('--require-preserved')) throw new Error('Missing original Innovate source');
  console.log('NOT RUN: original application blob absent from this presentation-only workspace');
}
console.log(passed + ' checks passed. Authentication/backend and production hosting are outside this test.');
