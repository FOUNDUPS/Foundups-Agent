'use strict';

function typeMatches(value, expected) {
  if (expected === 'null') return value === null;
  if (expected === 'array') return Array.isArray(value);
  if (expected === 'object') return value !== null && typeof value === 'object' && !Array.isArray(value);
  if (expected === 'integer') return Number.isInteger(value);
  if (expected === 'number') return typeof value === 'number' && Number.isFinite(value);
  return typeof value === expected;
}

function resolveRef(root, reference) {
  if (!String(reference || '').startsWith('#/')) return null;
  return reference.slice(2).split('/').reduce((value, part) => {
    const key = part.replace(/~1/g, '/').replace(/~0/g, '~');
    return value && typeof value === 'object' ? value[key] : undefined;
  }, root);
}

function formatMatches(value, format) {
  if (typeof value !== 'string') return true;
  if (format === 'date') return /^\d{4}-\d{2}-\d{2}$/.test(value) && !Number.isNaN(Date.parse(value + 'T00:00:00Z'));
  if (format === 'date-time') return /^\d{4}-\d{2}-\d{2}T/.test(value) && !Number.isNaN(Date.parse(value));
  if (format === 'uri') {
    try { return Boolean(new URL(value).protocol); } catch (_error) { return false; }
  }
  return true;
}

function validateNode(value, schema, root, location, errors) {
  if (!schema || typeof schema !== 'object') { errors.push(location + ':schema_invalid'); return; }
  if (schema.$ref) {
    const target = resolveRef(root, schema.$ref);
    if (!target) errors.push(location + ':ref_unresolved');
    else validateNode(value, target, root, location, errors);
    return;
  }
  const types = Array.isArray(schema.type) ? schema.type : (schema.type ? [schema.type] : []);
  if (types.length && !types.some((item) => typeMatches(value, item))) {
    errors.push(location + ':type'); return;
  }
  if (Object.prototype.hasOwnProperty.call(schema, 'const') && value !== schema.const) errors.push(location + ':const');
  if (Array.isArray(schema.enum) && !schema.enum.some((item) => item === value)) errors.push(location + ':enum');
  if (typeof value === 'string') {
    if (schema.minLength !== undefined && value.length < schema.minLength) errors.push(location + ':minLength');
    if (schema.maxLength !== undefined && value.length > schema.maxLength) errors.push(location + ':maxLength');
    if (schema.pattern && !new RegExp(schema.pattern, 'u').test(value)) errors.push(location + ':pattern');
    if (schema.format && !formatMatches(value, schema.format)) errors.push(location + ':format');
  }
  if (typeof value === 'number') {
    if (schema.minimum !== undefined && value < schema.minimum) errors.push(location + ':minimum');
    if (schema.maximum !== undefined && value > schema.maximum) errors.push(location + ':maximum');
  }
  if (Array.isArray(value) && schema.items) value.forEach((item, index) => validateNode(item, schema.items, root, location + '/' + index, errors));
  if (value !== null && typeof value === 'object' && !Array.isArray(value)) {
    for (const key of schema.required || []) if (!Object.prototype.hasOwnProperty.call(value, key)) errors.push(location + '/' + key + ':required');
    for (const [key, child] of Object.entries(schema.properties || {})) {
      if (Object.prototype.hasOwnProperty.call(value, key)) validateNode(value[key], child, root, location + '/' + key, errors);
    }
  }
  for (const child of schema.allOf || []) validateNode(value, child, root, location, errors);
  if (Array.isArray(schema.oneOf)) {
    const passing = schema.oneOf.filter((child) => validateJsonSchema(value, child, root).length === 0).length;
    if (passing !== 1) errors.push(location + ':oneOf');
  }
  if (schema.if && validateJsonSchema(value, schema.if, root).length === 0 && schema.then) {
    validateNode(value, schema.then, root, location, errors);
  }
}

function validateJsonSchema(value, schema, rootSchema) {
  const errors = [];
  validateNode(value, schema, rootSchema || schema, '$', errors);
  return errors;
}

module.exports = { validateJsonSchema };
