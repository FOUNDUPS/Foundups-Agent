'use strict';

const execFileSync = require('child_process').execFileSync;
const execFile = require('child_process').execFile;
const existsSync = require('fs').existsSync;
const joinPath = require('path').join;
const provenance = require('./holoindex_interpreter_provenance');

const SYNC_OWNER_QUERY_DEADLINE_MS = 90000;
const ASYNC_OWNER_QUERY_DEADLINE_MS = 300000;

function terminateOwnedResource(resource) {
  try {
    if (resource && typeof resource.kill === 'function') resource.kill();
    else if (resource && typeof resource.terminate === 'function') resource.terminate();
  } catch (_err) {
    // Cancellation remains authoritative even when teardown races completion.
  }
}

class ProcessLifecycle {
  constructor(parentDisposed) {
    this.parentDisposed = parentDisposed;
    this.cancelled = false;
    this.completed = false;
    this.cancelReason = '';
    this.resources = new Set();
    this.listeners = new Set();
  }
  own(resource) {
    if (!resource) return false;
    if (this.isCancelled()) { terminateOwnedResource(resource); return false; }
    this.resources.add(resource); return true;
  }
  release(resource) { this.resources.delete(resource); }
  onCancel(listener) {
    if (typeof listener !== 'function') return () => {};
    if (this.isCancelled()) listener(this.cancelReason || 'request_cancelled');
    else this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }
  cancel(value) {
    if (this.cancelled || this.completed) return;
    this.cancelled = true;
    this.cancelReason = String(value || 'request_cancelled');
    for (const resource of this.resources) terminateOwnedResource(resource);
    this.resources.clear();
    for (const listener of this.listeners) listener(this.cancelReason);
    this.listeners.clear();
  }
  complete() {
    if (this.cancelled || this.completed) return;
    this.completed = true; this.resources.clear(); this.listeners.clear();
  }
  isCancelled() {
    return this.cancelled
      || (typeof this.parentDisposed === 'function' && this.parentDisposed());
  }
  reason() { return this.cancelReason || (this.isCancelled() ? 'webview_disposed' : ''); }
}

function createProcessLifecycle(parentDisposed) {
  return Object.seal(new ProcessLifecycle(parentDisposed));
}

function createProcessLifecycleRegistry() {
  let disposed = false;
  const active = new Set();
  return Object.freeze({
    begin() {
      const lifecycle = createProcessLifecycle(() => disposed);
      if (disposed) lifecycle.cancel('webview_disposed'); else active.add(lifecycle);
      return lifecycle;
    },
    release(lifecycle) {
      if (!lifecycle) return;
      lifecycle.complete(); active.delete(lifecycle);
    },
    dispose() {
      if (disposed) return;
      disposed = true;
      for (const lifecycle of active) lifecycle.cancel('webview_disposed');
      active.clear();
    },
    isDisposed() { return disposed; }
  });
}

async function buildOwnedContext(registry, input) {
  const useHolo = input.useHolo === true;
  const lifecycle = useHolo ? registry.begin() : null;
  let packet;
  try {
    if (input.useEmpty) packet = input.empty();
    else if (input.useDraft) packet = input.draft();
    else packet = useHolo ? await input.holo(lifecycle) : input.plain();
  } finally {
    if (lifecycle) registry.release(lifecycle);
  }
  return { packet, cancelled: registry.isDisposed()
    || Boolean(lifecycle && lifecycle.isCancelled()) };
}

function parseBridgeResult(stdout, failureResult) {
  const lines = String(stdout || '').trim().split('\n');
  const result = JSON.parse(lines[lines.length - 1]);
  return result && typeof result === 'object'
    ? result : failureResult('owner_response_invalid');
}

function classifyOwnerBridgeError(err) {
  const value = err && typeof err === 'object' ? err : {};
  if (value.code === 'ETIMEDOUT') return 'owner_query_timeout';
  if (value instanceof SyntaxError) return 'owner_response_invalid';
  if (typeof value.status === 'number') return 'owner_query_process_error';
  return 'owner_query_bridge_error';
}

function ownerRequest(opts) {
  return Object.assign(
    {}, opts.request && typeof opts.request === 'object' ? opts.request : {},
    { query: String(opts.query || ''), limit: Number(opts.limit || 5) }
  );
}

function runOwnerQuery(options, dependencies) {
  const opts = options && typeof options === 'object' ? options : {};
  const deps = dependencies;
  try {
    const script = joinPath(opts.root, 'scripts', deps.scriptName);
    if (!existsSync(script)) return deps.observe(deps.failureResult(
      'owner_query_bridge_missing', opts.query
    ));
    const stdout = execFileSync(opts.interpreterPath, ['-B', script], {
      input: JSON.stringify(ownerRequest(opts)), cwd: opts.root, env: opts.env,
      encoding: 'utf8', timeout: SYNC_OWNER_QUERY_DEADLINE_MS,
      maxBuffer: 32 * 1024 * 1024, windowsHide: true
    });
    const result = parseBridgeResult(stdout, deps.failureResult);
    result.requested_query = String(opts.query || '');
    result.interpreter_source = String(opts.interpreterSource || 'unknown');
    result.interpreter_path_digest = String(opts.interpreterPathDigest || '');
    return deps.observe(result);
  } catch (err) {
    return deps.observe(deps.failureResult(classifyOwnerBridgeError(err), opts.query));
  }
}

function sendOwnerRequest(child, request, onFailure) {
  if (!child || !child.stdin || typeof child.stdin.end !== 'function') {
    onFailure(new Error('owner_query_stdin_unavailable')); return;
  }
  if (typeof child.stdin.once === 'function') child.stdin.once('error', onFailure);
  try { child.stdin.end(JSON.stringify(request)); } catch (inputError) { onFailure(inputError); }
}

function cancelledResult(deps, opts, lifecycle, reason) {
  const result = deps.failureResult('owner_query_cancelled', opts.query);
  result.cancelled = true;
  result.cancellation_reason = String(reason || lifecycle.reason());
  return result;
}

function createAsyncSettlement(opts, deps, lifecycle, resolve) {
  const state = { settled: false, child: null, removeCancel: () => {} };
  state.finish = (result) => {
    if (state.settled) return;
    state.settled = true; state.removeCancel();
    if (lifecycle) lifecycle.release(state.child);
    result.interpreter_provenance = opts.interpreterProvenance || {};
    resolve(deps.observe(result));
  };
  state.fail = (error) => state.finish(
    deps.failureResult(classifyOwnerBridgeError(error), opts.query)
  );
  return state;
}

function launchOwnerChild(opts, deps, lifecycle, request, state) {
  const transport = typeof opts.execFile === 'function' ? opts.execFile : execFile;
  const script = joinPath(opts.root, 'scripts', deps.scriptName);
  state.child = transport(opts.interpreterPath, ['-B', script], {
    cwd: opts.root, env: opts.env, encoding: 'utf8', windowsHide: true,
    timeout: ASYNC_OWNER_QUERY_DEADLINE_MS, maxBuffer: 32 * 1024 * 1024
  }, (err, stdout) => {
    if (state.settled) return;
    if (err) return state.fail(err);
    try {
      const result = parseBridgeResult(stdout, deps.failureResult);
      result.requested_query = String(opts.query || '');
      return state.finish(result);
    } catch (parseError) { return state.fail(parseError); }
  });
  if (lifecycle && !lifecycle.own(state.child)) {
    state.finish(cancelledResult(deps, opts, lifecycle)); return false;
  }
  return true;
}

function executeOwnerQueryAsync(opts, deps, lifecycle, request, resolve) {
  const state = createAsyncSettlement(opts, deps, lifecycle, resolve);
  try {
    if (!launchOwnerChild(opts, deps, lifecycle, request, state)) return;
    if (lifecycle) state.removeCancel = lifecycle.onCancel((reason) => {
      state.finish(cancelledResult(deps, opts, lifecycle, reason));
    });
  } catch (transportError) {
    state.fail(transportError); return;
  }
  sendOwnerRequest(state.child, request, (error) => {
    if (state.settled) return;
    terminateOwnedResource(state.child); state.fail(error);
  });
}

function runOwnerQueryAsync(options, dependencies) {
  const opts = options && typeof options === 'object' ? options : {};
  const deps = dependencies;
  const lifecycle = opts.lifecycle;
  if (lifecycle && lifecycle.isCancelled()) {
    return Promise.resolve(deps.observe(cancelledResult(deps, opts, lifecycle)));
  }
  const script = joinPath(opts.root, 'scripts', deps.scriptName);
  if (!existsSync(script)) return Promise.resolve(deps.observe(
    deps.failureResult('owner_query_bridge_missing', opts.query)
  ));
  const request = ownerRequest(opts);
  return new Promise((resolve) => {
    executeOwnerQueryAsync(opts, deps, lifecycle, request, resolve);
  });
}

function createOwnerRuntime(dependencies) {
  const deps = Object.freeze(Object.assign({}, dependencies));
  return Object.freeze({
    buildOwnedContext,
    classifyOwnerBridgeError,
    createProcessLifecycleRegistry,
    resolveInterpreter: provenance.resolveInterpreter,
    resolveInterpreterAsync: provenance.resolveInterpreterAsync,
    runOwnerQuery: (options) => runOwnerQuery(options, deps),
    runOwnerQueryAsync: (options) => runOwnerQueryAsync(options, deps)
  });
}

module.exports = Object.freeze({ createOwnerRuntime });
