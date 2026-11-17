# Source-backed content campaigns

`content_orchestrator.prepare_campaign(brief)` compiles supplied public evidence
into an editorial package. It does not research a website, call a model, learn a
voice, book a slot, verify a source or publish. This is the first reusable content
layer from the [Soro audit](audits/SORO_SOCIAL_DAE_AUDIT_20261027.md).

## Input / output

`social_content_brief.v1` requires:

| Field | Contract |
|---|---|
| `campaign_id` | Lowercase ID, max64 characters |
| `brand` | Projection: foundup_id, canonical_brand, default_locale, nonempty rules, authority_boundary=`BRANDING_ONLY_NO_EXECUTION_AUTHORITY` |
| `audience`, `objective` | Nonempty text, max300 characters each |
| `cta` | `label` max80; `url` HTTPS DNS-name syntax, no credentials/port/query/fragment |
| `platforms` | Unique nonempty subset of `x`, `linkedin` |
| `start_at` | Explicit ISO date/time and UTC offset; no implicit host timezone |
| `interval_hours`, `max_items` | Integers 1..168 and 1..14; booleans reject |
| `sources` | 1..20 source_id/foundup_id/url/excerpt records; excerpts max1200; same FoundUp as brand |
| `topics` | 1..30 topic_id/title/source_ids/priority records; title max120; 1..5 existing unique source IDs; priority integer1..5 |

Unknown keys reject, including caller assertions such as `verified`, `approved`
or account/authority overrides. Public evidence/brand content must be reviewed by
the existing grounding/admission owners before effects. Source accuracy and rights
are not established by this syntax validator. Rules and locale are review inputs;
the deterministic source-preserving draft does not translate or implement voice.

Output `social_content_package.v1` contains deterministic priority order,
equivalent-evidence deduplication, proposed UTC slots, source-linked drafts,
review requirements, measurement join keys and a SHA256 `package_revision`.
The revision is an integrity identifier, not a signature or publication grant.
Reordered equivalent topics can produce the same output; unused sources remain
part of the package/revision. No stable effect job ID is issued here.

Each slot is an absolute elapsed interval. Daylight-saving local recurrence and
calendar collision checks belong to the existing scheduler. A proposed time may
be in the past; this compiler has no clock or booking side effects.

Drafts exceeding the existing platform raw-character limit return `content=null`
and `shorter_copy_required`, with the original sources retained. Short drafts
still require review and provider-specific length validation. No truncation is
performed and no SEO/performance score is fabricated.

## Existing SOCIAL entry

```text
social campaign content action=prepare dry_run=true brief='<inline JSON brief>'
```

For preparation, only `action=prepare`, `dry_run=true`, `brief` are accepted. Inline JSON max64KiB;
duplicate keys and malformed data reject with fixed diagnostics. No file-path
parameter is supported, and no new conversational publisher shortcut is added.
The standard SOCIAL classification/admission remains outside the pure compiler.

Use `config/content_campaign.example.json` as synthetic input. Python callers:

```python
from modules.platform_integration.social_media_orchestrator.src.content.content_orchestrator import prepare_campaign

package = prepare_campaign(brief)
assert package["publication_ready"] is False
```

The [remaining build sequence](audits/SORO_SOCIAL_DAE_AUDIT_20261027.md#remaining-build-sequence-and-acceptance)
covers research/model generation, admission/cadence, qualified publishing/CMS,
provider metrics and independently evaluated strategy changes.

## Community/newsletter instruction boundary

The [existing campaign skill's reusable workflow](../skillz/foundup_campaign_operator/references/community-newsletter-workflow.md)
coordinates private manuscripts, source evidence and platform-specific drafts.
It does not extend this compiler's schema or supported platform set. Keep private
issue/source bindings outside `social_content_brief.v1`; use only the supported,
reviewed public projection. Reddit/Substack remain DRAFT_OR_HANDOFF_ONLY until
their preparation and transport contracts are implemented and qualified.

## Publication reconciliation — 2026-11-16

The existing entry also accepts one effect-free receipt reconciliation action:

```text
social campaign content action=reconcile dry_run=true packet='<inline JSON>'
```

`action=reconcile` requires explicit `dry_run=true` and only `packet`, max64KiB,
unique JSON keys. It does not accept a path, publish/schedule action, account
override or caller grant. The prior `action=prepare` contract is unchanged.
The implementation is `src/content/publication_reconciliation.py`; its real
dispatcher fixture supplies a complete synthetic example in
`tests/test_content/test_content_orchestrator.py:publication_packet`.

`publication_reconciliation_input.v1` is strict: all fields below are required.
Non-null source revision/hash and stable identities are the minimum input;
without them, retrieve the source before compiling. Missing downstream evidence
uses null or the enumerated unknown state, never invented values. Nested unknown
keys reject. Strings and collections are bounded.

| Field | Required evidence |
|---|---|
| `foundup_id`, `publication_id`, `audit_at` | Stable IDs; explicit offset-aware audit time |
| `source` | Editorial `revision`, SHA256 `content_hash`, approval `{state, content_hash, receipt_ref}` |
| `archive` | Repository-relative `path`, immutable 40-hex `commit_sha`, manuscript `content_hash` |
| `website` | Expected exact HTTPS `url`, manuscript `source_hash`, deployment and observation below |
| `website.deployment` | `state` unknown/saved/blocked/succeeded, `source_revision` equal to the archive Git commit, `receipt_ref` |
| `website.observation` | `state` unknown/absent/present, actual `url`, `publication_id`, editorial `source_revision`, normalized manuscript `content_hash`, `observed_at`, `evidence_ref` |
| `channels` | 1..12 unique platform/locale/destination records for requested LinkedIn, Substack or Reddit review only |
| `open_work` | 0..30 unresolved obligations: `code`, `owner`, `next_action`, `evidence_ref`, `recorded_at` |

Each channel requires `platform`, `locale`, `destination`, exact edition
`artifact_hash`, editorial `source_revision`, manuscript `source_hash`, `approval`
and `delivery`. The channel approval has `{state, content_hash, receipt_ref,
destination, locale, platform, source_revision, source_hash}`: matching text
approval cannot silently authorize a different destination or translation.
Delivery has `{state, permalink, artifact_hash, observed_at, evidence_ref,
private_queue_checked, destination, publication_id, source_revision}`. Delivery
states are unknown/not_placed/draft/scheduled/live/submitted_unknown. Checks bind
the receipt to the issue/revision, destination and artifact. A live claim needs
a permalink; draft/scheduled/not_placed need private queue coverage. No public
absence, sent email or unrelated successful deployment establishes not_placed.

Hash comparisons require the **same approved manuscript/artifact bytes** under
an explicit upstream extraction policy. Raw HTML, a Doc export and a translation
are different objects; a collector must not label their unrelated hashes equal.
An unavailable normalization/build mapping remains unknown. The expected site,
publisher/account, series and destination must be resolved by existing owners;
the compiler performs no registry/host/account lookup and authenticates nothing.
HTTPS URLs retain the existing DNS/no-query/no-credential policy; this receipt
action alone allows bounded issue fragments. The editorial brief's URL rules
remain unchanged. Observation freshness is at most24hours before supplied
`audit_at`; this deterministic review bound is not a trusted clock or grant.

Output `publication_reconciliation.v1` exposes missing stages, per-channel next
actions and a deterministic review revision. `delivery_status` is only the
consistency result for the supplied claim; `delivery_status_is_verified=false`
and `evidence_status=SUPPLIED_UNVERIFIED` apply even when it says live. A known
permalink always selects `READBACK_EXISTING_NO_REPOST`; submitted_unknown always
selects `READBACK_ONLY`, even if its evidence is stale. Never create a new job ID
to retry an uncertain submission. The suggested duplicate key binds FoundUp,
issue, source revision, platform, locale and destination; it is not a durable
effect job and cannot provide exactly-once delivery.

Amplification review requires complete website prerequisites, no open work and
all requested derived editions reconciled as supplied live, source-bound and
approved. It still requires authentic provider readback, exact amplification
copy approval and existing SOCIAL DAE admission. An optional channel should not
be included as an automatic publication requirement; explicit editorial scope
selects channels. Reddit research never silently becomes a requested write.

The proposed memory projection carries audit time, canonical URL, immutable
archive, scoped receipt envelopes/timestamps/queue coverage, all open work,
named failed checks and channel next actions. Generated obligations explicitly
use owner `UNASSIGNED` until an existing owner accepts them. It is
`PROPOSED_NOT_WRITTEN`, `NOT_ADMITTED`, ingestion `NOT_ATTEMPTED`. It does not
fabricate verified outcomes or bypass the existing Brain/agent-db authenticity
owner. A sink acknowledgement and scoped readback must be recorded separately
before claiming memory persistence; a Git/Docs receipt alone is insufficient.

### Existing owners and remaining wiring

"Pub DAE" describes coordination through the existing SOCIAL adapter and
campaign owner. It introduces no new daemon, store, scheduler or production
skill promotion. Ingress is the current `social_campaign_adapter` content route;
the pure helper returns only review/proposed-continuity data. Existing WRE/SOCIAL
owners retain admission, cadence, cancellation, supervision and effect jobs.
The website owner retains build/deploy/live verification; each platform owner
retains account verification, exact-copy approval, actual placement and readback.
Current PublicationStore tables are X/AntifaFM-specific. No generic Sites,
LinkedIn-newsletter, Substack or Reddit writer is wired by this change.

The next existing-owner slice must collect authentic receipts, bind the current
archive/source/build and platform identities, persist acknowledged open work
through the governed sink and qualify provider/admission/cadence integration.
Until then this is an implemented dry-run reconciler and a documented handoff,
not a production publication pipeline. Legacy simulated success is not evidence.
The JHR failure and existing issue2126 obligation are recorded in
`modules/foundups/esingularity/jhr/PUBLICATION_AUDIT_20261116.md`.
