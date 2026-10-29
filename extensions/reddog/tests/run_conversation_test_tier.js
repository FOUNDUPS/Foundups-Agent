'use strict';

const cp = require('child_process');
const crypto = require('crypto');
const fs = require('fs');
const os = require('os');
const path = require('path');
const governedGitExecutable = require('../governed_git_executable');
const governedGitReadiness = require('../governed_git_readiness');

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

function samePath(left, right, platform = process.platform) {
  const resolved = (value) => path.resolve(value);
  return platform === 'win32'
    ? resolved(left).toLowerCase() === resolved(right).toLowerCase()
    : resolved(left) === resolved(right);
}

function governedGitValue(authority, binding, args, environment, root) {
  const output = authority.execFileSync(binding,
    governedGitReadiness.governedGitArgs(root, false, args), {
      cwd: root, encoding: 'utf8', timeout: 5000, maxBuffer: 8192,
      windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'],
      env: governedGitReadiness.sanitizedGitEnv(environment)
    });
  const value = String(output || '').trim();
  if (!value) throw new Error('Git topology lookup returned no path');
  return path.resolve(root, value);
}

function validateGitTopology(root, common, gitDirectory, top, platform) {
  if (!samePath(top, root, platform)) throw new Error('Git top-level mismatch');
  if (path.basename(common).toLowerCase() !== '.git') {
    throw new Error('Git common directory must end in .git');
  }
  const primary = trustedDirectory(path.dirname(common),
    'test primary repository root', platform);
  if (!samePath(path.join(primary, '.git'), common, platform)) {
    throw new Error('Git common directory is not primary checkout metadata');
  }
  if (samePath(gitDirectory, common, platform)) {
    if (!samePath(primary, root, platform)) throw new Error('Git primary topology mismatch');
    return primary;
  }
  const relative = path.relative(common, gitDirectory).split(path.sep);
  if (relative.length !== 2 || relative[0].toLowerCase() !== 'worktrees') {
    throw new Error('Git linked-worktree metadata is outside the common directory');
  }
  const marker = path.join(root, '.git');
  const metadata = fs.lstatSync(marker);
  const match = !metadata.isSymbolicLink() && metadata.isFile()
    ? /^gitdir:\s*(.+)\s*$/i.exec(fs.readFileSync(marker, 'utf8')) : null;
  if (!match || !samePath(path.resolve(root, match[1]), gitDirectory, platform)) {
    throw new Error('Git linked-worktree marker mismatch');
  }
  return primary;
}

function resolvePrimaryRepoRoot(platform = process.platform,
  authority = governedGitExecutable, environment = process.env) {
  const root = trustedDirectory(repoRoot, 'test repository root', platform);
  try {
    const binding = authority.bind(environment);
    const read = (args) => governedGitValue(authority, binding, args, environment, root);
    const common = trustedDirectory(read([
      'rev-parse', '--path-format=absolute', '--git-common-dir'
    ]), 'Git common directory', platform);
    const gitDirectory = trustedDirectory(read([
      'rev-parse', '--path-format=absolute', '--git-dir'
    ]), 'Git worktree directory', platform);
    const top = trustedDirectory(read([
      'rev-parse', '--path-format=absolute', '--show-toplevel'
    ]), 'Git worktree top level', platform);
    return validateGitTopology(root, common, gitDirectory, top, platform);
  } catch (error) {
    throw new Error('Git common-directory lookup failed', { cause: error });
  }
}

function resolvePython(environment = process.env, platform = process.platform) {
  let configured = environment.REDDOG_TEST_PYTHON;
  if (!configured) {
    if (platform === 'win32') {
      configured = path.join(
        resolvePrimaryRepoRoot(platform), '.venv', 'Scripts', 'python.exe'
      );
    } else {
      return 'python3';
    }
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

function ensureDirectory(candidate, label, platform = process.platform) {
  if (!fs.existsSync(candidate)) {
    try { fs.mkdirSync(candidate); }
    catch (error) { if (!error || error.code !== 'EEXIST') throw error; }
  }
  return trustedDirectory(candidate, label, platform);
}

function resolveTestTemporaryRoot(environment = process.env, platform = process.platform) {
  const configured = environment.REDDOG_TEST_TEMP;
  if (configured) return trustedDirectory(configured, 'test temporary root', platform);
  if (platform !== 'win32') return trustedDirectory(os.tmpdir(), 'test temporary root', platform);
  const root = trustedDirectory(repoRoot, 'test repository root', platform);
  const taskTemp = ensureDirectory(path.join(root, '.tmp'), 'test task temp root', platform);
  return ensureDirectory(
    path.join(taskTemp, 'reddog-tests'), 'test temporary root', platform
  );
}

function resolveDependencyRoot(environment = process.env, platform = process.platform) {
  const configured = environment.REDDOG_TEST_SITE_PACKAGES;
  if (configured) return trustedDirectory(configured, 'test Python dependency root', platform);
  const primaryRoot = resolvePrimaryRepoRoot(platform);
  if (platform === 'win32') {
    return trustedDirectory(
      path.join(primaryRoot, '.venv', 'Lib', 'site-packages'),
      'test Python dependency root', platform
    );
  }
  const libraryRoot = path.join(primaryRoot, '.venv', 'lib');
  const candidates = fs.readdirSync(libraryRoot, { withFileTypes: true })
    .filter((entry) => entry.isDirectory() && /^python\d+\.\d+$/.test(entry.name))
    .map((entry) => path.join(libraryRoot, entry.name, 'site-packages'))
    .filter((candidate) => fs.existsSync(candidate));
  if (candidates.length !== 1) throw new Error('test Python dependency root is ambiguous');
  return trustedDirectory(candidates[0], 'test Python dependency root', platform);
}

function controlledPythonEnvironment(
  sourceEnvironment = process.env,
  temporaryRoot = null,
  platform = process.platform
) {
  const environment = Object.assign({}, sourceEnvironment);
  for (const name of Object.keys(environment)) {
    if (/^(PYTHON|PYTEST)/i.test(name)) delete environment[name];
  }
  const dependencyRoot = resolveDependencyRoot(sourceEnvironment, platform);
  const resolvedTemporaryRoot = trustedDirectory(
    temporaryRoot || resolveTestTemporaryRoot(sourceEnvironment, platform),
    'test temporary root', platform
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
  const base = path.join(resolveTestTemporaryRoot(),
    'reddog-conversation-' + crypto.randomUUID());
  const python = resolvePython();
  try {
    run(python, [
      '-B', '-s', '-m', 'pytest', '-q', '--import-mode=importlib', '--basetemp', base,
      'modules/ai_intelligence/digital_twin/tests/test_conversation_plane.py'
    ], controlledPythonEnvironment());
  } finally {
    fs.rmSync(base, { recursive: true, force: true });
  }
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
  resolveTestTemporaryRoot,
  resolveDependencyRoot,
  resolvePrimaryRepoRoot,
  resolvePython,
  samePath,
  trustedDirectory
};
