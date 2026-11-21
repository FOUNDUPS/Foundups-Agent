/** Execute actual routing, HTML boot and contribution-review source in Node VM.
 * Controlled DOM/Clerk/storage only: no network, real authentication, membership,
 * editor authority, browser layout, submission, provider or device qualification.
 */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import vm from 'node:vm';

const member = dirname(dirname(fileURLToPath(import.meta.url)));
const publicRoot = dirname(member);
const projection = readFileSync(join(member, 'js/mall-video-projection.js'), 'utf8');
const stateSource = readFileSync(join(member, 'js/mall-state-restore.js'), 'utf8');
const rootHtml = readFileSync(join(publicRoot, 'index.html'), 'utf8');
const memberHtml = readFileSync(join(member, 'index.html'), 'utf8');
const callbackHtml = readFileSync(join(publicRoot, 'sso-callback/index.html'), 'utf8');
const entryHtml = readFileSync(join(member, 'foundup.html'), 'utf8');
const canonicalHtml = readFileSync(join(publicRoot, 'f/index.html'), 'utf8');
const preview = 'https://foundupscom--play-v26-iphone-review.web.app';
const clone = value => JSON.parse(JSON.stringify(value));

function inlineScript(html, marker) {
  const matches = [...html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/gi)]
    .filter(match => !/\bsrc\s*=/.test(match[1]) && match[2].includes(marker));
  assert.equal(matches.length, 1, 'one actual inline script must contain ' + marker);
  return matches[0][2];
}
const landingBoot = inlineScript(rootHtml, 'const publicLanding');
const gatewaySdkBoot = inlineScript(rootHtml, "getElementById('gatewayClerkSdk')");
const memberSdkBoot = inlineScript(memberHtml, 'const dedicatedVideoHost');
const productBoot = inlineScript(memberHtml, 'const publicVideoScope');
const ssoBoot = inlineScript(callbackHtml, "window.addEventListener('load'");
const canonicalBoot = inlineScript(canonicalHtml, 'var PUBLIC_CATALOG_URL');
const oauthStart = rootHtml.indexOf('async function handleClerkSignIn(');
const oauthEnd = rootHtml.indexOf('// Attach sign-in handlers', oauthStart);
assert.ok(oauthStart > 0 && oauthEnd > oauthStart, 'actual bounded gateway OAuth handler exists');
const oauthHandler = rootHtml.slice(oauthStart, oauthEnd);
const addStart = projection.indexOf("add.addEventListener('click', () => {");
const addEnd = projection.indexOf("options.setAttribute('aria-label'", addStart);
assert.ok(addStart > 0 && addEnd > addStart && addEnd - addStart < 1500, 'actual bounded dock Add handler exists');
const dockAddHandler = projection.slice(addStart, addEnd);

function runtime(href, { remember = true, actualState = false, autoNodes = false, blockIntentWrite = false } = {}) {
  let page = new URL(href);
  const calls = { replace: [], assign: [], href: [], sdk: [], mounts: [], intents: [], saves: 0, fetches: [], errors: [] };
  const location = {};
  for (const key of ['hostname', 'origin', 'pathname', 'search', 'hash']) {
    Object.defineProperty(location, key, { get: () => page[key] });
  }
  Object.defineProperty(location, 'href', {
    get: () => page.href,
    set: value => { calls.href.push(String(value)); page = new URL(value, page.href); },
  });
  location.replace = value => calls.replace.push(String(value));
  location.assign = value => calls.assign.push(String(value));
  const events = new Map();
  const ids = new Map();
  const document = { title: '', activeElement: null, documentElement: { dataset: {} },
    addEventListener() {}, querySelectorAll: () => [], visibilityState: 'visible' };
  class Element {
    constructor(tag = 'div') {
      this.tagName = tag.toUpperCase(); this.children = []; this.listeners = new Map(); this.attributes = {};
      this.style = {}; this.dataset = {}; this.className = ''; this.textContent = ''; this.value = '';
      this.disabled = false; this.open = false; this.hidden = false; this.isConnected = false;
      this.classList = { add() {}, remove() {}, toggle() {} };
    }
    setAttribute(key, value) { this.attributes[key] = String(value); }
    append(...children) {
      for (const child of children) {
        this.children.push(child); child.parentElement = this; child.isConnected = true;
        if (child.id) ids.set(child.id, child);
      }
    }
    appendChild(child) { this.append(child); return child; }
    addEventListener(type, callback, options) {
      const list = this.listeners.get(type) || []; list.push({ callback, once: options?.once }); this.listeners.set(type, list);
    }
    dispatch(type, event = {}) {
      event.target ||= this; event.stopPropagation ||= () => {}; event.preventDefault ||= () => {};
      for (const listener of [...(this.listeners.get(type) || [])]) {
        listener.callback(event);
        if (listener.once) this.listeners.set(type, (this.listeners.get(type) || []).filter(item => item !== listener));
      }
    }
    focus() { document.activeElement = this; }
    closest(selector) {
      for (let node = this; node; node = node.parentElement) if (selector === '[inert]' && node.inert) return node;
      return null;
    }
    showModal() { this.open = true; }
    close() { this.open = false; this.dispatch('close'); }
    remove() {
      this.isConnected = false;
      if (this.id && ids.get(this.id) === this) ids.delete(this.id);
      if (this.parentElement) this.parentElement.children = this.parentElement.children.filter(item => item !== this);
    }
  }
  document.createElement = tag => new Element(tag);
  document.body = new Element('body'); document.body.isConnected = true;
  document.head = new Element('head'); document.head.isConnected = true;
  document.head.appendChild = child => { calls.sdk.push(child.template || child.tagName); document.head.append(child); return child; };
  document.getElementById = id => {
    if (ids.has(id)) return ids.get(id);
    if (/^(gateway|member)ClerkSdk$/.test(id)) return { content: { cloneNode: () => ({ template: id }) } };
    if (!autoNodes) return null;
    const node = new Element(); node.id = id; ids.set(id, node); return node;
  };
  document.querySelector = selector => {
    if (selector.startsWith('link[')) return new Element('link');
    if (selector === '#mallTileField' || selector === '.mall-tile-field-wrapper') return null;
    return null;
  };
  const local = new Map(), session = new Map();
  const storage = map => ({ getItem: key => map.get(key) ?? null,
    setItem(key, value) {
      if (map === session && blockIntentWrite && key === 'pfmall_admission_intent_v1') throw Error('controlled session write failure');
      map.set(key, value);
    }, removeItem: key => map.delete(key) });
  const win = { location, document,
    history: { state: null, replaceState(_, __, value) { page = new URL(value, page.href); } },
    addEventListener(type, callback) { const list = events.get(type) || []; list.push(callback); events.set(type, list); },
    mallStateRestore: { rememberAdmissionIntent(intent) { calls.intents.push(clone(intent)); return remember; }, save() { calls.saves++; } },
  };
  const context = vm.createContext({ window: win, document, URL, URLSearchParams,
    localStorage: storage(local), sessionStorage: storage(session),
    setTimeout(callback) { queueMicrotask(callback); return 1; }, clearTimeout() {}, requestAnimationFrame() {},
    fetch(url) { calls.fetches.push(String(url)); return new Promise(() => {}); },
    console: { log() {}, warn() {}, error(...args) { calls.errors.push(args); } },
  });
  const run = (source, filename = 'actual-source') => vm.runInContext(source, context, { filename, timeout: 1000 });
  run(projection, 'mall-video-projection.js');
  if (actualState) run(stateSource, 'mall-state-restore.js');
  return { api: win.mallVideoProjection, win, document, calls, run, local, session,
    async load() { for (const callback of events.get('load') || []) await callback(); },
    caller() { const node = new Element('button'); document.body.append(node); node.focus(); return node; },
    dialog() { return ids.get('mallContributionReview'); },
  };
}

let checks = 0;
async function check(name, callback) { await callback(); checks++; console.log('PASS ' + name); }

await check('public Mall and explicit read-only entries use actual member boot without auth SDK', () => {
  for (const origin of ['https://play.foundups.com', preview]) {
    const mall = runtime(origin + '/member/');
    mall.api.mount = scope => mall.calls.mounts.push(scope);
    mall.run(memberSdkBoot, 'member.html#sdk'); mall.run(productBoot, 'member.html#productDiscoveryBoot');
    assert.deepEqual(mall.calls.mounts, ['mall']); assert.deepEqual(mall.calls.sdk, []);
    for (const id of ['hpc', 'voteballots', 'trade']) {
      const h = runtime(origin + '/member/?enter=' + id);
      h.api.mount = scope => h.calls.mounts.push(scope);
      assert.equal(h.api.publicEntryPath(h.win.location), '/member/foundup.html?id=' + id);
      assert.equal(h.api.shouldLoadMemberAuth(h.win.location), false);
      h.run(memberSdkBoot, 'member.html#sdk'); h.run(productBoot, 'member.html#productDiscoveryBoot');
      assert.deepEqual(h.calls.replace, ['/member/foundup.html?id=' + id]);
      assert.deepEqual(h.calls.mounts, []); assert.deepEqual(h.calls.sdk, []); assert.deepEqual(h.calls.fetches, []);
    }
  }
});

await check('malformed enter links do not mount public content or silently lose admission', () => {
  for (const query of ['enter=', 'enter=../hpc', 'enter=%2Fhpc', 'enter=__proto__', 'enter=constructor',
    'enter=prototype', 'enter=hpc&enter=hpc', 'enter=hpc%00', 'enter=hpc%22']) {
    const h = runtime('https://play.foundups.com/member/?' + query);
    h.api.mount = scope => h.calls.mounts.push(scope);
    assert.equal(h.api.publicEntryPath(h.win.location), null, query);
    assert.equal(h.api.resolve(h.win.location), null, query);
    assert.equal(h.api.shouldLoadMemberAuth(h.win.location), true, query);
    h.run(memberSdkBoot); h.run(productBoot);
    assert.deepEqual(h.calls.replace, [], query); assert.deepEqual(h.calls.mounts, [], query);
    assert.deepEqual(h.calls.sdk, ['memberClerkSdk'], query);
  }
});

await check('actual gateway boot redirects guest roots and preserves explicit Play sign-in', () => {
  for (const origin of ['https://play.foundups.com', preview]) {
    const guest = runtime(origin + '/?creator=move2japan#red-dog');
    guest.run(landingBoot, 'root.html#landing'); guest.run(gatewaySdkBoot, 'root.html#sdk');
    assert.ok(guest.calls.replace.length >= 1);
    assert.ok(guest.calls.replace.every(value => value === '/member/?creator=move2japan#red-dog'));
    assert.deepEqual(guest.calls.sdk, []);
    const signIn = runtime(origin + '/?signin=required');
    signIn.run(landingBoot); signIn.run(gatewaySdkBoot);
    assert.deepEqual(signIn.calls.replace, [], 'projection loading and HTML boot must both preserve explicit sign-in');
    assert.deepEqual(signIn.calls.sdk, ['gatewayClerkSdk']);
    assert.equal(signIn.api.signInUrl(), origin + '/?signin=required');
  }
});

await check('admission parameters cannot be converted into a public discovery boot', () => {
  for (const query of ['signin=required', 'auth=failed', 'admission=resume', 'invite=x', 'invitation=x',
    'code=x', 'state=x', 'error=x', '__clerk_status=x']) {
    const h = runtime(preview + '/member/?' + query);
    h.api.mount = scope => h.calls.mounts.push(scope);
    assert.equal(h.api.isAdmissionRequest(h.win.location), true, query);
    assert.equal(h.api.resolve(h.win.location), null, query);
    h.run(memberSdkBoot); h.run(productBoot);
    assert.deepEqual(h.calls.mounts, [], query); assert.deepEqual(h.calls.replace, [], query);
    assert.deepEqual(h.calls.sdk, ['memberClerkSdk'], query);
  }
});

await check('explicit root and canonical detail links preserve public identity while app remains a handoff', () => {
  const rootEntry = runtime(preview + '/?enter=hpc'); rootEntry.run(landingBoot);
  assert.deepEqual(rootEntry.calls.replace, ['/member/foundup.html?id=hpc']);
  for (const href of [preview + '/f/hpc', preview + '/f/hpc#red-dog', 'https://foundups.com/f/trade']) {
    const h = runtime(href, { autoNodes: true }); h.run(canonicalBoot, 'f/index.html#actual-runtime');
    assert.deepEqual(h.calls.fetches, ['/f/public_catalog.json']);
    assert.deepEqual(h.calls.href, []); assert.deepEqual(h.calls.assign, []);
  }
  const app = runtime(preview + '/f/hpc/app', { autoNodes: true }); app.run(canonicalBoot);
  assert.deepEqual(app.calls.fetches, []); assert.equal(app.calls.href.length, 1);
  assert.equal(new URL(app.calls.href[0], app.win.location.origin).pathname, '/member/');
  assert.ok(!/Clerk|inviteValidated|location\.(?:assign|replace)|location\.href\s*=/.test(
    inlineScript(entryHtml, 'This static card is a public metadata')), 'public detail head must not install a new admission gate');
});

await check('apex landing planner remains test-only and never redirects actual apex HTML boot', () => {
  const h = runtime('https://foundups.com/');
  assert.equal(h.api.plannedApexLandingUrl(h.win.location), 'https://play.foundups.com/');
  for (const search of ['?signin=required', '?enter=hpc', '?foundup=hpc', '?next=x', '?return_to=x']) {
    assert.equal(h.api.plannedApexLandingUrl(new URL('https://foundups.com/' + search)), null);
  }
  h.run(landingBoot); h.run(gatewaySdkBoot);
  assert.deepEqual(h.calls.replace, []); assert.deepEqual(h.calls.sdk, ['gatewayClerkSdk']);
  assert.ok(!rootHtml.includes('plannedApexLandingUrl('), 'planning seam is not invoked by root HTML');
});

await check('actual gateway OAuth handler binds callback and completion to current origin', async () => {
  for (const origin of ['https://play.foundups.com', preview, 'https://foundups.com']) {
    const h = runtime(origin + '/?signin=required'); const oauth = [], fallback = [];
    h.win.Clerk = { load: async () => {}, client: { signIn: { authenticateWithRedirect: async options => oauth.push(clone(options)) } },
      redirectToSignIn: options => fallback.push(clone(options)) };
    h.run(oauthHandler, 'root.html#handleClerkSignIn');
    const button = h.caller(); await h.run('handleClerkSignIn(document.activeElement, "Google")');
    assert.deepEqual(oauth, [{ strategy: 'oauth_google', redirectUrl: origin + '/sso-callback/',
      redirectUrlComplete: origin + h.api.authCompletionPath(h.win.location) }]);
    h.win.Clerk.client.signIn.authenticateWithRedirect = async () => { throw Error('controlled rejection'); };
    await h.run('handleClerkSignIn(document.activeElement, "Google")');
    assert.deepEqual(fallback, [{ redirectUrl: origin + h.api.authCompletionPath(h.win.location) }]);
  }
});

await check('actual SSO callback preserves same-host admission for established and recovered sessions', async () => {
  for (const origin of ['https://play.foundups.com', preview, 'https://foundups.com']) {
    for (const established of [true, false]) {
      const h = runtime(origin + '/sso-callback/?state=opaque'); let loads = 0, redirects = 0;
      h.win.Clerk = { user: established ? { id: 'controlled-user' } : null,
        load: async () => { loads++; }, handleRedirectCallback: async () => { redirects++; h.win.Clerk.user = { id: 'controlled-user' }; } };
      h.run(ssoBoot, 'sso-callback/index.html#actual-runtime'); await h.load();
      assert.equal(loads, 1); assert.equal(redirects, established ? 0 : 1);
      assert.deepEqual(h.calls.replace, []);
      assert.deepEqual(h.calls.href, [origin === 'https://foundups.com' ? '/member/' : '/member/?admission=resume']);
      assert.equal(h.win.location.origin, origin);
    }
  }
});

await check('callback failures stay on current host instead of converting into guest discovery', async () => {
  for (const rejectLoad of [false, true]) {
    const h = runtime(preview + '/sso-callback/');
    h.win.Clerk = { user: null, load: async () => { if (rejectLoad) throw Error('controlled offline'); }, handleRedirectCallback: async () => {} };
    h.run(ssoBoot); await h.load();
    assert.equal(h.win.location.origin, preview);
    assert.match(h.calls.href[0], rejectLoad ? /^\/\?auth=error&msg=/ : /^\/\?auth=failed$/);
    assert.equal(h.api.dedicatedLandingPath(h.win.location), null);
    assert.equal(h.api.shouldLoadMemberAuth(h.win.location), true);
  }
});

await check('same-host contribution review saves typed context only after explicit sign-in click', () => {
  for (const origin of ['https://play.foundups.com', preview]) {
    for (const intent of [{ action: 'add-foundup' }, { action: 'add-video', foundupId: 'hpc' },
      { action: 'add-video', foundupId: 'hpc', videoId: 'abcDEF_12-3' }]) {
      const h = runtime(origin + '/member/?foundup=hpc#account', { actualState: true }); const caller = h.caller();
      assert.equal(h.api.showContributionReview(intent, false, caller), true);
      const dialog = h.dialog(), signIn = dialog.children.find(node => node.textContent === 'Sign in and check membership');
      assert.equal(h.document.activeElement, signIn); assert.equal(h.win.mallStateRestore.peekAdmissionIntent(), null);
      assert.deepEqual(h.calls.assign, []); assert.deepEqual(h.calls.fetches, []);
      assert.equal(h.api.showContributionReview(intent, false, caller), false, 'no duplicate dialog');
      signIn.dispatch('click');
      const saved = clone(h.win.mallStateRestore.peekAdmissionIntent());
      assert.equal(saved.action, intent.action); assert.equal(saved.foundupId, intent.foundupId);
      assert.equal(saved.videoId, intent.videoId); assert.equal(saved.returnPath, '/member/?foundup=hpc#account');
      assert.deepEqual(h.calls.assign, [origin + '/?signin=required']); assert.deepEqual(h.calls.fetches, []);
      dialog.children.find(node => node.textContent === 'Back to browsing').dispatch('click');
      assert.equal(h.document.activeElement, caller); assert.equal(h.dialog(), undefined);
    }
  }
});

await check('actual dock Add action distinguishes Mall creation from HPC selected-video context', () => {
  for (const [scope, videoId] of [[undefined, 'abcDEF_12-3'], ['hpc', 'abcDEF_12-3'], ['hpc', 'invalid']]) {
    const h = runtime(preview + '/member/', { actualState: true });
    h.document.documentElement.dataset.mallVideoScope = scope;
    h.win.mallVideoPlayer = { getCurrentVideoId: () => videoId };
    const add = h.caller();
    h.run('var add = document.activeElement; var showContributionReview = window.mallVideoProjection.showContributionReview;\n' + dockAddHandler,
      'mall-video-projection.js#actual-dock-add-handler');
    add.dispatch('click');
    const dialog = h.dialog();
    assert.equal(h.win.mallStateRestore.peekAdmissionIntent(), null, 'Add opens review without persisting or submitting');
    dialog.children.find(node => node.textContent === 'Sign in and check membership').dispatch('click');
    const saved = h.win.mallStateRestore.peekAdmissionIntent();
    assert.equal(saved.action, scope === 'hpc' ? 'add-video' : 'add-foundup');
    assert.equal(saved.foundupId, scope === 'hpc' ? 'hpc' : undefined);
    assert.equal(saved.videoId, scope === 'hpc' && videoId !== 'invalid' ? videoId : undefined);
    assert.deepEqual(h.calls.fetches, []);
  }
});

await check('failed intent persistence prevents contribution sign-in navigation', () => {
  const h = runtime(preview + '/member/', { remember: false });
  h.api.showContributionReview({ action: 'add-foundup' }, false, h.caller());
  const dialog = h.dialog(); dialog.children.find(node => node.textContent === 'Sign in and check membership').dispatch('click');
  assert.deepEqual(h.calls.assign, []); assert.equal(h.calls.saves, 0); assert.deepEqual(h.calls.fetches, []);
  assert.match(dialog.children[1].textContent, /safe return could not be saved/);
});

await check('actual state-owner persistence failure refuses review navigation and leaves no handoff', () => {
  const h = runtime(preview + '/member/?foundup=hpc#account', { actualState: true, blockIntentWrite: true });
  h.api.showContributionReview({ action: 'add-video', foundupId: 'hpc' }, false, h.caller());
  const dialog = h.dialog(); dialog.children.find(node => node.textContent === 'Sign in and check membership').dispatch('click');
  assert.equal(h.win.mallStateRestore.peekAdmissionIntent(), null);
  assert.equal(h.session.has('pfmall_admission_intent_v1'), false);
  assert.deepEqual(h.calls.assign, []); assert.deepEqual(h.calls.href, []); assert.deepEqual(h.calls.fetches, []);
  assert.match(dialog.children[1].textContent, /safe return could not be saved/);
  assert.match(dialog.children[1].textContent, /No sign-in or submission was started/);
});

await check('production HPC cross-origin contribution is disabled, records no intent and focuses Back', () => {
  const h = runtime('https://hpc.foundups.com/member/'); const caller = h.caller();
  h.api.showContributionReview({ action: 'add-video', foundupId: 'hpc', videoId: 'abcDEF_12-3' }, false, caller);
  const dialog = h.dialog(), signIn = dialog.children.find(node => node.textContent === 'Contribution return not connected');
  const back = dialog.children.find(node => node.textContent === 'Back to browsing');
  assert.equal(signIn.disabled, true); assert.equal(h.document.activeElement, back);
  signIn.dispatch('click');
  assert.deepEqual(h.calls.intents, []); assert.equal(h.calls.saves, 0);
  assert.deepEqual(h.calls.assign, []); assert.deepEqual(h.calls.fetches, []);
  back.dispatch('click'); assert.equal(h.document.activeElement, caller);
});

await check('admitted review remains unavailable and cannot auto-submit or grant editor capability', () => {
  const h = runtime(preview + '/member/?admission=resume'); const caller = h.caller();
  h.api.showContributionReview({ action: 'add-video', foundupId: 'hpc' }, true, caller);
  const dialog = h.dialog(), disabled = dialog.children.find(node => node.textContent === 'Contribution service not enabled');
  assert.equal(disabled.disabled, true); assert.match(dialog.children[1].textContent, /owning service verifies current membership and editor permission/);
  assert.match(dialog.children[1].textContent, /No contribution has been submitted/);
  disabled.dispatch('click'); assert.deepEqual(h.calls.intents, []); assert.deepEqual(h.calls.assign, []); assert.deepEqual(h.calls.fetches, []);
  assert.equal(h.document.activeElement.textContent, 'Back to browsing');
});

console.log(JSON.stringify({ checks, real_auth: 'UNEXECUTED', membership_editor: 'UNEXECUTED',
  browser_layout: 'UNEXECUTED', physical_phone: 'UNEXECUTED', external_requests: 0, submitted: false }));
