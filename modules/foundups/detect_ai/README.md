# AmIBot

**FoundUp ID:** `detect_ai` | **Owner:** 012 | **Intake:** 0102
**Status:** Registered skeleton candidate; SPECIFIED_NOT_IMPLEMENTED; TOKEN_DEFERRED.

A browser-first social detection game and evaluation FoundUp. Participants consent to an undisclosed human-or-AI partner, chat, lock a classification and confidence estimate, then see the result. Separate leaderboards compare human detectors, agent detectors, and conversational models. A separate Red Dog evaluation measures useful behavior rather than merely appearing human.

## Read order

1. [Outcome](docs/intake/OUTCOME.md)
2. [Solution](docs/intake/SOLUTION.md)
3. [Pain](docs/intake/PAIN.md)
4. [POC scope](docs/intake/POC_SCOPE.md)
5. [Prototype gate](docs/intake/PROTOTYPE_GATE.md)
6. [Skills map](docs/intake/SKILLS_MAP.md)
7. [Manifest draft](docs/intake/FOUNDUP_MANIFEST_DRAFT.md)
8. [Intake source and retrieval limits](docs/intake/INTAKE_SOURCE.md)

Supporting contracts: [benchmark](docs/BENCHMARK_CONTRACT.md), [research](docs/RESEARCH.md), [roadmap](ROADMAP.md), [change log](ModLog.md).

## Execution boundary

The existing intake now has a declarative [manifest](foundup_manifest.json),
[interface contract](INTERFACE.md) and canonical [registry entry](../foundup_registry.json).
It remains hidden, unbuilt and token-deferred. Registration does not authorize
runtime execution, catalog listing or public deployment.

012 -> RedDog/0102 intake -> WSP 109 packet -> WRE/architect routing -> bounded workers -> independent verification -> evidence returned to RedDog.

This describes the intended repository workflow, not evidence of running background workers. WRE acceptance and runtime dispatch have not occurred in this session.

Next bounded slice: `DETECT_AI_PREFLIGHT_AND_POC_CONTRACT_PHASE1`. Resolve remaining
retrieval, scope, dependency and runtime-admission gaps before construction.
Extend this existing module; do not create a second scaffold or FoundUp identity.

## AmIBot research update - 2026-09-15

Display name: **AmIBot**. Tagline: **Can you detect AI?** The original working name is retained only as provenance. Internal ID and path remain `detect_ai` to avoid a second FoundUp, route, or issue.

[Chat, PWA and safety research](docs/CHAT_PWA_SAFETY_RESEARCH.md) is the current technical decision record. Recommendation: an installable browser client with a small server-authoritative Socket.IO service, subject to the existing-owner preflight. Colyseus is the shortlisted alternative, not an additional runtime.

The first playable slice is invite-only, 18+, text-only and clean-chat only. Pre-delivery moderation, report/block/leave and an operator kill switch are pilot gates. Mature/NSFW rooms and their stronger age-assurance integration are deferred and disabled. Phone-hosted model inference is a later opt-in practice experiment, not the trusted benchmark or an always-on background worker.

PR #1751 preserves intake and registration lineage; issue #1750 remains the
bounded preflight/build-contract handoff. No application has been built or deployed.

## Route Namespace

WSP 104 declares `foundup_id=detect_ai`, landing `/f/detect_ai` and subordinate
deep links `/f/detect_ai/app/{path...}`. These are inactive declarations.
012's requested `/f/amibot` remains a public-surface dependency: the current shell
looks up exact IDs, so its owner must reconcile the name before publication.

## App Mount

Declared mount: `/f/detect_ai/app`. No bundle, active route or public entry URL
exists. No DNS or domain configuration is required by this experiment.

## AI Capability Hooks

`get_status`, `get_context`, `navigate`, `launch_capability` and shell handoff/return
are planned concepts only. No hook or agent route is implemented or enabled.

## DAEmon Outputs

No AmIBot DAEmon runs. Planned WSP 91 outputs are health, last action, error state,
recommended next action, queue/work state and per-order verification receipts.
The build package is planning evidence; it is not a live health or job report.

## Data / Telemetry Namespace

Declared namespace: `idb_detect_ai`. Future caches, storage, logs and traces must
remain tenant-scoped; no private chats may enter public/offline cache. No storage
or telemetry has been provisioned by registration.

## WSP References

WSP 00, 15, 22, 49, 50, 95, 97, 99, 109; WSP 91 observability and WSP 104 tenant
isolation follow the existing
[FOUNDUP_AI_HOOKS_AND_DAEMON_SURFACE_CONTRACT.md](../docs/FOUNDUP_AI_HOOKS_AND_DAEMON_SURFACE_CONTRACT.md).
Registration follows the existing [onboarding protocol](../docs/FOUNDUP_ONBOARDING_PROTOCOL_PHASE1.md).
