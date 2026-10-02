import assert from "node:assert/strict";
import test from "node:test";
import {
  DECISION_BLOCK,
  DECISION_SEND,
  PROVIDER_SENT_INTEGRITY_INCIDENT,
  PROVIDER_STATE_UNKNOWN,
  VERIFIED_SENT,
  buildRecipientPreflightReceipt,
  digestContent,
  executeSenderBoundary,
  prepareRecipientPreflightReceipt,
  sha256Hex,
  transactionDigest,
} from "../host/reddog_correspondence_sender_boundary.mjs";

const BODY = "Council reply body\n";
const isoOffset = (ms) => new Date(Date.now() + ms).toISOString();

function tx(operation="send_draft") {
  return {
    provider:"gmail",
    operation,
    scope_key:"FUKUI_CITY::COUNCIL::CHAIR_CIRCULATION",
    purpose:"Request Chair circulation with updated three-site PPP context",
    recipients:[
      {identity_id:"YMC-0145",role:"TO",address:"giji@city.fukui.lg.jp"},
      {identity_id:"YMC-0147",role:"CC",address:"yumori.commission@foundups.org"},
      {identity_id:"YMC-0118",role:"BCC",address:"okami@kisaki777.jp"},
    ],
    content_digest:digestContent(BODY),
    draft_id:operation === "send_draft" ? "draft-1" : null,
    draft_message_id:operation === "send_draft" ? "draft-mid-1" : null,
    reply_message_id:operation === "reply" ? "inbound-1" : null,
    thread_id:"thread-1",
  };
}

function evidence() {
  return [
    {identity_id:"YMC-0145",address:"giji@city.fukui.lg.jp",source:"provider reply-to",level:"EXPLICIT_PROVIDER",policy:"ORGANIZATION_ONLY",entity_kind:"organization",current:true,verified:true},
    {identity_id:"YMC-0147",address:"yumori.commission@foundups.org",source:"routing",level:"ROUTING_POLICY",policy:"ALLOW",entity_kind:"organization",current:true,verified:true},
    {identity_id:"YMC-0118",address:"okami@kisaki777.jp",source:"routing",level:"ROUTING_POLICY",policy:"BCC_ONLY",entity_kind:"person",current:true,verified:true},
  ];
}

class Provider {
  constructor(transaction) {
    this.transaction=transaction;
    this.messageIds=[];
    this.sentAddresses=[];
    this.draftPatch={};
    this.sentPatch={};
    this.submitError=false;
    this.readbackError=false;
    this.calls={coverage:0,draft:0,submit:0,sent:0};
  }
  async readSentCoverage() {
    this.calls.coverage += 1;
    return {message_ids:[...this.messageIds],already_sent_addresses:[...this.sentAddresses]};
  }
  async readDraft() {
    this.calls.draft += 1;
    const roles=rolesFor(this.transaction);
    return {
      message_id:this.transaction.draft_message_id,
      thread_id:this.transaction.thread_id,
      body:BODY,
      to:roles.to,cc:roles.cc,bcc:roles.bcc,
      ...this.draftPatch,
    };
  }
  async submit() {
    this.calls.submit += 1;
    if (this.submitError) throw new Error("ambiguous provider failure");
    return {id:"sent-mid-1",threadId:this.transaction.thread_id};
  }
  async readSent() {
    this.calls.sent += 1;
    if (this.readbackError) throw new Error("readback failed");
    const roles=rolesFor(this.transaction);
    return {
      id:"sent-mid-1",thread_id:this.transaction.thread_id,
      to:roles.to,cc:roles.cc,bcc:roles.bcc,
      ...this.sentPatch,
    };
  }
}

function rolesFor(transaction) {
  const result={to:[],cc:[],bcc:[]};
  for (const recipient of transaction.recipients) result[recipient.role.toLowerCase()].push(recipient.address);
  return result;
}

async function sendReceipt(transaction, provider, issuedAt=isoOffset(-1000), ttlSeconds=120) {
  return prepareRecipientPreflightReceipt({
    transaction,evidence:evidence(),provider,issuedAt,ttlSeconds,
  });
}

test("pure sha256 implementation is standard", () => {
  assert.equal(sha256Hex("abc"),"ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
});

test("receipt binds scope purpose operation identities roles addresses content and sent coverage", async () => {
  const transaction=tx();
  const provider=new Provider(transaction);
  const receipt=await sendReceipt(transaction,provider);
  assert.equal(receipt.decision,DECISION_SEND);
  assert.match(receipt.transaction_digest,/^sha256:[0-9a-f]{64}$/);
  assert.match(receipt.receipt_digest,/^sha256:[0-9a-f]{64}$/);
  assert.equal(receipt.checks.length,3);
  assert.ok(receipt.checks.every((check)=>check.allowed && check.exact_match && !check.duplicate_coverage));
  const changed={...transaction,purpose:"different purpose"};
  assert.notEqual(transactionDigest(transaction),transactionDigest(changed));
});

test("unknown or unverified route produces BLOCK receipt", () => {
  const transaction=tx("reply");
  const blocked=buildRecipientPreflightReceipt({
    transaction,
    evidence:evidence().filter((item)=>item.identity_id !== "YMC-0118"),
    sentCoverage:{message_ids:[],already_sent_addresses:[]},
    issuedAt:isoOffset(-1000),
  });
  assert.equal(blocked.decision,DECISION_BLOCK);
  assert.ok(blocked.reasons.includes("YMC-0118:UNKNOWN_ROUTE"));
});

test("duplicate Sent coverage produces BLOCK receipt", () => {
  const transaction=tx("reply");
  const blocked=buildRecipientPreflightReceipt({
    transaction,evidence:evidence(),
    sentCoverage:{message_ids:["sent-old"],already_sent_addresses:["giji@city.fukui.lg.jp"]},
    issuedAt:isoOffset(-1000),
  });
  assert.equal(blocked.decision,DECISION_BLOCK);
  assert.ok(blocked.reasons.includes("YMC-0145:DUPLICATE_SENT_COVERAGE"));
});

test("missing receipt makes provider entirely unreachable", async () => {
  const transaction=tx();
  const provider=new Provider(transaction);
  const result=await executeSenderBoundary({transaction,receipt:null,provider});
  assert.equal(result.decision,DECISION_BLOCK);
  assert.deepEqual(result.reasons,["MISSING_PREFLIGHT_RECEIPT"]);
  assert.deepEqual(provider.calls,{coverage:0,draft:0,submit:0,sent:0});
});

test("BLOCK receipt cannot reach provider mutation", async () => {
  const transaction=tx();
  const provider=new Provider(transaction);
  const receipt=await prepareRecipientPreflightReceipt({
    transaction,
    evidence:evidence().map((item)=>item.identity_id === "YMC-0145" ? {...item,address:"wrong@city.fukui.lg.jp"} : item),
    provider,issuedAt:isoOffset(-1000),
  });
  assert.equal(receipt.decision,DECISION_BLOCK);
  const result=await executeSenderBoundary({transaction,receipt,provider});
  assert.equal(result.decision,DECISION_BLOCK);
  assert.ok(result.reasons.includes("PREFLIGHT_NOT_SEND"));
  assert.equal(provider.calls.submit,0);
});

test("stale receipt blocks before any second provider read or mutation", async () => {
  const transaction=tx();
  const provider=new Provider(transaction);
  const receipt=await sendReceipt(transaction,provider,isoOffset(-120000),30);
  const before={...provider.calls};
  const result=await executeSenderBoundary({transaction,receipt,provider});
  assert.equal(result.decision,DECISION_BLOCK);
  assert.ok(result.reasons.includes("STALE_PREFLIGHT_RECEIPT"));
  assert.deepEqual(provider.calls,before);
});

test("transaction substitution blocks before provider mutation", async () => {
  const transaction=tx();
  const provider=new Provider(transaction);
  const receipt=await sendReceipt(transaction,provider);
  const changed={...transaction,content_digest:digestContent("changed")};
  const result=await executeSenderBoundary({transaction:changed,receipt,provider});
  assert.equal(result.decision,DECISION_BLOCK);
  assert.ok(result.reasons.includes("TRANSACTION_MISMATCH"));
  assert.equal(provider.calls.submit,0);
});

test("new Sent event after receipt invalidates coverage before provider mutation", async () => {
  const transaction=tx();
  const provider=new Provider(transaction);
  const receipt=await sendReceipt(transaction,provider);
  provider.messageIds.push("concurrent-send-mid");
  const result=await executeSenderBoundary({transaction,receipt,provider});
  assert.equal(result.decision,DECISION_BLOCK);
  assert.deepEqual(result.reasons,["STALE_SENT_COVERAGE"]);
  assert.equal(provider.calls.submit,0);
});

test("changed draft recipients fail closed before send_draft", async () => {
  const transaction=tx();
  const provider=new Provider(transaction);
  const receipt=await sendReceipt(transaction,provider);
  provider.draftPatch={bcc:["wrong@example.org"]};
  const result=await executeSenderBoundary({transaction,receipt,provider});
  assert.equal(result.decision,DECISION_BLOCK);
  assert.ok(result.reasons.includes("SENT_READBACK_MISSING_RECIPIENT"));
  assert.ok(result.reasons.includes("SENT_READBACK_EXTRA_RECIPIENT"));
  assert.equal(provider.calls.submit,0);
});

test("changed draft body fails closed before send_draft", async () => {
  const transaction=tx();
  const provider=new Provider(transaction);
  const receipt=await sendReceipt(transaction,provider);
  provider.draftPatch={body:"mutated body"};
  const result=await executeSenderBoundary({transaction,receipt,provider});
  assert.equal(result.decision,DECISION_BLOCK);
  assert.deepEqual(result.reasons,["DRAFT_CONTENT_MISMATCH"]);
  assert.equal(provider.calls.submit,0);
});

for (const operation of ["send_email","reply","delivery_repair"]) {
  test(operation + " uses the same receipt-enforced boundary", async () => {
    const transaction=tx(operation);
    const provider=new Provider(transaction);
    const receipt=await sendReceipt(transaction,provider);
    const result=await executeSenderBoundary({transaction,receipt,provider});
    assert.equal(result.decision,VERIFIED_SENT);
    assert.equal(provider.calls.submit,1);
    assert.equal(provider.calls.sent,1);
    assert.equal(provider.calls.draft,0);
  });
}

test("send_draft exact transaction reaches provider once and requires exact Sent readback", async () => {
  const transaction=tx();
  const provider=new Provider(transaction);
  const receipt=await sendReceipt(transaction,provider);
  const result=await executeSenderBoundary({transaction,receipt,provider});
  assert.equal(result.decision,VERIFIED_SENT);
  assert.equal(result.provider_invoked,true);
  assert.deepEqual(provider.calls,{coverage:2,draft:1,submit:1,sent:1});
  assert.deepEqual(result.readback,{id:"sent-mid-1",thread_id:"thread-1"});
});

test("post-send recipient mismatch is an integrity incident, never VERIFIED_SENT", async () => {
  const transaction=tx();
  const provider=new Provider(transaction);
  const receipt=await sendReceipt(transaction,provider);
  provider.sentPatch={cc:[]};
  const result=await executeSenderBoundary({transaction,receipt,provider});
  assert.equal(result.decision,PROVIDER_SENT_INTEGRITY_INCIDENT);
  assert.ok(result.reasons.includes("SENT_READBACK_MISSING_RECIPIENT"));
  assert.equal(provider.calls.submit,1);
});

test("provider exception is state unknown and cannot be treated as retry permission", async () => {
  const transaction=tx();
  const provider=new Provider(transaction);
  const receipt=await sendReceipt(transaction,provider);
  provider.submitError=true;
  const result=await executeSenderBoundary({transaction,receipt,provider});
  assert.equal(result.decision,PROVIDER_STATE_UNKNOWN);
  assert.deepEqual(result.reasons,["PROVIDER_SEND_RAISED_RECONCILE_BEFORE_RETRY"]);
  assert.equal(provider.calls.submit,1);
  assert.equal(provider.calls.sent,0);
});

test("post-send readback failure is an integrity incident", async () => {
  const transaction=tx();
  const provider=new Provider(transaction);
  const receipt=await sendReceipt(transaction,provider);
  provider.readbackError=true;
  const result=await executeSenderBoundary({transaction,receipt,provider});
  assert.equal(result.decision,PROVIDER_SENT_INTEGRITY_INCIDENT);
  assert.deepEqual(result.reasons,["PROVIDER_READBACK_FAILED"]);
  assert.equal(provider.calls.submit,1);
});
