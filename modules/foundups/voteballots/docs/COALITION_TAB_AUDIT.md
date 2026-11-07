# Coalition tab: source audit and release boundary

Reviewed 7 November 2026 against Foundups-Agent `cb3aaa1129bd80b4350b24f7f091a323d18f772d`
and the clean Vote Sites mirror `482ab0e3f5829a899729778bee7d7ee3b379a693`.
Role: architect, with separate source audit and adversarial verification workers.
WSP 00 bootstrap/compliance passed. WSP 97 governs evidence and delivery claims.

## Decision

Extend the existing Vote informational PWA with a **Coalition** navigation page.
Use the established Vote identity, navy/ivory/brass design, project and domains.
Keep Oversight and the preserved 155-file source inventory intact. A framework,
database and authentication migration is not necessary for this public layer.

Call the page **Vote Coalition**, without implying that Hasan Piker or any other
named creator has joined, endorsed or authorized it. No member roster is seeded.
A person's public prominence is not their consent to coalition membership.

The delivered interaction prepares a voluntary application **draft** locally and
exports a JSON file at the visitor's request. It does not submit an application,
create an account, verify a profile, enroll a member or grant a permission.
The page must state this before the form and in its result. No affiliation,
location or ZIP-based political targeting, campaign routing or personalized
political messages are included.

The contact reference is the same for every visitor: the official [House
directory](https://www.house.gov/representatives), [Senate contact
directory](https://www.senate.gov/senators/contact/), and the U.S. Capitol
Switchboard number published by the Senate. Its `tel:` link opens the device's
dialer only on a visitor's action. It selects no office and records no call.

## Existing owners and retrieval

- `web/` owns the buildless public landing. Its JavaScript previously handled
  installation and service-worker registration only; there is no intake API.
- The Sites source repository is a deployment mirror. All eight previous public
  files match the canonical source after newline normalization; five differences
  were CRLF/LF only. Its hosting manifest declares static `dist/` output.
- `youtube_auth` is operator-installed-app authentication. Its configured scopes
  and operator tokens are not a public visitor OAuth service or ownership proof.
- The member Mall's Clerk/invite/username flow is not coalition verification.
- Do not reuse `functions/index.js`'s reviewed `processSignup` handler unchanged:
  it accepts a payload UID without binding that UID to `request.auth` in the
  handler. This is an audit finding, not a repair or live exploit demonstration.

Holo retrieval returned `HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH`; semantic
freshness remains **UNKNOWN**, with an index gap. Exact local module files are
the evidence. Generic/duplicate lexical hits were discarded, module contracts
read first, and optional missing memory/requirements files were not scaffolded.
No authority reset or reindex was performed. Native worker delegation provides
implementation and independent verification; no Qwen/Gemma outcome or RSI gain
is claimed for this release.

## Findings in the proposed full-stack specification

1. **Keep four decisions separate:** provider-account control, observed audience
   metrics, explicit membership consent and server-issued authority. An allowlist
   or subscriber threshold must not enroll a creator or grant administrative,
   official, publishing or moderation rights.
2. **Bind identity server-side.** Never trust a submitted user ID. Reject an
   attempt to overwrite a channel bound to another principal; transfers and
   account linking need their own authenticated, audited flow. Refreshing a
   profile must not silently preserve a stale allowlist decision.
3. **Use provider-specific OAuth contracts.** Callback state, PKCE, exact
   registered redirects, session binding, minimal granted scopes, token expiry
   and revocation all need verification. Tokens belong on the server, outside
   public bundles, logs and browser storage. Google documents exact redirect
   matching and callback-state checks in its [OAuth server guide](https://developers.google.com/identity/protocols/oauth2/web-server).
4. **Treat metrics as observations.** YouTube's subscriber count is rounded;
   visibility and missing statistics require explicit unknown states. Its
   [`mine` channel filter](https://developers.google.com/youtube/data/reference/rest/v3/channels/list)
   identifies channels owned by the authenticated provider account, not coalition
   membership. See the [channel resource](https://developers.google.com/youtube/data/reference/rest/v3/channels).
   Twitch subscription access is a distinct permission from basic identity;
   a shared YouTube/Twitch numeric threshold is not an equivalent identity test.
   See [Twitch scopes](https://dev.twitch.tv/docs/authentication/scopes/).
5. **Official status requires independent review.** A typed handle, URL, `.gov`
   string or badge cannot grant an official role. A future challenge must bind
   the applicant, expected opaque provider account, purpose, expiry and single
   use. Account control still does not establish endorsement.
6. **Complete the data model before backend admission.** The supplied sketch
   references undefined Account, Endorsement and SeedRegistry models. It also
   lacks a declared author relation, independent role grants, consent records,
   verification provenance, review/revocation and immutable content revisions.
   Votes need per-principal uniqueness and transactional events. Mutable counters
   alone do not prove unique votes or completed calls.
7. **Protect public submissions and content.** Authentication, operation-level
   authorization, CSRF controls, bounded bodies, rate limits, moderation and
   abuse controls precede an intake receiver. Render Markdown safely and constrain
   embeds/links. Redis can accelerate reads; it is not identity, audit authority
   or complete DDoS protection. Private applications and sessions must not enter
   public caches.

## Public draft contract

`web/coalition-draft.mjs` exposes `createCoalitionDraft(input, createdAtISO)`.
Only known, bounded display-name, participation-role, public-profile and
contribution fields may enter the export. Acknowledgment must be exactly true.
Profile URLs are claims, never active proof; unsafe schemes, credential-bearing
URLs and deceptive hosts are refused. Metadata is fixed to schema version 1,
`DRAFT_NOT_SUBMITTED` and `UNVERIFIED`. No client-supplied badge, role grant or
arbitrary property may become authority.

The form uses explicit validation and text-only preview rendering. It performs
no network requests and uses no persistent browser storage. It does not collect
email, government IDs, passwords, credentials, political affiliation or location.
The service worker caches reviewed public shell files only. The download is
private to the visitor's device; it is not a server receipt or membership badge.

## Release gates and remaining scope

- Run meaningful independent adversarial draft tests, JavaScript syntax checks,
  public-page/link/manifest checks and the unchanged Oversight preservation guard.
- Review the complete diff and preserve all existing public assets and domains.
- Reconcile/push the existing Sites mirror, package that exact source, save and
  publish through the existing project, then verify actual HTTPS page/assets.
- Record browser layout/interaction results and any verification limit separately
  from a successful source check or deployment receipt.
- Merge through normal GitHub checks, verify resulting main, synchronize the PC
  without overwriting unrelated work and remove the owned disposable worktree.

An authenticated intake receiver, provider OAuth, official-status review,
membership grants, moderated briefing CMS, consensus votes and live enrollment
are **not delivered** by this public-tab release. The earlier proposed calling,
payments and AI voice component is also separate. No public profile or draft
export should be represented as any of those capabilities.
