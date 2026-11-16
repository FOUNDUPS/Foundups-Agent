# Poly Voice

**Status:** DOCUMENTATION_ONLY / SPECIFIED_NOT_IMPLEMENTED.
**Classification:** separate planned FoundUp connected to the Vote ecosystem; no registry or runtime admission.
**Proposed ID:** `polyvoice` (working product name, not a uniqueness or trademark claim).

## Outcome -> solution -> pain

**Outcome:** a participant retains a private, reviewable record of a business meeting and can voluntarily attest to a committed record without uploading the conversation.

**Solution:** manual, consented on-device capture; local extraction of a business-only structured JSON; local review and encryption; optional reviewed commitment receipt. Personal/non-business content is excluded from the business summary, not silently erased from retained source evidence. Source retention, interruption and deletion must follow an explicitly qualified policy.

**Pain:** disclosure and accountability can conflict with private conversation, confidential material, misclassification and device reliability. These are product hypotheses, not findings about any individual or evidence that non-adopters are concealing something.

## Ownership

Poly Voice owns meeting scope, consent, local review, private record lifecycle and commitment/disclosure policy. It is not the public calling/endorsement engine (**Voice**) or the verified-official ballot module (**Poly Vote**). It can reuse qualified shared services without transferring ownership of meeting assets.

The Foundups-Agent monorepo owns this documentation. AutoPost is a separately maintained potential capture dependency, not the owner of this product or a default publishing path. The [integration index](../voteballots/docs/VOTE_VOICE_INTEGRATION.md) connects the components without combining their roadmaps. No new repository or cloned Mall is requested.

## Read order

[Interface](INTERFACE.md) -> [roadmap](ROADMAP.md) -> [intake source](docs/intake/INTAKE_SOURCE.md) -> [change log](ModLog.md).

The intake's eight artifacts document a proposed FoundUp; they do not create a manifest, registry entry, tenant, wallet, route or deployed service. Runtime admission requires the existing onboarding and permission owners.

## Hard boundaries

The business JSON, raw conversation, transcript, speaker representations, source mapping and private keys stay local by default. No cloud speech fallback, social publication, telemetry copy or remote-agent ingestion is implied. Encrypted storage is a requirement to prove, not a capability claimed here. A second copy on the same phone is not disaster-recovery backup; off-device backup is not authorized by this design.

A hash is not a meeting transcript, encryption, proof of a meeting, or proof that nothing was omitted. Commitment receipt semantics and any optional public event metadata need separate explicit qualification. No capture, hashing service or endpoint is implemented by these files.
