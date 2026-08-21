(function drt007ContinuationIndependence() {
  const withContinuation = GOLDEN_FOUNDUP_PROMPT +
    '\n\nContinuation from last RedDog packet (run_prev123): prior audit HELD on evidence.\n';
  const a = orchestrator.holoIndexOutput(root, GOLDEN_FOUNDUP_PROMPT, 18000).meta || {};
  const b = orchestrator.holoIndexOutput(root, withContinuation, 18000).meta || {};
  assert.strictEqual(a.direct_read_fetch_attempted, true, 'DRT-007: fetch attempted (continuation absent)');
  assert.strictEqual(b.direct_read_fetch_attempted, true, 'DRT-007: fetch attempted (continuation present)');
  assert.strictEqual(a.direct_read_fallback_used, true, 'DRT-007: fallback used (continuation absent)');
  assert.strictEqual(b.direct_read_fallback_used, true, 'DRT-007: fallback used (continuation present)');
  assert.strictEqual(a.direct_read_fetch_arg_count, b.direct_read_fetch_arg_count, 'DRT-007: arg_count is continuation-invariant');
})();

// DRT-008: GOLDEN CONTRACT. The 8-target golden FoundUp prompt parses to exactly 8
// required targets, of which GOLDEN_FETCHABLE_TARGETS are direct-read fetchable, and
// buildMustIncludeArgs emits one --bundle-must-include pair per fetchable target.
(function drt008GoldenContract() {
  const parsed = orchestrator.parseRequiredTargetPaths(GOLDEN_FOUNDUP_PROMPT);
  assert.strictEqual(parsed.length, 8, 'DRT-008: golden prompt must parse to 8 required targets');
  const mustInclude = orchestrator.buildMustIncludeArgs(parsed);
  assert.strictEqual(mustInclude.length, GOLDEN_FETCHABLE_TARGETS.length * 2, 'DRT-008: one --bundle-must-include pair per fetchable target');
  assert.strictEqual(mustInclude.length / 2, GOLDEN_FETCHABLE_TARGETS.length, 'DRT-008: arg_count (pairs) == fetchable target count');
  // The one non-fetchable target (a symbol:) is counted in total but excluded from args.
  assert(parsed.some((t) => t.startsWith('symbol:')), 'DRT-008: golden 8th target is a non-fetchable symbol (total 8 > fetchable 7)');
})();

includes(blockedCopy, '## Governed Handoff Recommendation', 'substantive task must include governed handoff recommendation');
includes(blockedCopy, 'handoff_needed: unknown', 'blocked-local packet must use conservative handoff_needed');
includes(blockedCopy, 'reason: blocked_context_needs_local_0102_review', 'blocked-local packet must include conservative handoff reason');
includes(blockedCopy, 'WSP_15 priority: P1', 'blocked-local packet must default handoff priority to P1');
includes(blockedCopy, 'suggested_slice_name: none', 'blocked-local packet must not invent slice name');
includes(blockedCopy, 'authority_level: advisory_only', 'handoff must remain advisory_only');
assert(!blockedCopy.includes('OPENROUTER_API_KEY'), 'Copy MD must not include secret-adjacent env names');
assert(!blockedCopy.includes('Bearer sk-'), 'Copy MD must not include bearer/token patterns');

const blockedTrail = orchestrator.createWorkTrail();
blockedTrail.push('orchestrator_started');
blockedTrail.push('redaction_gate_blocked', 'Redaction gate blocked before network.');
blockedTrail.push('redaction_gate_blocked');
const blockedTrailCopy = orchestrator.buildCopyMarkdown({
  reason: 'redaction_blocked',
  review_packet: { made_network_call: false, retry_count: 0, output_validation: { validated: false, reason: 'redaction_blocked' } }
}, 'reddog_architect', '', blockedTrail, null, 'high', { substantive: true, handoffRecommendation: blockedHandoffRec });
const trailLines = blockedTrailCopy.split('\n').filter((line) => line.startsWith('- redaction_gate_blocked'));
assert.strictEqual(trailLines.length, 1, 'blocked-local Copy MD must not show adjacent duplicate Work Trail events');

const cappedTrail = orchestrator.createWorkTrail();
for (let i = 0; i < 60; i++) {
  cappedTrail.push('orchestrator_started', 'event-' + i);
}
assert.strictEqual(cappedTrail.count(), orchestrator.WORK_TRAIL_MAX_EVENTS, 'Work Trail must cap normalized events');

const repairFailCopy = orchestrator.buildCopyMarkdown({
  ok: true,
  content: '## Decision\npartial answer',
  review_packet: {
    task_classification: { tier: 'HIGH' },
    resolved_effort: 'high',
    resolved_mode: 'openrouter_single',
    resolved_context: 'wsp_holo',
    mode_selection_reasoning: 'Single-model GLM principal',
    principal_model: 'z-ai/glm-5.2',
    panel_models: ['deepseek/deepseek-v4-pro'],
    made_network_call: true,
    output_validation: {
      validated: false,
      output_validation_failed: true,
      repair_attempted: true,
      repair_failure_reason: 'redaction_blocked',
      missing_sections: ['Architect Trace', 'WSP_15 Priority']
    }
  }
}, 'reddog_architect', 'Repo context attached', null, null, 'high', { substantive: false });
includes(repairFailCopy, 'OUTPUT_VALIDATION_FAILED', 'repair-blocked Copy MD must include validation failure');
includes(repairFailCopy, 'repair_failure_reason: redaction_blocked', 'repair-blocked Copy MD must include repair_failure_reason');
includes(repairFailCopy, 'Architect Trace', 'repair-blocked Copy MD must list missing sections');
includes(repairFailCopy, 'Output failed local contract validation.', 'repair-blocked Copy MD must include local fallback footer');
includes(repairFailCopy, 'reddog_effort:', 'Run Trace must include reddog_effort');
includes(repairFailCopy, 'provider_reasoning_requested:', 'Run Trace must include provider reasoning requested');
includes(repairFailCopy, 'provider_reasoning_applied: unknown', 'provider reasoning applied must be unknown in report-only slice');

const sanitized = orchestrator.sanitizeCopyMdText('OPENROUTER_API_KEY visible to bridge: yes');
includes(sanitized, 'key_env_present: true', 'trail sanitizer must normalize secret-adjacent env phrase');

// ADDENDUM E - 0102 test-first content inclusion (no OpenRouter)
// Fixtures: tests/fixtures.js -- reuse EXT_ACC_001_PROMPT; do not duplicate.
const extAcc001Prompt = fixtures.EXT_ACC_001_PROMPT;

const recallTargets = orchestrator.inferRecallTargetPaths(extAcc001Prompt);
assert(recallTargets.includes(fixtures.EXT_ACC_001_TARGET_PATH), 'EXT-ACC-001 prompt must map to extension.js');

const extensionSnippet = orchestrator.readBoundedTargetSnippet(root, fixtures.EXT_ACC_001_TARGET_PATH, 24000);
includes(extensionSnippet.content, "const EXTENSION_VERSION = '0.4.102'", 'target snippet must include extension.js source');
assert(extensionSnippet.chars > 0, 'target snippet chars must be nonzero');
assert.strictEqual(extensionSnippet.omitted_reason, 'none', 'extension.js snippet must not be omitted');

for (const [badPath, label] of fixtures.TARGET_READ_DENIED_PATHS) {
  assert(orchestrator.isTargetReadPathDenied(badPath), 'must reject ' + label + ': ' + badPath);
}

const safeResolve = orchestrator.resolveSafeRepoFile(root, fixtures.EXT_ACC_001_TARGET_PATH);
assert.strictEqual(safeResolve.ok, true, 'extension.js must resolve inside workspace root');

const linkedRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'reddog-path-policy-'));
const hardlinkSource = path.join(os.tmpdir(), `reddog-hardlink-source-${process.pid}-${Date.now()}.md`);
try {
  const sensitiveDir = path.join(linkedRoot, '.ssh');
  const publicLink = path.join(linkedRoot, 'docs');
  fs.mkdirSync(sensitiveDir);
  fs.writeFileSync(path.join(sensitiveDir, 'README.md'), 'private material', 'utf8');
  fs.symlinkSync(sensitiveDir, publicLink, process.platform === 'win32' ? 'junction' : 'dir');
  const linkedResolve = orchestrator.resolveSafeRepoFile(linkedRoot, 'docs/README.md');
  assert.strictEqual(linkedResolve.ok, false,
    'resolved in-repository links must reapply the deny policy');
  assert.strictEqual(linkedResolve.reason, 'outside_root',
    'resolved links into denied segments must report outside_root');
  assert.strictEqual(
    orchestrator.readBoundedRepoFile(linkedRoot, 'docs/README.md', 1400),
    '',
    'Skillz snippet reads must share resolved-path denial'
  );
  vscodeMock.window.activeTextEditor = {
    document: {
      uri: { scheme: 'file', fsPath: path.join(publicLink, 'README.md') },
      languageId: 'text',
      getText: () => 'private material'
    },
    selection: { isEmpty: true }
  };
  assert.strictEqual(orchestrator.activeEditorContext(linkedRoot), '',
    'active-editor context must reject links into denied repository segments');
  vscodeMock.window.activeTextEditor.document.uri.fsPath = __filename;
  vscodeMock.window.activeTextEditor.document.getText = () => 'external private material';
  assert.strictEqual(orchestrator.activeEditorContext(linkedRoot), '',
    'active-editor context must reject files outside the repository root');

  fs.writeFileSync(hardlinkSource, 'external hardlink material', 'utf8');
  const hardlinkAlias = path.join(linkedRoot, 'hardlink-alias.md');
  fs.linkSync(hardlinkSource, hardlinkAlias);
  const hardlinkResolve = orchestrator.resolveSafeRepoFile(linkedRoot, 'hardlink-alias.md');
  assert.strictEqual(hardlinkResolve.ok, false,
    'repository context must reject multiply linked files');
  assert.strictEqual(hardlinkResolve.reason, 'hardlink_denied',
    'hard-link rejection must be explicit');
  assert.strictEqual(orchestrator.readBoundedRepoFile(linkedRoot, 'hardlink-alias.md', 1400), '',
    'hard-linked external content must not enter repository context');

  const allowedEditor = path.join(linkedRoot, 'allowed.py');
  fs.writeFileSync(allowedEditor, 'print("allowed")', 'utf8');
  vscodeMock.window.activeTextEditor.document.uri.fsPath = allowedEditor;
  vscodeMock.window.activeTextEditor.document.languageId = 'python';
  vscodeMock.window.activeTextEditor.document.getText = () => 'print("allowed")';
  includes(orchestrator.activeEditorContext(linkedRoot), 'print("allowed")',
    'active-editor context must retain an admitted repository source');
  vscodeMock.window.activeTextEditor = null;
} finally {
  vscodeMock.window.activeTextEditor = null;
  fs.rmSync(linkedRoot, { recursive: true, force: true });
  fs.rmSync(hardlinkSource, { force: true });
}

const targetSection = orchestrator.buildTargetRecallContentSection(root, extAcc001Prompt, 24000);
includes(targetSection.text, '### Target recall content', 'target recall section header missing');
includes(targetSection.text, fixtures.EXT_ACC_001_TARGET_PATH, 'target recall must cite extension.js path');
includes(targetSection.text, "const EXTENSION_VERSION = '0.4.102'", 'target recall must include source snippet');
assert.strictEqual(targetSection.meta.target_content_included, true, 'target_content_included must be true when snippets present');
assert(targetSection.meta.target_content_chars > 0, 'target_content_chars must be > 0');

const wsp97Excerpt = orchestrator.buildWsp97ProtocolExcerpt(root, 4096);
includes(wsp97Excerpt.text, '### WSP protocol excerpt (bounded)', 'WSP_97 excerpt header missing');
includes(wsp97Excerpt.text, 'WSP 97: System Execution Prompting Protocol', 'WSP_97 excerpt must include protocol title');
assert.strictEqual(wsp97Excerpt.meta.wsp97_excerpt_included, true, 'wsp97_excerpt_included must be true');

const boundedContext = orchestrator.buildBoundedRepoContext('wsp_holo_skillz', extAcc001Prompt);
includes(boundedContext.text, '### Target recall content', 'bounded context must include target recall section');
includes(boundedContext.text, fixtures.EXT_ACC_001_TARGET_PATH, 'bounded context must include extension.js path');
includes(boundedContext.text, "const EXTENSION_VERSION = '0.4.102'", 'bounded context must include source snippet');
includes(boundedContext.text, '### WSP protocol excerpt (bounded)', 'WSP_97 task must include protocol excerpt');
includes(boundedContext.text, 'WSP 97: System Execution Prompting Protocol', 'bounded context must include WSP_97 excerpt body');
assert.strictEqual(boundedContext.holoindex_scorecard.target_content_included, true, 'scorecard target_content_included must be true');
assert(boundedContext.holoindex_scorecard.target_content_chars > 0, 'scorecard target_content_chars must be > 0');
includes(boundedContext.holoindex_scorecard.target_content_paths.join(','), fixtures.EXT_ACC_001_TARGET_PATH, 'scorecard must list included path');

const governedDiffRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'reddog-git-diff-'));
const injectedGitEnvKeys = [
  'GIT_CONFIG_COUNT', 'GIT_CONFIG_KEY_0', 'GIT_CONFIG_VALUE_0',
  'GIT_CONFIG_KEY_1', 'GIT_CONFIG_VALUE_1'
];
const savedGitEnv = Object.fromEntries(injectedGitEnvKeys.map((key) => [key, process.env[key]]));
try {
  cp.execFileSync('git', ['init', '-q'], { cwd: governedDiffRoot });
  fs.mkdirSync(path.join(governedDiffRoot, 'keys'));
  fs.writeFileSync(path.join(governedDiffRoot, 'allowed.py'), 'value = 1\n', 'utf8');
  fs.writeFileSync(path.join(governedDiffRoot, 'keys', 'key'), 'private-old\n', 'utf8');
  cp.execFileSync('git', ['add', '.'], { cwd: governedDiffRoot });
  cp.execFileSync('git', ['-c', 'user.name=RedDog Test', '-c', 'user.email=reddog@example.invalid', 'commit', '-qm', 'fixture'], { cwd: governedDiffRoot });
  fs.writeFileSync(path.join(governedDiffRoot, 'allowed.py'), 'value = 2\n', 'utf8');
  fs.writeFileSync(path.join(governedDiffRoot, 'keys', 'key'), 'private-new\n', 'utf8');
  cp.execFileSync('git', ['add', 'allowed.py', 'keys/key'], { cwd: governedDiffRoot });
  fs.writeFileSync(path.join(governedDiffRoot, 'notes.txt'), 'untracked admitted evidence\n', 'utf8');
  fs.mkdirSync(path.join(governedDiffRoot, 'secrets'));
  fs.writeFileSync(path.join(governedDiffRoot, 'secrets', 'api_keys.py'),
    'UNTRACKED_SECRET_SOURCE_SENTINEL = true\n', 'utf8');
  const governedDiff = orchestrator.governedGitDiff(governedDiffRoot, 24000);
  const governedStatus = orchestrator.governedGitStatus(governedDiffRoot, 8000);
  const governedStat = orchestrator.governedGitStat(governedDiffRoot, 8000);
  const currentBranch = cp.execFileSync('git', ['branch', '--show-current'], {
    cwd: governedDiffRoot,
    encoding: 'utf8'
  }).trim();
  const branchRef = path.join(governedDiffRoot, '.git', 'refs', 'heads', currentBranch);
  const branchRefValue = fs.readFileSync(branchRef, 'utf8');
  const branchRefAlias = path.join(governedDiffRoot, 'branch-ref-hardlink-source.tmp');
  fs.writeFileSync(branchRefAlias, branchRefValue, 'utf8');
  fs.rmSync(branchRef);
  fs.linkSync(branchRefAlias, branchRef);
  includes(orchestrator.governedGitDiff(governedDiffRoot, 24000), '[git context unavailable:',
    'a nested ref hardlink introduced after cache fill must invalidate governed Git storage');
  fs.rmSync(branchRef);
  fs.writeFileSync(branchRef, branchRefValue, 'utf8');
  fs.rmSync(branchRefAlias);
  const filterMarker = path.join(governedDiffRoot, 'filter-ran.txt');
  const filterProbe = path.join(governedDiffRoot, 'filter-probe.js');
  fs.writeFileSync(filterProbe,
    `require('fs').writeFileSync(${JSON.stringify(filterMarker)}, 'ran'); process.stdin.pipe(process.stdout);`,
    'utf8');
  const filterCommand = `"${process.execPath.replace(/\\/g, '/')}" "${filterProbe.replace(/\\/g, '/')}"`;
  cp.execFileSync('git', ['config', 'filter.probe.clean', filterCommand], { cwd: governedDiffRoot });
  cp.execFileSync('git', ['config', 'diff.probe.textconv', filterCommand], { cwd: governedDiffRoot });
  fs.writeFileSync(path.join(governedDiffRoot, '.gitattributes'),
    '*.py filter=envprobe diff=probe\n', 'utf8');
  process.env.GIT_CONFIG_COUNT = '2';
  process.env.GIT_CONFIG_KEY_0 = 'filter.envprobe.clean';
  process.env.GIT_CONFIG_VALUE_0 = filterCommand;
  process.env.GIT_CONFIG_KEY_1 = 'filter.envprobe.required';
  process.env.GIT_CONFIG_VALUE_1 = 'true';
  const blockedGit = orchestrator.governedGitDiff(governedDiffRoot, 24000);
  includes(governedDiff, 'value = 2', 'governed git diff must retain admitted source changes');
  includes(governedDiff, 'untracked admitted evidence',
    'governed git diff must include admitted untracked work');
  assert(!governedDiff.includes('private-old') && !governedDiff.includes('private-new'),
    'governed git diff must exclude protected file contents');
  assert(!governedDiff.includes('keys/key'),
    'governed git diff must exclude protected paths');
  assert(!governedDiff.includes('UNTRACKED_SECRET_SOURCE_SENTINEL')
    && !governedDiff.includes('secrets/api_keys.py'),
  'governed git diff must exclude secret-like untracked source paths and contents');
  includes(governedStatus, 'allowed.py', 'governed git status must retain admitted paths');
  includes(governedStatus, 'notes.txt', 'governed git status must retain admitted untracked paths');
  includes(governedStat, 'allowed.py', 'governed git stat must retain admitted paths');
  assert(!governedStatus.includes('keys/key') && !governedStat.includes('keys/key'),
    'governed git metadata must exclude protected paths');
  includes(blockedGit, '[git context unavailable:',
    'configured Git content commands must fail context collection closed');
  assert.strictEqual(fs.existsSync(filterMarker), false,
    'governed Git context must not execute configured clean filters');
  cp.execFileSync('git', ['config', '--unset-all', 'filter.probe.clean'], { cwd: governedDiffRoot });
  cp.execFileSync('git', ['config', '--unset-all', 'diff.probe.textconv'], { cwd: governedDiffRoot });
  cp.execFileSync('git', ['config', 'extensions.worktreeConfig', 'true'], { cwd: governedDiffRoot });
  cp.execFileSync('git', ['config', '--worktree', 'filter.worktreeprobe.clean', filterCommand],
    { cwd: governedDiffRoot });
  const blockedWorktreeGit = orchestrator.governedGitDiff(governedDiffRoot, 24000);
  includes(blockedWorktreeGit, '[git context unavailable:',
    'worktree-scoped Git content commands must fail context collection closed');
  assert.strictEqual(fs.existsSync(filterMarker), false,
    'governed Git context must not execute worktree-scoped clean filters');
  cp.execFileSync('git', ['config', '--worktree', '--unset-all', 'filter.worktreeprobe.clean'],
    { cwd: governedDiffRoot });
  const redirectedWorktree = fs.mkdtempSync(path.join(os.tmpdir(), 'reddog-git-redirect-'));
  try {
    fs.writeFileSync(path.join(redirectedWorktree, 'allowed.py'), 'EXTERNAL_REDIRECTED_CONTENT\n', 'utf8');
    cp.execFileSync('git', ['config', '--local', 'core.worktree', redirectedWorktree],
      { cwd: governedDiffRoot });
    const blockedRedirectGit = orchestrator.governedGitDiff(governedDiffRoot, 24000);
    includes(blockedRedirectGit, '[git context unavailable:',
      'configured core.worktree must fail governed context collection closed');
    assert(!blockedRedirectGit.includes('EXTERNAL_REDIRECTED_CONTENT'),
      'governed Git context must never disclose redirected worktree content');
  includes(governedGitReadinessJs, "'-c', 'core.worktree=' + root",
      'every governed Git command must pin the canonical workspace worktree');
    includes(governedGitReadinessJs, "'-c', 'safe.directory=' + root",
      'governed Git must explicitly admit only its validated canonical root');
  } finally {
    cp.execFileSync('git', ['config', '--local', '--unset-all', 'core.worktree'],
      { cwd: governedDiffRoot });
    fs.rmSync(redirectedWorktree, { recursive: true, force: true });
  }
  const includedConfig = path.join(governedDiffRoot, 'attacker-include.config');
  fs.writeFileSync(includedConfig, `[filter "includedprobe"]\n\tclean = ${filterCommand}\n`, 'utf8');
  cp.execFileSync('git', ['config', '--local', '--add', 'include.path', includedConfig],
    { cwd: governedDiffRoot });
  const blockedIncludeGit = orchestrator.governedGitDiff(governedDiffRoot, 24000);
  includes(blockedIncludeGit, '[git context unavailable:',
    'local Git include directives must fail context collection closed without being followed');
  assert.strictEqual(fs.existsSync(filterMarker), false,
    'governed Git context must not execute commands from included configuration');
  cp.execFileSync('git', ['config', '--local', '--unset-all', 'include.path'],
    { cwd: governedDiffRoot });
  cp.execFileSync('git', ['config', '--local', 'core.attributesFile', includedConfig],
    { cwd: governedDiffRoot });
  includes(orchestrator.governedGitDiff(governedDiffRoot, 24000), '[git context unavailable:',
    'external attributes files must fail governed context collection closed');
  cp.execFileSync('git', ['config', '--local', '--unset-all', 'core.attributesFile'],
    { cwd: governedDiffRoot });
  cp.execFileSync('git', ['config', '--local', 'core.excludesFile', includedConfig],
    { cwd: governedDiffRoot });
  includes(orchestrator.governedGitStatus(governedDiffRoot, 8000), '[git context unavailable:',
    'external excludes files must not silently remove untracked evidence');
  cp.execFileSync('git', ['config', '--local', '--unset-all', 'core.excludesFile'],
    { cwd: governedDiffRoot });
  fs.writeFileSync(path.join(governedDiffRoot, '.gitattributes'), 'allowed.py -diff\n', 'utf8');
  const forcedTextDiff = orchestrator.governedGitDiff(governedDiffRoot, 24000);
  includes(forcedTextDiff, 'value = 2',
    'repository attributes must not suppress admitted source content as binary');
  assert(!forcedTextDiff.includes('Binary files'),
    'governed source diff must override repository binary attributes');
  fs.appendFileSync(path.join(governedDiffRoot, '.git', 'info', 'exclude'), '\nignored-by-info.py\n', 'utf8');
  fs.writeFileSync(path.join(governedDiffRoot, 'ignored-by-info.py'),
    'ignored_but_governed = true\n', 'utf8');
  const ignoredSourceDiff = orchestrator.governedGitDiff(governedDiffRoot, 24000);
  assert(!ignoredSourceDiff.includes('[git context unavailable:'),
    '.git/info/exclude entries must be excluded without making the projection unusable');
  assert(!ignoredSourceDiff.includes('ignored_but_governed = true'),
    'ignored source content must not enter model context or Copy MD');
  includes(extensionJs, 'const { status, stat, diff } = governedGitSnapshot(root);',
    'final context must use one validated governed Git snapshot');
  const governedGitStorageJs = fs.readFileSync(path.join(extDir, 'governed_git_storage.js'), 'utf8');
  assert(governedGitStorageJs.includes('function authorityReceipt(root, gitEntry) {') && governedGitStorageJs.includes("const dirs = ['objects', 'refs', 'refs/heads', 'info', 'objects/info']"), 'Git receipt must scope authority and required ordinary directories');
  assert(governedGitStorageJs.includes('function sameDirectory(left, right) {') && governedGitStorageJs.includes('sameCanonicalPath(canonical, candidate)'), 'nested directory identity and confinement must be stable');
  assert(governedGitStorageJs.includes("return relative.split('/').every") && governedGitStorageJs.includes("!part.endsWith('.lock')") && governedGitStorageJs.includes('function refParentChain(common, refName) {'), 'supported heads grammar and parent chain must validate every component');
  assert(governedGitStorageJs.includes('const content = Buffer.allocUnsafe(opened.size);') && governedGitStorageJs.includes('fs.readSync(handle, content, offset, opened.size - offset, offset)'), 'control allocation and fd reads must be opened-size bounded');
  assert(governedGitStorageJs.includes("content: name === 'index' ? '' : content.toString('utf8')"), 'binary index bytes must not be duplicated as UTF-8 text');
  assert(governedGitStorageJs.includes('const targetsCurrent = tokens.includes(refName);') && governedGitStorageJs.includes("const canonical = /^([0-9a-f]+) ([^\\s]+)$/i.exec(line);") && governedGitStorageJs.includes('validOid(canonical[1])') && governedGitStorageJs.includes('function noFollowPathEntry(filePath) {') && fs.readFileSync(path.join(extDir, 'governed_git_context.js'), 'utf8').includes('registeredGitMetadataState(canonicalRoot)'), 'packed refs and all presence decisions must use exact classification');
  assert(governedGitStorageJs.includes("const prefix = 'refs/heads/';") && governedGitStorageJs.includes('(value.length === 40 || value.length === 64)') && !governedGitStorageJs.includes('function objectFormat(') && fs.readFileSync(path.join(extDir, 'governed_git_projection.js'), 'utf8').includes("['rev-parse', '--verify', 'HEAD^{commit}']"), 'receipt OIDs must be width-bounded while Git retains object/config semantics');
  const governedGitProjectionJs = fs.readFileSync(path.join(extDir, 'governed_git_projection.js'), 'utf8');
  assert(governedGitProjectionJs.includes("const { noFollowPathEntry } = require('./governed_git_storage');") && governedGitProjectionJs.includes('function projectionPathState(root, relPath) {') && !governedGitProjectionJs.includes('fs.existsSync(full)') && governedGitProjectionJs.includes('function readOpenedBytes(handle, size, maxSize) {') && governedGitProjectionJs.includes('function openedFileMatches(before, opened, maxSize) {') && governedGitProjectionJs.includes('Number.isSafeInteger(size)') && governedGitProjectionJs.includes('fs.readSync(handle, bytes, offset, size - offset, offset)'), 'projection absence and content reads must remain no-follow, identity-bound, and capped before allocation');
} finally {
  for (const key of injectedGitEnvKeys) {
    if (savedGitEnv[key] === undefined) delete process.env[key];
    else process.env[key] = savedGitEnv[key];
  }
  fs.rmSync(governedDiffRoot, { recursive: true, force: true });
}

const unbornGitRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'reddog-git-unborn-'));
try {
  cp.execFileSync('git', ['init', '-q'], { cwd: unbornGitRoot });
  fs.writeFileSync(path.join(unbornGitRoot, 'allowed.py'), 'unborn staged evidence\n', 'utf8');
  cp.execFileSync('git', ['add', 'allowed.py'], { cwd: unbornGitRoot });
  fs.writeFileSync(path.join(unbornGitRoot, 'notes.txt'), 'unborn untracked evidence\n', 'utf8');
  includes(orchestrator.governedGitStatus(unbornGitRoot, 8000), 'allowed.py',
    'unborn repositories must report admitted staged work');
  includes(orchestrator.governedGitStatus(unbornGitRoot, 8000), 'notes.txt',
    'unborn repositories must report admitted untracked work');
  const unbornDiff = orchestrator.governedGitDiff(unbornGitRoot, 8000);
  includes(unbornDiff, 'unborn staged evidence',
    'unborn repositories must not collapse staged work to a clean state');
  includes(unbornDiff, 'unborn untracked evidence',
    'unborn repositories must not collapse untracked work to a clean state');
} finally {
  fs.rmSync(unbornGitRoot, { recursive: true, force: true });
}

const excessiveGitRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'reddog-git-excessive-'));
try {
  cp.execFileSync('git', ['init', '-q'], { cwd: excessiveGitRoot });
  for (let index = 0; index < 501; index += 1) {
    fs.writeFileSync(path.join(excessiveGitRoot, `change-${String(index).padStart(3, '0')}.txt`), '', 'utf8');
  }
  fs.writeFileSync(path.join(excessiveGitRoot, 'zz-consequential.py'), 'consequential = true\n', 'utf8');
  includes(orchestrator.governedGitDiff(excessiveGitRoot, 24000),
    '[git context unavailable: governed change enumeration failed]',
    'change sets above the admitted-path bound must fail closed instead of omitting later paths');
} finally {
  fs.rmSync(excessiveGitRoot, { recursive: true, force: true });
}

const concealedIndexRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'reddog-git-index-flags-'));
try {
  cp.execFileSync('git', ['init', '-q'], { cwd: concealedIndexRoot });
  fs.writeFileSync(path.join(concealedIndexRoot, 'allowed.py'), 'visible = 1\n', 'utf8');
  cp.execFileSync('git', ['add', 'allowed.py'], { cwd: concealedIndexRoot });
  cp.execFileSync('git', ['-c', 'user.name=RedDog Test', '-c', 'user.email=reddog@example.invalid',
    'commit', '-qm', 'fixture'], { cwd: concealedIndexRoot });
  for (const [setFlag, clearFlag] of [
    ['--skip-worktree', '--no-skip-worktree'],
    ['--assume-unchanged', '--no-assume-unchanged']
  ]) {
    cp.execFileSync('git', ['update-index', setFlag, 'allowed.py'], { cwd: concealedIndexRoot });
    fs.writeFileSync(path.join(concealedIndexRoot, 'allowed.py'), `concealed = ${JSON.stringify(setFlag)}\n`, 'utf8');
    includes(orchestrator.governedGitDiff(concealedIndexRoot, 24000),
      '[git context unavailable: governed change enumeration failed]',
      `${setFlag} index state must fail closed instead of concealing a tracked change`);
    cp.execFileSync('git', ['update-index', clearFlag, 'allowed.py'], { cwd: concealedIndexRoot });
  }
} finally {
  fs.rmSync(concealedIndexRoot, { recursive: true, force: true });
}

const weakenedStatRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'reddog-git-stat-config-'));
