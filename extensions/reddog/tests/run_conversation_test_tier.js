'use strict';

const cp = require('child_process');
const crypto = require('crypto');
const fs = require('fs');
const os = require('os');
const path = require('path');

const repoRoot = path.resolve(__dirname, '..', '..', '..');

function run(command, args, environment = process.env) {
  const result = cp.spawnSync(command, args, {
    cwd: repoRoot, encoding: 'utf8', timeout: 120000,
    maxBuffer: 2 * 1024 * 1024, windowsHide: true,
    env: Object.assign({}, environment, { PYTEST_DISABLE_PLUGIN_AUTOLOAD: '1' })
  });
  if (result.stdout) process.stdout.write(result.stdout);
  if (result.stderr) process.stderr.write(result.stderr);
  if (result.error || result.status !== 0) {
    throw result.error || new Error(path.basename(command) + ' exited ' + result.status);
  }
}

function assertAllowedArtifactVolume(resolved, label, platform = process.platform) {
  const drive = (platform === 'win32' ? path.win32 : path).parse(resolved).root.toUpperCase();
  if (platform === 'win32' && !['O:\\', 'E:\\'].includes(drive)) {
    throw new Error(label + ' must reside on O: or E:');
  }
}

function assertNoLinkComponents(candidate, label) {
  const parsed = path.parse(candidate);
  let current = parsed.root;
  for (const component of candidate.slice(parsed.root.length).split(path.sep).filter(Boolean)) {
    current = path.join(current, component);
    if (fs.lstatSync(current).isSymbolicLink()) {
      throw new Error(label + ' must not cross a link or reparse point');
    }
  }
}

function resolvePython(environment = process.env, platform = process.platform) {
  const configured = environment.REDDOG_TEST_PYTHON;
  if (!configured) {
    if (platform === 'win32') {
      throw new Error('REDDOG_TEST_PYTHON is required on Windows');
    }
    return 'python3';
  }
  if (!path.isAbsolute(configured)) throw new Error('test Python override must be absolute');
  assertNoLinkComponents(configured, 'test Python override');
  const link = fs.lstatSync(configured);
  if (!link.isFile() || link.isSymbolicLink()) {
    throw new Error('test Python override must be a regular non-link file');
  }
  const resolved = fs.realpathSync(configured);
  assertAllowedArtifactVolume(resolved, 'test Python override', platform);
  return resolved;
}

function trustedDirectory(candidate, label, platform = process.platform) {
  if (!path.isAbsolute(candidate)) throw new Error(label + ' must be absolute');
  assertNoLinkComponents(candidate, label);
  const link = fs.lstatSync(candidate);
  if (!link.isDirectory() || link.isSymbolicLink()) {
    throw new Error(label + ' must be a regular non-link directory');
  }
  const resolved = fs.realpathSync(candidate);
  assertAllowedArtifactVolume(resolved, label, platform);
  return resolved;
}

function resolveDependencyRoot(environment = process.env, platform = process.platform) {
  const configured = environment.REDDOG_TEST_SITE_PACKAGES;
  if (configured) return trustedDirectory(configured, 'test Python dependency root', platform);
  if (platform === 'win32') {
    return trustedDirectory(
      path.join(repoRoot, '.venv', 'Lib', 'site-packages'),
      'test Python dependency root', platform
    );
  }
  const libraryRoot = path.join(repoRoot, '.venv', 'lib');
  const candidates = fs.readdirSync(libraryRoot, { withFileTypes: true })
    .filter((entry) => entry.isDirectory() && /^python\d+\.\d+$/.test(entry.name))
    .map((entry) => path.join(libraryRoot, entry.name, 'site-packages'))
    .filter((candidate) => fs.existsSync(candidate));
  if (candidates.length !== 1) throw new Error('test Python dependency root is ambiguous');
  return trustedDirectory(candidates[0], 'test Python dependency root', platform);
}

function controlledPythonEnvironment(
  sourceEnvironment = process.env,
  temporaryRoot = os.tmpdir(),
  platform = process.platform
) {
  const environment = Object.assign({}, sourceEnvironment);
  for (const name of Object.keys(environment)) {
    if (/^(PYTHON|PYTEST)/i.test(name)) delete environment[name];
  }
  const dependencyRoot = resolveDependencyRoot(sourceEnvironment, platform);
  const resolvedTemporaryRoot = trustedDirectory(
    temporaryRoot, 'test temporary root', platform
  );
  environment.PYTHONPATH = [
    dependencyRoot, trustedDirectory(repoRoot, 'repository root', platform)
  ]
    .join(path.delimiter);
  environment.TEMP = resolvedTemporaryRoot;
  environment.TMP = resolvedTemporaryRoot;
  environment.TMPDIR = resolvedTemporaryRoot;
  environment.PYTHONDONTWRITEBYTECODE = '1';
  environment.PYTHONNOUSERSITE = '1';
  environment.PYTHONSAFEPATH = '1';
  environment.PYTHONUTF8 = '1';
  environment.PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1';
  return environment;
}

function main() {
  run(process.execPath, [path.join(__dirname, 'test_conversation_plane_policy.js')]);
  const base = path.join(os.tmpdir(), 'reddog-conversation-' + crypto.randomUUID());
  const python = resolvePython();
  run(python, [
    '-B', '-s', '-m', 'pytest', '-q', '--import-mode=importlib', '--basetemp', base,
    'modules/ai_intelligence/digital_twin/tests/test_conversation_plane.py'
  ], controlledPythonEnvironment());
  console.log('[REDDOG-CONVERSATION-TEST] status=PASS');
}

if (require.main === module) {
  try { main(); }
  catch (error) {
    console.error('[REDDOG-CONVERSATION-TEST] status=FAIL ' + String(error && error.message || error));
    process.exitCode = 1;
  }
}

module.exports = {
  assertAllowedArtifactVolume,
  controlledPythonEnvironment,
  resolveDependencyRoot,
  resolvePython,
  trustedDirectory
};
