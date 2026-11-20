import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const sourceUrl = new URL('../../../../public/js/reddog-public-client.js', import.meta.url);
const source = await readFile(sourceUrl, 'utf8');
const clientModule = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);
const {
  RedDogPublicClient,
  createMemberConversationAdapter,
  encounterPayload,
  normalizePublicFoundupId,
  resolvePublicApiRoot,
  turnPayload,
} = clientModule;

const ORIGIN = 'https://foundups.com';
const ROOT = '/api/reddog/public';
const answer = (body, status = 200) => new Response(JSON.stringify(body), {
  status,
  headers: { 'Content-Type': 'application/json' },
});
const session = {
  token: 'synthetic-public-token',
  nonce: 'a'.repeat(64),
  revision: 0,
  remaining_turns: 10,
  expires_at: 2000,
  idle_expires_at: 1500,
};

assert.equal(resolvePublicApiRoot('', ORIGIN), '');
assert.equal(resolvePublicApiRoot('https://api.example/api/reddog/public', ORIGIN), '');
assert.equal(resolvePublicApiRoot('/api/private', ORIGIN), '');
assert.equal(resolvePublicApiRoot(ROOT, ORIGIN), ORIGIN + ROOT);
assert.deepEqual(encounterPayload(), {
  consent: true,
  consent_version: 'reddog.public-guest.v1',
  actor_claim: 'unspecified',
});
assert.deepEqual(turnPayload(session, ' Public question '), {
  nonce: session.nonce,
  revision: 0,
  message: 'Public question',
});
assert.deepEqual(turnPayload(session, 'What is this?', 'hpc'), {
  nonce: session.nonce,
  revision: 0,
  message: 'What is this?',
  foundup_id: 'hpc',
});
assert.equal(normalizePublicFoundupId('private/path'), '');
assert.throws(() => turnPayload(session, 'What is this?', 'private/path'), {code: 'input'});

const calls = [];
let queue = [];
const fetchImpl = async (url, options) => {
  calls.push({ url, options, body: JSON.parse(options.body) });
  const next = queue.shift();
  if (!next) throw new Error('Unexpected request');
  if (next instanceof Error) throw next;
  return typeof next === 'function' ? await next() : next;
};
const client = new RedDogPublicClient('foundups', ROOT, { origin: ORIGIN, fetchImpl });
assert.equal(calls.length, 0, 'construction must not call the network');

queue = [answer(session)];
await client.start();
assert.equal(calls[0].url, `${ORIGIN}${ROOT}/foundups/encounter`);
assert.deepEqual(calls[0].body, encounterPayload());
assert.equal(calls[0].options.credentials, 'omit');
assert.equal(calls[0].options.headers.Authorization, undefined);

queue = [answer({
  revision: 1,
  nonce: 'b'.repeat(64),
  remaining_turns: 9,
  reply: 'Public answer.',
  disclosure: 'public',
  effect_ceiling: 'NONE',
})];
await client.send('What is this?', 'hpc');
assert.deepEqual(calls.at(-1).body, {
  nonce: session.nonce,
  revision: 0,
  message: 'What is this?',
  foundup_id: 'hpc',
});
assert.deepEqual(
  Object.keys(calls.at(-1).body).sort(),
  ['foundup_id', 'message', 'nonce', 'revision']
);
assert.equal(calls.at(-1).options.headers.Authorization, 'Bearer synthetic-public-token');

queue = [
  answer({ revision: 2, nonce: 'c'.repeat(64), remaining_turns: 8,
    reply: 'Unexpected response scope', disclosure: 'private', effect_ceiling: 'NONE' }),
  answer({ revision: 2, nonce: 'c'.repeat(64), remaining_turns: 8, in_flight: false }),
];
await assert.rejects(client.send('Check scope'), error => error.code === 'uncertain');

queue = [
  new Error('lost after acceptance'),
  answer({ revision: 2, nonce: 'c'.repeat(64), remaining_turns: 8, in_flight: false }),
];
await assert.rejects(client.send('Do not replay me'), (error) => error.code === 'uncertain');
assert.deepEqual(calls.slice(-2).map((call) => call.url.split('/').at(-1)), ['turn', 'status']);
assert.equal(calls.filter((call) => call.body.message === 'Do not replay me').length, 1);
assert.ok(calls.every((call) => call.url.startsWith(ORIGIN + ROOT)));

queue = [answer({ withdrawn: true })];
await client.end();
assert.equal(client.session, null);

let adapterFetches = 0;
const unavailable = createMemberConversationAdapter({
  apiRoot: '',
  origin: ORIGIN,
  fetchImpl: async () => { adapterFetches += 1; },
  document: null,
});
assert.deepEqual(unavailable.getAvailability({ foundupId: 'hpc' }), {
  available: false,
  reason: 'Public guest conversation is not configured on this deployment.',
});
assert.equal(unavailable.open({ foundupId: 'hpc' }), false);
assert.equal(adapterFetches, 0);

class FakeElement {
  constructor(tag, document) {
    this.tagName = tag.toUpperCase();
    this.ownerDocument = document;
    this.children = [];
    this.attributes = new Map();
    this.listeners = new Map();
    this.className = '';
    this.textContent = '';
    this.hidden = false;
    this.disabled = false;
    this.checked = false;
    this.open = false;
    this.value = '';
    this.isConnected = true;
  }
  append(...nodes) { for (const node of nodes) this.appendChild(node); }
  appendChild(node) { this.children.push(node); return node; }
  setAttribute(name, value) { this.attributes.set(name, String(value)); }
  removeAttribute(name) { this.attributes.delete(name); if (name === 'open') this.open = false; }
  addEventListener(type, listener) {
    const handlers = this.listeners.get(type) || [];
    handlers.push(listener);
    this.listeners.set(type, handlers);
  }
  async dispatch(type) {
    for (const listener of this.listeners.get(type) || []) {
      await listener({ preventDefault() {} });
    }
  }
  replaceChildren(...nodes) { this.children = []; this.append(...nodes); }
  querySelector(selector) {
    const matches = (node) => selector.startsWith('.')
      ? node.className.split(/\s+/).includes(selector.slice(1))
      : selector.startsWith('[') && node.attributes.has(selector.slice(1, -1));
    for (const child of this.children) {
      if (matches(child)) return child;
      const nested = child.querySelector?.(selector);
      if (nested) return nested;
    }
    return null;
  }
  showModal() { this.open = true; }
  close() {
    this.open = false;
    for (const listener of this.listeners.get('close') || []) listener({});
  }
  focus() { this.ownerDocument.activeElement = this; }
}

class FakeDocument {
  constructor() {
    this.location = { origin: ORIGIN };
    this.body = new FakeElement('body', this);
    this.activeElement = null;
  }
  createElement(tag) { return new FakeElement(tag, this); }
  createTextNode(text) {
    const node = new FakeElement('#text', this);
    node.textContent = text;
    return node;
  }
  querySelector() { return null; }
}

const uiDocument = new FakeDocument();
const opener = uiDocument.createElement('button');
uiDocument.body.appendChild(opener);
opener.focus();
const uiCalls = [];
const uiQueue = [answer(session)];
const uiAdapter = createMemberConversationAdapter({
  apiRoot: ROOT,
  origin: ORIGIN,
  document: uiDocument,
  fetchImpl: async (url, options) => {
    uiCalls.push({ url, body: JSON.parse(options.body) });
    return uiQueue.shift();
  },
});
assert.deepEqual(uiAdapter.getAvailability({ foundupId: 'hpc', bindingRevision: 1 }), { available: true });
assert.equal(uiAdapter.open({ foundupId: 'hpc', bindingRevision: 1 }), true);
const dialog = uiDocument.body.children.at(-1);
assert.equal(dialog.tagName, 'DIALOG');
assert.equal(dialog.open, true);
assert.equal(uiCalls.length, 0, 'opening the modal must not start a guest session');
assert.match(dialog.querySelector('.reddog-guest-disclosure').textContent, /FoundUp ID “hpc”/);
const uiConsent = dialog.querySelector('[data-reddog-guest-consent]');
const uiStart = dialog.querySelector('.reddog-guest-start');
uiConsent.checked = true;
await uiConsent.dispatch('change');
assert.equal(uiStart.disabled, false);
await uiStart.dispatch('click');
assert.deepEqual(uiCalls[0].body, encounterPayload());
assert.equal(dialog.querySelector('.reddog-guest-form').hidden, false);
const uiDraft = dialog.querySelector('.reddog-guest-form').children.find(el => el.tagName === 'TEXTAREA');
uiDraft.value = 'Unsent local question';
await dialog.querySelector('.reddog-guest-close').dispatch('click');
assert.equal(dialog.open, false);
assert.equal(uiDocument.activeElement, opener, 'modal close must return focus');
uiAdapter.syncContext({ foundupId: 'hpc', bindingRevision: 2 });
assert.equal(uiConsent.checked, false, 'principal/context rebind must clear consent');
assert.equal(uiDraft.value, '', 'a new binding cannot recover a previous unsent question');
assert.equal(dialog.querySelector('.reddog-guest-messages').children.length, 0);
assert.equal(uiAdapter.open({ foundupId: 'hpc', access: 'unknown', bindingRevision: 3 }), false);
assert.equal(uiAdapter.open({ selectionState: 'invalid', bindingRevision: 4 }), false);
assert.equal(uiAdapter.open({ foundupId: 'private/path', bindingRevision: 5 }), false);
assert.equal(uiCalls.length, 1, 'a blocked or changed binding must not start a session');

for (const forbidden of [
  'localStorage', 'sessionStorage', 'document.cookie', 'SpeechRecognition',
  'speechSynthesis', 'chat-3wqfxfmvuq-uc.a.run.app',
]) {
  assert.equal(source.includes(forbidden), false, `${forbidden} must not enter the guest client`);
}

console.log('PASS: explicit same-origin config, consent, canonical payloads, no load request, no replay/fallback/private state.');
