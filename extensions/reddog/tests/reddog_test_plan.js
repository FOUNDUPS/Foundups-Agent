'use strict';

const assert = require('assert');

const SCHEMA_VERSION = 'reddog_test_plan.v1';
const RELEASE_WORKER_CAP = 4;
const RELEASE_CHILD_TIMEOUT_MS = 400000;
const RELEASE_CEILING_MS = 420000;
const CHILD_OUTPUT_CAP_BYTES = 2 * 1024 * 1024;

const CONTRACT_TESTS = Object.freeze([
  'test_reddog_test_tiering.js',
  'test_reddog_release_supervisor.js',
  'test_extension_contract_shards.js'
]);

const FAST_TESTS = Object.freeze([
  ...CONTRACT_TESTS,
  'test_package_manifest.js',
  'test_holoindex_async_bridge.js',
  'test_holoindex_incident_repair.js',
  'test_bridge_python_environment.js',
  'test_conversational_draft_policy.js',
  'test_authoritative_work_state_query.js',
  'test_backend_compatibility_contract.js',
  'test_backend_compatibility_async.js',
  'verify_fusion_panel_input_contract.js'
]);

const RELEASE_GROUPS = Object.freeze([
  Object.freeze({ id: 'core', tests: Object.freeze([]) }),
  Object.freeze({ id: 'governed_git', tests: Object.freeze([
    './test_governed_git_context_hardening'
  ]) }),
  Object.freeze({ id: 'git_formats_environment', tests: Object.freeze([
    './test_governed_git_environment', './test_governed_git_executable',
    './test_governed_git_production_scan', './test_governed_git_ref_formats'
  ]) }),
  Object.freeze({ id: 'bridge_wsp62', tests: Object.freeze([
    './test_bridge_python_environment', './test_reddog_candidate_wsp62',
    './test_package_surface'
  ]) })
]);

function releaseTests() {
  return RELEASE_GROUPS.flatMap((group) => group.tests);
}

function validateTestNames(names) {
  assert(Array.isArray(names) && names.length > 0, 'test tier must not be empty');
  assert.strictEqual(new Set(names).size, names.length, 'test tier has duplicate members');
  for (const name of names) {
    assert(/^[a-z0-9_]+\.js$/.test(name), 'invalid test tier member: ' + name);
  }
}

function validateReleaseGroups() {
  assert(RELEASE_GROUPS.length <= RELEASE_WORKER_CAP, 'release worker cap is exceeded');
  assert.strictEqual(new Set(RELEASE_GROUPS.map((group) => group.id)).size,
    RELEASE_GROUPS.length, 'release group IDs must be unique');
  const tests = releaseTests();
  assert.strictEqual(new Set(tests).size, tests.length, 'release tests must be unique');
  assert(RELEASE_CHILD_TIMEOUT_MS < RELEASE_CEILING_MS,
    'child timeout must remain below release ceiling');
}

function validateAggregateMembership(aggregate) {
  const members = Array.from(String(aggregate).matchAll(
    /require\('(\.\/test_[a-z0-9_]+)'\);/g), (match) => match[1]);
  assert.deepStrictEqual(members, releaseTests(),
    'release group plan must exactly cover deferred aggregate members');
}

validateTestNames(CONTRACT_TESTS);
validateTestNames(FAST_TESTS);
validateReleaseGroups();

module.exports = Object.freeze({
  SCHEMA_VERSION, RELEASE_WORKER_CAP, RELEASE_CHILD_TIMEOUT_MS,
  RELEASE_CEILING_MS, CHILD_OUTPUT_CAP_BYTES, CONTRACT_TESTS, FAST_TESTS,
  RELEASE_GROUPS, releaseTests, validateAggregateMembership
});
