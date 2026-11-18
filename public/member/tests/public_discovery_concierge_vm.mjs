/**
 * Execute the actual account concierge and gesture owner with a bounded DOM.
 * Run: node public/member/tests/public_discovery_concierge_vm.mjs
 *
 * Recovery note: this fixture was rebuilt against current source and the actual
 * member plane/search template after the earlier scratch checkout was lost.
 * It is new verification, not a claim to have recovered the old fixture bytes.
 * Reuses the existing Mall VM approach: Node built-ins, observed owner calls,
 * no network, browser layout, real authentication or membership/payment proof.
 */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { runInNewContext } from 'node:vm';
import test from 'node:test';

const memberRoot = dirname(dirname(fileURLToPath(import.meta.url)));
const source = readFileSync(join(memberRoot, 'js/account-concierge.js'), 'utf8');
const gestureSource = readFileSync(join(memberRoot, 'js/gesture-engine.js'), 'utf8');
const memberHTML = readFileSync(join(memberRoot, 'index.html'), 'utf8');
const planeHTML = memberHTML.match(/<aside\b[^>]*id="accountPlane"[^>]*>[\s\S]*?<\/aside>/)?.[0];
const formHTML = memberHTML.match(/<template\b[^>]*id="move2japanSearchTemplate"[^>]*>([\s\S]*?)<\/template>/)?.[1];
assert.ok(planeHTML && formHTML, 'fixture uses the real member plane and domain template');

const escapeHTML = value => String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
const decode = value => String(value).replace(/&#x([\da-f]+);/gi, (_, hex) => String.fromCodePoint(parseInt(hex, 16)))
  .replaceAll('&quot;', '"').replaceAll('&#39;', "'").replaceAll('&lt;', '<').replaceAll('&gt;', '>').replaceAll('&amp;', '&');
const voidTags = new Set(['INPUT', 'IMG', 'BR', 'HR', 'META', 'LINK', 'PATH', 'POLYLINE', 'LINE']);

class Element {
  constructor(tag, document) {
    this.tagName = tag.toUpperCase();
    this.nodeType = 1;
    this.ownerDocument = document;
    this.attributes = new Map();
    this.children = [];
    this.events = new Map();
    this.style = {};
    this.dataset = {};
    this.scrollTop = 0;
    this.scrollHeight = 1300;
    this.clientHeight = 600;
    this._value = '';
    this._text = '';
    const classes = () => new Set((this.getAttribute('class') || '').split(/\s+/).filter(Boolean));
    this.classList = {
      contains: name => classes().has(name),
      add: (...names) => this.setAttribute('class', [...new Set([...classes(), ...names])].join(' ')),
      remove: (...names) => this.setAttribute('class', [...classes()].filter(name => !names.includes(name)).join(' ')),
      toggle: (name, force) => {
        const add = force === undefined ? !classes().has(name) : force;
        if (add) this.classList.add(name); else this.classList.remove(name);
        return add;
      }
    };
  }
  get id() { return this.getAttribute('id') || ''; }
  set id(value) { this.setAttribute('id', value); }
  get className() { return this.getAttribute('class') || ''; }
  set className(value) { this.setAttribute('class', value); }
  get hidden() { return this.hasAttribute('hidden'); }
  set hidden(value) { if (value) this.setAttribute('hidden', ''); else this.removeAttribute('hidden'); }
  get disabled() { return this.hasAttribute('disabled'); }
  set disabled(value) { if (value) this.setAttribute('disabled', ''); else this.removeAttribute('disabled'); }
  get value() { return this._value; }
  set value(value) { this._value = String(value); }
  get src() { return this.getAttribute('src') || ''; }
  set src(value) { this.setAttribute('src', value); }
  get href() { return this.getAttribute('href') || ''; }
  get tabIndex() {
    if (this.hasAttribute('tabindex')) return Number(this.getAttribute('tabindex'));
    return ['BUTTON', 'INPUT', 'SELECT', 'TEXTAREA', 'SUMMARY'].includes(this.tagName) ||
      (this.tagName === 'A' && this.hasAttribute('href')) ? 0 : -1;
  }
  get isConnected() { return !!this.ownerDocument && this.ownerDocument.contains(this); }
  get firstChild() { return this.children[0] || null; }
  get nextSibling() {
    const siblings = this.parentElement?.children || [];
    return siblings[siblings.indexOf(this) + 1] || null;
  }
  get textContent() { return this._text + this.children.map(child => child.textContent).join(''); }
  set textContent(value) { this.replaceChildren(); this._text = String(value); }
  get innerHTML() { return escapeHTML(this._text) + this.children.map(child => child.outerHTML).join(''); }
  get outerHTML() {
    const attrs = [...this.attributes].map(([key, value]) => ` ${key}="${escapeHTML(value).replaceAll('"', '&quot;')}"`).join('');
    return `<${this.tagName.toLowerCase()}${attrs}>${this.innerHTML}</${this.tagName.toLowerCase()}>`;
  }
  set innerHTML(html) {
    this.replaceChildren();
    this._text = '';
    const stack = [this];
    for (const token of String(html).match(/<!--[\s\S]*?-->|<[^>]+>|[^<]+/g) || []) {
      if (token.startsWith('<!--')) continue;
      if (token.startsWith('</')) {
        const tag = token.match(/^<\/([\w-]+)/)?.[1].toUpperCase();
        const at = stack.map(node => node.tagName).lastIndexOf(tag);
        if (at > 0) stack.length = at;
      } else if (token.startsWith('<')) {
        const open = token.match(/^<([\w-]+)([\s\S]*?)\/?>$/);
        if (!open) continue;
        const element = new Element(open[1], this.ownerDocument);
        for (const attr of open[2].matchAll(/([^\s=/>]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+)))?/g)) {
          element.setAttribute(attr[1], decode(attr[2] ?? attr[3] ?? attr[4] ?? ''));
        }
        stack.at(-1).appendChild(element);
        if (!voidTags.has(element.tagName) && !token.endsWith('/>')) stack.push(element);
      } else stack.at(-1)._text += decode(token);
    }
  }
  setAttribute(name, value) {
    this.attributes.set(name, String(value));
    if (name.startsWith('data-')) this.dataset[name.slice(5).replace(/-([a-z])/g, (_, char) => char.toUpperCase())] = String(value);
    if (name === 'value') this._value = String(value);
    if (name === 'style') for (const rule of String(value).split(';')) {
      const [key, val] = rule.split(':');
      if (key?.trim()) this.style[key.trim()] = val?.trim() || '';
    }
  }
  getAttribute(name) { return this.attributes.get(name) ?? null; }
  hasAttribute(name) { return this.attributes.has(name); }
  removeAttribute(name) { this.attributes.delete(name); }
  appendChild(child) { return this.insertBefore(child, null); }
  insertBefore(child, reference) {
    child.remove();
    const at = reference ? this.children.indexOf(reference) : this.children.length;
    assert.ok(at >= 0, 'insertBefore reference belongs to parent');
    this.children.splice(at, 0, child);
    child.parentElement = child.parentNode = this;
    return child;
  }
  remove() {
    if (!this.parentElement) return;
    const parent = this.parentElement;
    parent.children.splice(parent.children.indexOf(this), 1);
    this.parentElement = this.parentNode = null;
  }
  replaceChildren() {
    if (this.children.some(child => child.contains(this.ownerDocument?.activeElement))) {
      this.ownerDocument.activeElement = this.ownerDocument.body;
    }
    for (const child of [...this.children]) child.remove();
  }
  contains(node) { return this === node || this.children.some(child => child.contains(node)); }
  matches(selector) {
    return selector.split(',').some(part => {
      let query = part.trim();
      let rejected = false;
      query = query.replace(/:not\(([^)]+)\)/g, (_, inner) => { if (this.matches(inner)) rejected = true; return ''; });
      if (rejected) return false;
      if (query.includes(':disabled')) {
        if (!this.disabled && !this.parentElement?.closest('fieldset[disabled]')) return false;
        query = query.replace(':disabled', '');
      }
      const tag = query.match(/^[a-z][\w-]*/i)?.[0];
      if (tag && this.tagName !== tag.toUpperCase()) return false;
      for (const match of query.matchAll(/([.#])([\w-]+)/g)) {
        if (match[1] === '#' ? this.id !== match[2] : !this.classList.contains(match[2])) return false;
      }
      for (const match of query.matchAll(/\[([\w-]+)(?:="([^"]*)")?\]/g)) {
        if (!this.hasAttribute(match[1]) || (match[2] !== undefined && this.getAttribute(match[1]) !== match[2])) return false;
      }
      return true;
    });
  }
  closest(selector) { for (let node = this; node; node = node.parentElement) if (node.matches(selector)) return node; return null; }
  querySelectorAll(selector) {
    const result = [];
    for (const child of this.children) {
      if (child.matches(selector)) result.push(child);
      result.push(...child.querySelectorAll(selector));
    }
    return result;
  }
  querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
  getClientRects() {
    for (let node = this; node; node = node.parentElement) if (node.hidden || node.style.display === 'none') return [];
    return this.isConnected ? [{}] : [];
  }
  focus() {
    if (!this.isConnected || this.ownerDocument.activeElement === this) return;
    this.ownerDocument.activeElement = this;
    this.fire('focusin');
  }
  scrollIntoView() { this.scrolledIntoView = true; }
  addEventListener(type, handler, options = {}) {
    const config = typeof options === 'boolean' ? { capture: options } : options;
    this.events.set(type, [...(this.events.get(type) || []), { handler, ...config }]);
  }
  removeEventListener(type, handler) { this.events.set(type, (this.events.get(type) || []).filter(entry => entry.handler !== handler)); }
  dispatchEvent(event) { this.fire(event.type, event); return !event.defaultPrevented; }
  fire(type, values = {}) {
    const event = { type, target: this, bubbles: true, defaultPrevented: false,
      preventDefault() { this.defaultPrevented = true; },
      stopPropagation() { this.stopped = true; },
      stopImmediatePropagation() { this.stopped = this.immediate = true; }, ...values };
    const chain = [];
    for (let node = event.target; node; node = node.parentElement) chain.push(node);
    function invoke(node, capture) {
      event.currentTarget = node;
      for (const entry of [...(node.events.get(type) || [])]) {
        if (!!entry.capture !== capture) continue;
        entry.handler(event);
        if (entry.once) node.removeEventListener(type, entry.handler);
        if (event.immediate) break;
      }
    }
    for (const node of [...chain].reverse()) { invoke(node, true); if (event.stopped) break; }
    if (!event.stopped) for (const node of chain) { invoke(node, false); if (event.stopped || !event.bubbles) break; }
    event.currentTarget = null;
    return event;
  }
}

function createFixture(mode = 'product-discovery', setup) {
  const doc = new Element('document');
  doc.ownerDocument = doc;
  doc.createElement = tag => new Element(tag, doc);
  doc.getElementById = id => doc.querySelector('#' + id);
  doc.body = doc.createElement('body');
  doc.appendChild(doc.body);
  doc.activeElement = doc.body;
  doc.body.innerHTML = '<div id="accountPlaneScrim"></div>' + planeHTML
    + '<div class="mall-shell"><header data-anchor="top"><button id="mallAvatarTrigger"><img src="" style="display:none"><span class="account-avatar-placeholder"></span></button></header>'
    + '<button id="topFilters" data-reddog-open-discovery>Filters</button><div id="houses">Houses stay here</div>'
    + '<div id="redDogAnchor"><button id="redDogBtn"><span data-reddog-anchor-state="idle"></span></button>'
    + '<div id="redDogSummary" hidden><div data-reddog-summary-content></div></div><div id="redDogListening" hidden></div></div></div>';
  const plane = doc.getElementById('accountPlane');
  if (mode) plane.setAttribute('data-reddog-mode', mode);
  if (mode === 'public-discovery') {
    for (const selector of ['[data-reddog-state]', '[data-reddog-identity]', '[data-reddog-foundups]', '[data-reddog-invites]', '[data-reddog-options]', '[data-reddog-concierge]']) {
      plane.querySelector(selector)?.remove();
    }
  }
  const staging = doc.createElement('div');
  staging.innerHTML = formHTML;
  doc.body.appendChild(staging);
  const form = doc.getElementById('propertySearchPanel');
  const query = doc.getElementById('propertyQuery');
  const effects = [];
  const playerReads = [];
  const events = [];
  let clock = 10000, timerID = 0;
  const timers = new Map();
  const fieldCatalog = [{ foundup_id: 'move2japan', listing_id: 'one' }, { foundup_id: 'move2japan', listing_id: 'two' }];
  const field = { getProjection: () => 'default', getCatalog: () => fieldCatalog,
    requestDensity: id => { effects.push(['density', id]); return { applied: true }; },
    setMotionMode: mode => effects.push(['motion', mode]) };
  for (const name of ['initialize', 'updateCatalog', 'setProjection', 'resetProjection', 'projectPersonalMall', 'searchCatalog', 'searchByCreator', 'filterByCategory', 'filterByTag', 'clearFieldScope', 'setLayoutMode', 'enterFoundUp']) {
    field[name] = (...args) => { effects.push([name, ...args]); return true; };
  }
  const windowEvents = new Map();
  const sb = { document: doc, console: { log() {}, warn() {} }, URL,
    location: { href: 'https://foundups.com/member/?foundup=move2japan&admitted=true' },
    Date: class extends Date { static now() { return clock; } },
    setTimeout: (fn, delay = 0) => { const id = ++timerID; timers.set(id, { fn, at: clock + delay }); return id; },
    clearTimeout: id => timers.delete(id),
    CustomEvent: function (type, options) { this.type = type; this.detail = options?.detail; },
    fetch: () => { effects.push(['fetch']); throw new Error('No network belongs to this controller'); },
    navigator: { clipboard: { writeText: value => { effects.push(['copy', value]); return Promise.resolve(); } } },
    Clerk: { user: { id: 'signed-in-but-not-admitted' },
      openUserProfile: () => effects.push(['profile', plane.classList.contains('open'), doc.querySelector('.mall-shell').hasAttribute('inert')]),
      signOut: () => { effects.push(['signout']); return Promise.resolve(); } },
    mallTileField: field,
    mallPlanes: { isOpen: () => false, closeView: () => effects.push(['closeDetail']) },
    mallVideoPlayer: {
      getSavedVideos: () => { playerReads.push('saved'); return {}; },
      getHistory: () => { playerReads.push('history'); return []; },
      clearHistory: () => effects.push(['clearHistory']),
      open: (...args) => effects.push(['player', ...args]) },
    addEventListener: (type, fn) => windowEvents.set(type, [...(windowEvents.get(type) || []), fn]) };
  sb.window = sb;
  doc.addEventListener('reddog:command', event => events.push(event.detail));
  setup?.({ doc, plane, form, query, sb });
  runInNewContext(gestureSource, sb, { filename: 'gesture-engine.js' });
  runInNewContext(source, sb, { filename: 'account-concierge.js' });
  function advance(ms) {
    const target = clock + ms;
    for (;;) {
      const next = [...timers].filter(([, timer]) => timer.at <= target).sort((a, b) => a[1].at - b[1].at)[0];
      if (!next) break;
      clock = next[1].at; timers.delete(next[0]); next[1].fn();
    }
    clock = target;
  }
  function swipe(element, from, to) {
    element.fire('touchstart', { touches: [{ clientX: 100, clientY: from }] });
    element.fire('touchmove', { touches: [{ clientX: 100, clientY: to }] });
    element.fire('touchend', { touches: [], changedTouches: [{ clientX: 100, clientY: to }] });
  }
  const $ = selector => doc.querySelector(selector);
  return { doc, sb, api: sb.redDog, plane, form, query, effects, events, playerReads, fieldCatalog, advance, swipe, $, timers, windowEvents };
}

function register(fixture) {
  assert.equal(fixture.api.registerDiscoveryAdapter({ element: fixture.form, focusElement: fixture.query }), true);
}
const identity = { id: 'member-one', firstName: 'Aiko', imageUrl: 'https://example.test/member.png' };
const registeredCatalog = [{ foundup_id: 'move2japan', title: 'Move2Japan', category: 'housing', status: 'active' },
  { foundup_id: 'gotjunk', title: 'GotJunk', category: 'clothes', status: 'active' }];
const globalMethods = ['setCategory', 'populateMyMall', 'openPersonalMall', 'searchCatalog', 'searchByCreator', 'clearSearch', 'toggleChannel'];

test('standalone public discovery retains its small API and moves the same form', () => {
  const f = createFixture('public-discovery');
  register(f);
  assert.equal(f.api, f.sb.accountConcierge);
  assert.equal(f.api.setIdentity, undefined);
  assert.equal(f.form.parentElement, f.$('[data-reddog-discovery]'));
  f.$('#topFilters').fire('click');
  assert.equal(f.api.isOpen(), true);
  assert.equal(f.doc.activeElement, f.query);
  assert.equal(f.$('.mall-shell').hasAttribute('inert'), true);
  f.$('[data-reddog-close]').fire('click');
  assert.equal(f.doc.activeElement, f.$('#topFilters'));
});

test('product presentation starts as a guest even with Clerk user and query flags', () => {
  const f = createFixture(); register(f);
  assert.equal(f.api.isDiscoveryAdmitted(), false);
  for (const selector of ['[data-reddog-identity]', '[data-reddog-foundups]', '[data-reddog-invites]', '[data-reddog-options]', '[data-reddog-concierge]']) {
    assert.equal(f.$(selector).hidden, true, selector);
    assert.equal(f.$(selector).hasAttribute('inert'), true, selector);
  }
  assert.equal(f.$('[data-reddog-discovery]').hidden, false);
  assert.equal(new URL(f.$('[data-reddog-discovery-account]').href, f.sb.location.href).href,
    'https://foundups.com/member/?account=1');
  f.$('#redDogBtn').fire('click', { detail: 1 });
  assert.equal(f.api.isOpen(), true, 'guest search does not wait for account initialization or a gesture timer');
  assert.equal(f.playerReads.length, 0);
  assert.deepEqual(f.effects, []);
});

test('guest APIs and member DOM actions cannot acquire or display private state', async () => {
  const f = createFixture(); register(f);
  assert.equal(f.api.setIdentity(identity, { username: 'private' }), false);
  assert.equal(f.api.setFoundUps(registeredCatalog), false);
  assert.equal(f.api.setInvites([{ code: 'SECRET', status: 'active' }]), false);
  for (const name of ['showSummary', 'startListening', 'openModes', 'openTools', 'openChannels', 'openSaved', 'openHistory', 'clearHistory', 'getContext', 'getChannels']) {
    assert.equal(f.api[name](), false, name);
  }
  for (const name of globalMethods) assert.equal(f.api[name]('all'), false, name);
  f.doc.fire('reddog:verification_alert', { detail: { alert_id: 'guest-secret', summary: 'Private' } });
  f.$('[data-account-signout]').fire('click');
  f.$('[data-account-invites-toggle]').fire('click');
  await Promise.resolve();
  assert.equal(f.$('[data-account-invites-drawer]').classList.contains('open'), false);
  assert.equal(f.$('[data-account-name]').textContent, '');
  assert.equal(f.$('[data-account-foundups-grid]').children.length, 0);
  assert.deepEqual(f.effects, []);
  assert.deepEqual(f.playerReads, []);
  assert.deepEqual(f.events, []);
});

test('admission requires a strict boolean and restores only prior presentation flags', () => {
  const f = createFixture('product-discovery', ({ plane }) => plane.querySelector('[data-reddog-invites]').hidden = true);
  for (const value of ['true', 1, {}, [], null, undefined]) assert.equal(f.api.setDiscoveryAdmission(value), false);
  assert.equal(f.api.setDiscoveryAdmission(true), true);
  assert.equal(f.$('[data-reddog-identity]').hidden, false);
  assert.equal(f.$('[data-reddog-invites]').hidden, true, 'an independently hidden member section stays hidden');
  assert.equal(f.$('[data-reddog-discovery-account]').hidden, true);
  assert.equal(f.$('[data-reddog-concierge]').hidden, true, 'video-only guide stays out of the house flow');
});

test('registration validates document/containment and preserves state and listeners', () => {
  const f = createFixture();
  const outside = f.doc.createElement('input');
  const foreign = createFixture().form;
  for (const options of [{}, { element: f.$('[data-reddog-discovery]') }, { element: foreign },
    { element: f.form, focusElement: outside }, { element: f.plane }]) {
    assert.equal(f.api.registerDiscoveryAdapter(options), false);
  }
  let submissions = 0;
  f.$('#propertySearch').addEventListener('submit', event => { event.preventDefault(); submissions++; });
  f.query.value = 'Fukui';
  f.form.querySelector('details').setAttribute('open', '');
  register(f); register(f);
  assert.equal(f.api.registerDiscoveryAdapter({ element: f.doc.createElement('form') }), false);
  f.api.open();
  f.$('#propertySearch').fire('submit');
  f.api.setDiscoveryAdmission(true);
  f.api.close(); f.api.open(); f.api.setDiscoveryAdmission(false);
  assert.equal(submissions, 1);
  assert.equal(f.query.value, 'Fukui');
  assert.equal(f.form.querySelector('details').hasAttribute('open'), true);
  assert.equal(f.form.parentElement, f.$('[data-reddog-discovery]'));
});

test('modal closes by Escape/scrim and keeps the trigger and ARIA state coherent', () => {
  const f = createFixture(); register(f);
  for (const closer of [() => f.doc.fire('keydown', { key: 'Escape' }), () => f.$('#accountPlaneScrim').fire('click')]) {
    f.$('#topFilters').fire('click');
    assert.equal(f.plane.getAttribute('role'), 'dialog');
    assert.equal(f.plane.getAttribute('aria-modal'), 'true');
    assert.equal(f.plane.getAttribute('aria-hidden'), 'false');
    assert.equal(f.$('#topFilters').getAttribute('aria-expanded'), 'true');
    closer();
    assert.equal(f.api.isOpen(), false);
    assert.equal(f.plane.hasAttribute('inert'), true);
    assert.equal(f.plane.getAttribute('aria-hidden'), 'true');
    assert.equal(f.$('#topFilters').getAttribute('aria-expanded'), 'false');
    assert.equal(f.$('.mall-shell').hasAttribute('inert'), false);
    assert.equal(f.doc.activeElement, f.$('#topFilters'));
  }
});

test('focus wrapping excludes closed details and disabled controls', () => {
  const f = createFixture(); register(f); f.api.open();
  const summaries = f.form.querySelectorAll('summary');
  summaries.at(-1).focus();
  assert.equal(f.doc.fire('keydown', { key: 'Tab' }).defaultPrevented, true);
  assert.equal(f.doc.activeElement, f.$('[data-reddog-close]'));
  f.doc.fire('keydown', { key: 'Tab', shiftKey: true });
  assert.equal(f.doc.activeElement, summaries.at(-1));
  summaries.at(-1).parentElement.setAttribute('open', '');
  const lastLink = summaries.at(-1).parentElement.querySelector('a[href]');
  lastLink.focus(); f.doc.fire('keydown', { key: 'Tab' });
  assert.equal(f.doc.activeElement, f.$('[data-reddog-close]'));
  f.$('[data-reddog-close]').disabled = true;
  lastLink.focus(); f.doc.fire('keydown', { key: 'Tab' });
  assert.equal(f.doc.activeElement, f.$('[data-reddog-discovery-account]'));
  f.doc.body.focus();
  assert.equal(f.doc.activeElement, f.query, 'unexpected outside focus is contained');
});

test('late idempotent form registration never steals an active filter control', () => {
  const f = createFixture(); register(f); f.api.open();
  f.$('#propertyCountry').focus();
  register(f);
  assert.equal(f.doc.activeElement, f.$('#propertyCountry'));
});

test('closing the product preserves pre-existing inert and surface state', () => {
  const f = createFixture(); register(f);
  f.$('.mall-shell').setAttribute('inert', '');
  f.doc.body.classList.add('surface-open');
  f.api.open(); f.api.close();
  assert.equal(f.$('.mall-shell').hasAttribute('inert'), true);
  assert.equal(f.doc.body.classList.contains('surface-open'), true);
});

test('the actual gesture owner leaves vertical form scrolling native', () => {
  const f = createFixture(); register(f); f.api.open();
  f.swipe(f.form, 500, 200);
  assert.equal(f.api.isOpen(), true, 'form scroll is not a modal-dismiss gesture');
  f.swipe(f.$('.account-plane-handle'), 400, 150);
  assert.equal(f.api.isOpen(), false);
  f.swipe(f.$('[data-anchor="top"]'), 20, 120);
  assert.equal(f.api.isOpen(), true);
  f.api.close();
  f.swipe(f.$('#redDogAnchor'), 600, 400);
  assert.equal(f.api.isOpen(), true, 'guest anchor swipe opens house search');
});

test('opening product search closes the previous detail through its existing owner', () => {
  const f = createFixture(); register(f);
  f.sb.mallPlanes.isOpen = () => true;
  f.sb.mallPlanes.closeView = () => { f.effects.push(['closeDetail']); f.doc.body.classList.remove('surface-open'); };
  f.doc.body.classList.add('surface-open');
  f.api.open(); f.api.close();
  assert.deepEqual(f.effects, [['closeDetail']]);
  assert.equal(f.doc.body.classList.contains('surface-open'), false);
});

test('admitted product keeps full account APIs but every global field command is refused', () => {
  const f = createFixture(); register(f); f.api.setDiscoveryAdmission(true);
  f.api.setIdentity(identity, { username: 'aiko' }); f.api.setFoundUps(registeredCatalog);
  f.api.setInvites([{ code: 'CODE-ONE', status: 'active' }]); f.api.open();
  assert.equal(f.$('[data-account-name]').textContent, 'Aiko');
  assert.equal(f.$('[data-invite-count]').textContent, '1 active');
  assert.equal(f.$('[data-reddog-briefing]').closest('[hidden], [inert]'), null);
  assert.equal(f.$('[data-reddog-recommendations]').closest('[hidden], [inert]'), null);
  assert.match(f.$('[data-reddog-briefing]').textContent, /2 FoundUps/);
  f.$('[data-reddog-rec="open_invites"]').fire('click');
  assert.equal(f.$('[data-account-invites-drawer]').classList.contains('open'), true);
  assert.equal(f.$('[data-reddog-tools]').hidden, false);
  assert.equal(f.$('[data-reddog-channels]').querySelector('a[href]').href, '/member/');
  for (const selector of ['[data-reddog-browse-rows]', '[data-reddog-category]', '[data-reddog-tag-select]', '[data-reddog-search-input]', '[data-reddog-populate-mall]', '[data-reddog-personal-mall]']) {
    assert.equal(f.plane.querySelector(selector), null, selector);
  }
  for (const name of globalMethods) assert.equal(f.api[name]('music'), false, name);
  for (const id of ['enter_foundup', 'reset_projection', 'view_active']) assert.equal(f.api.runRecommendation(id), false);
  const tools = f.$('[data-reddog-tools]');
  for (const attr of ['data-reddog-browse-rows', 'data-reddog-category', 'data-reddog-creator-search']) {
    const injected = f.doc.createElement('button'); injected.setAttribute(attr, 'music'); tools.appendChild(injected); injected.fire('click');
  }
  assert.deepEqual(f.effects, [], 'even admitted forged global controls cannot filter or replace houses');
  assert.equal(f.fieldCatalog.length, 2);
  assert.equal(f.$('#houses').textContent, 'Houses stay here');
  f.api.setDensity('4x6'); f.api.setMotionMode('glide');
  assert.deepEqual(f.effects, [['density', '4x6'], ['motion', 'glide']]);
});

test('Your FoundUps uses canonical unambiguous IDs without replacing housing records', () => {
  const f = createFixture(); register(f); f.api.setDiscoveryAdmission(true);
  f.api.setFoundUps([...registeredCatalog, { foundup_id: 'duplicate', title: 'One' }, { foundup_id: 'duplicate', title: 'Two' },
    { foundup_id: '../escape' }, { foundup_id: 'undefined', title: 'Named literal' }, {}, null]);
  assert.deepEqual(f.$('[data-account-foundups-grid]').querySelectorAll('a[href]').map(link => link.href),
    ['/f/move2japan', '/f/gotjunk', '/f/undefined']);
  assert.equal(f.api.getChannels().length, 3);
  assert.equal(f.fieldCatalog.length, 2);
  assert.deepEqual(f.effects, []);
});

test('revocation clears both avatars, cards, invites, alerts and captured API references', () => {
  const f = createFixture(); register(f); f.api.setDiscoveryAdmission(true);
  const capturedIdentity = f.api.setIdentity;
  const capturedDensity = f.api.setDensity;
  f.api.setIdentity(identity, { username: 'aiko' }); f.api.setFoundUps(registeredCatalog);
  f.api.setInvites([{ code: 'PRIVATE-CODE', status: 'active' }]);
  assert.equal(f.api.showVerificationAlert({ alert_id: 'private-alert', summary: 'Private' }), true);
  f.api.open(); f.query.value = 'Wakasa'; f.$('[data-account-signout]').focus();
  assert.equal(f.$('#mallAvatarTrigger').querySelector('img').src, identity.imageUrl);
  assert.equal(f.api.setDiscoveryAdmission(false), false);
  assert.equal(capturedIdentity(identity, { username: 'late' }), false);
  assert.equal(capturedDensity('5x8'), false);
  f.$('[data-reddog-density="4x6"]').fire('click');
  for (const image of [f.$('[data-account-avatar-img]'), f.$('#mallAvatarTrigger').querySelector('img')]) {
    assert.equal(image.hasAttribute('src'), false); assert.equal(image.style.display, 'none');
  }
  for (const placeholder of [f.$('[data-account-avatar-placeholder]'), f.$('#mallAvatarTrigger').querySelector('.account-avatar-placeholder')]) {
    assert.notEqual(placeholder.style.display, 'none');
  }
  assert.equal(f.$('[data-account-foundups-grid]').children.length, 0);
  assert.equal(f.$('[data-account-invites-drawer]').children.length, 0);
  assert.equal(f.$('[data-account-name]').textContent, '');
  assert.equal(f.doc.activeElement, f.query);
  assert.equal(f.query.value, 'Wakasa');
  f.api.setDiscoveryAdmission(true);
  assert.equal(f.api.getVerificationAlertCount(), 0);
  assert.equal(f.api.getChannels().length, 0);
  assert.deepEqual(f.effects, []);
});

test('identity enrichment binds one profile action and releases modal before Clerk opens', () => {
  const f = createFixture(); register(f); f.api.setDiscoveryAdmission(true);
  f.api.setIdentity(identity, { username: 'aiko' }); f.api.setIdentity(identity, { username: 'aiko' }); f.api.open();
  f.$('[data-account-avatar-link]').fire('click');
  assert.deepEqual(f.effects, [['profile', false, false]]);
  f.api.setDiscoveryAdmission(false); f.$('[data-account-avatar-link]').fire('click');
  assert.equal(f.effects.length, 1, 'revocation also guards an already-bound DOM handler');
});

test('admitted modes/hold use shared controller while revocation cancels pending work', () => {
  const f = createFixture(); register(f); f.api.setDiscoveryAdmission(true); f.api.open();
  f.api.openModes();
  assert.equal(f.api.isOpen(), false);
  assert.equal(f.api.isModeSheetOpen(), true);
  assert.equal(f.$('.mall-shell').hasAttribute('inert'), false);
  f.api.closeModes();
  f.$('#redDogBtn').fire('pointerdown'); f.advance(500);
  assert.equal(f.$('#redDogListening').hidden, false);
  f.$('#redDogBtn').fire('pointerup');
  assert.equal(f.$('#redDogListening').hidden, true);
  f.$('#redDogBtn').fire('pointerdown'); f.api.setDiscoveryAdmission(false); f.advance(1000);
  assert.equal(f.$('#redDogListening').hidden, true);
  assert.equal(f.$('#redDogSummary').hidden, true);
  assert.equal(f.$('[data-reddog-mode-sheet]').hidden, true);
  f.api.setDiscoveryAdmission(true);
  f.swipe(f.$('#redDogAnchor'), 600, 400);
  assert.equal(f.api.isModeSheetOpen(), true, 'admitted anchor retains the shared mode surface');
});

test('admitting an open guest form recovers focus from the now-hidden account link', () => {
  const f = createFixture(); register(f); f.api.open();
  f.$('[data-reddog-discovery-account]').focus();
  f.api.setDiscoveryAdmission(true);
  assert.equal(f.doc.activeElement, f.query);
  assert.equal(f.api.isOpen(), true);
  assert.ok(f.$('[data-reddog-tools]'));
});

test('opening search dismisses sibling mode/summary/listening surfaces', () => {
  const f = createFixture(); register(f); f.api.setDiscoveryAdmission(true);
  for (const action of ['openModes', 'showSummary', 'startListening']) {
    f.api[action]();
    f.api.open();
    assert.equal(f.api.isOpen(), true);
    assert.equal(f.api.isModeSheetOpen(), false);
    assert.equal(f.$('#redDogSummary').hidden, true);
    assert.equal(f.$('#redDogListening').hidden, true);
    assert.equal(f.api.anchorState(), 'active');
    f.api.close();
  }
});

test('admitted pointer tap and double-tap retain the existing timing contract', () => {
  const f = createFixture(); register(f); f.api.setDiscoveryAdmission(true);
  function tap(detail = 1) {
    f.$('#redDogBtn').fire('pointerdown'); f.$('#redDogBtn').fire('pointerup');
    f.$('#redDogBtn').fire('click', { detail });
  }
  tap();
  assert.equal(f.api.isOpen(), false);
  f.advance(301);
  assert.equal(f.api.isOpen(), true);
  f.api.close();
  tap(); f.advance(100); tap(2); f.advance(301);
  assert.equal(f.api.isOpen(), false);
  assert.equal(f.$('#redDogSummary').hidden, false);
  f.api.dismissSummary();
  tap(); f.api.setDiscoveryAdmission(false); f.advance(1000);
  assert.equal(f.api.isOpen(), false, 'revocation cancels a delayed member tap');
  assert.equal(f.$('#redDogSummary').hidden, true);
  f.$('#redDogBtn').fire('click', { detail: 0 });
  assert.equal(f.api.isOpen(), true, 'keyboard activation still opens guest search immediately');
});

test('repeated admission and form registration do not accumulate shell listeners', () => {
  const f = createFixture(); register(f);
  const count = () => JSON.stringify([f.doc, f.plane, f.$('#redDogBtn'), f.$('#redDogAnchor'), f.$('#mallAvatarTrigger')]
    .map(element => [...element.events].map(([name, handlers]) => [name, handlers.length])));
  const before = count();
  for (let i = 0; i < 12; i++) {
    f.api.setDiscoveryAdmission(true); f.api.setIdentity(identity, { username: 'aiko' });
    register(f); f.api.open(); f.api.setDiscoveryAdmission(false); f.api.close();
  }
  assert.equal(count(), before);
  assert.equal(f.$('[data-account-avatar-link]').events.get('click').length, 1);
});

test('normal Mall preserves upstream catalog query, dynamic categories and adaptive rows', () => {
  const f = createFixture('');
  assert.equal(f.api.registerDiscoveryAdapter, undefined);
  f.api.setFoundUps(registeredCatalog); f.api.open();
  const search = f.$('[data-reddog-search-input]');
  assert.ok(search);
  search.value = 'show me videos on Fukui'; search.fire('input');
  assert.deepEqual(f.effects.at(-1), ['searchCatalog', 'show me videos on Fukui']);
  f.api.searchCatalog('cars');
  assert.deepEqual(f.effects.at(-1), ['searchCatalog', 'cars']);
  assert.ok(f.$('[data-reddog-category-filters]').querySelector('[data-reddog-category="housing"]'));
  f.$('[data-reddog-browse-rows]').fire('click');
  assert.deepEqual(f.effects.at(-1), ['setLayoutMode', 'rows']);
  assert.equal(f.$('[data-reddog-concierge]').hidden, false);
  assert.equal(f.$('[data-account-foundups-grid]').querySelector('a[href]').href, '/member/foundup.html?id=move2japan');
});
