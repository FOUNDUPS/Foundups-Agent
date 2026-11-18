'use strict';

const fs = require('fs');
const path = require('path');
const { isTargetReadPathDenied } = require('./target_read_path_policy');
const files = require('./backend_compatibility_filesystem');
const targetPhrase = require('./foundup_target_phrase');
const { validateJsonSchema } = require('./json_schema_subset_validator');

const BRAND_CONTEXT_SCHEMA_PATH = 'modules/foundups/brand_context.schema.json';

function normalized(value) {
  return String(value || '').normalize('NFKC').toLowerCase().replace(/[_-]+/g, ' ')
    .replace(/[^a-z0-9\u3040-\u30ff\u3400-\u9fff.]+/g, ' ').trim().replace(/\s+/g, ' ');
}

function realFile(repoRoot, relative) {
  if (typeof relative !== 'string' || isTargetReadPathDenied(relative)) return null;
  const deps = files.dependencies();
  const root = files.safeRoot(repoRoot, deps);
  if (root.reason) return null;
  const result = files.containedRegularFile(root, relative, deps);
  if (!result.ok || fs.lstatSync(result.candidate).nlink !== 1) return null;
  const resolved = path.relative(root.canonicalRoot, fs.realpathSync(result.candidate)).replace(/\\/g, '/');
  return isTargetReadPathDenied(resolved) ? null : result.candidate;
}

function loadBrandContext(repoRoot, authority, entity) {
  const declared = entity && entity.brand_context_path;
  if (declared == null) return null;
  if (typeof declared !== 'string' || isTargetReadPathDenied(declared)) {
    throw new Error('foundup_brand_context_path_invalid');
  }
  const relative = declared.replace(/\\/g, '/');
  if (!authority || !authority.tracked.has(relative) || !authority.tracked.has(BRAND_CONTEXT_SCHEMA_PATH)) {
    throw new Error('foundup_brand_context_evidence_missing');
  }
  if (authority.dirty.has(relative) || authority.dirty.has(BRAND_CONTEXT_SCHEMA_PATH)) {
    throw new Error('foundup_brand_context_evidence_dirty');
  }
  const contextFile = realFile(repoRoot, relative);
  const schemaFile = realFile(repoRoot, BRAND_CONTEXT_SCHEMA_PATH);
  if (!contextFile || !schemaFile) throw new Error('foundup_brand_context_evidence_missing');
  const context = JSON.parse(fs.readFileSync(contextFile, 'utf8'));
  const schema = JSON.parse(fs.readFileSync(schemaFile, 'utf8'));
  if (validateJsonSchema(context, schema).length) throw new Error('foundup_brand_context_schema_invalid');
  if (context.foundup_id !== entity.foundup_id) throw new Error('foundup_brand_context_identity_mismatch');
  const state = { path: relative, schema_path: BRAND_CONTEXT_SCHEMA_PATH, context };
  brandAliasRecords(state);
  return state;
}

function brandAliasRecords(state) {
  if (!state || !state.context) return [];
  const context = state.context;
  const records = [];
  const identities = new Set();
  const aliases = new Map();
  for (const brand of [context, ...(context.child_foundups || [])]) {
    if (identities.has(brand.foundup_id)) throw new Error('foundup_brand_identity_ambiguous');
    identities.add(brand.foundup_id);
    for (const value of [brand.foundup_id, brand.canonical_brand, ...(brand.aliases || [])]) {
      const reference = normalized(value);
      if (!reference) throw new Error('foundup_brand_alias_invalid');
      if (aliases.has(reference)) {
        if (aliases.get(reference) !== brand.foundup_id) throw new Error('foundup_brand_alias_ambiguous');
        continue;
      }
      aliases.set(reference, brand.foundup_id);
      records.push({ reference, brand_foundup_id: brand.foundup_id, canonical_brand: brand.canonical_brand });
    }
  }
  return records;
}

function selectEntity(repoRoot, authority, registry, taskText) {
  const matches = new Map();
  for (const entity of registry.entities) {
    const state = loadBrandContext(repoRoot, authority, entity);
    const canonical = state ? state.context.canonical_brand : entity.display_name;
    const moduleBase = path.posix.basename(String(entity.module_path || '').replace(/\\/g, '/'));
    const records = brandAliasRecords(state);
    for (const alias of [entity.foundup_id, entity.display_name, entity.token_symbol, moduleBase]) {
      const reference = normalized(alias);
      if (reference.length < 2) continue;
      if (records.some((record) => record.reference === reference && record.brand_foundup_id !== entity.foundup_id)) {
        throw new Error('foundup_brand_alias_ambiguous');
      }
      records.push({ reference, brand_foundup_id: entity.foundup_id, canonical_brand: canonical });
    }
    for (const record of records) if (targetPhrase.referenceNearFoundup(taskText, record.reference)) {
      const key = entity.foundup_id + ':' + record.brand_foundup_id;
      if (!matches.has(key)) matches.set(key, Object.assign({ entity, brand_state: state }, record));
    }
  }
  if (matches.size > 1) throw new Error('foundup_reference_ambiguous');
  return matches.values().next().value || null;
}

module.exports = { BRAND_CONTEXT_SCHEMA_PATH, brandAliasRecords, loadBrandContext, realFile, selectEntity };
