'use strict';
const assert = require('assert');
const crypto = require('crypto');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawn, spawnSync } = require('child_process');
const { PrincipalActivityLedger, ledgerPath, withRootLock } = require('../principal_activity_ledger');

if (process.argv[2] === '--hold-lock') {
  withRootLock(process.argv[3], () => {
    process.stdout.write('locked\n');
    const deadline = Date.now() + 5000;
    while (!fs.existsSync(process.argv[4])) {
      if (Date.now() > deadline) throw new Error('fixture release timeout');
      Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 10);
    }
  });
  process.exit(0);
}
if (process.argv[2] === '--append-child') {
  try {
    new PrincipalActivityLedger({ rootDir: process.argv[3], principalId: 'fixture', key: Buffer.alloc(32, 7) })
      .append({ notes: 'synthetic child event' });
    process.exit(0);
  } catch (error) { process.exit(error.code === 'EEXIST' ? 2 : 3); }
}

const root = fs.mkdtempSync(path.join(os.tmpdir(), 'reddog-pal-'));
try {
  const key = crypto.randomBytes(32);
  const ledger = new PrincipalActivityLedger({ rootDir: root, principalId: '012', key });
  ledger.append({ kind: 'meeting', projects: ['YUMORI.me'], contacts: ['Sano'], notes: 'private onsen meeting', commitments: [{ id: 'send-03', status: 'open', text: 'send 03' }] });
  ledger.append({ kind: 'email', projects: ['YUMORI.me'], notes: 'sent mayor package', commitments: [{ id: 'send-03', status: 'done' }] });
  const disk = fs.readFileSync(ledgerPath(root, '012'), 'utf8');
  assert(!disk.includes('private onsen meeting'));
  assert(!disk.includes('Sano'));
  assert(!disk.includes('YUMORI.me'));
  assert(!disk.includes(key.toString('hex')));
  const events = ledger.events();
  assert.strictEqual(events.length, 2);
  assert.strictEqual(events[0].contacts[0], 'Sano');
  const context = ledger.context({ project: 'YUMORI.me' });
  assert.strictEqual(context.event_count, 2);
  assert.strictEqual(context.open_commitments.length, 0);

  const other = new PrincipalActivityLedger({ rootDir: root, principalId: '099', key });
  assert.strictEqual(other.events().length, 0);
  assert.notStrictEqual(ledger.file, other.file);

  const lines = disk.trim().split(/\r?\n/);
  const first = JSON.parse(lines[0]);
  first.ciphertext = first.ciphertext.slice(0, -2) + 'AA';
  fs.writeFileSync(ledger.file, JSON.stringify(first) + '\n' + lines.slice(1).join('\n') + '\n');
  assert.throws(() => ledger.events(), /tampered|chain mismatch/);
  console.log('RedDog principal activity ledger contracts: PASS');
} finally {
  fs.rmSync(root, { recursive: true, force: true });
}

async function proveRepairBoundaries() {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'reddog-pal-repair-'));
  const key = Buffer.alloc(32, 7); // Synthetic fixture only; never a host key.
  function ledger(name) { return new PrincipalActivityLedger({ rootDir: path.join(temp, name), principalId: 'fixture', key }); }
  try {
    const wrong = ledger('wrong-key');
    wrong.append({ notes: 'original' });
    const before = fs.readFileSync(wrong.file);
    const foreign = new PrincipalActivityLedger({ rootDir: wrong.rootDir, principalId: 'fixture', key: Buffer.alloc(32, 8) });
    assert.throws(() => foreign.append({ notes: 'must not append' }));
    assert.deepStrictEqual(fs.readFileSync(wrong.file), before);
    const otherKey = new PrincipalActivityLedger({ rootDir: wrong.rootDir, principalId: 'different', key: Buffer.alloc(32, 8) });
    assert.throws(() => otherKey.append({ notes: 'must not mix keys across principals' }));
    assert.strictEqual(fs.existsSync(otherKey.file), false);
    assert.deepStrictEqual(fs.readFileSync(wrong.file), before);

    const cyclic = {}; cyclic.self = cyclic;
    for (const [index, facts] of [{ value: undefined }, { value: () => {} }, { value: Symbol('fixture') },
      { value: BigInt(1) }, { value: NaN }, { value: Infinity }, { value: [, 1] }, cyclic].entries()) {
      const target = ledger('json-' + index);
      assert.throws(() => target.append({ facts }), /json_invalid/);
      assert.strictEqual(fs.existsSync(target.rootDir), false, 'invalid payload must not create storage');
    }

    const complete = ledger('complete-write');
    const originalWrite = fs.writeSync;
    let shortWrites = 0;
    fs.writeSync = (fd, buffer, offset, length, position) => {
      shortWrites += 1;
      return originalWrite(fd, buffer, offset, Math.min(length, 13), position);
    };
    try { complete.append({ notes: 'unicode fixture \u65e5\u672c' }); } finally { fs.writeSync = originalWrite; }
    assert(shortWrites > 1);
    assert.strictEqual(complete.events()[0].notes, 'unicode fixture \u65e5\u672c');

    for (const [index, bad] of [0, -1, NaN, 0.5, Infinity, Number.MAX_SAFE_INTEGER].entries()) {
      const target = ledger('bad-count-' + index);
      fs.writeSync = () => bad;
      try { assert.throws(() => target.append({ notes: 'no receipt' }), /append_incomplete/); }
      finally { fs.writeSync = originalWrite; }
      assert.throws(() => target.append({ notes: 'must not repair empty file' }), /file_empty/);
    }
    const partial = ledger('partial');
    let writes = 0;
    fs.writeSync = (fd, buffer, offset, length, position) => {
      if (writes++) throw new Error('injected write failure');
      return originalWrite(fd, buffer, offset, 9, position);
    };
    try { assert.throws(() => partial.append({ notes: 'partial' }), /injected/); }
    finally { fs.writeSync = originalWrite; }
    const partialBytes = fs.readFileSync(partial.file);
    assert(partialBytes.length > 0);
    assert.throws(() => partial.append({ notes: 'must not repair silently' }));
    assert.deepStrictEqual(fs.readFileSync(partial.file), partialBytes);

    const sync = ledger('fsync');
    const originalSync = fs.fsyncSync;
    fs.fsyncSync = () => { throw new Error('injected fsync failure'); };
    try { assert.throws(() => sync.append({ notes: 'uncertain durability' }), /injected/); }
    finally { fs.fsyncSync = originalSync; }
    const close = ledger('close');
    const originalClose = fs.closeSync;
    let closed = false;
    fs.closeSync = (fd) => {
      originalClose(fd);
      if (!closed) { closed = true; throw new Error('injected close failure'); }
    };
    try { assert.throws(() => close.append({ notes: 'no receipt' }), /injected/); }
    finally { fs.closeSync = originalClose; }

    // Every owned descriptor closes on failed lock metadata/cleanup. Never
    // remove an unverified or replacement lock, or turn uncertainty into success.
    const originalFstat = fs.fstatSync;
    const originalLstat = fs.lstatSync;
    for (const mode of ['acquire-stat', 'release-stat', 'release-close', 'replacement']) {
      const lockRoot = path.join(temp, 'lock-' + mode);
      const lock = path.join(lockRoot, '.principal-activity.lock');
      let closes = 0;
      fs.closeSync = (fd) => {
        closes += 1; originalClose(fd);
        if (mode === 'release-close') throw new Error('injected lock close');
      };
      if (mode === 'acquire-stat') fs.fstatSync = () => { throw new Error('injected lock stat'); };
      if (mode === 'release-stat') fs.lstatSync = () => { throw new Error('injected lock lstat'); };
      try {
        assert.throws(() => withRootLock(lockRoot, () => {
          if (mode === 'replacement') {
            fs.renameSync(lock, lock + '.original');
            fs.writeFileSync(lock, 'replacement fixture');
          }
          return 'must not succeed';
        }), /injected|lock_changed/);
      } finally { fs.closeSync = originalClose; fs.fstatSync = originalFstat; fs.lstatSync = originalLstat; }
      assert.strictEqual(closes, 1, 'owned lock descriptor must close exactly once');
      assert.strictEqual(fs.existsSync(lock), true, 'uncertain lock must remain for inspection');
      if (mode === 'replacement') assert.strictEqual(fs.readFileSync(lock, 'utf8'), 'replacement fixture');
    }

    const projection = ledger('projection');
    projection.append({ occurred_at: '9999', contacts: ['contact'], projects: ['project'], commitments: [{ id: 'task', status: 'open' }] });
    projection.append({ occurred_at: '0000', commitments: [{ id: 'task', status: 'done' }] });
    assert.strictEqual(projection.context({ contact: 'contact', project: 'project', limit: 1 }).open_commitments.length, 0);
    projection.append({ occurred_at: '0000', commitments: [{ id: 'task', status: 'open', text: 'reopened' }] });
    projection.append({ contacts: ['contact'], projects: ['project'], notes: 'later unrelated event' });
    const packet = projection.context({ contact: 'contact', project: 'project', limit: 1 });
    assert.strictEqual(packet.recent_events.length, 1);
    assert.strictEqual(packet.open_commitments.length, 1);
    assert.strictEqual(packet.open_commitments[0].text, 'reopened');
    projection.append({ commitments: [{ id: 'task', status: 'cancelled' }] });
    assert.strictEqual(projection.context({ contact: 'contact' }).open_commitments.length, 0);
    projection.append({ contacts: ['contact'], commitments: [
      { id: 'task', status: 'open', text: 'old duplicate' },
      { id: 'task', status: 'open', text: 'latest duplicate' },
      { id: 'second', status: 'open' }, { id: 'third', status: 'open' }
    ] });
    const bounded = projection.context({ contact: 'contact', limit: 2 });
    assert.strictEqual(bounded.open_commitment_count, 3);
    assert.strictEqual(bounded.open_commitments_truncated, true);
    assert.deepStrictEqual(bounded.open_commitments.map((item) => item.id), ['second', 'third']);
    const allOpen = projection.context({ contact: 'contact' });
    assert.strictEqual(allOpen.open_commitments_truncated, false);
    assert.strictEqual(allOpen.open_commitments.filter((item) => item.id === 'task').length, 1);
    assert.strictEqual(allOpen.open_commitments[0].text, 'latest duplicate');

    const contended = ledger('process');
    contended.append({ notes: 'parent' });
    const release = path.join(temp, 'release');
    const holder = spawn(process.execPath, [__filename, '--hold-lock', contended.rootDir, release], { stdio: ['ignore', 'pipe', 'pipe'] });
    const exited = new Promise((resolve, reject) => { holder.once('error', reject); holder.once('exit', resolve); });
    try {
      await new Promise((resolve, reject) => {
        const timer = setTimeout(() => reject(new Error('fixture lock timeout')), 3000);
        holder.stdout.once('data', () => { clearTimeout(timer); resolve(); });
        holder.once('error', (error) => { clearTimeout(timer); reject(error); });
      });
      const contender = spawnSync(process.execPath, [__filename, '--append-child', contended.rootDir], { timeout: 3000 });
      assert.strictEqual(contender.status, 2, 'independent child must reject the held lock');
    } finally { fs.writeFileSync(release, 'release'); }
    assert.strictEqual(await exited, 0);
    assert.strictEqual(spawnSync(process.execPath, [__filename, '--append-child', contended.rootDir], { timeout: 3000 }).status, 0);
    assert.strictEqual(contended.events().length, 2);
    const stale = path.join(contended.rootDir, '.principal-activity.lock');
    fs.writeFileSync(stale, 'stale fixture');
    assert.throws(() => contended.append({ notes: 'blocked' }), { code: 'EEXIST' });
    assert.strictEqual(fs.readFileSync(stale, 'utf8'), 'stale fixture');
    fs.unlinkSync(stale);
    assert.strictEqual(contended.events().length, 2);
    console.log('RedDog PAL repair boundaries: PASS (synthetic storage and real child contention)');
  } finally { fs.rmSync(temp, { recursive: true, force: true }); }
}
proveRepairBoundaries().catch((error) => { console.error(error.message); process.exitCode = 1; });
