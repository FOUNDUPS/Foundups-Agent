'use strict';

const cp = require('child_process');
const EventEmitter = require('events');
const fs = require('fs');
const os = require('os');
const path = require('path');
const protocol = require('../start_operations_control');
const grounding = require('../grounded_target_continuity');

function signedResult(request, overrides) {
  const value = Object.assign(protocol.failureResult(request.action, 'none', request), {
    accepted: true, status: 'DETERMINED', intent_id: 'sha256:' + 'a'.repeat(64),
    cycle_id: 'sha256:' + 'b'.repeat(64), repo_head_sha: 'c'.repeat(40),
    rejection_reasons: []
  }, overrides || {});
  const body = { ...value };
  delete body.response_id;
  value.response_id = grounding.canonicalDigest(body);
  return value;
}

function signedProgress(request) {
  const value = {
    schema_version: protocol.PROGRESS_SCHEMA, stage: 'resident_cycle_submitting',
    action: request.action, control_request_id: request.control_request_id,
    intent_id: 'sha256:' + 'a'.repeat(64), repo_head_sha: 'c'.repeat(40),
    operations_profile_id: protocol.PROFILE_ID
  };
  value.progress_id = grounding.canonicalDigest(value);
  return value;
}

function pythonResult(request) {
  const repoRoot = path.resolve(__dirname, '..', '..', '..');
  const code = [
    'from modules.communication.moltbot_bridge.src.reddog_start_operations_control_receipt import reject,result_json',
    'from modules.communication.moltbot_bridge.src.reddog_start_operations_profile import StartOperationsProfile',
    `print(result_json(reject("submit", StartOperationsProfile(), {}, ("test_rejection",), control_request_id="${request.control_request_id}")))`
  ].join(';');
  return JSON.parse(cp.execFileSync(process.env.PYTHON || 'python',
    ['-B', '-c', code], { cwd: repoRoot, encoding: 'utf8' }).trim());
}

function fakeChild(lines, exitCode) {
  const child = new EventEmitter();
  child.stdout = new EventEmitter(); child.stderr = new EventEmitter();
  child.stdin = { end() {} }; child.kill = () => { child.killed = true; };
  process.nextTick(() => {
    child.stdout.emit('data', lines.join('\n') + '\n');
    child.emit('close', exitCode || 0);
  });
  return child;
}

function chunkedChild(chunks) {
  const child = new EventEmitter();
  child.stdout = new EventEmitter(); child.stderr = new EventEmitter();
  child.stdin = { end() {} }; child.kill = () => { child.killed = true; };
  process.nextTick(() => {
    for (const chunk of chunks) child.stdout.emit('data', chunk);
    child.emit('close', 0);
  });
  return child;
}

function approvedRuntime() {
  const repoRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'reddog-operations-'));
  const bin = path.join(repoRoot, '.venv', 'Scripts');
  const sitePackages = path.join(repoRoot, '.venv', 'Lib', 'site-packages');
  fs.mkdirSync(bin, { recursive: true });
  fs.mkdirSync(sitePackages, { recursive: true });
  const interpreter = path.join(bin, 'python.exe');
  fs.writeFileSync(interpreter, '');
  return { repoRoot, interpreter, sitePackages };
}

function fakeMaterializer(runtime) {
  return () => ({
    runtimeRoot: runtime.repoRoot, targetRepoRoot: runtime.repoRoot,
    manifestPath: path.join(runtime.repoRoot, 'runtime-manifest.json'),
    manifestDigest: '0'.repeat(64),
    scriptPath: (value) => path.join(runtime.repoRoot, 'sealed', path.basename(value)),
    cleanup() {}
  });
}

module.exports = Object.freeze({
  approvedRuntime, chunkedChild, fakeChild, fakeMaterializer,
  pythonResult, signedProgress, signedResult
});
