const assert = require('assert');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const contractExecution = require('./reddog_contract_execution');

const EXPECTED_SOURCE_SHA256 = 'sha256:5a7584a411187fad2ff8139c95c4397702c2a1488783f10c0b8f04fef022b4af';
const EXPECTED_SOURCE_LINES = 6942;
const EXPECTED_ASSERTION_CALLS = 492;
const MAX_SHARD_LINES = 400;
const MAX_ORCHESTRATOR_LINES = 200;

const testsDir = __dirname;
const shardsDir = path.join(testsDir, 'contract_shards');
const manifest = JSON.parse(fs.readFileSync(path.join(shardsDir, 'manifest.json'), 'utf8'));
const orchestrator = fs.readFileSync(path.join(testsDir, 'verify_extension_contract.js'), 'utf8');
const execution = fs.readFileSync(path.join(testsDir, 'reddog_contract_execution.js'), 'utf8');
const authenticatedRunner = orchestrator + execution;

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
  contractExecution.assertionCount(aggregate),
  EXPECTED_ASSERTION_CALLS,
  'assertion calls must not be lost'
);
assert.strictEqual(contractExecution.assertionCount(
  "// assert(commentOnly)\n'assert(stringOnly)';\nassert(realCall);"
), 1, 'assertion counter must ignore comments and strings');
assert(lineCount(orchestrator) <= MAX_ORCHESTRATOR_LINES, 'orchestrator exceeds WSP_62 ceiling');
assert(lineCount(execution) <= 400, 'contract execution module exceeds WSP_62 ceiling');
assert(authenticatedRunner.includes("'contract_shards', 'manifest.json'"),
  'authenticated runner must load the shard manifest');
assert(authenticatedRunner.includes('Module.wrap(aggregate)'),
  'runner must use local CommonJS bindings');
assert(authenticatedRunner.includes('Module.createRequire(__filename)'),
  'runner must preserve local require semantics');
assert(!authenticatedRunner.includes('global.require'), 'runner must not leak require globally');
assert(!authenticatedRunner.includes('global.__dirname'), 'runner must not leak dirname globally');
assert(!authenticatedRunner.includes('global.__filename'), 'runner must not leak filename globally');
assert(authenticatedRunner.includes('lstatSync(candidate)'), 'runner must reject invalid shard types');
assert(authenticatedRunner.includes('isSymbolicLink()'), 'runner must reject shard symlinks');
assert(authenticatedRunner.includes('realpathSync(candidate)'), 'runner must enforce realpath confinement');
assert(authenticatedRunner.includes('shard.path !== relative'), 'runner must require exact shard paths');

console.log(
  `RedDog extension contract shard structure passed: ${manifest.shards.length} shards, ` +
  `${EXPECTED_SOURCE_LINES} source lines, ${EXPECTED_ASSERTION_CALLS} assertion calls.`
);
