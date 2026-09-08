'use strict';

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const { PrincipalActivityLedger, principalDigest } = require('./principal_activity_ledger');

const KEY_SECRET = 'reddog.principalActivity.key.v1';
const STORAGE_SUBDIR = 'principal-activity-ledger';
const DEFAULT_PRINCIPAL = '012';
const CONTEXT_EVENT_LIMIT = 50;
const CONTEXT_CHAR_LIMIT = 12000;

function principalId(value) {
  const text = String(value || DEFAULT_PRINCIPAL).trim();
  if (!text || text.length > 128) throw new Error('principal_activity_principal_invalid');
  return text;
}

function rootDir(context) {
  if (!context || !context.globalStorageUri || !context.globalStorageUri.fsPath) {
    throw new Error('principal_activity_local_storage_unavailable');
  }
  const root = path.join(path.resolve(context.globalStorageUri.fsPath), STORAGE_SUBDIR);
  fs.mkdirSync(root, { recursive: true, mode: 0o700 });
  return root;
}

async function ensureKey(secretStorage) {
  if (!secretStorage || typeof secretStorage.get !== 'function'
      || typeof secretStorage.store !== 'function') {
    throw new Error('principal_activity_secret_storage_unavailable');
  }
  const stored = await secretStorage.get(KEY_SECRET);
  if (stored) {
    const key = Buffer.from(String(stored), 'base64');
    if (key.length !== 32) throw new Error('principal_activity_key_invalid');
    return key;
  }
  const key = crypto.randomBytes(32);
  await secretStorage.store(KEY_SECRET, key.toString('base64'));
  return key;
}

async function openLedger(context, requestedPrincipal) {
  const id = principalId(requestedPrincipal);
  const key = await ensureKey(context && context.secrets);
  return new PrincipalActivityLedger({ rootDir: rootDir(context), principalId: id, key });
}

function normalizeStringList(value, maxItems = 32, maxChars = 180) {
  if (!Array.isArray(value)) return [];
  const seen = new Set();
  const out = [];
  for (const item of value) {
    const text = String(item || '').trim().slice(0, maxChars);
    if (!text || seen.has(text)) continue;
    seen.add(text);
    out.push(text);
    if (out.length >= maxItems) break;
  }
  return out;
}

function normalizeCommitments(value) {
  if (!Array.isArray(value)) return [];
  return value.slice(0, 32).map((item) => {
    const source = item && typeof item === 'object' ? item : {};
    const id = String(source.id || '').trim().slice(0, 160);
    if (!id) return null;
    return {
      id,
      status: String(source.status || 'open').trim().slice(0, 32),
      owner: String(source.owner || '').trim().slice(0, 128),
      due_at: source.due_at ? String(source.due_at).trim().slice(0, 64) : '',
      text: String(source.text || '').trim().slice(0, 1000)
    };
  }).filter(Boolean);
}

function normalizeEvent(event) {
  const source = event && typeof event === 'object' ? event : {};
  const facts = source.facts && typeof source.facts === 'object' && !Array.isArray(source.facts)
    ? source.facts : {};
  return {
    event_id: source.event_id ? String(source.event_id).slice(0, 160) : undefined,
    occurred_at: source.occurred_at ? String(source.occurred_at).slice(0, 64) : undefined,
    kind: String(source.kind || 'activity').slice(0, 64),
    source: String(source.source || 'reddog_extension').slice(0, 96),
    projects: normalizeStringList(source.projects),
    contacts: normalizeStringList(source.contacts),
    commitments: normalizeCommitments(source.commitments),
    evidence_refs: normalizeStringList(source.evidence_refs, 64, 300),
    facts,
    notes: String(source.notes || '').slice(0, 12000)
  };
}

async function append(context, event, requestedPrincipal) {
  const ledger = await openLedger(context, requestedPrincipal);
  return ledger.append(normalizeEvent(event));
}

function boundContextPacket(packet, maxChars) {
  const limit = Math.max(1000, Math.min(Number(maxChars) || CONTEXT_CHAR_LIMIT, 32000));
  const source = packet && typeof packet === 'object' ? packet : {};
  const events = Array.isArray(source.recent_events) ? source.recent_events.slice() : [];
  const open = Array.isArray(source.open_commitments) ? source.open_commitments.slice() : [];
  const base = {
    schema: source.schema,
    principal_digest: source.principal_digest,
    generated_at: source.generated_at,
    event_count: source.event_count,
    recent_events: events,
    open_commitments: open,
    local_only: true,
    disclosure_authority: 'separate_required'
  };
  while (Buffer.byteLength(JSON.stringify(base), 'utf8') > limit && base.recent_events.length > 1) {
    base.recent_events.shift();
  }
  while (Buffer.byteLength(JSON.stringify(base), 'utf8') > limit && base.open_commitments.length > 1) {
    base.open_commitments.shift();
  }
  if (Buffer.byteLength(JSON.stringify(base), 'utf8') > limit) {
    base.recent_events = [];
    base.open_commitments = [];
    base.truncated = true;
  } else {
    base.truncated = base.recent_events.length !== events.length || base.open_commitments.length !== open.length;
  }
  return Object.freeze(base);
}

async function contextPacket(context, options, requestedPrincipal) {
  const opts = options && typeof options === 'object' ? options : {};
  const ledger = await openLedger(context, requestedPrincipal);
  const packet = ledger.context({
    project: opts.project ? String(opts.project).slice(0, 180) : undefined,
    contact: opts.contact ? String(opts.contact).slice(0, 180) : undefined,
    limit: Math.max(1, Math.min(Number(opts.limit) || CONTEXT_EVENT_LIMIT, 200))
  });
  return boundContextPacket(packet, opts.maxChars);
}

async function status(context, requestedPrincipal) {
  const id = principalId(requestedPrincipal);
  const ledger = await openLedger(context, id);
  const events = ledger.events();
  return Object.freeze({
    principal_digest: principalDigest(id),
    event_count: events.length,
    storage: 'local_extension_global_storage',
    encrypted_at_rest: true,
    key_storage: 'vscode_secret_storage',
    network_transport: false
  });
}

async function captureFromPrompt(vscode, context) {
  if (!vscode || !vscode.window || typeof vscode.window.showInputBox !== 'function') {
    return { captured: false, reason: 'principal_activity_ui_unavailable' };
  }
  const note = await vscode.window.showInputBox({
    title: 'RedDog Principal Activity',
    prompt: 'Capture a meeting, decision, promise, contact note, or other activity for 012. Stored locally and encrypted.',
    ignoreFocusOut: true
  });
  if (note === undefined) return { captured: false, reason: 'principal_activity_capture_cancelled' };
  if (!String(note).trim()) return { captured: false, reason: 'principal_activity_capture_empty' };
  const receipt = await append(context, {
    kind: 'manual_note', source: 'reddog_command', notes: String(note).trim()
  });
  return { captured: true, receipt };
}

function registerCommands(vscode, context) {
  return [
    vscode.commands.registerCommand('reddog.capturePrincipalActivity', async () => {
      try {
        const result = await captureFromPrompt(vscode, context);
        if (result.captured) vscode.window.showInformationMessage('RedDog activity captured locally.');
        else if (result.reason !== 'principal_activity_capture_cancelled') {
          vscode.window.showWarningMessage('RedDog activity was not captured: ' + result.reason);
        }
      } catch (error) {
        vscode.window.showWarningMessage('RedDog activity capture failed closed.');
      }
    }),
    vscode.commands.registerCommand('reddog.showPrincipalActivityContext', async () => {
      try {
        const packet = await contextPacket(context, { limit: 50, maxChars: CONTEXT_CHAR_LIMIT });
        const document = await vscode.workspace.openTextDocument({
          language: 'json', content: JSON.stringify(packet, null, 2)
        });
        await vscode.window.showTextDocument(document, { preview: true });
      } catch (error) {
        vscode.window.showWarningMessage('RedDog local activity context is unavailable.');
      }
    }),
    vscode.commands.registerCommand('reddog.principalActivityStatus', async () => {
      try {
        const value = await status(context);
        vscode.window.showInformationMessage(
          'RedDog local activity: ' + value.event_count + ' events; encrypted; no network transport.'
        );
      } catch (error) {
        vscode.window.showWarningMessage('RedDog local activity status is unavailable.');
      }
    })
  ];
}

module.exports = Object.freeze({
  KEY_SECRET,
  STORAGE_SUBDIR,
  DEFAULT_PRINCIPAL,
  append,
  boundContextPacket,
  captureFromPrompt,
  contextPacket,
  ensureKey,
  normalizeEvent,
  openLedger,
  registerCommands,
  rootDir,
  status
});
