'use strict';

const path = require('path');
const health = require('./runtime_health_query');
const freshness = require('./model_freshness_query');

function classify(text) {
  if (health.isRuntimeHealthQuestion(text)) {
    return { path: health.LOCAL_FAST_PATH, reason: 'runtime_health_fast_path' };
  }
  if (freshness.isModelFreshnessQuestion(text)) {
    return { path: freshness.LOCAL_FAST_PATH, reason: 'model_freshness_fast_path' };
  }
  return null;
}

async function run(name, options) {
  if (name === health.LOCAL_FAST_PATH) {
    return health.runHoloIndexHealth(options);
  }
  if (name === freshness.LOCAL_FAST_PATH) {
    const receipt = await freshness.runConfiguredQuery({
      interpreter: options.interpreterPath,
      script: path.join(options.root, 'scripts', 'reddog_model_freshness_query_once.py'),
      repoRoot: options.root,
      env: catalogEnvironment(options.env),
      modelIds: [options.worker.lead].concat(options.worker.panel || [])
    });
    return freshness.buildLocalResult(receipt);
  }
  return null;
}

function catalogEnvironment(source) {
  const allowed = new Set([
    'APPDATA', 'HOME', 'LOCALAPPDATA', 'PROGRAMDATA', 'SYSTEMROOT',
    'TEMP', 'TMP', 'USERPROFILE', 'WINDIR'
  ]);
  const result = { PYTHONIOENCODING: 'utf-8', PYTHONUTF8: '1' };
  for (const [key, value] of Object.entries(source || {})) {
    if (allowed.has(String(key).toUpperCase()) && typeof value === 'string') result[key] = value;
  }
  return result;
}

module.exports = { catalogEnvironment, classify, run };
