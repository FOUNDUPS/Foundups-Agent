# EDUIT interfaces

All interfaces here are **SPECIFIED_NOT_IMPLEMENTED**. Names are semantic contracts;
HTTP routes and authentication adapters must be reconciled with the actual gateway
owner during implementation, not assumed to exist because they appear in this file.

## Platform hooks

| Hook | Input/authority | Output and denial behavior |
| --- | --- | --- |
| get_status | Tenant context; public summary only | implementation/runtime state, release version, safe health; no learner metrics |
| get_context | Authorized role plus requested scoped purpose | Bounded role-specific context with provenance; deny wider cohort/learner scope |
| navigate | Target subordinate to `/f/eduit/app` | Allowed route or route-denied; no shell-root takeover |
| launch_capability | Declared capability plus admitted actor/context | `play`, `review_evidence`, or `propose_content` session reference; deny unavailable capability |
| shell handoff/return | Allowlisted destination and opaque return reference | No learner evidence in URLs/query strings; re-authorize on return |

## Learning operations

`start_session` receives mode, approved pack/version, selected locale, accessibility
settings, and an authorized learner or ephemeral guest reference. It returns a session
reference, policy version and permitted event schema. `record_event_batch` validates
schema, scope, timestamps/sequence and idempotency before acknowledgement.
`get_progress` returns authorized progress, not a global ability rank.
`request_export` and `request_deletion` return tracked operations with scope and status.

## Discovery and opportunities

`build_evidence_summary` requires qualified measurement versions and sufficient evidence;
otherwise it returns `insufficient_evidence` with specific reasons. It returns observed
strengths, uncertainty, task provenance, input/context limitations and alternative
interpretations, not an IQ or genius diagnosis.

`propose_opportunity` requires a vetted provider, verified eligibility criteria and current
specific sharing permission. `approve_referral` is a human decision separate from the
proposal. `deliver_referral` rechecks consent and recipient, uses an idempotency key, and
records a provider receipt. No email is sent merely because an AI suggests it.

Referral states: `draft -> consent_pending -> human_review -> approved -> delivered`;
`declined`, `withdrawn`, and `failed` are terminal outcomes for that attempt. Revocation
before delivery prevents sending. Post-delivery withdrawal triggers partner follow-up
under the documented agreement; do not promise data retrieval from an external recipient.

## Content-improvement operations

`propose_content` creates a sandbox candidate linked to its parent release and purpose.
`evaluate_candidate` records functional, accessibility, privacy and educational results
against frozen baselines. `approve_release` requires a separate authorized reviewer.
`publish_release` checks admission, evidence, approved hash and rollback target at use-time.
Changes to measurement/scoring create a new version and require recalibration.

## Error and audit contract

Stable classes: `unauthorized`, `consent_required`, `scope_mismatch`, `invalid_event`,
`unsupported_version`, `duplicate_event`, `insufficient_evidence`, `capability_unavailable`,
`release_not_approved`, `provider_failure`. Public logs exclude identifying data.
Audit records include actor authority, purpose, policy/version, request ID, result,
and receipt reference. Do not log arbitrary free text from child sessions.

See [data contract](docs/DATA_CONTRACT.md) and [safety/privacy](docs/CHILD_SAFETY_AND_PRIVACY.md).
