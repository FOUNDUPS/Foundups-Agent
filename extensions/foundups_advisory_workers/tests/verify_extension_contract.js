const fs = require('fs');
const path = require('path');
const assert = require('assert');
const Module = require('module');

const root = path.resolve(__dirname, '..', '..', '..');
const extDir = path.join(root, 'extensions', 'foundups_advisory_workers');
const extensionJs = fs.readFileSync(path.join(extDir, 'extension.js'), 'utf8');
const bridgePy = fs.readFileSync(path.join(root, 'scripts', 'advisory_model_once.py'), 'utf8');
const pkg = JSON.parse(fs.readFileSync(path.join(extDir, 'package.json'), 'utf8'));
const readme = fs.readFileSync(path.join(extDir, 'README.md'), 'utf8');
const iface = fs.readFileSync(path.join(extDir, 'INTERFACE.md'), 'utf8');
const roadmap = fs.readFileSync(path.join(extDir, 'ROADMAP.md'), 'utf8');

function includes(haystack, needle, label) {
  assert(haystack.includes(needle), label || `missing ${needle}`);
}

assert.strictEqual(pkg.version, '0.3.13', 'package version must be 0.3.13');
includes(readme, 'Version: 0.3.13', 'README version mismatch');
includes(extensionJs, "const EXTENSION_VERSION = '0.3.13'", 'extension build mismatch');

includes(extensionJs, 'grid-template-rows: auto minmax(0, 1fr) auto', 'terminal/chat grid rows missing');
includes(extensionJs, 'html, body { height: 100%; overflow: hidden; }', 'body overflow lock missing');
includes(extensionJs, '#log { min-height: 0; overflow-y: auto;', 'scrollback output contract missing');
assert(extensionJs.indexOf('<main id="log"') < extensionJs.indexOf('<form id="form">'), 'output must precede bottom composer');
assert(!extensionJs.includes('>Send<'), 'Send button should not exist');
assert(!extensionJs.includes('>Clear<'), 'Clear button should not exist');

includes(extensionJs, 'RedDog Architect', 'RedDog Architect worker missing');
includes(extensionJs, 'WSP_15', 'WSP_15 requirement missing');
includes(extensionJs, 'WSP_97', 'WSP_97 requirement missing');
includes(extensionJs, 'Every finding must include a proposed fix', 'proposed-fix contract missing');
includes(extensionJs, 'HOLO_SKIP_MODEL', 'HoloIndex fastpath env missing');
includes(extensionJs, '--bundle-json', 'bundle-json retrieval missing');
includes(extensionJs, '--offline', 'offline fallback missing');

includes(bridgePy, 'evaluate_redaction_gate(prompt, context_for_gate)', 'prompt/context redaction gate missing');
includes(bridgePy, 'redacted_user_message = gate.redacted_prompt', 'redacted user assembly missing');
includes(bridgePy, 'messages = [{"role": "system", "content": _system_prompt(payload)}]', 'Fusion alias system prompt missing');
includes(bridgePy, 'base_system = _system_prompt(payload)', 'manual panel system prompt missing');

includes(iface, 'SPECIFIED_NOT_IMPLEMENTED', 'interface truth boundary missing');
includes(iface, 'WSP_15 Priority', 'interface priority contract missing');
includes(roadmap, 'REDDOG_FOUNDUP_INTAKE_PACKET_MODE_PHASE1', 'FoundUp intake roadmap missing');

includes(extensionJs, 'function classifyTaskForRedDog', 'auto effort classifier missing');
includes(extensionJs, 'function resolveAutoEffort', 'resolveAutoEffort missing');
includes(extensionJs, 'function resolveModelMode', 'resolveModelMode missing');
includes(extensionJs, 'function validateRedDogOutput', 'validateRedDogOutput missing');
includes(extensionJs, 'function buildRepairPrompt', 'buildRepairPrompt missing');
includes(extensionJs, 'output_validation', 'review packet validator status missing');
includes(extensionJs, 'Do not invent evidence', 'repair prompt evidence guard missing');
includes(extensionJs, 'RedDog WSP default', 'RedDog WSP default mode label missing');
includes(extensionJs, 'openrouter_fusion_alias', 'OpenRouter Fusion alias option must remain selectable');

const vscodeMock = {
  window: {
    activeTextEditor: null,
    visibleTextEditors: [],
    createWebviewPanel: () => ({ webview: { onDidReceiveMessage: () => ({ dispose() {} }), asWebviewUri: () => ({ toString: () => '' }) }, dispose() {} })
  },
  workspace: {
    workspaceFolders: [{ uri: { fsPath: root } }],
    getConfiguration: () => ({ get: (_key, fallback) => fallback })
  },
  commands: { registerCommand: () => ({ dispose() {} }) },
  env: { clipboard: { writeText: async () => {} } },
  Uri: { joinPath: (_base, _name) => ({ fsPath: path.join(extDir, 'icon.png') }) },
  ViewColumn: { Beside: 2 }
};
const vscodePath = path.join(extDir, 'node_modules', 'vscode', 'index.js');
require.cache[vscodePath] = { exports: vscodeMock, loaded: true, id: vscodePath };
const originalResolve = Module._resolveFilename;
Module._resolveFilename = function(request, parent, isMain, options) {
  if (request === 'vscode') {
    return vscodePath;
  }
  return originalResolve.call(this, request, parent, isMain, options);
};

const orchestrator = require(path.join(extDir, 'extension.js'));
Module._resolveFilename = originalResolve;

const ultra = orchestrator.classifyTaskForRedDog('Audit OAuth auth secrets on live runtime deploy path', 'wsp_holo_git', 'reddog_architect');
assert.strictEqual(ultra.tier, 'ULTRA', 'security/auth prompts must classify ULTRA');

const wsp = orchestrator.classifyTaskForRedDog('Review WSP protocol architecture and HoloIndex gap', 'wsp_holo', 'wsp_gate_critic');
assert(wsp.tier === 'HIGH' || wsp.tier === 'ULTRA', 'WSP/architecture prompts must classify HIGH or ULTRA');

const regular = orchestrator.classifyTaskForRedDog('Reply with exactly: regular mode works', 'none', 'smoke_tester');
assert.strictEqual(regular.tier, 'REGULAR', 'simple smoke prompts must classify REGULAR');

assert.strictEqual(
  orchestrator.resolveModelMode(wsp, 'foundups_fusion', 'reddog_architect'),
  'foundups_fusion',
  'RedDog WSP work must default to auditable manual panel'
);
assert.strictEqual(
  orchestrator.resolveModelMode(wsp, 'openrouter_fusion_alias', 'reddog_architect'),
  'openrouter_fusion_alias',
  'OpenRouter Fusion alias must remain selectable'
);

assert.strictEqual(orchestrator.resolveAutoEffort(ultra, 'auto'), 'ultra', 'auto effort must map ULTRA classification to ultra');
assert.strictEqual(orchestrator.resolveAutoEffort(regular, 'auto'), 'regular', 'auto effort must map REGULAR classification to regular');

const badOutput = 'Decision\nFindings\nEvidence';
const validation = orchestrator.validateRedDogOutput(badOutput);
assert.strictEqual(validation.valid, false, 'validator must detect missing sections');
assert(validation.missingSections.includes('Proposed fixes'), 'validator must list missing Proposed fixes');

const repairPrompt = orchestrator.buildRepairPrompt('task', badOutput, validation.missingSections);
includes(repairPrompt, 'Do not invent evidence', 'repair prompt must forbid invented evidence');
includes(repairPrompt, 'preserve the existing answer content', 'repair prompt must be bounded');

console.log('FoundUps Fusion extension contract checks passed.');
