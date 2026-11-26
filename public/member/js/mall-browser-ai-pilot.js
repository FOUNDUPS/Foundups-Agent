// On-demand compatibility check only. No model/runtime selection or preload.
export const PILOT_WASM_ARTIFACT = Object.freeze({
  path: '/member/wasm/pilot-add.wasm',
  bytes: 41,
  sha256: 'f61fd62f57c41269c3c23f360eeaf1090b1db9c38651106674d48bc65dba88ba'
});

const mounted = new WeakMap();
let panelNumber = 0;

function inspectCapabilities(view) {
  const wasm = view.WebAssembly;
  return {
    wasm: typeof wasm?.validate === 'function' && typeof wasm.Module === 'function' &&
      typeof wasm.Module.imports === 'function' && typeof wasm.Module.exports === 'function' &&
      typeof wasm.Instance === 'function',
    crypto: typeof view.crypto?.subtle?.digest === 'function',
    fetch: typeof view.fetch === 'function',
    abort: typeof view.AbortController === 'function',
    webgpuDetected: !!view.navigator?.gpu
  };
}

async function boundedBytes(response, job, progress) {
  const mime = response.headers.get('content-type') || '';
  if (!/^application\/wasm(?:\s*;|\s*$)/i.test(mime)) throw new Error('The response is not a WASM artifact.');
  const length = response.headers.get('content-length');
  const encoding = response.headers.get('content-encoding');
  if (length !== null && (!encoding || encoding === 'identity') &&
      (!/^\d+$/.test(length) || Number(length) !== PILOT_WASM_ARTIFACT.bytes)) {
    throw new Error('The response length does not match the approved 41-byte payload.');
  }
  if (typeof response.body?.getReader !== 'function') {
    throw new Error('Bounded streaming is unavailable; the artifact was not run.');
  }
  job.reader = response.body.getReader();
  const bytes = new Uint8Array(PILOT_WASM_ARTIFACT.bytes);
  let received = 0;
  for (;;) {
    const { done, value } = await job.reader.read();
    if (job.cancelled) throw new Error('Cancelled');
    if (done) break;
    if (!ArrayBuffer.isView(value) || value.BYTES_PER_ELEMENT !== 1) {
      throw new Error('A byte-stream response is required. The artifact was not run.');
    }
    if (!value.byteLength) throw new Error('The response made no byte progress. The artifact was not run.');
    if (value.byteLength > bytes.length - received) {
      throw new Error('The response exceeds the approved 41-byte payload.');
    }
    bytes.set(new Uint8Array(value.buffer, value.byteOffset, value.byteLength), received);
    received += value.byteLength;
    progress(received);
  }
  if (received !== bytes.length) throw new Error('The 41-byte payload is incomplete.');
  return bytes;
}

/** Mount inside the existing dock/dialog. The caller owns that surrounding UI. */
export function mountBrowseAiPilot(container, options = {}) {
  if (!container?.ownerDocument || typeof container.append !== 'function') {
    throw new TypeError('Browse AI pilot requires an existing DOM container.');
  }
  if (mounted.has(container)) return mounted.get(container);
  const doc = container.ownerDocument;
  const view = doc.defaultView;
  const returnFocusTo = options.returnFocusTo || doc.activeElement;
  const capabilities = inspectCapabilities(view);
  const missing = ['wasm', 'crypto', 'fetch', 'abort'].filter(key => !capabilities[key]);
  const compatible = missing.length === 0;
  let standalone = view.navigator?.standalone === true;
  try { standalone ||= view.matchMedia?.('(display-mode: standalone)').matches === true; } catch { /* Not reported. */ }
  const context = standalone ? 'Standalone / Home Screen mode (browser-reported)' :
    'Browser context (standalone not reported)';
  let phase = compatible ? 'idle' : 'unsupported';
  let activeJob = null;
  let destroyed = false;
  let result = null;

  function element(tag, text, parent) {
    const node = doc.createElement(tag);
    if (text !== undefined) node.textContent = text;
    parent?.append(node);
    return node;
  }
  const panel = element('section');
  panel.className = 'mall-browser-ai-pilot';
  panel.setAttribute('role', 'region');
  const title = element('h2', 'Browse AI pilot', panel);
  title.id = 'mall-browser-ai-pilot-' + (++panelNumber);
  title.tabIndex = -1;
  panel.setAttribute('aria-labelledby', title.id);
  element('p', 'No AI model or runtime is approved for this pilot. This compatibility test only adds two integers; it does not run AI.', panel);
  element('p', 'Approved local model choices: none.', panel);
  element('p', 'Context: ' + context, panel);
  element('p', capabilities.webgpuDetected
    ? 'WebGPU API detected. UNQUALIFIED: no adapter, model or physical-device test has run.'
    : 'WebGPU API not detected. No WebGPU/model compatibility has been qualified.', panel);
  element('p', 'WASM compatibility test payload: 41 bytes. Network headers and browser overhead are additional.', panel);
  const hash = element('code', 'SHA-256: ' + PILOT_WASM_ARTIFACT.sha256, panel);
  hash.style.overflowWrap = 'anywhere';
  hash.style.display = 'block';
  const review = element('button', 'Review 41-byte WASM test', panel);
  review.type = 'button';
  review.disabled = !compatible;
  const confirmation = element('div', undefined, panel);
  confirmation.hidden = true;
  confirmation.setAttribute('role', 'group');
  confirmation.setAttribute('aria-label', 'Confirm the 41-byte compatibility test');
  element('p', 'Download the exact 41-byte artifact shown above, verify its hash, then run add(2, 40)? No AI model or cloud service will load.', confirmation);
  const confirm = element('button', 'Confirm 41-byte test', confirmation);
  const cancelConfirmation = element('button', 'Cancel', confirmation);
  confirm.type = cancelConfirmation.type = 'button';
  const cancelRun = element('button', 'Cancel test', panel);
  cancelRun.type = 'button';
  cancelRun.hidden = true;
  const status = element('p', compatible ? 'Not downloaded.' :
    'This test is unavailable. Missing browser capabilities: ' + missing.join(', ') + '.', panel);
  status.setAttribute('role', 'status');
  status.setAttribute('aria-live', 'polite');
  status.setAttribute('aria-atomic', 'true');
  const close = element('button', 'Close Browse AI pilot', panel);
  close.type = 'button';
  for (const button of [review, confirm, cancelConfirmation, cancelRun, close]) {
    button.style.minHeight = '44px';
  }
  container.append(panel);

  function current(job) { return !destroyed && activeJob === job && !job.cancelled; }
  function update(job, nextPhase, text) {
    if (!current(job)) return false;
    phase = nextPhase;
    status.textContent = text;
    return true;
  }
  function cancel(reason = 'Cancelled. The test was not run.') {
    const job = activeJob;
    if (!job) return;
    job.cancelled = true;
    job.controller.abort();
    try { Promise.resolve(job.reader?.cancel()).catch(() => {}); } catch { /* Cancellation is best effort. */ }
    view.clearTimeout(job.timer);
    activeJob = null;
    if (!destroyed) {
      phase = 'cancelled';
      status.textContent = reason;
      review.disabled = !compatible;
      cancelRun.hidden = true;
      review.focus();
    }
  }

  async function run() {
    if (destroyed || !compatible || activeJob || confirmation.hidden) return;
    confirmation.hidden = true;
    review.disabled = true;
    cancelRun.hidden = false;
    result = null;
    const job = { controller: new view.AbortController(), reader: null, cancelled: false, timer: null };
    activeJob = job;
    job.timer = view.setTimeout(() => {
      if (current(job)) cancel('Timed out after 15 seconds. The test was not run.');
    }, 15000);
    update(job, 'downloading', 'Downloading compatibility test: 0 / 41 bytes.');
    cancelRun.focus();
    try {
      const url = new URL(PILOT_WASM_ARTIFACT.path, view.location.origin);
      if (url.origin !== view.location.origin) throw new Error('The artifact must remain on this origin.');
      const response = await view.fetch(url.href, {
        credentials: 'omit', mode: 'same-origin', cache: 'no-store', redirect: 'error', signal: job.controller.signal
      });
      if (!current(job)) return;
      if (!response.ok || response.redirected || (response.url && response.url !== url.href)) {
        throw new Error('The approved artifact is unavailable at its fixed path.');
      }
      const bytes = await boundedBytes(response, job, count => {
        update(job, 'downloading', 'Downloading compatibility test: ' + count + ' / 41 bytes.');
      });
      if (!update(job, 'verifying', 'Verifying the 41-byte payload and SHA-256.')) return;
      const digest = new Uint8Array(await view.crypto.subtle.digest('SHA-256', bytes));
      const actualHash = Array.from(digest, byte => byte.toString(16).padStart(2, '0')).join('');
      if (!current(job)) return;
      if (actualHash !== PILOT_WASM_ARTIFACT.sha256) throw new Error('SHA-256 mismatch. The artifact was not run.');
      if (!update(job, 'validating', 'Hash verified. Checking the WASM module.')) return;
      const wasm = view.WebAssembly;
      if (!wasm.validate(bytes)) throw new Error('WASM validation failed. The artifact was not run.');
      const module = new wasm.Module(bytes);
      const imports = wasm.Module.imports(module);
      const exports = wasm.Module.exports(module);
      if (imports.length || exports.length !== 1 || exports[0].name !== 'add' || exports[0].kind !== 'function') {
        throw new Error('Unexpected module interface. The artifact was not run.');
      }
      if (!current(job)) return;
      const instance = new wasm.Instance(module);
      const sum = instance.exports.add(2, 40);
      if (sum !== 42) throw new Error('The compatibility calculation did not return 42.');
      result = { bytes: bytes.length, sha256: actualHash, imports: imports.length, addResult: sum };
      update(job, 'passed', 'Compatibility test passed: add(2, 40) = 42. No AI model was loaded. WebGPU and physical-device behavior remain unqualified.');
    } catch (error) {
      if (current(job)) {
        phase = 'error';
        status.textContent = 'Test failed: ' + (error?.message || 'Unknown browser error.') + ' No model or cloud fallback was loaded.';
      }
    } finally {
      view.clearTimeout(job.timer);
      try { Promise.resolve(job.reader?.cancel()).catch(() => {}); } catch { /* No pending stream required. */ }
      try { job.reader?.releaseLock(); } catch { /* A cancelled read may still settle. */ }
      if (activeJob === job) {
        activeJob = null;
        if (!destroyed) {
          review.disabled = !compatible;
          cancelRun.hidden = true;
          review.focus();
        }
      }
    }
  }

  review.addEventListener('click', () => {
    if (destroyed || !compatible || activeJob) return;
    phase = 'reviewing';
    confirmation.hidden = false;
    confirm.focus();
  });
  cancelConfirmation.addEventListener('click', () => {
    if (destroyed) return;
    confirmation.hidden = true;
    phase = result ? 'passed' : 'idle';
    status.textContent = 'Review cancelled. No new test started.';
    review.focus();
  });
  confirm.addEventListener('click', run);
  cancelRun.addEventListener('click', () => cancel());

  const handle = {
    element: panel,
    getState() { return { phase, capabilities: { ...capabilities }, context, result: result ? { ...result } : null }; },
    destroy() {
      if (destroyed) return;
      destroyed = true;
      cancel();
      phase = 'destroyed';
      options.signal?.removeEventListener('abort', handle.destroy);
      panel.remove();
      mounted.delete(container);
      if (returnFocusTo?.isConnected !== false) returnFocusTo?.focus?.();
      options.onClose?.();
    }
  };
  mounted.set(container, handle);
  close.addEventListener('click', handle.destroy);
  if (options.signal?.aborted) handle.destroy();
  else {
    options.signal?.addEventListener('abort', handle.destroy, { once: true });
    title.focus();
  }
  return handle;
}
