import assert from 'node:assert/strict';
import test from 'node:test';
import nextConfig from '../frontend/next.config.ts';

// Dependency-free checks of the executable Next/Vinext configuration.
// These are config contract tests, not an HTTP/deployment verification.
const rewrites = await nextConfig.rewrites();
const movementRule = rewrites.beforeFiles.find((rule) => rule.source === '/');
const partnersRule = rewrites.beforeFiles.find((rule) => rule.source === '/partners');
const hostCondition = movementRule.has[0];
const hostPattern = new RegExp(`^(?:${hostCondition.value})$`);

// beforeFiles is important: app/page.tsx already owns the '/' filesystem route.
test('YUMORI homepage selection precedes the existing project homepage', () => {
  assert.deepEqual(Object.keys(rewrites).sort(), ['afterFiles', 'beforeFiles', 'fallback']);
  assert.deepEqual(rewrites.beforeFiles.map((rule) => rule.source).sort(), ['/', '/partners']);
  assert.deepEqual(rewrites.afterFiles, []);
  assert.deepEqual(rewrites.fallback, []);
  assert.equal(movementRule.source, '/');
  assert.equal(movementRule.destination, '/yumori');
});

test('routing uses the host condition, not query strings or forwarded headers', () => {
  assert.equal(movementRule.has.length, 1);
  assert.equal(hostCondition.type, 'host');
  assert.deepEqual(Object.keys(hostCondition).sort(), ['type', 'value']);
  assert.deepEqual(Object.keys(movementRule).sort(), ['destination', 'has', 'source']);
});

for (const hostname of ['yumori.me', 'www.yumori.me']) {
  test(`${hostname} selects the movement homepage`, () => {
    assert.equal(hostPattern.test(hostname), true);
  });
}

for (const hostname of [
  'esingularity.ai', 'www.esingularity.ai', 'yumori.info', 'www.yumori.info',
  'localhost', 'preview.example.test', 'music.yumori.me', 'notyumori.me',
  'yumori.me.example.test', 'yumoriXme', 'wwwXyumori.me',
]) {
  test(`${hostname} is not captured by the movement rule`, () => {
    assert.equal(hostPattern.test(hostname), false);
  });
}

test('reports, assets, APIs, and explicit movement links are not broadly rewritten', () => {
  for (const pathname of [
    '/reports/jhr', '/jhr', '/yumori', '/yumori/', '/future', '/team',
    '/api/interest', '/favicon.svg', '/sw.js', '/manifest.webmanifest',
    '/_next/static/example.js', '/vision/vision-sprite.jpg',
  ]) {
    assert.notEqual(movementRule.source, pathname);
  }
  assert.equal(movementRule.source.includes(':path'), false);
});

test('the movement mapping is internal and does not impose a new redirect', () => {
  assert.equal(movementRule.destination.startsWith('/'), true);
  assert.equal(movementRule.destination.startsWith('//'), false);
  assert.equal('redirects' in nextConfig, false);
  assert.equal('basePath' in nextConfig, false);
});

test('the rule does not filter or overwrite campaign query parameters', () => {
  assert.equal(movementRule.destination.includes('?'), false);
  assert.equal(movementRule.has.some((condition) => condition.type === 'query'), false);
  assert.equal('missing' in movementRule, false);
});

test('the partner alias is an internal exact-path rule with the same host boundary', () => {
  assert.equal(partnersRule.destination, '/yumori/partners');
  assert.deepEqual(partnersRule.has, movementRule.has);
  assert.deepEqual(Object.keys(partnersRule).sort(), ['destination', 'has', 'source']);
  assert.equal(partnersRule.source.includes(':path'), false);
  assert.equal(partnersRule.destination.includes('?'), false);
});

// Exercise selection from the actual config, including negative host/path pairs.
function selectedDestination(hostname, pathname) {
  const rule = rewrites.beforeFiles.find((candidate) =>
    candidate.source === pathname && candidate.has.every((condition) =>
      condition.type === 'host' && new RegExp(`^(?:${condition.value})$`).test(hostname)));
  return rule?.destination ?? pathname;
}

for (const hostname of ['yumori.me', 'www.yumori.me']) {
  test(`${hostname} selects only the root and partner aliases`, () => {
    assert.equal(selectedDestination(hostname, '/'), '/yumori');
    assert.equal(selectedDestination(hostname, '/partners'), '/yumori/partners');
    for (const pathname of ['/yumori', '/yumori/partners', '/partners-extra',
      '/partners/example', '/reports/jhr', '/api/interest', '/_next/static/example.js']) {
      assert.equal(selectedDestination(hostname, pathname), pathname);
    }
  });
}

for (const hostname of ['esingularity.ai', 'www.esingularity.ai', 'yumori.info',
  'www.yumori.info', 'localhost', 'preview.example.test', 'music.yumori.me',
  'notyumori.me', 'yumori.me.example.test', 'yumoriXme', 'wwwXyumori.me']) {
  test(`${hostname} keeps its homepage and partner paths`, () => {
    for (const pathname of ['/', '/partners', '/yumori/partners']) {
      assert.equal(selectedDestination(hostname, pathname), pathname);
    }
  });
}
