'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const extensionSource = fs.readFileSync(path.join(root, 'extension.js'), 'utf8');
const disclosureSource = fs.readFileSync(path.join(root, 'principal_memex_disclosure_source.js'), 'utf8');
const packageJson = JSON.parse(fs.readFileSync(path.join(root, 'package.json'), 'utf8'));

assert(extensionSource.includes("require('./principal_memex_disclosure_source')"),
  'RedDog activation must retain the principal Memex registration seam');
assert(extensionSource.includes('...principalMemexDisclosureSource.registerCommands(vscode, context)'),
  'RedDog activation must register the principal continuity command bundle');
assert(disclosureSource.includes("require('./principal_activity_extension_adapter')"),
  'principal continuity seam must bind the activity adapter');
assert(disclosureSource.includes('...principalActivityExtensionAdapter.registerCommands(vscode, context)'),
  'principal continuity seam must register PAL commands');

for (const command of [
  'reddog.capturePrincipalActivity',
  'reddog.showPrincipalActivityContext',
  'reddog.principalActivityStatus'
]) {
  assert(packageJson.activationEvents.includes(`onCommand:${command}`),
    `package activation missing ${command}`);
  assert(packageJson.contributes.commands.some((entry) => entry.command === command),
    `package command contribution missing ${command}`);
}

console.log('RedDog principal activity runtime registration contracts: PASS');
