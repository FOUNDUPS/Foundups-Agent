'use strict';

const assert = require('assert');
const cp = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

const environment = require('../start_operations_environment');
const readiness = require('../governed_git_readiness');
const governedGit = require('../governed_git_context');

const FORBIDDEN = Object.freeze([
  'UNRELATED_SENTINEL', 'OPENROUTER_API_KEY', 'GITHUB_TOKEN',
  'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'GENERIC_API_KEY',
  'PYTHONPATH', 'PYTHONHOME', 'PYTHONSTARTUP', 'PYTHONINSPECT',
  'NODE_OPTIONS', 'NODE_PATH', 'LD_PRELOAD', 'LD_LIBRARY_PATH',
  'DYLD_INSERT_LIBRARIES', 'DYLD_LIBRARY_PATH', 'SSH_AUTH_SOCK',
  'SSH_AGENT_PID', 'GIT_SSH', 'GIT_SSH_COMMAND', 'GIT_ASKPASS',
  'GIT_CONFIG_COUNT', 'GIT_DIR', 'GIT_WORK_TREE'
]);

const FIXED_GIT = Object.freeze({
  GIT_CONFIG_NOSYSTEM: '1',
  GIT_CONFIG_GLOBAL: process.platform === 'win32' ? 'NUL' : os.devNull,
  GIT_ATTR_NOSYSTEM: '1',
  GIT_EXTERNAL_DIFF: '',
  GIT_NO_LAZY_FETCH: '1',
  GIT_NO_REPLACE_OBJECTS: '1',
  GIT_OPTIONAL_LOCKS: '0',
  GIT_PAGER: 'cat',
  GIT_TERMINAL_PROMPT: '0'
});

function fixture() {
  return Object.assign({
    PATH: 'upper-path', Path: 'mixed-path', PATHEXT: '.EXE;.CMD',
    SYSTEMROOT: 'upper-root', SystemRoot: 'mixed-root', WINDIR: 'windows-dir',
    COMSPEC: 'upper-shell', ComSpec: 'mixed-shell', TEMP: 'temp-dir',
    TMP: 'tmp-dir', TMPDIR: 'tmpdir-dir', LANG: 'en_US.UTF-8',
    LC_ALL: 'C.UTF-8', LC_CTYPE: 'C.UTF-8', HOME: 'ambient-home',
    USERPROFILE: 'ambient-profile', VIRTUAL_ENV: 'ambient-venv'
  }, Object.fromEntries(FORBIDDEN.map((key) => [key, 'ambient-marker'])),
  Object.fromEntries(Object.keys(FIXED_GIT).map((key) => [key, 'caller-override'])));
}

function assertAmbientForbiddenFieldsDoNotCross() {
  const saved = Object.fromEntries(FORBIDDEN.map((key) => [key, process.env[key]]));
  try {
    for (const key of FORBIDDEN) process.env[key] = 'ambient-marker';
    const env = readiness.sanitizedGitEnv();
    for (const key of FORBIDDEN) assert.strictEqual(env[key], undefined, key);
  } finally { restoreEnvironment(saved); }
}

function assertClosedBuilder() {
  assert.strictEqual(typeof environment.buildGovernedGit, 'function');
  const source = fixture();
  const before = JSON.stringify(source);
  const first = environment.buildGovernedGit(source);
  const second = environment.buildGovernedGit(source);
  assert.notStrictEqual(first, source);
  assert.notStrictEqual(first, second);
  first.TEMP = 'changed';
  assert.strictEqual(second.TEMP, 'temp-dir');
  assert.strictEqual(JSON.stringify(source), before);
  for (const key of FORBIDDEN) assert.strictEqual(second[key], undefined, key);
  for (const [key, value] of Object.entries(FIXED_GIT)) {
    assert.strictEqual(second[key], value, key + ' must be pinned');
  }
  assert.strictEqual(second.HOME, undefined);
  assert.strictEqual(second.USERPROFILE, undefined);
  assert.strictEqual(second.VIRTUAL_ENV, undefined);
  const allowed = process.platform === 'win32'
    ? ['SystemRoot', 'WINDIR', 'ComSpec', 'TEMP', 'TMP',
      'LANG', 'LC_ALL', 'LC_CTYPE']
    : ['TEMP', 'TMP', 'TMPDIR', 'LANG', 'LC_ALL', 'LC_CTYPE'];
  assert.deepStrictEqual(
    Object.keys(second).filter((key) => !Object.hasOwn(FIXED_GIT, key)).sort(),
    allowed.sort()
  );
  assert.deepStrictEqual(readiness.sanitizedGitEnv(source), second);
  assert.deepStrictEqual(environment.buildGovernedGit(undefined), FIXED_GIT);
}

function restoreEnvironment(saved) {
  for (const [key, value] of Object.entries(saved)) {
    if (value === undefined) delete process.env[key];
    else process.env[key] = value;
  }
}

function committedRepository(originalExec) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'reddog-git-env-'));
  originalExec('git', ['init', '-q'], { cwd: root });
  originalExec('git', ['config', 'core.autocrlf', 'false'], { cwd: root });
  fs.writeFileSync(path.join(root, 'probe.txt'), 'probe\n', 'utf8');
  originalExec('git', ['add', 'probe.txt'], { cwd: root });
  originalExec('git', ['-c', 'user.name=RedDog Test', '-c',
    'user.email=reddog@example.invalid', 'commit', '-qm', 'probe'], { cwd: root });
  return root;
}

function assertObservedEnvironments(observed) {
  assert(observed.length >= 4, 'configuration and content Git children must be observed');
  for (const env of observed) {
    for (const key of FORBIDDEN) assert.strictEqual(env[key], undefined, key);
    for (const [key, value] of Object.entries(FIXED_GIT)) {
      assert.strictEqual(env[key], value, key);
    }
  }
}

function assertEveryGitChildReceivesClosedEnvironment() {
  const saved = Object.fromEntries(FORBIDDEN.map((key) => [key, process.env[key]]));
  const originalExec = cp.execFileSync;
  const observed = [];
  const root = committedRepository(originalExec);
  try {
    for (const key of FORBIDDEN) process.env[key] = 'ambient-marker';
    cp.execFileSync = function(file, args, options) {
      if (/^git(?:\.exe)?$/i.test(path.basename(file)) && options && options.env) {
        observed.push(options.env);
        assert.strictEqual(path.isAbsolute(file), true);
      }
      return originalExec.apply(this, arguments);
    };
    const output = governedGit.governedGitStatus(root, 8000);
    assert(!output.includes('[git context unavailable:'), output);
    assertObservedEnvironments(observed);
    assertGovernedReceipts(root);
  } finally {
    cp.execFileSync = originalExec;
    restoreEnvironment(saved);
    fs.rmSync(root, { recursive: true, force: true });
  }
}

function assertGovernedReceipts(root) {
  const proof = governedGit.governedGitReadiness(root);
  assert.strictEqual(proof.schema_version, 'reddog_governed_git_readiness.v2');
  assert.strictEqual(proof.git_executable_binding.signature.status,
    process.platform === 'win32' ? 'valid' : 'not_applicable');
  const snapshot = governedGit.governedGitSnapshot(root);
  const repoState = governedGit.governedRepoState(root);
  assert.strictEqual(repoState.schema_version, 'reddog_governed_git_repo_state.v2');
  assert.strictEqual(repoState.governed_git_readiness.schema_version,
    'reddog_governed_git_readiness.v2');
  assert.match(repoState.content_digest, /^sha256:[a-f0-9]{64}$/);
  for (const receipt of [proof, snapshot.projection_receipt, repoState]) {
    assert.strictEqual(serializedStrings(receipt).some(isAbsolutePath), false);
    assert.strictEqual(JSON.stringify(receipt).includes('powershell.exe'), false);
  }
}

function serializedStrings(value) {
  if (typeof value === 'string') return [value];
  if (Array.isArray(value)) return value.flatMap(serializedStrings);
  if (!value || typeof value !== 'object') return [];
  return Object.values(value).flatMap(serializedStrings);
}

function isAbsolutePath(value) {
  return path.isAbsolute(value) || /^[A-Za-z]:[\\/]/.test(value);
}

function assertNodeStartupInjectionDoesNotRun() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'reddog-node-env-'));
  const preload = path.join(root, 'preload.js');
  const sentinel = path.join(root, 'preload-ran');
  fs.writeFileSync(preload,
    `require('fs').writeFileSync(${JSON.stringify(sentinel)}, 'ran')\n`, 'utf8');
  const source = Object.assign({}, process.env, {
    NODE_OPTIONS: '--require=' + preload,
    NODE_PATH: root
  });
  try {
    cp.execFileSync(process.execPath, ['-e', 'process.stdout.write("clean")'], {
      env: readiness.sanitizedGitEnv(source), encoding: 'utf8', windowsHide: true
    });
    assert.strictEqual(fs.existsSync(sentinel), false);
  } finally { fs.rmSync(root, { recursive: true, force: true }); }
}

assertAmbientForbiddenFieldsDoNotCross();
assertClosedBuilder();
assertEveryGitChildReceivesClosedEnvironment();
assertNodeStartupInjectionDoesNotRun();
console.log('RedDog governed Git child environment contracts: PASS');
