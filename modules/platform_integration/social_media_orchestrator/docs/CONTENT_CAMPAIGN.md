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

Only `action=prepare`, `dry_run=true`, `brief` are accepted. Inline JSON max64KiB;
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
