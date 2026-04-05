/**
 * Runtime checks for shell-bridge-interceptor.js (Node vm).
 * Run: node public/member/tests/shell_bridge_interceptor_vm.mjs
 * @see test_shell_bridge_interceptor.py (invoked optionally from pytest)
 */
import { readFileSync } from 'fs';
import { runInNewContext } from 'vm';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = dirname(__dirname);
const JS = readFileSync(join(ROOT, 'js', 'shell-bridge-interceptor.js'), 'utf8');

function createSandbox() {
  const posted = [];
  const sandbox = {
    console,
    performance: { now: () => 42 },
    setTimeout: (fn, _ms) => {
      Promise.resolve().then(() => fn());
    },
    location: { origin: 'http://127.0.0.1:5500', search: '' },
    document: {
      readyState: 'complete',
      addEventListener() {},
    },
    postMessageCalls: posted,
  };
  sandbox.addEventListener = function (evt, handler) {
    if (evt === 'message') sandbox._messageHandler = handler;
  };
  sandbox.window = sandbox;
  return sandbox;
}

function loadInterceptor(sandbox) {
  runInNewContext(JS, sandbox, { filename: 'shell-bridge-interceptor.js' });
  if (!sandbox.shellBridgeInterceptor) {
    throw new Error('shellBridgeInterceptor not exposed');
  }
}

function assert(cond, msg) {
  if (!cond) throw new Error(msg || 'assert failed');
}

// --- tests ---
async function run() {
  // 1) Default: no backend => stub marker on search
  {
    const sb = createSandbox();
    loadInterceptor(sb);
    const status = sb.shellBridgeInterceptor.getShellBridgeBackendStatus();
    assert(status.mode === 'stub', 'default mode stub');
    assert(status.registered === false, 'not registered');

    let resolved;
    const source = {
      postMessage(msg, _origin) {
        resolved = msg;
      },
    };
    sb._messageHandler({
      origin: 'http://127.0.0.1:5500',
      source,
      data: {
        type: 'agent_request',
        route: 'openclaw_search',
        payload: { action: 'semantic_search', query: 'x', limit: 2 },
      },
    });
    await new Promise((r) => setImmediate(r));
    assert(resolved && resolved.data && resolved.data.stub === true, 'stub search has stub:true');
    assert(
      resolved.data.results[0].content.includes('Stub') || resolved.data.results[0].path.includes('stub'),
      'stub search content/path marks stub'
    );
  }

  // 2) Register backend => search leaves stub (no stub:true from interceptor when backend returns clean data)
  {
    const sb = createSandbox();
    loadInterceptor(sb);
    const reg = sb.shellBridgeInterceptor.registerShellBridgeBackend({
      search(q, lim) {
        return Promise.resolve({
          results: [
            { content: 'real hit', path: '/repo/a.py', relevance: 0.99 },
          ],
          quantum_coherence: 0.77,
        });
      },
      wspLookup(n) {
        return Promise.resolve({
          results: [
            {
              content: 'WSP body',
              path: `WSP_framework/src/WSP_${n}.md`,
              relevance: 1,
              protocol: String(n),
              title: 'T',
              status: 'active',
            },
          ],
          quantum_coherence: 0.88,
        });
      },
      health() {
        return Promise.resolve({
          results: [
            { content: '{"status":"healthy","backend":"registered"}', path: '/status', relevance: 1 },
          ],
          quantum_coherence: 0.9,
        });
      },
    }, { label: 'test-mock' });

    assert(reg.ok === true, 'registration ok');
    const st = sb.shellBridgeInterceptor.getShellBridgeBackendStatus();
    assert(st.mode === 'registered', 'mode registered');
    assert(st.label === 'test-mock', 'label passed');

    let resolved;
    const source = { postMessage(msg) { resolved = msg; } };
    sb._messageHandler({
      origin: 'http://127.0.0.1:5500',
      source,
      data: {
        type: 'agent_request',
        route: 'openclaw_search',
        payload: { action: 'semantic_search', query: 'q', limit: 3 },
      },
    });
    await new Promise((r) => setImmediate(r));
    assert(resolved.status === 'success', 'search success');
    assert(resolved.data.results[0].content === 'real hit', 'real search body');
    assert(resolved.data.stub !== true, 'no stub flag when backend omits it');

    sb._messageHandler({
      origin: 'http://127.0.0.1:5500',
      source,
      data: {
        type: 'agent_request',
        route: 'openclaw_search',
        payload: { action: 'wsp_lookup', protocol_number: '97' },
      },
    });
    await new Promise((r) => setImmediate(r));
    assert(resolved.data.results && resolved.data.results.length === 1, 'wsp results');

    sb._messageHandler({
      origin: 'http://127.0.0.1:5500',
      source,
      data: {
        type: 'agent_request',
        route: 'openclaw_search',
        payload: { action: 'health' },
      },
    });
    await new Promise((r) => setImmediate(r));
    assert(resolved.data.results[0].content.includes('healthy'), 'health from backend');

    sb.shellBridgeInterceptor.clearShellBridgeBackend();
    const st2 = sb.shellBridgeInterceptor.getShellBridgeBackendStatus();
    assert(st2.mode === 'stub', 'after clear, stub');
  }

  // 3) Invalid registration rejected
  {
    const sb = createSandbox();
    loadInterceptor(sb);
    const bad = sb.shellBridgeInterceptor.registerShellBridgeBackend({ search: async () => ({}) });
    assert(bad.ok === false, 'reject partial backend');
    assert(sb.shellBridgeInterceptor.getShellBridgeBackendStatus().mode === 'stub', 'still stub');
  }

  console.log('shell_bridge_interceptor_vm.mjs: all checks passed');
}

run().catch((e) => {
  console.error(e);
  process.exit(1);
});
