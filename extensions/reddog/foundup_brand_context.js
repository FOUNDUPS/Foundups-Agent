'use strict';

const fs = require('fs');
const path = require('path');
const { validateJsonSchema } = require('./json_schema_subset_validator');

const BRAND_CONTEXT_SCHEMA_PATH = 'modules/foundups/brand_context.schema.json';

function normalized(value) {
  return String(value || '').normalize('NFKC').toLowerCase().replace(/[_-]+/g, ' ')
    .replace(/[^a-z0-9\u3040-\u30ff\u3400-\u9fff.]+/g, ' ').trim().replace(/\s+/g, ' ');
}

function containedRelative(value) {
  const text = String(value || '').replace(/\\/g, '/');
  if (!text || path.isAbsolute(text) || text.includes('\0') || text.includes(':') || /^[a-z]:/i.test(text)) return null;
  const clean = path.posix.normalize(text);
  return clean === '..' || clean.startsWith('../') ? null : clean;
}

function realFile(repoRoot, relative) {
  const target = path.resolve(repoRoot, relative);
  if (!fs.existsSync(target)) return null;
  const root = fs.realpathSync(repoRoot);
  const real = fs.realpathSync(target);
  const rel = path.relative(root, real);
  if (rel === '..' || rel.startsWith('..' + path.sep) || path.isAbsolute(rel)) return null;
  const stat = fs.lstatSync(target);
  return !stat.isSymbolicLink() && stat.isFile() ? target : null;
}

function loadBrandContext(repoRoot, authority, entity) {
  const relative = containedRelative(entity && entity.brand_context_path);
  if (!relative) return null;
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
  return { path: relative, schema_path: BRAND_CONTEXT_SCHEMA_PATH, context };
}

function brandAliasRecords(state) {
  if (!state || !state.context) return [];
  const context = state.context;
  const records = [];
  const push = (value, foundupId, canonicalBrand) => {
    const reference = normalized(value);
    if (reference && !records.some((item) => item.reference === reference && item.brand_foundup_id === foundupId)) {
      records.push({ reference, brand_foundup_id: foundupId, canonical_brand: canonicalBrand });
    }
  };
  push(context.canonical_brand, context.foundup_id, context.canonical_brand);
  for (const alias of context.aliases || []) push(alias, context.foundup_id, context.canonical_brand);
  for (const child of context.child_foundups || []) {
    push(child.foundup_id, child.foundup_id, child.canonical_brand);
    push(child.canonical_brand, child.foundup_id, child.canonical_brand);
    for (const alias of child.aliases || []) push(alias, child.foundup_id, child.canonical_brand);
  }
  return records;
}

module.exports = { BRAND_CONTEXT_SCHEMA_PATH, brandAliasRecords, loadBrandContext };
