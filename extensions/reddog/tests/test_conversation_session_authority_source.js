'use strict';

const assert = require('assert');
const source = require('../conversation_session_authority_source');

async function main() {
  const values = new Map();
  const storage = {
    get: async (key) => values.get(key),
    store: async (key, value) => values.set(key, value),
    delete: async (key) => values.delete(key)
  };
  const credential = JSON.stringify({
    schema_version: source.CREDENTIAL_SCHEMA,
    principal_id: 'principal_012',
    foundup_scope: ['foundups_agent', 'trade']
  });
  const vscode = {
    window: {
      showInputBox: async (options) => {
        assert.strictEqual(options.password, true);
        assert.strictEqual(options.validateInput(credential), undefined);
        return credential;
      }
    }
  };

  const stored = await source.storeFromPrompt(vscode, storage);
  assert.strictEqual(stored.stored, true);
  assert.strictEqual(await source.read(storage), credential);
  assert.deepStrictEqual(source.credentialClaims(credential), {
    principalId: 'principal_012',
    foundupScope: ['foundups_agent', 'trade']
  });

  const env = source.buildBridgeEnvironment({
    OPENROUTER_API_KEY: 'synthetic-openrouter-key',
    FOUNDUPS_INTAKE_HMAC_SECRET: 'synthetic-hmac-secret',
    REDDOG_SIGNER_SYSTEM_SERVICE_OWNER_CONFIG_PATH: 'O:/runtime/owner.json',
    UNRELATED_SECRET: 'must-not-cross'
  });
  assert.strictEqual(env.REDDOG_CONVERSATION_SESSION_TOKEN, undefined);
  assert.strictEqual(env.FOUNDUPS_INTAKE_HMAC_SECRET, undefined);
  assert.strictEqual(env.REDDOG_SIGNER_SYSTEM_SERVICE_OWNER_CONFIG_PATH, 'O:/runtime/owner.json');
  assert.strictEqual(env.UNRELATED_SECRET, undefined);

  const cleared = await source.clear(storage);
  assert.strictEqual(cleared.cleared, true);
  assert.strictEqual(await source.read(storage), '');
  assert.strictEqual(source.validSessionCredential('not-a-session-credential'), false);
}

main().then(
  () => console.log('RedDog conversation session authority source checks passed.'),
  (error) => {
    console.error(error);
    process.exitCode = 1;
  }
);
