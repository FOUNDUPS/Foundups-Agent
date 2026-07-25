'use strict';

const constants = require('./backend_compatibility_constants');
const filesystem = require('./backend_compatibility_filesystem');
const runtimeDigestCache = new Map();

function stableUniqueStrings(value) {
  if (!Array.isArray(value) || value.some((item) => typeof item !== 'string')) {
    return null;
  }
  const result = value.slice().sort();
  return new Set(result).size === result.length ? result : null;
}

function arraysEqual(left, right) {
  return left.length === right.length
    && left.every((value, index) => value === right[index]);
}

function canonicalize(value) {
  if (Array.isArray(value)) {
    return value.map(canonicalize);
  }
  if (!value || typeof value !== 'object') {
    return value;
  }
  const result = {};
  for (const key of Object.keys(value).sort()) {
    result[key] = canonicalize(value[key]);
  }
  return result;
}

function validDigestMap(value, paths) {
  return !!value
    && typeof value === 'object'
    && !Array.isArray(value)
    && arraysEqual(Object.keys(value).sort(), paths.slice().sort())
    && Object.values(value).every(
      (digest) => typeof digest === 'string' && constants.SHA256_PATTERN.test(digest)
    );
}

function manifestContractLists(manifest) {
  return {
    bridges: stableUniqueStrings(manifest.required_bridge_files),
    executables: stableUniqueStrings(manifest.required_executable_files),
    markers: stableUniqueStrings(manifest.required_repository_markers),
    runtime: stableUniqueStrings(manifest.required_runtime_files)
  };
}

function validateManifestIdentity(manifest, reasons) {
  if (!arraysEqual(Object.keys(manifest).sort(), constants.MANIFEST_KEYS.slice().sort())) {
    reasons.push('backend_manifest_shape_invalid');
  }
  if (manifest.schema_version !== constants.BACKEND_MANIFEST_SCHEMA) {
    reasons.push('backend_manifest_schema_mismatch');
  }
  if (manifest.product !== constants.BACKEND_PRODUCT) {
    reasons.push('backend_product_mismatch');
  }
  if (manifest.backend_api_version !== constants.BACKEND_API_VERSION) {
    reasons.push('backend_api_version_mismatch');
  }
  if (manifest.runtime_dependency_graph_version !== constants.RUNTIME_DEPENDENCY_GRAPH_VERSION) {
    reasons.push('backend_runtime_graph_version_mismatch');
  }
}

function validateManifestLists(manifest, lists, reasons) {
  if (!lists.bridges || !arraysEqual(lists.bridges, constants.REQUIRED_BRIDGE_FILES.slice().sort())) {
    reasons.push('backend_bridge_contract_mismatch');
  }
  if (
    !lists.executables
    || !arraysEqual(lists.executables, constants.REQUIRED_EXECUTABLE_FILES.slice().sort())
  ) {
    reasons.push('backend_executable_contract_mismatch');
  }
  if (!lists.markers || !arraysEqual(lists.markers, constants.REQUIRED_REPOSITORY_MARKERS.slice().sort())) {
    reasons.push('backend_repository_marker_contract_mismatch');
  }
  if (
    !lists.runtime
    || !lists.runtime.length
    || lists.runtime.length > constants.MAX_RUNTIME_FILES
    || constants.REQUIRED_EXECUTABLE_FILES.some((item) => !lists.runtime.includes(item))
  ) {
    reasons.push('backend_runtime_file_contract_mismatch');
  }
}

function validateManifest(manifest) {
  const reasons = [];
  const lists = manifestContractLists(manifest);
  validateManifestIdentity(manifest, reasons);
  validateManifestLists(manifest, lists, reasons);
  if (!validDigestMap(manifest.required_bridge_sha256, constants.REQUIRED_BRIDGE_FILES)) {
    reasons.push('backend_bridge_digest_contract_mismatch');
  }
  if (!lists.runtime || !validDigestMap(manifest.required_runtime_sha256, lists.runtime)) {
    reasons.push('backend_runtime_digest_contract_mismatch');
  }
  if (
    lists.runtime
    && constants.REQUIRED_BRIDGE_FILES.some(
      (path) => manifest.required_bridge_sha256[path] !== manifest.required_runtime_sha256[path]
    )
  ) {
    reasons.push('backend_bridge_runtime_digest_mismatch');
  }
  return reasons;
}

function invalidManifest(reason, manifestDigest) {
  return { manifest: null, manifestDigest: manifestDigest || '', reason };
}

function cachedRuntimeDigest(located, expected) {
  if (!located.identity) {
    return '';
  }
  const cached = runtimeDigestCache.get(located.candidate);
  return cached
    && cached.identity === located.identity
    && cached.expected === expected
    ? cached.observed
    : '';
}

function rememberRuntimeDigest(located, expected, observed) {
  if (located.identity && observed === expected) {
    runtimeDigestCache.set(located.candidate, {
      identity: located.identity,
      expected,
      observed
    });
  }
}

function readManifest(rootState, deps) {
  const located = filesystem.containedRegularFile(
    rootState,
    constants.BACKEND_MANIFEST_PATH,
    deps
  );
  if (!located.ok) {
    return invalidManifest('backend_manifest_missing_or_unsafe');
  }
  try {
    const raw = deps.fs.readFileSync(located.candidate);
    if (raw.length <= 0 || raw.length > constants.MAX_MANIFEST_BYTES) {
      return invalidManifest('backend_manifest_size_invalid');
    }
    const manifest = JSON.parse(raw.toString('utf8'));
    if (!manifest || typeof manifest !== 'object' || Array.isArray(manifest)) {
      return invalidManifest('backend_manifest_invalid');
    }
    const canonical = Buffer.from(JSON.stringify(canonicalize(manifest)), 'utf8');
    const digest = filesystem.sha256Hex(canonical, deps.crypto);
    return digest === constants.EXPECTED_MANIFEST_SHA256
      ? { manifest, manifestDigest: digest, reason: '' }
      : invalidManifest('backend_manifest_integrity_mismatch', digest);
  } catch (err) {
    return invalidManifest('backend_manifest_invalid');
  }
}

function runtimeFileResult(relativePath, manifest, rootState, deps) {
  const bridge = constants.REQUIRED_BRIDGE_FILES.includes(relativePath);
  const missing = bridge ? 'required_bridge_missing_or_unsafe:' : 'required_runtime_file_missing_or_unsafe:';
  const mismatch = bridge ? 'required_bridge_integrity_mismatch:' : 'required_runtime_file_integrity_mismatch:';
  const located = filesystem.containedRegularFile(rootState, relativePath, deps);
  if (!located.ok || located.size > constants.MAX_RUNTIME_FILE_BYTES) {
    return { reason: missing + relativePath };
  }
  const expected = manifest.required_runtime_sha256[relativePath];
  const cached = cachedRuntimeDigest(located, expected);
  if (cached) {
    return { observed: cached, size: located.size, reason: '' };
  }
  try {
    const raw = deps.fs.readFileSync(located.candidate);
    const observed = filesystem.sha256Hex(
      filesystem.normalizedTextBytes(raw),
      deps.crypto
    );
    rememberRuntimeDigest(located, expected, observed);
    return observed === expected
      ? { observed, size: raw.length, reason: '' }
      : { observed, size: raw.length, reason: mismatch + relativePath };
  } catch (err) {
    return { reason: missing + relativePath };
  }
}

function verifyRuntimeFiles(rootState, manifest, deps) {
  const reasons = [];
  const observedDigests = {};
  let totalBytes = 0;
  for (const relativePath of manifest.required_runtime_files) {
    const result = runtimeFileResult(relativePath, manifest, rootState, deps);
    if (result.reason) {
      reasons.push(result.reason);
      continue;
    }
    totalBytes += result.size;
    observedDigests[relativePath] = result.observed;
  }
  if (totalBytes > constants.MAX_RUNTIME_TOTAL_BYTES) {
    reasons.push('backend_runtime_total_size_invalid');
  }
  return { reasons, observedDigests, totalBytes };
}

function verifyRepositoryMarkers(rootState, deps) {
  const reasons = [];
  for (const relativePath of constants.REQUIRED_REPOSITORY_MARKERS) {
    if (!filesystem.containedRegularFile(rootState, relativePath, deps).ok) {
      reasons.push('repository_marker_missing_or_unsafe:' + relativePath);
    }
  }
  return reasons;
}

module.exports = {
  clearRuntimeDigestCache: () => runtimeDigestCache.clear(),
  readManifest,
  validateManifest,
  verifyRepositoryMarkers,
  verifyRuntimeFiles
};
