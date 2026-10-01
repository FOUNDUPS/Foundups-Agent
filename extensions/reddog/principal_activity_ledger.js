'use strict';

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const SCHEMA = 'reddog.principal_activity.v1';
const ZERO_HASH = '0'.repeat(64);

function assertKey(key) {
  if (!Buffer.isBuffer(key) || key.length !== 32) {
    throw new Error('principal activity key must be a 32-byte Buffer');
  }
}

function digest(value) {
  return crypto.createHash('sha256').update(value).digest('hex');
}

function stableJson(value) {
  if (Array.isArray(value)) return '[' + value.map(stableJson).join(',') + ']';
  if (value && typeof value === 'object') {
    return '{' + Object.keys(value).sort().map((key) =>
      JSON.stringify(key) + ':' + stableJson(value[key])).join(',') + '}';
  }
  return JSON.stringify(value);
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
    fs.writeSync(fd, line + '\n', null, 'utf8');
    fs.fsyncSync(fd);
  } finally {
    fs.closeSync(fd);
  }
}

function readEnvelopes(file) {
  if (!fs.existsSync(file)) return [];
  return fs.readFileSync(file, 'utf8').split(/\r?\n/).filter(Boolean).map((line) => JSON.parse(line));
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
    const envelopes = readEnvelopes(this.file);
    this.verifyChain(envelopes);
    const sequence = envelopes.length + 1;
    const previous_hash = envelopes.length ? envelopes[envelopes.length - 1].record_hash : ZERO_HASH;
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
    const aad = `${SCHEMA}:${this.principal_digest}:${sequence}:${previous_hash}`;
    const encrypted = encryptPayload(this.key, payload, aad);
    const unsigned = { schema: SCHEMA, principal_digest: this.principal_digest, sequence, previous_hash, ...encrypted };
    const record_hash = digest(stableJson(unsigned));
    const envelope = { ...unsigned, record_hash };
    atomicAppend(this.file, stableJson(envelope));
    return Object.freeze({ event_id: payload.event_id, sequence, record_hash, principal_digest: this.principal_digest });
  }

  verifyChain(envelopes = readEnvelopes(this.file)) {
    let previous = ZERO_HASH;
    for (let index = 0; index < envelopes.length; index += 1) {
      const envelope = envelopes[index];
      if (envelope.schema !== SCHEMA || envelope.principal_digest !== this.principal_digest) throw new Error('principal activity scope mismatch');
      if (envelope.sequence !== index + 1 || envelope.previous_hash !== previous) throw new Error('principal activity chain mismatch');
      const { record_hash, ...unsigned } = envelope;
      if (digest(stableJson(unsigned)) !== record_hash) throw new Error('principal activity record tampered');
      previous = record_hash;
    }
    return true;
  }

  events() {
    const envelopes = readEnvelopes(this.file);
    this.verifyChain(envelopes);
    return envelopes.map((envelope) => {
      const aad = `${SCHEMA}:${this.principal_digest}:${envelope.sequence}:${envelope.previous_hash}`;
      return decryptPayload(this.key, envelope, aad);
    });
  }

  context({ project, contact, limit = 50 } = {}) {
    let events = this.events();
    if (project) events = events.filter((event) => event.projects.includes(project));
    if (contact) events = events.filter((event) => event.contacts.includes(contact));
    events = events.slice(-Math.max(1, Math.min(Number(limit) || 50, 200)));
    const open = [];
    const resolved = new Set();
    for (const event of events) {
      for (const item of event.commitments) {
        if (!item || !item.id) continue;
        if (item.status === 'done' || item.status === 'cancelled') resolved.add(item.id);
        else open.push({ ...item, event_id: event.event_id, occurred_at: event.occurred_at });
      }
    }
    return Object.freeze({
      schema: 'reddog.context_packet.v1',
      principal_digest: this.principal_digest,
      generated_at: new Date().toISOString(),
      event_count: events.length,
      recent_events: events,
      open_commitments: open.filter((item) => !resolved.has(item.id))
    });
  }
}

module.exports = Object.freeze({ SCHEMA, PrincipalActivityLedger, principalDigest, ledgerPath });
