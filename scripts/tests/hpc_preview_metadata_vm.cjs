'use strict';

// Offline source-binding contracts; all release identities below are synthetic.
// No artifact writes, Git mutation, network, allocation or deployment.
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { resolve } = require('node:path');
const { createHash } = require('node:crypto');
const { buildMetadata, validateMetadata } = require('../hpc_preview_metadata.cjs');
const root = resolve(__dirname, '../..');
let checks = 0;
function check(name, fn) { fn(); checks++; console.log('PASS ' + name); }
function context(overrides = {}) {
  return {
    sourceSha: '1'.repeat(40), channelId: 'preview-alpha',
    projectionSource: "(function(){const mallBuild = 'v41';})();",
    discoveryCatalog: { generation: '2'.repeat(64), items: [] },
    probeSource: Buffer.from('synthetic-probe\r\n'), ...overrides
  };
}
const hash = bytes => createHash('sha256').update(bytes).digest('hex');

check('two distinct source/build/channel/artifact contexts bind independently', () => {
  const a = context();
  const b = context({ sourceSha: 'a'.repeat(40), channelId: 'preview-beta',
    projectionSource: 'const mallBuild = "v102";', discoveryCatalog: { generation: 'b'.repeat(64) },
    probeSource: 'different probe', hostingVersion: 'abcdef0123456789' });
  const first = buildMetadata(a), second = buildMetadata(b);
  assert.deepEqual(first, {
    source_sha: a.sourceSha, app_source_sha: a.sourceSha, channel_id: a.channelId, mall_build: 'v41',
    discovery_generation: a.discoveryCatalog.generation, probe_sha256: hash(a.probeSource),
    hosting_version: 'unverified', stage_status: 'SOURCE_BOUND_ARTIFACT'
  });
  assert.equal(second.mall_build, 'v102');
  assert.equal(Object.isFrozen(first), true);
  assert.equal(validateMetadata(first, a), true);
  assert.equal(validateMetadata(second, b, { requireHosting: true }), true);
  assert.equal(validateMetadata(first, b), false);
  assert.equal(validateMetadata(second, a), false);
  assert.equal('published' in second, false);
});

check('unknown Hosting stays explicit and never passes the allocation gate', () => {
  const a = context(); const meta = buildMetadata(a);
  assert.equal(meta.hosting_version, 'unverified');
  assert.equal(validateMetadata(meta, a), true);
  assert.equal(validateMetadata(meta, a, { requireHosting: true }), false);
  assert.equal(validateMetadata({ ...meta, hosting_version: '0123456789abcdef' }, a, { requireHosting: true }), false);
  for (const hostingVersion of ['unpublished', 'unverified', null, '', '1234567', 'a'.repeat(41),
    'projects/site/versions/abcdef12', 'ABCDEFGH']) {
    assert.throws(() => buildMetadata(context({ hostingVersion })), TypeError);
  }
});

check('allocated Hosting requires complete expected identity, not merely a shaped field', () => {
  for (const hostingVersion of ['01234567', '0123456789abcdef', 'c'.repeat(40)]) {
    const a = context({ hostingVersion }); const meta = buildMetadata(a);
    assert.equal(validateMetadata(meta, a, { requireHosting: true }), true);
    assert.equal(validateMetadata({ ...meta, hosting_version: 'f'.repeat(hostingVersion.length) }, a), false);
    assert.equal(validateMetadata({ ...meta, hosting_version: hostingVersion.slice(0, -1) }, a), false);
  }
});

check('projection extraction ignores comment, string, regex and template decoys', () => {
  const source = [
    "// const mallBuild = 'v90';", "/* const mallBuild = 'v91'; */",
    "const text = \"const mallBuild = 'v92';\";",
    "const pattern = /const mallBuild = 'v93';/;",
    "if ((true)) /const mallBuild = 'v96';/.test('');",
    "const template = `const mallBuild = 'v94'; ${ `const mallBuild = 'v95';` }`;",
    "const mallBuild /* owner */ = 'v42';"
  ].join('\n');
  assert.equal(buildMetadata(context({ projectionSource: source })).mall_build, 'v42');
});

check('regex statements after control-flow parentheses cannot supply a declaration', () => {
  for (const projectionSource of [
    "if (true) /const mallBuild = 'v99';/.test(''); const other = /x/;",
    "if ((true)) /const mallBuild = 'v99';/.test(''); 1 / 2;",
    "while (false) /const mallBuild = 'v99';/.test('');",
    "for (;;) /const mallBuild = 'v99';/.test('');",
  ]) assert.throws(() => buildMetadata(context({ projectionSource })), TypeError);
});

check('missing, duplicate, computed and ambiguous projection declarations reject', () => {
  for (const projectionSource of ['', "// const mallBuild = 'v1';", "const text = \"const mallBuild = 'v1';\";",
    "const mallBuild = 'v1'; const mallBuild = 'v1';", "const mallBuild = 'v1'; const mallBuild = 'v2';",
    "const mallBuild = version;", "const mallBuild = 'v' + 26;", "const mallBuild = 'v26' + suffix;",
    "let mallBuild = 'v26';", "const mallBuild = `v26`;", "const mallBuild = 'v\\x32\\x36';",
    "const mallBuild = 'v12345';", "/* unterminated", "const x = `unterminated", ' '.repeat(2 * 1024 * 1024 + 1)]) {
    assert.throws(() => buildMetadata(context({ projectionSource })), TypeError);
  }
});

check('probe digest binds exact bytes without newline or Unicode normalization', () => {
  const a = buildMetadata(context({ probeSource: 'a\r\nb' }));
  const b = buildMetadata(context({ probeSource: 'a\nb' }));
  assert.notEqual(a.probe_sha256, b.probe_sha256);
  const value = '日本語\r\n';
  assert.equal(buildMetadata(context({ probeSource: value })).probe_sha256,
    buildMetadata(context({ probeSource: Buffer.from(value, 'utf8') })).probe_sha256);
  assert.notEqual(buildMetadata(context({ probeSource: 'é' })).probe_sha256,
    buildMetadata(context({ probeSource: 'e\u0301' })).probe_sha256);
  for (const probeSource of [null, undefined, '', Buffer.alloc(0), {}, new Uint8Array([1]), Buffer.alloc(16 * 1024 * 1024 + 1)]) {
    assert.throws(() => buildMetadata(context({ probeSource })), TypeError);
  }
});

check('all stale/null/partial identities and contradictory publication fields reject', () => {
  const a = context({ hostingVersion: '0123456789abcdef' }); const meta = buildMetadata(a);
  const mutations = {
    source_sha: [null, a.sourceSha.slice(0, 7), '3'.repeat(40)],
    app_source_sha: [null, '3'.repeat(40)], channel_id: ['live', 'preview-older'],
    mall_build: ['v25'], discovery_generation: ['4'.repeat(64), '4'.repeat(63)],
    probe_sha256: ['5'.repeat(64), '5'.repeat(63)], hosting_version: ['unpublished', 'unverified', '0123456'],
    stage_status: ['PUBLISHED', 'UNPUBLISHED_INTEGRATION_CANDIDATE', null]
  };
  for (const [key, values] of Object.entries(mutations)) {
    for (const value of values) assert.equal(validateMetadata({ ...meta, [key]: value }, a), false, key);
    const missing = { ...meta }; delete missing[key]; assert.equal(validateMetadata(missing, a), false, 'missing ' + key);
  }
  for (const extra of [{ published: true }, { schema_version: 2 }, { credentials: null }, { __extra: 1 }]) {
    assert.equal(validateMetadata({ ...meta, ...extra }, a), false);
  }
});

check('invalid context, live IDs, accessors and prototype fields fail closed', () => {
  for (const patch of [{ sourceSha: 'main' }, { sourceSha: 'a'.repeat(39) }, { sourceSha: null },
    { sourceSha: 'A'.repeat(40) }, { channelId: 'live' }, { channelId: '../preview' }, { channelId: 'https://example.invalid' },
    { channelId: '' }, { channelId: 'a'.repeat(65) }, { discoveryCatalog: { generation: 'b'.repeat(63) } },
    { discoveryCatalog: null }, { authority: true }]) {
    assert.throws(() => buildMetadata(context(patch)), TypeError);
    assert.equal(validateMetadata({}, context(patch)), false);
  }
  const a = context(); const meta = buildMetadata(a); let invoked = 0;
  const getter = { ...meta }; Object.defineProperty(getter, 'source_sha', { enumerable: true, get() { invoked++; return a.sourceSha; } });
  assert.equal(validateMetadata(getter, a), false);
  assert.equal(validateMetadata(Object.assign(Object.create({ granted: true }), meta), a), false);
  assert.equal(validateMetadata({ ...meta, [Symbol('identity')]: true }, a), false);
  assert.equal(validateMetadata(JSON.parse('{"__proto__":{}}'), a), false);
  const input = context(); Object.defineProperty(input, 'sourceSha', { enumerable: true, get() { invoked++; return a.sourceSha; } });
  assert.throws(() => buildMetadata(input), TypeError);
  assert.equal(invoked, 0);
  assert.equal(validateMetadata(meta, a, { requireHosting: 'yes' }), false);
  assert.equal(validateMetadata(meta, a, { publish: true }), false);
  assert.equal(validateMetadata(meta, a, null), false);
});

check('frozen stale v25 repo metadata rejects against actual current source assets', () => {
  const stale = JSON.parse(readFileSync(resolve(root, 'modules/foundups/pfmall/tests/fixtures/hpc_preview_metadata_stale_v25.json'), 'utf8'));
  const actual = context({
    channelId: 'preview-current-fixture',
    projectionSource: readFileSync(resolve(root, 'public/member/js/mall-video-projection.js'), 'utf8'),
    discoveryCatalog: JSON.parse(readFileSync(resolve(root, 'public/member/discovery/catalog.json'), 'utf8')),
    probeSource: readFileSync(resolve(root, 'modules/foundups/pfmall/tests/fixtures/hpc_iphone_playback_probe.js'))
  });
  const expected = buildMetadata(actual);
  assert.equal(stale.mall_build, 'v25', 'frozen regression input is not stamped with a cyclic source SHA');
  assert.notEqual(expected.mall_build, stale.mall_build);
  assert.equal(validateMetadata(stale, actual), false);
  for (const key of ['source_sha', 'app_source_sha', 'channel_id', 'mall_build']) {
    assert.equal(validateMetadata({ ...expected, [key]: stale[key] }, actual), false, 'stale actual field ' + key);
  }
  assert.equal(expected.probe_sha256, hash(actual.probeSource));
  assert.equal(validateMetadata(expected, actual), true);
});

console.log(JSON.stringify({ checks, network: false, artifact_writes: false, allocation: false, deployment: false, publication_proof: false }));
