'use strict';

const execution = require('./reddog_contract_execution');
const plan = require('./reddog_test_plan');
const supervisor = require('./reddog_release_supervisor');

async function main() {
  const startedAt = Date.now();
  const aggregate = execution.loadShards();
  plan.validateAggregateMembership(aggregate);
  const receipt = await supervisor.runPromotion(plan.RELEASE_GROUPS, { startedAt });
  supervisor.printReceipt(receipt);
  if (!receipt.passed) process.exitCode = 1;
}

main().catch((error) => {
  console.error('[REDDOG-RELEASE] status=FAIL ' + String(error && error.stack || error));
  process.exitCode = 1;
});
