'use strict';

const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');

const extensionRoot = path.resolve(__dirname, '..');
const repoRoot = path.resolve(extensionRoot, '..', '..');
const packageJson = JSON.parse(fs.readFileSync(
  path.join(extensionRoot, 'package.json'), 'utf8'
));
const plan = require('./reddog_test_plan');
const conversationTier = require('./run_conversation_test_tier');

assert(packageJson.scripts, 'package.json must operationalize RedDog test tiers');
assert.strictEqual(packageJson.scripts.test, 'node tests/run_reddog_test_tier.js fast');
assert.strictEqual(packageJson.scripts['test:conversation'],
  'node tests/run_conversation_test_tier.js');
assert.strictEqual(packageJson.scripts['test:contract'],
  'node tests/run_reddog_test_tier.js contract');
assert.strictEqual(packageJson.scripts['test:package'],
  'node tests/test_package_surface.js');
assert.strictEqual(packageJson.scripts['test:release'],
  'node tests/verify_extension_contract.js');
assert.strictEqual(packageJson.dependencies, undefined);
assert.strictEqual(packageJson.devDependencies, undefined);
const conversationRunner = fs.readFileSync(
  path.join(__dirname, 'run_conversation_test_tier.js'), 'utf8'
);
assert(conversationRunner.includes("'-B', '-s', '-m', 'pytest'"),
  'conversation Python must suppress bytecode and user-site imports');
assert(conversationRunner.includes('REDDOG_TEST_PYTHON is required on Windows'),
  'Windows conversation tests must reject ambient Python fallback');
assert(conversationRunner.includes("environment.PYTHONNOUSERSITE = '1'"),
  'conversation tests must block per-user dependency discovery');
assert(conversationRunner.includes('/^(PYTHON|PYTEST)/i.test(name)'),
  'conversation tests must erase every ambient Python and pytest control');
assert(conversationRunner.includes('test Python dependency root'),
  'conversation tests must validate their O:/E: dependency root');
assert.throws(
  () => conversationTier.resolvePython({}, 'win32'),
  /REDDOG_TEST_PYTHON is required on Windows/
);
assert.throws(
  () => conversationTier.resolvePython({ REDDOG_TEST_PYTHON: 'python.exe' }, 'win32'),
  /must be absolute/
);
assert.throws(
  () => conversationTier.assertAllowedArtifactVolume(
    'C:\\untrusted\\python.exe', 'test Python override', 'win32'
  ),
  /must reside on O: or E:/
);
assert.doesNotThrow(() => conversationTier.assertAllowedArtifactVolume(
  'O:\\trusted\\python.exe', 'test Python override', 'win32'
));
assert.doesNotThrow(() => conversationTier.assertAllowedArtifactVolume(
  'E:\\trusted\\python.exe', 'test Python override', 'win32'
));
const temporaryBase = process.platform === 'win32' ? 'O:\\tmp' : os.tmpdir();
const confinementRoot = fs.mkdtempSync(
  path.join(temporaryBase, 'reddog-conversation-guard-')
);
try {
  const realDirectory = path.join(confinementRoot, 'real');
  const junctionDirectory = path.join(confinementRoot, 'junction');
  fs.mkdirSync(realDirectory);
  fs.mkdirSync(path.join(realDirectory, 'nested'));
  fs.symlinkSync(
    realDirectory, junctionDirectory,
    process.platform === 'win32' ? 'junction' : 'dir'
  );
  assert.throws(
    () => conversationTier.trustedDirectory(
      junctionDirectory, 'test temporary root', process.platform
    ),
    /must not cross a link or reparse point/
  );
  assert.throws(
    () => conversationTier.trustedDirectory(
      path.join(junctionDirectory, 'nested'), 'test temporary root', process.platform
    ),
    /must not cross a link or reparse point/
  );
  assert.throws(
    () => conversationTier.resolvePython({
      REDDOG_TEST_PYTHON: path.join(confinementRoot, 'missing-python')
    }, process.platform),
    /ENOENT/
  );
  const polluted = Object.assign({}, process.env, {
    PYTHONHOME: 'untrusted-home',
    PYTHONINSPECT: '1',
    PYTHONPATH: 'untrusted-path',
    PYTHONSTARTUP: 'untrusted-startup',
    PYTHONUSERBASE: 'untrusted-userbase',
    PYTHONWARNINGS: 'error',
    PYTHONBREAKPOINT: 'untrusted.breakpoint',
    PYTHONPYCACHEPREFIX: path.join(confinementRoot, 'untrusted-pyc'),
    PYTHONFUTURECONTROL: 'untrusted-future-control',
    pythonlowercontrol: 'untrusted-lower-control',
    PYTEST_ADDOPTS: '--collect-only',
    PYTEST_PLUGINS: 'untrusted_plugin',
    REDDOG_TEST_SITE_PACKAGES: process.platform === 'win32'
      ? (process.env.REDDOG_TEST_SITE_PACKAGES
        || path.join(repoRoot, '.venv', 'Lib', 'site-packages'))
      : extensionRoot
  });
  const controlled = conversationTier.controlledPythonEnvironment(
    polluted, confinementRoot, process.platform
  );
  for (const name of [
    'PYTHONHOME', 'PYTHONINSPECT', 'PYTHONSTARTUP', 'PYTHONUSERBASE',
    'PYTHONWARNINGS', 'PYTHONBREAKPOINT', 'PYTHONPYCACHEPREFIX',
    'PYTHONFUTURECONTROL', 'pythonlowercontrol', 'PYTEST_ADDOPTS', 'PYTEST_PLUGINS'
  ]) {
    assert.strictEqual(controlled[name], undefined, name + ' must be removed');
  }
  assert.strictEqual(controlled.TEMP, fs.realpathSync(confinementRoot));
  assert.strictEqual(controlled.TMP, controlled.TEMP);
  assert.strictEqual(controlled.TMPDIR, controlled.TEMP);
  assert.strictEqual(controlled.PYTHONNOUSERSITE, '1');
  assert.strictEqual(controlled.PYTHONSAFEPATH, '1');
  assert.strictEqual(controlled.PYTEST_DISABLE_PLUGIN_AUTOLOAD, '1');
  const admittedControls = new Set([
    'PYTHONPATH', 'PYTHONDONTWRITEBYTECODE', 'PYTHONNOUSERSITE',
    'PYTHONSAFEPATH', 'PYTHONUTF8', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD'
  ]);
  assert.deepStrictEqual(
    Object.keys(controlled)
      .filter((name) => /^(PYTHON|PYTEST)/i.test(name) && !admittedControls.has(name))
      .sort(),
    []
  );
  assert(controlled.PYTHONPATH.startsWith(fs.realpathSync(
    polluted.REDDOG_TEST_SITE_PACKAGES
  )));
} finally {
  fs.rmSync(confinementRoot, { recursive: true, force: true });
}
assert.strictEqual(plan.RELEASE_WORKER_CAP, 4);
assert.strictEqual(plan.RELEASE_CHILD_TIMEOUT_MS, 400000);
assert.strictEqual(plan.RELEASE_CEILING_MS, 420000);
assert(plan.RELEASE_GROUPS.length <= plan.RELEASE_WORKER_CAP);
assert(!plan.FAST_TESTS.includes('verify_extension_contract.js'),
  'default tier must not silently run promotion');
assert(plan.FAST_TESTS.includes('test_progressive_execution_stage.js'),
  'default tier must prove evaluation topology cannot open action planning');
assert(!plan.releaseTests().includes('./test_reddog_candidate_wsp62'),
  'candidate-only WSP 62 proof must not enter committed-main release closure');

const manifest = require('./contract_shards/manifest.json');
const aggregate = manifest.shards.map((shard) => fs.readFileSync(
  path.join(__dirname, shard.path), 'utf8'
)).join('');
assert.doesNotThrow(() => plan.validateAggregateMembership(aggregate));

const ci = fs.readFileSync(path.join(repoRoot, '.github', 'workflows', 'ci.yml'), 'utf8');
assert(ci.includes('working-directory: extensions/reddog'));
assert(ci.includes('run: npm test'));
const owner = fs.readFileSync(path.join(__dirname, 'verify_extension_contract.js'), 'utf8');
const supervisorSource = fs.readFileSync(path.join(__dirname, 'reddog_release_supervisor.js'), 'utf8');
assert(!owner.includes('process.env.REDDOG_CONTRACT_GROUP'),
  'ambient environment must not select an internal release group');
assert(owner.includes('supervisor.runPromotion') && supervisorSource.includes('RELEASE_CEILING_MS'),
  'promotion owner must enforce the declared overall release ceiling');
assert(supervisorSource.includes('timedOut'),
  'promotion receipts must distinguish timeout from child exit status');
for (const relative of ['README.md', 'INTERFACE.md', 'ROADMAP.md',
  'tests/README.md', 'ModLog.md', 'tests/TestModLog.md']) {
  const doc = fs.readFileSync(path.join(extensionRoot, relative), 'utf8');
  assert(doc.includes('npm run test:release'), relative + ' must name the release command');
}

console.log('RedDog package test-tier contract: PASS');
