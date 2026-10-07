# Data contract

Status: specified. The event schema is a POC software contract, not a validated
measurement model. Examples are synthetic and must never be mistaken for learner data.

## Event envelope

[schema](../schemas/learning_event.schema.json),
[synthetic example](../examples/learning_event.json).
The minimum envelope identifies tenant, session, pseudonymous/ephemeral learner,
event ID, mode, item and pack versions, sequence, selected outcome and approved
accessibility context. Use a closed schema; reject undeclared extra fields.
The schema cannot establish consent, enforce security, verify identity, or measure talent.
Those checks belong to the authorized service and study protocol.

## Other records to implement later

| Record | Required semantics |
| --- | --- |
| Consent record | Subject, guardian authority where applicable, purpose, policy version, time, expiry/revocation, auditable evidence |
| Content release | Pack/version, objective map, license, asset hashes, reviewer, approved configuration, rollback target |
| Evidence summary | Authorized scope, included/excluded events, task/scoring/model versions, uncertainty, limitations, reviewer status |
| Opportunity | Vetted provider, criteria/source/date, geography and age restrictions, funding availability, sharing terms |
| Referral receipt | Exact approved recipient/payload version, use-time permission check, idempotency key, delivery status |
| Deletion operation | Requested scope, affected stores/derived data/backups, tombstone, completion evidence and remaining exceptions |

## Data minimization and lifecycle

A guest reference is not permission to persist a child profile. Consent and contact
records stay separate from learning events. Do not collect exact location, date of birth,
face, voice, eye-tracking, health data, household income, or sensitive demographics in
the first POC. Accessibility selection is for usability, not disability diagnosis.
Research involving additional variables requires an explicit approved purpose and protocol.

Local/demo data are synthetic. Before a participant pilot, define per-record retention,
expiration, authorized access, export, deletion, backups, offline-queue invalidation,
and processor agreements. No indefinite retention by default. Pseudonymization is not
anonymization. Public reporting requires disclosure-risk review, including small groups.
Child records and ability profiles never go on chain or into public training datasets.

## Integrity

Derive scope from authenticated context. Treat client-supplied `foundup_id` and
`learner_ref` as claims to check, not authorization. Verify item outcomes server-side
when stakes justify it, without assuming invasive surveillance is required.
Deduplicate by tenant/session/event ID; reject conflicting duplicate payloads;
record version changes rather than silently rescoring old events.
