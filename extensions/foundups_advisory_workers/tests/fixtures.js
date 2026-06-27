/**
 * Shared contract-test fixtures. Reuse in verify_extension_contract.js and future
 * RedDog slices — do not duplicate prompt strings across test files.
 */
const EXT_ACC_001_PROMPT = 'Review extensions/foundups_advisory_workers/extension.js for WSP_97 truth-label compliance. List OBSERVED vs INFERRED claims, missing evidence, and smallest valid fixes. Include WSP_15 priority for each fix.';

const EXT_ACC_001_TARGET_PATH = 'extensions/foundups_advisory_workers/extension.js';

const BUILD_COPY_MARKDOWN_PROMPT = 'Review buildCopyMarkdown in extensions/foundups_advisory_workers/extension.js for WSP_97 compliance.';

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
  'E1: OBSERVED — primary pass completed with bounded context attached.',
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
  'E1: OBSERVED — primary Fusion pass completed with routing summary attached.',
  '## Architect Trace',
  '- Evidence retrieved: primary lead/panel/synthesis excerpts from prior pass.',
  '- Alternatives considered: full re-run rejected; schema supplement chosen.',
  '## Verification gaps',
  'NEEDS_VERIFICATION: whether supplement fully satisfies local schema validator.',
  '## Next safest step',
  '012 confirms Run Trace shows repair_minimal + openrouter_single, then land if validation passes.'
].join('\n\n');

const TARGET_READ_DENIED_PATHS = [
  ['C:/Windows/System32/drivers/etc/hosts', 'absolute path'],
  ['../outside.txt', 'traversal'],
  ['.env', '.env basename'],
  ['extensions/foundups_advisory_workers/node_modules/pkg/index.js', 'node_modules segment'],
  ['.git/config', '.git segment'],
  ['extensions/foundups_advisory_workers/foundups-fusion-worker-0.3.21.vsix', 'vsix extension']
];

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
  TARGET_READ_DENIED_PATHS
};
