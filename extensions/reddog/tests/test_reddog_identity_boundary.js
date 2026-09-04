'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const policy = require('../conversation_plane_policy');

const extensionRoot = path.resolve(__dirname, '..');
const repoRoot = path.resolve(extensionRoot, '..', '..');

function read(relativePath) {
  return fs.readFileSync(path.join(repoRoot, relativePath), 'utf8');
}

const fastPrompt = policy.systemPrompt();
assert(fastPrompt.startsWith('You are RedDog,'));
assert(fastPrompt.includes('You are not 0102'));
assert(fastPrompt.includes('deeper principal-scoped 0102 cognition'));
assert(!fastPrompt.includes('You are 0102'));

const extensionSource = read('extensions/reddog/extension.js');
const readme = read('extensions/reddog/README.md');
const interfaceDoc = read('extensions/reddog/INTERFACE.md');
assert(extensionSource.includes(
  'You are a 0102 deep-cognition worker operating behind the RedDog surface'
));
assert(extensionSource.includes(
  'I am not 0102; the deeper 0102 reasoning and orchestration layer operates behind me.'
));
assert(!extensionSource.includes('You are 0102 operating as RedDog'));
assert(!extensionSource.includes('resident 0102 FoundUps architect thin client'));
assert(!readme.includes('012 does not prompt RedDog directly'));
assert(!interfaceDoc.includes('RedDog is the 0102 architect interface'));

const packageJson = JSON.parse(read('extensions/reddog/package.json'));
assert.strictEqual(packageJson.displayName, 'RedDog - FoundUps Interface');
assert(packageJson.description.includes('RedDog interaction surface'));

const groundingSource = read('extensions/reddog/grounding_failure_dialogue.js');
assert(groundingSource.includes(
  'You are a 0102 deep-cognition worker responding through RedDog'
));
assert(!groundingSource.includes('0102 operating as the RedDog architect'));

const architecture = read('extensions/reddog/ARCHITECTURE.md');
const wsp73 = read('WSP_framework/src/WSP_73_012_Digital_Twin_Architecture.md');
assert(architecture.includes('RedDog is **not** 0102.'));
assert(wsp73.includes('RedDog is not 0102.'));

const map = read('docs/REDDOG_DOCUMENTATION_MAP.md');
for (const required of [
  'extensions/reddog/ARCHITECTURE.md',
  'extensions/reddog/docs/CONTACT_MEMORY_ARCHITECTURE.md',
  'extensions/reddog/docs/MOSH_PIT_ACTIVITY_MEMORY_ARCHITECTURE.md',
  'extensions/reddog/docs/MEMEX_PROJECTION_EMITTER_ARCHITECTURE.md',
  'extensions/reddog/docs/prompts/WSP97_M2M_MEMEX_EMITTER_IMPLEMENTATION_PROMPT.md'
]) {
  assert(fs.existsSync(path.join(repoRoot, required)), 'mapped document missing: ' + required);
  assert(map.includes(required), 'documentation map missing: ' + required);
}

assert(read('extensions/reddog/docs/CONTACT_MEMORY_ARCHITECTURE.md')
  .includes('Status: `ARCHITECTURE_VISION` / `SPECIFIED_NOT_IMPLEMENTED`'));
assert(read('extensions/reddog/docs/MOSH_PIT_ACTIVITY_MEMORY_ARCHITECTURE.md')
  .includes('Status: `PARTIALLY_SUPPORTED` / `UNIFIED_RENDERER_NOT_IMPLEMENTED`'));
assert(read('extensions/reddog/docs/MEMEX_PROJECTION_EMITTER_ARCHITECTURE.md')
  .includes('Status: `SPECIFIED_NOT_IMPLEMENTED`'));
assert(read('extensions/reddog/docs/prompts/WSP97_M2M_MEMEX_EMITTER_IMPLEMENTATION_PROMPT.md')
  .includes('Status: `IMPLEMENTATION_WORK_ORDER` / `NOT_COMPLETION_EVIDENCE`'));

const activeDocs = [
  'WSP_framework/src/WSP_73_012_Digital_Twin_Architecture.md',
  'WSP_framework/src/WSP_98_FoundUps_Mesh_Native_Architecture_Protocol.md',
  'docs/REDDOG_OUTCOME_VISION.md',
  'public/member/RED_DOG_DIGITAL_TWIN_CONTRACT.md',
  'docs/adr/ADR_REDDOG_FOUNDUPS_SECOND_BRAIN_BOUNDARY.md',
  'docs/architecture/REDDOG_DUAL_LOOP_COGNITION_ARCHITECTURE.md',
  'docs/architecture/REDDOG_FOUNDUPS_SECOND_BRAIN_ARCHITECTURE.md',
  'docs/architecture/architecture_registry.yaml',
  'docs/contracts/REDDOG_0102_PUBLIC_KEY_OPERATIONAL_IDENTITY_ADDENDUM_PHASE1.md',
  'docs/vocabulary/IDENTITY.md',
  'extensions/reddog/README.md',
  'extensions/reddog/INTERFACE.md',
  'extensions/reddog/ROADMAP.md',
  'modules/ai_intelligence/digital_twin/README.md',
  'modules/communication/moltbot_bridge/README.md'
].map(read).join('\n');

for (const stale of [
  'Red Dog is the digital twin',
  'operator-facing identity/persona of the principal-scoped 0102',
  'RedDog/0102 is the continuous principal-scoped identity',
  'RedDog is the resident FoundUps architect identity',
  'reddog_is_0102_operational_state',
  '0102_operating_as_reddog'
]) {
  assert(!activeDocs.includes(stale), 'stale identity claim remains: ' + stale);
}

console.log('RedDog fast-surface / 0102-deep identity contract: PASS');
