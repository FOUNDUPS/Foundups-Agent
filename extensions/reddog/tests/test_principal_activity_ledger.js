'use strict';
const assert = require('assert');
const crypto = require('crypto');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { PrincipalActivityLedger, ledgerPath } = require('../principal_activity_ledger');

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
  assert(!disk.includes(key.toString('hex'));
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
