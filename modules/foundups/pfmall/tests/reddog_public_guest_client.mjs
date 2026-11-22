import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const sourceUrl = new URL('../../../../public/js/reddog-public-client.js', import.meta.url);
const source = await readFile(sourceUrl, 'utf8');
const focusSourceUrl = new URL('../../../../public/js/reddog-fractal-focus.js', import.meta.url);
const focusSource = await readFile(focusSourceUrl, 'utf8');
const focusDataUrl = `data:text/javascript;base64,${Buffer.from(focusSource).toString('base64')}`;
const resolvedSource = source.replace(
  "import './reddog-fractal-focus.js';",
  `import '${focusDataUrl}';`,
);
assert.notEqual(resolvedSource, source, 'fixture resolves the real side-effect dependency');
const clientModule = await import(`data:text/javascript;base64,${Buffer.from(resolvedSource).toString('base64')}`);
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
assert.equal(normalizePublicFoundupId('hpc\n'), '', 'a trailing line terminator is not an exact ID');
assert.throws(() => turnPayload(session, 'What is this?', 'private/path'), {code: 'input'});
assert.throws(() => turnPayload(session, 'What is this?', 'hpc\n'), {code: 'input'});

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
const fractalFocus = dialog.querySelector('.reddog-guest-fractal-focus');
assert.equal(fractalFocus.hidden, true, 'focus face waits for guest admission');
const uiConsent = dialog.querySelector('[data-reddog-guest-consent]');
const uiStart = dialog.querySelector('.reddog-guest-start');
uiConsent.checked = true;
await uiConsent.dispatch('change');
assert.equal(uiStart.disabled, false);
await uiStart.dispatch('click');
assert.deepEqual(uiCalls[0].body, encounterPayload());
assert.equal(dialog.querySelector('.reddog-guest-form').hidden, false);
const uiDraft = dialog.querySelector('.reddog-guest-form').children.find(el => el.tagName === 'TEXTAREA');
assert.equal(fractalFocus.hidden, false);
assert.equal(fractalFocus.querySelector('[data-reddog-fractal-path]').textContent, 'Mall › hpc');
const ask = fractalFocus.querySelector('[data-reddog-fractal-ask]');
assert.ok(ask, 'selected admitted focus exposes the shared ask action');
await ask.dispatch('click');
assert.equal(uiDraft.value, 'What should I know about hpc?');
assert.equal(uiDocument.activeElement, uiDraft, 'Ask focuses the live local question');
assert.equal(uiCalls.length, 1, 'Ask neither sends nor starts another request');
uiDraft.value = 'Unsent local question';
await ask.dispatch('click');
assert.equal(uiDraft.value, 'Unsent local question', 'Ask never overwrites an existing draft');
assert.equal(uiCalls.length, 1);
uiDraft.value = '';
await dialog.querySelector('.reddog-guest-close').dispatch('click');
assert.equal(dialog.open, false);
assert.equal(uiDocument.activeElement, opener, 'modal close must return focus');
await ask.dispatch('click');
assert.equal(uiDraft.value, '', 'a hidden stale Ask control cannot stage a draft');
assert.equal(uiCalls.length, 1);
assert.equal(uiAdapter.open({ foundupId: 'hpc', bindingRevision: 1 }), true);
assert.ok(fractalFocus.querySelector('[data-reddog-fractal-ask]'),
  'render after showModal restores Ask when the same admitted session reopens');
await dialog.querySelector('.reddog-guest-close').dispatch('click');
uiAdapter.syncContext({ foundupId: 'hpc', bindingRevision: 2 });
assert.equal(uiConsent.checked, false, 'principal/context rebind must clear consent');
assert.equal(uiDraft.value, '', 'a new binding cannot recover a previous unsent question');
assert.equal(dialog.querySelector('.reddog-guest-messages').children.length, 0);
assert.equal(fractalFocus.hidden, true, 'rebind removes the admitted focus face');
assert.equal(fractalFocus.children.length, 0);
assert.equal(uiAdapter.open({ foundupId: 'hpc', access: 'unknown', bindingRevision: 3 }), false);
assert.equal(uiAdapter.open({ selectionState: 'invalid', bindingRevision: 4 }), false);
assert.equal(uiAdapter.open({ foundupId: 'private/path', bindingRevision: 5 }), false);
assert.equal(uiCalls.length, 1, 'a blocked or changed binding must not start a session');

const zeroDocument = new FakeDocument();
const zeroAdapter = createMemberConversationAdapter({
  apiRoot: ROOT,
  origin: ORIGIN,
  document: zeroDocument,
  fetchImpl: async () => answer({ ...session, remaining_turns: 0 }),
});
assert.equal(zeroAdapter.open({ foundupId: 'hpc', bindingRevision: 1 }), true);
const zeroDialog = zeroDocument.body.children.at(-1);
const zeroConsent = zeroDialog.querySelector('[data-reddog-guest-consent]');
zeroConsent.checked = true;
await zeroConsent.dispatch('change');
await zeroDialog.querySelector('.reddog-guest-start').dispatch('click');
const zeroDraft = zeroDialog.querySelector('.reddog-guest-form').children.find(el => el.tagName === 'TEXTAREA');
assert.equal(zeroDraft.disabled, true, 'zero allowance disables the authoritative input');
assert.equal(zeroDialog.querySelector('[data-reddog-fractal-path]').textContent, 'Mall › hpc');
assert.equal(zeroDialog.querySelector('[data-reddog-fractal-ask]'), null,
  'zero allowance cannot expose Ask');

const pureContainer = uiDocument.createElement('section');
const selectedByAsk = [];
globalThis.RedDogFractalFocus.renderFractalFocus(pureContainer, {
  state: 'selected', foundupId: 'pottery-lab', canAsk: true,
}, foundupId => selectedByAsk.push(foundupId));
assert.equal(pureContainer.querySelector('[data-reddog-fractal-path]').textContent,
  'Mall › pottery-lab', 'the shared face is not HPC-specific');
const detachedAsk = pureContainer.querySelector('[data-reddog-fractal-ask]');
globalThis.RedDogFractalFocus.renderFractalFocus(pureContainer, {
  state: 'selected', foundupId: 'garden-lab', canAsk: true,
}, foundupId => selectedByAsk.push(foundupId));
await detachedAsk.dispatch('click');
assert.deepEqual(selectedByAsk, [], 'a detached Ask cannot use its prior binding');
await pureContainer.querySelector('[data-reddog-fractal-ask]').dispatch('click');
assert.deepEqual(selectedByAsk, ['garden-lab']);
globalThis.RedDogFractalFocus.renderFractalFocus(pureContainer, {
  state: 'selected', foundupId: 'pottery-lab\n', canAsk: true,
}, foundupId => selectedByAsk.push(foundupId));
assert.equal(pureContainer.querySelector('[data-reddog-fractal-path]').textContent,
  'Mall · Focus unavailable');
assert.equal(pureContainer.querySelector('[data-reddog-fractal-ask]'), null);
assert.equal(uiAdapter.open({ foundupId: 'pottery-lab\n', bindingRevision: 6 }), false,
  'malformed selected context is unavailable, not generic');

for (const forbidden of [
  'localStorage', 'sessionStorage', 'document.cookie', 'SpeechRecognition',
  'speechSynthesis', 'chat-3wqfxfmvuq-uc.a.run.app',
]) {
  assert.equal(source.includes(forbidden), false, `${forbidden} must not enter the guest client`);
}

console.log('PASS: explicit same-origin config, consent, canonical payloads, no load request, no replay/fallback/private state.');
