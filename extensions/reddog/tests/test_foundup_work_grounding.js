'use strict';

const assert = require('assert');
const cp = require('child_process');
const crypto = require('crypto');
const fs = require('fs');
const os = require('os');
const path = require('path');

const root = path.resolve(__dirname, '..', '..', '..');
const modulePath = path.join(root, 'extensions', 'reddog', 'foundup_work_grounding.js');
const runtimePath = path.join(root, 'extensions', 'reddog', 'foundup_work_runtime_binding.js');
const grounding = require(modulePath);
const runtime = require(runtimePath);

function authority(repo) {
  const head = fs.existsSync(path.join(repo, '.git'))
    ? cp.execFileSync('git', ['rev-parse', 'HEAD'], { cwd: repo, encoding: 'utf8' }).trim()
    : 'a'.repeat(40);
  const tracked = fs.existsSync(path.join(repo, '.git'))
    ? cp.execFileSync('git', ['ls-files'], { cwd: repo, encoding: 'utf8' }).split(/\r?\n/).filter(Boolean)
    : listFiles(repo);
  const registryClean = fs.existsSync(path.join(repo, '.git'))
    ? cp.execFileSync('git', ['status', '--porcelain=v1', '--', grounding.REGISTRY_PATH, grounding.REGISTRY_SCHEMA_PATH], { cwd: repo, encoding: 'utf8' }).trim() === ''
    : true;
  const dirty = fs.existsSync(path.join(repo, '.git'))
    ? cp.execFileSync('git', ['diff', '--name-only', 'HEAD'], { cwd: repo, encoding: 'utf8' }).split(/\r?\n/).filter(Boolean)
    : [];
  return { repo_head_sha: head, registry_status_clean: registryClean, tracked_paths: tracked, dirty_paths: dirty };
}

function listFiles(directory, base) {
  const rootDirectory = base || directory;
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const target = path.join(directory, entry.name);
    return entry.isDirectory() ? listFiles(target, rootDirectory) : [path.relative(rootDirectory, target).replace(/\\/g, '/')];
  });
}

function writeFixture(entities) {
  const repo = fs.mkdtempSync(path.join(os.tmpdir(), 'reddog-foundup-grounding-'));
  const registry = path.join(repo, 'modules', 'foundups', 'foundup_registry.json');
  fs.mkdirSync(path.dirname(registry), { recursive: true });
  fs.writeFileSync(registry, JSON.stringify({
    schema_version: '1.0.0',
    last_updated: '2026-08-02T00:00:00Z',
    entities
  }), 'utf8');
  fs.copyFileSync(path.join(root, grounding.REGISTRY_SCHEMA_PATH), path.join(repo, grounding.REGISTRY_SCHEMA_PATH));
  for (const entity of entities) {
    if (!entity.module_path || entity.module_path.includes('..')) continue;
    const directory = path.join(repo, entity.module_path);
    fs.mkdirSync(directory, { recursive: true });
    fs.writeFileSync(path.join(directory, 'README.md'), '# Fixture\n', 'utf8');
    if (entity.manifest_path) {
      fs.writeFileSync(path.join(repo, entity.manifest_path), JSON.stringify({
        foundup_id: entity.foundup_id,
        build_contract: { safe_mutation_surface: [entity.module_path + '/**'] }
      }) + '\n', 'utf8');
    }
  }
  const skill = path.join(repo, 'modules', 'communication', 'moltbot_bridge', 'skillz', 'reddog_operations', 'SKILLz.md');
  fs.mkdirSync(path.dirname(skill), { recursive: true });
  fs.writeFileSync(skill, '# Skill\n', 'utf8');
  const skillRegistry = path.join(repo, 'modules', 'infrastructure', 'wre_core', 'skillz', 'skills_registry_v2.json');
  fs.mkdirSync(path.dirname(skillRegistry), { recursive: true });
  fs.writeFileSync(skillRegistry, '{}\n', 'utf8');
  return repo;
}

function fixtureEntity(id, displayName, token, moduleName) {
  const module = 'modules/foundups/' + moduleName;
  return {
    foundup_id: id,
    display_name: displayName,
    entity_type: 'foundup',
    module_path: module,
    stage: 'proto',
    tier: 'F0_DAE',
    implementation_status: 'IMPLEMENTED',
    token_status: 'EXISTS',
    manifest_status: 'exists',
    manifest_path: module + '/foundup_manifest.json',
    token_symbol: token,
    evidence_docs: []
  };
}

function canonical(value) {
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === 'object') return Object.keys(value).sort().reduce((out, key) => {
    out[key] = canonical(value[key]); return out;
  }, {});
  return value;
}

function rehash(receipt) {
  const value = JSON.parse(JSON.stringify(receipt));
  delete value.receipt_id;
  value.receipt_id = 'sha256:' + crypto.createHash('sha256')
    .update(JSON.stringify(canonical(value)), 'utf8').digest('hex');
  return value;
}

const rootAuthority = authority(root);
const trade = grounding.resolveFoundupWorkGrounding(root, 'work on TRADE foundup', rootAuthority);
assert.strictEqual(trade.applied, true);
assert.strictEqual(trade.passed, true);
assert.strictEqual(trade.foundup_id, 'trade');
assert.strictEqual(trade.module_path, 'modules/foundups/trade');
assert(trade.evidence_targets.includes('modules/foundups/foundup_registry.json'));
assert(trade.evidence_targets.includes('modules/foundups/foundup_registry.schema.json'));
assert(trade.evidence_targets.includes('modules/foundups/trade/foundup_manifest.json'));
assert.strictEqual(trade.grants_authority, false);
assert(trade.receipt_id.startsWith('sha256:'));
assert(Object.isFrozen(trade) && Object.isFrozen(trade.evidence_targets)
  && Object.isFrozen(trade.evidence_digests) && Object.isFrozen(trade.safe_mutation_surfaces),
  'receipt and nested authority inputs must be immutable');
const originalEvidencePath = trade.evidence_digests[0].path;
assert.throws(() => { trade.evidence_digests[0].path = 'modules/foundups/other'; }, TypeError);
assert.strictEqual(trade.evidence_digests[0].path, originalEvidencePath);
assert.deepStrictEqual(
  grounding.resolveFoundupWorkGrounding(root, 'work on TRADE foundup', rootAuthority),
  trade,
  'grounding receipt must be deterministic'
);
const conversationalTrade = grounding.resolveFoundupWorkGrounding(
  root,
  'I want you to work on TRADE FoundUp; what should you work on next?',
  rootAuthority
);
assert.strictEqual(conversationalTrade.passed, true);
assert.strictEqual(conversationalTrade.foundup_id, 'trade');
for (const prompt of [
  'Please work on the FoundUp called TRADE.',
  'Work on TRADE, which is a registered FoundUp.',
  'Work on TRADE, a FoundUp.',
  'Work on TRADE as a FoundUp.',
  'Work on TRADE, our new FoundUp.',
  'Work on TRADE, an existing FoundUp.',
  'Work on TRADE, which is a FoundUp.',
  'Work on TRADE, another FoundUp.',
  'Work on TRADE, which is another FoundUp.'
]) assert.strictEqual(grounding.resolveFoundupWorkGrounding(root, prompt, rootAuthority).foundup_id, 'trade');
for (const prompt of [
  'Review the FoundUp registry.',
  'Audit FoundUp onboarding under WSP 109.',
  'Improve generic FoundUp grounding without targeting a registered entity.',
  'Review how TRADE differs from another FoundUp.',
  'Audit another FoundUp workflow without selecting one.',
  'Review some FoundUp workflows.',
  'Review more FoundUp workflows.',
  'Review fewer FoundUp workflows.',
  'Review less FoundUp work.',
  'Review all FoundUp workflows.',
  'Review both FoundUp workflows.',
  'Review many FoundUp workflows.',
  'Review no FoundUp workflow.'
]) assert.strictEqual(grounding.resolveFoundupWorkGrounding(root, prompt, rootAuthority).applied, false,
  'generic FoundUp work must not become an unknown identity target: ' + prompt);

const gotJunk = grounding.resolveFoundupWorkGrounding(root, 'continue work on GotJunk FoundUp', rootAuthority);
assert.strictEqual(gotJunk.passed, true);
assert.strictEqual(gotJunk.foundup_id, 'gotjunk_001');
assert.strictEqual(gotJunk.module_path, 'modules/foundups/gotjunk');
const adjacentAliasWins = grounding.resolveFoundupWorkGrounding(
  root, 'Compare TRADE history, then work on GotJunk FoundUp.', rootAuthority
);
assert.strictEqual(adjacentAliasWins.foundup_id, 'gotjunk_001',
  'an incidental alias elsewhere in the prompt must not create ambiguity');

const registry = JSON.parse(fs.readFileSync(path.join(root, grounding.REGISTRY_PATH), 'utf8'));
for (const entity of registry.entities) {
  const resolved = grounding.resolveFoundupWorkGrounding(
    root, 'work on ' + entity.foundup_id + ' foundup', rootAuthority
  );
  assert.strictEqual(resolved.passed, true, 'every registered FoundUp identity must resolve: ' + entity.foundup_id);
  assert.strictEqual(resolved.foundup_id, entity.foundup_id);
}
const antifafmEntity = registry.entities.find((entity) => entity.foundup_id === 'antifafm_001');
const antifafm = grounding.resolveFoundupWorkGrounding(root, 'work on antifafm_001 foundup', rootAuthority);
assert.strictEqual(antifafm.passed, true);
assert(!(antifafmEntity.evidence_docs || []).some((doc) => antifafm.evidence_targets.includes(doc)),
  'optional audit history must not exhaust the mandatory direct-read budget');

const unknown = grounding.resolveFoundupWorkGrounding(root, 'fix Nimbus FoundUp', rootAuthority);
assert.strictEqual(unknown.passed, true);
assert.strictEqual(unknown.applied, false);
assert.strictEqual(unknown.requires_wsp109_resolution, true);
assert.deepStrictEqual(unknown.safe_mutation_surfaces, []);
assert(unknown.evidence_targets.includes(grounding.REGISTRY_PATH));
assert.strictEqual(unknown.grants_authority, false);
const unknownAfter = grounding.resolveFoundupWorkGrounding(root, 'work on FoundUp Nimbus', rootAuthority);
assert.strictEqual(unknownAfter.requires_wsp109_resolution, true);
for (const prompt of ['work on Nimbus, a FoundUp', 'work on Nimbus as a FoundUp', 'work on Nimbus, our new FoundUp',
  'work on Nimbus, an existing FoundUp', 'work on Nimbus, which is a FoundUp', 'work on Nimbus, another FoundUp',
  'work on Nimbus, which is another FoundUp']) {
  const result = grounding.resolveFoundupWorkGrounding(root, prompt, rootAuthority);
  assert.strictEqual(result.requires_wsp109_resolution, true, 'unmatched language must route to WSP 109: ' + prompt);
  assert.deepStrictEqual(result.safe_mutation_surfaces, []);
}
for (const prompt of ['edit Nimbus FoundUp', 'modify Nimbus FoundUp', 'patch Nimbus FoundUp',
  'create Nimbus FoundUp', 'migrate Nimbus FoundUp', 'work on Nimbus FoundUps', 'review multiple FoundUps',
  'Review FoundUps agent workflows']) {
  const result = grounding.resolveFoundupWorkGrounding(root, prompt, rootAuthority);
  assert.strictEqual(result.requires_wsp109_resolution, true, 'verb/plural form must route without authority: ' + prompt);
  assert.deepStrictEqual(result.safe_mutation_surfaces, []);
}
const pluralAgentMarket = grounding.resolveFoundupWorkGrounding(root, 'Edit FoundUps Agent Market', rootAuthority);
assert.strictEqual(pluralAgentMarket.foundup_id, 'agent_market', 'registered alias must outrank product-token similarity');
assert.deepStrictEqual(pluralAgentMarket.safe_mutation_surfaces, []);

const notApplicable = grounding.resolveFoundupWorkGrounding(root, 'Explain the portfolio.', rootAuthority);
assert.strictEqual(notApplicable.applied, false);
assert.strictEqual(grounding.resolveFoundupWorkGrounding(
  root, 'Audit the FoundUps-Agent repository.', rootAuthority
).applied, false, 'the product name must not be parsed as a FoundUp target');

const duplicateRepo = writeFixture([
  fixtureEntity('alpha', 'Shared', 'AAA', 'alpha'),
  fixtureEntity('beta', 'Shared', 'BBB', 'beta')
]);
const ambiguous = grounding.resolveFoundupWorkGrounding(duplicateRepo, 'review Shared FoundUp', authority(duplicateRepo));
assert.strictEqual(ambiguous.passed, false);
assert(ambiguous.rejection_reasons.includes('foundup_reference_ambiguous'), JSON.stringify(ambiguous));

const traversalRepo = writeFixture([
  fixtureEntity('escape', 'Escape', 'ESC', '../outside')
]);
const traversal = grounding.resolveFoundupWorkGrounding(traversalRepo, 'work on Escape FoundUp', authority(traversalRepo));
assert.strictEqual(traversal.passed, false);
assert(traversal.rejection_reasons.includes('foundup_module_path_invalid'));

const malformedRepo = fs.mkdtempSync(path.join(os.tmpdir(), 'reddog-foundup-malformed-'));
const malformedRegistry = path.join(malformedRepo, grounding.REGISTRY_PATH);
fs.mkdirSync(path.dirname(malformedRegistry), { recursive: true });
fs.writeFileSync(malformedRegistry, '{"schema_version":"wrong","entities":[]}', 'utf8');
fs.copyFileSync(path.join(root, grounding.REGISTRY_SCHEMA_PATH), path.join(malformedRepo, grounding.REGISTRY_SCHEMA_PATH));
const malformed = grounding.resolveFoundupWorkGrounding(malformedRepo, 'work on Any FoundUp', authority(malformedRepo));
assert.strictEqual(malformed.passed, false);
assert(malformed.rejection_reasons.includes('foundup_registry_schema_invalid'));
const conditionalEntity = fixtureEntity('conditional', 'Conditional', 'CON', 'conditional');
delete conditionalEntity.token_symbol;
const conditionalRepo = writeFixture([conditionalEntity]);
const conditional = grounding.resolveFoundupWorkGrounding(
  conditionalRepo, 'work on Conditional FoundUp', authority(conditionalRepo)
);
assert(conditional.rejection_reasons.includes('foundup_registry_schema_invalid'),
  'checked-in JSON schema conditionals must be enforced');
assert.strictEqual(grounding.verifyFoundupWorkGroundingReceipt(root, trade, rootAuthority), true);
const tamperedReceipt = Object.assign({}, trade, { repo_head_sha: 'b'.repeat(40) });
assert.strictEqual(grounding.verifyFoundupWorkGroundingReceipt(root, tamperedReceipt, rootAuthority), false);

const tamperRepo = writeFixture([fixtureEntity('tamper', 'Tamper', 'TMP', 'tamper')]);
const tamperAuthority = authority(tamperRepo);
const beforeTamper = grounding.resolveFoundupWorkGrounding(tamperRepo, 'work on Tamper FoundUp', tamperAuthority);
assert.strictEqual(beforeTamper.passed, true);
fs.writeFileSync(path.join(tamperRepo, 'modules', 'foundups', 'tamper', 'README.md'), '# Changed\n', 'utf8');
assert.strictEqual(grounding.verifyFoundupWorkGroundingReceipt(tamperRepo, beforeTamper, tamperAuthority), false);
const missingAuthority = grounding.resolveFoundupWorkGrounding(root, 'work on TRADE foundup', {});
assert(missingAuthority.rejection_reasons.includes('foundup_authority_context_invalid'));
const dirtyAuthority = Object.assign({}, rootAuthority, { registry_status_clean: false });
assert(grounding.resolveFoundupWorkGrounding(root, 'work on TRADE foundup', dirtyAuthority)
  .rejection_reasons.includes('foundup_authority_context_invalid'));
const dirtyManifestAuthority = Object.assign({}, rootAuthority, {
  dirty_paths: rootAuthority.dirty_paths.concat(['modules/foundups/trade/foundup_manifest.json'])
});
assert(grounding.resolveFoundupWorkGrounding(root, 'work on TRADE foundup', dirtyManifestAuthority)
  .rejection_reasons.includes('foundup_manifest_evidence_dirty'));
const unverifiedBinding = runtime.workOrderBinding({
  foundup_use_time_verified: false,
  typed_targets: { foundup_work_grounding: trade }
}, null, []);
assert.strictEqual(unverifiedBinding.targetValid, false);
assert.deepStrictEqual(unverifiedBinding.allowed, [], 'self-hashed transport evidence cannot create mutation scope');
const unresolvedBinding = runtime.workOrderBinding({
  foundup_use_time_verified: true,
  typed_targets: { foundup_work_grounding: unknown }
}, null, ['modules/foundups/**']);
assert.strictEqual(unresolvedBinding.targetValid, false);
assert.deepStrictEqual(unresolvedBinding.allowed, [], 'unresolved FoundUp language cannot create mutation scope');
const forged = rehash(Object.assign({}, trade, { safe_mutation_surfaces: ['modules/foundups/**'] }));
assert.strictEqual(grounding.receiptIntegrityValid(forged), true, 'attack fixture must carry a valid recomputed hash');
const explicitOnlyBinding = runtime.workOrderBinding({}, forged, ['modules/foundups/**']);
assert.strictEqual(explicitOnlyBinding.targetValid, false, 'an explicit receipt cannot replace verified preflight');
assert.deepStrictEqual(explicitOnlyBinding.allowed, []);
const forgedBinding = runtime.workOrderBinding({
  foundup_use_time_verified: true,
  typed_targets: { foundup_work_grounding: trade }
}, forged, []);
assert.strictEqual(forgedBinding.targetValid, false, 'caller-supplied recomputed receipt cannot override verified preflight');
assert.deepStrictEqual(forgedBinding.allowed, []);

const sensitiveEntity = fixtureEntity('private', 'Private', 'PVT', 'private');
sensitiveEntity.evidence_docs = ['.env', 'secrets/private.pem'];
const sensitiveRepo = writeFixture([sensitiveEntity]);
fs.writeFileSync(path.join(sensitiveRepo, '.env'), 'DO_NOT_READ=1\n', 'utf8');
const sensitive = grounding.resolveFoundupWorkGrounding(
  sensitiveRepo, 'work on Private FoundUp', authority(sensitiveRepo)
);
assert.strictEqual(sensitive.passed, true);
assert(!sensitive.evidence_targets.some((item) => item === '.env' || item.includes('secrets/')),
  'sensitive paths must never become grounding evidence');

const source = fs.readFileSync(modulePath, 'utf8');
const runtimeSource = fs.readFileSync(runtimePath, 'utf8');
const phraseSource = fs.readFileSync(path.join(root, 'extensions', 'reddog', 'foundup_target_phrase.js'), 'utf8');
assert(source.split(/\r?\n/).length <= 200, 'resolver exceeds WSP_62 file limit');
assert(runtimeSource.split(/\r?\n/).length <= 200, 'runtime binding exceeds WSP_62 file limit');
assert(phraseSource.split(/\r?\n/).length <= 200, 'target phrase parser exceeds WSP_62 file limit');
assert(fs.readFileSync(path.join(root, 'extensions', 'reddog', 'json_schema_subset_validator.js'), 'utf8')
  .split(/\r?\n/).length <= 200, 'schema validator exceeds WSP_62 file limit');
assert(!/\b(?:trade|gotjunk)\b/i.test(source), 'production resolver must not hard-code FoundUp names');
assert(!/\b(?:trade|gotjunk)\b/i.test(phraseSource), 'target parser must not hard-code FoundUp names');
assert(!/child_process|\bexec(?:File|Sync)?\b|\bspawn(?:Sync)?\b|\bsubprocess\b/.test(source));
assert(!/child_process|\bexec(?:File|Sync)?\b|\bspawn(?:Sync)?\b|\bsubprocess\b/.test(runtimeSource));

console.log('PASS: registered FoundUp work grounding is generic, deterministic, and fail-closed');
