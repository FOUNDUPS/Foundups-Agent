'use strict';

const cp = require('child_process');
const fs = require('fs');
const path = require('path');
const plan = require('./reddog_test_plan');

const TIER_TESTS = Object.freeze({
  fast: plan.FAST_TESTS,
  contract: plan.CONTRACT_TESTS
});

function resolveTest(name) {
  const candidate = path.join(__dirname, name);
  const stat = fs.lstatSync(candidate);
  if (!stat.isFile() || stat.isSymbolicLink()) {
    throw new Error('RedDog tier member is not a regular file: ' + name);
  }
  const root = fs.realpathSync(__dirname);
  const resolved = fs.realpathSync(candidate);
  if (path.dirname(resolved) !== root) throw new Error('RedDog tier member escapes tests root');
  return resolved;
}

function runTest(name) {
  const started = Date.now();
  const result = cp.spawnSync(process.execPath, [resolveTest(name)], {
    cwd: path.resolve(__dirname, '..', '..', '..'),
    encoding: 'utf8', timeout: 120000,
    maxBuffer: plan.CHILD_OUTPUT_CAP_BYTES, windowsHide: true
  });
  if (result.stdout) process.stdout.write(result.stdout);
  if (result.stderr) process.stderr.write(result.stderr);
  if (result.error || result.status !== 0) {
    throw result.error || new Error(name + ' exited ' + result.status);
  }
  return { name, duration_ms: Date.now() - started };
}

function main() {
  const tier = process.argv[2];
  const tests = TIER_TESTS[tier];
  if (!tests) throw new Error('expected RedDog test tier: fast or contract');
  const started = Date.now();
  const receipts = tests.map(runTest);
  const slowest = receipts.reduce((left, right) =>
    left.duration_ms >= right.duration_ms ? left : right);
  console.log(`[REDDOG-TEST] tier=${tier} status=PASS members=${receipts.length} ` +
    `duration_ms=${Date.now() - started} slowest=${slowest.name}:${slowest.duration_ms}`);
}

try { main(); }
catch (error) {
  console.error('[REDDOG-TEST] status=FAIL ' + String(error && error.message || error));
  process.exitCode = 1;
}
