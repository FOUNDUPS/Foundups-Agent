'use strict';

const startOperationsEnvironment = require('./start_operations_environment');

const SECRET_KEY = 'reddog.conversation.sessionCredential.v1';
const CREDENTIAL_SCHEMA = 'reddog_conversation_session_credential.v1';
const AUTHORITY_ENV_KEYS = Object.freeze([
  'REDDOG_SIGNER_SYSTEM_SERVICE_OWNER_CONFIG_PATH'
]);

function credentialClaims(value) {
  if (typeof value !== 'string' || !value || value.length > 8192 || !/^[\x20-\x7e]+$/.test(value)) {
    return null;
  }
  try {
    const parsed = JSON.parse(value);
    const scope = parsed && parsed.foundup_scope;
    if (parsed.schema_version !== CREDENTIAL_SCHEMA
        || typeof parsed.principal_id !== 'string' || !parsed.principal_id
        || !Array.isArray(scope) || !scope.length
        || scope.some((item) => typeof item !== 'string' || !item)) return null;
    return { principalId: parsed.principal_id, foundupScope: [...scope] };
  } catch (_error) {
    return null;
  }
}

function validSessionCredential(value) {
  return credentialClaims(value) !== null;
}

async function read(secretStorage) {
  if (!secretStorage || typeof secretStorage.get !== 'function') return '';
  const credential = await secretStorage.get(SECRET_KEY);
  return validSessionCredential(credential) ? credential : '';
}

async function storeFromPrompt(vscode, secretStorage) {
  if (!vscode || !vscode.window || typeof vscode.window.showInputBox !== 'function'
      || !secretStorage || typeof secretStorage.store !== 'function') {
    return { stored: false, reason: 'conversation_session_secret_storage_unavailable' };
  }
  const credential = await vscode.window.showInputBox({
    title: 'RedDog Conversation Session',
    prompt: 'Enter a pre-issued principal-signed RedDog conversation credential.',
    password: true,
    ignoreFocusOut: true,
    validateInput: (value) => validSessionCredential(value) ? undefined : 'A valid signed conversation credential is required.'
  });
  if (credential === undefined) return { stored: false, reason: 'conversation_session_source_cancelled' };
  if (!validSessionCredential(credential)) return { stored: false, reason: 'conversation_session_credential_invalid' };
  await secretStorage.store(SECRET_KEY, credential);
  return { stored: true, reason: '' };
}

async function clear(secretStorage) {
  if (!secretStorage || typeof secretStorage.delete !== 'function') {
    return { cleared: false, reason: 'conversation_session_secret_storage_unavailable' };
  }
  await secretStorage.delete(SECRET_KEY);
  return { cleared: true, reason: '' };
}

function buildBridgeEnvironment(source) {
  return startOperationsEnvironment.buildBridge(source, 'resident_architect');
}

module.exports = {
  AUTHORITY_ENV_KEYS,
  CREDENTIAL_SCHEMA,
  SECRET_KEY,
  buildBridgeEnvironment,
  clear,
  credentialClaims,
  read,
  storeFromPrompt,
  validSessionCredential
};
