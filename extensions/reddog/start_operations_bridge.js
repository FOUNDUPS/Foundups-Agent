'use strict';

const cp = require('child_process');
const protocol = require('./start_operations_control');

const MAX_STDOUT_BYTES = 2 * 1024 * 1024;
const MAX_STDERR_BYTES = 64 * 1024;
const DEFAULT_DEADLINE_MS = 15 * 60 * 1000;

function run(options) {
  const opts = options && typeof options === 'object' ? options : {};
  const action = opts.request && opts.request.action;
  return new Promise((resolve) => {
    let child;
    try {
      child = (opts.spawn || cp.spawn)(
        opts.interpreter,
        ['-B', opts.script],
        {
          cwd: opts.repoRoot,
          env: opts.env,
          stdio: ['pipe', 'pipe', 'pipe'],
          windowsHide: true
        }
      );
    } catch (_err) {
      resolve(protocol.failureResult(action, 'start_operations_bridge_spawn_failed'));
      return;
    }
    collect(child, opts, resolve);
  });
}

function collect(child, options, resolve) {
  const state = { stdout: '', stderrBytes: 0, finalResult: null };
  const controls = collectionControls(child, options, resolve, state);
  attachOutputListeners(child, options, state, controls);
  attachLifecycleListeners(child, options, state, controls);
  writeRequest(child, options, controls);
}

function collectionControls(child, options, resolve, state) {
  let settled = false;
  const finish = (value) => {
    if (settled) return;
    settled = true;
    clearTimeout(timer);
    resolve(value);
  };
  const fail = (reason) => {
    if (child && typeof child.kill === 'function') child.kill();
    finish(protocol.failureResult(action, reason));
  };
  const action = options.request && options.request.action;
  const timer = setTimeout(
    () => fail('start_operations_bridge_timeout'),
    options.deadlineMs || DEFAULT_DEADLINE_MS
  );
  return { fail, finish, isSettled: () => settled };
}

function attachOutputListeners(child, options, state, controls) {
  child.stdout.on('data', (chunk) => {
    state.stdout += String(chunk || '');
    if (Buffer.byteLength(state.stdout, 'utf8') > MAX_STDOUT_BYTES) {
      controls.fail('start_operations_bridge_output_too_large');
      return;
    }
    const parsed = consumeLines(state.stdout, options.onProgress);
    state.stdout = parsed.remaining;
    if (parsed.result) state.finalResult = parsed.result;
  });
  child.stderr.on('data', (chunk) => {
    state.stderrBytes += Buffer.byteLength(String(chunk || ''), 'utf8');
    if (state.stderrBytes > MAX_STDERR_BYTES) {
      controls.fail('start_operations_bridge_stderr_too_large');
    }
  });
}

function attachLifecycleListeners(child, options, state, controls) {
  const action = options.request && options.request.action;
  child.once('error', () => controls.fail('start_operations_bridge_failed'));
  child.once('close', (code) => {
    if (controls.isSettled()) return;
    const parsed = consumeLines(state.stdout + '\n', options.onProgress);
    if (parsed.result) state.finalResult = parsed.result;
    controls.finish(code === 0 && state.finalResult
      ? state.finalResult
      : protocol.failureResult(action, 'start_operations_bridge_failed'));
  });
}

function writeRequest(child, options, controls) {
  try {
    child.stdin.end(JSON.stringify(options.request || {}));
  } catch (_err) {
    controls.fail('start_operations_bridge_input_failed');
  }
}

function consumeLines(buffer, onProgress) {
  const lines = String(buffer || '').split(/\r?\n/);
  const remaining = lines.pop() || '';
  let result = null;
  for (const line of lines) {
    if (!line.trim()) continue;
    let value;
    try {
      value = JSON.parse(line);
    } catch (_err) {
      continue;
    }
    const progress = protocol.validateProgress(value);
    if (progress && typeof onProgress === 'function') onProgress(progress);
    const terminal = protocol.validateResult(value);
    if (terminal) result = terminal;
  }
  return { remaining, result };
}

module.exports = {
  DEFAULT_DEADLINE_MS,
  MAX_STDERR_BYTES,
  MAX_STDOUT_BYTES,
  consumeLines,
  run
};
