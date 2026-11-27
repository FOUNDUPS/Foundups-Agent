# Labs Interface — proposed, not implemented

Consumers: public FoundUps.org/Play discovery; Labs direct-entry public projection; authenticated program and project interiors. Reuse p.fMALL `FoundUpManifest`, `FoundUpTile`, `resolve_route` and the existing navigation/state owner, subject to code audit.

## Read model (proposed fields, not API)
Program: stable_id, canonical_url, display_name, independent_or_affiliate_status, affiliation_evidence, public_summary, organization, category, publication_consent, source_revision.
Cohort: stable_id, program_id, year, label, visibility.
Project: stable_id, founder/team rights holder, program/cohort association, title, year, lifecycle_status, public board, approved artifacts, access policy, provenance, last_update.
Membership: subject_id, program_id, scoped_role, issuer, expiry, revocation; project permissions are independent. Never expose private fields in public tiles.

## Proposed commands (not available today)
CreateProgram requires authorized affiliate creator; CreateProject requires scoped program admission and founder/team consent; PublishProject requires review/permissions; RateProject requires admitted verified account and moderation. A claim or email code alone does not confer affiliation, ownership, publishing rights or broad program access.

## UI behavior
Public program/project tiles open same HPC-sized stage as a board. Approved video uses the same stage. Back restores board or tile, scroll, search, selection, caller and focus. Provide accessible controls alongside gestures; no protected prefetch. Private routes revalidate access server-side on every operation. Direct entry without caller returns to public Labs wall.

## Compatibility and testing
No change to HPC, shared p.fMALL dimensions, player or WSP 104 route semantics. Test uninvited public access, distinct program gates, private project leakage, founder export, minors consent, Back/gesture/keyboard/voice fallback, and independent vs affiliate badge accuracy. All runtime behavior is acceptance target until separately verified.
