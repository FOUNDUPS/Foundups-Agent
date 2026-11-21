// Actual pilot functions and native Node WASM/crypto, controlled DOM/network only.
// These tests do not qualify Safari, Home Screen PWA, WebGPU, or physical devices.
import assert from 'node:assert/strict';
import { createHash, webcrypto } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { runInNewContext } from 'node:vm';

const memberRoot = dirname(dirname(fileURLToPath(import.meta.url)));
const source = readFileSync(join(memberRoot, 'js/mall-browser-ai-pilot.js'), 'utf8');
const artifact = new Uint8Array(readFileSync(join(memberRoot, 'wasm/pilot-add.wasm')));
const expectedHash = 'f61fd62f57c41269c3c23f360eeaf1090b1db9c38651106674d48bc65dba88ba';
const origin = 'https://preview.example';
let checks = 0;
async function check(name, fn) { await fn(); checks++; console.log('PASS ' + name); }
const tick = () => new Promise(done => setImmediate(done));
function deferred() {
  let resolve;
  const promise = new Promise(done => { resolve = done; });
  return { promise, resolve };
}

class Element {
  constructor(tag, doc) {
    this.tagName = tag.toUpperCase(); this.ownerDocument = doc;
    this.children = []; this.parentNode = null; this.style = {}; this.attributes = new Map();
    this.listeners = new Map(); this.hidden = false; this.disabled = false;
    this.textContent = ''; this.id = ''; this.type = ''; this.tabIndex = 0;
  }
  append(...nodes) { for (const node of nodes) { node.parentNode = this; this.children.push(node); } }
  remove() { if (this.parentNode) this.parentNode.children.splice(this.parentNode.children.indexOf(this), 1); this.parentNode = null; }
  setAttribute(key, value) { this.attributes.set(key, String(value)); }
  getAttribute(key) { return this.attributes.get(key) ?? null; }
  addEventListener(type, callback) { if (!this.listeners.has(type)) this.listeners.set(type, []); this.listeners.get(type).push(callback); }
  async trigger(type) { if (this.disabled) return; for (const callback of this.listeners.get(type) || []) await callback({ target: this }); }
  focus() { this.ownerDocument.activeElement = this; }
  get isConnected() { return this === this.ownerDocument.body || !!this.parentNode?.isConnected; }
  find(predicate) { if (predicate(this)) return this; for (const child of this.children) { const result = child.find(predicate); if (result) return result; } return null; }
  all(predicate) { return [...(predicate(this) ? [this] : []), ...this.children.flatMap(child => child.all(predicate))]; }
  text() { return this.textContent + '\n' + this.children.map(child => child.text()).join('\n'); }
}

function response(bytes = artifact, options = {}) {
  const chunks = options.chunks || [bytes.subarray(0, 20), bytes.subarray(20)];
  let index = 0;
  const reader = {
    reads: 0, cancelled: 0,
    async read() { this.reads++; return index < chunks.length ? { value: chunks[index++], done: false } : { done: true }; },
    async cancel() { this.cancelled++; }, releaseLock() {}
  };
  const headers = new Map([
    ['content-type', options.mime ?? 'application/wasm'],
    ['content-length', options.length === undefined ? String(bytes.byteLength) : options.length]
  ]);
  if (options.encoding) headers.set('content-encoding', options.encoding);
  return {
    ok: options.ok ?? true, redirected: options.redirected ?? false,
    url: options.url ?? origin + '/member/wasm/pilot-add.wasm',
    headers: { get: key => headers.get(key) ?? null },
    body: options.noStream ? null : { getReader: () => options.reader || reader },
    reader,
    arrayBuffer() { throw new Error('Unbounded body fallback must never run'); }
  };
}

function runtime(options = {}) {
  const calls = [], timers = new Map();
  const activity = { validation: 0, compilation: 0, execution: 0, digests: 0, adapters: 0, reloads: 0 };
  let timerId = 0;
  let handler = options.fetch || (async () => response());
  function Module(bytes) { activity.compilation++; return new WebAssembly.Module(bytes); }
  Module.imports = WebAssembly.Module.imports; Module.exports = WebAssembly.Module.exports;
  function Instance(module) { activity.execution++; return new WebAssembly.Instance(module); }
  const doc = { activeElement: null, createElement(tag) { return new Element(tag, doc); } };
  const view = {
    navigator: { standalone: !!options.standalone, ...(options.gpu ? { gpu: { requestAdapter() { activity.adapters++; } } } : {}) },
    matchMedia: () => ({ matches: !!options.standalone }),
    location: { origin, reload() { activity.reloads++; } },
    WebAssembly: {
      validate(bytes) { activity.validation++; return WebAssembly.validate(bytes); }, Module, Instance
    },
    crypto: { subtle: { async digest(...args) { activity.digests++; return options.digest ? options.digest(...args) : webcrypto.subtle.digest(...args); } } },
    AbortController,
    async fetch(url, init) {
      calls.push({ url, init });
      assert.equal(url, origin + '/member/wasm/pilot-add.wasm');
      assert.equal(init.credentials, 'omit'); assert.equal(init.mode, 'same-origin');
      assert.equal(init.redirect, 'error'); assert.equal(init.cache, 'no-store');
      return handler(url, init);
    },
    setTimeout(callback, delay) { const id = ++timerId; timers.set(id, { callback, delay }); return id; },
    clearTimeout(id) { timers.delete(id); }
  };
  if (options.missing) view[options.missing] = undefined;
  doc.defaultView = view;
  doc.body = new Element('body', doc);
  const trigger = doc.createElement('button'); trigger.textContent = 'Leading +';
  const container = doc.createElement('div'); doc.body.append(trigger, container); trigger.focus();
  // Strip only ES export declarations to run the same functions in the existing
  // Node VM style; browser module import/integration remains a separate check.
  const executable = source.replace(/^export /gm, '') + '\nglobalThis.pilotExports = { mountBrowseAiPilot, PILOT_WASM_ARTIFACT };';
  const context = { URL, Uint8Array, ArrayBuffer, WeakMap, Promise };
  runInNewContext(executable, context);
  assert.equal(calls.length, 0, 'Evaluating the module cannot download its artifact');
  const handle = context.pilotExports.mountBrowseAiPilot(container, { returnFocusTo: trigger, ...options.mount });
  const button = label => handle.element.find(node => node.tagName === 'BUTTON' && node.textContent === label);
  return { doc, view, calls, timers, activity, handle, trigger, container, button,
    mount: context.pilotExports.mountBrowseAiPilot,
    manifest: context.pilotExports.PILOT_WASM_ARTIFACT,
    async review() { await button('Review 41-byte WASM test').trigger('click'); },
    async confirm() { await button('Confirm 41-byte test').trigger('click'); },
    setFetch(value) { handler = value; } };
}

await check('pinned binary is exactly 41 bytes, valid, import-free and only exports add', async () => {
  assert.equal(artifact.byteLength, 41);
  assert.equal(createHash('sha256').update(artifact).digest('hex'), expectedHash);
  assert.equal(WebAssembly.validate(artifact), true);
  const module = new WebAssembly.Module(artifact);
  assert.deepEqual(WebAssembly.Module.imports(module), []);
  assert.deepEqual(WebAssembly.Module.exports(module), [{ name: 'add', kind: 'function' }]);
  assert.equal(new WebAssembly.Instance(module).exports.add(2, 40), 42);
});

await check('the browser source also imports as an actual ES module with its public API', async () => {
  const imported = await import('data:text/javascript;base64,' + Buffer.from(source).toString('base64'));
  assert.equal(typeof imported.mountBrowseAiPilot, 'function');
  assert.equal(imported.PILOT_WASM_ARTIFACT.bytes, 41);
  assert.equal(imported.PILOT_WASM_ARTIFACT.sha256, expectedHash);
});

await check('mount is thin: no artifact/model fetch, digest, module or WebGPU adapter request', async () => {
  const h = runtime({ gpu: true });
  assert.equal(h.calls.length, 0); assert.equal(h.activity.digests, 0); assert.equal(h.activity.compilation, 0);
  assert.equal(h.activity.adapters, 0); assert.equal(h.handle.getState().phase, 'idle');
  const text = h.handle.element.text();
  assert.match(text, /No AI model or runtime is approved/); assert.match(text, /model choices: none/);
  assert.match(text, /41 bytes/); assert.match(text, new RegExp(expectedHash)); assert.match(text, /UNQUALIFIED/);
  assert.equal(h.mount(h.container), h.handle, 'Repeated mounting does not duplicate UI or requests');
  h.handle.destroy();
});

await check('review and cancelled confirmation never download; focus returns to the review control', async () => {
  const h = runtime();
  await h.confirm(); assert.equal(h.calls.length, 0, 'Hidden confirmation cannot run the test');
  await h.review(); assert.equal(h.handle.getState().phase, 'reviewing');
  assert.equal(h.doc.activeElement, h.button('Confirm 41-byte test'));
  await h.button('Cancel').trigger('click');
  assert.equal(h.calls.length, 0); assert.equal(h.doc.activeElement, h.button('Review 41-byte WASM test'));
  assert.equal(h.activity.execution, 0); h.handle.destroy();
});

await check('only explicit confirmation downloads and verifies the pinned fixture before native WASM execution', async () => {
  const h = runtime();
  await h.review(); await h.confirm();
  assert.equal(h.calls.length, 1); assert.equal(h.activity.digests, 1);
  assert.equal(h.activity.validation, 1); assert.equal(h.activity.compilation, 1); assert.equal(h.activity.execution, 1);
  const state = h.handle.getState(); assert.equal(state.phase, 'passed');
  assert.equal(state.result.addResult, 42); assert.equal(state.result.sha256, expectedHash);
  assert.equal(state.result.imports, 0); assert.equal(h.timers.size, 0); assert.equal(h.activity.reloads, 0);
  assert.match(h.handle.element.text(), /No AI model was loaded/); h.handle.destroy();
});

await check('same-size hash mismatch prevents validation, compilation and execution', async () => {
  const changed = artifact.slice(); changed[40] ^= 1;
  const h = runtime({ fetch: async () => response(changed) });
  await h.review(); await h.confirm();
  assert.equal(h.handle.getState().phase, 'error'); assert.match(h.handle.element.text(), /SHA-256 mismatch/);
  assert.equal(h.activity.validation, 0); assert.equal(h.activity.compilation, 0); assert.equal(h.activity.execution, 0);
  assert.equal(h.calls.length, 1); assert.equal(h.timers.size, 0); h.handle.destroy();
});

await check('oversized, truncated and unbounded responses are refused without executing any module', async () => {
  const fixtures = [
    () => response(new Uint8Array(42)),
    () => response(new Uint8Array(42), { length: null }),
    () => response(artifact.subarray(0, 40), { length: '41' }),
    () => response(artifact, { chunks: [new Uint8Array(0)], length: null }),
    () => response(artifact, { noStream: true })
  ];
  for (const fixture of fixtures) {
    const h = runtime({ fetch: async () => fixture() }); await h.review(); await h.confirm();
    assert.equal(h.handle.getState().phase, 'error'); assert.equal(h.activity.execution, 0);
    assert.equal(h.activity.compilation, 0); assert.equal(h.calls.length, 1); h.handle.destroy();
  }
});

await check('missing actual browser capabilities disable the only test and perform no fetch', async () => {
  for (const missing of ['WebAssembly', 'crypto', 'fetch', 'AbortController']) {
    const h = runtime({ missing });
    assert.equal(h.handle.getState().phase, 'unsupported');
    assert.equal(h.button('Review 41-byte WASM test').disabled, true);
    await h.review(); await h.confirm(); assert.equal(h.calls.length, 0); h.handle.destroy();
  }
});

await check('cancelling a later review preserves the previous result without denying its download', async () => {
  const h = runtime(); await h.review(); await h.confirm();
  await h.review(); await h.button('Cancel').trigger('click');
  assert.equal(h.calls.length, 1); assert.equal(h.handle.getState().phase, 'passed');
  assert.equal(h.handle.getState().result.addResult, 42);
  assert.match(h.handle.element.text(), /Review cancelled\. No new test started/);
  const cancel = h.button('Cancel'); h.handle.destroy();
  await cancel.trigger('click'); assert.equal(h.handle.getState().phase, 'destroyed');
});

await check('cancel during fetch aborts it and ignores a late success response', async () => {
  const pending = deferred(); const h = runtime({ fetch: () => pending.promise });
  await h.review(); const running = h.confirm(); await tick();
  await h.button('Cancel test').trigger('click');
  assert.equal(h.calls[0].init.signal.aborted, true); assert.equal(h.handle.getState().phase, 'cancelled');
  pending.resolve(response()); await running;
  assert.equal(h.handle.getState().phase, 'cancelled'); assert.equal(h.activity.execution, 0);
  assert.equal(h.timers.size, 0); h.handle.destroy();
});

await check('cancel after download but during digest still prevents compilation and execution', async () => {
  const pending = deferred(); const h = runtime({ digest: () => pending.promise });
  await h.review(); const running = h.confirm(); await tick();
  assert.equal(h.handle.getState().phase, 'verifying');
  await h.button('Cancel test').trigger('click');
  pending.resolve(Uint8Array.from(Buffer.from(expectedHash, 'hex')).buffer); await running;
  assert.equal(h.activity.compilation, 0); assert.equal(h.activity.execution, 0);
  assert.equal(h.handle.getState().phase, 'cancelled'); h.handle.destroy();
});

await check('deadline is bounded and a timed-out request cannot replace its terminal status', async () => {
  const pending = deferred(); const h = runtime({ fetch: () => pending.promise });
  await h.review(); const running = h.confirm(); await tick();
  const timer = [...h.timers.values()][0]; assert.equal(timer.delay, 15000); timer.callback();
  assert.match(h.handle.element.text(), /Timed out after 15 seconds/);
  pending.resolve(response()); await running;
  assert.equal(h.activity.execution, 0); assert.equal(h.handle.getState().phase, 'cancelled'); h.handle.destroy();
});

await check('a stale cancelled run cannot clobber a subsequent explicitly confirmed test', async () => {
  const pending = deferred(); const h = runtime({ fetch: () => pending.promise });
  await h.review(); const first = h.confirm(); await tick();
  await h.button('Cancel test').trigger('click'); h.setFetch(async () => response());
  await h.review(); await h.confirm(); assert.equal(h.handle.getState().phase, 'passed');
  pending.resolve(response()); await first;
  assert.equal(h.handle.getState().phase, 'passed'); assert.equal(h.activity.execution, 1); h.handle.destroy();
});

await check('redirects, changed origins, HTML and network failures have no fallback request', async () => {
  const failures = [
    async () => response(artifact, { redirected: true }),
    async () => response(artifact, { url: 'https://external.example/pilot-add.wasm' }),
    async () => response(artifact, { mime: 'text/html' }),
    async () => { throw new Error('Network unavailable'); }
  ];
  for (const fetch of failures) {
    const h = runtime({ fetch }); await h.review(); await h.confirm();
    assert.equal(h.handle.getState().phase, 'error'); assert.equal(h.calls.length, 1);
    assert.equal(h.activity.execution, 0); assert.equal(h.activity.reloads, 0); h.handle.destroy();
  }
});

await check('reported display mode is separated from device qualification and closing restores keyboard focus', async () => {
  const h = runtime({ standalone: true, gpu: true });
  assert.match(h.handle.getState().context, /Standalone.*browser-reported/);
  assert.match(h.handle.element.text(), /physical-device test/);
  const status = h.handle.element.find(node => node.getAttribute('role') === 'status');
  assert.equal(status.getAttribute('aria-live'), 'polite');
  assert.ok(h.handle.element.all(node => node.tagName === 'BUTTON').every(button => button.style.minHeight === '44px'));
  await h.button('Close Browse AI pilot').trigger('click');
  assert.equal(h.doc.activeElement, h.trigger); assert.equal(h.handle.getState().phase, 'destroyed');
  assert.equal(h.container.children.length, 0); assert.equal(h.activity.adapters, 0);
});

await check('external owner abort removes the panel and cancels in-flight work without late state updates', async () => {
  const controller = new AbortController(); const pending = deferred();
  const h = runtime({ mount: { signal: controller.signal }, fetch: () => pending.promise });
  await h.review(); const running = h.confirm(); await tick(); controller.abort();
  assert.equal(h.container.children.length, 0); assert.equal(h.calls[0].init.signal.aborted, true);
  pending.resolve(response()); await running;
  assert.equal(h.handle.getState().phase, 'destroyed'); assert.equal(h.activity.execution, 0);
});

console.log('Browse AI compatibility pilot: ' + checks + ' checks passed; no browser/device qualification.');
