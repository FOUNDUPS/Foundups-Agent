/*
 * RedDog correspondence sender boundary.
 *
 * This dependency-free host adapter is intentionally loadable both by Node and
 * by the ChatGPT code-mode V8 isolate. It is the mandatory final seam between
 * a recipient-preflight SEND receipt and a provider mutation.
 */

export const RECEIPT_SCHEMA = "reddog-correspondence-preflight.v2";
export const MAX_RECEIPT_TTL_SECONDS = 300;
export const SUPPORTED_OPERATIONS = Object.freeze([
  "send_email",
  "reply",
  "send_draft",
  "delivery_repair",
]);
export const DECISION_SEND = "SEND";
export const DECISION_BLOCK = "BLOCK";
export const VERIFIED_SENT = "VERIFIED_SENT";
export const PROVIDER_SENT_INTEGRITY_INCIDENT = "PROVIDER_SENT_INTEGRITY_INCIDENT";
export const PROVIDER_STATE_UNKNOWN = "PROVIDER_STATE_UNKNOWN";

const ROLE_ORDER = Object.freeze({ TO: 0, CC: 1, BCC: 2 });
const LEVELS = Object.freeze({
  PUBLIC_DIRECTORY: 10,
  PRIOR_THREAD: 20,
  CONTACTS: 30,
  ROUTING_POLICY: 40,
  EXPLICIT_PROVIDER: 50,
});
const CLOSED_POLICIES = new Set(["DO_NOT_ADDRESS_OR_CC", "PERSONAL_ROUTE_CLOSED"]);

function fail(code) {
  const error = new Error(code);
  error.code = code;
  throw error;
}

function utf8Bytes(value) {
  const bytes = [];
  for (let i = 0; i < value.length; i += 1) {
    let code = value.charCodeAt(i);
    if (code >= 0xd800 && code <= 0xdbff && i + 1 < value.length) {
      const low = value.charCodeAt(i + 1);
      if (low >= 0xdc00 && low <= 0xdfff) {
        code = 0x10000 + ((code - 0xd800) << 10) + (low - 0xdc00);
        i += 1;
      }
    }
    if (code <= 0x7f) bytes.push(code);
    else if (code <= 0x7ff) {
      bytes.push(0xc0 | (code >> 6), 0x80 | (code & 0x3f));
    } else if (code <= 0xffff) {
      bytes.push(0xe0 | (code >> 12), 0x80 | ((code >> 6) & 0x3f), 0x80 | (code & 0x3f));
    } else {
      bytes.push(
        0xf0 | (code >> 18),
        0x80 | ((code >> 12) & 0x3f),
        0x80 | ((code >> 6) & 0x3f),
        0x80 | (code & 0x3f),
      );
    }
  }
  return bytes;
}

function rotr(value, bits) {
  return (value >>> bits) | (value << (32 - bits));
}

export function sha256Hex(value) {
  const bytes = utf8Bytes(String(value));
  const bitLength = bytes.length * 8;
  bytes.push(0x80);
  while ((bytes.length % 64) !== 56) bytes.push(0);
  const hi = Math.floor(bitLength / 0x100000000);
  const lo = bitLength >>> 0;
  for (let shift = 24; shift >= 0; shift -= 8) bytes.push((hi >>> shift) & 0xff);
  for (let shift = 24; shift >= 0; shift -= 8) bytes.push((lo >>> shift) & 0xff);

  const k = [
    0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
    0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
    0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
    0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
    0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
    0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
    0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
    0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2,
  ];
  const h = [0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19];
  const w = new Array(64);

  for (let offset = 0; offset < bytes.length; offset += 64) {
    for (let i = 0; i < 16; i += 1) {
      const j = offset + i * 4;
      w[i] = ((bytes[j] << 24) | (bytes[j+1] << 16) | (bytes[j+2] << 8) | bytes[j+3]) >>> 0;
    }
    for (let i = 16; i < 64; i += 1) {
      const s0 = rotr(w[i-15],7) ^ rotr(w[i-15],18) ^ (w[i-15] >>> 3);
      const s1 = rotr(w[i-2],17) ^ rotr(w[i-2],19) ^ (w[i-2] >>> 10);
      w[i] = (w[i-16] + s0 + w[i-7] + s1) >>> 0;
    }
    let [a,b,c,d,e,f,g,hh] = h;
    for (let i = 0; i < 64; i += 1) {
      const s1 = rotr(e,6) ^ rotr(e,11) ^ rotr(e,25);
      const ch = (e & f) ^ ((~e) & g);
      const t1 = (hh + s1 + ch + k[i] + w[i]) >>> 0;
      const s0 = rotr(a,2) ^ rotr(a,13) ^ rotr(a,22);
      const maj = (a & b) ^ (a & c) ^ (b & c);
      const t2 = (s0 + maj) >>> 0;
      hh=g; g=f; f=e; e=(d+t1)>>>0; d=c; c=b; b=a; a=(t1+t2)>>>0;
    }
    h[0]=(h[0]+a)>>>0; h[1]=(h[1]+b)>>>0; h[2]=(h[2]+c)>>>0; h[3]=(h[3]+d)>>>0;
    h[4]=(h[4]+e)>>>0; h[5]=(h[5]+f)>>>0; h[6]=(h[6]+g)>>>0; h[7]=(h[7]+hh)>>>0;
  }
  return h.map((value) => value.toString(16).padStart(8,"0")).join("");
}

function canonicalize(value) {
  if (Array.isArray(value)) return value.map(canonicalize);
  if (value && typeof value === "object") {
    const result = {};
    for (const key of Object.keys(value).sort()) {
      if (value[key] !== undefined) result[key] = canonicalize(value[key]);
    }
    return result;
  }
  return value;
}

export function stableStringify(value) {
  return JSON.stringify(canonicalize(value));
}

export function digestValue(value) {
  return "sha256:" + sha256Hex(stableStringify(value));
}

export function digestContent(body) {
  return "sha256:" + sha256Hex(String(body));
}

export function normalizeAddress(value) {
  if (typeof value !== "string" || !value.trim()) fail("INVALID_ADDRESS");
  const trimmed = value.trim();
  const match = trimmed.match(/<([^<>]+)>\s*$/);
  return (match ? match[1] : trimmed).trim().toLowerCase();
}

function normalizeLevel(value) {
  if (Number.isInteger(value)) return value;
  if (typeof value === "string" && Object.prototype.hasOwnProperty.call(LEVELS, value)) return LEVELS[value];
  fail("INVALID_EVIDENCE_LEVEL");
}

function normalizeRecipient(value) {
  if (!value || typeof value !== "object") fail("INVALID_RECIPIENT");
  if (typeof value.identity_id !== "string" || !value.identity_id) fail("INVALID_IDENTITY_ID");
  if (!Object.prototype.hasOwnProperty.call(ROLE_ORDER, value.role)) fail("INVALID_RECIPIENT_ROLE");
  return { identity_id:value.identity_id, role:value.role, address:normalizeAddress(value.address) };
}

function normalizeTransaction(value) {
  if (!value || typeof value !== "object") fail("INVALID_TRANSACTION");
  if (value.provider !== "gmail") fail("UNSUPPORTED_PROVIDER");
  if (!SUPPORTED_OPERATIONS.includes(value.operation)) fail("UNSUPPORTED_OPERATION");
  if (typeof value.scope_key !== "string" || !value.scope_key) fail("INVALID_SCOPE_KEY");
  if (typeof value.purpose !== "string" || !value.purpose) fail("INVALID_PURPOSE");
  if (!Array.isArray(value.recipients) || !value.recipients.length) fail("EMPTY_RECIPIENT_SET");
  if (typeof value.content_digest !== "string" || !/^sha256:[0-9a-f]{64}$/.test(value.content_digest)) fail("INVALID_CONTENT_DIGEST");
  const recipients = value.recipients.map(normalizeRecipient);
  return {
    provider:value.provider, operation:value.operation, scope_key:value.scope_key, purpose:value.purpose,
    recipients, content_digest:value.content_digest, draft_id:value.draft_id || null,
    draft_message_id:value.draft_message_id || null, reply_message_id:value.reply_message_id || null,
    thread_id:value.thread_id || null,
  };
}

function normalizedEvidence(evidence) {
  if (!Array.isArray(evidence)) fail("INVALID_EVIDENCE");
  return evidence.map((item) => ({
    identity_id:item.identity_id,
    address:normalizeAddress(item.address),
    source:String(item.source || ""),
    level:normalizeLevel(item.level),
    policy:item.policy || null,
    entity_kind:item.entity_kind || "organization",
    current:item.current !== false,
    verified:item.verified !== false,
  }));
}

function resolveAddress(identityId, evidence) {
  const current = evidence.filter((item) => item.identity_id === identityId && item.current);
  if (!current.length) return { route:null, reasons:["UNKNOWN_ROUTE"] };
  const verified = current.filter((item) => item.verified);
  if (!verified.length) return { route:null, reasons:["UNVERIFIED_ROUTE"] };
  const topLevel = Math.max(...verified.map((item) => item.level));
  const top = verified.filter((item) => item.level === topLevel);
  if (new Set(top.map((item) => item.address)).size !== 1) return { route:null, reasons:["CONFLICTING_AUTHORITATIVE_ADDRESSES"] };
  return { route:top[0], reasons:[] };
}

function resolvePolicy(identityId, evidence) {
  const current = evidence.filter((item) => item.identity_id === identityId && item.current && item.policy);
  if (!current.length) return { policy:"ALLOW", reasons:[] };
  const topLevel = Math.max(...current.map((item) => item.level));
  const top = current.filter((item) => item.level === topLevel);
  const policies = new Set(top.map((item) => item.policy));
  if (policies.size !== 1) return { policy:"ALLOW", reasons:["CONFLICTING_AUTHORITATIVE_POLICIES"] };
  return { policy:top[0], reasons:[] };
}

export function buildSentCoverage(value={}) {
  const ids = Array.isArray(value.message_ids) ? value.message_ids : fail("INVALID_SENT_MESSAGE_IDS");
  const addresses = Array.isArray(value.already_sent_addresses) ? value.already_sent_addresses : [];
  const messageIds = [...new Set(ids.map((item) => String(item)))].sort();
  const sentAddresses = [...new Set(addresses.map(normalizeAddress))].sort();
  return {
    message_ids:messageIds,
    already_sent_addresses:sentAddresses,
    watermark:digestValue({message_ids:messageIds}),
    coverage_digest:digestValue({message_ids:messageIds,already_sent_addresses:sentAddresses}),
  };
}

function buildChecks(transaction, evidence, sentCoverage) {
  const sent = new Set(sentCoverage.already_sent_addresses);
  const seen = new Set();
  const checks = [];
  const reasons = [];
  for (const recipient of transaction.recipients) {
    const local = [];
    if (seen.has(recipient.address)) local.push("DUPLICATE_RECIPIENT_IN_TRANSACTION");
    seen.add(recipient.address);
    const addressResult = resolveAddress(recipient.identity_id, evidence);
    const policyResult = resolvePolicy(recipient.identity_id, evidence);
    local.push(...addressResult.reasons, ...policyResult.reasons);
    const route = addressResult.route;
    const exact = Boolean(route && route.address === recipient.address);
    if (route && !exact) local.push("EXACT_ADDRESS_MISMATCH");
    if (CLOSED_POLICIES.has(policyResult.policy)) local.push(policyResult.policy);
    if (policyResult.policy === "BCC_ONLY" && recipient.role !== "BCC") local.push("ROLE_POLICY_VIOLATION_BCC_ONLY");
    if (policyResult.policy === "ORGANIZATION_ONLY" && route && route.entity_kind !== "organization") local.push("ROLE_POLICY_VIOLATION_ORGANIZATION_ONLY");
    const duplicate = sent.has(recipient.address);
    if (duplicate) local.push("DUPLICATE_SENT_COVERAGE");
    const check = {
      identity_id:recipient.identity_id, role:recipient.role, proposed_address:recipient.address,
      authoritative_address:route ? route.address : null, authoritative_source:route ? route.source : null,
      evidence_level:route ? route.level : null, policy:policyResult.policy, exact_match:exact,
      duplicate_coverage:duplicate, allowed:local.length === 0, reasons:local,
    };
    checks.push(check);
    for (const reason of local) reasons.push(recipient.identity_id + ":" + reason);
  }
  return { checks, reasons };
}

export function transactionDigest(value) {
  const tx = normalizeTransaction(value);
  const recipients = [...tx.recipients].sort((a,b) =>
    ROLE_ORDER[a.role]-ROLE_ORDER[b.role] || a.identity_id.localeCompare(b.identity_id) || a.address.localeCompare(b.address));
  return digestValue({...tx, recipients});
}

function receiptDigest(receipt) {
  const copy = {...receipt};
  delete copy.receipt_digest;
  return digestValue(copy);
}

export function buildRecipientPreflightReceipt({transaction,evidence,sentCoverage,issuedAt,ttlSeconds=120}) {
  const tx = normalizeTransaction(transaction);
  const ev = normalizedEvidence(evidence);
  const coverage = buildSentCoverage(sentCoverage);
  const issuedMs = Date.parse(issuedAt);
  if (!Number.isFinite(issuedMs)) fail("INVALID_RECEIPT_TIME");
  if (!Number.isInteger(ttlSeconds) || ttlSeconds <= 0 || ttlSeconds > MAX_RECEIPT_TTL_SECONDS) fail("INVALID_RECEIPT_TTL");
  const result = buildChecks(tx, ev, coverage);
  const receipt = {
    schema:RECEIPT_SCHEMA,
    decision:result.reasons.length ? DECISION_BLOCK : DECISION_SEND,
    issued_at:new Date(issuedMs).toISOString(),
    expires_at:new Date(issuedMs + ttlSeconds*1000).toISOString(),
    transaction_digest:transactionDigest(tx),
    sent_watermark:coverage.watermark,
    sent_coverage_digest:coverage.coverage_digest,
    checks:result.checks,
    reasons:result.reasons,
  };
  return {...receipt, receipt_digest:receiptDigest(receipt)};
}

export async function prepareRecipientPreflightReceipt({transaction,evidence,provider,issuedAt,ttlSeconds=120}) {
  if (!provider || typeof provider.readSentCoverage !== "function") fail("MISSING_SENT_COVERAGE_READER");
  const current = await provider.readSentCoverage(normalizeTransaction(transaction));
  return buildRecipientPreflightReceipt({transaction,evidence,sentCoverage:current,issuedAt,ttlSeconds});
}

function validateReceipt(transaction, receipt, now) {
  const reasons = [];
  if (!receipt || typeof receipt !== "object") return ["MISSING_PREFLIGHT_RECEIPT"];
  if (receipt.schema !== RECEIPT_SCHEMA) reasons.push("INVALID_RECEIPT_SCHEMA");
  if (receipt.decision !== DECISION_SEND) reasons.push("PREFLIGHT_NOT_SEND");
  const nowMs=Date.parse(now), issuedMs=Date.parse(receipt.issued_at), expiresMs=Date.parse(receipt.expires_at);
  if (![nowMs,issuedMs,expiresMs].every(Number.isFinite)) reasons.push("INVALID_RECEIPT_TIME");
  else {
    if (expiresMs <= issuedMs || expiresMs-issuedMs > MAX_RECEIPT_TTL_SECONDS*1000) reasons.push("INVALID_RECEIPT_WINDOW");
    if (nowMs < issuedMs) reasons.push("PREFLIGHT_NOT_YET_VALID");
    if (nowMs > expiresMs) reasons.push("STALE_PREFLIGHT_RECEIPT");
  }
  if (receipt.transaction_digest !== transactionDigest(transaction)) reasons.push("TRANSACTION_MISMATCH");
  if (receipt.receipt_digest !== receiptDigest(receipt)) reasons.push("RECEIPT_DIGEST_MISMATCH");
  if (!Array.isArray(receipt.checks) || receipt.checks.some((check) => !check.allowed || !check.exact_match || check.duplicate_coverage)) reasons.push("INVALID_SEND_CHECKS");
  return [...new Set(reasons)];
}

function expectedByRole(transaction) {
  const result = {TO:[],CC:[],BCC:[]};
  for (const recipient of normalizeTransaction(transaction).recipients) result[recipient.role].push(recipient.address);
  for (const role of Object.keys(result)) result[role] = [...new Set(result[role])].sort();
  return result;
}

function observedByRole(snapshot) {
  const result = {};
  for (const role of ["TO","CC","BCC"]) {
    const key = role.toLowerCase();
    const values = snapshot && Array.isArray(snapshot[key]) ? snapshot[key] : [];
    result[role] = [...new Set(values.map(normalizeAddress))].sort();
  }
  return result;
}

function recipientReadbackReasons(transaction, snapshot) {
  const expected=expectedByRole(transaction), observed=observedByRole(snapshot);
  const reasons=[];
  for (const role of ["TO","CC","BCC"]) {
    const e=new Set(expected[role]), o=new Set(observed[role]);
    if (expected[role].some((address)=>!o.has(address))) reasons.push("SENT_READBACK_MISSING_RECIPIENT");
    if (observed[role].some((address)=>!e.has(address))) reasons.push("SENT_READBACK_EXTRA_RECIPIENT");
  }
  return [...new Set(reasons)];
}

function draftReasons(transaction, snapshot) {
  const reasons = recipientReadbackReasons(transaction, snapshot);
  if (transaction.draft_message_id && snapshot.message_id !== transaction.draft_message_id) reasons.push("DRAFT_MESSAGE_ID_MISMATCH");
  if (transaction.thread_id && snapshot.thread_id !== transaction.thread_id) reasons.push("DRAFT_THREAD_ID_MISMATCH");
  const observedDigest = typeof snapshot.body === "string" ? digestContent(snapshot.body) : snapshot.content_digest;
  if (observedDigest !== transaction.content_digest) reasons.push("DRAFT_CONTENT_MISMATCH");
  return [...new Set(reasons)];
}

function blocked(reasons, providerInvoked=false) {
  return {decision:DECISION_BLOCK,provider_invoked:providerInvoked,reasons:[...new Set(reasons)]};
}

export async function executeSenderBoundary({transaction,receipt,provider,now}) {
  const tx = normalizeTransaction(transaction);
  const initial = validateReceipt(tx,receipt,now);
  if (initial.length) return blocked(initial);
  if (!provider || typeof provider.readSentCoverage !== "function") return blocked(["MISSING_SENT_COVERAGE_READER"]);

  let coverage;
  try { coverage=buildSentCoverage(await provider.readSentCoverage(tx)); }
  catch (_) { return blocked(["SENT_COVERAGE_READ_FAILED"]); }
  if (coverage.watermark !== receipt.sent_watermark || coverage.coverage_digest !== receipt.sent_coverage_digest) return blocked(["STALE_SENT_COVERAGE"]);

  if (tx.operation === "send_draft") {
    if (typeof provider.readDraft !== "function") return blocked(["MISSING_DRAFT_READER"]);
    let snapshot;
    try { snapshot=await provider.readDraft(tx); }
    catch (_) { return blocked(["DRAFT_READ_FAILED"]); }
    const reasons=draftReasons(tx,snapshot);
    if (reasons.length) return blocked(reasons);
  }

  if (typeof provider.submit !== "function" || typeof provider.readSent !== "function") return blocked(["MISSING_PROVIDER_BOUNDARY"]);
  let sent;
  try { sent=await provider.submit(tx); }
  catch (_) {
    return {decision:PROVIDER_STATE_UNKNOWN,provider_invoked:true,reasons:["PROVIDER_SEND_RAISED_RECONCILE_BEFORE_RETRY"]};
  }

  let readback;
  try { readback=await provider.readSent(sent,tx); }
  catch (_) {
    return {decision:PROVIDER_SENT_INTEGRITY_INCIDENT,provider_invoked:true,reasons:["PROVIDER_READBACK_FAILED"],provider_result:sent};
  }
  const reasons=recipientReadbackReasons(tx,readback);
  if (sent && sent.id && readback && readback.id !== sent.id) reasons.push("SENT_MESSAGE_ID_MISMATCH");
  const sentThread=sent && (sent.threadId || sent.thread_id);
  if (sentThread && readback && readback.thread_id !== sentThread) reasons.push("SENT_THREAD_ID_MISMATCH");
  if (reasons.length) {
    return {decision:PROVIDER_SENT_INTEGRITY_INCIDENT,provider_invoked:true,reasons:[...new Set(reasons)],provider_result:sent};
  }
  return {decision:VERIFIED_SENT,provider_invoked:true,reasons:[],provider_result:sent,readback:{id:readback.id,thread_id:readback.thread_id}};
}
