'use strict';

const assert = require('assert');
const cp = require('child_process');
const EventEmitter = require('events');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const supervisor = require('./reddog_release_supervisor');
const worker = require('./reddog_release_worker');

function loadPrivateSupervisor(childProcess, environment) {
  const filename = path.join(__dirname, 'reddog_release_supervisor.js');
  const source = fs.readFileSync(filename, 'utf8') +
    '\nmodule.exports = { terminateWindows, terminatePosix };';
  const sandbox = {
    Buffer, console, module: { exports: {} }, exports: {}, __dirname,
    process: {
      env: environment, platform: process.platform, execPath: process.execPath,
      stdout: process.stdout, stderr: process.stderr, kill: process.kill
    },
    require: (request) => {
      if (request === 'child_process') return childProcess;
      if (request.startsWith('./')) return require(path.resolve(__dirname, request));
      return require(request);
    },
    setTimeout, clearTimeout
  };
  vm.runInNewContext(source, sandbox, { filename });
  return sandbox.module.exports;
}

class FakeClock {
  constructor() { this.time = 0; this.next = 1; this.timers = new Map(); }
  now = () => this.time;
  setTimeout = (callback, delay) => {
    const id = this.next++;
    this.timers.set(id, { at: this.time + delay, callback });
    return id;
  };
  clearTimeout = (id) => { this.timers.delete(id); };
  tick(milliseconds) {
    const target = this.time + milliseconds;
    while (true) {
      const entries = [...this.timers.entries()].filter((entry) => entry[1].at <= target)
        .sort((left, right) => left[1].at - right[1].at);
      if (!entries.length) break;
      const [id, timer] = entries[0];
      this.timers.delete(id);
      this.time = timer.at;
      timer.callback();
    }
    this.time = target;
  }
}

class FakeChild extends EventEmitter {
  constructor(pid) {
    super();
    this.pid = pid;
    this.stdout = new EventEmitter();
    this.stderr = new EventEmitter();
    this.stdout.destroy = () => { this.stdoutDestroyed = true; };
    this.stderr.destroy = () => { this.stderrDestroyed = true; };
  }
  unref() { this.unrefCalled = true; }
}

class FakeKiller extends EventEmitter {
  unref() { this.unrefCalled = true; }
  kill() { this.killCalled = true; return true; }
}

const group = Object.freeze({ id: 'fake', tests: Object.freeze([]) });
const limits = Object.freeze({
  childTimeoutMs: 10, releaseCeilingMs: 20, outputCapBytes: 64,
  terminationGraceMs: 2, settlementGraceMs: 5
});

async function proveChildTimeoutRejectsExitZero() {
  const clock = new FakeClock();
  const child = new FakeChild(11);
  const calls = [];
  const controller = supervisor.createGroupController(group, {
    clock, nonce: '0'.repeat(32), spawn: () => child,
    terminate: (_child, force) => { calls.push(force); return true; }
  }, limits);
  clock.tick(10);
  child.emit('close', 0, null);
  const result = await controller.promise;
  assert.strictEqual(result.timedOut, true);
  assert.strictEqual(result.timeoutReason, 'child_timeout');
  assert.strictEqual(supervisor.resultPassed(result), false);
  assert.deepStrictEqual(calls, [false]);
}

async function proveKillFailureSettlesBounded() {
  const clock = new FakeClock();
  const child = new FakeChild(12);
  const controller = supervisor.createGroupController(group, {
    clock, nonce: '1'.repeat(32), spawn: () => child, terminate: () => false
  }, limits);
  clock.tick(15);
  const result = await controller.promise;
  assert.strictEqual(result.timedOut, true);
  assert.strictEqual(result.terminationFailed, true);
  assert.strictEqual(result.terminationUnconfirmed, true);
  assert(result.duration_ms <= 15, 'kill failure must settle within fixed grace');
  assert.strictEqual(child.stdoutDestroyed && child.stderrDestroyed && child.unrefCalled, true);
  assert.strictEqual(supervisor.resultPassed(result), false);
}

async function proveParentDeadlineOverridesExitZero() {
  const clock = new FakeClock();
  const children = [];
  const parentLimits = Object.freeze({ ...limits, childTimeoutMs: 30 });
  const pending = supervisor.runPromotion([group], {
    clock, startedAt: 0, nonce: '2'.repeat(32), limits: parentLimits,
    spawn: () => { const child = new FakeChild(13); children.push(child); return child; },
    terminate: () => true
  });
  clock.tick(20);
  children[0].emit('close', 0, null);
  const receipt = await pending;
  assert.strictEqual(receipt.releaseTimedOut, true);
  assert.strictEqual(receipt.results[0].timeoutReason, 'release_timeout');
  assert.strictEqual(receipt.passed, false);
}

function proveAmbientCannotSelectWorker() {
  assert.throws(() => worker.parseInvocation(['node', 'worker'], {
    REDDOG_CONTRACT_GROUP: 'core', REDDOG_RELEASE_PARENT_NONCE: '3'.repeat(32)
  }), /internal RedDog release worker invocation required/);
}

async function proveAsyncTaskkillErrorIsBounded() {
  const killer = new FakeKiller();
  const calls = [];
  const internals = loadPrivateSupervisor({
    spawn: (executable, args, options) => {
      calls.push({ executable, args, options });
      return killer;
    }
  }, { SYSTEMROOT: 'c:\\Windows' });
  const pending = internals.terminateWindows(new FakeChild(14), false);
  let thrown;
  await new Promise((resolve) => queueMicrotask(() => {
    try { killer.emit('error', new Error('synthetic async taskkill ENOENT')); }
    catch (error) { thrown = error; }
    resolve();
  }));
  assert.ifError(thrown);
  assert.strictEqual(await pending, false);
  assert.strictEqual(killer.unrefCalled, true);
  assert.strictEqual(path.win32.isAbsolute(calls[0].executable), true);
  assert.strictEqual(Array.from(calls[0].args).join(' '), '/PID 14 /T');
  assert.strictEqual(calls[0].options.shell, false);
  assert.doesNotThrow(() => killer.emit('error', new Error('late error')));
}

async function proveInvalidSystemRootProbe() {
  if (process.platform !== 'win32') return;
  const invalidRoot = `C:\\RedDogMissingSystemRoot_${process.pid}`;
  const internals = loadPrivateSupervisor(cp, {
    ...process.env, SystemRoot: invalidRoot, SYSTEMROOT: invalidRoot
  });
  const pending = internals.terminateWindows(new FakeChild(process.pid), false);
  assert.strictEqual(await pending, false);
}

async function proveTaskkillExitAndForceContracts() {
  const killers = [new FakeKiller(), new FakeKiller()];
  const calls = [];
  const internals = loadPrivateSupervisor({
    spawn: (executable, args, options) => {
      calls.push({ executable, args, options });
      return killers[calls.length - 1];
    }
  }, { SystemRoot: 'C:\\Windows' });
  const nonzero = internals.terminateWindows(new FakeChild(15), false);
  killers[0].emit('close', 1, null);
  assert.strictEqual(await nonzero, false);
  const forced = internals.terminateWindows(new FakeChild(16), true);
  killers[1].emit('exit', 0, null);
  assert.strictEqual(await forced, true);
  assert.strictEqual(Array.from(calls[1].args).join(' '), '/PID 16 /T /F');
  assert.strictEqual(killers[0].listenerCount('close'), 0);
  assert.strictEqual(killers[1].listenerCount('exit'), 0);
}

async function proveTaskkillTimeoutAndPathContracts() {
  const clock = new FakeClock();
  const killer = new FakeKiller();
  let spawnCalls = 0;
  const internals = loadPrivateSupervisor({
    spawn: () => { spawnCalls += 1; return killer; }
  }, { SYSTEMROOT: 'C:\\Windows' });
  const timed = internals.terminateWindows(new FakeChild(17), false,
    { clock, timeoutMs: 3 });
  clock.tick(3);
  assert.strictEqual(await timed, false);
  assert.strictEqual(killer.killCalled, true);
  assert.strictEqual(killer.unrefCalled, true);
  const invalid = loadPrivateSupervisor({
    spawn: () => { spawnCalls += 1; return new FakeKiller(); }
  }, { SystemRoot: 'relative-root' });
  assert.strictEqual(await invalid.terminateWindows(new FakeChild(18), false), false);
  assert.strictEqual(spawnCalls, 1);
}

function provePosixTerminationUnchanged() {
  const calls = [];
  const internals = loadPrivateSupervisor(cp, process.env);
  const child = new FakeChild(19);
  const result = internals.terminatePosix(child, true, (pid, signal) => {
    calls.push([pid, signal]);
  });
  assert.strictEqual(result, true);
  assert.deepStrictEqual(calls, [[-19, 'SIGKILL']]);
}

async function proveAsyncTerminationFailureReceipt() {
  const clock = new FakeClock();
  const gracefulKiller = new FakeKiller();
  const forceKiller = new FakeKiller();
  const killers = [gracefulKiller, forceKiller];
  const forces = [];
  const internals = loadPrivateSupervisor({ spawn: () => killers.shift() }, {
    SystemRoot: 'C:\\Windows'
  });
  const controller = supervisor.createGroupController(group, {
    clock, nonce: '4'.repeat(32), spawn: () => new FakeChild(20),
    terminate: (child, force) => {
      forces.push(force);
      return internals.terminateWindows(child, force, { clock, timeoutMs: 1 });
    }
  }, limits);
  clock.tick(10);
  gracefulKiller.emit('error', new Error('graceful taskkill failure'));
  await Promise.resolve();
  clock.tick(2);
  forceKiller.emit('error', new Error('force taskkill failure'));
  await Promise.resolve();
  clock.tick(3);
  const result = await controller.promise;
  assert.deepStrictEqual(forces, [false, true]);
  assert.strictEqual(result.terminationFailed, true);
  assert.strictEqual(result.terminationUnconfirmed, true);
  assert.strictEqual(supervisor.resultPassed(result), false);
}

(async () => {
  if (process.argv.includes('--probe-real-taskkill')) {
    await proveInvalidSystemRootProbe();
    console.log('RedDog invalid-SystemRoot taskkill probe: PASS');
    return;
  }
  proveAmbientCannotSelectWorker();
  provePosixTerminationUnchanged();
  await proveAsyncTaskkillErrorIsBounded();
  await proveInvalidSystemRootProbe();
  await proveTaskkillExitAndForceContracts();
  await proveTaskkillTimeoutAndPathContracts();
  await proveAsyncTerminationFailureReceipt();
  await proveChildTimeoutRejectsExitZero();
  await proveKillFailureSettlesBounded();
  await proveParentDeadlineOverridesExitZero();
  console.log('RedDog release supervisor bypass/timeout contracts: PASS');
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
