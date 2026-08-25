'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const extensionRoot = path.resolve(__dirname, '..');
const repoRoot = path.resolve(extensionRoot, '..', '..');
const packageJson = JSON.parse(fs.readFileSync(
  path.join(extensionRoot, 'package.json'), 'utf8'
));
const plan = require('./reddog_test_plan');

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
