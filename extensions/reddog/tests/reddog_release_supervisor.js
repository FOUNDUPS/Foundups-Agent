'use strict';

const cp = require('child_process');
const crypto = require('crypto');
const path = require('path');
const plan = require('./reddog_test_plan');

const TERMINATION_GRACE_MS = 1000;
const SETTLEMENT_GRACE_MS = 2500;
const TASKKILL_TIMEOUT_MS = 750;
const realClock = Object.freeze({ now: Date.now, setTimeout, clearTimeout });

function spawnWorker(group, nonce) {
  const worker = path.join(__dirname, 'reddog_release_worker.js');
  const env = Object.assign({}, process.env, { REDDOG_RELEASE_PARENT_NONCE: nonce });
  return cp.spawn(process.execPath,
    [worker, '--reddog-release-worker', group.id, nonce], {
      cwd: path.resolve(__dirname, '..', '..', '..'), env, shell: false,
      detached: process.platform !== 'win32', windowsHide: true,
      stdio: ['ignore', 'pipe', 'pipe']
    });
}

function terminatePosix(child, force, killProcess) {
  const signal = force ? 'SIGKILL' : 'SIGTERM';
  const killGroup = killProcess || process.kill;
  try { killGroup(-child.pid, signal); return true; }
  catch (_) {
    try { return child.kill(signal); } catch (_) { return false; }
  }
}

function windowsTaskkillPath(environment) {
  const root = environment.SystemRoot || environment.SYSTEMROOT || 'C:\\Windows';
  if (!path.win32.isAbsolute(root)) return '';
  return path.win32.join(path.win32.normalize(root), 'System32', 'taskkill.exe');
}

function watchTaskkill(killer, clock, timeoutMs) {
  return new Promise((resolve) => {
    let settled = false;
    let timer;
    const finish = (success) => {
      if (settled) return;
      settled = true;
      clock.clearTimeout(timer);
      killer.removeListener('exit', onExit);
      killer.removeListener('close', onClose);
      resolve(Boolean(success));
    };
    const onError = () => finish(false);
    const onExit = (code, signal) => finish(code === 0 && signal === null);
    const onClose = (code, signal) => finish(code === 0 && signal === null);
    killer.on('error', onError);
    killer.once('exit', onExit);
    killer.once('close', onClose);
    timer = clock.setTimeout(() => {
      try { killer.kill(); } catch (_) { /* failure is already explicit */ }
      finish(false);
    }, timeoutMs);
    if (timer && typeof timer.unref === 'function') timer.unref();
    try { killer.unref(); } catch (_) { finish(false); }
  });
}

function terminateWindows(child, force, options) {
  const settings = options || {};
  const executable = windowsTaskkillPath(settings.environment || process.env);
  if (!executable) return Promise.resolve(false);
  const args = ['/PID', String(child.pid), '/T'];
  if (force) args.push('/F');
  let killer;
  try {
    killer = (settings.spawn || cp.spawn)(executable, args, {
      shell: false, windowsHide: true, stdio: 'ignore'
    });
  } catch (_) { return Promise.resolve(false); }
  if (!killer || typeof killer.on !== 'function') return Promise.resolve(false);
  return watchTaskkill(killer, settings.clock || realClock,
    settings.timeoutMs || TASKKILL_TIMEOUT_MS);
}

function terminateTree(child, force) {
  if (!child || !Number.isInteger(child.pid) || child.pid <= 0) return false;
  return process.platform === 'win32' ? terminateWindows(child, force) : terminatePosix(child, force);
}

function resultPassed(result) {
  return result.code === 0 && result.signal === null && !result.timedOut &&
    !result.terminationFailed && !result.terminationUnconfirmed &&
    !result.stdout.exceeded && !result.stderr.exceeded;
}

function newControllerContext(group, dependencies, limits) {
  const context = {
    group, dependencies, limits, clock: dependencies.clock,
    child: dependencies.spawn(group, dependencies.nonce),
    started: dependencies.clock.now(), settled: false, timers: [],
    pendingTerminations: 0,
    state: { timedOut: false, timeoutReason: '', terminationFailed: false },
    stdout: { bytes: 0, chunks: [], exceeded: false },
    stderr: { bytes: 0, chunks: [], exceeded: false }
  };
  context.promise = new Promise((resolve) => { context.resolve = resolve; });
  return context;
}

function releaseChildHandles(child) {
  for (const stream of [child && child.stdout, child && child.stderr]) {
    if (stream && typeof stream.destroy === 'function') stream.destroy();
  }
  if (child && typeof child.removeAllListeners === 'function') child.removeAllListeners();
  if (child && typeof child.unref === 'function') child.unref();
}

function finishController(context, code, signal, unconfirmed) {
  if (context.settled) return;
  context.settled = true;
  for (const timer of context.timers) context.clock.clearTimeout(timer);
  if (unconfirmed && context.pendingTerminations) context.state.terminationFailed = true;
  if (unconfirmed) releaseChildHandles(context.child);
  context.resolve({ group: context.group, code, signal,
    stdout: context.stdout, stderr: context.stderr, ...context.state,
    terminationUnconfirmed: Boolean(unconfirmed),
    duration_ms: context.clock.now() - context.started });
}

function recordTerminationOutcome(context, outcome) {
  if (!outcome || typeof outcome.then !== 'function') {
    if (!outcome) context.state.terminationFailed = true;
    return;
  }
  context.pendingTerminations += 1;
  const finish = (success) => {
    if (!success) context.state.terminationFailed = true;
    context.pendingTerminations -= 1;
  };
  outcome.then(finish, () => finish(false));
}

function attemptTermination(context, force) {
  let outcome;
  try { outcome = context.dependencies.terminate(context.child, force); }
  catch (_) { context.state.terminationFailed = true; return; }
  recordTerminationOutcome(context, outcome);
}

function stopController(context, reason, timedOut) {
  if (context.settled || context.state.timeoutReason) return;
  context.state.timedOut = Boolean(timedOut);
  context.state.timeoutReason = reason;
  attemptTermination(context, false);
  context.timers.push(context.clock.setTimeout(() => {
    attemptTermination(context, true);
  }, context.limits.terminationGraceMs));
  context.timers.push(context.clock.setTimeout(() =>
    finishController(context, null, 'termination_unconfirmed', true),
  context.limits.settlementGraceMs));
}

function captureController(context, target, chunk) {
  target.bytes += chunk.length;
  if (target.bytes > context.limits.outputCapBytes) {
    target.exceeded = true;
    stopController(context, 'output_overflow', false);
  } else target.chunks.push(chunk);
}

function wireController(context) {
  context.child.stdout.on('data', (chunk) => captureController(context, context.stdout, chunk));
  context.child.stderr.on('data', (chunk) => captureController(context, context.stderr, chunk));
  context.child.on('error', () => finishController(context, null, 'spawn_error', false));
  context.child.on('close', (code, signal) => finishController(context, code, signal, false));
  context.timers.push(context.clock.setTimeout(() =>
    stopController(context, 'child_timeout', true), context.limits.childTimeoutMs));
}

function createGroupController(group, dependencies, limits) {
  const context = newControllerContext(group, dependencies, limits);
  wireController(context);
  return { promise: context.promise,
    expire: () => stopController(context, 'release_timeout', true) };
}

function defaultLimits(overrides) {
  return Object.freeze({
    childTimeoutMs: plan.RELEASE_CHILD_TIMEOUT_MS,
    releaseCeilingMs: plan.RELEASE_CEILING_MS,
    outputCapBytes: plan.CHILD_OUTPUT_CAP_BYTES,
    terminationGraceMs: TERMINATION_GRACE_MS,
    settlementGraceMs: SETTLEMENT_GRACE_MS,
    ...(overrides || {})
  });
}

async function runPromotion(groups, options) {
  const settings = options || {};
  const clock = settings.clock || realClock;
  const startedAt = settings.startedAt === undefined ? clock.now() : settings.startedAt;
  const limits = defaultLimits(settings.limits);
  const dependencies = {
    clock, nonce: settings.nonce || crypto.randomBytes(16).toString('hex'),
    spawn: settings.spawn || spawnWorker, terminate: settings.terminate || terminateTree
  };
  const controllers = groups.map((group) => createGroupController(group, dependencies, limits));
  let releaseTimedOut = false;
  const remaining = Math.max(0, limits.releaseCeilingMs - (clock.now() - startedAt));
  const deadline = clock.setTimeout(() => {
    releaseTimedOut = true;
    for (const controller of controllers) controller.expire();
  }, remaining);
  const results = await Promise.all(controllers.map((controller) => controller.promise));
  clock.clearTimeout(deadline);
  return { results, releaseTimedOut, duration_ms: clock.now() - startedAt,
    passed: !releaseTimedOut && results.every(resultPassed) };
}

function printResult(result) {
  process.stdout.write(`[REDDOG-RELEASE-GROUP] id=${result.group.id} ` +
    `duration_ms=${result.duration_ms} timed_out=${result.timedOut} ` +
    `timeout_reason=${result.timeoutReason || 'none'}\n`);
  if (result.stdout.chunks.length) process.stdout.write(Buffer.concat(result.stdout.chunks));
  if (result.stderr.chunks.length) process.stderr.write(Buffer.concat(result.stderr.chunks));
}

function printReceipt(receipt) {
  for (const result of receipt.results) printResult(result);
  const slowest = receipt.results.reduce((left, right) =>
    left.duration_ms >= right.duration_ms ? left : right);
  console.log(`[REDDOG-RELEASE] status=${receipt.passed ? 'PASS' : 'FAIL'} ` +
    `groups=${receipt.results.length} worker_cap=${plan.RELEASE_WORKER_CAP} ` +
    `duration_ms=${receipt.duration_ms} release_timed_out=${receipt.releaseTimedOut} ` +
    `slowest=${slowest.group.id}:${slowest.duration_ms}`);
}

module.exports = Object.freeze({
  TERMINATION_GRACE_MS, SETTLEMENT_GRACE_MS, TASKKILL_TIMEOUT_MS,
  terminatePosix, terminateWindows, createGroupController, defaultLimits,
  resultPassed, runPromotion, printReceipt
});
