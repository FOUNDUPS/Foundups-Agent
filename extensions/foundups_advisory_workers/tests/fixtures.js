/**
 * Shared contract-test fixtures. Reuse in verify_extension_contract.js and future
 * RedDog slices — do not duplicate prompt strings across test files.
 */
const EXT_ACC_001_PROMPT = 'Review extensions/foundups_advisory_workers/extension.js for WSP_97 truth-label compliance. List OBSERVED vs INFERRED claims, missing evidence, and smallest valid fixes. Include WSP_15 priority for each fix.';

const EXT_ACC_001_TARGET_PATH = 'extensions/foundups_advisory_workers/extension.js';

const BUILD_COPY_MARKDOWN_PROMPT = 'Review buildCopyMarkdown in extensions/foundups_advisory_workers/extension.js for WSP_97 compliance.';

const REGULAR_SMOKE_PROMPT = 'Reply with exactly: regular mode works';

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
  TARGET_READ_DENIED_PATHS
};
