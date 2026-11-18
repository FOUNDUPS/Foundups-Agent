'use strict';

const cp = require('child_process');
const { createOwnerProof } = require('./holoindex_owner_proof');
const interpreterPolicy = require('./start_operations_interpreter');
const runtimeMaterializer = require('./backend_compatibility_runtime_materializer');
const startOperationsBridge = require('./start_operations_bridge');

function createSealedPythonJsonRunner() {
  const outputProof = createOwnerProof((value) => Boolean(
    value && typeof value === 'object' && !Array.isArray(value)
  ));
  return Object.freeze({
    run(options) {
      const opts = options && typeof options === 'object' ? options : {};
      const runtime = interpreterPolicy.approved(opts.interpreter, opts.repoRoot);
      if (!runtime) throw new Error('unapproved_interpreter');
      const source = (opts.materialize || runtimeMaterializer.materialize)(
        runtime.repoRoot, opts.materializerOptions
      );
      try {
        const args = [
          '-I', '-S', '-B', source.scriptPath(startOperationsBridge.PYTHON_BOOTSTRAP),
          source.scriptPath(opts.script), source.runtimeRoot,
          source.targetRepoRoot, runtime.sitePackages,
          source.manifestPath, source.manifestDigest
        ];
        const stdout = (opts.execFileSync || cp.execFileSync)(runtime.interpreter, args, {
          cwd: source.runtimeRoot, input: JSON.stringify(opts.request || {}),
          encoding: 'utf8', env: startOperationsBridge.sealedEnvironment(opts.env, source, runtime),
          windowsHide: true, maxBuffer: Number(opts.maxBuffer || 262144)
        });
        const parsed = JSON.parse(stdout);
        const result = typeof opts.mapResult === 'function' ? opts.mapResult(parsed) : parsed;
        return outputProof.observe(result);
      } finally {
        source.cleanup();
      }
    },
    isAccepted(value) { return outputProof.isAccepted(value); }
  });
}

module.exports = { createSealedPythonJsonRunner };
