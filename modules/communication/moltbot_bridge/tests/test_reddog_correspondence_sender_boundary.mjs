import test from "node:test";
import assert from "node:assert/strict";
import {
  buildRecipientPreflightReceipt, prepareRecipientPreflightReceipt,
  executeSenderBoundary,
} from "../host/reddog_correspondence_sender_boundary.mjs";

// v2's successful composer-built receipt was not an authenticated authority.
// Freeze the retired bypass: even a fabricated SEND must never invoke callbacks.
for (const operation of ["send_email", "reply", "send_draft", "delivery_repair",
                         "create_draft", "update_draft", "scheduled_send"]) {
  test(`quarantined V8 ${operation} has zero provider calls`, async () => {
    let calls = 0;
    const provider = new Proxy({}, {get: () => async () => { calls++; return {}; }});
    const args = {transaction:{operation}, receipt:{decision:"SEND",checks:[]}, provider};
    assert.equal(buildRecipientPreflightReceipt(args).decision, "BLOCK");
    assert.equal((await prepareRecipientPreflightReceipt(args)).decision, "BLOCK");
    const result = await executeSenderBoundary(args);
    assert.equal(result.decision, "BLOCK");
    assert.equal(result.provider_invoked, false);
    assert.equal(calls, 0);
  });
}
