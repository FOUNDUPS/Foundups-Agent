'use strict';

const execution = require('./reddog_contract_execution');
const plan = require('./reddog_test_plan');

function parseInvocation(argv, env) {
  if (argv.length !== 5 || argv[2] !== '--reddog-release-worker') {
    throw new Error('internal RedDog release worker invocation required');
  }
  const group = plan.RELEASE_GROUPS.find((entry) => entry.id === argv[3]);
  const nonce = argv[4];
  if (!group || !/^[a-f0-9]{32}$/.test(nonce) || env.REDDOG_RELEASE_PARENT_NONCE !== nonce) {
    throw new Error('invalid RedDog release worker parent binding');
  }
  return group;
}

function main() {
  const group = parseInvocation(process.argv, process.env);
  const aggregate = execution.loadShards();
  plan.validateAggregateMembership(aggregate);
  if (group.id === 'core') execution.runCore(aggregate);
  else execution.runGroup(group);
}

if (require.main === module) {
  try { main(); }
  catch (error) {
    console.error('[REDDOG-RELEASE-WORKER] status=FAIL ' + String(error && error.stack || error));
    process.exitCode = 1;
  }
}

module.exports = Object.freeze({ parseInvocation });
