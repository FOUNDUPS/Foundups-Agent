/**
 * Shared contract-test fixtures. Reuse in verify_extension_contract.js and future
 * RedDog slices Edo not duplicate prompt strings across test files.
 */
const EXT_ACC_001_PROMPT = 'Review extensions/reddog/extension.js for WSP_97 truth-label compliance. List OBSERVED vs INFERRED claims, missing evidence, and smallest valid fixes. Include WSP_15 priority for each fix.';

const EXT_ACC_001_TARGET_PATH = 'extensions/reddog/extension.js';

const BUILD_COPY_MARKDOWN_PROMPT = 'Review buildCopyMarkdown in extensions/reddog/extension.js for WSP_97 compliance.';

const REGULAR_SMOKE_PROMPT = 'Reply with exactly: regular mode works';

const MALFORMED_UNICODE_CONTEXT = 'PR #718 WSP_109_FOUNDUP_ONBOARDI' + '\udc94' + ' trailing safe context for gate probe.';

const BLOCKED_POLICY_CONTEXT = 'Bounded repo context with grant authority and merge authorization token present.';

const EMDASH_UNICODE_CONTEXT = 'PR #718 \u2014 `WSP_109_FOUNDUP_ONBOARDI' + ' trailing HoloIndex context for UTF-8 bridge probe.';

const REPAIR_DRAFT_WITH_BLOCK_LITERALS = [
  '## Decision',
  'Review redaction_gate_passed handling and grant authority paths.',
  'internal governance instruction noted in draft.',
  '## Findings',
  'F1: example',
  '## Evidence',
  'E1: example'
].join('\n');

const REPAIR_SUPPLEMENT_SECTIONS = [
  '## Evidence',
  'E1: OBSERVED Eprimary pass completed with bounded context attached.',
  '## Proposed fixes',
  'F1: defer until verified.',
  '## Uncertainties',
  'NEEDS_VERIFICATION: none.',
  '## Architect Trace',
  'Evidence retrieved from primary pass.',
  '## WSP_97 Truth Labels',
  '- OBSERVED: primary pass completed.',
  '## WSP_15 Priority',
  '| Action | Priority |',
  '| --- | --- |',
  '| Verify | P2 |',
  '## Verification gaps',
  'None listed.',
  '## Next safest step',
  'Re-run with narrower context.'
].join('\n');

const REPAIR_TAIL_SUPPLEMENT = [
  '## Evidence',
  'E1: OBSERVED Eprimary Fusion pass completed with routing summary attached.',
  '## Architect Trace',
  '- Evidence retrieved: primary lead/panel/synthesis excerpts from prior pass.',
  '- Alternatives considered: full re-run rejected; schema supplement chosen.',
  '## Verification gaps',
  'NEEDS_VERIFICATION: whether supplement fully satisfies local schema validator.',
  '## Next safest step',
  '012 confirms Run Trace shows repair_minimal + openrouter_single, then land if validation passes.'
].join('\n\n');

// REDDOG_TARGET_RECALL_PATH_AWARE_PHASE1 (slice 1/3): a FoundUps-creation audit
// prompt carrying an explicit "Required direct-read targets" list. The detector
// must honestly report index_gap_detected when none of these are recalled.
const FOUNDUP_REQUIRED_TARGETS = [
  'WSP_framework/src/WSP_109_FoundUps_Onboarding_Protocol.md',
  'modules/infrastructure/openclaw/src/openclaw_foundup_orchestrator.py',
  'modules/communication/moltbot_bridge/src/hermes_foundup_job_executor.py'
];

const FOUNDUP_CREATION_PROMPT = [
  'Audit the FoundUps creation monorepo WSP_109 execution path.',
  '',
  'Required direct-read targets:',
  '- ' + FOUNDUP_REQUIRED_TARGETS[0],
  '- ' + FOUNDUP_REQUIRED_TARGETS[1],
  '- ' + FOUNDUP_REQUIRED_TARGETS[2],
  '',
  'Produce required RedDog architect output sections per contract.'
].join('\n');

const TARGET_READ_DENIED_PATHS = [
  ['C:/Windows/System32/drivers/etc/hosts', 'absolute path'],
  ['../outside.txt', 'traversal'],
  ['.env', '.env basename'],
  ['extensions/reddog/node_modules/pkg/index.js', 'node_modules segment'],
  ['.git/config', '.git segment'],
  ['extensions/reddog/foundups-fusion-worker-0.3.21.vsix', 'vsix extension']
];

// REDDOG_WORK_FOCUS_TARGET_DERIVATION_PHASE1 (WFTD): free-form work-focus prompt shapes.
// Repo paths are named OUTSIDE the exact "Required direct-read targets:" header and must still
// be promoted to required direct-read targets so the governed fetch fires.

// The three paths from the real multi-lane-orchestration audit run that stayed dormant at
// v0.3.41/0.3.43 (target_recall_ok:false, required_targets_total:0, fetch never attempted).
const WORK_FOCUS_ORCH_PATHS = [
  'docs/0102_session_briefings/ACTIVE_SLICE_LEDGER.md',
  'docs/0102_session_briefings/work_ledger.schema.json',
  'holo_index/adaptive_learning/breadcrumb_tracer.py'
];

// Source 2: "Read first:" block.
const WORK_FOCUS_READ_FIRST_PROMPT = [
  'Audit the multi-lane orchestration brain.',
  '',
  'Read first:',
  '- ' + WORK_FOCUS_ORCH_PATHS[0],
  '- ' + WORK_FOCUS_ORCH_PATHS[1],
  '- ' + WORK_FOCUS_ORCH_PATHS[2],
  '',
  'Produce required RedDog architect output sections per contract.'
].join('\n');

// Source 3: WSP_99 M2M READ: array.
const WORK_FOCUS_M2M_READ_PROMPT = [
  'M2M work order (WSP_99).',
  'READ: ["' + WORK_FOCUS_ORCH_PATHS[0] + '", "' + WORK_FOCUS_ORCH_PATHS[2] + '"]',
  'Determine current state.'
].join('\n');

// Source 4: WSP_99 M2M CTX.FILES array.
const WORK_FOCUS_CTX_FILES_PROMPT = [
  'M2M work order (WSP_99).',
  'CTX.FILES: [' + WORK_FOCUS_ORCH_PATHS[0] + ', ' + WORK_FOCUS_ORCH_PATHS[1] + ']',
  'Determine current state.'
].join('\n');

// Source 7: backticked repo paths in prose.
const WORK_FOCUS_BACKTICK_PROMPT =
  'Review `' + WORK_FOCUS_ORCH_PATHS[2] + '` and `' + WORK_FOCUS_ORCH_PATHS[1] + '` for the ledger contract.';

// Source 6: inline repo paths embedded in ordinary prose (must NOT capture surrounding words).
const WORK_FOCUS_INLINE_PROMPT =
  'See ' + WORK_FOCUS_ORCH_PATHS[0] + ' for the active slice ledger and check '
  + WORK_FOCUS_ORCH_PATHS[2] + ' too before proceeding.';

// Guard B-i: a validation fence naming extension.js must NOT derive it.
const WORK_FOCUS_COMMAND_FENCE_PROMPT = [
  'Validate the change.',
  '',
  '```powershell',
  'node --check extensions/reddog/extension.js',
  'python holo_index.py --search "reddog work focus"',
  '```',
  '',
  'Then land.'
].join('\n');

// Guard B-ii: a SCOPE - OUT bullet naming a path must NOT derive; an in-scope Read-first does.
const WORK_FOCUS_SCOPE_OUT_PROMPT = [
  'Audit.',
  '',
  'SCOPE - OUT:',
  '- modules/off_limits/secret_area.py',
  '- modules/off_limits/do_not_touch.py',
  '',
  'Read first:',
  '- modules/in/scope.py',
  '',
  'Proceed.'
].join('\n');

// Denied paths named with read-intent are emitted honestly (so the Python gate rejects them),
// alongside one legitimate path that survives.
const WORK_FOCUS_DENIED_MIX_PROMPT = [
  'Read first:',
  '- .env',
  '- ../outside.txt',
  '- modules/communication/moltbot_bridge/src/foundup_job_contract.py'
].join('\n');

// REDDOG_WORK_FOCUS_READ_CAPTURE_PROSE_TOKENIZATION_PHASE1 (WFTD-015+): the EXACT failed 0.3.44
// prompt shape. Three files named in ONE flowing "Read first:" sentence, with a period + prose
// after breadcrumb_tracer.py ("...breadcrumb_tracer.py. Determine ...") and the embedded-slash
// English fragment "and the breadcrumb/handoff layer". At 0.3.44 the comma-splitter produced
// required_targets_total=4 / recalled=2 / target_recall_ok=false. This fixture is FLOWING PROSE by
// design -- the CoR guard forbids rewriting it as bullets to make the fix pass.
const WORK_FOCUS_PROSE_READ_FIRST_PROMPT = [
  'Audit the multi-lane orchestration brain and its lane-state derivation.',
  '',
  'Read first:',
  'the sources are ' + WORK_FOCUS_ORCH_PATHS[0] + ', ' + WORK_FOCUS_ORCH_PATHS[1] + ', and '
    + WORK_FOCUS_ORCH_PATHS[2] + '. Determine current lane-state sources and the breadcrumb/handoff layer.',
  '',
  'Produce required RedDog architect output sections per contract.'
].join('\n');

// REDDOG_DETERMINE_BLOCK_TARGET_DERIVATION_GUARD_PHASE1: the exact 0.3.58 host failure shape.
// The three real repo files are named in prose, then a Determine numbered list asks questions
// containing slash-bearing conceptual phrases like "ledger/runtime". Those question lines are
// answer obligations, not repo-file read intent, and must not enter repo_file_targets.
const WORK_FOCUS_DETERMINE_FALSE_POSITIVE_PROMPT = [
  'Audit whether a multi-lane orchestration brain should be a WRE module or a RedDog extension feature, and what already exists. Read first: the active slice ledger at '
    + WORK_FOCUS_ORCH_PATHS[0] + ', the typed schema ' + WORK_FOCUS_ORCH_PATHS[1]
    + ', and the breadcrumb/handoff layer ' + WORK_FOCUS_ORCH_PATHS[2] + '.',
  '',
  'Determine:',
  '1. What lane-state sources currently exist.',
  '2. Which source should be authoritative.',
  '3. Whether duplicate-work prevention already exists.',
  '4. Whether stale ledger/runtime reconciliation is the real gap.',
  '5. Whether WRE, not the RedDog extension, should own recursive multi-lane orchestration.'
].join('\n');

// Option-3 REGRESSION guard: the SAME three files, one path per line as a BULLETED "Read first:"
// list, must still derive all three cleanly (must not regress when the prose branch was tightened).
const WORK_FOCUS_PROSE_READ_FIRST_BULLET_PROMPT = WORK_FOCUS_READ_FIRST_PROMPT;

// Tiered-strictness proof: the EXPLICIT / M2M / CLEAN-BULLET tiers still accept an intentionally
// named DIRECTORY-style path (slash, no file extension) -- only FLOWING PROSE is stricter.
const WORK_FOCUS_DIR_PATH_M2M_PROMPT = [
  'M2M work order (WSP_99).',
  'READ: ["holo_index/adaptive_learning", "' + WORK_FOCUS_ORCH_PATHS[2] + '"]',
  'Determine current state.'
].join('\n');

module.exports = {
  EXT_ACC_001_PROMPT,
  EXT_ACC_001_TARGET_PATH,
  BUILD_COPY_MARKDOWN_PROMPT,
  REGULAR_SMOKE_PROMPT,
  MALFORMED_UNICODE_CONTEXT,
  BLOCKED_POLICY_CONTEXT,
  EMDASH_UNICODE_CONTEXT,
  REPAIR_DRAFT_WITH_BLOCK_LITERALS,
  REPAIR_SUPPLEMENT_SECTIONS,
  REPAIR_TAIL_SUPPLEMENT,
  TARGET_READ_DENIED_PATHS,
  FOUNDUP_REQUIRED_TARGETS,
  FOUNDUP_CREATION_PROMPT,
  WORK_FOCUS_ORCH_PATHS,
  WORK_FOCUS_READ_FIRST_PROMPT,
  WORK_FOCUS_M2M_READ_PROMPT,
  WORK_FOCUS_CTX_FILES_PROMPT,
  WORK_FOCUS_BACKTICK_PROMPT,
  WORK_FOCUS_INLINE_PROMPT,
  WORK_FOCUS_COMMAND_FENCE_PROMPT,
  WORK_FOCUS_SCOPE_OUT_PROMPT,
  WORK_FOCUS_DENIED_MIX_PROMPT,
  WORK_FOCUS_PROSE_READ_FIRST_PROMPT,
  WORK_FOCUS_DETERMINE_FALSE_POSITIVE_PROMPT,
  WORK_FOCUS_PROSE_READ_FIRST_BULLET_PROMPT,
  WORK_FOCUS_DIR_PATH_M2M_PROMPT
};
