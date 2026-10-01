'use strict';

const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const adapter = require('../principal_activity_extension_adapter');
const { ledgerPath } = require('../principal_activity_ledger');

function fakeSecrets() {
  const values = new Map();
  return {
    async get(key) { return values.get(key); },
    async store(key, value) { values.set(key, value); },
    async delete(key) { values.delete(key); },
    values
  };
}

function fakeContext(root) {
  return { globalStorageUri: { fsPath: root }, secrets: fakeSecrets() };
}

async function proveKeyLivesOnlyInSecretStorage() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'reddog-pal-adapter-'));
  try {
    const context = fakeContext(root);
    const key = await adapter.ensureKey(context.secrets);
    assert.strictEqual(key.length, 32);
    assert.strictEqual(context.secrets.values.has(adapter.KEY_SECRET), true);
    await adapter.append(context, { kind: 'meeting', notes: '012 met Governor office contact' });
    const files = [];
    function walk(dir) {
      for (const name of fs.readdirSync(dir)) {
        const target = path.join(dir, name);
        const stat = fs.statSync(target);
        if (stat.isDirectory()) walk(target); else files.push(target);
      }
    }
    walk(root);
    const bytes = files.map((file) => fs.readFileSync(file)).reduce((n, value) => n + value.length, 0);
    assert(bytes > 0, 'encrypted ledger should exist on local storage');
    const disk = Buffer.concat(files.map((file) => fs.readFileSync(file))).toString('utf8');
    assert(!disk.includes(key.toString('base64')), 'key must not persist beside ledger');
    assert(!disk.includes('Governor office contact'), 'plaintext activity must not persist');
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
}

async function provePrincipalIsolationAndProjection() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'reddog-pal-context-'));
  try {
    const context = fakeContext(root);
    await adapter.append(context, {
      kind: 'commitment', projects: ['YUMORI.me'], contacts: ['Mayor'],
      commitments: [{ id: 'send-03', owner: '012', text: 'Send 03', status: 'open' }],
      notes: 'prepare evidence package'
    }, '012');
    await adapter.append(context, {
      kind: 'commitment_update', projects: ['YUMORI.me'],
      commitments: [{ id: 'send-03', owner: '012', text: 'Send 03', status: 'done' }],
      notes: 'sent'
    }, '012');
    await adapter.append(context, { kind: 'note', projects: ['other'], notes: 'separate principal' }, 'other-principal');

    const packet = await adapter.contextPacket(context, { project: 'YUMORI.me', maxChars: 4000 }, '012');
    assert.strictEqual(packet.schema, 'reddog.context_packet.v1');
    assert.strictEqual(packet.local_only, true);
    assert.strictEqual(packet.disclosure_authority, 'separate_required');
    assert.strictEqual(packet.recent_events.length, 2);
    assert.strictEqual(packet.open_commitments.length, 0, 'resolved commitments should close');
    assert(Buffer.byteLength(JSON.stringify(packet), 'utf8') <= 4000);

    assert.notStrictEqual(
      ledgerPath(path.join(root, adapter.STORAGE_SUBDIR), '012'),
      ledgerPath(path.join(root, adapter.STORAGE_SUBDIR), 'other-principal')
    );
    const status = await adapter.status(context, '012');
    assert.strictEqual(status.event_count, 2);
    assert.strictEqual(status.encrypted_at_rest, true);
    assert.strictEqual(status.network_transport, false);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
}

async function proveKeyIsStableAcrossOpenings() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'reddog-pal-key-'));
  try {
    const context = fakeContext(root);
    const first = await adapter.ensureKey(context.secrets);
    const second = await adapter.ensureKey(context.secrets);
    assert(first.equals(second), 'same device secret must reopen encrypted continuity');
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
}

async function run() {
  await proveKeyLivesOnlyInSecretStorage();
  await provePrincipalIsolationAndProjection();
  await proveKeyIsStableAcrossOpenings();
  console.log('RedDog principal activity extension adapter contracts: PASS');
}

if (require.main === module) {
  run().catch((error) => {
    console.error(error && error.stack || error);
    process.exitCode = 1;
  });
}

module.exports = { run };
