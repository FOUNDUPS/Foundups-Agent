'use strict';

const cp = require('child_process');
const crypto = require('crypto');
const os = require('os');
const path = require('path');

const repoRoot = path.resolve(__dirname, '..', '..', '..');

function run(command, args) {
  const result = cp.spawnSync(command, args, {
    cwd: repoRoot, encoding: 'utf8', timeout: 120000,
    maxBuffer: 2 * 1024 * 1024, windowsHide: true,
    env: Object.assign({}, process.env, { PYTEST_DISABLE_PLUGIN_AUTOLOAD: '1' })
  });
  if (result.stdout) process.stdout.write(result.stdout);
  if (result.stderr) process.stderr.write(result.stderr);
  if (result.error || result.status !== 0) {
    throw result.error || new Error(path.basename(command) + ' exited ' + result.status);
  }
}

function main() {
  run(process.execPath, [path.join(__dirname, 'test_conversation_plane_policy.js')]);
  const base = path.join(os.tmpdir(), 'reddog-conversation-' + crypto.randomUUID());
  const python = process.platform === 'win32' ? 'python' : 'python3';
  run(python, [
    '-m', 'pytest', '-q', '--import-mode=importlib', '--basetemp', base,
    'modules/ai_intelligence/digital_twin/tests/test_conversation_plane.py'
  ]);
  console.log('[REDDOG-CONVERSATION-TEST] status=PASS');
}

try { main(); }
catch (error) {
  console.error('[REDDOG-CONVERSATION-TEST] status=FAIL ' + String(error && error.message || error));
  process.exitCode = 1;
}
