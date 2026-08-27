'use strict';

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const contractExecution = require('./reddog_contract_execution');

const testsDir = __dirname;
const shardsDir = path.join(testsDir, 'contract_shards');
const manifestPath = path.join(shardsDir, 'manifest.json');
const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));

function digest(content) {
  const canonical = String(content).replace(/\r\n/g, '\n');
  return 'sha256:' + crypto.createHash('sha256').update(canonical).digest('hex');
}

function lineCount(content) {
  return content.match(/.*(?:\r?\n|$)/g).filter((line) => line.length > 0).length;
}

function shardNames() {
  return fs.readdirSync(shardsDir)
    .filter((name) => /^verify_extension_contract\.part\d{2}\.js$/.test(name))
    .sort();
}

function readShard(name) {
  const candidate = path.join(shardsDir, name);
  const stat = fs.lstatSync(candidate);
  if (!stat.isFile() || stat.isSymbolicLink()) throw new Error(`invalid shard type: ${name}`);
  if (path.dirname(fs.realpathSync(candidate)) !== fs.realpathSync(shardsDir)) {
    throw new Error(`shard escapes root: ${name}`);
  }
  return fs.readFileSync(candidate, 'utf8');
}

function buildIdentity() {
  let nextLine = 1;
  const sources = [];
  const shards = shardNames().map((name, index) => {
    const source = readShard(name);
    const count = lineCount(source);
    if (count === 0 || count > manifest.max_shard_lines) {
      throw new Error(`shard exceeds line contract: ${name} (${count})`);
    }
    sources.push(source);
    const entry = {
      order: index + 1,
      path: `contract_shards/${name}`,
      source_line_start: nextLine,
      source_line_end: nextLine + count - 1,
      line_count: count,
      sha256: digest(source)
    };
    nextLine += count;
    return entry;
  });
  const aggregate = sources.join('');
  return {
    aggregate,
    shards,
    source_sha256: digest(aggregate),
    source_line_count: lineCount(aggregate),
    assertion_call_count: contractExecution.assertionCount(aggregate)
  };
}

function expectedManifest(identity) {
  return Object.assign({}, manifest, {
    source_sha256: identity.source_sha256,
    source_line_count: identity.source_line_count,
    assertion_call_count: identity.assertion_call_count,
    shards: identity.shards
  });
}

function replaceConstants(source, identity, labels) {
  const values = {
    [labels.digest]: `'${identity.source_sha256}'`,
    [labels.lines]: String(identity.source_line_count),
    [labels.assertions]: String(identity.assertion_call_count)
  };
  let output = source;
  for (const [label, value] of Object.entries(values)) {
    const pattern = new RegExp(`(const ${label} = )[^;]+;`);
    if (!pattern.test(output)) throw new Error(`missing identity constant: ${label}`);
    output = output.replace(pattern, `$1${value};`);
  }
  return output;
}

function projectedFiles(identity) {
  const targets = [
    ['test_extension_contract_shards.js', {
      digest: 'EXPECTED_SOURCE_SHA256', lines: 'EXPECTED_SOURCE_LINES',
      assertions: 'EXPECTED_ASSERTION_CALLS'
    }],
    ['reddog_contract_execution.js', {
      digest: 'SOURCE_SHA256', lines: 'SOURCE_LINES', assertions: 'ASSERTION_CALLS'
    }]
  ];
  const files = new Map([[manifestPath, JSON.stringify(expectedManifest(identity), null, 2) + '\n']]);
  for (const [name, labels] of targets) {
    const target = path.join(testsDir, name);
    const source = fs.readFileSync(target, 'utf8');
    files.set(target, replaceConstants(source, identity, labels));
  }
  return files;
}

function main() {
  const mode = process.argv[2] || '--check';
  if (!['--check', '--write'].includes(mode) || process.argv.length > 3) {
    throw new Error('usage: node generate_extension_contract_shard_manifest.js [--check|--write]');
  }
  const identity = buildIdentity();
  const projected = projectedFiles(identity);
  const stale = [...projected].filter(([target, content]) => fs.readFileSync(target, 'utf8') !== content);
  if (mode === '--check' && stale.length) {
    throw new Error(`RedDog contract shard manifest is stale: ${stale.map(([p]) => path.basename(p)).join(', ')}`);
  }
  if (mode === '--write') for (const [target, content] of projected) fs.writeFileSync(target, content, 'utf8');
  console.log(`RedDog contract shards ${mode === '--write' ? 'generated' : 'verified'}: ` +
    `${identity.shards.length} shards, ${identity.source_line_count} lines, ` +
    `${identity.assertion_call_count} assertions, ${identity.source_sha256}.`);
}

main();
