'use strict';

const fs = require('fs');
const path = require('path');
const defaultGitExecutable = require('./governed_git_executable');
const {
  registeredGitMetadataReceipt,
  registeredGitMetadataState
} = require('./governed_git_storage');
const {
  GIT_READINESS_SCHEMA,
  configuredGitRiskySettings,
  governedGitArgs,
  gitOwnershipReadiness,
  governedGitReadiness,
  sanitizedGitEnv,
  sameCanonicalPath,
  setGitReadiness,
  validatedCanonicalRoot
} = require('./governed_git_readiness');
const projectionFactory = require('./governed_git_projection');
const repoState = require('./governed_git_repo_state');
const { isTargetReadPathDenied } = require('./target_read_path_policy');

const GIT_OUTPUT_TRUNCATED_MARKER = '[REDDOG_GIT_OUTPUT_TRUNCATED]';
const GIT_OPERATIONS = Object.freeze({
  HEAD_SHA: Object.freeze({
    args: Object.freeze(['rev-parse', '--verify', 'HEAD^{commit}']), maxChars: 128
  }),
  FOUNDUP_REGISTRY_STATUS: Object.freeze({
    args: Object.freeze(['status', '--porcelain=v1', '--',
      'modules/foundups/foundup_registry.json',
      'modules/foundups/foundup_registry.schema.json']), maxChars: 4096
  }),
  TRACKED_PATHS: Object.freeze({ args: Object.freeze(['ls-files']), maxChars: 4 * 1024 * 1024 }),
  DIRTY_PATHS: Object.freeze({ args: Object.freeze(['diff', '--name-only', 'HEAD']), maxChars: 4 * 1024 * 1024 })
  , REPO_STATUS: Object.freeze({
    args: Object.freeze(['status', '--porcelain=v1', '-z', '--untracked-files=all']),
    maxChars: 4 * 1024 * 1024
  }), WORKTREE_LIST: Object.freeze({
    args: Object.freeze(['worktree', 'list', '--porcelain', '-z']),
    maxChars: 4 * 1024 * 1024
  })
});

const FAILED_POLICY = Object.freeze({
  isTargetReadPathDenied: () => { throw new Error('invalid governed Git policy'); },
  resolveSafeRepoFile: () => { throw new Error('invalid governed Git policy'); }
});

function defaultResolveSafeRepoFile(root, relPath) {
  if (isTargetReadPathDenied(relPath)) return { ok: false };
  try {
    const canonicalRoot = fs.realpathSync(path.resolve(root));
    const candidate = fs.realpathSync(path.resolve(canonicalRoot, relPath));
    const metadata = fs.lstatSync(candidate);
    if (!candidate.startsWith(canonicalRoot + path.sep) || !metadata.isFile()
      || metadata.isSymbolicLink() || metadata.nlink !== 1) return { ok: false };
    return { ok: true, full: candidate };
  } catch (err) {
    return { ok: false };
  }
}

const DEFAULT_POLICY = Object.freeze({
  isTargetReadPathDenied,
  resolveSafeRepoFile: defaultResolveSafeRepoFile
});

function immutablePolicy(options) {
  try {
    if (!options || typeof options !== 'object'
      || typeof options.isTargetReadPathDenied !== 'function'
      || typeof options.resolveSafeRepoFile !== 'function') return FAILED_POLICY;
    return Object.freeze({
      isTargetReadPathDenied: options.isTargetReadPathDenied,
      resolveSafeRepoFile: options.resolveSafeRepoFile
    });
  } catch (err) {
    return FAILED_POLICY;
  }
}

function create(options) {
  const authority = executableAuthority(options);
  return createProjectionApi(
    projectionFactory.create(immutablePolicy(options)), authority
  );
}

function executableAuthority(options) {
  try {
    return options && validExecutableAuthority(options.gitExecutable)
      ? options.gitExecutable : defaultGitExecutable;
  } catch (_err) {
    return defaultGitExecutable;
  }
}

function validExecutableAuthority(value) {
  return value && typeof value.bind === 'function'
    && typeof value.revalidate === 'function'
    && typeof value.execFileSync === 'function';
}

function validateGitExecutionRoot(root) {
  const canonicalRoot = validatedCanonicalRoot(root);
  if (!canonicalRoot) return { error: 'canonical root invalid' };
  const metadata = registeredGitMetadataState(canonicalRoot);
  if (metadata.state === 'absent') return { empty: true };
  if (metadata.state !== 'present') return { error: 'external or linked Git directory denied' };
  const receipt = metadata.receipt;
  if (receipt.valid) return { canonicalRoot, receipt, headState: metadata.headState };
  setGitReadiness(canonicalRoot, {
    canonical_root_validated: true, reason: 'git_metadata_invalid'
  });
  return { error: 'external or linked Git directory denied' };
}

function validateGitConfiguration(canonicalRoot, receipt, binding, authority) {
  const env = sanitizedGitEnv();
  const ownership = gitOwnershipReadiness(canonicalRoot, env, binding, authority);
  if (ownership === null) {
    setGitReadiness(canonicalRoot, { canonical_root_validated: true,
      git_metadata_validated: true, reason: 'ownership_unproven' }, binding, authority);
    return { error: 'Git ownership unreadable' };
  }
  const riskySettings = configuredGitRiskySettings(
    canonicalRoot, env, ownership.overrideRequired, receipt.worktree_config_state,
    binding, authority
  );
  const shared = configurationEvidence(ownership);
  if (riskySettings === null) {
    setGitReadiness(canonicalRoot, { ...shared,
      reason: 'git_configuration_unreadable' }, binding, authority);
    return { error: 'Git configuration unreadable' };
  }
  if (riskySettings.length) {
    setGitReadiness(canonicalRoot, { ...shared,
      reason: 'configured_git_setting_denied' }, binding, authority);
    return { error: 'configured Git setting denied' };
  }
  setGitReadiness(canonicalRoot, { ...shared, ready: true,
    safe_directory_override_applied: ownership.overrideRequired,
    safe_directory_scope: ownership.overrideRequired ? 'command' : 'none',
    reason: ownership.overrideRequired ? 'ownership_override_required' : 'ready' },
  binding, authority);
  return { env, safeDirectory: ownership.overrideRequired, binding, authority };
}

function invalidBatch(size, reason) {
  const count = Math.max(1, Math.min(Number.isInteger(size) ? size : 1, 16));
  return Array(count).fill('[git context unavailable: ' + reason + ']');
}

function namedOperationSpecs(operationNames) {
  if (!Array.isArray(operationNames) || !operationNames.length
    || operationNames.length > 16) return null;
  const names = operationNames.slice();
  if (names.some((name) => typeof name !== 'string'
    || !Object.prototype.hasOwnProperty.call(GIT_OPERATIONS, name))
    || new Set(names).size !== names.length) return null;
  return Object.freeze(names.map((name) => GIT_OPERATIONS[name]));
}

function gitOutputs(root, operationNames, authority) {
  const specs = namedOperationSpecs(operationNames);
  if (!specs) return invalidBatch(Array.isArray(operationNames) ? operationNames.length : 1,
    'invalid named Git batch');
  try {
    const session = prepareGitSession(root, authority);
    if (session.empty) return specs.map(() => '');
    if (session.error) {
      return specs.map(() => '[git context unavailable: ' + session.error + ']');
    }
    const needsHeadProof = session.headState !== 'unborn'
      && !specs.includes(GIT_OPERATIONS.HEAD_SHA);
    const executed = needsHeadProof ? [GIT_OPERATIONS.HEAD_SHA, ...specs] : specs;
    const first = executeGitOutputs(session, executed);
    const second = executeGitOutputs(session, executed);
    const outputsMatch = first.every((value, index) => value === second[index]);
    const verified = needsHeadProof ? first.slice(1) : first;
    return outputsMatch && gitSessionStillValid(session) ? verified
      : specs.map(() => '[git context unavailable: Git storage changed during batch]');
  } catch (err) {
    return specs.map(() => '[git context unavailable: named Git batch command failed]');
  }
}

function configurationEvidence(ownership) {
  return { canonical_root_validated: true, git_metadata_validated: true,
    ownership_mismatch_observed: ownership.overrideRequired };
}

function executeGitOutputs(session, specs) {
  return specs.map((item) => executeGitOutput(
    session.canonicalRoot, item.args, item.maxChars, session.configuration
  ));
}

function gitOutput(root, operationName, authority) {
  return gitOutputs(root, [operationName], authority)[0];
}

function prepareGitSession(root, authority) {
  const rootCheck = validateGitExecutionRoot(root);
  if (rootCheck.empty || rootCheck.error) return rootCheck;
  let binding;
  try {
    binding = authority.bind(process.env);
  } catch (_err) {
    setGitReadiness(rootCheck.canonicalRoot, { canonical_root_validated: true,
      git_metadata_validated: true, reason: 'git_executable_unavailable' });
    return { error: 'Git executable unavailable' };
  }
  const configuration = validateGitConfiguration(
    rootCheck.canonicalRoot, rootCheck.receipt, binding, authority
  );
  if (configuration.error) return configuration;
  return {
    canonicalRoot: rootCheck.canonicalRoot,
    receipt: rootCheck.receipt,
    headState: rootCheck.headState,
    binding,
    authority,
    configuration,
    output: (args, maxChars) => executeGitOutputSafely(
      rootCheck.canonicalRoot, args, maxChars, configuration
    )
  };
}

function gitSessionStillValid(session) {
  const finalReceipt = registeredGitMetadataReceipt(
    session.canonicalRoot, { force: true }
  );
  try { session.authority.revalidate(session.binding); } catch (_err) { return false; }
  return finalReceipt.valid
    && finalReceipt.fingerprint === session.receipt.fingerprint
    && finalReceipt.worktree_config_state === session.receipt.worktree_config_state;
}

function executeGitOutputSafely(canonicalRoot, args, maxChars, configuration) {
  try {
    return executeGitOutput(canonicalRoot, args, maxChars, configuration);
  } catch (err) {
    const reason = err && err.message ? err.message.slice(0, 180) : 'unknown';
    return '[git context unavailable: ' + reason + ']';
  }
}

function executeGitOutput(canonicalRoot, args, maxChars, configuration) {
  const gitArgs = governedGitArgs(
    canonicalRoot, configuration.safeDirectory, args
  );
  const output = configuration.authority.execFileSync(configuration.binding, gitArgs, {
    cwd: canonicalRoot, encoding: 'utf8', env: configuration.env, timeout: 5000,
    maxBuffer: Math.max(maxChars * 4, 65536), windowsHide: true
  });
  return boundedGitOutput(String(output || ''), maxChars);
}

function boundedGitOutput(text, maxChars) {
  if (text.length <= maxChars) return text;
  const suffix = '\n' + GIT_OUTPUT_TRUNCATED_MARKER;
  return text.slice(0, Math.max(0, maxChars - suffix.length)) + suffix;
}

function prepareGitChanges(projection, root, authority) {
  try {
    const session = prepareGitSession(root, authority);
    if (session.empty || session.error) return session;
    const changed = projection.enumerate(
      session.canonicalRoot, session.output, session.headState
    );
    return changed === null
      ? { error: 'governed change enumeration failed' }
      : { canonicalRoot: session.canonicalRoot, changed, receipt: session.receipt,
        binding: session.binding, authority: session.authority };
  } catch (err) {
    const reason = err && err.message ? err.message.slice(0, 180) : 'unknown';
    return { error: reason };
  }
}

function samePreparedProjection(projection, left, right) {
  return sameCanonicalPath(left.canonicalRoot, right.canonicalRoot)
    && left.receipt.fingerprint === right.receipt.fingerprint
    && projection.changedSetDigest(left.changed)
      === projection.changedSetDigest(right.changed);
}

function failedSnapshot(reason) {
  const failed = '[git context unavailable: ' + reason + ']';
  return { status: failed, stat: failed, diff: failed };
}

function emptySnapshot() {
  return { status: '', stat: '', diff: '' };
}

function failedProjection(prepared) {
  if (prepared.empty) return '';
  return '[git context unavailable: ' + prepared.error + ']';
}

function governedGitProjection(projection, authority, root, kind, maxChars) {
  const limits = { status: 8000, stat: 8000, diff: 24000 };
  limits[kind] = maxChars;
  return governedGitSnapshotWithProjection(projection, authority, root, limits)[kind];
}

function governedGitSnapshotWithProjection(projection, authority, root, limits) {
  const caps = Object.assign({ status: 8000, stat: 8000, diff: 24000 }, limits);
  const first = prepareGitChanges(projection, root, authority);
  if (first.empty || first.error) {
    return first.empty ? emptySnapshot() : failedSnapshot(first.error);
  }
  const captured = projection.capture(first.canonicalRoot, first.changed);
  if (!captured) return failedSnapshot('governed projection capture failed');
  const render = (kind) => projection.render(captured, kind, caps[kind]);
  const rendered = { status: render('status'), stat: render('stat'), diff: render('diff') };
  const second = prepareGitChanges(projection, root, authority);
  if (second.empty || second.error || !samePreparedProjection(projection, first, second)) {
    return failedSnapshot('Git projection changed during snapshot');
  }
  const recaptured = projection.capture(second.canonicalRoot, second.changed);
  if (!recaptured || recaptured.contentDigest !== captured.contentDigest) {
    return failedSnapshot('worktree content changed during snapshot');
  }
  const finalCapture = projection.capture(second.canonicalRoot, second.changed);
  if (!finalCapture || finalCapture.contentDigest !== captured.contentDigest) {
    return failedSnapshot('worktree content changed before final proof');
  }
  const proof = finalProjectionReceipt(projection, authority, first, captured);
  return proof.error ? failedSnapshot(proof.error)
    : { ...rendered, projection_receipt: proof.receipt };
}

function finalProjectionReceipt(projection, authority, first, captured) {
  const finalGit = registeredGitMetadataReceipt(first.canonicalRoot, { force: true });
  if (!finalGit.valid || finalGit.fingerprint !== first.receipt.fingerprint
    || finalGit.worktree_config_state !== first.receipt.worktree_config_state) {
    return { error: 'Git storage changed during snapshot' };
  }
  let executable;
  try { executable = authority.revalidate(first.binding); }
  catch (_err) { return { error: 'Git executable changed during snapshot' }; }
  const publicExecutable = defaultGitExecutable.toPublicExecutableReceipt(executable);
  return { receipt: projection.receipt(
    first, captured, finalGit.fingerprint, publicExecutable
  ) };
}

function createProjectionApi(projection, authority) {
  const snapshot = (root, limits) =>
    governedGitSnapshotWithProjection(projection, authority, root, limits);
  return Object.freeze({
    gitOutput: (root, operation) => gitOutput(root, operation, authority),
    gitOutputs: (root, operations) => gitOutputs(root, operations, authority),
    governedRepoState: (root) => repoState.capture(
      root, (operations) => gitOutputs(root, operations, authority)
    ),
    governedGitReadiness, governedGitSnapshot: snapshot,
    governedGitStatus: (root, maxChars) =>
      governedGitProjection(projection, authority, root, 'status', maxChars),
    governedGitStat: (root, maxChars) =>
      governedGitProjection(projection, authority, root, 'stat', maxChars),
    governedGitDiff: (root, maxChars) =>
      governedGitProjection(projection, authority, root, 'diff', maxChars)
  });
}

const DEFAULT_API = createProjectionApi(
  projectionFactory.create(DEFAULT_POLICY), defaultGitExecutable
);

module.exports = { create, ...DEFAULT_API, GIT_OUTPUT_TRUNCATED_MARKER,
  GIT_REPO_STATE_SCHEMA: repoState.SCHEMA,
  GIT_PROJECTION_RECEIPT_SCHEMA: projectionFactory.SCHEMA,
  GIT_READINESS_SCHEMA };
