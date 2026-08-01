'use strict';

const BACKEND_MANIFEST_SCHEMA = 'reddog_backend_manifest.v3';
const BACKEND_PRODUCT = 'foundups-agent-reddog-backend';
const BACKEND_API_VERSION = 2;
const BACKEND_MANIFEST_PATH = 'scripts/reddog_backend_manifest.json';
const EXPECTED_MANIFEST_SHA256 = '510382693fda5fd5f01aeb0d1e047f743fcc3096b0932ce11a6ea4acc7eafb73';
const RUNTIME_DEPENDENCY_GRAPH_VERSION = 2;
const MAX_MANIFEST_BYTES = 256 * 1024;
const MAX_RUNTIME_FILE_BYTES = 2 * 1024 * 1024;
const MAX_RUNTIME_FILES = 1150;
const MAX_RUNTIME_TOTAL_BYTES = 32 * 1024 * 1024;
const REQUIRED_BRIDGE_FILES = Object.freeze([
  'scripts/advisory_model_once.py',
  'scripts/reddog_authoritative_work_state_query_once.py',
  'scripts/reddog_extension_live_enqueue_invoke_once.py',
  'scripts/reddog_extension_wre_spine_invoke_once.py',
  'scripts/reddog_github_permission_probe_once.py',
  'scripts/reddog_holoindex_owner_query_once.py',
  'scripts/reddog_judgment_verifier_once.py',
  'scripts/reddog_model_freshness_query_once.py',
  'scripts/reddog_model_runtime_binding_query_once.py',
  'scripts/reddog_operator_wardrobe_selection_once.py',
  'scripts/reddog_repair_guard_once.py',
  'scripts/reddog_resident_architect_session_once.py',
  'scripts/reddog_start_operations_control_once.py'
]);
const REQUIRED_EXECUTABLE_FILES = Object.freeze([
  ...REQUIRED_BRIDGE_FILES,
  'holo_index.py'
]);
const REQUIRED_REPOSITORY_MARKERS = Object.freeze([
  'main.py',
  'holo_index.py',
  'WSP_framework/src/WSP_97_System_Execution_Prompting_Protocol.md'
]);
const MANIFEST_KEYS = Object.freeze([
  'schema_version',
  'product',
  'backend_api_version',
  'runtime_dependency_graph_version',
  'required_executable_files',
  'required_bridge_files',
  'required_bridge_sha256',
  'required_runtime_files',
  'required_runtime_sha256',
  'required_repository_markers'
]);
const SHA256_PATTERN = /^[a-f0-9]{64}$/;

module.exports = {
  BACKEND_API_VERSION,
  BACKEND_MANIFEST_PATH,
  BACKEND_MANIFEST_SCHEMA,
  BACKEND_PRODUCT,
  EXPECTED_MANIFEST_SHA256,
  MANIFEST_KEYS,
  MAX_MANIFEST_BYTES,
  MAX_RUNTIME_FILE_BYTES,
  MAX_RUNTIME_FILES,
  MAX_RUNTIME_TOTAL_BYTES,
  REQUIRED_BRIDGE_FILES,
  REQUIRED_EXECUTABLE_FILES,
  REQUIRED_REPOSITORY_MARKERS,
  RUNTIME_DEPENDENCY_GRAPH_VERSION,
  SHA256_PATTERN
};
