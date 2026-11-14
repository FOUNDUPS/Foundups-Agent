'use strict';

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const SCHEMA = 'reddog.principal_activity.v1';
const ZERO_HASH = '0'.repeat(64);
const LOCK_FILE = '.principal-activity.lock';

// Cooperating hosts only: an abandoned lock is never reclaimed automatically.
function withRootLock(rootDir, operation) {
  fs.mkdirSync(rootDir, { recursive: true, mode: 0o700 });
  const file = path.join(fs.realpathSync(rootDir), LOCK_FILE);
  const fd = fs.openSync(file, 'wx', 0o600);
  let owned;
  try { owned = fs.fstatSync(fd); } catch (error) {
    try { fs.closeSync(fd); } catch (cleanup) { throw new AggregateError([error, cleanup], 'principal_activity_lock_cleanup_failed'); }
    throw error; // Leave the unverified lock for explicit recovery.
  }
  function release() {
    let failure;
    try {
      const current = fs.lstatSync(file);
      if (!current.isFile() || current.dev !== owned.dev || current.ino !== owned.ino) {
        throw new Error('principal_activity_lock_changed');
      }
    } catch (error) { failure = error; }
    try { fs.closeSync(fd); } catch (cleanup) {
      if (failure) throw new AggregateError([failure, cleanup], 'principal_activity_lock_cleanup_failed');
      throw cleanup;
    }
    if (failure) throw failure;
    fs.unlinkSync(file);
  }
  function fail(error) {
    try { release(); } catch (cleanup) {
      throw new AggregateError([error, cleanup], 'principal_activity_operation_and_cleanup_failed');
    }
    throw error;
  }
  let result;
  try { result = operation(); } catch (error) { return fail(error); }
  if (result && typeof result.then === 'function') {
    return Promise.resolve(result).then((value) => { release(); return value; }, fail);
  }
  release();
  return result;
}

function assertKey(key) {
  if (!Buffer.isBuffer(key) || key.length !== 32) {
    throw new Error('principal activity key must be a 32-byte Buffer');
  }
}

function digest(value) {
  return crypto.createHash('sha256').update(value).digest('hex');
}

function stableJson(value, ancestors = new Set()) {
  if (value === null || typeof value === 'string' || typeof value === 'boolean') return JSON.stringify(value);
  if (typeof value === 'number' && Number.isFinite(value)) return JSON.stringify(value);
  if (!value || typeof value !== 'object' || ancestors.has(value)) throw new Error('principal_activity_json_invalid');
  if (!Array.isArray(value) && ![Object.prototype, null].includes(Object.getPrototypeOf(value))) {
    throw new Error('principal_activity_json_invalid');
  }
  if (Object.getOwnPropertySymbols(value).length) throw new Error('principal_activity_json_invalid');
  ancestors.add(value);
  try {
    if (Array.isArray(value)) {
      const entries = [];
      for (let i = 0; i < value.length; i += 1) {
        const descriptor = Object.getOwnPropertyDescriptor(value, String(i));
        if (!descriptor || !Object.hasOwn(descriptor, 'value')) throw new Error('principal_activity_json_invalid');
        entries.push(stableJson(descriptor.value, ancestors));
      }
      return '[' + entries.join(',') + ']';
    }
    return '{' + Object.keys(value).sort().map((key) => {
      const descriptor = Object.getOwnPropertyDescriptor(value, key);
      if (!Object.hasOwn(descriptor, 'value')) throw new Error('principal_activity_json_invalid');
      return JSON.stringify(key) + ':' + stableJson(descriptor.value, ancestors);
    }).join(',') + '}';
  } finally { ancestors.delete(value); }
}

function principalDigest(principalId) {
  if (!principalId || typeof principalId !== 'string') throw new Error('principalId required');
  return digest('reddog-principal:' + principalId);
}

function ledgerPath(rootDir, principalId) {
  return path.join(path.resolve(rootDir), principalDigest(principalId), 'activity.jsonl');
}

function atomicAppend(file, line) {
  fs.mkdirSync(path.dirname(file), { recursive: true, mode: 0o700 });
  const fd = fs.openSync(file, 'a', 0o600);
  try {
    const bytes = Buffer.from(line + '\n', 'utf8');
    let offset = 0;
    while (offset < bytes.length) {
      const written = fs.writeSync(fd, bytes, offset, bytes.length - offset, null);
      if (!Number.isInteger(written) || written <= 0 || written > bytes.length - offset) {
        throw new Error('principal_activity_append_incomplete');
      }
      offset += written;
    }
    fs.fsyncSync(fd);
  } finally {
    fs.closeSync(fd);
  }
}

function readEnvelopes(file) {
  if (!fs.existsSync(file)) return [];
  if (!fs.lstatSync(file).isFile()) throw new Error('principal_activity_file_invalid');
  const lines = fs.readFileSync(file, 'utf8').split(/\r?\n/).filter(Boolean);
  if (!lines.length) throw new Error('principal_activity_file_empty');
  return lines.map((line) => JSON.parse(line));
}

// Called only inside withRootLock, including while the host awaits SecretStorage.
function storedLedgers(rootDir) {
  const files = [];
  for (const name of fs.readdirSync(rootDir)) {
    if (name === LOCK_FILE) continue;
    const dir = path.join(rootDir, name);
    if (!/^[a-f0-9]{64}$/.test(name) || !fs.lstatSync(dir).isDirectory()) {
      throw new Error('principal_activity_storage_invalid');
    }
    const entries = fs.readdirSync(dir);
    if (entries.some((entry) => entry !== 'activity.jsonl')) throw new Error('principal_activity_storage_invalid');
    if (entries.length) files.push({ file: path.join(dir, 'activity.jsonl'), principal: name });
  }
  return files;
}

function verifyEnvelopes(envelopes, principal) {
  let previous = ZERO_HASH;
  for (let index = 0; index < envelopes.length; index += 1) {
    const envelope = envelopes[index];
    if (envelope.schema !== SCHEMA || envelope.principal_digest !== principal) throw new Error('principal activity scope mismatch');
    if (envelope.sequence !== index + 1 || envelope.previous_hash !== previous) throw new Error('principal activity chain mismatch');
    const { record_hash, ...unsigned } = envelope;
    if (digest(stableJson(unsigned)) !== record_hash) throw new Error('principal activity record tampered');
    previous = record_hash;
  }
  return true;
}

function decryptEvents(envelopes, principal, key) {
  verifyEnvelopes(envelopes, principal);
  return envelopes.map((envelope) => decryptPayload(key, envelope,
    `${SCHEMA}:${principal}:${envelope.sequence}:${envelope.previous_hash}`));
}

function validateStoredKey(rootDir, key) {
  for (const entry of storedLedgers(rootDir)) {
    decryptEvents(readEnvelopes(entry.file), entry.principal, key);
  }
}

function encryptPayload(key, payload, aad) {
  const iv = crypto.randomBytes(12);
  const cipher = crypto.createCipheriv('aes-256-gcm', key, iv);
  cipher.setAAD(Buffer.from(aad, 'utf8'));
  const ciphertext = Buffer.concat([cipher.update(Buffer.from(stableJson(payload), 'utf8')), cipher.final()]);
  return {
    iv: iv.toString('base64'),
    tag: cipher.getAuthTag().toString('base64'),
    ciphertext: ciphertext.toString('base64')
  };
}

function decryptPayload(key, envelope, aad) {
  const decipher = crypto.createDecipheriv('aes-256-gcm', key, Buffer.from(envelope.iv, 'base64'));
  decipher.setAAD(Buffer.from(aad, 'utf8'));
  decipher.setAuthTag(Buffer.from(envelope.tag, 'base64'));
  return JSON.parse(Buffer.concat([
    decipher.update(Buffer.from(envelope.ciphertext, 'base64')),
    decipher.final()
  ]).toString('utf8'));
}

class PrincipalActivityLedger {
  constructor({ rootDir, principalId, key }) {
    if (!rootDir) throw new Error('rootDir required');
    assertKey(key);
    this.rootDir = path.resolve(rootDir);
    this.principalId = principalId;
    this.principal_digest = principalDigest(principalId);
    this.key = Buffer.from(key);
    this.file = ledgerPath(this.rootDir, principalId);
  }

  append(event) {
    if (!event || typeof event !== 'object') throw new Error('event object required');
    const payload = Object.freeze({
      event_id: event.event_id || crypto.randomUUID(),
      occurred_at: event.occurred_at || new Date().toISOString(),
      kind: event.kind || 'activity',
      source: event.source || 'reddog',
      projects: Array.isArray(event.projects) ? event.projects : [],
      contacts: Array.isArray(event.contacts) ? event.contacts : [],
      commitments: Array.isArray(event.commitments) ? event.commitments : [],
      evidence_refs: Array.isArray(event.evidence_refs) ? event.evidence_refs : [],
      facts: event.facts && typeof event.facts === 'object' ? event.facts : {},
      notes: typeof event.notes === 'string' ? event.notes : ''
    });
    stableJson(payload); // Reject poison JSON before creating a lock or writing data.
    return withRootLock(this.rootDir, () => {
      validateStoredKey(this.rootDir, this.key);
      const envelopes = readEnvelopes(this.file);
      const sequence = envelopes.length + 1;
      const previous_hash = envelopes.length ? envelopes[envelopes.length - 1].record_hash : ZERO_HASH;
      const aad = `${SCHEMA}:${this.principal_digest}:${sequence}:${previous_hash}`;
      const encrypted = encryptPayload(this.key, payload, aad);
      const unsigned = { schema: SCHEMA, principal_digest: this.principal_digest, sequence, previous_hash, ...encrypted };
      const record_hash = digest(stableJson(unsigned));
      const envelope = { ...unsigned, record_hash };
      atomicAppend(this.file, stableJson(envelope));
      return Object.freeze({ event_id: payload.event_id, sequence, record_hash, principal_digest: this.principal_digest });
    });
  }

  verifyChain(envelopes) {
    if (envelopes !== undefined) return verifyEnvelopes(envelopes, this.principal_digest);
    return withRootLock(this.rootDir, () => verifyEnvelopes(readEnvelopes(this.file), this.principal_digest));
  }

  events() {
    return withRootLock(this.rootDir, () => decryptEvents(readEnvelopes(this.file), this.principal_digest, this.key));
  }

  context({ project, contact, limit = 50 } = {}) {
    const history = this.events();
    let events = history;
    if (project) events = events.filter((event) => event.projects.includes(project));
    if (contact) events = events.filter((event) => event.contacts.includes(contact));
    const relevant = new Set(events.flatMap((event) => event.commitments.filter((item) => item && item.id).map((item) => item.id)));
    const latest = new Map();
    for (const event of history) {
      for (const item of event.commitments) {
        if (!item || !item.id) continue;
        latest.delete(item.id);
        latest.set(item.id, { ...item, event_id: event.event_id, occurred_at: event.occurred_at });
      }
    }
    const count = Math.max(1, Math.min(Number(limit) || 50, 200));
    events = events.slice(-count);
    const open = [...latest.values()].filter((item) => relevant.has(item.id)
      && item.status !== 'done' && item.status !== 'cancelled');
    return Object.freeze({
      schema: 'reddog.context_packet.v1',
      principal_digest: this.principal_digest,
      generated_at: new Date().toISOString(),
      event_count: events.length,
      recent_events: events,
      open_commitment_count: open.length,
      open_commitments_truncated: open.length > count,
      open_commitments: open.slice(-count)
    });
  }
}

module.exports = Object.freeze({ SCHEMA, PrincipalActivityLedger, principalDigest, ledgerPath,
  withRootLock, storedLedgers, validateStoredKey, stableJson });
