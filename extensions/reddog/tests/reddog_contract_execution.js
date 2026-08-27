'use strict';

const crypto = require('crypto');
const fs = require('fs');
const Module = require('module');
const path = require('path');
const vm = require('vm');
const plan = require('./reddog_test_plan');

const SOURCE_SHA256 = 'sha256:d1e4f7f54bab4b8e5749e744ffbd145c467f8f68c71a81e08ba6c17703097f22';
const SOURCE_LINES = 6929;
const ASSERTION_CALLS = 490;
const manifestPath = path.join(__dirname, 'contract_shards', 'manifest.json');
const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));

function digest(content) {
  const canonical = String(content).replace(/\r\n/g, '\n');
  return 'sha256:' + crypto.createHash('sha256').update(canonical).digest('hex');
}

function lineCount(content) {
  return content.match(/.*(?:\r?\n|$)/g).filter((line) => line.length > 0).length;
}

function maskNonCode(content) {
  let output = '', quote = '', escaped = false;
  let lineComment = false, blockComment = false;
  for (let index = 0; index < content.length; index += 1) {
    const char = content[index]; const next = content[index + 1];
    if (char === '\n') { output += '\n'; lineComment = false; continue; }
    if (lineComment) { output += ' '; continue; }
    if (blockComment) {
      if (char === '*' && next === '/') {
        output += '  '; index += 1; blockComment = false;
      } else output += ' ';
      continue;
    }
    if (quote) {
      output += ' ';
      if (escaped) escaped = false;
      else if (char === '\\') escaped = true;
      else if (char === quote) quote = '';
      continue;
    }
    if (char === '/' && next === '/') { output += '  '; index += 1; lineComment = true; }
    else if (char === '/' && next === '*') { output += '  '; index += 1; blockComment = true; }
    else if ('\'"`'.includes(char)) { output += ' '; quote = char; }
    else output += char;
  }
  return output;
}

function assertionCount(content) {
  return (maskNonCode(content).match(/\bassert(?:\.[A-Za-z_$][\w$]*)?\s*\(/g) || []).length;
}

function resolveShardPath(shard, index) {
  const name = `verify_extension_contract.part${String(index + 1).padStart(2, '0')}.js`;
  const relative = `contract_shards/${name}`;
  if (shard.path !== relative) throw new Error('invalid shard path: ' + shard.path);
  const root = fs.realpathSync(path.dirname(manifestPath));
  const candidate = path.join(root, name);
  const stat = fs.lstatSync(candidate);
  if (!stat.isFile() || stat.isSymbolicLink()) throw new Error('invalid shard type: ' + relative);
  const resolved = fs.realpathSync(candidate);
  if (path.dirname(resolved) !== root) throw new Error('shard escapes root: ' + relative);
  return resolved;
}

function validateManifest() {
  if (manifest.schema_version !== 'reddog_extension_contract_shards.v1' ||
      manifest.canonical_line_endings !== 'LF' || !Array.isArray(manifest.shards) ||
      manifest.shards.length === 0) throw new Error('invalid shard manifest');
  if (manifest.source_sha256 !== SOURCE_SHA256 || manifest.source_line_count !== SOURCE_LINES ||
      manifest.assertion_call_count !== ASSERTION_CALLS) throw new Error('source identity mismatch');
}

function validateShardSet() {
  const listed = manifest.shards.map((shard) => path.basename(shard.path)).sort();
  const actual = fs.readdirSync(path.dirname(manifestPath))
    .filter((name) => /^verify_extension_contract\.part\d{2}\.js$/.test(name)).sort();
  if (JSON.stringify(listed) !== JSON.stringify(actual)) throw new Error('shard set mismatch');
}

function loadShard(shard, index, state) {
  if (shard.order !== index + 1 || state.seen.has(shard.path)) throw new Error('invalid shard order');
  state.seen.add(shard.path);
  if (shard.source_line_start !== state.next ||
      shard.source_line_end - shard.source_line_start + 1 !== shard.line_count) {
    throw new Error('invalid shard source range: ' + shard.path);
  }
  state.next = shard.source_line_end + 1;
  const source = fs.readFileSync(resolveShardPath(shard, index), 'utf8');
  if (lineCount(source) !== shard.line_count || shard.line_count > manifest.max_shard_lines ||
      digest(source) !== shard.sha256) throw new Error('invalid shard content: ' + shard.path);
  return source;
}

function validateAggregate(aggregate) {
  const assertions = assertionCount(aggregate);
  if (lineCount(aggregate) !== manifest.source_line_count ||
      digest(aggregate) !== manifest.source_sha256 || assertions !== ASSERTION_CALLS) {
    throw new Error('aggregate identity mismatch');
  }
}

function loadShards() {
  validateManifest();
  validateShardSet();
  const state = { seen: new Set(), next: 1 };
  const aggregate = manifest.shards.map((shard, index) => loadShard(shard, index, state)).join('');
  validateAggregate(aggregate);
  return aggregate;
}

function runCore(aggregate) {
  const localRequire = Module.createRequire(__filename);
  const deferred = new Set(plan.releaseTests());
  const contractRequire = (request) => deferred.has(request) ? {} : localRequire(request);
  contractRequire.cache = localRequire.cache;
  const wrapper = vm.runInThisContext(Module.wrap(aggregate), {
    filename: path.join(__dirname, 'verify_extension_contract.js'), displayErrors: true
  });
  wrapper.call(module.exports, module.exports, contractRequire, module,
    path.join(__dirname, 'verify_extension_contract.js'), __dirname);
}

function runGroup(group) {
  const localRequire = Module.createRequire(__filename);
  for (const request of group.tests) localRequire(request);
  console.log(`[REDDOG-RELEASE-GROUP] id=${group.id} status=PASS members=${group.tests.length}`);
}

module.exports = Object.freeze({ assertionCount, loadShards, runCore, runGroup });
