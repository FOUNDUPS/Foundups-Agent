'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const repoRoot = path.resolve(__dirname, '..', '..', '..');
const roots = [
  path.join(repoRoot, 'extensions', 'reddog'),
  path.join(repoRoot, 'modules', 'communication', 'moltbot_bridge', 'src')
];
const BARE_JS_GIT = /(?:execFileSync|spawnSync|execFile|spawn)\s*\(\s*['"]git['"]/;
const BARE_PYTHON_GIT = /subprocess\.(?:run|call|check_call|check_output|Popen)\s*\([^\n]{0,160}['"]git['"]/;
const RAW_HOLO_EXECUTION = /(?:execFileSync|spawnSync|execFile|spawn)\s*\([\s\S]{0,640}?holo_index\.py/;

function productionFiles(root) {
  const values = [];
  for (const entry of fs.readdirSync(root, { withFileTypes: true })) {
    if (entry.name === 'tests' || entry.name === 'node_modules') continue;
    const target = path.join(root, entry.name);
    if (entry.isDirectory()) values.push(...productionFiles(target));
    else if (/\.(?:js|py)$/.test(entry.name)) values.push(target);
  }
  return values;
}

for (const file of roots.flatMap(productionFiles)) {
  const source = fs.readFileSync(file, 'utf8');
  assert.strictEqual(BARE_JS_GIT.test(source), false,
    path.relative(repoRoot, file) + ' must not execute ambient bare Git');
  assert.strictEqual(BARE_PYTHON_GIT.test(source), false,
    path.relative(repoRoot, file) + ' must not execute ambient bare Git');
  assert.strictEqual(RAW_HOLO_EXECUTION.test(source), false,
    path.relative(repoRoot, file) + ' must use the governed HoloIndex bridge');
}

console.log('RedDog production bare-Git scan contracts: PASS');
