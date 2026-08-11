const contractRunnerCrypto = require('crypto');
const contractRunnerFs = require('fs');
const ContractRunnerModule = require('module');
const contractRunnerPath = require('path');
const contractRunnerVm = require('vm');

const CONTRACT_RUNNER_SOURCE_SHA256 = 'sha256:ace47ca30d99d460557cd1d4c57b0c4c15bf5ca8242ca7974b1dd8b35788419b';
const CONTRACT_RUNNER_SOURCE_LINES = 6857;
const CONTRACT_RUNNER_ASSERTION_CALLS = 1213;

const contractRunnerManifestPath = contractRunnerPath.join(
  __dirname,
  'contract_shards',
  'manifest.json'
);
const contractRunnerManifest = JSON.parse(
  contractRunnerFs.readFileSync(contractRunnerManifestPath, 'utf8')
);

function contractRunnerDigest(content) {
  const canonical = String(content).replace(/\r\n/g, '\n');
  return 'sha256:' + contractRunnerCrypto.createHash('sha256').update(canonical).digest('hex');
}

function contractRunnerLineCount(content) {
  return content.match(/.*(?:\r?\n|$)/g).filter((line) => line.length > 0).length;
}

function contractRunnerResolveShardPath(shard, index) {
  const expectedName = `verify_extension_contract.part${String(index + 1).padStart(2, '0')}.js`;
  const expectedRelative = `contract_shards/${expectedName}`;
  if (shard.path !== expectedRelative) {
    throw new Error(`invalid RedDog extension contract shard path: ${shard.path}`);
  }
  const shardRoot = contractRunnerFs.realpathSync(
    contractRunnerPath.dirname(contractRunnerManifestPath)
  );
  const shardPath = contractRunnerPath.join(shardRoot, expectedName);
  const shardStat = contractRunnerFs.lstatSync(shardPath);
  if (!shardStat.isFile() || shardStat.isSymbolicLink()) {
    throw new Error(`RedDog extension contract shard is not a regular file: ${shard.path}`);
  }
  const realShardPath = contractRunnerFs.realpathSync(shardPath);
  if (contractRunnerPath.dirname(realShardPath) !== shardRoot) {
    throw new Error(`RedDog extension contract shard escapes shard root: ${shard.path}`);
  }
  return realShardPath;
}

function contractRunnerLoadShards() {
  if (contractRunnerManifest.schema_version !== 'reddog_extension_contract_shards.v1') {
    throw new Error('unsupported RedDog extension contract shard manifest');
  }
  if (contractRunnerManifest.canonical_line_endings !== 'LF') {
    throw new Error('RedDog extension contract canonical line-ending policy mismatch');
  }
  if (!Array.isArray(contractRunnerManifest.shards) || contractRunnerManifest.shards.length === 0) {
    throw new Error('RedDog extension contract shard manifest is empty');
  }
  if (contractRunnerManifest.source_sha256 !== CONTRACT_RUNNER_SOURCE_SHA256 ||
      contractRunnerManifest.source_line_count !== CONTRACT_RUNNER_SOURCE_LINES ||
      contractRunnerManifest.assertion_call_count !== CONTRACT_RUNNER_ASSERTION_CALLS) {
    throw new Error('RedDog extension contract source identity mismatch');
  }

  const listedFiles = contractRunnerManifest.shards.map((shard) => contractRunnerPath.basename(shard.path)).sort();
  const actualFiles = contractRunnerFs.readdirSync(contractRunnerPath.dirname(contractRunnerManifestPath))
    .filter((name) => /^verify_extension_contract\.part\d{2}\.js$/.test(name))
    .sort();
  if (JSON.stringify(listedFiles) !== JSON.stringify(actualFiles)) {
    throw new Error('RedDog extension contract shard set mismatch');
  }

  const seen = new Set();
  let nextSourceLine = 1;
  const sources = contractRunnerManifest.shards.map((shard, index) => {
    if (shard.order !== index + 1 || seen.has(shard.path)) {
      throw new Error(`invalid RedDog extension contract shard order at ${index + 1}`);
    }
    seen.add(shard.path);
    if (shard.source_line_start !== nextSourceLine ||
        shard.source_line_end - shard.source_line_start + 1 !== shard.line_count) {
      throw new Error(`invalid RedDog extension contract source range: ${shard.path}`);
    }
    nextSourceLine = shard.source_line_end + 1;
    const shardPath = contractRunnerResolveShardPath(shard, index);
    const source = contractRunnerFs.readFileSync(shardPath, 'utf8');
    if (contractRunnerLineCount(source) !== shard.line_count) {
      throw new Error(`RedDog extension contract shard line count mismatch: ${shard.path}`);
    }
    if (shard.line_count > contractRunnerManifest.max_shard_lines) {
      throw new Error(`RedDog extension contract shard exceeds line ceiling: ${shard.path}`);
    }
    if (contractRunnerDigest(source) !== shard.sha256) {
      throw new Error(`RedDog extension contract shard digest mismatch: ${shard.path}`);
    }
    return { path: shardPath, source };
  });

  const aggregate = sources.map((shard) => shard.source).join('');
  if (contractRunnerLineCount(aggregate) !== contractRunnerManifest.source_line_count) {
    throw new Error('RedDog extension contract aggregate line count mismatch');
  }
  if (contractRunnerDigest(aggregate) !== contractRunnerManifest.source_sha256) {
    throw new Error('RedDog extension contract aggregate digest mismatch');
  }
  const assertionCalls = (aggregate.match(/\bassert(?:\.[A-Za-z_$][\w$]*)?\s*\(/g) || []).length;
  if (assertionCalls !== CONTRACT_RUNNER_ASSERTION_CALLS) {
    throw new Error('RedDog extension contract assertion count mismatch');
  }
  return aggregate;
}

const contractRunnerAggregate = contractRunnerLoadShards();
const contractRunnerWrapper = contractRunnerVm.runInThisContext(
  ContractRunnerModule.wrap(contractRunnerAggregate),
  { filename: __filename, displayErrors: true }
);
const contractRunnerRequire = ContractRunnerModule.createRequire(__filename);
contractRunnerWrapper.call(
  module.exports,
  module.exports,
  contractRunnerRequire,
  module,
  __filename,
  __dirname
);
