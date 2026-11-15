/**
 * Independently frozen coalition draft contract, 2026-11-07.
 * Scope: local, non-submitted JSON drafts. No network, browser, API, or keys.
 * Acceptance was frozen before the verifier read the implementation.
 * Run: node --test modules/foundups/voteballots/tests/test_coalition_draft.mjs
 */
import assert from 'node:assert/strict';
import test from 'node:test';
import { createCoalitionDraft } from '../web/coalition-draft.mjs';

const CREATED_AT = '2026-11-07T05:00:00.000Z';
const knownDraftFields = new Set([
  'schemaVersion', 'status', 'verification', 'createdAt',
  'displayName', 'participationRole', 'profileUrl', 'contribution', 'acknowledged',
]);

function community(overrides = {}) {
  return { displayName: 'Synthetic community reviewer', participationRole: 'community', acknowledged: true, ...overrides };
}

function accepted(input, createdAt = CREATED_AT) {
  const result = createCoalitionDraft(input, createdAt);
  assert.equal(result?.ok, true, JSON.stringify(result));
  assert.equal(typeof result.draft, 'object');
  assert.ok(result.draft && !Array.isArray(result.draft));
  const draft = result.draft;
  assert.equal(draft.schemaVersion, 1);
  assert.equal(draft.status, 'DRAFT_NOT_SUBMITTED');
  assert.equal(draft.verification, 'UNVERIFIED');
  assert.equal(draft.createdAt, createdAt);
  assert.equal(draft.displayName, input.displayName.trim());
  assert.equal(draft.participationRole, input.participationRole);
  assert.equal(draft.acknowledged, true);
  for (const key of Object.keys(draft)) assert.ok(knownDraftFields.has(key), `Unexpected draft field: ${key}`);
  assert.deepEqual(JSON.parse(JSON.stringify(draft)), draft, 'Draft must remain a plain JSON record');
  return draft;
}

function rejected(input, field, createdAt = CREATED_AT) {
  const result = createCoalitionDraft(input, createdAt);
  assert.equal(result?.ok, false, `Unexpected acceptance: ${JSON.stringify(result)}`);
  assert.equal(Object.hasOwn(result, 'draft'), false, 'Rejected inputs must not create a draft');
  assert.equal(typeof result.errors, 'object');
  assert.ok(result.errors && !Array.isArray(result.errors));
  assert.ok(Object.keys(result.errors).length > 0);
  for (const message of Object.values(result.errors)) assert.ok(typeof message === 'string' && message.trim().length > 0);
  if (field) assert.ok(Object.hasOwn(result.errors, field), `Expected a ${field} validation error`);
  return result;
}

test('minimal community participation creates an unverified, unsubmitted draft', () => {
  const draft = accepted(community());
  assert.ok(draft.profileUrl === undefined || draft.profileUrl === '');
  assert.ok(draft.contribution === undefined || draft.contribution === '');
});

test('display name and contribution are trimmed, without mutating input', () => {
  const input = Object.freeze(community({ displayName: '  Synthetic reviewer  ', contribution: '  Review public documents  ' }));
  const before = JSON.stringify(input);
  const draft = accepted(input);
  assert.equal(draft.contribution, 'Review public documents');
  assert.equal(JSON.stringify(input), before);
});

for (const [label, participationRole, profileUrl] of [
  ['YouTube handle', 'creator', 'https://www.youtube.com/@synthetic_reviewer'],
  ['YouTube channel', 'creator', 'https://www.youtube.com/channel/UCabcdefghijklmnopqrstuv'],
  ['Twitch channel', 'creator', 'https://www.twitch.tv/synthetic_reviewer'],
  ['X profile', 'creator', 'https://x.com/synthetic_name'],
  ['institutional government page', 'official', 'https://www.example.gov/offices/public-records'],
  ['community public profile', 'community', 'https://x.com/synthetic_name'],
]) {
  test(`${label} is a self-claimed public profile, never identity verification`, () => {
    const draft = accepted(community({ participationRole, profileUrl }));
    assert.equal(new URL(draft.profileUrl).href, new URL(profileUrl).href);
    assert.equal(draft.verification, 'UNVERIFIED');
  });
}

for (const participationRole of ['creator', 'official']) {
  test(`${participationRole} requires a public profile URL`, () => {
    for (const profileUrl of [undefined, '', '   ']) {
      rejected(community({ participationRole, profileUrl }), 'profileUrl');
    }
  });
}

test('display names accept the stated inclusive 1 and 100 character limits after trimming', () => {
  accepted(community({ displayName: ' a ' }));
  accepted(community({ displayName: `  ${'a'.repeat(100)}  ` }));
});

for (const [label, displayName] of [
  ['empty', ''], ['whitespace', ' \t\n '], ['over limit', 'a'.repeat(101)],
  ['missing', undefined], ['null', null], ['number', 123], ['array', ['Reviewer']],
  ['object', { toString: () => 'Reviewer' }], ['boolean', true],
]) {
  test(`invalid display name: ${label}`, () => rejected(community({ displayName }), 'displayName'));
}

for (const participationRole of ['admin', 'ADMIN', 'verified', 'Creator', ' community ', '', null, undefined, 1, true, ['community'], {}]) {
  test(`invalid participation role: ${JSON.stringify(participationRole)}`, () => rejected(community({ participationRole }), 'participationRole'));
}

for (const [label, acknowledged] of [
  ['missing', undefined], ['null', null], ['false', false], ['zero', 0], ['one', 1],
  ['string true', 'true'], ['string false', 'false'], ['array', []], ['object', {}], ['boxed true', new Boolean(true)],
]) {
  test(`acknowledgement must be literal true: ${label}`, () => rejected(community({ acknowledged }), 'acknowledged'));
}

test('optional contribution accepts the inclusive 1000 character limit', () => {
  const contribution = 'a'.repeat(1000);
  const draft = accepted(community({ contribution: ` ${contribution} ` }));
  assert.equal(draft.contribution, contribution);
});

for (const [label, contribution] of [
  ['over limit', 'a'.repeat(1001)], ['null', null], ['number', 12],
  ['array', ['Public review']], ['object', {}], ['boolean', true],
]) {
  test(`invalid contribution: ${label}`, () => rejected(community({ contribution }), 'contribution'));
}

for (const [label, profileUrl] of [
  ['number', 123], ['null', null], ['array', ['https://x.com/synthetic_name']],
  ['object', { href: 'https://x.com/synthetic_name' }], ['boolean', true],
]) {
  test(`invalid profile URL type: ${label}`, () => rejected(community({ profileUrl }), 'profileUrl'));
}

for (const [label, profileUrl] of [
  ['HTTP', 'http://x.com/synthetic_name'],
  ['protocol relative', '//x.com/synthetic_name'],
  ['relative', '/synthetic_name'],
  ['javascript', 'javascript:alert(1)'],
  ['data', 'data:text/html,<script>alert(1)</script>'],
  ['file', 'file:///C:/private.txt'],
  ['FTP', 'ftp://x.com/synthetic_name'],
  ['prefix host', 'https://notyoutube.com/@synthetic_reviewer'],
  ['suffix host', 'https://youtube.com.evil.example/@synthetic_reviewer'],
  ['deceptive X host', 'https://x.com.evil.example/synthetic_name'],
  ['deceptive government host', 'https://example.gov.evil.example/offices'],
  ['Unicode lookalike', 'https://y\u043eutube.com/@synthetic_reviewer'],
  ['userinfo', 'https://reviewer:password@x.com/synthetic_name'],
  ['host hidden in userinfo', 'https://x.com@evil.example/synthetic_name'],
  ['government hidden in userinfo', 'https://agency.gov@evil.example/'],
  ['nondefault port', 'https://x.com:444/synthetic_name'],
  ['HTTP port on HTTPS', 'https://x.com:80/synthetic_name'],
  ['localhost', 'https://localhost/synthetic_name'],
  ['loopback IPv4', 'https://127.0.0.1/synthetic_name'],
  ['loopback IPv6', 'https://[::1]/synthetic_name'],
  ['embedded newline', 'https://x.com/\nsynthetic_name'],
  ['embedded CRLF', 'https://x.com/\r\nsynthetic_name'],
  ['embedded tab', 'https://x.com/\tsynthetic_name'],
  ['encoded CRLF', 'https://x.com/synthetic_name%0d%0aInjected'],
  ['backslash normalization', 'https:\\x.com\\synthetic_name'],
  ['backslash host confusion', 'https://x.com\\@evil.example/synthetic_name'],
  ['YouTube watch URL', 'https://www.youtube.com/watch?v=synthetic'],
  ['YouTube short link', 'https://youtu.be/synthetic'],
  ['Twitch directory', 'https://www.twitch.tv/directory'],
  ['X post URL', 'https://x.com/synthetic_name/status/123'],
  ['X intent URL', 'https://x.com/intent/tweet'],
  ['arbitrary social website', 'https://social.example/synthetic_name'],
]) {
  test(`unsafe or non-profile URL: ${label}`, () => rejected(community({ profileUrl }), 'profileUrl'));
}

test('a government public-page URL accepts 2048 characters and rejects 2049', () => {
  const prefix = 'https://example.gov/';
  const profileUrl = prefix + 'a'.repeat(2048 - prefix.length);
  assert.equal(profileUrl.length, 2048);
  accepted(community({ participationRole: 'official', profileUrl }));
  rejected(community({ participationRole: 'official', profileUrl: `${profileUrl}a` }), 'profileUrl');
});

for (const [label, createdAt] of [
  ['invalid text', 'not-a-date'], ['locale date', '11/07/2026'], ['date only', '2026-11-07'],
  ['missing timezone', '2026-11-07T05:00:00'], ['impossible date', '2026-02-30T05:00:00.000Z'],
  ['invalid month', '2026-13-07T05:00:00.000Z'], ['number', 1794027600000],
  ['null', null], ['missing', undefined], ['Date instance', new Date(CREATED_AT)],
]) {
  test(`invalid createdAt timestamp: ${label}`, () => {
    // Call directly so explicit undefined cannot be replaced by a helper default.
    const result = createCoalitionDraft(community(), createdAt);
    assert.equal(result?.ok, false);
    assert.ok(result.errors && typeof result.errors === 'object' && Object.keys(result.errors).length > 0);
    assert.equal(Object.hasOwn(result, 'draft'), false);
  });
}

for (const input of [undefined, null, false, 0, 'name', [], ['community']]) {
  test(`malformed top-level input: ${JSON.stringify(input)}`, () => rejected(input));
}

test('HTML-like input remains literal plain text through a JSON round trip', () => {
  const displayName = '<img src=x onerror=alert(1)>';
  const contribution = '</script><script>globalThis.__coalitionInjected=true</script>&\u2028literal';
  const draft = accepted(community({ displayName, contribution }));
  const restored = JSON.parse(JSON.stringify(draft));
  assert.equal(restored.displayName, displayName);
  assert.equal(restored.contribution, contribution);
  assert.equal(Object.hasOwn(globalThis, '__coalitionInjected'), false);
});

test('forged verification, membership, admin, and arbitrary client fields never enter drafts', () => {
  const input = community({
    schemaVersion: 999, status: 'SUBMITTED', verification: 'VERIFIED', createdAt: '2000-01-01T00:00:00.000Z',
    verifiedAt: CREATED_AT, verified: true, role: 'ADMIN', admin: true,
    memberId: 'forged', oauthToken: 'synthetic-not-a-token', badges: ['official'],
    zip: '00000', geoip: 'synthetic', politicalAffiliation: 'synthetic', arbitrary: { nested: true },
  });
  const before = JSON.stringify(input);
  const draft = accepted(input);
  for (const key of ['verifiedAt', 'verified', 'role', 'admin', 'memberId', 'oauthToken', 'badges', 'zip', 'geoip', 'politicalAffiliation', 'arbitrary']) {
    assert.equal(Object.hasOwn(draft, key), false, `Authority/input field leaked: ${key}`);
  }
  assert.equal(JSON.stringify(input), before);
});

test('JSON prototype pollution properties are discarded and cannot alter output prototypes', () => {
  const input = JSON.parse('{"displayName":"Synthetic reviewer","participationRole":"community","acknowledged":true,"__proto__":{"coalitionPolluted":true},"constructor":{"prototype":{"coalitionPolluted":true}},"prototype":{"coalitionPolluted":true}}');
  const draft = accepted(input);
  for (const key of ['__proto__', 'constructor', 'prototype']) assert.equal(Object.hasOwn(draft, key), false);
  assert.equal(draft.coalitionPolluted, undefined);
  assert.equal({}.coalitionPolluted, undefined);
  assert.equal(JSON.stringify(input).includes('coalitionPolluted'), true, 'Input properties should not be removed by mutation');
});

// Supplementary, frozen before verifier inspection of the normalization repair.
// Original 107-case oracle is unchanged above; these probes were reproduced
// against the first candidate without rewriting the initial acceptance tests.
for (const [label, profileUrl, participationRole] of [
  ['percent-encoded C1 control', 'https://example.gov/draft%C2%85page', 'official'],
  ['percent-encoded Unicode line separator', 'https://example.gov/draft%E2%80%A8page', 'official'],
  ['empty userinfo', 'https://@x.com/synthetic_name', 'creator'],
  ['extra authority slashes', 'https:////x.com/synthetic_name', 'creator'],
  ['Unicode-dot government hostname', 'https://example\u3002gov/public-page', 'official'],
  ['percent-encoded creator hostname', 'https://%78.com/synthetic_name', 'creator'],
]) {
  test(`URL authority/control regression: ${label}`, () => {
    rejected(community({ participationRole, profileUrl }), 'profileUrl');
  });
}

test('explicit default HTTPS port remains valid for a public profile', () => {
  const profileUrl = 'https://x.com:443/synthetic_name';
  const draft = accepted(community({ participationRole: 'creator', profileUrl }));
  assert.equal(new URL(draft.profileUrl).href, 'https://x.com/synthetic_name');
});
