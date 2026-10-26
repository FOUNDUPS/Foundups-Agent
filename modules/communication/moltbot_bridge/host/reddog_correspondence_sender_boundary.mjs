/*
 * Quarantined v2 compatibility surface (#1779).
 * Caller-loadable code cannot isolate direct Gmail capabilities or authenticate
 * composer-supplied evidence. Do not restore a second recipient resolver here.
 * The service-owned v3 authority is src/reddog_correspondence_sender_boundary.py.
 */
export const DECISION_BLOCK = "BLOCK";
export const RECEIPT_SCHEMA = "reddog-correspondence-preflight.v2-quarantined";
const blocked = () => ({decision:DECISION_BLOCK, provider_invoked:false,
  reasons:["TOOL_HOST_AUTHORITY_NOT_INSTALLED"]});
export function buildRecipientPreflightReceipt() { return blocked(); }
export async function prepareRecipientPreflightReceipt() { return blocked(); }
export async function executeSenderBoundary() { return blocked(); }
