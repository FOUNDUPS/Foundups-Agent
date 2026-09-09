import { test, after } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, writeFileSync, mkdtempSync, rmSync } from 'node:fs';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import ts from 'typescript';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';

const root = fileURLToPath(new URL('../', import.meta.url));
const compiled = mkdtempSync(path.join(root, 'node_modules/.mosh-tests-'));
after(() => rmSync(compiled, { recursive: true, force: true }));
for (const [source, target] of [
  ['lib/mosh-pit-policy.ts', 'mosh-pit-policy.js'],
  ['lib/mosh-pit-gateway.ts', 'mosh-pit-gateway.js'],
  ['components/MoshPitFeed.tsx', 'MoshPitFeed.js'],
]) {
  writeFileSync(path.join(compiled, target), ts.transpileModule(readFileSync(path.join(root, source), 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX },
  }).outputText);
}
writeFileSync(path.join(compiled, 'package.json'), '{"type":"commonjs"}');
const require = createRequire(import.meta.url);
const { membershipFor, cleanProjection, MOSH_SITE, MOSH_PROJECT } = require(path.join(compiled, 'mosh-pit-policy.js'));
const { readMoshPit } = require(path.join(compiled, 'mosh-pit-gateway.js'));
const Feed = require(path.join(compiled, 'MoshPitFeed.js')).default;
const policy = (members = [{ user_id: 'synthetic-viewer', expires_at: '2099-01-01T00:00:00Z' }]) => ({
  version: 1, site_id: MOSH_SITE, project_id: MOSH_PROJECT, revision: 'test-1', members,
});
const config = () => ({ MOSH_PIT_MEMBERSHIPS_JSON: JSON.stringify(policy()),
  MOSH_PIT_SOURCE_URL: 'https://synthetic.invalid/mosh-pit/read', MOSH_PIT_SOURCE_TOKEN: 'synthetic-test-only-token-not-real-secret' });
const entry = () => ({ event_id: 'synthetic-event', actor: '架空の参加者', summary: '架空の活動',
  details: ['架空の詳細'], truth: 'OBSERVED', replies: [], more_replies: false });
const projection = (snapshot = 'snapshot') => ({ schema_version: 'mosh_pit_projection.v1', foundup_id: MOSH_PROJECT,
  disclosure_class: 'stakeholder', snapshot_id: snapshot, timezone: 'Asia/Tokyo',
  days: [{ date: '2026-09-09', entries: [entry()] }], has_more: false, read_only: true });
const upstream = (mutate = () => {}) => async (_url, options) => {
  const input = JSON.parse(options.body);
  assert.equal(options.cache, 'no-store');
  assert.equal(options.redirect, 'error');
  assert.equal(input.foundup_id, MOSH_PROJECT);
  assert.equal(input.disclosure_class, 'stakeholder');
  const body = { schema_version: 'mosh_pit_gateway_snapshot.v1', site_id: MOSH_SITE,
    viewer_id: input.viewer_id, membership_revision: input.membership_revision,
    expires_at: new Date(Date.now() + 30_000).toISOString(), projection: projection(input.snapshot_id) };
  mutate(body);
  return Response.json(body);
};

test('identity and current explicit membership are required before any upstream request', async () => {
  let calls = 0;
  const never = async () => { calls++; throw Error('should not read'); };
  assert.equal((await readMoshPit(null, config(), never)).status, 'signed_out');
  assert.equal((await readMoshPit('different-viewer', config(), never)).status, 'not_approved');
  assert.equal((await readMoshPit('synthetic-viewer', {}, never)).status, 'unavailable');
  const revoked = config(); revoked.MOSH_PIT_MEMBERSHIPS_JSON = JSON.stringify(policy([]));
  assert.equal((await readMoshPit('synthetic-viewer', revoked, never)).status, 'not_approved');
  assert.equal(calls, 0);
});

test('expired, duplicate, malformed and cross-site/project grants fail closed', () => {
  assert.equal(membershipFor(JSON.stringify(policy([{ user_id: 'synthetic-viewer', expires_at: '2000-01-01T00:00:00Z' }])), 'synthetic-viewer').status, 'not_approved');
  for (const alter of [p => p.members.push(p.members[0]), p => p.site_id = 'other-site', p => p.project_id = 'other-project',
    p => p.members[0].expires_at = 'bad', p => p.members[0] = null, p => p.revision = null]) {
    const p = policy(); alter(p);
    assert.equal(membershipFor(JSON.stringify(p), 'synthetic-viewer').status, 'unavailable');
  }
  assert.equal(membershipFor('{', 'synthetic-viewer').status, 'unavailable');
  assert.equal(membershipFor(JSON.stringify(policy([{ user_id: 'synthetic-viewer', expires_at: '2099-02-30T00:00:00Z' }])), 'synthetic-viewer').status, 'unavailable');
});

test('a validated stakeholder snapshot is stripped of extra private fields', async () => {
  const result = await readMoshPit('synthetic-viewer', config(), upstream(body => {
    body.raw_private = 'PRIVATE_SENTINEL'; body.projection.raw_private = 'PRIVATE_SENTINEL';
    body.projection.days[0].entries[0].private_details = 'PRIVATE_SENTINEL';
  }));
  assert.equal(result.status, 'ready');
  assert.ok(!JSON.stringify(result).includes('PRIVATE_SENTINEL'));
});

test('mismatched or expired snapshots and private disclosures never reach the browser', async () => {
  for (const mutate of [b => b.site_id = 'other', b => b.viewer_id = 'other', b => b.membership_revision = 'old',
    b => b.expires_at = '2000-01-01T00:00:00Z', b => b.expires_at = '2099-01-01T00:00:00Z',
    b => b.projection.disclosure_class = 'principal_private', b => b.projection.foundup_id = 'other',
    b => b.projection.snapshot_id = 'replayed', b => b.projection.read_only = false]) {
    assert.equal((await readMoshPit('synthetic-viewer', config(), upstream(mutate))).status, 'unavailable');
  }
});

test('upstream denial, failure, oversized data and insecure configuration have no fallback', async () => {
  for (const status of [401, 403]) assert.equal((await readMoshPit('synthetic-viewer', config(), async () => new Response('', { status }))).status, 'not_approved');
  for (const request of [async () => { throw Error('PRIVATE_SENTINEL'); }, async () => new Response('bad'),
    async () => new Response('x'.repeat(1_000_001), { headers: { 'Content-Type': 'application/json' } })]) {
    assert.equal((await readMoshPit('synthetic-viewer', config(), request)).status, 'unavailable');
  }
  for (const url of ['http://synthetic.invalid', 'https://user:secret@synthetic.invalid', 'https://synthetic.invalid?token=bad']) {
    assert.equal((await readMoshPit('synthetic-viewer', { ...config(), MOSH_PIT_SOURCE_URL: url }, () => { throw Error('must not call'); })).status, 'unavailable');
  }
});

test('invalid dates, oldest-first days, duplicate events and speculative root activities reject', () => {
  for (const change of [p => p.days[0].date = '2026-02-30', p => p.days.push({ date: '2026-09-10', entries: [{ ...entry(), event_id: 'newer' }] }),
    p => p.days[0].entries.push(entry()), p => p.days[0].entries[0].truth = 'PROPOSED',
    p => p.days[0].entries[0].details = Array(13).fill('overflow'),
    p => p.days[0].entries = Array.from({ length: 51 }, (_, i) => ({ ...entry(), event_id: `event-${i}` }))]) {
    const p = projection(); change(p); assert.throws(() => cleanProjection(p, 'snapshot'));
  }
});

test('expanded discussions render escaped content and label proposals beneath real activities', () => {
  const p = projection();
  p.days[0].entries[0].summary = '<script>sentinel()</script>';
  p.days[0].entries[0].replies = [{ ...entry(), event_id: 'reply', truth: 'PROPOSED' }];
  const html = renderToStaticMarkup(React.createElement(Feed, { projection: cleanProjection(p, 'snapshot') }));
  assert.ok(html.includes('<details>') && html.includes('<summary>'));
  assert.ok(html.includes('&lt;script&gt;') && !html.includes('<script>'));
  assert.ok(html.includes('提案') && html.includes('<ul'));
  assert.ok(html.includes('記録あり'));
  p.days[0].entries[0].truth = 'REPORTED_BY_012';
  const reported = renderToStaticMarkup(React.createElement(Feed, { projection: cleanProjection(p, 'snapshot') }));
  assert.ok(reported.includes('012からの報告'));
});
