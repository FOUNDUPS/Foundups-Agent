const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const { validateJsonSchema } = require('./json_schema_subset_validator');
const targetPhrase = require('./foundup_target_phrase');
const REGISTRY_PATH = 'modules/foundups/foundup_registry.json';
const REGISTRY_SCHEMA_PATH = 'modules/foundups/foundup_registry.schema.json';
const OPERATIONS_SKILL_PATH = 'modules/communication/moltbot_bridge/skillz/reddog_operations/SKILLz.md';
const SKILL_REGISTRY_PATH = 'modules/infrastructure/wre_core/skillz/skills_registry_v2.json';
const RECEIPT_SCHEMA = 'registered_foundup_target_receipt.v1';
const FOUNDUP_RE = /\bfound[\s-]?ups?\b/i;

function canonical(value) {
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === 'object') return Object.keys(value).sort().reduce((out, key) => {
    out[key] = canonical(value[key]); return out;
  }, {});
  return value;
}

function digest(value) {
  const input = Buffer.isBuffer(value) ? value : Buffer.from(JSON.stringify(canonical(value)), 'utf8');
  return 'sha256:' + crypto.createHash('sha256').update(input).digest('hex');
}

function deepFreeze(value) {
  if (value && typeof value === 'object' && !Object.isFrozen(value)) {
    Object.values(value).forEach(deepFreeze); Object.freeze(value);
  }
  return value;
}

function normalized(value) {
  return String(value || '').normalize('NFKC').toLowerCase().replace(/[_-]+/g, ' ')
    .replace(/[^a-z0-9]+/g, ' ').trim().replace(/\s+/g, ' ');
}

function failure(reason, extra) {
  const values = Object.assign({ schema_version: RECEIPT_SCHEMA, applied: true, passed: false,
    rejection_reasons: [reason], evidence_targets: [], evidence_digests: [], safe_mutation_surfaces: [], grants_authority: false }, extra || {});
  return deepFreeze(Object.assign(values, { receipt_id: digest(values) }));
}

function containedRelative(relativePath) {
  const value = String(relativePath || '').replace(/\\/g, '/');
  if (!value || path.isAbsolute(value) || value.includes('\0') || value.includes(':') || /^[a-z]:/i.test(value)) return null;
  const clean = path.posix.normalize(value);
  return clean === '..' || clean.startsWith('../') ? null : clean;
}

function evidencePathAllowed(relativePath) {
  const parts = String(relativePath || '').toLowerCase().split('/');
  const leaf = parts[parts.length - 1] || '';
  return !parts.some((part) => ['.git', 'node_modules', 'secrets', 'credentials'].includes(part))
    && leaf !== '.env' && !leaf.startsWith('.env.') && !leaf.endsWith('.key') && !leaf.endsWith('.pem');
}

function realPathContained(repoRoot, target, kind) {
  if (!fs.existsSync(target)) return false;
  const relative = path.relative(fs.realpathSync(repoRoot), fs.realpathSync(target));
  if (relative === '..' || relative.startsWith('..' + path.sep) || path.isAbsolute(relative)) return false;
  const stat = fs.lstatSync(target);
  if (stat.isSymbolicLink()) return false;
  return kind === 'directory' ? stat.isDirectory() : stat.isFile();
}

function authorityState(repoRoot, options) {
  const value = options && typeof options === 'object' ? options : {};
  const tracked = new Set(Array.isArray(value.tracked_paths) ? value.tracked_paths.map((item) => String(item).replace(/\\/g, '/')) : []);
  const dirty = new Set(Array.isArray(value.dirty_paths) ? value.dirty_paths.map((item) => String(item).replace(/\\/g, '/')) : []);
  if (!/^[0-9a-f]{40}$/i.test(String(value.repo_head_sha || '')) || value.registry_status_clean !== true
    || !tracked.has(REGISTRY_PATH) || !tracked.has(REGISTRY_SCHEMA_PATH)) return null;
  return { repo_head_sha: String(value.repo_head_sha).toLowerCase(), tracked, dirty };
}

function readRegistry(repoRoot, authority) {
  const registryFile = path.resolve(repoRoot, REGISTRY_PATH);
  const schemaFile = path.resolve(repoRoot, REGISTRY_SCHEMA_PATH);
  if (!authority || !realPathContained(repoRoot, registryFile, 'file') || !realPathContained(repoRoot, schemaFile, 'file')) throw new Error('foundup_authority_context_invalid');
  const bytes = fs.readFileSync(registryFile);
  const schemaBytes = fs.readFileSync(schemaFile);
  const registry = JSON.parse(bytes.toString('utf8'));
  const schema = JSON.parse(schemaBytes.toString('utf8'));
  if (validateJsonSchema(registry, schema).length) throw new Error('foundup_registry_schema_invalid');
  const ids = registry.entities.map((entity) => entity && entity.foundup_id);
  if (ids.some((id) => !/^[a-z0-9_]+$/.test(String(id || ''))) || new Set(ids).size !== ids.length) throw new Error('foundup_registry_identity_invalid');
  if (registry.entities.some((entity) => !entity || !String(entity.display_name || '').trim()
    || !String(entity.entity_type || '').trim() || !String(entity.implementation_status || '').trim()
    || (entity.module_path !== null && typeof entity.module_path !== 'string'))) throw new Error('foundup_registry_entity_invalid');
  return { registry, registry_digest: digest(bytes), registry_schema_digest: digest(schemaBytes) };
}

function aliases(entity) {
  const moduleBase = path.posix.basename(String(entity.module_path || '').replace(/\\/g, '/'));
  return Array.from(new Set([entity.foundup_id, entity.display_name, entity.token_symbol, moduleBase]
    .map(normalized).filter((value) => value.length >= 2)));
}

function selectEntity(registry, taskText) {
  const matches = [];
  for (const entity of registry.entities) for (const reference of aliases(entity)) {
    if (targetPhrase.referenceNearFoundup(taskText, reference)) {
      matches.push({ entity, reference }); break;
    }
  }
  if (matches.length > 1) throw new Error('foundup_reference_ambiguous');
  return matches[0] || null;
}
function unresolved(registryState, authority) {
  return deepFreeze({ applied: false, passed: true, rejection_reasons: [], foundup_language_present: true,
    foundup_resolution: 'UNRESOLVED', requires_wsp109_resolution: true,
    registry_digest: registryState.registry_digest, registry_schema_digest: registryState.registry_schema_digest,
    repo_head_sha: authority.repo_head_sha, evidence_targets: [REGISTRY_PATH, REGISTRY_SCHEMA_PATH, OPERATIONS_SKILL_PATH],
    evidence_digests: [], safe_mutation_surfaces: [], grants_authority: false });
}

function foundupLanguagePresent(taskText) {
  const withoutProductName = String(taskText || '').replace(/\bfoundups-agent\b/gi, '');
  return FOUNDUP_RE.test(withoutProductName);
}

function evidencePaths(entity, modulePath) {
  const values = [REGISTRY_PATH, REGISTRY_SCHEMA_PATH, containedRelative(entity.manifest_path), OPERATIONS_SKILL_PATH, SKILL_REGISTRY_PATH];
  if (modulePath) for (const suffix of ['README.md', 'INTERFACE.md', 'ROADMAP.md', 'ModLog.md', 'tests/TestModLog.md']) values.push(modulePath + '/' + suffix);
  return Array.from(new Set(values.filter((value) => value && evidencePathAllowed(value))));
}

function readEvidence(repoRoot, authority, candidates) {
  const records = [];
  for (const relative of candidates) {
    if (!authority.tracked.has(relative)) continue;
    const target = path.resolve(repoRoot, relative);
    if (realPathContained(repoRoot, target, 'file')) records.push({ path: relative, content_digest: digest(fs.readFileSync(target)) });
  }
  return records;
}

function manifestState(repoRoot, entity, modulePath, records) {
  const manifestPath = containedRelative(entity.manifest_path);
  if (!manifestPath || !records.some((record) => record.path === manifestPath)) return { manifest_path: null, safe_mutation_surfaces: [] };
  const manifest = JSON.parse(fs.readFileSync(path.resolve(repoRoot, manifestPath), 'utf8'));
  if (String(manifest.foundup_id || '') !== String(entity.foundup_id || '')) throw new Error('foundup_manifest_identity_mismatch');
  const raw = manifest.build_contract && Array.isArray(manifest.build_contract.safe_mutation_surface) ? manifest.build_contract.safe_mutation_surface : [];
  const safe = raw.map(containedRelative).filter(Boolean);
  if (!modulePath || safe.some((scope) => scope !== modulePath + '/**' && !scope.startsWith(modulePath + '/'))) throw new Error('foundup_mutation_surface_invalid');
  return { manifest_path: manifestPath, safe_mutation_surfaces: safe };
}

function success(repoRoot, authority, registryState, entity, reference) {
  const modulePath = entity.module_path == null ? null : containedRelative(entity.module_path);
  if (entity.module_path != null && (!modulePath || !realPathContained(repoRoot, path.resolve(repoRoot, modulePath), 'directory'))) throw new Error('foundup_module_path_invalid');
  const records = readEvidence(repoRoot, authority, evidencePaths(entity, modulePath));
  if (!records.some((record) => record.path === REGISTRY_PATH)) throw new Error('foundup_registry_evidence_missing');
  if (entity.manifest_path && authority.dirty.has(containedRelative(entity.manifest_path))) throw new Error('foundup_manifest_evidence_dirty');
  const manifest = manifestState(repoRoot, entity, modulePath, records);
  if (entity.manifest_status === 'exists' && !manifest.manifest_path) throw new Error('foundup_manifest_evidence_missing');
  const values = { schema_version: RECEIPT_SCHEMA, applied: true, passed: true, rejection_reasons: [],
    resolver_version: '1.0.0', foundup_id: String(entity.foundup_id), matched_reference: reference,
    entity_type: String(entity.entity_type || ''), module_path: modulePath, manifest_path: manifest.manifest_path,
    registry_schema_version: registryState.registry.schema_version, registry_digest: registryState.registry_digest,
    registry_schema_digest: registryState.registry_schema_digest,
    registry_entity_digest: digest(entity), repo_head_sha: authority.repo_head_sha, repo_root_digest: digest(fs.realpathSync(repoRoot)),
    evidence_targets: records.map((record) => record.path), evidence_digests: records,
    safe_mutation_surfaces: manifest.safe_mutation_surfaces, grants_authority: false };
  values.evidence_checkout_state = 'workspace_current';
  values.dirty_evidence_paths = records.map((record) => record.path).filter((item) => authority.dirty.has(item));
  return deepFreeze(Object.assign(values, { receipt_id: digest(values) }));
}

function resolveFoundupWorkGrounding(repoRoot, taskText, options) {
  if (!foundupLanguagePresent(taskText)) return deepFreeze({ applied: false, passed: true, rejection_reasons: [], evidence_targets: [], safe_mutation_surfaces: [], grants_authority: false });
  const authority = authorityState(repoRoot, options);
  if (!authority) return failure('foundup_authority_context_invalid');
  try {
    const registryState = readRegistry(repoRoot, authority);
    const selected = selectEntity(registryState.registry, taskText);
    if (!selected) return unresolved(registryState, authority);
    return success(repoRoot, authority, registryState, selected.entity, selected.reference);
  } catch (error) {
    return failure(String(error && error.message || 'foundup_grounding_failed'));
  }
}

function verifyFoundupWorkGroundingReceipt(repoRoot, receipt, options) {
  if (!receiptIntegrityValid(receipt)) return false;
  const current = resolveFoundupWorkGrounding(repoRoot, 'work on ' + receipt.matched_reference + ' foundup', options);
  return current.passed === true && current.receipt_id === receipt.receipt_id;
}

function receiptIntegrityValid(receipt) {
  if (!receipt || receipt.schema_version !== RECEIPT_SCHEMA || receipt.passed !== true || receipt.grants_authority !== false) return false;
  const payload = Object.fromEntries(Object.entries(receipt).filter(([key]) => key !== 'receipt_id'));
  return receipt.receipt_id === digest(payload);
}

module.exports = { RECEIPT_SCHEMA, REGISTRY_PATH, REGISTRY_SCHEMA_PATH, receiptIntegrityValid, resolveFoundupWorkGrounding, verifyFoundupWorkGroundingReceipt };
