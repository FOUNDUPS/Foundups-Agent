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

assert.strictEqual(pkg.version, '0.3.19', 'package version must be 0.3.19');
includes(extensionJs, "const EXTENSION_VERSION = '0.3.19'", 'extension build mismatch');
assert.strictEqual(pkg.name, 'foundups-fusion-worker', 'package id must remain stable in branding slice');
assert.strictEqual(pkg.displayName, 'Foundups®Agent', 'display name must be Foundups®Agent');
includes(JSON.stringify(pkg), 'Foundups®Agent: Open', 'command title must use Foundups®Agent');
includes(extensionJs, "title: 'Foundups®Agent'", 'webview title must use Foundups®Agent');
includes(readme, 'Foundups®Agent is the product surface', 'README product identity statement missing');
includes(iface, 'Fusion is one internal reasoning mode, not the product identity', 'INTERFACE mode identity statement missing');
includes(roadmap, 'Foundups®Agent is the product surface', 'ROADMAP product identity statement missing');
includes(extensionJs, 'id="reddogWorkingTrail"', 'working trail DOM missing');
includes(extensionJs, 'data-reddog-pixel', 'trail pixel attribute missing');
includes(extensionJs, "command: 'progress'", 'progress command shape missing');
includes(extensionJs, 'Stopped before OpenRouter. Nothing left the machine.', 'redaction operator message missing');
assert(!extensionJs.includes("command: 'status', stage"), 'status must not carry stage field');
includes(extensionJs, 'REDDOG_STAGE_ACTIONS', 'structured stage map missing');
includes(extensionJs, 'REDDOG_PROGRESS_ACTIONS', 'progress regex fallback missing');
includes(extensionJs, 'function matchReddogProgress', 'matchReddogProgress missing');
includes(extensionJs, 'function formatElapsed', 'formatElapsed missing');
includes(readme, 'Version: 0.3.19', 'README version mismatch');
includes(extensionJs, 'function resolvePythonInterpreter', 'python resolver missing');
includes(extensionJs, 'function applyBridgeContextBudget', 'context budget missing');
includes(extensionJs, 'function killBridgeChild', 'orphan cleanup missing');
includes(extensionJs, 'output_cap_exceeded', 'output cap failure reason missing');
includes(extensionJs, 'bridge_meta', 'bridge metadata payload missing');
includes(bridgePy, 'MAX_PANEL_MODELS = 6', 'panel cap missing in bridge');
includes(bridgePy, 'RETRYABLE_HTTP_STATUS', 'retryable status set missing');
includes(bridgePy, 'reason="missing_key"', 'missing_key taxonomy missing');

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

const ytFocus = 'process youtube comments';
const ytClass = orchestrator.classifyTaskForRedDog(ytFocus, 'auto', 'reddog_architect');
const ytWsp = orchestrator.constructWspTaskPrompt(ytFocus, ytClass, 'HoloIndex ok', 'reddog_architect');
includes(ytWsp, 'WSP_00', 'WSP prompt must include WSP_00 operating frame');
includes(ytWsp, 'WSP_97', 'WSP prompt must include WSP_97 truth boundary');
includes(ytWsp, 'WSP_15 tier', 'WSP prompt must include WSP_15 tier/routing');
includes(ytWsp, ytFocus, 'WSP prompt must embed bounded work focus excerpt');
includes(ytWsp, '012 work focus (non-authoritative input)', 'WSP prompt must declare non-authoritative input');
assert.notStrictEqual(ytWsp.trim(), ytFocus.trim(), 'raw work focus must not bypass constructWspTaskPrompt');
assert(ytWsp.length > ytFocus.length + 50, 'WSP task prompt must wrap work focus with 0102 contract framing');

const longFocus = 'process youtube comments '.repeat(200);
const focusDigest = orchestrator.redactedDigest(longFocus, 180);
assert.strictEqual(typeof focusDigest.hash, 'string', 'digest hash required');
assert(focusDigest.excerpt.length <= 180, 'digest excerpt must be bounded');
assert(!Object.prototype.hasOwnProperty.call(focusDigest, 'raw'), 'digest must not store raw full focus');
assert(focusDigest.length === longFocus.length, 'digest length metadata may exceed excerpt');

const wspDigest = orchestrator.redactedDigest(ytWsp, 320);
assert(wspDigest.excerpt.length <= 320, 'wsp prompt digest excerpt must be bounded');

function extractBridgeStages(source) {
  const stages = [];
  const re = /_progress\("([^"]+)"/g;
  let match;
  while ((match = re.exec(source)) !== null) {
    stages.push(match[1]);
  }
  return [...new Set(stages)].sort();
}

const bridgeStages = extractBridgeStages(bridgePy);
const mappedStages = Object.keys(orchestrator.REDDOG_STAGE_ACTIONS).sort();
assert.deepStrictEqual(mappedStages, bridgeStages, 'REDDOG_STAGE_ACTIONS must cover every advisory bridge stage');
assert.strictEqual(bridgeStages.length, 16, 'expected 16 unique bridge stages');
assert.strictEqual(orchestrator.REDDOG_TERMINAL_HOLD_MS, 3000, 'terminal hold must be 3000ms');

const redactionMatch = orchestrator.matchReddogProgress({ stage: 'redaction_blocked', text: 'Redaction gate blocked before network.' });
assert.strictEqual(redactionMatch.action, 'barking', 'redaction_blocked must map to barking');
assert.strictEqual(redactionMatch.pixel, '!rd!', 'redaction_blocked must use barking pixel');

const successMatch = orchestrator.matchReddogProgress({ stage: 'single_done', text: 'Regular OpenRouter response received: x' });
assert.strictEqual(successMatch.action, 'pointing', 'single_done must map to pointing');
assert.strictEqual(successMatch.pixel, '>rd>', 'single_done must use pointing pixel');

const failureMatch = orchestrator.matchReddogProgress({ stage: 'panel_blocked', text: 'Panel blocked: x' });
assert.strictEqual(failureMatch.action, 'sitting', 'panel_blocked must map to sitting');
assert.strictEqual(failureMatch.pixel, '.rd.', 'panel_blocked must use sitting pixel');

const diggingMatch = orchestrator.matchReddogProgress({ stage: null, text: 'Output schema incomplete. Missing: Architect Trace. Running one repair pass...' });
assert.strictEqual(diggingMatch.action, 'digging', 'repair pass text must map to digging');

const sniffMatch = orchestrator.matchReddogProgress({ stage: null, text: 'Work focus sent. 0102 will assemble WSP task prompt...' });
assert.strictEqual(sniffMatch.action, 'sniffing', 'work focus sent must map to sniffing');

assert.strictEqual(orchestrator.formatElapsed(45000), '45s', 'formatElapsed under 60s');
assert.strictEqual(orchestrator.formatElapsed(62000), '1m02s', 'formatElapsed above 60s');

const blocked = orchestrator.enrichRedactionBlockResult({ ok: false, reason: 'redaction_blocked' });
assert.strictEqual(blocked.review_packet.made_network_call, false, 'redaction block must set made_network_call=false');
assert.strictEqual(blocked.review_packet.retry_count, 0, 'redaction block must set retry_count=0');
assert.strictEqual(orchestrator.REDACTION_BLOCK_OPERATOR_MESSAGE, 'Stopped before OpenRouter. Nothing left the machine.', 'operator message constant');

const forbiddenPixels = ['\u2022', '\u0254', '\u1401', '\u1400'];
for (const glyph of forbiddenPixels) {
  assert(!extensionJs.includes(glyph), 'trail pixel grammar must stay ASCII-only');
}

const budget = orchestrator.applyBridgeContextBudget('p'.repeat(20000), 'c'.repeat(60000));
assert.strictEqual(budget.budget.truncation_applied, true, 'context budget must truncate oversized prompt/context');
assert(budget.prompt.length <= orchestrator.BRIDGE_MAX_PROMPT_CHARS, 'prompt must respect cap');
assert(budget.context.length <= orchestrator.BRIDGE_MAX_CONTEXT_CHARS, 'context must respect cap');

const interpreter = orchestrator.resolvePythonInterpreter(root, 'python');
includes(interpreter.path, 'python', 'python resolver must return a path');
includes(interpreter.source, 'system', 'default python must fall back to system when no configured path');

console.log('Foundups®Agent extension contract checks passed.');
