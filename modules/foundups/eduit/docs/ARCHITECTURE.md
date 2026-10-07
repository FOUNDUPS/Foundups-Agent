# Architecture — software first, one EDUIT tenant

Status: planned; no deployment implied.

## Logical components

The Experience is the browser/PWA learner client. It loads approved versioned content
packs and runs deterministic game logic. The learner-state service stores authorized
progress. The evidence service summarizes measured task behavior; Discovery proposes
reviewable opportunities only after qualification. An operator-only content workflow
creates and evaluates candidates using the existing FoundUps execution/admission owners.

```text
approved content catalog -> The Experience -> scoped learning events
                                   |                    |
                            local/offline state     evidence summaries
                                                        |
                                         qualified Discovery review
                                                        |
                                      permission-checked opportunities

candidate authoring -> sandbox -> independent evaluation -> release registry
                                (no direct learner deployment)
```

## Deployment progression

POC: a static browser client and synthetic/local data; no backend required to establish
that the learning loop works. Prototype: add a consent/identity boundary, tenant-scoped
API adapter, persistent progress and managed synchronization. Research pilot: freeze
measurement packs and evaluate them prospectively. Public release is a separate gate.
A PWA cache does not make first-time access possible without any provisioning.

## Storage and trust boundaries

Namespace `idb_eduit` is necessary but not sufficient. Every persisted operation also
carries organization/cohort and learner scope derived from authenticated authority,
not trusted directly from client JSON. Store guardian identifiers/consent separately
from pseudonymous events and separate both from operator logs and public metrics.
No shared cross-FoundUp learner memory. Local shared-device sessions need an explicit
clear/switch-user operation and a documented cache-retention policy.

## Versioning and synchronization

Pin game, pack, rules, scoring, locale, input adaptation, and model versions. Signed or
otherwise authenticated release manifests identify approved assets and hashes.
Event IDs are idempotency keys; duplicate submissions do not create extra outcomes.
Out-of-order events remain attributable to sessions. Never rewrite evidence from an
older scoring version in place. Derived summaries carry provenance and supersession.
Deletion tombstones suppress rehydration from offline queues and restored backups.

## Reuse before building

Reuse the current FoundUp registry, shell route rules, gateway/authentication owners,
observability contracts, and WRE admission/release mechanisms when their availability
is verified at implementation time. S04’s GuiGame is historical intent, not an existing
runtime dependency. Do not build a second scheduler or import a quantum/AGI claim as
an architectural requirement.

## Infrastructure relationship

`esingularity_001` is not the EDUIT learner tenant. Future hosting could use eSingularity
compute, other infrastructure, or a local installation under explicit contracts.
No onsen, school asset, financing, or regional-site dependency blocks the software POC.

## Failure behavior

Network unavailable: approved local practice continues; cloud-dependent discovery is
unavailable, not guessed. Model unavailable: deterministic approved game remains usable.
Consent unavailable/revoked: stop the affected processing and sharing; retain an allowed
learning alternative. Validation failure: retain current release and quarantine candidate.
Untrusted pack/event: reject with a bounded error and no public child information.
