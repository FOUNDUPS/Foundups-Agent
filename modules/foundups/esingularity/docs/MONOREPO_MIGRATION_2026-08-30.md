# eSingularity monorepo migration record

## Decision

Project eSingularity is a FoundUp. Its canonical incubation path is therefore `modules/foundups/esingularity`, not a root-level `sites/` checkout.

## Preserved

- Existing public routes and campaign content
- Existing media and privacy-safe team assets
- Existing package manager and lockfile
- Existing OpenAI Sites project and D1 declaration
- Existing source-of-truth and production audit documents

## Changed

- Canonical source ownership moved into the FoundUps domain.
- The Vinext/Sites product surface is now the module's `frontend/` block.
- FoundUps registry and WSP 104 namespace contracts now identify the project.

## Explicitly unchanged

- DNS and the `esingularity.ai` domain
- Public design and editorial content
- LINE invitation URL
- Financial or engineering claims
- Authentication, fundraising, token, CABR, payout, and DAO state

## Rollback

The original nested checkout is retained as a recoverable archive until the migrated source has built and deployed successfully.
