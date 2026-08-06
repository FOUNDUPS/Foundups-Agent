'use strict';

const SECRET_KEY = 'reddog.principalMemex.disclosure.v2';
const DISCLOSURE_SCHEMA = 'reddog_principal_memex_disclosure.v2';
const SUPPLY_FIELDS = Object.freeze([
  'conversation_id',
  'expected_conversation_revision',
  'serialized_disclosure'
]);
const DISCLOSURE_FIELDS = Object.freeze([
  'audience', 'conversation_id', 'conversation_record_digest',
  'conversation_revision', 'credential_id', 'decision_item_ids',
  'disclosure_id', 'expires_at', 'grounding_receipt_id', 'intent_id',
  'issued_at', 'model_runtime_binding_digest',
  'model_runtime_binding_receipt_id', 'nonce', 'principal_id',
  'principal_provider', 'purpose', 'repo_full_name', 'runtime_surface',
  'schema_version', 'sensitivity', 'session_binding_digest', 'session_id',
  'signature', 'transport'
]);
const SHA256_RE = /^sha256:[0-9a-f]{64}$/;
const MAX_STORED_BYTES = 16384;
const MAX_DISCLOSURE_BYTES = 12288;
let operationTail = Promise.resolve();

async function serialized(operation) {
  const previous = operationTail;
  let release;
  operationTail = new Promise((resolve) => { release = resolve; });
  await previous.catch(() => {});
  try {
    return await operation();
  } finally {
    release();
  }
}

function parseSupply(value) {
  if (typeof value !== 'string' || !value || Buffer.byteLength(value, 'utf8') > MAX_STORED_BYTES
      || !/^[\x20-\x7e]+$/.test(value)) return null;
  try {
    const supply = JSON.parse(value);
    if (!exactKeys(supply, SUPPLY_FIELDS)
        || !SHA256_RE.test(supply.conversation_id)
        || !Number.isSafeInteger(supply.expected_conversation_revision)
        || supply.expected_conversation_revision < 0
        || !validDisclosure(supply.serialized_disclosure)) return null;
    return {
      serialized_disclosure: supply.serialized_disclosure,
      conversation_id: supply.conversation_id,
      expected_conversation_revision: supply.expected_conversation_revision
    };
  } catch (_error) {
    return null;
  }
}

function validDisclosure(serialized) {
  if (typeof serialized !== 'string' || !serialized
      || Buffer.byteLength(serialized, 'ascii') > MAX_DISCLOSURE_BYTES
      || !/^[\x20-\x7e]+$/.test(serialized)) return false;
  try {
    const disclosure = JSON.parse(serialized);
    return exactKeys(disclosure, DISCLOSURE_FIELDS)
      && disclosure.schema_version === DISCLOSURE_SCHEMA
      && SHA256_RE.test(disclosure.disclosure_id)
      && Array.isArray(disclosure.decision_item_ids)
      && disclosure.decision_item_ids.length > 0;
  } catch (_error) {
    return false;
  }
}

function exactKeys(value, expected) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return false;
  const keys = Object.keys(value).sort();
  return keys.length === expected.length
    && keys.every((key, index) => key === [...expected].sort()[index]);
}

async function take(secretStorage) {
  return serialized(() => takeExclusive(secretStorage));
}

async function takeExclusive(secretStorage) {
  if (!secretStorage || typeof secretStorage.get !== 'function'
      || typeof secretStorage.delete !== 'function') {
    return { supply: null, reason: 'principal_memex_secret_storage_unavailable' };
  }
  const stored = await secretStorage.get(SECRET_KEY);
  if (!stored) return { supply: null, reason: '' };
  await secretStorage.delete(SECRET_KEY);
  const supply = parseSupply(stored);
  return supply
    ? { supply, reason: '' }
    : { supply: null, reason: 'principal_memex_source_supply_invalid' };
}

async function invokeStored(secretStorage, invoke) {
  return serialized(() => invokeStoredExclusive(secretStorage, invoke));
}

async function invokeStoredExclusive(secretStorage, invoke) {
  if (!secretStorage || typeof secretStorage.get !== 'function'
      || typeof secretStorage.delete !== 'function'
      || typeof invoke !== 'function') {
    return { value: null, reason: 'principal_memex_secret_storage_unavailable' };
  }
  const stored = await secretStorage.get(SECRET_KEY);
  if (!stored) return { value: await invoke(null), reason: '' };
  if (typeof secretStorage.store !== 'function') {
    return { value: null, reason: 'principal_memex_secret_storage_unavailable' };
  }
  await secretStorage.delete(SECRET_KEY);
  const supply = parseSupply(stored);
  if (!supply) return { value: null, reason: 'principal_memex_source_supply_invalid' };
  try {
    const value = await invoke(supply);
    if (value && value.principal_memex_source_consumed === false) {
      await secretStorage.store(SECRET_KEY, stored);
    }
    return { value, reason: '' };
  } catch (error) {
    throw error;
  }
}

async function runConfigured(input) {
  const sessionOptions = {
    explicitResidentArchitectSessionRequested: true,
    groundingPreflight: input.options.groundingPreflight,
    holoScorecard: input.options.holoScorecard,
    authenticatedPrincipal: input.claims.principalId,
    authorizedFoundupIds: input.claims.foundupScope,
    conversationSessionCredential: input.credential
  };
  const payloadResult = input.buildPayload(input.workFocus, sessionOptions);
  if (!payloadResult.ok) {
    const reasons = Array.isArray(payloadResult.rejection_reasons)
      ? payloadResult.rejection_reasons : ['resident_architect_session_preflight_failed'];
    return input.skip(reasons[0], reasons);
  }
  const invoked = await invokeStored(
    input.secretStorage,
    (supply) => input.invoke(
      input.workFocus,
      Object.assign(sessionOptions, { principalMemexSourceSupply: supply })
    )
  );
  return invoked.reason ? input.skip(invoked.reason) : invoked.value;
}

function bridgePayload(payload, sessionCredential, principalMemexSupply) {
  const value = Object.assign({}, payload, {
    conversation_session_credential: sessionCredential
  });
  if (principalMemexSupply && typeof principalMemexSupply === 'object') {
    value.principal_memex_source_supply = principalMemexSupply;
  }
  return value;
}

async function storeFromPrompt(vscode, secretStorage) {
  if (!vscode || !vscode.window || typeof vscode.window.showInputBox !== 'function'
      || !secretStorage || typeof secretStorage.store !== 'function') {
    return { stored: false, reason: 'principal_memex_secret_storage_unavailable' };
  }
  const packet = await vscode.window.showInputBox({
    title: 'RedDog Principal Memex Disclosure',
    prompt: 'Enter one pre-issued principal-signed Principal Memex disclosure packet.',
    password: true,
    ignoreFocusOut: true,
    validateInput: (value) => parseSupply(value)
      ? undefined
      : 'A valid Principal Memex disclosure packet is required.'
  });
  if (packet === undefined) {
    return { stored: false, reason: 'principal_memex_source_cancelled' };
  }
  if (!parseSupply(packet)) {
    return { stored: false, reason: 'principal_memex_source_supply_invalid' };
  }
  await serialized(() => secretStorage.store(SECRET_KEY, packet));
  return { stored: true, reason: '' };
}

async function clear(secretStorage) {
  return serialized(() => clearExclusive(secretStorage));
}

async function clearExclusive(secretStorage) {
  if (!secretStorage || typeof secretStorage.delete !== 'function') {
    return { cleared: false, reason: 'principal_memex_secret_storage_unavailable' };
  }
  await secretStorage.delete(SECRET_KEY);
  return { cleared: true, reason: '' };
}

function registerCommands(vscode, context) {
  return [
    vscode.commands.registerCommand('reddog.setPrincipalMemexDisclosure', async () => {
      const result = await storeFromPrompt(vscode, context.secrets);
      if (result.stored) {
        vscode.window.showInformationMessage('One-use Principal Memex disclosure stored securely.');
      } else if (result.reason !== 'principal_memex_source_cancelled') {
        vscode.window.showWarningMessage('Principal Memex disclosure was not stored.');
      }
    }),
    vscode.commands.registerCommand('reddog.clearPrincipalMemexDisclosure', async () => {
      const result = await clear(context.secrets);
      if (result.cleared) {
        vscode.window.showInformationMessage('Principal Memex disclosure cleared.');
      }
    })
  ];
}

module.exports = {
  DISCLOSURE_SCHEMA,
  SECRET_KEY,
  bridgePayload,
  clear,
  invokeStored,
  parseSupply,
  registerCommands,
  runConfigured,
  storeFromPrompt,
  take,
  validDisclosure
};
