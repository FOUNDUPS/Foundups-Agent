# Evidence contract

Use the root evidentiary-packet schema as the only packet contract. A source must be identifiable by issuer, title, publication or record date, public locator, retrieval date and exact support pinpoint. A law citation requires a version or effective-date check and later-history review. For a blockchain event retain chain/network, transaction hash, block reference, asset contract and extraction method.

Maintain original and derived data separately. A hash records byte identity, not truth, authenticity or lawful acquisition. Record transformations, script version, units, time zones and a reproducible calculation. Keep ambiguous entity matches and attribution hypotheses separate from established relationships.

A fact describes what a source actually establishes. An allegation identifies who asserted it. An inference names its premises, method and limits. An unknown states the missing evidence. Counterevidence belongs beside the proposition it qualifies. Do not disguise uncertainty with numeric precision or an aggregate trust score.

No public packet may include private returns, SAR content or existence information, sealed material, grand-jury secrets, privileged communications, confidential personal identifiers or credentials. Congress, a prosecutor and a public researcher have different powers and disclosure limits. A model instrument is an unsigned draft until the actual authorized actor approves, authenticates and lawfully issues it.

Machine checks assess structure, references and selected reproducibility conditions. A human must inspect the primary record, verify the proposition and approve public wording. For consequential legal claims, obtain qualified legal review. Record disagreements and correction history rather than silently replacing findings.

## Packet field binding

Use `schema_version` 1.0.0. Give a packet its `PKT-` identifier and the originating `SPOKE-` task identifier. Supply `created_at`, contributors, scope, sources, claims, entities, relationships, custody, review, disclosure and limitations exactly as the root schema requires. `claims[].status` is one of `fact`, `allegation`, `inference`, or `unknown`; counterevidence is a separate array on the claim. Reference `source_id` in every citation and provide a claim-specific pinpoint and statement of what the source supports.

A newly submitted packet has `review.status` equal to `unreviewed`. A contributor-controlled review field never authorizes publication. The publication gate is a separate trusted maintainer registry, `approved-packets.json`, containing the identifier and hash of the exact approved JSON. Check the actual registry location in the repository publication policy before release. Changed bytes require fresh approval. Set `disclosure.classification` to `public` and `contains_restricted_data` to false only after checking the packet; do not use those values to conceal uncertainty about source restrictions.

The original root schema controls if this reference and executable validation diverge. Report the mismatch rather than silently emitting a different packet. A task card is a research-planning form and is not an evidentiary packet.
