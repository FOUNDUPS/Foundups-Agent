'use strict';

const { parentPort, workerData } = require('worker_threads');
const preflight = require('./backend_compatibility_preflight');

function run() {
  try {
    parentPort.postMessage(
      preflight.runBackendCompatibilityPreflight(workerData.root)
    );
  } catch (err) {
    parentPort.postMessage({
      checked: true,
      passed: false,
      rejection_reasons: ['backend_compatibility_worker_failed']
    });
  }
}

run();
