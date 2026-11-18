'use strict';

const { parentPort, workerData } = require('worker_threads');
const owner = require('./holoindex_generation_bound_query');

function run() {
  const result = owner.runOwnerQuery(workerData);
  parentPort.postMessage({ result, accepted: owner.isAccepted(result) });
}

try {
  run();
} catch (_err) {
  parentPort.postMessage({
    result: { error: 'holoindex_health_worker_failed' },
    accepted: false
  });
}
