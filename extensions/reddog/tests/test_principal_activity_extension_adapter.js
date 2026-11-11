'use strict';

const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const adapter = require('../principal_activity_extension_adapter');
const { ledgerPath, withRootLock } = require('../principal_activity_ledger');
const { spawnSync } = require('child_process');

if (process.argv[2] === '--key-contender') {
  adapter.ensureKey({ async get() { throw new Error('must not read during contention'); }, async store() {} }, process.argv[3])
    .then(() => { process.exitCode = 3; }, (error) => { process.exitCode = error.code === 'EEXIST' ? 2 : 3; });
} else if (require.main === module) {
  run().catch((error) => { console.error(error.message); process.exitCode = 1; });
}

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
    const key = await adapter.ensureKey(context.secrets, adapter.rootDir(context));
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
    const first = await adapter.ensureKey(context.secrets, adapter.rootDir(context));
    const second = await adapter.ensureKey(context.secrets, adapter.rootDir(context));
    assert(first.equals(second), 'same device secret must reopen encrypted continuity');
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
}

async function run() {
  await proveKeyLivesOnlyInSecretStorage();
  await provePrincipalIsolationAndProjection();
  await proveKeyIsStableAcrossOpenings();
  await proveRepairBoundaries();
  console.log('RedDog principal activity extension adapter contracts: PASS');
}

async function proveRepairBoundaries() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'reddog-pal-key-repair-'));
  try {
    const context = fakeContext(root);
    const scoped = adapter.rootDir(context);
    await assert.rejects(adapter.ensureKey(context.secrets), /scope_required/);
    await assert.rejects(adapter.ensureKey(context.secrets, 'relative'), /scope_required/);
    let stores = 0;
    const store = context.secrets.store;
    context.secrets.store = async (...args) => { stores += 1; await store(...args); };
    const keys = await Promise.all(Array.from({ length: 8 }, () => adapter.ensureKey(context.secrets, scoped)));
    assert(keys.every((key) => key.equals(keys[0])));
    assert.strictEqual(stores, 1);
    const receipts = await Promise.all(Array.from({ length: 8 }, (_, i) => adapter.append(context, { notes: 'synthetic ' + i })));
    assert.deepStrictEqual(receipts.map((item) => item.sequence), [1, 2, 3, 4, 5, 6, 7, 8]);
    assert.strictEqual((await adapter.status(context)).event_count, 8);

    await withRootLock(scoped, async () => {
      const contender = spawnSync(process.execPath, [__filename, '--key-contender', scoped], { timeout: 3000 });
      assert.strictEqual(contender.status, 2, 'independent key initializer must reject a held root lock');
    });
    const file = ledgerPath(scoped, '012');
    const before = fs.readFileSync(file);
    context.secrets.values.clear();
    await assert.rejects(adapter.append(context, { notes: 'blocked' }, 'different-principal'), /missing_for_existing_data/);
    assert.strictEqual(stores, 1);
    assert.deepStrictEqual(fs.readFileSync(file), before);
    context.secrets.values.set(adapter.KEY_SECRET, Buffer.alloc(32, 3).toString('base64'));
    await assert.rejects(adapter.append(context, { notes: 'wrong key' }, 'different-principal'));
    assert.deepStrictEqual(fs.readFileSync(file), before);
    context.secrets.values.set(adapter.KEY_SECRET, 'invalid fixture');
    await assert.rejects(adapter.status(context), /key_invalid/);
    context.secrets.values.set(adapter.KEY_SECRET, keys[0].toString('base64'));
    assert.strictEqual((await adapter.status(context)).event_count, 8);

    for (const [index, contents] of ['', '{partial'].entries()) {
      const partial = fakeContext(path.join(root, 'partial-' + index));
      const partialRoot = adapter.rootDir(partial);
      const partialFile = ledgerPath(partialRoot, '012');
      fs.mkdirSync(path.dirname(partialFile)); fs.writeFileSync(partialFile, contents);
      await assert.rejects(adapter.append(partial, { notes: 'blocked' }), /missing_for_existing_data/);
      assert.strictEqual(partial.secrets.values.size, 0);
      assert.strictEqual(fs.readFileSync(partialFile, 'utf8'), contents);
    }
    for (const mode of ['get', 'store', 'unconfirmed']) {
      const failure = fakeContext(path.join(root, 'failure-' + mode));
      if (mode === 'get') failure.secrets.get = async () => { throw new Error('injected get failure'); };
      else if (mode === 'store') failure.secrets.store = async () => { throw new Error('injected store failure'); };
      else failure.secrets.store = async () => {};
      await assert.rejects(adapter.append(failure, { notes: 'no success' }));
      assert.strictEqual(fs.existsSync(ledgerPath(adapter.rootDir(failure), '012')), false);
    }
    const poison = fakeContext(path.join(root, 'poison'));
    await assert.rejects(adapter.append(poison, { facts: { invalid: undefined } }), /json_invalid/);
    assert.strictEqual(poison.secrets.values.size, 0);
    assert.strictEqual(fs.existsSync(poison.globalStorageUri.fsPath), false);

    const source = { schema: 'reddog.context_packet.v1', recent_events: [{ notes: 'a'.repeat(550) }, { notes: 'b'.repeat(550) }], open_commitments: [] };
    const packet = adapter.boundContextPacket(source, 1000);
    assert.strictEqual(packet.recent_events.length, 1);
    assert.strictEqual(packet.truncated, true);
    assert.strictEqual(source.recent_events.length, 2);
    assert(Buffer.byteLength(JSON.stringify(packet), 'utf8') <= 1000);
    const noDrop = adapter.boundContextPacket({ recent_events: [{ notes: 'small' }], open_commitments: [] }, 1000);
    assert.strictEqual(noDrop.truncated, false);
    const capped = adapter.boundContextPacket({ recent_events: [], open_commitments: [{ id: 'last' }],
      open_commitment_count: 2, open_commitments_truncated: true }, 1000);
    assert.strictEqual(capped.truncated, true);
    assert.strictEqual(capped.open_commitment_count, 2);
    assert.strictEqual(capped.open_commitments_truncated, true);
    // Include metadata in sizing: the payload alone can fit while the final
    // truncation fields put it over the limit. Test both sides of that boundary.
    for (const size of [770, 780, 790, 800, 810, 820]) {
      const edge = adapter.boundContextPacket({ recent_events: [{ notes: 'x'.repeat(size) }], open_commitments: [] }, 1000);
      assert(Buffer.byteLength(JSON.stringify(edge), 'utf8') <= 1000);
      assert.strictEqual(edge.truncated, edge.recent_events.length === 0);
    }
    console.log('RedDog PAL adapter repair boundaries: PASS (scoped synthetic secrets)');
  } finally { fs.rmSync(root, { recursive: true, force: true }); }
}

module.exports = { run };
