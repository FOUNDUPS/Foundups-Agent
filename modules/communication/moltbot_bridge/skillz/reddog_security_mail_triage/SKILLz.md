---
name: reddog_security_mail_triage
description: Deduplicate and verify security-alert mail against exact repository, workflow, scanner, and deployment evidence
version: 0.1.0
author: 0102
agents: [0102, qwen, gemma]
primary_agent: 0102
dependencies: [reddog_gmail_intake_router, security_scan]
domain: security_operations
intent_type: DECISION
promotion_state: prototype
pattern_fidelity_threshold: 0.99
category: safety
wsp_chain: [WSP_00, WSP_15, WSP_48, WSP_50, WSP_77, WSP_91, WSP_95, WSP_97]
evals:
  - repeated_report_counts_not_summed
  - exact_commit_digest_reproduction_required
  - separate_credential_candidates_remain_open
  - incomplete_scan_never_clean
  - no_secret_value_in_receipts
---

# Red Dog security-mail triage

## Purpose

Turn security-vendor, CI, scanner, and repository alert mail into a deduplicated,
evidence-grounded work receipt. Email is a notification channel, not proof of a
vulnerability, resolution, secret, repository state, or deployment state.

This skill does not send mail, rotate credentials, change vendor incidents,
modify repositories, deploy, or publish vulnerabilities. Each effect requires
its current owner and authorization.

Read first:

- `modules/communication/moltbot_bridge/docs/clarity/gmail_wre_rsi_routing.md`
- `modules/infrastructure/wre_core/skillz/security_scan/SKILLz.md`
- `WSP_framework/src/WSP_97_System_Execution_Prompting_Protocol.md`

## Triage sequence

1. Read the exact provider message/thread without changing unread/archive state
   unless the work order explicitly authorizes that effect.
2. Extract vendor, repository, alert/scan ID, detector, severity claim, commit/
   object reference, path, timestamp, and report scope without copying a secret.
3. Deduplicate by stable vendor incident ID. If unavailable, use repository +
   detector + exact commit/object fingerprint. Repeated scan totals are not
   unique-incident arithmetic and must never be added together.
4. Verify the current repository default-branch SHA, relevant exact PR heads,
   current file content, security workflow results, and deployment revision when
   exposure depends on deployment.
5. Compare the alert's exact historical object to current code before assigning
   `UNRESOLVED`, `RESOLVED`, `FALSE_POSITIVE`, or `UNKNOWN`.
6. Record scan coverage, missing tools, failures, confidence, deployment
   applicability, and the next authorized owner/action.
7. Keep every separate credential-shaped candidate open until independently
   verified; do not generalize a false-positive class to unrelated paths.

## Digest false-positive rule

A SHA-256 manifest/evidence value may be classified as a detector false positive
only when all of these are true:

- the alert identifies the exact repository, path, detector, and commit/object;
- the field semantics declare a digest/checksum/evidence hash;
- the referenced source bytes at that exact commit are retrieved independently;
- recomputing SHA-256 over those exact bytes reproduces the flagged value;
- no independent evidence shows the value is an active credential.

Do not include the value in the receipt, comment, email, log, Moshpit, or report.
Record only a redacted fingerprint and the recomputation result. Same path,
similar length, a vendor label, or an email assertion is not enough.

## Genuine-secret path

For a credential-shaped finding:

- minimize display and never broaden access to the value;
- confirm repository/path/commit and whether the value is current or historical;
- determine exposure and deployment applicability without testing the credential
  against a live service unless explicitly authorized;
- route revocation/rotation to the credential owner;
- remove or quarantine source through the repository owner;
- add prevention and history-cleanup recommendations separately;
- verify resolution using current code, provider/vendor state, and deployment
  state as applicable.

A source removal does not prove credential revocation. A vendor dismissal does
not prove the deployment is safe.

## Scanner and WRE boundary

The existing WRE `security_scan` supplies bounded scanner evidence. Preserve its
actual `completed|partial|error|tool_unavailable` state. Missing tools, parse
errors, nonzero coverage failures, or a nonblocking CI grep are not clean scans.
Do not describe the prototype/manual scanner as a full-repository autonomous
audit.

Use WRE for orchestration and receipts when appropriate. WRE does not authorize
provider mutation, repository mutation, secret rotation, deployment, or vendor
classification.

## Output receipt

Emit a redacted receipt containing:

- provider and vendor incident references;
- repository, alert object SHA, current main SHA, and relevant PR exact heads;
- detector and redacted fingerprint;
- deduplication key/method and related report IDs;
- verification steps and evidence references;
- status: `UNRESOLVED|RESOLVED|FALSE_POSITIVE|UNKNOWN`;
- confidence and explicit contradictions;
- scanner coverage plus missing tools/errors;
- deployment applicability: `YES|NO|UNKNOWN`;
- severity after verification, not merely vendor severity;
- current owner, next authorized action, and notification threshold.

Never store the secret value or raw message body.

## Notification discipline

Notify only a new verified high/critical finding, materially changed exposure,
verified resolution, or new blocking coverage failure. Aggregate routine
duplicates and unchanged lower-severity state. A draft/response must still pass
the independent release gate and recipient preflight.

## RSI boundary

A repeated detector mistake or triage failure may nominate a sanitized
engineering lesson. Promotion requires independent evidence and WSP 48
measurement, including later-use benefit. The triage skill cannot mark its own
lesson learned or production RSI.
