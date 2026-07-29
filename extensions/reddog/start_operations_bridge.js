'use strict';

const cp = require('child_process');
const path = require('path');
const protocol = require('./start_operations_control');
const interpreterPolicy = require('./start_operations_interpreter');
const runtimeMaterializer = require('./backend_compatibility_runtime_materializer');

const MAX_STDOUT_BYTES = 2 * 1024 * 1024;
const MAX_STDERR_BYTES = 64 * 1024;
const MAX_FRAMES = 256;
const DEFAULT_DEADLINE_MS = 15 * 60 * 1000;
const PYTHON_BOOTSTRAP = path.join(
  __dirname, 'start_operations_python_bootstrap.py'
);
const SEALED_BOOTSTRAP_RELATIVE = path.join(
  'extensions', 'reddog', 'start_operations_python_bootstrap.py'
);

function run(options) {
  const opts = options && typeof options === 'object' ? options : {};
  const action = opts.request && opts.request.action;
  return new Promise((resolve) => {
    try {
      const launched = launch(opts);
      collect(launched.child, opts, resolve, launched.cleanup);
    } catch (_err) {
      resolve(protocol.failureResult(
        action, 'start_operations_bridge_spawn_failed', opts.request
      ));
    }
  });
}

function launch(options) {
  const runtime = interpreterPolicy.approved(
    options.interpreter, options.repoRoot
  );
  if (!runtime) throw new Error('unapproved_interpreter');
  const source = (options.materialize || runtimeMaterializer.materialize)(
    runtime.repoRoot, options.materializerOptions
  );
  try {
    const args = [
      '-I', '-S', '-B', PYTHON_BOOTSTRAP,
      source.scriptPath(options.script), source.runtimeRoot,
      source.targetRepoRoot, runtime.sitePackages,
      source.manifestPath, source.manifestDigest
    ];
    const childEnvironment = sealedEnvironment(
      options.env, source, runtime
    );
    const child = (options.spawn || cp.spawn)(runtime.interpreter, args, {
      cwd: source.runtimeRoot, env: childEnvironment,
      stdio: ['pipe', 'pipe', 'pipe'], windowsHide: true
    });
    return { child, cleanup: source.cleanup };
  } catch (error) {
    source.cleanup();
    throw error;
  }
}

function sealedEnvironment(base, source, runtime) {
  return {
    ...(base || {}),
    REDDOG_SEALED_RUNTIME_REQUIRED: '1',
    REDDOG_SEALED_RUNTIME_ROOT: source.runtimeRoot,
    REDDOG_SEALED_RUNTIME_MANIFEST_PATH: source.manifestPath,
    REDDOG_SEALED_RUNTIME_MANIFEST_DIGEST: source.manifestDigest,
    REDDOG_SEALED_RUNTIME_BOOTSTRAP_PATH: path.join(
      source.runtimeRoot, SEALED_BOOTSTRAP_RELATIVE
    ),
    REDDOG_SEALED_RUNTIME_SITE_PACKAGES: runtime.sitePackages
  };
}

function collect(child, options, resolve, cleanup) {
  const state = {
    stdout: '', stdoutBytes: 0, stderrBytes: 0, frameCount: 0, finalResult: null
  };
  const controls = collectionControls(child, options, resolve, state, cleanup);
  attachOutputListeners(child, options, state, controls);
  attachLifecycleListeners(child, options, state, controls);
  writeRequest(child, options, controls);
}

function collectionControls(child, options, resolve, state, cleanup) {
  let settled = false;
  const finish = (value) => {
    if (settled) return;
    settled = true;
    clearTimeout(timer);
    if (typeof cleanup === 'function') cleanup();
    resolve(value);
  };
  const fail = (reason) => {
    if (child && typeof child.kill === 'function') child.kill();
    finish(protocol.failureResult(action, reason, options.request));
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
    if (controls.isSettled()) return;
    const text = String(chunk || '');
    state.stdoutBytes += Buffer.byteLength(text, 'utf8');
    state.stdout += text;
    if (state.stdoutBytes > MAX_STDOUT_BYTES) {
      controls.fail('start_operations_bridge_output_too_large');
      return;
    }
    const parsed = consumeLines(
      state.stdout, options.request, options.onProgress, state.frameCount
    );
    state.stdout = parsed.remaining;
    state.frameCount = parsed.frameCount;
    if (parsed.frameLimitExceeded) {
      controls.fail('start_operations_bridge_frame_limit_exceeded');
      return;
    }
    if (parsed.result) state.finalResult = parsed.result;
  });
  child.stderr.on('data', (chunk) => {
    if (controls.isSettled()) return;
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
    const parsed = consumeLines(
      state.stdout + '\n', options.request, options.onProgress, state.frameCount
    );
    if (parsed.frameLimitExceeded) {
      controls.fail('start_operations_bridge_frame_limit_exceeded');
      return;
    }
    if (parsed.result) state.finalResult = parsed.result;
    controls.finish(code === 0 && state.finalResult
      ? state.finalResult
      : protocol.failureResult(
        action, 'start_operations_bridge_failed', options.request
      ));
  });
}

function writeRequest(child, options, controls) {
  try {
    child.stdin.end(JSON.stringify(options.request || {}));
  } catch (_err) {
    controls.fail('start_operations_bridge_input_failed');
  }
}

function consumeFrame(line, request, onProgress) {
  let value;
  try {
    value = JSON.parse(line);
  } catch (_err) {
    return null;
  }
  const progress = protocol.validateProgress(value, request);
  if (progress && typeof onProgress === 'function') onProgress(progress);
  return protocol.validateResult(value, request);
}

function consumeLines(buffer, request, onProgress, frameCount) {
  const lines = String(buffer || '').split(/\r?\n/);
  const remaining = lines.pop() || '';
  let result = null;
  let count = Number(frameCount || 0);
  for (const line of lines) {
    if (!line.trim()) continue;
    if (count >= MAX_FRAMES) {
      return {
        remaining: '', result: null, frameCount: count, frameLimitExceeded: true
      };
    }
    count += 1;
    const terminal = consumeFrame(line, request, onProgress);
    if (terminal) result = terminal;
  }
  return {
    remaining, result, frameCount: count, frameLimitExceeded: false
  };
}

module.exports = {
  DEFAULT_DEADLINE_MS,
  MAX_STDERR_BYTES,
  MAX_STDOUT_BYTES,
  MAX_FRAMES,
  PYTHON_BOOTSTRAP,
  consumeLines,
  run
};
