const assert = require('assert');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const EXPECTED_SOURCE_SHA256 = 'sha256:fcbb42a5b8b6715ec15cba73c457daef5c83507f2c978d98a7dd5237fc5144c6';
const EXPECTED_SOURCE_LINES = 6857;
const EXPECTED_ASSERTION_CALLS = 1214;
const MAX_SHARD_LINES = 400;
const MAX_ORCHESTRATOR_LINES = 200;

const testsDir = __dirname;
const shardsDir = path.join(testsDir, 'contract_shards');
const manifest = JSON.parse(fs.readFileSync(path.join(shardsDir, 'manifest.json'), 'utf8'));
const orchestrator = fs.readFileSync(path.join(testsDir, 'verify_extension_contract.js'), 'utf8');

function digest(content) {
  const canonical = String(content).replace(/\r\n/g, '\n');
  return 'sha256:' + crypto.createHash('sha256').update(canonical).digest('hex');
}

function lineCount(content) {
  return content.match(/.*(?:\r?\n|$)/g).filter((line) => line.length > 0).length;
}

assert.strictEqual(manifest.schema_version, 'reddog_extension_contract_shards.v1');
assert.strictEqual(manifest.source_sha256, EXPECTED_SOURCE_SHA256);
assert.strictEqual(manifest.source_line_count, EXPECTED_SOURCE_LINES);
assert.strictEqual(manifest.assertion_call_count, EXPECTED_ASSERTION_CALLS);
assert.strictEqual(manifest.canonical_line_endings, 'LF');
assert.strictEqual(manifest.max_shard_lines, MAX_SHARD_LINES);
assert.strictEqual(manifest.max_orchestrator_lines, MAX_ORCHESTRATOR_LINES);
assert(Array.isArray(manifest.shards) && manifest.shards.length > 1);

const listedPaths = manifest.shards.map((shard) => shard.path);
assert.strictEqual(new Set(listedPaths).size, listedPaths.length, 'shard paths must be unique');
const actualPaths = fs.readdirSync(shardsDir)
  .filter((name) => /^verify_extension_contract\.part\d{2}\.js$/.test(name))
  .map((name) => `contract_shards/${name}`)
  .sort();
assert.deepStrictEqual(actualPaths, [...listedPaths].sort(), 'manifest must list every shard exactly once');

let nextSourceLine = 1;
const aggregate = manifest.shards.map((shard, index) => {
  assert.strictEqual(shard.order, index + 1, 'shard order must be contiguous');
  assert.strictEqual(shard.source_line_start, nextSourceLine, 'source ranges must be contiguous');
  assert.strictEqual(shard.source_line_end - shard.source_line_start + 1, shard.line_count);
  assert(shard.line_count > 0 && shard.line_count <= MAX_SHARD_LINES, 'shard exceeds WSP_62 ceiling');
  const source = fs.readFileSync(path.join(testsDir, shard.path), 'utf8');
  assert.strictEqual(lineCount(source), shard.line_count, `line count mismatch: ${shard.path}`);
  assert.strictEqual(digest(source), shard.sha256, `digest mismatch: ${shard.path}`);
  assert.doesNotThrow(() => new vm.Script(source), `syntax failure: ${shard.path}`);
  nextSourceLine = shard.source_line_end + 1;
  return source;
}).join('');

assert.strictEqual(nextSourceLine - 1, EXPECTED_SOURCE_LINES);
assert.strictEqual(lineCount(aggregate), EXPECTED_SOURCE_LINES);
assert.strictEqual(digest(aggregate), EXPECTED_SOURCE_SHA256, 'original source body must reconstruct exactly');
assert.strictEqual(
  (aggregate.match(/\bassert(?:\.[A-Za-z_$][\w$]*)?\s*\(/g) || []).length,
  EXPECTED_ASSERTION_CALLS,
  'assertion calls must not be lost'
);
assert(lineCount(orchestrator) <= MAX_ORCHESTRATOR_LINES, 'orchestrator exceeds WSP_62 ceiling');
assert(orchestrator.includes("'contract_shards',"), 'orchestrator must load the shard manifest');
assert(orchestrator.includes('ContractRunnerModule.wrap(contractRunnerAggregate)'), 'runner must use local CommonJS bindings');
assert(orchestrator.includes('ContractRunnerModule.createRequire(__filename)'), 'runner must preserve local require semantics');
assert(!orchestrator.includes('global.require'), 'runner must not leak require onto the process global');
assert(!orchestrator.includes('global.__dirname'), 'runner must not leak __dirname onto the process global');
assert(!orchestrator.includes('global.__filename'), 'runner must not leak __filename onto the process global');
assert(orchestrator.includes('lstatSync(shardPath)'), 'runner must reject non-regular shard paths');
assert(orchestrator.includes('isSymbolicLink()'), 'runner must reject shard symlinks');
assert(orchestrator.includes('realpathSync(shardPath)'), 'runner must enforce realpath confinement');
assert(orchestrator.includes('shard.path !== expectedRelative'), 'runner must require exact shard paths');

console.log(
  `RedDog extension contract shard structure passed: ${manifest.shards.length} shards, ` +
  `${EXPECTED_SOURCE_LINES} source lines, ${EXPECTED_ASSERTION_CALLS} assertion calls.`
);
