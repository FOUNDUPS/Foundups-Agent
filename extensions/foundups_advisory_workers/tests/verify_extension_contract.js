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

assert.strictEqual(pkg.version, '0.3.15', 'package version must be 0.3.15');
includes(readme, 'Version: 0.3.15', 'README version mismatch');
includes(extensionJs, "const EXTENSION_VERSION = '0.3.15'", 'extension build mismatch');

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
includes(extensionJs, 'Skillz/Wardrobe/Rolodex discovery', 'Skillz/Rolodex discovery context missing');

includes(bridgePy, 'evaluate_redaction_gate(prompt, context_for_gate)', 'prompt/context redaction gate missing');
includes(bridgePy, 'redacted_user_message = gate.redacted_prompt', 'redacted user assembly missing');
includes(bridgePy, 'messages = [{"role": "system", "content": _system_prompt(payload)}]', 'Fusion alias system prompt missing');
includes(bridgePy, 'base_system = _system_prompt(payload)', 'manual panel system prompt missing');
includes(bridgePy, 'GLM_PRINCIPAL_MODEL = "z-ai/glm-5.2"', 'bridge GLM principal missing');
includes(bridgePy, 'DEEPSEEK_CRITIC_MODEL = "deepseek/deepseek-v4-pro"', 'bridge DeepSeek V4 critic missing');

includes(iface, 'SPECIFIED_NOT_IMPLEMENTED', 'interface truth boundary missing');
includes(iface, 'WSP_15 Priority', 'interface priority contract missing');
includes(roadmap, 'REDDOG_FOUNDUP_INTAKE_PACKET_MODE_PHASE1', 'FoundUp intake roadmap missing');

includes(extensionJs, 'function classifyTaskForRedDog', 'auto effort classifier missing');
includes(extensionJs, 'function resolveAutoEffort', 'resolveAutoEffort missing');
includes(extensionJs, 'function resolveAutoContextMode', 'resolveAutoContextMode missing');
includes(extensionJs, 'function resolveModelMode', 'resolveModelMode missing');
includes(extensionJs, 'function validateRedDogOutput', 'validateRedDogOutput missing');
includes(extensionJs, 'function buildRepairPrompt', 'buildRepairPrompt missing');
includes(extensionJs, 'output_validation', 'review packet validator status missing');
includes(extensionJs, 'Do not invent evidence', 'repair prompt evidence guard missing');
includes(extensionJs, 'function modeSelectionReasoning', 'mode selection reasoning missing');
includes(extensionJs, 'Architect Trace', 'architect trace schema missing');
includes(extensionJs, 'Verification gaps', 'verification gaps schema missing');
includes(extensionJs, "mode === 'wsp_holo_skillz' || mode === 'wsp_holo_git_skillz'", 'skillz context wiring in buildBoundedRepoContext missing');
includes(extensionJs, 'mode_selection_reasoning', 'review packet mode selection reasoning missing');
includes(readme, 'WSP_97 Truth Table', 'README WSP_97 truth table missing');
includes(roadmap, 'REDDOG_GOVERNED_HANDOFF_CONTRACT_PHASE1', 'governed handoff roadmap slice missing');
includes(roadmap, 'REDDOG_PFMALL_SURFACE_BINDING_PHASE1', 'pfMALL binding roadmap slice missing');
includes(roadmap, 'REDDOG_REVIEW_PACKET_MEMORY_PHASE1', 'review packet memory roadmap slice missing');
includes(extensionJs, 'function constructWspTaskPrompt', 'constructWspTaskPrompt missing');
includes(extensionJs, 'function redactedDigest', 'redactedDigest missing');
includes(extensionJs, '0102_generated_from_work_focus', 'prompt construction marker missing');
includes(extensionJs, 'work_focus_digest', 'work focus digest in review packet missing');
includes(extensionJs, 'wsp_prompt_digest', 'wsp prompt digest in review packet missing');
includes(extensionJs, 'id="workFocus"', 'work focus composer missing');
includes(extensionJs, '012 work focus', '012 work focus label missing');
assert(!extensionJs.includes('012 prompt'), 'legacy 012 prompt label must be removed');
includes(readme, 'Work Focus Contract', 'README work focus contract missing');
includes(iface, '012 Work Focus to 0102 WSP Task Prompt', 'INTERFACE work focus contract missing');
includes(roadmap, 'REDDOG_BRIDGE_HARDENING_PHASE1', 'bridge hardening roadmap slice missing');
includes(extensionJs, 'Routing: Auto via WSP_15', 'auto routing label missing');
includes(extensionJs, 'deepseek/deepseek-v4-pro', 'DeepSeek V4 Pro critic default missing');
includes(extensionJs, 'z-ai/glm-5.2', 'GLM 5.2 principal default missing');
includes(extensionJs, 'openrouter_fusion_alias', 'OpenRouter Fusion alias path must remain implemented');
assert(!extensionJs.includes('<select id="mode"'), 'Mode must not be a 012-facing dropdown');
assert(!extensionJs.includes('<select id="contextMode"'), 'Context must not be a 012-facing dropdown');
assert(!extensionJs.includes('<select id="effort"'), 'Effort must not be a 012-facing dropdown');

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

const ultra = orchestrator.classifyTaskForRedDog('Audit OAuth auth secrets on live runtime deploy path', 'auto', 'reddog_architect');
assert.strictEqual(ultra.tier, 'ULTRA', 'security/auth prompts must classify ULTRA');

const wsp = orchestrator.classifyTaskForRedDog('Review WSP protocol architecture and HoloIndex gap', 'auto', 'wsp_gate_critic');
assert(wsp.tier === 'HIGH' || wsp.tier === 'ULTRA', 'WSP/architecture prompts must classify HIGH or ULTRA');

const regular = orchestrator.classifyTaskForRedDog('Reply with exactly: regular mode works', 'auto', 'smoke_tester');
assert.strictEqual(regular.tier, 'REGULAR', 'simple smoke prompts must classify REGULAR');

assert.strictEqual(
  orchestrator.resolveModelMode(wsp, 'auto', 'reddog_architect'),
  'foundups_fusion',
  'RedDog WSP work must auto-route to auditable manual panel'
);
assert.strictEqual(
  orchestrator.resolveModelMode(wsp, 'openrouter_fusion_alias', 'reddog_architect'),
  'openrouter_fusion_alias',
  'OpenRouter Fusion alias must remain available as an explicit path'
);
assert.strictEqual(
  orchestrator.resolveModelMode(regular, 'auto', 'smoke_tester'),
  'openrouter_single',
  'Regular smoke work must auto-route to single-model mode'
);

assert.strictEqual(orchestrator.resolveAutoEffort(ultra, 'auto'), 'ultra', 'auto effort must map ULTRA classification to ultra');
assert.strictEqual(orchestrator.resolveAutoContextMode(ultra, 'auto'), 'wsp_holo_git_skillz', 'ULTRA must attach WSP/Holo/git/Skillz context');
assert.strictEqual(orchestrator.resolveAutoContextMode(wsp, 'auto'), 'wsp_holo_skillz', 'HIGH/WSP must attach WSP/Holo/Skillz context');
assert.strictEqual(orchestrator.resolveAutoContextMode(regular, 'auto'), 'none', 'REGULAR smoke must avoid repo context');
assert.strictEqual(orchestrator.resolveAutoEffort(regular, 'auto'), 'regular', 'auto effort must map REGULAR classification to regular');

const reasoning = orchestrator.modeSelectionReasoning(wsp, 'high', 'foundups_fusion', 'wsp_holo_skillz');
includes(reasoning, 'Fusion manual panel', 'mode selection reasoning must explain Fusion path');
includes(reasoning, 'wsp_holo_skillz', 'mode selection reasoning must cite resolved context');

const singleReasoning = orchestrator.modeSelectionReasoning(regular, 'regular', 'openrouter_single', 'none');
includes(singleReasoning, 'Single-model GLM', 'mode selection reasoning must explain single-model path');

const architectBad = 'Decision\nFindings\nEvidence\nProposed fixes\nUncertainties\nWSP_97 Truth Labels\nWSP_15 Priority\nNext safest step';
const architectValidation = orchestrator.validateRedDogOutput(architectBad, { substantiveArchitect: true, mode: 'openrouter_single' });
assert.strictEqual(architectValidation.valid, false, 'architect validator must require Architect Trace and Verification gaps');
assert(architectValidation.missingSections.includes('Architect Trace'), 'architect validator must list Architect Trace');

const fusionBad = architectBad + '\nArchitect Trace\nVerification gaps';
const fusionValidation = orchestrator.validateRedDogOutput(fusionBad, { substantiveArchitect: true, mode: 'foundups_fusion' });
assert.strictEqual(fusionValidation.valid, false, 'fusion validator must require Lead/Synthesis structure');
assert(fusionValidation.missingSections.some((s) => /Fusion panel/i.test(s)), 'fusion validator must flag missing panel structure');

const badOutput = 'Decision\nFindings\nEvidence';
const validation = orchestrator.validateRedDogOutput(badOutput);
assert.strictEqual(validation.valid, false, 'validator must detect missing sections');
assert(validation.missingSections.includes('Proposed fixes'), 'validator must list missing Proposed fixes');

const repairPrompt = orchestrator.buildRepairPrompt('task', badOutput, validation.missingSections);
includes(repairPrompt, 'Do not invent evidence', 'repair prompt must forbid invented evidence');
includes(repairPrompt, 'preserve the existing answer content', 'repair prompt must be bounded');

const handoffContext = orchestrator.skillzWardrobeRolodexContext(root, 'process all youtube comments with existing skillz', 12000);
includes(handoffContext, 'Skillz/Wardrobe/Rolodex discovery', 'handoff context header missing');
assert(/youtube|comments|skillz/i.test(handoffContext), 'handoff context must surface relevant YouTube/comment/Skillz paths');
assert(!handoffContext.includes('(no matching Skillz/Wardrobe/Rolodex paths found'), 'handoff context must not be empty for YouTube comments');

const ytFocus = 'process all youtube comments with existing skillz';
const ytClass = orchestrator.classifyTaskForRedDog(ytFocus, 'auto', 'reddog_architect');
const ytWsp = orchestrator.constructWspTaskPrompt(ytFocus, ytClass, 'HoloIndex ok', 'reddog_architect');
includes(ytWsp, 'WSP_97', 'WSP prompt must include WSP_97 framing');
includes(ytWsp, 'WSP_15 tier', 'WSP prompt must include tier');
includes(ytWsp, ytFocus.slice(0, 40), 'WSP prompt must embed work focus excerpt');
includes(ytWsp, 'non-authoritative', 'WSP prompt must label work focus non-authoritative');

const digest = orchestrator.redactedDigest('process youtube comments', 80);
assert.strictEqual(typeof digest.hash, 'string', 'digest hash required');
assert.strictEqual(typeof digest.excerpt, 'string', 'digest excerpt required');
assert(digest.excerpt.includes('youtube'), 'digest excerpt must reflect input');

console.log('FoundUps Fusion extension contract checks passed.');
